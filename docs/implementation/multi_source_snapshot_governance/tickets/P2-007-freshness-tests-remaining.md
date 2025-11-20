# Ticket P2-007: Add Freshness Tests (Weekly/Sporadic Sources)

**Phase**: 2 - Governance\
**Status**: CANCELLED (Replaced by P2-006B)\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: None (can work in parallel with P2-006)

______________________________________________________________________

## CANCELLATION NOTICE

**Status**: CANCELLED on 2025-11-20\
**Reason**: Same as P2-006 - dbt source freshness architecturally incompatible with external Parquet pattern.\
**Replacement**: P2-006B includes freshness thresholds for ALL sources (nflverse, sheets, sleeper, ffanalytics, ktc).\
**Note**: The per-source threshold configuration in P2-006B covers both frequently-updated (P2-006) and weekly/sporadic (P2-007) sources in a single implementation.

**See**: `P2-006B-add-freshness-validation.md` for the unified implementation.

______________________________________________________________________

## Original Objective (Preserved for Historical Context)

Add dbt source freshness tests for weekly/sporadically updated sources (ktc, ffanalytics) with appropriate warn/error thresholds based on their less frequent update cadence.

## Original Context

This ticket completes freshness test coverage by adding tests for the **weekly/sporadically updated sources**. These sources have different update patterns than the frequently updated sources (nflverse/sheets/sleeper in P2-006):

- **ffanalytics**: Weekly projection updates during season (2 day warn threshold)
- **ktc**: Less frequent, news-driven market valuation updates (5 day warn threshold)

These sources are grouped together because they share similar operational characteristics: less frequent updates that don't require daily monitoring.

## Tasks

### Add ktc Freshness Tests

- [ ] Create or update `dbt/ff_data_transform/models/sources/src_ktc.yml`
- [ ] Set `loaded_at_field: dt` at source level
- [ ] Configure freshness: warn_after 5 days, error_after 14 days
- [ ] Test with `dbt source freshness --select source:ktc`

### Add ffanalytics Freshness Tests

- [ ] Create or update `dbt/ff_data_transform/models/sources/src_ffanalytics.yml`
- [ ] Set `loaded_at_field: dt` at source level
- [ ] Configure freshness: warn_after 2 days, error_after 7 days
- [ ] Test with `dbt source freshness --select source:ffanalytics`

### Run Full Freshness Check

- [ ] Run `dbt source freshness` across all 5 sources
- [ ] Verify ktc and ffanalytics sources pass freshness checks
- [ ] Document expected update cadence for each source

## Acceptance Criteria

- [ ] ktc source has freshness tests configured
- [ ] ffanalytics source has freshness tests configured
- [ ] `dbt source freshness` passes for all 5 sources (combined with P2-006)
- [ ] Thresholds appropriate for weekly/sporadic update cadence

## Implementation Notes

**Freshness Thresholds** (grouped by frequency - weekly/sporadic):

| Source          | Warn After | Error After | Rationale                                |
| --------------- | ---------- | ----------- | ---------------------------------------- |
| **ffanalytics** | 2 days     | 7 days      | Weekly projection updates during season  |
| **ktc**         | 5 days     | 14 days     | Sporadic market valuations (news-driven) |

**Note**: Frequently updated sources (sheets, sleeper, nflverse) are covered in P2-006.

**File: `dbt/ff_data_transform/models/sources/src_ktc.yml`**

```yaml
version: 2

sources:
  - name: ktc
    description: "Keep Trade Cut dynasty valuations (1QB default)"
    freshness:
      warn_after: {count: 5, period: day}
      error_after: {count: 14, period: day}
    loaded_at_field: dt

    tables:
      - name: players
        description: "Dynasty player valuations"
        identifier: "players/dt=*/*.parquet"
        meta:
          external_location: "data/raw/ktc/players/dt=*/*.parquet"

      - name: picks
        description: "Draft pick valuations"
        identifier: "picks/dt=*/*.parquet"
        meta:
          external_location: "data/raw/ktc/picks/dt=*/*.parquet"
```

**File: `dbt/ff_data_transform/models/sources/src_ffanalytics.yml`**

```yaml
version: 2

sources:
  - name: ffanalytics
    description: "Fantasy projections from FFAnalytics R package"
    freshness:
      warn_after: {count: 2, period: day}
      error_after: {count: 7, period: day}
    loaded_at_field: dt

    tables:
      - name: projections
        description: "Fantasy football projections"
        identifier: "projections/dt=*/*.parquet"
        meta:
          external_location: "data/raw/ffanalytics/projections/dt=*/*.parquet"
```

**Rationale for Thresholds**:

- **ffanalytics**: Projections update weekly during season, but may lag slightly (2 day tolerance)
- **ktc**: Market valuations update sporadically based on news/trades, not on weekly schedule (5 day tolerance appropriate)

## Testing

1. **Test ktc freshness**:

   ```bash
   cd dbt/ff_data_transform
   uv run dbt source freshness --select source:ktc
   ```

2. **Test ffanalytics freshness**:

   ```bash
   uv run dbt source freshness --select source:ffanalytics
   ```

3. **Test all sources together**:

   ```bash
   uv run dbt source freshness
   ```

4. **Expected output format** (all 5 sources together):

   ```
   Running with dbt=...

   Completed with 5 sources:

   source: nflverse (from P2-006)
     freshness of nflverse.weekly: PASS
     freshness of nflverse.snap_counts: PASS
     ...

   source: sheets (from P2-006)
     freshness of sheets.roster: PASS
     ...

   source: sleeper (from P2-006)
     freshness of sleeper.league_data: PASS

   source: ktc (from P2-007)
     freshness of ktc.players: PASS
     freshness of ktc.picks: PASS

   source: ffanalytics (from P2-007)
     freshness of ffanalytics.projections: PASS

   Done. PASS=X WARN=0 ERROR=0 SKIP=0 TOTAL=X
   ```

5. **Integration test in CI**:

   ```yaml
   # In .github/workflows/data-pipeline.yml
   - name: Check Data Freshness
     run: |
       cd dbt/ff_data_transform
       uv run dbt source freshness
       # Fails workflow if any source shows ERROR status
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Design Decision #5 (lines 181-213)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 2 Freshness (lines 170-185)
- All 5 sources: Plan lines 23-28
