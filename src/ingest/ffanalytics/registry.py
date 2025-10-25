"""FFanalytics dataset registry.

Maps logical dataset names to loader functions and metadata.
"""

DATASETS = {
    "projections": {
        "loader": "load_projections",
        "description": "Fantasy football projections with weighted consensus from multiple sources",
        "r_required": True,
        "python_available": False,  # Pure R implementation
        "output_format": "parquet",
        "incremental_key": "asof_date",
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
            f"Unknown dataset: {dataset_name}. "
            f"Available: {', '.join(DATASETS.keys())}"
        )
    return DATASETS[dataset_name]
