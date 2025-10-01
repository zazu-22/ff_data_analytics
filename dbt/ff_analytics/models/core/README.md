# Core Marts

Facts, dimensions, and scoring outputs following Kimball dimensional modeling patterns.

Models include:

- ✅ `fact_player_stats` (6.3M rows, 6 seasons, 88 stat types, 19/19 tests passing)
- ☐ `dim_player`, `dim_team`, `dim_schedule` (planned)
- ☐ Fantasy scoring marts (planned)

**Design Guidance**: See `../../../docs/architecture/kimball_modeling_guidance/kimbal_modeling.md` for dimensional modeling patterns including:

- Grain declaration and enforcement
- Conformed dimensions and surrogate keys
- SCD (Slowly Changing Dimensions) patterns
- Fact table types and design anti-patterns
