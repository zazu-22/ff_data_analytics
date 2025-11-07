# Ticket CC-001: Create Comparison Testing Framework

**Phase**: Cross-Cutting\
**Estimated Effort**: Medium (2-3 hours)\
**Dependencies**: P1-002, P1-003 (models updated for comparison)

## Objective

Create regression comparison queries and testing framework to validate that snapshot selection changes don't alter row counts or data integrity.

## Context

When migrating from hardcoded dates to macro-based selection, we need to prove no data loss or duplication occurred. This framework provides automated comparison tests.

## Tasks

- [ ] Create regression comparison queries (row count, min/max/sum of key stats)
- [ ] Create comparison test script
- [ ] Run comparisons before/after macro changes
- [ ] Document comparison test process
- [ ] Add to CI pipeline (optional)

## Acceptance Criteria

- [ ] Comparison queries created and tested
- [ ] Row counts match pre-change baseline
- [ ] Statistical checks pass (min/max/sum unchanged)
- [ ] No data loss or duplication detected

## Implementation Notes

**Comparison Queries**:

```sql
-- Row count comparison
WITH pre_change AS (
    SELECT 'pre_change' as version, COUNT(*) as row_count
    FROM read_parquet('data/raw/nflverse/weekly/dt=2025-10-27/*.parquet')
),
post_change AS (
    SELECT 'post_change' as version, COUNT(*) as row_count
    FROM stg_nflverse__player_stats  -- After macro change
)
SELECT * FROM pre_change
UNION ALL
SELECT * FROM post_change;

-- Statistical validation
SELECT
    'player_stats' as dataset,
    MIN(pass_yds) as min_pass_yds,
    MAX(pass_yds) as max_pass_yds,
    SUM(pass_yds) as total_pass_yds,
    COUNT(DISTINCT player_id) as unique_players
FROM stg_nflverse__player_stats;
```

**Test Script**: Create `tests/test_snapshot_migration_regression.py`

## Testing

```bash
uv run pytest tests/test_snapshot_migration_regression.py -v
```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Cross-Cutting (lines 571-578)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Comparison Testing (lines 574-579)
