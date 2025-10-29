# IDP Projection Source Investigation

**Date:** 2025-10-29
**Context:** Phase 2.2 - Investigating why most fantasy football sources don't provide IDP projections

______________________________________________________________________

## Executive Summary

**Finding:** FantasySharks is currently the ONLY source providing IDP stat projections through ffanalytics.

**Risk:** Single point of failure for all IDP projection data (616 players, 8 stat types).

**Recommendation:** Monitor FantasySharks availability and consider alternative IDP data sources (IDP Guru, paid APIs).

______________________________________________________________________

## Investigation Results

### Sources Tested

- **FantasyPros** - Scraped QB/RB/WR/TE successfully, NO IDP data
- **FantasySharks** - Scraped ALL positions including DL/LB/DB ✅

### Data from 2025-10-29 Scrape

| Position Type           | Players | Sources Providing Data          |
| ----------------------- | ------- | ------------------------------- |
| Offensive (QB/RB/WR/TE) | 802     | 2 (FantasyPros + FantasySharks) |
| IDP (DL/LB/DB)          | 616     | 1 (FantasySharks ONLY)          |

**Source Count Analysis:**

- ALL projections have `source_count=1` in our test (only scraped 2 sources)
- Offensive positions: Both sources contributed
- IDP positions: Only FantasySharks contributed

______________________________________________________________________

## Why Other Sources Lack IDP

### Key Distinction: Rankings vs. Projections

**Rankings** = Ordinal lists (Player A is better than Player B)
**Projections** = Stat forecasts (7.5 tackles, 0.3 sacks, 0.05 INTs)

The ffanalytics package scrapes **stat projections**, not rankings.

### Research Findings

1. **ESPN**

   - ✅ Provides: IDP rankings (weekly updated)
   - ❌ Does NOT provide: IDP stat projections
   - Format: Consensus expert rankings, no stat values

2. **FantasyPros**

   - ✅ Provides: IDP consensus rankings, draft guides, strategy articles
   - ❌ Does NOT provide: IDP weekly stat projections
   - Format: Expert consensus rankings, no tackle/sack/INT projections

3. **CBS, NFL, NumberFire, FFToday, etc.**

   - No evidence of IDP stat projections found
   - Most focus exclusively on offensive players for projections
   - May have IDP rankings but not stat forecasts

4. **FantasySharks**

   - ✅ Provides: Full IDP stat projections (tackles, sacks, INTs, PD, FF, FR, TDs)
   - Format: Per-game stat forecasts for DL/LB/DB positions
   - Availability: Confirmed working as of 2025-10-29

______________________________________________________________________

## Why IDP Projections Are Rare

### Market Reality

**IDP leagues are a minority:** Most fantasy leagues play standard format (QB/RB/WR/TE/K/DST) without individual defensive players.

**Low demand = Low supply:** Projection sites focus resources on what 90%+ of users need (offensive players).

**Complexity:** IDP performance is harder to project than offensive players:

- More volatile week-to-week (scheme dependent)
- Injury replacements more common (rotational players)
- Less public data/analysis available

**Business model:** Sites that DO provide IDP often monetize it:

- Free tier: Rankings only
- Paid tier: Stat projections

______________________________________________________________________

## Alternative IDP Sources

### Identified Options

1. **IDP Guru** (https://idpguru.com/)

   - Comprehensive IDP rankings and analysis
   - Unclear if provides stat projections (requires investigation)
   - Potential ffanalytics integration candidate

2. **Fantasy Nerds** ($399.95/year)

   - Confirmed to provide IDP projections via API
   - Identified in previous research
   - Cost may be prohibitive

3. **Sports Data IO / Fantasy Data**

   - Team defense projections confirmed
   - IDP support unclear (requires investigation)

4. **nflverse** (free)

   - Historical IDP stats ONLY (not projections)
   - Good for backtesting, not for weekly forecasts

______________________________________________________________________

## Risk Assessment

### Current Architecture

```
IDP Projections Pipeline:
  Raw Data → FantasySharks ONLY → 616 players → 8 stat types → fact table
```

### Single Point of Failure Risks

| Risk                           | Probability | Impact   | Mitigation                      |
| ------------------------------ | ----------- | -------- | ------------------------------- |
| FantasySharks site down        | Medium      | High     | Add monitoring/alerts           |
| FantasySharks changes format   | Medium      | High     | Version scraper, test regularly |
| FantasySharks discontinues IDP | Low         | Critical | Identify backup source NOW      |
| ffanalytics scraper breaks     | Low         | High     | Pin R package version           |

______________________________________________________________________

## Recommendations

### Immediate Actions (Task 2.3)

1. **Add source diversity monitoring**

   - Track which sources contribute to each position
   - Alert if IDP source count drops below threshold
   - Log FantasySharks scrape success rate

2. **Document dependency**

   - Add ADR documenting FantasySharks dependency
   - Update data pipeline documentation
   - Add to system health dashboard

### Future Considerations

3. **Investigate IDP Guru integration**

   - Check if provides stat projections (not just rankings)
   - Assess ffanalytics compatibility
   - Timeline: Sprint 2

4. **Consider paid API as insurance**

   - Fantasy Nerds ($400/year) as backup
   - Only activate if FantasySharks fails
   - Decision: Defer until failure occurs

5. **Use nflverse for historical validation**

   - Already have historical IDP stats
   - Use to validate projection accuracy
   - Helps build internal IDP model if needed

______________________________________________________________________

## Appendix: FFanalytics Package Findings

### Default Sources (from config)

- fantasypros, numberfire, fantasysharks, espn, fftoday, cbs, nfl, rtsports, walterfootball

### IDP Position Support

- Package DOES support DL, LB, DB positions
- Includes default VOR baselines for IDP (10 for each position)
- Documentation lacks source-specific IDP capability matrix

### Known Issues (GitHub)

- Issue #30 (2019): Multiple sources had scraping failures
- No recent issues specifically about IDP support
- Package maintenance appears active as of 2024-2025

______________________________________________________________________

## Conclusion

**FantasySharks is our sole IDP projection source**, which creates a critical dependency. While this is a common limitation in the fantasy football data ecosystem (most sites don't provide IDP projections), we should:

1. ✅ **Monitor FantasySharks availability closely** (Task 2.3)
2. ⏳ **Investigate IDP Guru as potential backup** (Future sprint)
3. ⏳ **Consider paid API only if free source fails** (Defer)

The good news: Our IDP mapping is now working at 99% success rate with the one source we have. The risk is sustainability, not current functionality.
