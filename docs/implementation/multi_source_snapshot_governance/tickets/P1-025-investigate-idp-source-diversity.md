# Ticket P1-025: Investigate assert_idp_source_diversity Test Failures

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: None (independent data quality check)\
**Priority**: Low - 3 failures in IDP source diversity validation

## Objective

Investigate and resolve 3 failures in the `assert_idp_source_diversity` test, which validates that IDP (Individual Defensive Player) statistics are sourced from multiple providers to ensure data coverage and reliability.

## Context

During comprehensive dbt test analysis (2025-11-10), the `assert_idp_source_diversity` test failed with 3 violations, indicating that some IDP players or position groups lack expected source diversity.

**Test Failure**:

```
assert_idp_source_diversity
Got 3 results, configured to fail if != 0
```

**Expected Behavior**:

IDP statistics should be available from multiple data providers to:

- Validate data accuracy through cross-referencing
- Ensure coverage if one provider is unavailable
- Provide redundancy for critical defensive stats

**Why This Matters**:

- Data reliability - multiple sources reduce single-point-of-failure risk
- IDP leagues require accurate defensive stats for scoring
- Source diversity enables data quality validation
- Low priority because it's a data quality warning, not a data corruption issue

## Tasks

### Phase 1: Investigation

- [ ] Run test query to identify which IDP players/positions lack source diversity:
  ```sql
  -- Example query structure (actual query in test file)
  SELECT player_id, player_name, position,
         COUNT(DISTINCT provider) as provider_count
  FROM main.fct_player_stats
  WHERE position IN ('DL', 'DE', 'DT', 'LB', 'DB', 'S', 'CB')
    AND stat_kind = 'actual'
  GROUP BY player_id, player_name, position
  HAVING COUNT(DISTINCT provider) < 2
  ORDER BY player_id;
  ```
- [ ] Check which providers are available for IDP:
  ```sql
  SELECT DISTINCT provider, COUNT(*) as stat_count
  FROM main.fct_player_stats
  WHERE position IN ('DL', 'DE', 'DT', 'LB', 'DB', 'S', 'CB')
  GROUP BY provider;
  ```
- [ ] Determine if failures are:
  - [ ] Specific players missing from secondary providers
  - [ ] Entire position groups missing from secondary providers
  - [ ] Seasonal gaps (e.g., rookies only in primary source)
- [ ] Review test expectations:
  - [ ] Is requiring 2+ sources realistic for all IDP players?
  - [ ] Should test allow exceptions for specific scenarios?
- [ ] Document root cause with SQL evidence

### Phase 2: Determine Fix Strategy

Based on investigation, choose approach:

**Option A: Accept Current State (Test Too Strict)**

- [ ] Test expectation of 2+ sources is unrealistic
- [ ] NFLverse is primary/only IDP source
- [ ] Update test to warn instead of fail
- [ ] Document known single-source IDP players

**Option B: Add Secondary IDP Source**

- [ ] Additional IDP data provider available but not integrated
- [ ] Integrate secondary source (e.g., Pro Football Reference, Sleeper)
- [ ] Update ingestion to include IDP from new source

**Option C: Fix Source Attribution**

- [ ] IDP data from multiple sources but incorrectly attributed
- [ ] Fix provider field in staging models
- [ ] Ensure proper source labeling

**Option D: Document Exceptions**

- [ ] 3 failures are legitimate exceptions (e.g., practice squad, recent signings)
- [ ] Update test to exclude these specific cases
- [ ] Add comments explaining exceptions

### Phase 3: Implementation

- [ ] Implement chosen fix strategy
- [ ] If test change: Update `tests/assert_idp_source_diversity.sql`
- [ ] If model change: Update IDP staging models
- [ ] If ingestion change: Add new IDP provider (out of P1 scope, defer to later)
- [ ] Test compilation if models changed

### Phase 4: Validation

- [ ] Run IDP diversity test:
  ```bash
  make dbt-test --select assert_idp_source_diversity
  # Expect: PASS (0 failures) or WARN (if downgraded)
  ```
- [ ] Verify IDP coverage:
  ```sql
  SELECT position,
         COUNT(DISTINCT player_id) as unique_players,
         COUNT(DISTINCT provider) as provider_count
  FROM main.fct_player_stats
  WHERE position IN ('DL', 'DE', 'DT', 'LB', 'DB', 'S', 'CB')
  GROUP BY position
  ORDER BY position;
  ```
- [ ] Spot-check that offensive players still have expected diversity

## Acceptance Criteria

- [ ] Root cause identified and documented
- [ ] Fix strategy chosen and implemented
- [ ] Test passes (0 failures) OR updated to warn instead of fail
- [ ] IDP coverage documented (single-source vs multi-source)
- [ ] Decision logged: accept single-source or add secondary source (future work)

## Implementation Notes

**Test File**: `dbt/ff_data_transform/tests/assert_idp_source_diversity.sql`

**Related Models**:

- `fct_player_stats` (primary fact table with provider field)
- `stg_nflverse__player_stats` (likely primary IDP source)
- Any other IDP staging models

**Investigation Query Template**:

```sql
-- Check current IDP source coverage
WITH idp_coverage AS (
  SELECT
    position,
    provider,
    COUNT(DISTINCT player_id) as player_count,
    COUNT(*) as stat_rows
  FROM main.fct_player_stats
  WHERE position IN ('DL', 'DE', 'DT', 'LB', 'DB', 'S', 'CB')
    AND season >= 2024
  GROUP BY position, provider
)
SELECT * FROM idp_coverage
ORDER BY position, provider;
```

## Testing

1. **Current state check**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" \
   duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT position, COUNT(DISTINCT provider) as provider_count
      FROM main.fct_player_stats
      WHERE position IN ('DL', 'DE', 'DT', 'LB', 'DB', 'S', 'CB')
      GROUP BY position
      ORDER BY position;"
   ```

2. **Run test**:

   ```bash
   make dbt-test --select assert_idp_source_diversity
   ```

3. **After fix, verify**:

   ```bash
   # Should pass with 0 failures (or warn if downgraded)
   make dbt-test --select assert_idp_source_diversity
   ```

## Impact

**Before Fix**:

- 3 IDP players/positions with insufficient source diversity
- Potential single-point-of-failure for defensive stats
- Test failure (low severity)

**After Fix**:

- IDP source diversity validated or exceptions documented ✅
- Clear understanding of IDP data coverage ✅
- Test passes or appropriately warns ✅

**Downstream Impact**:

- IDP scoring in fantasy leagues
- Defensive player analysis
- Data quality monitoring

**Note**: This is a **low priority** ticket. If resolving requires significant effort (e.g., adding new data provider), consider deferring to post-Phase 1 work and downgrading test to warning.

## References

- Test: `dbt/ff_data_transform/tests/assert_idp_source_diversity.sql`
- Model: `dbt/ff_data_transform/models/core/fct_player_stats.sql`
- IDP positions: DL, DE, DT, LB, DB, S, CB
- Discovery: Comprehensive test analysis (2025-11-10)

## Notes

**Why This Ticket Exists**:

This test failure was discovered during comprehensive Phase 1 test analysis. It's a data quality check rather than a data integrity issue, making it lower priority than duplicates or orphan references.

**Sequencing**:

- Lowest priority among Phase 1 data quality tickets
- Can be done last or deferred to post-Phase 1
- No dependencies; completely independent

**IDP Context**:

IDP (Individual Defensive Player) leagues score defensive players individually rather than using team defenses (DST). This requires granular defensive statistics like tackles, sacks, interceptions, etc. Most fantasy platforms focus on offensive stats, so defensive stats may have less source diversity.

**Recommendation**:

If investigation shows that adding a secondary IDP source requires significant effort, consider:

1. Downgrading test from ERROR to WARN
2. Documenting NFLverse as authoritative IDP source
3. Deferring secondary source integration to future sprint
