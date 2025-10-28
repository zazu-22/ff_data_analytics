"""FFanalytics dataset registry.

Maps logical dataset names to loader functions and metadata.

Production loaders:
    - projections_ros: Auto-detect current week + load through week 17 (recommended for automation)
    - projections_multi_week: Manual multi-week with explicit week list
    - projections: Single-week (legacy/manual use)
"""

DATASETS = {
    "projections_ros": {
        "loader": "load_projections_ros",
        "description": "Rest-of-season projections with auto-detection (weeks current->17). PRODUCTION DEFAULT for GitHub Actions.",
        "r_required": True,
        "python_available": False,
        "output_format": "parquet",
        "incremental_key": "asof_date",
        "usage": "load_projections_ros() - fully automatic, no args needed",
        "recommended": True,
    },
    "projections_multi_week": {
        "loader": "load_projections_multi_week",
        "description": "Multi-week projections with explicit week list",
        "r_required": True,
        "python_available": False,
        "output_format": "parquet",
        "incremental_key": "asof_date",
        "usage": "load_projections_multi_week(season=2025, weeks=[9,10,11])",
    },
    "projections": {
        "loader": "load_projections",
        "description": "Single-week fantasy football projections (legacy/manual use)",
        "r_required": True,
        "python_available": False,
        "output_format": "parquet",
        "incremental_key": "asof_date",
        "usage": "load_projections(season=2025, week=9)",
    }
}


def get_dataset_info(dataset_name: str) -> dict:
    """Get metadata for a dataset.

    Args:
        dataset_name: Name of dataset (e.g., 'projections')

    Returns:
        dict: Dataset metadata

    Raises:
        ValueError: If dataset not found

    """
    if dataset_name not in DATASETS:
        raise ValueError(
            f"Unknown dataset: {dataset_name}. Available: {', '.join(DATASETS.keys())}"
        )
    return DATASETS[dataset_name]
