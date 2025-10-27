# Task 1.2: Sleeper Production Integration

**Sprint:** Sprint 1 - FASA Optimization & Trade Intelligence
**Phase:** Phase 1 - Critical Path for Wednesday FASA
**Estimated Duration:** 8 hours
**Priority:** CRITICAL (blocks FASA target mart)

______________________________________________________________________

## Objective

Build production-grade Sleeper loader to fetch league rosters and calculate the free agent pool. This enables FASA target identification by knowing which players are available vs rostered.

______________________________________________________________________

## Context

**Why this task matters:**

- FASA bids can only be placed on free agents (not rostered players)
- Need to know which 500-800 players are available
- Sleeper API provides roster data + full NFL player database

**Current state:**

- Sample generator exists (`tools/make_samples.py`) but is dev-only
- Need production loader following `scripts/ingest/` patterns
- Sleeper API is public (no auth) with rate limits

**Dependencies:**

- ✅ `dim_player_id_xref` exists (for sleeper_id → mfl_id mapping)
- ✅ Storage helpers exist (`src/ingest/common/storage.py`)
- ⬜ Task 1.1 complete (not a hard blocker, but helpful for testing)

______________________________________________________________________

## Sleeper API Endpoints

**Base URL:** `https://api.sleeper.app/v1`

1. **Get Rosters:**

   - `GET /league/{league_id}/rosters`
   - Returns: Array of rosters with `roster_id`, `owner_id`, `players[]`, `starters[]`

1. **Get Players (ALL NFL):**

   - `GET /players/nfl`
   - Returns: Dict keyed by sleeper_player_id (~5MB JSON)
   - Contains: full_name, position, team, age, status, injury_status

1. **Get League Users:**

   - `GET /league/{league_id}/users`
   - Returns: Array of users with `user_id`, `username`, `display_name`

**Rate Limiting:**

- No official limits documented
- Best practice: 0.5-2s random delay between requests
- Implement exponential backoff on failures

______________________________________________________________________

## Files to Create

### 1. `src/ingest/sleeper/__init__.py`

```python
"""Sleeper API integration module."""
```

### 2. `src/ingest/sleeper/client.py`

```python
"""Sleeper API client following ingest patterns."""

import requests
import polars as pl
from datetime import datetime
import time
import random
from typing import Optional

BASE_URL = "https://api.sleeper.app/v1"


class SleeperClient:
    """Client for Sleeper API with rate limiting and caching."""

    def __init__(self, cache_ttl_seconds: int = 3600):
        """
        Initialize Sleeper client.

        Args:
            cache_ttl_seconds: Time-to-live for players cache (default 1 hour)
        """
        self.cache_ttl = cache_ttl_seconds
        self._players_cache: Optional[pl.DataFrame] = None
        self._players_cache_time: Optional[datetime] = None

    def get_rosters(self, league_id: str) -> pl.DataFrame:
        """
        Fetch rosters for a league.

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
        df = pl.from_dicts(data)
        return df

    def get_players(self) -> pl.DataFrame:
        """
        Fetch all NFL players (5MB file, cache locally).

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
        records = [
            {"sleeper_player_id": k, **v}
            for k, v in data.items()
        ]
        df = pl.from_dicts(records)

        # Cache
        self._players_cache = df
        self._players_cache_time = datetime.now()

        return df

    def get_league_users(self, league_id: str) -> pl.DataFrame:
        """
        Fetch league users/owners.

        Args:
            league_id: Sleeper league ID

        Returns:
            DataFrame with columns:
                - user_id, username, display_name, avatar
        """
        url = f"{BASE_URL}/league/{league_id}/users"
        response = self._get_with_retry(url)
        data = response.json()
        return pl.from_dicts(data)

    def _get_with_retry(
        self,
        url: str,
        max_retries: int = 3
    ) -> requests.Response:
        """
        HTTP GET with exponential backoff retry.

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
                wait = 2 ** attempt + random.uniform(0, 1)
                time.sleep(wait)

        raise Exception(f"Failed to fetch {url} after {max_retries} retries")
```

### 3. `scripts/ingest/load_sleeper.py`

```python
"""
Sleeper production loader.

Usage:
    python scripts/ingest/load_sleeper.py --league-id 1230330435511275520 --out data/raw/sleeper
    python scripts/ingest/load_sleeper.py --league-id $SLEEPER_LEAGUE_ID --out gs://ff-analytics/raw/sleeper

Outputs:
    - data/raw/sleeper/rosters/dt=YYYY-MM-DD/rosters.parquet
    - data/raw/sleeper/players/dt=YYYY-MM-DD/players.parquet
    - data/raw/sleeper/fa_pool/dt=YYYY-MM-DD/fa_pool.parquet
    - data/raw/sleeper/users/dt=YYYY-MM-DD/users.parquet
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import polars as pl

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ingest.sleeper.client import SleeperClient
from src.ingest.common.storage import write_parquet_with_metadata


def load_sleeper(league_id: str, out_dir: str) -> dict:
    """
    Load Sleeper data: rosters, players, FA pool.

    Args:
        league_id: Sleeper league ID
        out_dir: Output directory (local or GCS)

    Returns:
        Manifest dict with row counts and paths
    """
    client = SleeperClient()
    dt = datetime.now().strftime("%Y-%m-%d")

    manifest = {
        "loaded_at": datetime.now().isoformat(),
        "league_id": league_id,
        "datasets": {}
    }

    # 1. Load rosters
    print(f"Loading rosters for league {league_id}...")
    rosters_df = client.get_rosters(league_id)
    rosters_path = f"{out_dir}/rosters/dt={dt}/rosters.parquet"
    write_parquet_with_metadata(
        rosters_df,
        rosters_path,
        metadata={
            "source": "sleeper",
            "dataset": "rosters",
            "league_id": league_id,
            "loaded_at": datetime.now().isoformat()
        }
    )
    manifest["datasets"]["rosters"] = {
        "rows": len(rosters_df),
        "path": rosters_path
    }
    print(f"✅ Loaded {len(rosters_df)} rosters")

    # 2. Load all players
    print("Loading all NFL players...")
    players_df = client.get_players()
    players_path = f"{out_dir}/players/dt={dt}/players.parquet"
    write_parquet_with_metadata(
        players_df,
        players_path,
        metadata={
            "source": "sleeper",
            "dataset": "players",
            "note": "Full NFL player database (5MB)",
            "loaded_at": datetime.now().isoformat()
        }
    )
    manifest["datasets"]["players"] = {
        "rows": len(players_df),
        "path": players_path
    }
    print(f"✅ Loaded {len(players_df)} players")

    # 3. Calculate FA pool
    print("Calculating FA pool...")
    # Extract all rostered player IDs
    rostered_player_ids = set()
    for players_list in rosters_df["players"]:
        if players_list:
            rostered_player_ids.update(players_list)

    # FA pool = All active NFL players NOT on any roster
    fa_pool_df = players_df.filter(
        ~pl.col("sleeper_player_id").is_in(list(rostered_player_ids))
    ).filter(
        # Only active NFL players (exclude retired, practice squad if desired)
        pl.col("status").is_in(["Active", "Injured Reserve", "Questionable", "Doubtful", "Out", "PUP"])
    )

    fa_pool_path = f"{out_dir}/fa_pool/dt={dt}/fa_pool.parquet"
    write_parquet_with_metadata(
        fa_pool_df,
        fa_pool_path,
        metadata={
            "source": "sleeper",
            "dataset": "fa_pool",
            "note": "Calculated as: all_players - rostered_players",
            "rostered_count": len(rostered_player_ids),
            "fa_count": len(fa_pool_df),
            "loaded_at": datetime.now().isoformat()
        }
    )
    manifest["datasets"]["fa_pool"] = {
        "rows": len(fa_pool_df),
        "path": fa_pool_path,
        "rostered_players": len(rostered_player_ids)
    }
    print(f"✅ Calculated FA pool: {len(fa_pool_df)} players available ({len(rostered_player_ids)} rostered)")

    # 4. Load users
    print(f"Loading league users for league {league_id}...")
    users_df = client.get_league_users(league_id)
    users_path = f"{out_dir}/users/dt={dt}/users.parquet"
    write_parquet_with_metadata(
        users_df,
        users_path,
        metadata={
            "source": "sleeper",
            "dataset": "users",
            "loaded_at": datetime.now().isoformat()
        }
    )
    manifest["datasets"]["users"] = {
        "rows": len(users_df),
        "path": users_path
    }
    print(f"✅ Loaded {len(users_df)} users")

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Load Sleeper league data (rosters, players, FA pool)"
    )
    parser.add_argument(
        "--league-id",
        required=True,
        help="Sleeper league ID"
    )
    parser.add_argument(
        "--out",
        default="data/raw/sleeper",
        help="Output directory (default: data/raw/sleeper)"
    )
    args = parser.parse_args()

    print(f"Starting Sleeper data load...")
    print(f"League ID: {args.league_id}")
    print(f"Output dir: {args.out}")
    print()

    manifest = load_sleeper(args.league_id, args.out)

    print()
    print("=" * 60)
    print("Sleeper data load complete!")
    print("=" * 60)
    print(f"Datasets loaded: {len(manifest['datasets'])}")
    for dataset, info in manifest['datasets'].items():
        print(f"  - {dataset}: {info['rows']} rows → {info['path']}")


if __name__ == "__main__":
    main()
```

### 4. `dbt/ff_analytics/models/sources/src_sleeper.yml`

```yaml
version: 2

sources:
  - name: sleeper
    description: |
      Sleeper platform data loaded via production loader.

      Schedule: Daily refresh (6am/6pm EST via GitHub Actions)
      Loader: scripts/ingest/load_sleeper.py

      Future: Will migrate to BigQuery external tables pointing to GCS.

    tables:
      - name: rosters
        description: |
          Current roster ownership by team.

          Grain: roster_id (one row per team)
          Refresh: Daily

        external:
          location: "{{ env_var('EXTERNAL_ROOT', 'data/raw') }}/sleeper/rosters/dt=*/*.parquet"
          options:
            format: parquet
            hive_partitioning: true

        columns:
          - name: roster_id
            description: Sleeper roster ID (unique per team)
          - name: owner_id
            description: Sleeper user ID (owner)
          - name: players
            description: Array of sleeper_player_ids on roster
          - name: starters
            description: Array of sleeper_player_ids in starting lineup

      - name: players
        description: |
          Full NFL player database from Sleeper (~5MB).

          Grain: sleeper_player_id (one row per player)
          Refresh: Daily (cached 1hr in loader)

        external:
          location: "{{ env_var('EXTERNAL_ROOT', 'data/raw') }}/sleeper/players/dt=*/*.parquet"
          options:
            format: parquet
            hive_partitioning: true

        columns:
          - name: sleeper_player_id
            description: Sleeper player ID (primary key)
          - name: full_name
            description: Player full name
          - name: position
            description: Player position (QB, RB, WR, TE, K, DEF, etc.)
          - name: team
            description: Current NFL team
          - name: status
            description: NFL roster status (Active, Injured Reserve, etc.)

      - name: fa_pool
        description: |
          Free agent pool (calculated as all_players - rostered_players).

          Grain: sleeper_player_id (one row per FA)
          Refresh: Daily

          Calculation: Players with status Active/IR/Q/D/O and NOT on any roster.

        external:
          location: "{{ env_var('EXTERNAL_ROOT', 'data/raw') }}/sleeper/fa_pool/dt=*/*.parquet"
          options:
            format: parquet
            hive_partitioning: true

        columns:
          - name: sleeper_player_id
            description: Sleeper player ID
          - name: full_name
            description: Player full name
          - name: position
            description: Player position
          - name: team
            description: Current NFL team
          - name: status
            description: NFL roster status

      - name: users
        description: |
          League users/owners.

          Grain: user_id (one row per user)
          Refresh: Daily

        external:
          location: "{{ env_var('EXTERNAL_ROOT', 'data/raw') }}/sleeper/users/dt=*/*.parquet"
          options:
            format: parquet
            hive_partitioning: true

        columns:
          - name: user_id
            description: Sleeper user ID
          - name: username
            description: Sleeper username
          - name: display_name
            description: Display name
```

### 5. `dbt/ff_analytics/models/staging/stg_sleeper__fa_pool.sql`

```sql
-- Grain: player_key (one row per FA player)
-- Purpose: All available free agents with fantasy relevance

{{ config(
    materialized='view'
) }}

WITH fa_raw AS (
    SELECT * FROM {{ source('sleeper', 'fa_pool') }}
),

player_xref AS (
    SELECT
        player_id,
        sleeper_id,
        player_name,
        position AS xref_position
    FROM {{ ref('dim_player_id_xref') }}
)

SELECT
    -- Identity (map sleeper_id → mfl_id)
    COALESCE(xref.player_id, 'sleeper_' || fa.sleeper_player_id) AS player_key,
    xref.player_id AS mfl_id,
    fa.sleeper_player_id,

    -- Demographics
    COALESCE(xref.player_name, fa.full_name) AS player_name,
    COALESCE(xref.xref_position, fa.position) AS position,
    fa.team AS nfl_team,
    fa.age,
    fa.years_exp AS nfl_experience,

    -- Status
    fa.status AS nfl_status,
    fa.injury_status,
    fa.fantasy_positions,  -- Array of eligible positions

    -- Metadata
    CURRENT_DATE AS asof_date,
    'sleeper' AS source_platform,

    -- Mapping flag
    CASE
        WHEN xref.player_id IS NOT NULL THEN TRUE
        ELSE FALSE
    END AS is_mapped_to_mfl_id

FROM fa_raw fa
LEFT JOIN player_xref xref
    ON fa.sleeper_player_id = xref.sleeper_id

WHERE
    -- Filter to fantasy-relevant positions
    fa.position IN ('QB', 'RB', 'WR', 'TE', 'K', 'DL', 'LB', 'DB', 'DEF')
```

### 6. `dbt/ff_analytics/models/staging/stg_sleeper__fa_pool.yml`

```yaml
version: 2

models:
  - name: stg_sleeper__fa_pool
    description: |
      Free agent pool with player identity mapping.

      Grain: player_key, asof_date
      Source: Sleeper API (calculated FA pool)

      Key transformations:
      - Map sleeper_id → mfl_id via dim_player_id_xref
      - Filter to fantasy-relevant positions
      - Add player_key composite identifier

    columns:
      - name: player_key
        description: |
          Composite player identifier:
          - Mapped players: player_key = mfl_id
          - Unmapped players: player_key = 'sleeper_' + sleeper_player_id
        tests:
          - not_null
          - unique

      - name: mfl_id
        description: MFL player ID (canonical player_id, null if unmapped)
        tests:
          - relationships:
              to: ref('dim_player_id_xref')
              field: player_id
              where: "mfl_id IS NOT NULL"

      - name: sleeper_player_id
        description: Sleeper player ID (raw)
        tests:
          - not_null

      - name: player_name
        description: Player full name
        tests:
          - not_null

      - name: position
        description: Player position
        tests:
          - not_null
          - accepted_values:
              values: ['QB', 'RB', 'WR', 'TE', 'K', 'DL', 'LB', 'DB', 'DEF']

      - name: nfl_team
        description: Current NFL team

      - name: nfl_status
        description: NFL roster status
        tests:
          - accepted_values:
              values: ['Active', 'Injured Reserve', 'Questionable', 'Doubtful', 'Out', 'PUP']

      - name: is_mapped_to_mfl_id
        description: Flag indicating if player mapped to canonical mfl_id
        tests:
          - not_null
          - accepted_values:
              values: [true, false]
```

______________________________________________________________________

## Implementation Steps

1. **Create Sleeper client module:**

   - Create `src/ingest/sleeper/__init__.py`
   - Create `src/ingest/sleeper/client.py` with `SleeperClient` class

1. **Create production loader:**

   - Create `scripts/ingest/load_sleeper.py`
   - Test locally: `python scripts/ingest/load_sleeper.py --league-id $SLEEPER_LEAGUE_ID --out data/raw/sleeper`

1. **Create dbt source definition:**

   - Create `dbt/ff_analytics/models/sources/src_sleeper.yml`

1. **Create staging model:**

   - Create `dbt/ff_analytics/models/staging/stg_sleeper__fa_pool.sql`
   - Create `dbt/ff_analytics/models/staging/stg_sleeper__fa_pool.yml` with tests

1. **Run and validate:**

   ```bash
   # Load data
   uv run python scripts/ingest/load_sleeper.py \
     --league-id $SLEEPER_LEAGUE_ID \
     --out data/raw/sleeper

   # Run dbt
   export EXTERNAL_ROOT="$PWD/data/raw"
   make dbt-run --select stg_sleeper__fa_pool
   make dbt-test --select stg_sleeper__fa_pool
   ```

______________________________________________________________________

## Success Criteria

1. **Loader execution:**

   - ✅ Runs without errors
   - ✅ Creates 4 parquet files (rosters, players, fa_pool, users)
   - ✅ FA pool: 500-800 players
   - ✅ Rosters: 12 teams
   - ✅ Players: ~2000+ NFL players

1. **dbt model:**

   - ✅ `stg_sleeper__fa_pool` builds successfully
   - ✅ All tests pass (9 column tests + 1 unique test)
   - ✅ Mapping rate >95% (sleeper_id → mfl_id)

1. **Data validation:**

   - ✅ Jason's rostered players NOT in FA pool
   - ✅ Known free agents (e.g., recently cut players) ARE in FA pool
   - ✅ Position distribution reasonable (not all QBs, etc.)

1. **Code quality:**

   - ✅ `make lint` passes
   - ✅ `make typecheck` passes

______________________________________________________________________

## Validation Commands

```bash
# 1. Load Sleeper data
export SLEEPER_LEAGUE_ID="1230330435511275520"
uv run python scripts/ingest/load_sleeper.py \
  --league-id $SLEEPER_LEAGUE_ID \
  --out data/raw/sleeper

# 2. Verify output files
ls -lh data/raw/sleeper/*/dt=*/*.parquet

# 3. Inspect FA pool
uv run python -c "
import polars as pl
fa = pl.read_parquet('data/raw/sleeper/fa_pool/dt=*/fa_pool.parquet')
print(f'FA pool size: {len(fa)}')
print(f'Positions: {fa[\"position\"].value_counts().sort(\"counts\", descending=True)}')
print(f'Sample FAs:', fa.select(['full_name', 'position', 'team']).head(10))
"

# 4. Run dbt staging model
export EXTERNAL_ROOT="$PWD/data/raw"
make dbt-run --select stg_sleeper__fa_pool

# 5. Run tests
make dbt-test --select stg_sleeper__fa_pool

# 6. Check mapping rate
dbt run-operation print_query --args '{
  sql: "
    SELECT
      COUNT(*) AS total_fas,
      SUM(CASE WHEN is_mapped_to_mfl_id THEN 1 ELSE 0 END) AS mapped_count,
      ROUND(100.0 * SUM(CASE WHEN is_mapped_to_mfl_id THEN 1 ELSE 0 END) / COUNT(*), 1) AS mapping_pct
    FROM stg_sleeper__fa_pool
  "
}'

# 7. Code quality
make lint
make typecheck
```

______________________________________________________________________

## Commit Message

```
feat: add Sleeper production loader and FA pool staging

Build production-grade Sleeper loader to fetch league rosters and
calculate free agent pool. Adds:

- SleeperClient with rate limiting and caching
- load_sleeper.py production loader script
- src_sleeper.yml source definitions
- stg_sleeper__fa_pool staging model with player identity mapping

Enables FASA target identification by knowing which 500-800 players
are available for bidding.

Resolves: Sprint 1 Task 1.2
```

______________________________________________________________________

## Notes

- **Rate limiting:** Client implements 0.5-2s random delays + exponential backoff
- **Caching:** Players endpoint cached for 1 hour (doesn't change often)
- **Player mapping:** ~95% of FAs should map to mfl_id via dim_player_id_xref
- **Unmapped players:** Use fallback player_key = 'sleeper\_' + sleeper_player_id
- **Future:** Add stg_sleeper\_\_rosters and stg_sleeper\_\_players models if needed
