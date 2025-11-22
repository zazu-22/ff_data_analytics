# Ticket P4-010: Refactor Shared Utilities and Reduce Duplication

**Phase**: 4 - Orchestration\
**Status**: TODO\
**Estimated Effort**: Small (2-3 hours)\
**Dependencies**: P4-008 (tests must exist before refactoring)\
**Priority**: 🟢 **LOW - Technical debt cleanup**

## Objective

Refactor duplicate code patterns across flows into shared utilities, specifically the 120-line snapshot registry update logic and logging task decorators, following DRY principles.

## Context

Senior developer review identified two main areas of code duplication:

1. **Snapshot registry update logic**: Same 120-line pattern duplicated in 4 flows (nfl, ktc, ffanalytics, sleeper)
2. **Logging as tasks**: `@task` decorator on logging utilities creates unnecessary task nodes in Prefect UI

**Review Findings**:

- "Duplicate registry update code - Same 120-line pattern in 4 flows" (section 7)
- "log_info/warning/error are tasks, not functions - Creates unnecessary task nodes" (section 5)

## Tasks

### 1. Consolidate Registry Update Logic

- [ ] Create `src/flows/utils/registry.py` module
- [ ] Extract shared `update_snapshot_registry()` function with proper parameters
- [ ] Update all 4 flows to use shared function:
  - [ ] `nfl_data_pipeline.py` (lines 118-244)
  - [ ] `ktc_pipeline.py` (lines 290-414)
  - [ ] `ffanalytics_pipeline.py` (lines 324-451)
  - [ ] `sleeper_pipeline.py` (lines 325-447)
- [ ] Ensure function handles all use cases (seasons, weeks, market_scope)
- [ ] Add comprehensive docstring with examples

### 2. Remove @task from Logging Utilities

- [ ] Update `src/flows/utils/notifications.py`:
  - [ ] Remove `@task` decorator from `log_info`
  - [ ] Remove `@task` decorator from `log_warning`
  - [ ] Remove `@task` decorator from `log_error`
  - [ ] Keep function signatures unchanged
- [ ] Update all flows to use non-task logging (should be transparent)
- [ ] Verify Prefect UI shows cleaner flow graphs

### 3. Optional: Extract Common Validation Patterns

- [ ] Consider extracting player mapping validation (used in ktc + sleeper)
- [ ] Consider extracting manifest row count extraction (used in nfl + ktc)

## Acceptance Criteria

- [ ] Registry update logic exists in single location (`utils/registry.py`)
- [ ] All 4 flows use shared registry update function (zero duplication)
- [ ] Logging utilities are plain functions (not Prefect tasks)
- [ ] All tests pass (especially P4-008 registry tests)
- [ ] Prefect UI flow graphs are cleaner (fewer task nodes)
- [ ] Code reduction: ~400 lines of duplicate code eliminated

## Implementation Notes

### Shared Registry Update Function

```python
# src/flows/utils/registry.py
"""Shared utilities for snapshot registry management."""

from pathlib import Path
from typing import Optional
import polars as pl
from prefect import task

from src.flows.utils.notifications import log_info, log_warning


@task(name="update_snapshot_registry")
def update_snapshot_registry(
    source: str,
    dataset: str,
    snapshot_date: str,
    row_count: int,
    coverage_start_season: Optional[int] = None,
    coverage_end_season: Optional[int] = None,
    coverage_start_week: Optional[int] = None,
    coverage_end_week: Optional[int] = None,
    market_scope: Optional[str] = None,
    notes: str = "",
) -> dict:
    """Update snapshot registry with new snapshot metadata.

    This task atomically updates the registry, marking old snapshots as
    'superseded' and adding the new snapshot as 'current'.

    Handles all source types (NFLverse with seasons, FFAnalytics with weeks,
    KTC with market scope, etc.) through optional parameters.

    Args:
        source: Data source (e.g., 'nflverse', 'ktc')
        dataset: Dataset name (e.g., 'weekly', 'players')
        snapshot_date: Snapshot date (YYYY-MM-DD)
        row_count: Number of rows in snapshot
        coverage_start_season: Earliest season covered (NFLverse)
        coverage_end_season: Latest season covered (NFLverse)
        coverage_start_week: Earliest week covered (FFAnalytics)
        coverage_end_week: Latest week covered (FFAnalytics)
        market_scope: Market scope (KTC: dynasty_1qb, dynasty_superflex)
        notes: Optional notes for registry

    Returns:
        Update result dictionary with success status

    Examples:
        # NFLverse with season coverage
        update_snapshot_registry(
            source="nflverse",
            dataset="weekly",
            snapshot_date="2024-11-21",
            row_count=18981,
            coverage_start_season=2024,
            coverage_end_season=2024,
            notes="NFLverse ingestion for seasons [2024]"
        )

        # KTC with market scope
        update_snapshot_registry(
            source="ktc",
            dataset="players",
            snapshot_date="2024-11-21",
            row_count=464,
            market_scope="dynasty_1qb",
            notes="KTC dynasty_1qb ingestion"
        )

        # FFAnalytics with week coverage
        update_snapshot_registry(
            source="ffanalytics",
            dataset="projections",
            snapshot_date="2024-11-21",
            row_count=1456,
            coverage_start_week=13,
            coverage_end_week=18,
            notes="FFAnalytics ROS projections (weeks 13-18)"
        )
    """
    log_info(
        "Updating snapshot registry",
        context={
            "source": source,
            "dataset": dataset,
            "snapshot_date": snapshot_date,
            "row_count": row_count,
        },
    )

    registry_path = Path("dbt/ff_data_transform/seeds/snapshot_registry.csv")

    # Read current registry
    registry = pl.read_csv(registry_path)

    # Check if this snapshot already exists
    existing = registry.filter(
        (pl.col("source") == source)
        & (pl.col("dataset") == dataset)
        & (pl.col("snapshot_date") == snapshot_date)
    )

    if len(existing) > 0:
        log_warning(
            f"Snapshot already exists in registry: {source}.{dataset}.{snapshot_date}",
            context={"action": "updating_existing_row"},
        )

        # Update existing row (idempotent)
        registry = registry.with_columns(
            pl.when(
                (pl.col("source") == source)
                & (pl.col("dataset") == dataset)
                & (pl.col("snapshot_date") == snapshot_date)
            )
            .then(pl.lit("current"))
            .otherwise(pl.col("status"))
            .alias("status"),
            pl.when(
                (pl.col("source") == source)
                & (pl.col("dataset") == dataset)
                & (pl.col("snapshot_date") == snapshot_date)
            )
            .then(pl.lit(row_count))
            .otherwise(pl.col("row_count"))
            .alias("row_count"),
        )

    else:
        # Mark previous snapshots for this source/dataset as superseded
        registry = registry.with_columns(
            pl.when(
                (pl.col("source") == source)
                & (pl.col("dataset") == dataset)
                & (pl.col("status") == "current")
            )
            .then(pl.lit("superseded"))
            .otherwise(pl.col("status"))
            .alias("status")
        )

        # Build notes with context
        if not notes:
            notes_parts = [f"{source} ingestion"]
            if coverage_start_season and coverage_end_season:
                notes_parts.append(f"seasons {coverage_start_season}-{coverage_end_season}")
            if coverage_start_week and coverage_end_week:
                notes_parts.append(f"weeks {coverage_start_week}-{coverage_end_week}")
            if market_scope:
                notes_parts.append(market_scope)
            notes = " - ".join(notes_parts)

        # Add new snapshot
        new_row = pl.DataFrame(
            [
                {
                    "source": source,
                    "dataset": dataset,
                    "snapshot_date": snapshot_date,
                    "status": "current",
                    "coverage_start_season": coverage_start_season,
                    "coverage_end_season": coverage_end_season,
                    "row_count": row_count,
                    "notes": notes,
                }
            ]
        )

        registry = pl.concat([registry, new_row])

    # Write updated registry atomically
    registry.write_csv(registry_path)

    log_info(
        "Snapshot registry updated",
        context={
            "source": source,
            "dataset": dataset,
            "snapshot_date": snapshot_date,
            "registry_path": str(registry_path),
        },
    )

    return {
        "success": True,
        "source": source,
        "dataset": dataset,
        "snapshot_date": snapshot_date,
        "row_count": row_count,
    }
```

### Updated Logging Utilities

```python
# src/flows/utils/notifications.py (UPDATED)
"""Notification utilities for Prefect flows.

Note: These are NOT Prefect tasks - they're plain functions that log
messages. Making them tasks creates unnecessary nodes in the Prefect UI.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


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
```

### Migration Example

```python
# Before (nfl_data_pipeline.py)
@task(name="update_snapshot_registry")
def update_snapshot_registry(...):
    # 120 lines of duplicate code
    ...

# After (nfl_data_pipeline.py)
from src.flows.utils.registry import update_snapshot_registry

# Just call the shared function - no local definition needed
registry_update = update_snapshot_registry(
    source="nflverse",
    dataset=dataset,
    snapshot_date=snapshot_date,
    row_count=row_count,
    coverage_start_season=coverage.get("coverage_start_season"),
    coverage_end_season=coverage.get("coverage_end_season"),
    notes=f"NFLverse ingestion for seasons {seasons}",
)
```

## Testing

**Prerequisites**: P4-008 must be complete (tests exist for registry logic)

```bash
# 1. Run existing tests to establish baseline
pytest tests/flows/test_registry_updates.py -v

# 2. Refactor to use shared function
# (make changes)

# 3. Re-run tests - should still pass
pytest tests/flows/test_registry_updates.py -v

# 4. Run all flow tests
pytest tests/flows/ -v

# 5. Test each flow locally
python src/flows/nfl_data_pipeline.py
python src/flows/ktc_pipeline.py
python src/flows/ffanalytics_pipeline.py
python src/flows/sleeper_pipeline.py
```

## References

- Code Review: Section 7 (duplicate code), Section 5 (logging tasks)
- DRY Principle: https://en.wikipedia.org/wiki/Don%27t_repeat_yourself
- Dependency: P4-008 (tests must exist before refactoring)

## Success Metrics

- [ ] ~400 lines of duplicate code removed
- [ ] Single shared registry update function
- [ ] All 4 flows use shared function
- [ ] Logging utilities are plain functions (not tasks)
- [ ] Prefect UI shows fewer task nodes
- [ ] All tests pass (regression protection from P4-008)

## Completion Notes

**Implementation Date**: TBD\
**Lines Removed**: TBD\
**Refactoring Safety**: Protected by P4-008 tests

______________________________________________________________________

**Note**: This is technical debt cleanup. **Must wait for P4-008** (tests) to be complete to ensure safe refactoring with regression protection.
