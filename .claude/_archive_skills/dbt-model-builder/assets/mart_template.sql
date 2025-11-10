-- models/marts/mart_{purpose}.sql
-- Grain: {describe the grain}
-- Purpose: {describe the analytical purpose}

{{ config(
    materialized='table',
    external=true,
    partition_by=['season']
) }}

WITH fact_data AS (
    SELECT * FROM {{ ref('fact_{process}') }}
),

dimensions AS (
    SELECT * FROM {{ ref('dim_{entity}') }}
),

-- For 2×2 model: pivot long stats to wide format
pivoted AS (
    SELECT
        {dimension_key},
        season,
        week,

        -- Pivot measures
        SUM(CASE WHEN stat_name = '{stat1}' THEN stat_value END) AS {stat1},
        SUM(CASE WHEN stat_name = '{stat2}' THEN stat_value END) AS {stat2}

    FROM fact_data
    GROUP BY {dimension_key}, season, week
),

enriched AS (
    SELECT
        p.*,
        d.{display_name},
        d.{attribute}

    FROM pivoted p
    LEFT JOIN dimensions d
        ON p.{dimension_key} = d.{entity}_id
),

final AS (
    SELECT
        -- Grain keys
        {dimension_key},
        season,
        week,

        -- Dimensions
        {display_name},
        {attribute},

        -- Measures (wide format)
        {stat1},
        {stat2},

        -- Calculated metrics
        CASE
            WHEN {denominator} > 0 THEN {numerator} / {denominator}
            ELSE NULL
        END AS {rate_metric},

        -- Metadata
        CURRENT_TIMESTAMP() AS dbt_updated_at

    FROM enriched
)

SELECT * FROM final
