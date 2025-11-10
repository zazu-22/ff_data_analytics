# Trade Evaluation Template

Use this template to systematically evaluate dynasty trade opportunities.

## Trade Summary

**Date:** ____________________

**Trade Partner:** ____________________

**Partner's Timeline:** ☐ Contending  ☐ Retooling  ☐ Rebuilding

**My Timeline:** ☐ Contending  ☐ Retooling  ☐ Rebuilding

---

## Assets Exchanged

### I Give:
| Asset | Position | Age | KTC Value | Notes |
|-------|----------|-----|-----------|-------|
|       |          |     |           |       |
|       |          |     |           |       |
|       |          |     |           |       |
| **TOTAL GIVING** | | | **_____** | |

### I Receive:
| Asset | Position | Age | KTC Value | Notes |
|-------|----------|-----|-----------|-------|
|       |          |     |           |       |
|       |          |     |           |       |
|       |          |     |           |       |
| **TOTAL RECEIVING** | | | **_____** | |

**Quantity Premium Applied:** ☐ None  ☐ 30%  ☐ 40%  ☐ 50%

**Net Value (after premium):** ____________________

---

## Multi-Objective Analysis

### Dimension 1: Current Year Value
**Impact on 2025 starting lineup:**
- Week 1-6 improvement: +/- _____ projected PPG
- Week 7-14 improvement: +/- _____ projected PPG
- Playoff weeks improvement: +/- _____ projected PPG

**Overall:** ☐ Significant upgrade  ☐ Slight upgrade  ☐ Neutral  ☐ Slight downgrade  ☐ Significant downgrade

### Dimension 2: Future Value (1-3 years)
**Assets acquired:**
- 2026 outlook: ____________________
- 2027 outlook: ____________________
- 2028 outlook: ____________________

**Overall:** ☐ Significantly better  ☐ Slightly better  ☐ Neutral  ☐ Slightly worse  ☐ Significantly worse

### Dimension 3: Competitive Window Alignment
**Does this trade align with my timeline?**
- ☐ Perfectly aligned (getting win-now assets while contending, or future assets while rebuilding)
- ☐ Well aligned
- ☐ Neutral
- ☐ Misaligned (giving away assets that don't match my timeline)
- ☐ Severely misaligned

### Dimension 4: Positional Scarcity
**Positional impact:**
- QB depth after trade: ____________________
- RB depth after trade: ____________________
- WR depth after trade: ____________________
- TE depth after trade: ____________________

**Creating any critical gaps?** ☐ Yes  ☐ No

**Addressing scarcity at premium positions (TE, RB)?** ☐ Yes  ☐ No

### Dimension 5: Market Timing
**For each asset I'm giving away:**
| Asset | Value Trend | Notes |
|-------|-------------|-------|
|       | ☐ Rising ☐ Peak ☐ Declining | |
|       | ☐ Rising ☐ Peak ☐ Declining | |
|       | ☐ Rising ☐ Peak ☐ Declining | |

**For each asset I'm receiving:**
| Asset | Value Trend | Notes |
|-------|-------------|-------|
|       | ☐ Rising ☐ Peak ☐ Declining | |
|       | ☐ Rising ☐ Peak ☐ Declining | |
|       | ☐ Rising ☐ Peak ☐ Declining | |

**Am I buying low / selling high?** ☐ Yes  ☐ Neutral  ☐ No

---

## Aging Curve Analysis

**Assets I'm giving (age concerns):**
| Asset | Position | Age | Career Year | Risk Level | Notes |
|-------|----------|-----|-------------|------------|-------|
|       |          |     |             | ☐ Low ☐ Med ☐ High | |
|       |          |     |             | ☐ Low ☐ Med ☐ High | |

**Assets I'm receiving (age concerns):**
| Asset | Position | Age | Career Year | Risk Level | Notes |
|-------|----------|-----|-------------|------------|-------|
|       |          |     |             | ☐ Low ☐ Med ☐ High | |
|       |          |     |             | ☐ Low ☐ Med ☐ High | |

**Reference:**
- RBs: Exit after Year 4, decline starts Year 7
- WRs: Peak Year 5, hold value into late 20s
- TEs: Breakout Year 2, maintain through Year 7
- QBs: Peak ages 28-33, stable into mid-30s

---

## Sustainability Check

**For key assets received, check for TD regression risk:**
| Asset | Actual TDs | Expected TDs (xTD) | TDOE | Regression Risk |
|-------|------------|---------------------|------|-----------------|
|       |            |                     |      | ☐ Low ☐ Med ☐ High |
|       |            |                     |      | ☐ Low ☐ Med ☐ High |

**Volume indicators (healthy = sustainable):**
| Asset | Target/Carry Share | Snap % | Opportunity Share | Sustainable? |
|-------|-------------------|--------|-------------------|--------------|
|       |                   |        |                   | ☐ Yes ☐ No |
|       |                   |        |                   | ☐ Yes ☐ No |

---

## Win-Win Analysis

**How does this trade help my partner?**
- Addresses their positional needs: ____________________
- Aligns with their timeline: ____________________
- Fills competitive gaps: ____________________

**Is this mutually beneficial?** ☐ Yes  ☐ Marginal  ☐ No

*(If "No," trade is less likely to be accepted)*

---

## Data Architecture Queries

Use these queries against your FF Analytics dbt models to inform the trade:

### Player Performance Analysis
```sql
-- Recent performance trends
SELECT * FROM mart_player_fantasy_scoring
WHERE player_id IN ('player_1_mfl_id', 'player_2_mfl_id')
  AND season >= 2023
ORDER BY season DESC, week DESC;
```

### Projection Variance Check
```sql
-- Identify over/under performers vs projections
SELECT * FROM mart_projection_variance
WHERE player_id IN ('player_1_mfl_id', 'player_2_mfl_id')
  AND season = 2024;
```

### Market Value Tracking (if KTC data available)
```sql
-- Track value trends over time
SELECT player_name, value_date, value, value_trend
FROM stg_ktc__player_values
WHERE player_id IN ('player_1_mfl_id', 'player_2_mfl_id')
  AND value_date >= CURRENT_DATE - INTERVAL 90 DAY
ORDER BY player_name, value_date;
```

---

## Final Decision

**Overall Assessment:**

☐ **Accept** - Strong trade that improves my roster along key dimensions

☐ **Counter** - Close, but needs adjustment (specify: ____________________)

☐ **Decline** - Does not align with strategy/timeline/value

**Key factors driving decision:**
1. ____________________
2. ____________________
3. ____________________

**Notes for future reference:**
