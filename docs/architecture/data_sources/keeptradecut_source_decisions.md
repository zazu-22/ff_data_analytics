# KeepTradeCut (Dynasty 1QB + Picks) — Source Decisions (v2025-09-24)

**Market scope:** **1QB default** (league uses 1QB). Collect **players** and **rookie pick** values.

## Scope & Scrape Plan

- Scrape 1QB player rankings and **rookie rankings**; include rank, value, tier, position, team.
- Include **draft picks** separately (round/year/slot where available).

## Access & Politeness

- HTML scrape with **randomized sleeps** and a rotating User-Agent. Respect robots/ToS; minimal impact.
- Failure handling: persist Last-Known-Good (LKG) values if scrape fails.

## Storage & Partitioning

- Raw HTML/CSV under `gs://ff-analytics/raw/keeptradecut/dt=YYYY-MM-DD/` per **`asof_date`**.
- Stage under `gs://ff-analytics/stage/keeptradecut/` with long-form rows:
  - `asset_type ∈ {'player','pick'}`, `market_scope='dynasty_1qb'`, `asof_date`.

## IDs & Crosswalk

- Players identified by site slug/name → resolve to canonical `player_id` via `dim_player_id_xref`/aliases.
- Picks resolved to `dim_pick(season, round, round_slot)`; create/ensure `dim_asset` rows for union views.

## Data Quality (dbt tests)

- **Freshness:** values within 2 days (warn after 2d; error after 4d).
- **Keys:** uniqueness on (`asset_id`,`asof_date`,`market_scope`).
- **Sanity:** ranks monotonic; values non-negative; position in allowed set.

## dbt Notes

- `source: ktc.*`, `loaded_at_field=asof_datetime` (scrape timestamp).
- Write to `fact_asset_market_values` and `mart_market_metrics_daily` per **SPEC**.
