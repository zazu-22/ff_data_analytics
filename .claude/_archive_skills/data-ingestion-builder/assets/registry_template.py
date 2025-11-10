"""ingest/{PROVIDER}/registry.py.

Dataset registry for the {PROVIDER} loader.
Maps logical dataset names to loader functions and metadata.
"""

from dataclasses import dataclass


@dataclass
class DatasetSpec:
    """Dataset specification for {PROVIDER} registry.

    Captures loader functions and expected primary keys for data quality validation.
    """

    name: str
    loader_function: str  # Function name in loader.py (e.g., "load_dataset_name")
    primary_keys: tuple  # Expected unique keys for DQ tests
    description: str = ""
    notes: str = ""


# Registry mapping dataset names to specifications
REGISTRY: dict[str, DatasetSpec] = {
    "{dataset_name}": DatasetSpec(
        name="{dataset_name}",
        loader_function="load_{dataset_name}",
        primary_keys=("{pk_column}",),
        description="{Brief description of what this dataset contains}",
        notes="{Any special notes about this dataset}",
    ),
    # Add more datasets as needed
}
