# SPEC-1 — Ops, Playbooks & Appendices

## A. dbt-duckdb External Parquet — Configuration

```yaml
# dbt_project.yml (snippets)
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
    +partition_by: ['season','week']
  markets:
    +partition_by: ['asof_date']
    +cluster_by: ['asset_id']           # optional logical clustering
```

```yaml
# profiles.yml
ff_duckdb:
  target: prod
  outputs:
    prod:
      type: duckdb
      path: ":memory:"
      threads: 4
      extensions: [httpfs]
```

## B. Partitioning Strategy & Compaction

- **Facts (weekly/game)**: partition by `season, week`.
- **Daily markets**: partition by `asof_date`.
- **Dims**: small, unpartitioned tables (single Parquet per refresh).
- **Compaction**: monthly job to coalesce partitions to \~128–256 MB row groups.

### Compaction playbook

1. Read partition with projection pushdown (only necessary columns).
2. Re‑write to a temp path with `row_group_size=256MB`.
3. Atomic swap (rename temp → live) and cleanup old shards.

## C. GCS Lifecycle & Storage Classes

- `raw/`: move to **Nearline** after 30 days; optional retention lock to avoid accidental deletes.
- `mart/`: keep **Standard** (interactive reads); compact monthly.
- Historical seasons (≥180 days old): transition to **Coldline**.

## D. Identity Resolution & Aliases

- `dim_player_id_xref`: authoritative provider IDs → `player_id`.
- `dim_name_alias(player_id, alias, source, first_seen_at)` to store fuzzy matches.
- Staging uniqueness guard: enforce `(provider, provider_id)` or `(provider, normalized_name, team, position)` before mapping.

## E. KTC (Dynasty 1QB + Picks) Ingestion

- Parse players and picks separately; normalize to **long** rows.
- `market_scope='dynasty_1qb'`; `asset_type in ('player','pick')`.
- Picks: derive `(season, round, overall?, round_slot, round_type)`.
- Upsert `dim_pick`, ensure `dim_asset` rows, then write `fact_asset_market_values`.

## F. Failure Handling & LKG — Decision Table

| Source      | Retry (1m/2m/5m)          | On Persistent Fail                            | LKG Window | Downstream Behavior                                  |
| ----------- | ------------------------- | --------------------------------------------- | ---------- | ---------------------------------------------------- |
| GoogleSheet | ✅                         | mark partial, skip only sheet‑dependent marts | 1 day      | notebooks banner `sheets_stale=true`                 |
| Sleeper     | ✅ (with backoff & jitter) | partial, use LKG                              | 2 days     | skip trades dependent on latest rosters if >2d stale |
| nflreadpy   | ✅                         | partial, keep last good week                  | n/a        | build unaffected models                              |
| KTC (1QB)   | ✅ (polite)                | partial, use LKG                              | 2 days     | banner `market_stale=true`                           |

## G. Data Quality & Freshness Gates (dbt)

- `accepted_values` on `measure_domain`, `stat_kind`, `horizon`, `market_scope`.
- `fresher_than` macros: KTC `asof_date >= today-2`; Sheets `dt >= today-2`.
- Row‑delta tests (± thresholds) on `fact_player_stats`, `mart_*_weekly`.

## H. Observability

- `ops.run_ledger(run_id, started_at, ended_at, status, trigger, scope, error_class, retry_count)`
- `ops.model_metrics(model_name, run_id, row_count, bytes_written, duration_ms, error_rows?)`
- `ops.data_quality(check_name, status, observed_value, threshold)`
- Weekly health notebook: duration, bytes scanned, rows produced trends; outlier alerts.

## I. Backfill Playbook

- Ingest historical seasons (`--season 2012..2024`) in batches.
- Build dbt models season by season to limit working set.
- Compact and transition old seasons to Coldline.

## J. Legal & ToS Hygiene

- KTC scraped politely; cache and avoid redistribution of full tables.
- Respect rate limits for all providers.

## K. Security & IAM

- Separate service accounts / IAM for `raw`, `mart`, `ops`.
- Rotate Discord webhook quarterly.
- Colab uses secrets; no long‑lived tokens in notebooks.

## L. Notebook UX Conventions

- Top‑cell config: `MARKET_SCOPE='dynasty_1qb'`.
- Freshness banner: per‑source lag from a view over `ops` + marts.
- Convenience views: `vw_trade_value_default` selects 1QB columns by default.

## M. ADRs (Examples)

- **ADR‑001** Canonical stat dictionary (neutral names; provider maps)
- **ADR‑002** Twice‑daily cron (08:00, 16:00 UTC)
- **ADR‑003** Versioning strategy for breaking changes (`_vN` + compat views)

## N. Issue Backlog (Starter)

1. Buckets & IAM: create `ff-analytics` and service accounts; apply lifecycle policies.
2. Ingestors: implement Sheets, Sleeper, nflreadpy, KTC (players+picks 1QB); retries + LKG.
3. dbt project: external Parquet config; sources; stage models; seeds (Half‑PPR + stat map).
4. Core marts: weekly real‑world & fantasy; asset market marts; default views.
5. Ops: run ledger, model metrics, DQ tests; Discord webhook; health notebook.
6. Compaction: monthly job and metrics; partition audits.
7. Notebooks: roster health, waiver, start/sit, trade scenarios with 1QB default.

