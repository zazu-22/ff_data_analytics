{{ config(materialized='table') }}

/*
Player ID crosswalk - backward compatibility model for dim_player_id_xref.

This model provides backward compatibility for all models that reference
dim_player_id_xref via {{ ref('dim_player_id_xref') }}.

**Source**: stg_nflverse__ff_playerids (staging model with deduplication logic)
**Migration**: Previously a seed (CSV), now a staging model for always-fresh data
**Migration date**: 2025-11-06

All downstream models continue to work without modification.
*/

select *
from {{ ref('stg_nflverse__ff_playerids') }}

