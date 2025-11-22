# Ticket P4-007: Production Hardening (Retry & Timeout Configuration)

**Phase**: 4 - Orchestration\
**Status**: TODO\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P4-002 through P4-006 (all flows must be complete)\
**Priority**: 🔴 **CRITICAL - Required before production deployment**

## Objective

Add retry and timeout configuration to all Prefect tasks that interact with external APIs or perform long-running operations to handle transient failures gracefully.

## Context

Senior developer review identified that all P4 flows are missing retry and timeout configuration despite the specification calling for it. This creates brittleness for production deployments where transient network issues, API rate limits, or hung processes could unnecessarily fail flows.

**Review Finding**: "No Prefect task-level retry configuration despite spec calling for it" (see code review section 1)

## Tasks

### Retry Configuration

- [ ] Add retries to **Google Sheets API tasks** (P4-002):

  - `create_gspread_client`: `retries=3, retry_delay_seconds=60`
  - `download_tabs_to_csv`: `retries=2, retry_delay_seconds=30`

- [ ] Add retries to **Sleeper API tasks** (P4-006):

  - `fetch_sleeper_data`: `retries=3, retry_delay_seconds=60`

- [ ] Add retries to **KTC API tasks** (P4-004):

  - `fetch_ktc_data`: `retries=2, retry_delay_seconds=30`

- [ ] Add retries to **NFLverse fetch tasks** (P4-003):

  - `fetch_nflverse_data`: `retries=2, retry_delay_seconds=60`

### Timeout Configuration

- [ ] Add timeouts to **R projections tasks** (P4-005):

  - `run_projections_scraper`: `timeout=600` (10 minutes)

- [ ] Add timeouts to **NFLverse fetch tasks** (P4-003):

  - `fetch_nflverse_data`: `timeout=300` (5 minutes per dataset)

- [ ] Add timeouts to **Sleeper fetch tasks** (P4-006):

  - `fetch_sleeper_data`: `timeout=180` (3 minutes)

### Documentation

- [ ] Document retry/timeout patterns in flow docstrings
- [ ] Update SPEC v2.3 checklist with production hardening status

## Acceptance Criteria

- [ ] All external API tasks have retry configuration (2-3 retries with exponential backoff)
- [ ] All long-running tasks have timeout configuration (3-10 minutes based on expected duration)
- [ ] Retries use appropriate delays (30-60 seconds to avoid rate limit issues)
- [ ] Validation tasks do NOT have retries (fast, deterministic operations)
- [ ] Flows recover gracefully from transient failures during testing

## Implementation Notes

### Retry Pattern

```python
# External API calls - aggressive retries
@task(
    name="fetch_external_data",
    retries=3,
    retry_delay_seconds=60,  # 1 minute between retries
    tags=["external_api"]
)

# File I/O operations - limited retries
@task(
    name="download_file",
    retries=2,
    retry_delay_seconds=30,
    tags=["io"]
)

# Validation/computation - no retries (deterministic)
@task(name="validate_data")  # No retry needed
```

### Timeout Pattern

```python
# Long-running operations
@task(
    name="run_r_script",
    timeout=600,  # 10 minutes
    tags=["long_running"]
)

# Medium operations
@task(
    name="fetch_nflverse",
    timeout=300,  # 5 minutes
    tags=["fetch"]
)
```

### Files to Modify

1. `src/flows/parse_league_sheet_flow.py` (lines 42, 87)
2. `src/flows/nfl_data_pipeline.py` (line 47)
3. `src/flows/ktc_pipeline.py` (line 45)
4. `src/flows/ffanalytics_pipeline.py` (line 41)
5. `src/flows/sleeper_pipeline.py` (line 53)

### Guidance from Spec

Reference: `docs/spec/prefect_dbt_sources_migration_20251026.md`

- Lines 124-127: Task retry example
- Lines 172-174: Task timeout example
- Lines 464-466: Exponential backoff pattern

## Testing

### Manual Testing

```bash
# Test retry behavior with network issues
# 1. Start flow with network enabled
# 2. Kill network during external API call
# 3. Restore network
# 4. Verify flow retries and succeeds

# Test timeout behavior
# 1. Mock long-running operation (sleep)
# 2. Verify flow times out after configured duration
```

### Test Scenarios

1. **Transient network failure**: Flow retries and succeeds on 2nd attempt
2. **API rate limit**: Flow waits 60s and retries successfully
3. **Hung R process**: Flow times out after 10 minutes and fails gracefully
4. **Validation failure**: Flow fails immediately without retry (expected)

## References

- Code Review: Senior dev review section "Missing Retry Configuration"
- Spec: `docs/spec/prefect_dbt_sources_migration_20251026.md` (lines 124-127, 172-174)
- Prefect Docs: https://docs.prefect.io/latest/concepts/tasks/#retries

## Success Metrics

- [ ] Zero transient failures in production (network, API rate limits)
- [ ] All flows complete within expected time windows
- [ ] No hung processes requiring manual intervention
- [ ] Graceful degradation on persistent failures (clear error messages)

## Completion Notes

**Implementation Date**: TBD\
**Tests**: TBD

______________________________________________________________________

**Note**: This ticket is marked **CRITICAL** because production deployment without retry/timeout configuration will result in brittle flows that fail unnecessarily on transient issues. Should be completed before any automated scheduling is enabled.
