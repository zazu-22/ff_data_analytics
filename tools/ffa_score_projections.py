"""FFanalytics projections enrichment: weighting + scoring (scaffold).

Reads raw projections Parquet written by `scripts/R/ffanalytics_run.R`, applies
simple source weights from config YAML, and emits a canonical long-form table
with basic weighted fantasy points (QB/RB/WR/TE subset), if columns are present.

Usage:
  uv run python tools/ffa_score_projections.py \
    --raw-glob data/raw/ffanalytics/dt=*/projections_raw_*.parquet \
    --weights-yaml config/projections/ffanalytics_projections_config.yaml \
    --scoring-yaml config/scoring/sleeper_scoring_rules.yaml \
    --out data/raw/ffanalytics
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import yaml

from ingest.common.storage import write_parquet_any, write_text_sidecar


@dataclass
class Weights:
    """Projection source weights by provider id."""

    by_source: dict[str, float]


def load_weights(path: Path) -> Weights:
    """Load projection weights YAML and return a mapping object."""
    cfg = yaml.safe_load(path.read_text())
    sites = cfg.get("projections", {}).get("sites", [])
    return Weights(by_source={str(s.get("id")): float(s.get("weight", 1.0)) for s in sites})


def load_scoring(path: Path) -> dict[str, float]:
    """Load scoring rules YAML into a flat dict of multipliers."""
    cfg = yaml.safe_load(path.read_text())
    return {str(k): float(v) for k, v in (cfg.get("scoring", {}) or {}).items()}


def compute_weighted_points(
    frame: pl.DataFrame, weights: Weights, scoring: dict[str, float]
) -> pl.DataFrame:
    """Apply provider weights and heuristic fantasy point scoring to projections."""
    # Map weights by data_src if present
    if "data_src" in frame.columns:
        frame = frame.with_columns(
            provider_weight=pl.col("data_src").map_dict(weights.by_source, default=1.0)
        )
    else:
        frame = frame.with_columns(provider_weight=pl.lit(1.0))

    # Heuristic scoring based on common columns if present
    # This is a placeholder; replace with full rules mapping per position
    cols = {c for c in frame.columns}
    exprs = []
    if {"pass_yd", "pass_td", "int"}.issubset(cols):
        exprs.append(
            (pl.col("pass_yd") * scoring.get("pass_yd", 0.04))
            + (pl.col("pass_td") * scoring.get("pass_td", 4.0))
            + (pl.col("int") * scoring.get("int", -1.0))
        )
    if {"rush_yd", "rush_td"}.issubset(cols):
        exprs.append(
            (pl.col("rush_yd") * scoring.get("rush_yd", 0.1))
            + (pl.col("rush_td") * scoring.get("rush_td", 6.0))
        )
    if {"rec", "rec_yd", "rec_td"}.issubset(cols):
        exprs.append(
            (pl.col("rec") * scoring.get("rec", 0.5))
            + (pl.col("rec_yd") * scoring.get("rec_yd", 0.1))
            + (pl.col("rec_td") * scoring.get("rec_td", 6.0))
        )

    if exprs:
        frame = frame.with_columns(
            weighted_points=pl.sum_horizontal(exprs) * pl.col("provider_weight")
        )
    else:
        frame = frame.with_columns(weighted_points=pl.lit(None, dtype=pl.Float64))
    return frame


def to_long_form(frame: pl.DataFrame, id_cols: list[str]) -> pl.DataFrame:
    """Melt to long-form metrics keyed by given id columns."""
    # Keep id columns + single value column
    value_cols = [c for c in frame.columns if c not in set(id_cols)]
    melted = frame.melt(
        id_vars=id_cols, value_vars=value_cols, variable_name="metric", value_name="value"
    )
    return melted


def main() -> int:
    """CLI wrapper for reading raw projections, scoring, and writing outputs."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-glob", required=True)
    ap.add_argument("--weights-yaml", required=True)
    ap.add_argument("--scoring-yaml", required=True)
    ap.add_argument("--out", default="data/raw/ffanalytics")
    args = ap.parse_args()

    scans = pl.scan_parquet(args.raw_glob)
    raw = scans.collect()
    if raw.height == 0:
        print("No raw projections found; exiting")
        return 0

    weights = load_weights(Path(args.weights_yaml))
    scoring = load_scoring(Path(args.scoring_yaml))

    enriched = compute_weighted_points(raw, weights, scoring)
    # Minimal id columns we expect to be present in raw export
    id_cols = [
        c for c in ["season", "week", "position", "player", "data_src"] if c in enriched.columns
    ]
    long_df = to_long_form(enriched.select(id_cols + ["weighted_points"]), id_cols)

    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    out_uri = args.out.rstrip("/") + f"/dt={dt}/projections_weighted_{dt}.parquet"
    write_parquet_any(long_df, out_uri)
    meta_uri = args.out.rstrip("/") + f"/dt={dt}/_meta_weighted.json"
    write_text_sidecar(
        json.dumps(
            {
                "dataset": "ffanalytics_projections_weighted",
                "asof_datetime": datetime.now(UTC).isoformat(),
                "rows": long_df.height,
                "raw_files_glob": args.raw_glob,
            },
            indent=2,
        ),
        meta_uri,
    )
    print(out_uri)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
