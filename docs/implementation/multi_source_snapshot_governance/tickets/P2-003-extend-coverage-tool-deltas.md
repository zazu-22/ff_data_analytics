# Ticket P2-003: Extend analyze_snapshot_coverage - Row Deltas

**Status**: READY FOR REVIEW\
**Phase**: 2 - Governance\
**Estimated Effort**: Medium (2-3 hours)\
**Dependencies**: None (can work in parallel with registry tickets)

## Objective

Extend `tools/analyze_snapshot_coverage.py` to add row delta reporting that compares current vs previous snapshots to detect anomalies and unexpected changes.

## Context

The existing `analyze_snapshot_coverage.py` tool provides basic snapshot inventory. This ticket adds row delta analysis to help detect:

- Unexpected data loss (negative deltas)
- Anomalous growth (deltas exceeding expected ranges)
- Data quality issues (zero or near-zero deltas when growth expected)

This provides pre-dbt validation to catch issues before they propagate to downstream models.

## Tasks

### Add Delta Calculation Logic

- [x] Read snapshot registry to identify current vs previous snapshots
- [x] Compare row counts between snapshot pairs
- [x] Calculate absolute delta (current - previous)
- [x] Calculate percentage change

### Flag Anomalies

- [x] Define expected delta thresholds per dataset type
- [x] Flag deltas exceeding thresholds (e.g., >50% change)
- [x] Flag negative deltas (data loss)
- [x] Flag near-zero deltas during active season

### Update Output Format

- [x] Add delta section to human-readable output
- [x] Include delta in JSON output for CI consumption
- [x] Highlight anomalies in summary

### Test with Real Data

- [x] Test delta calculation logic with snapshot registry
- [ ] Run against nflverse weekly (expect growth during season)
- [ ] Run against sheets data (expect smaller deltas)
- [ ] Verify anomaly detection works correctly

## Acceptance Criteria

- [x] Tool calculates row deltas between current and previous snapshots
- [x] Anomalies flagged based on thresholds
- [x] Output includes delta information (both JSON and human-readable)
- [ ] Tool runs without errors on all 5 sources (needs validation with real data)
- [x] Documentation updated with new features

## Implementation Notes

**File**: `tools/analyze_snapshot_coverage.py`

**New Function** (add to existing tool):

```python
def calculate_deltas(source: str, dataset: str, registry_df: DataFrame) -> dict:
    """Calculate row count deltas between current and previous snapshots.

    Args:
        source: Data source (e.g., 'nflverse')
        dataset: Dataset within source (e.g., 'weekly')
        registry_df: Snapshot registry DataFrame

    Returns:
        Dictionary with delta statistics
    """
    # Filter registry to source/dataset
    snapshots = (
        registry_df
        .filter(
            (pl.col('source') == source) &
            (pl.col('dataset') == dataset)
        )
        .sort('snapshot_date', descending=True)
    )

    if len(snapshots) < 2:
        return {'error': 'Need at least 2 snapshots for delta calculation'}

    current = snapshots[0]
    previous = snapshots[1]

    current_count = current['row_count']
    previous_count = previous['row_count']

    delta = current_count - previous_count
    pct_change = (delta / previous_count * 100) if previous_count > 0 else 0

    # Anomaly detection
    is_anomaly = abs(pct_change) > 50  # >50% change
    is_data_loss = delta < 0
    is_stagnant = abs(delta) < 10 and source == 'nflverse'  # Expect growth during season

    return {
        'source': source,
        'dataset': dataset,
        'current_snapshot': current['snapshot_date'],
        'current_count': current_count,
        'previous_snapshot': previous['snapshot_date'],
        'previous_count': previous_count,
        'delta': delta,
        'pct_change': pct_change,
        'is_anomaly': is_anomaly,
        'is_data_loss': is_data_loss,
        'is_stagnant': is_stagnant
    }
```

**Expected Output Format** (from plan line 152):

```
Snapshot Coverage Analysis
=========================

NFLverse Weekly:
- 2025-10-27: 89,145 rows (2020-2024, 100% mapped)
- 2025-11-05: 97,302 rows (+8,157 delta, 2020-2025, 98.7% mapped)

Coverage Gaps:
- Week 10 missing for 2025 season (expected by 2025-11-12)
```

**Delta Thresholds** (configurable):

```python
DELTA_THRESHOLDS = {
    'nflverse': {
        'weekly': {'min_pct': -5, 'max_pct': 20},  # Allow 20% growth during season
        'snap_counts': {'min_pct': -5, 'max_pct': 20},
    },
    'sheets': {
        'roster': {'min_pct': -10, 'max_pct': 30},  # Trades can cause swings
        'transactions': {'min_pct': 0, 'max_pct': 100},  # Cumulative, always grows
    },
    'ktc': {
        'players': {'min_pct': -10, 'max_pct': 10},  # Valuations fairly stable
    },
    # Add thresholds for other sources
}
```

## Testing

1. **Run tool with delta reporting**:

   ```bash
   uv run python tools/analyze_snapshot_coverage.py \
       --sources nflverse sheets \
       --report-deltas
   ```

2. **Verify delta calculation**:

   ```python
   # Test script
   from tools.analyze_snapshot_coverage import calculate_deltas
   import polars as pl

   # Load registry
   registry = pl.read_csv('dbt/ff_data_transform/seeds/snapshot_registry.csv')

   # Calculate deltas for nflverse weekly
   deltas = calculate_deltas('nflverse', 'weekly', registry)
   print(deltas)
   ```

3. **Test anomaly detection**:

   - Create test registry with anomalous delta (>50% change)
   - Verify tool flags it as anomaly
   - Test data loss scenario (negative delta)

4. **JSON output validation**:

   ```bash
   uv run python tools/analyze_snapshot_coverage.py \
       --sources nflverse \
       --report-deltas \
       --output-format json \
       > deltas.json

   cat deltas.json | jq '.deltas'
   ```

## Completion Notes

**Implemented**: 2025-11-18

**Changes Made**:
- Added `load_snapshot_registry()` function to read snapshot registry CSV
- Added `calculate_deltas()` function with configurable thresholds per source/dataset
- Added `_print_delta_info()` function to display delta information with anomaly warnings
- Updated `_print_snapshot_metrics()` to include delta info when available
- Updated `_analyze_dataset()` to calculate and pass delta info
- Updated `analyze_snapshots()` to support delta reporting
- Added `--report-deltas` and `--registry-path` command-line flags
- Defined `DELTA_THRESHOLDS` configuration for all 5 sources (nflverse, sheets, ktc, sleeper, etc.)

**Tests Completed**:
- Unit test with snapshot registry: PASS (tested with sheets/cap_space, contracts_active, contracts_cut)
- Delta calculation logic verified with real registry data
- Anomaly detection thresholds configured and tested

**Still Needs Validation**:
- End-to-end testing with actual parquet files (data/raw/ not available in dev environment)
- Verification that tool runs without errors on all 5 sources
- Confirmation that output format matches expected format from plan

**Next Steps**:
- Test in environment with actual data files
- Verify anomaly detection triggers correctly
- Consider adding delta information to markdown report generation

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Design Decision #4 (lines 142-162)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 2 Validation (lines 112-116)
- Existing tool: `tools/analyze_snapshot_coverage.py`
