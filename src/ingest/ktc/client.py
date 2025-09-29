from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import polars as pl

from ingest.common.storage import write_parquet_any

AssetType = Literal["players", "picks"]


@dataclass
class KTCClient:
    """Authenticated/cached client for KeepTradeCut.

    This is a scaffold; wire up real HTTP calls and caching as needed.
    """

    user_agent: str = "ff-analytics/ktc"

    def fetch_players(self) -> pl.DataFrame:  # pragma: no cover - to be implemented
        """Fetch player market values.

        Replace with real implementation returning a Polars DataFrame.
        """
        raise NotImplementedError("Implement players fetch from KTC site/API")

    def fetch_picks(self) -> pl.DataFrame:  # pragma: no cover - to be implemented
        """Fetch rookie pick market values.

        Replace with real implementation returning a Polars DataFrame.
        """
        raise NotImplementedError("Implement picks fetch from KTC site/API")


def write_partitioned(df: pl.DataFrame, asset: AssetType, out_dir: str = "data/raw/ktc") -> str:
    """Write KTC asset dataframe to partitioned Parquet with dt=YYYY-MM-DD.

    Returns the destination URI used.
    """
    import uuid

    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    dest = f"{out_dir.rstrip('/')}/{asset}/dt={dt}/{asset}_{uuid.uuid4().hex[:8]}.parquet"
    write_parquet_any(df, dest)
    return dest
