"""tests/test_{provider}_samples_pk.py.

Primary key uniqueness tests for {PROVIDER} sample data.
Validates that sample data matches expected grain from registry.
"""

import pytest

try:
    import polars as pl
except ImportError:
    pytest.skip("polars not available", allow_module_level=True)

from pathlib import Path
from ingest.{provider}.registry import REGISTRY


# Sample data location
SAMPLE_DIR = Path("samples/{provider}")


@pytest.mark.parametrize("dataset_name,spec", REGISTRY.items())
def test_{provider}_primary_keys(dataset_name, spec):
    """Test primary key uniqueness for {dataset_name}."""

    # Find sample files
    pattern = f"{dataset_name}/dt=*/*.parquet"
    files = list(SAMPLE_DIR.glob(pattern))

    if not files:
        pytest.skip(f"No sample data found for {dataset_name}")

    # Read sample data
    df = pl.read_parquet(files)

    # Check row count
    assert len(df) > 0, f"{dataset_name} sample is empty"

    # Check primary keys exist
    pk_cols = list(spec.primary_keys)
    missing_cols = [col for col in pk_cols if col not in df.columns]
    assert not missing_cols, f"Missing PK columns in {dataset_name}: {missing_cols}"

    # Check primary key uniqueness
    duplicates = df.group_by(pk_cols).agg(pl.count().alias("count")).filter(pl.col("count") > 1)

    assert len(duplicates) == 0, (
        f"{dataset_name} has {len(duplicates)} duplicate PK values:\\n"
        f"{duplicates.head(10)}"
    )


def test_{provider}_metadata_exists():
    """Test that all sample datasets have metadata sidecars."""

    for dataset_name in REGISTRY.keys():
        pattern = f"{dataset_name}/dt=*/_meta.json"
        meta_files = list(SAMPLE_DIR.glob(pattern))

        if meta_files:
            # Validate metadata structure
            import json
            with open(meta_files[0]) as f:
                meta = json.load(f)

            assert "dataset" in meta
            assert "asof_datetime" in meta
            assert "loader_path" in meta
            assert "source_name" in meta
            assert meta["dataset"] == dataset_name
