# Dynasty Fantasy Football Strategy Research

**Compiled:** 2025-10-29
**Purpose:** Authoritative literature review on dynasty fantasy football strategies, player valuation frameworks, roster construction, trade evaluation, and asset management.

______________________________________________________________________

## Executive Summary

This document compiles research-backed frameworks and methodologies for dynasty fantasy football strategy. Key themes include:

1. **Player valuation** using Value over Replacement (VoR), sustainable performance metrics, and aging curves
2. **Roster construction** strategies for win-now vs. rebuild modes with competitive window analysis
3. **Trade evaluation** using multi-objective optimization and crowdsourced market values
4. **Asset management** including draft pick valuation, contract/salary cap strategies, and positional allocation

Sources range from academic research papers to industry-standard tools like KeepTradeCut, DynastyProcess, and PFF analytics.

______________________________________________________________________

## 1. Dynasty Player Valuation Frameworks

### 1.1 Value Over Replacement (VoR/VORP)

**Definition:**
Value over Replacement Player (VoR) measures a player's projected performance relative to a baseline replacement-level player at the same position, quantifying true fantasy value through relative production advantage.

**Calculation Formula:**

```
VoR = Player's Projected Points - Replacement Level Player's Projected Points
```

**Example:**

- QB projects 300 points, replacement QB = 250 → VoR = 50
- RB projects 200 points, replacement RB = 125 → VoR = 75
- The RB provides more relative value despite lower absolute scoring

**Setting the Replacement Baseline (Three Methods):**

1. **Worst Starter Method:** Use the lowest-scoring starting player at each position (straightforward comparison)
2. **Man-Games Approach:** Calculate total games needed to fill a season at each position, accounting for injuries
3. **Draft Position Method:** Set baseline using players typically drafted by round 10 or pick 100

**Key Advantage:**
VoR enables cross-positional comparison by standardizing value relative to position-specific baselines, revealing which positions offer the most competitive advantage.

**Source:**

- [Fantasy Football Analytics - Value-Based Drafting](https://fantasyfootballanalytics.net/2024/08/winning-fantasy-football-with-projections-value-over-replacement-and-value-based-drafting.html)
- [YAFSB - 2025 VORP Rankings](https://www.yafsb.com/fantasy-football/2025-vorp-rankings/)

### 1.2 Value-Based Drafting (VBD) Strategy

**Core Principle:**
Rather than filling positional needs, VBD emphasizes "assembling the highest-scoring team possible by selecting the best players available based on their projected VoR."

**Application Rules:**

1. Prioritize players with highest VoR regardless of position
2. Use "drop off" metrics to identify positions with steep value declines (prioritize early)
3. Exploit positions with gentle declines (defer to later rounds)
4. Transition to uncertainty metrics in later rounds for sleeper identification

**Drop Off Metric:**
Measures "the decline in production between players at a given position and those immediately below them," revealing tier structures and identifying when elite players provide substantial competitive advantages.

**Position-Specific Insights (2024 Projections):**

- **Quarterbacks:** Low median VoR (~25) with steep drops; secure top QBs early or wait
- **Running Backs:** High VoR with notable drops after top 5 players; prioritize early
- **Wide Receivers:** Consistent value throughout draft with gentle declines; depth available later
- **Tight Ends:** Low VoR with consistent drops; balanced approach recommended

**Source:**

- [Fantasy Football Analytics - VBD Guide](https://fantasyfootballanalytics.net/2024/08/winning-fantasy-football-with-projections-value-over-replacement-and-value-based-drafting.html)

### 1.3 Dynasty-Specific Valuation Systems

#### Draft Sharks Methodology

**Baseline Calculation:**
Starts with weighted average of:

- Current year projection
- Last two seasons of performance

**Forecasting:**
Applies 3-year, 5-year, and 10-year fantasy forecasted output using machine learning trained on all NFL data since 1999, incorporating:

- Performance aging curves
- Retirement rates by position

**Source:**

- [Draft Sharks Dynasty Trade Value Chart](https://www.draftsharks.com/trade-value-chart/dynasty/ppr)

#### PFF Valuation Approach

**Scaling Method:**
Sets the top-ranked player or pick in each category at value of 100, with all other rankings scaled proportionally.

**Source:**

- [PFF Dynasty Trade Value Chart](https://www.pff.com/news/fantasy-football-2025-dynasty-trade-value-chart)

#### DynastyProcess Methodology

**Foundation:**
Built on FantasyPros Dynasty Expert Consensus Rankings as proxy for long-term market value.

**League Assumptions:**

- Typical 12-team PPR league
- Starting lineup: QB/RB/RB/WR/WR/TE/FLEX/FLEX
- Rosters approximately 300 players

**Draft Pick Valuation:**
Rookie picks valued by taking weighted average of nth highest player's value from recent draft classes (2015-2018).

**Example:** Pick 1.03 = average value of 3rd highest ranked player from last 4 draft classes, weighted by recency.

**Future Picks:**
Valued at 80% of current year through present-value discounting.

**Customization:**
Offers controls for QB scoring, startup trade mode, rookie pick optimism, and league depth preferences.

**Source:**

- [DynastyProcess Trade Calculator](https://calc.dynastyprocess.com/)
- [DynastyProcess Pick Values Methodology](https://dynastyprocess.com/blog/2019-02-14-2019pickvalues/)

### 1.4 Sustainable vs. Fluky Performance Metrics

#### Touchdown Regression

**Key Insight:**
Touchdowns are "least sticky" statistics—highly variable year-to-year and not predictive of future performance. High/low TD totals typically regress toward the mean.

**Expected Touchdowns (xTD):**
Weighs each carry/target and converts data into single number indicating player's scoring opportunity based on usage patterns, field position, and opportunity quality.

**Touchdowns Over Expected (TDOE):**
Measures efficiency by comparing actual TDs to xTD. TDOE is volatile and subject to regression:

- Players with positive TDOE experience ~86% decline the following year
- Players with negative TDOE improve by ~93% on average

**Regression Examples (2025 Season):**

- James Cook: +6.0 TDs over expected, including scores from 65, 49, 46, and 41 yards (prime regression candidate)
- Terry McLaurin: xTD of 6.1 but scored 13 (biggest negative regression candidate at WR)

**Volume as King:**
"Volume is king in fantasy football. There is no better predictor of fantasy points over large samples."

**Sources:**

- [ESPN - Fantasy Metrics That Matter](https://www.espn.co.uk/fantasy/football/story/_/id/38069858/fantasy-football-statistics-targets-trends)
- [NBC Sports - TD Regression Candidates](https://www.nbcsports.com/fantasy/football/news/fantasy-football-2025-touchdown-regression-candidates-include-james-cook-trey-mcbride-and-more)
- [Medium - Building Better Prediction Models](https://medium.com/@ashimshock/building-a-better-fantasy-football-prediction-model-a-data-driven-approach-8730694ac40a)

#### Predictive Opportunity Metrics

**Key Leading Indicators:**

1. **Target Share:** Percentage of team targets received (highly predictive for pass-catchers)
2. **Opportunity Share:** Player's share of offensive touches (carries + targets)
3. **Snap Count:** Offensive snap participation rate

**WOPR (Weighted Opportunity Rating):**
Considered by many analysts as the most predictive statistic for evaluating receivers, combining:

- Target share
- Air yard share

These metrics are leading indicators because they tend to be more predictive of future performance than lagging stats like touchdowns.

**Source:**

- [PlayerProfiler Advanced Stats Glossary](https://www.playerprofiler.com/terms-glossary/)

### 1.5 Market Pricing Inefficiencies

**P/E Ratio Approach:**
Some analysts apply stock market concepts, calculating how much you pay for a player (draft capital, trade value) relative to their fantasy point production—similar to price-to-earnings ratios in equity investing.

**Common Market Inefficiencies:**

1. **Injury Overreactions:** Temporary injuries create buying opportunities for patient managers
2. **Offseason Pretty Roster Syndrome:** During long offseason, managers overvalue youth/upside, undervaluing proven veterans (reverses as season approaches)
3. **Recency Bias:** Recent performance (good or bad) disproportionately affects valuation
4. **Value Lag:** Changes in player value show up later in dynasty formats compared to redraft

**Value Investing Philosophy:**
"Playing Dynasty can be approached like playing the stock market, with a portfolio of investments (players) looking to maximize value and achieve superior returns by performing better than the market."

**Identifying Mispriced Players:**
Look for large gaps between:

- Predicted dynasty ADP
- Current market value (e.g., KeepTradeCut)
- Actual production metrics

**Sources:**

- [Footballguys - Dynasty Investor: Intro to Value](https://www.footballguys.com/article/2023-dynasty-investor-intro-to-value)
- [FantasyPros - Dynasty Trade Values](https://www.fantasypros.com/2025/06/dynasty-trade-values-targets-players-to-avoid-fantasy-football/)

### 1.6 Prospect Profiling Analytics

#### Dominator Rating

**Definition:**
For WR/TE: Percentage of team receiving production
For RB: Percentage of total offensive production (rushing + receiving)

**Significance:**
Identifies college players who commanded significant share of their team's production, correlating with NFL fantasy success.

#### Breakout Age

**Definition:**
Age at which a receiver first reaches 20% dominator rating.

**Significance:**
Early production (age 19 or below = excellent) indicates player will likely continue production stretch into NFL.

**Application:**
Combined with Dominator Rating, these metrics help identify rookie WR prospects most likely to succeed in dynasty formats. Incorporating PFF grades provides additional validation.

**Sources:**

- [PFF - Predicting Rookie WRs with Dominator Rating](https://www.pff.com/news/fantasy-football-predicting-top-2021-rookie-wide-receivers-using-dominator-rating-and-breakout-age)
- [PlayerProfiler - College Dominator & Breakout Age](https://www.playerprofiler.com/article/cordarrelle-patterson-advanced-stats-metrics-nfl-scouting/)
- [RotoViz - Dominator Rating and Breakout Age](https://www.rotoviz.com/2014/01/whats-this-then-dominator-rating-and-breakout-age/)

______________________________________________________________________

## 2. Roster Construction Strategies

### 2.1 Win-Now vs. Rebuild Philosophy

#### Win-Now Strategy

**Core Principle:**
Balance immediate success with long-term planning without overvaluing youth. "Production wins titles, not potential."

**Key Tactics:**

1. Prioritize proven producers over unproven rookies/prospects
2. Target players with track record of consistent production
3. Mix in younger players with upside to maintain long-term viability
4. **Critical:** Hold your draft picks—easiest and cheapest way to add youth and rejuvenate aging roster

**Timeline:**
Aim to compete immediately rather than building for distant future window.

#### Rebuild Strategy

**Core Principle:**
"A well-executed rebuild can transform a struggling roster into a future powerhouse."

**Optimal Timing:**
Decide to rebuild early—weeks 4-6 provide good temperature check. Earlier decision = better trade opportunities.

**Key Tactics:**

1. **Draft picks are lifeblood:** Accumulate multiple picks across classes
2. **Focus on 2-3 foundational pieces:** Especially QB core or elite WRs under 26
3. **Avoid RBs during rebuild:** Shortest shelf life means they'll age out before you're ready to contend (2-3 years)
4. **Build through WRs:** Longer careers and more stable value trajectory

**Modern Approach:**
"The best way to build a dynasty roster is through wide receivers, with the goal not to win now but to win a few years from now and continue doing so."

**Sources:**

- [Fantasy in Frames - Dynasty Reset Guide](https://www.fantasyinframes.com/the-dynasty-reset-rebuilding-a-fantasy-football-team-part-1/)
- [The Undroppables - Roster Construction](https://www.theundroppables.com/the-art-of-dynasty-chapter-2-roster-construction/)
- [FTN Fantasy - How to Pull Off a Rebuild](https://ftnfantasy.com/nfl/dynasty-fantasy-football-how-to-pull-off-a-rebuild)

### 2.2 Competitive Window Analysis

**Definition:**
Your team's window to compete for championships, typically 2-3 years depending on roster construction.

**Window Dynamics:**

**Typical Window:** Most managers think in terms of maximum 3-year competitive window.

**Building Windows:**

- Takes 1-2 seasons to establish direction from ground-up rebuild
- Drafting RBs early may mean missing their peak if roster isn't ready to contend

**Maximizing Windows:**
When ready to contend with quality roster, acquire young RBs via trade/draft to align with competitive window.

**Trade-offs:**
"Making a considerable push to 'win now' will disrupt the longevity of your roster, but it will maximize the shorter window of contention."

**Strategic Implications:**
Understanding when your window is open and making moves to maximize that opportunity is essential. Don't waste competitive years; equally, don't sacrifice future windows for marginal present gains.

**Sources:**

- [Fantasy Alarm - Win Now vs. Rebuilding](https://www.fantasyalarm.com/articles/nfl/dynasty-leagues/2022-fantasy-football-dynasty-leagues-win-now-vs-rebuilding/123832)
- [The Undroppables - Rebuild Roadmap](https://www.theundroppables.com/the-art-of-dynasty-chapter-18-rebuild-roadmap/)

### 2.3 Positional Allocation Strategy

#### Optimal Roster Size

**Standard Dynasty:** 25-30 total roster spots, with 27 commonly recommended

**Popular Configurations:**

- 10-team: 25 roster spots
- 14-team: 26 roster spots

#### Starting Lineup Formats

**Recommended Format 1:**

- 1 QB, 2 RB, 2 WR, 1 TE, 4 FLEX
- No kicker or defense

**Recommended Format 2 (Superflex):**

- 1 QB, 2 RB, 3 WR, 2 FLEX, 1 Superflex

**Rationale:**
"Deeper starting lineups are mandatory in dynasty leagues as they reward managers who build better rosters."

#### Position-Specific Strategies

**Quarterbacks:**

- Prioritize securing higher-level QB early (limited streaming options)
- In Superflex: QB = most valuable position
- Keep drafting QBs every year even if you have multiple

**Running Backs:**

- "Get in early and exit before decline begins"
- Teams with every-down back at reasonable price have large competitive advantage
- Top RBs have ultimate trade value in dynasty
- **Key timing:** Sell after year 4, before decline begins

**Wide Receivers:**

- Be patient with rookie WRs, look for improvement signs in year 2-3
- "Dynasty's blue-chip stocks"—hold value longer, age more gracefully
- Best position to build roster foundation

**Tight Ends:**

- Sophomore TEs show greatest year-over-year growth (98.5% increase in PPR)
- Maintain production through year 7, don't decline significantly until age 30

#### Roster Depth Guidelines

**Bye Week Coverage** (reducing issues below 10% probability):

- 1 starter position → 2 roster spots
- 2 starter positions → 4 roster spots
- 3 starter positions → 6 roster spots
- 4 starter positions → 7 roster spots

**Sources:**

- [PFF - Positional Scarcity in Dynasty](https://www.pff.com/news/fantasy-football-positional-scarcity-volatility-dynasty)
- [Footballguys - Roster Decomposition](https://www.footballguys.com/article/HarstadDiT42)
- [PFN - Optimal Dynasty Setup](https://www.profootballnetwork.com/dynasty-fantasy-football-optimal-setup-rules-and-more/)

### 2.4 Draft Strategy Philosophies

#### Zero RB Strategy

**Definition:**
Avoid RBs in first 4-5 rounds; load up on elite WRs, top QB, and strong TE before selecting RBs late.

**Philosophy:**
"Ignore running back completely in the early rounds, but stockpile backs in the later rounds—hoping that when the expected injury chaos of the position kicks in league-wide, you'll be well equipped to benefit."

**Pros:**

- Avoids high injury risk of early-round RBs
- Banks on finding late-round breakouts or waiver gems

**Cons:**

- Top RBs are gone
- Scrambling for production at scarcest position

#### Robust RB Strategy

**Definition:**
Draft multiple RBs early—pair of RBs with two of first three picks, or even first two picks.

**Philosophy:**
Traditional approach prioritizing scarcest position early to dominate that position.

#### Hero/Anchor RB Strategy

**Definition:**
Draft one elite RB in rounds 1-2, then fill out WRs, TE, QB before selecting more RBs later.

**Philosophy:**
"Middle ground between Robust RB and Zero RB." Secure one "hero" RB (top-10/12), then wait until rest of starting lineup filled.

**Key Benefits:**

- Balance—no glaring weakness at any position
- Access to RBs with incredible upside
- Mix in top-end WRs, QBs, TEs

**Flexibility:**
All three strategies have merit depending on draft flow and league dynamics.

**Sources:**

- [Fantasy Football Counselor - Ultimate RB Strategy Guide](https://thefantasyfootballcounselor.com/the-ultimate-fantasy-football-rb-draft-strategy-guide-2025-zero-rb-vs-hero-rb-vs-robust-rb/)
- [Footballguys - RB Draft Strategy Guide](https://www.footballguys.com/article/2025-fantasy-draft-strategy-guide-running-backs)

### 2.5 Startup Draft Strategy

#### Slow Draft Tactics

**Timeline:**
Dynasty startups typically use 8-hour pick timers, allowing thoughtful selections and trade negotiations.

**Advantage:**
Extra time to negotiate trades with managers during draft.

#### Tiered Rankings Approach

**Method:**
Organize personal rankings into defined tiers reflecting value and projected performance over next three seasons.

**Application:**

- Identify when to trade up (pick falls just outside tier break)
- Identify when to trade down (struggling to decide between equivalent players)

#### Golden Rule

**"Draft for value, trade for need"**

Don't draft based on need; stick to tiers, draft for value, and trade for needs later.

#### Position Priority

**Core Focus:**
Prioritize QBs and WRs (longer careers than RBs).

**Foundation:**
"Young wide receivers are typically the players you want to build around."

**Exception:**
Superflex leagues—ensure path to startable quarterbacks early.

**Sources:**

- [PlayerProfiler - Dynasty Startup Strategy](https://www.playerprofiler.com/article/dynasty-football-startup-strategy-protect-draft-picks/)
- [RotoBallers - Superflex Startup Strategy](https://www.rotoballer.com/2025-dynasty-startup-strategy-guide/1541666)

______________________________________________________________________

## 3. Trade Evaluation Methodologies

### 3.1 Crowdsourced Valuation Systems

#### KeepTradeCut (KTC) Methodology

**Core Mechanism:**
Users rank three players of similar value, designating most valuable as "Keep," second as "Trade," least valuable as "Cut."

**Data Scale:**

- 23+ million data points (and counting)
- Rankings update in real-time with every user submission

**Quality Control:**
Occasional "test" KTCs with obvious right answers to verify users are paying attention.

**Output:**
Creates fluid, market-driven valuations rather than static rankings. More frequent "Keep" votes = higher ranking.

**Advantage:**
Captures real-time market sentiment and league-wide consensus on player values.

**Source:**

- [KeepTradeCut Trade Calculator](https://keeptradecut.com/trade-calculator)
- [KeepTradeCut FAQ](https://keeptradecut.com/frequently-asked-questions)

### 3.2 Win-Win Trade Structures

#### Identifying Complementary Needs

**Principle:**
"The ideal trade candidate is with a team that is weak in a position that you may be strong in, so both teams can benefit from a trade."

**Targeting:**
Seek teams that are heaviest where you're lightest—"these trades benefit everyone equally, regardless of overall roster construction."

#### Even Swap Strategy

**Definition:**
Send two players, get two players back.

**Benefit:**
"Most of the time these trades benefit both teams by addressing both teams' specific needs." Made to help both teams' long-term goals, making them appealing.

#### Account for Team Timelines

**Age Factor:**
If rebuilding, trade RBs for WRs—"wide receivers tend to hold their value longer in dynasty than running backs do."

Conversely, contending teams should target RBs by sending future-focused assets.

#### Quantity vs. Quality Premium

**2-for-1 or 3-for-2 Trades:**
Side sending more players needs to overpay to smaller side.

**Example:**
Trading for player with value of 75, sending 2 players? They likely need combined value of 98-113 (30-50% premium).

**Rationale:**
Consolidating value into elite player requires premium because elite players are scarcer and provide competitive advantages.

#### Avoid Lopsided Offers

"Sending lopsided or nonsense trades that aren't helping both sides win, wastes time."

Shoot your shot, but understand league landscape and create mutually beneficial structures.

**Sources:**

- [Footballguys - Flexibility Has Value](https://www.footballguys.com/article/2023-dynasty-in-theory-67-flexibility-has-value)
- [Dynasty Football Factory - Trade Enthusiast Manifesto](https://dynastyfootballfactory.com/manifesto-of-a-trade-enthusiast/)

### 3.3 Multi-Objective Optimization Considerations

**Dimension 1: Current Year Value**
How much does this trade improve my starting lineup for this season?

**Dimension 2: Future Value**
How does this affect my team's outlook 1-3 years from now?

**Dimension 3: Competitive Window Alignment**
Does this trade align with my team's timeline (contending vs. rebuilding)?

**Dimension 4: Positional Scarcity**
Am I trading for/away from a scarce position where replacement options are limited?

**Dimension 5: Market Timing**
Is this player's value at peak (sell high) or trough (buy low)?

**Balancing Act:**
Successful dynasty trades rarely optimize just one dimension. Best trades create win-win scenarios where both sides improve along different dimensions aligned with their team situations.

### 3.4 Manager Profiling

While not extensively documented in sources, manager profiling involves understanding:

**Risk Tolerance:**
Some managers overvalue safety (proven veterans), others chase upside (rookies/prospects).

**Position Preferences:**
Managers often overvalue certain positions or roster construction philosophies.

**Timeline Awareness:**
Identify managers who don't recognize their competitive window (rebuilding team holding aging assets, or contending team holding distant-future picks).

**Trade Frequency:**
Active traders vs. passive roster builders respond differently to offers.

**Market Knowledge:**
Less engaged managers may not track player value changes, creating arbitrage opportunities.

______________________________________________________________________

## 4. Asset Management

### 4.1 Draft Pick Valuation

#### Value by Round

**First Round Picks:**
Carry most value but not guaranteed "hits." Sometimes trading pick is more beneficial depending on draft position.

**Hit Rate Context:**
First-round picks have highest success rates, but managers often overvalue them relative to proven players at similar value tiers.

**Second Round Picks:**

- Hit rates drop to 22%
- Miss rates skyrocket to 69%
- Still hold significant trade value due to upside potential

**Third Round and Later:**
Much lower value with very low hit rates. Often referred to as "dart throws."

#### Valuation Methodologies

**Average Startup Pick Valuation (ASPV) Model:**
Collected rookie ADP data from multiple providers over 11 years (2013-2023), averaged to create standard values for each rookie draft pick.

**Limitation:**
Only measures perceived value based on where dynasty managers draft rookies, not actual hit rates.

**Historical Averaging Method (DynastyProcess):**
Pick value = average current valuation of best players from recent draft classes (2015-2018) at each pick position.

**Example:**
1.10 pick value = average of current 10th best players from 2015, 2016, 2017, 2018 classes.

**Purpose:**
Determines "absolute maximum a pick should be worth" by capturing owner optimism and upside framing.

#### Strategic Timing Considerations

**Before NFL Draft:**
Trading picks means giving up mystery and hype before it peaks. Values often highest in weeks leading up to NFL Draft.

**After NFL Draft:**
Market typically cools as landing spots become known and hype consolidates around clear winners.

**During Season:**
Pick values fluctuate based on team performance (early picks become more valuable as teams fall out of contention).

#### NFL Draft Capital Consideration

**High Draft Capital:**
NFL teams using high picks indicates team faith and opportunity, warranting rise in dynasty rankings for those prospects.

**Source Impact:**
Where NFL teams draft players significantly affects dynasty value—1st round NFL pick at position carries premium over day 3 pick.

**Sources:**

- [RotoBallers - How to Value Dynasty Picks](https://www.rotoballer.com/dynasty-primer-1-how-to-value-dynasty-draft-picks/1343067)
- [Dynasty Nerds - Draft Pick Values](https://www.dynastynerds.com/dynasty/dynasty-trade-secrets-understanding-draft-pick-values/)
- [DynastyProcess - Pick Values Methodology](https://dynastyprocess.com/blog/2019-02-14-2019pickvalues/)

### 4.2 Contract & Salary Cap Strategies

#### What is Salary Cap Dynasty?

**Core Requirements:**

1. Pay salary to each player on roster
2. All players must have contracts in years
3. Restraint on total salary (salary cap)

**Alternative Name:**
Often called "Contract Leagues" due to dual components.

#### Dead Cap Strategy

**Key Principle:**
"In general, teams will not move on from players where the dead cap hit is higher than the actual cap hit."

**Dead Money Penalty:**
Releasing player with multiple years remaining on contract counts against salary cap as "dead money."

**Strategic Calculation:**
Use sites like Spotrac or OverTheCap to compare:

- Player's dead cap
- Current salary
- Difference = cap savings

**Rule of Thumb:**
Only cut players when cap savings exceed dead cap penalty.

#### Contract Structure Strategy

**Long Contracts to Expensive Players = Extremely Risky**
They cost more each season in future, limiting flexibility.

**Alternative Strategy:**
Give long contracts to less proven/cheaper players you think will break out. If right, you lock in value below market rate.

**NFL Signal:**
"Players who receive sizable guarantees will receive opportunities on the field."

Track real NFL guarantees for signals about opportunity and role security.

#### Dynasty Value Differences

**Critical Insight:**
"When salaries and contracts are introduced, that changes the entire dynamic of a player's value compared to traditional dynasty leagues."

**Examples:**

- Expensive veteran on long contract has lower dynasty value (cap burden)
- Cheap young player on short contract has higher value (flexibility + potential)
- Players on expiring contracts become more valuable if they'll reset to cheap salaries

**Complexity Level:**
These leagues require thinking like real NFL GMs, balancing present competitiveness with long-term cap health.

**Sources:**

- [Dynasty Football Factory - Dynasty and Salary Cap](https://dynastyfootballfactory.com/dynasty-and-the-nfl-salary-cap/)
- [Dynasty League Football - Salary Cap Confidential](https://dynastyleaguefootball.com/2019/05/05/salary-cap-confidential-introduction/)
- [League Tycoon - Contract Leagues Guide](https://leaguetycoon.com/contract-leagues/)

### 4.3 Player Aging Curves by Position

#### Running Backs

**Career Arc:**

- Rookie season: 88% of baseline average
- Year 7: First season production dips below career baseline
- Year 8: Distribution of outcomes spreads dramatically

**Key Insight:**
"Shortest shelf-life among fantasy positions with significant decline after rookie contract."

**Dynasty Strategy:**
"Wise to move off older backs in dynasty before the decline, while their value is highest (typically after year four)."

#### Wide Receivers

**Career Arc:**

- Rookie season: 74% of baseline average
- Year 2-3: Significant improvement (sophomore surge)
- Year 5: Peak production year
- Maintain production into late 20s

**Key Insight:**
"Hold value longer and age more gracefully than RBs."

**Dynasty Strategy:**
Be patient with rookie WRs, look for improvement signs in years 2-3.

#### Tight Ends

**Career Arc:**

- Rookie season: 33% of baseline average
- Sophomore season: 94% of baseline (98.5% PPR increase from rookie year)
- Maintain average through year 7
- Don't decline significantly until age 30

**Key Insight:**
"Second-year tight ends show the greatest pattern of year-over-year growth across any skill position."

**Dynasty Strategy:**
Don't give up on rookie TEs; expect major year 2 jump.

#### Quarterbacks

**Career Arc:**

- Efficiency steadily rises starting age 25
- Peak between ages 28-33
- Many QBs produce strong EPA into mid-to-late 30s

**Key Insight:**
Most stable position for aging; many maintain performance well into 30s.

**Dynasty Strategy:**
Can safely roster older QBs for win-now pushes.

#### Alternative Framework: Mortality Tables (Adam Harstad)

**Core Thesis:**
Players don't gradually decline; they either maintain performance or "fall off a cliff."

**Evidence:**
Study of 100 retired elite RBs/WRs found exactly 50% declined in final fantasy-relevant season—no different from random chance.

**Implication:**
"Death rates (75%+ production drops) rise consistently across ages, while non-bust performers maintain relatively stable output until retirement."

**Practical Application:**
Rather than projecting "50% of typical Frank Gore," better to think "50/50 shot at getting 100% of typical Frank Gore."

**Reframe:**
Player valuation should focus on survival probability rather than gradual erosion, making aging players simultaneously safer (if they survive) and riskier (if they don't) than traditional aging curves suggest.

**Sources:**

- [PFF - Aging Curves by Position](https://www.pff.com/news/fantasy-football-metrics-that-matter-aging-curves-by-position)
- [Dynasty Edge - Age Curve Study](https://thedynastyedge.com/2025/06/21/nfl-age-curve-study-epa-trends-by-position-rb-wr-te-qb-fantasy-football-analysis-2014-2024/)
- [Footballguys - Adam Harstad Mortality Tables](https://www.footballguys.com/article/HarstadMortalityTables)
- [ESPN - When Players Peak/Decline](https://www.espn.co.uk/fantasy/football/story/_/id/37933720/2023-fantasy-football-players-peak-decline-quarterback-running-back-wide-receiver)

______________________________________________________________________

## 5. Academic & Analytical Research

### 5.1 Academic Papers

#### SMU Data Science Review (2024)

**Focus:**
Computational methods to enhance predictive capabilities in fantasy football analytics.

**Methods:**
Evaluated models including Boosting Regressor based on mean squared error (MSE).

**Source:**

- [SMU Data Science Review](https://scholar.smu.edu/cgi/viewcontent.cgi?article=1279&context=datasciencereview)

#### MIT Project - Interactive Tools for FF Analytics

**Focus:**
Constructing robust predictive models for individual football players.

**Innovation:**
Explores statistics at finer granularity than existing macro-level data tools.

**Coverage:**
Various machine learning techniques for QBs, RBs, WRs, TEs, and kickers.

**Source:**

- [MIT DSpace](https://dspace.mit.edu/handle/1721.1/100687)

#### UC Denver - Fantasy Football Analytics Capstone

**Method:**
Prediction algorithm utilizing machine learning for expected fantasy points.

**Techniques:**
Linear regression and gradient descent models.

**Source:**

- [UC Denver Capstone](https://engineering.ucdenver.edu/current-students/capstone-expo/archived-expos/spring-2020/computer-science/csci15-fantasy-football-analytics)

#### University of New Hampshire - Predictive Analytics Study

**Focus:**
Statistical modeling and machine learning approaches to fantasy football predictions.

**Source:**

- [UNH Scholars Repository](https://scholars.unh.edu/cgi/viewcontent.cgi?article=1418&context=honors)

### 5.2 Academic Textbook

**Title:** Fantasy Football Analytics: Statistics, Prediction, and Empiricism Using R

**Author:** Isaac T. Petersen (2025)

**Format:** Open-access textbook

**Purpose:** Teaches statistics, prediction, and empiricism through fantasy football context.

**Source:**

- [Fantasy Football Analytics Textbook](https://isaactpetersen.github.io/Fantasy-Football-Analytics-Textbook/)

### 5.3 Advanced Research Methodologies

#### Transformer-Based Sentiment Analysis

**Research:** Fantasy Premier League study using transformer-based sentiment analysis on news and statistical data.

**Results:** 63.18% accuracy, showing 6.9% boost over traditional statistical methods alone.

**Implication:**
Incorporating natural language processing of news/social media can improve predictions beyond purely statistical models.

**Source:**

- [ResearchGate - FPL Prediction Study](https://www.researchgate.net/publication/391452336_Players'_Performance_Prediction_for_Fantasy_Premier_League_Using_Transformer-based_Sentiment_Analysis_on_News_and_Statistical_Data)

______________________________________________________________________

## 6. Key Tools & Resources

### 6.1 Trade Calculators

| Tool                         | Methodology                        | Key Features                                      |
| ---------------------------- | ---------------------------------- | ------------------------------------------------- |
| **KeepTradeCut**             | Crowdsourced (23M+ data points)    | Real-time market values, dynasty rankings         |
| **DynastyProcess**           | FantasyPros consensus + historical | Customizable (QB scoring, depth, optimism)        |
| **Draft Sharks**             | ML on NFL data (1999+)             | Aging curves, retirement rates, 10-year forecasts |
| **PFF**                      | Expert rankings scaled to 100      | Position-based scaling, expert analysis           |
| **Dynasty Trade Calculator** | Open market values                 | Buy/sell line averaging                           |

### 6.2 Analytical Resources

| Resource                       | Focus                          | URL                          |
| ------------------------------ | ------------------------------ | ---------------------------- |
| **Fantasy Football Analytics** | VoR, VBD, projections          | fantasyfootballanalytics.net |
| **PlayerProfiler**             | Advanced metrics glossary      | playerprofiler.com           |
| **Footballguys**               | Dynasty strategy, aging curves | footballguys.com             |
| **RotoViz**                    | Analytics, visualizations      | rotoviz.com                  |
| **The Undroppables**           | Dynasty strategy guides        | theundroppables.com          |
| **Dynasty Nerds**              | Trade values, rankings         | dynastynerds.com             |

### 6.3 Data & Rankings

| Resource         | Specialization                |
| ---------------- | ----------------------------- |
| **FantasyPros**  | Expert consensus rankings     |
| **PFF**          | Grading, advanced stats       |
| **Draft Sharks** | ML-powered projections        |
| **4for4**        | Projections, matchup analysis |
| **RotoWire**     | Player news, strategy         |

______________________________________________________________________

## 7. Key Frameworks Summary

### 7.1 Player Valuation Decision Tree

```
1. Calculate VoR relative to replacement level
   ├─ High VoR + Scarce position → Priority target
   └─ Low VoR + Deep position → Defer

2. Evaluate sustainability
   ├─ Volume-based production → Sustainable
   ├─ TD-dependent production → Regression risk
   └─ Opportunity metrics (target share, snaps) → Leading indicators

3. Consider aging curve
   ├─ RB: Peak years 2-4, sell after year 4
   ├─ WR: Peak year 5, stable through late 20s
   ├─ TE: Breakout year 2, stable through year 7
   └─ QB: Peak 28-33, stable into mid-30s

4. Factor in market pricing
   ├─ KTC value > Model value → Overpriced (sell)
   ├─ KTC value < Model value → Underpriced (buy)
   └─ KTC value ≈ Model value → Fair market
```

### 7.2 Roster Construction Framework

```
1. Determine team timeline
   ├─ Contending (next 1-2 years) → Win-now mode
   ├─ Fringe (2-3 years out) → Hold/accumulate
   └─ Rebuilding (3+ years out) → Rebuild mode

2. Win-now tactics
   ├─ Target proven producers
   ├─ Trade picks for players
   ├─ Acquire young RBs for window
   └─ Hold own picks for future youth injection

3. Rebuild tactics
   ├─ Accumulate draft picks (multiple classes)
   ├─ Focus on 2-3 young foundational pieces (WR/QB)
   ├─ Avoid RBs (will age out before contention)
   └─ Trade aging assets at peak value

4. Position allocation
   ├─ QB: Secure startable QB(s) early in Superflex
   ├─ RB: 4-5 roster spots for 2 starters
   ├─ WR: 6-7 roster spots for 2-3 starters (build foundation here)
   └─ TE: 2-3 roster spots for 1 starter
```

### 7.3 Trade Evaluation Framework

```
1. Calculate raw value exchange
   ├─ Use KTC/DynastyProcess for baseline
   └─ Apply quantity premium (30-50% for consolidation)

2. Evaluate timeline alignment
   ├─ Win-now → Prioritize current year impact
   ├─ Rebuilding → Prioritize future value/picks
   └─ Mismatch = win-win opportunity

3. Consider positional needs
   ├─ Scarce position (RB/TE) → Pay premium
   └─ Deep position (WR) → Accept discount

4. Factor in age/sustainability
   ├─ Acquiring aging RB → Verify TD sustainability
   ├─ Acquiring young WR → Accept year 1-2 patience
   └─ Apply mortality probability for 27+ players

5. Assess market timing
   ├─ Buying post-injury → Discount opportunity
   ├─ Selling in offseason hype → Premium opportunity
   └─ Selling aging player → Exit before cliff
```

### 7.4 Asset Management Heuristics

**Draft Picks:**

- 1st round picks = premium assets (but often overvalued by ~20-30%)
- 2nd round picks = volatile (22% hit rate)
- 3rd+ round picks = dart throws (minimal trade value)
- Future picks = discount to 80% of current year value

**Contract/Salary:**

- Never cut when dead cap > cap hit
- Long contracts to expensive players = high risk
- Long contracts to cheap breakout candidates = high reward
- NFL guarantees signal opportunity

**Position-Specific Exit Points:**

- RB: Sell after year 4 (before decline)
- WR: Can hold through age 28-29
- TE: Can hold through age 29-30
- QB: Can hold into mid-30s

______________________________________________________________________

## 8. Concrete Examples & Case Studies

### 8.1 VoR Calculation Example

**Scenario:** 12-team PPR league, 2 RB starters

**Top RB Projection:** 250 points
**RB24 (replacement level):** 150 points
**VoR:** 250 - 150 = 100

**Mid-tier WR Projection:** 200 points
**WR24 (replacement level):** 100 points
**VoR:** 200 - 100 = 100

**Conclusion:** Despite RB scoring more absolute points (250 vs 200), both provide equal value over replacement. Draft based on VoR equality, not raw points.

### 8.2 Touchdown Regression Case Study

**James Cook (2024 Season):**

- Expected TDs (xTD): 10
- Actual TDs: 16
- TDOE: +6

**Analysis:**
+6 TDOE extremely high. Historical data shows 86% regression in following year.

**2025 Projection:**
Expect ~10-11 TDs (regression to expectation), reducing overall fantasy value by ~30-40 PPR points.

**Dynasty Strategy:**
Sell Cook at peak value (offseason 2025) before regression manifests.

### 8.3 Win-Win Trade Structure Example

**Team A:** Contending, weak at RB, strong at WR, has 2025 late 1st
**Team B:** Rebuilding, weak at WR, strong at RB, has no 2025 1st

**Trade:**

- Team A sends: 2025 1.11, WR (age 26, value 70)
- Team B sends: RB (age 24, value 80)

**Analysis:**

- **Value:** Team A sends ~90 total, receives 80 (pays 12% premium to consolidate)
- **Timeline:** Team A gets win-now RB, Team B gets future pick + stable WR
- **Positional:** Team A addresses scarce RB position, Team B doesn't need RB depth
- **Market timing:** Team B sells RB before year 4 decline cliff

**Result:** Win-win aligned with both teams' competitive windows.

### 8.4 Draft Pick Valuation Example

**1.03 Pick Valuation (DynastyProcess Method):**

Recent 3rd overall picks (2015-2018):

- 2018: WR (current value: 85)
- 2017: RB (current value: 40)
- 2016: WR (current value: 75)
- 2015: RB (current value: 5)

**Average:** (85 + 40 + 75 + 5) / 4 = 51.25

**With recency weighting (2018 = 40%, 2017 = 30%, 2016 = 20%, 2015 = 10%):**
(85 × 0.4) + (40 × 0.3) + (75 × 0.2) + (5 × 0.1) = 62

**Conclusion:** 1.03 pick valued around 60-62 on dynasty trade calculator scale.

______________________________________________________________________

## 9. Implementation Recommendations

### 9.1 For Player Valuation

1. **Start with VoR calculations** using your league's scoring settings and roster requirements
2. **Cross-reference multiple tools** (KTC, DynastyProcess, Draft Sharks) to identify market inefficiencies
3. **Apply sustainability filters** (opportunity metrics, TD regression analysis)
4. **Factor in aging curves** by position to project 3-year values
5. **Monitor market pricing** weekly using KTC to identify buy-low/sell-high windows

### 9.2 For Roster Construction

1. **Define your competitive window** (honest assessment)
2. **Set position allocation targets** based on starting requirements + depth needs
3. **Build foundation with young WRs** (longest value retention)
4. **Time RB acquisitions** to align with competitive window
5. **Maintain pick diversification** across multiple draft classes

### 9.3 For Trade Evaluation

1. **Calculate baseline value** using trade calculators
2. **Apply timeline adjustments** (does this align with my window?)
3. **Factor in quantity premium** (30-50% for consolidation trades)
4. **Evaluate sustainability** (am I buying TD regression risk?)
5. **Consider market timing** (offseason vs. in-season values)

### 9.4 For Asset Management

1. **Track pick values** weekly as NFL Draft approaches
2. **Set position-specific exit points** (especially RBs after year 4)
3. **Monitor dead cap** in salary leagues (never cut when dead cap > cap hit)
4. **Diversify draft capital** across multiple years
5. **Exploit market inefficiencies** (veteran undervaluation in offseason)

______________________________________________________________________

## 10. Research Gaps & Future Directions

### 10.1 Identified Gaps

1. **Manager profiling methodologies** - Limited published research on systematic approaches to profiling trading partners
2. **Multi-objective optimization frameworks** - No formal mathematical models for dynasty trade evaluation found
3. **Salary cap dynasty strategies** - Emerging format with limited published strategic frameworks
4. **IDP dynasty valuation** - Sparse research on defensive player valuation in dynasty formats
5. **League size scaling** - Most research assumes 12-team leagues; limited guidance for 8-team or 16+ team formats

### 10.2 Emerging Areas

1. **Machine learning for breakout prediction** - Increasing sophistication in prospect profiling
2. **Sentiment analysis integration** - NLP on news/social media showing promise (6.9% improvement)
3. **Real-time market pricing** - Crowdsourced tools enabling more efficient markets
4. **Contract league evolution** - Growing interest in salary cap formats mimicking NFL dynamics

______________________________________________________________________

## 11. Bibliography & Key Sources

### Primary Analytical Resources

- Fantasy Football Analytics - [VBD Guide](https://fantasyfootballanalytics.net/2024/08/winning-fantasy-football-with-projections-value-over-replacement-and-value-based-drafting.html)
- Footballguys - [Harstad Mortality Tables](https://www.footballguys.com/article/HarstadMortalityTables)
- DynastyProcess - [Pick Values Methodology](https://dynastyprocess.com/blog/2019-02-14-2019pickvalues/)
- PFF - [Aging Curves by Position](https://www.pff.com/news/fantasy-football-metrics-that-matter-aging-curves-by-position)
- PlayerProfiler - [Advanced Stats Glossary](https://www.playerprofiler.com/terms-glossary/)

### Trade Calculators & Tools

- KeepTradeCut - [Trade Calculator](https://keeptradecut.com/trade-calculator)
- DynastyProcess - [Value Calculator](https://calc.dynastyprocess.com/)
- Draft Sharks - [Dynasty Trade Values](https://www.draftsharks.com/trade-value-chart/dynasty/ppr)

### Strategy Guides

- The Undroppables - [Roster Construction](https://www.theundroppables.com/the-art-of-dynasty-chapter-2-roster-construction/)
- Fantasy in Frames - [Dynasty Reset Guide](https://www.fantasyinframes.com/the-dynasty-reset-rebuilding-a-fantasy-football-team-part-1/)
- Dynasty Football Factory - [Salary Cap Strategies](https://dynastyfootballfactory.com/dynasty-and-the-nfl-salary-cap/)

### Academic Research

- SMU Data Science Review - [FF Analytics Research](https://scholar.smu.edu/cgi/viewcontent.cgi?article=1279&context=datasciencereview)
- MIT - [Interactive Tools for FF Analytics](https://dspace.mit.edu/handle/1721.1/100687)
- Isaac T. Petersen - [Fantasy Football Analytics Textbook](https://isaactpetersen.github.io/Fantasy-Football-Analytics-Textbook/)

______________________________________________________________________

## Appendix: Quick Reference Tables

### A1. Aging Curves by Position

| Position | Rookie Performance | Peak Year(s) | Decline Begins     | Dynasty Exit Point |
| -------- | ------------------ | ------------ | ------------------ | ------------------ |
| RB       | 88% baseline       | Years 2-4    | Year 7             | After Year 4       |
| WR       | 74% baseline       | Year 5       | Late 20s (gradual) | Age 28-29          |
| TE       | 33% baseline       | Years 3-7    | Age 30             | Age 29-30          |
| QB       | Variable           | Ages 28-33   | Mid-30s            | Age 35+            |

### A2. Draft Pick Hit Rates

| Round | Hit Rate | Miss Rate | Value Category |
| ----- | -------- | --------- | -------------- |
| 1st   | ~40-50%  | ~40%      | Premium asset  |
| 2nd   | 22%      | 69%       | Volatile asset |
| 3rd+  | \<15%    | >80%      | Dart throw     |

### A3. VoR Baselines by League Size

| League Size | QB Baseline | RB Baseline | WR Baseline | TE Baseline |
| ----------- | ----------- | ----------- | ----------- | ----------- |
| 10-team     | QB10        | RB20        | WR20        | TE10        |
| 12-team     | QB12        | RB24        | WR24        | TE12        |
| 14-team     | QB14        | RB28        | WR28        | TE14        |

*Baselines assume 1 QB, 2 RB, 2 WR, 1 TE starting requirements*

### A4. Trade Value Premiums

| Trade Type            | Premium Required | Rationale             |
| --------------------- | ---------------- | --------------------- |
| 2-for-1 consolidation | +30-50%          | Elite player scarcity |
| 3-for-2 consolidation | +20-30%          | Roster spot value     |
| Future picks          | -20% discount    | Time value of assets  |
| Injured player        | -20-40% discount | Risk premium          |
| Post-hype falloff     | -30-50% discount | Market inefficiency   |

______________________________________________________________________

**Document Version:** 1.0
**Last Updated:** 2025-10-29
**Maintained By:** FF Analytics Project
**License:** Internal research compilation for project use
