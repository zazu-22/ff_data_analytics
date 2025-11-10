-- models/core/dim_{entity}.sql
-- Grain: One row per {entity} (SCD Type {1 or 2})
-- Source: {source description}

{{ config(
    materialized='table',
    external=true
) }}

WITH source AS (
    SELECT * FROM {{ ref('stg_{provider}__{dataset}') }}
),

-- SCD Type 2 pattern (remove if SCD Type 1)
with_validity AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY {natural_key}
            ORDER BY {effective_date}
        ) AS version_number,
        {effective_date} AS valid_from,
        LEAD({effective_date}) OVER (
            PARTITION BY {natural_key}
            ORDER BY {effective_date}
        ) AS valid_to,
        CASE
            WHEN LEAD({effective_date}) OVER (PARTITION BY {natural_key} ORDER BY {effective_date}) IS NULL
            THEN TRUE
            ELSE FALSE
        END AS is_current
    FROM source
),

final AS (
    SELECT
        -- Surrogate key
        {{ dbt_utils.generate_surrogate_key(['{natural_key}', 'version_number']) }} AS {entity}_id,

        -- Natural key
        {natural_key},

        -- Attributes
        {attribute_1},
        {attribute_2},

        -- SCD Type 2 fields (remove if SCD Type 1)
        valid_from,
        valid_to,
        is_current,
        version_number,

        -- Metadata
        CURRENT_TIMESTAMP() AS dbt_updated_at

    FROM with_validity
)

SELECT * FROM final
