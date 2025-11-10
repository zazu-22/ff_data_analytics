-- models/staging/stg_{provider}__{dataset}.sql
-- Grain: {describe the grain - one row per...}
-- Source: data/raw/{provider}/{dataset}/dt=*/

{{ config(
    materialized='view'
) }}

WITH source_data AS (
    SELECT * FROM {{ source('{provider}', '{dataset}') }}
),

renamed AS (
    SELECT
        -- Primary keys
        {pk_column_1},
        {pk_column_2},

        -- Foreign keys
        {fk_column_1},

        -- Attributes
        {attribute_column_1},
        {attribute_column_2},

        -- Metadata
        {metadata_column} AS load_date

    FROM source_data
)

SELECT * FROM renamed
