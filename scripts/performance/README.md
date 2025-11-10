# Performance Analysis Suite

This directory contains comprehensive performance analysis and benchmarking tools for the FF Analytics project.

## Quick Start

```bash
# Run full performance analysis
cd /Users/jason/code/ff_analytics
uv run python scripts/performance/comprehensive_benchmark.py
uv run python scripts/performance/scalability_stress_test.py
./scripts/performance/dbt_performance_test.sh

# View results
cat scripts/performance/PERFORMANCE_ANALYSIS_REPORT.md
```

## Analysis Summary (2025-11-09)

### Overall Performance: ✅ EXCELLENT

- **Query Latency:** \<100ms (50x faster than 5s target)
- **Scalability:** Handles 10-year projection (13M rows) with \<25ms degradation
- **Concurrency:** 3 simultaneous queries in 97ms
- **Memory:** Peak 983 MB (well within 8GB target)
- **dbt Pipeline:** 27 seconds full run

### Key Findings

1. **VARCHAR player_key joins are 20.8% FASTER than INT** ✅
2. Crosswalk join overhead is negligible (+0.6ms absolute)
3. Current architecture scales to 10-year horizon without optimization
4. No performance bottlenecks identified

## Files in This Directory

### Reports

- **`PERFORMANCE_ANALYSIS_REPORT.md`** - Comprehensive performance analysis report (main deliverable)
- **`README.md`** - This file

### Test Scripts

| Script                        | Purpose                        | Runtime |
| ----------------------------- | ------------------------------ | ------- |
| `comprehensive_benchmark.py`  | Query performance benchmarks   | ~30s    |
| `scalability_stress_test.py`  | 10-year scalability projection | ~15s    |
| `dbt_performance_test.sh`     | dbt transformation timing      | ~2min   |
| `profile_analysis.py`         | Database statistics profiling  | ~10s    |
| `db_analysis.sql`             | Raw SQL analysis queries       | Manual  |
| `query_performance_tests.sql` | Manual query tests             | Manual  |

### Results (JSON)

| File                       | Contents                     |
| -------------------------- | ---------------------------- |
| `benchmark_results.json`   | Query benchmark summary      |
| `detailed_metrics.json`    | Individual query metrics     |
| `scalability_results.json` | 10-year projection analysis  |
| `baseline_metrics.json`    | Database baseline statistics |

## Usage

### Run Individual Tests

```bash
# Query performance benchmarks
uv run python scripts/performance/comprehensive_benchmark.py

# Scalability projection
uv run python scripts/performance/scalability_stress_test.py

# dbt transformation timing
./scripts/performance/dbt_performance_test.sh

# Database profiling
uv run python scripts/performance/profile_analysis.py

# Manual SQL queries
duckdb dbt/ff_data_transform/target/dev.duckdb < scripts/performance/db_analysis.sql
```

### Run Full Analysis

```bash
# Run all tests
uv run python scripts/performance/comprehensive_benchmark.py && \
uv run python scripts/performance/scalability_stress_test.py && \
./scripts/performance/dbt_performance_test.sh

# View report
cat scripts/performance/PERFORMANCE_ANALYSIS_REPORT.md
```

## Test Coverage

### Database Performance

- ✅ VARCHAR vs INT join performance
- ✅ Crosswalk join overhead
- ✅ Large fact table aggregations (7.8M rows)
- ✅ Window function performance
- ✅ Analytics mart query patterns
- ✅ Concurrent query handling

### Transformation Performance

- ✅ Full dbt pipeline timing
- ✅ Large staging model (1,568 LOC unpivot)
- ✅ Fact table rebuild (7.8M rows)
- ✅ Complex mart model (1,017 LOC)

### Scalability

- ✅ 10-year data volume projection (13M rows)
- ✅ Performance degradation estimation
- ✅ Memory usage patterns
- ✅ Database size growth

### I/O Performance

- ✅ Parquet read throughput
- ✅ DuckDB memory management
- ✅ Concurrent file access

## Benchmark Results Summary

### Query Performance (7.8M rows)

| Query Type         | Execution Time | Status               |
| ------------------ | -------------- | -------------------- |
| Simple Aggregation | 4.7 ms         | ✅                   |
| Complex Multi-Stat | 63.5 ms        | ✅                   |
| Full Table Scan    | 37.4 ms        | ✅                   |
| Window Functions   | 67.4 ms        | ✅                   |
| Mart Query         | 52.9 ms        | ✅                   |
| VARCHAR Join       | 29.6 ms        | ✅ (faster than INT) |
| Crosswalk Join     | 2.8 ms         | ✅                   |

### dbt Transformation

| Model           | Time |
| --------------- | ---- |
| Full dbt run    | 27s  |
| Staging unpivot | 3s   |
| Fact table      | 15s  |
| Complex mart    | 3s   |

### Scalability (10-Year Projection)

| Metric     | Current | Projected    |
| ---------- | ------- | ------------ |
| Rows       | 7.9M    | 13.2M (1.7x) |
| DB Size    | 1.3 GB  | 2.2 GB       |
| Query Time | \<100ms | \<125ms      |
| Status     | ✅      | ✅           |

## Performance Targets

| Target           | Threshold | Actual       | Status |
| ---------------- | --------- | ------------ | ------ |
| Query latency    | \<5s      | **\<100ms**  | ✅     |
| dbt run          | \<15min   | **27s**      | ✅     |
| Memory usage     | \<8GB     | **\<1GB**    | ✅     |
| Concurrent users | 3-5       | **3 tested** | ✅     |

## Recommendations

### Priority 1: No Critical Optimizations Needed ✅

Current performance exceeds all targets. No immediate action required.

### Priority 2: Future Monitoring

1. **Add query performance monitoring** when data reaches 15M rows
2. **Consider incremental dbt models** when full run exceeds 5 minutes
3. **Enable DuckDB result caching** for Jupyter notebook workflows

### Priority 3: Caching Strategy (Future)

- Implement incremental materialization for fact tables (at 20M+ rows)
- Enable DuckDB persistent query result cache
- Monitor crosswalk table growth (threshold: 50,000 rows)

## Phase 1 Architecture Validation

All Phase 1 concerns have been addressed:

1. ✅ **VARCHAR player_key joins:** FASTER than INT (-20.8%)
2. ✅ **Crosswalk join overhead:** Negligible (+0.6ms absolute)
3. ✅ **Large staging model:** Excellent performance (3s for 1,568 LOC)
4. ✅ **Concurrent DuckDB access:** No contention
5. ✅ **10-year scalability:** All queries \<100ms with 1.7x growth

## Next Steps

1. Review **PERFORMANCE_ANALYSIS_REPORT.md** for detailed findings
2. No immediate performance optimizations required
3. Re-run analysis when database reaches 15M rows or 3GB size
4. Monitor dbt run times; implement incremental models if exceeds 5 minutes

## Contact

For questions about these performance tests, see:

- **Main Report:** `PERFORMANCE_ANALYSIS_REPORT.md`
- **dbt Performance:** `dbt/ff_data_transform/CLAUDE.md`
- **Project README:** `../../README.md`

______________________________________________________________________

**Last Updated:** 2025-11-09
**Database Size:** 1.3 GB (7.9M rows)
**Performance Status:** ✅ EXCELLENT
