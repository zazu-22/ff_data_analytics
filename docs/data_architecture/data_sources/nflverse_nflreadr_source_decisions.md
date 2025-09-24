# nflverse via nflreadr/nflreadpy — Source Decisions (v2025-09-24)

**Purpose:** Open NFL datasets (play-by-play, rosters, schedules, snap counts, depth charts, etc.) via nflreadr/nflreadpy.

## Scope & Functions

- Use `load_pbp`, `load_player_stats`, `load_rosters`, `load_schedules`, `load_snap_counts`, `load_depth_charts` (timestamped), and related dictionaries.
- **Injuries:** nflverse injury source ended after 2024; **exclude injuries** until a replacement is selected.

## Update Behavior (per upstream)

- Schedules update every ~5 minutes in-season.
- Rosters daily at ~07:00 UTC.
- Depth charts daily at ~07:00 UTC with **timestamped records** (post‑2024 provider change).
- NGS/FTN player-level weekly stats update overnight ET; snap/advanced stats depend on upstream cadence.

## Cadence & Re-pulls

- Align to **08:00 & 16:00 UTC**; add a **Thursday re-pull** to capture stat corrections.

## Storage & Partitioning

- Raw under `gs://ff-analytics/raw/nflverse_nflreadr/dt=YYYY-MM-DD/` by `dt`.
- Stage under `gs://ff-analytics/stage/nflverse_nflreadr/` with partitions:
  - **Weekly/game facts:** (`season`,`week`) (or by `game_id` where appropriate).
  - **Daily dims:** `asof_date` (rosters, depth charts).
  - **PBP:** partition by `season` and optionally `week` if split.

## IDs & Crosswalk

- Preserve GSIS/GSIS ID, PFR IDs as provided; map to canonical `player_id` via `dim_player_id_xref`.

## Data Quality (dbt tests)

- **Freshness:** weekly facts within 3 days in-season; daily rosters/depth within 2 days.
- **Keys:** uniqueness on canonical keys (e.g., `game_id` unique; (`player_id`,`season`,`week`) unique per table).
- **Row deltas:** guard rails on per-week volume to detect partial loads.
- **Depth charts:** use latest timestamp per team/position to derive an “active” chart per game week.

## dbt Notes

- `source: nflverse.*`, `loaded_at_field=asof_datetime`.
- Add compatibility views if upstream schemas shift; version `_vN` on breaking changes.

## Gaps

- Injury data (2025+) not available via nflverse; evaluate alternatives in a separate ADR.
