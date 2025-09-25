# SportsDataIO Discovery Lab (NFL) — Source Decisions (v2025-09-24)

**Scope:** NFL actuals & projections (2022 → current). **Output:** JSON → Parquet.

## Scope & Endpoints

- Initial endpoints: seasonal/weekly **stats (actuals)**, **projections**, **depth charts**, **injuries** (if entitled), **teams/players** dictionaries.
- Parameterization by `season`, `week` (where applicable). Persist postseason when available.

## Access & Quotas

- Access via API key stored in CI secrets (never commit). Respect per-minute/day quotas with jittered retries.
- Capture `asof_datetime` (UTC) and request metadata (endpoint, params, status).

## Storage & Partitioning

- Raw snapshots under `gs://ff-analytics/raw/sdio_discovery_lab/dt=YYYY-MM-DD/`; one file per endpoint+param set.
- Stage normalized tables under `gs://ff-analytics/stage/sdio_discovery_lab/` with partitioning:
  - **Weekly facts:** partition by (`season`, `week`).
  - **Daily rosters/depth/injuries:** partition by `asof_date`.
  - **Dimensions (players/teams):** unpartitioned small tables (full refresh).

## IDs & Crosswalk

- Prefer native **SportsDataIO PlayerID/TeamID**; add to `dim_player_id_xref` (map to canonical ID, GSIS, PFR where available).

## Data Quality (dbt tests)

- **Freshness:** weekly facts within 3 days in-season.
- **Keys:** uniqueness on endpoint-specific natural keys (e.g., `game_id, player_id, season, week`).
- **Types & Ranges:** numeric stats ≥ 0; snap counts in [0, 100%].
- **Row deltas:** guard rails on weekly volume swings (±30% typical).

## dbt Notes

- `source: sdio.*`, `loaded_at_field=asof_datetime`.
- Stage models mirror each endpoint; marts feed **projections** and **player-model features**.

## Legal / ToS

- Internal storage for personal analysis; no redistribution of vendor data beyond our team. Follow license limits.

## Freshness & LKG

- On 429/5xx use exponential backoff; if persistent, publish **LKG** partition and set `market_stale=true` flag.
