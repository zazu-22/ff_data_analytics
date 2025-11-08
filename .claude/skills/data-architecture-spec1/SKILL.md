---
name: data-architecture-spec1
description: Design and validate data pipelines following SPEC-1 patterns including batch ingestion, Kimball dimensional modeling, 2×2 stat model, identity resolution, and data quality frameworks. Use for schema design, pipeline architecture, new data source integration, SPEC-1 compliance validation, or architectural decision questions.
---

# SPEC-1 Data Architecture for FF Analytics

## When to Use This Skill

**Invoke this skill proactively when users request:**

- "How should I integrate a new data source (KTC, FFanalytics, etc.)?"
- "What's the correct grain for weekly/game-level player stats?"
- "Should fantasy scoring go in facts or marts?"
- "Help me implement batch ingestion following SPEC-1 patterns"
- "How do I handle players that don't map to the crosswalk?"
- "Validate my staging model follows SPEC-1 compliance"
- "What's the architecture decision for [X]?" (check ADR_INDEX.md)
- "How do I set up identity resolution for a new provider?"

**Use for these tasks:**

- **Designing new data source integrations** (nflverse, KTC, FFanalytics, commissioner sheets)
- **Implementing batch processing workflows** (twice-daily ingestion patterns)
- **Creating or modifying dbt models** (staging, facts, dimensions, marts)
- **Validating SPEC-1 compliance** (schema patterns, grain definitions, test coverage)
- **Resolving architectural questions** (check ADR_INDEX.md for decisions)
- **Ensuring 2×2 model compliance** (real-world vs fantasy, actuals vs projections)
- **Implementing identity resolution** (player, team, franchise ID mapping)
- **Setting up data quality checks** (grain, FK, enums, freshness)

## Quick Reference: Core Architectural Patterns

### 1. Batch Ingestion Pattern (ADR-001, ADR-002, ADR-003)

**Storage Layout:**

```
data/raw/<provider>/<dataset>/dt=YYYY-MM-DD/
├── *.parquet              # Columnar format (PyArrow)
└── _meta.json            # Lineage metadata (required)
```

**Cloud equivalent:**

```
gs://ff-analytics/raw/<provider>/<dataset>/dt=YYYY-MM-DD/
```

**Metadata requirements (_meta.json):**

```json
{
  "loader_path": "src.ingest.nflverse.shim.load_nflverse",
  "source_version": "nflreadr==1.5.0",
  "asof_datetime": "2025-10-24T08:00:00Z",
  "row_count": 12133,
  "schema_hash": "sha256:abc123...",
  "dataset_name": "players",
  "partition_date": "2025-10-24"
}
```

**Schedule:** Twice-daily at 08:00 and 16:00 UTC (ADR-002)

**Validation:**

```bash
# Check metadata presence and format
uv run .claude/skills/data-architecture-spec1/scripts/check_lineage.py \
  --path data/raw/nflverse/players/dt=2025-10-24

# Validate schema hash consistency
uv run .claude/skills/data-architecture-spec1/scripts/validate_schema.py \
  --path data/raw/nflverse/players \
  --check metadata
```

### 2. Identity Resolution (ADR-010)

**Canonical Player ID:** `mfl_id` (from nflverse ff_playerids dataset)

**Provider ID Crosswalk:**
All staging models with player references MUST map to canonical `player_id` via `dim_player_id_xref`:

```sql
-- Standard crosswalk pattern for staging models
left join {{ ref('dim_player_id_xref') }} xref
  on source.gsis_id = xref.gsis_id  -- or sleeper_id, espn_id, yahoo_id, etc.

select
  coalesce(xref.player_id, source.gsis_id) as player_key,
  xref.player_id,
  source.gsis_id as raw_provider_id,
  -- ... other columns
```

**19 Provider IDs Supported:**

- `mfl_id` (canonical)
- `gsis_id`, `sleeper_id`, `espn_id`, `yahoo_id`, `pfr_id`
- `fantasypros_id`, `pff_id`, `cbs_id`, `ktc_id`
- `sportradar_id`, `fleaflicker_id`, `rotowire_id`, `rotoworld_id`
- `stats_id`, `stats_global_id`, `fantasy_data_id`
- `swish_id`, `cfbref_id`, `nfl_id`

**player_key Pattern (for unmapped players):**
Use when some players don't map to canonical ID:

```sql
coalesce(xref.player_id, source.<raw_provider_id>) as player_key
```

This prevents grain violations while preserving unmapped player data.

**Coverage Documentation:**
Document mapping coverage in staging model headers:

```sql
-- stg_nflverse__player_stats.sql
-- Maps gsis_id → mfl_id via dim_player_id_xref
-- NULL filtering: 0.12% of records (unidentifiable players)
-- Mapping coverage: 99.9% (12,089 / 12,133 mapped)
```

### 3. 2×2 Stat Model (ADR-007)

**Separate fact tables for actuals vs projections:**

```
                 Real-World Stats              Fantasy Points
                 ────────────────              ──────────────
Actuals          fact_player_stats        →    mart_fantasy_actuals_weekly
                 (per-game grain)              (apply dim_scoring_rule)

Projections      fact_player_projections  →    mart_fantasy_projections
                 (weekly/season grain)         (apply dim_scoring_rule)
```

**Why separate facts?**

- Actuals have per-game grain (game_id required, NOT NULL)
- Projections have weekly/season grain (game_id meaningless, would be NULL)
- Unified table would require nullable keys (anti-pattern)
- Separate tables eliminate conditional logic and improve clarity

See ADR_INDEX.md → ADR-007 for full rationale.

**Fantasy Scoring Pattern:**
Fantasy scoring applied ONLY in mart layer (never in facts):

```sql
-- mart_fantasy_actuals_weekly.sql
select
  stats.player_id,
  stats.season,
  stats.week,
  sum(stats.stat_value * rules.points_per_unit) as fantasy_points
from {{ ref('fact_player_stats') }} stats
join {{ ref('dim_scoring_rule') }} rules
  on stats.stat_name = rules.stat_name
  and stats.season between rules.valid_from_season and rules.valid_to_season
where stats.measure_domain = 'real_world'
  and stats.stat_kind = 'actual'
group by 1, 2, 3
```

**Measure Domain:**

- `measure_domain='real_world'` in ALL fact tables
- `measure_domain='fantasy'` ONLY in mart tables (after scoring applied)

### 4. Grain Definition & Testing

**Every fact/dimension requires explicit grain:**

```yaml
# dbt/ff_data_transform/tests/singular/fact_player_stats_grain.yml
tests:
  - name: fact_player_stats_grain_uniqueness
    description: "Validates grain: player_key + game_id + stat_name + provider + measure_domain + stat_kind"
    columns:
      - player_key
      - game_id
      - stat_name
      - provider
      - measure_domain
      - stat_kind
```

**Grain Analysis Helper (generates SQL for manual validation):**

```bash
uv run .claude/skills/data-architecture-spec1/scripts/analyze_grain.py \
  --model fact_player_stats \
  --expected-grain "player_key,game_id,stat_name,provider,measure_domain,stat_kind"
```

This script generates SQL to check for duplicate grain keys. Run the generated SQL manually or create a dbt singular test for automated validation (recommended approach).

### 5. Data Quality Framework

**Required tests for all staging models:**

1. **Grain uniqueness** (composite key test)
2. **FK integrity** (player_id, team_id, franchise_id)
3. **Enum validation** (controlled vocabularies)
4. **Not-null** on grain columns
5. **Mapping coverage** documentation (for ID crosswalks)

**Required tests for all fact tables:**

1. **Grain uniqueness** (see section 4)
2. **FK integrity** to dimensions
3. **Enum validation** (season, season_type, measure_domain, stat_kind, provider)
4. **Not-null** on all grain columns
5. **Range checks** (season 2020-2025, week 1-18)

**Standard test template for staging models:**

```yaml
# dbt/ff_data_transform/models/staging/<provider>/schema.yml
models:
  - name: stg_<provider>__<dataset>
    columns:
      # Grain uniqueness test (composite key)
      - name: grain_key
        tests:
          - unique
        # Create grain_key column: concat(col1, '-', col2, '-', col3)

      # FK integrity tests
      - name: player_id
        tests:
          - relationships:
              to: ref('dim_player_id_xref')
              field: player_id

      # Enum validation tests
      - name: season_type
        tests:
          - accepted_values:
              values: ['REG', 'POST', 'PRE']

      # Not-null tests on grain columns
      - name: season
        tests:
          - not_null
      - name: week
        tests:
          - not_null
```

For complex grain tests, create a singular test in `dbt/ff_data_transform/tests/singular/`.

### 6. Kimball Dimensional Modeling

**Fact Table Pattern:**

```sql
-- fact_player_stats.sql
select
  -- Grain columns (NOT NULL)
  player_key,
  game_id,
  stat_name,
  provider,
  measure_domain,
  stat_kind,

  -- Dimensions (foreign keys)
  player_id,
  team_id,

  -- Degenerate dimensions
  season,
  week,
  season_type,

  -- Measures
  stat_value,

  -- Metadata
  loaded_at
from {{ ref('stg_nflverse__player_stats') }}
```

**Dimension Table Pattern (SCD Type 2):**

```sql
-- dim_scoring_rule.sql (slowly changing dimension)
select
  rule_id,
  stat_name,
  points_per_unit,
  valid_from_season,
  valid_to_season,
  is_current,
  effective_date,
  expiration_date
from {{ ref('seed_scoring_rules') }}
```

See `reference/kimball_modeling.md` for comprehensive guidance.

## Integration Checklist for New Data Sources

When adding a new data source (KTC, FFanalytics, etc.), follow this sequence:

- [ ] **Define registry entry** in `src/ingest/<provider>/registry.py`
  - Dataset name, loader function, primary key, partition columns
- [ ] **Implement loader** following batch ingestion pattern
  - Write Parquet to `data/raw/<provider>/<dataset>/dt=YYYY-MM-DD/`
  - Generate `_meta.json` with lineage metadata
- [ ] **Create sample fixtures** via `tools/make_samples.py`
  - Small representative dataset for testing
  - Commit to `samples/<provider>/` directory
- [ ] **Map player IDs** (if applicable)
  - Crosswalk via `dim_player_id_xref` using appropriate provider ID column
  - Document mapping coverage percentage
- [ ] **Create staging model** in `dbt/ff_data_transform/models/staging/<provider>/`
  - Follow naming: `stg_<provider>__<dataset>.sql`
  - Map to canonical IDs, normalize to long-form
  - Document NULL filtering and mapping coverage in header
- [ ] **Generate dbt tests**
  - Grain uniqueness, FK integrity, enums, not-null
  - Use standard test template (see section 5 above)
- [ ] **Integrate into fact/mart tables**
  - UNION into existing facts (if same grain) or create new fact table
  - Apply 2×2 model (real-world in facts, fantasy scoring in marts)
- [ ] **Validate schema compliance**
  - Run validation scripts
  - Verify metadata lineage
  - Check test coverage (100% on grain, FK, enums)
- [ ] **Update SPEC checklist**
  - Mark tasks complete in [`reference/SPEC-1_v_2.3_implementation_checklist_v_0.md`](reference/SPEC-1_v_2.3_implementation_checklist_v_0.md)

See [VALIDATION.md](VALIDATION.md) for complete compliance checklist with acceptance criteria.

## Common Architectural Questions

### Q: Should I create a new fact table or UNION into existing fact?

**Decision tree:**

1. **Same grain?** If yes → UNION into existing fact (e.g., snap counts → fact_player_stats)
2. **Different grain?** If yes → Create separate fact table (e.g., projections have weekly grain vs actuals have game grain)
3. **Same measure domain?** Ensure both are `measure_domain='real_world'` before UNION

See [ADR_INDEX.md](ADR_INDEX.md) → ADR-007 for actuals vs projections decision.

### Q: Where should fantasy scoring be calculated?

**Always in marts, never in facts.**

Facts store `measure_domain='real_world'` only. Apply `dim_scoring_rule` in mart layer to derive fantasy points.

Rationale: Scoring rules change over time (SCD Type 2). Storing real-world stats in facts allows rescoring without re-ingesting.

### Q: How do I handle unmapped players?

**Use player_key pattern:**

```sql
coalesce(xref.player_id, source.raw_provider_id) as player_key
```

This allows unmapped players to have stats without violating grain uniqueness. Document mapping coverage in model header.

### Q: What grain should I use for weekly aggregations?

**Standard weekly grain:**

```
(player_id, season, week, stat_name, measure_domain, stat_kind)
```

Exclude `game_id` (players can play multiple games per week in rare cases). Use `season + week` as temporal key.

### Q: How do I handle SCD Type 2 dimensions?

**Use validity dates and is_current flag:**

```sql
-- dim_scoring_rule example
join {{ ref('dim_scoring_rule') }} rules
  on stats.stat_name = rules.stat_name
  and stats.season between rules.valid_from_season and rules.valid_to_season
  and rules.is_current = true  -- for most recent rules
```

See `reference/kimball_modeling.md` → "Slowly Changing Dimensions" for patterns.

## Provider-Specific Patterns

### nflverse

- **Canonical ID:** `gsis_id` → `mfl_id`
- **Datasets:** players, weekly, season, injuries, depth_charts, schedule, teams, snap_counts, ff_opportunity
- **Grain:** Per-game for stats, per-week for injuries/depth
- **Quirks:** team codes differ from other providers, requires crosswalk

### Sleeper

- **Canonical ID:** `sleeper_id` → `mfl_id`
- **Datasets:** league, users, rosters, players
- **Grain:** Per-roster snapshot
- **Quirks:** Native sleeper_id, minimal crosswalk needed

### Commissioner Sheets (ADR-005)

- **Canonical ID:** Player display names → `mfl_id` (via fuzzy matching + aliases)
- **Datasets:** Roster tabs (12 GMs), TRANSACTIONS tab
- **Grain:** Per-player per-GM for rosters, per-asset per-transaction for TRANSACTIONS
- **Quirks:** Requires extensive name alias table, manual validation

### KTC (Keep Trade Cut)

- **Canonical ID:** Player names → `mfl_id` (via fuzzy matching)
- **Datasets:** players, picks (dynasty 1QB default)
- **Grain:** Per-asset per-asof-date
- **Quirks:** Dynasty-only, includes rookies pre-draft, requires polite rate limiting

### FFanalytics

- **Canonical ID:** Player names → `mfl_id` (via fuzzy matching)
- **Datasets:** projections (season, weekly, rest-of-season)
- **Grain:** Per-player per-stat per-horizon per-asof-date
- **Quirks:** Multi-source aggregation, requires weighted consensus calculation

See `reference/data_sources/` for detailed source decision docs.

## File References

All reference files are symlinked to authoritative project documentation:

- **Complete specification:** [`reference/SPEC-1_v_2.2.md`](reference/SPEC-1_v_2.2.md)
- **Implementation checklist:** [`reference/SPEC-1_v_2.3_implementation_checklist_v_0.md`](reference/SPEC-1_v_2.3_implementation_checklist_v_0.md)
- **Technical specifications:** [`reference/refined_data_model_plan_v4.md`](reference/refined_data_model_plan_v4.md)
- **Architecture decisions:** [`ADR_INDEX.md`](ADR_INDEX.md) (all ADRs cataloged)
- **Validation checklists:** [`VALIDATION.md`](VALIDATION.md) (step-by-step compliance)
- **Kimball modeling guide:** [`reference/kimball_modeling.md`](reference/kimball_modeling.md)
- **Data source patterns:** [`reference/data_sources/`](reference/data_sources/)

## Validation Scripts

All scripts in `.claude/skills/data-architecture-spec1/scripts/`:

```bash
# Check metadata lineage (validates _meta.json format)
uv run .claude/skills/data-architecture-spec1/scripts/check_lineage.py \
  --path data/raw/<provider>/<dataset>/dt=YYYY-MM-DD

# Validate schema compliance (metadata, consistency, ID mapping)
uv run .claude/skills/data-architecture-spec1/scripts/validate_schema.py \
  --path data/raw/<provider>/<dataset> \
  --check <metadata|schema_consistency|player_id_mapping>

# Generate grain validation SQL (manual execution required)
uv run .claude/skills/data-architecture-spec1/scripts/analyze_grain.py \
  --model <model_name> \
  --expected-grain "col1,col2,..."
```

See [VALIDATION.md](VALIDATION.md) for complete usage and acceptance criteria.

## Common Pitfalls to Avoid

1. ❌ **Fantasy scoring in fact tables** → Violates 2×2 model; scoring must be in marts
2. ❌ **Nullable keys in grain** → Use player_key pattern for unmapped players
3. ❌ **Missing mapping coverage docs** → Always document % mapped in staging header
4. ❌ **Inconsistent measure_domain** → Facts must be 'real_world', marts can be 'fantasy'
5. ❌ **Mixed actuals/projections grain** → Requires separate fact tables per ADR-007
6. ❌ **Missing metadata (_meta.json)** → Required for lineage and data quality tracking
7. ❌ **Uppercase SQL** → Violates style guide (lowercase keywords, functions, identifiers)

## Implementation Status

**Current status tracked in:** [`reference/SPEC-1_v_2.3_implementation_checklist_v_0.md`](reference/SPEC-1_v_2.3_implementation_checklist_v_0.md)

Refer to the implementation checklist for:

- Real-time status updates by phase and track
- Detailed task completion tracking
- Test coverage metrics
- Next priority recommendations

The checklist is the authoritative source for implementation status and is updated regularly as work progresses.
