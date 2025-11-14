# Ticket P1-028: Add DST Team Defense Seed for FFAnalytics Mapping

**Status**: IN PROGRESS (Phases 1-4 complete, Phase 5 pending)
**Phase**: Tech Debt
**Estimated Effort**: Small (2-3 hours)
**Dependencies**: P1-018 (FFAnalytics source duplicates fix)
**Priority**: MEDIUM - Improves FFAnalytics mapping coverage from ~89% to ~98%

## Objective

Create a manually maintained dbt seed CSV for NFL team defenses (DST) with position aliases to improve FFAnalytics projection mapping coverage.

## Context

After fixing P1-018 (name normalization issues), ~90 of 138 unmapped FFAnalytics projections remain unmapped because **defense/special teams entities are not in dim_player_id_xref**.

**Current mapping coverage**: ~89% (138/1291 unmapped)
**Target after DST seed**: ~98% (10-15 unmapped - deep roster only)

**Root causes for DST unmapping:**

1. NFLverse `ff_playerids` (source of dim_player_id_xref) only includes individual players
2. DST projections use various position formats: "D", "DST", "D/ST", "DEF"
3. Team names have variations: "49ers, San Francisco" vs "San Francisco 49ers"

**Example unmapped DST entries:**

```
49ers, San Francisco       pos=D
Bills, Buffalo             pos=DST
Chiefs, Kansas City        pos=D
Ravens, Baltimore          pos=DST
```

## Tasks

### Phase 1: Create DST Seed CSV ✅ COMPLETE

- [x] Create `dbt/ff_data_transform/seeds/seed_team_defense_xref.csv`
- [x] Include columns:
  - [x] `defense_id` (90001-90036 for 36 teams - 32 current + 4 historical)
  - [x] `team_abbrev` (canonical 3-letter code: ARI, ATL, BAL, etc.)
  - [x] `team_name_primary` (e.g., "Arizona Cardinals")
  - [x] `team_name_alias_1` (e.g., "Cardinals, Arizona")
  - [x] `team_name_alias_2` (e.g., "Cardinals")
  - [x] `team_name_alias_3` (e.g., "Arizona")
  - [x] `team_name_alias_4` (e.g., "Cardinals D/ST")
  - [x] `position_primary` (always "DST")
  - [x] `position_alias_1` (e.g., "D")
  - [x] `position_alias_2` (e.g., "D/ST")
  - [x] `position_alias_3` (e.g., "DEF")
- [x] Populate all 36 teams (32 current + 4 historical: LA, OAK, SD, STL)
- [x] Use consistent team abbreviations with dim_team_conference_division

### Phase 2: Create dbt Model ✅ COMPLETE

- [x] Create `dbt/ff_data_transform/models/core/dim_team_defense_xref.sql`
- [x] Model references seed: `SELECT * FROM {{ ref('seed_team_defense_xref') }}`
- [x] Configure as table materialization with unique_key
- [x] Create YAML schema file `_dim_team_defense_xref.yml`:
  - [x] Document grain: one row per team defense (36 total)
  - [x] Add unique test on `defense_id`
  - [x] Add not_null tests on key columns
  - [x] Document all columns with 90K range rationale
  - [x] Add range validation test (90001-90036)
  - [x] Add accepted_values test for team_abbrev
- [x] All 9 tests passing

### Phase 3: Update Python Utility Function ✅ COMPLETE

- [x] Create `src/ff_analytics_utils/defense_xref.py` with `get_defense_xref()` function
- [x] Implement **DuckDB-first with CSV fallback** pattern (consistent with `get_player_xref()`)
  - [x] Default to `source='auto'` (try DuckDB, fall back to CSV)
  - [x] DuckDB path: Query `main.dim_team_defense_xref` table
  - [x] CSV fallback: Read `dbt/ff_data_transform/seeds/seed_team_defense_xref.csv`
  - [x] Support optional `columns` parameter for selective loading
- [x] Return as Polars DataFrame
- [x] Add comprehensive docstring with examples
- [x] Include error handling with clear messages
- [x] Add to `ff_analytics_utils.__init__` exports
- [x] Tested: successfully loads 36 teams from DuckDB

### Phase 4: Update Python Loader ✅ COMPLETE

- [x] Modify `src/ingest/ffanalytics/loader.py`:
  - [x] Add `_defense_xref_csv` context manager (mirrors `_player_xref_csv` pattern)
  - [x] Materializes temp CSV from `get_defense_xref()` query
  - [x] Update `load_projections()` to pass defense xref temp file to R runner
  - [x] Update `load_projections_multi_week()` to pass defense_xref
  - [x] Update `load_projections_ros()` to pass defense_xref
  - [x] Update `_scrape_week_projections()` helper function
  - [x] Add `--defense_xref` parameter to R subprocess call
  - [x] Add `defense_xref` parameter to all function signatures
  - [x] Update all docstrings

### Phase 5: Update R Runner to Use DST Table

- [ ] Modify `scripts/R/ffanalytics_run.R`:
  - [ ] Add CLI parameter `--defense_xref` (receives temp CSV path from Python)
  - [ ] Load defense xref CSV (lines ~467-479, similar to player_xref loading)
  - [ ] Update player mapping logic (lines 467-639) to handle DST:
    - [ ] After individual player matching, attempt DST team matching
    - [ ] Normalize team names using existing `normalize_team_abbrev` function
    - [ ] Match against all position aliases (D, DST, D/ST, DEF)
    - [ ] Match against all team name aliases
    - [ ] Assign `player_id = defense_id` for mapped DST
    - [ ] Retain `player_id = -1` for unmapped DST (log as warning)
  - [ ] Update metadata to separately track DST mapping stats

### Phase 4: Validation

- [ ] Run `just dbt-seed` to load new DST seed
- [ ] Verify seed loaded: `SELECT * FROM dim_team_defense_xref LIMIT 5`
- [ ] Re-run FFAnalytics ingestion: `just ingest-ffanalytics`
- [ ] Check unmapped count in metadata (expect ~10-15, down from ~90)
- [ ] Verify DST projections have valid `player_id` values
- [ ] Query staging model to confirm DST records are no longer filtered out
- [ ] Test downstream marts include DST projections

### Phase 5: Documentation

- [ ] Update `dbt/ff_data_transform/seeds/README.md` with DST seed documentation
- [ ] Document CSV columns and maintenance process
- [ ] Add note about keeping seed in sync with NFL team changes (relocations, etc.)
- [ ] Update `scripts/R/CLAUDE.md` with DST mapping logic
- [ ] Update this ticket with completion notes

## Acceptance Criteria

- [ ] `dim_team_defense_xref.csv` seed created with all 32 teams
- [ ] Seed includes 3+ name aliases and 4 position aliases per team
- [ ] R runner successfully loads and uses DST seed
- [ ] FFAnalytics mapping coverage improves to ~98% (unmapped ~10-15)
- [ ] DST projections have valid `player_id` values (not -1)
- [ ] Staging model includes DST records (no longer filtered by `player_id > 0` condition)
- [ ] Documentation updated

## Implementation Notes

### Architecture: Seed → Model → Python → R

This follows the same pattern as `dim_name_alias` and `dim_player_id_xref`:

1. **CSV seed** (`seed_team_defense_xref.csv`) - Version-controlled source of truth
2. **dbt model** (`dim_team_defense_xref`) - References seed, applies transformations
3. **Python utility** (`get_defense_xref()`) - **DuckDB-first with CSV fallback**
4. **Python loader** (`_defense_xref_csv` context manager) - Materializes temp CSV for R
5. **R runner** - Receives temp CSV path, loads defense mapping

### DuckDB-First with CSV Fallback Pattern

**Why this pattern?**

- **Performance**: DuckDB queries are faster than CSV parsing (~9,000 projections processed)
- **Consistency**: All code uses same dbt-transformed data
- **Robustness**: CSV fallback ensures first-run works without `dbt seed`
- **No hard dependency**: Ingestion layer can operate independently

**Access Pattern**:

```python
# Default: Try DuckDB first, fall back to CSV
defense_xref = get_defense_xref()  # source='auto'

# Force CSV (for testing or first run)
defense_xref = get_defense_xref(source='csv')

# Force DuckDB (fails if table doesn't exist)
defense_xref = get_defense_xref(source='duckdb')
```

**Bootstrap Process**:

1. First run: `make ingest-ffanalytics` uses CSV fallback (slower but works)
2. Then: `dbt seed --select seed_team_defense_xref` materializes CSV into DuckDB
3. Subsequent runs: Use DuckDB (faster)

**Benefits**:

- CSV seed is single source of truth (no duplication)
- dbt seed materializes it into DuckDB for performance
- Python utility queries DuckDB (fast) with CSV fallback (robust)
- No hard circular dependency, just optimization
- Consistent with existing `get_name_alias()` and `get_player_xref()` patterns

**DST player_id assignment strategy:**

- Use sequential IDs starting at 10000 to avoid collision with player IDs (1-N)
- Example: Cardinals = 10001, Falcons = 10002, Ravens = 10003, etc.
- Or: Use negative IDs (-1 to -32) to clearly distinguish from players

**Team name normalization:**

- Leverage existing `normalize_team_abbrev` function in R runner
- Handle both "City Team" and "Team, City" formats
- Strip common suffixes like "Football Team", "Football Club"

**Position alias handling:**

- Normalize all position values to "DST" in staging model
- Match against any alias (D, DST, D/ST, DEF) during R runner mapping

## Example CSV Structure

```csv
defense_id,team_abbrev,team_name_primary,team_name_alias_1,team_name_alias_2,position_primary,position_alias_1,position_alias_2,position_alias_3
10001,ARI,Arizona Cardinals,Cardinals Arizona,Cardinals,DST,D,D/ST,DEF
10002,ATL,Atlanta Falcons,Falcons Atlanta,Falcons,DST,D,D/ST,DEF
10003,BAL,Baltimore Ravens,Ravens Baltimore,Ravens,DST,D,D/ST,DEF
10004,BUF,Buffalo Bills,Bills Buffalo,Bills,DST,D,D/ST,DEF
...
```

## Testing

**Before DST seed:**

```sql
-- Check unmapped DST projections
SELECT pos, COUNT(*)
FROM read_parquet('data/raw/ffanalytics/projections/dt=*/projections_consensus_*.parquet')
WHERE player_id = -1 AND pos IN ('D', 'DST', 'D/ST', 'DEF')
GROUP BY pos;
-- Expected: ~90 rows
```

**After DST seed:**

```sql
-- Verify DST mapping
SELECT pos, COUNT(*) as mapped_count
FROM read_parquet('data/raw/ffanalytics/projections/dt=*/projections_consensus_*.parquet')
WHERE pos IN ('D', 'DST', 'D/ST', 'DEF') AND player_id > 0
GROUP BY pos;
-- Expected: ~90 rows with valid player_id

-- Check remaining unmapped
SELECT player, pos
FROM read_parquet('data/raw/ffanalytics/projections/dt=*/projections_consensus_*.parquet')
WHERE player_id = -1
ORDER BY pos, player;
-- Expected: ~10-15 deep roster players only
```

## Related Issues

- **P1-018**: Fixed name normalization (periods, suffixes) - reduced unmapped from 138 to ~90
- **ADR-011**: Sequential surrogate key architecture for player_id

## References

- FFAnalytics R runner: `scripts/R/ffanalytics_run.R`
- Python loader: `src/ingest/ffanalytics/loader.py`
- Player xref: `dbt/ff_data_transform/models/core/dim_player_id_xref.sql`
- Staging model: `dbt/ff_data_transform/models/staging/stg_ffanalytics__projections.sql`

______________________________________________________________________

## Completion Notes

### Session 1: 2025-11-13 (Phases 1-4)

**Status**: Phases 1-4 COMPLETE, Phases 5-7 PENDING

**Implemented**: 2025-11-13
**Commit**: `752ed21` - feat(snapshot): implement P1-028 phases 1-4 - DST defense seed and Python integration

#### Accomplishments

**Phase 1: DST Seed CSV** ✅

- Created `seed_team_defense_xref.csv` with 36 teams (32 current + 4 historical)
- **Defense ID Range Decision**: Changed from 10,001-10,032 to **90,001-90,036**
  - **Rationale**: Current player IDs at 9,757, max NFL history ~28K players
  - **Buffer**: ~80,000 IDs between max expected players and min defense IDs
  - **Benefits**: Clear separation in sort order, no collision risk, future extensibility
- 5 name aliases per team: full name, reversed, nickname, city, with D/ST suffix
- 4 position aliases: DST, D, D/ST, DEF
- Historical teams: LA (pre-STL Rams), OAK (pre-LV Raiders), SD (pre-LAC Chargers), STL (pre-LA Rams)

**Phase 2: dbt Model & Schema** ✅

- Created `dim_team_defense_xref.sql` model (table materialization)
- Created `_dim_team_defense_xref.yml` with comprehensive documentation
- **90K Range Rationale Documented**: Clear explanation of defense_id strategy in YAML
- All 9 tests passing:
  - Uniqueness on defense_id
  - Not null on key columns
  - Accepted values for team_abbrev (quoted 'NO' to avoid YAML boolean issue)
  - Range validation (90001-90036)
  - Position validation (DST only)
- Seed and model built successfully in DuckDB

**Phase 3: Python Utility Function** ✅

- Created `src/ff_analytics_utils/defense_xref.py` (122 lines)
- Implemented DuckDB-first + CSV fallback pattern (consistent with `get_player_xref()`)
- Added to `ff_analytics_utils` exports
- Tested: successfully loads 36 teams from DuckDB

**Phase 4: Python Loader Integration** ✅

- Added `_defense_xref_csv()` context manager to `loader.py`
- Updated all 4 projection loading functions:
  - `load_projections()` - base single-week loader
  - `_scrape_week_projections()` - internal helper
  - `load_projections_multi_week()` - multi-week batch loader
  - `load_projections_ros()` - production ROS loader
- Nested context managers pass both `player_xref` AND `defense_xref` to R subprocess
- All function signatures and docstrings updated
- **No Breaking Changes**: R script will receive `--defense_xref` parameter but can safely ignore it until Phase 5

#### Files Changed (6 files, +463/-4 lines)

1. `dbt/ff_data_transform/seeds/seed_team_defense_xref.csv` (NEW - 37 lines)
2. `dbt/ff_data_transform/models/core/dim_team_defense_xref.sql` (NEW - 43 lines)
3. `dbt/ff_data_transform/models/core/_dim_team_defense_xref.yml` (NEW - 284 lines)
4. `src/ff_analytics_utils/defense_xref.py` (NEW - 122 lines)
5. `src/ff_analytics_utils/__init__.py` (MODIFIED - added export)
6. `src/ingest/ffanalytics/loader.py` (MODIFIED - +40 lines)

#### Testing Performed

- ✅ dbt seed loaded: 36 teams
- ✅ dbt model built: all tests passing
- ✅ Python utility: successfully queries DuckDB and loads 36 teams
- ✅ All pre-commit hooks passing (ruff, mypy, sqlfmt, sqlfluff, dbt-compile, dbt-opiner)

______________________________________________________________________

### Next Session: Phase 5-7 (R Integration + Validation)

**Remaining Work**:

#### Phase 5: Update R Runner (Estimated: 2-3 hours)

**File**: `scripts/R/ffanalytics_run.R`

**Tasks**:

1. Add CLI parameter `--defense_xref` (receives temp CSV path from Python)
2. Load defense xref CSV (lines ~467-479, similar to existing player_xref loading pattern)
3. **Update player mapping logic** (lines 467-639) to handle DST:
   - After individual player matching, attempt DST team matching
   - Normalize team names using existing `normalize_team_abbrev()` function
   - Match against all position aliases (D, DST, D/ST, DEF)
   - Match against all team name aliases (5 variations)
   - Assign `player_id = defense_id` (90001-90036) for matched DST
   - Retain `player_id = -1` for unmapped DST (log as warning)
4. Update metadata to separately track DST mapping stats (success vs. unmapped)

**Key Implementation Notes**:

- R script already has `normalize_team_abbrev()` function with team_alias_map
- Can reuse existing player_xref loading pattern for defense_xref
- Team name matching logic needs to handle multiple name formats from different FFAnalytics providers
- Position normalization already exists - just need to match DST variations

**Expected Complexity**: Moderate - requires ~100-150 lines of R logic changes

#### Phase 6: Validation Testing (Estimated: 1 hour)

1. Run `just dbt-seed --select seed_team_defense_xref` (already done)
2. Re-run FFAnalytics ingestion with DST support: `just ingest-ffanalytics` or equivalent
3. Verify unmapped count reduction: ~138 → ~10-15 (or ~90 → ~10-15 post-P1-018)
4. Check DST projections have valid `player_id` values (90001-90036, not -1)
5. Query staging model to confirm DST records included
6. Validate downstream marts include DST projections

#### Phase 7: Documentation Updates (Estimated: 30 min)

1. Update `dbt/ff_data_transform/seeds/README.md`:
   - Add DST seed documentation
   - Document columns and maintenance process
   - Note about keeping seed in sync with NFL team changes (relocations)
2. Update `scripts/R/CLAUDE.md`:
   - Document DST mapping logic
   - Explain defense_xref parameter
3. Update ticket tracking:
   - Mark ticket as COMPLETE in 00-OVERVIEW.md
   - Update tasks checklist

**Success Criteria**:

- [ ] R runner accepts `--defense_xref` parameter
- [ ] DST projections mapped to defense_id 90001-90036 (not -1)
- [ ] FFAnalytics mapping coverage improves to ~98% (unmapped ~10-15)
- [ ] All staging/mart tests passing
- [ ] Documentation complete
