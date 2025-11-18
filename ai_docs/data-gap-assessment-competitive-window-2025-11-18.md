# Data Gap Assessment: Competitive Window Analysis

**Date:** 2025-11-18
**Purpose:** Assess data availability for real-time competitive assessment
**Trigger:** Competitive Window research identified missing injury status, league record, and game results data

______________________________________________________________________

## Executive Summary

**Finding:** We have MORE data than initially thought, but it's not yet modeled in dbt.

**ACTUAL USER DATA (Provided 2025-11-18):**

- **Record:** 5-6 (validates "Transition/Contender" window)
- **Injuries:** Stroud (QB), Nabers (WR), Brooks (RB), Ekeler (RB), Dike - IR/multi-week out
- **Source:** User-provided (also available in Sleeper + Google Sheets but not modeled in dbt)

**Status:**

- ✅ **League Record/Standings** - Data exists in raw Sleeper files (NOT YET MODELED) - **USER CONFIRMED: 5-6 record**
- ⚠️ **Injury Status** - Available via Sleeper API + Google Sheets (NOT YET INGESTED) - **USER CONFIRMED: 5 players out**
- ❌ **Matchup/Game Results** - NOT YET IMPLEMENTED
- ❌ **Division Record** - Partial (need matchup data for full picture)

**Impact:** Competitive Window analysis **VALIDATED** with real data. Architecture gaps identified for PRD phase.

**User Request:** Do NOT implement now, but ensure gaps documented for planning phases.

______________________________________________________________________

## Detailed Findings

### 1. League Record & Standings

**Status:** ✅ **DATA EXISTS** (raw Parquet) → ⚠️ **NOT MODELED** (dbt)

**Evidence:**
Raw Sleeper roster Parquet files contain `settings` struct with:

- `wins` (int)
- `losses` (int)
- `ties` (int)
- `fpts` (fantasy points scored)
- `fpts_against` (fantasy points against)
- `fpts_decimal` (fractional points)
- `ppts` (potential points)
- `waiver_position` (waiver order)
- `total_moves` (transaction count)

**Example Data:**

```json
{
  "roster_id": 1,
  "owner_id": "463401851887284224",
  "settings": {
    "wins": 8,
    "losses": 2,
    "fpts": 1649,
    "fpts_against": 1342
  }
}
```

**Gap:** `stg_sleeper__rosters` only extracts player-level data, NOT roster-level settings.

**Solution:**

1. Create new staging model: `stg_sleeper__roster_settings`
2. Extract settings struct from raw Parquet
3. Join to dim_franchise via roster_id → owner_id mapping
4. Create mart: `mrt_league_standings`

**Effort:** 2-4 hours (dbt model + tests)

**Priority:** 🔥 **HIGH** - Critical for competitive assessment

______________________________________________________________________

### 2. Injury Status

**Status:** ⚠️ **AVAILABLE BUT NOT INGESTED**

**Evidence:**
Sleeper API client (`src/ingest/sleeper/client.py:59`) includes `injury_status` field in players endpoint:

```python
def get_players(self) -> pl.DataFrame:
    """Fetch all NFL players (5MB file, cache locally).

    Returns:
        DataFrame with columns:
            - status (Active, Injured Reserve, etc.)
            - injury_status  # ← THIS EXISTS!
    """
```

**Gap:** `get_players()` is called in loader but injury data not tracked in staging models.

**Solution:**

1. Check if `stg_sleeper__players` exists (or create it)
2. Add columns: `status`, `injury_status`, `injury_start_date`, `injury_body_part`, `injury_notes`
3. Create mart: `mrt_player_injury_status` (current injuries by roster)

**Effort:** 1-2 hours (verify existing model or create new)

**Priority:** 🔥 **CRITICAL** - Cannot assess current competitiveness without knowing who's injured

______________________________________________________________________

### 3. Weekly Matchup Results

**Status:** ❌ **NOT IMPLEMENTED**

**Sleeper API Endpoint:** `GET /league/{league_id}/matchups/{week}`

Returns:

- `roster_id`
- `matchup_id` (pairs teams playing each other)
- `points` (fantasy points scored this week)
- `custom_points` (if custom scoring)
- `players_points` (individual player scores)
- `starters_points` (starter scores)

**Gap:** No loader or staging model for matchup data.

**Solution:**

1. Add to `src/ingest/sleeper/client.py`:
   ```python
   def get_matchups(self, league_id: str, week: int) -> pl.DataFrame:
       """Fetch matchups for a given week."""
       url = f"{BASE_URL}/league/{league_id}/matchups/{week}"
       # ...
   ```
2. Create staging model: `stg_sleeper__matchups`
3. Create fact table: `fct_fantasy_matchup_results`

**Effort:** 4-6 hours (client method + loader + dbt models + tests)

**Priority:** 📊 **MEDIUM** - Useful for trend analysis, but roster settings give us W/L already

______________________________________________________________________

### 4. Division/Playoff Picture

**Status:** ❌ **PARTIALLY AVAILABLE**

**What We Have:**

- Division assignment (roster settings has `division` field = 3 for roster_id 1)
- Overall W/L record

**What We Need:**

- Division standings (W/L within division)
- Playoff bracket structure
- Tiebreaker rules (points for? head-to-head?)

**Gap:** Need matchup data to calculate divisional record.

**Solution:**

1. Implement matchup data (see #3)
2. Parse matchup_id to determine opponents
3. Join opponent's division to calculate divisional record
4. Create mart: `mrt_playoff_picture`

**Effort:** 6-8 hours (depends on matchup implementation)

**Priority:** 📊 **MEDIUM** - Nice to have, but overall W/L is sufficient for initial analysis

______________________________________________________________________

## Impact on Competitive Window Analysis

### Current Analysis Limitations

The Competitive Window research (2025-11-18) made these assessments **WITHOUT** real-time data:

1. **"You're competitive but not desperate"** ← ASSUMPTION

   - **Actual:** Could be 8-2 (contending) OR 2-8 (rebuilding)
   - **Impact:** Feature prioritization changes dramatically based on record

2. **"Transition/Contender Window"** ← THEORY

   - **Actual:** Current season performance unknown
   - **Impact:** If 2-8, you're rebuilding NOW, not transitioning

3. **"Roster health unknown"** ← MISSING

   - **Actual:** If Stroud/Achane/Lamb injured, competitive position changes
   - **Impact:** Cannot assess TRUE current strength

### Revised Assessment Needed

**Once data is modeled, re-run analysis with:**

1. Current 2025 season record (wins/losses)
2. Division standing (1st? 4th?)
3. Injury status (who's available?)
4. Recent performance trend (winning streak? losing streak?)

**Example Scenarios:**

**Scenario A: 8-2, 1st in division, healthy roster**
→ Competitive Window = **WIN-NOW** (not transition!)
→ Feature Priority = Weekly lineup optimization + trade analysis (go all-in)

**Scenario B: 2-8, 4th in division, key injuries**
→ Competitive Window = **REBUILD** (not transition!)
→ Feature Priority = Draft analytics + contract efficiency (tank for picks)

**Scenario C: 5-5, 2nd in division, some injuries**
→ Competitive Window = **TRANSITION** (as analyzed)
→ Feature Priority = Multi-year projections + draft analytics (current assessment holds)

______________________________________________________________________

## Recommended Action Plan

### Phase 1: Quick Win (2-4 hours) - IMMEDIATE

**Goal:** Get league standings data into dbt

**Tasks:**

1. Create `stg_sleeper__roster_settings` model

   - Source: `data/raw/sleeper/rosters/dt=*/rosters_*.parquet`
   - Extract: `settings` struct (wins, losses, fpts, etc.)
   - Output: Roster-level standings data

2. Create `mrt_league_standings` mart

   - Join roster_settings → dim_franchise
   - Add calculated fields: win_pct, division_rank, league_rank
   - Add metadata: asof_date (snapshot date)

3. Update Competitive Window research with actual standings

**Deliverable:** Know if you're 8-2 or 2-8 TODAY

______________________________________________________________________

### Phase 2: Injury Tracking (1-2 hours) - HIGH PRIORITY

**Goal:** Track player injury status

**Tasks:**

1. Verify `stg_sleeper__players` exists (or create it)

2. Ensure `status` and `injury_status` fields captured

3. Create `mrt_player_injury_status` mart

   - Current injuries by franchise
   - Injury history (if we keep snapshots)

4. Update Competitive Window research with roster health assessment

**Deliverable:** Know which key players are injured

______________________________________________________________________

### Phase 3: Matchup History (4-6 hours) - MEDIUM PRIORITY

**Goal:** Weekly matchup results and opponent analysis

**Tasks:**

1. Add `get_matchups()` to Sleeper client
2. Create loader: `src/ingest/sleeper/loader.py::load_matchups()`
3. Create staging: `stg_sleeper__matchups`
4. Create fact: `fct_fantasy_matchup_results`

**Deliverable:** Weekly performance trends, strength of schedule analysis

______________________________________________________________________

### Phase 4: Playoff Picture (2-4 hours) - NICE TO HAVE

**Goal:** Division standings and playoff seeding

**Tasks:**

1. Calculate divisional record from matchup data
2. Apply playoff format rules
3. Create `mrt_playoff_picture` mart

**Deliverable:** Playoff probability, magic number, etc.

______________________________________________________________________

## Documentation Updates Required

### 1. Competitive Window Research

**File:** `ai_docs/research-competitive-window-2025-11-18.md`

**Updates:**

- Add "Data Limitations" section at top
- Note that analysis is incomplete without standings data
- Add caveat to all conclusions: "Subject to revision once standings data modeled"

**Section to Add:**

```markdown
## ⚠️ Data Limitations

This analysis was conducted WITHOUT access to:
1. Current 2025 season record (wins/losses/ties)
2. Player injury status
3. Weekly matchup results
4. Division standings

**Impact:** Competitive window classification is THEORETICAL. Once standings data
is modeled, this analysis should be re-run to validate assumptions.

**Status:** See data-gap-assessment-competitive-window-2025-11-18.md for details.
```

### 2. Contract Economics Research

**File:** `ai_docs/research-contract-economics-2025-11-18.md`

**Updates:**

- No changes needed (focused on contract mechanics, not current state)

### 3. Project Documentation Index

**File:** `ai_docs/index.md`

**Updates:**

- Add link to this data gap assessment
- Flag Competitive Window research as "incomplete - pending data modeling"

______________________________________________________________________

## Architecture Gaps for PRD Planning

### Data Modeling Gaps

**Priority 1: Injury Tracking** ⭐⭐⭐⭐⭐ **CRITICAL**

**Why Critical:**

- User has 5 major injuries affecting 2025 season (Stroud, Nabers, Brooks, Ekeler, Dike)
- Cannot build lineup optimization without knowing who's available
- Cannot assess trade targets without injury context
- Cannot evaluate roster health for competitive assessment

**Architecture Needed:**

1. `stg_sleeper__player_injuries` (or add to existing player staging)
   - Fields: player_id, injury_status, injury_body_part, injury_start_date, practice_status
2. `mrt_roster_injury_report` (current injuries by franchise)
   - Current IR players
   - Out/Questionable/Doubtful players
   - Expected return dates (if available)
3. Integration: Weekly lineup optimizer MUST check injury status before recommendations

**Data Source:** Sleeper API players endpoint (already available) + Google Sheets (backup)

______________________________________________________________________

**Priority 2: League Standings** ⭐⭐⭐⭐ **HIGH**

**Why High:**

- User is 5-6 = needs to know playoff picture
- Feature prioritization depends on playoff contention
- Trade decisions require understanding competitive urgency

**Architecture Needed:**

1. `stg_sleeper__roster_settings` (extract settings struct)
2. `mrt_league_standings` (current standings with playoff positioning)
3. `mrt_playoff_picture` (magic number, clinch scenarios, elimination scenarios)

**Data Source:** Raw Sleeper rosters Parquet (settings struct)

______________________________________________________________________

**Priority 3: Weekly Matchup Results** ⭐⭐⭐ **MEDIUM**

**Why Medium:**

- Standings give you W/L, matchups give you context (strength of schedule, points trends)
- Useful for identifying "should have won" games (high points, unlucky opponent)
- Lower priority because standings alone sufficient for immediate needs

**Architecture Needed:**

1. `stg_sleeper__matchups` (weekly matchup data)
2. `fct_fantasy_matchup_results` (game-level results)
3. `mrt_strength_of_schedule` (opponent difficulty analysis)

**Data Source:** Sleeper API matchups endpoint (not yet implemented)

______________________________________________________________________

### Feature Implications

**Weekly Lineup Optimization** (Priority: MEDIUM → HIGH given injuries)

- **Gap:** Cannot optimize lineup without injury status
- **Blocker:** Need injury tracking BEFORE building lineup optimizer
- **Impact:** With 5 injuries, lineup decisions are critical every week

**Trade Analysis** (Priority: HIGH)

- **Gap:** Cannot evaluate "am I buying or selling?" without knowing playoff position
- **Blocker:** Need standings data to determine trade strategy
- **Impact:** At 5-6, every trade decision matters (push for playoffs vs. sell for picks)

**Rookie Draft Analytics** (Priority: CRITICAL - unchanged)

- **Gap:** None - this doesn't require real-time data
- **Impact:** Elite draft capital (26 picks) = highest ROI regardless of current standing

**Multi-Year Cap Projections** (Priority: CRITICAL - unchanged)

- **Gap:** None - contract data already available
- **Impact:** 2027 cap explosion requires planning NOW regardless of 2025 results

______________________________________________________________________

### PRD Implications

When creating the PRD, these architecture gaps should inform:

**1. Data Pipeline Enhancements (Pre-MVP or Phase 1)**

- Injury tracking ingestion (Sleeper API + Sheets fallback)
- Roster settings extraction (dbt model)
- Matchup results loader (future phase)

**2. Feature Dependencies**

```
Weekly Lineup Optimizer
└── REQUIRES: Injury tracking
└── REQUIRES: Roster composition (✅ have)
└── REQUIRES: Projections (✅ have)

Trade Analyzer
└── REQUIRES: League standings
└── REQUIRES: Playoff picture
└── REQUIRES: Draft capital (✅ have)
└── REQUIRES: Contract data (✅ have)

Draft Analytics
└── REQUIRES: Draft pick inventory (✅ have)
└── REQUIRES: Prospect rankings (need to add)
└── REQUIRES: Rookie contract scale (✅ have)
```

**3. MVP Scope Adjustment**

**Original MVP Assumption:** Build features against existing data models

**REALITY CHECK:** Missing critical real-time data (injuries, standings)

**Revised MVP Approach:**

- **Phase 0 (Data Foundation):** Add injury + standings models BEFORE feature development
- **Phase 1 (MVP Features):** Draft analytics + multi-year cap (don't need real-time)
- **Phase 2 (Real-Time Features):** Lineup optimizer + trade analyzer (after Phase 0 data models)

______________________________________________________________________

## Conclusion

**Good News:** The data we need EXISTS in our pipeline (Sleeper API + raw Parquet files)

**Bad News:** It's not yet modeled in dbt, so we can't query it for analysis

**User Validation:** 5-6 record with 5 major injuries CONFIRMS the data gaps are real and impactful

**Action for PRD Phase:**

1. **Document data pipeline requirements** (injury tracking, standings extraction)
2. **Sequence features by data dependencies** (draft analytics first, lineup optimizer after injury tracking)
3. **Consider Phase 0 data foundation** before MVP feature development

**Total Effort:** 7-12 hours to complete full competitive assessment capability

**User Decision:** Defer implementation, but ensure PRD accounts for these gaps in architecture and feature sequencing.

______________________________________________________________________

## Appendix: SQL Queries to Validate Data

### Check Raw Roster Settings Data

```sql
-- Verify settings struct exists in raw Parquet
SELECT
    roster_id,
    owner_id,
    settings.wins,
    settings.losses,
    settings.fpts,
    settings.fpts_against,
    dt
FROM read_parquet('data/raw/sleeper/rosters/dt=*/rosters_*.parquet')
WHERE dt = (SELECT MAX(dt) FROM read_parquet('data/raw/sleeper/rosters/dt=*/rosters_*.parquet'))
ORDER BY settings.wins DESC;
```

### Check If Injury Data Exists

```sql
-- Check if players data has injury fields
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_name LIKE '%sleeper%player%'
  AND (column_name LIKE '%injury%' OR column_name = 'status');
```

______________________________________________________________________

**Next Step:** Create dbt models for roster settings and injury status, then re-run Competitive Window analysis with real data.
