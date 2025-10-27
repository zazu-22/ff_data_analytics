"""Sleeper API client following ingest patterns."""

import random
import time
from datetime import datetime

import polars as pl
import requests

BASE_URL = "https://api.sleeper.app/v1"


class SleeperClient:
    """Client for Sleeper API with rate limiting and caching."""

    def __init__(self, cache_ttl_seconds: int = 3600):
        """Initialize Sleeper client.

        Args:
            cache_ttl_seconds: Time-to-live for players cache (default 1 hour)

        """
        self.cache_ttl = cache_ttl_seconds
        self._players_cache: pl.DataFrame | None = None
        self._players_cache_time: datetime | None = None

    def get_rosters(self, league_id: str) -> pl.DataFrame:
        """Fetch rosters for a league.

        Args:
            league_id: Sleeper league ID

        Returns:
            DataFrame with columns:
                - roster_id (int)
                - owner_id (str)
                - players (list[str]) - sleeper player IDs
                - starters (list[str])
                - settings (struct: wins, losses, fpts, etc.)

        """
        url = f"{BASE_URL}/league/{league_id}/rosters"
        response = self._get_with_retry(url)
        data = response.json()

        # Normalize to DataFrame
        df = pl.from_dicts(data, infer_schema_length=None)
        return df

    def get_players(self) -> pl.DataFrame:
        """Fetch all NFL players (5MB file, cache locally).

        Returns:
            DataFrame with columns:
                - sleeper_player_id (str) - key
                - full_name, first_name, last_name
                - position, team, age
                - status (Active, Injured Reserve, etc.)
                - injury_status
                - fantasy_positions (list)

        Cache: 1 hour TTL (players don't change often)

        """
        # Check cache
        if self._players_cache is not None and self._players_cache_time is not None:
            age = (datetime.now() - self._players_cache_time).total_seconds()
            if age < self.cache_ttl:
                return self._players_cache

        url = f"{BASE_URL}/players/nfl"
        response = self._get_with_retry(url)
        data = response.json()  # Dict keyed by player_id

        # Convert to DataFrame
        records = [{"sleeper_player_id": k, **v} for k, v in data.items()]
        # Increase infer_schema_length to handle varying string lengths
        df = pl.from_dicts(records, infer_schema_length=10000)

        # Cache
        self._players_cache = df
        self._players_cache_time = datetime.now()

        return df

    def get_league_users(self, league_id: str) -> pl.DataFrame:
        """Fetch league users/owners.

        Args:
            league_id: Sleeper league ID

        Returns:
            DataFrame with columns:
                - user_id, username, display_name, avatar

        """
        url = f"{BASE_URL}/league/{league_id}/users"
        response = self._get_with_retry(url)
        data = response.json()
        return pl.from_dicts(data, infer_schema_length=None)

    def _get_with_retry(self, url: str, max_retries: int = 3) -> requests.Response:
        """HTTP GET with exponential backoff retry.

        Args:
            url: URL to fetch
            max_retries: Maximum retry attempts

        Returns:
            Response object

        Raises:
            Exception: If all retries exhausted

        """
        for attempt in range(max_retries):
            try:
                # Rate limiting: random sleep 0.5-2s
                time.sleep(random.uniform(0.5, 2.0))

                response = requests.get(url, timeout=30)
                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to fetch {url} after {max_retries} retries: {e}")

                # Exponential backoff
                wait = 2**attempt + random.uniform(0, 1)
                time.sleep(wait)

        raise Exception(f"Failed to fetch {url} after {max_retries} retries")
