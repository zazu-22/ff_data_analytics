# Dynasty Fantasy Football Player Valuation Frameworks

**Research Report**
**Date:** October 29, 2025
**Purpose:** Comprehensive reference for quantitative valuation models in dynasty fantasy football

______________________________________________________________________

## Table of Contents

1. [Value over Replacement (VoR)](#value-over-replacement-vor)
2. [Wins over Replacement (WoR/WAR)](#wins-over-replacement-worwar)
3. [Value-Based Drafting (VBD)](#value-based-drafting-vbd)
4. [Model vs. Market Pricing](#model-vs-market-pricing)
5. [Sustainable vs. Fluky Performance](#sustainable-vs-fluky-performance)
6. [Advanced Predictive Metrics](#advanced-predictive-metrics)
7. [Dynasty-Specific Frameworks](#dynasty-specific-frameworks)
8. [Implementation Guidelines](#implementation-guidelines)

______________________________________________________________________

## Value over Replacement (VoR)

### Overview

Value over Replacement quantifies how much better a player performs compared to a replacement-level baseline player at their position. This creates a position-agnostic valuation framework.

### Mathematical Formula

```
VoR = Player_Projected_Points − Replacement_Level_Points
```

### Baseline Determination Methods

#### 1. Worst Starter Method

**Definition:** Use the projected points of the last starter at each position.

**Calculation:**

- 12-team league, 1 QB starter → Baseline = QB12
- 12-team league, 2 RB starters → Baseline = RB24
- 12-team league, 3 WR starters → Baseline = WR36

**Example:**

```
QB1 projects: 300 points
QB12 projects: 250 points
VoR = 300 − 250 = 50

RB1 projects: 200 points
RB24 projects: 125 points
VoR = 200 − 125 = 75
```

**Interpretation:** Despite QB1 scoring 100 more raw points than RB1, the RB1 has higher VoR (75 vs 50) due to greater positional scarcity.

#### 2. Man-Games Approach

**Definition:** Calculates total games needed to fill position requirements across a season, accounting for injuries, bye weeks, and roster turnover.

**Process:**

1. Calculate total position-weeks needed (teams × starters × weeks)
2. Determine typical number of players used to fill those games
3. Set baseline at that player threshold

**Example for 12-team league with 2 RB starters:**

- Total RB-games needed: 12 teams × 2 starters × 17 weeks = 408 games
- Average RBs used per team: ~3.5 (accounting for injuries/byes)
- Baseline: RB42 (12 teams × 3.5)

**Advantage:** More realistic for in-season valuation as it accounts for attrition.

#### 3. Draft Round Method

**Definition:** Set baseline by examining where players are typically drafted.

**Common benchmarks:**

- Pick 100 cutoff
- End of 10th round (in 12-team leagues)

**Application:** Analyze historical drafts to determine position distribution at the cutoff, then set baselines accordingly.

### Dynasty-Specific VoR Considerations

For dynasty leagues, VoR must account for multi-year value:

```
Dynasty_VoR = Σ(Year_i_Points − Replacement_Year_i_Points) × Discount_Factor_i
```

**Example:**

```
RB_A: 300 pts/yr for 4 years = 1,200 total
Baseline: 100 pts/yr for 4 years = 400 total
VoR = 1,200 − 400 = 800 (200% over baseline)

WR_A: 250 pts/yr for 8 years = 2,000 total
Baseline: 150 pts/yr for 8 years = 1,200 total
VoR = 2,000 − 1,200 = 800 (67% over baseline)
```

The WR has equivalent total VoR but lower percentage advantage, requiring time-discounting adjustments.

### Strengths

- Position-agnostic comparison framework
- Quantifies scarcity value
- Mathematically rigorous
- Flexible baseline selection for league-specific optimization

### Limitations

- Baseline selection significantly impacts results
- League-specific (team count, roster size, scoring)
- Doesn't account for consistency/variance
- Single-season focus unless modified for dynasty
- Assumes perfect projection accuracy

### Sources

- [Fantasy Football Analytics - VoR and VBD](https://fantasyfootballanalytics.net/2024/08/winning-fantasy-football-with-projections-value-over-replacement-and-value-based-drafting.html)
- [FantasyPros - What is VBD?](https://www.fantasypros.com/2017/06/what-is-value-based-drafting/)
- [Fantasy Footballers - Using VORP](https://www.thefantasyfootballers.com/analysis/using-vorp-to-assess-a-tight-end-wasteland-fantasy-football/)

______________________________________________________________________

## Wins over Replacement (WoR/WAR)

### Overview

WAR converts point differentials into expected wins, accounting for the non-linear relationship between points and winning. Not all points are created equal—consistent scoring is more valuable than boom/bust performance.

### Theoretical Framework

**Core Insight:** "How many wins a player added to your roster" vs. "how many points they scored."

WAR recognizes that:

1. Positional scarcity affects win probability differently
2. Weekly consistency matters for head-to-head matchups
3. Diminishing returns exist for extreme scoring

### Calculation Methodology

#### Step 1: Establish Replacement Baseline

For standard lineup (QB/2RB/3WR/TE/FLEX):

```
Average Roster Points Per Game:
- QB (avg QB1-QB12):     18.3 PPG
- RB (avg RB1-RB24 × 2): 23.5 PPG
- WR (avg WR1-WR36 × 3): 33.1 PPG
- TE (avg TE1-TE12):      8.8 PPG
- FLEX (avg pos 48-72):   8.1 PPG
─────────────────────────────────
Total:                   91.8 PPG
```

#### Step 2: Calculate Win Probability

Use normal distribution to determine how a player shifts expected outcomes:

```
Win_Probability = P(Your_Score > Opponent_Score)

Where scoring follows normal distribution:
- Mean = 91.8 PPG (replacement roster average)
- Std Dev = position and league dependent
```

#### Step 3: Convert to Wins Added

**Example: Cooper Kupp**

```
Kupp PPG: 21.6
Replacement WR: 11.0
Difference: +10.6 PPG

Impact on win probability:
- With replacement WR: 50% win rate (average roster)
- With Kupp: 72% win rate
- Increase: 22 percentage points

Over 17-game season:
WAR = (0.72 − 0.50) × 17 = +3.74 wins above replacement
```

### WAR vs. VoR Comparison

| Metric  | Measures           | Accounts for Variance | Best For                              |
| ------- | ------------------ | --------------------- | ------------------------------------- |
| **VoR** | Point differential | No                    | Draft value, simple comparisons       |
| **WAR** | Win probability    | Yes                   | True player impact, consistency value |

**Key Difference:** A player with 20 PPG ± 2 (consistent) may have higher WAR than a player with 22 PPG ± 10 (volatile), despite lower average scoring.

### Strengths

- Directly measures fantasy success (wins)
- Accounts for scoring consistency
- Captures diminishing returns on points
- More realistic impact assessment
- Superior for head-to-head formats

### Limitations

- Complex calculation requiring distribution analysis
- League-specific (opponent distributions vary)
- Requires full-season data for accuracy
- Less intuitive than point-based metrics
- Difficult to calculate in real-time

### Sources

- [Fantasy Footballers - Understanding Performance Above Replacement](https://www.thefantasyfootballers.com/articles/on-the-warpath-understanding-performance-above-replacement-fantasy-football/)
- [FantasyPros - Introducing Fantasy Football WAR](https://www.fantasypros.com/2019/08/introducing-fantasy-football-wins-above-replacement-war-2019-fantasy-football/)
- [Fantasy Points - Understanding Fantasy WAR](https://www.fantasypoints.com/nfl/articles/2024/understanding-fantasy-war-league-settings)

______________________________________________________________________

## Value-Based Drafting (VBD)

### Overview

VBD is a systematic draft strategy that ranks all players by their value over replacement (VoR), creating a unified draft board across positions. Developed by Joe Bryant in 1996.

### Seven-Step VBD Process

#### Step 1: Project Player Statistics

Create comprehensive projections for all draftable players including:

- Passing: attempts, completions, yards, TDs, INTs
- Rushing: attempts, yards, TDs
- Receiving: targets, receptions, yards, TDs

#### Step 2: Calculate Fantasy Points

Apply league-specific scoring:

**Example (4pt passing TD, 6pt rushing/receiving TD):**

```
QB projection:
- 4,000 passing yards ÷ 30 yards/pt = 133.3 pts
- 30 passing TDs × 4 pts = 120 pts
- 200 rushing yards ÷ 10 yards/pt = 20 pts
- 2 rushing TDs × 6 pts = 12 pts
────────────────────────────────────────────
Total: 285.3 fantasy points
```

#### Step 3: Establish Baseline (X-Values)

**Baseline Rule:** Use approximately 100 picks as measurement point.

**12-team, 18-round league example:**

- Total picks ≈ 216 (12 × 18)
- Pick 100 represents 46th percentile
- Position distribution at pick 100:
  - 15 QBs (QB15 = baseline)
  - 36 RBs (RB36 = baseline)
  - 38 WRs (WR38 = baseline)
  - 8 TEs (TE8 = baseline)
  - 2 DST, 1 K

**X-Value Formula:**

```
X-Value = Player_Points − Baseline_Player_Points
```

**Example Calculations:**

```
QB1: 285 pts, QB15: 220 pts → X-Value = +65
RB1: 280 pts, RB36: 150 pts → X-Value = +130
WR1: 270 pts, WR38: 140 pts → X-Value = +130
TE1: 200 pts, TE8:  120 pts → X-Value = +80
```

**Unified Rankings:**

1. RB1 (+130)
2. WR1 (+130)
3. TE1 (+80)
4. QB1 (+65)

#### Step 4: Sort All Players by X-Values

Create single master list regardless of position, revealing true draft value.

#### Step 5: Track Average Draft Position (ADP)

Compare your X-Value rankings to market ADP to identify value opportunities:

- Players ranked higher in X-Value than ADP = bargains
- Players ranked lower in X-Value than ADP = overpriced

#### Step 6: Apply Need Factor During Draft

Adjust X-values based on roster composition:

**Need Factor Table:**

| Positions Filled | Start 1 | Start 2 | Start 3 | Start 4 | Start 5 |
| ---------------- | ------- | ------- | ------- | ------- | ------- |
| 0                | 1.0     | 1.0     | 1.0     | 1.0     | 1.0     |
| 1                | 0.8     | 1.0     | 1.0     | 1.0     | 1.0     |
| 2                | 0.6     | 0.8     | 1.0     | 1.0     | 1.0     |
| 3                | 0.4     | 0.6     | 0.8     | 1.0     | 1.0     |
| 4                | 0.2     | 0.4     | 0.6     | 0.8     | 1.0     |

**Adjusted Value Formula:**

```
Adjusted_Value = X-Value × Need_Factor
```

**Example:**

```
Your roster: 2 RBs filled (start 2 RB league)
Available RB with X-Value = 50
Adjusted_Value = 50 × 0.8 = 40

Available WR with X-Value = 45 (0 WRs filled)
Adjusted_Value = 45 × 1.0 = 45

→ Draft WR despite RB having higher raw X-Value
```

#### Step 7: Switch to Positional Rankings After Baseline

After ~pick 120 (all baselines filled), switch to best player by position for:

- Bye week coverage
- Handcuff backups for injury protection
- Favorable matchup exploitation

### VBD Baseline Variants

#### VOLS (Value Over Last Starter)

**Definition:** Baseline = last starting roster spot

**Best for:**

- Shallow leagues
- Active waiver wire environments
- Prioritizing elite starters

**Trade-off:** Inflates top-player prices, minimal bench budget

#### VORP (Value Over Replacement Player)

**Definition:** Baseline = best waiver wire player

**Best for:**

- Best Ball formats (no waivers)
- Deep leagues with thin waivers
- Bench depth strategies

**Trade-off:** Undervalues elite starters relative to bench depth

#### BEER (Best Ever Evaluation of Replacement)

**Definition:** Baseline = man-games analysis (accounts for injuries, byes, turnover)

**Methodology:**

1. Calculate total player-games needed across season
2. Determine average players used per team per position
3. Set baseline at that threshold

**Best for:** Balanced approach between starter priority and depth

**Example:**

```
12-team league, 2 RB starters, 17 weeks:
- Total RB-games: 12 × 2 × 17 = 408
- Avg RBs used per team: 3.5 (injuries/byes)
- Baseline: RB42 (12 × 3.5)
```

#### BEER+ (Recommended Default)

**Enhancements over BEER:**

1. **Dual baselines:** Blends VOLS and BEER, redistributing bench value to starters
2. **Risk adjustment:** Incorporates Sharpe ratio accounting for positional variance
3. **Streaming adjustment:** Factors in QB/TE streaming viability

**Recommendation:** "You should probably use the BEER+ valuation in general" - Subvertadown

### Strengths

- Systematic, repeatable process
- Exploits market inefficiencies (ADP vs X-Value)
- Adapts to league-specific scoring/rosters
- Quantifiable decision framework
- Proven historical success

### Limitations

- Requires accurate projections (garbage in, garbage out)
- Time-intensive setup
- Doesn't account for consistency variance
- Can lead to roster imbalance if applied rigidly
- Baseline selection significantly affects rankings

### Sources

- [Footballguys - Principles of VBD (Joe Bryant)](https://www.footballguys.com/article/bryant_vbd?article=bryant_vbd)
- [Subvertadown - Guide to VBD Baselines (VOLS, VORP, BEER)](https://subvertadown.com/article/guide-to-understanding-the-different-baselines-in-value-based-drafting-vbd-vols-vs-vorp-vs-man-games-and-beer-)
- [FantasyPros - VBD for Dummies](https://www.fantasypros.com/2012/08/vbd-value-based-drafting/)

______________________________________________________________________

## Model vs. Market Pricing

### Overview

Market inefficiencies exist when crowd valuations (ADP, dynasty trade values) diverge from model-based projections. Identifying and exploiting these gaps creates competitive advantage.

### Model-Based Approaches

#### Draft Sharks 3D Values+

**Methodology:**

1. **Baseline:** Weighted average of current year projection + last 2 seasons
2. **Forecasting:** ML-driven projections for 3-year, 5-year, 10-year windows
3. **Aging curves:** Position-specific performance decline rates (1999-present data)
4. **Retirement rates:** Probabilistic career length modeling
5. **Aggregation:** Weighted average of 1-yr, 3-yr, 5-yr, 10-yr projections

**Formula (conceptual):**

```
3D_Value = w1×Proj_1yr + w3×Proj_3yr + w5×Proj_5yr + w10×Proj_10yr

Where weights (w) vary by:
- Position
- Player age
- League format (redraft vs dynasty)
```

**Example weights:**

- 24-year-old WR: [0.2, 0.3, 0.3, 0.2] (balanced)
- 29-year-old RB: [0.5, 0.3, 0.15, 0.05] (near-term heavy)
- 22-year-old rookie: [0.1, 0.2, 0.3, 0.4] (long-term heavy)

#### PFF Dynasty Values

**Methodology:**

- Top player/pick in each category = 100
- All others scaled proportionally
- Updated regularly based on PFF projections + expert consensus

**Scaling formula:**

```
Player_Value = (Player_Projection / Top_Player_Projection) × 100
```

### Market-Based Approaches

#### KeepTradeCut (Crowdsourced)

**Methodology:**

- Users vote on head-to-head player comparisons
- Elo-style rating system determines relative values
- Real-time updates from thousands of votes
- Pure market sentiment capture

**Strengths:** Reflects actual trade market
**Weaknesses:** Lags behind real performance changes, groupthink bias

#### Peaked in High School (Hybrid)

**Methodology:**
Blends three signals:

1. Dynasty ADP data
2. Expert consensus rankings
3. Real user-submitted trade data

**Advantage:** Balances expert analysis with market reality

### Identifying Inefficiencies

#### Early-Season Production vs. Talent

**Pattern:** Players with "fluky" early success become overpriced relative to sustainable talent.

**Example:**

```
Player X: 3 weeks of 20+ PPG on 3 TDs/game (unsustainable)
Model value: 6,000 (expects TD regression)
Market value: 9,500 (recency bias)
→ SELL opportunity
```

#### Injury Recovery Lag

**Pattern:** Market undervalues elite players returning from injury.

**Example:**

```
Elite WR1 returning from torn ACL (week 12)
Model value: 8,500 (projects WR1 return)
Market value: 5,000 (injury concern discount)
→ BUY opportunity
```

#### Age-Based Market Overreactions

**Pattern:** Market overweights single down year for older players.

**Example:**

```
30-year-old WR, down year (QB change, injury)
Model value: 6,000 (aging curve + talent)
Market value: 3,500 (age panic)
→ BUY if situation improves
```

#### Positional Scarcity Timing

**Pattern:** Market undervalues positions during weak draft classes.

**Example:**

```
Weak TE rookie class → veteran TE values spike
Model: Gradual adjustment
Market: Overreaction to draft prospects
→ Trade timing opportunity
```

### Quantifying Model-Market Gaps

**Gap Size Formula:**

```
Gap_% = (Model_Value − Market_Value) / Market_Value × 100

Gap > +25% → Strong BUY signal
Gap < −25% → Strong SELL signal
Gap ±10% → Fair value (hold)
```

### Strengths

- Systematic identification of trading edges
- Exploits behavioral biases (recency, loss aversion)
- Quantifiable buy/sell signals
- Can be automated with data feeds

### Limitations

- Models require accurate inputs (projections, aging curves)
- Market can remain "wrong" longer than expected
- Liquidity constraints (finding trade partners)
- Regression to mean takes time (multiple seasons)

### Sources

- [Draft Sharks - Dynasty Trade Value Chart](https://www.draftsharks.com/trade-value-chart/dynasty/ppr)
- [Peaked in High School - Dynasty Trade Values](https://peakedinhighskool.com/dynasty-trade-value-charts/)
- [KeepTradeCut - Dynasty Trade Calculator](https://keeptradecut.com/trade-calculator)

______________________________________________________________________

## Sustainable vs. Fluky Performance

### Overview

Distinguishing signal from noise is critical for valuation. Some performance is skill-based and repeatable; other performance is variance-driven and regresses to the mean.

### Key Concepts

#### Regression to the Mean

**Definition:** Extreme outcomes tend to move toward average over time.

**Statistical Basis:** Performance = Skill + Luck

- Skill is stable
- Luck is random and mean-reverts

### Touchdown Regression

#### Expected Touchdowns (xTD)

**Methodology:**
Calculate TD probability for each touch based on:

- Field position (red zone, goal line)
- Down and distance
- Play type
- Historical conversion rates

**Example:**

```
RB receives:
- 10 carries from the 1-yard line → 0.6 xTD each = 6.0 xTD
- 50 carries from the 20-yard line → 0.05 xTD each = 2.5 xTD
─────────────────────────────────────────────────────────
Total: 8.5 expected TDs

Actual TDs: 14
Touchdowns Over Expected (TDOE): +5.5
```

**Interpretation:** Player is likely overachieving; expect 5-6 fewer TDs next season.

#### Statistical Evidence

**Quarterbacks:**

- 72.9% of QB overachievers → TD rate drops next year (avg −0.9 PPG)
- 90.2% of outlier overachievers → TD rate drops (avg −1.5 PPG)

**Wide Receivers:**

- 89.7% of WRs with positive TDOE → decline in efficiency next season
- 92.5% of WRs with negative TDOE → improvement next season

**Historical Regression Rates:**

- Top 25 positive TDOE seasons → only 1 player improved next year
- Average decline: 52% fewer TDs
- Bottom 25 negative TDOE seasons → 18/25 improved
- Average improvement: 63% more TDs

**Key Insight:** "Touchdowns are extremely valuable in fantasy football, but touchdowns are also rare events, mostly random, and extremely hard to predict."

### Expected Fantasy Points (xFP)

#### Methodology

Calculate expected points based on usage quality:

**Factors weighted:**

- **Location:** Red zone opportunities worth more
- **Down/distance:** 3rd-and-short carries more valuable
- **Depth of target (air yards):** Deep targets higher xFP
- **Play type:** Pass vs. run expected values
- **Field position:** Goal-to-go vs. midfield

**Formula (conceptual):**

```
xFP = Σ(Opportunity_i × Expected_Value_i)

Where Expected_Value considers:
- Historical PPG by situation
- League scoring settings
- Position-specific baselines
```

#### Fantasy Points Over Expected (FPOE)

**Formula:**

```
FPOE = Actual_Fantasy_Points − Expected_Fantasy_Points
```

**Interpretation:**

- **Positive FPOE:** Player is efficient (skill or luck?)
- **Negative FPOE:** Player is inefficient (skill or bad luck?)

**Regression Principle:**

- Large positive FPOE → expect decline (unless skill-driven)
- Large negative FPOE → expect improvement (unless talent issue)

**Example:**

```
RB-A: 250 actual FP, 200 xFP → FPOE = +50 (regression candidate)
RB-B: 200 actual FP, 200 xFP → FPOE = 0 (sustainable)
RB-C: 150 actual FP, 200 xFP → FPOE = −50 (buy-low candidate)
```

### Sticky vs. Fluky Metrics

#### Sticky (Predictive) Metrics

**High Year-Over-Year Correlation (r² > 0.5):**

| Metric                           | Correlation | Why It's Sticky         |
| -------------------------------- | ----------- | ----------------------- |
| **Targets**                      | 0.65        | Team-driven role        |
| **Opportunity Share**            | 0.62        | Coaching/talent         |
| **Target Share**                 | 0.60        | Receiver role stability |
| **TPRR (Targets Per Route Run)** | 0.65        | QB trust, route tree    |
| **YPRR (Yards Per Route Run)**   | 0.58        | Route-running skill     |
| **Air Yards**                    | 0.55        | Role in offense         |

#### Fluky (Non-Predictive) Metrics

**Low Year-Over-Year Correlation (r² < 0.4):**

| Metric                  | Correlation | Why It's Fluky                 |
| ----------------------- | ----------- | ------------------------------ |
| **Touchdowns**          | 0.30        | Red zone variance, game script |
| **TD Rate**             | 0.25        | Small sample, randomness       |
| **Yards After Contact** | 0.40        | Defender quality variance      |
| **Broken Tackles**      | 0.38        | Situation-dependent            |

**Key Finding:** "Fantasy points per game from one season to the next has r² = 0.59" — meaning 59% explained by prior year, 41% is new variance.

### Volume is King

**Principle:** Opportunity metrics predict future performance better than efficiency metrics.

**Evidence:**

- Targets are more predictive than yards per target
- Carries are more predictive than yards per carry
- Opportunity share is more predictive than FPOE

**Practical Application:**

```
WR-A: 120 targets, 1,200 yards, 6 TDs (10 yds/tgt)
WR-B: 80 targets, 1,100 yards, 9 TDs (13.75 yds/tgt)

Despite similar raw stats, WR-A has better outlook:
- Higher volume (120 vs 80) is stickier
- WR-B's efficiency likely regresses
- WR-A's 6 TDs likely increases with volume
```

### Consistency Metrics

#### Coefficient of Variation (CV)

**Formula:**

```
CV = Standard_Deviation / Mean

Lower CV = more consistent scoring
```

**Positional Baselines:**

- QBs: 0.36 (most consistent)
- RBs: 0.54
- WRs: 0.58
- TEs: 0.63 (most volatile)

**Application:**

```
Player-A: 15 PPG ± 3 → CV = 3/15 = 0.20 (excellent)
Player-B: 15 PPG ± 8 → CV = 8/15 = 0.53 (average)

For WAR/win-focused formats, Player-A more valuable despite equal mean.
```

**Interpretation:**

- CV < 0.30: Excellent consistency
- CV 0.30-0.50: Above-average consistency
- CV 0.50-0.70: Average consistency
- CV > 0.70: Boom/bust player

### Strengths

- Separates skill from luck
- Identifies buy-low/sell-high opportunities
- Prevents overpayment for variance-driven outliers
- Grounded in statistical theory

### Limitations

- Requires large sample sizes (minimum 1 season)
- Context changes (new team, injury) invalidate historical patterns
- Skill development (young players) vs. regression is difficult to distinguish
- Advanced metrics require subscription data (Next Gen Stats, PFF)

### Sources

- [FanDuel Research - Touchdown Regression Analysis](https://www.fanduel.com/research/touchdown-regression-what-it-is-and-how-to-use-it-for-player-prop-bets-fantasy-football)
- [Fantasy Footballers - Expected Fantasy Points Primer](https://www.thefantasyfootballers.com/dfs/fantasy-football-expected-points-opportunity-the-2023-primer/)
- [SMU Data Science Review - Predicting Top 12 Fantasy Players](https://scholar.smu.edu/cgi/viewcontent.cgi?article=1279&context=datasciencereview)
- [Dynasty League Football - Using Coefficient of Variation](https://dynastyleaguefootball.com/2017/11/25/using-coefficient-variation-consistency-help-weekly-decisions/)

______________________________________________________________________

## Advanced Predictive Metrics

### Receiving Metrics

#### Target Share

**Definition:** Percentage of team passing targets directed at a player.

**Formula:**

```
Target_Share = Player_Targets / Team_Total_Targets × 100
```

**Predictive Power:** r² = 0.60 year-over-year

**Benchmarks:**

- Elite (WR1): 25%+
- Strong (WR2): 18-25%
- Flex: 12-18%
- Depth: \<12%

#### Air Yards

**Definition:** Total distance the ball travels in the air on targets.

**Formula:**

```
Air_Yards = Σ(Distance from LOS to target point)
Completed_Air_Yards = Total_Receiving_Yards − Yards_After_Catch
```

**Interpretation:**

- High air yards = downfield role
- aDOT (average depth of target) = Air_Yards / Targets

**Usage:** Leading indicator of role; compares to actual yards to identify efficiency.

#### Yards Per Route Run (YPRR)

**Definition:** Receiving yards divided by routes run.

**Formula:**

```
YPRR = Total_Receiving_Yards / Routes_Run
```

**Why It Matters:**

- Controls for snap count/playing time
- More predictive than yards per target
- Measures true efficiency

**Benchmarks:**

- Elite: 2.5+ YPRR
- Good: 1.8-2.5 YPRR
- Average: 1.2-1.8 YPRR
- Poor: \<1.2 YPRR

#### Targets Per Route Run (TPRR)

**Definition:** Targets divided by routes run.

**Formula:**

```
TPRR = Targets / Routes_Run
```

**Predictive Power:** r² = 0.65 (excellent)

**Why It's Sticky:** Reflects QB trust and route tree role independent of playing time.

**Benchmarks:**

- Elite: 0.25+ (1 target per 4 routes)
- Good: 0.20-0.25
- Average: 0.15-0.20
- Poor: \<0.15

#### WOPR (Weighted Opportunity Rating)

**Definition:** Combines target share and air yards share.

**Formula:**

```
WOPR = (1.5 × Target_Share + 0.7 × Air_Yards_Share) / 2.2
```

**Interpretation:**

- Emphasizes target volume (1.5x weight)
- Includes downfield role (0.7x weight)
- Highly predictive of fantasy output

**Benchmarks:**

- Elite: 20%+
- Good: 15-20%
- Flex: 10-15%
- Depth: \<10%

### Running Back Metrics

#### Opportunity Share

**Definition:** Percentage of team RB touches (carries + targets).

**Formula:**

```
Opportunity_Share = (Player_Carries + Player_Targets) /
                    (Team_RB_Carries + Team_RB_Targets) × 100
```

**Benchmarks:**

- Workhorse (RB1): 70%+
- Committee lead: 50-70%
- Split backfield: 30-50%
- Change-of-pace: \<30%

#### Weighted Opportunities

**Definition:** Adjusts raw opportunities by expected fantasy value.

**Conceptual Formula:**

```
Weighted_Opp = Carries × Carry_Weight + Targets × Target_Weight

Where weights reflect:
- Targets worth ~2.7x carries in PPR
- Red zone touches worth more
- Goal-line touches worth most
```

**Application:** Better predictor than raw touch count for fantasy points.

### Efficiency Metrics (Use Cautiously)

#### Yards After Contact (YAC)

**Definition:** Yards gained after first defender contact.

**Predictive Power:** Moderate (r² ≈ 0.40)

**Caution:** Somewhat sticky for elite players but varies with blocking, opponent quality.

#### Broken Tackles

**Predictive Power:** Low-moderate (r² ≈ 0.38)

**Caution:** High variance year-over-year; use as descriptor, not predictor.

### Summary: Metric Hierarchy

**Most Predictive (Use for Projections):**

1. Opportunity metrics (targets, carries, opportunity share)
2. Volume-based roles (target share, WOPR)
3. Routes run, snaps

**Moderately Predictive (Supporting Evidence):**

1. Efficiency with volume (YPRR, TPRR)
2. Consistency (CV)
3. Air yards, aDOT

**Least Predictive (Descriptive Only):**

1. Touchdowns
2. Yards after contact
3. Broken tackles
4. Single-game performances

### Sources

- [FantasyData - Advanced RB Opportunity Share](https://fantasydata.com/advanced-fantasy-metrics-rb-opportunity-share)
- [PlayerProfiler - Advanced Stats Glossary](https://www.playerprofiler.com/terms-glossary/)
- [RotoWire - WR Trade Value Metrics](https://www.rotowire.com/football/article/fantasy-football-wide-receiver-trade-value-metrics-96090)
- [Fantasy Points - Most Important WR Stats](https://www.fantasypoints.com/nfl/articles/2023/fantasy-points-data-most-important-wr-stats)

______________________________________________________________________

## Dynasty-Specific Frameworks

### Aging Curves

**Purpose:** Project career arc to value multi-year production.

#### Running Backs

**Career Arc:**

- **Year 1:** 88% of career baseline
- **Years 2-6:** Peak production (relatively flat)
- **Year 7+:** Steep decline begins

**Age-Based Peaks:**

- Best year: Age 26
- Roughly peak: Ages 24-28
- Decline phase: 28+
- Rushing EPA: Plummets post-28 (steepest drop of any position)

**Dynasty Implication:**

```
Value_Discount_Rate = 15-20% per year after age 27

27-year-old RB worth ~50% of 24-year-old with equal current production
```

#### Wide Receivers

**Career Arc:**

- **Year 1:** 74% of career baseline
- **Year 2:** Exceed career average, continue climbing
- **Year 5:** Peak season
- **Year 6+:** Steady decline
- **Year 8+:** Below career baseline

**Age-Based Peaks:**

- Prime begins: Age 25
- Absolute peak: Ages 26-28
- Decline: 29+

**Dynasty Implication:**

```
Value_Discount_Rate = 8-12% per year after age 28

Longer shelf life than RBs; less age penalty
```

#### Tight Ends

**Career Arc:**

- **Year 1:** 33% of career baseline (slowest start)
- **Year 2:** 94% of career baseline (massive sophomore jump: +98.5% PPG increase)
- **Years 3-4:** Hover around baseline
- **Years 5-6:** Peak seasons

**Dynasty Implication:**

```
Rookie TEs: Minimal value (wait 2 years)
2nd-year TEs: Buy-low window (market lags breakout)
Year 5-6 TEs: Peak value
```

#### Quarterbacks

**Career Arc:**

- Efficiency rising: Age 25+
- Peak: Ages 28-33 (longest peak of any position)
- Can maintain strong EPA into mid-to-late 30s

**Dynasty Implication:**

```
Value_Discount_Rate = 5-8% per year after age 32

Longest shelf life; safe multi-year investments
```

### Multi-Year Valuation (Dynasty DCF Analog)

**Concept:** Discount future production like discounted cash flow (DCF) in finance.

**Formula:**

```
Dynasty_Value = Σ(Projected_Points_Year_i / (1 + discount_rate)^i)

Where:
- i = years from present
- discount_rate = risk + time preference
```

**Example:**

```
Player A (24-year-old WR):
Year 1: 250 pts / (1.10)^1 = 227.3
Year 2: 260 pts / (1.10)^2 = 214.9
Year 3: 270 pts / (1.10)^3 = 202.8
Year 4: 250 pts / (1.10)^4 = 170.8
Year 5: 220 pts / (1.10)^5 = 136.6
───────────────────────────────────
Total Dynasty Value: 952.4

Player B (28-year-old WR):
Year 1: 280 pts / (1.10)^1 = 254.5
Year 2: 260 pts / (1.10)^2 = 214.9
Year 3: 220 pts / (1.10)^3 = 165.3
Year 4: 180 pts / (1.10)^4 = 123.0
Year 5: 100 pts / (1.10)^5 = 62.1
───────────────────────────────────
Total Dynasty Value: 819.8

Verdict: Player A worth ~16% more despite lower Year 1 projection
```

**Discount Rate Calibration:**

- Conservative leagues: 8-10%
- Standard: 10-12%
- Aggressive/win-now: 12-15%

### Rookie Evaluation Metrics

#### Breakout Age

**Definition:** Age when player first achieves 20% dominator rating.

**Formula:**

```
Breakout_Age = Age when (TD_Share + Yards_Share) / 2 ≥ 20%
```

**Benchmarks:**

- Elite predictor: Age ≤19
- Good: Age 20
- Average: Age 21
- Concern: Age 22+

**Why It Matters:** Early production indicates advanced development, higher NFL ceiling.

#### Dominator Rating

**Definition:** Percentage of team's receiving production (yards + TDs).

**Formula:**

```
Dominator = (Player_Rec_Yards / Team_Rec_Yards × 0.5) +
            (Player_Rec_TDs / Team_Rec_TDs × 0.5)
```

**Benchmarks:**

- Elite (potential WR1): 35%+
- Strong (WR2 potential): 25-35%
- Flex potential: 20-25%
- Red flag: \<20%

**Why It Matters:** Demonstrates ability to dominate touches in college; correlates with NFL alpha.

#### Combined Application

**Optimal Profile:**

- Breakout age ≤20
- Dominator rating ≥30%
- PFF grade ≥85

**Historical Success Rate:**

- Players meeting all three: 65% hit rate (WR2+ career)
- Players meeting none: 15% hit rate

### Draft Pick Valuation

**Age-Adjusted Value Curve:**

```
Pick Value = Base_Value × (1 + Prospect_Class_Strength) × Age_Modifier

Where Age_Modifier:
- 1st Round: 1.0 (immediate impact)
- 2nd Round: 0.6 (year 2-3 breakout)
- 3rd Round: 0.3 (lottery ticket)
```

**Positional Value by Round:**

| Round     | RB Value | WR Value | QB Value (1QB) | TE Value |
| --------- | -------- | -------- | -------------- | -------- |
| Early 1st | 100      | 95       | 60             | 70       |
| Mid 1st   | 85       | 90       | 50             | 60       |
| Late 1st  | 75       | 80       | 40             | 50       |
| Early 2nd | 50       | 60       | 25             | 35       |

**Superflex Adjustments:**

- Multiply QB values by 1.8-2.0
- Top 3 picks often QBs in Superflex

### Strengths

- Accounts for career longevity
- Quantifies age/development risk
- Systematic rookie evaluation
- Enables player-pick trade comparisons

### Limitations

- Requires accurate aging curve assumptions
- Draft pick value highly class-dependent
- Breakout age/dominator won't catch late bloomers
- Multi-year projections compound error

### Sources

- [PFF - Aging Curves by Position](https://www.pff.com/news/fantasy-football-metrics-that-matter-aging-curves-by-position)
- [PFF - Predicting Rookie WRs with Dominator + Breakout Age](https://www.pff.com/news/fantasy-football-predicting-top-2021-rookie-wide-receivers-using-dominator-rating-and-breakout-age)
- [Fantasy Points - Age Curves: When Players Break Out/Fall Off](https://www.fantasypoints.com/nfl/articles/2023/age-curves-when-nfl-players-break-out-and-fall-off)
- [ESPN - What Age Do Players Peak/Decline?](https://www.espn.co.uk/fantasy/football/story/_/id/37933720/2023-fantasy-football-players-peak-decline-quarterback-running-back-wide-receiver)

______________________________________________________________________

## Implementation Guidelines

### 1. Projection System Requirements

**Minimum Viable System:**

- Rest-of-season projections for all rosterable players
- League-specific scoring calculator
- Baseline determination logic (VOLS, VORP, or BEER)
- VoR/VBD calculation pipeline

**Advanced System:**

- Multi-year projections (1, 3, 5, 10 years)
- Aging curve adjustments by position
- xFP calculation (opportunity quality)
- TD regression analysis (xTD vs actual)
- Consistency metrics (CV, weekly floors/ceilings)

### 2. Data Sources

**Free Sources:**

- **nflverse** (via nflreadpy): Play-by-play, advanced stats
- **FantasyPros**: Consensus projections, ADP
- **Sleeper**: Dynasty ADP, league data
- **Pro Football Reference**: Historical stats, career data

**Paid/Premium Sources:**

- **PFF**: Grades, advanced receiving metrics (YPRR, TPRR)
- **Next Gen Stats**: Route data, separation metrics
- **Football Outsiders**: DVOA, opponent adjustments
- **FantasyPoints**: WAR calculations, expected points

### 3. Recommended Tech Stack

**Python Libraries:**

```python
import polars as pl           # Dataframe operations (faster than pandas)
import pyarrow as pa          # Parquet I/O
import nfl_data_py            # NFLverse data
from scipy import stats       # Statistical functions (normal dist for WAR)
import numpy as np            # Numerical operations
```

**Storage:**

- Raw data: Parquet columnar format
- Projections: JSON or Parquet with metadata
- Historical: DuckDB for analytical queries

### 4. Valuation Workflow

#### Step 1: Gather Projections

```python
# Combine multiple projection sources
projections = merge_projections([
    fantasypros_consensus(),
    pff_projections(),
    internal_model()
])
```

#### Step 2: Calculate Baselines

```python
def calculate_baselines(league_config):
    """
    league_config: {teams: 12, roster: {QB: 1, RB: 2, WR: 3, TE: 1, FLEX: 1}}
    """
    baselines = {}
    baselines['QB'] = league_config['teams'] * league_config['roster']['QB']  # QB12
    baselines['RB'] = league_config['teams'] * league_config['roster']['RB']  # RB24
    baselines['WR'] = league_config['teams'] * league_config['roster']['WR']  # WR36
    baselines['TE'] = league_config['teams'] * league_config['roster']['TE']  # TE12
    return baselines
```

#### Step 3: Calculate VoR

```python
def calculate_vor(projections, baselines):
    vor = []
    for pos in ['QB', 'RB', 'WR', 'TE']:
        # Get replacement-level projection
        replacement = projections.filter(
            pl.col('position') == pos
        ).sort('projected_points', descending=True)[baselines[pos] - 1]['projected_points']

        # Calculate VoR for all players
        pos_vor = projections.filter(
            pl.col('position') == pos
        ).with_columns(
            (pl.col('projected_points') - replacement).alias('vor')
        )
        vor.append(pos_vor)

    return pl.concat(vor).sort('vor', descending=True)
```

#### Step 4: Dynasty Adjustments

```python
def calculate_dynasty_value(player, discount_rate=0.10):
    """Multi-year NPV calculation"""
    total_value = 0
    for year in range(1, 6):  # 5-year window
        # Apply aging curve
        age_adjustment = get_aging_adjustment(player['position'], player['age'], year)
        projected_points = player[f'year_{year}_proj'] * age_adjustment

        # Discount to present value
        discounted_value = projected_points / ((1 + discount_rate) ** year)
        total_value += discounted_value

    return total_value
```

### 5. Integration with League Data

**Roster Evaluation:**

```python
def evaluate_roster(roster, projections):
    """Calculate total team VoR and expected wins"""
    starters = select_optimal_lineup(roster, projections)
    total_vor = sum([p['vor'] for p in starters])
    expected_ppg = sum([p['projected_points'] for p in starters]) / 17
    return {
        'total_vor': total_vor,
        'expected_ppg': expected_ppg,
        'expected_wins': calculate_expected_wins(expected_ppg)
    }
```

**Trade Analyzer:**

```python
def analyze_trade(give, get, roster, projections):
    """Compare roster before/after trade"""
    current = evaluate_roster(roster, projections)

    new_roster = roster.copy()
    new_roster = [p for p in new_roster if p not in give] + get
    new_state = evaluate_roster(new_roster, projections)

    return {
        'vor_change': new_state['total_vor'] - current['total_vor'],
        'win_change': new_state['expected_wins'] - current['expected_wins'],
        'recommendation': 'ACCEPT' if new_state['total_vor'] > current['total_vor'] else 'REJECT'
    }
```

### 6. Testing and Validation

**Backtesting:**

- Calculate VoR/VBD rankings for previous seasons
- Compare to actual fantasy outcomes
- Measure predictive accuracy (R², RMSE)
- Iterate on baseline selection and adjustments

**Sensitivity Analysis:**

- Vary discount rates (8%, 10%, 12%, 15%)
- Test different baselines (VOLS vs VORP vs BEER)
- Adjust aging curves by ±10%
- Identify which parameters most affect rankings

**Calibration:**

```python
def backtest_vor(historical_projections, actual_results):
    """Measure VoR predictive power"""
    for season in range(2018, 2024):
        projections = historical_projections[season]
        actuals = actual_results[season]

        vor_rankings = calculate_vor(projections, baselines)
        correlation = stats.spearmanr(vor_rankings, actuals)

        print(f"{season}: r² = {correlation.statistic ** 2:.3f}")
```

### 7. Common Pitfalls

**Overfitting on Efficiency:**

- Don't overweight FPOE, YPC, catch rate
- Focus on opportunity volume (targets, carries)

**Ignoring Context:**

- Team changes (new OC, QB, scheme)
- Injury history
- Competition (new draft picks, FA signings)

**Static Baselines:**

- Update baselines weekly during season
- Adjust for injuries (shift from RB24 to RB28 if injuries)

**Projection Anchoring:**

- Don't rely on single projection source
- Blend expert consensus with your model

### 8. Recommended Reading

**Core Texts:**

- Joe Bryant - "Principles of Value Based Drafting" (Footballguys)
- Jeff Henderson - "Fantasy WAR" series (FantasyPoints)
- Footballguys Subscribers - VBD cheat sheets and articles

**Statistical Foundations:**

- "The Signal and the Noise" - Nate Silver (regression concepts)
- "Thinking, Fast and Slow" - Daniel Kahneman (cognitive biases in valuation)

**Dynasty Resources:**

- Dynasty Nerds - Rookie rankings, trade charts
- KeepTradeCut - Crowdsourced dynasty values
- Sleeper - Dynasty ADP and league data

______________________________________________________________________

## Glossary of Abbreviations

| Term     | Full Name                           | Definition                                   |
| -------- | ----------------------------------- | -------------------------------------------- |
| **VoR**  | Value over Replacement              | Points above replacement-level baseline      |
| **VBD**  | Value-Based Drafting                | Draft strategy using VoR rankings            |
| **WAR**  | Wins Above Replacement              | Expected wins added vs. replacement          |
| **PAR**  | Performance Above Replacement       | Synonym for WAR                              |
| **VOLS** | Value Over Last Starter             | Baseline = last starting roster spot         |
| **VORP** | Value Over Replacement Player       | Baseline = best waiver player                |
| **BEER** | Best Ever Evaluation of Replacement | Baseline using man-games analysis            |
| **xFP**  | Expected Fantasy Points             | Points expected based on usage quality       |
| **FPOE** | Fantasy Points Over Expected        | Actual points − expected points              |
| **xTD**  | Expected Touchdowns                 | TD probability based on opportunity location |
| **TDOE** | Touchdowns Over Expected            | Actual TDs − expected TDs                    |
| **YPRR** | Yards Per Route Run                 | Receiving efficiency per route               |
| **TPRR** | Targets Per Route Run               | Target rate per route                        |
| **WOPR** | Weighted Opportunity Rating         | Blend of target share + air yards share      |
| **aDOT** | Average Depth of Target             | Average air yards per target                 |
| **CV**   | Coefficient of Variation            | Std dev / mean (consistency measure)         |
| **ADP**  | Average Draft Position              | Market consensus on draft timing             |

______________________________________________________________________

## Summary Comparison Matrix

| Framework          | Best For                         | Complexity | Data Required          | Dynasty-Suitable       |
| ------------------ | -------------------------------- | ---------- | ---------------------- | ---------------------- |
| **VoR**            | Draft rankings, simple valuation | Low        | Projections only       | With modifications     |
| **VBD**            | Snake draft strategy             | Medium     | Projections + ADP      | Partial (1-year focus) |
| **WAR**            | True impact, consistency value   | High       | Projections + variance | With modifications     |
| **xFP/FPOE**       | Regression analysis, buy-low     | Medium     | Play-by-play data      | Yes                    |
| **TD Regression**  | Identifying outliers             | Low        | Red zone stats         | Yes                    |
| **Aging Curves**   | Dynasty career arc               | Medium     | Historical data        | Essential              |
| **Multi-Year DCF** | Dynasty total value              | High       | Multi-year projections | Essential              |
| **Rookie Metrics** | Draft prospect evaluation        | Low        | College stats          | Essential              |

______________________________________________________________________

## Conclusion

Effective player valuation requires combining multiple frameworks:

1. **Draft/Redraft:** VBD with BEER+ baseline for optimal draft capital allocation
2. **In-Season:** xFP and TD regression to identify buy-low/sell-high opportunities
3. **Dynasty:** Multi-year DCF with aging curves for long-term value assessment
4. **Rookie Evaluation:** Breakout age + dominator rating for prospect screening
5. **Consistency:** WAR and CV for risk-adjusted valuation in win-focused leagues

**Golden Rule:** Volume (opportunity) is more predictive than efficiency. Prioritize targets, carries, and opportunity share over yards per touch or touchdown rates.

**Model-Market Synthesis:** Use quantitative models to identify mispricings in crowd-sourced values (ADP, dynasty trade charts), then exploit gaps of ±25% or more.

______________________________________________________________________

## Citations

### Primary Sources

01. Fantasy Football Analytics - [VoR and VBD Guide](https://fantasyfootballanalytics.net/2024/08/winning-fantasy-football-with-projections-value-over-replacement-and-value-based-drafting.html)
02. Footballguys - [Principles of VBD (Joe Bryant)](https://www.footballguys.com/article/bryant_vbd?article=bryant_vbd)
03. Subvertadown - [VBD Baselines Comparison](https://subvertadown.com/article/guide-to-understanding-the-different-baselines-in-value-based-drafting-vbd-vols-vs-vorp-vs-man-games-and-beer-)
04. Fantasy Footballers - [Understanding WAR/PAR](https://www.thefantasyfootballers.com/articles/on-the-warpath-understanding-performance-above-replacement-fantasy-football/)
05. FantasyPoints - [Fantasy WAR Theory](https://www.fantasypoints.com/nfl/articles/season/2021/fantasy-war-part-1-theory)
06. FanDuel Research - [Touchdown Regression Analysis](https://www.fanduel.com/research/touchdown-regression-what-it-is-and-how-to-use-it-for-player-prop-bets-fantasy-football)
07. PFF - [Aging Curves by Position](https://www.pff.com/news/fantasy-football-metrics-that-matter-aging-curves-by-position)
08. PFF - [Rookie WR Prediction (Dominator + Breakout Age)](https://www.pff.com/news/fantasy-football-predicting-top-2021-rookie-wide-receivers-using-dominator-rating-and-breakout-age)
09. SMU Data Science Review - [Predicting Top 12 Fantasy Players](https://scholar.smu.edu/cgi/viewcontent.cgi?article=1279&context=datasciencereview)
10. Dynasty League Football - [Coefficient of Variation for Consistency](https://dynastyleaguefootball.com/2017/11/25/using-coefficient-variation-consistency-help-weekly-decisions/)

### Secondary Sources

11. FantasyPros - [What is VBD?](https://www.fantasypros.com/2017/06/what-is-value-based-drafting/)
12. FantasyData - [RB Opportunity Share](https://fantasydata.com/advanced-fantasy-metrics-rb-opportunity-share)
13. PlayerProfiler - [Advanced Stats Glossary](https://www.playerprofiler.com/terms-glossary/)
14. RotoWire - [WR Trade Value Metrics](https://www.rotowire.com/football/article/fantasy-football-wide-receiver-trade-value-metrics-96090)
15. Draft Sharks - [Dynasty Trade Value Chart](https://www.draftsharks.com/trade-value-chart/dynasty/ppr)
16. KeepTradeCut - [Dynasty Trade Calculator](https://keeptradecut.com/trade-calculator)
17. Peaked in High School - [Dynasty Trade Values](https://peakedinhighskool.com/dynasty-trade-value-charts/)

______________________________________________________________________

**Document Version:** 1.0
**Last Updated:** October 29, 2025
**Maintained by:** FF Analytics Project
