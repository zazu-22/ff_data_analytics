# Ticket P1-028: Add DST Team Defense Seed for FFAnalytics Mapping

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

### Phase 1: Create DST Seed CSV

- [ ] Create `dbt/ff_data_transform/seeds/seed_team_defense_xref.csv`
- [ ] Include columns:
  - [ ] `defense_id` (sequential 10001-10032 for 32 NFL teams, avoiding player_id collision)
  - [ ] `team_abbrev` (canonical 3-letter code: ARI, ATL, BAL, etc.)
  - [ ] `team_name_primary` (e.g., "Arizona Cardinals")
  - [ ] `team_name_alias_1` (e.g., "Cardinals, Arizona")
  - [ ] `team_name_alias_2` (e.g., "Cardinals")
  - [ ] `position_primary` (always "DST")
  - [ ] `position_alias_1` (e.g., "D")
  - [ ] `position_alias_2` (e.g., "D/ST")
  - [ ] `position_alias_3` (e.g., "DEF")
- [ ] Populate all 32 NFL teams with common name variations
- [ ] Use same team abbreviations as `dim_franchise` for consistency

### Phase 2: Create dbt Model

- [ ] Create `dbt/ff_data_transform/models/core/dim_team_defense_xref.sql`
- [ ] Model references seed: `SELECT * FROM {{ ref('seed_team_defense_xref') }}`
- [ ] Add any transformations needed (e.g., computed columns, normalization)
- [ ] Configure as table materialization
- [ ] Create YAML schema file `_dim_team_defense_xref.yml`:
  - [ ] Document grain: one row per team defense
  - [ ] Add unique test on `defense_id`
  - [ ] Add not_null tests on key columns
  - [ ] Document all columns

### Phase 3: Update Python Utility Function

- [ ] Add `get_defense_xref()` function to `src/ff_analytics_utils/` (or appropriate module)
- [ ] Query DuckDB for `dim_team_defense_xref` model
- [ ] Return as polars/pandas DataFrame
- [ ] Mirror pattern from existing `get_player_xref()` function

### Phase 4: Update Python Loader

- [ ] Modify `src/ingest/ffanalytics/loader.py`:
  - [ ] Add `_defense_xref_csv` context manager (mirrors `_player_xref_csv` pattern)
  - [ ] Materializes temp CSV from `get_defense_xref()` query
  - [ ] Update `load_projections()` to pass defense xref temp file to R runner
  - [ ] Add `--defense_xref` parameter to R subprocess call

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

**Architecture: Seed → Model → Python → R**

This follows the same pattern as `dim_player_id_xref`:

1. **CSV seed** (`seed_team_defense_xref.csv`) - Version-controlled source of truth
2. **dbt model** (`dim_team_defense_xref`) - References seed, applies transformations
3. **Python utility** (`get_defense_xref()`) - Queries DuckDB model, returns DataFrame
4. **Python loader** (`_defense_xref_csv` context manager) - Materializes temp CSV for R
5. **R runner** - Receives temp CSV path, loads defense mapping

**Benefits**:

- No downstream dependencies on raw CSV files
- Seed CSV is manually maintained (appropriate for slowly changing dimension)
- dbt model can apply transformations, add computed columns
- Python layer provides abstraction and temp file management
- R runner receives data via standard CSV interface

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
