# Core Marts

Facts, dimensions, and scoring outputs following Kimball dimensional modeling patterns.

Models include:

- `fact_player_stats`, `dim_player`, `dim_team`, `dim_schedule`, fantasy scoring marts

**Design Guidance**: See `../../../docs/architecture/kimball_modeling_guidance/kimbal_modeling.md` for dimensional modeling patterns including:

- Grain declaration and enforcement
- Conformed dimensions and surrogate keys
- SCD (Slowly Changing Dimensions) patterns
- Fact table types and design anti-patterns
