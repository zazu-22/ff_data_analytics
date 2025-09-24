# Google Sheets — Commissioner SSoT — Source Decisions (v2025-09-24)

**Canonical?** Yes (commissioner-managed). **Scope tabs:** `transactions`, `rosters`, `contracts`, `cut_contracts`, `draft_assets`, `cap`, `trade_conditions`.

## Scope & Access

- Treat the Google Sheet as **authoritative** for contracts, cap, draft assets, and commissioner adjustments.
- Access via a **service account** (read-only). Store credentials in CI secrets; **do not** embed keys in code.
- Write policy: Tabs are **editable** by managers; ingestion is **read-only**. We produce a **frozen daily export** for reproducibility.

## Change Capture & Storage

- **Daily raw snapshot** per twice-daily schedule (08:00 & 16:00 UTC): write each tab as Parquet under `gs://ff-analytics/raw/google_sheets_commissioner/dt=YYYY-MM-DD/`.
- Stage normalized tables under `gs://ff-analytics/stage/google_sheets_commissioner/`; include `asof_datetime` (UTC) and `dt` partition.
- Maintain `stg_sheets_change_log` for contract and roster-affecting changes (hash rows by natural keys).

## IDs & Crosswalk

- Player identity via name + team + position → map to canonical `player_id` using `dim_player_id_xref` and `dim_name_alias` guards.
- League franchise identifiers (manager/owner) are maintained as `franchise_id` separate from NFL `team_id`.

## Data Quality (dbt tests)

- **Freshness:** `asof_datetime` within 1 day (warn) / 2 days (error).
- **Contracts:** `years` ∈ {1,2,3,4,5}; dollar amounts whole ≥ 0; proration conforms to policy.
- **Cap:** `cap_remaining` ≥ 0 at team level.
- **Rosters:** Active counts within league limits; taxi/IR rules respected.
- **Keys:** tab-specific natural keys unique per `dt`.
- **Overrides:** Fields in Sheets override external sources for contracts/cap.

## dbt Notes

- `source: sheets.google_commissioner_*`, `loaded_at_field=asof_datetime`.
- Models: `stg_sheets_contracts`, `stg_sheets_rosters`, `stg_sheets_cap`, `stg_sheets_draft_assets`, `stg_sheets_trade_conditions`.
- Downstream marts derive **legal-state views** for rules enforcement.

## Freshness & LKG

- On API/auth failures, use **Last-Known-Good** (previous partition) and set `sheets_stale=true` in ops freshness banners.

## Security & Audit

- Principle of least privilege for SA.
- Daily frozen exports enable historical audits and backtesting.
