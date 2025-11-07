# Ticket P2-006: Add Freshness Tests (Frequently Updated Sources)

**Phase**: 2 - Governance\
**Estimated Effort**: Small (2-3 hours)\
**Dependencies**: None (can work in parallel)

## Objective

Add dbt source freshness tests for frequently updated sources (nflverse, sheets, sleeper) with appropriate warn/error thresholds based on their daily/near-daily update cadence.

## Context

Freshness tests provide a pre-dbt safety net that catches stale data before model execution. By configuring `loaded_at_field: dt` and setting warn/error thresholds per source, we can detect when snapshots haven't been updated within expected timeframes.

This ticket covers the **frequently updated sources** grouped by their operational update cadence:

- **sheets**: Daily updates (roster moves, transactions) - 1 day warn threshold
- **sleeper**: Daily league activity updates - 1 day warn threshold
- **nflverse**: Weekly during season, updates within 2 days post-games - 2 day warn threshold

These sources are grouped together because they share similar operational monitoring needs (daily/near-daily freshness checks).

## Tasks

### Add nflverse Freshness Tests

- [ ] Update `dbt/ff_analytics/models/sources/src_nflverse.yml`
- [ ] Set `loaded_at_field: dt` at source level
- [ ] Configure freshness: warn_after 2 days, error_after 7 days
- [ ] Test with `dbt source freshness --select source:nflverse`

### Add sheets Freshness Tests

- [ ] Create or update `dbt/ff_analytics/models/sources/src_sheets.yml`
- [ ] Set `loaded_at_field: dt` at source level
- [ ] Configure freshness: warn_after 1 day, error_after 7 days
- [ ] Test with `dbt source freshness --select source:sheets`

### Add sleeper Freshness Tests

- [ ] Create or update `dbt/ff_analytics/models/sources/src_sleeper.yml`
- [ ] Set `loaded_at_field: dt` at source level
- [ ] Configure freshness: warn_after 1 day, error_after 7 days
- [ ] Test with `dbt source freshness --select source:sleeper`

### Verify Freshness Checks

- [ ] Run full freshness check: `dbt source freshness`
- [ ] Verify current data meets thresholds (should pass) for all three sources
- [ ] Document expected update cadence per source

## Acceptance Criteria

- [ ] nflverse source has freshness tests configured
- [ ] sheets source has freshness tests configured
- [ ] sleeper source has freshness tests configured
- [ ] `dbt source freshness` passes for all three sources
- [ ] Thresholds appropriate for update cadence (daily/near-daily)
- [ ] Source YAML files documented with freshness expectations

## Implementation Notes

**Freshness Thresholds** (grouped by frequency):

| Source       | Warn After | Error After | Rationale                                          |
| ------------ | ---------- | ----------- | -------------------------------------------------- |
| **sheets**   | 1 day      | 7 days      | Daily roster/transaction updates expected          |
| **sleeper**  | 1 day      | 7 days      | Daily roster changes and league activity           |
| **nflverse** | 2 days     | 7 days      | Weekly in-season, updates within 2 days post-games |

**File: `dbt/ff_analytics/models/sources/src_nflverse.yml`**

```yaml
version: 2

sources:
  - name: nflverse
    description: "NFLverse datasets via nflreadpy"
    freshness:
      warn_after: {count: 2, period: day}
      error_after: {count: 7, period: day}
    loaded_at_field: dt

    tables:
      - name: weekly
        description: "Player stats by week"
        identifier: "weekly/dt=*/*.parquet"
        meta:
          external_location: "{{ env_var('RAW_NFLVERSE_WEEKLY_GLOB', 'data/raw/nflverse/weekly/dt=*/*.parquet') }}"

      - name: snap_counts
        description: "Snap count participation by player/week"
        identifier: "snap_counts/dt=*/*.parquet"
        meta:
          external_location: "{{ env_var('RAW_NFLVERSE_SNAP_COUNTS_GLOB', 'data/raw/nflverse/snap_counts/dt=*/*.parquet') }}"

      - name: ff_opportunity
        description: "Fantasy-relevant opportunity metrics"
        identifier: "ff_opportunity/dt=*/*.parquet"
        meta:
          external_location: "{{ env_var('RAW_NFLVERSE_FF_OPPORTUNITY_GLOB', 'data/raw/nflverse/ff_opportunity/dt=*/*.parquet') }}"

      - name: schedule
        description: "NFL game schedule"
        identifier: "schedule/dt=*/*.parquet"

      - name: teams
        description: "NFL team information"
        identifier: "teams/dt=*/*.parquet"
```

**File: `dbt/ff_analytics/models/sources/src_sheets.yml`** (create if doesn't exist)

```yaml
version: 2

sources:
  - name: sheets
    description: "Commissioner league data from Google Sheets"
    freshness:
      warn_after: {count: 1, period: day}
      error_after: {count: 7, period: day}
    loaded_at_field: dt

    tables:
      - name: roster
        description: "League roster data"
        identifier: "roster/dt=*/*.parquet"
        meta:
          external_location: "data/raw/sheets/roster/dt=*/*.parquet"

      - name: transactions
        description: "League transactions (trades, waivers, etc.)"
        identifier: "transactions/dt=*/*.parquet"
        meta:
          external_location: "data/raw/sheets/transactions/dt=*/*.parquet"

      - name: picks
        description: "Draft pick ownership"
        identifier: "picks/dt=*/*.parquet"
        meta:
          external_location: "data/raw/sheets/picks/dt=*/*.parquet"
```

**File: `dbt/ff_analytics/models/sources/src_sleeper.yml`** (create if doesn't exist)

```yaml
version: 2

sources:
  - name: sleeper
    description: "Sleeper league platform data integration"
    freshness:
      warn_after: {count: 1, period: day}
      error_after: {count: 7, period: day}
    loaded_at_field: dt

    tables:
      - name: league_data
        description: "League rosters, transactions, and settings"
        identifier: "league_data/dt=*/*.parquet"
        meta:
          external_location: "data/raw/sleeper/league_data/dt=*/*.parquet"
```

**Benefits** (from plan lines 210-213):

- Pre-dbt safety net catches stale data before model execution
- Different thresholds per source reflect realistic update expectations
- CI failures surface freshness issues immediately

## Testing

1. **Test nflverse freshness**:

   ```bash
   cd dbt/ff_analytics
   uv run dbt source freshness --select source:nflverse
   ```

2. **Test sheets freshness**:

   ```bash
   uv run dbt source freshness --select source:sheets
   ```

3. **Test sleeper freshness**:

   ```bash
   uv run dbt source freshness --select source:sleeper
   ```

4. **Test all freshness**:

   ```bash
   uv run dbt source freshness
   ```

5. **Expected output format**:

   ```
   Running with dbt=...

   source: nflverse
     freshness of nflverse.weekly: PASS (0:01:30)
     freshness of nflverse.snap_counts: PASS (0:01:30)
     ...

   source: sheets
     freshness of sheets.roster: PASS (0:00:15)
     ...

   source: sleeper
     freshness of sleeper.league_data: PASS (0:00:10)
     ...
   ```

6. **Test failure scenario** (optional):

   ```bash
   # Temporarily update YAML to very short threshold (e.g., 1 minute)
   # Should trigger warning/error if data is older
   # Restore original thresholds after test
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Design Decision #5 (lines 181-213)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 2 Freshness (lines 146-162)
- Source YAML examples: Plan lines 195-208
