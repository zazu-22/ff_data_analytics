# Ticket P3-004: Create data_freshness_current_state Doc

**Phase**: 3 - Documentation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P2-006B (freshness validation implementation), P3-001\
**Updated**: 2025-11-20 - Revised to document manifest validation approach (not dbt source freshness)

## Objective

Create `docs/ops/data_freshness_current_state.md` documenting freshness validation thresholds, how to check snapshot freshness using `tools/validate_manifests.py`, and expected update cadence per source.

## Context

This doc provides operational guidance on snapshot freshness monitoring using the manifest validation approach. It explains the thresholds chosen, how to run freshness checks, and what to do when data goes stale.

**Note**: Original ticket assumed dbt source freshness, but this was cancelled (P2-006/P2-007) due to architectural incompatibility. Instead, freshness validation is implemented via `tools/validate_manifests.py` (P2-006B).

## Tasks

- [ ] Create `docs/ops/data_freshness_current_state.md`
- [ ] Document freshness validation thresholds per source (table format)
- [ ] Explain how to check data freshness using `validate_manifests.py --check-freshness`
- [ ] Document expected update cadence per source
- [ ] Note monitoring status (validate_manifests.py, CI integration ready)
- [ ] Link to freshness configuration file (`config/snapshot_freshness_thresholds.yaml`)

## Acceptance Criteria

- [ ] Document answers "how fresh is my data?"
- [ ] Thresholds clearly explained with rationale
- [ ] Commands for checking freshness provided
- [ ] Expected cadence documented per source

## Implementation Notes

**File**: `docs/ops/data_freshness_current_state.md`

**Document Structure**:

````markdown
# Data Freshness — Current State

**Last Updated**: 2025-11-07
**Status**: Active

## Overview

This document describes data freshness monitoring as of November 2025.

## Freshness Thresholds

**Frequently Updated Sources** (daily/near-daily):

| Source | Warn After | Error After | Expected Cadence | Rationale |
|--------|-----------|-------------|------------------|-----------|
| **nflverse** | 2 days | 7 days | Weekly during season | Updates 1-2 days post-games |
| **sheets** | 1 day | 7 days | Multiple times per day | Roster/transactions updated multiple times daily during season |
| **sleeper** | 1 day | 7 days | Daily | League activity updates daily |

**Weekly/Sporadic Sources**:

| Source | Warn After | Error After | Expected Cadence | Rationale |
|--------|-----------|-------------|------------------|-----------|
| **ktc** | 5 days | 14 days | Sporadic | Market valuations update based on news |
| **ffanalytics** | 2 days | 7 days | Weekly | Projections update weekly during season |

**Threshold Meanings**:
- **Warn After**: Yellow flag — data is getting stale but still usable
- **Error After**: Red flag — data is too stale for reliable analysis

## Checking Data Freshness

### Check All Sources

```bash
# From repository root
uv run python tools/validate_manifests.py \
    --sources all \
    --check-freshness \
    --freshness-config config/snapshot_freshness_thresholds.yaml
```

**Expected Output**:

```
Snapshot Manifest Validation (with Freshness)
==================================================

Validated: 24/24 snapshots (integrity)
Fresh: 22/24 snapshots (within thresholds)

Freshness Status:

  nflverse.weekly [2025-11-18] FRESH:
    - Snapshot FRESH: 2 days old

  sheets.transactions [2025-11-19] FRESH:
    - Snapshot FRESH: 1 day old

  ktc.assets [2025-11-15] STALE (WARN):
    - Snapshot STALE (WARN): 5 days old (threshold: 5 days)
```

### Check Specific Source

```bash
uv run dbt source freshness --select source:nflverse
uv run dbt source freshness --select source:sheets
```

### Check Before dbt Run

```bash
# Freshness check + model run
uv run dbt source freshness && uv run dbt run
```

## Expected Update Cadence

### During NFL Season (Sep-Feb)

**Frequently Updated**:

- **nflverse**: Tuesday/Wednesday after weekend games
- **sheets**: Multiple times per day (roster moves, transactions, picks)
- **sleeper**: Daily (league activity)

**Weekly/Sporadic**:

- **ffanalytics**: Weekly (Wednesday projections)
- **ktc**: Sporadic (news-driven valuation updates)

### Off-Season (Mar-Aug)

- **nflverse**: Infrequent (training camp, preseason only)
- **sheets**: Weekly or less (off-season trades)
- **ffanalytics**: Pre-draft rush (weekly), then monthly
- **ktc**: Weekly (draft season), then sporadic
- **sleeper**: Weekly or less

## Monitoring Status

**Current State**:

- Freshness checks via `dbt source freshness` (manual or CI)
- No automated alerts/notifications
- No dashboard monitoring

**Future Enhancements** (out of scope for now):

- Slack/email alerts on WARN/ERROR status
- Dashboard tracking freshness over time
- Automated freshness checks in Prefect flows

## Troubleshooting Stale Data

### Warning Status (Yellow)

1. **Check trigger status**: Did scheduled load run?

   ```bash
   # GitHub Actions
   # Go to repo → Actions → Check recent workflow runs
   ```

2. **Run manual load** if scheduled load failed:

   ```bash
   # See: docs/ops/ingestion_triggers_current_state.md
   ```

3. **Acceptable during off-season**: Warnings expected when games aren't being played

### Error Status (Red)

1. **Investigate immediately**: Data is too stale for analysis
2. **Check for blocker**: API down? Credentials expired?
3. **Run manual load** to get current data
4. **Document issue**: Add note to snapshot registry if load permanently failed

### False Positives

During off-season, ERROR status may be expected (no new games = no new data). Consider temporarily adjusting thresholds:

```yaml
# Temporarily in src_nflverse.yml
freshness:
  warn_after: {count: 14, period: day}  # Relaxed for off-season
  error_after: {count: 30, period: day}
```

## CI Integration

Freshness checks run in CI before dbt models:

```yaml
# .github/workflows/data-pipeline.yml
- name: Check Data Freshness
  run: |
    cd dbt/ff_data_transform
    uv run dbt source freshness
    # Workflow fails if any ERROR status
```

## References

- Source YAML configs: `dbt/ff_data_transform/models/sources/src_*.yml`
- Ingestion triggers: `docs/ops/ingestion_triggers_current_state.md`
- Snapshot registry: `dbt/ff_data_transform/seeds/snapshot_registry.csv`

```

## Testing

1. **Run freshness checks**: Verify commands work and output matches examples
2. **Test failure scenario**: Temporarily adjust threshold to trigger WARN/ERROR
3. **Verify thresholds**: Cross-check table against actual source YAML files

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 3 Activity (lines 398-407), Freshness table (lines 186-192)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 3 Ops Docs (lines 225-231)
- Source configs: `dbt/ff_data_transform/models/sources/src_*.yml`

```
````
