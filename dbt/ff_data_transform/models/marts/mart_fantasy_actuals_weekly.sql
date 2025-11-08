{{ config(materialized="table") }}

/*
Fantasy actuals mart - weekly player performance with fantasy scoring applied.

Grain: One row per player per season per week
Source: mart_real_world_actuals_weekly (with scoring rules applied from dim_scoring_rule)

Part of 2×2 model:
- Real-world base: mart_real_world_actuals_weekly (physical stats)
- Fantasy scoring: This mart (applies dim_scoring_rule dynamically)

League scoring: Half-PPR + IDP (data-driven from seed)
- Passing: From dim_scoring_rule.pass_* rules
- Rushing: From dim_scoring_rule.rush_* rules
- Receiving: From dim_scoring_rule.rec_* rules
- IDP: From dim_scoring_rule.idp_* rules
*/
with
    real_world as (select * from {{ ref("mart_real_world_actuals_weekly") }}),

    scoring as (
        select stat_name, points_per_unit
        from {{ ref("dim_scoring_rule") }}
        where is_current = true
    ),

    -- Pivot scoring rules into a single row for easy lookup
    scoring_pivoted as (
        select
            max(
                case when stat_name = 'pass_yard_point' then points_per_unit end
            ) as pass_yard_point,
            max(case when stat_name = 'pass_td' then points_per_unit end) as pass_td,
            max(case when stat_name = 'pass_int' then points_per_unit end) as pass_int,
            max(
                case when stat_name = 'pass_two_pt' then points_per_unit end
            ) as pass_two_pt,
            max(
                case when stat_name = 'rush_yard_point' then points_per_unit end
            ) as rush_yard_point,
            max(case when stat_name = 'rush_td' then points_per_unit end) as rush_td,
            max(
                case when stat_name = 'rush_lost_fumble' then points_per_unit end
            ) as rush_lost_fumble,
            max(
                case when stat_name = 'rush_two_pt' then points_per_unit end
            ) as rush_two_pt,
            max(
                case when stat_name = 'rec_reception' then points_per_unit end
            ) as rec_reception,
            max(
                case when stat_name = 'rec_yard_point' then points_per_unit end
            ) as rec_yard_point,
            max(case when stat_name = 'rec_td' then points_per_unit end) as rec_td,
            max(
                case when stat_name = 'rec_lost_fumble' then points_per_unit end
            ) as rec_lost_fumble,
            max(
                case when stat_name = 'rec_two_pt' then points_per_unit end
            ) as rec_two_pt,
            max(
                case when stat_name = 'idp_tackle' then points_per_unit end
            ) as idp_tackle,
            max(case when stat_name = 'idp_sack' then points_per_unit end) as idp_sack,
            max(
                case when stat_name = 'idp_interception' then points_per_unit end
            ) as idp_interception,
            max(
                case when stat_name = 'idp_forced_fumble' then points_per_unit end
            ) as idp_forced_fumble,
            max(case when stat_name = 'idp_td' then points_per_unit end) as idp_td,
            max(
                case when stat_name = 'idp_safety' then points_per_unit end
            ) as idp_safety
        from scoring
    )

select
    rw.*,

    -- Fantasy points calculation (data-driven from dim_scoring_rule)
    -- Offensive scoring
    (rw.passing_yards * s.pass_yard_point)
    + (rw.passing_tds * s.pass_td)
    + (rw.passing_interceptions * s.pass_int)  -- Negative value in seed
    + (rw.passing_2pt_conversions * s.pass_two_pt)

    + (rw.rushing_yards * s.rush_yard_point)
    + (rw.rushing_tds * s.rush_td)
    + (rw.rushing_fumbles_lost * s.rush_lost_fumble)  -- Negative value in seed
    + (rw.rushing_2pt_conversions * s.rush_two_pt)

    + (rw.receptions * s.rec_reception)  -- Half-PPR from seed
    + (rw.receiving_yards * s.rec_yard_point)
    + (rw.receiving_tds * s.rec_td)
    + (rw.receiving_fumbles_lost * s.rec_lost_fumble)  -- Negative value in seed
    + (rw.receiving_2pt_conversions * s.rec_two_pt)

    -- Defensive scoring (IDP)
    -- Note: Using both solo tackles and assisted tackles with same scoring (0.5
    -- points each per seed)
    + (rw.def_tackles_solo * s.idp_tackle)
    + (rw.def_tackles_with_assist * s.idp_tackle)
    + (rw.def_sacks * s.idp_sack)
    + (rw.def_interceptions * s.idp_interception)
    + (rw.def_fumbles_forced * s.idp_forced_fumble)
    + (rw.def_tds * s.idp_td)
    + (rw.def_safeties * s.idp_safety)

    -- Special teams TDs (using offensive TD scoring as fallback)
    + (rw.special_teams_tds * s.rec_td)  -- 6 points from seed

    as fantasy_points

from real_world rw
cross join scoring_pivoted s
