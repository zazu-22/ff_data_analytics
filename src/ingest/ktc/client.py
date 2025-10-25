from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import polars as pl
import requests

from ingest.common.storage import write_parquet_any

AssetType = Literal["players", "picks"]
MarketScope = Literal["dynasty_1qb", "dynasty_superflex"]


@dataclass
class KTCClient:
    """Respectful scraper for KeepTradeCut dynasty rankings.

    KTC embeds player/pick data in HTML as a JavaScript variable.
    This client extracts and normalizes that data with polite rate limiting.

    Attribution: Data sourced from KeepTradeCut (https://keeptradecut.com)
    per their content usage guidelines.
    """

    user_agent: str = "ff-analytics/ktc (personal dynasty analytics)"
    cache_dir: Path | None = None
    cache_ttl_seconds: int = 3600  # 1 hour cache by default
    min_delay_seconds: float = 2.0  # minimum delay between requests
    max_delay_seconds: float = 5.0  # maximum delay between requests
    market_scope: MarketScope = "dynasty_1qb"  # default to 1QB as per spec

    _last_request_time: float = field(default=0.0, init=False, repr=False)

    def _polite_delay(self) -> None:
        """Randomized delay to be respectful to KTC servers."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_delay_seconds:
            delay = random.uniform(self.min_delay_seconds, self.max_delay_seconds)  # noqa: S311
            time.sleep(delay)
        self._last_request_time = time.time()

    def _get_cache_path(self, cache_key: str) -> Path | None:
        """Get cache file path for a given key."""
        if self.cache_dir is None:
            return None
        cache_path = Path(self.cache_dir) / f"{cache_key}.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        return cache_path

    def _load_from_cache(self, cache_key: str) -> list[dict] | None:
        """Load data from cache if fresh enough."""
        cache_path = self._get_cache_path(cache_key)
        if cache_path is None or not cache_path.exists():
            return None

        # Check cache freshness
        cache_age = time.time() - cache_path.stat().st_mtime
        if cache_age > self.cache_ttl_seconds:
            return None

        with cache_path.open("r") as f:
            return json.load(f)

    def _save_to_cache(self, cache_key: str, data: list[dict]) -> None:
        """Save data to cache."""
        cache_path = self._get_cache_path(cache_key)
        if cache_path is None:
            return

        with cache_path.open("w") as f:
            json.dump(data, f)

    def _fetch_rankings_html(self) -> str:
        """Fetch the dynasty rankings page HTML."""
        url = "https://keeptradecut.com/dynasty-rankings"
        self._polite_delay()

        headers = {"User-Agent": self.user_agent}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text

    def _extract_players_array(self, html: str) -> list[dict]:
        """Extract the playersArray JavaScript variable from HTML."""
        # Look for: var playersArray = [...]
        pattern = r"var\s+playersArray\s*=\s*(\[.*?\]);"
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            raise ValueError("Could not find playersArray in KTC HTML")

        players_json = match.group(1)
        return json.loads(players_json)

    def fetch_all_rankings(self) -> list[dict]:
        """Fetch all rankings (players + picks) from KTC.

        Returns raw KTC data structure with all fields.
        Checks cache first to avoid unnecessary requests.
        """
        cache_key = f"ktc_rankings_{datetime.now(UTC).strftime('%Y-%m-%d')}"

        # Try cache first
        cached_data = self._load_from_cache(cache_key)
        if cached_data is not None:
            return cached_data

        # Fetch from web
        html = self._fetch_rankings_html()
        rankings = self._extract_players_array(html)

        # Save to cache
        self._save_to_cache(cache_key, rankings)

        return rankings

    def fetch_players(self) -> pl.DataFrame:
        """Fetch player market values in normalized long-form format.

        Returns:
            DataFrame with columns:
            - player_name: str
            - position: str
            - team: str
            - asset_type: "player"
            - rank: int (overall rank in selected format)
            - value: int (KTC value in selected format)
            - positional_rank: int
            - market_scope: str (e.g., "dynasty_1qb")
            - asof_date: date

        """
        rankings = self.fetch_all_rankings()

        # Filter to only players (not picks)
        # Picks have playerName like "2025 Early 1st", "2026 Mid 2nd", etc.
        pick_pattern = re.compile(r"^\d{4}\s+(Early|Mid|Late)\s+\d+(st|nd|rd|th)$")
        players = [r for r in rankings if not pick_pattern.match(r.get("playerName", ""))]

        # Extract relevant fields based on market scope
        value_field = "oneQBValues" if self.market_scope == "dynasty_1qb" else "superflexValues"

        rows = []
        for p in players:
            values = p.get(value_field, {})
            if not values or values.get("value") is None:
                continue  # skip players with no value in this format

            rows.append(
                {
                    "player_name": p.get("playerName"),
                    "position": p.get("position"),
                    "team": p.get("team"),
                    "asset_type": "player",
                    "rank": values.get("rank"),
                    "value": values.get("value"),
                    "positional_rank": values.get("positionalRank"),
                    "market_scope": self.market_scope,
                    "asof_date": datetime.now(UTC).date(),
                }
            )

        return pl.DataFrame(rows)

    def fetch_picks(self) -> pl.DataFrame:
        """Fetch rookie pick market values in normalized long-form format.

        Returns:
            DataFrame with columns:
            - pick_name: str (e.g., "2025 Early 1st")
            - draft_year: int
            - pick_tier: str (Early/Mid/Late)
            - pick_round: int
            - asset_type: "pick"
            - rank: int (overall rank in selected format)
            - value: int (KTC value in selected format)
            - market_scope: str (e.g., "dynasty_1qb")
            - asof_date: date

        """
        rankings = self.fetch_all_rankings()

        # Filter to only picks
        pick_pattern = re.compile(r"^(\d{4})\s+(Early|Mid|Late)\s+(\d+)(st|nd|rd|th)$")
        picks = []
        for r in rankings:
            name = r.get("playerName", "")
            match = pick_pattern.match(name)
            if match:
                picks.append((r, match))

        # Extract relevant fields based on market scope
        value_field = "oneQBValues" if self.market_scope == "dynasty_1qb" else "superflexValues"

        rows = []
        for p, match in picks:
            values = p.get(value_field, {})
            if not values or values.get("value") is None:
                continue  # skip picks with no value in this format

            draft_year = int(match.group(1))
            pick_tier = match.group(2)
            pick_round = int(match.group(3))

            rows.append(
                {
                    "pick_name": p.get("playerName"),
                    "draft_year": draft_year,
                    "pick_tier": pick_tier,
                    "pick_round": pick_round,
                    "asset_type": "pick",
                    "rank": values.get("rank"),
                    "value": values.get("value"),
                    "market_scope": self.market_scope,
                    "asof_date": datetime.now(UTC).date(),
                }
            )

        return pl.DataFrame(rows)


def write_partitioned(df: pl.DataFrame, asset: AssetType, out_dir: str = "data/raw/ktc") -> str:
    """Write KTC asset dataframe to partitioned Parquet with dt=YYYY-MM-DD.

    Returns the destination URI used.
    """
    import uuid

    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    dest = f"{out_dir.rstrip('/')}/{asset}/dt={dt}/{asset}_{uuid.uuid4().hex[:8]}.parquet"
    write_parquet_any(df, dest)
    return dest
