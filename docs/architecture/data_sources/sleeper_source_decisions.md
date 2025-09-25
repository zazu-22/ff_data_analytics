# Sleeper API — Source Decisions (v20250924)

**League:** 1230330435511275520 — **Season:** 2025 — **Total Rosters:** 12

## Scope & Endpoints

- In-scope endpoints (initial): **league_data**, **players**, **roster_data**, **user_data**.
- Contracts are **not** stored in Sleeper; the Google Sheets SSoT is authoritative for contracts.
- Historical backfill: **No** (current season only). Keep daily raw snapshots for auditability.

## Access & Rate Limiting

- Use official REST endpoints (see docs) or lightweight wrapper: `dtsong/sleeper-api-wrapper`.
- Set a polite throttle (e.g., 5 req/sec with jitter) and a retry policy (3x exponential backoff).
- Capture `asof_datetime` in UTC for every fetch.

## Change Capture Strategy (recommended)

- **Daily raw snapshot**: Save full JSON responses under `raw/sleeper_api/dt=YYYY-MM-DD/`.
- **Lightweight change log** in staging:
  - Compute a stable hash per **roster** (sorted players + starters + reserve + taxi + owner_id).
  - Compare to **prior partition**; emit `change_type` ∈ {'insert','update','delete','no_change'}.
  - Materialize `stg_sleeper_roster_changelog` with fields:
    - `league_id`, `roster_id`, `owner_id`, `hash_current`, `hash_prev`, `change_type`, `asof_date`.
  - Keep **latest-active** table for downstream joins (`is_current = true` via window).

## Minimal Data Quality Tests (lightweight)

- **Freshness**: `asof_datetime` within **1 day** (warn after 1d, error after 2d).
- **Uniqueness**: (`league_id`, `roster_id`, `asof_date`) unique in staging.
- **Not nulls**: `league_id`, `roster_id`, `owner_id` not null.
- **Cardinality sanity**: number of active `roster_id` values per day == **12**.
- **Player ID format**: `players[*]` must be string digits (regex `^\d+$`) or valid team codes for DEF.
- **Starters length**: `len(starters)` equals number of starter slots implied by `roster_positions` (ignore `BN`/`TAXI`).

## IDs & Crosswalk

- Canonical key from Sleeper: **`player_id`** (string).
- Crosswalk to unified IDs occurs in staging via `dim_player_xwalk` (Sleeper → gsis_id/pfr_id/sportradar_id).

## Storage & Paths

- Raw: `gs://ff-analytics/raw/sleeper_api/dt=YYYY-MM-DD/` (gzip JSON).
- Stage: `gs://ff-analytics/stage/sleeper_api/` with typed, exploded records for rosters, players, users.

## dbt Notes

- Define `source: league.sleeper_api_*` with `loaded_at_field=asof_datetime` and above tests.
- Create:
  - `stg_sleeper_rosters` (one row per `league_id` + `roster_id` per as-of date).
  - `stg_sleeper_roster_players` (explode `players` arrays).
  - `stg_sleeper_roster_changelog` (per strategy above).
  - `snap_sleeper_league_settings` for scoring & roster_positions (rarely changes; keep latest+history).

## Open Items

- None for initial scope; add transactions/matchups/draft endpoints later if needed.
