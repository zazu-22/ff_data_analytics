{% macro resolve_player_id_from_name(
    source_cte,
    player_name_col='player_name_canonical',
    position_context_col='position',
    context_type='position'
) %}
  {#
  Resolve player_id from player name using position-aware disambiguation.

  This macro standardizes player_id resolution across all sheets staging models,
  ensuring consistent disambiguation logic when multiple players share the same name
  (e.g., Josh Allen QB vs Josh Allen DB, Byron Young DT vs Byron Young DE).

  The macro uses a cascading waterfall approach:
    1. Exact/fuzzy name match from dim_player_id_xref with position scoring
    2. Fallback to transaction history (fct_league_transactions)
    3. Tiebreaker: MAX(player_id) prefers active/newer players

  Args:
    source_cte: Name of CTE containing player data to resolve
    player_name_col: Column name containing normalized player name (default: 'player_name_canonical')
    position_context_col: Column name containing position info (default: 'position')
    context_type: Type of position context - 'position' or 'roster_slot' (default: 'position')

  Returns:
    CTE with player_id, mfl_id, and canonical_name columns added

  Usage Examples:

    -- For transactions (position context)
    with_player_id as (
      {{ resolve_player_id_from_name(
          source_cte='with_alias',
          player_name_col='player_name_canonical',
          position_context_col='position',
          context_type='position'
      ) }}
    )

    -- For contracts_active (roster_slot context)
    with_player_id as (
      {{ resolve_player_id_from_name(
          source_cte='with_defense',
          player_name_col='player_name_canonical',
          position_context_col='roster_slot',
          context_type='roster_slot'
      ) }}
    )

  Position Scoring Logic:
    - Exact position match: 100 points
    - Compatible positions (DL → DE/DT): 80-90 points
    - Generic/flexible slots (BN, TAXI): 25-75 points
    - Retired player penalty: 0 points
    - Tiebreaker: MAX(player_id) for newest/active player

  Why This Approach:
    - Centralizes disambiguation logic (single source of truth)
    - Ensures consistent player_id resolution across all sheets models
    - Eliminates parser-level resolution (keeps raw data raw)
    - Leverages dbt's compile-time flexibility for different position contexts
  #}

  transaction_player_ids as (
    -- Fallback: Get player_id from transaction history (optional)
    -- NOTE: Only use this for non-transaction models (contracts_active, contracts_cut)
    --       to avoid circular dependencies. For transactions, crosswalk is the only source.
    -- IMPORTANT: Deduplicate to prevent fan-out when same player has multiple positions
    -- in transaction history (e.g., Jaelan Phillips as LB/DL)
    {% if source_cte != 'with_alias' %}
      select
        lower(trim(player_name)) as player_name_lower,
        player_id,
        position
      from {{ ref("fct_league_transactions") }}
      where asset_type = 'player' and player_id is not null
      qualify row_number() over (partition by player_id order by transaction_date desc) = 1
    {% else %}
      -- Empty CTE for transactions model (no fallback to avoid cycle)
      select
        cast(null as varchar) as player_name_lower,
        cast(null as bigint) as player_id,
        cast(null as varchar) as position
      where 1=0
    {% endif %}
  ),

  crosswalk_candidates as (
    -- Get all potential matches from dim_player_id_xref with position filtering
    select
      src.{{ player_name_col }},
      src.{{ position_context_col }},
      xref.player_id,
      xref.mfl_id,
      xref.name,
      xref.position,

      -- Position match scoring based on context_type
      {% if context_type == 'roster_slot' %}
        {# Roster slot scoring (for contracts_active) #}
        case
          -- Active player check (exclude retired players)
          when xref.draft_year < extract(year from current_date) - 15
          then 0

          -- Position-specific roster slots
          when src.{{ position_context_col }} = 'QB' and xref.position = 'QB' then 100
          when src.{{ position_context_col }} = 'RB' and xref.position = 'RB' then 100
          when src.{{ position_context_col }} = 'WR' and xref.position = 'WR' then 100
          when src.{{ position_context_col }} = 'TE' and xref.position = 'TE' then 100
          when src.{{ position_context_col }} = 'K' and xref.position in ('K', 'PK') then 100

          -- FLEX must be RB/WR/TE
          when src.{{ position_context_col }} = 'FLEX' and xref.position in ('RB', 'WR', 'TE') then 90

          -- IDP roster slots
          when src.{{ position_context_col }} = 'IDP BN' and xref.position in ('DB', 'LB', 'DL', 'DE', 'DT', 'CB', 'S') then 80
          when src.{{ position_context_col }} = 'IDP TAXI' and xref.position in ('DB', 'LB', 'DL', 'DE', 'DT', 'CB', 'S') then 80
          when src.{{ position_context_col }} = 'DB' and xref.position in ('DB', 'CB', 'S', 'WR') then 100
          when src.{{ position_context_col }} = 'DL' and xref.position in ('DL', 'DE', 'DT', 'LB') then 100
          when src.{{ position_context_col }} = 'LB' and xref.position in ('LB', 'DL', 'DE', 'DT') then 100

          -- BN, TAXI, IR can be any position - prefer offensive
          when src.{{ position_context_col }} in ('BN', 'TAXI', 'IR') and xref.position in ('QB', 'RB', 'WR', 'TE', 'K') then 50
          when src.{{ position_context_col }} in ('BN', 'TAXI', 'IR') then 25

          else 0
        end as match_score
      {% elif context_type == 'position' %}
        {# Generic position scoring (for transactions, contracts_cut) #}
        case
          -- Exact position match
          when src.{{ position_context_col }} = xref.position then 100

          -- Kicker position mapping (K in sheets → PK in crosswalk)
          when src.{{ position_context_col }} = 'K' and xref.position in ('K', 'PK') then 100

          -- Multi-position players (e.g., WR/DB for Travis Hunter)
          when src.{{ position_context_col }} like '%/%' and (
            xref.position = split_part(src.{{ position_context_col }}, '/', 1)
            or xref.position = split_part(src.{{ position_context_col }}, '/', 2)
          ) then 100

          -- Generic defensive positions map to specific ones (with dual-eligibility)
          when src.{{ position_context_col }} = 'DL' and xref.position in ('DL', 'DE', 'DT', 'LB') then 90
          when src.{{ position_context_col }} = 'DB' and xref.position in ('DB', 'CB', 'S') then 90
          when src.{{ position_context_col }} = 'LB' and xref.position in ('LB', 'DL', 'DE', 'DT') then 90

          -- Active player check (exclude retired players)
          when xref.draft_year < extract(year from current_date) - 15 then 0

          else 0
        end as match_score
      {% else %}
        {{ exceptions.raise_compiler_error("Invalid context_type '" ~ context_type ~ "'. Must be 'position' or 'roster_slot'") }}
      {% endif %}

    from {{ source_cte }} src
    left join
      {{ ref("dim_player_id_xref") }} xref
      on (
        lower(trim(src.{{ player_name_col }})) = lower(trim(xref.name))
        or lower(trim(src.{{ player_name_col }})) = lower(trim(xref.merge_name))
      )
  ),

  best_crosswalk_match as (
    -- Select best match per player using cascading tiebreakers
    select
      {{ player_name_col }},
      {{ position_context_col }},
      -- Use MAX(player_id) as final tiebreaker (newer/younger/active player)
      cast(max(player_id) as bigint) as player_id,
      cast(max(mfl_id) as bigint) as mfl_id,
      max(name) as canonical_name
    from crosswalk_candidates
    where match_score > 0
    group by {{ player_name_col }}, {{ position_context_col }}
    qualify row_number() over (
      partition by {{ player_name_col }}, {{ position_context_col }}
      order by max(match_score) desc
    ) = 1
  ),

  distinct_players as (
    -- Get unique (player_name_canonical, position) combinations from source
    -- This prevents cartesian products in the lookup join
    select distinct
      {{ player_name_col }},
      {{ position_context_col }}
    from {{ source_cte }}
  ),

  with_player_id_lookup as (
    -- Join to get player_id from crosswalk and transaction fallback
    -- Uses distinct_players (not source_cte) to ensure 1:1 joins
    select
      dp.{{ player_name_col }},
      dp.{{ position_context_col }},
      -- Cascading player_id resolution:
      -- 1. Crosswalk (canonical from dim_player_id_xref)
      -- 2. Transaction history (fallback, may have stale IDs)
      coalesce(cast(xwalk.player_id as bigint), cast(txn.player_id as bigint)) as player_id,
      cast(xwalk.mfl_id as bigint) as mfl_id,
      cast(xwalk.canonical_name as varchar) as canonical_name

    from distinct_players dp
    left join
      best_crosswalk_match xwalk
      on dp.{{ player_name_col }} = xwalk.{{ player_name_col }}
      and dp.{{ position_context_col }} = xwalk.{{ position_context_col }}
    left join
      transaction_player_ids txn
      on lower(trim(dp.{{ player_name_col }})) = txn.player_name_lower
      {% if context_type == 'roster_slot' %}
        {# For roster_slot, add position filtering to prevent duplicate rows #}
        and (
          -- Exact position match
          (dp.{{ position_context_col }} = txn.position)
          -- FLEX can be RB/WR/TE
          or (dp.{{ position_context_col }} = 'FLEX' and txn.position in ('RB', 'WR', 'TE'))
          -- IDP slots must be defensive
          or (
            dp.{{ position_context_col }} in ('IDP BN', 'IDP TAXI')
            and txn.position in ('DB', 'LB', 'DL', 'DE', 'DT', 'CB', 'S')
          )
          or (dp.{{ position_context_col }} = 'DB' and txn.position in ('DB', 'CB', 'S'))
          or (dp.{{ position_context_col }} = 'DL' and txn.position in ('DL', 'DE', 'DT'))
          or (dp.{{ position_context_col }} = 'LB' and txn.position = 'LB')
          -- BN, TAXI, IR match any position (no filter)
          or dp.{{ position_context_col }} in ('BN', 'TAXI', 'IR')
        )
      {% elif context_type == 'position' %}
        {# For generic position, simpler filtering #}
        and (
          dp.{{ position_context_col }} = txn.position
          or (dp.{{ position_context_col }} = 'DL' and txn.position in ('DL', 'DE', 'DT'))
          or (dp.{{ position_context_col }} = 'DB' and txn.position in ('DB', 'CB', 'S'))
        )
      {% endif %}
  )

{% endmacro %}
