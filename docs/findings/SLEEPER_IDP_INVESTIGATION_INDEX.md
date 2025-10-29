# Sleeper API IDP Investigation - Index

**Investigation Date:** October 29, 2025
**Status:** ✅ Complete
**Verdict:** ❌ NOT VIABLE for IDP Projections

______________________________________________________________________

## Quick Start

### Need the answer right away?

👉 **Read:** `SLEEPER_IDP_SUMMARY.txt` (6KB, 2 min read)

### Want more details?

👉 **Read:** `SLEEPER_IDP_QUICK_REFERENCE.md` (3.5KB, 5 min read)

### Need the full investigation?

👉 **Read:** `SLEEPER_IDP_INVESTIGATION_REPORT.md` (8.4KB, 15 min read)

______________________________________________________________________

## File Guide

### 📋 Documentation Files

| File                                    | Size      | Purpose                                  | Read Time |
| --------------------------------------- | --------- | ---------------------------------------- | --------- |
| **SLEEPER_IDP_SUMMARY.txt**             | 6.0KB     | Executive summary with key findings      | 2 min     |
| **SLEEPER_IDP_QUICK_REFERENCE.md**      | 3.5KB     | Quick reference guide with code examples | 5 min     |
| **SLEEPER_IDP_INVESTIGATION_REPORT.md** | 8.4KB     | Complete investigation report            | 15 min    |
| **SLEEPER_IDP_INVESTIGATION_INDEX.md**  | This file | Navigation guide                         | -         |
| **sleeper_api_sample_responses.json**   | 7.1KB     | Real API responses and data samples      | Reference |

### 🔬 Test Scripts

| File                                | Size  | Purpose                          | Runnable |
| ----------------------------------- | ----- | -------------------------------- | -------- |
| **test_sleeper_idp_projections.py** | 9.4KB | Initial API endpoint testing     | ✅ Yes   |
| **test_sleeper_api_exploration.py** | 5.1KB | Endpoint discovery and structure | ✅ Yes   |
| **test_sleeper_idp_deep_dive.py**   | 9.9KB | Comprehensive IDP data analysis  | ✅ Yes   |
| **test_sleeper_player_lookup.py**   | 5.0KB | Player verification and samples  | ✅ Yes   |

All test scripts are functional and can be re-run independently.

______________________________________________________________________

## Investigation Workflow

### What was tested:

1. ✅ **Player Metadata Endpoint** - `/v1/players/nfl`
2. ✅ **Stats Endpoint** - `/v1/stats/nfl/regular/{season}/{week}`
3. ❌ **Projection Endpoints** - Multiple variations tested, all failed or empty

### How it was tested:

1. **Direct API calls** - Used Python requests library
2. **Multiple weeks** - Tested weeks 1, 2, 3, 8, 9 of 2024 season
3. **Elite player samples** - Verified 10 well-known defensive players
4. **Data quality checks** - Analyzed 50-player samples for completeness
5. **Field analysis** - Cataloged all 67 IDP stat fields

### What was found:

- ✅ Historical stats work perfectly (974+ players per week)
- ✅ Data quality is good (80% have IDP data)
- ✅ Comprehensive stat coverage (tackles, sacks, INTs, etc.)
- ❌ Projection endpoints return empty data
- ❌ No projection data for any player
- ❌ Not viable for fantasy projections

______________________________________________________________________

## Key Findings Summary

### ❌ Projections: NOT VIABLE

| Endpoint                     | Status | Issue                |
| ---------------------------- | ------ | -------------------- |
| `/v1/projections/nfl/2024`   | 404    | Not found            |
| `/projections/nfl/2025`      | 400    | Bad request          |
| `/v1/projections/nfl/2024/1` | 200    | Returns empty arrays |

**Verdict:** Sleeper API does not provide IDP projections.

### ✅ Historical Stats: VIABLE

| Metric                     | Value |
| -------------------------- | ----- |
| Defensive players per week | 974+  |
| IDP stat fields available  | 67    |
| Data completeness          | 80%   |
| Elite players coverage     | 8/10  |
| Cost                       | Free  |

**Verdict:** Excellent for historical analysis and backtesting.

______________________________________________________________________

## Recommendations

### For IDP Projections:

❌ **Do NOT use Sleeper API**

Alternative sources:

- ESPN IDP Rankings (free)
- FantasyPros IDP API (paid, ~$100/year)
- PFF API (expensive, ~$1000+/year)
- Custom model using Sleeper historical data

### For IDP Historical Stats:

✅ **Consider using Sleeper API**

Good for:

- Historical performance analysis
- Backtesting fantasy models
- Player trend identification
- Training data for ML models

______________________________________________________________________

## Code Examples

### Quick Example: Get IDP Stats

```python
import requests

# Fetch stats
stats = requests.get("https://api.sleeper.app/v1/stats/nfl/regular/2024/1").json()

# Get player metadata
players = requests.get("https://api.sleeper.app/v1/players/nfl").json()

# Find Micah Parsons
micah_id = "7640"
if micah_id in stats:
    print(f"Micah Parsons Week 1 2024:")
    print(f"  Tackles: {stats[micah_id].get('idp_tkl', 0)}")
    print(f"  Sacks: {stats[micah_id].get('idp_sack', 0)}")
    print(f"  QB Hits: {stats[micah_id].get('idp_qb_hit', 0)}")
```

**More examples:** See `SLEEPER_IDP_QUICK_REFERENCE.md`

______________________________________________________________________

## Sample Data

### Top Tacklers (Week 1 2024)

1. **T.J. Edwards** (LB-CHI) - 15 tackles (10 solo, 5 ast)
2. **Zack Baun** (LB-PHI) - 15 tackles (11 solo, 4 ast, 2 sacks)
3. **Nick Cross** (DB-IND) - 14 tackles (8 solo, 6 ast)

### Elite Player Sample

**Micah Parsons** (LB-DAL, ID: 7640)

```json
{
  "idp_tkl": 4.0,
  "idp_tkl_solo": 3.0,
  "idp_tkl_ast": 1.0,
  "idp_sack": 1.0,
  "idp_qb_hit": 5.0,
  "idp_pass_def": 1.0,
  "idp_tkl_loss": 1.0
}
```

**Full samples:** See `sleeper_api_sample_responses.json`

______________________________________________________________________

## Running Test Scripts

All scripts are standalone and can be run independently:

```bash
# Initial projection testing
python3 test_sleeper_idp_projections.py

# API endpoint exploration
python3 test_sleeper_api_exploration.py

# Comprehensive IDP analysis
python3 test_sleeper_idp_deep_dive.py

# Player lookup verification
python3 test_sleeper_player_lookup.py
```

**Requirements:** Python 3.x, `requests` library

______________________________________________________________________

## Investigation Timeline

1. **12:44 PM** - Started investigation, tested initial endpoints
2. **12:49 PM** - Created first test script (projections)
3. **12:57 PM** - Discovered projection endpoints return empty data
4. **1:55 PM** - Found working stats endpoint with IDP data
5. **1:56 PM** - Verified elite players and data quality
6. **1:57 PM** - Generated comprehensive documentation
7. **1:58 PM** - Investigation complete ✅

**Total time:** ~1 hour 15 minutes

______________________________________________________________________

## Next Steps

### Immediate Actions:

1. ❌ **Do NOT** build Sleeper IDP projection integration
2. ✅ **Evaluate** alternative projection sources (ESPN, FantasyPros)
3. ✅ **Document** decision in project architecture docs

### Future Considerations:

1. **Short-term:** Use existing projection source (ESPN rankings)
2. **Medium-term:** Build custom projection model using Sleeper historical data
3. **Long-term:** Evaluate paid APIs (FantasyPros, PFF) if budget allows

______________________________________________________________________

## Questions?

All common questions are answered in the documentation:

- **Quick answers:** `SLEEPER_IDP_SUMMARY.txt`
- **Code examples:** `SLEEPER_IDP_QUICK_REFERENCE.md`
- **Full details:** `SLEEPER_IDP_INVESTIGATION_REPORT.md`
- **Sample data:** `sleeper_api_sample_responses.json`

______________________________________________________________________

## Conclusion

**The Sleeper API does not provide IDP projections.**

While the historical stats are excellent and free, they are not suitable for:

- Weekly projection analysis
- Pre-draft rankings
- Start/sit decisions
- Rest-of-season (ROS) projections

Alternative sources must be used for IDP projection needs.

______________________________________________________________________

**Investigation Status:** ✅ Complete
**Date:** October 29, 2025
**Total Files:** 8 (4 documentation, 4 test scripts)
**Total Size:** 54.8 KB
