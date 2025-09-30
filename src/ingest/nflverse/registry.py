"""ingest/nflverse/registry.py.

Dataset registry for the nflverse loader shim.
Maps logical dataset names to loader call details for both python (nflreadpy) and R (nflreadr).

Add/modify entries here as your coverage expands.
"""

from dataclasses import dataclass


@dataclass
class DatasetSpec:
    """Dataset specification for nflverse shim registry.

    Captures loader entrypoints and expected primary keys for DQ.
    """

    name: str
    py_loader: str | None  # dotted callable in nflreadpy, e.g., "nflreadpy.load_players"
    r_loader: str | None  # R function in nflreadr, e.g., "nflreadr::load_players"
    primary_keys: tuple  # expected unique keys for DQ
    notes: str = ""


# Initial registry; extend as needed
REGISTRY: dict[str, DatasetSpec] = {
    # TIER 1: Critical for Phase 1 seeds (ADR-010)
    "ff_playerids": DatasetSpec(
        name="ff_playerids",
        py_loader="nflreadpy.load_ff_playerids",
        r_loader="nflreadr::load_ff_playerids",
        primary_keys=("mfl_id",),
        notes="Fantasy platform ID crosswalk; mfl_id is canonical player_id. "
        "Contains 19 provider ID mappings (gsis_id, sleeper_id, espn_id, "
        "yahoo_id, pfr_id, ktc_id, etc.). "
        "Required for dim_player_id_xref seed generation.",
    ),
    # Existing datasets (DEPRECATED - use ff_playerids for crosswalk)
    "players": DatasetSpec(
        name="players",
        py_loader="nflreadpy.load_players",
        r_loader="nflreadr::load_players",
        primary_keys=("gsis_id",),
        notes="DEPRECATED for crosswalk: Use ff_playerids for canonical player ID mapping. "
        "This dataset lacks mfl_id and many provider IDs. "
        "Retained only for supplemental reference data (headshots, jersey numbers, etc.).",
    ),
    "weekly": DatasetSpec(
        name="weekly",
        py_loader="nflreadpy.load_player_stats",
        r_loader="nflreadr::load_player_stats",
        primary_keys=("season", "week", "player_id"),
        notes="Weekly player stats; uses summary_level='week' by default. "
        "Raw column 'player_id' contains gsis_id values; map to mfl_id via crosswalk.",
    ),
    "season": DatasetSpec(
        name="season",
        py_loader="nflreadpy.load_player_stats",
        r_loader="nflreadr::load_player_stats",
        primary_keys=("season", "gsis_id"),
        notes="Season-level player stats; needs summary_level='reg+post'.",
    ),
    "injuries": DatasetSpec(
        name="injuries",
        py_loader="nflreadpy.load_injuries",
        r_loader="nflreadr::load_injuries",
        primary_keys=("season", "week", "gsis_id", "report_date"),
        notes="Weekly injury reports.",
    ),
    "depth_charts": DatasetSpec(
        name="depth_charts",
        py_loader="nflreadpy.load_depth_charts",
        r_loader="nflreadr::load_depth_charts",
        primary_keys=("team", "position", "gsis_id", "season", "week"),
        notes="Team depth charts.",
    ),
    "schedule": DatasetSpec(
        name="schedule",
        py_loader="nflreadpy.load_schedules",
        r_loader="nflreadr::load_schedules",
        primary_keys=("season", "game_id"),
        notes="NFL schedules and results.",
    ),
    "teams": DatasetSpec(
        name="teams",
        py_loader="nflreadpy.load_teams",
        r_loader="nflreadr::load_teams",
        primary_keys=("team", "season"),
        notes="Team reference data.",
    ),
    # TIER 2: Expanded stats for fact_player_stats (ADR-009)
    "snap_counts": DatasetSpec(
        name="snap_counts",
        py_loader="nflreadpy.load_snap_counts",
        r_loader="nflreadr::load_snap_counts",
        primary_keys=("season", "week", "pfr_player_id", "team"),
        notes="Snap participation by phase (offense, defense, ST). "
        "Integrates into fact_player_stats (6 stat types). "
        "Maps to mfl_id via pfr_id in crosswalk.",
    ),
    "ff_opportunity": DatasetSpec(
        name="ff_opportunity",
        py_loader="nflreadpy.load_ff_opportunity",
        r_loader="nflreadr::load_ff_opportunity",
        primary_keys=("season", "week", "player_id", "game_id"),
        notes="Expected stats, variances, team shares (170+ columns). "
        "Integrates into fact_player_stats (~40 key stat types selected). "
        "Enables variance analysis without manual calculation. "
        "player_id field is gsis_id; maps to mfl_id via crosswalk.",
    ),
}
