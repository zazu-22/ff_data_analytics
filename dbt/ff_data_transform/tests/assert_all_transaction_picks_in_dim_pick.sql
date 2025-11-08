-- All transaction picks must have a canonical match in dim_pick
-- Fails if any picks cannot be matched (excludes known data quality issues)
select
    transaction_id_unique,
    pick_id_raw,
    'No canonical match found' as issue
from {{ ref('int_pick_transaction_xref') }}
where not has_canonical_match
