"""ingest/nflverse/shim.py.

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

from ingest.common.storage import write_parquet_any, write_text_sidecar

from .registry import REGISTRY

try:
    import polars as pl
except Exception:
    pl = None  # type: ignore[assignment]  # Optional dependency - None when not installed (e.g., doc builds)


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


class LoaderResolutionError(RuntimeError):
    """Raised when a loader path fails to produce output."""

    pass


def _write_parquet(
    frame, out_path: str, dataset: str, loader_path: str, source_name: str, source_version: str
):
    """Write a dataframe to Parquet with a sidecar _meta.json.

    Supports both local paths and `gs://` destinations via PyArrow FS.
    """
    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    # Build partition directory URI (works for local and GCS)
    # Ensure no trailing slash duplication
    base = out_path.rstrip("/")
    partition_uri = f"{base}/{dataset}/dt={dt}"
    file_name = f"{dataset}_{uuid.uuid4().hex[:8]}.parquet"
    parquet_uri = f"{partition_uri}/{file_name}"

    # Write parquet using common storage helper (polars/pandas supported)
    write_parquet_any(frame, parquet_uri)

    meta = {
        "dataset": dataset,
        "asof_datetime": _utcnow_iso(),
        "loader_path": loader_path,
        "source_name": source_name,
        "source_version": source_version,
        "output_parquet": parquet_uri,
    }
    # Write sidecar metadata using the same FS abstraction
    write_text_sidecar(json.dumps(meta, indent=2), f"{partition_uri}/_meta.json")

    return {
        "dataset": dataset,
        "partition_dir": partition_uri,
        "parquet_file": parquet_uri,
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

    result_frame = func(**call_kwargs)
    # Get version if available
    try:
        source_version = importlib.import_module("nflreadpy").__version__
    except Exception:
        source_version = "unknown"
    return result_frame, f"python:{loader_path}", "nflverse", source_version


def _repo_root(start: Path) -> Path:
    for p in start.parents:
        if (p / "pyproject.toml").exists():
            return p
    return start.parents[3] if len(start.parents) >= 4 else start.parents[-1]


def _build_r_command(script: Path, spec, seasons=None, weeks=None, out_dir=None) -> list[str]:
    cmd = ["Rscript", script.as_posix(), "--dataset", spec.name]
    if seasons is not None:
        cmd += [
            "--seasons",
            ",".join(map(str, seasons)) if isinstance(seasons, list | tuple) else str(seasons),
        ]
    if weeks is not None:
        cmd += [
            "--weeks",
            ",".join(map(str, weeks)) if isinstance(weeks, list | tuple) else str(weeks),
        ]
    if out_dir:
        cmd += ["--out_dir", out_dir]
    return cmd


def _parse_r_output(proc: subprocess.CompletedProcess) -> tuple[dict, str, str, str]:
    if proc.returncode != 0:
        raise LoaderResolutionError(f"R loader failed: {proc.stderr[:500]}")
    try:
        manifest = json.loads(proc.stdout.strip().splitlines()[-1])
        return manifest, "r:nflreadr", "nflverse", "nflreadr"
    except Exception:
        return (
            {
                "note": "Runner did not return JSON manifest; check logs.",
                "stdout_tail": proc.stdout.strip()[-500:],
            },
            "r:nflreadr",
            "nflverse",
            "nflreadr",
        )


def _load_with_r(spec, seasons=None, weeks=None, out_dir=None, **kwargs):
    here = Path(__file__).resolve()
    script = _repo_root(here) / "scripts" / "R" / "nflverse_load.R"
    cmd = _build_r_command(script, spec, seasons=seasons, weeks=weeks, out_dir=out_dir)
    proc = subprocess.run(  # noqa: S603
        cmd, capture_output=True, text=True, check=False, env=os.environ.copy()
    )
    return _parse_r_output(proc)


def load_nflverse(
    dataset: str,
    seasons: int | list[int] | None = None,
    weeks: int | list[int] | None = None,
    out_dir: str = "data/raw/nflverse",
    loader_preference: str = "python_first",
    **kwargs,
) -> dict[str, Any]:
    """Unified loader for nflverse datasets.

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
        frame, loader_path, source_name, source_version = _load_with_python(
            spec, seasons=seasons, weeks=weeks, **kwargs
        )
        manifest = _write_parquet(frame, out_dir, dataset, loader_path, source_name, source_version)
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
