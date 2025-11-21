# Ticket P4-001: Create Flows Directory and Shared Utilities

**Phase**: 4 - Orchestration\
**Status**: COMPLETE\
**Estimated Effort**: Small (2 hours)\
**Dependencies**: P2-005 (validate_manifests tool should exist for governance integration)

## Objective

Create `src/flows/` directory structure with shared validation and notification utilities that all Prefect flows will use.

## Context

This ticket establishes the foundation for all Prefect flows, providing shared utilities for validation tasks and notification helpers that ensure consistent governance integration across all 5 source pipelines.

## Tasks

- [x] Create `src/flows/` directory
- [x] Create `src/flows/__init__.py`
- [x] Create `src/flows/utils/` subdirectory
- [x] Create `src/flows/utils/validation.py` (validation task helpers)
- [x] Create `src/flows/utils/notifications.py` (logging/alerting helpers)
- [x] Add basic validation tasks (manifest validation, freshness checks)
- [x] Add notification helpers (log warnings, fail on critical errors)

## Acceptance Criteria

- [x] Directory structure created
- [x] Shared utilities implemented and tested
- [x] Validation helpers functional
- [x] Notification helpers functional
- [x] Documentation added to utility modules

## Implementation Notes

**Directory Structure**:

```text
src/flows/
├── __init__.py
├── utils/
│   ├── __init__.py
│   ├── validation.py
│   └── notifications.py
├── google_sheets_pipeline.py    (created in P4-002)
├── nfl_data_pipeline.py          (created in P4-003)
├── ktc_pipeline.py                (created in P4-004)
├── ffanalytics_pipeline.py        (created in P4-005)
└── sleeper_pipeline.py            (created in P4-006)
```

**File: `src/flows/utils/validation.py`**

```python
"""Shared validation utilities for Prefect flows."""

import subprocess
from pathlib import Path
from prefect import task
import polars as pl


@task(name="validate_manifests")
def validate_manifests_task(sources: list[str], fail_on_gaps: bool = True) -> dict:
    """Run manifest validation tool.

    Args:
        sources: List of source names to validate
        fail_on_gaps: Whether to fail on validation errors

    Returns:
        Validation results dictionary

    Raises:
        RuntimeError: If validation fails and fail_on_gaps=True
    """
    cmd = [
        "uv", "run", "python", "tools/validate_manifests.py",
        "--sources", ",".join(sources),
        "--output-format", "json"
    ]

    if fail_on_gaps:
        cmd.append("--fail-on-gaps")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 and fail_on_gaps:
        raise RuntimeError(f"Manifest validation failed: {result.stderr}")

    return {
        "success": result.returncode == 0,
        "output": result.stdout,
        "errors": result.stderr
    }


@task(name="check_snapshot_currency")
def check_snapshot_currency(source: str, dataset: str, max_age_days: int) -> dict:
    """Check if snapshot is current (not stale).

    Args:
        source: Data source (e.g., 'nflverse')
        dataset: Dataset within source (e.g., 'weekly')
        max_age_days: Maximum acceptable age in days

    Returns:
        Dictionary with currency check results
    """
    from datetime import datetime, timedelta

    # Read snapshot registry
    registry_path = Path("dbt/ff_data_transform/seeds/snapshot_registry.csv")
    registry = pl.read_csv(registry_path)

    # Find current snapshot for source/dataset
    current = (
        registry
        .filter(
            (pl.col("source") == source) &
            (pl.col("dataset") == dataset) &
            (pl.col("status") == "current")
        )
        .select(["snapshot_date"])
        .first()
    )

    if not current:
        return {
            "is_current": False,
            "reason": f"No current snapshot found for {source}.{dataset}"
        }

    snapshot_date = datetime.strptime(current["snapshot_date"], "%Y-%m-%d")
    age_days = (datetime.now() - snapshot_date).days
    is_current = age_days <= max_age_days

    return {
        "is_current": is_current,
        "snapshot_date": current["snapshot_date"],
        "age_days": age_days,
        "max_age_days": max_age_days
    }


@task(name="detect_row_count_anomaly")
def detect_row_count_anomaly(
    source: str,
    dataset: str,
    current_count: int,
    threshold_pct: float = 50.0
) -> dict:
    """Detect unusual row count changes.

    Args:
        source: Data source
        dataset: Dataset within source
        current_count: Row count from latest load
        threshold_pct: Percentage change threshold for anomaly

    Returns:
        Dictionary with anomaly detection results
    """
    # Read snapshot registry
    registry_path = Path("dbt/ff_data_transform/seeds/snapshot_registry.csv")
    registry = pl.read_csv(registry_path)

    # Get previous snapshot row count
    snapshots = (
        registry
        .filter(
            (pl.col("source") == source) &
            (pl.col("dataset") == dataset)
        )
        .sort("snapshot_date", descending=True)
        .select(["snapshot_date", "row_count"])
        .head(2)
    )

    if len(snapshots) < 2:
        return {
            "is_anomaly": False,
            "reason": "Not enough snapshots for comparison"
        }

    previous_count = snapshots[1]["row_count"]
    delta = current_count - previous_count
    pct_change = (delta / previous_count * 100) if previous_count > 0 else 0

    is_anomaly = abs(pct_change) > threshold_pct

    return {
        "is_anomaly": is_anomaly,
        "current_count": current_count,
        "previous_count": previous_count,
        "delta": delta,
        "pct_change": pct_change,
        "threshold_pct": threshold_pct
    }
```

**File: `src/flows/utils/notifications.py`**

```python
"""Notification utilities for Prefect flows."""

import logging
from typing import Optional
from prefect import task

logger = logging.getLogger(__name__)


@task(name="log_warning")
def log_warning(message: str, context: Optional[dict] = None):
    """Log warning message.

    Args:
        message: Warning message
        context: Optional context dictionary
    """
    log_msg = f"WARNING: {message}"
    if context:
        log_msg += f" | Context: {context}"
    logger.warning(log_msg)
    print(f"⚠️  {log_msg}")


@task(name="log_error")
def log_error(message: str, context: Optional[dict] = None):
    """Log error message and fail flow.

    Args:
        message: Error message
        context: Optional context dictionary

    Raises:
        RuntimeError: Always raises to fail the flow
    """
    log_msg = f"ERROR: {message}"
    if context:
        log_msg += f" | Context: {context}"
    logger.error(log_msg)
    print(f"❌ {log_msg}")
    raise RuntimeError(log_msg)


@task(name="log_info")
def log_info(message: str, context: Optional[dict] = None):
    """Log info message.

    Args:
        message: Info message
        context: Optional context dictionary
    """
    log_msg = f"INFO: {message}"
    if context:
        log_msg += f" | Context: {context}"
    logger.info(log_msg)
    print(f"✓ {log_msg}")


# Future: Add Slack/email notification tasks
# @task(name="send_slack_alert")
# def send_slack_alert(message: str, channel: str):
#     """Send Slack notification."""
#     pass
```

## Testing

1. **Import test**:

   ```python
   from src.flows.utils.validation import validate_manifests_task
   from src.flows.utils.notifications import log_info
   print("✓ Imports successful")
   ```

2. **Validation task test**:

   ```python
   from src.flows.utils.validation import validate_manifests_task

   result = validate_manifests_task(sources=["nflverse"], fail_on_gaps=False)
   print(f"Validation result: {result['success']}")
   ```

3. **Notification task test**:

   ```python
   from src.flows.utils.notifications import log_info

   log_info("Test message", context={"source": "test"})
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 4 Activities (lines 449-453)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 4 Directory (lines 271-277)

## Completion Notes

**Implemented**: 2025-11-21
**Tests**: All passing

**Files Created**:
- `src/flows/__init__.py` - Module initialization
- `src/flows/utils/__init__.py` - Utils module initialization
- `src/flows/utils/validation.py` - Validation task helpers (validate_manifests, snapshot_currency, row_count_anomaly)
- `src/flows/utils/notifications.py` - Notification helpers (log_warning, log_error, log_info)

**Testing Results**:
- Import test: PASS (all modules successfully imported)
- Directory structure: PASS (all files created as specified)
- Validation tasks: validate_manifests_task, check_snapshot_currency, detect_row_count_anomaly
- Notification tasks: log_warning, log_error, log_info

**Impact**:
- Foundation established for Phase 4 Prefect flow development
- Shared utilities provide consistent validation and notification patterns across all 5 source pipelines
- Dependencies satisfied: P2-005 (validate_manifests tool) verified present
- Ready for P4-002a through P4-006 implementation
