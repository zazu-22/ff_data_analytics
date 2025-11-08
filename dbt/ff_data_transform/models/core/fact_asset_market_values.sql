{{
    config(
        materialized="table",
        indexes=[
            {"columns": ["player_id"]},
            {"columns": ["asset_type"]},
            {"columns": ["market_scope"]},
            {"columns": ["asof_date"]},
            {"columns": ["player_key", "market_scope", "asof_date"]},
        ],
    )
}}

/*
KTC dynasty market values fact table - time-series of asset valuations.

Grain: One row per asset per market_scope per asof_date
Sources: stg_ktc_assets
Architecture: Snapshot fact table (Kimball) - periodic snapshots of market values

This table tracks crowdsourced dynasty market values from KeepTradeCut across time.
Values represent community consensus on asset worth in dynasty leagues.

Asset Types:
- player: Active NFL players and rookies
- pick: Future draft picks (2025-2028, Early/Mid/Late, rounds 1-5)

Market Scopes:
- dynasty_1qb: Standard 1-QB dynasty league format
- dynasty_superflex: Superflex (2-QB) dynasty league format

Key Design Decisions:
- Degenerate dimensions: asset_type, market_scope, provider (no separate dimension tables)
- Player mapping: Uses player_key for grain (handles unmapped players via name fallback)
- Time-series: asof_date enables historical trend analysis
- Denormalized: Includes asset_name, position for convenience

Grain Example Rows:
player_key='12345', market_scope='dynasty_1qb', asof_date='2025-10-25' → Ja'Marr Chase value on this date
player_key='2027 Early 1st', market_scope='dynasty_1qb', asof_date='2025-10-25' → 2027 1st round pick value

Composite Key: (player_key, market_scope, asof_date)

Data Attribution: Market values sourced from KeepTradeCut (https://keeptradecut.com/dynasty-rankings)
per their content usage guidelines.
*/
select
    -- Composite grain key
    player_key,  -- Identity key (canonical player_id when mapped, provider fallback otherwise)
    market_scope,  -- dynasty_1qb or dynasty_superflex
    asof_date,  -- Snapshot date

    -- Degenerate dimensions
    asset_type,  -- player or pick
    provider,  -- 'keeptradecut'

    -- Asset identity
    asset_name,  -- Player name or pick name
    position,  -- QB/RB/WR/TE/K (null for picks)
    current_team,  -- NFL team code (null for picks)

    -- Player dimension FK (null for picks or unmapped players)
    player_id,  -- FK to dim_player_id_xref (when mapped)

    -- Pick attributes (null for players)
    pick_name,  -- e.g., "2027 Early 1st"
    draft_year,  -- e.g., 2027
    pick_tier,  -- Early/Mid/Late
    pick_round,  -- 1-5

    -- Market value measures
    overall_rank,  -- Overall rank across all assets in this market_scope
    ktc_value,  -- KTC value score (0-10000 scale)
    positional_rank,  -- Rank within position (null for picks)

    -- Metadata
    loaded_at

from {{ ref("stg_ktc_assets") }}
