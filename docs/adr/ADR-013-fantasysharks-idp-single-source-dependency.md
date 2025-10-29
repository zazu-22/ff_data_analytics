# ADR-013: FantasySharks Single-Source Dependency for IDP Projections

**Status:** Accepted
**Date:** 2025-10-29
**Decision Makers:** Architecture Team
**Related:** ADR-011 (Player ID Mapping), docs/findings/2025-10-29_idp_source_investigation.md

______________________________________________________________________

## Context

As of 2025-10-29, our IDP (Individual Defensive Player) projection pipeline depends entirely on a single data source: **FantasySharks**.

### Current State

- **IDP Players:** 616 (DL: 232, LB: 133, DB: 251)
- **IDP Stats:** 8 types (solo/assisted tackles, sacks, passes defended, interceptions, fumbles, TDs)
- **Source Count:** 1 (FantasySharks only)
- **Offensive Players:** 802 with 2+ sources (FantasyPros + FantasySharks)

### Why Only One Source?

Investigation revealed that most fantasy football projection sites provide IDP **rankings** but not IDP **stat projections**:

- **ESPN:** IDP rankings only, no stat projections
- **FantasyPros:** Consensus rankings, no weekly tackle/sack forecasts
- **CBS, NFL, FFToday, etc.:** No evidence of IDP stat projections
- **FantasySharks:** ONLY source providing actual IDP stat projections (tackles, sacks, INTs, etc.)

**Root cause:** IDP leagues are a minority (~10% of fantasy leagues), so most sites don't invest in IDP projection models.

______________________________________________________________________

## Decision

We **accept this single-source dependency** with the following mitigation strategies:

### Immediate Actions ✅

1. **Monitoring:** Created `assert_idp_source_diversity.sql` test to alert if source count drops
2. **Documentation:** This ADR + investigation findings document
3. **Metadata Tracking:** Raw data includes `source_count` for visibility

### Future Considerations ⏳

1. **Backup Source Investigation:** Evaluate IDP Guru or Fantasy Nerds API (Sprint 2+)
2. **Historical Validation:** Use nflverse IDP stats to validate projection accuracy
3. **Internal Model:** If FantasySharks fails, consider building simple IDP model using historical stats

______________________________________________________________________

## Consequences

### Positive

- ✅ **Simple Architecture:** One source means less complexity, easier to maintain
- ✅ **Cost:** Free vs. paid alternatives ($400/year for Fantasy Nerds)
- ✅ **Quality:** FantasySharks projections include all 8 stat types we need

### Negative

- ❌ **Single Point of Failure:** If FantasySharks goes down, we lose ALL IDP projections
- ❌ **No Consensus:** Can't average multiple sources for better accuracy
- ❌ **Format Changes:** Breaking changes to FantasySharks site will break our pipeline

### Risks & Mitigation

| Risk                           | Probability | Impact   | Mitigation                             |
| ------------------------------ | ----------- | -------- | -------------------------------------- |
| FantasySharks site unavailable | Medium      | High     | Monitoring + alert to switch to backup |
| Site format changes            | Medium      | High     | Pin scraper version, test in CI        |
| FantasySharks discontinues IDP | Low         | Critical | Identify backup source proactively     |
| Projection quality issues      | Low         | Medium   | Validate against nflverse historical   |

______________________________________________________________________

## Alternatives Considered

### Option A: Add Paid Source (Fantasy Nerds)

- **Cost:** $399.95/year
- **Pros:** Professional API, reliable
- **Cons:** Budget constraint, may not justify cost for IDP-only
- **Decision:** Defer unless FantasySharks fails

### Option B: IDP Guru Integration

- **Cost:** Unknown (need to investigate)
- **Pros:** IDP specialist, comprehensive coverage
- **Cons:** Unknown if provides stat projections (may be rankings only)
- **Decision:** Investigate in Sprint 2

### Option C: Build Internal IDP Model

- **Cost:** High development time
- **Pros:** Full control, no external dependency
- **Cons:** Complex (defensive stats are noisy), may not be more accurate
- **Decision:** Last resort only

### Option D: Drop IDP Projections

- **Pros:** Eliminates dependency
- **Cons:** Incomplete data for IDP leagues, defeats purpose of project
- **Decision:** Not acceptable

______________________________________________________________________

## Implementation

### Monitoring Setup

**Test:** `tests/assert_idp_source_diversity.sql`

```sql
-- Alerts if >80% of IDP players come from single source
-- Currently WILL alert (expected) until we add 2nd source
```

**Metadata:** Raw projection files include:

- `source_count` - Number of sources contributing to each player
- `provider` - Source attribution
- Allows tracking source health over time

### Health Dashboard

Add to ops monitoring:

```sql
SELECT
  pos,
  source_count,
  COUNT(*) as players
FROM projections_latest
WHERE pos IN ('DL', 'LB', 'DB')
GROUP BY pos, source_count;
```

**Alert Condition:** If `source_count = 0` for any IDP position

______________________________________________________________________

## Review Triggers

This decision should be revisited if:

1. **FantasySharks fails** - Immediate switch to backup source required
2. **Budget available** - Consider Fantasy Nerds paid API
3. **Sprint 2+** - Investigate IDP Guru integration
4. **Projection accuracy issues** - Consider alternative sources or internal model

______________________________________________________________________

## References

- Investigation findings: `docs/findings/2025-10-29_idp_source_investigation.md`
- Test implementation: `tests/assert_idp_source_diversity.sql`
- Related ADRs: ADR-011 (Player ID Mapping), ADR-012 (Name/Position Normalization)
- nflverse: Historical IDP stats for validation
- Fantasy Nerds API: https://api.fantasynerds.com/ ($399.95/year)
- IDP Guru: https://idpguru.com/ (investigate)

______________________________________________________________________

## Approval

**Date:** 2025-10-29
**Status:** Accepted with monitoring
**Next Review:** Sprint 2 planning or upon FantasySharks failure
