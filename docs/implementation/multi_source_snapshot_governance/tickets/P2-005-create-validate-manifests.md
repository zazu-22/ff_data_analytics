# Ticket P2-005: Create validate_manifests Tool

**Phase**: 2 - Governance\
**Estimated Effort**: Medium (3-4 hours)\
**Dependencies**: P2-001, P2-002 (registry must exist and be populated)

## Objective

Create `tools/validate_manifests.py` for registry-driven validation that cross-checks snapshot registry expectations against actual `_meta.json` manifests and Parquet files, with CI integration.

## Context

The snapshot registry defines expected snapshots, but we need automated validation that:

1. Expected snapshots actually exist on disk
2. Manifests are present and well-formed
3. Row counts match between manifest and actual Parquet files
4. Coverage dates align with registry expectations

This tool provides CI-integrated validation that catches missing or corrupted snapshots before dbt execution.

## Tasks

### Create Core Validation Tool

- [ ] Create `tools/validate_manifests.py`
- [ ] Implement registry-driven validation logic
- [ ] Add manifest vs Parquet verification
- [ ] Add CI integration (exit code handling)

### Implement Validation Checks

- [ ] Check expected snapshots exist in `data/raw/`
- [ ] Verify `_meta.json` manifests exist for each snapshot
- [ ] Compare manifest row_count vs actual Parquet row count
- [ ] Validate date ranges (coverage_start_season/end_season)
- [ ] Check required metadata fields (source_version, asof_datetime)

### Add CLI Interface

- [ ] Support `--sources` flag to validate specific sources
- [ ] Add `--fail-on-gaps` flag for strict enforcement
- [ ] Add `--output-format` flag (text, json)
- [ ] Implement proper exit codes (0=pass, 1=fail)

### Optional: Notification Hooks

- [ ] Log warnings for minor issues
- [ ] Slack alerts for critical failures (optional)
- [ ] Email notifications (optional)

## Acceptance Criteria

- [ ] Tool validates all registry entries against disk
- [ ] Manifest vs Parquet row count verification works
- [ ] CI integration functional (exit code 1 on failure)
- [ ] Tool runs successfully on all 5 sources
- [ ] Documentation complete with usage examples

## Implementation Notes

**File**: `tools/validate_manifests.py`

**Core Validation Function**:

```python
#!/usr/bin/env python3
"""Validate snapshot manifests against registry expectations.

Usage:
    uv run python tools/validate_manifests.py --sources nflverse sheets
    uv run python tools/validate_manifests.py --sources all --fail-on-gaps
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
import polars as pl
import click


def validate_snapshot(
    source: str,
    dataset: str,
    snapshot_date: str,
    expected_row_count: int,
    raw_dir: Path = Path('data/raw')
) -> Dict:
    """Validate a single snapshot entry.

    Returns:
        Dictionary with validation results and issues
    """
    issues = []

    # Check snapshot directory exists
    snapshot_path = raw_dir / source / dataset / f'dt={snapshot_date}'
    if not snapshot_path.exists():
        issues.append(f"Snapshot directory missing: {snapshot_path}")
        return {'valid': False, 'issues': issues}

    # Check manifest exists
    manifest_path = snapshot_path / '_meta.json'
    if not manifest_path.exists():
        issues.append(f"Manifest missing: {manifest_path}")
        return {'valid': False, 'issues': issues}

    # Load and validate manifest
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Check required fields
    required_fields = ['dataset', 'loader_path', 'source_version', 'row_count', 'asof_datetime']
    for field in required_fields:
        if field not in manifest:
            issues.append(f"Manifest missing required field: {field}")

    # Verify row count matches
    manifest_row_count = manifest.get('row_count')
    if manifest_row_count != expected_row_count:
        issues.append(
            f"Row count mismatch: registry={expected_row_count}, "
            f"manifest={manifest_row_count}"
        )

    # Verify actual Parquet row count
    parquet_files = list(snapshot_path.glob('*.parquet'))
    if parquet_files:
        actual_df = pl.read_parquet(parquet_files)
        actual_row_count = len(actual_df)

        if actual_row_count != expected_row_count:
            issues.append(
                f"Actual row count mismatch: expected={expected_row_count}, "
                f"actual={actual_row_count}"
            )
    else:
        issues.append(f"No Parquet files found in {snapshot_path}")

    return {
        'valid': len(issues) == 0,
        'issues': issues
    }


@click.command()
@click.option('--sources', default='all', help='Comma-separated sources or "all"')
@click.option('--fail-on-gaps', is_flag=True, help='Exit with code 1 if validation fails')
@click.option('--output-format', type=click.Choice(['text', 'json']), default='text')
@click.option('--registry', default='dbt/ff_analytics/seeds/snapshot_registry.csv',
              help='Path to snapshot registry')
def main(sources, fail_on_gaps, output_format, registry):
    """Validate snapshot manifests against registry."""

    # Load registry
    registry_df = pl.read_csv(registry)

    # Filter sources
    if sources != 'all':
        source_list = [s.strip() for s in sources.split(',')]
        registry_df = registry_df.filter(pl.col('source').is_in(source_list))

    # Validate each entry
    results = []
    for row in registry_df.iter_rows(named=True):
        result = validate_snapshot(
            source=row['source'],
            dataset=row['dataset'],
            snapshot_date=row['snapshot_date'],
            expected_row_count=row['row_count']
        )

        results.append({
            'source': row['source'],
            'dataset': row['dataset'],
            'snapshot_date': row['snapshot_date'],
            'valid': result['valid'],
            'issues': result['issues']
        })

    # Output results
    if output_format == 'json':
        print(json.dumps({'results': results}, indent=2))
    else:
        print("Snapshot Manifest Validation")
        print("=" * 50)

        valid_count = sum(1 for r in results if r['valid'])
        total_count = len(results)

        print(f"\nValidated: {valid_count}/{total_count} snapshots")

        # Show failures
        failures = [r for r in results if not r['valid']]
        if failures:
            print(f"\nFailed Validations ({len(failures)}):")
            for f in failures:
                print(f"\n  {f['source']}.{f['dataset']} [{f['snapshot_date']}]:")
                for issue in f['issues']:
                    print(f"    - {issue}")

    # Exit code
    if fail_on_gaps and any(not r['valid'] for r in results):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
```

**CI Integration** (from plan lines 176-179):

```yaml
# In .github/workflows/data-pipeline.yml
- name: Validate Snapshot Manifests
  run: |
    uv run python tools/validate_manifests.py \
      --sources nflverse sheets \
      --fail-on-gaps
```

## Testing

1. **Run validation on all sources**:

   ```bash
   uv run python tools/validate_manifests.py --sources all
   ```

2. **Test specific sources**:

   ```bash
   uv run python tools/validate_manifests.py --sources nflverse,sheets
   ```

3. **Test failure handling**:

   ```bash
   # Temporarily rename a manifest to trigger failure
   mv data/raw/nflverse/weekly/dt=2025-10-27/_meta.json \
      data/raw/nflverse/weekly/dt=2025-10-27/_meta.json.bak

   # Should fail validation
   uv run python tools/validate_manifests.py --sources nflverse --fail-on-gaps
   echo $?  # Should be 1

   # Restore
   mv data/raw/nflverse/weekly/dt=2025-10-27/_meta.json.bak \
      data/raw/nflverse/weekly/dt=2025-10-27/_meta.json
   ```

4. **Test JSON output**:

   ```bash
   uv run python tools/validate_manifests.py \
       --sources nflverse \
       --output-format json \
       > validation_results.json

   cat validation_results.json | jq '.results[] | select(.valid == false)'
   ```

5. **Test with registry edge cases**:

   - Empty registry
   - Missing source
   - Invalid snapshot_date format

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Design Decision #4 (lines 164-179)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 2 Validation (lines 128-142)
- Registry: `dbt/ff_analytics/seeds/snapshot_registry.csv`
- Manifest spec: See existing `_meta.json` files in `data/raw/`
