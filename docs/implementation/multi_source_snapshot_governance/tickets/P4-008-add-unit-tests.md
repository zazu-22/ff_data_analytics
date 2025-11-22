# Ticket P4-008: Add Unit Tests for Flow Validation Logic

**Phase**: 4 - Orchestration\
**Status**: TODO\
**Estimated Effort**: Medium (3-4 hours)\
**Dependencies**: P4-002 through P4-006 (all flows complete)\
**Priority**: 🟡 **HIGH - Do soon (before major refactoring)**

## Objective

Add unit tests for critical flow validation logic, focusing on snapshot registry updates, governance checks, and data validation tasks to prevent regressions.

## Context

Senior developer review identified zero automated tests for Phase 4 flows despite `tests/` directory existing and flows containing critical data integrity logic (snapshot registry updates, governance validation).

**Review Finding**: "No test files for any P4 flows... No regression protection, Manual testing only, Refactoring risk" (see code review section 2)

## Tasks

### High Priority - Registry Update Logic (All Flows)

- [ ] Test atomic snapshot registry updates:

  - [ ] New snapshot marks old as 'superseded'
  - [ ] Re-running with same date is idempotent
  - [ ] Coverage metadata extracted correctly
  - [ ] Row counts populated from manifests

- [ ] Test edge cases:

  - [ ] First snapshot for new source/dataset
  - [ ] Multiple snapshots on same date
  - [ ] Missing row_count in manifest (graceful handling)

### Medium Priority - Validation Tasks

- [ ] Test governance validation logic:

  - [ ] **KTC**: Player mapping coverage calculation
  - [ ] **KTC**: Valuation range checks (0-10000)
  - [ ] **FFAnalytics**: Projection reasonableness (no negatives)
  - [ ] **FFAnalytics**: Statistical outlier detection (>3 std devs)
  - [ ] **Sleeper**: Roster size validation (25-35 players)
  - [ ] **Sheets**: Copy completeness validation
  - [ ] **Sheets**: Row count validation

- [ ] Test validation result structures:

  - [ ] Warning vs error conditions
  - [ ] Actionable error messages
  - [ ] Context dictionaries complete

### Low Priority - Metadata Extraction

- [ ] Test row count extraction from manifests:

  - [ ] Both manifest formats (top-level, nested)
  - [ ] Missing parquet_file field

- [ ] Test coverage metadata extraction:

  - [ ] Season ranges from NFLverse data
  - [ ] Week ranges from FFAnalytics data

## Acceptance Criteria

- [ ] At least 80% code coverage for registry update logic (critical path)
- [ ] All governance validation functions have unit tests
- [ ] Tests use fixtures/mocks (no actual API calls or file I/O)
- [ ] Tests run in \<5 seconds total
- [ ] CI integration ready (tests run on every PR)
- [ ] Clear test documentation with examples

## Implementation Notes

### Test Structure

```
tests/
├── flows/
│   ├── __init__.py
│   ├── conftest.py                    # Shared fixtures
│   ├── test_registry_updates.py       # HIGH PRIORITY
│   ├── test_ktc_validation.py         # MEDIUM
│   ├── test_ffanalytics_validation.py # MEDIUM
│   ├── test_sleeper_validation.py     # MEDIUM
│   └── test_sheets_validation.py      # MEDIUM
└── fixtures/
    ├── sample_manifests.py
    └── sample_registry.csv
```

### Example Test - Registry Updates

```python
# tests/flows/test_registry_updates.py
import polars as pl
import pytest
from pathlib import Path
from src.flows.nfl_data_pipeline import update_snapshot_registry


@pytest.fixture
def mock_registry(tmp_path):
    """Create temporary registry with existing snapshot."""
    registry_data = pl.DataFrame([
        {
            "source": "nflverse",
            "dataset": "weekly",
            "snapshot_date": "2024-01-01",
            "status": "current",
            "row_count": 10000,
            "notes": "Initial snapshot"
        }
    ])

    registry_path = tmp_path / "snapshot_registry.csv"
    registry_data.write_csv(registry_path)
    return registry_path


def test_update_registry_marks_old_as_superseded(mock_registry, monkeypatch):
    """Test that new snapshot supersedes old one."""
    # Mock the registry path
    monkeypatch.setattr(
        "src.flows.nfl_data_pipeline.Path",
        lambda x: mock_registry.parent / x
    )

    # Update with new snapshot
    result = update_snapshot_registry(
        source="nflverse",
        dataset="weekly",
        snapshot_date="2024-01-02",
        row_count=12000,
        coverage_start_season=2024,
        coverage_end_season=2024
    )

    # Read updated registry
    registry = pl.read_csv(mock_registry)

    # Assertions
    assert result["success"] is True
    assert len(registry) == 2  # Old + new

    # Old snapshot should be superseded
    old = registry.filter(pl.col("snapshot_date") == "2024-01-01")
    assert old["status"][0] == "superseded"

    # New snapshot should be current
    new = registry.filter(pl.col("snapshot_date") == "2024-01-02")
    assert new["status"][0] == "current"
    assert new["row_count"][0] == 12000


def test_update_registry_idempotent(mock_registry, monkeypatch):
    """Test running update twice with same date is safe."""
    # First update
    update_snapshot_registry(...)

    # Second update (same date)
    update_snapshot_registry(...)

    # Should have only 2 rows (old + new), not 3
    registry = pl.read_csv(mock_registry)
    assert len(registry) == 2
```

### Example Test - Validation

```python
# tests/flows/test_ktc_validation.py
import polars as pl
import pytest
from src.flows.ktc_pipeline import validate_valuation_ranges


@pytest.fixture
def ktc_manifest_valid(tmp_path):
    """Create KTC manifest with valid valuations."""
    data = pl.DataFrame({
        "player_name": ["Player A", "Player B"],
        "value": [5000, 8000]
    })

    path = tmp_path / "ktc_players.parquet"
    data.write_parquet(path)

    return {"output_path": str(path)}


def test_valuation_ranges_valid_data(ktc_manifest_valid):
    """Test validation passes with valid valuations."""
    result = validate_valuation_ranges(ktc_manifest_valid, "players")

    assert result["is_valid"] is True
    assert result["anomalies"] == []
    assert result["min_value"] == 5000
    assert result["max_value"] == 8000


def test_valuation_ranges_negative_values(tmp_path):
    """Test validation catches negative values."""
    data = pl.DataFrame({
        "player_name": ["Player C"],
        "value": [-100]  # Invalid
    })

    path = tmp_path / "ktc_invalid.parquet"
    data.write_parquet(path)
    manifest = {"output_path": str(path)}

    result = validate_valuation_ranges(manifest, "players")

    assert result["is_valid"] is False
    assert "Negative values" in result["anomalies"][0]
    assert result["outlier_count"] == 1
```

### Running Tests

```bash
# Run all flow tests
pytest tests/flows/ -v

# Run with coverage
pytest tests/flows/ --cov=src/flows --cov-report=html

# Run specific test file
pytest tests/flows/test_registry_updates.py -v

# Run specific test
pytest tests/flows/test_ktc_validation.py::test_valuation_ranges_valid_data -v
```

## Testing Strategy

### Priority 1: Registry Updates

- **Why**: Critical data integrity - bugs here corrupt historical tracking
- **Coverage target**: 90%+
- **Files**: All flows (5 files have duplicate registry logic)

### Priority 2: Governance Validation

- **Why**: Business logic - ensures data quality before ingestion
- **Coverage target**: 80%+
- **Files**: All validation tasks in all flows

### Priority 3: Metadata Extraction

- **Why**: Helps debugging, not critical to correctness
- **Coverage target**: 60%+
- **Files**: Coverage extraction, row count extraction tasks

## References

- Code Review: "Missing Automated Tests" section
- Pytest Docs: https://docs.pytest.org/
- Polars Testing: Mock DataFrames with fixtures
- Prefect Testing: https://docs.prefect.io/latest/guides/testing/

## Success Metrics

- [ ] Registry update logic has 90%+ coverage
- [ ] Governance validation has 80%+ coverage
- [ ] Zero regressions after refactoring (P4-010)
- [ ] Tests run in CI on every PR
- [ ] Test failures provide clear, actionable errors

## Completion Notes

**Implementation Date**: TBD\
**Coverage Achieved**: TBD\
**Tests Added**: TBD

______________________________________________________________________

**Note**: This ticket should be completed **before** P4-010 (refactoring) to ensure we have regression protection when consolidating duplicate code.
