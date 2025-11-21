# CI Transition Plan — GitHub Actions to Prefect

**Last Updated**: 2025-11-20
**Status**: Planning Only (Execution Deferred)

## Overview

This document describes the planned transition from GitHub Actions to Prefect as the primary orchestration system.

**Important**: This is planning documentation. Actual execution is deferred to future work after Phase 4 (Prefect flows) is complete.

## Parallel Run Strategy

### Week 1: Deploy Prefect Alongside GH Actions

**Objectives**:

- Add Prefect flows to deployment
- Keep GitHub Actions running unchanged
- Begin collecting metrics

**Actions**:

- [ ] Deploy Prefect flows (manual trigger initially)
- [ ] Run both systems in parallel (non-blocking)
- [ ] Collect metrics: row counts, timing, failure rates
- [ ] Log outputs from both systems for comparison

### Week 2: Compare and Validate

**Objectives**:

- Compare outputs daily
- Monitor for discrepancies
- Adjust Prefect flows if issues found

**Actions**:

- [ ] Daily comparison: row counts match? (±1% acceptable)
- [ ] Compare manifests (lineage fields populated?)
- [ ] Check timing (Prefect faster/slower?)
- [ ] Monitor for failures in either system

**Comparison Script**:

```bash
# Compare outputs
uv run python tools/compare_pipeline_outputs.py \
    --source1 data/raw/nflverse \
    --source2 data/raw/nflverse_prefect \
    --output comparison_report.json
```

### Week 3: Cut-Over Decision

**Objectives**:

- Decide if Prefect ready for primary
- Cut over if validation passes
- Keep GH Actions as backup

**Decision Criteria** (see section below):

- All validation criteria met?
- Team approval?
- Go/no-go decision

**If GO**:

- [ ] Disable GitHub Actions schedules (keep workflows, don't delete)
- [ ] Enable Prefect scheduled deployments
- [ ] Monitor closely for 48 hours

**If NO-GO**:

- [ ] Continue parallel run for another week
- [ ] Address issues found
- [ ] Repeat validation

### Week 4+: Monitoring Period

**Objectives**:

- Monitor Prefect stability
- Keep GH Actions available for rollback
- After 2+ weeks, consider archiving GH Actions

**Actions**:

- [ ] Daily monitoring (first week)
- [ ] Weekly monitoring (ongoing)
- [ ] Document any issues and resolutions
- [ ] After 2+ weeks stable: Archive (don't delete) GH Actions workflows

## Cut-Over Validation Criteria

### Must Pass All Criteria

1. **Row Count Parity**:

   - Prefect row counts match GH Actions (±1% acceptable for sampling variance)
   - Verified across all 5 sources
   - No data loss or duplication

2. **Manifest Quality**:

   - All required lineage fields populated (`loader_path`, `source_version`, `row_count`, `asof_datetime`)
   - Manifests valid JSON
   - Match expected schema

3. **Query Performance**:

   - dbt model execution time no worse than baseline (±10% acceptable)
   - No query timeouts
   - Memory usage within limits

4. **Freshness Tests**:

   - No freshness test failures for 3+ consecutive days
   - All sources updating on expected schedule
   - No stale data incidents

5. **Team Approval**:

   - Team review meeting after 1-2 week parallel run
   - All stakeholders approve cut-over
   - Unanimous approval required

### Validation Queries

```sql
-- Row count comparison
SELECT
    source,
    dataset,
    snapshot_date,
    SUM(row_count) as total_rows
FROM snapshot_registry
WHERE status = 'current'
GROUP BY source, dataset, snapshot_date
ORDER BY source, dataset;

-- Compare to actual files
SELECT
    COUNT(*) as actual_rows
FROM read_parquet('data/raw/nflverse/weekly/dt=2025-10-27/*.parquet');
```

## Rollback Procedures

### Scenario 1: Prefect Crashes During Parallel Run

**Symptoms**: Prefect flows failing, no data loading

**Actions**:

1. [ ] Verify GitHub Actions still running (should be unaffected)
2. [ ] Investigate Prefect failure (check logs)
3. [ ] Disable Prefect deployments if needed
4. [ ] Debug locally before retrying
5. [ ] No user impact (GH Actions continues)

### Scenario 2: Data Quality Regression Detected

**Symptoms**: Row counts mismatch, validation failures, query errors

**Actions**:

1. [ ] Immediately stop Prefect deployments
2. [ ] Compare outputs to identify issue
3. [ ] Re-enable GitHub Actions if needed (should still be running)
4. [ ] Debug Prefect locally
5. [ ] Fix issue before retrying parallel run

### Scenario 3: Performance Degradation

**Symptoms**: Prefect runs >2x slower than GH Actions

**Actions**:

1. [ ] Continue parallel run (not critical)
2. [ ] Profile Prefect flows (identify bottleneck)
3. [ ] Optimize hot paths
4. [ ] Re-benchmark
5. [ ] Consider infrastructure scaling

### Scenario 4: Post-Cut-Over Failure

**Symptoms**: Prefect fails after becoming primary (GH Actions disabled)

**Actions**:

1. [ ] Re-enable GitHub Actions schedules immediately
2. [ ] Disable Prefect deployments
3. [ ] Validate data integrity (compare manifests)
4. [ ] Run `dbt source freshness` to check staleness
5. [ ] Debug Prefect locally
6. [ ] Do not retry cut-over until 1+ week stable locally

**Rollback Script**:

```bash
# Re-enable GH Actions
gh workflow enable data-pipeline.yml
gh workflow enable ingest_google_sheets.yml

# Disable Prefect deployments
prefect deployment pause --all

# Validate data integrity
uv run python tools/validate_manifests.py --sources all --fail-on-gaps
```

## Comparison Process

### Automated Diff

Create `tools/compare_pipeline_outputs.py`:

```python
#!/usr/bin/env python3
"""Compare pipeline outputs (GH Actions vs Prefect)."""

import json
from pathlib import Path
import polars as pl

def compare_manifests(gh_path, prefect_path):
    """Compare manifest files."""
    with open(gh_path) as f:
        gh_manifest = json.load(f)
    with open(prefect_path) as f:
        prefect_manifest = json.load(f)

    discrepancies = []

    # Compare row counts
    if gh_manifest['row_count'] != prefect_manifest['row_count']:
        discrepancies.append({
            'field': 'row_count',
            'gh_value': gh_manifest['row_count'],
            'prefect_value': prefect_manifest['row_count']
        })

    return discrepancies

def compare_parquet_files(gh_path, prefect_path):
    """Compare actual Parquet data."""
    gh_df = pl.read_parquet(gh_path)
    prefect_df = pl.read_parquet(prefect_path)

    return {
        'gh_rows': len(gh_df),
        'prefect_rows': len(prefect_df),
        'match': len(gh_df) == len(prefect_df)
    }
```

### Manual Review Process

Weekly review meeting:

1. Review automated comparison report
2. Spot-check data samples (10-20 rows per source)
3. Review error logs from both systems
4. Discuss findings and blockers
5. Go/no-go decision for next week

## Decision Framework

```
┌─────────────────────────────────┐
│  All criteria met?              │
│  - Row count parity             │
│  - Manifest quality             │
│  - Performance acceptable       │
│  - Freshness tests passing      │
└────────┬────────────────────────┘
         │
    ┌────▼────┐
    │  Yes    │
    └────┬────┘
         │
    ┌────▼────────────────────────┐
    │  Team approval?             │
    └────┬────────────────────────┘
         │
    ┌────▼────┐
    │  Yes    │
    └────┬────┘
         │
    ┌────▼──────────┐
    │  CUT OVER     │
    └───────────────┘


    ┌────▼────┐
    │  No     │
    └────┬────┘
         │
    ┌────▼─────────────────────────┐
    │  Extend parallel run 1 week  │
    │  Address issues found        │
    └──────────────────────────────┘
```

## Post-Cut-Over Monitoring

### First 48 Hours (Critical)

- [ ] Check every 4 hours
- [ ] Monitor Prefect UI for failures
- [ ] Run freshness checks: `dbt source freshness`
- [ ] Validate row counts: `tools/validate_manifests.py`

### First Week

- [ ] Check daily
- [ ] Review error logs
- [ ] Compare to baseline metrics
- [ ] Address any issues immediately

### Ongoing

- [ ] Check 2-3x per week
- [ ] Monthly performance review
- [ ] Quarterly architecture review

## References

- Prefect flows: `src/flows/`
- GitHub Actions: `.github/workflows/`
- Orchestration architecture: `docs/ops/orchestration_architecture.md`
- Validation tool: `tools/validate_manifests.py`
