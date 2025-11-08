# Ticket P1-006: Performance Profiling and Baseline Documentation

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (2 hours)\
**Dependencies**: P1-002, P1-003, P1-004 (all three staging models must be updated first)

## Objective

Profile query performance of all three updated NFLverse staging models using `EXPLAIN` to measure query impact and document query times to establish baseline for future optimization decisions.

## Context

After updating all three NFLverse staging models to use the new `snapshot_selection_strategy` macro, we need to establish performance baselines:

- **player_stats** and **snap_counts**: Use `baseline_plus_latest` strategy (UNION of two partitions)
- **ff_opportunity**: Uses `latest_only` strategy (single partition)

This ticket establishes performance baselines so we can:

1. Understand current query performance with new macro
2. Identify if materialization is needed (threshold: >30s query time)
3. Monitor for degradation in future updates
4. Compare UNION queries (baseline+latest) vs single partition (latest_only)

The plan calls for using `union_by_name=true` to handle schema drift, which may also impact performance.

## Tasks

### Profile All Three Models

- [ ] Run `EXPLAIN` on `stg_nflverse__player_stats` (after P1-002 changes)

  - [ ] Measure compilation time
  - [ ] Measure execution time
  - [ ] Document query plan (UNION strategy, filter pushdown, etc.)

- [ ] Run `EXPLAIN` on `stg_nflverse__snap_counts` (after P1-003 changes)

  - [ ] Measure compilation time
  - [ ] Measure execution time
  - [ ] Document query plan

- [ ] Run `EXPLAIN` on `stg_nflverse__ff_opportunity` (after P1-004 changes)

  - [ ] Measure compilation time
  - [ ] Measure execution time
  - [ ] Document query plan (single partition - should be fastest)
  - [ ] Compare to baseline+latest models to quantify UNION overhead

### Assess Materialization Need

- [ ] Compare query times to 30s threshold
- [ ] Consider materialization if any query exceeds threshold
- [ ] Document recommendation in findings

### Schema Drift Handling

- [ ] Verify `union_by_name=true` in models where schema can evolve
- [ ] Monitor null rates by column (baseline)
- [ ] Document schema evolution patterns observed

### Document Findings

- [ ] Create `docs/implementation/multi_source_snapshot_governance/performance_baseline.md`
- [ ] Include query times, plans, and recommendations
- [ ] Add materialization decision criteria

## Acceptance Criteria

- [ ] Performance baseline documented for all three models (player_stats, snap_counts, ff_opportunity)
- [ ] Query plans captured and analyzed
- [ ] UNION overhead quantified (baseline+latest vs latest_only comparison)
- [ ] Materialization recommendation made (if needed)
- [ ] Schema drift handling verified

## Implementation Notes

**Profiling Commands**:

```bash
cd dbt/ff_data_transform

# Profile player_stats
uv run dbt run --select stg_nflverse__player_stats --profiles-dir .

# Get query plan
cat target/compiled/ff_data_transform/models/staging/nflverse/stg_nflverse__player_stats.sql

# Run EXPLAIN in DuckDB
duckdb target/dev.duckdb << EOF
EXPLAIN ANALYZE
<paste compiled SQL here>
EOF
```

**What to Look For**:

1. **Scan Strategy**: Are both partitions being scanned efficiently?
2. **Filter Pushdown**: Is DuckDB pushing the dt filter down to file scans?
3. **UNION Overhead**: How much time is spent combining partitions?
4. **Memory Usage**: Are queries staying within reasonable memory limits?

**Materialization Threshold** (from plan):

- If query time > 30s, consider materialized view or incremental model
- Document decision and rationale

**Schema Drift Configuration**:

Verify models include `union_by_name=true` in read_parquet calls where applicable:

```sql
select * from read_parquet(
    '{{ env_var("RAW_NFLVERSE_WEEKLY_GLOB", "data/raw/nflverse/weekly/dt=*/*.parquet") }}',
    union_by_name=true  -- Handle schema evolution
)
```

**Performance Baseline Document Structure**:

```markdown
# Performance Baseline - Phase 1 Foundation

## Date
2025-11-07

## Models Profiled
- stg_nflverse__player_stats (baseline_plus_latest)
- stg_nflverse__snap_counts (baseline_plus_latest)
- stg_nflverse__ff_opportunity (latest_only)

## Results

### stg_nflverse__player_stats
- Strategy: baseline_plus_latest (UNION of 2 partitions)
- Compilation time: X seconds
- Execution time: X seconds
- Row count: X rows
- Partitions scanned: 2 (2025-10-01 + 2025-10-27)
- Query plan: [UNION strategy, filter pushdown details]
- Recommendation: [none|consider materialization]

### stg_nflverse__snap_counts
- Strategy: baseline_plus_latest (UNION of 2 partitions)
- [same structure]

### stg_nflverse__ff_opportunity
- Strategy: latest_only (single partition)
- Compilation time: X seconds (expected: fastest)
- Execution time: X seconds (expected: fastest)
- Row count: X rows
- Partitions scanned: 1 (latest only)
- Query plan: [single scan strategy]
- Recommendation: [baseline for comparison]

## Performance Comparison

### UNION Overhead
- baseline_plus_latest vs latest_only execution time difference
- Memory usage comparison
- Query plan differences

## Observations
- [Any notable patterns or issues]
- UNION overhead acceptable? (<10% overhead is good)

## Recommendations
- [Actionable next steps]
- Materialization needed? (if any query >30s)
```

## Testing

1. **Run profiling queries**:

   ```bash
   cd dbt/ff_data_transform
   time uv run dbt run --select stg_nflverse__player_stats
   time uv run dbt run --select stg_nflverse__snap_counts
   time uv run dbt run --select stg_nflverse__ff_opportunity
   ```

2. **Check compiled SQL**:

   ```bash
   cat target/compiled/ff_data_transform/models/staging/nflverse/stg_nflverse__player_stats.sql
   # Verify UNION pattern is correct
   ```

3. **Run EXPLAIN ANALYZE**:

   ```bash
   duckdb target/dev.duckdb
   # Copy compiled SQL and run:
   EXPLAIN ANALYZE <compiled SQL>;
   ```

4. **Compare to baseline**:

   - Document current row counts
   - Compare to pre-change row counts (should match)
   - Verify no data loss or duplication

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 1 Activities (lines 288-298)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 1 Performance (lines 66-72)
- Risk: Performance degradation from UNION queries (plan line 685)
