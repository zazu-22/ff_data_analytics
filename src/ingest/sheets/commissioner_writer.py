"""Commissioner sheet writer - handles all file I/O for commissioner data.

This module centralizes all file writing logic for commissioner sheet data,
providing cloud-ready (local + GCS) writes with consistent patterns:

1. **Idempotent**: Clears partitions before writing (safe reruns)
2. **Atomic**: Single timestamp across all tables (guaranteed consistency)
3. **Cloud-Ready**: Works with local paths and gs:// URIs via PyArrow FS
4. **Metadata**: All tables write _meta.json with lineage

Environment:
    OUTPUT_PATH: Base output path ("data/raw" or "gs://bucket/raw")

Usage:
    writer.write_all_commissioner_tables(
        roster_tables=parsed_rosters,
        transactions_tables=parsed_transactions,
        base_uri="data/raw/commissioner"  # or gs://bucket/raw/commissioner
    )
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from ingest.common.storage import write_parquet_any, write_text_sidecar


def _clear_partition_cloud(partition_uri: str) -> int:
    """Clear all parquet and metadata files in partition (local or GCS).

    This ensures idempotent writes - if the writer runs multiple times on the same
    date, only the most recent write persists (no duplicates).

    Uses PyArrow FileSystem for cloud-agnostic deletion.

    Args:
        partition_uri: Partition URI (e.g., "data/raw/commissioner/transactions/dt=2025-10-26"
                       or "gs://bucket/raw/commissioner/transactions/dt=2025-10-26")

    Returns:
        Number of files deleted

    """
    try:
        from pyarrow import fs as pafs
    except ImportError as err:  # pragma: no cover
        raise RuntimeError("pyarrow is required for partition clearing") from err

    # Handle relative paths for local filesystem
    if not partition_uri.startswith("gs://"):
        partition_uri = str(Path(partition_uri).resolve())

    # Get filesystem and path from URI
    try:
        filesystem, path = pafs.FileSystem.from_uri(partition_uri)
    except Exception:
        # Partition doesn't exist yet
        return 0

    # Check if partition exists
    try:
        file_info = filesystem.get_file_info(path)
        if file_info.type != pafs.FileType.Directory:
            return 0
    except Exception:
        return 0

    # Delete parquet and metadata files
    deleted_count = 0
    selector = pafs.FileSelector(path, allow_not_found=True, recursive=False)
    for file_info in filesystem.get_file_info(selector):
        if file_info.path.endswith((".parquet", "_meta.json")):
            filesystem.delete_file(file_info.path)
            deleted_count += 1

    return deleted_count


def _write_table_with_metadata(
    table: pl.DataFrame,
    table_name: str,
    base_uri: str,
    dt: str,
    extra_metadata: dict[str, Any] | None = None,
) -> int:
    """Write a table with metadata (idempotent, fixed filename, cloud-ready).

    Args:
        table: DataFrame to write
        table_name: Table name (e.g., 'contracts_active')
        base_uri: Base URI (e.g., 'data/raw/commissioner' or 'gs://bucket/raw/commissioner')
        dt: Date partition (YYYY-MM-DD)
        extra_metadata: Optional extra metadata fields

    Returns:
        Row count

    """
    if table.is_empty():
        return 0

    # Construct partition URI (cloud-agnostic)
    partition_uri = f"{base_uri}/{table_name}/dt={dt}"

    # Clear partition (idempotent)
    _clear_partition_cloud(partition_uri)

    # Write parquet with fixed filename
    parquet_uri = f"{partition_uri}/{table_name}.parquet"
    write_parquet_any(table, parquet_uri)

    # Write metadata
    meta_uri = f"{partition_uri}/_meta.json"
    metadata = {
        "dataset": table_name,
        "source": "commissioner_google_sheet",
        "parser_function": "ingest.sheets.commissioner_parser",
        "writer_function": "ingest.sheets.commissioner_writer.write_all_commissioner_tables",
        "asof_datetime": datetime.now(UTC).isoformat(),
        "output_parquet": [f"{table_name}.parquet"],
        "row_count": table.height,
        "dt": dt,
    }

    # Add extra metadata
    if extra_metadata:
        metadata.update(extra_metadata)

    # Write metadata as JSON
    meta_json = json.dumps(metadata, indent=2)
    write_text_sidecar(meta_json, meta_uri)

    return table.height


def write_all_commissioner_tables(
    roster_tables: dict[str, pl.DataFrame],
    transactions_tables: dict[str, pl.DataFrame],
    base_uri: str,
    dt: str | None = None,
) -> dict[str, int]:
    """Write all commissioner tables atomically with consistent timestamp.

    This is the main entry point for writing commissioner data. It ensures all tables
    from a single sheet snapshot are written with the same timestamp partition.

    Args:
        roster_tables: Dict with keys:
            - 'contracts_active': Active roster contracts
            - 'contracts_cut': Dead cap obligations
            - 'draft_picks': Draft pick ownership
            - 'draft_pick_conditions': Conditional picks
            - 'cap_space': Cap space by season
        transactions_tables: Dict with keys:
            - 'transactions': Transaction history
            - 'unmapped_players': QA table
            - 'unmapped_picks': QA table (optional)
        base_uri: Base output URI (e.g., "data/raw/commissioner" or "gs://bucket/raw/commissioner")
        dt: Optional date partition (defaults to today UTC)

    Returns:
        Dict of row counts by table name

    Example:
        counts = write_all_commissioner_tables(
            roster_tables={
                'contracts_active': active_df,
                'contracts_cut': cut_df,
                'draft_picks': picks_df,
                'draft_pick_conditions': conds_df,
                'cap_space': cap_df,
            },
            transactions_tables={
                'transactions': txn_df,
                'unmapped_players': unmapped_df,
            },
            base_uri="gs://ff-analytics/raw/commissioner"
        )

    """
    if dt is None:
        dt = datetime.now(UTC).strftime("%Y-%m-%d")

    counts: dict[str, int] = {}

    # Write roster-derived tables
    for table_name in [
        "contracts_active",
        "contracts_cut",
        "draft_picks",
        "draft_pick_conditions",
        "cap_space",
    ]:
        if table_name in roster_tables:
            counts[table_name] = _write_table_with_metadata(
                roster_tables[table_name], table_name, base_uri, dt
            )

    # Write transactions table
    if "transactions" in transactions_tables:
        counts["transactions"] = _write_table_with_metadata(
            transactions_tables["transactions"],
            "transactions",
            base_uri,
            dt,
            extra_metadata={
                "unmapped_players": transactions_tables.get(
                    "unmapped_players", pl.DataFrame()
                ).height,
                "unmapped_picks": transactions_tables.get("unmapped_picks", pl.DataFrame()).height,
            },
        )

    # Write QA tables (separate qa partition for observability)
    qa_base_uri = base_uri.replace("/commissioner", "/commissioner/transactions_qa")
    for qa_table_name in ["unmapped_players", "unmapped_picks"]:
        if qa_table_name in transactions_tables:
            table = transactions_tables[qa_table_name]
            if not table.is_empty():
                # QA files go directly in dt partition (no table subfolder)
                partition_uri = f"{qa_base_uri}/dt={dt}"
                _clear_partition_cloud(partition_uri)

                qa_uri = f"{partition_uri}/{qa_table_name}.parquet"
                write_parquet_any(table, qa_uri)
                counts[f"qa_{qa_table_name}"] = table.height

    return counts
