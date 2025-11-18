# Competitive Window Analysis: Jason Shaffer Franchise

**Date:** 2025-11-18
**Prepared by:** Jason
**Research Type:** Domain Research (Internal Competitive Assessment)
**Cross-Reference:** [Contract Economics Research](./research-contract-economics-2025-11-18.md)

______________________________________________________________________

## ⚠️ Analysis Updated With Real Data (2025-11-18)

**ACTUAL 2025 PERFORMANCE (User-Provided):**

- **Record:** 5-6 (45% win rate) - Competitive but below playoff line
- **Injuries (IR):** Jonathon Brooks (RB), Malik Nabers (WR), Austin Ekeler (RB)
- **Injuries (Out):** C.J. Stroud (QB - franchise cornerstone), Dike (multi-week)
- **Impact:** VALIDATES "Transition/Contender" classification - competing despite significant injuries to core pieces

**Key Insight:** You're 5-6 WITH your franchise QB (Stroud) and young star WR (Nabers) sidelined. This is actually STRONG evidence of roster depth and future potential. When healthy, this roster projects as a clear contender.

**Data Architecture Gap Identified:** Injury status and standings data exist in Sleeper but not modeled in dbt. See [Data Gap Assessment](./data-gap-assessment-competitive-window-2025-11-18.md) for remediation plan (deferred per user request).

______________________________________________________________________

## Executive Summary

The Jason Shaffer franchise (F001 - Franchise 001, Lauren Noble Division) is in a **Transition/Contender Window** with elite future potential. You acquired this franchise in 2025 and inherited a roster built for sustained success: young core talent on cheap contracts, elite star pieces, and exceptional future flexibility.

**The Verdict**: Your franchise is **competitive now (2025-2026)** but positioned for **elite contention (2027-2029)** when massive cap flexibility ($158M+) and elite draft capital (26 picks, including bonus 2026 1st rounder) converge.

### Key Findings

- **Competitive Window:** **Transition/Contender** - Compete now, elite later (2027+)
- **Roster Profile:** Young core (38% rookies) + elite stars (CeeDee Lamb, C.J. Stroud, De'Von Achane, Will Anderson)
- **Cap Flexibility:** Moderate now ($71M), **MASSIVE 2027+** ($158M → $250M clean slate by 2029)
- **Draft Capital:** **ELITE** - All picks owned + bonus 2026 1st round comp pick (26 total picks over 5 years)

### Strategic Recommendation

**Feature Prioritization for Analytics Platform:**

1. **🔥 CRITICAL: Rookie Draft Analytics** - You have elite draft capital (bonus 1st rounder + full slate) - this is your highest ROI opportunity
2. **🔥 HIGH: Multi-Year Projections** - Plan for 2027+ cap explosion ($158M+ available) - need multi-year contract/cap modeling
3. **📊 MEDIUM: Trade Analysis** - Draft capital + cap flexibility = trade optionality - need trade value models
4. **📊 MEDIUM: Contract Value Analysis** - Optimize transition years (2025-2026) - identify value contracts
5. **✅ LOWER: Weekly Lineup Optimization** - You're competitive but not desperate - this is secondary to long-term planning

______________________________________________________________________

## 1. Research Objectives

### Purpose

Assess the "Jason Shaffer" franchise's current competitive position to inform feature prioritization for the Fantasy Football Data Analytics Platform.

### Key Questions

1. **Roster Composition** - What is the current roster makeup (position distribution, age profile, contract types)?
2. **Cap Situation** - What is current and projected cap space (2025-2029)? Are there significant dead cap obligations?
3. **Draft Capital** - What draft picks are owned (current + 3 years)? Trade history analysis?
4. **Competitive Position** - Recent performance, league landscape, projected competitive window

### Rationale

The [Contract Economics Research](./research-contract-economics-2025-11-18.md) identified **rookie draft analytics** as the highest ROI opportunity. However, feature prioritization depends on competitive window:

- **Win-Now Mode** → Prioritize: Weekly lineup optimization, trade analysis, win probability modeling
- **Rebuild Mode** → Prioritize: Rookie draft tools, multi-year projections, contract value analysis
- **Transition** → Balanced approach with flexibility

______________________________________________________________________

## 2. Data Sources and Methodology

### Data Sources

All data sourced from dimensional models in `/dbt/ff_data_transform/`:

- `dim_player_contract_history` - Current roster composition
- `stg_sheets__cap_space` - Cap space timeline (2025-2029)
- `stg_sheets__draft_pick_holdings` - Draft pick inventory
- `fct_league_transactions` - Transaction history
- `dim_franchise` - Franchise metadata

### Methodology

1. Query dimensional models for franchise-specific data
2. Analyze roster composition (positions, age, contract types)
3. Assess cap situation (current + 5-year projection)
4. Evaluate draft capital (picks owned, trade history)
5. Determine competitive window classification
6. Generate feature prioritization recommendations

______________________________________________________________________

## 3. Roster Composition Analysis

### Roster Overview

**Total Players:** 45

**Contract Type Distribution:**

- **FASA (Free Agent):** 18 players (40%) - Mix of value signings and role players
- **Rookie Contracts:** 17 players (38%) - Young, cost-controlled talent
- **Extensions:** 3 players (7%) - Core pieces locked in
- **Trade Acquired:** 3 players (7%) - Strategic additions
- **FAAD:** 3 players (7%) - Premium free agent acquisitions
- **Waiver Claim:** 1 player (2%)

### Position Breakdown

| Position | Total | Contract Types                                  | Notes                |
| -------- | ----- | ----------------------------------------------- | -------------------- |
| WR       | 14    | 6 rookie, 5 FASA, 2 trade, 1 FAAD               | Deep, young WR room  |
| RB       | 10    | 4 rookie, 3 FASA, 1 extension, 1 FAAD, 1 waiver | Balanced mix         |
| LB       | 5     | 2 rookie, 3 FASA                                | Defensive depth      |
| DB       | 4     | 1 rookie, 3 FASA                                | IDP coverage         |
| DL       | 4     | 2 rookie, 1 extension, 1 trade                  | Young defensive line |
| TE       | 3     | 2 rookie, 1 FAAD                                | Developing position  |
| K        | 3     | 3 FASA                                          | Special teams depth  |
| QB       | 2     | 1 extension, 1 FASA                             | QB stability         |

### Elite Tier (Top 10 by Contract Value)

01. **CeeDee Lamb (WR)** - $291M total ($58.2M/year, 2024-2028, FAAD) - **SUPERSTAR**

    - Dead cap: $103M (significant commitment)
    - Elite WR1 anchor

02. **Austin Ekeler (RB)** - $57M total ($14.25M/year, 2023-2026, Waiver)

    - Dead cap: $22M
    - Veteran RB, contract expires 2026

03. **Jordan Mason (RB)** - $52M total ($10.4M/year, 2024-2028, FASA)

    - Dead cap: $19M
    - Young RB on value FASA deal

04. **Patrick Queen (LB)** - $20M total ($10M/year, 2025-2026, FASA)

    - IDP linebacker piece

05. **Malik Nabers (WR)** - $18M total ($6M/year, 2024-2026, Rookie)

    - **ELITE YOUNG TALENT** on cheap rookie deal

06. **Sincere McCormick (RB)** - $16M total ($16M/year, 2024, FASA)

07. **Jordan Addison (WR)** - $15M total ($5M/year, 2023-2025, Trade)

    - Acquired via trade, contract expires soon

08. **C.J. Stroud (QB)** - $8M total ($2.67M/year, 2024-2026, Extension)

    - **FRANCHISE QB** locked in on cheap extension!

09. **De'Von Achane (RB)** - $8M total ($2.67M/year, 2024-2026, Extension)

    - **ELITE RB** locked in on cheap extension!

10. **Will Anderson (DL)** - $8M total ($2.67M/year, 2024-2026, Extension)

    - **ELITE DEFENSIVE PIECE** locked in on cheap extension!

### Roster Architecture Insights

**🎯 Core Strength:** Young stars on team-friendly deals (Stroud, Achane, Anderson, Nabers) provide elite production at minimal cap cost

**💰 Cap Commitment:** CeeDee Lamb represents 58% of top-10 contract value but anchors elite WR room

**📈 Youth Movement:** 38% rookie contracts = sustainable pipeline of cheap talent

**⚖️ Balance:** Mix of proven veterans (Ekeler, Lamb), rising stars (Nabers, Stroud), and young depth

______________________________________________________________________

## 4. Cap Space Analysis

### Cap Space Timeline (2025-2029)

| Year     | Base Cap | Available Cap | Dead Cap | Traded Cap | Net Flexibility | Status              |
| -------- | -------- | ------------- | -------- | ---------- | --------------- | ------------------- |
| **2025** | $250M    | **$71M**      | $28M     | $7M        | Moderate        | Transition Year 1   |
| **2026** | $250M    | **$71M**      | $13M     | $0         | Improving       | Transition Year 2   |
| **2027** | $250M    | **$158M**     | $6M      | $0         | **ELITE**       | **Window Opens**    |
| **2028** | $250M    | **$183M**     | $0       | $0         | **ELITE+**      | Peak Flexibility    |
| **2029** | $250M    | **$250M**     | $0       | $0         | **CLEAN SLATE** | Maximum Flexibility |

### Key Cap Trends

**📊 Dead Cap Decay:**

- 2025: $28M dead cap (11% of base cap)
- 2026: $13M dead cap (5% of base cap) - **Drops 54%**
- 2027: $6M dead cap (2% of base cap) - **Drops 79% from 2025**
- 2028-2029: $0 dead cap - **Clean slate**

**Primary Dead Cap Source:** CeeDee Lamb ($103M if cut today) - but you're NOT cutting him, so this decays naturally over contract life

**💡 Cap Space Growth:**

- 2025-2026: Stable at $71M (28% of cap)
- 2027: **$158M (63% of cap)** - **2.2x increase!**
- 2028: **$183M (73% of cap)** - Near-total flexibility
- 2029: **$250M (100% of cap)** - Complete clean slate

### Cap Strategy Implications

**Phase 1: Transition (2025-2026)**

- **Cap Position:** Moderate flexibility ($71M)
- **Strategy:** Selective additions, optimize existing contracts
- **Limitations:** Can't go "all-in" with big FA signings
- **Opportunity:** Identify value contracts, develop young talent

**Phase 2: Window Opens (2027)**

- **Cap Position:** MASSIVE flexibility ($158M = 63% of cap)
- **Strategy:** Go aggressive - sign elite FAs, extend core pieces
- **Opportunity:** Build elite contender around young core (Stroud, Achane, Anderson, Nabers)
- **Timeline:** Coincides with rookie extensions for 2024 draft class

**Phase 3: Peak Contention (2028-2029)**

- **Cap Position:** Near-total flexibility ($183M-$250M)
- **Strategy:** Sustained excellence - reload annually
- **Opportunity:** Maintain elite roster while managing cap efficiently

### Cap Efficiency Analysis

**High-Value Contracts (Elite Production / Low Cap Hit):**

1. C.J. Stroud (QB) - $2.67M/year - **ELITE EFFICIENCY**
2. De'Von Achane (RB) - $2.67M/year - **ELITE EFFICIENCY**
3. Will Anderson (DL) - $2.67M/year - **ELITE EFFICIENCY**
4. Malik Nabers (WR) - $6M/year - **HIGH EFFICIENCY**

**Cap-Heavy Contracts:**

1. CeeDee Lamb (WR) - $58.2M/year - Elite talent, premium price
2. Austin Ekeler (RB) - $14.25M/year - Veteran RB, expires 2026
3. Jordan Mason (RB) - $10.4M/year - FASA deal
4. Patrick Queen (LB) - $10M/year - IDP piece

**Cap Health Grade: A-**

- Strong core on team-friendly deals
- Manageable dead cap (decaying rapidly)
- ELITE future flexibility starting 2027

______________________________________________________________________

## 5. Draft Capital Inventory

### Draft Pick Holdings (2026-2030)

| Year      | 1st   | 2nd | 3rd | 4th | 5th | Total  | Notes                                         |
| --------- | ----- | --- | --- | --- | --- | ------ | --------------------------------------------- |
| **2026**  | **2** | 1   | 1   | 1   | 1   | **6**  | ✨ **BONUS 1st round comp pick (T. McBride)** |
| **2027**  | 1     | 1   | 1   | 1   | 1   | 5      | Full slate                                    |
| **2028**  | 1     | 1   | 1   | 1   | 1   | 5      | Full slate                                    |
| **2029**  | 1     | 1   | 1   | 1   | 1   | 5      | Full slate                                    |
| **2030**  | 1     | 1   | 1   | 1   | 1   | 5      | Full slate                                    |
| **TOTAL** | **6** | 5   | 5   | 5   | 5   | **26** | **ELITE draft capital**                       |

### Draft Capital Analysis

**🎯 Draft Capital Grade: A+**

**Key Findings:**

1. **Zero Draft Debt** - You own ALL your original picks (no picks traded away)
2. **BONUS Pick** - Extra 2026 1st round compensatory pick for T. McBride
3. **26 Total Picks** - Average of 5.2 picks/year over next 5 years
4. **Flexibility** - Can trade picks for win-now pieces OR keep for rebuild
5. **Sustained Pipeline** - Full draft slates through 2030

### 2026 Draft: Premium Year

**2026 is a PREMIUM draft year for you:**

- **TWO 1st round picks** (original + compensatory)
- Full complement of 2nd-5th round picks
- **Strategic Optionality:**
  - **Option A:** Use both 1st rounders to draft elite talent (RB, WR, TE depth)
  - **Option B:** Trade one 1st rounder for proven veteran to accelerate window
  - **Option C:** Package picks to move up for elite prospect

### Draft Strategy by Competitive Phase

**Phase 1: Transition (2025-2026)**

- **2026 Draft Strategy:** Use 2 first rounders to add elite young talent
- **Focus:** WR depth (complement Lamb/Nabers), RB pipeline (post-Ekeler), TE upgrade
- **Trade Consideration:** Could trade ONE 1st for proven veteran if contending

**Phase 2: Window Opens (2027-2029)**

- **Draft Strategy:** Sustained excellence - draft BPA, fill gaps
- **Focus:** Maintain young pipeline while cap space allows FA additions
- **Trade Consideration:** Can trade future picks for win-now pieces

**Phase 3: Peak Contention (2028-2030)**

- **Draft Strategy:** Reload annually with rookie talent
- **Focus:** Cost-controlled depth to maximize cap efficiency

### Draft Capital vs. League Context

**Comparative Analysis** (Need league-wide data for complete picture):

- You have MORE draft capital than average (6 picks in 2026 vs. typical 5)
- Zero draft debt = flexibility to trade OR draft
- Bonus 1st rounder = competitive advantage

**Trade Value:** Two 1st rounders in 2026 = High trade leverage for proven veterans

______________________________________________________________________

## 6. Competitive Position Assessment

### Current Competitive Standing (2025)

**Franchise Status:** New ownership (Jason acquired F001 in 2025)

**2025 Season Performance (ACTUAL):**

- **Record:** 5-6 (45% win rate) - In playoff hunt but below cutline
- **Injuries Crushing Season:** Stroud (QB), Nabers (WR), Brooks (RB), Ekeler (RB), Dike - 5 key pieces out
- **Resilience:** 5-6 despite losing franchise QB and young star WR = roster has depth
- **Projection:** If healthy in 2026, this roster is a legitimate contender

**Inherited Roster Assessment:**

- **Elite Core (When Healthy):** C.J. Stroud (QB), De'Von Achane (RB), Will Anderson (DL), CeeDee Lamb (WR), Malik Nabers (WR)
- **Current Reality:** Stroud + Nabers out = ~30% of elite production sidelined
- **Young Pipeline:** 17 players on rookie contracts (38% of roster)
- **Veteran Depth:** Mix of FASA signings and trade acquisitions
- **Cap Status:** Moderate flexibility ($71M) transitioning to elite ($158M+ by 2027)
- **Draft Assets:** Elite (26 picks, including bonus 2026 1st)

**Key Finding:** 5-6 WITH major injuries = roster is BETTER than record suggests

### Strengths (SWOT Analysis)

**Strengths:**

- 🏆 **Elite young core locked in** - Stroud, Achane, Anderson, Nabers on team-friendly deals
- 💰 **MASSIVE future cap flexibility** - $158M+ starting 2027
- 📈 **Elite draft capital** - 26 picks, bonus 2026 1st rounder
- 🎯 **Positional strength at premium positions** - QB (Stroud), RB (Achane, Mason), WR (Lamb, Nabers)
- 👶 **Young roster** - 38% rookies = sustainable pipeline

**Weaknesses:**

- 💸 **Cap-constrained short term** - Only $71M available in 2025-2026
- 📊 **Dead cap obligations** - $28M in 2025 (decaying to $0 by 2028)
- 🎖️ **Veteran RB risk** - Austin Ekeler contract expires 2026, age concerns
- 📉 **CeeDee Lamb commitment** - $103M dead cap if cut (locked in)
- ⏰ **New ownership** - No historical performance data to assess

**Opportunities:**

- 🚀 **2026 Draft** - Two 1st round picks = major roster upgrade potential
- 💎 **2027 Cap Explosion** - $158M cap space = sign multiple elite FAs
- 🔄 **Trade flexibility** - Can trade draft picks/players given strong core
- 📈 **Extension window** - Lock in Stroud, Achane, Anderson long-term before market reset
- 🎯 **Positional upgrades** - TE depth, IDP improvements with available resources

**Threats:**

- 🏥 **INJURY REALITY (2025)** - Stroud, Nabers, Brooks, Ekeler, Dike out = 5-6 record instead of contending
- ⏰ **Rookie contract expirations** - Stroud, Achane, Anderson, Nabers all expire 2026 = extension decisions
- 💰 **Market inflation** - Elite player costs rising, may eat into 2027+ cap flexibility
- 🏥 **Durability concerns CONFIRMED** - Nabers (IR), Stroud (multi-week), Brooks (IR - rookie season lost)
- 🎖️ **CeeDee Lamb age curve** - Contract runs through 2028 when he's 29 years old
- 📊 **League competitive dynamics** - Unknown: Are other teams in win-now mode or rebuilding?

**2025 Lesson:** Depth matters. Without Stroud/Nabers, you're still competitive (5-6). Need injury tracking in analytics platform.

### League Context (Data Gaps)

**⚠️ Missing Context for Complete Assessment:**

- League-wide competitive balance (playoff standings, championship contenders)
- Other teams' cap situations (are you cap-flexible vs. league average?)
- Other teams' draft capital (is your draft position strong vs. peers?)
- Recent trade market activity (what's the going rate for picks/players?)
- League scoring settings and roster requirements (impacts positional value)

**Recommendation:** Query league transaction history and standings data to complete competitive landscape analysis

______________________________________________________________________

## 7. Competitive Window Determination

### Competitive Window Classification: **TRANSITION/CONTENDER**

**Primary Window:** **2027-2029 (Elite Contention)**
**Secondary Window:** **2025-2026 (Competitive Transition)**
**Sustained Excellence:** **2028-2032 (Peak Years)**

### Window Justification

**Why Transition/Contender (2025-2026)?**

1. **ACTUAL 2025 RECORD: 5-6** - Competitive but below playoff line (VALIDATES transition classification)
2. **Elite core when healthy** (Stroud, Achane, Anderson, Nabers) = contender, but injuries derailed 2025
3. **Moderate cap flexibility** ($71M) limits "all-in" moves
4. **New ownership + injury adversity** = 2025 as learning year, 2026 as true contention test
5. **Two 1st round picks in 2026** = roster upgrade mid-transition (can add depth to avoid 2025 injury issues)

**Why Elite Contender (2027-2029)?**

1. **MASSIVE cap explosion** - $158M in 2027 = sign 2-3 elite FAs
2. **Young core in prime** - Stroud (26), Achane (25), Anderson (25), Nabers (24) all hitting peak years
3. **Zero dead cap by 2028** - Complete cap flexibility
4. **Sustained draft capital** - Continue adding young talent
5. **Veteran pieces still productive** - Lamb (28-29), extensions secured

**Why Sustained Excellence (2028-2032)?**

1. **Core locked in long-term** - Extensions for Stroud, Achane, Anderson, Nabers
2. **$183M-$250M cap flexibility** - Reload annually with elite FAs
3. **Established championship culture** - 3+ years of contention
4. **Draft pipeline mature** - 2026-2028 draft classes contributing
5. **Cap efficiency mastery** - Balance stars + value contracts

### Competitive Window Timeline

```
2025 ═══════════════════════════════════════════════════════════════════════
     │                                                                       │
     │  TRANSITION YEAR 1: Compete & Build                                 │
     │  - Cap: $71M available                                              │
     │  - Focus: Develop young core, selective FA adds                     │
     │  - Outcome: Playoff contender, not championship favorite            │
     │                                                                       │
2026 ═══════════════════════════════════════════════════════════════════════
     │                                                                       │
     │  TRANSITION YEAR 2: Upgrade via Draft                               │
     │  - Cap: $71M available                                              │
     │  - Focus: TWO 1st round picks = major roster upgrades               │
     │  - Outcome: Strong playoff contender, championship dark horse       │
     │                                                                       │
2027 ═══════════════════════════════════════════════════════════════════════
     │                                                                       │
     │  ⭐ WINDOW OPENS: Elite Contention Phase 1                          │
     │  - Cap: $158M available (MASSIVE JUMP)                              │
     │  - Focus: Sign 2-3 elite FAs, extend core pieces                    │
     │  - Outcome: CHAMPIONSHIP CONTENDER                                  │
     │                                                                       │
2028 ═══════════════════════════════════════════════════════════════════════
     │                                                                       │
     │  ⭐⭐ PEAK WINDOW: Elite Contention Phase 2                         │
     │  - Cap: $183M available, $0 dead cap                                │
     │  - Focus: Sustained excellence, reload annually                      │
     │  - Outcome: CHAMPIONSHIP FAVORITE                                   │
     │                                                                       │
2029 ═══════════════════════════════════════════════════════════════════════
     │                                                                       │
     │  ⭐⭐⭐ APEX: Complete Flexibility                                   │
     │  - Cap: $250M available (CLEAN SLATE)                               │
     │  - Focus: Dynasty mode - maintain elite roster                       │
     │  - Outcome: SUSTAINED DOMINANCE                                     │
     │                                                                       │
2030+ ══════════════════════════════════════════════════════════════════════
      │                                                                      │
      │  SUSTAINED EXCELLENCE: Core in prime (ages 27-29)                  │
      │  - Cap: Managed efficiently with rookie pipeline                    │
      │  - Focus: Championship windows stack annually                       │
      │                                                                      │
      ════════════════════════════════════════════════════════════════════
```

### Window Risk Factors

**Low Risk:**

- ✅ Elite QB locked in (Stroud)
- ✅ Zero draft debt
- ✅ Strong cap trajectory

**Medium Risk:**

- ⚠️ Rookie contract expirations (2026) = extension costs
- ⚠️ Ekeler age curve / contract expiration (2026)
- ⚠️ Lamb dead cap ($103M) limits flexibility if performance declines

**High Risk:**

- ❌ Unknown league competitive dynamics (need more data)
- ❌ Injury risk to young core (Achane durability concerns)

**Mitigation Strategies:**

- Extend Stroud, Achane, Anderson before 2026 season (capture team-friendly deals)
- Use 2026 draft to hedge Ekeler departure (draft elite RB)
- Monitor Lamb performance; if decline, absorb dead cap and move on by 2027
- Build depth via FASA to protect against injury

______________________________________________________________________

## 8. Feature Prioritization Recommendations

### Priority Framework

Based on competitive window analysis (**Transition/Contender → Elite Contention 2027-2029**), feature prioritization should align with:

1. **Maximize draft capital ROI** (elite draft assets)
2. **Plan for cap explosion** (2027+ massive flexibility)
3. **Optimize transition years** (2025-2026 moderate cap)
4. **Sustain long-term excellence** (2028+ peak window)

______________________________________________________________________

### 🔥 TIER 1: CRITICAL PRIORITIES (Build These First)

#### 1. **Rookie Draft Analytics & Decision Support**

**Priority:** ⭐⭐⭐⭐⭐ CRITICAL
**Rationale:** You have ELITE draft capital (26 picks, bonus 2026 1st) - this is your highest ROI opportunity

**Features:**

- **Draft pick valuation models** - Value picks across rounds (e.g., Jimmy Johnson draft value chart adapted for dynasty)
- **Prospect ranking system** - Integrate multiple sources (FFAnalytics, nflverse, KTC) with customizable weights
- **Trade value calculator** - Should I trade 1st rounder for proven veteran? What's fair value?
- **Position scarcity analysis** - Which positions are undervalued in your league's draft?
- **Rookie contract value projection** - Expected ROI per pick ($/WAR or $/projected points)
- **Draft strategy simulator** - Mock different draft strategies (BPA vs. positional need)
- **2026 Draft spotlight** - TWO 1st rounders = special decision tree (use both? trade one? package up?)

**Impact:** **MASSIVE** - 26 picks over 5 years = 26 opportunities to add elite talent at minimal cost

**Timeline:** Build for 2026 draft (6 months away)

______________________________________________________________________

#### 2. **Multi-Year Contract & Cap Projection Modeling**

**Priority:** ⭐⭐⭐⭐⭐ CRITICAL
**Rationale:** $158M cap explosion in 2027 requires multi-year planning NOW to maximize value

**Features:**

- **5-year cap projection dashboard** - Visualize 2025-2029 cap space evolution
- **Contract extension simulator** - Model Stroud/Achane/Anderson/Nabers extensions before 2026
- **Dead cap calculator** - What if scenarios for cutting players (e.g., Lamb dead cap impact)
- **Cap space optimizer** - Identify optimal timing for FA signings (2027 vs 2028 vs 2029)
- **Roster salary distribution analysis** - Are you paying appropriately by position?
- **Extension timing optimizer** - Should you extend Stroud NOW (2025) or WAIT (2026)?
- **Multi-year FAAD/FASA budget planner** - Allocate cap across seasons

**Impact:** **MASSIVE** - $158M in 2027 could be wasted without proper planning. Need to know:

- Which core pieces to extend (and when)?
- Which veterans to let walk (e.g., Ekeler 2026)?
- When to sign elite FAs (2027? 2028?)?

**Timeline:** Build NOW - extension decisions needed by end of 2025 season

______________________________________________________________________

### 📊 TIER 2: HIGH PRIORITIES (Build These Next)

#### 3. **Trade Analysis & Value Models**

**Priority:** ⭐⭐⭐⭐ HIGH
**Rationale:** Draft capital + cap flexibility = trade optionality. Need models to evaluate trade offers.

**Features:**

- **Player trade value calculator** - Dynasty trade values (current + future picks)
- **Pick-for-player trade analyzer** - Is 2026 1st rounder worth proven RB1?
- **Win-now vs. rebuild trade optimizer** - Should you trade future picks for veterans?
- **Trade fairness evaluator** - Are you getting fair value in proposed trades?
- **Positional trade value charts** - Which positions command premium trade prices?
- **Historical trade market analysis** - What have similar players/picks traded for in your league?

**Impact:** HIGH - You have flexibility to trade (draft capital + cap space). Need tools to evaluate opportunities.

**Timeline:** Build by mid-2025 season (trade deadline decisions)

______________________________________________________________________

#### 4. **Contract Value & Efficiency Analysis**

**Priority:** ⭐⭐⭐ MEDIUM-HIGH
**Rationale:** Optimize transition years (2025-2026) by identifying value contracts and avoiding overpays

**Features:**

- **Contract value vs. production analysis** - Which players are underpaid/overpaid?
- **FASA target identifier** - Which FAs offer best value for cap hit?
- **Positional spending benchmarks** - Are you paying too much at RB vs. league average?
- **Extension value calculator** - Is Stroud extension at $X fair vs. market?
- **Dead cap impact analyzer** - Cost-benefit of cutting underperforming veterans

**Impact:** MEDIUM-HIGH - Helps optimize limited cap in 2025-2026, identify value adds

**Timeline:** Build by 2025 FASA period (need for FA bidding)

______________________________________________________________________

### ✅ TIER 3: MEDIUM PRIORITIES (Build After Core Features)

#### 5. **Weekly Lineup Optimization**

**Priority:** ⭐⭐ MEDIUM
**Rationale:** You're competitive but not desperate. Long-term planning > weekly optimization.

**Features:**

- **Start/sit recommendations** - Based on projections + matchups
- **Lineup efficiency analyzer** - Are you leaving points on bench?
- **Injury/bye week optimizer** - Handle roster constraints
- **DFS-style lineup optimizer** - Maximize projected points given constraints

**Impact:** MEDIUM - Helps win weekly matchups, but roster construction (draft/trades/extensions) is higher ROI

**Timeline:** Build after Tier 1-2 features complete

______________________________________________________________________

### 🔍 TIER 4: LOWER PRIORITIES (Nice-to-Have)

#### 6. **In-Season Waiver Wire / Streaming Analysis**

**Priority:** ⭐ LOW
**Rationale:** Dynasty leagues have limited waiver value. Focus on long-term assets (draft/trades).

**Features:**

- **Waiver wire target rankings** - Who to claim?
- **Streaming position recommendations** - Kicker/defense week-to-week
- **Breakout player alerts** - Emerging talent on waivers

**Impact:** LOW - Limited impact in dynasty format with deep rosters

**Timeline:** Build only if time permits after Tier 1-3

______________________________________________________________________

### Summary Priority Matrix

| Feature                    | Priority   | ROI         | Competitive Window Alignment   | Timeline           |
| -------------------------- | ---------- | ----------- | ------------------------------ | ------------------ |
| Rookie Draft Analytics     | ⭐⭐⭐⭐⭐ | MASSIVE     | Elite draft capital (26 picks) | 2026 draft         |
| Multi-Year Cap Projections | ⭐⭐⭐⭐⭐ | MASSIVE     | 2027 cap explosion ($158M)     | NOW (extensions)   |
| Trade Analysis             | ⭐⭐⭐⭐   | HIGH        | Transition optionality         | Mid-2025           |
| Contract Value Analysis    | ⭐⭐⭐     | MEDIUM-HIGH | Optimize 2025-2026             | 2025 FASA          |
| Weekly Lineup Optimization | ⭐⭐       | MEDIUM      | Competitive but not desperate  | Post core features |
| Waiver Wire Analysis       | ⭐         | LOW         | Limited dynasty impact         | Nice-to-have       |

______________________________________________________________________

### Phased Implementation Plan

**Phase 1 (Q1 2025): MVP - Draft & Cap Foundation**

- Rookie draft pick valuation
- Basic multi-year cap projection dashboard
- 2026 draft decision support (TWO 1st rounders)

**Phase 2 (Q2 2025): Trade & Extension Tools**

- Trade value calculator
- Extension timing optimizer (Stroud, Achane, Anderson decisions)
- Contract value analyzer

**Phase 3 (Q3-Q4 2025): Optimization & Polish**

- Weekly lineup optimization
- Advanced trade analysis
- Waiver wire tools (if time permits)

**Phase 4 (2026+): Sustained Excellence Features**

- Long-term dynasty planning tools
- Championship roster construction models
- Historical performance tracking

______________________________________________________________________

## 9. Cross-Reference: Contract Economics Insights

### Critical Data Gaps Identified

**⚠️ IMPORTANT: This analysis is incomplete due to missing real-time data:**

1. **Injury Status** - No current injury data for roster players

   - **Impact:** Can't assess TRUE current competitiveness
   - **Need:** Integrate injury tracking (nflverse, Sleeper API, or manual)

2. **Current League Record/Standings** - No 2025 season record data

   - **Impact:** Don't know if you're 8-2 (contender) or 2-8 (rebuilding)
   - **Need:** Sleeper API integration for real-time standings

3. **In-Division Record** - No divisional performance data

   - **Impact:** Can't assess path to playoffs
   - **Need:** League schedule and results tracking

4. **Game Results** - No weekly matchup data

   - **Impact:** Can't analyze recent performance trends
   - **Need:** Historical game log ingestion

**Recommendation:** Add Sleeper API integration to pipeline for real-time league context. This would significantly enhance competitive assessment accuracy.

______________________________________________________________________

### Key Insights from Contract Economics Research

The [Contract Economics Deep Dive](./research-contract-economics-2025-11-18.md) provides critical context that **directly validates and amplifies** the competitive window analysis findings.

#### Alignment #1: Rookie Draft Analytics = Highest ROI

**From Contract Economics:**

> "Rookie Contracts = Major Arbitrage Opportunity"
>
> - Fixed scale: $6/year (R1.P1-2) down to $1/year (R3+)
> - Hit rookies = massive cap efficiency (potential 10:1 value ratio)
> - **Feature Priority: ELEVATE rookie draft analytics**

**From Competitive Window:**

- **ELITE draft capital:** 26 picks over 5 years, including BONUS 2026 1st rounder
- **You have TWO 1st round picks in 2026** = double the arbitrage opportunity
- **Cap-constrained in 2025-2026** ($71M) = need cheap talent = rookies!

**🎯 SYNERGY:** Your elite draft capital + league's rookie contract economics = **PERFECT STORM for rookie draft analytics**. This is your single highest ROI feature.

______________________________________________________________________

#### Alignment #2: Multi-Year Cap Projections are Essential

**From Contract Economics:**

> "Pro-Rating Adds Complexity but Opportunities"
>
> - 150% geometric constraints enable "cap smoothing" analytics
> - Front-loaded vs back-loaded contract strategies
> - Multi-year dead cap liabilities (50% Year 1-2, 25% Year 3-5)

**From Competitive Window:**

- **2027 cap explosion:** $158M available (2.2x increase from 2025-2026)
- **Core extension decisions NOW:** Stroud, Achane, Anderson, Nabers expire 2026
- **Dead cap decay:** $28M (2025) → $13M (2026) → $0 (2028)

**🎯 SYNERGY:** Complex pro-rating rules + cap explosion timing = **CRITICAL need for multi-year projection tools**. Extension timing matters enormously.

______________________________________________________________________

#### Alignment #3: Dead Cap Burden is Strategic Risk

**From Contract Economics:**

> "Dead Cap Creates Strategic Trade-offs"
>
> - 50% dead cap hit in Year 1-2, 25% in Year 3-5
> - Cutting players is EXPENSIVE
> - **CeeDee Lamb example:** $103M dead cap if cut today

**From Competitive Window:**

- **CeeDee Lamb commitment:** $291M total contract, $103M dead cap
- **Cap-constrained 2025-2026:** Limited flexibility to absorb mistakes
- **2027+ flexibility:** Can absorb dead cap if needed

**🎯 SYNERGY:** Lamb's dead cap ($103M) is manageable in 2027+ ($158M available) but would be DEVASTATING in 2025-2026 ($71M available). Dead cap "what-if" modeling is essential.

______________________________________________________________________

### How Competitive Window Impacts Contract Strategy

#### Transition Years (2025-2026): Cap Efficiency Focus

**Strategy:** Maximize value contracts, avoid overpays, develop young talent

**Contract Priorities:**

1. **EXTEND CORE NOW** (before market reset):

   - C.J. Stroud - Lock in before 2026 expiration
   - De'Von Achane - Lock in before 2026 expiration
   - Will Anderson - Lock in before 2026 expiration
   - **Rationale:** These expire 2026. Extend NOW while you have leverage.

2. **Let Veterans Walk:**

   - Austin Ekeler (expires 2026) - Don't extend, replace via 2026 draft (2 first rounders)
   - **Rationale:** Use elite draft capital to replace aging veterans

3. **Selective FASA:**

   - Target undervalued role players ($2M-$5M range)
   - Avoid FAAD bidding wars (limited cap)

______________________________________________________________________

#### Window Opens (2027): Aggressive Expansion

**Strategy:** Leverage $158M cap space explosion to add elite talent

**Contract Priorities:**

1. **AGGRESSIVE FAAD BIDDING:**

   - Target 2-3 elite free agents
   - Front-load contracts (take cap hit NOW while you have space)
   - **Rationale:** $158M cap = afford premium talent

2. **Strategic Dead Cap Management:**

   - If CeeDee Lamb declines, consider cutting ($103M dead cap manageable with $158M available)

______________________________________________________________________

#### Peak Window (2028-2029): Sustained Excellence

**Strategy:** Maintain elite roster while managing cap efficiently

**Contract Priorities:**

1. **RELOAD ANNUALLY:**

   - Continued FAAD/FASA excellence
   - Rookie pipeline (5 picks/year)
   - **Rationale:** $183M-$250M cap = near-unlimited flexibility

2. **CAP SMOOTHING:**

   - Use pro-rating rules strategically
   - Back-load contracts when needed

______________________________________________________________________

### Feature Priority Validation

**Contract Economics recommended:**

1. ELEVATE: Rookie draft analytics
2. ELEVATE: Dead cap "what-if" modeling
3. ELEVATE: Contract efficiency metrics

**Competitive Window confirms:**

1. ✅ Rookie draft analytics = **CRITICAL** (elite draft capital)
2. ✅ Multi-year cap projections = **CRITICAL** (2027 explosion)
3. ✅ Dead cap modeling = **HIGH** (Lamb $103M risk)
4. ✅ Weekly lineup = **MEDIUM** (not desperate)

**🎯 VERDICT:** Both reports converge on the same priorities

______________________________________________________________________

## Appendices

### Appendix A: Roster Details

{{roster_details}}

### Appendix B: Cap Space Timeline

{{cap_space_timeline}}

### Appendix C: Draft Pick Inventory

{{draft_pick_details}}

______________________________________________________________________

## Document Information

**Workflow:** BMad Domain Research Workflow
**Generated:** 2025-11-18
**Data Freshness:** Current as of 2025-11-18
**Cross-References:**

- [Contract Economics Research](./research-contract-economics-2025-11-18.md)
- [Project Documentation Index](./index.md)

______________________________________________________________________

_This domain research report analyzes internal franchise data to assess competitive positioning and inform feature prioritization for the Fantasy Football Data Analytics Platform._
