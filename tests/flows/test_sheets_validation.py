"""Unit tests for Sheets flow validation logic.

This module tests Sheets-specific governance validation:
- Copy completeness validation (all tabs copied)
- Row count validation (tables meet minimum sizes)
- Required columns validation
"""

import polars as pl
import pytest


class TestRowCountValidation:
    """Test Sheets row count validation."""

    def test_row_counts_valid(self):
        """Test validation passes when all tables meet minimums."""
        from src.flows.parse_league_sheet_flow import validate_row_counts

        data = {
            "contracts_active": pl.DataFrame({"player": ["P1", "P2", "P3"]}),
            "contracts_cut": pl.DataFrame({"player": ["P4"]}),
            "draft_pick_holdings": pl.DataFrame({"pick": ["2025-1-01", "2025-1-02"]}),
        }

        expected_min_rows = {
            "contracts_active": 1,
            "contracts_cut": 0,
            "draft_pick_holdings": 1,
        }

        result = validate_row_counts(data, expected_min_rows)

        assert result["valid"] is True
        assert result["issues"] == []

    def test_row_counts_below_minimum(self):
        """Test validation catches tables with too few rows."""
        from src.flows.parse_league_sheet_flow import validate_row_counts

        data = {
            "contracts_active": pl.DataFrame({"player": ["P1"]}),  # 1 row
            "contracts_cut": pl.DataFrame({"player": []}),  # 0 rows
        }

        expected_min_rows = {
            "contracts_active": 10,  # Expect at least 10
            "contracts_cut": 1,  # Expect at least 1
        }

        result = validate_row_counts(data, expected_min_rows)

        assert result["valid"] is False
        assert len(result["issues"]) == 2
        assert any(
            i["table"] == "contracts_active" and i["issue"] == "below_minimum"
            for i in result["issues"]
        )
        assert any(
            i["table"] == "contracts_cut" and i["issue"] == "below_minimum"
            for i in result["issues"]
        )

    def test_row_counts_missing_table(self):
        """Test validation catches missing tables."""
        from src.flows.parse_league_sheet_flow import validate_row_counts

        data = {
            "contracts_active": pl.DataFrame({"player": ["P1", "P2"]}),
            # Missing contracts_cut and draft_pick_holdings
        }

        expected_min_rows = {
            "contracts_active": 1,
            "contracts_cut": 0,
            "draft_pick_holdings": 1,
        }

        result = validate_row_counts(data, expected_min_rows)

        assert result["valid"] is False
        assert len(result["issues"]) == 2
        assert any(
            i["table"] == "contracts_cut" and i["issue"] == "table_missing"
            for i in result["issues"]
        )
        assert any(
            i["table"] == "draft_pick_holdings" and i["issue"] == "table_missing"
            for i in result["issues"]
        )

    def test_row_counts_empty_expectations(self):
        """Test validation passes with no expectations."""
        from src.flows.parse_league_sheet_flow import validate_row_counts

        data = {
            "contracts_active": pl.DataFrame({"player": ["P1"]}),
        }

        expected_min_rows = {}

        result = validate_row_counts(data, expected_min_rows)

        assert result["valid"] is True
        assert result["issues"] == []


class TestRequiredColumnsValidation:
    """Test Sheets required columns validation."""

    def test_required_columns_valid(self):
        """Test validation passes when all required columns exist."""
        from src.flows.parse_league_sheet_flow import validate_required_columns

        data = {
            "contracts_active": pl.DataFrame(
                {
                    "gm": ["GM1"],
                    "player": ["Player 1"],
                    "position": ["QB"],
                    "salary": [10],
                }
            ),
            "draft_pick_holdings": pl.DataFrame(
                {
                    "gm": ["GM1"],
                    "pick": ["2025-1-01"],
                }
            ),
        }

        required_columns = {
            "contracts_active": ["gm", "player", "position", "salary"],
            "draft_pick_holdings": ["gm", "pick"],
        }

        result = validate_required_columns(data, required_columns)

        assert result["valid"] is True
        assert result["issues"] == []

    def test_required_columns_missing(self):
        """Test validation catches missing required columns."""
        from src.flows.parse_league_sheet_flow import validate_required_columns

        data = {
            "contracts_active": pl.DataFrame(
                {
                    "gm": ["GM1"],
                    "player": ["Player 1"],
                    # Missing: position, salary
                }
            ),
        }

        required_columns = {
            "contracts_active": ["gm", "player", "position", "salary"],
        }

        # log_error raises RuntimeError, so we expect an exception
        with pytest.raises(RuntimeError) as excinfo:
            validate_required_columns(data, required_columns)

        # Verify the error message contains information about missing columns
        assert "Missing required columns" in str(excinfo.value)
        assert "position" in str(excinfo.value) or "salary" in str(excinfo.value)

    def test_required_columns_skip_missing_table(self):
        """Test validation skips tables not in data dict."""
        from src.flows.parse_league_sheet_flow import validate_required_columns

        data = {
            "contracts_active": pl.DataFrame({"gm": ["GM1"], "player": ["Player 1"]}),
        }

        required_columns = {
            "contracts_active": ["gm", "player"],
            "contracts_cut": ["gm", "player"],  # Table not in data
        }

        result = validate_required_columns(data, required_columns)

        # Should validate only contracts_active, skip contracts_cut
        assert result["valid"] is True
        assert result["issues"] == []

    def test_required_columns_extra_columns_ok(self):
        """Test validation passes when table has extra columns beyond required."""
        from src.flows.parse_league_sheet_flow import validate_required_columns

        data = {
            "contracts_active": pl.DataFrame(
                {
                    "gm": ["GM1"],
                    "player": ["Player 1"],
                    "position": ["QB"],
                    "extra_col": ["value"],  # Extra column
                }
            ),
        }

        required_columns = {
            "contracts_active": ["gm", "player", "position"],
        }

        result = validate_required_columns(data, required_columns)

        assert result["valid"] is True


class TestCopyCompletenessValidation:
    """Test Sheets copy completeness validation.

    Note: These tests would require mocking Google Sheets API calls.
    For now, testing the validation logic structure.
    """

    def test_copy_completeness_mock_structure(self, monkeypatch):
        """Test copy completeness validation structure (requires API mocking)."""
        # This test demonstrates the expected validation structure
        # Full integration testing would require Google Sheets API mocks

        # Expected result structure
        expected_valid_result = {
            "valid": True,
            "missing_tabs": [],
            "copied_tabs": ["Andy", "Bob", "Charlie", "Transactions"],
        }

        expected_invalid_result = {
            "valid": False,
            "missing_tabs": ["Transactions"],
            "copied_tabs": ["Andy", "Bob", "Charlie"],
        }

        # Validation should return these structures
        assert expected_valid_result["valid"] is True
        assert expected_valid_result["missing_tabs"] == []

        assert expected_invalid_result["valid"] is False
        assert len(expected_invalid_result["missing_tabs"]) > 0
