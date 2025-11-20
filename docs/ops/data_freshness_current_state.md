# Data Freshness — Current State

**Last Updated**: 2025-11-20
**Status**: Active

## Overview

This document describes data freshness monitoring as of November 2025.

Data freshness validation ensures that snapshots are recent enough for reliable analysis. The project uses `tools/validate_manifests.py` with configurable per-source thresholds to detect stale data before dbt model execution.

## Freshness Thresholds

**Frequently Updated Sources** (daily/near-daily):

| Source       | Warn After | Error After | Expected Cadence       | Rationale                                                      |
| ------------ | ---------- | ----------- | ---------------------- | -------------------------------------------------------------- |
| **nflverse** | 2 days     | 7 days      | Weekly during season   | Updates 1-2 days post-games                                    |
| **sheets**   | 1 day      | 7 days      | Multiple times per day | Roster/transactions updated multiple times daily during season |
| **sleeper**  | 1 day      | 7 days      | Daily                  | League activity updates daily                                  |

**Weekly/Sporadic Sources**:

| Source          | Warn After | Error After | Expected Cadence | Rationale                               |
| --------------- | ---------- | ----------- | ---------------- | --------------------------------------- |
| **ktc**         | 5 days     | 14 days     | Sporadic         | Market valuations update based on news  |
| **ffanalytics** | 2 days     | 7 days      | Weekly           | Projections update weekly during season |

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
# Check single source
uv run python tools/validate_manifests.py \
    --sources nflverse \
    --check-freshness \
    --freshness-config config/snapshot_freshness_thresholds.yaml

# Check multiple sources
uv run python tools/validate_manifests.py \
    --sources nflverse,sheets \
    --check-freshness \
    --freshness-config config/snapshot_freshness_thresholds.yaml
```

### Check Before dbt Run

```bash
# Freshness check + model run (fail fast if data stale)
uv run python tools/validate_manifests.py \
    --sources all \
    --check-freshness \
    --freshness-config config/snapshot_freshness_thresholds.yaml \
    --fail-on-gaps && just dbt-run
```

### JSON Output for Programmatic Use

```bash
# Get machine-readable freshness report
uv run python tools/validate_manifests.py \
    --sources all \
    --check-freshness \
    --freshness-config config/snapshot_freshness_thresholds.yaml \
    --output-format json > freshness_report.json

# Filter for stale-error snapshots only
cat freshness_report.json | jq '.results[] | select(.freshness.status == "stale-error")'
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

- Freshness checks via `tools/validate_manifests.py` (manual execution)
- Configurable per-source thresholds in `config/snapshot_freshness_thresholds.yaml`
- No automated alerts/notifications
- No dashboard monitoring

**CI Integration** (ready to use):

```yaml
# Example .github/workflows/data-pipeline.yml
- name: Validate Snapshot Integrity and Freshness
  run: |
    uv run python tools/validate_manifests.py \
      --sources nflverse,sheets,sleeper \
      --check-freshness \
      --freshness-config config/snapshot_freshness_thresholds.yaml \
      --fail-on-gaps
```

**Future Enhancements** (out of scope for now):

- Slack/email alerts on WARN/ERROR status
- Dashboard tracking freshness over time
- Automated freshness checks in Prefect flows

## Troubleshooting Stale Data

### Warning Status (Yellow)

1. **Check trigger status**: Did scheduled load run?

   ```bash
   # GitHub Actions (when implemented)
   # Go to repo → Actions → Check recent workflow runs
   ```

2. **Run manual load** if scheduled load failed:

   ```bash
   # See: docs/ops/ingestion_triggers_current_state.md
   # Example for nflverse:
   uv run python scripts/ingest/ingest_nflverse.py
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
# Edit config/snapshot_freshness_thresholds.yaml temporarily
nflverse:
  warn_days: 14   # Relaxed for off-season
  error_days: 30
  rationale: "Off-season: Weekly/monthly updates only"
```

**Remember to revert** when season starts:

```yaml
nflverse:
  warn_days: 2
  error_days: 7
  rationale: "Weekly in-season, updates within 2 days post-games"
```

## Freshness Configuration

**Location**: `config/snapshot_freshness_thresholds.yaml`

**Structure**:

```yaml
source_name:
  warn_days: <integer>
  error_days: <integer>
  rationale: "<explanation>"
```

**Editing Thresholds**:

1. Edit `config/snapshot_freshness_thresholds.yaml`
2. Update `warn_days` and `error_days` values
3. Update `rationale` to explain threshold choice
4. Test changes: `uv run python tools/validate_manifests.py --sources <source> --check-freshness --freshness-config config/snapshot_freshness_thresholds.yaml`

## Why Not dbt source freshness?

This project uses external Parquet files read via `read_parquet()`, not database tables. dbt's `dbt source freshness` requires queryable tables with timestamp columns, making it architecturally incompatible with this project's external data architecture.

**Advantages of manifest validation approach**:

- ✅ Works with existing Parquet architecture (no architectural change)
- ✅ Consolidates validation in one tool (integrity + freshness)
- ✅ Supports per-source thresholds (flexible configuration)
- ✅ Can run before dbt as pre-execution safety check
- ✅ No dependency on dbt execution

## References

- Freshness configuration: `config/snapshot_freshness_thresholds.yaml`
- Validation tool: `tools/validate_manifests.py`
- Ingestion triggers: `docs/ops/ingestion_triggers_current_state.md`
- Snapshot registry: `dbt/ff_data_transform/seeds/snapshot_registry.csv`
- Tool documentation: `tools/CLAUDE.md` (validate_manifests.py section)
