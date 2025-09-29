______________________________________________________________________

## title: Applying Kimball Dimensional Modeling to SPEC-1 date_time: 2025-09-29 21:09:54 UTC version: 1.1 status: reviewed author: Jason Shaffer audience: \[data engineers, data analysts, data scientists\] tags: \[kimball, dimensional modeling, dbt, duckdb, external parquet\]

## Applying Kimball Dimensional Modeling to SPEC-1

<!--toc:start-->

- [Introduction](#introduction)
- [Core Dimensional Design Process](#core-dimensional-design-process)
  - [1. Four-Step Design Process](#1-four-step-design-process)
  - [Step 1: Select a Business Process](#step-1-select-a-business-process)
  - [Step 2: Declare the Grain](#step-2-declare-the-grain)
  - [Step 3: Identify the Dimensions](#step-3-identify-the-dimensions)
  - [Step 4: Identify the Facts](#step-4-identify-the-facts)
- [Key Techniques for Implementation](#key-techniques-for-implementation)
  - [Dimension Surrogate Keys](#dimension-surrogate-keys)
  - [Conformed Dimensions](#conformed-dimensions)
  - [Grain Declaration and Enforcement](#grain-declaration-and-enforcement)
  - [Transaction vs Periodic Snapshot vs Accumulating Snapshot](#transaction-vs-periodic-snapshot-vs-accumulating-snapshot)
  - [Slowly Changing Dimensions](#slowly-changing-dimensions)
  - [Junk Dimensions](#junk-dimensions)
  - [Role-Playing Dimensions](#role-playing-dimensions)
  - [Multivalued Dimensions with Bridge Tables](#multivalued-dimensions-with-bridge-tables)
  - [Consolidated Fact Tables](#consolidated-fact-tables)
  - [External Parquet Tables (per SPEC-1)](#external-parquet-tables-per-spec-1)
  - [Identity Resolution Pattern](#identity-resolution-pattern)
  - [Asset-Based Modeling (Players and Picks)](#asset-based-modeling-players-and-picks)
  - [Freshness Tests](#freshness-tests)
  - [Accepted Values (Grain Enforcement)](#accepted-values-grain-enforcement)
  - [Referential Integrity](#referential-integrity)
- [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
  - [1. Centipede Fact Tables](#1-centipede-fact-tables)
  - [2. Snowflaking](#2-snowflaking)
  - [3. Fact-to-Fact Joins](#3-fact-to-fact-joins)
- [Implementation Checklist](#implementation-checklist)
  - [Phase 1: Foundation](#phase-1-foundation)
  - [Phase 2: Core Dimensions](#phase-2-core-dimensions)
  - [Phase 3: Fact Tables](#phase-3-fact-tables)
  - [Phase 4: Marts](#phase-4-marts)
  - [Phase 5: Quality and Ops](#phase-5-quality-and-ops)
- [Decision Framework](#decision-framework)
  - [When to use each technique](#when-to-use-each-technique)
- [References](#references)

<!--toc:end-->

## Introduction

This guide maps Kimball's dimensional modeling techniques to this Fantasy Football Analytics platform (SPEC-1 v2.2). It provides practical implementation guidance for working with dbt, DuckDB, and external Parquet storage.

## Core Dimensional Design Process

### 1. Four-Step Design Process

Follow this sequence for each data mart in this Fantasy Football Analytics platform:

#### Step 1: Select a Business Process

- `fact_player_stats`: Weekly player performance (NFL stats)
- `fact_asset_market_values`: Trade valuations (market pricing)
- `fact_commissioner_roster`: Roster management (commissioner data)
- `fact_fantasy_projections`: Fantasy projections (aggregated from multiple sources)
- `fact_league_transactions`: League transactions (Sleeper API)

**Implementation:** Each process maps to a separate dbt model or model group. Don't mix grains in a single fact table, as this will make it difficult to maintain.

#### Step 2: Declare the Grain

The grain is the binding contract for the high-level data model.

##### Rules

> **Critical:** The grain is the most important decision in dimensional modeling. Get this wrong and everything downstream suffers.

1. Grain is the binding contract for the high-level data model.
1. Each fact table should have exactly one grain.
1. Never mix grains in a single fact table, as this will make it difficult to maintain.
1. Each grain should be self-contained.
1. Pick one grain for a given set of data and don't mix grains within that set of data.

##### Examples from SPEC-1

- `fact_player_stats`: One row per player, per game, per stat type, per source
- `fact_asset_market_values`: One row per asset (player/pick), per date, per provider, per market scope
- `mart_fantasy_actuals_weekly`: One row per player, per week, per season

**Anti-pattern to avoid:** Never mix weekly and season-level stats in the same fact table without explicit grain declaration.

#### Step 3: Identify the Dimensions

Your core conformed dimensions are:

- `dim_player` (surrogate key: player_id)
- `dim_team` (NFL teams)
- `dim_franchise` (league teams, separate from NFL teams)
- `dim_date` (calendar dimension)
- `dim_asset` (players + draft picks union)
- `dim_scoring_rule` (league rules, SCD Type 2)

#### Step 4: Identify the Facts

Categorize your facts:

- **Additive:** receiving_yards, rushing_attempts, fantasy_points
- **Semi-additive:** trade_value_1qb (additive across assets, not across time)
- **Non-additive:** completion_percentage, yards_per_carry (store components separately)

______________________________________________________________________

## Key Techniques for Implementation

### Dimension Surrogate Keys

**Why this matters for SPEC-1:** Multiple data sources use different player identifiers.

**Implementation:** Create a seed table with the natural keys and their surrogates. Each player should have ONE surrogate key that maps to ALL their provider IDs via the crosswalk table.

```sql
-- dim_player_id_xref (your seed table)
CREATE TABLE dim_player_id_xref (
    player_id INTEGER PRIMARY KEY,  -- Your surrogate
    gsis_id VARCHAR,                -- nflverse
    sleeper_id VARCHAR,             -- Sleeper
    ktc_id VARCHAR,                 -- KeepTradeCut
    ffanalytics_name VARCHAR,       -- FFanalytics
    -- ... other provider IDs
);
```

**dbt implementation:** Build your crosswalk seed table, normalized as a stg\_ schema table. Then load into the desired schema.

```sql
# dbt/models/core/dim_player.sql
{{ config(
    materialized='table',
    external=true,
    partition_by=['season']  -- if applicable
) }}

SELECT
    ROW_NUMBER() OVER (ORDER BY gsis_id) AS player_id,
    gsis_id AS natural_key,
    display_name,
    position,
    team,
    -- ... other attributes
FROM {{ ref('stg_nflverse__players') }}
```

### Conformed Dimensions

**Critical for SPEC-1:** Our integration strategy depends on this.

**Implementation approach:** Define your core conformed dimensions, and build dimension tables in `dbt/models/core/`. Reference these dimensions via `{{ ref('dim_player') }}` in all marts.

1. Define dimensions once in collaboration with stakeholders; build seed tables (which staging models will reference)
1. Build dimension tables in `dbt/models/core/`
1. Reference via `{{ ref('dim_player') }}` in all marts
1. Never duplicate dimension logic

**Example - dim_player conformance:**

```sql
-- All marts reference the same dim_player
-- mart_real_world_actuals_weekly
SELECT
    f.player_id,  -- FK to dim_player
    d.display_name,
    d.position,
    f.season,
    f.week,
    f.stat_value
FROM {{ ref('fact_player_stats') }} f
JOIN {{ ref('dim_player') }} d ON f.player_id = d.player_id
```

### Grain Declaration and Enforcement

#### Define and document the grain explicitly

```sql
-- fact_player_stats structure
CREATE TABLE fact_player_stats (
    -- Grain declaration through PKs
    player_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    game_id VARCHAR,
    measure_domain VARCHAR NOT NULL,  -- 'real_world' or 'fantasy'
    stat_kind VARCHAR NOT NULL,       -- 'actual' or 'projection'
    horizon VARCHAR,                  -- 'season', 'weekly', 'rest_of_season'
    provider VARCHAR NOT NULL,        -- 'nflverse', 'ffanalytics', etc.
    stat_name VARCHAR NOT NULL,       -- 'receiving_yards', 'rush_attempts'

    -- Facts
    stat_value DECIMAL,
    sample_size INTEGER,

    -- Metadata
    asof_date DATE NOT NULL,
    src_hash VARCHAR,

    -- Test with dbt
    UNIQUE(player_id, season, week, game_id, measure_domain,
           stat_kind, provider, stat_name)
);
```

#### Test your grain-level fact table

```yaml
# models/core/fact_player_stats.yml
version: 2
models:
  - name: fact_player_stats
    columns:
      - name: player_id
        tests:
          - not_null
          - relationships:
              to: ref('dim_player')
              field: player_id

      # Grain test
      - name: grain_composite
        tests:
          - dbt_utils.unique_combination_of_columns:
              combination_of_columns:
                - player_id
                - season
                - week
                - measure_domain
                - stat_kind
                - provider
                - stat_name
```

### Transaction vs Periodic Snapshot vs Accumulating Snapshot

#### Map fact tables to types

**Transaction Fact Tables:** Create transaction fact tables for events that happen infrequently and have a clear start and end.

- `fact_waiver_transactions`: One row per waiver claim
- `fact_trades`: One row per trade event
- Sparse, event-driven

**Periodic Snapshot Fact Tables:** Create periodic snapshot fact tables for events that happen regularly and have a clear start and end.

- `mart_fantasy_actuals_weekly`: One row per player per week (even if zero points)
- `mart_roster_status_weekly`: One row per player per team per week
- Dense, regular intervals

**Accumulating Snapshot Fact Tables:** Create accumulating snapshot fact tables for events that happen regularly and have a clear start and end.

**Consider for:** Draft pick lifecycle (offered → traded → used → player drafted)

```sql
CREATE TABLE fact_draft_pick_lifecycle (
    pick_id INTEGER,
    offered_date DATE,
    traded_date DATE,
    draft_date DATE,
    player_selected_id INTEGER,
    -- Lag facts
    days_held INTEGER,
    days_to_draft INTEGER
);
```

### Slowly Changing Dimensions

**Type 0: Retain Original** Create a type 0 slowly changing dimension for attributes that never change after initial load.

- Use for: `dim_player.draft_year`, `dim_player.college`
- Never changes after initial load

**Type 1: Overwrite** Create a type 1 slowly changing dimension for attributes that change over time.

- Use for: `dim_player.current_team`, `dim_player.current_status`
- Only shows most recent value
- **Warning:** Destroys history; use sparingly

**Type 2: Add New Row** _Primary pattern for SPEC-1_ Create a type 2 slowly changing dimension for attributes that change over time and need to track history.

```sql
-- dim_scoring_rule (SCD Type 2)
CREATE TABLE dim_scoring_rule (
    scoring_rule_key INTEGER PRIMARY KEY,  -- Surrogate
    league_id VARCHAR,                     -- Natural key
    rule_name VARCHAR,
    pass_td_points DECIMAL,
    reception_points DECIMAL,
    -- SCD Type 2 columns
    effective_date DATE,
    expiration_date DATE,
    is_current BOOLEAN
);
```

_dbt snapshot for Type 2_: Create a snapshot for the slowly changing dimension.

```sql
-- snapshots/snap_scoring_rules.sql
{% snapshot snap_scoring_rules %}

{{
    config(
      target_schema='snapshots',
      unique_key='league_id',
      strategy='timestamp',
      updated_at='modified_at',
    )
}}

SELECT * FROM {{ source('sheets', 'scoring_rules') }}

{% endsnapshot %}
```

**Note:** Snapshots must run before the model that references them. Schedule appropriately in your dbt execution order.

**Type 6: Hybrid (Current + Historical)** Create a type 6 slowly changing dimension for attributes that change over time and need to track history.

- _Use for:_ Commissioner roster tracking where you need both current and as-of views

```sql
-- Roster dimension with Type 6
CREATE TABLE dim_roster (
    roster_key INTEGER PRIMARY KEY,
    franchise_id INTEGER,
    player_id INTEGER,
    contract_year INTEGER,
    contract_amount DECIMAL,
    -- Type 2 tracking
    effective_date DATE,
    expiration_date DATE,
    is_current BOOLEAN,
    -- Type 1 current values (for easy filtering)
    current_team VARCHAR,
    current_contract_amount DECIMAL
);
```

### Junk Dimensions

Create junk dimensions for attributes that are low-cardinality and don't need to track history.

**Use case in SPEC-1:** Transaction flags and indicators

```sql
-- dim_transaction_profile (junk dimension)
CREATE TABLE dim_transaction_profile (
    transaction_profile_key INTEGER PRIMARY KEY,
    is_waiver BOOLEAN,
    is_trade BOOLEAN,
    is_free_agent BOOLEAN,
    requires_approval BOOLEAN,
    is_keeper_eligible BOOLEAN
);
-- Note: Only create rows for flag combinations that actually exist
-- in your data, not the full Cartesian product

-- Fact table reference
CREATE TABLE fact_roster_transactions (
    transaction_id INTEGER,
    player_id INTEGER,
    franchise_id INTEGER,
    transaction_date DATE,
    transaction_profile_key INTEGER,  -- FK to junk
    -- Facts
    faab_bid_amount DECIMAL
);
```

### Role-Playing Dimensions

_Critical for SPEC-1:_ Multiple dates in accumulating snapshots

```sql
-- fact_asset_market_values with role-playing dates
CREATE TABLE fact_asset_market_values (
    asset_id INTEGER,
    asof_date_key INTEGER,           -- FK to dim_date (as "Valuation Date")
    market_scope VARCHAR,
    provider VARCHAR,
    trade_value DECIMAL,

    -- Create views for each role
    -- view: market_values_by_valuation_date
    -- view: market_values_by_refresh_date
);
```

_dbt implementation:_ Create views for each role.

```yaml
# dbt_project.yml - role-playing date views
models:
  ff_analytics:
    marts:
      +materialized: view
      valuation_date:
        +enabled: true
```

### Degenerate Dimensions

_Use case:_ Transaction identifiers with no other attributes

```sql
-- Sleeper transaction_id goes directly in fact table
CREATE TABLE fact_sleeper_transactions (
    transaction_id VARCHAR,  -- Degenerate dimension (no separate table)
    player_id INTEGER,
    franchise_id INTEGER,
    transaction_date_key INTEGER,
    transaction_type VARCHAR,
    -- Facts
    faab_amount DECIMAL
);
```

### Multivalued Dimensions with Bridge Tables

_Use case in SPEC-1:_ Players with multiple positions (e.g., RB/WR flex)

```sql
-- Bridge table for multi-position players
CREATE TABLE bridge_player_positions (
    player_id INTEGER,
    position VARCHAR,
    position_rank INTEGER,  -- 1 = primary, 2 = secondary
    weight_factor DECIMAL   -- For allocating metrics across positions
                            -- (e.g., if a player is 70% RB, 30% WR)
);

-- Query pattern
SELECT
    p.display_name,
    b.position,
    f.fantasy_points
FROM fact_player_stats f
JOIN bridge_player_positions b ON f.player_id = b.player_id
JOIN dim_player p ON f.player_id = p.player_id
WHERE b.position = 'RB' OR b.position = 'WR';
```

### Consolidated Fact Tables

_Use case:_ Actuals vs Projections in single table

_SPEC-1 already uses this pattern:_ Consolidate actuals and projections into a single fact table.

```sql
-- fact_player_stats consolidates actuals and projections
SELECT
    player_id,
    season,
    week,
    'actual' AS stat_kind,
    'nflverse' AS provider,
    stat_name,
    stat_value
FROM nflverse_stats

UNION ALL

SELECT
    player_id,
    season,
    week,
    'projection' AS stat_kind,
    'ffanalytics' AS provider,
    stat_name,
    stat_value
FROM ffanalytics_projections;
```

_Advantage:_ Simple comparisons without drill-across
_Disadvantage:_ Sparse rows (not all combinations exist)

______________________________________________________________________

## Architecture-Specific Patterns

### External Parquet Tables (per SPEC-1)

_Partition Strategy:_ Partition by the grain.

```yaml
# dbt_project.yml
models:
  ff_analytics:
    core:
      fact_player_stats:
        +materialized: table
        +external: true
        +partition_by: ['season', 'week']
        +location: "{{ var('external_root') }}/core/fact_player_stats"

    markets:
      fact_asset_market_values:
        +materialized: table
        +external: true
        +partition_by: ['asof_date']
```

_Compaction Strategy (from SPEC-1):_ Monthly job to coalesce small files.

- Monthly job to coalesce small files
- Target: 128-256 MB row groups per partition
- Reduces GCS request overhead

### Identity Resolution Pattern

_Specific challenge:_ Multiple provider IDs for same player

_Implementation:_ Build a crosswalk seed table with the natural keys and their surrogates. Then normalize the data to the surrogate key in the staging models.

```sql
-- Step 1: Build crosswalk (seed or staging)
-- dim_player_id_xref

-- Step 2: Staging models normalize to surrogate key
-- stg_nflverse__weekly
SELECT
    x.player_id,  -- Canonical surrogate
    w.season,
    w.week,
    w.receiving_yards,
    w.rushing_yards
FROM raw_nflverse.weekly w
LEFT JOIN {{ ref('dim_player_id_xref') }} x
    ON w.gsis_id = x.gsis_id;

-- Step 3: Guard against unmapped IDs
-- Test in dbt
tests:
  - not_null: player_id
  - accepted_values:
      field: player_id
      values: SELECT player_id FROM {{ ref('dim_player') }}
```

### Asset-Based Modeling (Players and Picks)

_SPEC-1 specific pattern:_ Create a supertype and subtype for the assets.

```sql
-- dim_asset (supertype)
CREATE TABLE dim_asset (
    asset_id INTEGER PRIMARY KEY,
    asset_type VARCHAR,  -- 'player' or 'pick'
    player_id INTEGER,   -- Populated if type = 'player'
    pick_id INTEGER,     -- Populated if type = 'pick'
    display_name VARCHAR,
    sort_order INTEGER
);

-- dim_pick (subtype)
CREATE TABLE dim_pick (
    pick_id INTEGER PRIMARY KEY,
    season INTEGER,
    round INTEGER,
    overall_number INTEGER,
    round_slot INTEGER,
    round_type VARCHAR  -- 'rookie', 'veteran', 'compensatory'
);

-- Unified market values
CREATE TABLE fact_asset_market_values (
    asset_id INTEGER,  -- FK to dim_asset
    asof_date DATE,
    market_scope VARCHAR,  -- 'dynasty_1qb', 'dynasty_sf', 'redraft'
    provider VARCHAR,
    trade_value DECIMAL,
    trade_rank INTEGER
);
```

______________________________________________________________________

## Data Quality Patterns (Kimball + SPEC-1)

### Freshness Tests

_Per SPEC-1 requirements:_ Freshness tests on the sources.

```yaml
# models/sources.yml
sources:
  - name: raw_sheets
    tables:
      - name: commissioner_roster
        freshness:
          warn_after: {count: 2, period: day}
          error_after: {count: 3, period: day}
        loaded_at_field: dt

  - name: raw_ktc
    tables:
      - name: player_values
        freshness:
          warn_after: {count: 2, period: day}
```

### Accepted Values (Grain Enforcement)

Ensure the grain is enforced in the fact table.

```yaml
# models/core/fact_player_stats.yml
models:
  - name: fact_player_stats
    columns:
      - name: measure_domain
        tests:
          - accepted_values:
              values: ['real_world', 'fantasy']

      - name: stat_kind
        tests:
          - accepted_values:
              values: ['actual', 'projection']

      - name: horizon
        tests:
          - accepted_values:
              values: ['weekly', 'season', 'rest_of_season']
              config:
                where: "stat_kind = 'projection'"
```

### Referential Integrity

Ensure the referential integrity is enforced in the fact table.

```yaml
models:
  - name: fact_player_stats
    columns:
      - name: player_id
        tests:
          - relationships:
              to: ref('dim_player')
              field: player_id

      - name: game_id
        tests:
          - relationships:
              to: ref('dim_schedule')
              field: game_id
              config:
                where: "game_id IS NOT NULL"
```

______________________________________________________________________

## Anti-Patterns to Avoid

Avoid the following anti-patterns.

### 1. Centipede Fact Tables

_Don't do this_: The problem with this is that you will have to join on the date dimension to get the date attributes.

```sql
-- BAD: Separate dimension for each hierarchy level
CREATE TABLE fact_player_stats (
    player_id INTEGER,
    date_key INTEGER,
    week_key INTEGER,      -- Don't do this
    month_key INTEGER,     -- Don't do this
    quarter_key INTEGER,   -- Don't do this
    year_key INTEGER,      -- Don't do this
    ...
);
```

_Do this instead:_ Create a single date dimension with hierarchies. This ensures that you have a single source of truth for the date attributes.

```sql
-- GOOD: Single date dimension with hierarchies
CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,
    calendar_date DATE,
    day_of_week VARCHAR,
    week_number INTEGER,
    month_number INTEGER,
    quarter_number INTEGER,
    year_number INTEGER,
    fiscal_period VARCHAR,
    nfl_week INTEGER,
    nfl_season INTEGER
);
```

### 2. Snowflaking

_Don't normalize dimensions:_ This will create a snowflake schema. The problem is it creates complex multi-table joins that confuse users and hurt query performance. Keep dimensions flat and denormalized.

```sql
-- BAD: Snowflaked player dimension
dim_player → dim_team → dim_conference → dim_division
```

_Keep dimensions denormalized:_ This ensures that you have a single source of truth for the date attributes.

```sql
-- GOOD: Flat player dimension
CREATE TABLE dim_player (
    player_id INTEGER PRIMARY KEY,
    display_name VARCHAR,
    position VARCHAR,
    team_abbreviation VARCHAR,
    team_name VARCHAR,
    team_conference VARCHAR,  -- Denormalized
    team_division VARCHAR     -- Denormalized
);
```

### 3. Fact-to-Fact Joins

_Never join facts directly on foreign keys:_ This creates unpredictable cardinality and can produce incorrect results due to many-to-many relationships.

```sql
-- BAD: Direct fact-to-fact join
SELECT
    a.player_id,
    a.actual_points,
    p.projected_points
FROM fact_actuals a
JOIN fact_projections p
    ON a.player_id = p.player_id
    AND a.week = p.week;  -- WRONG! Cardinality issues
```

_Use drill-across pattern:_ This ensures that you have a single source of truth for the date attributes.

```sql
-- GOOD: Separate queries, merged on common dimensions
WITH actuals AS (
    SELECT player_id, week, SUM(points) AS actual_points
    FROM fact_actuals GROUP BY player_id, week
),
projections AS (
    SELECT player_id, week, AVG(points) AS projected_points
    FROM fact_projections GROUP BY player_id, week
)
SELECT
    d.display_name,
    a.actual_points,
    p.projected_points
FROM dim_player d
LEFT JOIN actuals a ON d.player_id = a.player_id
LEFT JOIN projections p ON d.player_id = p.player_id AND a.week = p.week;
```

______________________________________________________________________

## Implementation Checklist

### Phase 1: Foundation

- [ ] Create surrogate key generation strategy (sequences or auto-increment)
- [ ] Build `dim_player_id_xref` seed table with all provider mappings (which staging models will reference)
- [ ] Implement calendar `dim_date` with NFL-specific attributes
- [ ] Define conformed dimension naming conventions

### Phase 2: Core Dimensions

- [ ] `dim_player` with Type 1 current attributes in the core schema
- [ ] `dim_team` (NFL teams, fairly static)
- [ ] `dim_franchise` (league teams, linked to users)
- [ ] `dim_scoring_rule` with SCD Type 2 tracking in the core schema
- [ ] `dim_asset` (players + picks union) in the core schema
- [ ] `dim_pick` with rookie draft pick details in the core schema

### Phase 3: Fact Tables

- [ ] `fact_player_stats` (long-form canonical)
- [ ] `fact_asset_market_values` (KTC + other sources)
- [ ] `fact_player_projections` (FFanalytics aggregated)
- [ ] Transaction facts (waivers, trades) if needed

### Phase 4: Marts

- [ ] `mart_real_world_actuals_weekly` (denormalized for queries) in the marts schema
- [ ] `mart_fantasy_actuals_weekly` (with scoring applied) in the marts schema
- [ ] `mart_fantasy_projections` (multiple providers weighted)
- [ ] `mart_market_metrics_daily` (trade values) in the marts schema

### Phase 5: Quality and Ops

- [ ] dbt tests on all grain declarations in the core schema
- [ ] Freshness tests per source
- [ ] `ops.run_ledger` tracking in the ops schema
- [ ] `ops.model_metrics` (row counts, durations) in the ops schema
- [ ] `ops.data_quality` (test results) in the ops schema

______________________________________________________________________

## Decision Framework

### When to use each technique

| Scenario                                    | Recommended Technique       | SPEC-1 Example                                   |
| ------------------------------------------- | --------------------------- | ------------------------------------------------ |
| Multiple source IDs for entities            | Surrogate keys + crosswalk  | `dim_player_id_xref`                             |
| Attributes change over time (track history) | SCD Type 2                  | `dim_scoring_rule`                               |
| Attributes change (don't need history)      | SCD Type 1                  | `dim_player.current_team`                        |
| Original value must never change            | SCD Type 0                  | `dim_player.draft_year`                          |
| Multiple date roles in fact                 | Role-playing dimensions     | Valuation date vs refresh date                   |
| Transaction IDs with no attributes          | Degenerate dimensions       | Sleeper `transaction_id`                         |
| Low-cardinality flags                       | Junk dimension              | Transaction type flags                           |
| Sparse fact table with many measures        | Keep atomic, document nulls | Weekly stats (not all positions score all stats) |
| Combining actuals + projections             | Consolidated fact table     | `fact_player_stats` with `stat_kind`             |
| Different grains                            | Separate fact tables        | Weekly vs season-level stats                     |
| Players with multiple positions             | Bridge table                | Position eligibility                             |
| Heterogeneous products                      | Supertype/subtype           | Players vs picks in `dim_asset`                  |

______________________________________________________________________

## References

_Kimball must-reads:_

- Start with: "Four-Step Dimensional Design Process" (p. 1-2)
- Deep dive: "Slowly Changing Dimension Techniques" (p. 12-13)
- Architecture: "Enterprise Data Warehouse Bus Architecture" (p. 10-11)

_SPEC-1 alignment:_

- Storage layout → External Parquet partitioning strategy
- Identity & Conformance → Surrogate key + crosswalk approach
- 2×2 Stat Model → Consolidated fact table with measure_domain + stat_kind
- Ops schema → Audit dimensions + error event schemas

_Next steps:_

1. Review the Enterprise Data Warehouse Bus Matrix approach (p. 11)
1. Create your own matrix with business processes as rows, dimensions as columns
1. Use matrix to sequence implementation (one row/process at a time)
1. Reference this guide during collaborative modeling workshops
