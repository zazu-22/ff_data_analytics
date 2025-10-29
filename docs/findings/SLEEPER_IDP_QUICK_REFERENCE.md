# Sleeper IDP Investigation - Quick Reference

**Investigation Date:** October 29, 2025

______________________________________________________________________

## TL;DR

### ❌ **NOT VIABLE for IDP Projections**

Sleeper API provides **historical stats only** - NOT projections.

______________________________________________________________________

## Quick Answers

### Can I get IDP projections from Sleeper API?

**NO.** The projection endpoints return empty data.

### Can I get IDP stats from Sleeper API?

**YES.** Historical (actual game) stats are available and high quality.

### What should I use instead for projections?

- ESPN IDP Rankings
- FantasyPros IDP API (paid)
- PFF API (expensive)
- Build custom model using Sleeper historical data

______________________________________________________________________

## Working Endpoint

```bash
# Get IDP stats for a specific week
curl https://api.sleeper.app/v1/stats/nfl/regular/2024/1
```

**Returns:** Actual game statistics for 974+ defensive players

______________________________________________________________________

## Key IDP Fields

| Field          | Description        |
| -------------- | ------------------ |
| `idp_tkl`      | Total tackles      |
| `idp_tkl_solo` | Solo tackles       |
| `idp_tkl_ast`  | Assisted tackles   |
| `idp_sack`     | Sacks              |
| `idp_qb_hit`   | QB hits            |
| `idp_int`      | Interceptions      |
| `idp_ff`       | Forced fumbles     |
| `idp_pass_def` | Passes defended    |
| `pts_idp`      | IDP fantasy points |

______________________________________________________________________

## Example: Get Top Tacklers

```python
import requests

# Fetch stats
stats = requests.get("https://api.sleeper.app/v1/stats/nfl/regular/2024/1").json()

# Get players
players = requests.get("https://api.sleeper.app/v1/players/nfl").json()

# Find top tacklers
defensive_positions = ['DE', 'DT', 'LB', 'CB', 'DB', 'S']

tacklers = []
for player_id, player_stats in stats.items():
    if player_id in players:
        player = players[player_id]
        if player.get('position') in defensive_positions:
            tackles = player_stats.get('idp_tkl', 0)
            if tackles > 0:
                tacklers.append({
                    'name': player.get('full_name'),
                    'position': player.get('position'),
                    'team': player.get('team'),
                    'tackles': tackles
                })

# Sort and display
tacklers.sort(key=lambda x: x['tackles'], reverse=True)
for t in tacklers[:10]:
    print(f"{t['name']:30s} {t['position']:3s} {t['team']:3s} - {t['tackles']} tkl")
```

**Output:**

```
T.J. Edwards                   LB  CHI - 15.0 tkl
Zack Baun                      LB  PHI - 15.0 tkl
Nick Cross                     DB  IND - 14.0 tkl
```

______________________________________________________________________

## Data Quality

✅ **Good coverage:** 974 defensive players per week
✅ **Complete stats:** 67 defensive stat fields
✅ **Elite players:** All major IDP stars included
❌ **No projections:** Actual stats only

______________________________________________________________________

## Files Created

1. **`SLEEPER_IDP_INVESTIGATION_REPORT.md`** - Full investigation report
2. **`sleeper_api_sample_responses.json`** - Sample API responses
3. **`test_sleeper_*.py`** - Test scripts (4 files)

______________________________________________________________________

## Next Steps

If IDP is a priority:

1. **Short-term:** Use ESPN rankings or another source for projections
2. **Medium-term:** Build custom projection model using Sleeper historical stats
3. **Long-term:** Consider paid API (FantasyPros, PFF) if budget allows

______________________________________________________________________

## Final Verdict

| Use Case                 | Sleeper API  | Recommendation                |
| ------------------------ | ------------ | ----------------------------- |
| **IDP Projections**      | ❌ No data   | Use alternative source        |
| **IDP Historical Stats** | ✅ Excellent | Good for analysis/backtesting |
| **Player Research**      | ✅ Good      | Free and reliable             |
| **Fantasy Scoring**      | ✅ Good      | All fields available          |

______________________________________________________________________

**Bottom Line:** Don't integrate Sleeper for IDP projections. Consider for historical analysis only.
