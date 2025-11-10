# Ticket P1-019: Investigate Sleeper-Commissioner Roster Parity Failures

**Phase**: 1 - Foundation\
**Estimated Effort**: Medium (3-5 hours)\
**Dependencies**: P1-009 (to rule out snapshot selection as root cause)\
**Priority**: Medium - Data quality reconciliation issue

## Objective

Investigate and resolve 30 roster parity failures between Sleeper API data and Commissioner Google Sheet data, as detected by the `assert_sleeper_commissioner_roster_parity` test.

## Context

During P1-009 implementation (`stg_sheets__contracts_active`), we discovered a pre-existing test failure that indicates roster discrepancies between two authoritative data sources:

**Test Failure**:

```
assert_sleeper_commissioner_roster_parity
Got 30 results, configured to fail if != 0
```

This test compares active rosters from:

- **Sleeper API**: `stg_sleeper__rosters` (platform truth)
- **Commissioner Sheet**: `stg_sheets__contracts_active` (manual tracking)

The 30 discrepancies indicate players who appear on one roster but not the other, or with different roster positions/attributes.

**Why This Matters**:

- Both sources are considered authoritative for different purposes
- Sleeper API is real-time platform data (source of truth for league operations)
- Commissioner Sheet is manually maintained (source of truth for contract obligations)
- Discrepancies suggest either:
  1. Data sync lag between sources
  2. Manual data entry errors in Commissioner Sheet
  3. Edge cases not handled in roster matching logic
  4. Legitimate differences (e.g., taxi squad, IR, practice squad handling)

**Important**: This is NOT caused by the snapshot governance changes in P1-008 or P1-009. The failure is a **data quality/reconciliation issue**, not a structural problem.

## Tasks

### Phase 1: Investigation

- [ ] Run the assertion test in isolation to see the 30 failing rows:
  ```bash
  dbt test --select assert_sleeper_commissioner_roster_parity --store-failures
  ```
- [ ] Examine the failed rows to identify patterns:
  - [ ] Are they specific franchises?
  - [ ] Are they specific player types (rookies, IR, taxi squad)?
  - [ ] Are they recent adds/drops with sync lag?
  - [ ] Are they data entry errors (typos, missing players)?
- [ ] Check test definition to understand matching logic:
  - [ ] Review `tests/assert_sleeper_commissioner_roster_parity.sql`
  - [ ] Understand join keys and filters
  - [ ] Verify grain expectations
- [ ] Document root causes with SQL evidence and examples

### Phase 2: Categorize Discrepancies

Classify each of the 30 failures into categories:

- [ ] **Category A: Data Sync Lag** - Recent roster moves not yet in Commissioner Sheet
- [ ] **Category B: Manual Entry Errors** - Typos, missing players, incorrect positions
- [ ] **Category C: Roster Slot Differences** - Taxi/IR/PS handling differences between platforms
- [ ] **Category D: Test Logic Issues** - Matching logic doesn't handle edge cases
- [ ] **Category E: Legitimate Differences** - Expected divergence between sources

### Phase 3: Resolution Strategy

Based on categorization, determine approach:

- [ ] **For Category A**: Document as expected lag, no fix needed (or automate sync)
- [ ] **For Category B**: Fix Commissioner Sheet data (manual update or script)
- [ ] **For Category C**: Adjust test to account for legitimate roster slot differences
- [ ] **For Category D**: Fix test matching logic
- [ ] **For Category E**: Update test expectations or add exclusions

### Phase 4: Implementation

- [ ] Implement fixes based on resolution strategy
- [ ] Re-run test to verify fixes
- [ ] Document any permanent exclusions or expected discrepancies
- [ ] Update test YAML or SQL if logic changes needed

## Acceptance Criteria

- [ ] All 30 discrepancies investigated and categorized
- [ ] Root causes documented with specific player examples
- [ ] Resolution strategy defined for each category
- [ ] Fixes implemented (data corrections, test logic updates, or documented exceptions)
- [ ] Test passes with 0 failures OR expected failures are documented and excluded
- [ ] Reconciliation process documented for future roster moves

## Implementation Notes

**Test File**: `dbt/ff_data_transform/tests/assert_sleeper_commissioner_roster_parity.sql`

**Data Sources**:

1. **Sleeper Rosters**: `stg_sleeper__rosters`

   - Grain: `sleeper_roster_id`, `sleeper_player_id`, `roster_position`
   - Updated: Real-time via Sleeper API
   - Snapshot strategy: `latest_only` (after P1-014)

2. **Commissioner Contracts**: `stg_sheets__contracts_active`

   - Grain: `franchise_id`, `player_key`, `obligation_year`, `snapshot_date`
   - Updated: Manual entry in Google Sheet
   - Snapshot strategy: `latest_only` (after P1-009)

**Investigation Queries**:

```sql
-- Query the failed rows from test results
SELECT * FROM [test_results_table] WHERE test_name = 'assert_sleeper_commissioner_roster_parity';

-- Manual comparison query
WITH sleeper_active AS (
  SELECT franchise_id, player_id, roster_slot
  FROM stg_sleeper__rosters
  WHERE roster_status = 'active'
),
commissioner_active AS (
  SELECT franchise_id, player_id, roster_slot
  FROM stg_sheets__contracts_active
  WHERE obligation_year = 2025
)
SELECT
  COALESCE(s.franchise_id, c.franchise_id) AS franchise_id,
  COALESCE(s.player_id, c.player_id) AS player_id,
  s.roster_slot AS sleeper_slot,
  c.roster_slot AS commissioner_slot,
  CASE
    WHEN s.player_id IS NULL THEN 'Missing in Sleeper'
    WHEN c.player_id IS NULL THEN 'Missing in Commissioner Sheet'
    WHEN s.roster_slot != c.roster_slot THEN 'Roster slot mismatch'
    ELSE 'Unknown'
  END AS discrepancy_type
FROM sleeper_active s
FULL OUTER JOIN commissioner_active c
  ON s.franchise_id = c.franchise_id AND s.player_id = c.player_id
WHERE s.player_id IS NULL OR c.player_id IS NULL OR s.roster_slot != c.roster_slot;
```

**Common Discrepancy Patterns**:

1. **Recent Trades/Pickups**: Sleeper updated, Commissioner Sheet not yet synced
2. **Taxi Squad**: Different handling between platforms
3. **IR/Injured Reserve**: May be tracked differently
4. **Practice Squad**: Platform-specific roster designations
5. **Name Variations**: Player name normalization issues in matching logic
6. **Dropped Players**: Timing difference in reflection across sources

## Testing

1. **Run test with failure storage**:

   ```bash
   make dbt-test ARGS="--select assert_sleeper_commissioner_roster_parity --store-failures"
   ```

2. **Examine failures**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT * FROM main.assert_sleeper_commissioner_roster_parity_failures LIMIT 20;"
   ```

3. **After fixes, verify**:

   ```bash
   make dbt-test ARGS="--select assert_sleeper_commissioner_roster_parity"
   # Expect: PASS (0 failures) or documented expected failures
   ```

## Impact

**Before Fix**:

- 30 roster discrepancies between Sleeper and Commissioner Sheet
- Unclear which source is correct for each discrepancy
- Potential analytics errors if relying on incorrect roster data
- Test fails on every run, masking new issues

**After Fix**:

- All discrepancies investigated and categorized ✅
- Data corrections made where needed ✅
- Test logic updated to handle legitimate differences ✅
- Clear documentation of expected edge cases ✅
- Test passes consistently (or fails only on new genuine issues) ✅

**Downstream Impact**:

- Contract analysis relies on accurate `stg_sheets__contracts_active`
- Roster depth analysis uses both Sleeper and Commissioner data
- FASA target recommendations depend on accurate roster composition
- Trade analysis compares actual rosters with contract obligations

## References

- Test file: `dbt/ff_data_transform/tests/assert_sleeper_commissioner_roster_parity.sql`
- Model files:
  - `dbt/ff_data_transform/models/staging/stg_sleeper__rosters.sql`
  - `dbt/ff_data_transform/models/staging/stg_sheets__contracts_active.sql`
- Related tickets:
  - P1-009: `stg_sheets__contracts_active` snapshot governance (where issue was discovered)
  - P1-014: `stg_sleeper__rosters` snapshot governance (dependency)

## Notes

**Why This Ticket Exists**:

During P1-009 implementation, the `assert_sleeper_commissioner_roster_parity` test failed with 30 discrepancies. This is a **pre-existing data quality issue**, not caused by snapshot governance changes. However, it needs investigation to:

1. Ensure both roster data sources are accurate
2. Understand if discrepancies are expected or errors
3. Fix any data quality issues
4. Update test logic if needed for legitimate edge cases

**Sequencing**:

This ticket should be completed:

- AFTER P1-009 (to rule out snapshot selection as cause)
- AFTER P1-014 (to ensure `stg_sleeper__rosters` also uses latest snapshot)
- BEFORE Phase 2 (to ensure foundation data quality)

**Not Blocking**:

This ticket is data quality focused and doesn't block:

- Other staging model snapshot governance updates (P1-010, P1-011, P1-012)
- Phase 2 governance infrastructure

It can be worked in parallel with remaining P1 staging updates.

**Expected Outcome**:

Most likely, this will result in:

1. A few manual data entry corrections in the Commissioner Sheet
2. Documentation of expected discrepancies (e.g., taxi squad handling)
3. Possible test logic refinement to ignore known edge cases
4. Process documentation for reconciling rosters going forward
