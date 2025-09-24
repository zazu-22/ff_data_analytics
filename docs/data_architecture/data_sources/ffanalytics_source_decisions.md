# Fantasy Football Analytics (R) — Source Decisions (v2025-09-24)

**Purpose:** Aggregate multi-source projections + risk metrics using the **ffanalytics** R ecosystem.

## Scope & Outputs

- Functions in scope: projections (weekly/seasonal), raw stat projections, **risk/volatility** metrics.
- Scoring: parameterize to **Half-PPR** with our league rules; export both **fantasy points** and **underlying raw** projections.
- Outputs (tables):
  - `proj_weekly (season, week, player_id, provider, fpts, fpts_floor, fpts_ceil, sd, ... )`
  - `proj_seasonal (season, player_id, ...)`
  - `proj_raw_weekly/raw_seasonal` (yards, targets, etc.)

## Execution & Cadence

- Run via R script in CI aligned to **08:00 & 16:00 UTC** during season; **weekly** in offseason.
- Re-run on Sunday morning (ET) as needed for late updates (manual `workflow_dispatch`).

## Storage & Partitioning

- Raw exports (CSV/Parquet) under `gs://ff-analytics/raw/ffanalytics/dt=YYYY-MM-DD/` grouped by `asof_date`.
- Stage under `gs://ff-analytics/stage/ffanalytics/`; projections partition by (`season`, `week`) + `asof_date` for versioning.

## IDs & Crosswalk

- Source sites may use names → use robust name normalization + `dim_name_alias` to map to canonical `player_id`.
- Persist original source name / site for lineage.

## Data Quality (dbt tests)

- **Freshness:** `asof_date` within 2 days in-season.
- **Keys:** uniqueness on (`season`,`week`,`player_id`,`provider`).
- **Sanity:** fpts within reasonable bounds; floors ≤ means ≤ ceilings; SD ≥ 0.

## Legal / ToS

- Respect each scraped/downloaded site's usage policy. Cache results; avoid heavy scraping.

## dbt Notes

- `source: ffa.*`, `loaded_at_field=asof_datetime` (use export timestamp).
- Marts feed **player value models** and **trade simulators**.
