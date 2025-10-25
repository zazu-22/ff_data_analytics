"""FFanalytics projections integration.

Python wrapper around R-based FFanalytics scraper with weighted consensus aggregation.
"""

from .loader import load_projections

__all__ = ["load_projections"]
