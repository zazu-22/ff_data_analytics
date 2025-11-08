# Seeds

Dictionaries, scoring rules, id crosswalks.

**Note**: `dim_player_id_xref` has been migrated to a staging model (`stg_nflverse__ff_playerids`)
as of 2025-11-06. See `dbt/ff_data_transform/models/core/dim_player_id_xref.sql` for the backward
compatibility model.

Example seed names: `dim_scoring_rule.csv`, `dim_franchise.csv`, `dim_timeframe.csv`.
