# Ticket P1-001: Create snapshot_selection_strategy Macro

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (2-3 hours)\
**Dependencies**: None

## Objective

Implement a flexible `snapshot_selection_strategy` macro that eliminates hardcoded dates in dbt staging models and supports three selection strategies: `latest_only`, `baseline_plus_latest`, and `all`.

## Context

Currently, NFLverse staging models use hardcoded `dt IN (...)` filters, making snapshot management brittle and requiring SQL changes for every snapshot update. This macro provides a centralized, parameterizable approach to snapshot selection that can be configured via dbt vars and environment variables.

The macro builds on the existing `latest_snapshot_only()` helper but extends it to support multiple selection patterns needed for different use cases (historical continuity, backfills, etc.).

## Tasks

- [x] Create `dbt/ff_data_transform/macros/snapshot_selection.sql`
- [x] Implement `snapshot_selection_strategy` macro with three strategies:
  - [x] `latest_only` strategy - Select only most recent snapshot
  - [x] `baseline_plus_latest` strategy - Select baseline + latest for continuity
  - [x] `all` strategy - No filter (for backfills)
- [x] Test macro compilation with `uv run dbt compile`
- [x] Add inline documentation explaining each strategy
- [x] Verify macro works with `env_var()` function for glob patterns

## Acceptance Criteria

- [x] Macro file exists at `dbt/ff_data_transform/macros/snapshot_selection.sql`
- [x] All three strategies implemented and documented
- [x] `dbt compile` succeeds with no errors
- [x] Macro accepts `source_glob`, `strategy`, and optional `baseline_dt` parameters

## Implementation Notes

**File**: `dbt/ff_data_transform/macros/snapshot_selection.sql`

```sql
{% macro snapshot_selection_strategy(source_glob, strategy='latest_only', baseline_dt=none) %}
  {% if strategy == 'latest_only' %}
    -- Select only the most recent snapshot
    and {{ latest_snapshot_only(source_glob) }}
  {% elif strategy == 'baseline_plus_latest' %}
    -- Select baseline snapshot + latest (for historical continuity)
    and (dt = '{{ baseline_dt }}' or {{ latest_snapshot_only(source_glob) }})
  {% elif strategy == 'all' %}
    -- No filter (load all snapshots for backfills)
  {% endif %}
{% endmacro %}
```

**Design Decisions** (from plan):

- Eliminates hardcoded dates in SQL
- Supports multiple selection patterns via single interface
- Enables environment-specific configuration via dbt vars
- Calls existing `latest_snapshot_only()` helper for the `latest_only` strategy

**Macro/Helper Relationship**:

The new `snapshot_selection_strategy` macro **calls** the existing `latest_snapshot_only()` helper for consistency. We're intentionally keeping both:

- **`latest_snapshot_only()` helper**: Simple helper for "just get latest" use case. Stays available for direct use.
- **`snapshot_selection_strategy()` macro**: Higher-level abstraction supporting multiple strategies (latest_only, baseline_plus_latest, all).

**Benefits of this approach**:

- Backwards compatibility: Existing models using `latest_snapshot_only()` directly still work
- Single source of truth: The "latest" logic lives in one place (the helper)
- Flexibility: Can use helper directly (simple) or macro (flexible)
- No breaking changes: Gradual migration at model's own pace

**Related Macro**: `dbt/ff_data_transform/macros/get_latest_snapshot.sql` (existing helper to reference)

## Testing

1. **Compilation test**:

   ```bash
   cd dbt/ff_data_transform
   uv run dbt compile
   ```

2. **Verify strategies**:

   - Add test calls to a staging model temporarily
   - Compile and verify SQL output matches expected filter logic
   - Remove test calls after validation

3. **Check macro resolution**:

   ```bash
   uv run dbt compile --select stg_nflverse__ff_opportunity
   # Verify compiled SQL in target/compiled/
   ```

## Implementation Summary

**Completed**: 2025-11-09\
**Commit**: `609bc9c` - feat(snapshot): implement P1-001 - snapshot_selection_strategy macro

### What Was Delivered

1. **Macro Created**: `dbt/ff_data_transform/macros/snapshot_selection.sql` (71 lines)

   - Implements all three snapshot selection strategies
   - Comprehensive inline documentation and usage examples
   - Calls existing `latest_snapshot_only()` helper for consistency

2. **Three Strategies Implemented**:

   - `latest_only`: Filters to MAX(dt) from source (calls existing helper)
   - `baseline_plus_latest`: Selects baseline + latest for historical continuity
   - `all`: No filter for backfills and debugging

3. **Testing Results**:

   - Compilation: PASS (`dbt compile` successful)
   - Macro resolution: PASS (verified with `stg_nflverse__ff_opportunity`)
   - Strategy testing: PASS (all three strategies expand correctly)

4. **Tracking Updated**:

   - `00-OVERVIEW.md`: P1-001 marked complete (2/49 tickets done, 4%)
   - `tasks_checklist_v_2_0.md`: Phase 1 macro implementation tasks complete

### Foundation for Phase 1

This macro is the foundation for all subsequent staging model updates (P1-002 through P1-016), enabling:

- Parameterizable snapshot selection
- Elimination of hardcoded dates
- Consistent snapshot governance pattern across all models

**Status**: COMPLETE - Ready for staging model updates

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Design Decision #1 (lines 48-89)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 1 Macro Implementation (lines 32-38)
- Existing macro: `dbt/ff_data_transform/macros/get_latest_snapshot.sql`
