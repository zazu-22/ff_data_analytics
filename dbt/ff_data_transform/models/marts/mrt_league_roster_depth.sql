{{ config(materialized="table", unique_key=['franchise_id', 'player_key']) }}

/*
League Roster Depth - rank all rostered players for VoR analysis.

Grain: franchise_id, player_key, asof_date
Purpose: Provide league-wide context for FA target evaluation
*/
with
    current_rosters as (
        select c.franchise_id, c.player_id as player_key, d.display_name as player_name, d.position, c.cap_hit
        from {{ ref("stg_sheets__contracts_active") }} c
        inner join {{ ref("dim_player") }} d on c.player_id = d.player_id
        where c.obligation_year = year(current_date) and d.position in ('QB', 'RB', 'WR', 'TE')
    ),

    projections_ros as (
        select
            player_id as player_key,
            avg(projected_fantasy_points) as projected_ppg_ros,
            sum(projected_fantasy_points) as projected_total_ros,
            count(*) as weeks_remaining
        from {{ ref("mrt_fantasy_projections") }}
        where
            season = year(current_date)
            and week > (
                select max(week)
                from {{ ref("dim_schedule") }}
                where season = year(current_date) and cast(game_date as date) < current_date
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
            coalesce(p.projected_ppg_ros, 0.0) as projected_ppg_ros,
            coalesce(p.projected_total_ros, 0.0) as projected_total_ros,

            -- Rank within franchise (depth chart)
            row_number() over (
                partition by r.franchise_id, r.position order by coalesce(p.projected_ppg_ros, 0.0) desc
            ) as team_depth_rank,

            -- Rank across entire league
            row_number() over (
                partition by r.position order by coalesce(p.projected_ppg_ros, 0.0) desc
            ) as league_rank_at_position,

            -- Count of rostered players at position
            count(*) over (partition by r.position) as total_rostered_at_position,

            -- Percentile within position
            percent_rank() over (
                partition by r.position order by coalesce(p.projected_ppg_ros, 0.0) desc
            ) as league_percentile_at_position

        from current_rosters r
        left join projections_ros p on r.player_key = p.player_key
    ),

    starter_stats as (
        select
            position,
            percentile_cont(0.5) within group (order by projected_ppg_ros desc) as median_starter_ppg,
            percentile_cont(0.25) within group (order by projected_ppg_ros desc) as weak_starter_ppg
        from position_rankings
        where league_rank_at_position <= 12
        group by position
    ),

    flex_stats as (
        select position, percentile_cont(0.5) within group (order by projected_ppg_ros desc) as median_flex_ppg
        from position_rankings
        where league_rank_at_position between 13 and 24
        group by position
    ),

    median_rostered_stats as (
        select position, percentile_cont(0.5) within group (order by projected_ppg_ros) as median_rostered_ppg
        from position_rankings
        group by position
    ),

    replacement_level_stats as (
        select position, percentile_cont(0.75) within group (order by projected_ppg_ros) as replacement_level_ppg
        from position_rankings
        group by position
    ),

    position_benchmarks as (
        select
            pr.position,
            ss.median_starter_ppg,
            ss.weak_starter_ppg,
            fs.median_flex_ppg,
            mr.median_rostered_ppg,
            rl.replacement_level_ppg
        from (select distinct position from position_rankings) pr
        left join starter_stats ss on pr.position = ss.position
        left join flex_stats fs on pr.position = fs.position
        left join median_rostered_stats mr on pr.position = mr.position
        left join replacement_level_stats rl on pr.position = rl.position
    )

select
    -- Base roster details
    pr.franchise_id,
    pr.player_key,
    pr.player_name,
    pr.position,
    pr.cap_hit,
    pr.projected_ppg_ros,
    pr.projected_total_ros,
    pr.team_depth_rank,
    pr.league_rank_at_position,
    pr.total_rostered_at_position,
    pr.league_percentile_at_position,

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
        when pr.team_depth_rank = 1
        then 'Starter'
        when pr.team_depth_rank = 2 and pr.position in ('RB', 'WR')
        then 'Starter'
        when pr.team_depth_rank = 3 and pr.position = 'RB'
        then 'Flex'
        when pr.team_depth_rank <= 5
        then 'Bench'
        else 'Deep Bench'
    end as roster_tier,

    -- League tier (for comparison to FAs)
    case
        when pr.league_percentile_at_position <= 0.25
        then 'Elite'
        when pr.league_percentile_at_position <= 0.50
        then 'Strong'
        when pr.league_percentile_at_position <= 0.75
        then 'Viable'
        else 'Weak'
    end as league_tier,

    -- Metadata
    current_date as asof_date

from position_rankings pr
left join position_benchmarks pb on pr.position = pb.position
