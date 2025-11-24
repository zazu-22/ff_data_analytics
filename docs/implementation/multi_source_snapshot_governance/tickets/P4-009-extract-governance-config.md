# Ticket P4-009: Extract Governance Thresholds to Configuration

**Phase**: 4 - Orchestration\
**Status**: COMPLETE\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P4-002 through P4-006\
**Priority**: 🟡 **MEDIUM - Do soon (improves maintainability)**

## Objective

Extract hardcoded governance thresholds (freshness windows, anomaly percentages, coverage minimums) to centralized configuration module for easier tuning without code changes.

## Context

Senior developer review identified that governance thresholds are hardcoded throughout flows as magic numbers, making it difficult to tune without code changes and risking inconsistency.

**Review Finding**: "Governance thresholds hardcoded throughout flows... Extract to constants or config" (see code review section 4)

## Tasks

- [x] Create `src/flows/config.py` configuration module
- [x] Extract all governance thresholds from flows
- [x] Update all flows to import from config
- [x] Document threshold rationale in config
- [x] Update flow docstrings to reference config
- [x] Update SPEC v2.3 with configuration approach

## Hardcoded Thresholds to Extract

### Freshness Thresholds (Days)

**Current locations**:

- `nfl_data_pipeline.py:358` - `max_age_days=2`

**Recommendation**:

```python
FRESHNESS_THRESHOLDS = {
    "nflverse": 2,      # NFL data should update within 2 days
    "ffanalytics": 7,   # Projections update weekly
    "ktc": 5,           # Market values update ~weekly
    "sleeper": 1,       # League data should be daily
    "sheets": 1,        # Commissioner data should be daily
}
```

### Anomaly Detection Thresholds (Percentage)

**Current locations**:

- `nfl_data_pipeline.py:400` - `threshold_pct=50.0`

**Recommendation**:

```python
ANOMALY_THRESHOLD_PCT = 50.0  # Flag if row count changes >50%
```

### Player Mapping Coverage (Percentage)

**Current locations**:

- `ktc_pipeline.py:492` - `min_coverage_pct=90.0`
- `sleeper_pipeline.py:520` - `min_coverage_pct=85.0`

**Recommendation**:

```python
PLAYER_MAPPING_THRESHOLDS = {
    "ktc": 90.0,        # KTC players are well-known, expect high coverage
    "sleeper": 85.0,    # Sleeper has many players not in NFLverse
    "ffanalytics": 92.0,  # Projections should map well
}
```

### Valuation Ranges

**Current locations**:

- `ktc_pipeline.py:155-157` - Min 0, Max 10000

**Recommendation**:

```python
VALUATION_RANGES = {
    "ktc_players": {"min": 0, "max": 10000},
    "ktc_picks": {"min": 0, "max": 10000},
}
```

### Projection Validation

**Current locations**:

- `ffanalytics_pipeline.py:512` - `std_dev_threshold=3.0`
- `ffanalytics_pipeline.py:182-188` - Reasonable maxes

**Recommendation**:

```python
STATISTICAL_THRESHOLDS = {
    "outlier_std_devs": 3.0,  # Flag projections >3 std devs from mean
}

PROJECTION_REASONABLE_MAXES = {
    "pass_yds": 6000,   # Historical max ~5500 (Peyton 2013)
    "rush_yds": 2500,   # Historical max ~2100 (Eric Dickerson 1984)
    "rec": 200,         # Historical max ~150
    "rec_yds": 2500,    # Historical max ~1900 (Calvin Johnson 2012)
    "fpts": 600,        # Historical max ~500 for season-long
}
```

### Roster Size Validation

**Current locations**:

- `sleeper_pipeline.py:455-456` - `min_roster_size=25, max_roster_size=35`

**Recommendation**:

```python
ROSTER_SIZE_RANGES = {
    "dynasty": {"min": 25, "max": 35},
    "redraft": {"min": 15, "max": 20},  # For future use
}
```

### Row Count Minimums

**Current locations**:

- `parse_league_sheet_flow.py:403-408` - Various minimums

**Recommendation**:

```python
ROW_COUNT_MINIMUMS = {
    "contracts_active": 50,     # At least 50 active contracts
    "transactions": 100,        # Expect many transactions
    "draft_picks": 20,          # Expect draft picks
    "cap_space": 10,            # At least some cap space records
}
```

## Acceptance Criteria

- [ ] Single `src/flows/config.py` module with all thresholds
- [ ] All flows import thresholds from config (zero hardcoded values)
- [ ] Config includes docstring explaining each threshold
- [ ] Thresholds grouped logically by domain (freshness, anomaly, validation)
- [ ] Type hints on all config constants
- [ ] Config is importable and testable

## Implementation Notes

### Config Module Structure

```python
# src/flows/config.py
"""Governance configuration for Prefect data pipeline flows.

This module centralizes all governance thresholds used across flows,
making it easy to tune behavior without code changes.

Threshold Rationale:
- Freshness: Based on source update frequency and criticality
- Anomaly: 50% change is significant enough to warrant investigation
- Mapping: Based on historical coverage rates for each source
- Validation: Based on NFL historical records and league rules
"""

from typing import TypedDict


class FreshnessConfig(TypedDict):
    """Freshness thresholds in days."""
    nflverse: int
    ffanalytics: int
    ktc: int
    sleeper: int
    sheets: int


class PlayerMappingConfig(TypedDict):
    """Minimum player mapping coverage percentages."""
    ktc: float
    sleeper: float
    ffanalytics: float


class ValuationRangeConfig(TypedDict):
    """Valid valuation ranges."""
    min: int
    max: int


# Freshness Validation
FRESHNESS_THRESHOLDS: FreshnessConfig = {
    "nflverse": 2,      # NFL stats should update within 2 days of games
    "ffanalytics": 7,   # Projections update weekly (Tuesday typical)
    "ktc": 5,           # Market values update multiple times per week
    "sleeper": 1,       # League data should sync daily during season
    "sheets": 1,        # Commissioner updates should be daily
}

# Anomaly Detection
ANOMALY_THRESHOLD_PCT: float = 50.0  # Flag row count changes >50%

# Player Mapping Coverage
PLAYER_MAPPING_THRESHOLDS: PlayerMappingConfig = {
    "ktc": 90.0,        # KTC dynasty players are well-known
    "sleeper": 85.0,    # Sleeper includes practice squad, recently retired
    "ffanalytics": 92.0,  # Projection sources focus on fantasy-relevant
}

# Valuation Ranges
VALUATION_RANGES: dict[str, ValuationRangeConfig] = {
    "ktc_players": {"min": 0, "max": 10000},  # KTC scale 0-10000
    "ktc_picks": {"min": 0, "max": 10000},
}

# Statistical Validation
STATISTICAL_THRESHOLDS = {
    "outlier_std_devs": 3.0,  # Standard statistical outlier threshold
}

# Projection Reasonableness (based on NFL historical records)
PROJECTION_REASONABLE_MAXES = {
    "pass_yds": 6000,   # Well above historical max ~5500
    "rush_yds": 2500,   # Well above historical max ~2100
    "rec": 200,         # Well above historical max ~150
    "rec_yds": 2500,    # Well above historical max ~1900
    "fpts": 600,        # Well above historical max ~500
}

# Roster Size Validation (dynasty league rules)
ROSTER_SIZE_RANGES = {
    "dynasty": {"min": 25, "max": 35},  # Bell Keg League roster limits
}

# Row Count Minimums (sanity checks for sheet parsing)
ROW_COUNT_MINIMUMS = {
    "contracts_active": 50,     # ~12 teams × 4+ contracts each
    "transactions": 100,        # Multi-year transaction history
    "draft_picks": 20,          # At minimum a few years of picks
    "cap_space": 10,            # At least some cap space records
}


# Convenience exports for common patterns
def get_freshness_threshold(source: str) -> int:
    """Get freshness threshold for a source.

    Args:
        source: Data source name (e.g., 'nflverse', 'ktc')

    Returns:
        Maximum age in days before snapshot is considered stale

    Raises:
        KeyError: If source not configured
    """
    return FRESHNESS_THRESHOLDS[source]


def get_player_mapping_threshold(source: str) -> float:
    """Get minimum player mapping coverage for a source.

    Args:
        source: Data source name (e.g., 'ktc', 'sleeper')

    Returns:
        Minimum coverage percentage (0-100)

    Raises:
        KeyError: If source not configured
    """
    return PLAYER_MAPPING_THRESHOLDS[source]
```

### Usage Example

```python
# Before (hardcoded)
freshness = check_snapshot_currency(
    source="nflverse",
    dataset=dataset,
    max_age_days=2,  # ❌ Magic number
)

# After (from config)
from src.flows.config import get_freshness_threshold

freshness = check_snapshot_currency(
    source="nflverse",
    dataset=dataset,
    max_age_days=get_freshness_threshold("nflverse"),  # ✅ Centralized
)
```

### Files to Modify

1. **Create**: `src/flows/config.py` (new file, ~150 lines)
2. **Update**: `src/flows/nfl_data_pipeline.py` (import config, lines 358, 400)
3. **Update**: `src/flows/ktc_pipeline.py` (import config, lines 155-157, 492)
4. **Update**: `src/flows/ffanalytics_pipeline.py` (import config, lines 182-188, 512)
5. **Update**: `src/flows/sleeper_pipeline.py` (import config, lines 455-456, 520)
6. **Update**: `src/flows/parse_league_sheet_flow.py` (import config, lines 403-415)

## Testing

```python
# tests/flows/test_config.py
def test_freshness_thresholds_defined():
    """Ensure all sources have freshness thresholds."""
    from src.flows.config import FRESHNESS_THRESHOLDS

    required_sources = ["nflverse", "ffanalytics", "ktc", "sleeper", "sheets"]
    for source in required_sources:
        assert source in FRESHNESS_THRESHOLDS
        assert FRESHNESS_THRESHOLDS[source] > 0


def test_get_freshness_threshold_raises_on_unknown():
    """Test helper raises KeyError for unknown source."""
    from src.flows.config import get_freshness_threshold
    import pytest

    with pytest.raises(KeyError):
        get_freshness_threshold("unknown_source")
```

## References

- Code Review: "Hardcoded Magic Numbers" section
- Related: P4-010 (will make refactoring easier with centralized config)

## Success Metrics

- [ ] Zero hardcoded thresholds in flow files (all in config.py)
- [ ] Config is single source of truth
- [ ] Thresholds can be tuned without touching flow logic
- [ ] Config includes rationale for each threshold
- [ ] Type hints ensure type safety

## Completion Notes

**Implemented**: 2025-11-24\
**Tests**: All flows compile successfully, imports verified\
**Thresholds Extracted**: 8 threshold categories across 5 flows

### Implementation Summary

Created centralized `src/flows/config.py` with all governance thresholds:

**Thresholds Extracted:**

1. **Freshness Thresholds** (5 sources): nflverse (2d), ffanalytics (7d), ktc (5d), sleeper/sheets (1d)
2. **Anomaly Detection**: 50% row count change threshold
3. **Player Mapping Coverage**: ktc (90%), sleeper (85%), ffanalytics (92%)
4. **Valuation Ranges**: KTC players/picks (0-10,000)
5. **Statistical Outliers**: 3.0 standard deviations
6. **Projection Maxes**: pass_yds, rush_yds, rec, rec_yds, fpts
7. **Roster Size**: Dynasty (25-35 players)
8. **Row Count Minimums**: contracts_active (50), transactions (100), draft_picks (20), cap_space (10)

**Flows Updated:**

- `nfl_data_pipeline.py`: Freshness threshold (line 381), anomaly threshold (line 423)
- `ktc_pipeline.py`: Valuation ranges (lines 156-176), player mapping threshold (line 509)
- `ffanalytics_pipeline.py`: Projection maxes (line 191), statistical thresholds (line 514)
- `sleeper_pipeline.py`: Roster size ranges (lines 502-505), player mapping threshold (line 538)
- `parse_league_sheet_flow.py`: Row count minimums (line 421)

**Type Safety:** All config constants have proper TypedDict type hints for IDE support and type checking.

**Backward Compatibility:** All changes maintain existing behavior - only refactoring thresholds to centralized location.

______________________________________________________________________

**Note**: This makes governance thresholds transparent and tunable. Operators can adjust thresholds based on production experience without modifying flow logic.
