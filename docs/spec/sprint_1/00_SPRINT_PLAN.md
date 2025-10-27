# Sprint 1: FASA Optimization & Trade Intelligence

**Created:** 2025-10-27
**Sprint Duration:** 60 hours (ends Wednesday 2025-10-29 11:59 PM EST)
**Primary Goal:** Deliver actionable FASA bidding strategy for Week 9 + trade analysis infrastructure
**Status:** 🟡 Planning Complete, Ready to Execute

______________________________________________________________________

## Executive Summary

This sprint delivers a comprehensive analytics suite to support two critical use cases:

1. **FASA Weekly Optimization** (Deadline: Wednesday 11:59 PM EST)

   - Score and rank all free agents
   - Generate position-specific bid recommendations
   - Identify drop candidates if cap space needed
   - Calculate ROI for position upgrades

1. **Trade Target Identification** (Ongoing value)

   - Identify undervalued players on other rosters (buy-low)
   - Identify overvalued players on my roster (sell-high)
   - Profile trade partners and suggest packages
   - Enable data-driven trade negotiations

**Key Innovation:** Moves from descriptive analytics (what happened) to prescriptive analytics (what should I do).

______________________________________________________________________

## Sprint Timeline & Milestones

### Phase 1: Critical Path

**Milestone:** `mart_fasa_targets` + `fasa_weekly_strategy.ipynb` functional

- ✅ Hour 0-4: Cap space foundation
- ✅ Hour 4-12: Sleeper production integration
- ✅ Hour 12-20: FASA target mart
- ✅ Hour 20-24: FASA strategy notebook

### Phase 2: Trade Intelligence

**Milestone:** `mart_trade_targets` + `trade_targets_analysis.ipynb` functional

- ✅ Hour 24-32: Baseline valuation model
- ✅ Hour 32-40: Trade analysis notebook
- ✅ Hour 40-48: Historical backfill (runs in background)

### Phase 3: Automation & Production

**Milestone:** Daily automated refreshes operational

- ✅ Hour 48-54: GitHub Actions workflows
- ✅ Hour 54-60: Documentation & polish

______________________________________________________________________

## Phase 1: Critical Path for Wednesday FASA (0-24 hours)

### Task 1.1: Cap Space Foundation (0-4 hours)

**Objective:** Parse cap space data from Commissioner Sheet roster tabs for accurate bid planning.

**Files Modified/Created:**

- `src/ingest/sheets/commissioner_parser.py` - Add `parse_cap_space()` function
- `data/raw/commissioner/cap_space/dt=YYYY-MM-DD/cap_space.parquet` (new)
- `dbt/ff_analytics/models/staging/stg_sheets__cap_space.sql` (new)
- `dbt/ff_analytics/models/core/mart_cap_situation.sql` (new)

**Technical Spec - `parse_cap_space()`:**

```python
def parse_cap_space(roster_df: pl.DataFrame, gm_name: str) -> pl.DataFrame:
    """
    Parse cap space section from roster tab (row 3).

    Input: Raw roster CSV (row 3 format):
        Available Cap Space,,$80,$80,$158,$183,$250
        Dead Cap Space,,$26,$13,$6,$0,$0
        Traded Cap Space,$7,$0,$0,$0,$0

    Output: Long-form DataFrame
        Columns: gm, season, available_cap_space, dead_cap_space, traded_cap_space
        Rows: One per (gm, season) - typically 5 rows (2025-2029)

    Logic:
        1. Locate row 3 in roster_df
        2. Extract columns _1 through _5 (years 2025-2029)
        3. Unpivot to long form
        4. Add gm column
        5. Write to data/raw/commissioner/cap_space/dt={today}/cap_space.parquet
    """
```

**dbt Model - `stg_sheets__cap_space.sql`:**

```sql
-- Grain: franchise_id, season
-- Source: data/raw/commissioner/cap_space/dt=*/cap_space.parquet

SELECT
    x.franchise_id,
    c.season,
    c.available_cap_space::int AS available_cap_space,
    c.dead_cap_space::int AS dead_cap_space,
    c.traded_cap_space::int AS traded_cap_space,
    c.available_cap_space::int + c.dead_cap_space::int AS active_contracts_implied,
    250 AS base_cap
FROM {{ source('sheets', 'cap_space') }} c
INNER JOIN {{ ref('dim_franchise') }} x
    ON c.gm = x.owner_name
    AND c.season BETWEEN x.season_start AND COALESCE(x.season_end, 9999)
```

**dbt Model - `mart_cap_situation.sql`:**

```sql
-- Grain: franchise_id, season
-- Purpose: Comprehensive cap space view with reconciliation

SELECT
    franchise_id,
    franchise_name,
    season,

    -- Base
    base_cap,

    -- Calculated (from contracts)
    active_contracts_total,
    dead_cap_calculated,

    -- Reported (from sheets)
    available_cap_space AS available_cap_space_reported,
    dead_cap_space AS dead_cap_space_reported,
    traded_cap_space,

    -- Reconciliation
    (base_cap + traded_cap_space - active_contracts_total - dead_cap_calculated) AS available_cap_calculated,
    (available_cap_space_reported - available_cap_calculated) AS reconciliation_difference,

    -- Final (use reported values per Commissioner)
    available_cap_space_reported AS cap_space_available
FROM stg_sheets__cap_space
LEFT JOIN (
    -- Aggregate active contracts per franchise/season
    SELECT franchise_id, season, SUM(cap_hit) AS active_contracts_total
    FROM stg_sheets__contracts_active
    GROUP BY franchise_id, season
) contracts USING (franchise_id, season)
LEFT JOIN (
    -- Aggregate dead cap per franchise/season
    SELECT franchise_id, season, SUM(dead_cap_amount) AS dead_cap_calculated
    FROM stg_sheets__contracts_cut
    GROUP BY franchise_id, season
) dead_cap USING (franchise_id, season)
```

**Tests:**

- Unique: `franchise_id, season`
- Not null: `franchise_id, season, cap_space_available`
- Accepted values: `season IN (2025, 2026, 2027, 2028, 2029)`
- Relationships: `franchise_id → dim_franchise.franchise_id`

**Success Criteria:**

- ✅ Jason's cap space: $80 (2025), $80 (2026), $158 (2027), $183 (2028), $250 (2029)
- ✅ All 12 franchises have cap data for 5 years
- ✅ Reconciliation differences documented (if any)

______________________________________________________________________

### Task 1.2: Sleeper Production Integration (4-12 hours)

**Objective:** Build production-grade Sleeper loader to fetch rosters and calculate FA pool.

**Files Created:**

- `scripts/ingest/load_sleeper.py` (new - main loader)
- `src/ingest/sleeper/client.py` (new - API client module)
- `src/ingest/sleeper/registry.py` (new - dataset registry)
- `dbt/ff_analytics/models/sources/src_sleeper.yml` (new)
- `dbt/ff_analytics/models/staging/stg_sleeper__rosters.sql` (new)
- `dbt/ff_analytics/models/staging/stg_sleeper__players.sql` (new)
- `dbt/ff_analytics/models/staging/stg_sleeper__fa_pool.sql` (new)

**Technical Spec - `src/ingest/sleeper/client.py`:**

```python
"""Sleeper API client following ingest patterns."""

import requests
import polars as pl
from pathlib import Path
from datetime import datetime
import time
import random

BASE_URL = "https://api.sleeper.app/v1"

class SleeperClient:
    """Client for Sleeper API with rate limiting and caching."""

    def __init__(self, cache_ttl_seconds: int = 3600):
        self.cache_ttl = cache_ttl_seconds
        self._players_cache = None
        self._players_cache_time = None

    def get_rosters(self, league_id: str) -> pl.DataFrame:
        """
        Fetch rosters for a league.

        Endpoint: GET /v1/league/{league_id}/rosters
        Returns: DataFrame with columns:
            - roster_id (int)
            - owner_id (str)
            - players (list[str]) - sleeper player IDs
            - starters (list[str])
            - settings (struct: wins, losses, fpts)
        """
        url = f"{BASE_URL}/league/{league_id}/rosters"
        response = self._get_with_retry(url)
        data = response.json()

        # Normalize to DataFrame
        df = pl.DataFrame(data)
        return df

    def get_players(self) -> pl.DataFrame:
        """
        Fetch all NFL players (5MB file, cache locally).

        Endpoint: GET /v1/players/nfl
        Returns: DataFrame with columns:
            - sleeper_player_id (str) - key
            - full_name, position, team, age, status
            - fantasy_positions (list)
            - injury_status

        Cache: 1 hour TTL (players don't change often)
        """
        # Check cache
        if self._players_cache is not None:
            age = (datetime.now() - self._players_cache_time).total_seconds()
            if age < self.cache_ttl:
                return self._players_cache

        url = f"{BASE_URL}/players/nfl"
        response = self._get_with_retry(url)
        data = response.json()  # Dict keyed by player_id

        # Convert to DataFrame
        df = pl.DataFrame([
            {"sleeper_player_id": k, **v}
            for k, v in data.items()
        ])

        # Cache
        self._players_cache = df
        self._players_cache_time = datetime.now()

        return df

    def get_league_users(self, league_id: str) -> pl.DataFrame:
        """
        Fetch league users/owners.

        Endpoint: GET /v1/league/{league_id}/users
        Returns: DataFrame with columns:
            - user_id, username, display_name, avatar
        """
        url = f"{BASE_URL}/league/{league_id}/users"
        response = self._get_with_retry(url)
        data = response.json()
        return pl.DataFrame(data)

    def _get_with_retry(self, url: str, max_retries: int = 3) -> requests.Response:
        """HTTP GET with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                # Rate limiting: random sleep 0.5-2s
                time.sleep(random.uniform(0.5, 2.0))

                response = requests.get(url, timeout=30)
                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise

                # Exponential backoff
                wait = 2 ** attempt + random.uniform(0, 1)
                time.sleep(wait)

        raise Exception(f"Failed to fetch {url} after {max_retries} retries")
```

**Technical Spec - `scripts/ingest/load_sleeper.py`:**

```python
"""
Sleeper production loader.

Usage:
    python scripts/ingest/load_sleeper.py --league-id 1230330435511275520 --out gs://ff-analytics/raw/sleeper
    python scripts/ingest/load_sleeper.py --league-id $SLEEPER_LEAGUE_ID --out data/raw/sleeper
"""

import argparse
from datetime import datetime
from pathlib import Path
import polars as pl
from src.ingest.sleeper.client import SleeperClient
from src.ingest.common.storage import write_parquet_with_metadata

def load_sleeper(league_id: str, out_dir: str) -> dict:
    """
    Load Sleeper data: rosters, players, FA pool.

    Returns: Manifest dict with row counts and paths.
    """
    client = SleeperClient()
    out_path = Path(out_dir) if not out_dir.startswith("gs://") else out_dir
    dt = datetime.now().strftime("%Y-%m-%d")

    manifest = {
        "loaded_at": datetime.now().isoformat(),
        "league_id": league_id,
        "datasets": {}
    }

    # 1. Load rosters
    rosters_df = client.get_rosters(league_id)
    rosters_path = f"{out_path}/rosters/dt={dt}/rosters.parquet"
    write_parquet_with_metadata(
        rosters_df,
        rosters_path,
        metadata={"source": "sleeper", "dataset": "rosters", "league_id": league_id}
    )
    manifest["datasets"]["rosters"] = {
        "rows": len(rosters_df),
        "path": rosters_path
    }

    # 2. Load all players
    players_df = client.get_players()
    players_path = f"{out_path}/players/dt={dt}/players.parquet"
    write_parquet_with_metadata(
        players_df,
        players_path,
        metadata={"source": "sleeper", "dataset": "players", "note": "Full NFL player database"}
    )
    manifest["datasets"]["players"] = {
        "rows": len(players_df),
        "path": players_path
    }

    # 3. Calculate FA pool
    # FA pool = All active NFL players NOT on any roster
    rostered_player_ids = set()
    for players_list in rosters_df["players"]:
        if players_list:
            rostered_player_ids.update(players_list)

    fa_pool_df = players_df.filter(
        ~pl.col("sleeper_player_id").is_in(list(rostered_player_ids))
    ).filter(
        # Only active NFL players (exclude retired, practice squad if desired)
        pl.col("status").is_in(["Active", "Injured Reserve", "Questionable", "Doubtful", "Out"])
    )

    fa_pool_path = f"{out_path}/fa_pool/dt={dt}/fa_pool.parquet"
    write_parquet_with_metadata(
        fa_pool_df,
        fa_pool_path,
        metadata={
            "source": "sleeper",
            "dataset": "fa_pool",
            "note": "Calculated as: all_players - rostered_players",
            "rostered_count": len(rostered_player_ids),
            "fa_count": len(fa_pool_df)
        }
    )
    manifest["datasets"]["fa_pool"] = {
        "rows": len(fa_pool_df),
        "path": fa_pool_path,
        "rostered_players": len(rostered_player_ids)
    }

    # 4. Load users
    users_df = client.get_league_users(league_id)
    users_path = f"{out_path}/users/dt={dt}/users.parquet"
    write_parquet_with_metadata(
        users_df,
        users_path,
        metadata={"source": "sleeper", "dataset": "users"}
    )
    manifest["datasets"]["users"] = {
        "rows": len(users_df),
        "path": users_path
    }

    return manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--league-id", required=True)
    parser.add_argument("--out", default="data/raw/sleeper")
    args = parser.parse_args()

    manifest = load_sleeper(args.league_id, args.out)
    print(f"✅ Sleeper data loaded: {manifest}")
```

**dbt Model - `stg_sleeper__fa_pool.sql`:**

```sql
-- Grain: player_key (one row per FA player)
-- Purpose: All available free agents with fantasy relevance

WITH fa_raw AS (
    SELECT * FROM {{ source('sleeper', 'fa_pool') }}
),

player_xref AS (
    SELECT * FROM {{ ref('dim_player_id_xref') }}
)

SELECT
    -- Identity (map sleeper_id → mfl_id)
    COALESCE(xref.player_id, 'sleeper_' || fa.sleeper_player_id) AS player_key,
    xref.player_id AS mfl_id,
    fa.sleeper_player_id,

    -- Demographics
    fa.full_name AS player_name,
    fa.position,
    fa.team AS nfl_team,
    fa.age,
    fa.years_exp AS nfl_experience,

    -- Status
    fa.status AS nfl_status,
    fa.injury_status,
    fa.fantasy_positions,  -- Array of eligible positions

    -- Metadata
    CURRENT_DATE AS asof_date,
    'sleeper' AS source_platform

FROM fa_raw fa
LEFT JOIN player_xref xref
    ON fa.sleeper_player_id = xref.sleeper_id

WHERE
    -- Filter to fantasy-relevant positions
    fa.position IN ('QB', 'RB', 'WR', 'TE', 'K', 'DL', 'LB', 'DB', 'DEF')
```

**Tests:**

- Unique: `player_key, asof_date`
- Not null: `player_key, player_name, position`
- Accepted values: `position IN ('QB', 'RB', 'WR', 'TE', 'K', 'DL', 'LB', 'DB', 'DEF')`
- Relationships: `mfl_id → dim_player_id_xref.player_id` (where not null)

**Success Criteria:**

- ✅ FA pool contains 500-800 players
- ✅ Jason's current roster players NOT in FA pool
- ✅ High mapping rate (>95%) sleeper_id → mfl_id
- ✅ Refreshes daily via cron

______________________________________________________________________

### Task 1.3: FASA Target Mart (12-20 hours)

**Objective:** Score and rank every free agent for FASA bidding decisions.

**Files Created:**

- `dbt/ff_analytics/models/marts/mart_fasa_targets.sql` (new)
- `dbt/ff_analytics/models/marts/mart_my_roster_droppable.sql` (new)

**Technical Spec - `mart_fasa_targets.sql`:**

```sql
-- Grain: player_key, asof_date, week
-- Purpose: Score every FA for FASA with bid recommendations

WITH fa_pool AS (
    SELECT * FROM {{ ref('stg_sleeper__fa_pool') }}
),

recent_stats AS (
    -- Aggregate recent performance from fact_player_stats
    SELECT
        player_key,

        -- Last 3 games
        AVG(CASE WHEN game_recency <= 3 THEN fantasy_points END) AS fantasy_ppg_last_3,
        AVG(CASE WHEN game_recency <= 4 THEN fantasy_points END) AS fantasy_ppg_last_4,
        AVG(CASE WHEN game_recency <= 8 THEN fantasy_points END) AS fantasy_ppg_last_8,
        AVG(fantasy_points) AS fantasy_ppg_season,

        -- Real-world volume (last 4 weeks)
        AVG(CASE WHEN game_recency <= 4 THEN attempts END) AS attempts_per_game_l4,
        AVG(CASE WHEN game_recency <= 4 THEN targets END) AS targets_per_game_l4,
        AVG(CASE WHEN game_recency <= 4 THEN snaps END) AS snaps_per_game_l4,

        -- Efficiency
        SUM(CASE WHEN stat_name = 'rushing_yards' THEN stat_value END) / NULLIF(SUM(CASE WHEN stat_name = 'carries' THEN stat_value END), 0) AS ypc,
        SUM(CASE WHEN stat_name = 'receiving_yards' THEN stat_value END) / NULLIF(SUM(CASE WHEN stat_name = 'receptions' THEN stat_value END), 0) AS ypr,
        SUM(CASE WHEN stat_name = 'receptions' THEN stat_value END) / NULLIF(SUM(CASE WHEN stat_name = 'targets' THEN stat_value END), 0) AS catch_rate

    FROM {{ ref('mart_fantasy_actuals_weekly') }}
    WHERE season = YEAR(CURRENT_DATE)
        AND week <= (SELECT MAX(week) FROM {{ ref('dim_schedule') }} WHERE game_date < CURRENT_DATE)
    QUALIFY ROW_NUMBER() OVER (PARTITION BY player_key ORDER BY week DESC) AS game_recency
    GROUP BY player_key
),

projections AS (
    -- Rest of season projections
    SELECT
        player_key,
        SUM(projected_fantasy_points) AS projected_total_ros,
        AVG(projected_fantasy_points) AS projected_ppg_ros,
        COUNT(*) AS weeks_remaining
    FROM {{ ref('mart_fantasy_projections') }}
    WHERE season = YEAR(CURRENT_DATE)
        AND week > (SELECT MAX(week) FROM {{ ref('dim_schedule') }} WHERE game_date < CURRENT_DATE)
        AND horizon = 'full_season'
    GROUP BY player_key
),

opportunity AS (
    -- Usage metrics from ff_opportunity
    SELECT
        player_key,
        AVG(CASE WHEN game_recency <= 4 THEN target_share END) AS target_share_l4,
        AVG(CASE WHEN game_recency <= 4 THEN snap_share END) AS snap_share_l4,
        AVG(CASE WHEN game_recency <= 4 THEN air_yards_share END) AS air_yards_share_l4
    FROM (
        SELECT
            player_key,
            season,
            week,
            MAX(CASE WHEN stat_name = 'target_share' THEN stat_value END) AS target_share,
            MAX(CASE WHEN stat_name = 'snap_share' THEN stat_value END) AS snap_share,
            MAX(CASE WHEN stat_name = 'air_yards_share' THEN stat_value END) AS air_yards_share,
            ROW_NUMBER() OVER (PARTITION BY player_key ORDER BY season DESC, week DESC) AS game_recency
        FROM {{ ref('fact_player_stats') }}
        WHERE stat_kind = 'actual'
            AND measure_domain = 'real_world'
            AND season = YEAR(CURRENT_DATE)
        GROUP BY player_key, season, week
    )
    WHERE game_recency <= 4
    GROUP BY player_key
),

market_values AS (
    -- KTC valuations
    SELECT
        player_key,
        value AS ktc_value,
        rank AS ktc_rank_overall,
        ROW_NUMBER() OVER (PARTITION BY position ORDER BY value DESC) AS ktc_rank_at_position,
        value - LAG(value, 4) OVER (PARTITION BY player_key ORDER BY asof_date) AS ktc_trend_4wk
    FROM {{ ref('fact_asset_market_values') }}
    WHERE asset_type = 'player'
        AND market_scope = 'dynasty_1qb'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY player_key ORDER BY asof_date DESC) = 1
),

position_baselines AS (
    -- Calculate replacement level (25th percentile at position)
    SELECT
        position,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY projected_ppg_ros) AS replacement_ppg
    FROM projections p
    INNER JOIN fa_pool fa USING (player_key)
    GROUP BY position
)

SELECT
    -- Identity
    fa.player_key,
    fa.player_name,
    fa.position,
    fa.nfl_team,
    fa.age,
    fa.nfl_experience,
    fa.injury_status,

    -- Recent Performance
    rs.fantasy_ppg_last_3,
    rs.fantasy_ppg_last_4,
    rs.fantasy_ppg_last_8,
    rs.fantasy_ppg_season,

    -- Real-World Volume
    rs.attempts_per_game_l4,
    rs.targets_per_game_l4,
    rs.snaps_per_game_l4,

    -- Efficiency
    rs.ypc,
    rs.ypr,
    rs.catch_rate,

    -- Opportunity
    opp.target_share_l4,
    opp.snap_share_l4,
    opp.air_yards_share_l4,

    -- Projections
    proj.projected_ppg_ros,
    proj.projected_total_ros,
    proj.weeks_remaining,

    -- Market
    ktc.ktc_value,
    ktc.ktc_rank_overall,
    ktc.ktc_rank_at_position,
    ktc.ktc_trend_4wk,

    -- Value Composite (0-100 score)
    (
        0.40 * (proj.projected_ppg_ros / MAX(proj.projected_ppg_ros) OVER (PARTITION BY fa.position)) +
        0.25 * (COALESCE(opp.snap_share_l4, 0) + COALESCE(opp.target_share_l4, 0)) / 2 +
        0.20 * (CASE
            WHEN rs.ypc > AVG(rs.ypc) OVER (PARTITION BY fa.position) THEN 0.5
            WHEN rs.ypr > AVG(rs.ypr) OVER (PARTITION BY fa.position) THEN 0.5
            ELSE 0.2
        END) +
        0.15 * (1 - COALESCE(ktc.ktc_rank_at_position, 999) / 100.0)
    ) * 100 AS value_score,

    -- Points above replacement
    proj.projected_ppg_ros - pb.replacement_ppg AS points_above_replacement,

    -- Breakout indicator (usage trending up + efficiency)
    CASE
        WHEN opp.snap_share_l4 > 0.5
            AND rs.fantasy_ppg_last_4 > rs.fantasy_ppg_last_8
            AND (rs.ypc > 4.5 OR rs.ypr > 10.0)
        THEN TRUE
        ELSE FALSE
    END AS breakout_indicator,

    -- Regression risk (overperforming)
    CASE
        WHEN rs.fantasy_ppg_last_4 > proj.projected_ppg_ros * 1.3
        THEN TRUE
        ELSE FALSE
    END AS regression_risk_flag,

    -- Bid Recommendations (business logic)
    CASE
        WHEN fa.position = 'RB' THEN ROUND(proj.projected_total_ros / 10, 0)  -- $1 per 10 projected points
        WHEN fa.position = 'WR' THEN ROUND(proj.projected_total_ros / 12, 0)
        WHEN fa.position = 'TE' THEN ROUND(proj.projected_total_ros / 15, 0)
        WHEN fa.position = 'QB' THEN ROUND(proj.projected_total_ros / 20, 0)
        ELSE 1
    END AS suggested_bid_1yr,

    CASE
        WHEN proj.projected_total_ros > 100 THEN ROUND(proj.projected_total_ros / 8, 0)  -- Discount for multi-year
        ELSE NULL
    END AS suggested_bid_2yr,

    -- Bid confidence
    CASE
        WHEN rs.fantasy_ppg_last_4 IS NOT NULL
            AND opp.snap_share_l4 > 0.5
            AND proj.projected_ppg_ros > pb.replacement_ppg
        THEN 'HIGH'
        WHEN proj.projected_ppg_ros > pb.replacement_ppg
        THEN 'MEDIUM'
        ELSE 'LOW'
    END AS bid_confidence,

    -- Priority ranking
    ROW_NUMBER() OVER (ORDER BY value_score DESC) AS priority_rank_overall,
    ROW_NUMBER() OVER (PARTITION BY fa.position ORDER BY value_score DESC) AS priority_rank_at_position,

    -- Metadata
    CURRENT_DATE AS asof_date,
    (SELECT MAX(week) FROM {{ ref('dim_schedule') }} WHERE game_date < CURRENT_DATE) AS current_week

FROM fa_pool fa
LEFT JOIN recent_stats rs USING (player_key)
LEFT JOIN projections proj USING (player_key)
LEFT JOIN opportunity opp USING (player_key)
LEFT JOIN market_values ktc USING (player_key)
LEFT JOIN position_baselines pb ON fa.position = pb.position

WHERE fa.position IN ('QB', 'RB', 'WR', 'TE')  -- Focus on offensive skill positions for FASA
```

**Technical Spec - `mart_my_roster_droppable.sql`:**

```sql
-- Grain: player_key, asof_date
-- Purpose: Identify drop candidates on Jason's roster

WITH my_roster AS (
    SELECT DISTINCT
        player_id AS player_key,
        position
    FROM {{ ref('stg_sheets__contracts_active') }}
    WHERE gm = 'Jason Shaffer'
        AND year = YEAR(CURRENT_DATE)
),

contracts AS (
    SELECT
        player_id AS player_key,
        COUNT(DISTINCT year) AS years_remaining,
        SUM(CASE WHEN year = YEAR(CURRENT_DATE) THEN amount END) AS current_year_cap_hit,
        SUM(CASE WHEN year > YEAR(CURRENT_DATE) THEN amount END) AS future_years_cap_hit,
        SUM(amount) AS total_remaining
    FROM {{ ref('stg_sheets__contracts_active') }}
    WHERE gm = 'Jason Shaffer'
    GROUP BY player_id
),

dead_cap AS (
    -- Calculate dead cap if cut now using dim_cut_liability_schedule
    SELECT
        c.player_key,
        SUM(
            CASE
                WHEN dl.year_index = 1 THEN c.current_year_cap_hit * 0.5
                WHEN dl.year_index = 2 AND c.years_remaining >= 2 THEN c.current_year_cap_hit * 0.5
                WHEN dl.year_index >= 3 AND c.years_remaining >= 3 THEN c.current_year_cap_hit * 0.25
                ELSE 0
            END
        ) AS dead_cap_if_cut_now
    FROM contracts c
    CROSS JOIN {{ ref('dim_cut_liability_schedule') }} dl
    WHERE dl.year_index <= c.years_remaining
    GROUP BY c.player_key
),

performance AS (
    SELECT
        player_key,
        AVG(CASE WHEN game_recency <= 8 THEN fantasy_points END) AS fantasy_ppg_last_8
    FROM (
        SELECT
            player_key,
            fantasy_points,
            ROW_NUMBER() OVER (PARTITION BY player_key ORDER BY season DESC, week DESC) AS game_recency
        FROM {{ ref('mart_fantasy_actuals_weekly') }}
        WHERE season = YEAR(CURRENT_DATE)
    )
    WHERE game_recency <= 8
    GROUP BY player_key
),

projections AS (
    SELECT
        player_key,
        AVG(projected_fantasy_points) AS projected_ppg_ros
    FROM {{ ref('mart_fantasy_projections') }}
    WHERE season = YEAR(CURRENT_DATE)
        AND week > (SELECT MAX(week) FROM {{ ref('dim_schedule') }} WHERE game_date < CURRENT_DATE)
    GROUP BY player_key
),

position_depth AS (
    -- Rank players at each position on my roster
    SELECT
        player_key,
        ROW_NUMBER() OVER (PARTITION BY position ORDER BY projected_ppg_ros DESC) AS position_depth_rank
    FROM my_roster
    LEFT JOIN projections USING (player_key)
)

SELECT
    -- Identity
    r.player_key,
    dim.player_name,
    r.position,

    -- Contract
    c.years_remaining,
    c.current_year_cap_hit,
    c.future_years_cap_hit,
    c.total_remaining,
    dc.dead_cap_if_cut_now,
    c.current_year_cap_hit - dc.dead_cap_if_cut_now AS cap_space_freed,

    -- Performance
    perf.fantasy_ppg_last_8,
    proj.projected_ppg_ros,

    -- Value Assessment
    proj.projected_ppg_ros / NULLIF(c.current_year_cap_hit, 0) AS points_per_dollar,
    proj.projected_ppg_ros - (
        SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY projected_ppg_ros)
        FROM {{ ref('mart_fasa_targets') }}
        WHERE position = r.position
    ) AS replacement_surplus,

    -- Droppable score (0-100, higher = more droppable)
    (
        CASE WHEN proj.projected_ppg_ros < 5 THEN 30 ELSE 0 END +  -- Low production
        CASE WHEN c.current_year_cap_hit > 10 THEN 30 ELSE 0 END +  -- High cap hit
        CASE WHEN dc.dead_cap_if_cut_now < 5 THEN 20 ELSE 0 END +   -- Low dead cap
        CASE WHEN pd.position_depth_rank > 3 THEN 20 ELSE 0 END     -- Roster depth
    ) AS droppable_score,

    -- Opportunity cost
    (c.current_year_cap_hit - dc.dead_cap_if_cut_now) - (proj.projected_ppg_ros / 10) AS opportunity_cost,

    -- Roster Context
    pd.position_depth_rank,
    CASE
        WHEN pd.position_depth_rank <= 2 THEN 'STARTER'
        WHEN pd.position_depth_rank = 3 THEN 'FLEX'
        ELSE 'BENCH'
    END AS roster_tier,
    c.years_remaining AS weeks_until_contract_expires,

    -- Recommendation
    CASE
        WHEN droppable_score >= 80 THEN 'DROP_FOR_CAP'
        WHEN droppable_score >= 60 AND proj.projected_ppg_ros < 8 THEN 'CONSIDER'
        WHEN droppable_score >= 40 THEN 'DROP_FOR_UPSIDE'
        ELSE 'KEEP'
    END AS drop_recommendation,

    -- Metadata
    CURRENT_DATE AS asof_date

FROM my_roster r
LEFT JOIN contracts c USING (player_key)
LEFT JOIN dead_cap dc USING (player_key)
LEFT JOIN performance perf USING (player_key)
LEFT JOIN projections proj USING (player_key)
LEFT JOIN position_depth pd USING (player_key)
LEFT JOIN {{ ref('dim_player') }} dim ON r.player_key = dim.player_id

ORDER BY droppable_score DESC
```

**Tests (mart_fasa_targets):**

- Unique: `player_key, asof_date`
- Not null: `player_key, position, value_score, priority_rank_at_position`
- Accepted values: `position IN ('QB', 'RB', 'WR', 'TE')`
- Accepted values: `bid_confidence IN ('HIGH', 'MEDIUM', 'LOW')`
- Range: `value_score BETWEEN 0 AND 100`

**Tests (mart_my_roster_droppable):**

- Unique: `player_key, asof_date`
- Not null: `player_key, position, droppable_score`
- Accepted values: `drop_recommendation IN ('KEEP', 'REVIEW', 'DROP_FOR_CAP', 'DROP_FOR_UPSIDE')`
- Range: `droppable_score BETWEEN 0 AND 100`

**Success Criteria:**

- ✅ All FAs scored (500-800 players)
- ✅ RB rankings sensible (known starters ranked higher)
- ✅ Bid recommendations reasonable ($1-50 range)
- ✅ Jason's roster: 25 active players scored for droppability

______________________________________________________________________

### Task 1.4: FASA Strategy Notebook (20-24 hours)

**Objective:** Actionable Jupyter notebook for Wednesday FASA bids.

**File Created:**

- `notebooks/fasa_weekly_strategy.ipynb` (new)

**Notebook Structure:**

````markdown
# FASA Week 9 Strategy - Due Wednesday 11:59 PM EST

## 1. My Cap Situation

**Current Cap Space:** $80 (2025)

**Future Years:**
- 2026: $80
- 2027: $158
- 2028: $183
- 2029: $250

**Cap Space Calculator:**
```python
# If I drop Player X, how much cap space do I have?

def calculate_cap_if_drop(player_name):
    player = my_roster_droppable[my_roster_droppable['player_name'] == player_name].iloc[0]
    cap_freed = player['cap_space_freed']
    new_cap_space = 80 + cap_freed
    return {
        'current_cap': 80,
        'cap_freed': cap_freed,
        'dead_cap': player['dead_cap_if_cut_now'],
        'new_cap_space': new_cap_space
    }

# Example: Drop DeAndre Hopkins
calculate_cap_if_drop('DeAndre Hopkins')
# Output: {'current_cap': 80, 'cap_freed': 3, 'dead_cap': 0, 'new_cap_space': 83}
````

## 2. Top FASA Targets by Position

### 2.1 RB Targets (Priority #1)

**Top 10 RBs Available:**

```python
rb_targets = fasa_targets[fasa_targets['position'] == 'RB'].head(10)

display(rb_targets[[
    'priority_rank_at_position',
    'player_name',
    'nfl_team',
    'fantasy_ppg_last_4',
    'projected_ppg_ros',
    'snap_share_l4',
    'value_score',
    'suggested_bid_1yr',
    'suggested_bid_2yr',
    'bid_confidence'
]])

# Scatter plot: Projected PPG vs Bid Cost
plt.scatter(rb_targets['suggested_bid_1yr'], rb_targets['projected_ppg_ros'])
plt.xlabel('Suggested Bid ($)')
plt.ylabel('Projected PPG ROS')
plt.title('RB Value Matrix')
for i, row in rb_targets.iterrows():
    plt.annotate(row['player_name'], (row['suggested_bid_1yr'], row['projected_ppg_ros']))
plt.show()
```

### 2.2 WR Targets (Priority #2)

**Top 15 WRs Available:**

[Similar table and visualization]

### 2.3 TE Targets (Priority #3)

**Top 8 TEs Available:**

[Similar table and visualization]

## 3. Bidding Strategy Matrix

**RB Strategy (Position of Need):**

| Tier | Player | Bid (1yr) | Bid (2yr) | Logic |
|------|--------|-----------|-----------|-------|
| RB1 | [Top RB from data] | $X | $Y | High value_score, snap share >60%, projected 12 PPG |
| RB2 | [2nd RB] | $X-5 | $Y-5 | Fallback if RB1 bid fails |
| RB3 | [3rd RB] | $X-10 | - | Value play if top 2 bids fail |

**WR Strategy:**

[Similar tiered approach]

**TE Strategy:**

[Similar tiered approach]

**Bidding Sequence:**

1. Start with RB1 bid at $X/2yr
1. If outbid, immediately move to RB2 at $Y/1yr
1. Monitor WR bids; jump in if tier 1 WR goes below $Z

## 4. Drop Scenarios (if cap space needed)

**Current Cap:** $80
**Needed for RB1 bid:** $15 (example)
**Gap:** -$5 (need to create cap space)

**Top Drop Candidates:**

```python
drop_candidates = my_roster_droppable[
    my_roster_droppable['cap_space_freed'] >= 5
].head(5)

display(drop_candidates[[
    'player_name',
    'position',
    'current_year_cap_hit',
    'dead_cap_if_cut_now',
    'cap_space_freed',
    'projected_ppg_ros',
    'droppable_score',
    'drop_recommendation'
]])
```

**Scenario Analysis:**

| If I drop | Cap Freed | Dead Cap | Net Benefit | Value Lost (PPG) | Worth It? |
|-----------|-----------|----------|-------------|------------------|-----------|
| Player A | $7 | $1 | $6 | 3.2 PPG | ✅ YES if RB1 projects >10 PPG |
| Player B | $5 | $0 | $5 | 5.1 PPG | ⚠️ MARGINAL - depends on RB upside |

## 5. Position Depth Analysis

**My Current RB Depth vs League Median:**

```python
my_rb_ppg = [8.2, 5.1, 3.2]  # My RB1, RB2, RB3
league_median_rb_ppg = [12.5, 8.7, 4.5]

plt.bar(['RB1', 'RB2', 'RB3'], my_rb_ppg, label='My Team', alpha=0.7)
plt.bar(['RB1', 'RB2', 'RB3'], league_median_rb_ppg, label='League Median', alpha=0.7)
plt.ylabel('PPG')
plt.title('My RB Depth vs League')
plt.legend()
plt.show()
```

**FLEX Performance Impact:**

- Current FLEX avg: 6.2 PPG (Josh Downs)
- If I add RB1 target (proj 12 PPG), new FLEX: 8.2 PPG (Jordan Mason)
- **Expected gain:** +2.0 PPG/week × 9 weeks = +18 total points

**ROI Calculation:**

- Bid cost: $15
- Expected points gained: +18 points ROS
- Cost per point: $0.83/point
- **League median cost/point:** $1.20/point
- **✅ GOOD VALUE**

## 6. Final Recommendation

**Primary Bid:**

- Target: [RB1 from data]
- Bid: $15/2yr ($7.50 AAV)
- Cap impact: Need to drop Player X to create space
- Expected impact: +2 PPG in FLEX = +18 points ROS

**Contingency Plan:**

- If outbid on RB1, immediately bid $12/1yr on RB2
- If RB market too expensive, pivot to WR1 target at $10/2yr

**Drop Decision:**

- Drop Player X (cap freed: $7, dead cap: $1, value lost: 3.2 PPG)
- Net: Upgrade FLEX by 8.8 PPG for $8 net cap cost

______________________________________________________________________

**Notebook Execution:**

```python
# Load data
import duckdb
conn = duckdb.connect('data/ff_analytics.duckdb')

fasa_targets = conn.execute("""
    SELECT * FROM mart_fasa_targets
    WHERE asof_date = CURRENT_DATE
    ORDER BY priority_rank_at_position
""").df()

my_roster_droppable = conn.execute("""
    SELECT * FROM mart_my_roster_droppable
    WHERE asof_date = CURRENT_DATE
    ORDER BY droppable_score DESC
""").df()
```

**Success Criteria:**

- ✅ Notebook runs without errors
- ✅ RB targets ranked (Top 10 displayed)
- ✅ Bid recommendations reasonable ($5-30 range for RBs)
- ✅ Drop scenarios calculated correctly
- ✅ Position depth charts visualized
- ✅ Final recommendation actionable for Wednesday bids

______________________________________________________________________

## Phase 2: Trade Intelligence (24-48 hours)

### Task 2.1: Baseline Valuation Model (24-32 hours)

**Objective:** Train regression model to predict player fair value.

**Files Created:**

- `src/ff_analytics_utils/models/player_valuation.py` (new)
- `dbt/ff_analytics/models/marts/mart_player_features_historical.sql` (new)
- `models/player_valuation_v1.pkl` (new - pickled model)

**Technical Spec - `mart_player_features_historical.sql`:**

```sql
-- Grain: player_key, season, week
-- Purpose: Feature engineering for ML models

WITH player_stats AS (
    SELECT
        player_key,
        season,
        week,

        -- Fantasy points
        SUM(fantasy_points) AS fantasy_points_week,
        AVG(SUM(fantasy_points)) OVER (
            PARTITION BY player_key
            ORDER BY season, week
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ) AS fantasy_ppg_rolling_3,
        AVG(SUM(fantasy_points)) OVER (
            PARTITION BY player_key
            ORDER BY season, week
            ROWS BETWEEN 8 PRECEDING AND CURRENT ROW
        ) AS fantasy_ppg_rolling_8,

        -- Volume
        SUM(CASE WHEN stat_name = 'carries' THEN stat_value END) AS carries,
        SUM(CASE WHEN stat_name = 'targets' THEN stat_value END) AS targets,
        SUM(CASE WHEN stat_name = 'snaps' THEN stat_value END) AS snaps,

        -- Efficiency
        SUM(CASE WHEN stat_name = 'rushing_yards' THEN stat_value END) / NULLIF(SUM(CASE WHEN stat_name = 'carries' THEN stat_value END), 0) AS ypc,
        SUM(CASE WHEN stat_name = 'receiving_yards' THEN stat_value END) / NULLIF(SUM(CASE WHEN stat_name = 'receptions' THEN stat_value END), 0) AS ypr

    FROM {{ ref('fact_player_stats') }}
    WHERE stat_kind = 'actual'
        AND measure_domain = 'real_world'
    GROUP BY player_key, season, week
),

player_info AS (
    SELECT
        player_id AS player_key,
        position,
        birthdate,
        draft_year
    FROM {{ ref('dim_player') }}
),

team_context AS (
    SELECT
        team_id,
        season,
        AVG(points_scored) AS team_offense_rank  -- Simplified
    FROM {{ ref('dim_schedule') }}
    GROUP BY team_id, season
)

SELECT
    ps.player_key,
    pi.position,
    ps.season,
    ps.week,

    -- Demographics
    YEAR(ps.season || '-01-01') - YEAR(pi.birthdate) AS age,
    YEAR(ps.season || '-01-01') - pi.draft_year AS nfl_experience,

    -- Performance
    ps.fantasy_points_week,
    ps.fantasy_ppg_rolling_3,
    ps.fantasy_ppg_rolling_8,

    -- Usage
    ps.carries,
    ps.targets,
    ps.snaps,
    ps.carries + ps.targets AS touches,

    -- Efficiency
    ps.ypc,
    ps.ypr,

    -- Team Context
    tc.team_offense_rank,

    -- Career Stats
    SUM(ps.fantasy_points_week) OVER (
        PARTITION BY ps.player_key
        ORDER BY ps.season, ps.week
    ) AS career_points_cumulative,
    COUNT(*) OVER (
        PARTITION BY ps.player_key
        ORDER BY ps.season, ps.week
    ) AS career_games_played

FROM player_stats ps
INNER JOIN player_info pi USING (player_key)
LEFT JOIN team_context tc ON ps.team_id = tc.team_id AND ps.season = tc.season
```

**Technical Spec - `src/ff_analytics_utils/models/player_valuation.py`:**

```python
"""
Player valuation regression model.

Usage:
    python -m src.ff_analytics_utils.models.player_valuation --train --save models/player_valuation_v1.pkl
    python -m src.ff_analytics_utils.models.player_valuation --predict --model models/player_valuation_v1.pkl
"""

import duckdb
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import pickle
import argparse

def load_training_data(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Load historical player features for training."""
    query = """
        SELECT
            player_key,
            position,
            age,
            nfl_experience,
            fantasy_ppg_rolling_8,
            carries,
            targets,
            snaps,
            touches,
            ypc,
            ypr,
            team_offense_rank,
            career_games_played,

            -- Target: next week fantasy points
            LEAD(fantasy_points_week) OVER (
                PARTITION BY player_key
                ORDER BY season, week
            ) AS target_next_week_points

        FROM mart_player_features_historical
        WHERE season BETWEEN 2020 AND 2024
            AND position IN ('QB', 'RB', 'WR', 'TE')
    """

    df = conn.execute(query).df()

    # Drop rows with missing target (last week of season)
    df = df.dropna(subset=['target_next_week_points'])

    return df

def train_model(df: pd.DataFrame) -> dict:
    """
    Train regression model to predict player value.

    Returns: Dict with model, scaler, metrics
    """
    # Features
    feature_cols = [
        'age', 'nfl_experience', 'fantasy_ppg_rolling_8',
        'carries', 'targets', 'snaps', 'touches',
        'ypc', 'ypr', 'team_offense_rank', 'career_games_played'
    ]

    # Position dummy variables
    position_dummies = pd.get_dummies(df['position'], prefix='pos')
    X = pd.concat([df[feature_cols], position_dummies], axis=1)

    # Target
    y = df['target_next_week_points']

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Standardize features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train models (compare Linear, Ridge, Lasso)
    models = {
        'linear': LinearRegression(),
        'ridge': Ridge(alpha=1.0),
        'lasso': Lasso(alpha=0.1)
    }

    results = {}
    for name, model in models.items():
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)

        results[name] = {
            'model': model,
            'mae': mean_absolute_error(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
            'r2': r2_score(y_test, y_pred)
        }

    # Select best model (lowest MAE)
    best_name = min(results, key=lambda k: results[k]['mae'])
    best_model = results[best_name]['model']

    print(f"Best model: {best_name}")
    print(f"MAE: {results[best_name]['mae']:.2f}")
    print(f"RMSE: {results[best_name]['rmse']:.2f}")
    print(f"R²: {results[best_name]['r2']:.3f}")

    return {
        'model': best_model,
        'scaler': scaler,
        'feature_cols': feature_cols,
        'position_dummies': list(position_dummies.columns),
        'metrics': results[best_name]
    }

def save_model(model_dict: dict, path: str):
    """Save trained model to disk."""
    with open(path, 'wb') as f:
        pickle.dump(model_dict, f)
    print(f"✅ Model saved to {path}")

def load_model(path: str) -> dict:
    """Load trained model from disk."""
    with open(path, 'rb') as f:
        return pickle.load(f)

def predict_player_values(conn: duckdb.DuckDBPyConnection, model_dict: dict) -> pd.DataFrame:
    """Predict current player values using trained model."""
    query = """
        SELECT
            player_key,
            player_name,
            position,
            age,
            nfl_experience,
            fantasy_ppg_rolling_8,
            carries,
            targets,
            snaps,
            touches,
            ypc,
            ypr,
            team_offense_rank,
            career_games_played
        FROM mart_player_features_historical
        WHERE season = YEAR(CURRENT_DATE)
            AND week = (SELECT MAX(week) FROM dim_schedule WHERE game_date < CURRENT_DATE)
            AND position IN ('QB', 'RB', 'WR', 'TE')
    """

    df = conn.execute(query).df()

    # Prepare features
    X = df[model_dict['feature_cols']]
    position_dummies = pd.get_dummies(df['position'], prefix='pos')
    X = pd.concat([X, position_dummies], axis=1)

    # Ensure all dummy columns exist
    for col in model_dict['position_dummies']:
        if col not in X.columns:
            X[col] = 0

    # Scale features
    X_scaled = model_dict['scaler'].transform(X)

    # Predict
    predictions = model_dict['model'].predict(X_scaled)

    # Add to DataFrame
    df['model_fair_value'] = predictions * 10  # Convert weekly points to season value (approx)

    return df[['player_key', 'player_name', 'position', 'model_fair_value']]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--predict", action="store_true")
    parser.add_argument("--model", default="models/player_valuation_v1.pkl")
    parser.add_argument("--save", type=str)
    args = parser.parse_args()

    conn = duckdb.connect("data/ff_analytics.duckdb")

    if args.train:
        print("Loading training data...")
        df = load_training_data(conn)
        print(f"Loaded {len(df)} training samples")

        print("Training model...")
        model_dict = train_model(df)

        if args.save:
            save_model(model_dict, args.save)

    if args.predict:
        print(f"Loading model from {args.model}...")
        model_dict = load_model(args.model)

        print("Predicting player values...")
        predictions = predict_player_values(conn, model_dict)
        print(predictions.head(20))
```

**Success Criteria:**

- ✅ Model trained on 2020-2024 data
- ✅ MAE < 5.0 points per week
- ✅ R² > 0.50
- ✅ Predictions reasonable (no negative values, sensible ranges)
- ✅ Model saved and reusable

______________________________________________________________________

### Task 2.2: Trade Target Marts (32-40 hours)

**Files Created:**

- `dbt/ff_analytics/models/marts/mart_trade_targets.sql` (new)
- `dbt/ff_analytics/models/marts/mart_my_trade_chips.sql` (new)

**Technical Specs:** (Abbreviated - see full SQL in implementation phase)

**`mart_trade_targets.sql`** - Grain: `player_key, current_franchise_id, asof_date`

- All rostered players (all 12 teams)
- Performance, projections, contracts
- Model valuation vs KTC (identify undervalued players)
- Owner context (standings, cap space, position depth)
- Trade signals (BUY_LOW / SELL_HIGH / HOLD)
- Feasibility score (needs alignment)

**`mart_my_trade_chips.sql`** - Grain: `player_key, asof_date`

- Jason's players only
- Overvalued by market (KTC > model)
- High regression risk
- Trade chip quality rating

**Success Criteria:**

- ✅ All rostered players scored (300+ players)
- ✅ Buy-low signals identify known undervalued players
- ✅ Sell-high signals identify regression candidates
- ✅ Feasibility scores reasonable

______________________________________________________________________

### Task 2.3: Trade Analysis Notebook (36-44 hours)

**File Created:**

- `notebooks/trade_targets_analysis.ipynb` (new)

**Structure:** (Abbreviated)

1. Buy-Low Candidates (filter trade_signal='BUY_LOW')
1. Sell-High Candidates (my overvalued players)
1. Trade Partner Matrix (12x12 heatmap of needs alignment)
1. Position Arbitrage (market inefficiencies)

**Success Criteria:**

- ✅ Notebook runs without errors
- ✅ Buy-low list: 10-20 candidates
- ✅ Trade partner suggestions actionable
- ✅ Visualizations clear and insightful

______________________________________________________________________

### Task 2.4: Historical Backfill (40-48 hours, runs in background)

**Objective:** Load 2012-2024 nflverse data for aging curves and historical analysis.

**Command:**

```bash
# Run in background (tmux or screen)
for year in {2012..2024}; do
    python scripts/ingest/load_nflverse.py --seasons $year --datasets weekly,snap_counts,ff_opportunity --out data/raw/nflverse
done
```

**Success Criteria:**

- ✅ 2012-2024 data loaded (13 seasons)
- ✅ fact_player_stats contains historical data
- ✅ mart_player_features_historical spans 2012-2024

______________________________________________________________________

## Phase 3: Automation & Production (48-60 hours)

### Task 3.1: GitHub Actions Workflows (48-54 hours)

**Files Created:**

- `.github/workflows/nflverse_weekly.yml` (new)
- `.github/workflows/projections_weekly.yml` (new)
- `.github/workflows/league_data_daily.yml` (new)
- `.github/workflows/backfill_historical.yml` (new)

**Technical Spec - `league_data_daily.yml`:**

```yaml
name: League Data Daily Refresh

on:
  schedule:
    # 6am and 6pm EST daily
    - cron: '0 11,23 * * *'  # UTC times (6am/6pm EST)
  workflow_dispatch:

jobs:
  refresh-league-data:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Copy Commissioner Sheet
        run: |
          uv run python scripts/ingest/copy_league_sheet.py
        env:
          GOOGLE_APPLICATION_CREDENTIALS_JSON: ${{ secrets.GOOGLE_APPLICATION_CREDENTIALS_JSON }}
          COMMISSIONER_SHEET_ID: ${{ secrets.COMMISSIONER_SHEET_ID }}
          LEAGUE_SHEET_COPY_ID: ${{ secrets.LEAGUE_SHEET_COPY_ID }}

      - name: Parse Commissioner Sheet
        run: |
          uv run python scripts/ingest/parse_commissioner_sheet.py \
            --sheet-url ${{ secrets.LEAGUE_SHEET_COPY_URL }} \
            --out data/raw/commissioner

      - name: Load Sleeper Data
        run: |
          uv run python scripts/ingest/load_sleeper.py \
            --league-id ${{ secrets.SLEEPER_LEAGUE_ID }} \
            --out data/raw/sleeper

      - name: Load KTC Market Values
        run: |
          uv run python scripts/ingest/load_ktc.py \
            --out data/raw/ktc

      - name: Run dbt
        run: |
          export EXTERNAL_ROOT="$PWD/data/raw"
          uv run dbt seed
          uv run dbt run
          uv run dbt test

      - name: Update FASA Notebook (Wednesday only)
        if: github.event.schedule == '0 11 * * 3'  # Wednesday 6am EST
        run: |
          uv run jupyter nbconvert --execute --to notebook \
            --inplace notebooks/fasa_weekly_strategy.ipynb

      - name: Discord Notification
        if: always()
        env:
          DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
        run: |
          STATUS="${{ job.status }}"
          if [ "$STATUS" = "success" ]; then
            MESSAGE="✅ League data refresh succeeded"
            COLOR="3066993"  # Green
          else
            MESSAGE="❌ League data refresh FAILED"
            COLOR="15158332"  # Red
          fi

          # Send Discord webhook
          curl -H "Content-Type: application/json" \
            -d "{\"embeds\": [{\"title\": \"$MESSAGE\", \"color\": $COLOR}]}" \
            $DISCORD_WEBHOOK
```

**Similar workflows for:**

- `nflverse_weekly.yml` - Mon 8am EST
- `projections_weekly.yml` - Tue 8am EST
- `backfill_historical.yml` - Manual trigger

**Success Criteria:**

- ✅ All 4 workflows created
- ✅ Workflows run on schedule (verify with test trigger)
- ✅ Discord notifications work
- ✅ dbt tests pass in CI

______________________________________________________________________

### Task 3.2: Documentation & Polish (54-60 hours)

**Files Created:**

- `docs/analytics/FASA_STRATEGY_GUIDE.md` (new)
- `docs/analytics/TRADE_ANALYSIS_GUIDE.md` (new)
- `docs/dev/sleeper_loader.md` (new)

**FASA Strategy Guide Contents:**

- How to interpret value_score
- Bidding frameworks (tiered approach)
- Position scarcity considerations
- Drop decision frameworks
- Contract structure strategies (1yr vs 2yr vs 3yr)

**Trade Analysis Guide Contents:**

- Buy-low identification process
- Sell-high timing windows
- Trade partner profiling
- Negotiation frameworks
- Multi-player trade packages

**Sleeper Loader Documentation:**

- API endpoints used
- FA pool calculation logic
- Refresh cadence (daily)
- Caching strategy
- Rate limiting

**Success Criteria:**

- ✅ All 3 docs written
- ✅ Docs linked from main README
- ✅ Examples included in each doc

______________________________________________________________________

## Sprint Deliverables Summary

### Immediate Use (Wednesday FASA - Hours 0-24)

- `mart_fasa_targets` - Every FA scored with bid recommendations
- `mart_my_roster_droppable` - Drop candidates ranked
- `notebooks/fasa_weekly_strategy.ipynb` - Actionable strategy
  - Top 10 RBs, 15 WRs, 8 TEs
  - Tiered bid recommendations
  - Drop scenario calculator
  - ROI projections

### Trade Intelligence (Post-FASA - Hours 24-48)

- `mart_trade_targets` - Buy-low candidates (all rosters)
- `mart_my_trade_chips` - Sell-high candidates (my roster)
- `notebooks/trade_targets_analysis.ipynb` - Trade partner finder
- Linear regression valuation model (pickled)
- Historical backfill (2012-2024)

### Infrastructure (Hours 48-60)

- Sleeper production loader (rosters + FA pool)
- Enhanced Commissioner Sheet parser (cap space)
- 4 GitHub Actions workflows (daily/weekly automation)
- Discord notifications
- Comprehensive documentation

### dbt Models

_Note:_ All dbt models must be accompanied by a corresponding yml file. Use
the `dbt/ff_analytics/models/` directory to store dbt models, and look to
good examples there for patterns and best practices.

**Staging:**

- `stg_sheets__cap_space`
- `stg_sleeper__rosters`, `stg_sleeper__players`, `stg_sleeper__fa_pool`

**Marts:**

- `mart_cap_situation`
- `mart_fasa_targets`
- `mart_my_roster_droppable`
- `mart_trade_targets`
- `mart_my_trade_chips`
- `mart_player_features_historical`

**Tests:** Comprehensive DQ tests

______________________________________________________________________

## Progress Tracking

You should update this section when you begin and complete each task.

**Legend:**

- [ ] - Task not started
- [-] - Task in progress
- [x] - Task completed
- [C] - Task cancelled (note the reason in the task description)

### Phase 1 Progress

- [ ] Task 1.1: Cap space foundation (0-4h)
  - [ ] Enhance commissioner_parser.py
  - [ ] Create stg_sheets\_\_cap_space.sql
  - [ ] Create mart_cap_situation.sql
  - [ ] Validate Jason's cap: $80 (2025)
- [ ] Task 1.2: Sleeper integration (4-12h)
  - [ ] Create src/ingest/sleeper/client.py
  - [ ] Create scripts/ingest/load_sleeper.py
  - [ ] Create stg_sleeper\_\_\*.sql (3 models)
  - [ ] Validate FA pool: 500-800 players
- [ ] Task 1.3: FASA target mart (12-20h)
  - [ ] Create mart_fasa_targets.sql
  - [ ] Create mart_my_roster_droppable.sql
  - [ ] Run and validate: All FAs scored
- [ ] Task 1.4: FASA notebook (20-24h)
  - [ ] Create fasa_weekly_strategy.ipynb
  - [ ] Validate: Notebook runs end-to-end
  - [ ] Deliverable ready for Wednesday

### Phase 2 Progress

- [ ] Task 2.1: Valuation model (24-32h)
  - [ ] Create mart_player_features_historical.sql
  - [ ] Create player_valuation.py
  - [ ] Train model: MAE < 5.0, R² > 0.50
  - [ ] Save model: player_valuation_v1.pkl
- [ ] Task 2.2: Trade marts (32-40h)
  - [ ] Create mart_trade_targets.sql
  - [ ] Create mart_my_trade_chips.sql
  - [ ] Validate: 300+ players scored
- [ ] Task 2.3: Trade notebook (36-44h)
  - [ ] Create trade_targets_analysis.ipynb
  - [ ] Validate: Notebook runs end-to-end
- [ ] Task 2.4: Backfill (40-48h, background)
  - [ ] Run backfill script (2012-2024)
  - [ ] Validate: Historical data loaded

### Phase 3 Progress

- [ ] Task 3.1: GitHub Actions (48-54h)
  - [ ] Create nflverse_weekly.yml
  - [ ] Create projections_weekly.yml
  - [ ] Create league_data_daily.yml
  - [ ] Create backfill_historical.yml
  - [ ] Test workflows with manual trigger
  - [ ] Validate Discord notifications
- [ ] Task 3.2: Documentation (54-60h)
  - [ ] Create FASA_STRATEGY_GUIDE.md
  - [ ] Create TRADE_ANALYSIS_GUIDE.md
  - [ ] Create sleeper_loader.md
  - [ ] Link from main README

______________________________________________________________________

## Success Criteria

The sprint is complete only when we've achieved all success criteria below.
If we modify sucess criteria during the sprint, we should document the change
below, noting the original criteria and the revised criteria, and the reason
for the change.

### Primary Goal: Wednesday FASA

- [ ] `fasa_weekly_strategy.ipynb` runs without errors
- [ ] Top 10 RBs identified with bid recommendations
- [ ] Top 15 WRs identified with bid recommendations
- [ ] Drop scenarios calculated (if cap space needed)
- [ ] Bid tiers defined (RB1/RB2/RB3 strategy)
- [ ] Delivered by Tuesday 11:59 PM EST (12 hours before deadline)

### Secondary Goal: Trade Analysis

- [ ] `trade_targets_analysis.ipynb` runs without errors
- [ ] Buy-low candidates identified (10-20 players)
- [ ] Sell-high candidates identified (my overvalued players)
- [ ] Trade partner matrix generated
- [ ] Model valuation vs market comparison

### Tertiary Goal: Production Infrastructure

- [ ] Daily automated data refreshes operational
- [ ] Discord notifications working
- [ ] All dbt tests passing (>95%)
- [ ] Documentation complete and linked

______________________________________________________________________

## Dependencies & Risks

### Dependencies

1. **Commissioner Sheet access** - Already working ✅
1. **Sleeper API availability** - Public API, no auth required ✅
1. **Historical nflverse data** - Available back to 2012 ✅
1. **GitHub Actions** - Already set up for sheets ✅

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| FASA notebook not ready by Wed | **HIGH** | Prioritize Phase 1 (24h buffer) |
| Sleeper API rate limiting | Medium | Implement caching + backoff |
| Model training takes longer | Low | Use simple linear regression first |
| Backfill takes >8 hours | Low | Run in background, not blocking |
| GitHub Actions fail | Low | Test locally first, fallback to manual |

______________________________________________________________________

## Post-Sprint Roadmap

The features below are not part of this sprint. They are potential future
enhancements to the project. We should refine the roadmap afer the sprint is
complete to ensure continued alignment with the project's reality and goals.

### Advanced Analytics

- [ ] Advanced ML models (Random Forest, XGBoost)
- [ ] Player clustering (K-means tiering)
- [ ] Monte Carlo simulation for trades
- [ ] Lineup optimization algorithms
- [ ] Aging curve models by position
- [ ] Multi-objective optimization (win-now vs future)

### Infrastructure

- [ ] GCS migration (Phase A from Prefect plan)
- [ ] BigQuery warehouse (Phase B/C)
- [ ] dbt sources with freshness monitoring
- [ ] Advanced data quality framework
- [ ] Ops schema (run_ledger, model_metrics)

### Analytics

- [ ] Roster composition history
- [ ] Contract optimization models
- [ ] Championship probability simulator
- [ ] Draft pick valuation curves
- [ ] Manager tendency profiling

______________________________________________________________________

## Sprint Retrospective (To be filled post-sprint)

### What Went Well

- [ ] [To be filled]

### What Could Be Improved

- [ ] [To be filled]

### Lessons Learned

- [ ] [To be filled]

### Next Sprint Priorities

- [ ] [To be filled]

______________________________________________________________________

**Document Version:** 1.0
**Last Updated:** 2025-10-27
**Sprint Status:** 🟡 Ready to Execute
**Next Review:** 2025-10-29 (Post-FASA)
