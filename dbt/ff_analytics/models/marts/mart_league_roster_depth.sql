{{
  config(
    materialized='table'
  )
}}

/*
League Roster Depth - rank all rostered players for VoR analysis.

Grain: franchise_id, player_key, asof_date
Purpose: Provide league-wide context for FA target evaluation
*/

with current_rosters as (
  select
    c.franchise_id,
    c.player_id as player_key,
    d.display_name as player_name,
    d.position,
    c.cap_hit
  from {{ ref('stg_sheets__contracts_active') }} c
  inner join {{ ref('dim_player') }} d on c.player_id = d.player_id
  where
    c.obligation_year = YEAR(CURRENT_DATE)
    and d.position in ('QB', 'RB', 'WR', 'TE')
),

projections_ros as (
  select
    player_id as player_key,
    AVG(projected_fantasy_points) as projected_ppg_ros,
    SUM(projected_fantasy_points) as projected_total_ros,
    COUNT(*) as weeks_remaining
  from {{ ref('mart_fantasy_projections') }}
  where
    season = YEAR(CURRENT_DATE)
    and week > (
      select MAX(week)
      from {{ ref('dim_schedule') }}
      where
        season = YEAR(CURRENT_DATE)
        and CAST(game_date as DATE) < CURRENT_DATE
    )
    and horizon = 'weekly'
  group by player_id
),

position_rankings as (
  select
    r.franchise_id,
    r.player_key,
    r.player_name,
    r.position,
    r.cap_hit,
    COALESCE(p.projected_ppg_ros, 0.0) as projected_ppg_ros,
    COALESCE(p.projected_total_ros, 0.0) as projected_total_ros,

    -- Rank within franchise (depth chart)
    ROW_NUMBER() over (
      partition by r.franchise_id, r.position
      order by COALESCE(p.projected_ppg_ros, 0.0) desc
    ) as team_depth_rank,

    -- Rank across entire league
    ROW_NUMBER() over (
      partition by r.position
      order by COALESCE(p.projected_ppg_ros, 0.0) desc
    ) as league_rank_at_position,

    -- Count of rostered players at position
    COUNT(*) over (partition by r.position) as total_rostered_at_position,

    -- Percentile within position
    PERCENT_RANK() over (
      partition by r.position
      order by COALESCE(p.projected_ppg_ros, 0.0) desc
    ) as league_percentile_at_position

  from current_rosters r
  left join projections_ros p on r.player_key = p.player_key
),

position_benchmarks as (
-- Calculate key benchmarks for each position
  select
    position,

    -- Starter benchmarks (top players per league rules)
    PERCENTILE_CONT(0.5) within group (order by projected_ppg_ros desc) filter (where league_rank_at_position <= 12)
      as median_starter_ppg,
    PERCENTILE_CONT(0.25) within group (order by projected_ppg_ros desc) filter (where league_rank_at_position <= 12)
      as weak_starter_ppg,

    -- FLEX benchmarks (next tier of RB/WR/TE)
    PERCENTILE_CONT(0.5) within group (order by projected_ppg_ros desc) filter (
      where league_rank_at_position between 13 and 24
    ) as median_flex_ppg,

    -- Overall median
    PERCENTILE_CONT(0.5) within group (order by projected_ppg_ros) as median_rostered_ppg,

    -- Replacement level (bottom quartile of rostered players)
    PERCENTILE_CONT(0.75) within group (order by projected_ppg_ros) as replacement_level_ppg

  from position_rankings
  group by position
)

select
  pr.*,

  -- Benchmark comparisons
  pb.median_starter_ppg,
  pb.weak_starter_ppg,
  pb.median_flex_ppg,
  pb.median_rostered_ppg,
  pb.replacement_level_ppg,

  -- Points above benchmarks
  pr.projected_ppg_ros - pb.median_starter_ppg as pts_above_median_starter,
  pr.projected_ppg_ros - pb.median_flex_ppg as pts_above_flex_median,
  pr.projected_ppg_ros - pb.replacement_level_ppg as pts_above_replacement,

  -- Roster tier classification
  case
    when pr.team_depth_rank = 1 then 'Starter'
    when pr.team_depth_rank = 2 and pr.position in ('RB', 'WR') then 'Starter'
    when pr.team_depth_rank = 3 and pr.position = 'RB' then 'Flex'
    when pr.team_depth_rank <= 5 then 'Bench'
    else 'Deep Bench'
  end as roster_tier,

  -- League tier (for comparison to FAs)
  case
    when pr.league_percentile_at_position <= 0.25 then 'Elite'
    when pr.league_percentile_at_position <= 0.50 then 'Strong'
    when pr.league_percentile_at_position <= 0.75 then 'Viable'
    else 'Weak'
  end as league_tier,

  -- Metadata
  CURRENT_DATE as asof_date

from position_rankings pr
left join position_benchmarks pb on pr.position = pb.position
