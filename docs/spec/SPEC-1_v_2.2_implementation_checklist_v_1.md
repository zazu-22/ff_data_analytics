# Bell Keg League — Phase Next Implementation Checklist (v2.2)

A pragmatic, step‑by‑step list to stand up the data pipeline with our latest decisions (SPEC v2.2), nflverse Python shim, R runners, projections config, and sample generator. Use this to coordinate work across the team.

Legend: ☐ todo · ☑ done/verified · (owner) · (notes)

Updated: 2025-09-29 — reflects current repo status and a sequenced plan. Note: one key objective of the sample generators is to keep schemas aligned with raw provider structures so we can refine and lock contracts before dbt modeling.

______________________________________________________________________

## 0) Repo Prep & Version Pins

- ☑ Confirm repo tree matches SPEC paths:
  - `ingest/nflverse/registry.py`, `ingest/nflverse/shim.py` ☑
  - `scripts/R/nflverse_load.R`, `scripts/R/ffanalytics_run.R` ☑
  - `config/projections/ffanalytics_projections_config.yaml`, `config/projections/ffanalytics_projection_weights_mapped.csv` ☑
  - `config/scoring/sleeper_scoring_rules.yaml` ☑
  - `tools/make_samples.py` ☑
  - `docs/spec/SPEC-1_Consolidated_v2.2.md` (+ patch & change log) ☑ (named SPEC-1_v_2.2.md)
- ☑ Add `uv.lock` pinning: `polars (>=0.20)`, `pyarrow (>=15)`, `pandas`, `nflreadpy`. (polars 1.33.1, pyarrow 21.0.0, pandas 2.3.2, nflreadpy 0.1.3)
- ☑ Add `renv.lock` pinning: `nflreadr (>=1.5.0)`, `arrow`, `jsonlite`, `yaml`, `optparse`, `lubridate`, `remotes`, `ffanalytics` (GitHub), plus `digest`.
- ☑ Commit files and open PR "SPEC v2.2 integration". (Committed directly to main)

### Recommended Sequencing (High‑Level)

1. Populate dbt seeds (player xref, aliases, picks/assets, scoring rules, neutral stat dictionary).
1. Sheets: add dbt sources + staging (with SCD change tracking) for commissioner tables.
1. CI (Sheets): copy_league_sheet → commissioner_parse → dbt run/test, with CSV previews + dbt summary and LKG fallback.
1. Implement KTC fetcher (players + picks; cache/throttle) and update samples.
1. Projections: weighted aggregation per config + apply scoring rules, output long‑form.
1. Core marts + ops (run ledger, model metrics, data quality) and freshness banners.
1. Change‑capture staging models (roster/sheets change logs) and compaction playbook docs.

### 0a) Conventions & Structure

- ☑ Document repository conventions and layout (`docs/dev/repo_conventions_and_structure.md`).
- ☐ Align existing files to conventions (naming, placement):
  - Scripts named `verb_noun.py` under a domain folder
  - Ensure ingest shims stay in `ingest/<provider>/`; reusable helpers live in `src/ff_analytics_utils/`
  - Confirm data folders mirror cloud layout (`data/{raw,stage,mart,ops}` for local dev)
  - Add `dbt/ff_analytics/` scaffold with `models/{sources,staging,core,markets,ops}`
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

Normalization policy and dbt expectations:

- Long‑form normalization in parser for Sheets (semi‑structured) to simplify dbt:
  - `contracts_active(gm, player, position, year, amount, rfa, franchise)`
  - `contracts_cut(gm, player, position, year, dead_cap_amount)`
  - `draft_picks(gm, year, round, source_type, original_owner, acquired_from, acquisition_note, condition_flag)`
  - `draft_pick_conditions(gm, year, round, condition_text)`

## 5) KeepTradeCut — Replace Sampler Stub

- ☐ Implement real KTC fetcher (players + picks) respecting ToS and polite rate limits (randomized sleeps, caching).
- ☐ Update `tools/make_samples.py::sample_ktc` to call actual fetcher; keep `--top-n` sampling to limit size.
- ☐ Normalize to long‑form `asset_type ∈ {player,pick}` with `asof_date`, `rank`, `value`.
- ☐ Write Parquet to `data/raw/ktc/{players,picks}/dt=YYYY-MM-DD/` with `_meta.json`
- ☐ Export small samples from the KTC fetcher

Acceptance criteria:

- Contract test: `asset_type ∈ {player,pick}`, `market_scope='dynasty_1qb'`, values ≥ 0, `asof_date` present.
- Cache + throttle with randomized sleeps; backoff on errors.
- Samples updated to use real client.

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

Next step (scoring and weighted aggregation):

- ☐ Weighted aggregation per config/weights (site weights in projections config).
- ☐ Apply `sleeper_scoring_rules.yaml` to produce fantasy points.
- ☐ Output canonical long‑form with `measure_domain=fantasy`, `stat_kind=projection`.

Acceptance criteria:

- Deterministic long‑form output; staging validates presence and value ranges.

## 7) dbt — Seeds, Staging, and Marts

- ☑ Scaffold dbt project structure under `dbt/ff_analytics/` with external Parquet defaults.
- ☐ Create/refresh **seeds**: `dim_player_id_xref`, `dim_name_alias`, `dim_pick`, `dim_asset`, `dim_scoring_rule`, and **neutral stat dictionary** from nflreadr dictionaries.
- ☐ Stage models per provider:
  - `stg_nflverse_*` (players, weekly, season, injuries, depth_charts, schedule, teams)
    - ☑ `stg_nflverse__players.sql` reading local `data/raw` Parquet (tests: not_null + unique `gsis_id`)
    - ☑ `stg_nflverse__weekly.sql` with PK tests: not_null (`season`,`week`,`gsis_id`) + singular uniqueness test on key
  - `stg_sleeper_*` (league, users, rosters, roster_players)
  - `stg_sheets_*` (contracts_active, contracts_cut, draft_picks, draft_pick_conditions)
    - ☐ Add `stg_sheets__roster_changelog` (hash-based SCD tracking)
    - ☐ Add `stg_sheets__change_log` (row hash per tab/dt)
    - ☐ Tests:
      - unique: `contracts_active (gm,player,year)`, `contracts_cut (gm,player,year)`, `draft_picks (gm,year,round)`
      - FK: `contracts_cut (gm,player,year) → contracts_active (gm,player,year)` (when present)
      - FK: `draft_pick_conditions (gm,year,round) → draft_picks (gm,year,round)`
      - not_null and numeric ranges (amounts ≥ 0), enumerations on `source_type`
  - `stg_ktc_assets`, `stg_ffanalytics_projections`
- ☐ Add **change‑capture** tables:
  - `stg_sleeper_roster_changelog` (stable roster hash)
  - `stg_sheets_change_log` (row hash per tab)
- ☐ Marts:
  - `fact_player_stats` (long‑form; actuals + projections compatible)
  - `fact_asset_market_values` (KTC players + picks)
  - `fact_player_projections` (FFanalytics)
  - Fantasy scoring marts (weekly actuals, projections) using scoring seeds
  - `dim_player`, `dim_team`, `dim_schedule` (nflverse)
- ☐ DQ tests: uniqueness, referential integrity to canonical IDs, numeric ranges, enumerations.
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
  - ☐ `python tools/make_samples.py ktc --assets players picks --top-n 50 --out ./samples`
  - ☐ `python tools/make_samples.py ffanalytics --config ... --scoring ... --weeks 1 --out ./samples`
  - ☐ `python tools/make_samples.py sdio --paths <export files> --out ./samples`

Notes:

- Use samples to validate schemas and primary keys; keep samples as raw‑aligned as possible (names/types) to reduce friction in staging.

## 10) Ops & Monitoring

- ☐ Add ingestion logs & metrics: source version, loader path, as‑of timestamps (from `_meta.json`).
- ☐ Dashboard banners when freshness thresholds breached or LKG in effect.
- ☐ Alerts on schema drift (dbt run failures) and DQ violations.

ops schema details:

- `ops.run_ledger` captures `asof_datetime`, `loader_path`, `source_version` from `_meta.json`.
- Freshness banner UX per notebook conventions.

## 11) Documentation

- ☑ **SPEC v2.2** consolidated doc is present in `docs/spec/`.
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

- ☑ SPEC v2.2 patch + consolidated doc
- ☑ nflverse shim (Python‑first) + R fallback runner; robust repo root detection
- ☑ ffanalytics raw scrape runner + projections config + site weights mapped
- ☑ Sleeper scoring YAML exported from league
- ☑ `tools/make_samples.py` implemented (nflverse, sleeper, sheets, ffanalytics raw, sdio; ktc stub)
- ☑ Python shim GCS writes via PyArrow FS (+ smoke script)
- ☑ Commissioner Sheet parsing to normalized tables + tests
- ☐ KTC: real fetcher integration (replace stub)
- ☐ Projections: weighted aggregation + scoring outputs (scaffold present)
- ☑ dbt project (staging + tests; env-path globs; seeds skeleton)
- ☑ CI: starter pipeline (ingest + dbt); lint fixes for workflow shell quoting

______________________________________________________________________

## Open Questions / Inputs Needed

- Final GCS bucket names/prefixes and environment naming (dev/prod).
- Weekly run windows acceptable? (Mon nflverse; Tue projections)
- Confirm site list and any caps/floors on weights for projections.
- Provide initial seeds (`dim_*`) and any existing ID crosswalks for validation.

______________________________________________________________________

## Sign‑off Criteria

- All provider samplers produce non‑empty sample files (CSV + Parquet + `_meta.json`).
- dbt passes: `dbt seed`, `dbt run` (staging + marts), `dbt test` (DQ & freshness) on samples.
- CI schedules run without errors; artifacts uploaded.
- Documentation merged; contributors can reproduce samples end‑to‑end with the guide.
