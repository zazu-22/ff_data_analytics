{{ config(materialized="table", unique_key=['franchise_id', 'player_key', 'obligation_year', 'snapshot_date']) }}

/*
Contract snapshot mart - historical point-in-time contract obligations (commissioner sheet snapshots).

Grain: One row per player per franchise per snapshot date per obligation year
Source: stg_sheets__contracts_active (direct from commissioner's CONTRACTS_ACTIVE sheet)

This mart provides a point-in-time historical view of contract obligations as recorded
in the commissioner's CONTRACTS_ACTIVE sheet at various snapshot dates. This enables:
- Time-series analysis of how obligations changed over time
- Validation of transaction-derived contracts (mart_contract_snapshot_current)
- Historical cap space reconstruction
- Trend analysis of contract structures

Key Differences from mart_contract_snapshot_current:
- Uses direct commissioner sheet snapshots (not derived from transaction log)
- Includes snapshot_date as grain component (enables time-series)
- Shows obligations as commissioner recorded them at each point in time
- May include manual corrections not yet in transaction log

Use Cases:
- Historical cap space: What were my obligations as of Aug 1, 2024?
- Validation: Does transaction-derived view match latest snapshot?
- Trend analysis: How has Player X's value evolved over time?
- Commissioner audit: Track changes between snapshot dates

Grain Example Rows:
player_id=12345, franchise_id=F001, snapshot_date=2024-08-01, obligation_year=2025 → Snapshot 1
player_id=12345, franchise_id=F001, snapshot_date=2024-09-15, obligation_year=2025 → Snapshot 2
player_id=12345, franchise_id=F001, snapshot_date=2024-09-15, obligation_year=2026 → Snapshot 2
*/
with
    base as (select * from {{ ref("stg_sheets__contracts_active") }}),

    with_gm_tab as (
        select b.*, fran.gm_tab
        from base b
        left join
            {{ ref("dim_franchise") }} fran
            on b.franchise_id = fran.franchise_id
            and b.obligation_year between fran.season_start and fran.season_end
    )

select
    -- Grain columns (composite natural key)
    player_id,
    franchise_id,
    snapshot_date,
    obligation_year,

    -- Player attributes (denormalized)
    player_name,
    canonical_name,  -- From crosswalk
    roster_slot,  -- Roster slot (FLEX, BN, IR, TAXI, or starter position)

    -- Franchise attributes
    franchise_name,
    owner_name,
    gm_full_name,
    gm_tab,

    -- Year-specific measures
    cap_hit,  -- Annual obligation for this year

    -- Contract attributes (from source sheet)
    rfa,  -- RFA status flag
    franchise as franchise_tag,  -- Franchise tag flag

    -- Composite identifier (for unmapped players)
    player_key,

    -- Validation flags
    is_unmapped_player,  -- Player not in crosswalk
    is_unmapped_franchise,  -- Franchise not resolved

    -- Snapshot metadata
    snapshot_year,

    -- Metadata
    current_timestamp as loaded_at

from with_gm_tab
order by snapshot_date desc, player_name asc, obligation_year asc
