-- Compensatory pick rounds must match contract AAV thresholds
-- Per League Constitution Section XI.M-N:
--   $25+/year → R1 comp
--   $15-24/year → R2 comp
--   $10-14/year → R3 comp
select
    pick_id,
    season,
    round,
    awarded_to_franchise_id,
    rfa_player_name,
    rfa_contract_aav,
    case
        when rfa_contract_aav >= 25 then 1
        when rfa_contract_aav >= 15 then 2
        when rfa_contract_aav >= 10 then 3
        else null
    end as expected_round,
    'AAV does not match round assignment' as issue
from {{ ref('dim_pick') }}
where pick_type = 'comp'
    and case
        when rfa_contract_aav >= 25 then round != 1
        when rfa_contract_aav >= 15 then round != 2
        when rfa_contract_aav >= 10 then round != 3
        else false
    end
