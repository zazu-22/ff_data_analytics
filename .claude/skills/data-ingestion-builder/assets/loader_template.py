"""ingest/{PROVIDER}/loader.py.

Loader functions for {PROVIDER} data source.
Each function fetches data from the provider and writes to Parquet using storage helpers.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

try:
    import polars as pl
except Exception:
    pl = None

from ingest.common.storage import write_parquet_any, write_text_sidecar


def load_{dataset_name}(
    out_dir: str = "data/raw/{provider}",
    **kwargs
) -> dict[str, Any]:
    """Load {dataset_name} from {PROVIDER}.

    Args:
        out_dir: Output directory (local path or gs:// URI)
        **kwargs: Provider-specific parameters (e.g., date_range, filters, etc.)

    Returns:
        dict: Manifest with output paths and metadata

    Example:
        >>> result = load_{dataset_name}(out_dir="data/raw/{provider}")
        >>> print(result["parquet_file"])
    """
    # Step 1: Fetch data from provider
    # TODO: Implement data fetching logic here
    # Example:
    # - API calls
    # - File parsing
    # - Database queries
    data = _fetch_data_from_provider(**kwargs)

    # Step 2: Convert to DataFrame (Polars recommended, Pandas acceptable)
    if pl is not None:
        df = pl.DataFrame(data)
    else:
        import pandas as pd
        df = pd.DataFrame(data)

    # Step 3: Write to Parquet with metadata using storage helper
    dataset_name = "{dataset_name}"
    dt = datetime.now(UTC).strftime("%Y-%m-%d")

    # Build partition directory
    base = out_dir.rstrip("/")
    partition_dir = f"{base}/{dataset_name}/dt={dt}"
    parquet_file = f"{partition_dir}/{dataset_name}_{_generate_uuid()}.parquet"

    # Write Parquet
    write_parquet_any(df, parquet_file)

    # Write metadata sidecar
    metadata = {
        "dataset": dataset_name,
        "asof_datetime": datetime.now(UTC).isoformat(),
        "loader_path": "src.ingest.{provider}.loader.load_{dataset_name}",
        "source_name": "{PROVIDER}",
        "source_version": "{VERSION}",  # Update with actual version if available
        "output_parquet": parquet_file,
        "row_count": len(df),
        **kwargs  # Include any input parameters for traceability
    }
    write_text_sidecar(json.dumps(metadata, indent=2), f"{partition_dir}/_meta.json")

    return {
        "dataset": dataset_name,
        "partition_dir": partition_dir,
        "parquet_file": parquet_file,
        "row_count": len(df),
        "metadata": metadata
    }


def _fetch_data_from_provider(**kwargs) -> list[dict]:
    """Fetch data from provider API/file/database.

    TODO: Implement actual data fetching logic.

    Returns:
        list[dict]: Raw data records
    """
    # Example API call:
    # import requests
    # response = requests.get("{PROVIDER_API_URL}", params=kwargs)
    # return response.json()

    # Example file parsing:
    # import csv
    # with open(file_path) as f:
    #     return list(csv.DictReader(f))

    raise NotImplementedError("Implement data fetching for {PROVIDER}")


def _generate_uuid() -> str:
    """Generate short UUID for file naming."""
    import uuid
    return uuid.uuid4().hex[:8]
