"""Source freshness tracking and skip-if-unchanged logic for Prefect flows.

This module provides utilities to:
1. Track last successful run metadata for each source/dataset
2. Determine if a fetch should be skipped based on source modification time
3. Persist run metadata for governance and observability

Metadata is stored in data/.metadata/{source}/{dataset}/last_run.json
"""

import json
from datetime import datetime
from pathlib import Path
from typing import TypedDict


class LastRunMetadata(TypedDict, total=False):
    """Metadata from last successful run.

    Attributes:
        timestamp: ISO 8601 timestamp of run completion
        snapshot_date: Date of the snapshot (YYYY-MM-DD)
        row_count: Total rows written
        source_hash: Checksum/hash of source data (optional)
        source_modified_time: Source's last modified time (optional)

    """

    timestamp: str
    snapshot_date: str
    row_count: int
    source_hash: str | None
    source_modified_time: str | None


def get_last_successful_run(source: str, dataset: str) -> LastRunMetadata | None:
    """Get metadata from last successful run.

    Args:
        source: Data source name (e.g., 'sheets', 'nflverse', 'ktc')
        dataset: Dataset name (e.g., 'commissioner', 'weekly_stats')

    Returns:
        Dictionary with last run metadata, or None if no previous run found

    """
    metadata_file = Path(f"data/.metadata/{source}/{dataset}/last_run.json")
    if metadata_file.exists():
        return json.loads(metadata_file.read_text())
    return None


def should_skip_fetch(
    source: str,
    dataset: str,
    source_modified_time: datetime | None = None,
    force: bool = False,
) -> tuple[bool, str]:
    """Determine if fetch should be skipped based on freshness.

    This implements the "skip-if-unchanged" pattern from legacy scripts.

    Args:
        source: Data source name
        dataset: Dataset name
        source_modified_time: Source's last modified time (if available)
        force: Force fetch even if source appears unchanged

    Returns:
        Tuple of (should_skip, reason_string)

    Examples:
        >>> should_skip_fetch("sheets", "commissioner", None, force=True)
        (False, "Force flag set")

        >>> # If source modified time hasn't changed since last fetch
        >>> should_skip_fetch("sheets", "commissioner", datetime(2025, 1, 1))
        (True, "Source unchanged since 2025-01-01T12:00:00")

    """
    if force:
        return False, "Force flag set"

    last_run = get_last_successful_run(source, dataset)
    if not last_run:
        return False, "No previous run found"

    # Check source modified time (if available)
    if source_modified_time:
        last_source_modified = last_run.get("source_modified_time")

        if last_source_modified:
            last_source_dt = datetime.fromisoformat(last_source_modified)
            if source_modified_time <= last_source_dt:
                return True, f"Source unchanged since {last_source_dt.isoformat()}"

    return False, "Source may have changed"


def record_successful_run(
    source: str,
    dataset: str,
    snapshot_date: str,
    row_count: int,
    source_hash: str | None = None,
    source_modified_time: datetime | None = None,
) -> None:
    """Record metadata from successful run.

    Creates or updates the last_run.json file for the source/dataset combination.

    Args:
        source: Data source name
        dataset: Dataset name
        snapshot_date: Snapshot date (YYYY-MM-DD)
        row_count: Total rows written
        source_hash: Optional checksum/hash of source data
        source_modified_time: Optional source modification timestamp

    """
    metadata_file = Path(f"data/.metadata/{source}/{dataset}/last_run.json")
    metadata_file.parent.mkdir(parents=True, exist_ok=True)

    metadata: LastRunMetadata = {
        "timestamp": datetime.now().isoformat(),
        "snapshot_date": snapshot_date,
        "row_count": row_count,
        "source_hash": source_hash,
        "source_modified_time": source_modified_time.isoformat() if source_modified_time else None,
    }

    metadata_file.write_text(json.dumps(metadata, indent=2))


def get_data_age_hours(source: str, dataset: str) -> float | None:
    """Get age of last successful run in hours.

    Useful for freshness warnings in parse flows.

    Args:
        source: Data source name
        dataset: Dataset name

    Returns:
        Age in hours since last successful run, or None if no run found

    """
    last_run = get_last_successful_run(source, dataset)
    if not last_run:
        return None

    last_timestamp = datetime.fromisoformat(last_run["timestamp"])
    age = datetime.now() - last_timestamp
    return age.total_seconds() / 3600
