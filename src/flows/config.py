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
    commissioner: int


class PlayerMappingConfig(TypedDict):
    """Minimum player mapping coverage percentages."""

    ktc: float
    sleeper: float
    ffanalytics: float


class ValuationRangeConfig(TypedDict):
    """Valid valuation ranges."""

    min: int
    max: int


class RosterSizeRangeConfig(TypedDict):
    """Valid roster size ranges."""

    min: int
    max: int


class RowCountMinimumsConfig(TypedDict):
    """Minimum row counts for sheet parsing validation."""

    contracts_active: int
    transactions: int
    draft_picks: int
    cap_space: int


class ProjectionMaxesConfig(TypedDict):
    """Reasonable maximum values for projections."""

    pass_yds: int
    rush_yds: int
    rec: int
    rec_yds: int
    fpts: int


# Freshness Validation
FRESHNESS_THRESHOLDS: FreshnessConfig = {
    "nflverse": 2,  # NFL stats should update within 2 days of games
    "ffanalytics": 7,  # Projections update weekly (Tuesday typical)
    "ktc": 5,  # Market values update multiple times per week
    "sleeper": 1,  # League data should sync daily during season
    "commissioner": 1,  # Commissioner updates should be daily
}

# Anomaly Detection
ANOMALY_THRESHOLD_PCT: float = 50.0  # Flag row count changes >50%

# Player Mapping Coverage
PLAYER_MAPPING_THRESHOLDS: PlayerMappingConfig = {
    "ktc": 90.0,  # KTC dynasty players are well-known
    "sleeper": 85.0,  # Sleeper includes practice squad, recently retired
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
PROJECTION_REASONABLE_MAXES: ProjectionMaxesConfig = {
    "pass_yds": 6000,  # Well above historical max ~5500 (Peyton Manning 2013)
    "rush_yds": 2500,  # Well above historical max ~2100 (Eric Dickerson 1984)
    "rec": 200,  # Well above historical max ~150
    "rec_yds": 2500,  # Well above historical max ~1900 (Calvin Johnson 2012)
    "fpts": 600,  # Well above historical max ~500
}

# Roster Size Validation (dynasty league rules)
ROSTER_SIZE_RANGES: dict[str, RosterSizeRangeConfig] = {
    "dynasty": {"min": 25, "max": 35},  # Bell Keg League roster limits
}

# Row Count Minimums (sanity checks for sheet parsing)
ROW_COUNT_MINIMUMS: RowCountMinimumsConfig = {
    "contracts_active": 50,  # ~12 teams × 4+ contracts each
    "transactions": 100,  # Multi-year transaction history
    "draft_picks": 20,  # At minimum a few years of picks
    "cap_space": 10,  # At least some cap space records
}

# Source Freshness Validation (hours)
SOURCE_FRESHNESS_THRESHOLDS = {
    "commissioner": 24,  # Warn if working copy > 24 hours old
    "nflverse": 48,  # Warn if NFLverse fetch > 48 hours old
    "sleeper": 24,  # Warn if Sleeper fetch > 24 hours old
    "ktc": 120,  # Warn if KTC fetch > 5 days old (120 hours)
    "ffanalytics": 168,  # Warn if projections > 7 days old (168 hours)
}

# Skip-if-unchanged configuration (per source)
SKIP_IF_UNCHANGED_ENABLED = {
    "commissioner": True,  # Always skip if source sheet unchanged
    "nflverse": False,  # Always fetch (data changes frequently during season)
    "sleeper": False,  # Always fetch (league activity)
    "ktc": True,  # Skip if KTC data unchanged
    "ffanalytics": False,  # Always scrape (projections change weekly)
}

# Checksum validation configuration
CHECKSUM_VALIDATION = {
    "commissioner_copy": {"rows": 50, "cols": 50, "enabled": True},
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
