# SPEC-1 — Fantasy Football Analytics Data Architecture (Final)

## Background
Consolidated, dynasty-format fantasy analytics platform with twice‑daily batch refresh, ad‑hoc remote triggers, remote notebooks, and a neutral canonical stats model to mix real‑world and fantasy metrics. Storage in GCS (Parquet), compute via DuckDB, transforms in dbt‑duckdb, orchestration in GitHub Actions, notifications via Discord.

---

## Requirements (MoSCoW)

**Must**
- Twice‑daily schedule (08:00, 16:00 **UTC**), plus manual triggers. All timestamps in **UTC**; notebooks display ET.
- Remote analytics (Colab). Raw immutable snapshots; reproducible transforms with tests.
- Sources: Google Sheet (authoritative), nflreadpy/nflverse, Sleeper, KTC (Dynasty 1QB), injuries/depth charts.
- Canonical IDs; idempotent/ retryable jobs; simple Discord notifications; portability (local ↔ cloud).

**Should**
- Trade valuation marts (players + picks); incremental loads/backfills; DQ reports; partitioning & retention; SCD for rosters/contracts; basic exports; basic cost/usage observability.

**Could**
- Mobile-friendly triggers/read‑only views; ML‑readiness (feature marts + registry hooks); Discord bot.

**Won’t (MVP)**
- Real‑time/streaming game‑time mode; heavy microservices/enterprise warehouse features.

---

## Method

### Architecture (Batch, Cloud‑first, Greenfield)
- **Orchestration**: GitHub Actions (`cron` + `workflow_dispatch`)
- **Compute**: Ephemeral GitHub runners (Python/SQL)
- **Storage**: **GCS** Parquet lake with lifecycle
- **Engine**: **DuckDB** (`httpfs`)
- **Transforms**: **dbt‑duckdb** (external Parquet)
- **Analytics**: Colab notebooks
- **Notifications**: Discord webhook

### dbt‑duckdb — External Parquet Tables (Write Strategy)
- **Default write mode**: all large or append‑heavy marts are **external Parquet tables** in GCS (no persistent `.duckdb` files in CI).
- **Partitioning**: enable partition pruning by default
  - Weekly/game facts → partition by `['season','week']`
  - Daily market tables → partition by `['asof_date']`
  - Small dimensions → unpartitioned (single Parquet per refresh)
- **Project vars**: `vars: { external_root: "gs://ff-analytics/mart" }`
- **Model defaults**: `+materialized: table`, `+external: true` with the partition keys above.
- **Compaction**: monthly coalescing job targeting **128–256 MB** Parquet row groups per partition to minimize GCS request overhead.

### Storage Layout
```
gs://ff-analytics/
  raw/    # dt=YYYY-MM-DD (ingest date)
  stage/  # mirrors source grain (e.g., season/week)
  mart/   # partitioned by season/week or asof_date
  ops/    # run ledger, metrics, data quality
```

### Identity & Conformance
- `dim_player_id_xref` (provider IDs → canonical `player_id`)
- `dim_name_alias` (aliases, source, first_seen_at)
- Separate NFL `team_id` vs league `franchise_id` (seasonal mapping)

### 2×2 Stat Model (Actual/Projected × Real‑world/Fantasy)
- Canonical long store: `fact_player_stats(player_id, season, week, game_id, asof_date, measure_domain, stat_kind, horizon, provider, stat_name, stat_value, sample_size, model_version, provider_stat_name?, stat_unit?, src_hash)`
- Scoring as data: `dim_scoring_rule` (SCD2) enables recomputation under Half‑PPR (`HALF_PPR_SLEExt_2025`).
- Marts: `mart_real_world_actuals_weekly`, `mart_real_world_projections`, `mart_fantasy_actuals_weekly`, `mart_fantasy_projections`.

### Trade Valuation (Players + Picks)
- `dim_pick(season, round, overall?, round_slot, round_type)`
- `dim_asset(asset_type: player|pick, player_id?, pick_id?, display_name)`
- `fact_asset_market_values(asof_date, asset_id, provider, market_scope='dynasty_1qb', horizon='season', stat_name in {trade_value_1qb, trade_rank_1qb, …}, stat_value)`
- Marts: `mart_market_metrics_daily` (players 1QB default), `mart_pick_market_daily` (picks 1QB default), `vw_trade_value_default` (players+picks union, 1QB)

### Data Quality, Lineage, Metadata
- dbt tests (`not_null`, `unique`, `accepted_values`, freshness)
- `ops.run_ledger`, `ops.model_metrics(bytes_written, duration_ms, row_count, error_rows?)`, `ops.data_quality`
- Freshness banner in notebooks (per‑source lag)

### Failure Handling & LKG
- Retries: 1m → 2m → 5m (3 attempts); never overwrite last good raw partition
- On persistent failure: `partial_success`, LKG read; downstream models can `skip` if upstream stale > N days; log HTTP status & retry counts

### Schema Evolution & Versioning
- Additive‑first; breaking → `_vN` path + compatibility view + ADR; deprecate after one season

### Security & IAM
- Least‑privilege GCP SA; separate IAM for `raw`, `mart`, `ops`
- Rotate Discord webhook quarterly; Colab secrets only; optional retention lock for `raw/`

### Cost Controls
- Partition pruning by `season/week` and `asof_date`; avoid tiny files; column pruning in notebooks; lifecycle: `raw/`→Nearline at 30d; historical seasons→Coldline at 180d

### PlantUML (Overview)
```plantuml
@startuml
actor User as U
rectangle "GitHub Actions" as CI
rectangle "GCS Parquet" as GCS
rectangle "DuckDB (httpfs)" as DDB
rectangle "dbt-duckdb" as DBT
rectangle "Colab" as NB
rectangle "Discord" as DC
package "Ingestors" { [sheets] [nflreadpy] [sleeper] [ktc] }
U --> CI : manual trigger
CI --> sheets
CI --> nflreadpy
CI --> sleeper
CI --> ktc
sheets --> GCS
nflreadpy --> GCS
sleeper --> GCS
ktc --> GCS
CI --> DBT
DBT --> DDB
DDB --> GCS
NB --> DDB
CI --> DC
@enduml
```

---

## Core Schemas (selected)
```sql
-- Canonical player IDs (xref)
CREATE TABLE dim_player_id_xref (
  player_id TEXT,
  gsis_id TEXT, sleeper_id TEXT, espn_id TEXT, ktc_id TEXT, pfr_id TEXT,
  nfl_id TEXT, yahoo_id TEXT, cbs_id TEXT,
  PRIMARY KEY (player_id)
);

-- Conformed player dimension (SCD2)
CREATE TABLE dim_player (
  player_sk BIGINT,
  player_id TEXT,
  full_name TEXT, position TEXT, team_id TEXT,
  height_in INT, weight_lb INT, birth_date DATE, age DOUBLE,
  valid_from DATE, valid_to DATE, is_current BOOLEAN,
  src_hash TEXT
);

-- Scoring rules (SCD2)
CREATE TABLE dim_scoring_rule (
  scoring_id TEXT,
  stat_name TEXT,            -- e.g., receptions, rushing_yards
  multiplier DOUBLE,
  applies_to TEXT,           -- position group or 'ALL'
  valid_from DATE, valid_to DATE, is_current BOOLEAN
);

-- Fact: unified long-form stats (supports 2×2 matrix)
CREATE TABLE fact_player_stats (
  player_id TEXT,
  season INT, week INT, game_id TEXT, asof_date DATE,
  measure_domain TEXT,    -- real_world | fantasy
  stat_kind TEXT,         -- actual | projected
  horizon TEXT,           -- game|week|ros|season
  provider TEXT,
  stat_name TEXT,
  stat_value DOUBLE,
  sample_size DOUBLE,
  model_version TEXT,
  src_hash TEXT
);

-- Assets for market values (players and picks)
CREATE TABLE dim_pick (
  pick_id TEXT PRIMARY KEY,
  season INT, round INT, overall INT,
  round_slot TEXT, round_type TEXT, notes TEXT
);

CREATE TABLE dim_asset (
  asset_id TEXT PRIMARY KEY,
  asset_type TEXT CHECK (asset_type in ('player','pick')),
  player_id TEXT, pick_id TEXT,
  display_name TEXT,
  is_active BOOLEAN,
  valid_from DATE, valid_to DATE, is_current BOOLEAN
);

CREATE TABLE fact_asset_market_values (
  asof_date DATE,
  asset_id TEXT,
  provider TEXT,              -- 'ktc'
  market_scope TEXT,          -- 'dynasty_1qb'
  horizon TEXT,               -- 'season'
  stat_name TEXT,             -- trade_value_1qb, trade_rank_1qb, ...
  stat_value DOUBLE,
  model_version TEXT,
  src_hash TEXT
);
```

---

## Implementation

### Repos, Environments, Buckets
```
/ingest/                  # python source connectors
  sheets.py sleeper.py nflreadpy.py ktc.py
/dbt/                     # dbt-duckdb project
  dbt_project.yml
  profiles.yml            # templated; CI fills env vars
  models/
    sources.yml
    stage/*.sql
    marts/core/*.sql
    marts/trade/*.sql
  seeds/
    dim_scoring_rule.csv
    dim_stat_map.csv
    ktc_pick_aliases.csv  # optional
/tests/                   # generic & bespoke tests
/ops/                     # health notebooks + helper scripts
.github/workflows/pipeline.yml
requirements.txt
```
- **Storage**: `gs://ff-analytics/` with `raw/`, `stage/`, `mart/`, `ops/`
- **Colab**: notebooks query `gs://` via DuckDB `httpfs`

### Secrets & Auth (GitHub → env → DuckDB/dbt)
- GitHub Secrets: `GCS_KEY_ID`, `GCS_KEY_SECRET`, `GOOGLE_SA_JSON` (base64), `DISCORD_WEBHOOK`
- Export SA to file at runtime; create DuckDB GCS secret via env (no hardcoding)

### Ingestion (Python — highlights)
- **Google Sheets** → Parquet (`raw/google_sheets/dt=…/…`); LKG on failure
- **Sleeper** → league/roster/transactions; rate‑limit aware; raw snapshots
- **nflreadpy** → weekly, pbp, participation, snaps, nextgen, rankings; raw & partitioned
- **KTC (Dynasty 1QB; players + picks)** → normalize long; upsert `dim_pick` & `dim_asset`; write `fact_asset_market_values`

### dbt sources (external Parquet on GCS — excerpts)
```yaml
version: 2
sources:
  - name: raw
    tables:
      - name: ktc_market
        external:
          location: "gs://ff-analytics/raw/ktc/dt=*/ktc-values.parquet"
          using: parquet
      - name: nfl_weekly
        external:
          location: "gs://ff-analytics/raw/nflreadpy/weekly/season=*/week=*/part-*.parquet"
          using: parquet
      - name: google_sheets_rosters
        external:
          location: "gs://ff-analytics/raw/google_sheets/dt=*/rosters-*.parquet"
          using: parquet
```

### Seeds (initial)
- `dim_scoring_rule.csv`: preset `HALF_PPR_SLEExt_2025` (offensive/K/DEF/IDP)
- `dim_stat_map.csv`: provider→canonical mappings (Sleeper, nflreadpy, KTC players)
- `ktc_pick_aliases.csv` (optional): normalize pick strings → `(season, round, overall|slot)`

### Orchestration (GitHub Actions — excerpt)
```yaml
name: ff-data-pipeline
on:
  schedule:
    - cron: "0 8 * * *"   # 08:00 UTC
    - cron: "0 16 * * *"  # 16:00 UTC
  workflow_dispatch:
    inputs:
      scope: {type: choice, options: [all,sheets,nfl,sleeper,ktc], default: all}
      start_date: {required: false}
      end_date:   {required: false}

jobs:
  run:
    runs-on: ubuntu-latest
    env:
      GCS_KEY_ID: ${{ secrets.GCS_KEY_ID }}
      GCS_KEY_SECRET: ${{ secrets.GCS_KEY_SECRET }}
      GOOGLE_SA_JSON: ${{ secrets.GOOGLE_SA_JSON }}
      DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Decrypt SA & configure DuckDB GCS
        run: |
          echo "$GOOGLE_SA_JSON" | base64 -d > $RUNNER_TEMP/sa.json
          echo "GOOGLE_APPLICATION_CREDENTIALS=$RUNNER_TEMP/sa.json" >> $GITHUB_ENV
      - name: Ingest
        run: python ingest/runner.py --scope "${{ inputs.scope || 'all' }}" --start "${{ inputs.start_date }}" --end "${{ inputs.end_date }}"
      - name: dbt build
        run: |
          dbt deps --project-dir dbt
          dbt build --project-dir dbt --fail-fast
      - name: Post-run metrics & Discord
        run: python ops/post_run.py
```

### Failure Handling & LKG (implementation)
- Retries: 3 attempts @ 60s/120s/300s; mark `partial_success` on persistent failures
- Keep last good partition; expose `*_stale` flags in marts & notebook banners

### Schema Evolution (implementation)
- Additive columns allowed by default; breaking → `_vN` path + compatibility view + ADR + season-long deprecation

---

## Milestones

**M1 – Ingest & Raw Lake**
- Sheets, Sleeper, nflreadpy (weekly/pbp/core), KTC (Dynasty 1QB: players + picks) → `raw/`
- LKG + retries + run ledger

**M2 – dbt Stage & Core Marts**
- Stage models normalize to canonical stats; `dim_player_id_xref`, `dim_player`, scoring seeds
- Core marts: `dim_player (SCD2)`, `fact_player_stats`, weekly real‑world & fantasy marts

**M3 – Trade Valuation (Should)**
- `dim_pick`, `dim_asset`, `fact_asset_market_values`
- `mart_market_metrics_daily` (players), `mart_pick_market_daily` (picks), `vw_trade_value_default`

**M4 – Ops & Observability**
- `ops.*` tables populated per run; Discord summaries; weekly health notebook

**M5 – Colab Analytics Pack**
- Notebooks: roster health, waiver targets, start/sit baselines, trade scenarios (players+picks, 1QB default)

---

## Gathering Results
- Freshness SLAs; twice‑daily success rate; dbt tests green; cost & duration trends healthy; usability validated via notebooks 

