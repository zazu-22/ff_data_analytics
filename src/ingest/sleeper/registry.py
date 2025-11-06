"""Sleeper dataset registry.

Maps logical dataset names to loader functions.
"""

DATASETS = {
    "players": {
        "loader": "load_players",
        "description": "All NFL players from Sleeper API (used for player ID crosswalk validation)",
        "update_frequency": "weekly",
        "size_estimate": "5MB JSON -> ~2MB parquet",
    },
    "fa_pool": {
        "loader": "load_fa_pool",
        "description": "Free agent pool from Sleeper API",
        "update_frequency": "daily",
        "size_estimate": "<1MB",
    },
}
