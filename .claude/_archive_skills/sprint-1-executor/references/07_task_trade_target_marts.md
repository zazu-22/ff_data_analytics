# Task 2.3: Trade Target Marts

**Sprint:** Sprint 1
**Phase:** Phase 2
**Duration:** 8h
**Priority:** HIGH

## Objective

Create `mart_trade_targets` (all rosters) and `mart_my_trade_chips` (my overvalued players) for trade analysis.

## Dependencies

- ✅ Task 2.2 complete (valuation model exists)
- ✅ `fact_asset_market_values` (KTC) exists
- ✅ `stg_sheets__contracts_active` exists

## Files

1. `dbt/ff_data_transform/models/marts/mart_trade_targets.sql` + `.yml`

   - Grain: `player_key, current_franchise_id, asof_date`
   - All 300+ rostered players (12 teams)
   - Trade signals: BUY_LOW / SELL_HIGH / HOLD

1. `dbt/ff_data_transform/models/marts/mart_my_trade_chips.sql` + `.yml`

   - Grain: `player_key, asof_date`
   - Jason's players only
   - Overvalued by market

**Full specs:** See `00_SPRINT_PLAN.md` lines 1405-1436

## Success Criteria

- ✅ All rostered players scored (300+)
- ✅ Buy-low signals reasonable
- ✅ Tests passing

## Validation

```bash
make dbt-run --select mart_trade_targets mart_my_trade_chips
make dbt-test --select mart_trade_targets mart_my_trade_chips
```

## Commit

```text
feat: add trade target marts for buy-low/sell-high analysis
Resolves: Sprint 1 Task 2.3
```
