# SPEC-1 Validation and Compliance Checklists

Step-by-step validation checklists for ensuring SPEC-1 v2.2 compliance. Use these checklists when implementing new data sources, creating models, or reviewing existing implementations.

## Table of Contents

1. [New Data Source Integration Checklist](#new-data-source-integration-checklist)
2. [Staging Model Validation](#staging-model-validation)
3. [Fact Table Validation](#fact-table-validation)
4. [Dimension Table Validation](#dimension-table-validation)
5. [Mart Validation (2×2 Model)](#mart-validation-22-model)
6. [Identity Resolution Validation](#identity-resolution-validation)
7. [Batch Ingestion Validation](#batch-ingestion-validation)
8. [Test Coverage Validation](#test-coverage-validation)

---

## New Data Source Integration Checklist

Use this checklist when adding a new data provider (KTC, FFanalytics, etc.).

### Phase 1: Registry and Loader

- [ ] **Define dataset in registry**
  - Location: `src/ingest/<provider>/registry.py`
  - Fields: `name`, `py_loader`, `r_loader` (if applicable), `primary_keys`, `partition_cols`, `notes`
  - Example:

    ```python
    "dataset_name": DatasetSpec(
        name="dataset_name",
        py_loader="provider.load_function",
        primary_keys=("id_col",),
        partition_cols=("season", "week"),
        notes="Brief description"
    )
    ```

- [ ] **Implement loader function**
  - Location: `src/ingest/<provider>/shim.py` or dedicated module
  - Returns: Dictionary with `data` (Polars DataFrame) and `metadata`
  - Handles errors gracefully with retries
  - Respects rate limits (for external APIs)

- [ ] **Validate loader output**

  ```bash
  # Test loader locally
  python -c "from src.ingest.<provider>.shim import load_<dataset>; result = load_<dataset>(out_dir='data/raw/<provider>')"

  # Check output structure
  ls -la data/raw/<provider>/<dataset>/dt=*/
  # Should see: *.parquet and _meta.json
  ```

### Phase 2: Metadata and Lineage

- [ ] **Verify _meta.json format**

  ```bash
  uv run .claude/skills/data-architecture-spec1/scripts/check_lineage.py \
    --path data/raw/<provider>/<dataset>/dt=YYYY-MM-DD
  ```

  Required fields:
  - `loader_path`: Full Python path to loader function
  - `source_version`: Package version (e.g., "nflreadr==1.5.0")
  - `asof_datetime`: UTC timestamp of ingestion
  - `row_count`: Number of rows in dataset
  - `schema_hash`: Hash of Parquet schema
  - `dataset_name`: Name of dataset
  - `partition_date`: Date of partition (YYYY-MM-DD)

- [ ] **Validate Parquet schema**

  ```bash
  uv run .claude/skills/data-architecture-spec1/scripts/validate_schema.py \
    --path data/raw/<provider>/<dataset> \
    --check schema_consistency
  ```

  Acceptance:
  - All partitions have identical schema
  - Schema hash matches across partitions
  - Column names follow conventions (lowercase, snake_case)

### Phase 3: Sample Fixtures

- [ ] **Generate sample data**

  ```bash
  uv run tools/make_samples.py <provider> \
    --datasets <dataset> \
    --out ./samples \
    [provider-specific options]
  ```

- [ ] **Validate sample size**
  - Small enough to commit (<1MB per dataset)
  - Representative of real data structure
  - Covers edge cases (nulls, outliers, boundary values)

- [ ] **Commit samples to repository**

  ```bash
  git add samples/<provider>/<dataset>/
  git commit -m "feat: add <provider> <dataset> sample fixtures"
  ```

### Phase 4: Identity Resolution (if applicable)

- [ ] **Identify provider ID field**
  - Examples: `gsis_id`, `sleeper_id`, `player_name`, etc.

- [ ] **Verify crosswalk coverage**

  ```bash
  # Test mapping via dim_player_id_xref
  uv run .claude/skills/data-architecture-spec1/scripts/validate_schema.py \
    --path data/raw/<provider>/<dataset> \
    --check player_id_mapping \
    --id-field <provider_id_field>
  ```

  Acceptance criteria:
  - **≥95% mapping coverage** for statistical sources (nflverse, FFanalytics)
  - **≥90% mapping coverage** for market sources (KTC)
  - **≥85% mapping coverage** for commissioner sources (sheets with fuzzy matching)
  - Document coverage % in staging model header
  - Identify unmapped players for alias table updates

- [ ] **Identify unmapped players (if coverage < 98%)**

  Use SQL to find players without mapping:

  ```sql
  -- Query unmapped players
  select distinct
    source.<name_field> as player_name,
    source.<provider_id_field> as provider_id
  from read_parquet('data/raw/<provider>/<dataset>/dt=*/*.parquet') source
  left join read_csv('dbt/ff_data_transform/seeds/dim_player_id_xref.csv') xref
    on source.<provider_id_field> = xref.<provider_id_field>
  where xref.player_id is null
  order by player_name;
  ```

  Manually review unmapped players and add aliases to `dim_name_alias.csv` seed if valid matches exist.

### Phase 5: Staging Model

- [ ] **Create staging model**
  - Location: `dbt/ff_data_transform/models/staging/<provider>/stg_<provider>__<dataset>.sql`
  - Naming: `stg_<provider>__<dataset>.sql`
  - Header template:

    ```sql
    -- stg_<provider>__<dataset>.sql
    -- Maps <provider_id> → mfl_id via dim_player_id_xref
    -- NULL filtering: X.XX% of records (reason)
    -- Mapping coverage: XX.X% (N mapped / M total)
    ```

- [ ] **Implement ID crosswalk (if player data)**

  ```sql
  left join {{ ref('dim_player_id_xref') }} xref
    on source.<provider_id> = xref.<provider_id>

  select
    coalesce(xref.player_id, source.<provider_id>) as player_key,
    xref.player_id,
    source.<provider_id> as raw_provider_id,
    -- ... other columns
  ```

- [ ] **Normalize to long-form (if wide format)**
  - Use `UNPIVOT` or UNION ALL to convert wide stats to long
  - Ensure grain uniqueness after unpivoting

- [ ] **Add schema.yml**
  - Location: `dbt/ff_data_transform/models/staging/<provider>/schema.yml`
  - Document: description, columns, grain

### Phase 6: Tests

- [ ] **Create test suite using standard template**

  Add to `dbt/ff_data_transform/models/staging/<provider>/schema.yml`:

  ```yaml
  models:
    - name: stg_<provider>__<dataset>
      columns:
        # Grain uniqueness (composite key)
        - name: player_id
          tests:
            - not_null
        - name: season
          tests:
            - not_null

        # FK integrity
        - name: player_id
          tests:
            - relationships:
                to: ref('dim_player_id_xref')
                field: player_id

        # Enum validation
        - name: season_type
          tests:
            - accepted_values:
                values: ['REG', 'POST', 'PRE']
  ```

  For complex grain tests, create singular test in `tests/singular/`.

- [ ] **Required tests (100% coverage)**
  - Grain uniqueness (composite key)
  - FK integrity (player_id, team_id, franchise_id)
  - Enum validation (controlled vocabularies)
  - Not-null on grain columns

- [ ] **Run tests**

  ```bash
  dbt test --select stg_<provider>__<dataset>
  ```

  Acceptance: All tests pass (0 failures)

### Phase 7: Fact/Mart Integration

- [ ] **Integrate into fact table**
  - Same grain? → UNION into existing fact
  - Different grain? → Create new fact table (see ADR-007)

- [ ] **Validate 2×2 model compliance**
  - Facts: `measure_domain='real_world'` only
  - Marts: Apply fantasy scoring via `dim_scoring_rule`

- [ ] **Update marts (if new fact)**
  - Create `mart_real_world_*` (no scoring)
  - Create `mart_fantasy_*` (with scoring)

### Phase 8: Documentation

- [ ] **Update implementation checklist**
  - File: `docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md`
  - Mark tasks complete
  - Update status percentages

- [ ] **Document source decisions (if new provider)**
  - File: `docs/architecture/data_sources/<provider>_source_decisions.md`
  - Cover: API/source selection, rate limits, ToS compliance, update cadence

---

## Staging Model Validation

Use this checklist to validate an existing or new staging model.

### Schema Validation

- [ ] **Naming convention**
  - Pattern: `stg_<provider>__<dataset>.sql`
  - Location: `dbt/ff_data_transform/models/staging/<provider>/`

- [ ] **Header documentation**

  ```sql
  -- Required in header comment:
  -- 1. ID crosswalk description (if applicable)
  -- 2. NULL filtering percentage and reason
  -- 3. Mapping coverage percentage (if ID crosswalk)
  ```

- [ ] **Source reference**

  ```sql
  -- Must use dbt source() macro:
  select * from {{ source('<provider>', '<dataset>') }}
  -- NOT: select * from raw.<provider>.<dataset>
  ```

### ID Crosswalk Validation (if applicable)

- [ ] **Crosswalk join pattern**

  ```sql
  left join {{ ref('dim_player_id_xref') }} xref
    on source.<provider_id> = xref.<provider_id>
  ```

- [ ] **player_key pattern (for grain uniqueness)**

  ```sql
  coalesce(xref.player_id, source.<provider_id>) as player_key
  ```

- [ ] **Mapping coverage documented**
  - Calculate: `count(distinct xref.player_id) / count(distinct source.<provider_id>)`
  - Document in header comment
  - Target: ≥95% for stat sources, ≥90% for market sources

### Normalization Validation

- [ ] **Long-form conversion (if applicable)**
  - Wide stats → unpivot to long form
  - Grain: one row per entity per stat per timeframe

- [ ] **Lowercase SQL**
  - All keywords lowercase: `select`, `from`, `where`, `join`
  - All function names lowercase: `coalesce`, `sum`, `count`
  - All identifiers lowercase: table names, column names

- [ ] **Preserve raw column names (staging)**
  - Don't rename in staging (defer to marts)
  - Exception: Canonical ID columns (`player_id`, `player_key`)

### Test Coverage

- [ ] **schema.yml exists**
  - Location: `dbt/ff_data_transform/models/staging/<provider>/schema.yml`

- [ ] **Grain uniqueness test**

  ```yaml
  - name: stg_<provider>__<dataset>
    tests:
      - unique:
          column_name: "concat(col1, '-', col2, '-', col3)"  # Composite key
  ```

- [ ] **FK integrity tests**

  ```yaml
  - name: player_id
    tests:
      - relationships:
          to: ref('dim_player_id_xref')
          field: player_id
  ```

- [ ] **Enum validation tests**

  ```yaml
  - name: season_type
    tests:
      - accepted_values:
          values: ['REG', 'POST', 'PRE', 'WC', 'DIV', 'CON', 'SB']
  ```

- [ ] **Not-null tests on grain columns**

  ```yaml
  - name: season
    tests:
      - not_null
  ```

---

## Fact Table Validation

Use this checklist to validate fact table implementations.

### Grain Definition

- [ ] **Explicit grain documented**

  ```sql
  -- fact_player_stats.sql
  -- Grain: one row per (player_key, game_id, stat_name, provider, measure_domain, stat_kind)
  ```

- [ ] **Grain uniqueness test**

  ```bash
  uv run .claude/skills/data-architecture-spec1/scripts/analyze_grain.py \
    --model fact_<name> \
    --expected-grain "col1,col2,col3,..."
  ```

  Acceptance: 0 duplicate rows on expected grain

### 2×2 Model Compliance

- [ ] **measure_domain validation**

  ```sql
  -- All facts must have:
  where measure_domain = 'real_world'
  -- Fantasy scoring in marts only!
  ```

- [ ] **stat_kind validation**

  ```sql
  -- Actuals:
  where stat_kind = 'actual'

  -- Projections:
  where stat_kind = 'projection'
  ```

- [ ] **Separate fact tables for actuals vs projections**
  - Actuals: `fact_player_stats` (per-game grain, has `game_id`)
  - Projections: `fact_player_projections` (weekly/season grain, has `horizon`, NO `game_id`)
  - See ADR-007 for rationale

### Schema Validation

- [ ] **Required grain columns (NOT NULL)**
  - All columns in grain definition
  - No nullable keys

- [ ] **Foreign keys**
  - `player_id` → `dim_player_id_xref.player_id`
  - `team_id` → `dim_team.team_id` (if applicable)
  - `franchise_id` → `dim_franchise.franchise_id` (if applicable)

- [ ] **Enum fields**
  - `measure_domain` ∈ {'real_world'}
  - `stat_kind` ∈ {'actual', 'projection'}
  - `provider` ∈ documented provider list
  - `season_type` ∈ {'REG', 'POST', 'PRE', 'WC', 'DIV', 'CON', 'SB'}

### Test Coverage

- [ ] **Grain uniqueness test (singular)**
  - File: `dbt/ff_data_transform/tests/singular/fact_<name>_grain.sql`
  - Validates composite key uniqueness

- [ ] **FK integrity tests**

  ```yaml
  tests:
    - relationships:
        to: ref('dim_player_id_xref')
        field: player_id
  ```

- [ ] **Enum validation tests**

  ```yaml
  tests:
    - accepted_values:
        column_name: measure_domain
        values: ['real_world']
  ```

- [ ] **Not-null tests on all grain columns**

- [ ] **Range checks**

  ```yaml
  - name: season
    tests:
      - accepted_values:
          values: [2020, 2021, 2022, 2023, 2024, 2025]

  - name: week
    tests:
      - dbt_utils.expression_is_true:
          expression: "week BETWEEN 1 AND 18"
  ```

### Performance

- [ ] **Partitioning configured**

  ```yaml
  # dbt_project.yml
  models:
    ff_analytics:
      core:
        fact_player_stats:
          +partition_by: ["season", "week"]
  ```

- [ ] **Row count validation**

  ```bash
  # Expected scale documented
  # fact_player_stats: ~12-15M rows (5 years historical + current)
  # Current: 6.3M rows (6 seasons: 2020-2025)
  ```

---

## Dimension Table Validation

Use this checklist for SCD Type 1 and Type 2 dimension tables.

### SCD Type 1 (Simple Dimensions)

- [ ] **Primary key**
  - Single column surrogate key
  - NOT NULL, UNIQUE

- [ ] **Attributes**
  - Descriptive fields
  - No measures (measures go in facts)

- [ ] **Example: dim_team**

  ```sql
  create table dim_team (
    team_id varchar primary key,
    team_name varchar not null,
    team_abbr varchar not null,
    conference varchar,
    division varchar
  );
  ```

### SCD Type 2 (Slowly Changing Dimensions)

- [ ] **Required columns**
  - Surrogate key: `<entity>_key` or `<entity>_id`
  - Natural key: `<entity>_code` or source ID
  - `valid_from_season` / `valid_from_date`
  - `valid_to_season` / `valid_to_date`
  - `is_current` (boolean)

- [ ] **Temporal join pattern**

  ```sql
  join {{ ref('dim_scoring_rule') }} rules
    on facts.stat_name = rules.stat_name
    and facts.season between rules.valid_from_season and rules.valid_to_season
  ```

- [ ] **Example: dim_scoring_rule**

  ```sql
  create table dim_scoring_rule (
    rule_id varchar primary key,
    stat_name varchar not null,
    points_per_unit numeric not null,
    valid_from_season integer not null,
    valid_to_season integer not null,
    is_current boolean not null
  );
  ```

### Test Coverage

- [ ] **Primary key tests**

  ```yaml
  - name: <entity>_id
    tests:
      - unique
      - not_null
  ```

- [ ] **SCD Type 2 specific tests**

  ```yaml
  - name: is_current
    tests:
      - not_null

  # Ensure only one current version per natural key
  - name: singular_test_one_current_per_natural_key
  ```

---

## Mart Validation (2×2 Model)

Use this checklist for mart tables (real-world and fantasy).

### Real-World Marts

- [ ] **measure_domain**

  ```sql
  -- Real-world marts:
  where measure_domain = 'real_world'
  ```

- [ ] **No fantasy scoring**
  - Real-world stats only
  - No `dim_scoring_rule` joins

- [ ] **Examples**
  - `mart_real_world_actuals_weekly`
  - `mart_real_world_projections`

### Fantasy Marts

- [ ] **Scoring rule application**

  ```sql
  join {{ ref('dim_scoring_rule') }} rules
    on stats.stat_name = rules.stat_name
    and stats.season between rules.valid_from_season and rules.valid_to_season
  ```

- [ ] **Fantasy points calculation**

  ```sql
  sum(stats.stat_value * rules.points_per_unit) as fantasy_points
  ```

- [ ] **measure_domain**

  ```sql
  -- Source facts must be real_world:
  where stats.measure_domain = 'real_world'

  -- Output mart is fantasy:
  -- (no explicit measure_domain column, but implied by presence of fantasy_points)
  ```

- [ ] **Examples**
  - `mart_fantasy_actuals_weekly`
  - `mart_fantasy_projections`

### 2×2 Model Alignment

```
                 Real-World Stats              Fantasy Points
                 ────────────────              ──────────────
Actuals          fact_player_stats        →    mart_fantasy_actuals_weekly
                 ↓
                 mart_real_world_actuals

Projections      fact_player_projections  →    mart_fantasy_projections
                 ↓
                 mart_real_world_projections
```

- [ ] **Fact layer**: Real-world only
- [ ] **Mart layer**: Both real-world and fantasy
- [ ] **Scoring**: Applied in mart layer via `dim_scoring_rule`

---

## Identity Resolution Validation

Use this checklist to validate player ID mapping.

### Crosswalk Coverage

- [ ] **Calculate coverage**

  ```bash
  uv run .claude/skills/data-architecture-spec1/scripts/validate_schema.py \
    --model stg_<provider>__<dataset> \
    --check player_id_mapping
  ```

- [ ] **Target thresholds**
  - **Stat sources (nflverse, FFanalytics):** ≥95%
  - **Market sources (KTC):** ≥90%
  - **Commissioner sources (sheets):** ≥85% (with aliases)

- [ ] **Document in model header**

  ```sql
  -- Mapping coverage: 99.9% (12,089 / 12,133 mapped)
  ```

### Unmapped Players

- [ ] **Identify unmapped players**

  Use SQL query against staging model or raw data:

  ```sql
  -- Find players without mapping
  select distinct
    stg.player_name,
    stg.raw_provider_id,
    count(*) as record_count
  from {{ ref('stg_<provider>__<dataset>') }} stg
  where stg.player_id is null
  group by 1, 2
  order by record_count desc;
  ```

- [ ] **Review and create alias candidates**

  For unmapped players, check for:
  - Name variations (T.J. vs TJ)
  - Nicknames vs full names (Chris vs Christopher)
  - Punctuation differences (St. vs St)
  - Spelling errors or typos

  Search `dim_player_id_xref` for potential matches using fuzzy matching.

- [ ] **Update alias table (if valid matches found)**

  Add entries to `dbt/ff_data_transform/seeds/dim_name_alias.csv`:

  ```csv
  alias_name,canonical_name,alias_type,notes
  T.J. Hockenson,TJ Hockenson,punctuation,Missing period
  Chris Godwin,Christopher Godwin,nickname,Shortened first name
  ```

### player_key Pattern

- [ ] **Use for unmapped players**

  ```sql
  -- Ensures grain uniqueness even with unmapped players
  coalesce(xref.player_id, source.<raw_provider_id>) as player_key
  ```

- [ ] **Document purpose in model**

  ```sql
  -- player_key: Composite identifier for grain uniqueness
  --   - Mapped players: player_key = player_id (mfl_id)
  --   - Unmapped players: player_key = raw_provider_id (gsis_id, etc.)
  ```

---

## Batch Ingestion Validation

Use this checklist to validate batch ingestion jobs.

### Storage Layout

- [ ] **Partition structure**

  ```
  data/raw/<provider>/<dataset>/dt=YYYY-MM-DD/
  ├── *.parquet
  └── _meta.json
  ```

- [ ] **Cloud equivalent**

  ```
  gs://ff-analytics/raw/<provider>/<dataset>/dt=YYYY-MM-DD/
  ```

### Metadata Validation

- [ ] **_meta.json present**

  ```bash
  ls data/raw/<provider>/<dataset>/dt=*/\_meta.json
  ```

- [ ] **Required metadata fields**

  ```json
  {
    "loader_path": "src.ingest.nflverse.shim.load_nflverse",
    "source_version": "nflreadr==1.5.0",
    "asof_datetime": "2025-10-24T08:00:00Z",
    "row_count": 12133,
    "schema_hash": "sha256:abc123",
    "dataset_name": "players",
    "partition_date": "2025-10-24"
  }
  ```

- [ ] **Validate with script**

  ```bash
  uv run .claude/skills/data-architecture-spec1/scripts/check_lineage.py \
    --path data/raw/<provider>/<dataset>/dt=YYYY-MM-DD
  ```

### Schema Consistency

- [ ] **Same schema across partitions**

  ```bash
  uv run .claude/skills/data-architecture-spec1/scripts/validate_schema.py \
    --path data/raw/<provider>/<dataset> \
    --check schema_consistency
  ```

- [ ] **Schema hash matches**
  - All partitions have identical `schema_hash` in `_meta.json`

### Idempotency

- [ ] **Re-running produces identical output**

  ```bash
  # Run twice, compare output
  uv run tools/make_samples.py <provider> --datasets <dataset> --out ./test1
  uv run tools/make_samples.py <provider> --datasets <dataset> --out ./test2

  # Should be identical (excluding timestamps in _meta.json)
  ```

---

## Test Coverage Validation

Use this checklist to ensure comprehensive dbt test coverage.

### Required Tests (100% Coverage)

- [ ] **Grain uniqueness**
  - Every fact and staging model
  - Composite key test (singular or unique on concatenated columns)

- [ ] **FK integrity**
  - All foreign keys to dimensions
  - `relationships` tests

- [ ] **Enum validation**
  - All controlled vocabulary fields
  - `accepted_values` tests

- [ ] **Not-null**
  - All grain columns
  - All foreign keys
  - `not_null` tests

### Optional Tests (Recommended)

- [ ] **Range checks**
  - Numeric bounds (e.g., week 1-18, season 2020-2025)
  - Date ranges

- [ ] **Freshness tests**
  - Provider-specific thresholds
  - LKG banner flags

- [ ] **Row delta tests**
  - ± thresholds on fact tables
  - Detect anomalous batch sizes

### Running Tests

- [ ] **Run all tests**

  ```bash
  dbt test
  ```

- [ ] **Run model-specific tests**

  ```bash
  dbt test --select <model_name>
  ```

- [ ] **Acceptance**
  - All tests pass (0 failures)
  - 100% coverage on grain, FK, enum, not-null

---

## Validation Scripts Reference

Available validation scripts in `.claude/skills/data-architecture-spec1/scripts/`:

```bash
# Check metadata lineage (validates _meta.json format)
uv run .claude/skills/data-architecture-spec1/scripts/check_lineage.py \
  --path data/raw/<provider>/<dataset>/dt=YYYY-MM-DD

# Validate schema compliance
uv run .claude/skills/data-architecture-spec1/scripts/validate_schema.py \
  --path data/raw/<provider>/<dataset> \
  --check <metadata|schema_consistency|player_id_mapping>

# Generate grain validation SQL (manual execution required)
uv run .claude/skills/data-architecture-spec1/scripts/analyze_grain.py \
  --model <model_name> \
  --expected-grain "col1,col2,..."
```

**Note:** For identity resolution and test generation, use the SQL templates and dbt test patterns provided in the checklists above rather than automated scripts.

---

## Acceptance Criteria Summary

Use these thresholds for sign-off on new integrations:

| Component | Acceptance Criteria |
|-----------|---------------------|
| **Metadata** | _meta.json present with all required fields |
| **Schema** | Consistent across all partitions (same schema_hash) |
| **ID Mapping** | ≥95% coverage (stats), ≥90% (market), ≥85% (sheets) |
| **Tests** | 100% pass rate on grain, FK, enum, not-null |
| **Grain** | 0 duplicate rows on expected grain |
| **2×2 Model** | Facts real_world only, fantasy scoring in marts |
| **Documentation** | Header comments, coverage %, checklist updated |
