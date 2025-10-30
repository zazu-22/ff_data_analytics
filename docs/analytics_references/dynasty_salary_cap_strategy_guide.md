# Dynasty Salary Cap & Contract Management Strategy Guide

**Last Updated:** October 29, 2025

This comprehensive guide provides frameworks, formulas, and strategies for managing salary caps and contracts in dynasty fantasy football leagues with salary caps. Drawing from both fantasy football best practices and real NFL salary cap management principles.

______________________________________________________________________

## Table of Contents

1. [Contract Valuation Frameworks](#1-contract-valuation-frameworks)
2. [Salary Cap Strategy](#2-salary-cap-strategy)
3. [Dead Cap Management](#3-dead-cap-management)
4. [Contract Negotiation and Extension Strategies](#4-contract-negotiation-and-extension-strategies)
5. [Additional Resources](#5-additional-resources)

______________________________________________________________________

## 1. Contract Valuation Frameworks

### 1.1 Multi-Year Contract Valuation

#### Basic Valuation Formula

**Player Value = (Expected Fantasy Points × Years Remaining) / Contract Cost**

A more sophisticated approach considers:

```
Contract Efficiency = Total Expected Fantasy Points / Total Cap Hit
Cost Per Point = Annual Cap Hit / Expected Annual Fantasy Points
```

#### Contract Value Components

When evaluating multi-year contracts, consider three key dimensions:

1. **Immediate Production Value**: Expected points in current season
2. **Future Production Value**: Expected points in remaining contract years (discounted)
3. **Contract Term Flexibility**: Years remaining and extension eligibility

**Example:**

- Player A: $20 salary, 3 years remaining, projected 250 fantasy points/year

  - Cost per point = $20 / 250 = $0.08 per point
  - Total value = 750 points / $60 total = 12.5 points per dollar

- Player B: $10 salary, 1 year remaining, projected 180 fantasy points

  - Cost per point = $10 / 180 = $0.056 per point
  - Total value = 180 points / $10 = 18 points per dollar

Player B provides better short-term efficiency, but Player A offers long-term stability.

### 1.2 Present Value Calculations for Future Cap Hits

#### NFL Present Value Model

The NFL uses present value calculations for deferred payments:

**PV = FV / (1 + r)^n**

Where:

- PV = Present Value
- FV = Future Value (actual contract amount)
- r = Discount Rate (NFL uses a specified rate per CBA)
- n = Number of years until payment

#### Fantasy Application

For dynasty fantasy leagues, adapt this to value future cap flexibility:

**Present Cap Value = Future Cap Hit / (1 + inflation_rate)^years_out**

**Example with 5% annual cap inflation:**

- Year 1: $20 salary = $20.00 present value
- Year 2: $20 salary = $20 / 1.05 = $19.05 present value
- Year 3: $20 salary = $20 / 1.1025 = $18.14 present value
- **Total 3-year PV = $57.19** (vs. $60 nominal)

This means a $20 salary in Year 3 is actually less burdensome than $20 today, assuming cap inflation.

### 1.3 Contract Efficiency Metrics

#### Key Performance Indicators

1. **Value Over Replacement Cost (VORC)**

   ```
   VORC = (Player Points - Replacement Points) / Contract Cost
   ```

   - Replacement = Average points from waiver wire at position
   - Higher VORC = better contract value

2. **Contract Surplus Value (CSV)**

   ```
   CSV = Market Value - Actual Cap Hit
   ```

   - Market Value = What player would cost in current auction
   - Positive CSV = underpaid player (good)
   - Negative CSV = overpaid player (bad)

3. **Years of Control Premium**

   ```
   Control Premium = Base Value × (1 + 0.1 × Years Remaining)
   ```

   - Add 10% value for each additional year of team control
   - Long-term contracts provide roster stability

#### Practical Example

Player comparison using all three metrics:

**Christian McCaffrey**: $45 salary, 2 years, projected 320 PPR points

- VORC = (320 - 180) / 45 = 3.11
- CSV = $50 market - $45 actual = +$5 (good value)
- Control Premium = 320 × 1.2 = 384 adjusted value

**Najee Harris**: $25 salary, 1 year, projected 240 PPR points

- VORC = (240 - 180) / 25 = 2.40
- CSV = $22 market - $25 actual = -$3 (overpaid)
- Control Premium = 240 × 1.1 = 264 adjusted value

McCaffrey provides better contract efficiency despite higher absolute cost.

______________________________________________________________________

## 2. Salary Cap Strategy

### 2.1 Cap Allocation by Position

#### Baseline Position Allocation (Standard PPR Leagues)

Based on $200 total cap in 1QB/2RB/3WR/1TE/1FLEX format:

| Position          | Allocation | Percentage | Rationale                                      |
| ----------------- | ---------- | ---------- | ---------------------------------------------- |
| **Running Back**  | $100       | 50%        | Scarcity, volatility, high floor/ceiling       |
| **Wide Receiver** | $50        | 25%        | Depth position, value in mid-rounds            |
| **Quarterback**   | $30        | 15%        | Consistent production, less scarcity (1QB)     |
| **Tight End**     | $15        | 7.5%       | Top-heavy position, value gap after elite tier |
| **Flex/Bench**    | $5         | 2.5%       | Roster depth, $1 fill-ins                      |

**Important Notes:**

- These are starting guidelines, not rigid rules
- Adjust based on league settings (Superflex, PPR vs. Standard, etc.)
- Be flexible during draft based on value opportunities

#### Format-Specific Adjustments

**Superflex/2QB Leagues:**

```
QB: 30-40% (increase by 15-25%)
RB: 35-40% (decrease by 10-15%)
WR: 20-25%
TE: 5-10%
```

**Standard (Non-PPR) Leagues:**

```
RB: 55-60% (increase by 5-10%)
WR: 20% (decrease by 5%)
QB: 15%
TE: 5-10%
```

### 2.2 Balancing Current Cap vs. Future Flexibility

#### The 70/30 Rule

**Allocate 70% of cap to starters, 30% for depth and future flexibility**

This ensures:

- Competitive starting lineup now
- Bench depth for injuries/bye weeks
- Cap space for in-season acquisitions
- Future extension flexibility

#### Cap Management Strategies

**1. Stars & Scrubs Approach**

- Spend 60-70% on 4-5 elite players
- Fill remaining spots with $1-3 value plays
- High risk/high reward strategy
- Works best with excellent waiver wire management

**Example Budget:**

- 3 elite RBs: $90 (CMC $45, Bijan $25, Gibbs $20)
- 2 elite WRs: $50 (Jefferson $30, Lamb $20)
- Value QB: $15 (Goff, Purdy tier)
- Value TE: $10 (Kincaid, Ferguson tier)
- Depth: $35 remaining

**2. Balanced Approach**

- Distribute cap more evenly across roster
- No player exceeds 20% of total cap
- Lower variance, consistent floor
- Better injury/volatility protection

**Example Budget:**

- Top RB: $35 (17.5%)
- RB2: $25 (12.5%)
- WR1: $30 (15%)
- WR2: $20 (10%)
- QB: $25 (12.5%)
- TE: $15 (7.5%)
- Depth: $50 (25%)

**3. Rookie-Heavy Strategy**

- Acquire early rookie picks for low-cost contracts
- Build competitive team on rookie deals
- Leverage surplus cap for veteran stars
- Requires strong scouting/evaluation skills

**Optimal Mix:**

- 75% roster on low-cost contracts (rookies, waiver adds)
- 25% roster on premium deals (proven stars)
- Creates maximum cap efficiency

### 2.3 Cap Percentage Benchmarks by Position

#### Elite Player Benchmarks (% of Total Cap)

**Top-5 Position Players:**

- QB1-5: 12-20% (in Superflex), 8-12% (in 1QB)
- RB1-5: 20-25%
- WR1-5: 15-20%
- TE1-3: 7-10%

**Mid-Tier Starters:**

- QB6-12: 8-12% (Superflex), 5-8% (1QB)
- RB6-15: 12-18%
- WR6-15: 10-15%
- TE4-8: 5-7%

**Depth Players:**

- All positions: 2-5% per player
- Bench/Taxi: \<2% per player

#### Position-Specific Cap Strategies

**Quarterback (1QB Format):**

- Don't overpay: QBs rarely justify >10% of cap
- Value exists in $8-15 range (QB6-12)
- Streaming is viable if league allows
- Exception: elite rushing QBs (Hurts, Allen) at 12-15%

**Running Back:**

- Most cap-intensive position in standard formats
- Elite RBs (top-5) justify 20-25% allocation
- Steep drop-off after top-12 creates scarcity
- Consider handcuffs at $2-5 for injury protection

**Wide Receiver:**

- Deep position with late-round value
- Elite WRs more consistent than elite RBs
- Can build WR corps with 2 mid-tier ($15-20) instead of 1 elite ($35)
- Better long-term value due to longer careers

**Tight End:**

- Most top-heavy position
- Kelce/Andrews tier: 8-10% justified
- Tier 2 (LaPorta, Kincaid, etc.): 5-7%
- Huge value cliff after top-8
- Don't pay more than $1 for TE12+

#### Annual Cap Benchmarking

Track these metrics annually:

```
Position Concentration Index = (Top 3 Salaries at Position) / (Total Position Allocation)

Healthy range: 50-70%
> 80%: Overconcentrated, injury risk
< 40%: Too spread out, lacking stars
```

**Example:**

- Total RB allocation: $100
- Top 3 RBs: $70 (CMC $35, Bijan $20, Gibbs $15)
- Concentration = 70% (healthy)

______________________________________________________________________

## 3. Dead Cap Management

### 3.1 Understanding Dead Cap Mechanics

#### What is Dead Cap?

Dead cap represents the accelerated salary cap charge when a player is released before their contract expires. It consists of:

1. **Remaining Guaranteed Money**: Any unpaid guaranteed salary or bonuses
2. **Prorated Bonus Acceleration**: Remaining signing bonus allocations

#### Dead Cap Calculation

**Dead Cap = Remaining Guaranteed Salary + Unamortized Signing Bonus**

**Example:**

- Player signed 4-year, $40 contract ($10/year)
- $20 signing bonus (prorates $5/year for 4 years)
- After Year 2, player is cut

```
Remaining salary: $20 (2 years × $10)
Remaining bonus proration: $10 (2 years × $5)
Total dead cap if guaranteed: $30
Cap savings: $10 (Year 3 salary avoided)
Net cap impact: -$20 (dead cap exceeds savings)
```

### 3.2 When to Cut Players: The Break-Even Framework

#### The Dead Cap Decision Formula

**Cut player if: Net Cap Savings > Replacement Cost**

```
Net Cap Savings = Current Cap Hit - Dead Cap Hit
Replacement Cost = Cost to replace player's production
```

**Decision Rule:**

```
If (Net Cap Savings - Replacement Cost) > 0, then CUT
Otherwise, KEEP
```

#### Practical Example

**Scenario:** Should you cut aging RB?

- Current cap hit: $20
- Dead cap if cut: $12
- Net cap savings: $8
- Expected fantasy points: 160
- Replacement player costs $5, projects 140 points

**Analysis:**

```
Production loss: 160 - 140 = 20 points
Cost to replace: $5
Net cap available for other upgrades: $8 - $5 = $3

Decision: CUT
- Free up $3 net cap space
- Lose only 20 fantasy points
- Can use $3 to upgrade elsewhere (potentially +30-40 points)
```

#### The Sunk Cost Principle

**Dead money is a sunk cost. Never let dead cap deter you from making optimal roster decisions.**

Focus on:

1. ✅ **Net cap savings** (cap hit - dead cap)
2. ✅ **Replacement cost** (cost of comparable player)
3. ✅ **Opportunity cost** (better uses for cap space)
4. ❌ **NOT absolute dead cap amount** (this is gone regardless)

### 3.3 Timing Considerations: June 1st Designations

#### Pre-June 1st Cut

**All dead cap accelerates into current year**

Example:

- Cut player with $15 dead cap on March 1
- All $15 counts against current year cap
- No future cap impact

#### Post-June 1st Cut

**Dead cap spreads over two years**

Same player cut June 2:

- Year 1: $8 dead cap
- Year 2: $7 dead cap
- Current year cap relief: Better
- Future year cap cost: Creates obligation

#### Strategic Application

**Use June 1st designations when:**

- Need immediate cap relief for current season
- Can afford future year cap hit
- Player's contract has multiple years remaining
- Rebuilding and pushing costs to future

**Don't use June 1st designations when:**

- Competing now and need future flexibility
- Next year's cap is already tight
- Dead cap is minimal (\<$5)

### 3.4 Minimizing Dead Cap Exposure

#### Contract Structure Best Practices

**1. Limit Guaranteed Years**

- Guarantee year 1 only for veterans
- Guarantee 2-3 years for elite players only
- Rookies: 4-year non-guaranteed contracts (best!)

**2. Use Roster Bonuses Instead of Signing Bonuses**

- Roster bonuses don't prorate
- No dead cap acceleration
- Player must be on roster to earn it
- Example: $20 salary with $10 roster bonus on Week 1

**3. Backload Contracts**

- Lower early years, higher later years
- Easy to cut before high-salary years
- Less dead cap accumulation

**Example Structure:**

```
Year 1: $15 (guaranteed)
Year 2: $18 (guaranteed)
Year 3: $25 (not guaranteed)
Year 4: $30 (not guaranteed)

Can cut after Year 2 with only $0 dead cap vs. $55 remaining
```

#### Position-Specific Dead Cap Tolerance

**Low Dead Cap Tolerance (\<5% total cap):**

- Running backs (injury risk, short careers)
- Aging veterans (30+ years old)
- Injury-prone players

**Moderate Dead Cap Tolerance (5-10% total cap):**

- Wide receivers (longer careers, more stable)
- Quarterbacks in 1QB leagues
- Young proven players (25-28 years old)

**Higher Dead Cap Tolerance (10-15% total cap):**

- Elite QBs in Superflex
- Top-5 WRs in prime (26-29)
- Cornerstone franchise players

#### Dead Cap Budget Rule

**Never allow total team dead cap to exceed 15-20% of total salary cap**

Example with $200 cap:

- Maximum recommended dead cap: $30-40
- Operating cap: $160-170
- Maintains roster competitiveness

Track this metric quarterly and avoid multiple high dead cap players.

______________________________________________________________________

## 4. Contract Negotiation and Extension Strategies

### 4.1 Extension Decision Framework

#### When to Extend vs. Let Walk

**Extend players when:**

1. ✅ Current salary < projected market value
2. ✅ Player under 28 years old (RB) or 30 years old (WR/QB)
3. ✅ Injury history is clean
4. ✅ Contract surplus value (CSV) is positive
5. ✅ Player fills critical roster need
6. ✅ Extension cost < 15% of total cap

**Let players walk when:**

1. ❌ Current salary ≥ projected market value
2. ❌ Player aging out of prime window
3. ❌ Multiple injury-plagued seasons
4. ❌ Better value available in draft/free agency
5. ❌ Team is rebuilding (1-2 year timeline)

#### Extension Valuation Formula

**Extension Value = (Projected Market Value × Discount Factor) + Extension Premium**

Where:

- **Discount Factor**: 0.85-0.95 (lock in player below market)
- **Extension Premium**: +$5 per additional year of control

**Example:**

- Player's market value: $25
- Extension offer: $25 × 0.90 = $22.50 base
- Adding 2 years of control: $22.50 + $5 = $27.50 per year
- 3-year extension = $27.50/year for 3 years

This gives team below-market rate if player improves, while player gets security.

### 4.2 Rookie Contract Management

#### Rookie Contract Structure

**Standard Rookie Deal:**

- **Drafted rookies**: 4-year contracts
- **Undrafted rookies**: 3-year contracts
- **Non-guaranteed**: Can cut without dead cap penalty
- **Low cost**: Typically $1-5 depending on draft position

**Rookie Wage Scale (Example):**

```
1st Round (Picks 1-12): $5
2nd Round (Picks 13-24): $4
3rd Round (Picks 25-36): $3
4th Round+ (Picks 37+): $2
Undrafted: $1
```

#### Taxi Squad Strategies

Many leagues allow **taxi squads** where:

- Rookies stored at $0 cap cost
- Must promote to active roster to play
- Contract activates upon promotion
- Maximizes roster space and cap efficiency

**Optimal Taxi Usage:**

1. Keep all injured rookies on taxi (e.g., season-ending IR)
2. Store developmental prospects (raw TEs, project WRs)
3. Promote only when starting or needed for depth
4. Never promote players you won't use

#### Rookie Extension Timing

**Extension Eligibility:**

- Players can extend during off-season before final contract year
- 1-year contracts cannot be extended
- Must have 2+ years remaining to be extension-eligible

**Optimal Extension Window:**

```
4-year rookie deal (Years 1-4)
- Year 1: Don't extend (too early, unknown)
- Year 2: Consider if top-10 breakout at position
- Year 3: Prime extension window for proven players
- Year 4: Last chance, often let walk to FA
```

**Example Timeline:**

- **Year 1 (rookie season)**: Ja'Marr Chase, $3 salary

  - Performance: 1,455 yards, 13 TDs, WR5 overall
  - Decision: Monitor, too early to extend

- **Year 2**: $3 salary

  - Performance: 1,046 yards, 9 TDs, WR12 overall
  - Decision: Offer 3-year extension at $20/year

- **Year 3**: Now on extension at $20/year

  - Market value: $30+ (locked in below market)
  - Surplus value: $10+/year

### 4.3 Veteran Contract Strategies

#### Market-Based Extension Pricing

**Top-10 Performance Pricing:**
Some leagues use automatic pricing formulas:

```
If player finishes top-10 at position in 2 of last 2 seasons:
Extension Salary = Average of Top-10 Salaries at Position
```

**Example:**

- WR finishes WR6 in Year 1, WR8 in Year 2
- Top-10 WR average salary: $22
- Extension offer: $22/year

**Top-5 Performance Premium:**

```
If player finishes top-5 at position in 1 of last 3 seasons:
Extension Salary = Average of Top-5 Salaries at Position + 15%
```

**Example:**

- RB finishes RB3 in Year 2
- Top-5 RB average salary: $30
- Extension offer: $30 × 1.15 = $34.50/year

#### Restructuring Existing Contracts

**Restructure when:**

- Need immediate cap space
- Player willing to take less guaranteed money
- Spreading cap hit across multiple years helps

**Restructure Formula:**

```
Convert Base Salary → Signing Bonus
Prorate over remaining contract years
```

**Example:**

- Current deal: Year 2 of 4-year contract
- Year 2 salary: $25
- Restructure: Convert $15 to signing bonus

```
Original Year 2 cap hit: $25
New Year 2 cap hit: $10 salary + $5 bonus = $15 (save $10)
Future years: Add $5/year in Years 3 and 4 (bonus proration)
```

**Risk:** Creates future dead cap obligations. Only restructure players you're committed to keeping.

#### Age-Based Extension Guidelines

| Position          | Prime Years | Extension Age Limit | Max Extension Years |
| ----------------- | ----------- | ------------------- | ------------------- |
| **Running Back**  | 23-27       | 27                  | 2-3 years           |
| **Wide Receiver** | 25-30       | 30                  | 3-4 years           |
| **Quarterback**   | 27-35       | 34                  | 3-5 years           |
| **Tight End**     | 25-31       | 30                  | 3-4 years           |

**Never extend players beyond these age limits.** Risk of decline exceeds value of continuity.

#### The "Breakout Year" Extension Strategy

**Most valuable time to extend: After breakout season, before market recognizes value**

**Example:**

- Amon-Ra St. Brown after 2022 season
- 2021 (rookie): $3 salary, WR40
- 2022 (year 2): $3 salary, WR6 (breakout!)
- Extension opportunity: Lock in at $18-20/year before market values at $25-30

**Steps:**

1. Identify players in Year 2-3 of rookie deals
2. Monitor weekly production for breakouts
3. Offer extension immediately after season
4. Structure 3-4 year deals to maximize surplus value

### 4.4 Contract Negotiation Tactics

#### Negotiation Leverage Points

**Team Leverage:**

- Years of control remaining
- Player's age and injury history
- Availability of replacements in draft/FA
- Current salary vs. market value

**Player Leverage:**

- Recent top-tier performance
- Scarcity at position
- Multiple teams interested
- Approaching free agency

#### Fair Value Negotiation Formula

```
Fair Extension = (Player Value + Team Value) / 2

Where:
Player Value = Market value based on performance
Team Value = Discounted value for years of control
```

**Example Negotiation:**

- Player wants: $30/year (market rate for top-10 WR)
- Team offers: $24/year (hometown discount)
- Fair value: ($30 + $24) / 2 = $27/year
- Structure: 3 years, $27/year, $15 guaranteed Year 1

#### Extension Premium Calculation

**Standard Extension Cost: Original Salary + $5/year**

**Example:**

- Player drafted at $15 salary
- 4-year rookie contract
- Extension in Year 3: $15 + $5 = $20/year extension
- Can only extend once (one-time $5 bump)

#### Walk-Away Points

**Never extend if:**

- Extension cost > 125% of market value
- Player over 30 (RB) or 33 (WR/QB)
- Injury history includes 2+ missed seasons
- Team in rebuild mode (1-2 year timeline)

______________________________________________________________________

## 5. Additional Resources

### Key Sources Referenced

1. **Dynasty League Football**

   - [League Tycoon Dynasty Salary Cap Guide](https://dynastyleaguefootball.com/2023/12/15/league-tycoon-dynasty-salary-cap-fantasy-football/)
   - [Salary Cap Confidential Series](https://dynastyleaguefootball.com/2019/05/05/salary-cap-confidential-introduction/)
   - [Auction and Salary Cap League Approach](https://dynastyleaguefootball.com/2015/08/20/an-approach-to-auction-and-salary-capcontract-leagues/)

2. **The Fantasy Footballers**

   - [Dynasty 101: Rules, Formats and Salary Cap Leagues](https://www.thefantasyfootballers.com/dynasty/dynasty-101-rules-and-formats-plus-salary-cap-leagues-fantasy-football/)
   - [Building an Auction/Salary Cap Draft Budget](https://www.thefantasyfootballers.com/analysis/fantasy-football-building-using-a-budget-for-auction-salary-cap-drafts/)

3. **FantasyPros**

   - [Salary Cap Leagues Spending Strategy (2022)](https://www.fantasypros.com/2022/08/salary-cap-leagues-spending-strategy-advice-2022-fantasy-football/)
   - [How Contract Length and Term Impact Dynasty Player Value](https://www.fantasypros.com/2020/05/how-contract-length-and-term-impact-dynasty-player-value-fantasy-football/)

4. **League Tycoon**

   - [Fantasy Football Contract League Ultimate Guide](https://leaguetycoon.com/contract-leagues/)
   - [Salary Cap Fantasy Leagues](https://leaguetycoon.com/salary-cap-fantasy-leagues/)

5. **NFL Salary Cap Resources**

   - [Over the Cap - Understanding NFL Contracts](https://overthecap.com/)
   - [Spotrac - Understanding NFL Dead Cap](https://www.spotrac.com/news/_/id/1781/understanding-nfl-dead-cap)
   - [Sports Illustrated - How NFL Salary Cap Works](https://www.si.com/nfl/2023/05/17/nfl-business-football-explaining-salary-cap)
   - [Pro Football Network - NFL Salary Cap Explained (2025)](https://www.profootballnetwork.com/how-does-nfl-salary-cap-work/)

6. **CBS Sports**

   - [2024 Fantasy Football Salary Cap Strategies](https://www.cbssports.com/fantasy/football/news/2024-fantasy-football-salary-cap-strategies-and-prep-to-maximize-huge-wins-on-draft-day/)
   - [2025 Salary Cap Draft Results and Analysis](https://www.cbssports.com/fantasy/football/news/fantasy-football-2025-salary-cap-draft-results-recap-every-bid-best-buys-worst-values-strategies-more/)

7. **DraftKick**

   - [Ultimate Guide to Fantasy Salary Cap Leagues](https://draftkick.com/blog/ultimate-guide-fantasy-salary-cap-auction-leagues/)

8. **Dynasty Football Factory**

   - [Dynasty and the NFL Salary Cap](https://dynastyfootballfactory.com/dynasty-and-the-nfl-salary-cap/)

### Advanced Reading

**NFL Salary Cap Management (Applicable to Fantasy):**

- [PFF: Three-Year Salary Cap Analysis for 32 NFL Teams](https://www.pff.com/news/nfl-three-year-salary-cap-analysis-32-nfl-teams-2023)
- [Hogs Haven: Playing GM - A Primer on Salary Cap Management](https://www.hogshaven.com/2019/1/15/18183366/reprint-playing-gm-a-primer-on-salary-cap-management)
- [The 33rd Team: NFL Salary Cap Explained](https://www.the33rdteam.com/explaining-nfl-salary-cap/)

**Academic Research:**

- [ScienceDirect: Optimizing Allocation of Funds Under Salary Cap](https://www.sciencedirect.com/science/article/abs/pii/S0169207018301559)

### Tools and Calculators

- **Keep Trade Cut**: [Dynasty Trade Calculator](https://keeptradecut.com/trade-calculator)
- **DynastyProcess**: [Trade Calculator](https://calc.dynastyprocess.com/)
- **Footballguys**: [Dynasty Salary Cap Rankings](https://www.footballguys.com/rankings/duration/dynasty?salarycap=1)
- **FantasyPros**: [Dynasty Trade Value Charts](https://www.fantasypros.com/2025/10/fantasy-football-rankings-dynasty-trade-value-chart-october-2025-update/)

______________________________________________________________________

## Quick Reference Formulas

### Contract Valuation

```
Contract Efficiency = Total Expected Fantasy Points / Total Cap Hit
Cost Per Point = Annual Cap Hit / Expected Annual Fantasy Points
VORC = (Player Points - Replacement Points) / Contract Cost
CSV = Market Value - Actual Cap Hit
```

### Dead Cap Analysis

```
Net Cap Savings = Current Cap Hit - Dead Cap Hit
Cut Decision = (Net Cap Savings - Replacement Cost) > 0
```

### Extensions

```
Extension Value = (Projected Market Value × 0.90) + $5 Control Premium
Fair Extension = (Player Value + Team Value) / 2
```

### Cap Allocation

```
Position Concentration = (Top 3 Salaries at Position) / Total Position Allocation
Operating Cap = Total Cap - Dead Cap (should be >80% of total)
```

______________________________________________________________________

## Conclusion

Successful dynasty salary cap management requires balancing:

1. **Current competitiveness** with future flexibility
2. **Star power** with roster depth
3. **Contract efficiency** with roster needs
4. **Dead cap avoidance** with necessary cuts

The frameworks in this guide provide decision-making tools, but remember:

- Every league has unique settings and dynamics
- Player values fluctuate based on performance and injuries
- Risk tolerance varies by team goals (contending vs. rebuilding)
- Market inefficiencies create opportunities

**Core principles:**

- Maximize cost per point efficiency
- Build on rookie contracts
- Don't overpay for name value
- Treat dead cap as sunk cost
- Extend only players with positive surplus value
- Maintain 15-20% cap flexibility for opportunities

Use these frameworks as guidelines, adapt to your specific league, and track your metrics over time to refine your strategy.

______________________________________________________________________

*Last updated: October 29, 2025*
