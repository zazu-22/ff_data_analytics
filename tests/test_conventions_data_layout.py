from pathlib import Path


def test_local_data_dirs_exist():
    """Ensure local data directories mirror planned GCS layout."""
    for p in (Path("data/raw"), Path("data/stage"), Path("data/mart"), Path("data/ops")):
        assert p.exists(), f"Missing local data dir: {p}"


def test_samples_have_expected_files():
    """Spot-check expected sample Parquet files exist for quick iteration."""
    base = Path("samples")
    if not base.exists():
        return  # optional check
    # Spot check a few providers/datasets for parquet existence
    checks = [
        base / "nflverse" / "players" / "players.parquet",
        base / "nflverse" / "weekly" / "weekly.parquet",
        base / "sleeper" / "rosters" / "rosters.parquet",
    ]
    for path in checks:
        assert path.exists(), f"Expected sample parquet not found: {path}"
