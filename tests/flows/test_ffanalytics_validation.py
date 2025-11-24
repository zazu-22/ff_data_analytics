"""Unit tests for FFAnalytics pipeline validation logic.

This module tests FFAnalytics-specific governance validation:
- Projection reasonableness checks (no negative values)
- Statistical outlier detection (>3 std devs from position mean)
- Reasonable upper bounds validation
"""

import polars as pl


class TestProjectionRanges:
    """Test FFAnalytics projection range validation."""

    def test_projection_ranges_valid_data(self, tmp_path):
        """Test validation passes with reasonable projections."""
        from src.flows.ffanalytics_pipeline import validate_projection_ranges

        # Create valid consensus projections
        data = pl.DataFrame(
            {
                "player_name": ["QB1", "RB1", "WR1"],
                "position": ["QB", "RB", "WR"],
                "pass_yds": [4500, 0, 0],
                "pass_tds": [30, 0, 0],
                "rush_yds": [200, 1200, 50],
                "rush_tds": [2, 12, 0],
                "rec": [0, 60, 100],
                "rec_yds": [0, 500, 1300],
                "rec_tds": [0, 3, 8],
                "fpts": [350, 280, 250],
            }
        )

        consensus_path = tmp_path / "consensus.parquet"
        data.write_parquet(consensus_path)

        manifest = {"output_files": {"consensus": str(consensus_path)}}

        result = validate_projection_ranges(manifest)

        assert result["is_valid"] is True
        assert result.get("anomalies", []) == []

    def test_projection_ranges_negative_values(self, tmp_path):
        """Test validation catches negative projection values."""
        from src.flows.ffanalytics_pipeline import validate_projection_ranges

        # Create projections with negative values (data quality issue)
        data = pl.DataFrame(
            {
                "player_name": ["QB1", "RB1"],
                "position": ["QB", "RB"],
                "pass_yds": [4500, 0],
                "rush_yds": [-50, 1200],  # Negative!
                "fpts": [350, -20],  # Negative!
            }
        )

        consensus_path = tmp_path / "consensus_invalid.parquet"
        data.write_parquet(consensus_path)

        manifest = {"output_files": {"consensus": str(consensus_path)}}

        result = validate_projection_ranges(manifest)

        assert result["is_valid"] is False
        assert len(result["anomalies"]) >= 2  # rush_yds and fpts
        assert any("Negative values in rush_yds" in a for a in result["anomalies"])
        assert any("Negative values in fpts" in a for a in result["anomalies"])

    def test_projection_ranges_excessive_values(self, tmp_path):
        """Test warning for statistically improbable projections."""
        from src.flows.ffanalytics_pipeline import validate_projection_ranges

        # Create projections with excessive values (outliers)
        data = pl.DataFrame(
            {
                "player_name": ["Super QB"],
                "position": ["QB"],
                "pass_yds": [7000],  # Way over reasonable max (6000)
                "rush_yds": [3000],  # Way over reasonable max (2500)
                "fpts": [700],  # Way over reasonable max (600)
            }
        )

        consensus_path = tmp_path / "excessive.parquet"
        data.write_parquet(consensus_path)

        manifest = {"output_files": {"consensus": str(consensus_path)}}

        result = validate_projection_ranges(manifest)

        # Excessive values trigger warnings, not hard failures
        assert "warnings" in result or "anomalies" in result

    def test_projection_ranges_no_consensus_file(self, tmp_path):
        """Test graceful handling when consensus file doesn't exist."""
        from src.flows.ffanalytics_pipeline import validate_projection_ranges

        manifest = {"output_files": {"consensus": str(tmp_path / "nonexistent.parquet")}}

        result = validate_projection_ranges(manifest)

        # Should skip validation gracefully
        assert result["is_valid"] is True
        assert "reason" in result
        assert "No consensus file" in result["reason"]

    def test_projection_ranges_no_stat_columns(self, tmp_path):
        """Test handling when no recognizable stat columns exist."""
        from src.flows.ffanalytics_pipeline import validate_projection_ranges

        # Create data without standard stat columns
        data = pl.DataFrame(
            {
                "player_name": ["Player 1"],
                "position": ["QB"],
                "unknown_col": [100],
            }
        )

        consensus_path = tmp_path / "no_stats.parquet"
        data.write_parquet(consensus_path)

        manifest = {"output_files": {"consensus": str(consensus_path)}}

        result = validate_projection_ranges(manifest)

        assert result["is_valid"] is True
        assert "reason" in result
        assert "No stat columns" in result["reason"]

    def test_projection_ranges_partial_stat_columns(self, tmp_path):
        """Test validation with only some stat columns present."""
        from src.flows.ffanalytics_pipeline import validate_projection_ranges

        # WR-only projections (no pass_yds, pass_tds)
        data = pl.DataFrame(
            {
                "player_name": ["WR1", "WR2"],
                "position": ["WR", "WR"],
                "rec": [100, 80],
                "rec_yds": [1300, 1100],
                "rec_tds": [8, 6],
                "fpts": [250, 210],
            }
        )

        consensus_path = tmp_path / "partial_stats.parquet"
        data.write_parquet(consensus_path)

        manifest = {"output_files": {"consensus": str(consensus_path)}}

        result = validate_projection_ranges(manifest)

        # Should validate only the columns that exist
        assert result["is_valid"] is True
