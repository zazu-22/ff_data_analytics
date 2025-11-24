"""Unit tests for Sleeper pipeline validation logic.

This module tests Sleeper-specific governance validation:
- Roster size validation (25-35 players for dynasty)
- Player mapping coverage validation
"""

import polars as pl
import pytest


class TestRosterSizeValidation:
    """Test Sleeper roster size validation."""

    def test_roster_sizes_valid(self, tmp_path):
        """Test validation passes with roster sizes in expected range."""
        from src.flows.sleeper_pipeline import validate_roster_sizes

        # Create rosters with valid sizes (25-35)
        data = pl.DataFrame(
            {
                "roster_id": [1, 2, 3],
                "owner_id": ["user1", "user2", "user3"],
                "players": [
                    ["P001", "P002", "P003"] + [f"P{i:03d}" for i in range(4, 27)],  # 26 players
                    ["P101", "P102"] + [f"P{i:03d}" for i in range(103, 130)],  # 29 players
                    ["P201"] + [f"P{i:03d}" for i in range(202, 233)],  # 32 players
                ],
            }
        )

        roster_path = tmp_path / "rosters.parquet"
        data.write_parquet(roster_path)

        manifest = {"datasets": {"rosters": {"path": str(roster_path)}}}

        result = validate_roster_sizes(manifest, min_roster_size=25, max_roster_size=35)

        assert result["is_valid"] is True
        assert result["anomalies"] == []
        assert result["min_size"] == 26
        assert result["max_size"] == 32
        assert result["outlier_count"] == 0
        assert result["total_rosters"] == 3

    def test_roster_sizes_too_small(self, tmp_path):
        """Test validation catches rosters below minimum size."""
        from src.flows.sleeper_pipeline import validate_roster_sizes

        # Create rosters with some too small
        data = pl.DataFrame(
            {
                "roster_id": [1, 2],
                "owner_id": ["user1", "user2"],
                "players": [
                    ["P001", "P002", "P003"],  # Only 3 players (way too small)
                    ["P101"] + [f"P{i:03d}" for i in range(102, 132)],  # 31 players (valid)
                ],
            }
        )

        roster_path = tmp_path / "rosters_small.parquet"
        data.write_parquet(roster_path)

        manifest = {"datasets": {"rosters": {"path": str(roster_path)}}}

        result = validate_roster_sizes(manifest, min_roster_size=25, max_roster_size=35)

        assert result["is_valid"] is False
        assert len(result["anomalies"]) >= 1
        assert any("too small" in a for a in result["anomalies"])
        assert result["min_size"] == 3
        assert result["outlier_count"] == 1

    def test_roster_sizes_too_large(self, tmp_path):
        """Test validation catches rosters above maximum size."""
        from src.flows.sleeper_pipeline import validate_roster_sizes

        # Create rosters with some too large
        data = pl.DataFrame(
            {
                "roster_id": [1, 2],
                "owner_id": ["user1", "user2"],
                "players": [
                    ["P001"] + [f"P{i:03d}" for i in range(2, 28)],  # 27 players (valid)
                    ["P101"] + [f"P{i:03d}" for i in range(102, 143)],  # 42 players (too large)
                ],
            }
        )

        roster_path = tmp_path / "rosters_large.parquet"
        data.write_parquet(roster_path)

        manifest = {"datasets": {"rosters": {"path": str(roster_path)}}}

        result = validate_roster_sizes(manifest, min_roster_size=25, max_roster_size=35)

        assert result["is_valid"] is False
        assert len(result["anomalies"]) >= 1
        assert any("too large" in a for a in result["anomalies"])
        assert result["max_size"] == 42
        assert result["outlier_count"] == 1

    def test_roster_sizes_no_rosters_dataset(self, tmp_path):
        """Test graceful handling when rosters dataset is missing."""
        from src.flows.sleeper_pipeline import validate_roster_sizes

        manifest = {"datasets": {"users": {"path": "/some/path"}}}  # No rosters

        result = validate_roster_sizes(manifest)

        assert result["is_valid"] is False
        assert "reason" in result
        assert "No rosters dataset" in result["reason"]

    def test_roster_sizes_missing_players_column(self, tmp_path, capsys):
        """Test error handling when players column is missing."""
        from src.flows.sleeper_pipeline import validate_roster_sizes

        # Create data without players column
        data = pl.DataFrame(
            {
                "roster_id": [1, 2],
                "owner_id": ["user1", "user2"],
            }
        )

        roster_path = tmp_path / "no_players.parquet"
        data.write_parquet(roster_path)

        manifest = {"datasets": {"rosters": {"path": str(roster_path)}}}

        # Should raise error when players column is missing
        with pytest.raises((KeyError, Exception)):  # Raises when accessing missing column
            validate_roster_sizes(manifest)

    def test_roster_sizes_empty_rosters(self, tmp_path):
        """Test handling of empty player lists (should be flagged as too small)."""
        from src.flows.sleeper_pipeline import validate_roster_sizes

        data = pl.DataFrame(
            {
                "roster_id": [1, 2],
                "owner_id": ["user1", "user2"],
                "players": [
                    [],  # Empty roster
                    ["P001"] + [f"P{i:03d}" for i in range(2, 32)],  # 31 players (valid)
                ],
            }
        )

        roster_path = tmp_path / "empty_roster.parquet"
        data.write_parquet(roster_path)

        manifest = {"datasets": {"rosters": {"path": str(roster_path)}}}

        result = validate_roster_sizes(manifest, min_roster_size=25, max_roster_size=35)

        assert result["is_valid"] is False
        assert result["min_size"] == 0
        assert result["outlier_count"] == 1


class TestSleeperPlayerMapping:
    """Test Sleeper player mapping coverage validation."""

    def test_player_mapping_validation_skip_when_no_xref(self, tmp_path, monkeypatch):
        """Test graceful skip when xref DB doesn't exist."""
        from src.flows.sleeper_pipeline import validate_sleeper_player_mapping

        # Create minimal valid sleeper players data with required column
        players_data = pl.DataFrame(
            {
                "player_id": ["1", "2"],
                "sleeper_player_id": ["1", "2"],  # Required column
                "full_name": ["Player A", "Player B"],
            }
        )

        players_path = tmp_path / "players.parquet"
        players_data.write_parquet(players_path)

        manifest = {"datasets": {"players": {"path": str(players_path)}}}

        # Mock path to non-existent xref (should skip validation gracefully)
        def mock_path(*args):
            if "dev.duckdb" in str(args[0]):
                return tmp_path / "nonexistent.duckdb"
            return args[0]

        monkeypatch.setattr("src.flows.sleeper_pipeline.Path", mock_path)

        # Should skip validation when xref not available
        result = validate_sleeper_player_mapping(manifest, min_coverage_pct=85.0)

        # Should return valid result with reason
        assert result["is_valid"] is True
        assert "reason" in result
        assert "not available" in result["reason"]
