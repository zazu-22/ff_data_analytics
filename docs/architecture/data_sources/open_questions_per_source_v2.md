# Open Questions & Info Needed Per Source

Below are the outstanding questions, decisions, or missing details to finalize each source’s ingestion and documentation. Answering these will let us lock schemas, dbt sources, and schedules.

______________________________________________________________________

## Sleeper API — Resolutions

- League scope: **current league** (from `league_data.json`) and **current season only**.
- Endpoints: league_data, players, roster_data, user_data.
- Contracts: maintained in Google Sheets only.
- Historical backfill: **No**.
- Rate limits: **reasonable**; use polite throttle and retries.
- IDs: use Sleeper `player_id`; map via crosswalk.
- Change capture: daily snapshot + hash-based roster changelog.
- Tests: light set (freshness, uniqueness, not_nulls, roster count, player_id format, starters length).

______________________________________________________________________

## Google Sheets — Commissioner SSoT

- **Sheet URL & tabs:** Confirm the URL and the exact tab names in scope (transactions, rosters, contracts, cut_contracts, draft_assets, cap, trade_conditions).
- **Tab schemas:** Define column sets (names, types, required/optional) and validations for each tab.
- **Write policy:** Are tabs append-only or fully editable? Do we maintain a “frozen export” for reproducibility?
- **Service account access:** Has the SA been shared with the Sheet? (confirm email & perms)
- **Backfill:** Do we import the entire sheet each run or incremental changes only?
- **Golden sources:** Which fields in Sheets override external sources (e.g., contract $/yrs)?
- **DQ gates:** Required checks (e.g., cap never negative, contract years in \[1..X\], roster count in bounds).
- **Release notes:** How do managers communicate schema changes (e.g., add column → update registry)?

## SportsDataIO Discovery Lab (NFL)

- **Plan & entitlements:** Which endpoints are available in our subscription? (actuals, projections, injuries, depth charts, etc.)
- **Endpoint list:** Enumerate concrete endpoints + parameters (seasons, weeks, teams, players) for v1.
- **Rate limits & quotas:** Practical per-minute/per-day caps; required backoff.
- **Time coverage:** Start season (2022) to current — confirm completeness and postseason coverage.
- **Projection variants:** Which projection sets (rest-of-season, weekly, seasonal) are required?
- **Identifiers:** Which ID systems are present and how we map to our crosswalk?
- **Pagination & volume:** Typical payload sizes; partitioning strategy (season/week/date).
- **Licensing/ToS:** Redistribution constraints; what can be stored and shared internally.
- **Dictionary:** Validate alignment with `sdio_fantasydata-nflv3-data-dictionary.csv` (any gaps?).

## Fantasy Football Analytics (R)

- **Functions in scope:** Which reference functions do we rely on for projections/risk (floors/ceilings/SD)?
- **Scoring settings:** Confirm league scoring profile to parameterize functions.
- **Update cadence:** Desired refresh (daily in-season? weekly off-season? pre-kickoff re-runs?).
- **Data origins:** For each scraped source, confirm ToS and reproducibility (are mirrors or caches allowed?).
- **Licensing:** Any non-commercial restrictions we must heed; redistribution rules.
- **Outputs:** Required tables (weekly/seasonal projections, raw stats, risk metrics). CSV vs Parquet.
- **IDs:** Which identifiers are present; crosswalk coverage required.
- **Validation:** Sanity checks vs other sources (z-scores, outlier filters).

## KeepTradeCut (Dynasty Market Values)

- **Format:** 1QB vs Superflex default? Include TE premium? Target which ladders (overall, rookie, positions)?
- **Picks:** Do we also scrape draft pick values (by round/year)? Separate table?
- **Scrape scope:** Specific URLs/filters to scrape; pagination approach.
- **Anti-bot:** User-agent, randomized sleeps; failure handling & LKG policy.
- **Normalization:** Desired columns (player_id, position, team, value, rank, delta, tier, timestamp).
- **Licensing/ToS:** Confirm scraping is permitted or define a minimal-impact approach.
- **Freshness:** Cadence and times of day with least churn/noise; weekend behavior.
- **Crosswalk:** Strategy for mapping KTC players/picks to our unified IDs.

## nflverse via nflreadr

- **Functions:** Exact list to use (e.g., `load_pbp`, `load_player_stats`, `load_rosters`, `load_schedules`, `load_snap_counts`, `load_ftn_charting`, `load_depth_charts`).
- **Timing:** Respect nightly updates + intra-day schedules; add a Thursday re-pull for stat corrections.
- **Depth charts:** Post-2024 timestamp model (no week); how to version and select the “active” chart per game week.
- **Injuries:** 2025 data gap — do we supplement via another source?
- **Partitions:** Preferred partitioning per dataset (season/week/date) and retention policy.
- **Identifiers:** Confirm canonical IDs and crosswalk coverage.
- **dbt tests:** Freshness thresholds and key constraints per table (unique game_id, etc.).

______________________________________________________________________

## Cross-cutting

- **Player ID crosswalk:** What’s our authoritative mapping and where does it live? Update workflow?
- **Timezones & stamps:** Use UTC for ingestion timestamps; retain source-local when provided.
- **Backfills:** Policy for historical backfills and reprocesses (naming, idempotency).
- **Data quality:** Minimum tests per category; row-delta monitors; schema-change detection.
- **Access control:** Who can read raw vs stage; any PII concerns in Sheets.
- **Cost controls:** Caps on daily API calls; pruning policy for raw partitions.
