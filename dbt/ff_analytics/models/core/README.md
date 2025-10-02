# Core Marts

Facts, dimensions, and scoring outputs following Kimball dimensional modeling patterns.

Models include:

- ✅ `fact_player_stats` (6.3M rows, 6 seasons, 88 stat types, tests passing)
- ✅ `dim_player`, `dim_team` (deduped), `dim_schedule`
- ✅ `mart_real_world_actuals_weekly`, `mart_fantasy_actuals_weekly` (data-driven scoring via `dim_scoring_rule`)

**Design Guidance**: See `../../../docs/architecture/kimball_modeling_guidance/kimbal_modeling.md` for dimensional modeling patterns including:

- Grain declaration and enforcement
- Conformed dimensions and surrogate keys
- SCD (Slowly Changing Dimensions) patterns
- Fact table types and design anti-patterns

## Track A Status

- Architecture: ADR-010 enforced (`player_id` = `mfl_id`)
- Scoring: 2×2 model honored; `mart_fantasy_actuals_weekly` reads coefficients from `dim_scoring_rule`
- Teams: `dim_team` deduplicated by latest season per team

## Follow-ups (Non-blocking)

- Load nflverse `teams` and `schedule` parquet for environments where they’re missing
- Consider adding kicking stats (FGM/FGA, XPM/XPA) to staging and marts; wire to existing rules
- Verify defensive tackles fields to avoid double-counting (solo vs assist variants)
- Optional: add weekly team attribution alongside `current_team` for traded players
