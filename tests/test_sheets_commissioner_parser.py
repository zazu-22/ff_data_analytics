from __future__ import annotations

from pathlib import Path

import polars as pl

from ingest.sheets.commissioner_parser import parse_commissioner_dir, parse_gm_tab


def test_parse_single_gm_tab_samples():
    """Parse one GM tab sample and validate basic keys/coverage."""
    sample = Path("samples/sheets/Andy/Andy.csv")
    assert sample.exists(), "Sample sheet CSV not found"

    parsed = parse_gm_tab(sample)
    # Basic sanity
    assert parsed.gm.lower().startswith("andy"), "GM name detection failed"
    # Roster should have at least 1 row and required columns
    assert parsed.roster.height > 0
    assert set(["gm", "player", "position"]).issubset(parsed.roster.columns)
    # Keys present
    assert parsed.roster.filter(pl.col("gm").is_null()).height == 0
    assert parsed.roster.filter(pl.col("player").str.len_chars() == 0).height == 0


def test_parse_all_samples_dir():
    """Parse all sample GM tabs and ensure at least one picks row exists."""
    root = Path("samples/sheets")
    results = parse_commissioner_dir(root)
    assert len(results) >= 1
    # At least some picks should be parsed across GMs
    total_picks = sum(r.picks.height for r in results)
    assert total_picks >= 1
