"""Unit tests for KTC pipeline validation logic.

This module tests KTC-specific governance validation:
- Valuation range checks (0-10000 sanity check)
- Player mapping coverage (>90% against dim_player_id_xref)
- Missing player reporting
- Outlier detection
"""

import polars as pl
import pytest


class TestValuationRanges:
    """Test KTC valuation range validation (0-10000)."""

    def test_valuation_ranges_valid_data(self, sample_manifest_ktc):
        """Test validation passes with valid valuations."""
        from src.flows.ktc_pipeline import validate_valuation_ranges

        result = validate_valuation_ranges(sample_manifest_ktc, "players")

        assert result["is_valid"] is True
        assert result["dataset"] == "players"
        assert result["anomalies"] == []
        assert result["min_value"] == 3500
        assert result["max_value"] == 8000
        assert result["outlier_count"] == 0

    def test_valuation_ranges_negative_values(self, sample_ktc_players_invalid):
        """Test validation catches negative values."""
        from src.flows.ktc_pipeline import validate_valuation_ranges

        manifest = {"output_path": str(sample_ktc_players_invalid), "dataset": "players"}

        result = validate_valuation_ranges(manifest, "players")

        assert result["is_valid"] is False
        assert len(result["anomalies"]) == 2  # Both negative and excessive
        assert any("Negative values" in a for a in result["anomalies"])
        assert any("Excessive values" in a for a in result["anomalies"])
        assert result["outlier_count"] == 2  # Player D (-100) and Player E (15000)
        assert result["min_value"] == -100
        assert result["max_value"] == 15000

    def test_valuation_ranges_excessive_values_only(self, tmp_path):
        """Test validation catches excessive values (>10000)."""
        from src.flows.ktc_pipeline import validate_valuation_ranges

        # Create data with only excessive values
        data = pl.DataFrame(
            {
                "player_name": ["Player X", "Player Y"],
                "value": [12000, 15000],  # Both excessive
                "position": ["QB", "RB"],
            }
        )

        path = tmp_path / "excessive.parquet"
        data.write_parquet(path)

        manifest = {"output_path": str(path), "dataset": "players"}

        result = validate_valuation_ranges(manifest, "players")

        assert result["is_valid"] is False
        assert len(result["anomalies"]) == 1  # Only excessive warning
        assert "Excessive values" in result["anomalies"][0]
        assert result["outlier_count"] == 2
        assert result["max_value"] == 15000

    def test_valuation_ranges_edge_values(self, tmp_path):
        """Test validation with edge values (0 and 10000)."""
        from src.flows.ktc_pipeline import validate_valuation_ranges

        # Create data with boundary values
        data = pl.DataFrame(
            {
                "player_name": ["Player Min", "Player Max"],
                "value": [0, 10000],  # Exactly at boundaries
                "position": ["QB", "RB"],
            }
        )

        path = tmp_path / "edges.parquet"
        data.write_parquet(path)

        manifest = {"output_path": str(path), "dataset": "players"}

        result = validate_valuation_ranges(manifest, "players")

        assert result["is_valid"] is True  # Boundaries are valid
        assert result["anomalies"] == []
        assert result["outlier_count"] == 0
        assert result["min_value"] == 0
        assert result["max_value"] == 10000

    def test_valuation_ranges_missing_value_column(self, tmp_path, capsys):
        """Test graceful error when value column is missing."""
        from src.flows.ktc_pipeline import validate_valuation_ranges

        # Create data without value column
        data = pl.DataFrame(
            {
                "player_name": ["Player A"],
                "position": ["QB"],
            }
        )

        path = tmp_path / "no_value.parquet"
        data.write_parquet(path)

        manifest = {"output_path": str(path), "dataset": "players"}

        # Should raise error when value column is missing
        with pytest.raises((KeyError, Exception)):  # Polars raises when accessing missing column
            validate_valuation_ranges(manifest, "players")


class TestPlayerMapping:
    """Test KTC player mapping coverage validation."""

    def test_player_mapping_high_coverage(self, sample_manifest_ktc, mock_duckdb_xref, monkeypatch):
        """Test validation passes with >90% coverage."""
        from src.flows.ktc_pipeline import validate_player_mapping

        # Mock the xref path
        def mock_path(*args):
            if "dev.duckdb" in str(args[0]):
                return mock_duckdb_xref
            return args[0]

        monkeypatch.setattr("src.flows.ktc_pipeline.Path", mock_path)

        result = validate_player_mapping(sample_manifest_ktc, min_coverage_pct=90.0)

        assert result["is_valid"] is True
        assert result["total_players"] == 3
        assert result["mapped_count"] == 3  # All 3 players (A, B, C) are in xref
        assert result["unmapped_count"] == 0
        assert result["coverage_pct"] == 100.0
        assert result["top_unmapped"] == []

    def test_player_mapping_low_coverage(self, tmp_path, mock_duckdb_xref, monkeypatch):
        """Test validation fails when coverage <90%."""
        from src.flows.ktc_pipeline import validate_player_mapping

        # Create KTC data with mostly unmapped players
        data = pl.DataFrame(
            {
                "player_name": [
                    "Player A",
                    "Unmapped 1",
                    "Unmapped 2",
                    "Unmapped 3",
                    "Unmapped 4",
                ],
                "value": [5000, 6000, 7000, 8000, 9000],
                "position": ["QB", "RB", "WR", "TE", "RB"],
            }
        )

        path = tmp_path / "low_coverage.parquet"
        data.write_parquet(path)

        manifest = {"output_path": str(path)}

        def mock_path(*args):
            if "dev.duckdb" in str(args[0]):
                return mock_duckdb_xref
            return args[0]

        monkeypatch.setattr("src.flows.ktc_pipeline.Path", mock_path)

        result = validate_player_mapping(manifest, min_coverage_pct=90.0)

        assert result["is_valid"] is False
        assert result["total_players"] == 5
        assert result["mapped_count"] == 1  # Only Player A
        assert result["unmapped_count"] == 4
        assert result["coverage_pct"] == 20.0  # 1/5 = 20%
        assert len(result["top_unmapped"]) == 4

    def test_player_mapping_xref_not_available(self, sample_manifest_ktc, tmp_path, monkeypatch):
        """Test graceful handling when dim_player_id_xref doesn't exist."""
        from src.flows.ktc_pipeline import validate_player_mapping

        # Mock path to non-existent xref
        def mock_path(*args):
            if "dev.duckdb" in str(args[0]):
                return tmp_path / "nonexistent.duckdb"
            return args[0]

        monkeypatch.setattr("src.flows.ktc_pipeline.Path", mock_path)

        result = validate_player_mapping(sample_manifest_ktc, min_coverage_pct=90.0)

        # Should skip validation gracefully
        assert result["is_valid"] is True
        assert "reason" in result
        assert "not available" in result["reason"]

    def test_player_mapping_top_unmapped_reporting(self, tmp_path, mock_duckdb_xref, monkeypatch):
        """Test that top 10 unmapped players are reported for investigation."""
        from src.flows.ktc_pipeline import validate_player_mapping

        # Create data with 15 unmapped players (should report top 10)
        unmapped_names = [f"Unmapped Player {i}" for i in range(1, 16)]
        data = pl.DataFrame(
            {
                "player_name": unmapped_names,
                "value": list(range(5000, 5000 + len(unmapped_names))),
            }
        )

        path = tmp_path / "many_unmapped.parquet"
        data.write_parquet(path)

        manifest = {"output_path": str(path)}

        def mock_path(*args):
            if "dev.duckdb" in str(args[0]):
                return mock_duckdb_xref
            return args[0]

        monkeypatch.setattr("src.flows.ktc_pipeline.Path", mock_path)

        result = validate_player_mapping(manifest, min_coverage_pct=90.0)

        assert result["is_valid"] is False
        assert result["unmapped_count"] == 15
        assert len(result["top_unmapped"]) == 10  # Only top 10 reported

    def test_player_mapping_missing_player_name_column(
        self, tmp_path, mock_duckdb_xref, monkeypatch
    ):
        """Test error handling when player_name column is missing."""
        from src.flows.ktc_pipeline import validate_player_mapping

        # Create data without player_name column
        data = pl.DataFrame(
            {
                "value": [5000, 6000],
                "position": ["QB", "RB"],
            }
        )

        path = tmp_path / "no_player_name.parquet"
        data.write_parquet(path)

        manifest = {"output_path": str(path)}

        def mock_path(*args):
            if "dev.duckdb" in str(args[0]):
                return mock_duckdb_xref
            return args[0]

        monkeypatch.setattr("src.flows.ktc_pipeline.Path", mock_path)

        # Should raise error when player_name column is missing
        with pytest.raises((KeyError, Exception)):  # Raises when checking columns
            validate_player_mapping(manifest)
