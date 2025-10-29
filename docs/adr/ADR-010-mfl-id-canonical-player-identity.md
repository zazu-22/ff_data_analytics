# ADR-010: mfl_id as Canonical Player Identity

**Status:** Superseded by ADR-011
**Date:** 2025-09-30
**Superseded Date:** 2025-10-29
**Decision Makers:** Jason Shaffer, Development Team
**Supersedes:** Implicit decision to use gsis_id as canonical player_id
**Superseded By:** ADR-011 (Sequential Surrogate Key for player_id)
**Related:** ADR-009 (Single Consolidated Fact Table), ADR-011, ADR-012

## Context

The Fantasy Football Analytics platform integrates data from multiple providers, each using different player identifiers:

| Provider     | ID Field         | Example      | Coverage               |
| ------------ | ---------------- | ------------ | ---------------------- |
| NFLverse     | `gsis_id`        | `00-0036550` | NFL players            |
| Sleeper      | `sleeper_id`     | `8136`       | Fantasy platforms      |
| KeepTradeCut | `ktc_id`         | `123`        | Dynasty trade markets  |
| ESPN         | `espn_id`        | `4360939`    | Fantasy platforms      |
| Yahoo        | `yahoo_id`       | `31854`      | Fantasy platforms      |
| FantasyPros  | `fantasypros_id` | `23456`      | Projection aggregators |
| ...          | ...              | ...          | 19 total providers     |

### Problem Statement

**Original plan:** Use `gsis_id` (NFL's Game Statistics & Information System ID) as the canonical `player_id`

**Issues discovered:**

1. `gsis_id` is an **NFL-specific identifier**, not fantasy-platform-agnostic
2. Using a provider-specific ID as canonical creates coupling (what if we drop nflverse?)
3. `load_player_stats` returns `player_id` field which is **actually gsis_id** under the hood
4. **`load_ff_playerids` exists** specifically to provide a crosswalk with a platform-neutral ID

### Constraints

- Must support identity resolution across 19+ fantasy platforms and stat providers
- Must be stable (IDs shouldn't change when players change teams/leagues)
- Must separate canonical identity from provider-specific IDs
- Must support TRANSACTIONS tab player name → ID fuzzy matching
- Must enable future provider additions without schema changes
- Must align with nflverse's own crosswalk design philosophy

## Decision

**Use nflverse's `mfl_id` as the canonical `player_id`** throughout the dimensional model.

### Identity Architecture

```text
Canonical Player ID: mfl_id (from ff_playerids)
     ↓
dim_player_id_xref (crosswalk seed)
     ↓
Provider IDs: gsis_id, sleeper_id, espn_id, yahoo_id, ktc_id, pfr_id, ...
```

### Schema

```sql
-- dim_player_id_xref (seed table)
CREATE TABLE dim_player_id_xref (
    player_id VARCHAR PRIMARY KEY,  -- mfl_id (canonical)

    -- Provider IDs (19 total from ff_playerids)
    mfl_id VARCHAR,                 -- Same as player_id (for clarity)
    gsis_id VARCHAR,                -- NFLverse/NFL.com
    sleeper_id INTEGER,             -- Sleeper
    espn_id INTEGER,                -- ESPN
    yahoo_id VARCHAR,               -- Yahoo
    pfr_id VARCHAR,                 -- Pro Football Reference
    fantasypros_id INTEGER,         -- FantasyPros
    pff_id INTEGER,                 -- Pro Football Focus
    cbs_id INTEGER,                 -- CBS Sports
    ktc_id INTEGER,                 -- KeepTradeCut
    sportradar_id VARCHAR,          -- Sportradar
    fleaflicker_id VARCHAR,         -- Fleaflicker
    rotowire_id INTEGER,            -- RotoWire
    rotoworld_id VARCHAR,           -- Rotoworld
    stats_id INTEGER,               -- Stats Inc
    stats_global_id INTEGER,        -- Stats Global
    fantasy_data_id VARCHAR,        -- FantasyData
    swish_id VARCHAR,               -- Swish Analytics
    cfbref_id VARCHAR,              -- College Football Reference
    nfl_id INTEGER,                 -- NFL.com

    -- Attributes for name-based matching
    name VARCHAR,                   -- Display name
    merge_name VARCHAR,             -- Normalized for fuzzy matching
    position VARCHAR,
    team VARCHAR,

    -- Additional context
    birthdate DATE,
    draft_year INTEGER,
    height INTEGER,
    weight INTEGER,
    college VARCHAR
);
```

## Rationale

### 1. Platform Agnosticism

**mfl_id is designed specifically as a neutral crosswalk ID:**

From nflverse documentation:

> "mfl_id is a platform-agnostic identifier created by nflverse to enable consistent player identification across fantasy platforms. It is **not** tied to any specific stat provider."

This aligns with our integration strategy:

- We integrate with multiple fantasy platforms (Sleeper, ESPN, Yahoo)
- We integrate with multiple stat sources (nflverse, FFanalytics)
- We integrate with market data (KTC)
- Using a provider-neutral ID future-proofs the architecture

### 2. Separation of Concerns

**Canonical ID vs Provider IDs:**

```sql
-- BAD: Using provider ID as canonical
CREATE TABLE fact_player_stats (
    player_id VARCHAR,  -- Actually gsis_id; couples to NFL
    ...
);

-- Query from Sleeper data:
SELECT f.*
FROM fact_player_stats f
JOIN sleeper_rosters s ON ??? -- No direct join path!
-- Must always go through crosswalk anyway
```

```sql
-- GOOD: Using neutral canonical ID
CREATE TABLE fact_player_stats (
    player_id VARCHAR,  -- mfl_id; platform-neutral
    ...
);

-- Query from ANY provider:
SELECT f.*
FROM fact_player_stats f
JOIN dim_player_id_xref x ON f.player_id = x.player_id
JOIN sleeper_rosters s ON x.sleeper_id = s.player_id;
-- Explicit, clear join path through crosswalk
```

### 3. Stability

**mfl_id stability characteristics:**

- ✅ Stable across team changes
- ✅ Stable across platform migrations
- ✅ Stable across career (college → NFL)
- ✅ Maintained by nflverse (community-driven, open source)

**vs gsis_id:**

- ⚠️ Only exists for NFL players (no college-only players)
- ⚠️ Assigned by NFL (external dependency)
- ⚠️ Semantically coupled to NFL's systems

### 4. Comprehensive Provider Coverage

**`load_ff_playerids` provides 19 provider IDs:**

```python
# From nflreadpy schema
Schema({
    'mfl_id': Int64,              # Canonical
    'gsis_id': String,            # NFLverse stats
    'sleeper_id': Int64,          # Sleeper platform
    'espn_id': Int64,             # ESPN platform
    'yahoo_id': String,           # Yahoo platform
    'fantasypros_id': Int64,      # FantasyPros projections
    'ktc_id': Int64,              # KeepTradeCut valuations
    'pfr_id': String,             # Pro Football Reference
    'pff_id': Int64,              # Pro Football Focus
    'cbs_id': Int64,              # CBS Sports
    'sportradar_id': String,      # Sportradar
    'fleaflicker_id': String,     # Fleaflicker
    'rotowire_id': Int64,         # RotoWire
    'rotoworld_id': String,       # Rotoworld
    'stats_id': Int64,            # Stats Inc
    'stats_global_id': Int64,     # Stats Global
    'fantasy_data_id': String,    # FantasyData
    'swish_id': String,           # Swish Analytics
    'cfbref_id': String,          # College Football Reference
    'nfl_id': Int64,              # NFL.com
    'name': String,
    'merge_name': String,
    'position': String,
    'team': String,
    # ... additional attributes
})
```

### 5. Name-Based Resolution Support

**For TRANSACTIONS tab parsing:**

```sql
-- Commissioner sheets use player names, not IDs
-- "Patrick Mahomes" → which player_id?

SELECT player_id
FROM dim_player_id_xref
WHERE LOWER(merge_name) = LOWER('patrick mahomes')
   OR LOWER(name) LIKE '%mahomes%'
LIMIT 1;
```

`merge_name` is pre-normalized by nflverse for fuzzy matching (removes punctuation, handles "Jr"/"III" suffixes, etc.)

## Consequences

### Positive

1. **Future-proof:** Can add new providers without changing canonical ID
2. **Explicit joins:** All staging models explicitly map provider ID → mfl_id
3. **Comprehensive coverage:** 19 provider IDs in single crosswalk
4. **Name resolution:** Built-in support for fuzzy matching via merge_name
5. **Alignment with nflverse:** Uses their recommended crosswalk pattern

### Negative

1. **Additional indirection:** All provider integrations require crosswalk join
2. **Dependency on nflverse:** mfl_id is maintained by nflverse community
3. **Existing code impact:** Must update refined_data_model_plan_v4 SQL snippets

### Migration Required

**Update all staging models:**

```sql
-- stg_nflverse__weekly.sql (BEFORE)
SELECT
    w.player_id,  -- Actually gsis_id
    w.season,
    w.week,
    ...
FROM raw.player_stats w;

-- stg_nflverse__weekly.sql (AFTER)
SELECT
    COALESCE(xref.player_id, -1) AS player_id,  -- mfl_id from crosswalk
    w.season,
    w.week,
    ...
FROM raw.player_stats w
LEFT JOIN {{ ref('dim_player_id_xref') }} xref
    ON w.player_id = xref.gsis_id;  -- Explicit: map gsis_id → mfl_id
```

**Update all fact tables:**

- `fact_player_stats.player_id` → mfl_id
- `fact_player_projections.player_id` → mfl_id
- `fact_league_transactions.player_id` → mfl_id
- `fact_asset_market_values.player_id` → mfl_id (via dim_asset)

**Update seeds:**

- `dim_player_id_xref.csv` must be generated from `ff_playerids` sample data
- Primary key: `mfl_id`
- Include all 19 provider ID columns

## Implementation

### Phase 1: Generate ff_playerids Sample Data

```bash
# Add to registry
# src/ingest/nflverse/registry.py
"ff_playerids": DatasetSpec(
    name="ff_playerids",
    py_loader="nflreadpy.load_ff_playerids",
    r_loader="nflreadr::load_ff_playerids",
    primary_keys=("mfl_id",),
    notes="Fantasy platform ID crosswalk; mfl_id is canonical player_id"
),

# Generate samples
make samples-nflverse DATASETS=ff_playerids
```

### Phase 2: Create Seed

```bash
# Generate dim_player_id_xref.csv from sample
uv run python tools/generate_seed_from_sample.py \
  --source samples/nflverse/ff_playerids \
  --output dbt/ff_analytics/seeds/dim_player_id_xref.csv \
  --primary-key mfl_id
```

### Phase 3: Update Staging Models

For each staging model that references players:

1. Add join to `dim_player_id_xref`
2. Map provider ID → mfl_id
3. Test for unmapped players (should be rare)

### Phase 4: Update Tests

```yaml
# All fact tables:
tests:
  - relationships:
      to: ref('dim_player_id_xref')
      field: player_id  # Now tests mfl_id
```

## Alternatives Considered

### Alternative 1: Use gsis_id as Canonical (Original Plan)

**Rejected because:**

- Couples architecture to NFL's ID system
- Requires separate crosswalk lookups for every fantasy platform
- `gsis_id` is a provider ID, not a canonical ID
- Doesn't align with nflverse's own crosswalk design

### Alternative 2: Generate Our Own Surrogate Keys

**Rejected because:**

- Reinvents the wheel (nflverse already solved this)
- Would need to maintain our own crosswalk mappings
- Wouldn't benefit from nflverse community updates
- More complex to integrate with nflverse data

### Alternative 3: Use sleeper_id as Canonical

**Rejected because:**

- Couples architecture to Sleeper platform
- Not all players have sleeper_id (especially historical players)
- Sleeper is a commercial platform (could shut down)
- Same coupling issues as gsis_id

## References

- [nflreadpy Documentation](https://nflreadpy.nflverse.com/api/load_functions/#load_ff_playerids)
- [NFLverse Player ID Philosophy](https://github.com/nflverse/nflverse-data/blob/master/IDENTIFIERS.md)
- [SPEC-1 v2.2](../spec/SPEC-1_v_2.2.md) (Identity Resolution Requirements)
- [Kimball Dimensional Modeling Guidance](../../architecture/kimball_modeling_guidance/kimbal_modeling.md) (Surrogate Keys section)
- [ADR-009](./ADR-009-single-consolidated-fact-table-nfl-stats.md) (Fact Table Architecture)

## Revision History

- **2025-09-30:** Initial decision (v1.0)
