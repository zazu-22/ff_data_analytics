# Bell Keg League — Phase Next Implementation Checklist (v2.2)

A pragmatic, step‑by‑step list to stand up the data pipeline with our latest decisions (SPEC v2.2), nflverse Python shim, R runners, projections config, and sample generator. Use this to coordinate work across the team.

Legend: ☐ todo · ☑ done/verified · (owner) · (notes)

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

## 1) Cloud Paths & Secrets

- ☑ Confirm GCS bucket/prefix: `gs://ff-analytics/{raw,stage,mart}` (bucket created with lifecycle policies).
- ☑ Configure CI secrets:
  - `GOOGLE_APPLICATION_CREDENTIALS_JSON` (service account key configured).
  - `GCP_PROJECT_ID`, `GCS_BUCKET`, `SLEEPER_LEAGUE_ID`, `COMMISSIONER_SHEET_URL` (all configured).
  - `SPORTS_DATA_IO_API_KEY` (configured as optional).
- ☑ Validate service account access to GCS (verified with test workflow).
- ☑ Validate service account access to Commissioner Sheet (

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
- ☑ Extend `ingest/nflverse/registry.py` if we add datasets (injuries, depth_charts, teams, etc.)
  - Registry already includes: players, weekly, season, injuries, depth_charts, schedule, teams
  - Tested: injuries (5599 records), teams (768 records)

## 3) Sleeper — Minimal Ingest Checks

- ☑ Run samples: `uv run tools/make_samples.py sleeper --datasets league users rosters players --league-id 1230330435511275520 --out ./samples`
  - Fixed duplicate column issue (renamed index to sleeper_player_id)
- ☑ Confirm fields exist for contracts/cap linkage (IDs, roster slots, player IDs).
  - Key fields present: owner_id, roster_id, players, starters
- ☑ Validate row counts ~ league expectations (12 teams; starters per roster rules).
  - Confirmed: 12 rosters, 13 users (co-owners), league ID matches

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
- ☐ Parse raw commissioner sheets into logical tables:
  - Note: Raw sheets contain multiple embedded tables (Active Roster, Cut Contracts, Draft Picks, Trade Contingencies)
  - Need to extract and normalize into staging-ready formats: `contracts`, `rosters`, `cap`, `draft_assets`, `trade_conditions`
  - Include owner/GM metadata from each tab
  - Consider creating `scripts/ingest/parse_commissioner_sheets.py` or similar
- ☐ Verify natural keys per tab (unique per date partition) and numeric domains (cap ≥ 0, years 1..5, etc.).

## 5) KeepTradeCut — Replace Sampler Stub

- ☐ Implement real KTC fetcher (players + picks) respecting ToS and polite rate limits (randomized sleeps, caching).
- ☐ Update `tools/make_samples.py::sample_ktc` to call actual fetcher; keep `--top-n` sampling to limit size.
- ☐ Normalize to long‑form `asset_type ∈ {player,pick}` with `asof_date`, `rank`, `value`.
- [ ] Export small samples from the KTC fetcher

## 6) FFanalytics — Wire Runner (R) to Real Projections

- ☐ Edit `scripts/R/ffanalytics_run.R` to call `ffanalytics::getProjections(...)` with sites from `config/projections/ffanalytics_projections_config.yaml` (ids + weights) and scoring from `config/scoring/sleeper_scoring_rules.yaml`.
- ☐ Ensure output long‑form schema: `player, position, team, season, week, projected_points, site_id, site_weight, generated_at`.
- ☐ Smoke test via tool: `uv run python tools/make_samples.py ffanalytics --config ... --scoring ... --weeks 1 --positions QB RB WR TE --sites fantasypros numberfire --out ./samples`
- ☐ Document any site ID/name mapping adjustments discovered during wiring.

## 7) dbt — Seeds, Staging, and Marts

- ☐ Create/refresh **seeds**: `dim_player_id_xref`, `dim_name_alias`, `dim_pick`, `dim_asset`, `dim_scoring_rule`, and **neutral stat dictionary** from nflreadr dictionaries.
- ☐ Stage models per provider:
  - `stg_nflverse_*` (players, weekly, season, injuries, depth_charts, schedule, teams)
  - `stg_sleeper_*` (league, users, rosters, roster_players)
  - `stg_sheets_*` (contracts, rosters, cap, draft_assets, trade_conditions)
  - `stg_ktc_assets`, `stg_ffanalytics_projections`
- ☐ Add **change‑capture** tables:
  - `stg_sleeper_roster_changelog` (stable roster hash)
  - `stg_sheets_change_log` (row hash per tab)
- ☐ Marts:
  - `fact_asset_market_values` (KTC players + picks)
  - `fact_player_projections` (FFanalytics)
  - `dim_player`, `dim_team`, `dim_schedule` (nflverse)
- ☐ DQ tests: uniqueness, referential integrity to canonical IDs, numeric ranges, enumerations.
- ☐ Freshness tests: provider‑specific thresholds + LKG banner flags.

## 8) CI/CD — Schedules & Jobs

- ☐ Install starter workflow: `.github/workflows/data-pipeline.yml`.
- ☐ Add jobs:
  - **nflverse weekly** (Mon 08:00 UTC) + optional cron overlay for injuries/depth charts.
  - **projections weekly** (Tue 08:00 UTC).
  - **sheets & sleeper** twice daily (08:00 & 16:00 UTC) if desired.
- ☐ Upload build artifacts (logs, `_meta.json`) for traceability.

## 9) Samples & Fixtures

- ☐ Generate minimal fixtures for each dataset and commit to a fixture bucket (or store as CI artifacts):
  - ☑ `PYTHONPATH=. uv run tools/make_samples.py nflverse --datasets players weekly injuries schedule teams --seasons 2024 --weeks 1 --out ./samples`
  - ☑ `uv run tools/make_samples.py sleeper --datasets league users rosters players --league-id 1230330435511275520 --out ./samples`
  - ☑ `uv run tools/make_samples.py sheets --tabs Eric Gordon Joe JP Andy Chip McCreary TJ James Jason Kevin Piper --sheet-url https://docs.google.com/spreadsheets/d/1HktJj-VB5Rc35U6EXQJLwa_h4ytiur6A8QSJGN0tRy0 --out ./samples`
  - ☐ `python tools/make_samples.py ktc --assets players picks --top-n 50 --out ./samples`
  - ☐ `python tools/make_samples.py ffanalytics --config ... --scoring ... --weeks 1 --out ./samples`
  - ☐ `python tools/make_samples.py sdio --paths <export files> --out ./samples`

## 10) Ops & Monitoring

- ☐ Add ingestion logs & metrics: source version, loader path, as‑of timestamps (from `_meta.json`).
- ☐ Dashboard banners when freshness thresholds breached or LKG in effect.
- ☐ Alerts on schema drift (dbt run failures) and DQ violations.

## 11) Documentation

- ☐ Commit **SPEC v2.2** (consolidated) to `docs/spec/` and link in README.
- ☐ Add **How to Use the Sample Generator** guide to `docs/dev/` and keep in sync with code.
- ☐ Record **Orchestration & Language Strategy** (Python‑first with R escape hatch) in contributor docs.

______________________________________________________________________

## Current Status Snapshot (as of v2.2 handoff)

- ☑ SPEC v2.2 patch + consolidated doc
- ☑ nflverse shim (Python) + R fallback runner (stubs ready)
- ☑ ffanalytics runner (stub) + projections YAML + site weights mapped (sites‑only)
- ☑ Sleeper scoring YAML exported from league
- ☑ `tools/make_samples.py` implemented with provider subcommands
- ☐ KTC: real fetcher integration (replace stub)
- ☐ FFanalytics: wire real `getProjections(...)` and outputs
- ☐ Seeds/dbt staging/marts/tests to finalize
- ☐ CI schedules & secrets finalized

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
