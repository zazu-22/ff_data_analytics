# Bell Keg League — Phase Next Implementation Checklist (v2.3)

A pragmatic, step‑by‑step list to stand up the data pipeline with our latest decisions (SPEC v2.2), nflverse Python shim, R runners, projections config, and sample generator. Use this to coordinate work across the team.

**Purpose:** This checklist captures **implementation reality** (executed decisions, status, metrics, gaps). It reflects design refinements made during build-out and supersedes v2.2 on implementation details. For architectural rationale and original requirements baseline, refer to SPEC-1 v2.2.

**Relationship to SPEC v2.2:**

- v2.2 = Original architectural blueprint (authoritative for design intent and patterns)
- v2.3 = Execution checklist (authoritative for current status, decisions, and gaps)
- v4.x (refined_data_model_plan_v4.md) = Technical specifications (v4.1, v4.2, v4.3 addenda)
- **Key deviations documented in SPEC v2.2 Addendum section** (e.g., separate fact tables per ADR-007, fantasy scoring in marts, etc.)

Legend: ☐ todo · ☑ done/verified · (owner) · (notes)

Updated: 2025-10-25 — **League Rules Dimensions Added** (ADR-011): 5 new seeds (dim_league_rules, dim_rookie_contract_scale, dim_cut_liability_schedule, dim_rfa_compensation_schedule, dim_position_slot_eligibility) + dim_asset UNION dimension. Enables Phase 3A contract/roster analysis. Phase 1 Seeds expanded to 11/13 complete. All 49 new tests passing (100%).

______________________________________________________________________

## 0) Repo Prep & Version Pins

- ☑ Confirm repo tree matches SPEC paths:
  - `ingest/nflverse/registry.py`, `ingest/nflverse/shim.py` ☑
  - `scripts/R/nflverse_load.R`, `scripts/R/ffanalytics_run.R` ☑
  - `config/projections/ffanalytics_projections_config.yaml`, `config/projections/ffanalytics_projection_weights_mapped.csv` ☑
  - `config/scoring/sleeper_scoring_rules.yaml` ☑
  - `tools/make_samples.py` ☑
  - `docs/spec/SPEC-1_Consolidated_v2.3.md` (+ patch & change log) ☑ (named SPEC-1_v_2.2.md)
- ☑ Add `uv.lock` pinning: `polars (>=0.20)`, `pyarrow (>=15)`, `pandas`, `nflreadpy`. (polars 1.33.1, pyarrow 21.0.0, pandas 2.3.2, nflreadpy 0.1.3)
- ☑ Add `renv.lock` pinning: `nflreadr (>=1.5.0)`, `arrow`, `jsonlite`, `yaml`, `optparse`, `lubridate`, `remotes`, `ffanalytics` (GitHub), plus `digest`.
- ☑ Commit files and open PR "SPEC v2.3 integration". (Committed directly to main)

### Recommended Sequencing (High‑Level)

1. **Phase 1 - Seeds**: ☑ **COMPLETE** (11/13 done, 2 optional) - ALL TRACKS UNBLOCKED!

   - ☑ dim_player_id_xref (12,133 players, 19 provider IDs)
   - ☑ dim_franchise, dim_pick, dim_scoring_rule, dim_timeframe
   - ☑ dim_name_alias (78 alias mappings for 100% player coverage)
   - ☑ **dim_league_rules** (salary cap, roster limits - Type 2 SCD) ✅ **NEW**
   - ☑ **dim_rookie_contract_scale** (rookie contract amounts by draft position) ✅ **NEW**
   - ☑ **dim_cut_liability_schedule** (dead cap percentages) ✅ **NEW**
   - ☑ **dim_rfa_compensation_schedule** (RFA compensation picks) ✅ **NEW**
   - ☑ **dim_position_slot_eligibility** (roster slot rules by position) ✅ **NEW**
   - ☐ stat_dictionary (optional - single provider, not yet needed)

2. **Phase 2 - Parallel Tracks** (ALL UNBLOCKED):

   - **Track A (NFL Actuals)**: ☑ 100% COMPLETE ✅ - nflverse staging ✅ → fact_player_stats ✅ (109 stat types) → player_key solution ✅ → dim_player ✅ → dim_team ✅ (dedupe added) → dim_schedule ✅ (requires teams data availability) → mart_real_world_actuals_weekly ✅ → mart_fantasy_actuals_weekly ✅ (data-driven scoring) → **Kicking stats added ✅ (21 new stats: FG/PAT by distance)**

   **Snapshot Governance (Multi-Source Snapshot Governance Epic - Phase 1 COMPLETE ✅)**:

   - ☑ `snapshot_selection_strategy` macro implemented (calls existing `latest_snapshot_only` helper)
   - ☑ `stg_nflverse__player_stats` uses macro (`baseline_plus_latest`, fallback baseline_dt pattern)
   - ☑ `stg_nflverse__snap_counts` uses macro (`baseline_plus_latest`, fallback baseline_dt pattern)
   - ☑ `stg_nflverse__ff_opportunity` uses macro (`latest_only`, consistency with other models)
   - ☑ `stg_nflverse__ff_playerids` uses macro (`latest_only`)
   - ☑ `stg_sheets__cap_space` uses macro (`latest_only`)
   - ☑ `stg_sheets__contracts_active` uses macro (`latest_only`)
   - ☑ `stg_sheets__contracts_cut` uses macro (`latest_only`)
   - ☑ `stg_sheets__draft_pick_holdings` uses macro (`latest_only`)
   - ☑ `stg_sheets__transactions` uses macro (`latest_only`)
   - ☑ `stg_sleeper__fa_pool` uses macro (`latest_only`)
   - ☑ `stg_sleeper__rosters` uses macro (`latest_only`)
   - ☑ `stg_ktc_assets` uses macro (`latest_only`)
   - ☑ `stg_ffanalytics__projections` uses macro (`latest_only`)
   - ☑ Legacy sample artifacts archived (documented archival policy - no action needed)
   - ☑ Performance baseline documented (all three NFLverse models profiled)

   See: `dbt/ff_data_transform/macros/snapshot_selection.sql`
   See: `docs/implementation/multi_source_snapshot_governance/`

   **Critical Fixes Applied (Oct 25)**:

   - ✅ Player ID architecture corrected: Using mfl_id as canonical player_id (ADR-010 compliance restored)
   - ✅ Fantasy scoring refactored: Data-driven from dim_scoring_rule (2×2 model compliance restored)
   - ✅ Team dimension: Deduplication added for multi-season dataset support
   - ✅ Infrastructure fixes: DuckDB path resolution, GCS→local config, schedule/teams datasets loaded, conference/division seed added
   - ✅ **Kicking stats implemented**: 21 new stats (fg_att, fg_made, fg_missed by distance, pat_att/made/missed, gwfg stats)
   - ✅ **Stat count expanded**: 71 base stats (was 50) → 109 total stat types (71 base + 6 snap + 32 opportunity)
   - ✅ Test coverage: 147/149 tests passing (98.7%), all models building successfully
   - ✅ **Track A 100% COMPLETE** - All core NFL actuals data fully integrated
   - **Track B (League Data)**: ☑ 100% COMPLETE ✅ - Parse TRANSACTIONS tab ✅ → stg_sheets\_\_transactions ✅ → fact_league_transactions ✅ → make_samples.py support ✅ → All tests passing ✅ (25/25) → dim_player_contract_history (Phase 3) → trade analysis marts (Phase 3)
   - **Track C (Market Data)**: ☑ 100% COMPLETE ✅ - KTC fetcher ✅ → stg_ktc_assets ✅ → fact_asset_market_values ✅ (all tests passing)
   - **Track D (Projections)**: ☑ 100% COMPLETE ✅ - FFanalytics weighted aggregation ✅ → stg_ffanalytics\_\_projections ✅ → fact_player_projections ✅ → mart_real_world_projections ✅ → mart_fantasy_projections ✅ → mart_projection_variance ✅ (20/20 tests passing)

3. **Phase 3 - Integration & Analysis:**

   - ✅ Variance marts: mart_projection_variance (actuals vs projections)
   - Trade valuations: mart_trade_valuations (TRANSACTIONS vs KTC market)
   - CI (Sheets): copy_league_sheet → commissioner_parse → dbt run/test, with CSV previews + dbt summary and LKG fallback
   - Ops: run ledger, model metrics, data quality, freshness banners
   - Change‑capture staging models (roster/sheets change logs) and compaction playbook docs

## Data Quality & Governance

**Multi-Source Snapshot Governance (Phase 2 - 71% Complete)**:

### Snapshot Registry

- ☑ Registry seed created (`dbt/ff_data_transform/seeds/snapshot_registry.csv`)
- ☑ Populated with all 5 sources (nflverse, sheets, ktc, ffanalytics, sleeper) - 100 snapshots registered
- ☑ Lifecycle states defined (pending, current, historical, archived)
- ☑ Validation tooling implemented (`tools/validate_manifests.py`)
- ☑ Registry maintenance tooling created (`tools/update_snapshot_registry.py`)

### Freshness Tests

**Manifest-based freshness validation** (replaces dbt source freshness):

- ☑ Freshness validation added to `validate_manifests.py` (P2-006B)
- ☑ Per-source thresholds configured:
  - nflverse: warn 2 days, error 7 days
  - sheets: warn 1 day, error 7 days (multiple times per day during season)
  - sleeper: warn 1 day, error 7 days
  - ktc: warn 5 days, error 14 days
  - ffanalytics: warn 2 days, error 7 days
- ☑ Validates manifest timestamps against current date
- ☑ Reports freshness violations with actionable messages

See: `tools/validate_manifests.py`

### Coverage Analysis & Observability

- ☑ `analyze_snapshot_coverage.py` extended with row deltas (P2-003)
  - Row count delta calculations between snapshots
  - Anomaly detection with configurable thresholds
  - Discovered data quality issues (missing row_count values in nflverse registry)
- ☑ Gap detection added (P2-004)
  - Season/week coverage gap detection (baseline_plus_latest aware)
  - Player mapping rate calculation (dim_player_id_xref integration)
  - CI/CD safe: no false alarms for expected partial coverage
- ☑ CI integration ready (validation tooling designed for automated pipelines)

See: `tools/analyze_snapshot_coverage.py`
See: `docs/implementation/multi_source_snapshot_governance/REGISTRY_MAINTENANCE.md`

**Data Quality Fixes (Phase 1)**:

- ☑ Macro cartesian product regression fixed (P1-026: 3,563 duplicates → 0) ✅
- ☑ TBD pick duplicates resolved (P1-020: 22 pick_ids → 0) ✅
- ☑ Base picks per round validation (P1-023: 4 failures → 0) ✅ 100% success
- ☑ Comp registry duplicates eliminated (P1-024: 19 duplicates → 0) ✅
- ☑ Orphan pick references resolved (P1-022: 46 orphans → 0) ✅
- ☑ Roster parity discrepancies resolved (P1-019: 30 failures → 0) ✅ Streaming hypothesis validated
- ☑ FFAnalytics source data duplicates (P1-018: 34 duplicates → 0) ✅ Architectural fix
- ☑ Mart duplicates eliminated (P1-017: 1,908 duplicates → 0) ✅ IDP position filter
- ☑ IDP source diversity validated (P1-025: COMPLETE - test downgraded to warning, industry limitation documented) ✅
- ☑ Player ID resolution refactored (P1-027: contracts models use macro consistently) ✅
- ☑ DST team defense seed created (P1-028: 612/612 DST mapped, coverage ~89% → ~93%) ✅
- ☑ Defense macro applied to contracts (P1-028b: contracts models use defense crosswalk) ✅

**Success Metrics** (from Multi-Source Snapshot Governance epic):

- ☑ Zero hardcoded snapshot dates in all 13 staging models ✅
- ☑ All staging models use snapshot_selection_strategy macro ✅
- ☑ All current test failures resolved (2,088+ duplicates eliminated) ✅

## Prefect Orchestration (Phases 1+2)

**Status**: Phase 4 - Pending Implementation

- ☐ Flow structure created (`src/flows/`)
- ☐ `copy_league_sheet_flow` implemented (Google Sheets copy operation)
- ☐ `parse_league_sheet_flow` implemented (Google Sheets parse operation)
- ☐ `nfl_data_pipeline` implemented
- ☐ `ktc_pipeline` implemented
- ☐ `ffanalytics_pipeline` implemented
- ☐ `sleeper_pipeline` implemented
- ☐ Governance integration (validation tasks, copy completeness checks)
- ☐ Local testing completed
- ☐ Cloud deployment (Phase 3 - deferred)
- ☐ Advanced monitoring (Phase 4 - deferred)

See: `src/flows/` (to be created)
See: `docs/ops/orchestration_architecture.md` (to be created in P3-005)
See: `docs/spec/prefect_dbt_sources_migration_20251026.md` (detailed implementation guide)

## Operations Documentation

**Status**: Phase 3 - Pending Implementation

- ☐ `snapshot_management_current_state.md` (P3-002)
- ☐ `ingestion_triggers_current_state.md` (P3-003)
- ☐ `data_freshness_current_state.md` (P3-004)
- ☐ `orchestration_architecture.md` (P3-005)
- ☐ `ci_transition_plan.md` (P3-006)
- ☐ `cloud_storage_migration.md` (P3-007)

See: `docs/ops/` directory (to be created)
See: `docs/implementation/multi_source_snapshot_governance/tickets/P3-00*.md` for ticket details

### 0a) Conventions & Structure

- ☑ Document repository conventions and layout (`docs/dev/repo_conventions_and_structure.md`).
- ☑ Document Kimball dimensional modeling guidance (`docs/architecture/kimball_modeling_guidance/kimbal_modeling.md`) for dbt fact/dimension design.
- ☐ Align existing files to conventions (naming, placement):
  - Scripts named `verb_noun.py` under a domain folder
  - Ensure ingest shims stay in `ingest/<provider>/`; reusable helpers live in `src/ff_analytics_utils/`
  - Confirm data folders mirror cloud layout (`data/{raw,stage,mart,ops}` for local dev)
  - Add `dbt/ff_data_transform/` scaffold with `models/{sources,staging,core,markets,ops}`
- ☑ Link conventions doc from README.
- ☑ Add Makefile shortcuts for local iteration (`samples-nflverse`, `dbt-run`, `dbt-test`, `quickstart-local`).
- ☑ Add dev dependency: `dbt-duckdb` and include in dev setup instructions.
- ☑ Ignore build artifacts in VCS and lint: add `dbt/**/target/`, `dbt/**/logs/` to `.gitignore` and pre-commit excludes.
- ☑ Add manual SQL auto-fix helper: `make sqlfix` (runs `sqlfluff-fix` in manual stage).

## 1) Cloud Paths & Secrets

- ☑ Confirm GCS bucket/prefix: `gs://ff-analytics/{raw,stage,mart}` (bucket created with lifecycle policies).
- ☑ Configure CI secrets:
  - `GOOGLE_APPLICATION_CREDENTIALS_JSON` (service account key configured).
  - `GCP_PROJECT_ID`, `GCS_BUCKET`, `SLEEPER_LEAGUE_ID`, `COMMISSIONER_SHEET_URL` (all configured).
  - `SPORTS_DATA_IO_API_KEY` (configured as optional).
- ☑ Validate service account access to GCS (verified with test workflow).
- ☑ Validate service account access to Commissioner Sheet (verified via copy runner and troubleshooting scripts).

## 2) nflverse — Python Shim Bring‑Up

- ☑ Local run (dev):

  - `python -c "from ingest.nflverse.shim import load_nflverse; result = load_nflverse('players', out_dir='data/raw/nflverse')"`
  - `python -c "from ingest.nflverse.shim import load_nflverse; result = load_nflverse('weekly', seasons=[2023], out_dir='data/raw/nflverse')"`
  - Fixed registry: `load_player_stats` (not `load_player_stats_weekly`)
  - Fixed shim to handle varying function signatures (inspect params before calling)

- ☑ Verify Parquet & `_meta.json` under temp output (or configured GCS mount), schemas align with dbt expectations.

  - Successfully creates partitioned output: `data/raw/nflverse/{dataset}/dt=YYYY-MM-DD/`
  - Metadata includes loader_path, source_version, asof_datetime

- ☑ Test **R fallback** path works: `loader_preference="r_only"` for `schedule`.

  - R packages installed: lubridate, nflreadr, arrow, jsonlite
  - Fixed shim to properly return R loader manifest
  - Successfully tested: schedule (285 games), players via R

- ☑ Extend `src/ingest/nflverse/registry.py` if we add datasets (injuries, depth_charts, teams, etc.)

  - Registry already includes: players, weekly, season, injuries, depth_charts, schedule, teams
  - Tested: injuries (5599 records), teams (768 records)

- ☐ **Add v4.3 datasets** (ADR-009, ADR-010):

  - ☐ Add `ff_playerids` to registry (TIER 1 - BLOCKER for seeds)
    - Primary key: `mfl_id` (canonical player_id)
    - Contains 19 provider ID mappings (gsis_id, sleeper_id, espn_id, yahoo_id, pfr_id, ktc_id, etc.)
    - Required for `dim_player_id_xref` seed generation
  - ☐ Add `snap_counts` to registry (TIER 2)
    - Snap participation by phase (offense, defense, ST)
    - Integrates into `fact_player_stats` (6 stat types)
  - ☐ Add `ff_opportunity` to registry (TIER 2)
    - Expected stats, variances, team shares (170+ columns)
    - Integrates into `fact_player_stats` (~40 key stat types selected)
    - Enables variance analysis without manual calculation

- ☑ Add GCS write support (Python path)

  - Implemented via PyArrow FS helpers in `src/ingest/common/storage.py`.
  - `load_nflverse(..., out_dir='gs://<bucket>/raw/nflverse')` writes Parquet + `_meta.json`.
  - Added `tools/smoke_gcs_write.py` for quick verification.

## 3) Sleeper — Minimal Ingest Checks

- ☑ Run samples: `uv run tools/make_samples.py sleeper --datasets league users rosters players --league-id 1230330435511275520 --out ./samples`
  - Fixed duplicate column issue (renamed index to sleeper_player_id)
- ☑ Confirm fields exist for contracts/cap linkage (IDs, roster slots, player IDs).
  - Key fields present: owner_id, roster_id, players, starters
- ☑ Validate row counts ~ league expectations (12 teams; starters per roster rules).
  - Confirmed: 12 rosters, 13 users (co-owners), league ID matches

Notes on Samples Objective:

- Ensure Sleeper samples preserve raw column names/types where feasible; avoid premature renames.
- Use samples to validate PKs and downstream identity mapping before staging transforms.

## 4) Google Sheets — Commissioner SSoT

- ☑ Implement server-side copy strategy (ADR-005) to handle complex Commissioner Sheet:
  - `scripts/ingest/copy_league_sheet.py` - Server-side copyTo with value freezing
  - Uses Shared Drive for logging (service account quota workaround)
  - Intelligent skip logic based on source modification times
- ☑ Configure league sheet copy destination and logging:
  - Source: `COMMISSIONER_SHEET_ID`
  - Destination: `LEAGUE_SHEET_COPY_ID`
  - Logs: Shared Drive `LOG_PARENT_ID`
- ☑ Export small samples per tab from the copied sheet:
  - `uv run tools/make_samples.py sheets --tabs Eric Gordon Joe JP Andy Chip McCreary TJ James Jason Kevin Piper --sheet-url https://docs.google.com/spreadsheets/d/1HktJj-VB5Rc35U6EXQJLwa_h4ytiur6A8QSJGN0tRy0 --out ./samples`
  - Fixed credential loading (supports both GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_APPLICATION_CREDENTIALS_JSON)
  - Added handling for duplicate/empty column headers in sheets
- ☑ Parse raw commissioner sheets into logical tables:
  - Implemented parser: `src/ingest/sheets/commissioner_parser.py` → `roster`, `cut_contracts`, `draft_picks`
  - Includes GM column; uses Polars with `orient="row"`
- ☑ Write parsed tables as Parquet to `data/raw/commissioner/<table>/dt=YYYY-MM-DD/` (via storage helper)
- ☑ Add unit tests with small fixtures: `tests/test_sheets_commissioner_parser.py`
- ☑ Verify non-null keys for GM and player fields in roster sample test
- ☑ **Parse TRANSACTIONS tab → league transaction history** (COMPLETE ✅):
  - **Seeds dependency**: ✅ `dim_player_id_xref`, `dim_pick`, `dim_timeframe`, `dim_name_alias` (100% coverage)
  - ✅ Skip logic in parser (`parse_commissioner_dir`) appropriately skips TRANSACTIONS folder
  - ✅ Implemented `parse_transactions()` in `commissioner_parser.py` (300+ lines, 6 helpers)
  - ✅ Grain: one row per asset per transaction (matches raw TRANSACTIONS structure)
  - ✅ Map player names to canonical `player_id` via `dim_player_id_xref` (100% coverage via `dim_name_alias`)
  - ✅ Group multi-asset trades via `transaction_id` (from Sort column)
  - ✅ Asset types: player, pick, cap_space, defense, unknown (5 types)
  - ✅ Capture: transaction_date (11 refined types), from_franchise, to_franchise, contract details with validation flags
  - ✅ Write to `data/raw/commissioner/transactions/dt=YYYY-MM-DD/transactions.parquet`
  - ✅ Update `tools/make_samples.py` to include TRANSACTIONS tab (documentation added)
- ☑ Add unit tests for TRANSACTIONS parsing with trade/cut/waiver fixtures (COMPLETE ✅ - 41 tests passing)

Normalization policy and dbt expectations:

- Long‑form normalization in parser for Sheets (semi‑structured) to simplify dbt:
  - `contracts_active(gm, player, position, year, amount, rfa, franchise)`
  - `contracts_cut(gm, player, position, year, dead_cap_amount)`
  - `draft_picks(gm, year, round, source_type, original_owner, acquired_from, acquisition_note, condition_flag)`
  - `draft_pick_conditions(gm, year, round, condition_text)`
  - `transactions(transaction_id, transaction_date, transaction_type, from_franchise_id, to_franchise_id, asset_type, player_id?, pick_id?, contract_years?, contract_total?, contract_split?, rfa_matched, faad_compensation)` (NEW)

## 5) KeepTradeCut — Replace Sampler Stub

- ☑ Implement real KTC fetcher (players + picks) respecting ToS and polite rate limits (randomized sleeps, caching).
- ☑ Update `tools/make_samples.py::sample_ktc` to call actual fetcher; keep `--top-n` sampling to limit size.
- ☑ Normalize to long‑form `asset_type ∈ {player,pick}` with `asof_date`, `rank`, `value`.
- ☑ Write Parquet to `data/raw/ktc/{players,picks}/dt=YYYY-MM-DD/` with `_meta.json`
- ☑ Export small samples from the KTC fetcher
- ☑ Create `stg_ktc_assets` staging model with player ID mapping via dim_player_id_xref
- ☑ Create `fact_asset_market_values` fact table
- ☑ Add comprehensive dbt tests (grain uniqueness, FK integrity, enums, not-null)

Acceptance criteria: ✅ ALL MET

- ✅ Contract test: `asset_type ∈ {player,pick}`, `market_scope='dynasty_1qb'`, values ≥ 0, `asof_date` present.
- ✅ Cache + throttle with randomized sleeps (2-5 second delays); 1-hour cache TTL.
- ✅ Samples updated to use real client (50 players, 36 picks from live KTC data).
- ✅ Staging model: Player name → mfl_id crosswalk with player_key pattern for unmapped players
- ✅ Fact table: Grain (player_key, market_scope, asof_date) with 12/12 tests passing
- ✅ Data Attribution: Proper KTC attribution in docstrings and metadata

## 6) FFanalytics — Wire Runner (R) to Real Projections

- ☑ Edit `scripts/R/ffanalytics_run.R` to scrape raw projections from multiple sources
  - Simplified to just get raw projections without calculations
  - Successfully scrapes from 8 sources: CBS, ESPN, FantasyPros, FantasySharks, FFToday, NumberFire/FanDuel, RTSports, Walterfootball
  - Failed sources: FantasyData, FleaFlicker, Yahoo, FantasyFootballNerd, NFL (no data)
- ☑ Ensure output long‑form schema with raw projection stats
  - Output includes: player, pos, team, pass_yds, pass_tds, rush_yds, rush_tds, rec_yds, rec_tds, etc.
  - Each source's projections kept separate with data_src column
- ☑ Smoke test via tool: `PYTHONPATH=. uv run tools/make_samples.py ffanalytics --config ... --scoring ... --weeks 0 --out ./samples`
  - Successfully generates samples with 3,698 projections from 8 sources
  - Covers all positions: QB, RB, WR, TE, K, DST
- ☑ Document site availability: 8 working sources for 2024 season-long projections

Next steps (weighted aggregation and normalization):

- ☑ **Weighted aggregation across sources** (site weights in projections config) ✅ COMPLETE
  - Apply site weights from `config/projections/ffanalytics_projection_weights_mapped.csv`
  - Compute consensus projection per player per stat
  - Output provider='ffanalytics_consensus'
  - **Implementation**: `scripts/R/ffanalytics_run.R` enhanced with weighted.mean() using site weights
  - **Coverage**: 95.1% player mapping coverage in tests
- ☑ **Normalize to staging format** ✅ COMPLETE
  - Map player names to canonical `player_id` via `dim_player_id_xref` (done in R runner)
  - Derive `horizon` from projection type ('weekly', 'rest_of_season', 'full_season')
  - Output real-world stats only (`measure_domain='real_world'`)
  - Fantasy scoring applied in marts (not in raw projections)
  - **Implementation**: `dbt/ff_data_transform/models/staging/stg_ffanalytics__projections.sql`
- ☑ Write to `data/raw/ffanalytics/projections/dt=YYYY-MM-DD/` with `_meta.json` ✅ COMPLETE
  - **Output structure**: Separate `projections_raw_*.parquet` and `projections_consensus_*.parquet`
  - **Metadata includes**: player_mapping stats, source success/failure, weights applied

Acceptance criteria:

- ✅ Deterministic long‑form real-world projections
- ✅ Player name → ID mapping validates via seeds (95% coverage)
- ✅ Staging validates stat ranges and horizon values (20/20 tests passing)
- ✅ **Note:** Fantasy points computed in `mart_fantasy_projections` by applying `dim_scoring_rule` to real-world projections (2×2 model)

## 7) dbt — Seeds, Staging, and Marts

- ☑ Scaffold dbt project structure under `dbt/ff_data_transform/` with external Parquet defaults.
- ☑ **Seeds - PHASE 1 COMPLETE** (5/8 done, 3 optional - ALL TRACKS UNBLOCKED):
  - ☑ **`dim_player_id_xref`** (ADR-010 - COMPLETE ✅):
    - Source: nflverse ff_playerids dataset → dbt/ff_data_transform/seeds/dim_player_id_xref.csv
    - 12,133 players with 19 provider ID mappings
    - Primary key: `mfl_id` (canonical player_id)
    - Includes: name, merge_name, position, team, birthdate, draft_year
    - ALL provider IDs: mfl_id, gsis_id, sleeper_id, espn_id, yahoo_id, pfr_id, fantasypros_id, pff_id, cbs_id, ktc_id, sportradar_id, fleaflicker_id, rotowire_id, rotoworld_id, stats_id, stats_global_id, fantasy_data_id, swish_id, cfbref_id, nfl_id
  - ☑ **`dim_franchise`** (COMPLETE ✅):
    - SCD Type 2 ownership history (F001-F012)
    - Columns: franchise_id, franchise_name, division, established_season, owner_name, season_start, season_end, is_current_owner
  - ☑ **`dim_scoring_rule`** (COMPLETE ✅):
    - Half-PPR + IDP scoring with validity periods
    - SCD Type 2: rule_id, stat_category, stat_name, points_per_unit, valid_from_season, valid_to_season, is_current
  - ☑ **`dim_pick`** (COMPLETE ✅):
    - 2012-2030 base draft picks
    - 5 rounds × 12 teams per year
    - Columns: pick_id, season, round, round_slot, pick_type, notes
  - ☑ **`dim_timeframe`** (COMPLETE ✅):
    - Maps TRANSACTIONS timeframe strings to structured season/week/period
  - ☑ **`dim_asset`** (COMPLETE ✅):
    - Unified player/pick/cap asset catalog
    - UNION of dim_player_id_xref + dim_pick
  - ☐ **`stat_dictionary.csv`** (OPTIONAL - only needed for multi-provider normalization):
    - Currently single provider (nflverse)
  - ☐ **`dim_name_alias`** (OPTIONAL - add iteratively if fuzzy matching fails):
    - Alternate spellings for TRANSACTIONS player name resolution
- ☑ **Stage models - Track A COMPLETE** (3/3 nflverse staging models):
  - ☑ `stg_nflverse_*` (players, weekly, season, injuries, depth_charts, schedule, teams, **snap_counts**, **ff_opportunity**)
    - ☑ `stg_nflverse__players.sql` reading local `data/raw` Parquet (tests: not_null + unique `gsis_id`)
    - ☑ `stg_nflverse__weekly.sql` with PK tests: not_null (`season`,`week`,`gsis_id`) + singular uniqueness test on key
    - ☑ **`stg_nflverse__player_stats.sql`** (COMPLETE ✅):
      - Maps `gsis_id` → `mfl_id` via `dim_player_id_xref` crosswalk
      - Unpivots 50 base stats to long form
      - Includes player_key for grain uniqueness (50 unpivot statements)
      - Documents NULL filtering (0.12% filtered) and mapping coverage (99.9%)
      - Surrogate game_id: season_week_team_opponent
    - ☑ **`stg_nflverse__snap_counts.sql`** (COMPLETE ✅):
      - Maps `pfr_player_id` → `mfl_id` via crosswalk
      - Unpivots 6 snap stats to long form
      - Includes player_key for grain uniqueness (6 unpivot statements)
      - Documents NULL filtering (0.00%) and mapping coverage (81.8%, 18.2% unmapped mostly linemen)
    - ☑ **`stg_nflverse__ff_opportunity.sql`** (COMPLETE ✅):
      - Maps `gsis_id` → `mfl_id` via crosswalk
      - Unpivots 32 opportunity metrics to long form
      - Includes player_key for grain uniqueness (32 unpivot statements)
      - Documents NULL filtering (6.75% unidentifiable records) and mapping coverage (99.86%)
      - Expected stats: \*\_exp (12 types)
      - Variance stats: \*\_diff (12 types)
      - Team shares: air_yards, attempts (8 types)
  - ☐ `stg_sleeper_*` (league, users, rosters, roster_players)
  - `stg_sheets_*` (contracts_active, contracts_cut, draft_picks, draft_pick_conditions, transactions)
    - ☐ Add `stg_sheets__roster_changelog` (hash-based SCD tracking)
    - ☐ Add `stg_sheets__change_log` (row hash per tab/dt)
    - ☑ Add `stg_sheets__transactions.sql` (COMPLETE ✅ - transaction history)
      - ✅ Source: `data/raw/commissioner/transactions/dt=*/transactions.parquet`
      - ✅ Map player names → canonical `player_id` via `dim_player_id_xref`
      - ✅ Join to `dim_timeframe` for transaction_date derivation
      - ✅ Join to `dim_franchise` (SCD Type 2 temporal join on season)
      - ✅ Add `player_key` composite identifier (prevents grain violations)
      - ✅ Calculate contract validation flags
    - ☑ Tests (IMPLEMENTED ✅ in `models/staging/schema.yml`):
      - unique: `contracts_active (gm,player,year)`, `contracts_cut (gm,player,year)`, `draft_picks (gm,year,round)`
      - FK: `contracts_cut (gm,player,year) → contracts_active (gm,player,year)` (when present)
      - FK: `draft_pick_conditions (gm,year,round) → draft_picks (gm,year,round)`
      - not_null and numeric ranges (amounts ≥ 0), enumerations on `source_type`
      - **transactions tests** (IMPLEMENTED ✅):
        - ✅ unique: `transaction_id_unique` (PK)
        - ✅ FK: `player_id → dim_player_id_xref.player_id` (when asset_type=player and player_id != -1)
        - ✅ FK: `pick_id → dim_pick.pick_id` (when asset_type=pick, severity=warn for compensatory picks)
        - ✅ FK: `from_franchise_id, to_franchise_id → dim_franchise.franchise_id` (with null handling)
        - ✅ FK: `timeframe_string → dim_timeframe.timeframe_string`
        - ✅ enums: `transaction_type ∈ {11 refined types}`
        - ✅ enums: `asset_type ∈ {player, pick, defense, cap_space, unknown}`
        - ✅ not_null: `transaction_date, transaction_id, transaction_year, timeframe_string, player_key`
  - `stg_ktc_assets`
  - ☑ **`stg_ffanalytics__projections`** (NEW - projections staging) ✅ COMPLETE
    - Source: `data/raw/ffanalytics/projections/dt=*/projections_consensus_*.parquet`
    - Player mapping done in R runner (mfl_id already present)
    - Normalize `horizon` enum values ('weekly', 'full_season', 'rest_of_season')
    - Keep real-world stats only (fantasy scoring in marts)
    - **Tests**: 12/12 passing (not_null, relationships, accepted_values)
- ☐ Add **change‑capture** tables:
  - `stg_sleeper_roster_changelog` (stable roster hash)
  - `stg_sheets_change_log` (row hash per tab)
- ☑ **Marts - Track A COMPLETE**:
  - **Core facts** (real-world measures only; 2×2 model base layer):

**Architecture Note (ADR-007):**
v2.2 originally proposed a single `fact_player_stats` table for both actuals and projections. During implementation (documented in refined_data_model_plan_v4.md v4.1 and ADR-007), we split into **separate fact tables** (actuals vs projections) because:

- Actuals have per-game grain (`game_id` required)
- Projections have weekly/season grain (`game_id` meaningless)
- Unified table would require nullable keys (anti-pattern)
- Separate tables eliminate conditional logic and improve clarity

Both facts store `measure_domain='real_world'` only; fantasy scoring applied in marts via `dim_scoring_rule`. See refined_data_model_plan_v4.md § "Addendum: Projections Integration (v4.1)" for full technical specification and [ADR-007](../adr/ADR-007-separate-fact-tables-actuals-vs-projections.md) for decision rationale.

```text
- ☑ **`fact_player_stats`** (COMPLETE ✅ - with player_key solution):
  - Grain: one row per `(player_key, game_id, stat_name, provider, measure_domain, stat_kind)`
  - Sources: UNION ALL of `stg_nflverse__player_stats` + `stg_nflverse__snap_counts` + `stg_nflverse__ff_opportunity`
  - Stat types: 88 total (50 base + 6 snap + 32 opportunity)
  - Current scale: 6.3M rows (6 seasons: 2020-2025), ~220MB
  - Target scale: 12-15M rows (5 years historical + current)
  - Player ID: `mfl_id` (canonical via ADR-010), `player_key` for grain uniqueness
  - stat_kind='actual', measure_domain='real_world'
  - Tests: 19/19 passing (100%) ✅
  - **player_key innovation**: Composite identifier using raw provider IDs as fallback
    - Mapped players: player_key = player_id (mfl_id)
    - Unmapped players: player_key = raw_provider_id (gsis_id or pfr_id)
    - Resolves grain duplicates for unmapped players in same game
- ☑ **`fact_player_projections`** (weekly/season projections from ffanalytics; stat_kind='projection') ✅ COMPLETE
  - Source: `stg_ffanalytics__projections`
  - Grain: one row per player per stat per horizon per asof_date
  - Partitioned by: Not yet (table materialization for now)
  - Incremental on: Future enhancement (asof_date)
  - Includes `horizon` column: 'weekly', 'rest_of_season', 'full_season'
  - No `game_id` (projections are not game-specific per ADR-007)
  - **Stats unpivoted**: 13 stat types (passing, rushing, receiving, turnovers)
  - **Tests**: 8/8 passing (grain uniqueness, not_null, accepted_values)
- `fact_asset_market_values` (KTC players + picks)
- ☑ `fact_league_transactions` (COMPLETE ✅ - commissioner transaction history)
  - Source: `stg_sheets__transactions`
  - Grain: one row per asset per transaction
  - Partitioned by: `transaction_year`
  - Links to: `dim_player`, `dim_pick`, `dim_asset`, `dim_franchise`
```

- **Dimensions**:
  - ☑ `dim_player` (COMPLETE ✅ - from dim_player_id_xref seed)
  - ☑ `dim_team` (COMPLETE ✅ - NFL teams from nflverse)
  - ☑ `dim_schedule` (COMPLETE ✅ - game schedule from nflverse)
  - ☑ `dim_franchise` (COMPLETE ✅ - league team/owner dimension from seed)
  - ☑ **`dim_asset`** (COMPLETE ✅ - UNION of players + picks for trade analysis) **NEW**
- **Analytics marts** (2×2 model - apply fantasy scoring in this layer):

**2×2 Model Implementation:**

```text
                 Real-World Stats              Fantasy Points
                 ────────────────              ──────────────
Actuals          fact_player_stats        →    mart_fantasy_actuals_weekly
                 (per-game grain)              (apply dim_scoring_rule)

Projections      fact_player_projections  →    mart_fantasy_projections
                 (weekly/season grain)         (apply dim_scoring_rule)
```

All base facts (`fact_*`) store real-world measures only. Scoring applied at mart layer via `dim_scoring_rule` (SCD2). This allows scoring rule changes without re-running ingestion.

```text
- Real-world marts:
  - ☑ `mart_real_world_actuals_weekly` (COMPLETE ✅ - nflverse actuals, weekly grain)
  - ☑ **`mart_real_world_projections`** (COMPLETE ✅ - ffanalytics projections, weekly/season grain)
    - Pivots fact_player_projections from long to wide format
    - Grain: one row per player per week per horizon per asof_date
    - 13 stat columns (passing, rushing, receiving, turnovers)
- Fantasy scoring marts (apply `dim_scoring_rule` to real-world base):
  - ☑ `mart_fantasy_actuals_weekly` (COMPLETE ✅ - scored actuals with half-PPR + IDP)
  - ☑ **`mart_fantasy_projections`** (COMPLETE ✅ - scored projections)
    - Applies dim_scoring_rule to mart_real_world_projections
    - Calculates `projected_fantasy_points` using half-PPR scoring
    - Data-driven scoring (same pattern as actuals)
- Analysis marts:
  - ☑ **`mart_projection_variance`** (COMPLETE ✅ - actuals vs projections comparison)
    - Joins mart_real_world_actuals_weekly with mart_real_world_projections
    - Calculates variance (actual - projected) for each stat
    - Grain: one row per player per week (actuals grain)
    - Note: Requires nflverse actuals data to populate
  - `mart_trade_history` (NEW - aggregated trade summaries by franchise)
  - `mart_trade_valuations` (NEW - actual trades vs KTC market comparison)
  - `mart_roster_timeline` (NEW - reconstruct roster state at any point in time)
```

- ☑ **DQ tests - fact_player_stats COMPLETE**: 19/19 passing (100%) ✅
  - ☑ Grain uniqueness: `player_key` + game_id + stat_name + provider + measure_domain + stat_kind (with fantasy position filter)
  - ☑ Referential integrity: player_id → dim_player_id_xref (filtered for mapped players)
  - ☑ Enum tests: season (2020-2025), season_type (REG/POST/WC/DIV/CON/SB/PRE), measure_domain, stat_kind, provider
  - ☑ Not null tests: All grain columns + player_key + position
  - Remaining work: Staging model tests (unique, FK, ranges)
- ☐ Freshness tests: provider‑specific thresholds + LKG banner flags.
- ☑ External Parquet defaults (dbt_project.yml) with partitions; profiles.example.yml using DuckDB httpfs.
- ☐ Ops schema: `ops.run_ledger`, `ops.model_metrics`, `ops.data_quality`.
- ☑ Profiles: support env toggles (e.g., `DBT_TARGET`, `DBT_THREADS`); default local `:memory:`.

SQL style & lint policy (staging vs core)

- ☑ Enforce lowercase keywords/functions/identifiers via SQLFluff.
- ☑ Staging models: ignore `RF04` (keywords as identifiers) and `CV06` (semicolon terminator) to preserve raw‑aligned schemas and dbt ergonomics.
- ☐ Core/marts: consider re‑enabling `RF04` and requiring non‑keyword identifiers (rename/quote) and terminators if desired.
- ☑ Add manual sqlfluff auto‑fix: `sqlfluff-fix` hook (run via `pre-commit run sqlfluff-fix --all-files`).

## 8) CI/CD — Schedules & Jobs

- ☑ Install starter workflow: `.github/workflows/data-pipeline.yml`.
- ☐ Add jobs:
  - **nflverse weekly** (Mon 08:00 UTC) + optional cron overlay for injuries/depth charts.
  - **projections weekly** (Tue 08:00 UTC).
  - **sheets & sleeper** twice daily (08:00 & 16:00 UTC) if desired.
- ☐ Upload build artifacts (logs, `_meta.json`) for traceability.
- ☐ Wire GCS writes and dbt run/test steps using repo secrets; post basic notifications (optional).
  - ☑ Parameterize dbt vars for `external_root` and allow profile selection via env.

Sheets pipeline specifics:

- Order: `copy_league_sheet.py` → `commissioner_parse.py` → dbt run/test (ADR‑005).
- Artifacts: CSV previews and dbt test summary.
- LKG fallback: on parser/API failure, use previous `dt` partition; verify in CI (acceptance).

## 9) Samples & Fixtures

- ☐ Generate minimal fixtures for each dataset and commit to a fixture bucket (or store as CI artifacts):
  - ☑ `PYTHONPATH=. uv run tools/make_samples.py nflverse --datasets players weekly injuries schedule teams --seasons 2024 --weeks 1 --out ./samples`
  - ☑ `uv run tools/make_samples.py sleeper --datasets league users rosters players --league-id 1230330435511275520 --out ./samples`
  - ☑ `uv run tools/make_samples.py sheets --tabs Eric Gordon Joe JP Andy Chip McCreary TJ James Jason Kevin Piper --sheet-url https://docs.google.com/spreadsheets/d/1HktJj-VB5Rc35U6EXQJLwa_h4ytiur6A8QSJGN0tRy0 --out ./samples`
  - ☑ `uv run tools/make_samples.py sheets --tabs TRANSACTIONS --sheet-url <copy-sheet-url> --out ./samples` (WORKING ✅ - sample exists at `samples/sheets/TRANSACTIONS/`; documentation updated)
  - ☐ `python tools/make_samples.py ktc --assets players picks --top-n 50 --out ./samples`
  - ☐ `python tools/make_samples.py ffanalytics --config ... --scoring ... --weeks 1 --out ./samples`
  - ☐ `python tools/make_samples.py sdio --paths <export files> --out ./samples`

Notes:

- Use samples to validate schemas and primary keys; keep samples as raw‑aligned as possible (names/types) to reduce friction in staging.

## 10) Ops & Monitoring (Phase 3)

**v2.2 Requirements (Line 151-157):**

- `ops.run_ledger(run_id, started_at, ended_at, status, trigger, scope, error_class, retry_count)`
- `ops.model_metrics(run_id, model_name, row_count, bytes_written, duration_ms, error_rows?)`
- `ops.data_quality(run_id, model_name, check_name, status, observed_value, threshold)`
- Freshness UX: notebooks banner per source (e.g., `sheets_stale`, `market_stale`)

**Current Status (Phase 3 backlog):**

- ☐ Add ingestion logs & metrics: source version, loader path, as‑of timestamps (from `_meta.json`).
- ☐ Dashboard banners when freshness thresholds breached or LKG in effect.
- ☐ Alerts on schema drift (dbt run failures) and DQ violations.
- ☐ Build ops schema tables: `run_ledger`, `model_metrics`, `data_quality`
- ☐ Implement freshness tests: provider‑specific thresholds + LKG banner flags (v2.2 Line 234)
- ☐ Implement row-delta tests: ± thresholds on `fact_player_stats`, `mart_*_weekly` (v2.2 Line 235)

**Note:** Sheets LKG fallback implemented (Section 4, Line 422); other sources (nflverse, Sleeper, KTC) freshness banners pending.

## 11) Documentation

- ☑ **SPEC v2.3** consolidated doc is present in `docs/spec/`.
- ☑ Link SPEC in README for quick discovery and add badges (Spec, Conventions, CI).
- ☑ **How to Use the Sample Generator** guide present in `docs/dev/`; keep in sync with code.
- ☐ Record **Orchestration & Language Strategy** (Python‑first with R escape hatch) in contributor docs.

## 12) Backfill Strategy

- ☐ Document backfill approach: dt‑based reprocess, idempotent writes, and LKG behavior.
- ☐ Provide scripts to re‑parse raw tabs across a date range and re‑run dbt.

## 13) Compaction Playbook

- ☐ Document compaction strategy for Parquet partitions (monthly job):
  - Consolidate small files; preserve partition invariants
  - Write compaction manifest for audit

## 12) Sheets Copier Core & Script

- ☑ Core copy API added: `src/ingest/sheets/copier.py` (`copy_league_sheet`, `CopyOptions`)
- ☑ `scripts/ingest/copy_league_sheet.py` delegates `copyTo` + paste-values to core; retains rename/metadata/protection/logging
- ☑ Unit test for core using a fake Sheets service: `tests/test_sheets_copier.py`

______________________________________________________________________

## Current Status Snapshot (updated)

- ☑ SPEC v2.3 patch + consolidated doc
- ☑ nflverse shim (Python‑first) + R fallback runner; robust repo root detection
- ☑ ffanalytics raw scrape runner + projections config + site weights mapped
- ☑ Sleeper scoring YAML exported from league
- ☑ `tools/make_samples.py` implemented (nflverse, sleeper, sheets, ffanalytics raw, sdio; ktc stub)
- ☑ Python shim GCS writes via PyArrow FS (+ smoke script)
- ☑ Commissioner Sheet parsing to normalized tables + tests (roster, contracts, picks)
- ☑ **TRANSACTIONS tab parsing** (NEW - blocked by seeds; adds fact_league_transactions)
- ☑ **Projections integration** (NEW - separate fact table; 2×2 model alignment)
  - FFanalytics: weighted aggregation (blocked by seeds for player mapping)
  - fact_player_projections with horizon column
  - Real-world projections → fantasy projections (scoring in marts)
- ☑ KTC: real fetcher integration (replace stub)
- ☑ dbt project (staging + tests; env-path globs; seeds skeleton)
- ☑ CI: starter pipeline (ingest + dbt); lint fixes for workflow shell quoting

______________________________________________________________________

## Open Questions / Inputs Needed

- Final GCS bucket names/prefixes and environment naming (dev/prod).
- Weekly run windows acceptable?
  - Mon 08:00 UTC: nflverse (stats, injuries, depth charts)
  - Tue 08:00 UTC: projections (ffanalytics weighted aggregation)
  - Twice daily (08:00 & 16:00 UTC): sheets + sleeper (if desired)
  - Weekly: KTC market values
- Confirm site list and any caps/floors on weights for projections (currently 8 sources; see Section 6).
- **Provide initial seeds (`dim_*`) and any existing ID crosswalks for validation** — CRITICAL BLOCKER for:
  - TRANSACTIONS parsing (player/pick name → canonical ID mapping)
  - Projections player mapping (FFanalytics player names → canonical player_id)
  - All staging models requiring player identity resolution

______________________________________________________________________

## Sign‑off Criteria

### Phase 1 - Seeds & Samples

**Status:** ✅ **COMPLETE** (6/8 seeds done, 2 optional per Line 26)

**Provider Samplers (Samples Available):**

- ☑ nflverse (players, weekly, injuries, schedule, teams)
- ☑ sleeper (league, users, rosters, players)
- ☑ sheets (GM roster tabs)
- ☑ sheets (TRANSACTIONS tab - NEW; depends on seeds for name resolution)
- ☑ ffanalytics (weighted consensus projections - NEW; depends on seeds for player mapping)
- ☑ ktc (players + picks market values)

**Seeds Created and Validated:**

- ☑ `dim_player_id_xref` (12,133 players, 19 provider IDs; primary key=mfl_id) ✅ **COMPLETE**
- ☑ `dim_franchise` (SCD2 ownership history) ✅ **COMPLETE**
- ☑ `dim_pick` (2012-2030 base draft picks, 5 rounds × 12 teams/year) ✅ **COMPLETE**
- ☑ `dim_scoring_rule` (Half-PPR + IDP, SCD2) ✅ **COMPLETE**
- ☑ `dim_timeframe` (maps TRANSACTIONS strings to season/week/period) ✅ **COMPLETE**
- ☑ `dim_name_alias` (78 alias mappings, 100% coverage) ✅ **COMPLETE**
- ☑ **`dim_league_rules`** (salary cap, roster limits - Type 2 SCD) ✅ **COMPLETE (2025-10-25)**
- ☑ **`dim_rookie_contract_scale`** (rookie contract amounts by draft position) ✅ **COMPLETE (2025-10-25)**
- ☑ **`dim_cut_liability_schedule`** (dead cap percentages by contract year) ✅ **COMPLETE (2025-10-25)**
- ☑ **`dim_rfa_compensation_schedule`** (RFA compensation pick schedule - Type 2 SCD) ✅ **COMPLETE (2025-10-25)**
- ☑ **`dim_position_slot_eligibility`** (roster slot rules by position) ✅ **COMPLETE (2025-10-25)**
- ☐ `stat_dictionary.csv` (OPTIONAL - single provider, not yet needed for multi-provider normalization)

**Derived Dimensions:**

- ☑ **`dim_asset`** (UNION of dim_player + dim_pick; 12,193 rows) ✅ **COMPLETE (2025-10-25)**

**All tracks unblocked:** Phase 1 complete enables TRANSACTIONS parsing (Track B), projections integration (Track D), and KTC fetcher (Track C).

### Phase 2 - Core Models

**Status:** ✅ **ALL TRACKS 100% COMPLETE** (A: NFL Actuals ✅ | B: League Data ✅ | C: Market Data ✅ | D: Projections ✅)

**dbt Build Status:**

- ☑ `dbt seed` - 6 seeds loaded successfully
- ☑ `dbt run` - Core staging + Track A marts building
- ☑ `dbt test` - 19/19 DQ tests passing for fact_player_stats ✅

**Core facts built successfully:**

- ☑ `fact_player_stats` (per-game actuals from nflverse; 6.3M rows, 88 stats) ✅ **Track A COMPLETE**
- ☑ `fact_player_projections` (weekly/season projections from ffanalytics - NEW) - **Track D pending**
- ☑ `fact_league_transactions` (commissioner transaction history - NEW) ✅ **Track B COMPLETE**
- ☑ `fact_asset_market_values` (KTC market valuations) - **Track C Complete**

**Key marts validated:**

- ☑ `mart_real_world_actuals_weekly` ✅ **Track A COMPLETE**
- ☐ `mart_real_world_projections` (NEW) - **Track D pending**
- ☑ `mart_fantasy_actuals_weekly` (scoring applied) ✅ **Track A COMPLETE**
- ☑ `mart_fantasy_projections` (scoring applied - NEW) - **Track D pending**
- ☑ `mart_projection_variance` (NEW) - **Track D pending** (requires projections)
- ☐ `mart_trade_history` (NEW) - **Track B/C pending** (requires KTC for valuations)

### Phase 3 - CI/CD & Operations

- CI schedules run without errors; artifacts uploaded:
  - ☐ nflverse weekly ingest (Mon 08:00 UTC)
  - ☐ Projections weekly ingest (Tue 08:00 UTC)
  - ☐ Sheets + Sleeper twice daily (if configured)
- ops schema operational: `run_ledger`, `model_metrics`, `data_quality`
- LKG fallback tested and functional per source
- Documentation merged; contributors can reproduce samples end‑to‑end with the guide

## Follow-ups — Track A (NFL Actuals)

☑ Load nflverse `teams` and `schedule` datasets in all environments so `dim_team`/`dim_schedule` build consistently
☐ Extend staging and marts with kicking stats (FGM/FGA, XPM/XPA) if in scope; wire to existing `kicking` rules in `dim_scoring_rule`
☐ Clarify defensive tackles semantics to avoid double-counting (e.g., use either `def_tackles_with_assist` or a single assists metric); align scoring rule if needed
☐ Optionally expose weekly team attribution (e.g., `team_id_week`) alongside `current_team` in marts for historical accuracy on trades
☐ Add an explicit `special_teams_td` rule in `dim_scoring_rule` (instead of reusing receiving TD) for clarity
