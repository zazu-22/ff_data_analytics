-- models/core/fact_{process_name}.sql
-- Grain: {describe the grain - e.g., one row per player per game per stat}
-- Dependencies: dim_{entity1}, dim_{entity2}

{{ config(
    materialized='table',
    external=true,
    partition_by=['season', 'week']
) }}

WITH base AS (
    SELECT * FROM {{ ref('stg_{provider}__{dataset}') }}
),

entity_mapping AS (
    -- Join to conformed dimensions for foreign keys
    SELECT
        b.*,
        d.{entity_id}
    FROM base b
    LEFT JOIN {{ ref('dim_{entity}') }} d
        ON b.{raw_key} = d.{matching_key}
),

final AS (
    SELECT
        -- Fact grain keys (composite primary key)
        {entity_id},
        season,
        week,
        {dimension_key},

        -- Measures
        {measure_1},
        {measure_2},

        -- Metadata
        CURRENT_TIMESTAMP() AS dbt_updated_at

    FROM entity_mapping
)

SELECT * FROM final
