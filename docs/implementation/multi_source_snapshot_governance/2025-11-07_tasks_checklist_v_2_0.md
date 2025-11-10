# Multi-Source Snapshot Governance — Tasks Checklist

**Version**: 2.0\
**Date**: 2025-11-07\
**Status**: Active

______________________________________________________________________

**Implementation Tickets**: This checklist has been broken into 48 standalone tickets in the `tickets/` directory (expanded from 37 to cover all 13 staging models + mart fix). Each ticket corresponds to a logical unit of work completable in one session. See `tickets/00-OVERVIEW.md` for tracking.

**Status Legend**: `[ ]` pending, `[x]` complete, `[-]` in progress

______________________________________________________________________

## Phase 0: Kickoff & Decision Ratification

- [x] Confirm scope: All 5 sources for Prefect orchestration (nflverse, sheets, ktc, ffanalytics, sleeper)
- [x] Confirm Prefect Phases 1+2 implementation (local flows, all sources)
- [x] Approve snapshot registry seed creation and governance model
- [x] Define success metrics and acceptance criteria (document in README)
- [x] Identify blockers:
  - [x] GCS authentication status (service account key available?)
  - [x] Prefect Cloud access or local Prefect server setup
  - [x] Environment setup (Python 3.13.6, uv, dbt-fusion)
- [x] Configure environment and path management:
  - [x] Create `.env.example` with documented path overrides
  - [x] Create `config/env_config.yaml` with multi-environment paths (local, ci, cloud)
  - [x] Create `config/README.md` explaining environment switching
  - [x] Verify default globs in dbt models work without configuration
  - [x] Test that dbt works with zero configuration (defaults only)
- [x] Document Phase 0 decisions and exit criteria in implementation README

**Exit Criteria**: ✅ Complete - Team alignment on full scope and approach; blockers identified with mitigation plans.

______________________________________________________________________

## Phase 1: Foundation

### Macro Implementation

- [x] Create `dbt/ff_data_transform/macros/snapshot_selection.sql`
- [x] Implement `snapshot_selection_strategy` macro with three strategies:
  - [x] `latest_only` strategy
  - [x] `baseline_plus_latest` strategy
  - [x] `all` strategy (no filter for backfills)
- [x] Test macro compilation with `dbt compile`

### Staging Model Updates (13 models total)

**NFLverse (4 models)**:

- [x] Update `stg_nflverse__player_stats`:
  - [x] Replace `dt IN ('2025-10-01', '2025-10-27')` with macro call
  - [x] Use `baseline_plus_latest` strategy with baseline var
  - [x] Test compilation and execution
- [x] Update `stg_nflverse__snap_counts`:
  - [x] Replace `dt IN ('2025-10-01', '2025-10-28')` with macro call
  - [x] Use `baseline_plus_latest` strategy with baseline var
  - [x] Test compilation and execution
- [x] Update `stg_nflverse__ff_opportunity`:
  - [x] Replace direct `latest_snapshot_only()` call with `snapshot_selection_strategy` macro (latest_only strategy)
  - [x] Test compilation and execution for consistency
- [x] Update `stg_nflverse__ff_playerids`:
  - [x] Replace `dt=*` with macro call using `latest_only` strategy
  - [x] Test compilation and execution

**Sheets (5 models)**:

- [x] Update `stg_sheets__cap_space`:
  - [x] Replace `dt=*` with macro call using `latest_only` strategy
  - [x] Test compilation and execution
- [x] Update `stg_sheets__contracts_active`:
  - [x] Replace `latest_snapshot_only()` with `snapshot_selection_strategy` macro call using `latest_only` strategy
  - [x] Test compilation and execution
  - [x] Verify zero duplicates in unique key grain
- [x] Update `stg_sheets__contracts_cut`:
  - [x] Replace `latest_snapshot_only()` with `snapshot_selection_strategy` macro call using `latest_only` strategy
  - [x] Test compilation and execution
  - [x] Verify zero duplicates in unique key grain
- [x] Update `stg_sheets__draft_pick_holdings`:
  - [x] Replace `dt=*` with macro call using `latest_only` strategy
  - [x] Test compilation and execution
- [x] Update `stg_sheets__transactions`:
  - [x] Replace `dt=*` with macro call using `latest_only` strategy
  - [x] Test compilation and execution

**Sleeper (2 models)** ⚠️ **Priority: Fixes 1,893 duplicates**:

- [x] Update `stg_sleeper__fa_pool`:
  - [x] Replace custom latest_snapshot CTE with macro call using `latest_only` strategy
  - [x] Test compilation and execution
  - [~] Verify `mrt_fasa_targets` duplicate fix - ⚠️ DUPLICATES PERSIST (root cause in mart logic, not staging)
- [x] Update `stg_sleeper__rosters`:
  - [x] Replace `dt=*` with macro call using `latest_only` strategy
  - [x] Test compilation and execution
  - [x] Verify snapshot count = 1 (2025-11-05)
  - [x] Verify roster counts (12 franchises, 321 roster slots)

**KTC (1 model)**:

- [x] Update `stg_ktc_assets`:
  - [x] Replace `dt=*` with macro call using `latest_only` strategy
  - [x] Test compilation and execution

**FFAnalytics (1 model)** ⚠️ **Priority: Fixes 195 duplicates**:

- [x] Update `stg_ffanalytics__projections`:
  - [x] Replace `dt=*` with macro call using `latest_only` strategy
  - [x] Test compilation and execution
  - [x] Verify duplicate fix (33→17, remaining are source data quality issues)
  - [x] Verify `fct_player_projections` duplicate fix (162→101, cascaded from staging)

### Additional Data Quality Fixes ⚠️ **Priority: Discovered via comprehensive test analysis (2025-11-10)**

**NOTE**: Comprehensive test analysis revealed 3 additional data quality issues beyond the original 6. See tickets P1-023, P1-024, P1-025 for details. The `assert_canonical_player_key_alignment` test (originally P1-021) is now passing and ticket was removed.

**Status Update (2025-11-10)**: 3 of 8 data quality tickets completed, 1 significantly improved.

- [x] ✅ **Fix dim_pick_lifecycle_control TBD duplicates (P1-020)**:

  - [x] Identified Cartesian product join at line 68 (tbd × actual picks on season/round)
  - [x] Removed dead code (`actual_picks_created` CTE)
  - [x] Updated documentation (SQL comments + YAML) to reflect current state
  - [x] Result: 22 duplicates → 0 duplicates ✅

- [x] ✅ **Fix orphan pick references (P1-022)**:

  - [x] Identified root cause: Transaction data has incorrect round labels but correct overall pick numbers
  - [x] Updated `int_pick_transaction_xref.sql` to match on (season, overall_pick) only per ADR-014
  - [x] Removed unreliable `pick_round` from join conditions
  - [x] Result: 4 orphan picks → 0 orphan picks ✅

- [x] ✅ **Fix int_pick_comp_registry duplicate transaction IDs (P1-024)**:

  - [x] Identified SCD Type 2 join missing temporal filter
  - [x] Added temporal filter: `year(pc.transaction_date) between fm.season_start and coalesce(fm.season_end, 9999)`
  - [x] Result: 19 duplicates → 0 duplicates ✅

- [-] ⚠️ **Fix assert_12_base_picks_per_round test failures (P1-023)** - 81% IMPROVED:

  - [x] Fixed phantom R5 picks for 2018-2024 (league used 4-round format those years)
  - [x] Included "no selection" picks (asset_type='unknown') in draft actual counts
  - [-] Remaining: 4 rounds with \<12 picks (2014 R2, 2015 R2, 2017 R5, 2025 R5)
  - Result: 21 violations → 4 violations (81% improvement)

- [ ] Investigate `assert_idp_source_diversity` failures (P1-025):

  - [ ] Identify which IDP players/positions lack source diversity (3 failures)
  - [ ] Determine if test expectations are realistic
  - [ ] Either fix source coverage or downgrade test to warning (LOW PRIORITY)

- [ ] Update roster parity test count (P1-019):

  - [ ] Note: Test now shows 30 failures (was documented as 17)
  - [ ] Investigate and categorize all 30 roster discrepancies

### Mart Data Quality ⚠️ **Priority: Fixes 1,893 mart duplicates**

- [ ] Fix `mrt_fasa_targets` duplicate rows (discovered during P1-013):
  - [ ] Phase 1: Investigation
    - [ ] Test each CTE in isolation to identify where duplicates originate
    - [ ] Check `position_baselines` UNION ALL logic (offense vs IDP)
    - [ ] Determine correct grain: `player_id` vs `sleeper_player_id`
    - [ ] Document root cause with SQL evidence
  - [ ] Phase 2: Implementation
    - [ ] Implement fix based on root cause (QUALIFY/DISTINCT or join fixes)
    - [ ] Test compilation and execution
    - [ ] Verify row counts match expected (~3,380 unique combinations)
  - [ ] Phase 3: Validation
    - [ ] Run grain uniqueness test (expect 1,893 duplicates → 0)
    - [ ] Spot-check IDP players not duplicated
    - [ ] Verify metrics are consistent per player

### Sample Archival

- [ ] Archive legacy NFLverse samples:
  - [ ] Archive `data/raw/nflverse/weekly/dt=2024-01-01/` → `data/_archived_samples/2025-11-07/nflverse/weekly/dt=2024-01-01/`
  - [ ] Archive root-level CSV/Parquet samples to `data/_archived_samples/2025-11-07/`
  - [ ] Archive sheets samples similarly
- [ ] Preserve sample generation tool (`tools/make_samples.py`) for new source exploration
- [ ] Create archive README documenting what was archived and why
- [ ] Verify dbt globs don't match archived samples (test with `dbt compile`)

### Performance Profiling

- [ ] Profile `stg_nflverse__player_stats` query performance:
  - [ ] Run `EXPLAIN` before macro change (baseline)
  - [ ] Run `EXPLAIN` after macro change (with UNION)
  - [ ] Document query times and plan differences
- [ ] Profile `stg_nflverse__snap_counts` query performance (same process)
- [ ] Assess if materialization needed (threshold: >30s query time)

### Schema Drift Handling

- [ ] Verify `union_by_name=true` in models where schema can drift:
  - [ ] `stg_nflverse__player_stats` (stat columns evolve)
  - [ ] `stg_nflverse__snap_counts` (position groups may change)
- [ ] Monitor null rates by column after first snapshot update
- [ ] Document schema evolution patterns observed

**Exit Criteria**: All staging models compile, row counts match baseline, no CI breakage, performance acceptable.

______________________________________________________________________

## Phase 2: Governance

### Snapshot Registry Seed

- [ ] Create `dbt/ff_data_transform/seeds/snapshot_registry.csv` with columns:
  - [ ] `source` (nflverse, sheets, ktc, ffanalytics, sleeper)
  - [ ] `dataset` (weekly, snap_counts, etc.)
  - [ ] `snapshot_date` (dt value)
  - [ ] `status` (pending, current, historical, archived)
  - [ ] `coverage_start_season`
  - [ ] `coverage_end_season`
  - [ ] `row_count`
  - [ ] `notes`
- [ ] Populate with current snapshots for all 5 sources:
  - [ ] nflverse (weekly, snap_counts, ff_opportunity, schedule, teams)
  - [ ] sheets (roster, transactions, picks)
  - [ ] ktc (players, picks)
  - [ ] ffanalytics (projections)
  - [ ] sleeper (league data)
- [ ] Load seed with `dbt seed` and verify no errors
- [ ] Document snapshot lifecycle policy in registry notes

### Validation Tooling Extensions

#### Extend `tools/analyze_snapshot_coverage.py`

- [ ] Add row delta reporting:
  - [ ] Compare current vs previous snapshot row counts
  - [ ] Calculate delta (absolute and percentage)
  - [ ] Flag anomalies (deltas exceeding thresholds)
- [ ] Add season/week coverage gap detection:
  - [ ] Identify missing weeks within expected season ranges
  - [ ] Cross-reference with registry coverage expectations
  - [ ] Output gap report (season, week, expected date)
- [ ] Add player mapping rate checks:
  - [ ] Sample-join to `dim_player_id_xref`
  - [ ] Report mapping coverage by dataset/week
  - [ ] Flag datasets with \<90% mapping rate
- [ ] Update output format:
  - [ ] JSON output for CI consumption
  - [ ] Human-readable summary for manual review

#### Create `tools/validate_manifests.py`

- [ ] Implement registry-driven validation:
  - [ ] Read snapshot registry seed
  - [ ] Check for expected snapshots in `data/raw/`
  - [ ] Validate `_meta.json` manifests exist for each snapshot
- [ ] Implement manifest vs Parquet verification:
  - [ ] Compare row counts (manifest `row_count` vs actual Parquet)
  - [ ] Validate date ranges (coverage_start_season/end_season)
  - [ ] Check for required metadata fields (source_version, asof_datetime)
- [ ] Add CI integration:
  - [ ] Exit code 1 if validation fails (missing snapshots, count mismatches)
  - [ ] Exit code 0 if all validations pass
  - [ ] Optional: `--fail-on-gaps` flag for strict enforcement
- [ ] Optional: Add notification hooks (log warnings, Slack alerts)

### Freshness Tests (All 5 Sources)

- [ ] Add freshness tests for **nflverse**:

  - [ ] Update `dbt/ff_data_transform/models/sources/src_nflverse.yml`
  - [ ] Set `loaded_at_field: dt`
  - [ ] Set `warn_after: {count: 2, period: day}`
  - [ ] Set `error_after: {count: 7, period: day}`
  - [ ] Test with `dbt source freshness --select source:nflverse`

- [ ] Add freshness tests for **sheets**:

  - [ ] Update `dbt/ff_data_transform/models/sources/src_sheets.yml` (or create if missing)
  - [ ] Set `loaded_at_field: dt`
  - [ ] Set `warn_after: {count: 1, period: day}`
  - [ ] Set `error_after: {count: 7, period: day}`
  - [ ] Test with `dbt source freshness --select source:sheets`

- [ ] Add freshness tests for **ktc**:

  - [ ] Update `dbt/ff_data_transform/models/sources/src_ktc.yml` (or create if missing)
  - [ ] Set `loaded_at_field: dt`
  - [ ] Set `warn_after: {count: 5, period: day}`
  - [ ] Set `error_after: {count: 14, period: day}`
  - [ ] Test with `dbt source freshness --select source:ktc`

- [ ] Add freshness tests for **ffanalytics**:

  - [ ] Update `dbt/ff_data_transform/models/sources/src_ffanalytics.yml` (or create if missing)
  - [ ] Set `loaded_at_field: dt`
  - [ ] Set `warn_after: {count: 2, period: day}`
  - [ ] Set `error_after: {count: 7, period: day}`
  - [ ] Test with `dbt source freshness --select source:ffanalytics`

- [ ] Add freshness tests for **sleeper**:

  - [ ] Update `dbt/ff_data_transform/models/sources/src_sleeper.yml` (or create if missing)
  - [ ] Set `loaded_at_field: dt`
  - [ ] Set `warn_after: {count: 1, period: day}`
  - [ ] Set `error_after: {count: 7, period: day}`
  - [ ] Test with `dbt source freshness --select source:sleeper`

- [ ] Run full freshness check: `dbt source freshness`

- [ ] Validate current data meets thresholds (baseline)

**Exit Criteria**: Registry seed loads, validation tools functional, freshness tests pass for recently updated sources.

______________________________________________________________________

## Phase 3: Documentation

### SPEC Checklist Update (PRIORITY)

- [ ] Update `docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md`:
  - [ ] Document current snapshot selection state (hardcoded dates → macro)
  - [ ] Note which models updated vs pending
  - [ ] Document freshness test implementation status
  - [ ] Add snapshot registry governance section
  - [ ] Link to new ops docs (when created)
  - [ ] Update Prefect implementation status (Phases 1+2 in progress)

### Create Ops Documentation (Current State Focus)

- [ ] Create `docs/ops/snapshot_management_current_state.md`:

  - [ ] Document snapshot selection logic per source
  - [ ] List models using hardcoded dates vs macros
  - [ ] Explain sample storage patterns (`_samples/` directories)
  - [ ] Document snapshot lifecycle policy (pending → current → historical → archived)
  - [ ] Link to snapshot registry seed

- [ ] Create `docs/ops/ingestion_triggers_current_state.md`:

  - [ ] Document how loads run today (GH Actions, manual make commands)
  - [ ] List trigger frequency per source
  - [ ] Document credential storage patterns (env vars, service accounts)
  - [ ] Explain when/how each source updates
  - [ ] Note Prefect migration plan status

- [ ] Create `docs/ops/data_freshness_current_state.md`:

  - [ ] Document freshness test thresholds per source (table format)
  - [ ] Explain how to check data freshness (`dbt source freshness`)
  - [ ] Document expected update cadence per source
  - [ ] Note monitoring status (dbt tests only, no alerts yet)
  - [ ] Link to freshness test configurations

- [ ] Create `docs/ops/orchestration_architecture.md`:

  - [ ] Document current orchestration mix (GH Actions + manual)
  - [ ] Explain Prefect plan status (Phases 1+2 implementation)
  - [ ] Describe local vs cloud execution state
  - [ ] Document dependencies between ingestion jobs
  - [ ] Diagram flow sequence if helpful

- [ ] Create `docs/ops/ci_transition_plan.md`:

  - [ ] Document GitHub Actions → Prefect migration strategy
  - [ ] Define parallel run period (1-2 weeks)
  - [ ] Document rollback procedures if Prefect fails
  - [ ] Define cut-over validation criteria
  - [ ] Note: Planning only, execution deferred to future work

- [ ] Create `docs/ops/cloud_storage_migration.md`:

  - [ ] Document GCS bucket layout (`gs://ff-analytics/{raw,stage,mart,ops}/`)
  - [ ] Explain retention policies and lifecycle rules
  - [ ] Document IAM requirements (`storage.objects.*` permissions)
  - [ ] Provide service account setup guide with gcloud commands
  - [ ] Document DuckDB GCS configuration (httpfs extension)
  - [ ] Create migration checklist
  - [ ] Note: Blueprint only, no actual migration

### Update dbt Model Documentation

- [ ] Add comments to `stg_nflverse__player_stats` explaining snapshot strategy
- [ ] Add comments to `stg_nflverse__snap_counts` explaining snapshot strategy
- [ ] Update `dbt/ff_data_transform/models/staging/README.md` (if exists) with snapshot governance overview

**Exit Criteria**: SPEC checklist accurate, ops docs answer current-state questions, dbt model docs explain governance.

______________________________________________________________________

## Phase 4: Orchestration

### Directory Structure

- [ ] Create `src/flows/` directory
- [ ] Create `src/flows/__init__.py`
- [ ] Define shared utilities:
  - [ ] `src/flows/utils/validation.py` (validation task helpers)
  - [ ] `src/flows/utils/notifications.py` (logging/alerting helpers)

### Prefect Flow Implementation

#### Google Sheets Pipeline (Split into Two Flows)

**Copy Flow** (`copy_league_sheet_flow.py`):

- [ ] Create `src/flows/copy_league_sheet_flow.py`
- [ ] Define flow with tasks:
  - [ ] Copy tabs from Commissioner sheet to working copy
  - [ ] Validate copy completeness (all expected tabs copied)
- [ ] Configure to run every 2-4 hours during season
- [ ] Test locally with Prefect dev server

**Parse Flow** (`parse_league_sheet_flow.py`):

- [ ] Create `src/flows/parse_league_sheet_flow.py`
- [ ] Define flow with tasks:
  - [ ] Re-validate copy completeness before parsing
  - [ ] Parse with `src/ingest/sheets/commissioner_parser.py`
  - [ ] Write Parquet files
  - [ ] Write `_meta.json` manifests
- [ ] Add governance tasks:
  - [ ] Validate row counts against expected ranges
  - [ ] Check for required columns (player_name, team, etc.)
- [ ] Configure to run 15-30 minutes after copy flow completes
- [ ] Test flow sequencing (copy → parse)
- [ ] Test locally with Prefect dev server

#### NFL Data Pipeline

- [ ] Create `src/flows/nfl_data_pipeline.py`
- [ ] Define flow with tasks:
  - [ ] Fetch nflverse data via `src/ingest/nflverse/shim.py`
  - [ ] Write Parquet files (weekly, snap_counts, ff_opportunity)
  - [ ] Write `_meta.json` manifests
  - [ ] Update snapshot registry (mark new snapshot as current)
- [ ] Add governance tasks:
  - [ ] Freshness validation (check latest dt)
  - [ ] Row delta anomaly detection (compare to previous snapshot)
  - [ ] Call `validate_manifests.py`
- [ ] Test locally with Prefect dev server

#### KTC Pipeline

- [ ] Create `src/flows/ktc_pipeline.py`
- [ ] Define flow with tasks:
  - [ ] Fetch KTC API data
  - [ ] Parse players and picks
  - [ ] Write Parquet files
  - [ ] Write `_meta.json` manifests
- [ ] Add governance tasks:
  - [ ] Valuation range checks (min/max/median validations)
  - [ ] Player mapping validation (join to dim_player_id_xref)
- [ ] Test locally with Prefect dev server

#### FFAnalytics Projections Pipeline

- [ ] Create `src/flows/ffanalytics_pipeline.py`
- [ ] Define flow with tasks:
  - [ ] Run R projections via `scripts/R/run_projections.R`
  - [ ] Export Parquet files
  - [ ] Write `_meta.json` manifests
- [ ] Add governance tasks:
  - [ ] Projection reasonableness checks (min/max/sum validations)
  - [ ] Compare to historical projections (outlier detection)
- [ ] Test locally with Prefect dev server

#### Sleeper Pipeline

- [ ] Create `src/flows/sleeper_pipeline.py`
- [ ] Define flow with tasks:
  - [ ] Fetch league data via Sleeper API
  - [ ] Parse rosters and transactions
  - [ ] Write Parquet files
  - [ ] Write `_meta.json` manifests
- [ ] Add governance tasks:
  - [ ] Transaction date ordering validation
  - [ ] Roster size validations (expected ranges per league settings)
- [ ] Test locally with Prefect dev server

### Governance Integration

- [ ] Wire `validate_manifests.py` as Prefect task in each flow
- [ ] Add snapshot currency checks (latest dt meets freshness thresholds)
- [ ] Implement anomaly detection (row deltas exceeding thresholds)
- [ ] Configure notifications:
  - [ ] Log warnings for minor issues
  - [ ] Fail flow for critical errors
  - [ ] Optional: Slack/email notifications

### Local Testing

- [ ] Start Prefect dev server: `prefect server start`
- [ ] Run each flow manually via Prefect UI
- [ ] Validate task execution order and dependency handling
- [ ] Test failure scenarios:
  - [ ] API down (network error)
  - [ ] Invalid data (schema mismatch)
  - [ ] Validation failures (freshness, row counts)
- [ ] Review logs for debugging information quality

**Exit Criteria**: All 5 flows execute successfully locally, governance tasks catch known issues, no data quality regressions.

**Out of Scope**: Cloud deployment, advanced monitoring, backfill orchestration (Prefect Phases 3-4).

______________________________________________________________________

## Phase 5: CI Planning

### Parallel Run Strategy Documentation

- [ ] Document Week 1 plan:
  - [ ] Add Prefect flows to deployment
  - [ ] Keep GitHub Actions running unchanged
  - [ ] Begin collecting metrics (row counts, timing, failures)
- [ ] Document Week 2 plan:
  - [ ] Run both systems in parallel
  - [ ] Compare outputs daily (manifests, row counts, data integrity)
  - [ ] Monitor for discrepancies
- [ ] Document Week 3 plan (cut-over if validation passes):
  - [ ] Disable GitHub Actions schedules
  - [ ] Prefect becomes primary orchestrator
  - [ ] Keep GH Actions available for manual fallback
- [ ] Document Week 4+ (monitoring):
  - [ ] Monitor Prefect stability (2+ weeks)
  - [ ] Remove GH Actions if no issues
  - [ ] Archive old workflows (don't delete immediately)

### Rollback Procedures

- [ ] Document rollback steps:
  - [ ] Re-enable GitHub Actions schedules
  - [ ] Disable Prefect deployments
  - [ ] Validate data integrity after rollback
  - [ ] Debug Prefect locally before retrying
- [ ] Document failure scenarios:
  - [ ] Prefect crashes during execution
  - [ ] Data quality regressions detected
  - [ ] Performance degradation (>2x slower)
  - [ ] Governance validation failures

### Cut-Over Validation Criteria

- [ ] Define validation metrics:
  - [ ] Row count parity (±1% acceptable)
  - [ ] Manifest lineage fields populated correctly
  - [ ] Query performance no worse than baseline (±10%)
  - [ ] No freshness test failures for 3+ consecutive days
- [ ] Document decision framework:
  - [ ] All criteria must pass for cut-over approval
  - [ ] Team review meeting after 1-2 week parallel run
  - [ ] Unanimous approval required for cut-over

### Validation Tools in CI

- [ ] Add `validate_manifests.py` to GitHub Actions:
  - [ ] Add step to `.github/workflows/data-pipeline.yml`
  - [ ] Run before dbt execution
  - [ ] Fail workflow if validation fails
- [ ] Add freshness check step:
  - [ ] Run `dbt source freshness` before dbt models
  - [ ] Fail if any source shows errors
- [ ] Establish baseline metrics for comparison with Prefect

### Comparison Process Documentation

- [ ] Document automated diff process:
  - [ ] Compare output manifests (GH Actions vs Prefect)
  - [ ] Row count comparison queries (DuckDB)
  - [ ] Timing metrics collection (execution duration)
- [ ] Document manual review process:
  - [ ] Spot-check data samples
  - [ ] Review error logs from both systems
  - [ ] Team discussion of findings

**Exit Criteria**: Complete planning documentation with objective validation criteria and rollback procedures.

**Note**: Actual CI cut-over execution is out of scope. This phase delivers planning documentation only.

______________________________________________________________________

## Phase 6: Cloud Blueprint

### GCS Bucket Layout Documentation

- [ ] Document bucket structure:
  - [ ] `gs://ff-analytics/raw/` — Immutable source snapshots
  - [ ] `gs://ff-analytics/stage/` — Intermediate staging artifacts
  - [ ] `gs://ff-analytics/mart/` — Published dimensional models
  - [ ] `gs://ff-analytics/ops/` — Metadata, logs, monitoring
- [ ] Document partition patterns: `<source>/<dataset>/dt=YYYY-MM-DD/`
- [ ] Document retention policies per layer:
  - [ ] raw: 90 days (transition to Nearline)
  - [ ] stage: 30 days (delete after)
  - [ ] mart: 365 days (Archive tier)
  - [ ] ops: 180 days (Nearline)

### Retention and Lifecycle Policies

- [ ] Document lifecycle rules (explain `config/gcs/lifecycle.json`):
  - [ ] Age-based transitions (Standard → Nearline → Coldline → Archive)
  - [ ] Delete after retention period expires
  - [ ] Cost optimization considerations
- [ ] Document archival strategy for historical snapshots:
  - [ ] Promote to Coldline after 90 days
  - [ ] Archive after 1 year
  - [ ] Delete after 3 years (unless compliance requires longer)

### IAM Requirements Documentation

- [ ] Document required GCS permissions:
  - [ ] `storage.objects.create` (write Parquet)
  - [ ] `storage.objects.get` (DuckDB read)
  - [ ] `storage.objects.list` (glob patterns)
  - [ ] `storage.objects.delete` (lifecycle cleanup)
- [ ] Document service account roles:
  - [ ] Recommend `roles/storage.objectAdmin` for full control
  - [ ] Consider custom role for least-privilege access

### Service Account Setup Guide

- [ ] Document service account creation:
  ```bash
  gcloud iam service-accounts create ff-analytics-ingestion \
      --display-name="FF Analytics Ingestion"
  ```
- [ ] Document permission grant:
  ```bash
  gcloud projects add-iam-policy-binding PROJECT_ID \
      --member="serviceAccount:ff-analytics-ingestion@PROJECT_ID.iam.gserviceaccount.com" \
      --role="roles/storage.objectAdmin"
  ```
- [ ] Document key download:
  ```bash
  gcloud iam service-accounts keys create gcp-service-account-key.json \
      --iam-account=ff-analytics-ingestion@PROJECT_ID.iam.gserviceaccount.com
  ```
- [ ] Document key management:
  - [ ] Store in `config/secrets/` (gitignored)
  - [ ] Set `GOOGLE_APPLICATION_CREDENTIALS` env var
  - [ ] Rotate keys every 90 days

### DuckDB GCS Configuration

- [ ] Document DuckDB GCS setup:

  ```sql
  INSTALL httpfs;
  LOAD httpfs;

  SET gcs_access_key_id = '...';
  SET gcs_secret_access_key = '...';
  ```

- [ ] Document test query:

  ```sql
  SELECT * FROM read_parquet('gs://ff-analytics/raw/nflverse/weekly/dt=*/weekly.parquet')
  LIMIT 10;
  ```

- [ ] Document performance considerations (network latency, query pushdown)

### Migration Checklist

- [ ] Create pre-migration checklist:
  - [ ] Validate local data integrity
  - [ ] Backup critical snapshots
  - [ ] Test GCS credentials and permissions
- [ ] Create migration execution checklist:
  - [ ] Create GCS bucket with lifecycle rules
  - [ ] Set up service account and grant permissions
  - [ ] Initial data copy (gsutil rsync strategy)
  - [ ] Validate file counts and sizes match
  - [ ] Test DuckDB reads from GCS
  - [ ] Update Prefect flow env vars (`EXTERNAL_ROOT=gs://ff-analytics/raw`)
  - [ ] Test Prefect flows with cloud storage
- [ ] Create post-migration checklist:
  - [ ] Validate data integrity (row counts, checksums)
  - [ ] Monitor query performance (compare to local baseline)
  - [ ] Verify lifecycle rules trigger correctly
  - [ ] Document any issues encountered

### Rollback Plan

- [ ] Document rollback steps if migration issues arise:
  - [ ] Revert `EXTERNAL_ROOT` to local paths
  - [ ] Restart Prefect flows with local storage
  - [ ] Investigate GCS issues before retrying
  - [ ] Keep local data until cloud validated (2+ weeks)

### Optional: Sync Utility Prototype

- [ ] Create `tools/sync_snapshots.py`:
  - [ ] Implement bidirectional sync (local ↔ GCS)
  - [ ] Exclude `_samples/` directories (via glob patterns)
  - [ ] No overwrite unless `--force` flag
  - [ ] Dry-run mode (`--dry-run`) for testing
  - [ ] Progress reporting for large transfers
- [ ] Test sync utility:
  - [ ] Dry-run to preview operations
  - [ ] Sync small dataset (sample/test data)
  - [ ] Verify no data corruption

**Exit Criteria**: Complete GCS migration documentation ready for execution by team.

**Note**: This phase produces documentation only. Actual GCS migration execution is explicitly out of scope.

______________________________________________________________________

## Cross-Cutting Tasks

### Comparison Testing

- [ ] Create regression comparison queries:
  - [ ] Row count comparison (before/after macro change)
  - [ ] Statistical checks (min/max/sum of key stats)
  - [ ] Validate no data loss or duplication
- [ ] Document comparison test process in README

### Performance Monitoring

- [ ] Profile query performance before/after changes:
  - [ ] Use DuckDB `EXPLAIN` command
  - [ ] Document query plans and timing
  - [ ] Consider materialization if degradation detected

### Notebook Audit

- [ ] Audit Jupyter notebooks for hardcoded dt= filters:
  - [ ] `notebooks/fasa_enhanced_v2.ipynb`
  - [ ] `notebooks/fasa_weekly_strategy.ipynb`
- [ ] Add deprecation warnings for direct Parquet reads
- [ ] Encourage using dbt refs instead of raw files

______________________________________________________________________

## Progress Tracking

Use this checklist to track implementation progress. Update status (`[ ]` → `[-]` → `[x]`) as tasks are started and completed.

**Quick Reference**:

- Total phases: 7 (including Phase 0)
- Total tasks: ~150+ items across all phases
- Success metrics: 6 key criteria to complete

**For detailed rationale and technical specifications, see**: `2025-11-07_plan_v_2_0.md`
