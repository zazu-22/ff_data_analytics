# Player Valuation Frameworks for Dynasty Fantasy Football

## Value Over Replacement (VoR/VORP)

**Definition:** Measures a player's projected performance relative to a baseline replacement-level player at the same position.

**Formula:**
```
VoR = Player's Projected Points - Replacement Level Player's Projected Points
```

**Example:**
- QB projects 300 points, replacement QB = 250 → VoR = 50
- RB projects 200 points, replacement RB = 125 → VoR = 75
- The RB provides more relative value despite lower absolute scoring

**Setting the Replacement Baseline (Three Methods):**

1. **Worst Starter Method:** Use the lowest-scoring starting player at each position
2. **Man-Games Approach:** Calculate total games needed to fill a season at each position, accounting for injuries
3. **Draft Position Method:** Set baseline using players typically drafted by round 10 or pick 100

**Key Advantage:** VoR enables cross-positional comparison by standardizing value relative to position-specific baselines.

## Value-Based Drafting (VBD)

**Core Principle:** Assemble the highest-scoring team possible by selecting the best players available based on their projected VoR.

**Application Rules:**
1. Prioritize players with highest VoR regardless of position
2. Use "drop off" metrics to identify positions with steep value declines (prioritize early)
3. Exploit positions with gentle declines (defer to later rounds)
4. Transition to uncertainty metrics in later rounds for sleeper identification

**Drop Off Metric:** Measures the decline in production between players at a given position and those immediately below them.

**Position-Specific Insights:**
- **Quarterbacks:** Low median VoR (~25) with steep drops; secure top QBs early or wait
- **Running Backs:** High VoR with notable drops after top 5 players; prioritize early
- **Wide Receivers:** Consistent value throughout draft with gentle declines; depth available later
- **Tight Ends:** Low VoR with consistent drops; balanced approach recommended

## Sustainable vs. Fluky Performance

### Touchdown Regression

**Key Insight:** Touchdowns are "least sticky" statistics—highly variable year-to-year and not predictive of future performance.

**Expected Touchdowns (xTD):** Weighs each carry/target and converts data into single number indicating player's scoring opportunity based on usage patterns, field position, and opportunity quality.

**Touchdowns Over Expected (TDOE):** Measures efficiency by comparing actual TDs to xTD.
- Players with positive TDOE experience ~86% decline the following year
- Players with negative TDOE improve by ~93% on average

**Volume as King:** "Volume is king in fantasy football. There is no better predictor of fantasy points over large samples."

### Predictive Opportunity Metrics

**Key Leading Indicators:**
1. **Target Share:** Percentage of team targets received (highly predictive for pass-catchers)
2. **Opportunity Share:** Player's share of offensive touches (carries + targets)
3. **Snap Count:** Offensive snap participation rate
4. **WOPR (Weighted Opportunity Rating):** Combines target share + air yard share (most predictive for receivers)

These metrics are leading indicators because they tend to be more predictive of future performance than lagging stats like touchdowns.

## Market Pricing Inefficiencies

**Common Market Inefficiencies:**

1. **Injury Overreactions:** Temporary injuries create buying opportunities for patient managers
2. **Offseason Pretty Roster Syndrome:** During long offseason, managers overvalue youth/upside, undervaluing proven veterans (reverses as season approaches)
3. **Recency Bias:** Recent performance (good or bad) disproportionately affects valuation
4. **Value Lag:** Changes in player value show up later in dynasty formats compared to redraft

**Value Investing Philosophy:** "Playing Dynasty can be approached like playing the stock market, with a portfolio of investments (players) looking to maximize value and achieve superior returns by performing better than the market."

**Identifying Mispriced Players:** Look for large gaps between:
- Predicted dynasty ADP
- Current market value (e.g., KeepTradeCut)
- Actual production metrics

## Prospect Profiling Analytics

### Dominator Rating

**Definition:**
- For WR/TE: Percentage of team receiving production
- For RB: Percentage of total offensive production (rushing + receiving)

**Thresholds (College):**
- 30%+ = Elite prospect profile
- 20-30% = Good prospect
- <20% = Concern flag

### Breakout Age

**Definition:** Age at which player achieved threshold production level (e.g., 1000 yards, 20%+ target share).

**Research Finding:** Earlier breakout ages correlate with higher NFL success rates.

**Position-Specific Benchmarks:**
- RB: Breakout before age 20
- WR: Breakout before age 21
- TE: More forgiving, breakout before age 23

## Dynasty-Specific Valuation Tools

### KeepTradeCut (KTC)
- **Methodology:** Crowdsourced valuations from 23M+ user votes
- **Format:** 1QB, half-PPR default (customizable)
- **Strength:** Real-time market sentiment, large sample size
- **Use case:** Identifying consensus market value

### DynastyProcess Calculator
- **Methodology:** Based on FantasyPros Dynasty Expert Consensus Rankings
- **Draft Pick Valuation:** Weighted average of nth highest player from recent draft classes (2015-2018)
- **Future Picks:** Valued at 80% of current year (present-value discounting)
- **Strength:** Highly customizable (QB scoring, league depth, rookie optimism)

### Draft Sharks
- **Methodology:** ML-trained on all NFL data since 1999
- **Approach:** Weighted average of current year projection + last 2 seasons
- **Forecasting:** 3-year, 5-year, and 10-year projections with aging curves + retirement rates

### PFF Dynasty Values
- **Methodology:** Top-ranked player/pick set at value of 100, others scaled proportionally
- **Strength:** Incorporates PFF's advanced grading and analytics

## Player Valuation Decision Tree

1. **Calculate VoR** - Establish baseline value relative to replacement player
2. **Assess Sustainability** - Separate opportunity-driven from TD-luck-driven performance
3. **Apply Aging Curves** - Adjust for position-specific career arcs
4. **Compare to Market** - Identify mispriced assets (model vs. market discrepancies)

**Sources:**
- Fantasy Football Analytics, KeepTradeCut, DynastyProcess, Draft Sharks, PFF, PlayerProfiler, ESPN, NBC Sports
