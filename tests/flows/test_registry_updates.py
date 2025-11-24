"""Unit tests for snapshot registry update logic across all flows.

This module tests the critical registry update logic that appears in multiple flows.
Registry updates must be atomic and idempotent to maintain data integrity.

Coverage targets:
- Registry update atomicity (old snapshots marked 'superseded')
- Idempotent re-runs (same snapshot date)
- Coverage metadata extraction
- Row count population from manifests
- Edge cases (first snapshot, missing fields)
"""

from pathlib import Path

import polars as pl


class TestRegistryUpdateLogic:
    """Test atomic snapshot registry updates."""

    def test_update_registry_marks_old_as_superseded(self, mock_registry_with_data, monkeypatch):
        """Test that new snapshot supersedes old one atomically."""
        from src.flows.nfl_data_pipeline import update_snapshot_registry

        # Mock the registry path to use our temp fixture
        def mock_path(*args):
            if "snapshot_registry.csv" in str(args[0]):
                return mock_registry_with_data
            return Path(args[0])

        monkeypatch.setattr("src.flows.nfl_data_pipeline.Path", mock_path)

        # Update with new snapshot
        result = update_snapshot_registry(
            source="nflverse",
            dataset="weekly",
            snapshot_date="2024-01-02",
            row_count=12000,
            coverage_start_season=2023,
            coverage_end_season=2024,
        )

        # Read updated registry
        registry = pl.read_csv(mock_registry_with_data)

        # Assertions
        assert result["success"] is True
        assert len(registry) == 3  # Old nflverse + new nflverse + ktc

        # Old snapshot should be superseded
        old = registry.filter(
            (pl.col("source") == "nflverse")
            & (pl.col("dataset") == "weekly")
            & (pl.col("snapshot_date") == "2024-01-01")
        )
        assert len(old) == 1
        assert old["status"][0] == "superseded"

        # New snapshot should be current
        new = registry.filter(
            (pl.col("source") == "nflverse")
            & (pl.col("dataset") == "weekly")
            & (pl.col("snapshot_date") == "2024-01-02")
        )
        assert len(new) == 1
        assert new["status"][0] == "current"
        assert new["row_count"][0] == 12000

        # KTC snapshot should be unchanged
        ktc = registry.filter((pl.col("source") == "ktc") & (pl.col("dataset") == "players"))
        assert len(ktc) == 1
        assert ktc["status"][0] == "current"

    def test_update_registry_idempotent(self, mock_registry_with_data, monkeypatch):
        """Test running update twice with same date is safe."""
        from src.flows.nfl_data_pipeline import update_snapshot_registry

        def mock_path(*args):
            if "snapshot_registry.csv" in str(args[0]):
                return mock_registry_with_data
            return Path(args[0])

        monkeypatch.setattr("src.flows.nfl_data_pipeline.Path", mock_path)

        # First update
        update_snapshot_registry(
            source="nflverse",
            dataset="weekly",
            snapshot_date="2024-01-02",
            row_count=12000,
            coverage_start_season=2023,
            coverage_end_season=2024,
        )

        # Second update (same date, different row count)
        update_snapshot_registry(
            source="nflverse",
            dataset="weekly",
            snapshot_date="2024-01-02",
            row_count=12500,  # Updated count
            coverage_start_season=2023,
            coverage_end_season=2024,
        )

        # Should have only 3 rows (old nflverse superseded + new nflverse + ktc), not 4
        registry = pl.read_csv(mock_registry_with_data)
        assert len(registry) == 3

        # Latest row count should be updated
        new = registry.filter(
            (pl.col("source") == "nflverse")
            & (pl.col("dataset") == "weekly")
            & (pl.col("snapshot_date") == "2024-01-02")
        )
        assert len(new) == 1
        assert new["row_count"][0] == 12500

    def test_update_registry_first_snapshot_for_source(self, mock_registry_with_data, monkeypatch):
        """Test adding first snapshot for a new source/dataset."""
        from src.flows.ktc_pipeline import update_snapshot_registry

        def mock_path(*args):
            if "snapshot_registry.csv" in str(args[0]):
                return mock_registry_with_data
            return Path(args[0])

        monkeypatch.setattr("src.flows.ktc_pipeline.Path", mock_path)

        # Add first snapshot for a new dataset (picks, not players which already exists)
        result = update_snapshot_registry(
            source="ktc",
            dataset="picks",  # Different dataset (players already exists in fixture)
            snapshot_date="2024-01-01",
            row_count=2000,
            market_scope="dynasty_1qb",
            notes="Initial KTC picks snapshot",
        )

        # Read registry
        registry = pl.read_csv(mock_registry_with_data)

        # Assertions
        assert result["success"] is True
        assert len(registry) == 3  # nflverse.weekly + ktc.players + ktc.picks

        # New snapshot should be current
        new = registry.filter((pl.col("source") == "ktc") & (pl.col("dataset") == "picks"))
        assert len(new) == 1
        assert new["status"][0] == "current"
        assert new["row_count"][0] == 2000
        assert "Initial KTC picks snapshot" in new["notes"][0]

    def test_update_registry_multiple_datasets_same_source(
        self, mock_registry_with_data, monkeypatch
    ):
        """Test that updating one dataset doesn't affect other datasets from same source."""
        from src.flows.nfl_data_pipeline import update_snapshot_registry

        def mock_path(*args):
            if "snapshot_registry.csv" in str(args[0]):
                return mock_registry_with_data
            return Path(args[0])

        monkeypatch.setattr("src.flows.nfl_data_pipeline.Path", mock_path)

        # Add a new dataset (snap_counts) for nflverse
        result = update_snapshot_registry(
            source="nflverse",
            dataset="snap_counts",
            snapshot_date="2024-01-01",
            row_count=8000,
            coverage_start_season=2024,
            coverage_end_season=2024,
        )

        registry = pl.read_csv(mock_registry_with_data)

        assert result["success"] is True

        # nflverse.weekly should still be current
        weekly = registry.filter(
            (pl.col("source") == "nflverse")
            & (pl.col("dataset") == "weekly")
            & (pl.col("snapshot_date") == "2024-01-01")
        )
        assert len(weekly) == 1
        assert weekly["status"][0] == "current"

        # snap_counts should be added as current
        snap_counts = registry.filter(
            (pl.col("source") == "nflverse") & (pl.col("dataset") == "snap_counts")
        )
        assert len(snap_counts) == 1
        assert snap_counts["status"][0] == "current"


class TestCoverageMetadataExtraction:
    """Test coverage metadata extraction from manifests."""

    def test_extract_row_count_from_manifest_top_level(self, sample_nflverse_weekly):
        """Test extracting row count from manifest with top-level parquet_file."""
        from src.flows.nfl_data_pipeline import extract_row_count_from_manifest

        manifest = {"parquet_file": str(sample_nflverse_weekly)}

        row_count = extract_row_count_from_manifest(manifest)

        assert row_count == 3

    def test_extract_row_count_from_manifest_nested(self, sample_nflverse_weekly):
        """Test extracting row count from manifest with nested meta.output_parquet."""
        from src.flows.nfl_data_pipeline import extract_row_count_from_manifest

        manifest = {"meta": {"output_parquet": str(sample_nflverse_weekly)}}

        row_count = extract_row_count_from_manifest(manifest)

        assert row_count == 3

    def test_extract_coverage_metadata_valid(self, sample_nflverse_weekly):
        """Test extracting season coverage from NFLverse data."""
        from src.flows.nfl_data_pipeline import extract_coverage_metadata

        manifest = {"parquet_file": str(sample_nflverse_weekly)}

        coverage = extract_coverage_metadata(manifest)

        assert coverage["coverage_start_season"] == 2024
        assert coverage["coverage_end_season"] == 2024

    def test_extract_coverage_metadata_missing_season_column(self, tmp_path):
        """Test graceful handling when season column is missing."""
        from src.flows.nfl_data_pipeline import extract_coverage_metadata

        # Create data without season column
        data = pl.DataFrame(
            {
                "player_id": ["P001", "P002"],
                "fantasy_points": [25.5, 18.2],
            }
        )

        path = tmp_path / "no_season.parquet"
        data.write_parquet(path)

        manifest = {"parquet_file": str(path)}

        coverage = extract_coverage_metadata(manifest)

        assert coverage["coverage_start_season"] is None
        assert coverage["coverage_end_season"] is None

    def test_extract_coverage_metadata_empty_data(self, tmp_path):
        """Test handling empty dataset."""
        from src.flows.nfl_data_pipeline import extract_coverage_metadata

        # Create empty DataFrame with schema
        data = pl.DataFrame(
            schema={
                "player_id": pl.Utf8,
                "season": pl.Int64,
            }
        )

        path = tmp_path / "empty.parquet"
        data.write_parquet(path)

        manifest = {"parquet_file": str(path)}

        coverage = extract_coverage_metadata(manifest)

        assert coverage["coverage_start_season"] is None
        assert coverage["coverage_end_season"] is None

    def test_extract_coverage_metadata_multi_season(self, tmp_path):
        """Test extracting coverage from multi-season dataset."""
        from src.flows.nfl_data_pipeline import extract_coverage_metadata

        data = pl.DataFrame(
            {
                "player_id": ["P001", "P002", "P003"],
                "season": [2022, 2023, 2024],
                "fantasy_points": [25.5, 18.2, 22.1],
            }
        )

        path = tmp_path / "multi_season.parquet"
        data.write_parquet(path)

        manifest = {"parquet_file": str(path)}

        coverage = extract_coverage_metadata(manifest)

        assert coverage["coverage_start_season"] == 2022
        assert coverage["coverage_end_season"] == 2024
