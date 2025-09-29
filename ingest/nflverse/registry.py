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
    "players": DatasetSpec(
        name="players",
        py_loader="nflreadpy.load_players",
        r_loader="nflreadr::load_players",
        primary_keys=("gsis_id",),
        notes="Canonical player reference including cross-IDs.",
    ),
    "weekly": DatasetSpec(
        name="weekly",
        py_loader="nflreadpy.load_player_stats",
        r_loader="nflreadr::load_player_stats",
        primary_keys=("season", "week", "gsis_id"),
        notes="Weekly player stats; uses summary_level='week' by default.",
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
}
