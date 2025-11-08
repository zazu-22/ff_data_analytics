# Task 1.4: FASA Strategy Notebook

**Sprint:** Sprint 1 - FASA Optimization & Trade Intelligence
**Phase:** Phase 1 - Critical Path for Wednesday FASA
**Estimated Duration:** 4 hours
**Priority:** CRITICAL (final deliverable for Wednesday)

______________________________________________________________________

## Objective

Create actionable Jupyter notebook that generates FASA bidding strategy using `mart_fasa_targets` and `mart_my_roster_droppable`.

______________________________________________________________________

## Context

**Why this task matters:**

- Final deliverable for Wednesday 11:59 PM EST deadline
- Must provide clear RB/WR/TE bid recommendations
- Must show drop scenarios if cap space needed

**Dependencies:**

- ✅ Task 1.3 complete (`mart_fasa_targets` and `mart_my_roster_droppable` exist)
- ✅ `mart_cap_situation` exists (from Task 1.1)

______________________________________________________________________

## File to Create

### `notebooks/fasa_weekly_strategy.ipynb`

**Notebook sections:**

1. **My Cap Situation**

   - Current cap: $80 (2025)
   - Future years breakdown
   - Cap calculator function

2. **Top FASA Targets by Position**

   - Top 10 RBs (Priority #1)
   - Top 15 WRs (Priority #2)
   - Top 8 TEs (Priority #3)
   - Tables + scatter plots

3. **Bidding Strategy Matrix**

   - Tiered approach (RB1/RB2/RB3)
   - Bid recommendations (1yr/2yr/3yr)
   - Fallback logic

4. **Drop Scenarios**

   - Top 5 drop candidates
   - Cap freed vs value lost analysis
   - Trade-off calculations

5. **Position Depth Analysis**

   - My RB depth vs league median
   - FLEX performance impact
   - ROI calculations

6. **Final Recommendation**

   - Primary bid
   - Contingency plan
   - Drop decision

**Full notebook structure:** See `00_SPRINT_PLAN.md` lines 870-1072

______________________________________________________________________

## Implementation Steps

1. Create `notebooks/` directory if needed
2. Create Jupyter notebook with 6 sections
3. Add DuckDB connection code
4. Add data loading from marts
5. Add visualizations (matplotlib/seaborn)
6. Test execution end-to-end

______________________________________________________________________

## Success Criteria

- ✅ Notebook runs without errors
- ✅ Top 10 RBs displayed with bids
- ✅ Top 15 WRs displayed with bids
- ✅ Drop scenarios calculated
- ✅ Visualizations render correctly
- ✅ Final recommendation actionable

______________________________________________________________________

## Validation Commands

```bash
# Install jupyter if needed
uv add jupyter matplotlib seaborn

# Execute notebook
uv run jupyter nbconvert --execute --to notebook \
  --inplace notebooks/fasa_weekly_strategy.ipynb

# Or run interactively
uv run jupyter notebook notebooks/fasa_weekly_strategy.ipynb
```

______________________________________________________________________

## Commit Message

```
feat: add FASA weekly strategy notebook

Create interactive Jupyter notebook for FASA bid planning:
- Top targets by position (RB/WR/TE)
- Tiered bidding strategy
- Drop scenario analysis
- ROI calculations
- Final recommendations

Deliverable ready for Wednesday 11:59 PM EST FASA deadline.

Resolves: Sprint 1 Task 1.4
```
