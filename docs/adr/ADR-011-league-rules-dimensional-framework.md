# ADR-011: League Rules Dimensional Framework

**Status:** Accepted
**Date:** 2025-10-25
**Decision Makers:** Jason Shaffer, Development Team
**Related:** ADR-008 (League Transaction History), SPEC-1 v2.3 Phase 3A

## Context

The Fantasy Football Analytics platform needs to support dynasty valuation analysis that accounts for league-specific rules affecting player value:

- **Contract economics**: Dead cap liability, rookie contract scales, RFA compensation
- **Roster constraints**: Positional limits, taxi squad eligibility, salary cap
- **Rule changes over time**: Salary cap increases, roster expansion, rule modifications

Without formalized league rules dimensions, downstream analysis would require:

1. **Hardcoded business logic** scattered across marts (maintenance nightmare)
2. **No historical tracking** of rule changes (breaks time-travel queries)
3. **Contract calculations** repeated in every mart
4. **Roster validation** without authoritative rule source

### Problem Statement

**Current state:** League rules exist only in documentation (`rules_constants.json`, `league_constitution.csv`)

**Issues:**

1. **No SCD support** - Can't track rule changes over time (e.g., cap increases)
2. **Calculation duplication** - Rookie contracts, dead cap, RFA compensation calculated ad-hoc
3. **Roster validation impossible** - Can't programmatically validate roster legality
4. **Contract valuation incomplete** - No way to calculate "true cost" accounting for cut liability

### Requirements

- Support Type 2 SCD for rule changes (e.g., cap increases from $250 → $300)
- Enable roster validation in `mart_roster_timeline`
- Provide lookup tables for contract economics (rookie scale, dead cap, RFA comp)
- Support position slot eligibility rules (K/DST IDP-only bench privileges)
- Enable surplus value calculations (player production vs contract cost)

## Decision

**Create a suite of focused league rules seed dimensions** rather than one monolithic table:

### 1. `dim_league_rules` (Core configuration - Type 2 SCD)

**Grain:** One row per rule set version
**Validity:** Season ranges with `is_current` flag

```csv
rule_id,valid_from_season,valid_to_season,is_current,annual_salary_cap,cap_tradeable,cap_tradeable_years_ahead,roster_active_limit,roster_taxi_limit,roster_ir_limit,roster_total_defined_slots,starter_qb,starter_rb,starter_wr,starter_te,starter_flex,starter_dl,starter_lb,starter_db,starter_idp_flex,starter_dst,starter_k,bench_standard,bench_idp_only,taxi_standard,taxi_idp_only,notes
R001,2012,9999,true,250,true,5,25,5,3,33,1,2,2,1,1,2,2,2,1,1,1,7,2,4,1,"Base league rules"
```

**Usage:**

```sql
-- Validate roster against rules for a specific season
select rules.roster_active_limit, rules.annual_salary_cap
from {{ ref('dim_league_rules') }} rules
where season between rules.valid_from_season and rules.valid_to_season
  and rules.is_current = true
```

### 2. `dim_rookie_contract_scale` (Rookie contract lookup)

**Grain:** One row per draft position bucket

```csv
draft_position_start,draft_position_end,round,position_bucket_label,year1_amount,year2_amount,year3_amount,year4_option_amount,year4_option_guaranteed,year4_option_deadline,rfa_match_ineligible_after_option
1,2,1,"R1.P1-2",6,6,6,24,true,"August 1",true
3,4,1,"R1.P3-4",5,5,5,20,true,"August 1",true
...
```

**Usage:**

```sql
-- Calculate rookie contract for a drafted player
select
  player.draft_position,
  scale.year1_amount,
  scale.year4_option_amount
from {{ ref('dim_player') }} player
join {{ ref('dim_rookie_contract_scale') }} scale
  on player.draft_position between scale.draft_position_start and scale.draft_position_end
```

### 3. `dim_cut_liability_schedule` (Dead cap calculation)

**Grain:** One row per contract year (1-5)

```csv
contract_year,dead_cap_pct,rounding_rule,notes
1,0.50,ceil,"50% of year 1 amount owed as dead cap"
2,0.50,ceil,"50% of year 2 amount owed as dead cap"
3,0.25,ceil,"25% of year 3 amount owed as dead cap"
4,0.25,ceil,"25% of year 4 amount owed as dead cap"
5,0.25,ceil,"25% of year 5 amount owed as dead cap"
```

**Usage:**

```sql
-- Calculate dead cap when cutting a player
select
  contract_year,
  ceil(contract_amount * dead_cap_pct) as dead_cap_owed
from player_contracts
join {{ ref('dim_cut_liability_schedule') }} using (contract_year)
```

### 4. `dim_rfa_compensation_schedule` (RFA compensation picks)

**Grain:** One row per compensation tier (Type 2 SCD)

```csv
schedule_id,valid_from_season,valid_to_season,avg_annual_min,avg_annual_max,compensation_pick_round,awarded_timing,rounding_rule
RFC001,2012,2026,10,14,3,"end_of_round",ceil
RFC002,2012,2026,15,24,2,"end_of_round",ceil
RFC003,2012,2026,25,999,1,"end_of_round",ceil
```

**Usage:**

```sql
-- Determine compensation when matching RFA offers
select comp.compensation_pick_round
from rfa_matches
join {{ ref('dim_rfa_compensation_schedule') }} comp
  on ceil(avg_annual_value) between comp.avg_annual_min and comp.avg_annual_max
  and season between comp.valid_from_season and comp.valid_to_season
```

### 5. `dim_position_slot_eligibility` (Roster slot rules)

**Grain:** One row per position

```csv
position,eligible_starter_slots,eligible_bench_standard,eligible_bench_idp_only,eligible_taxi_standard,eligible_taxi_idp_only,notes
QB,"QB",true,false,true,false,"Standard offensive player"
RB,"RB|FLEX",true,false,true,false,"Can fill RB or FLEX starter slot"
K,"K",true,true,true,true,"Special: considered IDP for bench/taxi per constitution II.F"
DST,"TEAM_D_ST",true,true,false,false,"Special: considered IDP for bench; NOT eligible for taxi per constitution II.G"
...
```

**Usage:**

```sql
-- Validate roster slot assignments
select position, eligible_bench_idp_only
from roster_assignments r
join {{ ref('dim_position_slot_eligibility') }} e using (position)
where r.slot_type = 'IDP_ONLY_BENCH'
  and e.eligible_bench_idp_only = false  -- Violation!
```

### 6. `dim_asset` (UNION dimension for trade analysis)

**Grain:** One row per asset (player or pick)

```sql
-- Players as assets
select
  'player_' || player_id as asset_id,
  'player' as asset_type,
  player_id,
  null as pick_id,
  display_name as asset_name,
  position,
  current_team as team
from {{ ref('dim_player') }}

union all

-- Draft picks as assets
select
  'pick_' || pick_id as asset_id,
  'pick' as asset_type,
  null as player_id,
  pick_id,
  season || ' Round ' || round || ' Pick ' || round_slot as asset_name,
  null as position,
  null as team
from {{ ref('dim_pick') }}
```

**Purpose:** Eliminates UNION queries in trade analysis marts

## Rationale

### Why Multiple Seeds Instead of One Monolithic Table?

**Kimball Principle:** Separate natural keys require separate dimensions

Each dimension has a **different natural key:**

- `dim_league_rules`: rule_id + season range
- `dim_rookie_contract_scale`: draft_position bucket
- `dim_cut_liability_schedule`: contract_year
- `dim_rfa_compensation_schedule`: schedule_id + season range
- `dim_position_slot_eligibility`: position

Combining would create a **sparse, denormalized mess** violating normalized dimensional design.

### Why Seeds vs Derived Models?

These are **reference data** (league constitution rules), not **derived from facts**:

- ✅ Seeds: Version controlled, manually curated, Type 2 SCD friendly
- ❌ Derived: Would require hardcoding rules in SQL (defeats the purpose)

### Why Type 2 SCD Support?

League rules **change over time**:

- Salary cap could increase ($250 → $300)
- Roster slots could expand (33 → 35 total)
- RFA compensation schedule expires in 2026

Type 2 SCD with validity dates enables:

- **Historical accuracy**: "What was the cap in 2020?"
- **Time-travel queries**: Reconstruct roster legality at any date
- **Rule change analysis**: Compare player values under different cap regimes

## Consequences

### Positive

✅ **Roster validation** - `mart_roster_timeline` can validate legal rosters programmatically
✅ **Contract economics** - Dead cap, rookie scale, RFA comp calculated from authoritative source
✅ **Historical accuracy** - Type 2 SCD tracks rule changes over time
✅ **Dynasty valuation** - Enables surplus value analysis (production - contract cost)
✅ **Trade analysis** - `dim_asset` simplifies all trade marts (no UNION in queries)
✅ **Maintainability** - Rule changes require seed updates, not SQL refactoring
✅ **Testability** - dbt tests enforce referential integrity and enum validation

### Neutral

⚪ **Seed maintenance** - Manual updates required when rules change (acceptable trade-off)
⚪ **Join complexity** - Marts need multiple dimension joins (standard Kimball pattern)

### Negative

❌ **Testing burden** - 41 new dbt tests added (mitigated: automated via dbt test)
❌ **Documentation overhead** - Must maintain seeds.yml definitions (one-time cost)

## Alternatives Considered

### Alternative 1: Hardcode Rules in SQL

**Rejected:** Business logic scattered across marts, no historical tracking, unmaintainable

```sql
-- ❌ Anti-pattern: Hardcoded dead cap calculation
case
  when contract_year = 1 then ceil(contract_amount * 0.5)
  when contract_year = 2 then ceil(contract_amount * 0.5)
  when contract_year in (3,4,5) then ceil(contract_amount * 0.25)
end as dead_cap
```

### Alternative 2: Single Monolithic League Rules Seed

**Rejected:** Violates normalized dimensional design, sparse columns, unclear grain

```csv
rule_id,season,salary_cap,rookie_r1p1_y1,rookie_r1p1_y4,dead_cap_y1_pct,rfa_10_14_round,...
```

### Alternative 3: Store Rules in JSON Configuration

**Rejected:** Can't leverage dbt tests, no SQL join support, harder to version control

```json
{
  "rookie_scale": {
    "R1.P1-2": {"y1": 6, "y4": 24}
  }
}
```

## Implementation

### Files Created

**Seeds:**

- `dbt/ff_data_transform/seeds/dim_league_rules.csv` (1 row)
- `dbt/ff_data_transform/seeds/dim_rookie_contract_scale.csv` (7 rows)
- `dbt/ff_data_transform/seeds/dim_cut_liability_schedule.csv` (5 rows)
- `dbt/ff_data_transform/seeds/dim_rfa_compensation_schedule.csv` (3 rows)
- `dbt/ff_data_transform/seeds/dim_position_slot_eligibility.csv` (9 rows)

**Models:**

- `dbt/ff_data_transform/models/core/dim_asset.sql` (UNION dimension)

**Tests:**

- 41 dbt tests added (33 seed tests + 8 dim_asset tests)

**Documentation:**

- `dbt/ff_data_transform/seeds/seeds.yml` - Seed definitions with column tests
- `dbt/ff_data_transform/models/core/schema.yml` - dim_asset documentation

### Test Results

```text
✅ dim_league_rules: 9/9 tests passing
✅ dim_rookie_contract_scale: 8/8 tests passing
✅ dim_cut_liability_schedule: 6/6 tests passing
✅ dim_rfa_compensation_schedule: 9/9 tests passing
✅ dim_position_slot_eligibility: 9/9 tests passing
✅ dim_asset: 8/8 tests passing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 49/49 tests passing (100%)
```

## What This Unlocks

**Phase 3A - State Tracking:**

- `dim_player_contract_history` - Calculate dead cap using cut_liability_schedule
- `mart_roster_timeline` - Validate rosters against league_rules
- Contract valuation with rookie scale lookups

**Phase 3B - Dynasty Analysis:**

- `mart_trade_valuations` - KTC market vs actual trades (with contract context)
- `mart_trade_history` - Trading patterns with roster/cap validation
- `mart_player_value_composite` - Surplus value (talent - contract cost)

**Phase 3C - Advanced Analytics:**

- Salary cap optimization (WAR per dollar)
- Positional scarcity analysis (using roster limits)
- Draft pick value curves (rookie scale + opportunity cost)

## References

- **League Constitution:** `docs/spec/league_constitution.csv`
- **Rules Constants:** `docs/spec/rules_constants.json`
- **SPEC-1 v2.3:** `docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md`
- **ADR-008:** League Transaction History Integration
- **Kimball Modeling Guide:** `docs/architecture/kimball_modeling_guidance/kimbal_modeling.md`

## Related Decisions

- **ADR-008**: League transaction history (requires contract/roster context)
- **ADR-010**: mfl_id canonical identity (enables dim_asset player UNION)

## Future Considerations

1. **Rule change workflow**: When salary cap increases, add new row to dim_league_rules with new validity range
2. **Defense/cap_space assets**: Extend dim_asset UNION to include TEAM D/ST and cap space trades
3. **Multi-league support**: Add league_id to all rules dimensions if expanding beyond Bell Keg League
4. **Franchise tag rules**: Consider separate dim_franchise_tag_rules if complexity grows
5. **Proration constraints**: May need dim_proration_rules for complex contract structure validation
