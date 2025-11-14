{{
    config(
        materialized="table",
        unique_key="defense_id"
    )
}}
/*
NFL Team Defense Crosswalk - Maps defense player_ids to team abbreviations and name variations.

Grain: One row per team defense (32 current + 4 historical = 36 total)

Purpose: Enable mapping of FFAnalytics DST projections to canonical player_id values.
         Supports multiple name formats from various projection providers.

Defense ID Strategy:
    - Range: 90001-90036 (defense_id)
    - Rationale: Clear separation from individual player_ids (1-9757, growing to ~28K max)
    - Consistent with ADR-011 sequential surrogate key pattern
    - Prevents collision with player ID growth
    - Natural sort order: players (1-89999), defenses (90000+)

Source: seed_team_defense_xref.csv (version-controlled source of truth)

Related:
    - ADR-011: Sequential Surrogate Key for player_id
    - P1-028: Add DST team defense seed for FFAnalytics mapping
    - src/ff_analytics_utils/defense_xref.py: Python accessor
*/
select
    defense_id,
    team_abbrev,
    team_name_primary,
    team_name_alias_1,
    team_name_alias_2,
    team_name_alias_3,
    team_name_alias_4,
    position_primary,
    position_alias_1,
    position_alias_2,
    position_alias_3
from {{ ref('seed_team_defense_xref') }}
