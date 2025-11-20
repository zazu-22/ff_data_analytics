# Ticket P2-006B: Add Freshness Validation to validate_manifests.py

**Phase**: 2 - Governance\
**Status**: COMPLETE\
**Estimated Effort**: Small (2-3 hours)\
**Dependencies**: P2-005 (validate_manifests.py must exist - COMPLETE)\
**Replaces**: P2-006 (dbt source freshness - cancelled due to architectural incompatibility)

## Objective

Extend `tools/validate_manifests.py` to validate snapshot freshness (data age) in addition to existing integrity checks, providing a pre-dbt safety net that catches stale data before model execution.

## Context

**Why P2-006 was cancelled:**
P2-006 attempted to use `dbt source freshness`, which requires database tables. This project uses external Parquet files read via `read_parquet()`, making dbt's built-in freshness tests architecturally incompatible.

**Why we still need freshness validation:**
P2-005's `validate_manifests.py` validates snapshot integrity (files exist, row counts match, metadata complete) but does NOT check if snapshots are stale. We need to detect when data hasn't been updated within expected thresholds.

**Solution:**
Add freshness validation to the existing `validate_manifests.py` tool, consolidating both integrity and freshness checks in one place.

## Tasks

### Add Freshness Validation Logic

- [ ] Add `--freshness-warn-days` and `--freshness-error-days` CLI options
- [ ] Implement snapshot age calculation (current date - snapshot_date)
- [ ] Add age threshold checks (warn/error based on source type)
- [ ] Update validation results to include freshness status
- [ ] Preserve existing integrity checks (no breaking changes)

### Add Source-Specific Thresholds

- [ ] Support per-source threshold configuration
- [ ] Default thresholds from original P2-006 plan:
  - nflverse: warn 2 days, error 7 days
  - sheets: warn 1 day, error 7 days
  - sleeper: warn 1 day, error 7 days
  - ffanalytics: warn 2 days, error 7 days
  - ktc: warn 5 days, error 14 days

### Update Output and Reporting

- [ ] Add "freshness" status to text output (FRESH / STALE-WARN / STALE-ERROR)
- [ ] Include age in days in validation messages
- [ ] Update JSON output to include freshness metadata
- [ ] Fail with exit code 1 if any snapshots exceed error threshold (with --fail-on-gaps)

### Update Documentation

- [ ] Update `tools/CLAUDE.md` with freshness validation examples
- [ ] Document threshold selection rationale
- [ ] Add troubleshooting guidance for stale data scenarios

## Acceptance Criteria

- [ ] Tool validates snapshot age against configurable thresholds
- [ ] Per-source thresholds supported (different warn/error days per source)
- [ ] Freshness warnings/errors reported clearly in output
- [ ] CI integration works: `--fail-on-gaps` fails if data stale
- [ ] Existing integrity checks still work (backwards compatible)
- [ ] Documentation updated with freshness validation examples

## Implementation Notes

### Freshness Validation Function

Add to `tools/validate_manifests.py`:

```python
from datetime import datetime, timedelta

def check_snapshot_freshness(
    snapshot_date: str,
    warn_threshold_days: int,
    error_threshold_days: int
) -> dict:
    """Check if snapshot is within freshness thresholds.

    Returns:
        {
            'age_days': int,
            'status': 'fresh' | 'stale-warn' | 'stale-error',
            'message': str
        }
    """
    try:
        snapshot_dt = datetime.strptime(snapshot_date, "%Y-%m-%d")
    except ValueError:
        return {
            'age_days': None,
            'status': 'error',
            'message': f"Invalid snapshot_date format: {snapshot_date}"
        }

    age_days = (datetime.now() - snapshot_dt).days

    if age_days > error_threshold_days:
        status = 'stale-error'
        message = f"Snapshot STALE (ERROR): {age_days} days old (threshold: {error_threshold_days} days)"
    elif age_days > warn_threshold_days:
        status = 'stale-warn'
        message = f"Snapshot STALE (WARN): {age_days} days old (threshold: {warn_threshold_days} days)"
    else:
        status = 'fresh'
        message = f"Snapshot FRESH: {age_days} days old"

    return {
        'age_days': age_days,
        'status': status,
        'message': message
    }
```

### Updated CLI Interface

```python
@click.command()
@click.option("--sources", default="all", help='Comma-separated sources or "all"')
@click.option("--fail-on-gaps", is_flag=True, help="Exit with code 1 if validation fails")
@click.option("--output-format", type=click.Choice(["text", "json"]), default="text")
@click.option("--registry", default="dbt/ff_data_transform/seeds/snapshot_registry.csv")
# NEW freshness options
@click.option("--check-freshness", is_flag=True, help="Enable freshness validation")
@click.option("--freshness-warn-days", type=int, help="Warn if snapshot older than N days")
@click.option("--freshness-error-days", type=int, help="Error if snapshot older than N days")
@click.option("--freshness-config", type=click.Path(exists=True),
              help="Path to freshness config YAML (per-source thresholds)")
def main(sources, fail_on_gaps, output_format, registry,
         check_freshness, freshness_warn_days, freshness_error_days, freshness_config):
    """Validate snapshot manifests against registry."""
    # ... existing code ...

    # Load freshness config if provided
    freshness_thresholds = {}
    if freshness_config:
        import yaml
        with open(freshness_config) as f:
            freshness_thresholds = yaml.safe_load(f)

    # Validate each entry
    for row in registry_df.iter_rows(named=True):
        # Existing integrity validation
        result = validate_snapshot(...)

        # NEW: Freshness validation
        if check_freshness:
            # Get thresholds (per-source config or global defaults)
            source = row['source']
            warn_days = freshness_thresholds.get(source, {}).get('warn_days', freshness_warn_days)
            error_days = freshness_thresholds.get(source, {}).get('error_days', freshness_error_days)

            freshness_result = check_snapshot_freshness(
                snapshot_date=row['snapshot_date'],
                warn_threshold_days=warn_days,
                error_threshold_days=error_days
            )

            result['freshness'] = freshness_result
```

### Freshness Configuration File (Optional)

Create `config/snapshot_freshness_thresholds.yaml`:

```yaml
# Freshness thresholds by source (days)
# Based on expected update cadence

nflverse:
  warn_days: 2
  error_days: 7
  rationale: "Weekly in-season, updates within 2 days post-games"

sheets:
  warn_days: 1
  error_days: 7
  rationale: "Daily roster/transaction updates during season"

sleeper:
  warn_days: 1
  error_days: 7
  rationale: "Daily league activity updates"

ffanalytics:
  warn_days: 2
  error_days: 7
  rationale: "Weekly projection updates during season"

ktc:
  warn_days: 5
  error_days: 14
  rationale: "Sporadic market valuations updates"
```

### Updated Output Examples

**Text output with freshness:**

```
Snapshot Manifest Validation (with Freshness)
==================================================

Validated: 22/24 snapshots (integrity)
Fresh: 18/24 snapshots (within thresholds)

Freshness Issues (4):

  nflverse.weekly [2025-11-10] STALE (WARN):
    - Snapshot STALE (WARN): 10 days old (threshold: 2 days)

  sheets.transactions [2025-11-15] FRESH:
    - Snapshot FRESH: 5 days old

  ktc.assets [2025-10-01] STALE (ERROR):
    - Snapshot STALE (ERROR): 50 days old (threshold: 14 days)
```

**JSON output with freshness:**

```json
{
  "results": [
    {
      "source": "nflverse",
      "dataset": "weekly",
      "snapshot_date": "2025-11-10",
      "valid": true,
      "issues": [],
      "freshness": {
        "age_days": 10,
        "status": "stale-warn",
        "message": "Snapshot STALE (WARN): 10 days old (threshold: 2 days)"
      }
    }
  ]
}
```

## Testing

1. **Test freshness validation with default thresholds**:

   ```bash
   uv run python tools/validate_manifests.py \
       --sources nflverse \
       --check-freshness \
       --freshness-warn-days 2 \
       --freshness-error-days 7
   ```

2. **Test with per-source config file**:

   ```bash
   uv run python tools/validate_manifests.py \
       --sources all \
       --check-freshness \
       --freshness-config config/snapshot_freshness_thresholds.yaml
   ```

3. **Test CI integration (fail on stale data)**:

   ```bash
   uv run python tools/validate_manifests.py \
       --sources nflverse,sheets \
       --check-freshness \
       --freshness-config config/snapshot_freshness_thresholds.yaml \
       --fail-on-gaps

   echo $?  # Should be 1 if any snapshots stale
   ```

4. **Test JSON output**:

   ```bash
   uv run python tools/validate_manifests.py \
       --sources all \
       --check-freshness \
       --freshness-config config/snapshot_freshness_thresholds.yaml \
       --output-format json \
       > freshness_report.json

   cat freshness_report.json | jq '.results[] | select(.freshness.status == "stale-error")'
   ```

5. **Test backwards compatibility (freshness disabled by default)**:

   ```bash
   # Should work exactly as before (no freshness checks)
   uv run python tools/validate_manifests.py --sources all
   ```

## CI Integration

Update `.github/workflows/data-pipeline.yml` (when CI is implemented):

```yaml
- name: Validate Snapshot Integrity and Freshness
  run: |
    uv run python tools/validate_manifests.py \
      --sources nflverse,sheets,sleeper \
      --check-freshness \
      --freshness-config config/snapshot_freshness_thresholds.yaml \
      --fail-on-gaps
```

## References

- Original ticket: P2-006 (cancelled - dbt source freshness incompatible)
- Plan: `../2025-11-07_plan_v_2_0.md` - Design Decision #5 (lines 209-250)
- Existing tool: `tools/validate_manifests.py` (P2-005 - COMPLETE)
- Thresholds rationale: Plan lines 214-227

## Notes

**Why not dbt source freshness?**

dbt's `dbt source freshness` requires:

1. Actual database tables (not external Parquet files)
2. TIMESTAMP column for `loaded_at_field` (we have DATE partitions)
3. Sources defined as queryable tables in dbt

This project uses external Parquet files read directly via `read_parquet()`, making dbt source freshness architecturally incompatible (see ADR-002: External Parquet Data Flow).

**Advantages of this approach:**

- ✅ Works with existing Parquet architecture (no architectural change)
- ✅ Consolidates validation in one tool (integrity + freshness)
- ✅ Supports per-source thresholds (flexible configuration)
- ✅ CI integration already proven (P2-005)
- ✅ No dependency on dbt execution
- ✅ Can run before dbt as pre-execution safety check

______________________________________________________________________

## Completion Notes

**Implemented**: 2025-11-20

**Implementation Summary**:

- Added `check_snapshot_freshness()` function to `tools/validate_manifests.py:83-123`
- Added CLI options: `--check-freshness`, `--freshness-warn-days`, `--freshness-error-days`, `--freshness-config`
- Integrated freshness validation into main validation loop with per-source threshold support
- Created `config/snapshot_freshness_thresholds.yaml` with source-specific thresholds
- Updated output formatting to display freshness status (FRESH/STALE-WARN/STALE-ERROR)
- Enhanced exit code logic: fails with code 1 if `--fail-on-gaps` set and freshness errors exist
- Updated `tools/CLAUDE.md` documentation with comprehensive usage examples

**Tests Passed**:

- ✅ Freshness validation with global thresholds (warn=2, error=7)
- ✅ Freshness validation with per-source config file
- ✅ JSON output format includes freshness metadata
- ✅ Backwards compatibility: freshness disabled by default (no breaking changes)
- ✅ Exit code 1 with `--fail-on-gaps` when stale-error snapshots exist
- ✅ Exit code 0 when all snapshots fresh or only warnings present

**Impact**:

- Pre-dbt safety net: Can detect stale data before model execution
- CI-ready: Supports automated data freshness validation with configurable thresholds
- Flexible configuration: Per-source thresholds account for varying update cadences
- Backwards compatible: Existing validation workflows unaffected

**Files Modified**:

- `tools/validate_manifests.py` (added freshness validation)
- `config/snapshot_freshness_thresholds.yaml` (new file)
- `tools/CLAUDE.md` (added validate_manifests.py documentation)

**Acceptance Criteria Met**: All 6 criteria from ticket satisfied.
