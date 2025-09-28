"""
ingest/nflverse/shim.py

Python-first loader for nflverse datasets.
- Tries nflreadpy
- Falls back to an Rscript that uses nflreadr

Usage:
    from ingest.nflverse.shim import load_nflverse

    # Local development (default):
    load_nflverse("players", seasons=[2020,2021])  # writes to data/raw/nflverse/

    # Production (GitHub Actions will specify GCS path):
    load_nflverse("players", seasons=[2020,2021], out_dir="gs://ff-analytics/raw/nflverse")

Note: GCS writes require additional libraries (gcsfs/google-cloud-storage).
Current implementation treats all paths as local filesystem paths.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import polars as pl
except Exception:
    pl = None  # allow import when polars not installed (e.g., doc builds)

from .registry import REGISTRY


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


class LoaderResolutionError(RuntimeError):
    pass


def _write_parquet(
    df, out_path: str, dataset: str, loader_path: str, source_name: str, source_version: str
):
    """Write a polars or pandas dataframe to Parquet with a sidecar _meta.json."""
    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    partition_dir = Path(out_path) / dataset / f"dt={dt}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{dataset}_{uuid.uuid4().hex[:8]}.parquet"
    file_path = partition_dir / file_name

    # Convert to polars if possible
    if pl is not None:
        if not isinstance(df, pl.DataFrame):
            try:
                df = pl.from_pandas(df) if hasattr(df, "to_dict") else pl.DataFrame(df)
            except Exception:
                pass
        df.write_parquet(file_path.as_posix())
    else:
        # Try pandas fallback
        try:
            import pandas as pd

            if not isinstance(df, pd.DataFrame):
                df = pd.DataFrame(df)
            df.to_parquet(file_path.as_posix(), index=False, engine="pyarrow")
        except Exception as e:
            raise RuntimeError(f"Failed to write Parquet: {e}") from e

    meta = {
        "dataset": dataset,
        "asof_datetime": _utcnow_iso(),
        "loader_path": loader_path,
        "source_name": source_name,
        "source_version": source_version,
        "output_parquet": file_path.as_posix(),
    }
    (partition_dir / "_meta.json").write_text(json.dumps(meta, indent=2))
    return {
        "dataset": dataset,
        "partition_dir": partition_dir.as_posix(),
        "parquet_file": file_path.as_posix(),
        "meta": meta,
    }


def _load_with_python(spec, seasons=None, weeks=None, **kwargs):
    loader_path = spec.py_loader
    module_name, func_name = loader_path.rsplit(".", 1)
    mod = importlib.import_module(module_name)
    func = getattr(mod, func_name)

    # nflreadpy API varies; check function signature and only pass applicable params
    import inspect

    sig = inspect.signature(func)
    params = sig.parameters

    call_kwargs = {}
    if "seasons" in params and seasons is not None:
        call_kwargs["seasons"] = seasons
    if "weeks" in params and weeks is not None:
        call_kwargs["weeks"] = weeks
    # Pass through any other kwargs that the function accepts
    for k, v in (kwargs or {}).items():
        if k in params:
            call_kwargs[k] = v

    df = func(**call_kwargs)
    # Get version if available
    try:
        source_version = importlib.import_module("nflreadpy").__version__
    except Exception:
        source_version = "unknown"
    return df, f"python:{loader_path}", "nflverse", source_version


def _load_with_r(spec, seasons=None, weeks=None, out_dir=None, **kwargs):
    # Call Rscript runner
    script = Path(__file__).resolve().parents[2] / "scripts" / "R" / "nflverse_load.R"
    cmd = ["Rscript", script.as_posix(), "--dataset", spec.name]
    if seasons is not None:
        if isinstance(seasons, list | tuple):
            cmd += ["--seasons", ",".join(map(str, seasons))]
        else:
            cmd += ["--seasons", str(seasons)]
    if weeks is not None:
        if isinstance(weeks, list | tuple):
            cmd += ["--weeks", ",".join(map(str, weeks))]
        else:
            cmd += ["--weeks", str(weeks)]
    if out_dir:
        cmd += ["--out_dir", out_dir]
    # extra args are ignored by default; extend runner if needed
    env = os.environ.copy()
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    if proc.returncode != 0:
        raise LoaderResolutionError(f"R loader failed: {proc.stderr[:500]}")
    # Expect runner to print a single-line JSON manifest to stdout
    try:
        manifest = json.loads(proc.stdout.strip().splitlines()[-1])
        return manifest, "r:nflreadr", "nflverse", "nflreadr"
    except Exception:
        # If no JSON manifest, return minimal info
        return (
            {
                "note": "Runner did not return JSON manifest; check logs.",
                "stdout_tail": proc.stdout.strip()[-500:],
            },
            "r:nflreadr",
            "nflverse",
            "nflreadr",
        )


def load_nflverse(
    dataset: str,
    seasons: int | list[int] | None = None,
    weeks: int | list[int] | None = None,
    out_dir: str = "data/raw/nflverse",
    loader_preference: str = "python_first",
    **kwargs,
) -> dict[str, Any]:
    """
    Unified loader for nflverse datasets.

    Returns a manifest dict with keys:
      - dataset, partition_dir, parquet_file (if python path wrote it), meta
    """
    if dataset not in REGISTRY:
        raise KeyError(f"Unknown dataset '{dataset}'. Known: {list(REGISTRY.keys())}")

    spec = REGISTRY[dataset]

    if loader_preference == "r_only":
        manifest, loader_path, source_name, source_version = _load_with_r(
            spec, seasons=seasons, weeks=weeks, out_dir=out_dir, **kwargs
        )
        if isinstance(manifest, dict) and "output_parquet" in manifest:
            # R loader returned full manifest
            return manifest
        else:
            # Minimal response
            return {
                "dataset": dataset,
                "loader_path": loader_path,
                "source_name": source_name,
                "source_version": source_version,
            }

    # Try python path first
    try:
        df, loader_path, source_name, source_version = _load_with_python(
            spec, seasons=seasons, weeks=weeks, **kwargs
        )
        manifest = _write_parquet(df, out_dir, dataset, loader_path, source_name, source_version)
        return manifest
    except (NotImplementedError, AttributeError, ModuleNotFoundError):
        # Fallback to R
        manifest, loader_path, source_name, source_version = _load_with_r(
            spec, seasons=seasons, weeks=weeks, out_dir=out_dir, **kwargs
        )
        if isinstance(manifest, dict) and "output_parquet" in manifest:
            # R loader returned full manifest
            return manifest
        else:
            # Minimal fallback response
            return {
                "dataset": dataset,
                "loader_path": loader_path,
                "source_name": source_name,
                "source_version": source_version,
                "fallback": True,
            }
