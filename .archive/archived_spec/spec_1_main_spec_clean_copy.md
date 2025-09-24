# SPEC-1 — Fantasy Football Analytics Data Architecture (Main Spec)

## Background

Consolidated, dynasty-format fantasy analytics platform with daily batch refresh, ad‑hoc remote triggers, remote notebooks, and a neutral canonical stats model to mix real‑world and fantasy metrics. Storage in GCS (Parquet), compute via DuckDB, transforms in dbt‑duckdb, orchestration in GitHub Actions, notifications via Discord.

## Requirements (MoSCoW)

**Must**

- Twice‑daily schedule (08:00, 16:00 **UTC**), plus manual triggers. All timestamps stored in **UTC**; notebooks display ET.
- Remote analytics (Colab). Raw immutable snapshots; reproducible transforms with tests.
- Sources: Google Sheet (authoritative), nflreadpy/nflverse, Sleeper, KTC (Dynasty 1QB), injuries/depth charts.
- Canonical IDs; idempotent/ retryable jobs; simple Discord notifications; portability (local ↔ cloud).

**Should**

- Trade valuation marts (players + picks); incremental loads/backfills; DQ reports; partitioning & retention; SCD for rosters/contracts; basic exports; basic cost/usage observability.

**Could**

- Mobile-friendly triggers/read‑only views; ML‑readiness (feature marts + registry hooks); Discord bot.

**Won’t (MVP)**

- Real‑time/streaming game‑time mode; heavy microservices/enterprise warehouse features.

## Method

### Architecture

- **Orchestration**: GitHub Actions (cron + workflow\_dispatch)
- **Storage**: **GCS** Parquet lake with lifecycle
- **Engine**: **DuckDB** (`httpfs`)
- **Transforms**: **dbt‑duckdb** (external Parquet tables)
- **Analytics**: Colab notebooks
- **Notifications**: Discord webhook

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
- `dim_name_alias` (aliases, source, first\_seen\_at)
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

### dbt‑duckdb — External Parquet Tables

- Project vars: `vars: { external_root: "gs://ff-analytics/mart" }`
- Model defaults: `+materialized: table`, `+external: true`, `+partition_by`: weekly facts → `['season','week']`; markets → `['asof_date']`
- Row‑group target \~128–256 MB; monthly **compaction** job to coalesce small files.

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

- Least‑privilege GCP SA; separate IAM for `raw/`, `mart/`, `ops/`
- Rotate Discord webhook quarterly; Colab secrets only; optional retention lock for `raw/`

### Cost Controls

- Partition pruning by `season/week` and `asof_date`; avoid tiny files; column pruning in notebooks; lifecycle: `raw/`→Nearline at 30d; historical seasons to Coldline at 180d

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

## Implementation Highlights

- GitHub Actions: cron `0 8 * * *` and `0 16 * * *`; `workflow_dispatch` with scope filters
- Secrets: `GCS_KEY_ID`, `GCS_KEY_SECRET`, `GOOGLE_SA_JSON(base64)`, `DISCORD_WEBHOOK`
- Ingestors: Google Sheets (LKG fallback), Sleeper (rate‑limit aware), nflreadpy (weekly/pbp/NGS/snaps/participation/rankings), KTC (Dynasty 1QB players + picks)
- dbt sources: external Parquet on `gs://` for raw; marts write external Parquet with partitions

## Milestones

- **M1 Raw Lake**: all sources to `raw/` with retries + LKG + ledger
- **M2 Stage & Core Marts**: canonical stats normalization; dims/facts; Half‑PPR seed
- **M3 Trade Valuation**: assets (players+picks) marts + default views
- **M4 Ops & Observability**: ops tables, Discord summaries, weekly health notebook
- **M5 Colab Pack**: roster health, waiver, start/sit baselines, trade scenarios (1QB default)

## Gathering Results

- Freshness SLAs; twice‑daily success rate; dbt tests green; cost & duration trends healthy; usability validated via notebooks

