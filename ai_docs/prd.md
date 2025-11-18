# Product Requirements Document: Analytics Infrastructure Platform

**Project:** Fantasy Football Analytics Platform - Analytical Infrastructure MVP
**Date:** 2025-11-18
**Author:** Jason (Product Manager)
**Status:** Draft
**Timeline:** Aggressive (1-2 months)

______________________________________________________________________

## Executive Summary

This PRD defines the analytical infrastructure layer that will power sophisticated dynasty fantasy football decision-making. Rather than building tactical tools first, we're taking a disciplined infrastructure-first approach: building the core analytical engines (VoR/WAR, multi-year projections, cap modeling) that will enable systematic competitive advantage through superior data infrastructure.

**The Vision:** A unified analytics platform that systematically exploits league complexity through:

- Multi-dimensional player valuation (6-factor dynasty value score)
- Position-specific ML projections with uncertainty quantification
- Multi-year portfolio optimization under salary cap constraints
- Market inefficiency identification via data-driven arbitrage

**MVP Scope:** Core analytical engines that consume existing dbt models and produce analytics marts - NOT user-facing decision support tools (those come in Phase 2).

**Success Metrics:**

- **Technical:** Backtested projection accuracy \<20% MAE, 10+ identified market inefficiencies vs KTC consensus
- **Product:** "Top 5 Roster Optimization Moves" dashboard showing highest-impact decisions ranked by championship probability delta (2026-2028 window)

______________________________________________________________________

## 1. Product Vision & Strategic Context

### Vision Statement

Build the **analytical infrastructure** that enables systematic competitive advantage in dynasty fantasy football through superior data-driven decision-making. The platform will integrate multi-dimensional player valuation, machine learning projections, and portfolio optimization to identify market inefficiencies that generic fantasy tools cannot see.

### Strategic Goals

1. **Establish Analytical Moat:** Proprietary 13+ year transaction history + league-specific contract economics = sustainable competitive advantage no competitor can replicate

2. **Systematic Market Arbitrage:** Identify 10+ mispricings per season between internal valuations and market consensus (KTC/DynastyProcess)

3. **Infrastructure-First:** Build robust analytical engines that enable ALL future decision support (FASA optimization, trade analysis, roster construction) rather than point solutions

4. **Long-Term Optimization:** Multi-year competitive window planning (2025-2029) balancing immediate competitiveness with future flexibility

### Success Metrics

**Technical Quality:**

- Projection accuracy: \<20% Mean Absolute Error on 1-year ahead backtests (2020→2021, 2021→2022, 2022→2023)
- Model validation: Time-series CV with zero data leakage (TimeSeriesSplit compliance)
- Internal consistency: VoR baselines sum to expected totals, aging curves respect position-specific patterns

**Business Value:**

- Market inefficiency identification: ≥10 divergences (>15% delta) between internal dynasty value scores and KTC consensus
- Cap efficiency opportunities: Identify ≥5 undervalued contracts ($/WAR < league median)
- Portfolio optimization: Multi-year cap scenarios (2025-2029) with \<5% calculation error vs manual verification

**Operational:**

- Analytical pipeline runtime: \<30 minutes end-to-end (ingest → analytics → marts)
- Model retraining: Annual cadence (pre-season) + in-season updates (Week 4, Week 10)
- Code quality: 80%+ test coverage for valuation engines, 100% coverage for cap modeling rules

### User Impact

**Immediate (MVP):**

- Unified player valuation metric (Dynasty Value Score) integrating 6 dimensions
- Multi-year projections (2025-2029) enabling long-term roster planning
- Cap space scenario modeling with contract structure optimization

**Phase 2 (Post-Infrastructure):**

- FASA bid optimization: Optimal contract structures + drop scenarios
- Trade analysis: Multi-objective evaluation with win probability impacts
- Draft strategy: ROI-maximizing prospect targeting using contract arbitrage

### Strategic Alignment

**Current Competitive Position:** 7th of 12 teams (5-6 record), injuries to key players, unlikely to make deep playoff run in 2025

**Competitive Window:** Transition/Contender (2025-2026) → Elite Contention (2027-2029) as $71M cap grows to $158M+ with young core hitting prime years

**Product Strategy:** Build analytical infrastructure NOW (not competing hard this year) → Deploy decision support tools when infrastructure is validated → Systematic advantage compounds over multiple seasons

______________________________________________________________________

## 2. Problem Statement & Opportunity

### 2.1 Root Problem: Lack of Systematic Decision Framework

**Current State:** Dynasty franchise decisions are made inconsistently under time pressure because there is no systematic decision framework. This manifests across three critical decision types that determine championship competitiveness.

### 2.2 Critical Decision Moments (Prioritized by Impact)

**DECISION TYPE 1: Contract Extensions (2026 Decision Crunch) - HIGH IMPACT**

**Decision Context:**

- **Players Expiring:** Stroud, Achane, Anderson, Nabers
- **Decision Window:** Next 6-12 months (before RFA/FAAD market reset)
- **Frequency:** 4-6 extension decisions per season
- **Decision Stakes:** $15-25M cap savings vs market-rate extensions OR costly mistakes locking in declining players

**Current Approach:**

- Manual cap scenarios in spreadsheet
- Point-in-time KTC comparison (no multi-year value projection)
- Gut-feel on extension timing (extend now vs wait for RFA)

**Gap - Missing Analytics:**

- No multi-year value projection with age-adjusted uncertainty
- No extension vs RFA cost modeling (when to lock in value before market reset)
- No optimal contract structure calculator (front-load vs back-load given 2027 cap explosion)

**Infrastructure Requirements:**

- Multi-year projections (Epic 2) - project player value 2026-2029
- Cap modeling (Epic 3) - scenario analysis for extension structures
- Dynasty value composite (Epic 4) - internal valuation vs projected market value

**Expected Value if Solved:**

- **Quantified Impact:** Lock in 3 core players at 20% below predicted RFA cost = $15-25M total cap savings
- **Risk Mitigation:** Avoid overpaying for aging players entering decline phase
- **Example:** Extend Stroud now at $18M/year vs waiting for RFA market reset at $25M/year

______________________________________________________________________

**DECISION TYPE 2: FASA Weekly Bidding - HIGH FREQUENCY**

**Decision Context:**

- **Frequency:** 26 weeks × 3-5 serious targets = 78-130 bidding decisions per season
- **Decision Stakes:** Avoid overpays (save $8-12M cap waste/season) while acquiring undervalued talent

**Current Approach:**

- Rest-of-season projections (FFAnalytics)
- Manual contract efficiency comparison ($/projected points)
- Instinct on contract structure (1-year vs 3-year, front-loaded vs back-loaded)
- Time-constrained analysis (3-4 hours/week during season)

**Gap - Missing Analytics:**

- No contract efficiency benchmarking ($/WAR vs league median)
- No optimal contract structure calculator (balance 2025-2026 cap constraints with 2027 flexibility)
- No drop candidate ranking (who to cut if I win bid)
- No multi-year value assessment (Year 1 production vs Year 2-3 decline)

**Infrastructure Requirements:**

- VoR/WAR engine (Epic 1) - contract efficiency ($/WAR)
- Multi-year projections (Epic 2) - avoid overpaying for aging veterans
- Cap modeling (Epic 3) - optimal contract structures
- Dynasty value composite (Epic 4) - internal valuation vs market

**Expected Value if Solved:**

- **Quantified Impact:** Reduce overpays from 30% of bids to 10% = save $8-12M cap space per season
- **Time Savings:** FASA analysis 3-4 hours/week → 1 hour/week (automated filtering + recommendations)
- **Example:** Bid $10/year for RB based on contract efficiency vs gut-feel $13/year (save $3M/year × 3 years = $9M)

______________________________________________________________________

**DECISION TYPE 3: Trade Evaluation - MEDIUM IMPACT, OPPORTUNISTIC**

**Decision Context:**

- **Frequency:** 8-12 serious trade opportunities per season
- **Decision Stakes:** 2-3 better trades = $12-18K roster value improvement

**Current Approach:**

- Point-in-time KTC values (no multi-year trajectory)
- Gut feel on competitive window alignment
- Manual assessment of position needs (no portfolio optimization framework)

**Gap - Missing Analytics:**

- No portfolio rebalancing logic (position allocation, age distribution)
- No competitive window alignment (acquire youth when rebuilding, veterans when contending)
- No multi-objective evaluation (value, positional fit, cap impact, championship probability)

**Infrastructure Requirements:**

- Dynasty value composite (Epic 4) - unified valuation metric
- Multi-year projections (Epic 2) - trajectory alignment with competitive window
- Cap modeling (Epic 3) - cap impact of incoming/outgoing contracts

**Expected Value if Solved:**

- **Quantified Impact:** 2-3 better trade decisions/season = $12-18K roster value improvement
- **Strategic Alignment:** Portfolio rebalancing toward 2027-2028 championship window
- **Example:** Trade aging veteran for youth + pick because multi-year projections show veteran cliff in Year 2

### 2.3 Quantified Current-State Costs

**Time Waste (Manual Analysis Burden):**

- **FASA bidding analysis:** 3-4 hours/week × 26 weeks = 78-104 hours/season
- **Cap scenario modeling:** 30-45 min/scenario × 20 scenarios/season = 10-15 hours/season
- **Trade evaluation:** 1-2 hours/trade × 12 trades = 12-24 hours/season
- **Multi-year roster planning:** 20-30 hours/off-season (spreadsheet scenarios, aging curve guesswork)
- **TOTAL:** ~100-140 hours/season of manual analysis that could be automated

**Decision Quality Variance:**

- **High-quality decisions** (adequate time, rigorous analysis): 60% of opportunities
- **Rushed decisions** (time-constrained, gut feel): 40% of opportunities
- **Estimated cost of variance:** 2-3 bad FASA overpays/season = $8-12M wasted cap space

**Missed Opportunities (Invisible Without Systematic Comparison):**

- **Market inefficiencies undetected:** ~15-20 arbitrage opportunities/season (no systematic internal vs KTC comparison)
- **Extension timing suboptimal:** ~2 players/year extended reactively (at market reset) vs proactively (before market reset) = $5-8M overpaid
- **Portfolio imbalance:** Unknown (no quantified position/age allocation targets vs current state)

**Strategic Risks:**

- **2026 Extension Crunch:** 4 core players expiring without multi-year value framework = risk of overpaying OR losing talent
- **2027 Cap Explosion Waste:** $158M cap space without strategic acquisition plan = suboptimal deployment
- **Competitive Window Mistiming:** Pivot to compete too early (waste picks) or too late (aging roster) without probabilistic modeling

### Why Now?

**Timing Factors:**

1. **Competitive Window Alignment:** Not making deep playoff run in 2025 (7th place, injuries) = time to build infrastructure without urgent decision pressure

2. **Orchestration Work Parallel Track:** `multi_source_snapshot_governance` Prefect implementation is separate team/effort = analytical infrastructure can be built in parallel without conflicts

3. **2026 Decision Crunch Coming:** Multiple core players expire (Stroud, Achane, Anderson, Nabers) = extension decisions in 6-12 months require multi-year projection capability

4. **Cap Explosion Window:** 2027 cap jumps from $71M to $158M = strategic timing of acquisitions requires planning NOW to maximize 2027 opportunity

5. **Draft Capital Deployment:** 2026 draft (bonus 1st rounder) = 6-8 months to build prospect evaluation framework

**Market Context:**

- Dynasty analytics landscape is maturing (Draft Sharks ML, Fantasy Points WAR, PlayerProfiler metrics)
- BUT: Salary cap dynasty leagues remain niche = limited commercial tools = competitive advantage available through custom infrastructure
- Your 13+ years proprietary transaction history + unique contract economics = differentiation that scales over time

### Impact if Not Solved

**Short-Term (6-12 months):**

- Miss 2026 extension window optimization (Stroud, Achane, Anderson contracts expire)
- Suboptimal FASA bidding continues (manual analysis = time-constrained = lower quality decisions)
- 2026 draft capital underutilized (bonus 1st rounder without systematic prospect evaluation)

**Medium-Term (1-2 years):**

- 2027 cap explosion ($158M) wasted without strategic planning (sign wrong players, poor contract structures, miss arbitrage)
- Competitive window timing errors (pivot to compete too early/late, wasting draft picks or aging roster)
- Market inefficiency opportunities erode as league sophistication increases

**Long-Term (3+ years):**

- Systematic competitive disadvantage vs data-driven managers
- Manual analytical processes don't scale (time = limiting factor on decision quality)
- Infrastructure debt compounds (tactical tools built on weak analytical foundation require rebuilds)

______________________________________________________________________

## 3. Target Users & Use Cases

### Primary User

**Profile:**

- **Name:** Jason
- **Role:** Dynasty franchise manager (F001 - franchise 001, Lauren Noble Division)
- **Technical Sophistication:** Intermediate-advanced (Python, SQL, dbt, data modeling)
- **Domain Expertise:** Deep dynasty strategy knowledge, 13+ years league history
- **Current Workflow:** Jupyter notebooks consuming dbt marts, manual analysis, weekly FASA decisions

**Usage Pattern:**

- **High-Touch Periods:** FASA weeks (weekly during season), trade deadline (annual), draft (annual), extension decisions (ad-hoc)
- **Strategic Planning:** Off-season competitive window assessment, multi-year roster planning
- **Analytical Exploration:** Research-driven investigation of market inefficiencies, valuation framework refinement

**Pain Points:**

- Time-constrained during FASA weeks = rushed decisions
- Manual cap scenario modeling = slow, error-prone
- Inconsistent valuation approaches = decision quality varies
- Market inefficiencies invisible without systematic comparison

### Core User Journeys

**Journey 1: Multi-Year Roster Planning (Strategic)**

**Trigger:** Off-season competitive window assessment

**User Story:** "As a dynasty manager, I need to understand how my roster value evolves from 2025-2029 so I can time acquisitions to my competitive window."

**Workflow:**

1. Load current roster with contract details
2. Generate multi-year projections for all players (age-adjusted, opportunity-adjusted)
3. Calculate dynasty value scores (6-factor composite)
4. Identify peak value years by player
5. Model cap space scenarios (2025-2029) under different contract decisions
6. Determine optimal championship window (when roster + cap align)

**Success Criteria:** Can answer "When is my championship window?" with probabilistic confidence intervals and identify which players to extend/trade/cut to maximize window.

______________________________________________________________________

**Journey 2: FASA Bidding Decision Support (High-Frequency Tactical)**

**Trigger:** FASA week opens (weekly during season), 8 free agent targets available

**User Story:** "As a dynasty manager, I need to evaluate FASA targets efficiently and determine optimal bids/contracts so I acquire undervalued talent without overpaying."

**Detailed Decision Tree:**

**DECISION NODE 1: Which players to analyze in depth?**

- **Current State:** Review all 8 targets manually (3-4 hours total)
- **With Infrastructure:** Auto-filter by dynasty value threshold (15 minutes)
  - Dynasty value composite pre-calculated (Epic 4 output)
  - Filter: `dynasty_value > $3,000 AND contract_efficiency_potential > league_median`
  - **Output:** Focus analysis on top 3-4 targets only (save 2-3 hours)

**DECISION NODE 2: What's the maximum bid I should make?**

- **Current State:** Gut-feel based on KTC value + rest-of-season projection
- **With Infrastructure:** Contract efficiency ceiling calculation
  - Calculate maximum acceptable $/WAR (e.g., $8/WAR = league median efficiency)
  - Multi-year projection shows Year 2-3 value (avoid overpaying for aging players)
  - **Example Output:** "Player X: Max bid $12/year or walk away" (based on $8/WAR threshold × 1.5 projected WAR)
  - **Rationale:** Bidding $15/year would put contract at $10/WAR (below-median efficiency = overpay)

**DECISION NODE 3: What contract structure should I offer?**

- **Current State:** Copy last year's structure (1-year vs 3-year heuristic, no optimization)
- **With Infrastructure:** Optimal contract structure calculator
  - Cap space scenario analysis shows 2025-2026 tight ($71M), 2027+ open ($158M+)
  - **Recommendation:** 3-year back-loaded contract
    - Year 1: $8M (conserve tight 2025 cap)
    - Year 2: $12M (bridge year)
    - Year 3: $18M (utilize 2027 cap explosion)
  - Validate 150% pro-rating constraints automatically (Year 3 = 225% of Year 1, ILLEGAL) → adjust to legal structure
  - **Corrected Legal Structure:** Year 1: $10M, Year 2: $12M, Year 3: $15M (Year 3 = 150% of Year 1, LEGAL)

**DECISION NODE 4: Who do I drop if I win the bid?**

- **Current State:** Eyeball lowest-value rostered player (5-10 minutes gut feel)
- **With Infrastructure:** Drop candidate ranking (pre-calculated)
  - Contract efficiency analysis identifies negative-value players ($/WAR > 2x league median)
  - Dead cap calculator shows manageable vs prohibitive dead cap obligations
  - **Example Output:** "Drop Player Z ($2M dead cap, frees $6M cap space, -0.3 WAR) vs Player Y ($5M dead cap, frees $8M, -0.1 WAR)"
  - **Recommendation:** Drop Player Z (better cap efficiency, minimal production loss)

**DECISION NODE 5: Should I make a contingent bid? (Backup plan if I lose primary target)**

- **Current State:** No systematic contingency planning
- **With Infrastructure:** Contingent bid optimizer
  - If primary target (RB1) loses, auto-evaluate secondary targets (RB2, RB3)
  - Dynasty value comparison: RB2 at $8/year (better value) vs RB1 at $12/year (lost bid)
  - **Output:** "Contingent bid: $9/year for RB2 if RB1 bid fails"

**Outcome Measurement (Post-FASA):**

- **Time Savings:** Decision made in 30 minutes vs 2 hours (75% reduction)
- **Cap Efficiency:** Bid $10/year vs gut-feel $13/year (save $3M/year × 3 years = $9M total cap space)
- **Contract Optimization:** Back-loaded structure aligned with 2027 cap explosion (maximized flexibility)
- **Backtesting Loop:** Track actual performance vs projection (did Player X outperform? Update model if systematic bias detected)

**Success Criteria:**

- Reduce FASA analysis time from 3-4 hours/week to \<1 hour/week
- Achieve 80% of winning bids within ±15% of optimal contract efficiency threshold
- Avoid "buyer's remorse" overpays (players acquired perform within 80% of projected value in Year 1)

______________________________________________________________________

**Journey 2B: Market Inefficiency Detection (Analytical)**

**Trigger:** Weekly/bi-weekly market monitoring

**User Story:** "As a dynasty manager, I need to identify players whose internal value differs significantly from market consensus so I can exploit buy-low/sell-high opportunities."

**Workflow:**

1. Calculate dynasty value scores for all players in league
2. Fetch latest KTC consensus values
3. Compute delta (internal value - market value)
4. Filter to meaningful divergences (>15% delta, >$2,000 absolute)
5. Investigate causes (projections? age curves? contract economics? market sentiment?)
6. Generate trade target list (buy-low) and sell candidate list (sell-high)

**Success Criteria:** Weekly report identifying 3-5 arbitrage opportunities with rationale for divergence.

______________________________________________________________________

**Journey 3: Extension Decision Analysis (Tactical)**

**Trigger:** Player contract approaching expiration (6-12 months out)

**User Story:** "As a dynasty manager, I need to determine optimal extension timing and structure for core players so I lock in value before market reset."

**Workflow:**

1. Load player profile (current contract, multi-year projections, age curve)
2. Calculate current dynasty value vs expected market value at expiration
3. Model extension scenarios (1yr, 3yr, 5yr with different pro-rating structures)
4. Compute multi-year cap impact of each scenario
5. Identify optimal extension structure (maximize value lock-in, minimize cap burden)
6. Compare "extend now" vs "wait for RFA/FAAD" vs "let walk" strategies

**Success Criteria:** Data-backed extension decision with quantified trade-offs (value locked, cap impact, flexibility cost).

______________________________________________________________________

**Journey 4: Portfolio Rebalancing (Strategic + Tactical)**

**Trigger:** Trade deadline, FAAD prep, roster assessment

**User Story:** "As a dynasty manager, I need to understand my portfolio composition (proven veterans vs youth, position allocation, cap efficiency) so I can rebalance toward optimal structure."

**Workflow:**

1. Calculate dynasty value distribution by position (QB/RB/WR/TE)
2. Analyze age profile (proven veterans >27, prime 24-27, youth \<24)
3. Compute contract efficiency metrics ($/WAR, $/VoR by player)
4. Assess variance profile (high-floor foundation vs high-ceiling upside)
5. Compare to optimal portfolio allocation (evidence-based benchmarks)
6. Generate rebalancing recommendations (which positions to add/shed, age targets, contract efficiency thresholds)

**Success Criteria:** Portfolio dashboard showing current vs optimal allocation with actionable rebalancing trades.

______________________________________________________________________

## 4. Core Product Requirements

### 4.1 Multi-Dimensional Player Valuation Engine

**Functional Requirements:**

**FR-VAL-001: VoR/WAR Calculation**

- Calculate Value over Replacement (VoR) for all players using position-specific replacement levels
- Compute Wins Above Replacement (WAR) converting fantasy points to expected wins added
- Support multiple baseline methodologies (VORP, VOLS, BEER+) with configurable thresholds
- **Acceptance Criteria:** VoR calculations match hand-calculated examples within 2%, WAR aligns with Fantasy Points methodology conceptually (exact match not required - different scale)

**FR-VAL-002: Contract Economics Integration**

- Calculate $/WAR and $/VoR efficiency metrics for all rostered players
- Model dead cap impact if player cut today (50%/50%/25%/25%/25% schedule per league rules)
- Support multi-year contract structure analysis (pro-rating, front/back-loading, 150% geometric constraints)
- **Acceptance Criteria:** Contract efficiency metrics identify top 10 best/worst value contracts, dead cap calculations match league constitution rules

**FR-VAL-003: Positional Scarcity Adjustment**

- Implement cross-positional value algorithm accounting for roster constraints (starting slots, bench depth)
- Adjust valuations for positional supply/demand imbalances (RB scarcity premium vs WR depth)
- Support league-specific roster rules (25 active, 5 taxi, 3 IR)
- **Acceptance Criteria:** Scarcity adjustments reflect league roster depth analysis, QB/RB command higher valuations than WR/TE given scoring/roster settings

**FR-VAL-004: Variance/Uncertainty Quantification**

- Calculate consistency ratings (weekly_std_dev / mean PPG) for all players
- Generate projection ranges (floor/ceiling/median) using distributional modeling
- Classify players as high-floor (roster foundation) vs high-ceiling (upside speculation)
- **Acceptance Criteria:** Consistency ratings correlate with ESPN's published metrics, projection ranges capture 80% of actual outcomes in backtest

**FR-VAL-005: Market Signal Integration**

- Fetch latest KTC dynasty values via API
- Calculate divergence (internal dynasty value - KTC consensus)
- Identify arbitrage opportunities (>15% delta, minimum $2K absolute value)
- **Acceptance Criteria:** KTC integration refreshes weekly, divergence analysis produces 10+ opportunities per refresh

**FR-VAL-006: Dynasty Value Composite Score**

- Combine 6 dimensions (VoR, economics, age, scarcity, variance, market) into unified score
- Support configurable weighting (default: VoR 30%, economics 20%, age 20%, scarcity 15%, variance 10%, market 5%)
- Output dynasty value scores for all players (rostered + free agents + future draft picks)
- **Acceptance Criteria:** Dynasty value scores rank top 100 players in reasonable order (no major outliers), correlate 0.6-0.8 with KTC (not perfect match - we're trying to beat market)

**Non-Functional Requirements:**

**NFR-VAL-001: Performance**

- Full valuation refresh (all players) completes in \<10 minutes
- Incremental updates (weekly stats refresh) complete in \<2 minutes

**NFR-VAL-002: Extensibility**

- Modular design allows swapping VoR methodologies (VORP → VOLS → BEER+) without rewriting downstream logic
- New dimensions easily added to dynasty value composite (e.g., injury risk, manager preference adjustments)

______________________________________________________________________

### 4.2 Multi-Year Projection System

**Functional Requirements:**

**FR-PROJ-001: Age Curve Modeling**

- Derive position-specific aging curves from nflverse historical data (3+ years)
- Model career trajectories: RB cliff at Year 7, WR longevity to Year 10+, QB stability to Year 12+
- Apply age adjustments to base projections (FFAnalytics rest-of-season extended forward)
- **Acceptance Criteria:** Aging curves match PFF/Fantasy Points published research directionally (RB decline steeper than WR), backtesting shows age-adjusted projections outperform naive extrapolation by >10% MAE

**FR-PROJ-002: Opportunity Trend Adjustment**

- Integrate opportunity metrics (target share, snap %, carry share) from nflverse
- Model opportunity trends (rising/declining usage) using rolling averages (3-game, 5-game windows)
- Adjust future projections based on opportunity trajectory (opportunity increases → projections increase)
- **Acceptance Criteria:** Opportunity-adjusted projections correlate with actual outcomes better than volume-naive projections (A/B backtest shows >5% MAE improvement)

**FR-PROJ-003: Multi-Year Projection Generation**

- Generate 2025-2029 projections for all players (5-year forward horizon)
- Output yearly projections (PPG, total points, opportunity metrics) with confidence intervals
- Apply retirement probabilities (position-specific, age-based) to adjust longer-term projections
- **Acceptance Criteria:** 2020→2021-2023 backtest shows \<20% MAE on 1-year ahead, \<30% MAE on 2-year ahead, \<40% MAE on 3-year ahead (degradation expected with horizon)

**FR-PROJ-004: Variance Modeling**

- Generate projection distributions (not point estimates) using bootstrap/simulation
- Calculate floor (10th percentile), median (50th), ceiling (90th percentile) for each player-year
- Quantify uncertainty increasing with projection horizon (Year 1 narrow, Year 5 wide)
- **Acceptance Criteria:** Distributional projections capture 80% of actual outcomes within floor-ceiling range (backtested), uncertainty quantification enables risk-adjusted decision making

**FR-PROJ-005: Position-Specific Models**

- Separate projection models for QB/RB/WR/TE (different feature sets, aging curves)
- QB model emphasizes passing volume, efficiency, durability
- RB model emphasizes opportunity share, team run rate, age cliff risk
- WR model emphasizes target share, QB quality, route running efficiency
- TE model emphasizes breakout age (Year 2), role clarity, target competition
- **Acceptance Criteria:** Position-specific models outperform generic model by >15% MAE (backtested cross-validation)

**Non-Functional Requirements:**

**NFR-PROJ-001: Retraining Cadence**

- Annual retraining before each season (July/August)
- In-season updates after Week 4 and Week 10 (sufficient sample accumulation)
- Sliding window validation (5-year max history to avoid stale data)

**NFR-PROJ-002: Feature Engineering**

- Well-engineered features (weighted historical data, rolling averages, interaction terms) over complex models
- Document feature importance (SHAP values) to interpret model behavior

______________________________________________________________________

### 4.3 Cap Space Projection & Modeling

**Functional Requirements:**

**FR-CAP-001: Multi-Year Cap Space Projection**

- Project cap space 2025-2029 based on current contracts + known expirations
- Account for traded cap (in/out by season)
- Include dead cap obligations from prior cuts (decaying over time per league rules)
- **Acceptance Criteria:** Cap projections match manual spreadsheet calculations within $2M, correctly model cap "explosion" from $71M (2025-2026) to $158M (2027) to $250M (2029)

**FR-CAP-002: Contract Structure Optimization**

- Evaluate pro-rating options for multi-year contracts (3/4/5 years)
- Validate 150% geometric constraints per league rules (Year 3 within 150% of Year 1 and Year 5)
- Model front-loading vs back-loading cap impact
- **Acceptance Criteria:** Pro-rating validation catches illegal structures (>150% spread), optimization suggests contract structures minimizing cap burden in constrained years (2025-2026) while utilizing flexibility in explosion years (2027+)

**FR-CAP-003: Dead Cap Scenario Modeling**

- Calculate dead cap impact of cutting any rostered player (50%/50%/25%/25%/25% schedule)
- Model multi-year dead cap burden (player cut in Year 1 has Year 2-5 obligations)
- Support "what-if" scenarios (if I cut Player X + Player Y, what's total dead cap by year?)
- **Acceptance Criteria:** Dead cap calculations match league constitution rules exactly (verified against commissioner's manual calculations), scenario modeling enables portfolio-level cut analysis

**FR-CAP-004: Extension Scenario Analysis**

- Model cap impact of extending players before contract expiration
- Compare "extend now" vs "wait for RFA/FAAD" strategies
- Calculate NPV of extension options (discount future cap space)
- **Acceptance Criteria:** Extension scenarios quantify trade-offs (cap savings from early extension vs flexibility loss), NPV calculations use reasonable discount rate (5-10% reflecting competitive window timing urgency)

**FR-CAP-005: Contract Efficiency Benchmarking**

- Calculate $/WAR for all rostered players
- Identify best/worst value contracts (league median comparison)
- Flag "cut candidates" (negative value players with manageable dead cap)
- **Acceptance Criteria:** Efficiency benchmarking ranks contracts intuitively (rookie stars on cheap deals = top, expensive busts = bottom), cut candidate analysis balances dead cap cost vs roster value freed

**Non-Functional Requirements:**

**NFR-CAP-001: Rule Compliance**

- 100% adherence to league constitution contract rules (pro-rating constraints, dead cap schedule, cap trading limits)
- Automated validation prevents illegal contract structures from being modeled

**NFR-CAP-002: Scenario Performance**

- Single contract scenario (1 player extension) computes in \<1 second
- Portfolio scenario (5 player cuts + 3 extensions) computes in \<10 seconds

______________________________________________________________________

### 4.4 Integration & Data Pipeline

**Functional Requirements:**

**FR-INT-001: dbt Staging Model Consumption**

- Python analytics libraries consume existing dbt staging/mart models (no raw Parquet access)
- Read data from DuckDB database (dbt target location)
- Support incremental updates (delta processing when available)
- **Acceptance Criteria:** Analytics code uses `duckdb.connect()` to read from dbt database, no direct Parquet file reads, incremental mode reduces processing time by >50% vs full refresh

**FR-INT-002: Analytics Output as dbt Marts**

- Python analytics write results to database tables
- dbt materializes analytics results as mart models (SQL layer for documentation/testing)
- Naming convention: `mrt_player_valuation`, `mrt_multi_year_projections`, `mrt_cap_scenarios`, `mrt_dynasty_value_composite`
- **Acceptance Criteria:** Analytics output tables appear in dbt documentation, downstream notebooks consume marts (not Python objects), dbt tests validate mart grain/uniqueness

**FR-INT-003: Prefect Orchestration (Day 1)**

- All analytics tasks decorated as `@task` (Prefect-native from start)
- Flows orchestrate VoR → Projections → Cap → Composite pipeline with dependencies
- Backtesting runs as separate scheduled flow (weekly validation, cron-triggered)
- Discord notifications on model regression or pipeline failures
- Idempotent execution (re-running produces same results)
- Logging/monitoring via Prefect UI and structured logs
- **Acceptance Criteria:** Analytics run as Prefect flows (not standalone scripts), backtesting flow triggers weekly and sends Discord alerts on regression, Prefect UI shows task dependencies and runtime metrics

**FR-INT-004: Historical Data Access**

- Access 3+ years nflverse data for aging curves
- Access 13+ years commissioner transaction history for market calibration
- Support point-in-time queries (as-of date snapshots)
- **Acceptance Criteria:** Aging curve derivation uses 2019-2024 data minimum, transaction history analysis spans full 2012-2025 period, point-in-time snapshots enable backtesting

**Non-Functional Requirements:**

**NFR-INT-001: Pipeline Runtime**

- End-to-end analytics refresh (ingest → analytics → marts) \<30 minutes
- Parallelizable components (VoR calculation, projections, cap modeling) run concurrently

**NFR-INT-002: Data Freshness**

- Weekly data refresh during season (nflverse stats, FFAnalytics projections, KTC values)
- Daily refresh during high-activity periods (trade deadline, FAAD week, draft week)

______________________________________________________________________

## 5. Success Criteria & Metrics

### 5.1 Acceptance Criteria (MVP Complete)

**Analytical Quality:**

1. ✅ VoR/WAR engine produces valuations for all players (500+ NFL players)
2. ✅ Multi-year projections (2025-2029) generated for all rostered players + top 200 free agents
3. ✅ Cap space scenarios (2025-2029) computed with league rule compliance
4. ✅ Dynasty value composite scores integrate all 6 dimensions (VoR, economics, age, scarcity, variance, market)
5. ✅ Backtesting framework validates 2020→2021-2023 projection accuracy

**Data Quality:**
6\. ✅ VoR baselines sum to expected totals (internal consistency check passes)
7\. ✅ Aging curves respect position-specific patterns (RB cliff, WR longevity, QB stability)
8\. ✅ Cap modeling handles all league rule edge cases (pro-rating constraints, dead cap schedule, 150% limits)
9\. ✅ Contract efficiency rankings identify intuitively correct best/worst value deals

**Technical Quality:**
10\. ✅ Python libraries structured in `src/ff_analytics_utils/` with modular design
11\. ✅ dbt marts materialize analytics outputs (`mrt_player_valuation`, `mrt_multi_year_projections`, etc.)
12\. ✅ Test coverage: 80%+ for valuation engines, 100% for cap rule validation
13\. ✅ Pipeline runtime: \<30 minutes end-to-end (weekly refresh)

**Documentation:**
14\. ✅ README for each analytics library explaining methodology, usage, validation results
15\. ✅ dbt model documentation for all analytics marts (grain, columns, dependencies)

### 5.2 Key Performance Indicators

**Projection Accuracy (Backtested):**

- **Target:** \<20% Mean Absolute Error (MAE) on 1-year ahead projections
- **Measurement:** Compare 2020 projections to 2021 actuals, 2021→2022, 2022→2023
- **Baseline:** FFAnalytics rest-of-season accuracy (~25-30% MAE typical for fantasy projections)
- **Stretch Goal:** \<15% MAE (best-in-class commercial projections)

**Market Inefficiency Detection:**

- **Target:** Identify ≥10 divergences per week (>15% delta between internal value and KTC)
- **Measurement:** Count of players where abs(dynasty_value - ktc_value) / ktc_value > 0.15
- **Validation:** Manual review of top 10 divergences confirms plausible rationale (age curve, contract economics, opportunity trends)

**Cap Modeling Accuracy:**

- **Target:** \<5% error vs manual calculations (gold standard = commissioner's spreadsheet)
- **Measurement:** Compare multi-year cap projections to hand-calculated scenarios
- **Validation:** Test edge cases (5-year back-loaded contract, multiple simultaneous cuts, traded cap scenarios)

**Portfolio Optimization Value:**

- **Target:** Identify ≥5 contract efficiency opportunities per analysis
- **Measurement:** Count of rostered players with $/WAR >20% above/below league median
- **Validation:** Cross-check with KTC market values (internal undervalued = KTC overvalued → arbitrage confirmed)

**System Performance:**

- **Target:** \<30 minute end-to-end pipeline runtime
- **Measurement:** Log timestamp deltas (start → analytics complete → marts materialized)
- **Baseline:** Manual analysis ~4-6 hours for equivalent depth

### 5.2 Decision Outcome Metrics

**Purpose:** Track whether analytical infrastructure actually improves **decision quality**, not just technical accuracy. These metrics measure real-world impact on roster management effectiveness.

**FASA Bidding Quality:**

- **Leading Indicator: Contract Efficiency at Acquisition**

  - **Measurement:** % of winning bids within ±15% of optimal contract efficiency threshold ($/WAR vs league median)
  - **Target:** 80% of winning bids within efficiency threshold
  - **How to Measure:** Post-FASA, calculate actual $/WAR vs predicted at time of bid
  - **Baseline (Current State):** Unknown - no systematic tracking (estimated 50-60%)

- **Lagging Indicator: Acquired Players Outperform Projections**

  - **Measurement:** Year-end actual PPG vs projection at time of bid
  - **Target:** 70% of acquisitions meet/exceed projected value (>30% bust rate = bad process)
  - **How to Measure:** Compare actual Year 1 performance to projection used during bidding
  - **Baseline (Current State):** Unknown - no systematic tracking

**Extension Decision Quality:**

- **Leading Indicator: Extensions Below Predicted Market Value**

  - **Measurement:** Extension AAV vs projected RFA/FAAD market reset value
  - **Target:** 4 extensions over 2 years, average 20% savings vs predicted market
  - **How to Measure:** Extension AAV compared to "wait for market" projection
  - **Example:** Extend Stroud at $18M/year vs projected RFA market of $24M/year = 25% savings

- **Lagging Indicator: Extended Players Justify Contracts**

  - **Measurement:** Year 2-3 actual $/WAR vs league median contract efficiency
  - **Target:** 60% of extensions remain above-median efficiency in Year 2-3
  - **How to Measure:** Track contract efficiency 2-3 years post-extension
  - **Baseline (Current State):** Unknown - league 'Transactions' data has extension history, but hasn't been analyzed or evaluated

**Trade Evaluation Quality:**

- **Leading Indicator: Accepted Trades Improve Dynasty Value**

  - **Measurement:** Roster dynasty value score before/after trade
  - **Target:** 90% of accepted trades increase dynasty value (10% allowance for "intangibles" like competitive window alignment)
  - **How to Measure:** Calculate dynasty value delta immediately post-trade
  - **Baseline (Current State):** ~70% (rough estimate based on trade history)

- **Lagging Indicator: Trades Align With Competitive Window**

  - **Measurement:** 2027 projected roster strength vs 2025 baseline
  - **Target:** Roster value +25% by championship window (2027-2028)
  - **How to Measure:** Multi-year projection of roster value trajectory
  - **Rationale:** Trading for youth now should compound value into 2027-2028 competitive window

**Meta-Metric: Infrastructure ROI**

- **Time Investment vs Time Savings:**

  - **Upfront Cost:** 238 hours (6 weeks) to build infrastructure
  - **Ongoing Savings:** 100-140 hours/season → 30 hours/season (70% reduction)
  - **Payback Period:** ~2.5 seasons (238 hours / 90 hours saved per season)

- **Decision Quality Improvement:**

  - **Current State:** 60% high-quality decisions (adequate time + rigor)
  - **Target State:** 85% high-quality decisions (systematic process + automation)
  - **Impact:** Fewer rushed/gut-feel decisions during time-constrained periods (FASA weeks)

- **Championship Probability (Ultimate Outcome):**

  - **Baseline:** 8.3% (1/12 teams, assuming equal probability)
  - **Target:** 15%+ championship probability by 2027-2028 (competitive edge from superior analytics)
  - **How to Measure:** Monte Carlo simulation of season outcomes based on roster projections
  - **Caveat:** Championship outcomes are noisy (injuries, luck), so track 3-year rolling average

**Tracking Mechanism:**

- **Decision Log:** Record all FASA bids, extensions, trades with:
  - Projected value at time of decision
  - Actual contract terms
  - Dynasty value scores (internal + KTC)
  - Rationale/notes
- **Quarterly Review:** Assess leading indicators (contract efficiency, value deltas)
- **Annual Review:** Assess lagging indicators (Year 1 performance, trade outcomes)
- **Backtesting Loop:** Update models if systematic bias detected (e.g., consistently over-projecting RBs)

### 5.3 Validation Framework

**Time-Series Cross-Validation:**

- **Method:** TimeSeriesSplit with 3+ folds (train 2019-2021, test 2022; train 2019-2022, test 2023, etc.)
- **No shuffle:** Strict temporal ordering prevents data leakage
- **Metrics:** MAE, RMSE, directional accuracy (did we predict up/down correctly?)

**Backtesting Protocol:**

- **Historical Projections:** Use 2020 data to project 2021, compare to actuals
- **Holdout Season:** Reserve 2024 as final validation set (not used in model training)
- **Position-Specific:** QB/RB/WR/TE validated separately (different accuracy patterns)

**Market Calibration:**

- **Relative Rankings:** Spearman correlation with KTC (target: 0.6-0.8, not 1.0 - we're trying to beat market)
- **Divergence Analysis:** Top 20 divergences manually reviewed for plausibility
- **Trade Outcomes:** Track if identified "buy-low" targets outperform in following season

**Internal Consistency Checks:**

- **VoR Baselines:** Sum of replacement level values = expected league-wide baseline
- **Cap Arithmetic:** Multi-year cap space projections sum correctly (no leaked dollars)
- **Aging Curves:** RB decline steeper than WR, QB stable longest (matches domain research)

______________________________________________________________________

## 6. Technical Architecture & Approach

### 6.1 System Architecture

**High-Level Flow:**

```
Source Data (Sleeper, FFAnalytics, nflverse, KTC, Sheets)
  ↓
dbt Staging Models (existing - 15 models)
  ↓
Prefect Orchestration Layer (NEW - this PRD)
  │
  ├─ Python Analytics Tasks (@task-decorated)
  │   ├─ src/ff_analytics_utils/valuation/
  │   │   ├─ vor.py (VoR calculation)
  │   │   ├─ war.py (WAR estimation)
  │   │   ├─ baselines.py (replacement levels)
  │   │   └─ positional_value.py (scarcity adjustments)
  │   │
  │   ├─ src/ff_analytics_utils/projections/
  │   │   ├─ multi_year.py (2025-2029 projections)
  │   │   ├─ aging_curves.py (position-specific trajectories)
  │   │   └─ opportunity.py (usage trend adjustments)
  │   │
  │   ├─ src/ff_analytics_utils/cap_modeling/
  │   │   ├─ scenarios.py (multi-year cap space)
  │   │   ├─ contracts.py (pro-rating, structure optimization)
  │   │   └─ dead_cap.py (50%/50%/25%/25%/25% schedule)
  │   │
  │   └─ src/ff_analytics_utils/composite/
  │       └─ dynasty_value.py (6-factor composite score)
  │
  ↓ (Writes Parquet files)
  │
Parquet Files (data/analytics/)
  ├─ player_valuation/latest.parquet
  ├─ multi_year_projections/latest.parquet
  ├─ cap_scenarios/latest.parquet
  └─ dynasty_value_composite/latest.parquet
  ↓
dbt Source Tables (analytics schema, external Parquet)
  ├─ source('analytics', 'player_valuation')
  ├─ source('analytics', 'multi_year_projections')
  ├─ source('analytics', 'cap_scenarios')
  └─ source('analytics', 'dynasty_value_composite')
  ↓
dbt Analytics Marts (NEW - 4 models, external Parquet)
  ├─ mrt_player_valuation (VoR/WAR by player)
  ├─ mrt_multi_year_projections (2025-2029 forecasts)
  ├─ mrt_cap_scenarios (multi-year cap space)
  └─ mrt_dynasty_value_composite (final composite scores)
  ↓
Jupyter Notebooks (consume external Parquet marts)
```

**Architecture Principles:**

1. **Separation of Concerns:** SQL for transformations (dbt), Python for complex calculations (analytics), SQL for consumption (marts)
2. **Testability:** Each analytics module independently testable with mock data
3. **Incremental Processing:** Support delta updates where possible (weekly stat refresh, not full historical recomputation)
4. **Idempotency:** Re-running produces identical results (deterministic algorithms, seeded randomness)

### 6.2 Technology Stack

**Core Analytics:**

- **Language:** Python 3.13.6
- **Data Manipulation:** Polars (columnar, high-performance)
- **ML Libraries:** scikit-learn (regression, time-series CV), statsmodels (statistical models)
- **Database:** DuckDB (existing, local analytical database)

**Data Transformation:**

- **Framework:** dbt-fusion 2.0.0-preview.32 (DuckDB adapter)
- **Models:** Staging (existing), Analytics Marts (new)
- **Testing:** dbt tests (grain uniqueness, referential integrity, not-null constraints)

**Development Tooling:**

- **Package Manager:** UV 0.8.8
- **Testing:** pytest
- **Linting:** ruff (existing project standard)
- **Version Control:** git (conventional commits)

**Orchestration (Future):**

- **Framework:** Prefect (in-flight via `multi_source_snapshot_governance`)
- **Integration:** Analytics pipeline as Prefect task (post-MVP)

### 6.3 Data Models

**Analytics Library Outputs → Database Tables:**

**`analytics.player_valuation`** (VoR/WAR results)

- Grain: One row per player per snapshot date
- Columns: `player_id`, `snapshot_date`, `vor`, `war`, `replacement_level`, `positional_scarcity_adjustment`, `contract_efficiency_dollar_per_war`

**`analytics.multi_year_projections`** (2025-2029 forecasts)

- Grain: One row per player per projection year per snapshot date
- Columns: `player_id`, `snapshot_date`, `projection_year`, `ppg_median`, `ppg_floor_p10`, `ppg_ceiling_p90`, `total_points`, `opportunity_share`, `age_adjustment_factor`

**`analytics.cap_scenarios`** (multi-year cap space)

- Grain: One row per franchise per projection year per scenario per snapshot date
- Columns: `franchise_id`, `snapshot_date`, `projection_year`, `scenario_name`, `base_cap`, `active_obligations`, `dead_cap_obligations`, `traded_cap_net`, `available_cap_space`

**`analytics.dynasty_value_composite`** (final scores)

- Grain: One row per player per snapshot date
- Columns: `player_id`, `snapshot_date`, `dynasty_value_score`, `vor_component`, `economics_component`, `age_component`, `scarcity_component`, `variance_component`, `market_component`, `ktc_value`, `value_delta_vs_market`

**dbt Mart Layer (Materialized Views):**

- `mrt_player_valuation` (SELECT * FROM analytics.player_valuation WHERE snapshot_date = latest)
- `mrt_multi_year_projections` (materialized with dbt tests: grain uniqueness, non-null player_id)
- `mrt_cap_scenarios` (documented: how to interpret scenario_name, cap calculations)
- `mrt_dynasty_value_composite` (tested: dynasty_value_score NOT NULL, ktc_value joined successfully)

### 6.4 Algorithm Design

**VoR Calculation (vor.py):**

```python
# Simplified pseudocode
def calculate_vor(player_stats, position, league_settings):
    """
    Calculate Value over Replacement.

    Methodology:
    1. Determine replacement level (e.g., 24th RB in 12-team league with 2 RB slots)
    2. Calculate player's projected points
    3. VoR = player_points - replacement_level_points
    """
    replacement_level = get_replacement_baseline(
        position=position,
        num_teams=league_settings.num_teams,
        starting_slots=league_settings.starting_slots[position]
    )

    player_points = player_stats.projected_ppg * 17  # 17-game season

    vor = player_points - replacement_level

    return vor
```

**Multi-Year Projection (multi_year.py):**

```python
# Simplified pseudocode
def generate_multi_year_projection(player, base_projection, years=[2025, 2026, 2027, 2028, 2029]):
    """
    Generate 2025-2029 projections with age curves and opportunity trends.

    Methodology:
    1. Start with base projection (FFAnalytics rest-of-season × 17 weeks)
    2. Apply age curve adjustment for each future year
    3. Apply opportunity trend (rising/declining usage)
    4. Add uncertainty (variance increases with horizon)
    """
    projections = {}

    for year in years:
        years_ahead = year - 2025
        age_at_year = player.age + years_ahead

        # Age curve adjustment (position-specific)
        age_factor = get_age_curve_factor(player.position, age_at_year)

        # Opportunity trend (3-game, 5-game rolling average slope)
        opportunity_factor = get_opportunity_trend(player, years_ahead)

        # Combine
        projected_ppg = base_projection.ppg * age_factor * opportunity_factor

        # Uncertainty (wider bands further out)
        uncertainty_std = base_projection.std * (1 + 0.2 * years_ahead)

        projections[year] = {
            'median': projected_ppg,
            'floor_p10': projected_ppg - 1.28 * uncertainty_std,
            'ceiling_p90': projected_ppg + 1.28 * uncertainty_std
        }

    return projections
```

**Cap Space Projection (scenarios.py):**

```python
# Simplified pseudocode
def project_cap_space(franchise, years=[2025, 2026, 2027, 2028, 2029]):
    """
    Project multi-year cap space accounting for contracts, dead cap, traded cap.

    Methodology:
    1. Base cap = $250 (fixed per league rules)
    2. Active obligations = sum of pro-rated contract amounts by year
    3. Dead cap = prior cuts decaying per 50%/50%/25%/25%/25% schedule
    4. Traded cap = net in/out by year
    5. Available = Base - Active - Dead + Traded
    """
    cap_projections = {}

    for year in years:
        base_cap = 250  # Fixed cap per league constitution

        # Active contract obligations
        active_obligations = sum(
            contract.get_prorated_amount(year)
            for contract in franchise.active_contracts
            if contract.end_year >= year
        )

        # Dead cap from prior cuts
        dead_cap = sum(
            cut.get_dead_cap_obligation(year)
            for cut in franchise.cut_history
        )

        # Traded cap (positive = received, negative = sent)
        traded_cap_net = franchise.get_traded_cap(year)

        available_cap = base_cap - active_obligations - dead_cap + traded_cap_net

        cap_projections[year] = {
            'base': base_cap,
            'active': active_obligations,
            'dead': dead_cap,
            'traded': traded_cap_net,
            'available': available_cap
        }

    return cap_projections
```

### 6.5 Testing Strategy

**Unit Tests (pytest):**

- **Coverage Target:** 80%+ for valuation logic, 100% for cap rule validation
- **Test Cases:**
  - VoR calculation: Known inputs → expected outputs
  - Age curves: RB decline steeper than WR (validate curve shape)
  - Cap modeling: Edge cases (5-year back-loaded contract, simultaneous cuts, traded cap)
  - Dead cap: 50%/50%/25%/25%/25% schedule applied correctly

**Integration Tests:**

- dbt mart tests (grain uniqueness, not-null constraints, referential integrity)
- End-to-end pipeline test (sample data → analytics → marts → query results)

**Backtesting Validation:**

- 2020→2021, 2021→2022, 2022→2023 projection accuracy
- MAE/RMSE metrics vs baseline (FFAnalytics rest-of-season)
- Position-specific validation (QB/RB/WR/TE)

**Property-Based Testing:**

- VoR baselines sum to expected totals (internal consistency)
- Cap space never negative (unless valid traded cap scenario)
- Aging curves monotonic (performance declines with age for RB/WR)

______________________________________________________________________

## 7. Out of Scope (This Phase)

### Explicitly NOT Building in MVP

**Decision Support Tools:**

- ❌ FASA bid optimizer (Phase 2 - after infrastructure validated)
- ❌ Trade analyzer UI (Phase 2)
- ❌ Weekly lineup optimizer (Phase 2)
- ❌ Roster analyzer dashboard (Phase 2)

**Rationale:** Infrastructure-first approach. Decision support tools require robust analytical foundation to be effective. Build engines now, UIs later.

**Real-Time Data:**

- ❌ Injury tracking ingestion (identified in data-gap-assessment, deferred)
- ❌ League standings extraction (deferred)
- ❌ Weekly matchup results (deferred)

**Rationale:** Not competing hard this season (7th place, injuries). Real-time data needed for in-season tactical tools (Phase 2), not strategic infrastructure (MVP).

**Advanced ML:**

- ❌ Deep learning projection models (98-layer networks)
- ❌ Reinforcement learning draft optimizer
- ❌ Manager profiling/pattern recognition

**Rationale:** Diminishing returns. Research shows well-engineered features + simple models often outperform complex models. Start simple, add complexity only if validated need.

### Future Phases (Roadmap)

**Phase 2: Decision Support Tools (3-4 months post-MVP)**

- FASA bid optimizer (contract structures, drop scenarios, contingent bids)
- Trade analyzer (multi-objective evaluation, win probability impact)
- Roster analyzer (competitive window assessment, portfolio rebalancing)
- Weekly lineup optimizer (injury-aware, variance-optimized)

**Phase 3: Advanced Analytics (6-12 months post-MVP)**

- Sustainability analysis (TD regression, FPOE, opportunity metrics)
- Market intelligence (contract expirations, positional depth, rookie draft class quality)
- Manager profiling (trade history patterns, bidding behavior)
- Auction bidding game theory (probabilistic strategies, tier-based organization)

**Phase 4: Platform Maturity (12+ months post-MVP)**

- Real-time data pipelines (injury tracking, standings, matchup results)
- Web dashboard (visualization layer for non-technical consumption)
- API layer (RESTful interface for external tool integration)
- Multi-user support (league-wide analytics for all 12 franchises)

______________________________________________________________________

## 8. Risks & Mitigations

### 8.1 Technical Risks

**RISK-001: Model Overfitting (High Impact, High Probability)**

**Description:** Small NFL samples (17 games/season) + complex models = overfitting risk. Standard cross-validation with shuffle inflates performance 15-20%.

**Impact:** Production projections underperform backtests, bad decisions based on overconfident valuations.

**Mitigation:**

- **Mandatory time-series validation:** TimeSeriesSplit only (no shuffle=True)
- **Holdout final season:** Reserve 2024 as validation set (not used in training)
- **Regularization:** Ridge/Lasso/Elastic Net for small samples
- **Model simplicity:** Well-engineered features + linear models over complex deep learning

**Probability Reduction:** High → Medium (rigorous validation catches overfitting before production)

______________________________________________________________________

**RISK-002: Data Staleness (Medium Impact, High Probability)**

**Description:** NFL rules change, coaching philosophies shift, player roles evolve. Historical patterns may not hold.

**Impact:** Projections based on stale data miss recent trends (e.g., pass-heavy offense shift, RB committee backfields).

**Mitigation:**

- **Weight recent data 10x:** Rolling averages prioritize last 2-3 seasons
- **Sliding window validation:** 5-year max history (drop pre-2020 data)
- **Annual retraining:** Models retrained July/August before each season
- **In-season updates:** Week 4 and Week 10 refreshes with new data

**Probability Reduction:** High → Low (frequent retraining + recency weighting keeps models fresh)

______________________________________________________________________

**RISK-003: Position Heterogeneity Ignored (Medium Impact, Medium Probability)**

**Description:** QB/RB/WR/TE have different predictive features, aging curves, opportunity metrics. One-size-fits-all model underperforms.

**Impact:** Generic projections miss position-specific dynamics (e.g., RB cliff at Year 7, TE breakout Year 2).

**Mitigation:**

- **Position-specific models:** Separate engines for QB/RB/WR/TE
- **Feature sets tailored:** RB uses carry share + team run rate, WR uses target share + QB quality
- **Aging curves distinct:** RB steep decline, WR gradual, QB stable
- **Backtesting validates:** Position-specific models must outperform generic by >15% MAE

**Probability Reduction:** Medium → Low (architecture enforces position-specific design)

______________________________________________________________________

**RISK-004: Cap Modeling Rule Violations (High Impact, Low Probability)**

**Description:** League constitution has complex contract rules (150% pro-rating constraints, 50%/50%/25% dead cap schedule). Implementation bugs = illegal structures modeled.

**Impact:** Catastrophic - build decisions on invalid cap assumptions, discover illegality when trying to execute.

**Mitigation:**

- **100% test coverage:** Cap rule validation tests cover all edge cases
- **Commissioner validation:** Cross-check outputs against commissioner's manual spreadsheet
- **Constraint enforcement:** Pro-rating validator prevents illegal structures
- **Edge case testing:** 5-year back-loaded, simultaneous cuts, traded cap scenarios

**Probability Reduction:** Low → Very Low (rigorous testing + manual validation catches bugs)

______________________________________________________________________

### 8.2 Domain Risks

**RISK-005: Market Inefficiency Assumption (High Impact, Medium Probability)**

**Description:** If all league managers adopt sophisticated analytics, inefficiencies disappear. Arbitrage opportunities erode over time.

**Impact:** Dynasty value scores diverge from KTC, but divergences not exploitable (all managers see same signals).

**Mitigation:**

- **League-specific calibration:** Trade history analysis identifies league patterns (not generic market)
- **Unique constraints:** Salary cap + 13-year transaction history = proprietary advantage unavailable to competitors
- **Continuous monitoring:** Track arbitrage success rate (buy-low targets outperforming? sell-high targets underperforming?)
- **Adaptive strategy:** If inefficiencies erode, shift to other competitive edges (cap arbitrage, rookie contract value)

**Probability Reduction:** Medium → Medium (cannot fully eliminate - competitive advantage always at risk of erosion)

______________________________________________________________________

**RISK-006: Competitive Window Mistiming (High Impact, Low Probability)**

**Description:** Multi-year projections guide "pivot to compete" decisions. If projections wrong, pivot too early (waste picks) or too late (aging roster).

**Impact:** Strategic blunders - going "all-in" when window actually 2 years away, or rebuilding when competitive now.

**Mitigation:**

- **Reassess every 4-6 weeks:** Competitive window analysis not static, update with new data
- **Probabilistic modeling:** Monte Carlo simulations quantify window uncertainty (not point estimates)
- **Portfolio balance:** Maintain mix of proven veterans + youth (hedge against timing errors)
- **Flexible pivot:** Avoid "all-in" or "full rebuild" extremes (gradual adjustments)

**Probability Reduction:** Low → Very Low (frequent reassessment + probabilistic thinking reduces mistiming risk)

______________________________________________________________________

**RISK-007: Injury Black Swans (High Impact, Low Probability)**

**Description:** Season-ending injuries to key players (Stroud, Achane, Nabers) unpredictable. Projections assume health.

**Impact:** Roster value collapses, competitive window shifts, projections useless.

**Mitigation:**

- **Portfolio diversification:** Spread value across multiple positions + age ranges (not concentrated in 2-3 players)
- **High-floor depth:** Rostered backups with proven production (not just high-upside dart throws)
- **Injury insurance:** Handcuff valuable RBs (backup RB on same team)
- **Historical durability:** Weight projections by games played history (injury-prone players discounted)

**Probability Reduction:** Low → Low (cannot predict injuries, but portfolio construction limits blast radius)

______________________________________________________________________

### 8.3 Execution Risks

**RISK-008: Scope Creep (Medium Impact, High Probability)**

**Description:** Temptation to add "just one more feature" delays MVP. Infrastructure project becomes decision support tool project.

**Impact:** Timeline slips from 1-2 months to 3-4 months, parallel orchestration work gets out of sync, user loses interest.

**Mitigation:**

- **Strict scope:** MVP = analytical engines ONLY (no UIs, no decision support tools)
- **Phase gate:** Infrastructure must be validated (backtesting complete, marts materialized) before Phase 2 starts
- **Ruthless prioritization:** "Nice to have" features deferred to Phase 2/3/4
- **Weekly check-ins:** PM reviews progress, enforces scope boundaries

**Probability Reduction:** High → Medium (active scope management + phase gate discipline)

______________________________________________________________________

**RISK-009: Python-dbt Integration Complexity (Medium Impact, Medium Probability)**

**Description:** Hybrid architecture (Python analytics → database → dbt marts) introduces integration points. Data type mismatches, schema drift, pipeline failures.

**Impact:** Analytics run successfully but marts fail to materialize. Debugging integration issues burns time.

**Mitigation:**

- **Contract-driven design:** Python outputs conform to documented schema (analytics.player_valuation spec)
- **Integration tests:** End-to-end pipeline test validates Python → database → dbt flow
- **Type safety:** Polars DataFrames with explicit schemas prevent data type surprises
- **dbt tests:** Mart-level tests catch schema drift (column renames, type changes)

**Probability Reduction:** Medium → Low (rigorous testing + contract-driven design)

______________________________________________________________________

**RISK-010: Validation Disagreement (Low Impact, High Probability)**

**Description:** Dynasty value scores diverge significantly from KTC. Unclear if "we're right and market is wrong" or "our model is broken."

**Impact:** Confidence crisis - should we trust our valuations? Manual investigation burns time.

**Mitigation:**

- **Calibration range:** Expect 0.6-0.8 Spearman correlation with KTC (not 1.0 - we're trying to beat market)
- **Divergence investigation:** Top 20 divergences manually reviewed for plausibility (age curve? contract economics? opportunity trend?)
- **Trade outcome tracking:** Monitor if "buy-low" targets actually outperform in following season (validation metric)
- **Ensemble approach:** Blend internal valuations with KTC (weighted average) if pure internal too contrarian

**Probability Reduction:** High → Medium (accept divergence as feature, validate with outcomes)

______________________________________________________________________

## 9. Dependencies & Assumptions

### 9.1 External Dependencies

**Data Source Availability:**

- **nflverse:** Historical NFL stats (2019+) remain freely available via `nfl_data_py`
- **FFAnalytics:** Rest-of-season projections API continues providing weekly updates
- **KTC:** Dynasty values API remains accessible (or web scraping fallback)
- **Sleeper:** Platform APIs for roster data continue functioning
- **Commissioner Sheets:** Google Sheets access maintained (contract/cap/pick data)

**Dependency Risk:** Low (nflverse/FFAnalytics well-established, alternative sources available)

**Mitigation:** Monitor API health, maintain fallback scrapers for KTC/Sleeper

______________________________________________________________________

**Orchestration Integration:**

- **Prerequisite:** Prefect infrastructure built FIRST (Week 1-2) before analytics (Week 3-8)
- **Architecture:** Analytics designed as Prefect-native from Day 1 (@task decorators, flow orchestration)
- **Template Patterns:** Snapshot governance Prefect flows provide proven patterns for analytics flows (Discord notifications, error handling, retry logic)
- **Cloud Infrastructure:** Prefect Cloud (SaaS) for orchestration, flows run locally during development, GCS storage for production Parquet

**Dependency Risk:** Low (Prefect foundation straightforward, snapshot governance flows provide working examples)

______________________________________________________________________

**dbt Infrastructure:**

- **Assumption:** Existing dbt staging models remain stable (no breaking schema changes)
- **Dependency:** Analytics consumes `mrt_fantasy_actuals_weekly`, `mrt_fantasy_projections`, `mrt_contract_snapshot_current`, etc.

**Dependency Risk:** Low (dbt models mature, schema changes communicated)

**Mitigation:** Pin dbt model versions, integration tests catch upstream changes

______________________________________________________________________

### 9.2 Key Assumptions

**Domain Assumptions:**

1. **Historical Patterns Predictive:** Past 3-5 years NFL data predicts future (aging curves, positional trends)

   - **Validation:** Backtesting 2020→2023 confirms historical patterns hold
   - **Risk:** Rule changes, offensive philosophy shifts invalidate patterns

2. **VoR Framework Applicable:** Wins Above Replacement translates from baseball/NFL to fantasy football

   - **Validation:** Fantasy Points methodology demonstrates feasibility
   - **Risk:** League-specific scoring makes generic VoR less applicable (need customization)

3. **Market Inefficiencies Exist:** KTC consensus can be beaten with superior analytics

   - **Validation:** Contract economics + proprietary data = unique information not in KTC
   - **Risk:** If league managers sophisticated, inefficiencies erode

4. **Multi-Year Projections Useful:** 2025-2029 forecasts inform decisions despite uncertainty

   - **Validation:** Competitive window analysis (2027 cap explosion) requires multi-year view
   - **Risk:** Projection error compounds with horizon (3-year ahead = high uncertainty)

**Technical Assumptions:**

5. **Python-dbt Hybrid Works:** Complex analytics better in Python than SQL, dbt layer for consumption

   - **Validation:** Industry pattern (Airflow + dbt, Prefect + dbt)
   - **Risk:** Integration complexity, debugging across layers

6. **DuckDB Scales:** Local analytical database handles 500+ players × 5 years × weekly snapshots

   - **Validation:** DuckDB designed for analytical workloads, columnar storage efficient
   - **Risk:** If data volume explodes (adding more leagues, more history), may need distributed database

7. **Weekly Refresh Sufficient:** Analytics don't need daily/hourly updates

   - **Validation:** FASA weekly, trades ad-hoc, strategic planning monthly
   - **Risk:** If real-time decision support needed (Phase 2), refresh cadence increases

**User Assumptions:**

08. **Single User (Jason):** Platform designed for self-service, not multi-user

    - **Validation:** User confirmed single franchise management
    - **Risk:** If expanding to league-wide analytics (all 12 franchises), need access controls

09. **Technical User:** Comfortable with Jupyter notebooks, dbt, SQL queries

    - **Validation:** User built existing pipeline, writes Python/SQL
    - **Risk:** None (user highly technical)

10. **Aggressive Timeline Feasible:** 1-2 months MVP delivery acceptable to user

    - **Validation:** User confirmed aggressive timeline
    - **Risk:** Scope creep, unforeseen complexity (mitigated by strict scope control)

______________________________________________________________________

### 9.3 Validation Checkpoints

**Week 2 Checkpoint: VoR Engine Validation**

- **Deliverable:** VoR/WAR calculations for 50 sample players
- **Validation:** Compare to hand-calculated examples, cross-check with Fantasy Points conceptual framework
- **Go/No-Go:** If VoR baselines don't sum correctly or WAR values wildly off, pause and debug before proceeding

**Week 4 Checkpoint: Projection Backtesting**

- **Deliverable:** 2020→2021 projection accuracy results (MAE, RMSE)
- **Validation:** \<25% MAE (baseline), \<20% MAE (target)
- **Go/No-Go:** If >30% MAE, investigate feature engineering or model selection issues

**Week 6 Checkpoint: Cap Modeling Validation**

- **Deliverable:** Multi-year cap scenarios (2025-2029) for Jason's franchise
- **Validation:** Cross-check against commissioner spreadsheet, \<$5M error tolerance
- **Go/No-Go:** If cap calculations wrong, high risk for downstream decisions (must fix)

**Week 8 Checkpoint: Integration Testing**

- **Deliverable:** End-to-end pipeline (Python analytics → dbt marts → notebook consumption)
- **Validation:** Pipeline runs without errors, marts materialized with expected row counts
- **Go/No-Go:** If integration broken, blocks user consumption (must fix before MVP release)

______________________________________________________________________

## 10. Epic Breakdown & Implementation Plan

### Epic Structure

This section provides a tactical breakdown of the analytical infrastructure MVP into executable epics and stories. Each epic represents a cohesive unit of functionality that can be developed, tested, and validated independently.

______________________________________________________________________

### Epic 0: Prefect Foundation Setup

**Epic Goal:** Establish Prefect orchestration infrastructure before building analytics tasks. This foundation enables analytics to be built as Prefect-native from Day 1.

**Success Criteria:**

- Prefect Cloud workspace configured and tested
- Discord webhook block created for analytics alerts
- Task/flow decorator templates validated with working examples
- Local development environment proven (flows run successfully on Mac)
- Integration patterns documented from snapshot governance flows

**Dependencies:** None (foundation work, prerequisite for all other epics)

**Stories:**

**E0-S1: Prefect Cloud Workspace Setup**

- **Task:** Create Prefect Cloud workspace, configure authentication, test deployment
- **Outputs:** Workspace URL, API keys stored securely in environment variables
- **Acceptance:** Can deploy and trigger simple test flow from local Mac environment
- **Estimate:** 2 hours

**E0-S2: Discord Notification Block**

- **Task:** Create and configure DiscordWebhook block for analytics alerts
- **Outputs:** Block saved in Prefect Cloud (`ff-analytics-alerts`), tested with sample alert
- **Acceptance:** Discord message successfully received in designated channel with formatted alert
- **Estimate:** 1 hour

**E0-S3: Analytics Flow Templates**

- **Task:** Create reusable @task and @flow decorator templates for analytics patterns
- **Outputs:**
  - Template for data loading tasks (read dbt marts, return Polars DataFrames)
  - Template for analytics computation tasks (Pydantic schema validation)
  - Template for Parquet writer tasks (write to `data/analytics/`)
  - Template for dbt runner tasks (trigger `just dbt-run --select <model>`)
- **Acceptance:** All templates validated with working "hello world" examples that execute successfully
- **Estimate:** 4 hours

**E0-S4: Snapshot Governance Flow Integration Review**

- **Task:** Review existing snapshot governance Prefect flows to extract proven patterns
- **Outputs:**
  - Documented integration points (how analytics fits with snapshot ingestion → dbt staging → analytics pipeline)
  - Identified reusable patterns (error handling, retry logic, Discord notifications, artifact tracking)
  - Sequence diagram showing full data flow: Snapshot ingest → dbt staging → analytics → dbt analytics marts
- **Acceptance:** Clear architectural understanding of how analytics flows integrate with existing orchestration
- **Estimate:** 3 hours

**Epic 0 Total Estimate:** 10 hours (~1-2 days)

______________________________________________________________________

### Epic 1: VoR/WAR Valuation Engine

**Epic Goal:** Build the foundational player valuation engine calculating Value over Replacement (VoR) and Wins Above Replacement (WAR) for all players.

**Success Criteria:**

- VoR calculations for 500+ NFL players (all rostered + top 200 free agents)
- VoR baselines sum to expected league-wide totals (internal consistency check)
- WAR methodology aligns conceptually with Fantasy Points framework
- Contract efficiency metrics ($/WAR, $/VoR) identify best/worst value contracts

**Dependencies:**

- Epic 0: Prefect Foundation Setup (prerequisite - tasks must be Prefect-decorated)
- Existing dbt models: `mrt_fantasy_actuals_weekly`, `mrt_contract_snapshot_current`

**Stories:**

**E1-S1: Replacement Level Baseline Calculation**

- **Task:** Implement `baselines.py` to calculate position-specific replacement levels
- **Inputs:** League roster settings (12 teams, 2 RB, 3 WR, 1 TE, 1 FLEX, etc.)
- **Outputs:** Replacement level thresholds (QB12, RB24, WR36, TE12)
- **Acceptance:** Baselines match league roster depth (24 RBs rostered = RB24 is replacement level)
- **Estimate:** 4 hours

**E1-S2: VoR Calculation Engine**

- **Task:** Implement `vor.py` to calculate VoR for all players
- **Inputs:** Player projections (PPG), replacement baselines
- **Outputs:** VoR scores by player (value above replacement level)
- **Acceptance:** VoR for top 10 players per position matches hand-calculated examples within 5%
- **Estimate:** 6 hours

**E1-S3: WAR Estimation**

- **Task:** Implement `war.py` to convert fantasy points to wins above replacement
- **Inputs:** VoR scores, league scoring settings
- **Outputs:** WAR estimates (expected wins added vs replacement)
- **Acceptance:** WAR methodology documented, conceptually aligns with Fantasy Points framework (different scale OK)
- **Estimate:** 6 hours

**E1-S4: Positional Scarcity Adjustment**

- **Task:** Implement `positional_value.py` for cross-positional value algorithm
- **Inputs:** VoR by position, roster constraints (starting slots, bench depth)
- **Outputs:** Scarcity-adjusted valuations (RB premium, WR depth discount)
- **Acceptance:** RB/QB valued higher than WR/TE given scoring and roster settings
- **Estimate:** 6 hours

**E1-S5: Contract Economics Integration**

- **Task:** Calculate $/WAR and $/VoR efficiency metrics
- **Inputs:** Player contracts (annual cost), WAR/VoR scores
- **Outputs:** Contract efficiency rankings (best/worst value deals)
- **Acceptance:** Top 10 best value = rookie contracts + undervalued veterans, worst value = expensive busts
- **Estimate:** 4 hours

**E1-S6: dbt Mart: mrt_player_valuation**

- **Task:** Create dbt model materializing VoR/WAR results as mart
- **Inputs:** `analytics.player_valuation` table (Python output)
- **Outputs:** `mrt_player_valuation` mart with dbt tests (grain uniqueness, not-null)
- **Acceptance:** Mart queryable from notebooks, dbt tests pass
- **Estimate:** 4 hours

**E1-S7: Unit Tests & Validation**

- **Task:** Write pytest tests for VoR/WAR engines
- **Test Cases:** Known inputs → expected outputs, baseline consistency checks
- **Coverage Target:** 80%+
- **Estimate:** 6 hours

**Epic 1 Total Estimate:** 36 hours (~1 week)

______________________________________________________________________

### Epic 2: Multi-Year Projection System

**Epic Goal:** Generate 2025-2029 projections for all players integrating age curves, opportunity trends, and uncertainty quantification.

**Success Criteria:**

- Multi-year projections (5-year horizon) for all rostered players + top 200 free agents
- Backtesting shows \<20% MAE on 1-year ahead (2020→2021, 2021→2022, 2022→2023)
- Aging curves respect position-specific patterns (RB cliff, WR longevity, QB stability)
- Projection distributions (floor/ceiling/median) capture 80% of actual outcomes

**Dependencies:**

- Existing dbt models: `mrt_fantasy_projections`, nflverse opportunity metrics
- Epic 1 VoR engine (for validation comparisons)

**Stories:**

**E2-S1: Aging Curve Derivation**

- **Task:** Implement `aging_curves.py` to derive position-specific age curves from historical data
- **Inputs:** nflverse historical stats (2019-2024), player ages
- **Outputs:** Aging curve functions (QB/RB/WR/TE) modeling performance decline by age
- **Acceptance:** RB cliff at Year 7, WR longevity to Year 10+, QB stable to Year 12+ (matches domain research)
- **Estimate:** 8 hours

**E2-S2: Opportunity Trend Analysis**

- **Task:** Implement `opportunity.py` for usage trend adjustments (rising/declining opportunity)
- **Inputs:** nflverse snap %, target share, carry share (3-game, 5-game rolling averages)
- **Outputs:** Opportunity trend factors (0.8 = declining, 1.2 = rising)
- **Acceptance:** Opportunity trends improve projection accuracy >5% MAE vs naive baseline (backtested)
- **Estimate:** 8 hours

**E2-S3: Multi-Year Projection Engine**

- **Task:** Implement `multi_year.py` to generate 2025-2029 projections
- **Inputs:** Base projections (FFAnalytics rest-of-season), age curves, opportunity trends
- **Outputs:** Yearly projections (PPG, total points) with confidence intervals (floor/ceiling/median)
- **Acceptance:** Projections for 500+ players across 5 years, uncertainty increases with horizon
- **Estimate:** 10 hours

**E2-S4: Position-Specific Model Tuning**

- **Task:** Separate models for QB/RB/WR/TE with position-specific features
- **Inputs:** Position-specific feature sets (RB: carry share, WR: target share + QB quality, etc.)
- **Outputs:** Position-specific projection functions
- **Acceptance:** Position models outperform generic model by >15% MAE (backtested)
- **Estimate:** 10 hours

**E2-S5: Backtesting Framework**

- **Task:** Build backtesting infrastructure for 2020→2021, 2021→2022, 2022→2023 validation
- **Inputs:** Historical projections, actual outcomes
- **Outputs:** MAE, RMSE, directional accuracy metrics by position
- **Acceptance:** \<20% MAE on 1-year ahead target achieved
- **Estimate:** 8 hours

**E2-S6: dbt Mart: mrt_multi_year_projections**

- **Task:** Create dbt model materializing multi-year projections as mart
- **Inputs:** `analytics.multi_year_projections` table (Python output)
- **Outputs:** `mrt_multi_year_projections` mart with dbt tests
- **Acceptance:** Mart queryable, grain = player × projection_year
- **Estimate:** 4 hours

**E2-S7: Unit Tests & Validation**

- **Task:** Write pytest tests for projection engines
- **Test Cases:** Age curves monotonic, opportunity trends bounded, projections non-negative
- **Coverage Target:** 80%+
- **Estimate:** 6 hours

**Epic 2 Total Estimate:** 54 hours (~1.5 weeks)

______________________________________________________________________

### Epic 3: Cap Space Projection & Modeling

**Epic Goal:** Build multi-year cap space scenario modeling with contract structure optimization and dead cap calculation per league rules.

**Success Criteria:**

- Multi-year cap projections (2025-2029) for Jason's franchise
- Cap modeling accuracy \<5% error vs commissioner's manual calculations
- Contract structure optimization validates 150% pro-rating constraints
- Dead cap calculations implement 50%/50%/25%/25%/25% schedule exactly

**Dependencies:**

- Existing dbt models: `mrt_contract_snapshot_current`, `mrt_cap_situation`

**Stories:**

**E3-S1: Dead Cap Calculation Engine**

- **Task:** Implement `dead_cap.py` with 50%/50%/25%/25%/25% schedule per league constitution
- **Inputs:** Cut player, original contract details (years remaining, pro-rated amounts)
- **Outputs:** Dead cap obligations by year (Year 1-5)
- **Acceptance:** 100% rule compliance, matches commissioner spreadsheet calculations exactly
- **Estimate:** 6 hours

**E3-S2: Contract Structure Validator**

- **Task:** Implement `contracts.py` to validate pro-rating constraints (150% geometric limits)
- **Inputs:** Proposed contract structure (total value, years, pro-rated breakdown)
- **Outputs:** Valid/invalid determination, constraint violations flagged
- **Acceptance:** Catches illegal structures (>150% spread), allows legal structures
- **Estimate:** 6 hours

**E3-S3: Multi-Year Cap Space Projector**

- **Task:** Implement `scenarios.py` to project 2025-2029 cap space
- **Inputs:** Current contracts, cut history, traded cap
- **Outputs:** Cap space by year (base, active, dead, traded, available)
- **Acceptance:** Jason's franchise shows $71M (2025-2026) → $158M (2027) → $250M (2029) progression
- **Estimate:** 10 hours

**E3-S4: Extension Scenario Modeling**

- **Task:** Add extension scenario support (extend player before contract expires)
- **Inputs:** Player to extend, extension structure (years, total value, pro-rating)
- **Outputs:** Cap impact comparison (extend now vs wait for RFA/FAAD)
- **Acceptance:** Extension scenarios quantify cap savings vs flexibility trade-offs
- **Estimate:** 8 hours

**E3-S5: Contract Efficiency Benchmarking**

- **Task:** Calculate $/WAR for all rostered players, identify cut candidates
- **Inputs:** Player contracts, WAR scores (from Epic 1)
- **Outputs:** Efficiency rankings, cut candidate list (negative value + manageable dead cap)
- **Acceptance:** Efficiency rankings intuitively correct, cut candidates actionable
- **Estimate:** 6 hours

**E3-S6: dbt Mart: mrt_cap_scenarios**

- **Task:** Create dbt model materializing cap scenarios as mart
- **Inputs:** `analytics.cap_scenarios` table (Python output)
- **Outputs:** `mrt_cap_scenarios` mart with dbt tests
- **Acceptance:** Mart queryable, scenarios documented (baseline, extension, cut scenarios)
- **Estimate:** 4 hours

**E3-S7: Unit Tests & Validation**

- **Task:** Write pytest tests for cap modeling
- **Test Cases:** Dead cap edge cases, pro-rating constraints, multi-year arithmetic
- **Coverage Target:** 100% (cap rules are deterministic, must be bug-free)
- **Estimate:** 8 hours

**E3-S8: Commissioner Validation**

- **Task:** Cross-check cap projections against commissioner's manual spreadsheet
- **Validation:** Run Jason's actual roster, compare outputs
- **Acceptance:** \<$5M error tolerance across all years
- **Estimate:** 4 hours

**Epic 3 Total Estimate:** 52 hours (~1.5 weeks)

______________________________________________________________________

### Epic 4: Dynasty Value Composite Score

**Epic Goal:** Integrate 6 dimensions (VoR, economics, age, scarcity, variance, market) into unified dynasty value score.

**Success Criteria:**

- Dynasty value scores for 500+ players (rostered + free agents)
- Correlation with KTC: 0.6-0.8 Spearman (beat market, not match it)
- Top 20 divergences (internal vs KTC) manually reviewed for plausibility
- Market inefficiency detection: ≥10 opportunities per week (>15% delta)

**Dependencies:**

- Epic 1: VoR/WAR (economics component)
- Epic 2: Multi-year projections (age component, variance component)
- Epic 3: Cap modeling (economics component)
- External: KTC API integration

**Stories:**

**E4-S1: Variance Component Calculation**

- **Task:** Calculate consistency ratings (std_dev / mean PPG) and floor/ceiling spreads
- **Inputs:** Multi-year projection distributions (from Epic 2)
- **Outputs:** Variance scores (high-floor vs high-ceiling classification)
- **Acceptance:** High-variance players = late-round upside, low-variance = roster foundation
- **Estimate:** 6 hours

**E4-S2: Age Component Integration**

- **Task:** Extract age-adjusted value from multi-year projections
- **Inputs:** Aging curves (from Epic 2), player ages
- **Outputs:** Age component (young players valued higher than aging veterans on same production)
- **Acceptance:** 24-year-old WR valued higher than 29-year-old WR with same 2025 projection
- **Estimate:** 4 hours

**E4-S3: KTC Market Signal Integration**

- **Task:** Fetch KTC dynasty values via API, join to internal valuations
- **Inputs:** KTC API (or web scraping fallback)
- **Outputs:** Market component (KTC consensus values)
- **Acceptance:** Weekly refresh, 500+ player coverage
- **Estimate:** 8 hours

**E4-S4: Composite Score Algorithm**

- **Task:** Implement `dynasty_value.py` combining 6 dimensions with configurable weights
- **Inputs:** VoR (30%), economics (20%), age (20%), scarcity (15%), variance (10%), market (5%)
- **Outputs:** Unified dynasty value score (0-10,000 scale)
- **Acceptance:** Top 100 players ranked in reasonable order (no major outliers)
- **Estimate:** 8 hours

**E4-S5: Divergence Analysis**

- **Task:** Calculate delta (internal value - KTC), flag arbitrage opportunities
- **Inputs:** Dynasty value scores, KTC values
- **Outputs:** Divergence report (>15% delta, minimum $2K absolute)
- **Acceptance:** ≥10 opportunities per week, top 20 manually reviewed for plausibility
- **Estimate:** 6 hours

**E4-S6: dbt Mart: mrt_dynasty_value_composite**

- **Task:** Create dbt model materializing composite scores as mart
- **Inputs:** `analytics.dynasty_value_composite` table (Python output)
- **Outputs:** `mrt_dynasty_value_composite` mart with dbt tests
- **Acceptance:** Mart queryable, KTC values joined successfully
- **Estimate:** 4 hours

**E4-S7: Market Calibration Validation**

- **Task:** Validate Spearman correlation with KTC (target: 0.6-0.8)
- **Validation:** Top 20 divergences investigated (age curve? contract economics? opportunity?)
- **Acceptance:** Divergences have plausible rationale, not random noise
- **Estimate:** 6 hours

**E4-S8: Unit Tests**

- **Task:** Write pytest tests for composite score logic
- **Test Cases:** Component weighting sums to 100%, scores non-negative, divergence calculation correct
- **Coverage Target:** 80%+
- **Estimate:** 4 hours

**Epic 4 Total Estimate:** 46 hours (~1 week)

______________________________________________________________________

### Epic 5: Integration & End-to-End Validation

**Epic Goal:** Validate end-to-end Prefect flow integration, dbt mart materialization, and notebook consumption patterns.

**Success Criteria:**

- End-to-end Prefect flow runs without errors (Python analytics → Parquet → dbt source → dbt marts)
- Pipeline runtime \<30 minutes
- Notebooks successfully consume external Parquet analytics marts
- dbt documentation complete for all analytics models
- Backtesting flow runs on schedule and sends Discord alerts

**Dependencies:**

- Epic 0: Prefect Foundation (prerequisite)
- Epics 1-4 complete (all analytics engines built as Prefect tasks)

**Stories:**

**E5-S1: Parquet Writer Validation**

- **Task:** Validate Python analytics → Parquet → dbt source pattern end-to-end
- **Workflow:**
  1. Prefect task executes analytics (e.g., VoR calculation)
  2. Task writes Polars DataFrame to Parquet (`data/analytics/player_valuation/latest.parquet`)
  3. dbt source table reads Parquet as external table
  4. dbt mart materializes from source
- **Acceptance:** Complete flow works (Prefect task → Parquet write → dbt source read → dbt mart materialized)
- **Estimate:** 4 hours

**E5-S2: dbt Mart Materialization**

- **Task:** Create 4 dbt models (mrt_player_valuation, mrt_multi_year_projections, mrt_cap_scenarios, mrt_dynasty_value_composite)
- **Inputs:** `analytics` schema tables
- **Outputs:** Materialized marts in `marts` schema
- **Acceptance:** `dbt run` succeeds, marts queryable
- **Estimate:** 6 hours

**E5-S3: dbt Tests & Documentation**

- **Task:** Add dbt tests (grain uniqueness, not-null, referential integrity) and model documentation
- **Tests:** Grain = player_id per snapshot, not-null primary keys, foreign keys resolve
- **Documentation:** Column descriptions, grain definition, dependencies
- **Acceptance:** `dbt test` passes, `dbt docs generate` produces comprehensive docs
- **Estimate:** 8 hours

**E5-S4: Analytics Pipeline Flow Orchestration**

- **Task:** Create main analytics flow orchestrating all tasks (VoR → Projections → Cap → Composite → dbt)
- **Workflow:**
  - @flow decorator wraps entire pipeline
  - Task dependencies properly chained (VoR completes before Projections starts, etc.)
  - Error handling and retry logic configured
  - Prefect artifacts track intermediate results
- **Acceptance:** Single `analytics_pipeline_flow()` execution runs all tasks in correct order, Prefect UI shows task graph and timing
- **Estimate:** 6 hours

**E5-S5: Integration Testing**

- **Task:** Build end-to-end integration test with sample data
- **Test Flow:** Load sample → run analytics → validate marts → query results
- **Acceptance:** Integration test passes in CI/CD (future), runs locally
- **Estimate:** 8 hours

**E5-S6: Notebook Consumption Validation**

- **Task:** Create sample Jupyter notebook consuming analytics marts
- **Notebook:** Load dynasty value scores, plot top 100 players, compare to KTC
- **Acceptance:** Notebook runs without errors, visualizations render
- **Estimate:** 4 hours

**E5-S7: Performance Optimization**

- **Task:** Profile pipeline, optimize bottlenecks (parallelization, indexing, caching)
- **Target:** \<30 minute runtime end-to-end
- **Acceptance:** Pipeline completes in target time, no obvious inefficiencies
- **Estimate:** 6 hours

**E5-S8: Backtesting Flow & Continuous Validation**

- **Task:** Create scheduled backtesting flow with Discord alerts on model regression
- **Workflow:**
  - Separate @flow for backtesting (independent of main analytics pipeline)
  - TimeSeriesSplit validation (train on 2020-2021, test on 2022, etc.)
  - Calculate MAE by position, compare to thresholds
  - Discord alert if MAE exceeds threshold (e.g., RB MAE > 20%)
  - Schedule via Prefect deployment (`cron="0 9 * * 1"` for weekly Monday 9am runs)
- **Acceptance:** Backtesting flow executes successfully, Discord alert received on regression test, Prefect schedule confirmed active
- **Estimate:** 8 hours

**E5-S9: Documentation & README**

- **Task:** Write comprehensive README for analytics infrastructure
- **Content:** Architecture diagram, usage instructions, validation results, troubleshooting
- **Acceptance:** New user can understand and run pipeline from README alone
- **Estimate:** 4 hours

**Epic 5 Total Estimate:** 54 hours (~1.5 weeks)

______________________________________________________________________

### Implementation Timeline

**Total Estimate:** 252 hours (~6.5 weeks at 40 hours/week, ~5 weeks aggressive)

- Epic 0: 10 hours
- Epic 1: 36 hours
- Epic 2: 54 hours
- Epic 3: 52 hours
- Epic 4: 46 hours
- Epic 5: 54 hours

**Phased Delivery:**

**Week 1: Prefect Foundation + VoR Engine (Epic 0 + Epic 1 Start)**

- Days 1-2: Epic 0 (Prefect Cloud setup, Discord integration, flow templates)
- Days 3-5: Epic 1 begins (VoR/WAR engine as Prefect tasks)
- **Checkpoint:** Prefect flows working, first analytics task executes successfully

**Weeks 2-3: Core Analytics (Epic 1 Complete + Epic 2)**

- Week 2: Complete Epic 1 (VoR/WAR), start Epic 2 (Multi-year projections)
- Week 3: Complete Epic 2 (Projections + backtesting flow)
- **Checkpoint:** Projection accuracy \<20% MAE validated, backtesting flow sends Discord alerts on schedule

**Weeks 4-5: Advanced Analytics (Epics 3-4)**

- Week 4: Epic 3 (Cap space modeling as Prefect tasks)
- Week 5: Epic 4 (Dynasty value composite with dependencies orchestrated)
- **Checkpoint:** Dynasty value scores diverge from KTC (10+ arbitrage opportunities identified)

**Weeks 5.5-6.5: Integration & Validation (Epic 5)**

- Week 5.5-6: Integration testing, dbt source tables, analytics pipeline flow
- Week 6.5: Notebook validation, documentation, performance optimization
- **Checkpoint:** End-to-end Prefect flow demonstration (analytics → Parquet → dbt marts → notebooks)

**Aggressive Path (5 weeks):**

- Parallel development (VoR + Projections concurrently in Weeks 2-3)
- Reduce testing/documentation time (ship MVP, iterate)
- User (Jason) performs UAT during Week 5 (early feedback loop)
- Prefect foundation completed in 1.5 days instead of 2 (fast-track)

______________________________________________________________________

## Appendix A: Glossary

**VoR (Value over Replacement):** Fantasy points above replacement-level baseline for a position. Example: RB24 is replacement level in 12-team league with 2 RB slots; any RB scoring above RB24 has positive VoR.

**WAR (Wins Above Replacement):** Expected wins added vs replacement player. Adapted from baseball/NFL analytics to fantasy football context.

**Dynasty Value Score:** Composite metric integrating 6 dimensions: VoR (baseline value), economics (contract efficiency), age (career trajectory), scarcity (positional value), variance (floor/ceiling), market (KTC consensus).

**KTC (KeepTradeCut):** Crowdsourced dynasty trade value platform providing consensus player valuations.

**Aging Curve:** Position-specific performance trajectory over player's career. RB peaks Year 3-4, cliff at Year 7; WR peaks Year 5-7, gradual decline to Year 10+.

**Pro-Rating:** Salary cap technique spreading contract value unevenly across years (front-loading or back-loading) subject to 150% geometric constraints per league rules.

**Dead Cap:** Salary cap obligation from cutting a player before contract expires. League uses 50%/50%/25%/25%/25% schedule (Year 1-5 obligations).

**FASA (Free Agent Silent Auction):** Weekly sealed bid auction for free agents during NFL season. Winning bid = highest total dollars, tie-breaker = fewest years.

**Backtesting:** Validation technique using historical data. Example: 2020 projections → compare to 2021 actuals → measure accuracy (MAE, RMSE).

**Time-Series Cross-Validation:** Validation method respecting temporal ordering (train on past, test on future). Prevents data leakage vs standard cross-validation with shuffle.

______________________________________________________________________

## Appendix B: Research References

This PRD synthesizes findings from:

1. **research-domain-2025-11-18.md** - Domain landscape, VoR/WAR frameworks, ML applications, analytical best practices
2. **research-contract-economics-2025-11-18.md** - League salary cap mechanics, contract structures, dead cap rules
3. **research-competitive-window-2025-11-18.md** - Franchise assessment, competitive timeline, feature priorities
4. **data-gap-assessment-competitive-window-2025-11-18.md** - Data availability, missing injury/standings data
5. **research-validation-complete-2025-11-18.md** - Research completeness verification

Additional resources:

- **docs/analytics_references/** - Dynasty strategy frameworks, valuation methodologies, academic research
- **Advanced Dynasty Fantasy Football Modeling: Player Valuation and Trade Optimization.pdf** - Academic research paper on multi-objective optimization

______________________________________________________________________

## Document Control

**Version:** 1.0 (Draft)
**Last Updated:** 2025-11-18
**Next Review:** Weekly during implementation
**Approval Required:** Jason (Product Manager / User)
**Distribution:** Internal (Jason only)

**Change Log:**

- 2025-11-18: Initial draft (PM agent via BMad Method PRD workflow)
