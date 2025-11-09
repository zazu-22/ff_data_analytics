# Ticket P1-018: Fix FFAnalytics Projections Source Data Duplicates

**Phase**: 1 - Foundation\
**Estimated Effort**: Medium (3-5 hours)\
**Dependencies**: P1-016 (to rule out snapshot selection as root cause)\
**Priority**: ⚠️ **MEDIUM** - 17 staging duplicates cascading to 101 fact table duplicates

## Objective

Investigate and fix the root cause of 17 duplicate `(player_id, season, week, horizon, asof_date, provider)` combinations in `stg_ffanalytics__projections`, which persist even after fixing the snapshot selection strategy.

## Context

During P1-016 implementation, we discovered that the snapshot governance fix successfully reduced duplicates from 33→17 (staging) and 162→101 (fact table), but **17 duplicates remain** within the latest snapshot itself. These are **NOT** caused by reading multiple snapshots.

**Evidence of Source Data Quality Issue**:

```sql
-- Same player appears twice with DIFFERENT names and stat values
SELECT player_id, player_name, season, week, horizon, asof_date, provider,
       passing_yards, rushing_yards, receiving_yards
FROM main.stg_ffanalytics__projections
WHERE player_id = 6650 AND season = 2025 AND week = 11 AND horizon = 'weekly'
ORDER BY player_name;

-- Results:
-- player_id | player_name | season | week | horizon | asof_date  | provider              | passing_yards | rushing_yards    | receiving_yards
-- 6650      | DJ Moore    | 2025   | 11   | weekly  | 2025-11-09 | ffanalytics_consensus | NULL          | 6.832259314456   | 48.498062593145
-- 6650      | Moore, D.J. | 2025   | 11   | weekly  | 2025-11-09 | ffanalytics_consensus | NULL          | 6.0              | 57.0
```

**Root Cause Hypothesis**:

The FFAnalytics R runner (`scripts/projections/fetch_ffanalytics_projections.R`) is creating duplicate entries due to **player name matching inconsistencies**:

- Different name formats: "DJ Moore" vs "Moore, D.J."
- Different stat precision: decimal values vs rounded integers
- Same `player_id` (6650) mapped to different name variations

This suggests the R runner is aggregating projections from multiple sources but not properly deduplicating when the same player appears with name variations.

**Affected Players** (from investigation):

- player_id 6650 (DJ Moore/Moore, D.J.) - 10 duplicates across weeks 11-17
- player_id 7229 - 3 duplicates across weeks 11-14
- player_id 7945 - 4 duplicates across weeks 11-17

**Current Test Failures**:

```
1. stg_ffanalytics__projections grain test:
   dbt_utils_unique_combination_of_columns_player_id__season__week__horizon__asof_date__provider
   Got 17 results, configured to fail if != 0

2. fct_player_projections grain test (warning):
   dbt_utils_unique_combination_of_columns (9-column grain)
   Got 101 results, configured to warn if != 0
```

**Impact**:

- 17 staging duplicates (grain violation)
- 101 fact table duplicates (cascading from staging via 2×2 model pivot)
- Projection accuracy compromised (which values are correct?)
- Downstream marts affected: `mrt_fantasy_projections`, `mrt_projection_variance`

## Tasks

### Phase 1: Investigation

- [ ] **Verify duplicate patterns in raw Parquet files**:

  - [ ] Check `data/raw/ffanalytics/projections/dt=2025-11-09/*.parquet` directly
  - [ ] Confirm duplicates exist in source, not introduced by staging model
  - [ ] Document which players are affected and name variation patterns

- [ ] **Trace R runner logic**:

  - [ ] Review `scripts/projections/fetch_ffanalytics_projections.R`
  - [ ] Identify where player name mapping occurs
  - [ ] Check if consensus aggregation properly handles name variations
  - [ ] Review `ffanalytics` package source matching logic

- [ ] **Determine fix location**:

  - [ ] Option A: Fix in R runner (preferred - prevents bad data from being written)
  - [ ] Option B: Add deduplication in staging model (workaround if R fix is complex)
  - [ ] Document trade-offs of each approach

### Phase 2: Implementation

**If fixing in R runner** (Option A - Preferred):

- [ ] Update player name normalization logic in R runner
- [ ] Add deduplication step after consensus aggregation
- [ ] Use priority rules for conflicting stat values:
  - [ ] Prefer more precise decimal values over rounded integers
  - [ ] Or: Re-aggregate to resolve conflicts
- [ ] Add validation to prevent future duplicates
- [ ] Re-run ingestion to generate clean snapshot
- [ ] Verify `stg_ffanalytics__projections` test passes with new snapshot

**If fixing in staging model** (Option B - Workaround):

- [ ] Add `QUALIFY ROW_NUMBER() OVER (PARTITION BY player_id, season, week, horizon, asof_date, provider ORDER BY ...)`
- [ ] Choose appropriate sort criteria:
  - [ ] Prefer canonical name format from `dim_player_id_xref`?
  - [ ] Prefer more precise stat values (more decimal places)?
  - [ ] Use `total_weight` or `source_count` as tiebreaker?
- [ ] Document why staging deduplication was needed
- [ ] Add comment explaining sort logic
- [ ] Consider adding data quality warning

### Phase 3: Validation

- [ ] **Test staging model grain**:

  ```bash
  make dbt-test --select stg_ffanalytics__projections
  # Expect: unique_combination_of_columns test PASS (0 duplicates)
  ```

- [ ] **Test fact table grain**:

  ```bash
  make dbt-test --select fct_player_projections
  # Expect: unique_combination_of_columns test PASS (0 duplicates)
  ```

- [ ] **Verify affected players resolved**:

  ```sql
  SELECT player_id, season, week, horizon, asof_date, provider, COUNT(*) as row_count
  FROM main.stg_ffanalytics__projections
  WHERE player_id IN (6650, 7229, 7945)
  GROUP BY player_id, season, week, horizon, asof_date, provider
  HAVING COUNT(*) > 1;
  -- Should return 0 rows
  ```

- [ ] **Check downstream marts**:

  ```bash
  make dbt-run --select mrt_fantasy_projections mrt_projection_variance
  make dbt-test --select mrt_fantasy_projections mrt_projection_variance
  ```

### Phase 4: Documentation

- [ ] Update ticket with findings and chosen approach
- [ ] If R runner fix: Document changes in `scripts/projections/README.md`
- [ ] If staging fix: Add comments in `stg_ffanalytics__projections.sql`
- [ ] Update `00-OVERVIEW.md` to mark P1-018 complete
- [ ] Update `2025-11-07_tasks_checklist_v_2_0.md`
- [ ] Note resolution in P1-016 ticket notes

## Acceptance Criteria

- [ ] Zero duplicates in `stg_ffanalytics__projections` (17 → 0)
- [ ] Zero duplicates in `fct_player_projections` (101 → 0)
- [ ] Grain test passes with severity: error
- [ ] Root cause documented and fix implemented
- [ ] Approach decision documented (R runner vs staging model)
- [ ] No regression in row counts (should still have ~8,668 unique projections)

## Implementation Notes

**Preferred Approach**: Fix in R runner

Fixing at the source prevents bad data from entering the pipeline and ensures:

- Data quality at ingestion time
- No workarounds needed in staging
- Clearer data lineage
- Easier debugging for future issues

**Why R runner creates duplicates**:

The `ffanalytics` package aggregates projections from multiple sources (ESPN, Yahoo, CBS, etc.). When a player's name appears with variations across sources:

1. Each name variation gets mapped to the same `player_id` (via fuzzy matching)
2. But the aggregation doesn't deduplicate by `player_id` - it groups by `player_name`
3. Result: Same player appears multiple times with different name formats

**Fix Strategy**:

1. After initial aggregation, deduplicate by `player_id` (not `player_name`)
2. Use canonical name from `dim_player_id_xref` crosswalk
3. For conflicting stat values, either:
   - Re-aggregate using the same consensus logic
   - Choose the value with higher `total_weight` or `source_count`

## References

- Parent ticket: `P1-016-update-ffanalytics-projections-model.md` (snapshot governance fix)
- R runner: `scripts/projections/fetch_ffanalytics_projections.R`
- Staging model: `dbt/ff_data_transform/models/staging/stg_ffanalytics__projections.sql`
- YAML: `dbt/ff_data_transform/models/staging/_stg_ffanalytics__projections.yml`
- Fact table: `dbt/ff_data_transform/models/core/fct_player_projections.sql`
- Plan: `../2025-11-07_plan_v_2_0.md`
- Similar issue: `P1-017-fix-mrt-fasa-targets-duplicates.md` (mart-level duplicates)
