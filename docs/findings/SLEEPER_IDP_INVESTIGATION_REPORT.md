# Sleeper API IDP Capabilities Investigation Report

**Date:** October 29, 2025
**Investigator:** Claude Code
**Objective:** Test and document Sleeper API's actual IDP projection capabilities

______________________________________________________________________

## Executive Summary

### VERDICT: ❌ NOT VIABLE for IDP Projections

**Key Findings:**

- ✅ Sleeper API provides **actual IDP statistics** (historical results)
- ❌ Sleeper API does **NOT** provide IDP projections (future predictions)
- ✅ Historical stats data quality is GOOD
- ❌ Projection endpoints return empty data

______________________________________________________________________

## API Endpoints Tested

### 1. Working Endpoints

#### Stats Endpoint (Historical Data)

```
GET /v1/stats/nfl/regular/{season}/{week}
Example: https://api.sleeper.app/v1/stats/nfl/regular/2024/1
```

**Status:** ✅ Working
**Returns:** Actual game statistics for completed games
**Coverage:** 974+ defensive players per week

#### Player Metadata

```
GET /v1/players/nfl
Example: https://api.sleeper.app/v1/players/nfl
```

**Status:** ✅ Working
**Returns:** 11,400+ NFL players with position, team, status data

### 2. Non-Working/Empty Endpoints

#### Projection Endpoints

```
GET /v1/projections/nfl/{season}        → 404 Not Found
GET /v1/projections/nfl/{season}/{week} → Returns empty arrays
GET /projections/nfl/{season}           → 400 Bad Request
```

**Status:** ❌ Not usable for IDP
**Issue:** Returns 6,957 records but all are empty arrays `[]`

______________________________________________________________________

## IDP Data Fields Available

### Stats Endpoint Fields (67 defensive fields found)

**Core IDP Stats:**

- `idp_tkl` - Total tackles
- `idp_tkl_solo` - Solo tackles
- `idp_tkl_ast` - Assisted tackles
- `idp_tkl_loss` - Tackles for loss
- `idp_sack` - Sacks
- `idp_sack_yd` - Sack yardage
- `idp_qb_hit` - QB hits
- `idp_int` - Interceptions
- `idp_int_ret_yd` - Interception return yards
- `idp_pass_def` - Passes defended
- `idp_ff` - Forced fumbles
- `idp_fum_rec` - Fumble recoveries
- `idp_safe` - Safeties
- `idp_blk_kick` - Blocked kicks
- `idp_def_td` - Defensive touchdowns

**Additional Fields:**

- `pts_idp` - IDP fantasy points
- `def_snp` - Defensive snaps
- `tm_def_snp` - Team defensive snaps
- `bonus_tkl_10p` - 10+ tackle bonus
- `bonus_sack_2p` - 2+ sack bonus

______________________________________________________________________

## Data Quality Assessment

### Coverage Analysis (Week 1 2024)

| Metric                 | Count | Percentage |
| ---------------------- | ----- | ---------- |
| Total players in stats | 2,310 | -          |
| Defensive players      | 974   | 42.2%      |
| - DE                   | 130   | 13.3%      |
| - DT                   | 128   | 13.1%      |
| - LB                   | 285   | 29.3%      |
| - CB                   | 148   | 15.2%      |
| - DB                   | 283   | 29.1%      |

### Data Completeness (50-player sample)

| Stat Type     | Players with Data | Percentage |
| ------------- | ----------------- | ---------- |
| Any IDP data  | 40/50             | 80.0%      |
| Tackles       | 20/50             | 40.0%      |
| Sacks         | 0/50              | 0.0%       |
| Interceptions | 0/50              | 0.0%       |

**Note:** Lower percentages for sacks/INTs are expected since these are rarer events.

______________________________________________________________________

## Sample Data: Elite Defensive Players

### Micah Parsons (LB - DAL)

**Sleeper Player ID:** 7640

**Week 1 2024 Stats:**

```json
{
  "def_snp": 69.0,
  "idp_pass_def": 1.0,
  "idp_qb_hit": 5.0,
  "idp_sack": 1.0,
  "idp_sack_yd": 5.0,
  "idp_tkl": 4.0,
  "idp_tkl_ast": 1.0,
  "idp_tkl_loss": 1.0,
  "idp_tkl_solo": 3.0
}
```

### Top Tackler: T.J. Edwards (LB - CHI)

**Sleeper Player ID:** 5960

**Week 1 2024 Stats:**

```json
{
  "bonus_tkl_10p": 1.0,
  "idp_fum_rec": 1.0,
  "idp_tkl": 15.0,
  "idp_tkl_ast": 5.0,
  "idp_tkl_loss": 2.0,
  "idp_tkl_solo": 10.0
}
```

### Zack Baun (LB - PHI) - Tackles + Sacks

**Sleeper Player ID:** 6815

**Week 1 2024 Stats:**

```json
{
  "bonus_sack_2p": 1.0,
  "bonus_tkl_10p": 1.0,
  "idp_qb_hit": 2.0,
  "idp_sack": 2.0,
  "idp_sack_yd": 9.0,
  "idp_tkl": 15.0,
  "idp_tkl_ast": 4.0,
  "idp_tkl_loss": 1.0,
  "idp_tkl_solo": 11.0
}
```

______________________________________________________________________

## Comparison: Stats vs Projections

| Endpoint                       | Records | Non-Empty | Usable? |
| ------------------------------ | ------- | --------- | ------- |
| `/v1/stats/nfl/regular/2024/1` | 2,310   | 2,310     | ✅ Yes  |
| `/v1/projections/nfl/2024/1`   | 6,957   | 0         | ❌ No   |

**Projections Issue:** All 6,957 records are empty arrays `[]`. No projection data exists for any player.

______________________________________________________________________

## Practical Use Cases

### ✅ Viable Use Cases (Historical Stats)

1. **Historical Analysis**

   - Track player performance over time
   - Calculate season totals and averages
   - Identify trends and breakouts

2. **Backtesting Fantasy Models**

   - Test scoring systems against actual results
   - Validate projection accuracy
   - Train machine learning models

3. **Player Performance Tracking**

   - Monitor weekly IDP production
   - Compare players across positions
   - Identify waiver wire pickups

4. **League Integration**

   - Score actual fantasy points for IDP leagues
   - Calculate standings and results
   - Provide post-game analytics

### ❌ NOT Viable (Projections)

1. **Future Week Projections** - No data available
2. **Pre-Draft Rankings** - Cannot predict future performance
3. **Rest of Season (ROS) Analysis** - No forward-looking projections
4. **Start/Sit Decisions** - No projected values for upcoming games
5. **Trade Valuation** - No future performance predictions

______________________________________________________________________

## Comparison to Other Data Sources

### ESPN IDP Rankings

- ✅ Provides weekly projections
- ✅ Covers all defensive positions
- ❌ May not be API accessible
- ❌ Rankings only, not detailed stats

### FantasyPros IDP

- ✅ Provides weekly projections
- ✅ Expert consensus rankings
- ✅ API access available (paid)
- ✅ Rest of season projections

### PFF (Pro Football Focus)

- ✅ Advanced IDP metrics
- ✅ Grading and projections
- ❌ Expensive API access
- ✅ Highest quality data

### Sleeper API

- ✅ Free access
- ✅ Excellent historical stats
- ❌ NO projections
- ✅ Easy to integrate

______________________________________________________________________

## Recommendations

### For This Project (FF Analytics)

**IDP Projections:** ❌ Do NOT use Sleeper API

- Sleeper does not provide projection data
- Must source from alternative providers (ESPN, FantasyPros, etc.)
- Consider building custom projection model using historical data

**IDP Historical Stats:** ✅ Consider using Sleeper API

- High-quality actual game results
- Comprehensive stat coverage
- Free and reliable access
- Good for backtesting and analysis

### Integration Strategy

If IDP is a priority for this project:

1. **Short-term:** Use ESPN rankings or FantasyPros API for projections
2. **Medium-term:** Build custom IDP projection model using:
   - Sleeper historical stats (free)
   - NFLverse/nflreadpy for context (snap counts, matchups)
   - Simple statistical projections (moving averages, regression)
3. **Long-term:** Consider PFF API if budget allows

______________________________________________________________________

## API Integration Examples

### Fetching IDP Stats

```python
import requests

def fetch_idp_stats(season: int, week: int) -> dict:
    """Fetch IDP stats for a specific week."""
    url = f"https://api.sleeper.app/v1/stats/nfl/regular/{season}/{week}"
    response = requests.get(url)
    return response.json()

# Example: Get Week 1 2024 stats
stats = fetch_idp_stats(2024, 1)

# Filter for defensive players
def is_defensive_position(position: str) -> bool:
    return position in ['DE', 'DT', 'LB', 'CB', 'DB', 'S', 'ILB', 'OLB']
```

### Extracting IDP Fields

```python
def extract_idp_stats(player_stats: dict) -> dict:
    """Extract only IDP-related stats from player data."""
    idp_keywords = ['idp', 'tkl', 'sack', 'int', 'ff', 'fr', 'def_']

    return {
        key: value
        for key, value in player_stats.items()
        if any(kw in key.lower() for kw in idp_keywords)
        and value != 0
    }
```

______________________________________________________________________

## Appendix: Test Scripts

The following test scripts were created during this investigation:

1. **`test_sleeper_idp_projections.py`** - Initial API endpoint testing
2. **`test_sleeper_api_exploration.py`** - Endpoint discovery and structure analysis
3. **`test_sleeper_idp_deep_dive.py`** - Comprehensive IDP data analysis
4. **`test_sleeper_player_lookup.py`** - Player verification and stat samples

All scripts are functional and can be run independently for verification.

______________________________________________________________________

## Conclusion

**Q: Is Sleeper API viable for IDP projections?**
**A: NO.** Sleeper API does not provide projection data for defensive players.

**Q: Is Sleeper API viable for IDP stats?**
**A: YES.** Sleeper API provides excellent historical IDP statistics.

**Recommendation:** Do not integrate Sleeper API for IDP projections. Consider alternative sources (ESPN, FantasyPros) or build custom projection models using Sleeper's historical stats as training data.

______________________________________________________________________

**Investigation completed:** October 29, 2025
**Test scripts location:** `/Users/jason/code/ff_analytics/test_sleeper_*.py`
