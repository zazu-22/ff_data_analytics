"""NFLverse production loader.

Usage:
    # Load current season weekly stats
    python scripts/ingest/load_nflverse.py --seasons 2025 --datasets weekly --out data/raw/nflverse

    # Load multiple datasets for current season
    python scripts/ingest/load_nflverse.py --seasons 2025 --datasets weekly,snap_counts,ff_opportunity --out data/raw/nflverse

    # Load historical backfill (2012-2024)
    python scripts/ingest/load_nflverse.py --seasons 2012-2024 --datasets weekly,snap_counts,ff_opportunity --out data/raw/nflverse

    # Load to GCS
    python scripts/ingest/load_nflverse.py --seasons 2025 --datasets weekly --out gs://ff-analytics/raw/nflverse

Outputs:
    - data/raw/nflverse/{dataset}/dt=YYYY-MM-DD/{dataset}_{uuid}.parquet
    - data/raw/nflverse/{dataset}/dt=YYYY-MM-DD/_meta.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ingest.nflverse.registry import REGISTRY
from src.ingest.nflverse.shim import load_nflverse


def parse_seasons(seasons_arg: str) -> list[int]:
    """Parse seasons argument.

    Args:
        seasons_arg: Comma-separated seasons (2020,2021) or range (2020-2024)

    Returns:
        List of season integers

    Examples:
        >>> parse_seasons("2020,2021,2022")
        [2020, 2021, 2022]
        >>> parse_seasons("2020-2024")
        [2020, 2021, 2022, 2023, 2024]
    """
    if "-" in seasons_arg and "," not in seasons_arg:
        # Range format: 2020-2024
        start, end = seasons_arg.split("-")
        return list(range(int(start), int(end) + 1))
    else:
        # Comma-separated: 2020,2021,2022
        return [int(s.strip()) for s in seasons_arg.split(",")]


def load_nflverse_runner(seasons: list[int], datasets: list[str], out_dir: str) -> dict:
    """Load NFLverse datasets for specified seasons.

    Args:
        seasons: List of season years (e.g., [2024, 2025])
        datasets: List of dataset names (e.g., ['weekly', 'snap_counts'])
        out_dir: Output directory (local or GCS)

    Returns:
        Manifest dict with load results
    """
    manifest = {
        "loaded_at": datetime.now().isoformat(),
        "seasons": seasons,
        "datasets_requested": datasets,
        "results": []
    }

    for dataset in datasets:
        if dataset not in REGISTRY:
            print(f"⚠️  Unknown dataset: {dataset} (skipping)")
            print(f"   Available: {', '.join(REGISTRY.keys())}")
            manifest["results"].append({
                "dataset": dataset,
                "status": "error",
                "error": f"Unknown dataset: {dataset}"
            })
            continue

        for season in seasons:
            print(f"Loading {dataset} for {season} season...")
            try:
                result = load_nflverse(
                    dataset=dataset,
                    seasons=[season],
                    out_dir=out_dir
                )

                # Extract key info from result
                status_info = {
                    "dataset": dataset,
                    "season": season,
                    "status": "success",
                    "partition_dir": result.get("partition_dir"),
                    "parquet_file": result.get("parquet_file"),
                    "loader_path": result.get("meta", {}).get("loader_path", "unknown")
                }

                manifest["results"].append(status_info)
                print(f"✅ Loaded {dataset} ({season}) → {result.get('partition_dir', 'unknown')}")

            except Exception as e:
                error_info = {
                    "dataset": dataset,
                    "season": season,
                    "status": "error",
                    "error": str(e)
                }
                manifest["results"].append(error_info)
                print(f"❌ Failed to load {dataset} ({season}): {e}")

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Load NFLverse datasets (weekly stats, snap counts, ff_opportunity, etc.)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Current season weekly stats
  python scripts/ingest/load_nflverse.py --seasons 2025 --datasets weekly

  # Multiple datasets for current season
  python scripts/ingest/load_nflverse.py --seasons 2025 --datasets weekly,snap_counts,ff_opportunity

  # Historical backfill (range syntax)
  python scripts/ingest/load_nflverse.py --seasons 2012-2024 --datasets weekly,snap_counts,ff_opportunity

Available datasets:
  %(datasets)s
""" % {"datasets": "\n  ".join(f"- {k}: {v.notes}" for k, v in REGISTRY.items())}
    )

    parser.add_argument(
        "--seasons",
        required=True,
        help="Seasons to load (comma-separated: 2020,2021 or range: 2020-2024)"
    )
    parser.add_argument(
        "--datasets",
        required=True,
        help=f"Datasets to load (comma-separated). Available: {', '.join(REGISTRY.keys())}"
    )
    parser.add_argument(
        "--out",
        default="data/raw/nflverse",
        help="Output directory (default: data/raw/nflverse)"
    )

    args = parser.parse_args()

    # Parse arguments
    seasons = parse_seasons(args.seasons)
    datasets = [d.strip() for d in args.datasets.split(",")]

    print("=" * 60)
    print("NFLverse Data Loader")
    print("=" * 60)
    print(f"Seasons: {seasons}")
    print(f"Datasets: {datasets}")
    print(f"Output dir: {args.out}")
    print()

    # Load data
    manifest = load_nflverse_runner(seasons, datasets, args.out)

    # Summary
    print()
    print("=" * 60)
    print("NFLverse data load complete!")
    print("=" * 60)

    success_count = sum(1 for r in manifest["results"] if r["status"] == "success")
    error_count = sum(1 for r in manifest["results"] if r["status"] == "error")

    print(f"Total loads: {len(manifest['results'])}")
    print(f"  ✅ Success: {success_count}")
    print(f"  ❌ Errors: {error_count}")

    if error_count > 0:
        print()
        print("Errors:")
        for result in manifest["results"]:
            if result["status"] == "error":
                print(f"  - {result['dataset']} ({result.get('season', 'N/A')}): {result['error']}")
        sys.exit(1)

    print()
    print("Loaded datasets:")
    for result in manifest["results"]:
        if result["status"] == "success":
            dataset = result['dataset']
            season = result['season']
            path = result.get('partition_dir', 'unknown')
            print(f"  - {dataset} ({season}) → {path}")


if __name__ == "__main__":
    main()
