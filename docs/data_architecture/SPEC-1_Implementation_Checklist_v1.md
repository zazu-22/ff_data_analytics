# SPEC‑1 — Implementation Checklist (v1)

<!--toc:start-->

- [SPEC‑1 — Implementation Checklist (v1)](#spec1-implementation-checklist-v1)
  - [0) Pre‑Flight / Decisions](#0-preflight-decisions)
  - [1) Cloud Infra (GCP)](#1-cloud-infra-gcp)
  - [2) Repo Scaffolding](#2-repo-scaffolding)
  - [3) Python Tooling (uv)](#3-python-tooling-uv)
  - [4) DuckDB & dbt Setup](#4-duckdb-dbt-setup)
  - [5) Ingestors (Batch Writers → `raw/`)](#5-ingestors-batch-writers-raw)
  - [6) Secrets & Config](#6-secrets-config)
  - [7) Staging Models (`stage/`)](#7-staging-models-stage)
  - [8) Core Facts & Dims (`mart/`)](#8-core-facts-dims-mart)
  - [9) Ops / Observability (`ops/`)](#9-ops-observability-ops)
  - [10) Data Quality (dbt tests)](#10-data-quality-dbt-tests)
  - [11) Backfills](#11-backfills)
  - [12) Compaction Job (Monthly)](#12-compaction-job-monthly)
  - [13) GitHub Actions](#13-github-actions)
  - [14) Notebooks (Colab‑first UX)](#14-notebooks-colabfirst-ux)
  - [15) Acceptance Criteria (MVP done when…)](#15-acceptance-criteria-mvp-done-when)
  - [16) Cutover & Ops Runbook](#16-cutover-ops-runbook)
  - [17) Nice‑to‑Have (Post‑MVP)](#17-nicetohave-postmvp) - [File Skeleton (Reference)](#file-skeleton-reference)
  <!--toc:end-->

Use this as a step‑by‑step build guide for the consolidated data architecture. Boxes `[ ]` are action items; fill them as you go.

---

## 0) Pre‑Flight / Decisions

- [ ] Confirm **market scope default = Dynasty 1QB**; SF values stored but not defaulted.
- [ ] Confirm **cron**: 08:00 & 16:00 UTC; ad‑hoc via `workflow_dispatch`.
- [ ] Confirm **cloud**: Google Cloud Storage (GCS), project/billing enabled.
- [ ] Pick repo name (e.g., `ff-analytics`); branch strategy (e.g., `main` + PRs).

---

## 1) Cloud Infra (GCP)

- [ ] Create GCP project (or reuse): `ff-analytics`.
- [ ] Enable APIs: [ ] Cloud Storage [ ] IAM [ ] Secret Manager (optional) [ ] Cloud Monitoring (optional).
- [ ] Create GCS buckets (or a single bucket with prefixes):
  - [ ] `gs://ff-analytics/raw/`
  - [ ] `gs://ff-analytics/stage/`
  - [ ] `gs://ff-analytics/mart/`
  - [ ] `gs://ff-analytics/ops/`
- [ ] Apply **lifecycle policies**:
  - [ ] `raw/` → Nearline after 30d; protect from deletes.
  - [ ] `mart/` → Standard; compact monthly.
  - [ ] Historical seasons ≥180d → Coldline.
- [ ] Create **service accounts** / keys (scoped minimal):
  - [ ] `ingestor-runner@` (read/write `raw/`, `stage/`)
  - [ ] `dbt-runner@` (read `raw/`/`stage/`, write `mart/`/`ops/`)
  - [ ] Bind roles: Storage Object Admin (scoped to prefixes).
- [ ] Store secrets (GitHub OIDC or JSON key) for Actions.

---

## 2) Repo Scaffolding

- [ ] Initialize repo

```
mkdir ff-analytics && cd ff-analytics
printf "# ff-analytics
" > README.md
git init && git add . && git commit -m "chore: init"
```

- [ ] Create dirs

```
mkdir -p /ingestors /dbt/{models,macros,tests,analysis,seeds} /notebooks /ops /configs
```

- [ ] Add **LICENSE**, **CODEOWNERS**, **CONTRIBUTING.md** (optional).

---

## 3) Python Tooling (uv)

- [ ] Initialize with **uv**

```
uv init --python 3.11
uv add duckdb==1.* dbt-duckdb==1.* dbt-core==1.* google-cloud-storage==2.* pandas pyarrow python-dotenv httpx tenacity rich pydantic
```

- [ ] Add **dev** extras (optional): `ipykernel black ruff pytest`.
- [ ] Create `.env.example` with required vars (see §6 Secrets).

---

## 4) DuckDB & dbt Setup

- [ ] Create `profiles.yml` (DuckDB in‑memory + httpfs)

```yaml
ff_duckdb:
  target: prod
  outputs:
    prod:
      type: duckdb
      path: ":memory:"
      threads: 4
      extensions: [httpfs]
```

- [ ] Create `dbt_project.yml`

```yaml
name: ff_analytics
version: 1.0
profile: ff_duckdb
config-version: 2
vars:
  external_root: "gs://ff-analytics/mart"
models:
  +materialized: table
  +external: true
  core:
    +partition_by: ["season", "week"]
  markets:
    +partition_by: ["asof_date"]
    +cluster_by: ["asset_id"]
```

- [ ] Add seed files: `seeds/scoring_rules.csv`, `seeds/stat_dictionary.csv`, `seeds/team_franchise_map.csv`.

---

## 5) Ingestors (Batch Writers → `raw/`)

**Common**

- [ ] Create `/ingestors/common/gcs.py` (write Parquet with atomic temp → final).
- [ ] Implement retry/backoff with `tenacity`.
- [ ] Partition path: `raw/source=NAME/dt=YYYY-MM-DD/*.parquet`.

**Google Sheets (Commissioner)**

- [ ] Read via Sheets API or export CSV; persist raw with schema inference.
- [ ] On failure, **LKG** fallback (copy previous partition, set `sheets_stale=true`).

**Sleeper**

- [ ] Endpoints: league, rosters, drafts, transactions; parametrize season/league_id.
- [ ] Rate limit & cache responses; write as normalized Parquet.

**nflreadpy / nflverse**

- [ ] Weekly game/player stats; injuries/depth charts if available.
- [ ] Write long‑form tables keyed by `(season, week, game_id, player_id)`.

**KTC (Players + Rookie Picks, 1QB)**

- [ ] Fetch market tables for `players` and `picks`; include `asof_date`.
- [ ] Normalize to long rows with `asset_type in ('player','pick')` and `market_scope='dynasty_1qb'`.

---

## 6) Secrets & Config

- [ ] `.env` keys:
  - [ ] `GCP_PROJECT`, `GCS_BUCKET=ff-analytics`
  - [ ] `GCP_CREDENTIALS_JSON` (or OIDC in Actions)
  - [ ] `SHEETS_CREDENTIALS_JSON` (if using API)
  - [ ] `LEAGUE_ID=1230330435511275520`
  - [ ] `DISCORD_WEBHOOK_URL`
  - [ ] `MARKET_SCOPE=dynasty_1qb`
- [ ] Add `configs/runtime.yaml` with toggles (e.g., `sources.enabled`, `backfill: true/false`).

---

## 7) Staging Models (`stage/`)

- [ ] `stg_player_id_xref.sql` — map provider IDs → canonical `player_id`.
- [ ] `stg_dim_name_alias.sql` — alias table with `first_seen_at`.
- [ ] `stg_team_map.sql` — NFL `team_id` ↔ league `franchise_id`.
- [ ] Enforce uniqueness guards on `(provider, provider_id)`.

---

## 8) Core Facts & Dims (`mart/`)

- [ ] `dim_player.sql`, `dim_team.sql`, `dim_franchise.sql`, `dim_pick.sql`, `dim_asset.sql`.
- [ ] `fact_player_stats.sql` (long store; neutral stat names).
- [ ] `dim_scoring_rule.sql` (SCD2 from seeds).
- [ ] Quadrant marts:
  - [ ] `mart_real_world_actuals_weekly.sql`
  - [ ] `mart_real_world_projections.sql`
  - [ ] `mart_fantasy_actuals_weekly.sql`
  - [ ] `mart_fantasy_projections.sql`
- [ ] Market value marts (1QB default):
  - [ ] `mart_market_metrics_daily.sql` (players)
  - [ ] `mart_pick_market_daily.sql` (picks)
  - [ ] `vw_trade_value_default.sql` (union players+picks)

---

## 9) Ops / Observability (`ops/`)

- [ ] `ops.run_ledger` table; log `run_id`, times, trigger, status.
- [ ] `ops.model_metrics`; row counts, bytes, durations.
- [ ] `ops.data_quality`; test outcomes with thresholds.
- [ ] Discord notifier script; include freshness summary and row deltas.

---

## 10) Data Quality (dbt tests)

- [ ] Accepted values on enums: `measure_domain`, `stat_kind`, `horizon`, `market_scope`.
- [ ] Freshness windows: KTC `asof_date >= today-2`; Sheets `dt >= today-2`.
- [ ] Uniqueness keys for dims; non‑null critical FKs.
- [ ] Row‑delta checks on weekly marts (± thresholds seasonally tuned).

---

## 11) Backfills

- [ ] Implement CLI flags `--season 2012..2024` for ingestors.
- [ ] Run staged backfills (season batches) to control working set size.
- [ ] After each batch: run dbt, validate DQ, compact older partitions, transition to Coldline.

---

## 12) Compaction Job (Monthly)

- [ ] Create `ops/compact_parquet.py`:
  - [ ] Read partition with projection pushdown.
  - [ ] Write temp files targeting **128–256 MB** row groups.
  - [ ] Atomic swap; delete small files.
- [ ] Emit metrics to `ops.model_metrics`.

---

## 13) GitHub Actions

- [ ] Workflow: `.github/workflows/pipeline.yml`

```yaml
name: pipeline
on:
  schedule:
    - cron: "0 8 * * *"
    - cron: "0 16 * * *"
  workflow_dispatch:
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv sync
      - name: Configure GCP creds
        run: |
          echo "$GCP_CREDENTIALS_JSON" > /tmp/gcp.json
          export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp.json
      - name: Ingest sources
        run: uv run python -m ingestors.run --since today
      - name: dbt build
        run: uv run dbt build --project-dir dbt --profiles-dir .
      - name: Notify
        run: uv run python ops/notify_discord.py
```

- [ ] Add repository **secrets**: `GCP_CREDENTIALS_JSON`, `DISCORD_WEBHOOK_URL`, etc.

---

## 14) Notebooks (Colab‑first UX)

- [ ] `notebooks/_config.ipynb` — sets `MARKET_SCOPE='dynasty_1qb'`, connects DuckDB httpfs, points to `gs://ff-analytics/mart`.
- [ ] `notebooks/roster_health.ipynb` — league freshness banners + roster deltas.
- [ ] `notebooks/trade_scenarios.ipynb` — pulls `vw_trade_value_default` (players+picks).
- [ ] `notebooks/start_sit.ipynb` — weekly projections vs opponent.

---

## 15) Acceptance Criteria (MVP done when…)

- [ ] Two consecutive cron runs succeed and write to `raw/`, `stage/`, `mart/`, `ops/`.
- [ ] DQ tests pass with no critical failures.
- [ ] `vw_trade_value_default` returns rows with both players and picks for current date.
- [ ] Notebooks render freshness banners; no manual local files required.

---

## 16) Cutover & Ops Runbook

- [ ] Document LKG policies by source and the `*_stale` flags.
- [ ] Quarterly webhook rotation; annual secrets audit.
- [ ] Add ADRs to `/docs/adr`:
  - [ ] ADR‑001 Stat dictionary
  - [ ] ADR‑002 Cron schedule
  - [ ] ADR‑003 Breaking change versioning

---

## 17) Nice‑to‑Have (Post‑MVP)

- [ ] Discord bot for ad‑hoc triggers & summaries.
- [ ] Simple Streamlit/Dash read‑only UI over marts.
- [ ] Feature‑registry prep: per‑player per‑week feature table.

---

### File Skeleton (Reference)

```
ff-analytics/
  ingestors/
    run.py
    common/gcs.py
    sheets.py
    sleeper.py
    nflverse.py
    ktc.py
  dbt/
    dbt_project.yml
    models/
      core/*.sql
      markets/*.sql
      ops/*.sql
    seeds/
      scoring_rules.csv
      stat_dictionary.csv
      team_franchise_map.csv
  notebooks/
    _config.ipynb
    roster_health.ipynb
    trade_scenarios.ipynb
    start_sit.ipynb
  ops/
    compact_parquet.py
    notify_discord.py
  .github/workflows/pipeline.yml
  .env.example
  README.md
```
