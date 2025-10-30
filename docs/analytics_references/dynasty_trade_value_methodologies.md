# Dynasty Trade Value Chart Methodologies and Market Pricing Systems

**Date:** October 2025
**Purpose:** Comprehensive reference guide for dynasty fantasy football trade value systems, including construction methodologies, strategic applications, and best practices for identifying market inefficiencies.

______________________________________________________________________

## Table of Contents

1. [Major Dynasty Trade Value Charts](#major-dynasty-trade-value-charts)
2. [Construction Methodologies](#construction-methodologies)
3. [Trade Value Chart Usage Strategies](#trade-value-chart-usage-strategies)
4. [Dynamic Pricing Factors](#dynamic-pricing-factors)
5. [League Format Adjustments](#league-format-adjustments)
6. [Strategic Applications by Team Status](#strategic-applications-by-team-status)
7. [Best Practices and Recommendations](#best-practices-and-recommendations)

______________________________________________________________________

## Major Dynasty Trade Value Charts

### 1. KeepTradeCut (KTC)

**URL:** https://keeptradecut.com/

#### Methodology: Crowd-Sourced Market Consensus

**Data Collection:**

- Users evaluate three-player comparisons, ranking them as "Keep," "Trade," or "Cut"
- Aggregates data from over 23 million user submissions
- Real-time updating based on continuous community input

**Value Calculation:**

- Uses adapted ELO algorithm to process submissions
- Creates values that follow a reasonable distribution across the player spectrum
- Reflects scarcity of elite players and gradient from top to bottom

**Unique Features:**

1. **Value Adjustment Algorithm**

   - Goes beyond simple addition to account for roster economics
   - Uses exponential scaling to prevent "12 third-round picks for DeAndre Hopkins" type trades
   - Calculates hidden "raw adjustment" scores for each player based on:
     - Player's KTC value (p)
     - Most valuable player in specific trade (t)
     - Most valuable player overall (v, typically ~9999)
   - Exponential curve means a 5000 KTC player represents only 26% of maximum raw adjustment, not 50%

   **Example:**

   - Ja'Marr Chase (8200 value) vs CeeDee Lamb (5500) + Joe Mixon (4900)
   - Chase raw adjustment: ~2900
   - Lamb + Mixon combined: ~2500
   - Adjustment adds ~4900 value to smaller side to equalize

2. **Liquidity Scoring**

   - Tracks latest 25,000 real trades in Dynasty Trade Database
   - Assigns "Liquidity Score" (0-99) to every player
   - Most liquid player = 99; player appearing half as frequently = 50
   - Helps identify which players are actually tradeable vs. "roster cloggers"

**Strengths:**

- Most up-to-date values reflecting current market sentiment
- Massive data sample provides statistical reliability
- Real-time adjustment to news, injuries, and league developments
- Format-specific values (1QB, Superflex, TE Premium)

**Weaknesses:**

- Susceptible to recency bias and overreactions
- Can lag behind optimal valuations during market inefficiencies
- Crowd wisdom sometimes creates echo chambers
- May not reflect specific league contexts or scoring systems

**Best Use Cases:**

- Establishing baseline market values
- Understanding current community sentiment
- Quick trade evaluation during negotiations
- Identifying liquidity for potential trade targets

______________________________________________________________________

### 2. DynastyProcess

**URL:** https://dynastyprocess.com/ | https://calc.dynastyprocess.com/

#### Methodology: Algorithmic with Customizable Parameters

**Data Foundation:**

- Built on FantasyPros aggregated expert rankings
- Passes rankings through exponential curve to generate trade values

**Value Calculation:**

1. **Player Valuation:**

   - Exponential curve coefficient: -0.0235 (adjustable)
   - Makes assumptions about:
     - Positional value relationships
     - Depth player vs. elite stud valuation
     - Youth vs. age premium

2. **Rookie Pick Valuation:**

   - Historical averaging method (2015-2018+ draft classes)
   - Pick value = average current value of Nth-best players from historical classes
   - Establishes "ceiling valuation" reflecting pre-draft optimism
   - Toggle between "Perfect Knowledge" and "Hit Rate" algorithms
   - Future picks valued at 80% of current year picks (present-value calculation)

**Customization Options:**

| Setting                  | Options                      | Impact                                        |
| ------------------------ | ---------------------------- | --------------------------------------------- |
| **QB Type**              | 1QB, 2QB/SF                  | Adjusts QB values for format                  |
| **League Size**          | 6-32 teams                   | Renames picks, manual value adjustment needed |
| **Valuation Factor**     | Slider                       | Tunes star vs. bench player valuation         |
| **Rookie Pick Optimism** | Perfect Knowledge / Hit Rate | Changes pick valuation approach               |
| **Future Pick Factor**   | Slider                       | Adjusts future pick discount rate             |

**Strengths:**

- Open-source and transparent methodology (GitHub: dynastyprocess)
- Highly customizable for league-specific contexts
- Mathematically consistent and reproducible
- Less susceptible to short-term market overreactions

**Weaknesses:**

- Requires user understanding of settings for accuracy
- Expert consensus may lag behind market reality
- Less frequent updates compared to crowd-sourced tools
- Default settings may not match your league's market

**Best Use Cases:**

- League-specific valuation modeling
- Long-term strategic planning
- Understanding theoretical value vs. market value gaps
- Creating consistent internal valuation framework

______________________________________________________________________

### 3. Dynasty League Football (DLF)

**URL:** https://dynastyleaguefootball.com/

#### Methodology: Hybrid Expert + Community + Trade Data

**Data Sources:**

- Expert rankings from DLF analysts
- Community dynasty ADP data
- Actual trade database analysis

**Value Calculation:**

- Monthly superflex trade value chart updates
- Risers/fallers calculated by percentage change (not raw points)
- Combines three data streams to narrow down player trade values

**Update Frequency:**

- Monthly updates throughout the year
- Reflects injuries, performance changes, and situation shifts

**Strengths:**

- Balances expert opinion with market reality
- Real trade data grounds valuations in practice
- Format-specific (Superflex focus)
- Regularly updated with detailed explanations

**Weaknesses:**

- Less granular than real-time tools
- Smaller data sample than pure crowd-sourced systems
- Subjective expert input creates potential bias
- Monthly updates can miss rapid value changes

**Best Use Cases:**

- Second opinion on contested valuations
- Understanding analyst perspective vs. market
- Superflex league-specific valuations
- Monthly portfolio review and rebalancing

______________________________________________________________________

### 4. FantasyPros

**URL:** https://www.fantasypros.com/

#### Methodology: Expert Consensus Rankings

**Data Foundation:**

- Consensus of multiple fantasy football analysts
- Core contributors: Derek Brown, Pat Fitzmaurice, Andrew Erickson

**Value Calculation:**

- Dynamic chart from aggregated expert dynasty rankings
- Separate values for multiple formats:
  - 1QB leagues
  - Superflex leagues
  - TE Premium leagues

**Update Frequency:**

- Monthly updates throughout the year
- Includes dynasty rookie draft pick values for current and future years

**Strengths:**

- Respected analyst consensus provides credibility
- Multiple format options
- Clear presentation and easy to use
- Includes future pick valuations (2026, 2027)

**Weaknesses:**

- Expert opinion can lag market reality
- Smaller expert sample than crowd consensus
- May not reflect rapid market shifts
- Less transparent methodology than algorithmic tools

**Best Use Cases:**

- Expert perspective for trade evaluation
- Format-specific valuations (TE Premium)
- Cross-referencing with market-based tools
- Understanding "sharp" vs. "casual" valuations

______________________________________________________________________

### 5. Draft Sharks

**URL:** https://www.draftsharks.com/

#### Methodology: Proprietary Machine Learning + Long-Term Projections

**Data Foundation:**

- Proprietary "3D values+" system
- Uses 3-year, 5-year, and 10-year fantasy forecasted output
- Machine learning algorithms for value generation

**Value Calculation:**

- Data-driven analysis custom-fit for format and scoring
- Real-time dynamic updates
- Cross-positional algorithm based on exact league setup

**Format Options:**

- Dynasty PPR
- Superflex
- TE Premium
- Half-PPR, Standard

**Strengths:**

- Long-term projection focus aligns with dynasty philosophy
- Customizable for specific scoring systems
- Machine learning reduces human bias
- Forward-looking rather than reactive

**Weaknesses:**

- Proprietary methodology lacks transparency
- May not reflect current market sentiment
- Projections can be wrong (like all projections)
- Less established than KTC or DynastyProcess

**Best Use Cases:**

- Long-term value assessment for rebuilders
- Evaluating young player upside
- Understanding projection-based vs. market-based value gaps
- Identifying buy-low candidates with strong projections

______________________________________________________________________

### 6. Pro Football Focus (PFF)

**URL:** https://www.pff.com/

#### Methodology: Scaled Expert Analysis

**Value Calculation:**

- Top-ranked player/pick in each category = 100
- All other values scaled proportionally to reflect relative worth
- Separate charts for each position (QB, RB, WR, TE, picks)

**Data Foundation:**

- PFF's proprietary player grades and analysis
- Consistent, data-driven baseline for evaluations

**Strengths:**

- Normalized 0-100 scale is intuitive
- PFF's analytical reputation adds credibility
- Position-specific focus allows detailed comparisons
- Regular updates reflect latest news and injuries

**Weaknesses:**

- Relative scaling makes cross-positional trades harder
- PFF's analytical focus may not match fantasy production
- Expert-driven, not market-driven
- Requires understanding of PFF's grading philosophy

**Best Use Cases:**

- Position-specific player comparisons
- Understanding talent-based value vs. opportunity-based value
- Analytical perspective for long-term dynasty building
- Cross-referencing with market values

______________________________________________________________________

## Construction Methodologies

### Crowd-Sourced (KTC)

**How It Works:**

1. Large user base makes thousands of comparative judgments
2. ELO-style algorithm processes submissions
3. Continuous real-time updates reflect market sentiment
4. Statistical aggregation reduces individual bias

**Advantages:**

- Reflects actual market conditions
- Self-correcting through volume
- Captures "wisdom of crowds"
- Real-time responsiveness

**Disadvantages:**

- Herd mentality can create bubbles
- Recency bias amplified
- May lag optimal valuations during inefficiencies
- Difficult to reverse once narrative forms

**Best For:** Understanding what you can *actually* get in trades right now

______________________________________________________________________

### Expert-Based (FantasyPros, DLF, PFF)

**How It Works:**

1. Experienced analysts rank players based on:
   - Talent evaluation
   - Situation analysis
   - Historical performance
   - Future projections
2. Individual rankings aggregated into consensus
3. Periodic updates (weekly, monthly) based on new information

**Advantages:**

- Reduces emotional overreactions
- Incorporates deep film study and research
- Can identify market inefficiencies
- More stable over short periods

**Disadvantages:**

- Expert bias and blind spots
- May not match tradeable market values
- Update lag during fast-moving situations
- Smaller sample size than crowd consensus

**Best For:** Understanding what players *should* be worth based on analysis

______________________________________________________________________

### Algorithmic (DynastyProcess, Draft Sharks)

**How It Works:**

1. Mathematical models process input data:
   - Historical performance
   - Projections (short and long-term)
   - Age curves and positional aging
   - Situation and opportunity metrics
2. Exponential curves account for scarcity and roster economics
3. Customizable parameters for league-specific contexts

**Advantages:**

- Consistent and reproducible
- Removes emotional bias
- Can be tuned for specific leagues
- Transparent methodology (when open-source)

**Disadvantages:**

- Only as good as input data and assumptions
- May not capture intangibles (coaching, scheme fit)
- Requires understanding to customize properly
- Can lag sudden market shifts

**Best For:** Creating a personal valuation framework and identifying value gaps

______________________________________________________________________

### Hybrid (DLF)

**How It Works:**

1. Combines multiple data sources:
   - Expert rankings
   - Community ADP
   - Real trade database
2. Synthesizes into unified value chart
3. Regular updates balance stability and responsiveness

**Advantages:**

- Balances multiple perspectives
- Grounded in both theory and practice
- More robust than single-source methods
- Captures different market segments

**Disadvantages:**

- Complex methodology harder to understand
- Potential for conflicting signals
- Update frequency may miss rapid changes
- Weight of each component unclear

**Best For:** Balanced perspective combining market reality and expert analysis

______________________________________________________________________

## Trade Value Chart Usage Strategies

### 1. Establishing Baseline Values

**Primary Use:**
Start every trade negotiation with an understanding of consensus market value. This prevents egregious mistakes and anchors discussions.

**Best Practice:**

- Check 2-3 different charts before making offers
- Use market-based tools (KTC) for current tradeable value
- Use expert/algorithmic tools for "true value" assessment
- Identify gaps between different methodologies

**Example:**

- KTC value: Player X = 6500
- DynastyProcess value: Player X = 7200
- Your assessment: Player has upside not reflected in market
- **Strategy:** Buy at market price (6500), hold until value catches up

______________________________________________________________________

### 2. Identifying Value Inefficiencies

**Market Inefficiencies Occur When:**

1. **Recency bias overreaction**

   - One bad game tanks value disproportionately
   - Injury news creates panic selling
   - Breakout performance creates hype spike

2. **Narrative disconnect**

   - Market focuses on volume metrics, ignores efficiency
   - Age bias undervalues prime-age players
   - Draft capital bias overvalues high picks

3. **Format-specific misvaluation**

   - 1QB league owners overvalue QBs
   - Superflex league owners undervalue RBs
   - Standard scoring markets undervalue PPR specialists

4. **Timing arbitrage**

   - Rookie picks valued differently by season phase
   - Veterans undervalued mid-season by rebuilders
   - Contenders overvalue win-now players at deadline

**Arbitrage Strategy:**

```
IF (Market Value < Your Model Value) AND (Seller willing at market):
    → BUY

IF (Market Value > Your Model Value) AND (Buyer willing at market):
    → SELL

IF (Market Value ≈ Your Model Value):
    → HOLD (no edge)
```

**Example - Rookie Pick Arbitrage:**

- **During Season:** 2026 1st round pick = 4000 value (picks not scoring points)
- **Post-Season:** Same pick = 5500 value (draft hype building)
- **Strategy:** Acquire picks during season from contenders, sell post-season to rebuilders
- **Expected Return:** 37.5% value appreciation without any player acquisition risk

______________________________________________________________________

### 3. When to Trust the Market vs. Your Model

**Trust the Market When:**

- You need to complete a trade NOW (market = reality)
- Trading with sophisticated opponents who won't accept non-market deals
- Dealing with highly liquid players (lots of trade data)
- Your model has limited information (new players, injuries)

**Trust Your Model When:**

- Building long-term positional advantage
- Identifying multi-year value plays
- Trading in less sophisticated leagues
- You have information edge (film study, coaching connections)
- Market shows clear emotional overreaction

**Hybrid Approach (Recommended):**

1. Use market value to understand negotiation range
2. Use model to identify edge opportunities
3. Only trade when gap > 15% (accounts for uncertainty)
4. Diversify: make many +EV trades rather than betting everything on one conviction

**Example:**

```
Player A Market Value: 5000
Player A Model Value: 6000
Gap: +20%

Player B Market Value: 5000
Player B Model Value: 5100
Gap: +2%

→ Pursue Player A aggressively (significant edge)
→ Pass on Player B (minimal edge, transaction cost not worth it)
```

______________________________________________________________________

### 4. Accounting for League-Specific Factors

**Your league's market ≠ Industry consensus**

**Factors to Consider:**

| Factor                    | Impact on Values                     | Adjustment Strategy                               |
| ------------------------- | ------------------------------------ | ------------------------------------------------- |
| **League Experience**     | Less experienced = more volatile     | Trust industry values less, observe league trades |
| **Scoring System**        | PPR vs Standard, TEP, bonus scoring  | Use format-specific charts or adjust manually     |
| **Roster Size**           | Larger rosters = depth more valuable | Increase values of RB2/WR3 types                  |
| **Starting Requirements** | 2RB/3WR vs 3RB/2WR                   | Adjust position scarcity accordingly              |
| **Trade Frequency**       | Low activity = less liquid market    | Discount theoretical values, liquidity premium    |
| **League Philosophy**     | Rebuild vs win-now tendencies        | Adjust for supply/demand imbalances               |
| **Tanking Rules**         | Tanking allowed/discouraged          | Affects draft pick values                         |

**Building a League-Specific Model:**

1. Track all league trades for 1-2 seasons
2. Compare to industry consensus values
3. Identify systematic patterns (e.g., "our league overvalues RBs by 20%")
4. Create adjustment factors for your league
5. Update annually as league evolves

**Example - High-Scoring League:**

```
Standard Chart: Elite RB = 8000, Elite WR = 7000
Your League: More pass-friendly scoring, 3 WR + 2 Flex

Adjustment:
- Elite RB = 7500 (-6%)
- Elite WR = 7500 (+7%)
- Rationale: WR depth required, WR scoring boosted
```

______________________________________________________________________

### 5. Multi-Chart Validation Strategy

**Never rely on a single chart**

**Three-Source Method:**

1. **Market-Based** (KTC): What can you get RIGHT NOW?
2. **Expert-Based** (FantasyPros/PFF): What do analysts think?
3. **Algorithmic** (DynastyProcess): What does the model say?

**Decision Matrix:**

| Market | Expert | Model | Interpretation                      | Action                                    |
| ------ | ------ | ----- | ----------------------------------- | ----------------------------------------- |
| High   | High   | High  | Consensus value                     | Fair value, hold or make even swap        |
| High   | Low    | Low   | Market overvaluing                  | **SELL**                                  |
| Low    | High   | High  | Market undervaluing                 | **BUY**                                   |
| High   | High   | Low   | Model error or unique insight       | Investigate further, trust market/experts |
| Low    | Low    | High  | Model error or market knowledge gap | Investigate further, trust market/experts |
| Medium | High   | Low   | Expert optimism vs model            | Small buy if you trust analysis           |
| Medium | Low    | High  | Model optimism vs expert            | Small buy if you trust projections        |

**Example Trade Evaluation:**

```
Receive: Player X + 2026 1st
Give: Player Y

Player X Values:
- KTC: 5500
- FantasyPros: 6000
- DynastyProcess: 5200

Player Y Values:
- KTC: 7000
- FantasyPros: 6800
- DynastyProcess: 7200

2026 1st Values:
- KTC: 3500
- FantasyPros: 3200
- DynastyProcess: 3800

Your Side: 7000 (KTC), 6800 (FP), 7200 (DP) → Avg: 7000
Their Side: 9000 (KTC), 9200 (FP), 9000 (DP) → Avg: 9067

Verdict: Accept (getting ~30% more value across all sources)
```

______________________________________________________________________

## Dynamic Pricing Factors

### 1. News and Injury Impact

**Immediate Price Movements:**

| Event Type                      | Typical Impact | Recovery Time                    | Strategy                            |
| ------------------------------- | -------------- | -------------------------------- | ----------------------------------- |
| **Star Injury (Season-Ending)** | -40% to -60%   | Offseason (6-9 months)           | Buy if young, sell if 28+           |
| **Star Injury (4-6 weeks)**     | -15% to -25%   | 2-3 weeks after return           | Hold or buy from panicked owner     |
| **Backup Breakout**             | +200% to +500% | 2-4 weeks (regression expected)  | **SELL IMMEDIATELY**                |
| **Coaching Change**             | -10% to +30%   | Full offseason to evaluate       | Hold through uncertainty            |
| **Trade to Better Team**        | +20% to +40%   | Immediate (new situation)        | Quick buy before market adjusts     |
| **Trade to Worse Team**         | -20% to -30%   | Immediate                        | Sell if win-now, hold if rebuilding |
| **Contract Extension**          | +5% to +15%    | N/A (signals commitment)         | Stable hold                         |
| **Rookie Draft Buzz**           | +10% to +50%   | Week after NFL draft (peak hype) | Sell pre-draft or draft day         |

**Dynasty-Specific Considerations:**

Unlike redraft, dynasty values recover differently based on:

- **Age:** Young players (under 25) recover faster from injury value drops
- **Contract Status:** Multiple years remaining = more stability
- **Talent Level:** Elite talent holds value better through adversity
- **Positional Scarcity:** RB injuries matter more than WR (shorter shelf life)

**Injury Arbitrage Strategy:**

```
Short-term injury to young star:
1. Value drops 20-30% immediately
2. Owner panics about playoff implications
3. You offer market value (already discounted)
4. Hold through recovery
5. Value returns to pre-injury levels
6. Net gain: 20-30% for 6-8 weeks of patience
```

**Real Example:**

- Week 4, 2025: Breakout rookie WR suffers MCL sprain (6 weeks)
- Pre-injury value: 6000
- Post-injury panic: 4200 (-30%)
- Contender selling to stay in playoff race
- Rebuilder buys at 4200
- Week 12 return, performs well
- Post-season value: 6500
- Net gain: 54.8% in 8 weeks

**Key Insight:** Patient dynasty managers profit from other owners' urgency and recency bias.

______________________________________________________________________

### 2. Seasonal Trends in Player Values

**Annual Value Cycles:**

#### Q1 (January - March): Post-Season Evaluation

- **Trend:** Veterans who didn't perform drop sharply
- **Hot:** Young breakouts, draft picks (rising hype)
- **Cold:** Aging veterans, disappointing rookies
- **Strategy:** Sell veterans before age decay prices in, buy proven players at discounts

#### Q2 (April - June): NFL Draft & Offseason Moves

- **Trend:** Draft capital creates value, situation changes matter
- **Hot:** Newly drafted rookies (peak hype), players changing teams
- **Cold:** Veterans losing opportunity, players entering committees
- **Strategy:** Sell rookie picks at peak value (post-NFL draft), buy veterans whose situation improved

#### Q3 (July - September): Training Camp & Preseason

- **Trend:** Speculation peaks, training camp news drives volatility
- **Hot:** Preseason hype trains, "camp sleepers"
- **Cold:** Injured players, demoted players
- **Strategy:** Sell hype, buy talent in bad situations before season proves otherwise

#### Q4 (October - December): In-Season Performance

- **Trend:** Performance-based value changes, weekly volatility
- **Hot:** Win-now assets for contenders, breakout players
- **Cold:** Injured players, struggling teams' assets
- **Strategy:** Contenders buy proven producers, rebuilders sell veterans for picks

**Rookie Pick Value Seasonality:**

```
Peak Value: Post-NFL Draft (April-May)
           ↗ +40% from season

Minimum Value: Mid-Season (October-November)
           ↘ -30% from peak

Arbitrage Window: 70% value swing annually
```

**Example:**

- October 2025: Acquire 2026 1st from contender for 3000 value
- May 2026: Post-NFL Draft, pick now worth 4500-5000
- Trade pick at peak to rebuilder
- Net gain: 50-67% return in 7 months

**Why This Works:**

- Contenders discount future picks (not helping them now)
- Rebuilders overvalue picks (hope > reality)
- Timing + counter-positioning = systematic edge

______________________________________________________________________

### 3. League Format Impact on Values

#### 1QB vs Superflex: The Quarterback Value Chasm

**Magnitude of Difference:**

| Player Type                   | 1QB Value | Superflex Value | Ratio |
| ----------------------------- | --------- | --------------- | ----- |
| Elite QB (Josh Allen)         | 5,726     | 10,160          | 1.77x |
| Mid-Tier QB (Trevor Lawrence) | 2,500     | 5,800           | 2.32x |
| Backup QB (Tyrod Taylor)      | 200       | 1,800           | 9.00x |
| Elite WR (Ja'Marr Chase)      | 8,500     | 8,200           | 0.96x |
| Elite RB (Bijan Robinson)     | 9,000     | 8,500           | 0.94x |

**Key Insights:**

1. Elite QBs nearly **2x** in value for Superflex
2. Mid-tier QBs more than **double** in value
3. Backup QBs become **tradeable assets** (vs worthless in 1QB)
4. Non-QB positions slightly **decrease** in relative value
5. Positional scarcity completely reordered

**Strategic Implications:**

**For Superflex:**

- Lock in 3 startable QBs minimum (injury insurance)
- QB1 overall picks justified for elite young QBs
- Never trade away QB depth without replacement
- QB-needy teams overpay massively (exploit this)
- Rookie QB picks in top 5 = instant value (even bad prospects)

**For 1QB:**

- Wait on QB in dynasty drafts (rounds 4-7)
- Stream QBs based on matchups
- Elite QBs not worth top-tier assets
- Focus capital on RB/WR

**Format Transition Warning:**
If your league is considering switching 1QB → Superflex:

- **Act BEFORE** announcement to avoid price adjustment
- Acquire all available QB depth immediately
- QB market will shift overnight once announced
- Early movers gain 2-3 years of competitive advantage

______________________________________________________________________

#### PPR vs Standard vs Half-PPR

**Reception Scoring Impact:**

| Player Archetype   | Standard Value | Half-PPR Value | Full PPR Value |
| ------------------ | -------------- | -------------- | -------------- |
| Bell-Cow RB        | 10,000         | 10,000         | 10,000         |
| Pass-Catching RB   | 6,000          | 7,500 (+25%)   | 9,000 (+50%)   |
| Target-Heavy WR    | 7,000          | 8,000 (+14%)   | 9,000 (+29%)   |
| Yards-per-Catch WR | 6,000          | 6,300 (+5%)    | 6,500 (+8%)    |
| Possession WR      | 4,000          | 5,500 (+38%)   | 6,500 (+63%)   |

**Strategic Adjustments:**

**PPR Leagues:**

- Prioritize target share over yards per route
- Pass-catching RBs (Austin Ekeler type) gain significant value
- Possession WRs (slot receivers) become viable starters
- TEs with volume more valuable than TDs

**Standard Leagues:**

- Touchdowns and total yards drive value
- Big-play ability matters more than target volume
- Elite RBs dominate (TD regression less impactful)
- Home-run hitters preferred over compilers

______________________________________________________________________

#### TE Premium (TEP)

**Adjustment Guidelines:**

**Mild TEP (+0.5 PPR for TEs):**

- Elite TEs: +15-20% value
- Mid-tier TEs: +10% value
- Low-end TEs: +5% value

**Moderate TEP (+1.0 PPR for TEs):**

- Elite TEs: +30-40% value
- Mid-tier TEs: +20% value
- Low-end TEs: +10% value

**Extreme TEP (2 TE required or +1.5 PPR):**

- Elite TEs: +60-80% value
- Mid-tier TEs: +40% value
- Low-end TEs: +25% value

**Example Values:**

| Player                | Standard Dynasty | Extreme TEP Dynasty |
| --------------------- | ---------------- | ------------------- |
| Travis Kelce (age 35) | 4,000            | 6,500               |
| Sam LaPorta           | 5,500            | 8,500               |
| Kyle Pitts            | 4,000            | 6,800               |
| Trey McBride          | 4,500            | 7,200               |

**TEP Strategy:**

- Draft TEs early (scarcity amplified)
- Young TEs with target share = elite assets
- Never punt the position (floor matters)
- TE-desperate teams overpay massively

______________________________________________________________________

#### Roster Size & Starting Lineups

**Deep Rosters (30+ players):**

- Depth players gain significant value
- Handcuffs become tradeable
- Rookie picks decrease in relative value (harder to find playing time)
- Tier dropoffs less steep

**Shallow Rosters (20 or fewer):**

- Stars & scrubs strategy optimal
- Handcuffs nearly worthless
- Rookie picks highly valuable (easier to crack lineup)
- Tier dropoffs extremely steep

**Example:**

| Asset                 | 20-man Roster Value | 35-man Roster Value |
| --------------------- | ------------------- | ------------------- |
| Elite RB              | 10,000              | 10,000              |
| RB3 (low-end starter) | 3,000               | 4,500 (+50%)        |
| RB Handcuff           | 500                 | 1,800 (+260%)       |
| 1.08 Rookie Pick      | 4,500               | 3,500 (-22%)        |

**Strategic Implications:**

- Deep leagues: Diversify, hold depth, play matchups
- Shallow leagues: Consolidate, elite or bust, ignore bench

______________________________________________________________________

#### Best Ball vs Traditional

**Best Ball Considerations:**

- Upside matters more than floor (no start/sit decisions)
- Volatile players gain value
- Handcuffs gain value (automatic injury fill-in)
- Bye week coverage less important
- Volume consistency less important

**Value Shifts:**

- Boom-bust players: +10-20%
- High-floor low-ceiling: -10-20%
- Handcuffs: +50-100%

______________________________________________________________________

### 4. Positional Aging Curves

**Understanding age decay prevents value traps**

#### Running Backs: Cliff at 27-28

| Age Range | Value Trajectory            | Trade Strategy                        |
| --------- | --------------------------- | ------------------------------------- |
| 21-24     | Peak value years            | Hold or buy if situation improves     |
| 25-26     | Beginning decline awareness | Sell before cliff if not contending   |
| 27-28     | Sharp decline in value      | **SELL IMMEDIATELY** before worthless |
| 29+       | Minimal dynasty value       | Accept pennies on the dollar or cut   |

**RB Value Decay Example:**

- Age 24: RB produces 1,400 total yards, value = 7,000
- Age 25: RB produces 1,350 total yards, value = 6,200 (-11%)
- Age 26: RB produces 1,280 total yards, value = 5,000 (-19%)
- Age 27: RB produces 1,100 total yards, value = 3,200 (-36%)
- Age 28: RB produces 850 total yards, value = 1,500 (-53%)

**Lesson:** Sell RBs at 26, definitely by 27, or watch value evaporate

______________________________________________________________________

#### Wide Receivers: Longer Peak, Graceful Decline

| Age Range | Value Trajectory    | Trade Strategy                   |
| --------- | ------------------- | -------------------------------- |
| 21-23     | Rising value        | Buy before breakout              |
| 24-27     | Peak years          | Hold, highest trade value        |
| 28-30     | Slow decline        | Sell to contenders at fair value |
| 31-33     | Steeper decline     | Only valuable to win-now teams   |
| 34+       | Year-to-year assets | Minimal dynasty value            |

**WR Value Decay Example:**

- Age 25: WR produces 1,200 yards, 8 TDs, value = 6,500
- Age 27: WR produces 1,180 yards, 7 TDs, value = 6,200 (-5%)
- Age 29: WR produces 1,050 yards, 7 TDs, value = 5,000 (-19%)
- Age 31: WR produces 900 yards, 6 TDs, value = 3,000 (-40%)

**Lesson:** WRs hold value longer; can keep until 29-30 before urgency

______________________________________________________________________

#### Quarterbacks: Longest Careers, Variable Peaks

| Age Range | Value Trajectory              | Trade Strategy                         |
| --------- | ----------------------------- | -------------------------------------- |
| 21-24     | High volatility, developing   | Buy if talent evident, lottery tickets |
| 25-30     | Prime years                   | Peak value, hold or buy                |
| 31-35     | Sustained excellence possible | Contender assets, sell to rebuilders   |
| 36+       | Year-to-year, decline risk    | Minimal dynasty value except elite     |

**Format Matters:**

- **Superflex:** QBs hold value longer (scarcity)
- **1QB:** QBs decline faster (plentiful supply)

**QB Value Decay Example (Superflex):**

- Age 27: Elite QB, value = 9,500
- Age 30: Elite QB, value = 9,000 (-5%)
- Age 33: Elite QB, value = 7,000 (-22%)
- Age 36: Elite QB, value = 4,000 (-43%)

**Lesson:** In Superflex, QBs age gracefully until mid-30s; in 1QB, much faster

______________________________________________________________________

#### Tight Ends: Late Bloomers

| Age Range | Value Trajectory               | Trade Strategy                    |
| --------- | ------------------------------ | --------------------------------- |
| 21-23     | Developing (TE takes time)     | Buy if talent clear, be patient   |
| 24-26     | Breakout window                | Peak value gain, buy before elite |
| 27-31     | Prime production               | Hold, safe assets                 |
| 32-34     | Slow decline                   | Sell to contenders                |
| 35+       | Exceptions only (Kelce, Gronk) | Minimal value                     |

**TE Value Trajectory Example:**

- Age 22: Rookie TE, 400 yards, value = 2,000
- Age 24: Breakout TE, 800 yards, 6 TDs, value = 5,000 (+150%)
- Age 27: Elite TE, 950 yards, 9 TDs, value = 6,500 (+30%)
- Age 30: Elite TE, 900 yards, 8 TDs, value = 5,500 (-15%)
- Age 33: Declining TE, 650 yards, 5 TDs, value = 2,500 (-55%)

**Lesson:** TEs bloom late; buy after breakout before age 28

______________________________________________________________________

## Strategic Applications by Team Status

### Contender Strategy: Win Now While Window Open

**Definition:** Top 4 roster with realistic championship odds

**Trade Philosophy:**

> "Your bench isn't scoring you points. Consolidate."

**Asset Management:**

| Asset Type                | Contender Approach                | Rationale                                     |
| ------------------------- | --------------------------------- | --------------------------------------------- |
| **Draft Picks (1st/2nd)** | Trade away for proven producers   | Picks are lottery tickets; you need certainty |
| **Young Upside Players**  | Trade for established stars       | Can't wait 2 years for development            |
| **Aging Veterans**        | Acquire at discount               | 1-2 year window aligns with your timeline     |
| **Depth Players**         | Trade 2-for-1 or 3-for-2 upgrades | Quality > quantity for contenders             |
| **Injured Stars**         | Avoid unless playoffs secured     | Can't afford dead roster spots                |

**Trade Execution:**

1. **Consolidation Trades**

   ```
   Give: WR2 (value: 4,000) + RB3 (value: 3,500) + 2026 1st (value: 3,500)
   Get: Elite WR1 (value: 9,000)

   Math: Give 11,000 value → Get 9,000 value

   Why Accept "Loss"?
   - You upgrade starting lineup
   - Bench players don't score points
   - Future pick doesn't help this year
   - Net gain: +15 PPG in starting lineup = championship difference
   ```

2. **Aging Veteran Acquisitions**

   ```
   Give: 2026 1st (value: 3,500) + 2027 2nd (value: 1,500)
   Get: 29-year-old RB (value: 4,000)

   Math: Give 5,000 value → Get 4,000 value

   Why Accept "Loss"?
   - RB produces NOW (when you need it)
   - Picks help 1-2 years from now (when window might close)
   - Value preservation meaningless if you don't win this year
   ```

**Common Mistakes:**

❌ Hoarding picks "just in case"
❌ Keeping young upside players who won't help this year
❌ Refusing to "overpay" by 10-15% for needed upgrades
❌ Making lateral trades instead of consolidating up

✅ Going all-in when window is open
✅ Trading future assets for present production
✅ Paying premiums for scarce positional needs
✅ Accepting value "losses" that improve starting lineup

**Example Contender Trades:**

**Trade 1: RB Upgrade**

```
Give: James Cook (value: 5,500) + Trey Benson (value: 2,800) + 2026 1st
Get: Christian McCaffrey (value: 8,000)

Analysis:
- McCaffrey 32 years old, limited dynasty value
- But produces RB1 overall this season
- Contender getting +5 PPG at RB1
- That's 85 points over 17-week season = multiple wins
```

**Trade 2: Depth Consolidation**

```
Give: WR15 overall + WR25 overall + WR40 overall
Get: WR5 overall

Analysis:
- Three bench players combined
- Get one elite starter
- Only top 2 WRs start each week
- Net gain: +8 PPG in starting lineup
```

______________________________________________________________________

### Rebuilder Strategy: Maximize Future Value

**Definition:** Bottom 4-6 team with no realistic playoff chances

**Trade Philosophy:**

> "Veterans are decaying assets. Convert to youth and picks before value disappears."

**Asset Management:**

| Asset Type                  | Rebuilder Approach                 | Rationale                                 |
| --------------------------- | ---------------------------------- | ----------------------------------------- |
| **Veterans (26+)**          | Sell immediately                   | Value declining, convert before worthless |
| **Draft Picks**             | Accumulate aggressively            | Rebuilding blocks + options               |
| **Young Players (22-24)**   | Buy and develop                    | Will peak when you're contending          |
| **Proven Stars (under 26)** | Hold or sell only for massive haul | Core of future contender                  |
| **Injured Young Players**   | Buy at discount                    | Dynasty = long-term, injuries temporary   |

**Trade Execution:**

1. **Veteran Fire Sale**

   ```
   Give: 28-year-old RB (value: 4,500)
   Get: 2026 1st (value: 3,500) + 2027 2nd (value: 1,500)

   Math: Give 4,500 value → Get 5,000 value

   Why Accept RB "Loss"?
   - RB worthless in 2 years when you're competing
   - Picks gain value as draft approaches
   - Two lottery tickets > one declining asset
   ```

2. **Buy Low on Injured Youth**

   ```
   Give: 2026 1st (value: 3,500)
   Get: 24-year-old WR coming off torn ACL (value: 4,000 pre-injury, 2,800 post-injury)

   Math: Give 3,500 value → Get 2,800 current value (but 4,000+ future value)

   Why Accept?
   - WR will recover before you're contending
   - Market panic creates discount
   - You're buying future value, not current production
   ```

**Rebuild Timeline:**

```
Year 1 (Tear Down):
- Sell ALL veterans 26+
- Accumulate 4-6 future 1st round picks
- Target young players on rebuilding NFL teams (opportunity coming)

Year 2 (Draft & Develop):
- Convert picks to young talent
- Buy low on sophomore slumps
- Continue selling aging pieces

Year 3 (Contention):
- Young core now productive
- Make 1-2 win-now trades
- Compete for championship
```

**Common Mistakes:**

❌ Keeping "my favorite veterans" who won't be relevant
❌ Trying to compete in Year 2 before roster ready
❌ Drafting for need instead of best player available
❌ Trading young studs for "fair value" (keep your core)

✅ Ruthlessly selling ALL veterans before value gone
✅ Patience to let young players develop
✅ Buying during market panic (injuries, slumps)
✅ Accumulating draft capital (quantity → quality)

**Example Rebuilder Trades:**

**Trade 1: RB Liquidation**

```
Give: Derrick Henry (age 30, value: 3,000)
Get: 2026 2nd (value: 2,000) + 2027 2nd (value: 1,500)

Analysis:
- Henry might have 1 year left
- By 2027 (when competing), he's worthless
- Two picks provide optionality and appreciation
```

**Trade 2: Youth Accumulation**

```
Give: 2026 1st (value: 3,500) + 2026 2nd (value: 2,000)
Get: 22-year-old breakout WR on bad team (value: 6,000)

Analysis:
- WR has talent + draft capital investment
- Currently low value due to bad team situation
- When competing in 2027-2028, he'll be 24-25 (prime)
- Converting picks to proven young talent at discount
```

______________________________________________________________________

### Middle-Class Strategy: Avoid Dynasty Purgatory

**Definition:** Picks 5-8, not contending but not bottom-feeding

**The Problem:**

> "Dynasty Purgatory is the worst place in dynasty. You're not winning, but you're not accumulating assets."

**Two Options:**

#### Option A: Accelerate to Contention (If Close)

**Criteria to Accelerate:**

- Top-10 QB (Superflex) or streaming options (1QB)
- 2 elite WRs or 1 elite + 2 solid
- 1 elite RB or 2 solid RBs
- Competitive TE
- Weak schedule or league parity

**If Criteria Met:**
→ Make 2-3 win-now trades
→ Sacrifice future picks for immediate upgrades
→ Go all-in for 1-2 year window

______________________________________________________________________

#### Option B: Rebuild (If Multiple Pieces Away)

**Criteria to Rebuild:**

- Missing 2+ elite players
- Aging core (27+ at RB, 29+ at WR)
- Young team with bad situation (will improve in 2 years)
- Tough schedule or strong league competition

**If Criteria Met:**
→ Sell veterans immediately
→ Accumulate picks + young players
→ Bottom-out for 1-2 years to get top picks
→ Reset and contend 2-3 years later

______________________________________________________________________

**The Decision Matrix:**

```
IF (Current Roster + 2 Win-Now Trades) = Top 3 Team:
    → ACCELERATE (become contender)

ELSE IF (Current Roster + Draft Picks + Young Players) = Top 3 Team in 2-3 years:
    → REBUILD (maximize future value)

ELSE:
    → ERROR: Stuck in purgatory, MUST pick a lane
```

**Warning Signs You're Stuck:**

- Haven't made playoffs in 2+ years
- Haven't finished bottom-3 in 2+ years
- Roster mix of veterans AND young players
- Hoarding picks but also trying to compete
- Making lateral trades (swapping mid-tier players)

**Escape Plan:**

1. **Honest Assessment:** Can you compete in next 2 years?
2. **Pick a Lane:** Contend or rebuild
3. **Execute Aggressively:** 3-5 trades in one offseason
4. **Commit:** Don't second-guess and reverse course

______________________________________________________________________

## Best Practices and Recommendations

### 1. Use Multiple Trade Value Charts

**Recommended Workflow:**

```
Step 1: Check market value (KeepTradeCut)
        → Understand current negotiable price

Step 2: Check expert consensus (FantasyPros or DLF)
        → Understand analytical perspective

Step 3: Check algorithmic model (DynastyProcess)
        → Identify mathematical fair value

Step 4: Compare all three
        → Look for discrepancies > 15%

Step 5: Make decision
        IF Market < Model → Consider buying
        IF Market > Model → Consider selling
        IF Market ≈ Model → Hold or make even swap
```

**Example Workflow:**

```
Trade Offer Received:
Give: Player A
Get: Player B + 2026 2nd

Step 1 - Market Value (KTC):
- Player A: 6,000
- Player B: 4,500
- 2026 2nd: 2,000
- Trade Value: 6,000 vs 6,500 (+8% in your favor)

Step 2 - Expert Value (FantasyPros):
- Player A: 5,500
- Player B: 4,800
- 2026 2nd: 1,800
- Trade Value: 5,500 vs 6,600 (+20% in your favor)

Step 3 - Model Value (DynastyProcess):
- Player A: 5,800
- Player B: 4,200
- 2026 2nd: 2,200
- Trade Value: 5,800 vs 6,400 (+10% in your favor)

Step 4 - Analysis:
- All three sources agree you're getting value
- Range: +8% to +20% advantage
- Average: +12.7% advantage

Step 5 - Decision:
→ ACCEPT (clear value gain across all methodologies)
```

______________________________________________________________________

### 2. Track Your League's Market

**Build a League Trade Database:**

Create a spreadsheet tracking:

- Date
- Teams involved
- Players/picks traded
- Perceived fairness (fair/lopsided/questionable)
- Market values at time of trade
- Winner/loser 1 year later

**After 1-2 Seasons, Analyze:**

1. **Positional Premiums/Discounts**

   - Does your league overvalue RBs? QBs? Draft picks?
   - Quantify: "Our league values RBs at +18% vs industry"

2. **Manager Tendencies**

   - Who trades frequently? (high liquidity partners)
   - Who never trades? (avoid wasting time)
   - Who trades emotionally? (exploit overreactions)
   - Who trades sharp? (respect their offers)

3. **Trade Patterns**

   - When do most trades happen? (target those windows)
   - What types of trades succeed? (model successful patterns)
   - What offers get rejected? (avoid wasting effort)

**Use This Data:**

- Adjust industry values by your league's systematic biases
- Target high-frequency traders for easier negotiations
- Avoid low-frequency traders unless massive edge
- Time your trades to match league activity windows

______________________________________________________________________

### 3. Create Personal Trade Rules

**Prevent Emotional Mistakes:**

Example Rule Set:

```
RULE 1: Never trade a player after one great game
        (Wait 3 weeks to separate signal from noise)

RULE 2: Never accept first offer
        (Counter at least once to find ceiling)

RULE 3: Only trade when edge > 15%
        (Account for uncertainty and transaction costs)

RULE 4: Sell aging RBs at 26, definitely by 27
        (Cliff comes fast, can't time it perfectly)

RULE 5: Always check 3 trade value sources before accepting
        (Avoid obvious mistakes)

RULE 6: If rebuilding, no players over 26
        (Strict youth threshold prevents half-measures)

RULE 7: If contending, only trade for immediate impact
        (No "maybe he breaks out" lottery tickets)

RULE 8: Sleep on every trade for 24 hours
        (Prevents emotional impulse trades)

RULE 9: Track every trade outcome for 2 years
        (Learn from mistakes, reinforce good process)

RULE 10: Never trade your favorite player for "fair value"
        (Enjoyment has value; demand premium)
```

**Customize Your Rules:**

Based on:

- Your league's tendencies
- Your risk tolerance
- Your time horizon
- Your competitive advantages

______________________________________________________________________

### 4. Understand the Psychology of Trading

**Common Cognitive Biases:**

| Bias                  | Description                           | Impact                                 | Mitigation                      |
| --------------------- | ------------------------------------- | -------------------------------------- | ------------------------------- |
| **Recency Bias**      | Over-weighting recent events          | Pay too much after big games           | Wait 3 weeks before trading     |
| **Confirmation Bias** | Seeking info that confirms beliefs    | Ignore warning signs                   | Actively seek contrary evidence |
| **Endowment Effect**  | Overvaluing what you own              | Won't trade at fair value              | Use objective value charts      |
| **Sunk Cost Fallacy** | Can't let go of past investment       | Hold declining assets                  | Focus on future value only      |
| **Anchoring**         | First number shapes negotiation       | Disadvantage if other side anchors low | Make first offer when possible  |
| **Loss Aversion**     | Losses hurt more than gains feel good | Risk-averse behavior                   | Frame as gains, not losses      |

**Exploit Others' Biases:**

1. **Recency Bias → Buy Low After Bad Games**

   - Talented player has 2 bad weeks
   - Offer during panic for discount

2. **Endowment Effect → Sell After You Acquire**

   - New owners value players less than previous owner
   - Trade to original owner for premium

3. **Anchoring → Make First Offer**

   - Start negotiation at advantageous number
   - Opponent's counter will be closer to your anchor

4. **Loss Aversion → Frame as Gains**

   - Instead of "You're losing Player X"
   - Say "You're gaining Player Y + Pick + Player Z"

______________________________________________________________________

### 5. Advanced: Market Making Strategy

**For Experienced Managers:**

Become the "market maker" in your league:

**What is Market Making?**

- Offer to facilitate trades between other managers
- Take small spreads on each transaction
- Build reputation as fair and active trader
- Create information advantage (see all offers)

**How it Works:**

```
Manager A wants WR, has RB
Manager B wants RB, has WR

You broker:
- Buy RB from Manager A for 5,000 value
- Sell RB to Manager B for 5,300 value
- Net gain: 300 value (6% spread)

Both sides happy (got what they wanted)
You profit without taking directional risk
```

**Benefits:**

1. **Volume Edge**

   - More trades = more opportunities to extract value
   - Law of large numbers: many +3% edges compound

2. **Information Edge**

   - See all trade discussions
   - Know who's buying/selling what
   - Identify market inefficiencies first

3. **Relationship Edge**

   - Reputation as fair dealer
   - Preferred trade partner
   - See best opportunities first

**Risk:**

- Requires active engagement (time intensive)
- Need league trust (can't be exploitative)
- Must understand values deeply (can't make mistakes)

______________________________________________________________________

### 6. Draft Pick Valuation Framework

**Rookie Pick Values are Highly Variable:**

**Factors Affecting Pick Value:**

1. **Draft Class Strength**

   - Strong class (2025 RBs): +20-30% value
   - Weak class (2026 RBs): -20-30% value

2. **Positional Needs**

   - Superflex league, weak QB class: QB picks decline
   - RB-scarce league, strong RB class: RB picks spike

3. **Time Until Draft**

   - Post-NFL Draft (peak hype): +30-40% vs mid-season
   - Mid-season (scoring 0 points): -30-40% vs post-draft

4. **Pick Position Certainty**

   - Early pick (1.01-1.04): +10% due to certainty
   - Mid pick (1.05-1.08): baseline
   - Late pick (1.09-1.12): -10% due to uncertainty
   - Future uncertain pick: -20% due to unknown position

**Strategic Pick Trading:**

**Best Time to BUY Picks:**

- Mid-season from contenders (focused on now)
- Weak draft class (undervalued)
- 2-3 years out (maximum discount)

**Best Time to SELL Picks:**

- Post-NFL Draft (peak hype)
- Strong draft class (overvalued)
- Current year (minimum discount)

**Pick Value Conversion Examples:**

```
2026 1st (mid-season): 3,000 value
2026 1st (post-NFL draft): 4,500 value
Gain: +50% by holding

2027 1st (acquired now): 2,400 value (80% of 3,000)
2027 1st (post-NFL draft 2027): 4,500 value
Gain: +87.5% by holding 2 years
```

**Lesson:** Draft picks appreciate like fine wine (unless class is bad)

______________________________________________________________________

### 7. When to Make Trades vs Hold

**Trade Actively When:**

✅ You have clear positional advantage (edge > 15%)
✅ Timing creates arbitrage (buy low, sell high windows)
✅ Your team status demands it (contender needs upgrade, rebuilder needs picks)
✅ League is active with fair traders (high liquidity)
✅ You have information advantage (injury news, film study)

**Hold When:**

✅ Market value = your model value (no edge)
✅ High transaction costs (league requires picks as "tax")
✅ Low league activity (offers won't come)
✅ Roster is balanced for your timeline
✅ Uncertainty is high (coaching changes, rookie unproven)

**Trade Frequency Recommendations:**

| Manager Type         | Trades Per Year | Philosophy                    |
| -------------------- | --------------- | ----------------------------- |
| **Market Maker**     | 15-25           | High volume, small edges      |
| **Active Optimizer** | 8-12            | Regular portfolio rebalancing |
| **Strategic Trader** | 4-7             | Targeted major moves          |
| **Buy and Hold**     | 1-3             | Minimal activity, draft well  |

**No "right" approach—depends on:**

- League activity level
- Your time availability
- Your trade skill confidence
- Your risk tolerance

______________________________________________________________________

### 8. Red Flags to Avoid Bad Trades

**Walk Away If:**

🚩 Pressure to accept quickly ("Offer expires in 1 hour")
🚩 Confused by the trade complexity (too many pieces)
🚩 Trading after big emotional game (yours or theirs)
🚩 Gut says no despite numbers saying yes (listen to yourself)
🚩 Other manager unusually eager (they know something?)
🚩 You're getting "their guy" easily (why are they moving him?)
🚩 League consensus says you're losing badly (wisdom of crowds)
🚩 You can't explain why you're winning to others (lack of clarity)

**Pause and Investigate If:**

⚠️ Player value suddenly dropped 20%+ (injury? role change?)
⚠️ League mates warning you against trade (ask why)
⚠️ Trading with known shark in your league (be extra careful)
⚠️ Complex 3-for-3 or 4-for-4 (obscures value extraction)
⚠️ You've made 3+ trades this week (fatigue errors)
⚠️ Trading your favorite player (emotion clouds judgment)

**Green Lights to Accept:**

✅ All value charts agree you're winning by 10%+
✅ Fills specific positional need for your team status
✅ You've slept on it and still feel good
✅ League consensus is "fair" or "slight win" for you
✅ Trading partner is fair and reasonable (not desperate)
✅ Can clearly articulate why you're winning
✅ Excited about acquiring the assets

______________________________________________________________________

## Summary: Building Your Trade Value Framework

### Step 1: Establish Your Foundation

1. **Bookmark Key Resources:**

   - KeepTradeCut: https://keeptradecut.com/
   - DynastyProcess: https://dynastyprocess.com/
   - FantasyPros: https://www.fantasypros.com/

2. **Understand Your League:**

   - Format (1QB/SF, PPR, TE Premium, roster size)
   - Scoring system (bonuses, yardage scoring)
   - League history (trade frequency, biases)
   - Manager sophistication (sharp vs casual)

3. **Define Your Team Status:**

   - Contender (top 4)
   - Rebuilder (bottom 4)
   - Middle (pick a lane!)

______________________________________________________________________

### Step 2: Develop Your Process

1. **For Every Trade Evaluation:**

   - Check 3 value sources (market, expert, model)
   - Calculate value gap (aim for 10-15% edge minimum)
   - Consider team status fit (does this help my timeline?)
   - Sleep on it for 24 hours (prevent emotional errors)
   - Track outcome for future learning

2. **Set Personal Rules:**

   - Age thresholds for buying/selling
   - Minimum value edge to trade
   - Positional priorities by team status
   - Trade frequency targets
   - Red flags that trigger "no"

______________________________________________________________________

### Step 3: Execute Strategically

1. **Timing-Based Arbitrage:**

   - Buy picks mid-season, sell post-draft
   - Buy injured youth, sell after recovery
   - Buy veterans from rebuilders, sell to contenders
   - Buy post-slump, sell post-surge

2. **Value-Based Arbitrage:**

   - Cross-reference 3 sources for discrepancies
   - Exploit league-specific biases
   - Buy when model > market
   - Sell when market > model

3. **Risk Management:**

   - Diversify (many small edges > one big bet)
   - Avoid home run swings (singles and doubles win)
   - Track record (learn from mistakes)
   - Adjust based on results (iterate strategy)

______________________________________________________________________

### Step 4: Continuous Improvement

1. **Track Everything:**

   - Record all trades (yours and league's)
   - Note values at time of trade
   - Review outcomes 1-2 years later
   - Identify patterns in wins/losses

2. **Learn from Mistakes:**

   - What biases tripped you up?
   - Which value sources were most accurate?
   - Did you trade too much or too little?
   - What rules would have prevented errors?

3. **Adapt to Your League:**

   - Update league bias adjustments annually
   - Revise personal rules based on learnings
   - Adjust strategy as league evolves
   - Exploit consistent inefficiencies

______________________________________________________________________

## Final Thoughts

Dynasty fantasy football trade values are **part science, part art**.

**The Science:**

- Mathematical models provide baseline frameworks
- Historical data informs aging curves and pick values
- Statistical aggregation reduces individual bias
- Consistent methodology enables reproducibility

**The Art:**

- Market psychology creates inefficiencies
- Timing separates good from great traders
- League-specific contexts require customization
- Relationships and reputation enable opportunities

**The Edge:**

- Use multiple tools to triangulate true value
- Exploit timing-based arbitrage opportunities
- Understand your league's unique characteristics
- Balance long-term value with team-specific needs
- Make many good trades, not one perfect trade

**Remember:**

> "The goal isn't to win every trade. The goal is to make many +EV trades and let the law of large numbers work in your favor."

**Most Importantly:**
Trade value charts are **tools, not rules**. Use them to inform decisions, but don't be enslaved by them. The best trade is the one that moves your team toward a championship, even if it "loses" by 10% on paper.

______________________________________________________________________

## Additional Resources

### Tools and Calculators

- **KeepTradeCut Calculator:** https://keeptradecut.com/trade-calculator
- **DynastyProcess Calculator:** https://calc.dynastyprocess.com/
- **FantasyPros Trade Analyzer:** https://www.fantasypros.com/nfl/trade-analyzer.php
- **Draft Sharks Trade Values:** https://www.draftsharks.com/trade-value-chart/dynasty/ppr

### Community and Research

- **DynastyProcess GitHub:** https://github.com/dynastyprocess (open-source tools)
- **Dynasty League Football Forum:** https://forum.dynastyleaguefootball.com/
- **r/DynastyFF Reddit:** https://www.reddit.com/r/DynastyFF/
- **FantasyPros Articles:** https://www.fantasypros.com/content/nfl/dynasty-nfl/

### Further Reading

- **DynastyProcess Pick Values:** https://dynastyprocess.com/blog/2019-02-14-2019pickvalues/
- **KTC Value Adjustment Explained:** https://www.javelinfantasyfootball.com/2022/09/30/how-the-ktc-adjustment/
- **Trade Windows Analysis:** https://www.thefantasyfootballers.com/dynasty/dynasty-trade-windows-timing-the-market-fantasy-football/

______________________________________________________________________

**Document Maintained By:** FF Analytics Project
**Last Updated:** October 29, 2025
**Next Review:** After 2026 NFL Draft (May 2026)
