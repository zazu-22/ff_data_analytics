"""Common storage helpers for local and cloud (GCS) paths.

Provides a thin wrapper around PyArrow's filesystem API so callers can
write Parquet and small sidecar files to either local paths or `gs://` URIs
without branching.

Env-driven credentials:
- GOOGLE_APPLICATION_CREDENTIALS: path to service account JSON
- GCS_SERVICE_ACCOUNT_JSON: inline JSON credentials (optional convenience)

Note: Directory creation is only needed for the local filesystem; GCS
"folders" are virtual and don't require pre-creation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    from pyarrow import fs as pafs
except Exception:  # pragma: no cover - keep import-time failures non-fatal for docs
    pa = None
    pq = None
    pafs = None


def is_gcs_uri(uri: str) -> bool:
    """Return True if `uri` looks like a GCS URI (prefixed with gs://)."""
    return isinstance(uri, str) and uri.strip().lower().startswith("gs://")


def _ensure_local_dir_for_uri(uri: str) -> None:
    """Ensure parent directory exists for a file URI if it's local.

    For non-GCS schemes, create the parent dirs.
    """
    if not is_gcs_uri(uri):
        parent = Path(uri).expanduser().resolve().parent
        parent.mkdir(parents=True, exist_ok=True)


def _maybe_stage_inline_gcs_key(tmp_dir: str | None = None) -> None:
    """If GCS_SERVICE_ACCOUNT_JSON is set, write it to a temp file and point
    GOOGLE_APPLICATION_CREDENTIALS at it. Safe to call multiple times.
    """
    key_json = os.environ.get("GCS_SERVICE_ACCOUNT_JSON")
    if not key_json:
        return
    try:
        # Validate JSON
        parsed: dict[str, Any] = json.loads(key_json)
        # Write to a deterministic path within repo temp area
        base = Path(tmp_dir or ".").resolve() / ".gcp"
        base.mkdir(parents=True, exist_ok=True)
        key_path = base / "sa_key.json"
        key_path.write_text(json.dumps(parsed))
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", key_path.as_posix())
    except Exception:
        # Best-effort; leave env as-is if invalid
        return


def write_parquet_any(dataframe: Any, dest_uri: str) -> str:
    """Write a DataFrame-like object to Parquet at `dest_uri`.

    - Accepts Polars, Pandas, or PyArrow Table/RecordBatchReader
    - Uses PyArrow filesystem API to handle local and GCS uniformly
    - Returns the fully qualified destination URI/path used
    """
    if pa is None or pq is None or pafs is None:  # pragma: no cover
        raise RuntimeError("pyarrow is required to write parquet files")

    _maybe_stage_inline_gcs_key()

    # Normalize dataframe to a PyArrow table
    try:
        import polars as pl  # type: ignore

        if isinstance(dataframe, pl.DataFrame):
            table = dataframe.to_arrow()
        else:
            # try pandas → arrow
            try:
                import pandas as pd  # type: ignore

                if isinstance(dataframe, pd.DataFrame):
                    table = pa.Table.from_pandas(dataframe, preserve_index=False)
                else:
                    # best-effort: construct via pa.Table.from_pylist
                    table = pa.Table.from_pylist(list(dataframe))
            except Exception:
                table = pa.Table.from_pylist(list(dataframe))
    except Exception:
        # Fallback without polars import
        try:
            import pandas as pd  # type: ignore

            if isinstance(dataframe, pd.DataFrame):
                table = pa.Table.from_pandas(dataframe, preserve_index=False)
            else:
                table = pa.Table.from_pylist(list(dataframe))
        except Exception as e:  # pragma: no cover
            raise RuntimeError("Unsupported dataframe type; install polars or pandas") from e

    # Create parent dirs for local files
    _ensure_local_dir_for_uri(dest_uri)

    filesystem, normalized_path = pafs.FileSystem.from_uri(dest_uri)
    pq.write_table(table, normalized_path, filesystem=filesystem)
    return dest_uri


def write_text_sidecar(text: str, dest_uri: str) -> str:
    """Write a small text file at `dest_uri` using PyArrow FS.

    Creates local parent directories if needed. Returns `dest_uri`.
    """
    if pafs is None:  # pragma: no cover
        raise RuntimeError("pyarrow is required to write files")

    _maybe_stage_inline_gcs_key()
    _ensure_local_dir_for_uri(dest_uri)

    filesystem, normalized_path = pafs.FileSystem.from_uri(dest_uri)
    with filesystem.open_output_stream(normalized_path) as out:
        out.write(text.encode("utf-8"))
    return dest_uri
