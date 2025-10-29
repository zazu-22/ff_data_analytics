# Phase 1: IDP Data Flow Investigation - Findings Report

**Date**: 2025-10-29
**Investigator**: Claude Code
**Sprint**: IDP & DST Data Capability Assessment

______________________________________________________________________

## Executive Summary

**CRITICAL FINDING**: IDP projection data EXISTS in raw ingestion but is **completely filtered out** in the dbt staging layer, preventing it from reaching analytics marts and notebooks.

- ✅ **Raw Layer**: 5,839 IDP player records with 8 stat categories
- ❌ **Staging Layer**: ALL IDP players filtered out (`player_id = -1` exclusion)
- ❌ **Marts**: Zero actual IDP projections (35 false positives from name collisions)
- ❌ **FASA Notebook**: Only handles offensive positions (RB, WR, TE, QB)

**Root Cause**: `stg_ffanalytics__projections.sql` line 68 filters `WHERE player_id > 0`, excluding all unmapped IDP players.

______________________________________________________________________

## Detailed Findings by Layer

### 1. Raw Data Layer (`data/raw/ffanalytics/projections/`)

**Status**: ✅ **IDP DATA EXISTS AND IS COMPREHENSIVE**

**Latest Snapshot**: `dt=2025-10-28`

**IDP Player Counts:**

- **DB (Defensive Back)**: 2,381 players
- **DL (Defensive Line)**: 2,177 players
- **LB (Linebacker)**: 1,281 players
- **Total IDP**: 5,839 players

**IDP Stat Categories** (8 columns, all present):

1. `idp_solo` - Solo tackles (99.4% coverage)
2. `idp_asst` - Assisted tackles (99.2% coverage)
3. `idp_sacks` - Sacks (49.3% coverage)
4. `idp_pd` - Passes defended (73.6% coverage)
5. `idp_int` - Interceptions (24.3% coverage)
6. `idp_fum_force` - Forced fumbles (26.8% coverage)
7. `idp_fum_rec` - Fumble recoveries (6.7% coverage)
8. `idp_td` - Defensive touchdowns (3.8% coverage)

**Data Source**: FantasySharks (only 1 of 9 configured sources providing IDP)

**Sample IDP Projections (Week 10)**:

```text
Player               | Pos | Solo | Asst | Sacks | PD  | INT
---------------------|-----|------|------|-------|-----|-----
Brooks, Jordyn       | LB  | 6.7  | 4.1  | 0.3   | 0.1 | 0.0
Wagner, Bobby        | LB  | 5.1  | 4.8  | 0.2   | 0.1 | 0.1
Oluokun, Foyesade    | LB  | 5.5  | 4.1  | 0.1   | 0.4 | 0.1
```

**Player ID Mapping Issue**:

- **28.9% mapping rate** (1,686 of 5,839 players)
- **71.1% unmapped** (`player_id = -1`)
- Unmapped players include top IDP performers (Jordyn Brooks, Bobby Wagner, etc.)

______________________________________________________________________

### 2. Staging Layer (`dbt/ff_analytics/models/staging/`)

**Status**: ❌ **ALL IDP DATA FILTERED OUT**

**File**: `stg_ffanalytics__projections.sql`

**Blocking Issues**:

#### Issue 1: Player ID Filter (Line 68)

```sql
where cast(player_id as integer) > 0
```

- **Impact**: Excludes ALL unmapped players (`player_id = -1`)
- **Result**: 71.1% of IDP players (4,153 of 5,839) immediately discarded
- **Rationale**: Comment says "Filter out unmapped players for now"

#### Issue 2: Column Selection (Lines 40-59)

```sql
-- Only offensive stats selected:
pass_comp, pass_att, pass_yds, pass_tds, pass_int  -- Passing
rush_att, rush_yds, rush_tds                        -- Rushing
rec, rec_yds, rec_tds                               -- Receiving
fumbles_lost                                        -- Turnovers

-- IDP columns NOT selected (missing):
-- idp_solo, idp_asst, idp_sacks, idp_pd, idp_int,
-- idp_fum_force, idp_fum_rec, idp_td
```

- **Impact**: Even if player_id filter removed, IDP stats wouldn't flow through
- **Result**: Model designed exclusively for offensive players

#### Issue 3: No Separate IDP Staging Model

- Searched for: `*idp*.sql`, `*defense*.sql`
- **Result**: No dedicated IDP staging model exists

**Query Result**: Zero IDP rows in `stg_ffanalytics__projections`

______________________________________________________________________

### 3. Marts Layer (`dbt/ff_analytics/models/marts/`)

**Status**: ❌ **NO ACTUAL IDP DATA (FALSE POSITIVES ONLY)**

**File**: `mart_fantasy_projections.sql`

**Position Distribution**:

```text
Position | Count | Notes
---------|-------|------------------------------------------------
QB       | 633   | ✅ Offensive players
RB       | 1,131 | ✅ Offensive players
WR       | 1,630 | ✅ Offensive players
TE       | 907   | ✅ Offensive players
CB       | 27    | ❌ FALSE POSITIVE (name collisions)
DT       | 8     | ❌ FALSE POSITIVE (name collisions)
---------|-------|------------------------------------------------
Total    | 4,336 |
```

**False Positive Examples**:

```text
Reported Position | Player Name    | Actual Data         | True Identity
------------------|----------------|---------------------|----------------
CB                | Lamar Jackson  | 242 pass yds, 54 rush yds | QB Lamar Jackson
CB                | DJ Turner      | 20.6 rec yds        | WR DJ Turner
DT                | Kyle Williams  | 8.1 rec yds         | WR Kyle Williams
```

**Analysis**:

- The 35 "IDP" records are offensive players misidentified due to name conflicts
- They have offensive stats (passing, rushing, receiving yards)
- True IDP stats (tackles, sacks, INTs) absent
- **Conclusion**: ZERO actual IDP projections in marts

**Documentation Issue** (Line 13):

```sql
/*
League scoring: Half-PPR (no IDP in projections)
*/
```

- Comment is **INCORRECT** about raw data availability
- Comment is **CORRECT** about mart availability (due to staging filter)

______________________________________________________________________

### 4. Notebook Layer (`notebooks/fasa_weekly_strategy.ipynb`)

**Status**: ❌ **NO IDP SUPPORT DESIGNED**

**Position Handling**:

```python
rb_targets = fasa_targets[fasa_targets['position'] == 'RB']
wr_targets = fasa_targets[fasa_targets['position'] == 'WR']
te_targets = fasa_targets[fasa_targets['position'] == 'TE']
```

**IDP References**: None found

**Design**: Notebook exclusively handles offensive players (RB, WR, TE, QB)

**Rationale**: Consistent with marts having no IDP data

______________________________________________________________________

## Data Flow Diagram

```text
┌─────────────────────────────────────────────────────────────┐
│ RAW LAYER: data/raw/ffanalytics/projections/               │
│ ✅ 5,839 IDP players | 8 IDP stat columns                  │
│ Source: FantasySharks                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
           ┌─────────────────────────────┐
           │ STAGING FILTER (Line 68)    │
           │ WHERE player_id > 0         │
           │                             │
           │ ❌ Blocks 4,153 unmapped IDP │
           │    (71.1% of all IDP)       │
           └─────────────┬───────────────┘
                         │
                         ▼
           ┌─────────────────────────────┐
           │ COLUMN SELECTION            │
           │ (Lines 40-59)               │
           │                             │
           │ ❌ No IDP columns selected   │
           │    Only offensive stats     │
           └─────────────┬───────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGING: stg_ffanalytics__projections                       │
│ ❌ 0 IDP players                                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ MARTS: mart_fantasy_projections                             │
│ ❌ 0 actual IDP players (35 false positives from name dupes)│
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ NOTEBOOKS: fasa_weekly_strategy.ipynb                       │
│ ❌ Only handles RB, WR, TE, QB                              │
└─────────────────────────────────────────────────────────────┘
```

______________________________________________________________________

## Root Cause Analysis

### Primary Root Cause

**Unmapped Player Filter**: `WHERE player_id > 0` in staging SQL

**Contributing Factors**:

1. **Low IDP Mapping Rate**: Only 28.9% of IDP players successfully mapped to `mfl_id`
2. **Missing IDP Crosswalk Data**: `dim_player_id_xref` lacks most defensive players
3. **Design Decision**: Intentional filter to exclude unmapped players (comment: "for now")

### Secondary Issues

1. **No IDP Column Selection**: Staging model designed for offensive stats only
2. **No Separate IDP Model**: No alternative pathway for IDP data
3. **Outdated Documentation**: Mart comments misleading about data availability

______________________________________________________________________

## Impact Assessment

### Current State

- **IDP Projections**: NOT available in analytics layer
- **IDP Historical Stats**: Unknown (Phase 3 investigation)
- **Fantasy Scoring**: IDP players cannot be scored or analyzed
- **FASA Strategy**: Cannot bid on defensive players
- **Trade Analysis**: Cannot value IDP players using projections

### Downstream Effects

1. **Incomplete Fantasy Analysis**: Missing ~15-20% of fantasy-relevant players
2. **Roster Construction**: Cannot optimize IDP lineup decisions
3. **Dynasty Valuation**: IDP player values based solely on KTC market data, not projections
4. **Weekly Strategy**: FASA notebook excludes defensive free agents

______________________________________________________________________

## Comparison to Initial Research

**Research Claim** (from subagent investigation):

> "IDP projections ARE supported and ARE working in production"
> "5,839 IDP records in latest production data"

**Reality**:

- ✅ Correct about raw data (5,839 IDP records exist)
- ❌ Incorrect about production availability (filtered out before marts)
- ❌ Incorrect about "working" status (blocked at staging layer)

**Why Research Was Misled**:

- Subagent only examined raw Parquet files, not dbt transformations
- Didn't trace data flow through staging → marts → notebooks
- Didn't query actual mart tables to verify accessibility

______________________________________________________________________

## Recommendations (Phase 2 Scope)

### Immediate Fixes (High Priority)

1. **Remove Player ID Filter**: Allow unmapped IDP players through staging
2. **Add IDP Columns**: Select all 8 IDP stat columns in staging model
3. **Fix Documentation**: Update mart comments to reflect actual data state
4. **Add Player ID Fallback**: Use `player_key` pattern for unmapped players

### Medium-Term Improvements

1. **Improve ID Mapping**: Add defensive players to `dim_player_id_xref` (Phase 2.1)
2. **Source Investigation**: Determine why ESPN/FantasyPros lack IDP (Phase 2.2)
3. **Data Quality Monitoring**: Alert if FantasySharks (only source) fails (Phase 2.3)

### Long-Term Enhancements

1. **Extend FASA Notebook**: Add IDP position analysis (DB, DL, LB)
2. **IDP Scoring Rules**: Add IDP stat scoring to `dim_scoring_rule`
3. **Historical IDP Stats**: Integrate nflverse defensive stats (Phase 3)

______________________________________________________________________

## Appendix: Key File References

### dbt Models

- **Source Definition**: `dbt/ff_analytics/models/sources/src_ffanalytics.yml`
- **Staging Model**: `dbt/ff_analytics/models/staging/stg_ffanalytics__projections.sql` (blocking filter at line 68)
- **Mart Model**: `dbt/ff_analytics/models/marts/mart_fantasy_projections.sql` (incorrect comment at line 13)

### Python Ingestion

- **Loader**: `src/ingest/ffanalytics/loader.py` (DEFAULT_POSITIONS includes IDP)
- **R Script**: `scripts/R/ffanalytics_run.R` (default positions include DL,LB,DB)

### Notebooks

- **FASA Strategy**: `notebooks/fasa_weekly_strategy.ipynb` (RB, WR, TE only)

### Data Paths

- **Raw Data**: `data/raw/ffanalytics/projections/dt=2025-10-28/projections_consensus_2025-10-28.parquet`
- **DuckDB**: `dbt/ff_analytics/target/dev.duckdb`
- **Marts**: `main.mart_fantasy_projections` table

______________________________________________________________________

## Next Steps (Phase 2)

1. ✅ **Fix staging filter** to allow IDP players
2. ✅ **Add IDP columns** to staging select statement
3. ✅ **Update documentation** to correct misleading comments
4. ⏳ **Improve player ID mapping** (separate investigation)
5. ⏳ **Source coverage analysis** (why only FantasySharks has IDP?)
6. ⏳ **Add monitoring** (data quality tests for IDP)

**Phase 1 Status**: ✅ **COMPLETE**
**Phase 2 Status**: ⏳ **READY TO BEGIN**

______________________________________________________________________

**Document Version**: 1.0
**Last Updated**: 2025-10-29
**Location**: `/Users/jason/code/ff_analytics/docs/findings/PHASE_1_IDP_DATA_FLOW_INVESTIGATION.md`
