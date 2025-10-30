# Task 14 (2.7): Roster-Aware FASA Intelligence

**Priority:** HIGH
**Duration:** 4-6 hours
**Dependencies:** Task 13 (Enhance FASA Targets), mart_my_roster_droppable
**Sprint:** Phase 2 - FASA Intelligence Enhancements

---

## Objective

**What:** Create `mart_fasa_roster_net_value` - a roster-aware FASA intelligence mart that integrates FA opportunities with drop candidate analysis to calculate **net value improvements**.

**Why:** Current FASA targets analyze FAs in isolation without considering:
- What you'd need to drop to acquire them
- Net cap cost (bid - cap freed from drop)
- Net VoR improvement to YOUR roster (not league average)
- Position scarcity on YOUR specific roster

**Outcome:** Prescriptive "acquire X, drop Y" recommendations with net value calculations that account for your roster context, enabling smarter FASA bidding decisions.

---

## Context

### Current State

**Two Separate Systems:**

1. **`mart_fasa_targets`** - Analyzes FAs in isolation
   - Dynasty 3yr value
   - Market efficiency signals
   - Suggested bids (absolute)
   - VoR vs league replacement level

2. **`mart_my_roster_droppable`** - Analyzes your roster in isolation
   - Drop candidates
   - Cap space freed if cut
   - Points per dollar
   - Droppable scores

**Gap:** No integration to answer "Should I bid $X for FA Y if I have to drop player Z?"

### Problem Example

**Current analysis says:**
- Marcus Mariota: STRONG_BUY, $3 bid, 106 dynasty value
- Kalif Raymond: On your roster, $2 contract, 83 dynasty value

**Missing analysis:**
- Net VoR: +23 fantasy points (106 - 83)
- Net Cap Cost: +$1 ($3 bid - $2 freed)
- Value per Net Dollar: 23 pts / $1 = **23 pts/$** (excellent!)
- Position context: You have 8 WRs, only 2 QBs → QB acquisition more valuable

### Why It Matters

**Better Decision Making:**
- Avoid bidding on marginal upgrades that waste cap
- Identify cap-positive opportunities (save money while improving!)
- Consider position scarcity on YOUR roster, not league average
- Maximize value per net dollar spent

**Research Foundation:**
- "True VoR must be roster-specific" (4for4, JJ Zachariason)
- "Replacement level is YOUR worst starter, not league average" (Evan Silva)
- "Dynasty decisions require net present value thinking" (Rich Hribar)

---

## Files to Create/Modify

### New Files

```
dbt/ff_analytics/models/marts/mart_fasa_roster_net_value.sql
dbt/ff_analytics/models/marts/_mart_fasa_roster_net_value.yml
```

### Dependencies Required

- `{{ ref('mart_fasa_targets') }}` - FA intelligence
- `{{ ref('mart_my_roster_droppable') }}` - Drop candidate analysis
- `{{ ref('stg_sheets__contracts_active') }}` - Your current roster contracts
- `{{ ref('dim_player') }}` - Player identity resolution

---

## Implementation Steps

### Step 1: Create `mart_fasa_roster_net_value.sql`

**Grain:** One row per (fa_player_id, drop_candidate_player_id) pair

**Key CTEs:**

1. **`my_roster`** - Your current roster with dynasty values
2. **`fa_opportunities`** - Enhanced FASA targets
3. **`drop_candidates_per_fa`** - For each FA, identify viable drop candidates
4. **`net_value_analysis`** - Calculate net improvements for each pair
5. **`ranked_opportunities`** - Rank by value per net dollar

**SQL Template:**

```sql
-- Grain: fa_player_id, drop_candidate_player_id
-- Purpose: Roster-aware FASA intelligence with net value calculations

with my_roster as (
  -- Your current roster with dynasty valuations
  select
    dp.player_id,
    dp.display_name as player_name,
    dp.position,
    c.cap_hit as contract_value,
    c.obligation_year,

    -- Calculate dynasty 3yr value for rostered players (same logic as FASA targets)
    -- Use mart_fantasy_projections + aging curves
    COALESCE(dv.dynasty_3yr_value, 0) as dynasty_3yr_value,

    -- Droppable metrics from mart_my_roster_droppable
    rd.droppable_score,
    rd.dead_cap_if_cut_now,
    rd.cap_space_freed,
    rd.position_depth_rank,
    rd.roster_tier

  from {{ ref('stg_sheets__contracts_active') }} c
  inner join {{ ref('dim_player') }} dp on c.player_id = dp.player_id
  left join {{ ref('mart_my_roster_droppable') }} rd on dp.player_id = rd.player_id
  left join (
    -- Dynasty valuation logic (reuse from FASA targets or extract to separate mart)
    select player_id, dynasty_3yr_value
    from {{ ref('mart_fasa_targets') }}  -- Temporary: reuse existing logic
  ) dv on dp.player_id = dv.player_id

  where
    c.gm_full_name = 'Jason Shaffer'
    and c.obligation_year = YEAR(CURRENT_DATE)
),

fa_opportunities as (
  -- All FA targets with enhanced intelligence
  select
    player_id as fa_player_id,
    player_name as fa_name,
    position as fa_position,
    dynasty_3yr_value as fa_dynasty_value,
    market_efficiency_signal,
    suggested_bid_market_adjusted as fa_suggested_bid,
    bid_confidence_v3,
    enhanced_value_score_v2,

    -- League context
    pts_above_league_replacement as fa_league_vor,
    league_replacement_level_ppg,

    -- Market context
    model_percentile,
    market_percentile,
    value_gap_pct

  from {{ ref('mart_fasa_targets') }}
  where player_id is not null
),

drop_candidates_per_fa as (
  -- For each FA, identify viable drop candidates
  select
    fa.fa_player_id,
    fa.fa_name,
    fa.fa_position,
    fa.fa_dynasty_value,
    fa.fa_suggested_bid,
    fa.market_efficiency_signal,

    -- Drop candidate
    mr.player_id as drop_player_id,
    mr.player_name as drop_name,
    mr.position as drop_position,
    mr.dynasty_3yr_value as drop_dynasty_value,
    mr.contract_value as drop_contract_value,
    mr.dead_cap_if_cut_now as drop_dead_cap,
    mr.cap_space_freed as drop_cap_freed,
    mr.droppable_score,
    mr.position_depth_rank as drop_depth_rank,

    -- Matching logic priority
    case
      when fa.fa_position = mr.position then 1  -- Same position (depth play)
      when mr.droppable_score >= 60 then 2       -- High droppable score
      when mr.position_depth_rank > 3 then 3     -- Deep bench player
      else 4
    end as drop_priority

  from fa_opportunities fa
  cross join my_roster mr

  where
    -- Only consider actual drop candidates (not starters)
    mr.droppable_score > 20  -- Minimum droppability threshold
    or mr.position_depth_rank > 2  -- Bench players only
),

net_value_analysis as (
  select
    dc.*,

    -- Net improvements
    dc.fa_dynasty_value - dc.drop_dynasty_value as net_dynasty_value_gain,
    dc.fa_suggested_bid - dc.drop_cap_freed as net_cap_cost,

    -- Value efficiency
    (dc.fa_dynasty_value - dc.drop_dynasty_value)
      / NULLIF(dc.fa_suggested_bid - dc.drop_cap_freed, 0) as value_per_net_dollar,

    -- Position context flags
    dc.fa_position = dc.drop_position as same_position_upgrade,

    -- Actionability score (0-100)
    LEAST(100, GREATEST(0,
      -- High net value gain (40% weight)
      (CASE WHEN net_dynasty_value_gain > 100 THEN 40
            WHEN net_dynasty_value_gain > 50 THEN 30
            WHEN net_dynasty_value_gain > 25 THEN 20
            ELSE 10 END)

      -- Low/negative net cap cost (30% weight)
      + (CASE WHEN net_cap_cost <= 0 THEN 30  -- Cap positive!
              WHEN net_cap_cost <= 2 THEN 20
              WHEN net_cap_cost <= 5 THEN 10
              ELSE 0 END)

      -- Market signal (20% weight)
      + (CASE WHEN market_efficiency_signal = 'STRONG_BUY' THEN 20
              WHEN market_efficiency_signal = 'BUY' THEN 15
              WHEN market_efficiency_signal = 'HOLD' THEN 10
              ELSE 0 END)

      -- Droppable candidate (10% weight)
      + (CASE WHEN droppable_score > 80 THEN 10
              WHEN droppable_score > 60 THEN 7
              ELSE 3 END)
    )) as actionability_score,

    -- Recommendation
    CASE
      WHEN net_dynasty_value_gain > 50 AND net_cap_cost <= 0 THEN 'STRONG_ACQUIRE'
      WHEN net_dynasty_value_gain > 25 AND value_per_net_dollar > 15 THEN 'ACQUIRE'
      WHEN net_dynasty_value_gain > 10 AND net_cap_cost <= 3 THEN 'CONSIDER'
      WHEN net_dynasty_value_gain < 0 THEN 'AVOID'
      ELSE 'PASS'
    END as acquisition_recommendation

  from drop_candidates_per_fa dc
),

ranked_opportunities as (
  select
    *,
    ROW_NUMBER() over (
      order by actionability_score desc, value_per_net_dollar desc
    ) as overall_rank,

    ROW_NUMBER() over (
      partition by fa_player_id
      order by actionability_score desc, value_per_net_dollar desc
    ) as rank_per_fa,

    ROW_NUMBER() over (
      partition by drop_player_id
      order by actionability_score desc, value_per_net_dollar desc
    ) as rank_per_drop_candidate

  from net_value_analysis
  where net_dynasty_value_gain > 0  -- Only improvements
)

select
  -- FA Identity
  fa_player_id,
  fa_name,
  fa_position,
  fa_dynasty_value,
  fa_suggested_bid,
  market_efficiency_signal,

  -- Drop Candidate Identity
  drop_player_id,
  drop_name,
  drop_position,
  drop_dynasty_value,
  drop_contract_value,
  drop_cap_freed,
  droppable_score,

  -- Net Analysis
  net_dynasty_value_gain,
  net_cap_cost,
  value_per_net_dollar,

  -- Flags
  same_position_upgrade,
  drop_priority,

  -- Scores & Recommendations
  actionability_score,
  acquisition_recommendation,

  -- Rankings
  overall_rank,
  rank_per_fa,
  rank_per_drop_candidate,

  -- Metadata
  CURRENT_DATE as asof_date

from ranked_opportunities
where rank_per_fa = 1  -- Best drop candidate per FA (can be removed to see all pairs)

order by actionability_score desc, value_per_net_dollar desc
```

### Step 2: Create `_mart_fasa_roster_net_value.yml`

```yaml
version: 2

models:
  - name: mart_fasa_roster_net_value
    description: |
      Roster-aware FASA intelligence integrating FA opportunities with drop candidate
      analysis to calculate net value improvements specific to your roster.

      **Grain:** fa_player_id, drop_player_id (one row per viable FA+drop pair)

      **Business Question:** "Should I bid $X for FA Y if I have to drop player Z?"

      **Key Metrics:**
      - Net Dynasty Value Gain: FA value - Drop candidate value
      - Net Cap Cost: FA bid - Cap freed from drop
      - Value per Net Dollar: Net value / Net cap cost (efficiency metric)
      - Actionability Score: 0-100 composite of value gain, cap efficiency, market signal

      **Recommendation Tiers:**
      - STRONG_ACQUIRE: Net value >50 AND cap-positive (saves money!)
      - ACQUIRE: Net value >25 AND >15 pts/$ efficiency
      - CONSIDER: Net value >10 AND low cap cost
      - PASS: Marginal improvement
      - AVOID: Negative net value

      **Usage:** Filter to `rank_per_fa = 1` for best drop candidate per FA.
      Remove filter to see all viable combinations.

    columns:
      - name: fa_player_id
        description: "Free agent player_id (canonical)"
        data_tests:
          - not_null

      - name: fa_name
        description: "Free agent display name"

      - name: fa_position
        description: "Free agent position"

      - name: fa_dynasty_value
        description: "Free agent 3-year dynasty value (fantasy points)"

      - name: fa_suggested_bid
        description: "Suggested FAAB bid for FA (market-adjusted)"

      - name: market_efficiency_signal
        description: "Market signal for FA (STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL)"

      - name: drop_player_id
        description: "Drop candidate player_id (canonical)"
        data_tests:
          - not_null

      - name: drop_name
        description: "Drop candidate display name"

      - name: drop_position
        description: "Drop candidate position"

      - name: drop_dynasty_value
        description: "Drop candidate 3-year dynasty value (fantasy points)"

      - name: drop_contract_value
        description: "Drop candidate current year cap hit"

      - name: drop_cap_freed
        description: "Cap space freed if drop candidate is cut"

      - name: droppable_score
        description: "Droppable score of candidate (0-100, from mart_my_roster_droppable)"

      - name: net_dynasty_value_gain
        description: "Net fantasy points gained (FA value - drop value). Positive = upgrade."

      - name: net_cap_cost
        description: "Net cap dollars spent (FA bid - cap freed). Negative = save money!"

      - name: value_per_net_dollar
        description: "Dynasty points gained per net dollar spent. Higher = more efficient."

      - name: same_position_upgrade
        description: "TRUE if FA and drop candidate are same position (depth play)"

      - name: drop_priority
        description: "Drop candidate matching priority (1=same pos, 2=high droppable, 3=deep bench, 4=other)"

      - name: actionability_score
        description: "Composite actionability score (0-100). Higher = more actionable opportunity."
        data_tests:
          - dbt_utils.expression_is_true:
              arguments:
                expression: "actionability_score >= 0 AND actionability_score <= 100"

      - name: acquisition_recommendation
        description: "Recommendation tier (STRONG_ACQUIRE/ACQUIRE/CONSIDER/PASS/AVOID)"
        data_tests:
          - accepted_values:
              arguments:
                values: ['STRONG_ACQUIRE', 'ACQUIRE', 'CONSIDER', 'PASS', 'AVOID']

      - name: overall_rank
        description: "Overall rank across all FA+drop combinations (1 = best opportunity)"

      - name: rank_per_fa
        description: "Rank per FA (1 = best drop candidate for this FA)"

      - name: rank_per_drop_candidate
        description: "Rank per drop candidate (1 = best FA to replace this drop candidate with)"

      - name: asof_date
        description: "Snapshot date"

    data_tests:
      - dbt_utils.unique_combination_of_columns:
          arguments:
            combination_of_columns:
              - fa_player_id
              - drop_player_id
              - asof_date
```

### Step 3: Add to dbt Configuration

**File:** `dbt/ff_analytics/dbt_project.yml`

Ensure marts are configured with external materialization:

```yaml
models:
  ff_analytics:
    marts:
      +materialized: external
      +partition_by: ['dt']
      +location: "{{ env_var('EXTERNAL_ROOT', 'data/raw') }}/marts/{{ this.name }}/dt={{ run_started_at.strftime('%Y-%m-%d') }}"
```

---

## Validation Commands

### 1. Run dbt model

```bash
export EXTERNAL_ROOT="$PWD/data/raw"
mkdir -p data/raw/marts/mart_fasa_roster_net_value/dt=$(date +%Y-%m-%d)

make dbt-run MODELS=mart_fasa_roster_net_value
```

**Expected:** Model builds successfully

### 2. Validate grain uniqueness

```bash
make dbt-test MODELS=mart_fasa_roster_net_value
```

**Expected:** All tests pass (grain uniqueness, accepted values)

### 3. Inspect top recommendations

```bash
duckdb dbt/ff_analytics/target/dev.duckdb <<EOF
SELECT
  fa_name,
  fa_position,
  drop_name,
  drop_position,
  ROUND(net_dynasty_value_gain, 0) as net_value,
  net_cap_cost,
  ROUND(value_per_net_dollar, 1) as pts_per_dollar,
  acquisition_recommendation
FROM read_parquet('data/raw/marts/mart_fasa_roster_net_value/dt=*/data.parquet')
WHERE rank_per_fa = 1
ORDER BY actionability_score DESC
LIMIT 15;
EOF
```

**Expected:**
- Actionable recommendations with net value calculations
- Cap-positive opportunities (net_cap_cost < 0) ranked highly
- Clear upgrade paths (net_dynasty_value_gain > 0)

### 4. Validate roster coverage

```bash
duckdb dbt/ff_analytics/target/dev.duckdb <<EOF
SELECT
  COUNT(DISTINCT fa_player_id) as unique_fas,
  COUNT(DISTINCT drop_player_id) as unique_drop_candidates,
  COUNT(*) as total_combinations,
  SUM(CASE WHEN acquisition_recommendation = 'STRONG_ACQUIRE' THEN 1 ELSE 0 END) as strong_acquires,
  SUM(CASE WHEN same_position_upgrade THEN 1 ELSE 0 END) as same_position_upgrades
FROM read_parquet('data/raw/marts/mart_fasa_roster_net_value/dt=*/data.parquet');
EOF
```

**Expected:**
- Covers most FAs from mart_fasa_targets
- Includes multiple drop candidates per FA
- Some STRONG_ACQUIRE recommendations (cap-positive opportunities)

### 5. Check for cap-positive opportunities

```bash
duckdb dbt/ff_analytics/target/dev.duckdb <<EOF
SELECT
  fa_name,
  drop_name,
  fa_suggested_bid,
  drop_cap_freed,
  net_cap_cost,
  net_dynasty_value_gain,
  acquisition_recommendation
FROM read_parquet('data/raw/marts/mart_fasa_roster_net_value/dt=*/data.parquet')
WHERE net_cap_cost <= 0
ORDER BY net_dynasty_value_gain DESC
LIMIT 10;
EOF
```

**Expected:** Cap-positive opportunities (save money while improving roster!)

---

## Success Criteria

- [ ] `mart_fasa_roster_net_value.sql` created with all CTEs implemented
- [ ] `_mart_fasa_roster_net_value.yml` created with comprehensive column documentation
- [ ] Model builds successfully via `make dbt-run`
- [ ] All dbt tests pass (grain uniqueness, value constraints)
- [ ] Output contains net value calculations for FA+drop pairs
- [ ] Actionability score correlates with value_per_net_dollar
- [ ] STRONG_ACQUIRE recommendations include cap-positive opportunities
- [ ] Can identify top 10 most actionable FASA opportunities for your roster

---

## Commit Message

```
feat: add roster-aware FASA intelligence mart

Create mart_fasa_roster_net_value integrating FA opportunities with
drop candidate analysis to calculate net value improvements specific
to user's roster.

Key Features:
- Net dynasty value gain (FA value - drop value)
- Net cap cost (bid - cap freed from drop)
- Value per net dollar efficiency metric
- Actionability score (0-100 composite)
- Acquisition recommendations (STRONG_ACQUIRE/ACQUIRE/CONSIDER/PASS/AVOID)

Business Value:
- Answer "Should I bid $X for FA Y if I drop player Z?"
- Identify cap-positive opportunities (save money while improving!)
- Consider position scarcity on YOUR roster, not league average
- Maximize value per net dollar spent

Example Insight: "Bid $3 for Mack Hollins, drop Kalif Raymond
→ Net +67 dynasty pts for -$2 cap (saves money!)"

Grain: fa_player_id, drop_player_id (filtered to rank_per_fa=1 shows
best drop candidate per FA)

Resolves: Sprint 1 Task 14 (Roster-Aware FASA Intelligence)
```

---

## Notes & Gotchas

### Dynasty Valuation for Rostered Players

The SQL template shows a temporary approach of reusing values from `mart_fasa_targets`. A better long-term approach would be to:

1. Extract dynasty valuation logic to a separate mart (e.g., `mart_player_dynasty_value`)
2. Use same aging curve + projection logic for both FA and rostered players
3. Ensure consistency across all dynasty value calculations

### Position Scarcity

Current implementation uses simple depth rank. Could be enhanced with:
- League-wide positional scarcity multipliers
- Starter requirements by position (2 RB, 3 WR, 1 TE, 1 FLEX)
- Your team's specific positional needs vs league average

### Drop Candidate Selection

Current logic considers all bench/droppable players. Could be refined to:
- Exclude players with multi-year contracts (future value)
- Weight recent performance trends (hot/cold streaks)
- Consider injury status (don't drop injured players with potential)
- Add user-specified "protected players" list

### Performance

Cross join between FAs (230) and roster players (~30) creates ~6,900 combinations.
Filtering to `rank_per_fa = 1` reduces output to ~230 rows (manageable).

---

## Related Tasks

- **Prerequisite:** Task 13 (Enhance FASA Targets) - Provides dynasty valuations
- **Prerequisite:** `mart_my_roster_droppable` - Provides drop candidate analysis
- **Follows:** Task 1.4 (FASA Strategy Notebook) - Can leverage this mart for recommendations

---

## Research References

- "True Value Over Replacement" - JJ Zachariason, 4for4
- "Roster Construction Theory" - Rich Hribar, Fantasy Points Data
- "Dynasty Asset Valuation" - Chris Raybon, PFF
- "The 2×2 Trade Analysis Framework" - Evan Silva, Establish The Run
