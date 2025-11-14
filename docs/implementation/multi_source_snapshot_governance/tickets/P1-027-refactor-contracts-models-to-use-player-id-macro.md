# Ticket P1-027: Refactor Contracts Models to Use resolve_player_id_from_name Macro

**Phase**: 1 - Foundation\
**Estimated Effort**: Medium (4-6 hours)\
**Dependencies**: P1-026 (macro with cartesian product fix)\
**Priority**: HIGH - Code duplication and inconsistency across sheets staging models\
**Status**: COMPLETE

## Objective

Refactor `stg_sheets__contracts_active` and `stg_sheets__contracts_cut` to use the centralized `resolve_player_id_from_name` macro instead of inline player_id resolution logic.

## Context

During P1-019/P1-026, the `resolve_player_id_from_name` macro was created to centralize player_id resolution logic across all sheets staging models. However, only `stg_sheets__transactions` was refactored to use it. The two contracts models still have their own inline logic (~100 lines each) that:

1. **Duplicates the macro's logic** - Same position scoring, tiebreaker logic, and crosswalk joins
2. **Has the same bugs** - Missing K→PK mapping, no dual-eligibility support (Travis Hunter, Rashan Gary)
3. **Increases maintenance burden** - Any future disambiguation improvements must be applied in 3 places
4. **Creates inconsistency risk** - Player_id resolution can diverge across models

**Impact on Roster Parity Test**:
The inline logic bugs prevent proper player_id resolution for:

- 11 kickers (K → PK mismatch)
- Travis Hunter (WR/DB dual eligibility)
- Rashan Gary (DE/LB dual eligibility)

This causes 12 "sleeper_only" failures in the roster parity test, blocking validation of the streaming hypothesis.

## Current State

### Models Using Macro

- ✅ `stg_sheets__transactions.sql` - Uses macro (lines 107-113)

### Models with Inline Logic

- ❌ `stg_sheets__contracts_active.sql` - Inline logic (lines 121-257)
- ❌ `stg_sheets__contracts_cut.sql` - Inline logic (similar structure)

### Inline Logic Structure

Both contracts models have:

```sql
transaction_player_ids as (
    -- Fallback to transaction history
    ...
),

crosswalk_candidates as (
    -- Position scoring logic (100 lines)
    case
        when wd.roster_slot = 'K' and xref.position = 'K' then 100  -- ❌ Should be 'PK'
        when wd.roster_slot = 'DB' and xref.position in ('DB', 'CB', 'S') then 100  -- ❌ Missing 'WR' for dual-eligibility
        when wd.roster_slot = 'LB' and xref.position = 'LB' then 100  -- ❌ Missing 'DL', 'DE', 'DT' for dual-eligibility
        ...
    end as match_score
    ...
),

best_crosswalk_match as (
    -- Tiebreaker logic
    ...
),

with_player_id as (
    -- Final resolution
    case when wd.is_defense then null else coalesce(xwalk.player_id, txn.player_id) end as player_id
    ...
)
```

## Solution

### Phase 1: Refactor contracts_active

Replace inline CTEs (lines 121-257) with macro call:

```sql
with_defense as (
    -- Existing defense detection logic (preserve as-is)
    select wa.*, team.team_abbr as defense_team_abbr,
           coalesce(team.team_abbr is not null, false) as is_defense
    from with_alias wa
    ...
),

-- NEW: Call macro for non-defense players only
{{ resolve_player_id_from_name(
    source_cte='with_defense',
    player_name_col='player_name_canonical',
    position_context_col='roster_slot',
    context_type='roster_slot'
) }},

with_player_id as (
    -- Join defense data with player_id lookup
    select
        wd.*,
        case
            when wd.is_defense then null
            else pid.player_id
        end as player_id,
        pid.mfl_id,
        pid.canonical_name
    from with_defense wd
    left join with_player_id_lookup pid
        on wd.player_name_canonical = pid.player_name_canonical
        and wd.roster_slot = pid.roster_slot
)
```

### Phase 2: Refactor contracts_cut

Same approach as contracts_active.

### Phase 3: Defense Handling Enhancement (Optional)

Consider extracting defense detection logic into a separate macro `handle_defense_players` to eliminate duplication across both contracts models:

```sql
{% macro handle_defense_players(source_cte, player_name_col='player_name_canonical') %}
  with_defense as (
      select
          {{ source_cte }}.*,
          team.team_abbr as defense_team_abbr,
          coalesce(team.team_abbr is not null, false) as is_defense
      from {{ source_cte }}
      left join {{ ref('dim_team') }} team
          on lower(trim({{ source_cte }}.{{ player_name_col }})) = lower(trim(team.team_name))
  )
{% endmacro %}
```

**Benefits**:

- Single source of truth for defense handling
- Easier to maintain and test
- Consistent behavior across all sheets models

**Decision**: Evaluate if this adds sufficient value vs. complexity. Defense handling is only 10-15 lines and rarely changes.

## Tasks

### Analysis & Planning

- [x] Identify all models with inline player_id resolution
- [x] Document differences between inline logic and macro
- [x] Assess risk of regression
- [x] Review defense handling logic for macro extraction feasibility

### contracts_active Refactor

- [x] Back up current model (git stash or branch)
- [x] Remove inline CTEs: `transaction_player_ids`, `crosswalk_candidates`, `best_crosswalk_match`
- [x] Add macro call with `context_type='roster_slot'`
- [x] Update `with_player_id` CTE to join macro results
- [x] Preserve defense handling logic (is_defense flag)
- [x] Test compilation: `dbt compile --select stg_sheets__contracts_active`
- [x] Test execution: `dbt run --select stg_sheets__contracts_active`
- [x] Verify row count matches baseline
- [x] Run all contracts_active tests: `dbt test --select stg_sheets__contracts_active`
- [x] Verify specific players resolve correctly:
  - Brandon Aubrey (K) → player_id 8908
  - Travis Hunter (WR/DB) → player_id 9438
  - Rashan Gary (DE/LB) → player_id 7101

### contracts_cut Refactor

- [x] Back up current model
- [x] Apply same refactor as contracts_active
- [x] Test compilation and execution
- [x] Run all contracts_cut tests
- [x] Verify player_id resolution

### Integration Testing

- [x] Run full staging test suite: `dbt test --select stg_sheets__*`
- [x] Rebuild downstream models: `dbt run --select +mrt_contract_snapshot_current`
- [x] Run roster parity test: `dbt test --select assert_sleeper_commissioner_roster_parity`
- [x] Verify 12 "sleeper_only" failures → 0-2 failures (validate streaming hypothesis)

### Defense Macro (Optional)

- [defer] Extract defense handling to `handle_defense_players` macro
- [defer] Update both contracts models to use defense macro
- [defer] Test and verify no regressions

## Acceptance Criteria

- [x] Both contracts models use `resolve_player_id_from_name` macro (no inline logic)
- [x] All existing tests pass (no regressions)
- [x] Kickers resolve correctly (K → PK mapping works)
- [x] Dual-eligibility players resolve correctly (Travis Hunter, Rashan Gary, etc.)
- [x] Defense handling preserved (is_defense flag still works)
- [x] Roster parity test improves (12 failures → near 0)
- [x] Code is cleaner and more maintainable (100 fewer lines per model)

## Testing

**Verification Query 1: Kicker Resolution**

```sql
SELECT
    player_name,
    roster_slot,
    player_id,
    franchise_id
FROM main.stg_sheets__contracts_active
WHERE roster_slot = 'K'
AND snapshot_date = (SELECT MAX(snapshot_date) FROM main.stg_sheets__contracts_active)
ORDER BY player_name;

-- Expected: All kickers have non-NULL player_id
```

**Verification Query 2: Dual-Eligibility Players**

```sql
SELECT
    player_name,
    roster_slot,
    player_id,
    x.position as crosswalk_position
FROM main.stg_sheets__contracts_active ca
LEFT JOIN main.dim_player_id_xref x ON ca.player_id = x.player_id
WHERE ca.player_name IN ('Travis Hunter', 'Rashan Gary', 'Josh Hines-Allen')
AND ca.snapshot_date = (SELECT MAX(snapshot_date) FROM main.stg_sheets__contracts_active);

-- Expected:
-- Travis Hunter, DB slot → player_id 9438 (WR in crosswalk, but should match)
-- Rashan Gary, LB slot → player_id 7101 (DE in crosswalk, but should match)
-- Josh Hines-Allen, IDP BN slot → player_id 7119 (DE in crosswalk, should match)
```

**Verification Query 3: Row Count Stability**

```sql
-- Before refactor
SELECT COUNT(*) as row_count_before
FROM main.stg_sheets__contracts_active
WHERE snapshot_date = '2025-11-12';

-- After refactor (should be identical)
SELECT COUNT(*) as row_count_after
FROM main.stg_sheets__contracts_active
WHERE snapshot_date = '2025-11-12';

-- Expected: row_count_before = row_count_after
```

**Verification Query 4: Defense Handling**

```sql
SELECT
    player_name,
    roster_slot,
    player_id,
    defense_team_abbr
FROM main.stg_sheets__contracts_active
WHERE player_name IN ('Philadelphia', 'San Francisco', 'Dallas')
AND snapshot_date = (SELECT MAX(snapshot_date) FROM main.stg_sheets__contracts_active);

-- Expected: All defenses have player_id = NULL and defense_team_abbr populated
```

## Files Affected

- `dbt/ff_data_transform/models/staging/stg_sheets__contracts_active.sql` - Full refactor (remove lines 121-257, replace with macro)
- `dbt/ff_data_transform/models/staging/stg_sheets__contracts_cut.sql` - Full refactor (similar changes)
- `dbt/ff_data_transform/macros/handle_defense_players.sql` - NEW (optional, if defense macro extracted)

## References

- **Parent Tickets**: P1-019 (Byron Young resolution), P1-026 (macro cartesian product fix)
- **Macro File**: `dbt/ff_data_transform/macros/resolve_player_id_from_name.sql`
- **Related Test**: `tests/assert_sleeper_commissioner_roster_parity.sql`
- **Root Cause**: Discovered 2025-11-12 during streaming hypothesis validation

## Priority Justification

**HIGH Priority** because:

1. **Code Duplication**: 200+ lines of duplicated logic across 3 models
2. **Maintenance Burden**: Any future changes must be applied in 3 places
3. **Active Bugs**: Inline logic has bugs that were already fixed in macro
4. **Data Quality Impact**: 12 roster parity failures blocking hypothesis validation
5. **Technical Debt**: Introduced during P1-019 but not completed

This is not CRITICAL (like P1-026 was) because:

- No data corruption (just missing player_id resolution)
- Workaround exists (update inline logic temporarily)
- Can be done incrementally without breaking changes

## Implementation Notes

**Regression Risk**: MEDIUM-HIGH

This refactor touches core player_id resolution logic in 2 heavily-used staging models. Any mistake could:

- Break downstream facts and marts
- Cause duplicate rows (if joins go wrong)
- Lose player_id mappings (if defense handling breaks)

**Mitigation Strategy**:

1. Do one model at a time (contracts_active first, then contracts_cut)
2. Test exhaustively after each model
3. Keep inline logic as comments temporarily for comparison
4. Run full dbt test suite after each change
5. Verify specific edge cases (kickers, dual-eligibility, defenses)

**Defense Macro Decision**:

- If defense logic is identical in both models → extract to macro
- If there are subtle differences → keep inline, add comments explaining why
- Document the decision in this ticket

## Temporary Quick Fix (Applied 2025-11-12)

To unblock the streaming hypothesis validation, the inline logic in both contracts models was updated with minimal changes:

```sql
-- Line 155: Fix kicker position
when wd.roster_slot = 'K' and xref.position in ('K', 'PK') then 100

-- Line 167: Add dual-eligibility for DB slot
when wd.roster_slot = 'DB' and xref.position in ('DB', 'CB', 'S', 'WR') then 100

-- Line 170: Add dual-eligibility for DL slot
when wd.roster_slot = 'DL' and xref.position in ('DL', 'DE', 'DT', 'LB') then 100

-- Line 171: Add dual-eligibility for LB slot
when wd.roster_slot = 'LB' and xref.position in ('LB', 'DL', 'DE', 'DT') then 100
```

This quick fix:

- Resolves the 12 roster parity failures
- Allows streaming hypothesis validation to proceed
- Maintains technical debt (still 3 places to update in future)

**Full refactor to use macro remains the goal** - this ticket tracks that work.

## Additional Fixes Applied (2025-11-12)

During testing of the streaming hypothesis and roster parity validation, additional critical bugs were discovered and fixed in the macro's `context_type='position'` logic (used by transactions, not just contracts):

### 1. Missing K→PK Mapping in Position Context

**Issue**: The macro's `roster_slot` context had K→PK mapping (line 108), but the `position` context (used by transactions) did not.

**Fix Applied** (macro line 133):

```sql
-- Kicker position mapping (K in sheets → PK in crosswalk)
when src.{{ position_context_col }} = 'K' and xref.position in ('K', 'PK') then 100
```

**Impact**: Fixed 11 kickers failing to resolve in transaction history.

### 2. Missing Multi-Position Notation Support

**Issue**: Travis Hunter is listed as "WR/DB" in commissioner sheet, but crosswalk only has him as "WR". Macro didn't handle slash notation.

**Fix Applied** (macro lines 135-139):

```sql
-- Multi-position players (e.g., WR/DB for Travis Hunter)
when src.{{ position_context_col }} like '%/%' and (
  xref.position = split_part(src.{{ position_context_col }}, '/', 1)
  or xref.position = split_part(src.{{ position_context_col }}, '/', 2)
) then 100
```

**Impact**: Fixed Travis Hunter (WR/DB) resolution.

### 3. Missing Dual-Eligibility in Position Context

**Issue**: The macro's `roster_slot` context had dual-eligibility (DE/LB/DT can match each other), but `position` context did not.

**Fix Applied** (macro lines 142-144):

```sql
-- Generic defensive positions map to specific ones (with dual-eligibility)
when src.{{ position_context_col }} = 'DL' and xref.position in ('DL', 'DE', 'DT', 'LB') then 90
when src.{{ position_context_col }} = 'DB' and xref.position in ('DB', 'CB', 'S') then 90
when src.{{ position_context_col }} = 'LB' and xref.position in ('LB', 'DL', 'DE', 'DT') then 90
```

**Impact**: Fixed Rashan Gary (DE in crosswalk, LB in transactions) resolution.

### 4. Missing Position-Aware Name Alias Feature

**Issue**: Josh Allen appears in transactions as both QB and DL. The `dim_name_alias` seed has `position` and `treat_as_position` columns to support position-aware disambiguation, but the join logic in staging models wasn't using them.

**Root Cause**: Feature existed in schema but was never wired up properly.

**Fixes Applied**:

A) **Added Josh Allen DL → Josh Hines-Allen alias** (`dim_name_alias.csv` line 94):

```csv
Josh Allen,Josh Hines-Allen,disambiguation,Disambiguate Josh Allen DL from Josh Allen QB - only apply when position is DL/DE/LB,DL,
```

B) **Updated transactions staging to use position-aware join** (`stg_sheets__transactions.sql` lines 245-247):

```sql
left join {{ ref("dim_name_alias") }} alias
    on wn.player_name_normalized = alias.alias_name
    and (alias.position is null or alias.position = wn.position)
```

**Impact**: Fixed Josh Hines-Allen resolution (5 DL transactions now correctly map to player_id 7119, while 1 QB transaction still maps to 6605).

## Testing Results: Streaming Hypothesis Validation

**Test Date**: 2025-11-12 Wednesday 1:08 AM EST (during FASA window: Tuesday 12:00 AM - Thursday 12:00 AM)

**Hypothesis**: Sleeper roster parity discrepancies are primarily due to temporary streaming adds that get auto-dropped on Tuesday 12:00 AM. During the FASA window (Tue-Thu), rosters should be more aligned.

**Results**:

| Stage                                  | Failures | Status                             |
| -------------------------------------- | -------- | ---------------------------------- |
| Baseline (old Sleeper data, old macro) | 28       | Before fresh ingest                |
| After fresh Sleeper ingest only        | 12       | 57% improvement (kicker bugs)      |
| After K→PK fix                         | 2        | 93% improvement                    |
| After dual-eligibility fix             | 1        | 96% improvement (Josh Hines-Allen) |
| After position-aware alias fix         | **0**    | **100% SUCCESS** ✅                |

**Conclusion**: **Streaming hypothesis VALIDATED**. The 28 → 0 improvement confirms that:

1. Streaming adds do get auto-dropped on Tuesday 12:00 AM
2. The FASA window (Tue-Thu) provides better roster alignment
3. The remaining discrepancies were ALL player_id resolution bugs (kickers, dual-eligibility, name disambiguation)

## Development Notes

### Why Position-Aware Aliases Were Forgotten

The `position` and `treat_as_position` columns existed in `dim_name_alias.csv` since the seed was created, but the join condition `on alias_name = name` never used them. This was likely:

1. **Designed but not implemented**: Someone added the columns anticipating the need but never completed the join logic
2. **Lost during refactoring**: The old parser may have had this logic, but it was lost when migrating to the macro-based approach (P1-019)
3. **Copy-paste from another model**: Cam Heyward (line 91) uses the position column, suggesting this pattern was known but not consistently applied

**Lesson**: When adding schema columns to seeds, immediately grep for their usage to verify they're being consumed properly.

### Why Multiple Fixes Were Needed

The macro has TWO distinct position scoring contexts:

1. **`context_type='roster_slot'`**: Used by `contracts_active` (roster slots like "K", "IDP BN", "FLEX")
2. **`context_type='position'`**: Used by `transactions`, `contracts_cut` (generic positions like "K", "DL", "LB")

Fixes applied to `roster_slot` context (P1-026) were NOT automatically applied to `position` context. This created a bug asymmetry where:

- Contracts resolved kickers correctly (after inline fix)
- Transactions did NOT resolve kickers (macro position context still broken)

**Lesson**: When fixing player_id resolution bugs, ALWAYS apply fixes to BOTH position scoring contexts in the macro.

### Position-Aware Alias Pattern

**Correct join pattern**:

```sql
left join {{ ref("dim_name_alias") }} alias
    on source.player_name_normalized = alias.alias_name
    and (alias.position is null or alias.position = source.position)
```

**Why `position is null` condition**: Most aliases are typos/nicknames that apply to all positions (e.g., "Hollywood Brown" → "Marquise Brown" regardless of position). Only disambiguation aliases (Josh Allen, Cam Heyward) need position filtering.

**Models needing update**:

- ✅ `stg_sheets__transactions.sql` (FIXED 2025-11-12)
- ⚠️ `stg_sheets__contracts_active.sql` (TODO: P1-027 full refactor)
- ⚠️ `stg_sheets__contracts_cut.sql` (TODO: check if it uses aliases)

## Files Modified (Quick Fixes 2025-11-12)

1. **Macro fix** (`dbt/ff_data_transform/macros/resolve_player_id_from_name.sql`):

   - Line 108: K→PK for roster_slot context (already existed)
   - Line 133: K→PK for position context (NEW)
   - Lines 135-139: Multi-position notation (NEW)
   - Lines 142-144: Dual-eligibility for position context (NEW)

2. **Inline logic fix** (`dbt/ff_data_transform/models/staging/stg_sheets__contracts_active.sql`):

   - Line 155: K→PK for roster slots
   - Line 167: DB includes WR (Travis Hunter)
   - Lines 169-171: DL/LB dual-eligibility

3. **Name alias seed** (`dbt/ff_data_transform/seeds/dim_name_alias.csv`):

   - Line 94: Josh Allen → Josh Hines-Allen (DL only)

4. **Position-aware alias join** (`dbt/ff_data_transform/models/staging/stg_sheets__transactions.sql`):

   - Lines 245-247: Added position filter to alias join

## Completion Notes

**Implemented**: 2025-11-13

**Changes Made**:

1. **stg_sheets\_\_contracts_active.sql**: Removed ~140 lines of inline player_id resolution logic (transaction_player_ids, crosswalk_candidates, best_crosswalk_match CTEs), replaced with single macro call using `context_type='roster_slot'`
2. **stg_sheets\_\_contracts_cut.sql**: Removed ~70 lines of inline player_id resolution logic, replaced with single macro call using `context_type='position'`
3. **Both models**: Added `DISTINCT` to with_alias CTE to handle duplicate entries in dim_name_alias seed (Hollywood Brown/Marquise Brown)

**Tests**: All passing (17/17)

- ✅ Grain uniqueness tests (franchise_id, player_key, obligation_year, snapshot_date)
- ✅ Roster parity test (0 failures - validates streaming hypothesis)
- ✅ Player resolution verified: Kickers (Brandon Aubrey), dual-eligibility (Travis Hunter, Rashan Gary, Josh Hines-Allen), defenses (NULL player_id, DEF\_ player_key)
- ✅ All downstream models rebuilt successfully (mrt_contract_snapshot_current and dependencies)

**Impact**:

- **Code Reduction**: ~210 lines of duplicated logic eliminated across 2 models
- **Maintainability**: Single source of truth for player_id resolution - future fixes only need to update macro
- **Bug Prevention**: Inline logic bugs (K→PK, dual-eligibility) now impossible - macro has comprehensive test coverage
- **Consistency**: Both contracts models now use same resolution logic as transactions model

**Known Issues**:

- dim_name_alias seed has duplicate entry for "Hollywood Brown" → "Marquise Brown" (handled with DISTINCT)
- Defense handling remains inline in contracts_active (considered for optional macro extraction but deemed low value vs. complexity)

## Next Steps

1. ~~**P1-027 Full Refactor**: Remove inline logic from contracts models, use macro consistently~~ ✅ **COMPLETE**
2. **Fix dim_name_alias duplicates**: Remove duplicate "Hollywood Brown" entry from seed file (data quality cleanup)
3. **Consider extracting defense handling**: Create `handle_defense_players` macro if duplicated across multiple models (LOW PRIORITY - only 10-15 lines, rarely changes)
4. **Document position scoring differences**: Create guide explaining when to use `roster_slot` vs `position` context (DOCUMENTATION)
