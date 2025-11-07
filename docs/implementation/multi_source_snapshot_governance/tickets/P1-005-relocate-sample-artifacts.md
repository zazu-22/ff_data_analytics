# Ticket P1-005: Archive Legacy Sample Artifacts

**Phase**: 1 - Foundation\
**Estimated Effort**: Medium (2-3 hours)\
**Dependencies**: None (can be done in parallel with other Phase 1 work)

## Objective

Archive legacy sample data from fully integrated sources (nflverse, sheets) to prevent accidental inclusion in production dbt models, while preserving the sample generation tool for future use with new data sources.

## Context

Sample data was created during early development for testing and exploration. Now that we have real production data for nflverse and sheets, these samples are no longer needed for active development but should be preserved for historical reference.

**Key Decision**: Rather than actively maintaining samples in `_samples/` directories, we're **archiving** old samples from fully integrated sources while keeping the sample generation tool available for new source exploration (ktc, sleeper, ffanalytics).

**Rationale**:

- nflverse and sheets are fully integrated with real production data
- Keeping old samples creates confusion and maintenance burden
- Archive preserves them for reference without risk of accidental use
- Sample tool remains useful for exploring new data sources

## Tasks

### Validate and Archive Legacy Samples (Fully Integrated Sources)

- [ ] Create archive directory: `data/_archived_samples/2025-11-07/`
- [ ] Create README in archive explaining what samples were and why archived
- [ ] For each sample candidate, verify it's actually a sample (not production data):
  - [ ] Check `_meta.json` if exists (look for row_count, dates)
  - [ ] Check row counts (samples typically < 1000 rows)
  - [ ] Check dates (dt=2024-01-01 is typical sample date)
  - [ ] List candidates: `find data/raw -name "dt=2024-01-01" -o -name "*.csv" | head -20`
- [ ] Archive nflverse samples (if validation confirms they're samples):
  - [ ] Move `data/raw/nflverse/weekly/dt=2024-01-01/` → `data/_archived_samples/2025-11-07/nflverse/weekly/`
  - [ ] Move any CSV/Parquet samples → archive
  - [ ] Document what was archived in archive README
- [ ] Archive sheets samples if any exist (after validation)
- [ ] Keep ktc, sleeper, ffanalytics samples in place (sources still in development)

### Preserve Sample Generation Tool

- [ ] Document in `tools/make_samples.py` docstring when to use samples
- [ ] Add note: "Use `_samples/` for new source exploration, archive when source is production-ready"
- [ ] Keep tool functional for new source exploration
- [ ] No code changes needed - tool already writes to subdirectories

### Update Test Fixtures (If Needed)

- [ ] Check if `tests/test_nflverse_samples_pk.py` references archived paths
- [ ] If yes, either:
  - [ ] Update to use production data paths, OR
  - [ ] Create small test fixtures in `tests/fixtures/` directory
- [ ] Run pytest to verify: `uv run pytest tests/test_nflverse_samples_pk.py -v`

### Document Archive Policy

- [ ] Add section to `docs/ops/snapshot_management_current_state.md` explaining sample archival
- [ ] Document when to archive samples (source fully integrated with production data)
- [ ] Document `_samples/` usage (for new source exploration only)

## Acceptance Criteria

- [ ] Legacy samples from nflverse and sheets archived (not in production paths)
- [ ] Archive README documents what was archived and why
- [ ] Sample generation tool preserved and documented
- [ ] Test fixtures updated and passing (or using production data)
- [ ] dbt compilation succeeds and doesn't read archived data
- [ ] Archive policy documented in ops docs
- [ ] NO production data accidentally archived (validation passed)

## Implementation Notes

**Archive Structure**:

```
data/_archived_samples/2025-11-07/
├── README.md  # What was archived and why
├── nflverse/
│   ├── weekly/
│   │   ├── dt=2024-01-01/  # Old sample data
│   │   ├── weekly.csv
│   │   └── weekly.parquet
│   └── snap_counts/
│       └── ...
└── sheets/
    └── ...
```

**Archive README Template**:

```markdown
# Archived Samples - November 7, 2025

## Why Archived

These samples were created during early development (2024-early 2025) for:
- Testing data pipeline infrastructure
- Validating dbt models during development
- Exploring data structure before production loads

They are no longer needed because:
- nflverse: Fully integrated with real production data (2020-2025 seasons)
- sheets: Fully integrated with Commissioner league data

## What Was Archived

- nflverse samples (dt=2024-01-01): ~500 rows, sample player stats
- [List other archived samples]

## Validation

All archived files were validated as samples:
- Row counts < 1000 (production data has 50K+ rows)
- Dates are 2024-01-01 (known sample date, not real snapshot)
- _meta.json confirms sample data where present

NO production data was archived.
```

**Validation Safety Check** (critical before archiving):

```bash
# Check if file is actually a sample
check_if_sample() {
  local path=$1

  # Check row count (samples are small)
  if [ -f "$path/_meta.json" ]; then
    row_count=$(jq '.row_count' "$path/_meta.json")
    if [ "$row_count" -gt 1000 ]; then
      echo "WARNING: High row count ($row_count) - might be production data!"
      return 1
    fi
  fi

  # Check date (2024-01-01 is typical sample date)
  if [[ "$path" =~ dt=2024-01-01 ]]; then
    echo "Sample date pattern detected (dt=2024-01-01)"
    return 0
  fi

  echo "MANUAL REVIEW REQUIRED for: $path"
  return 2
}
```

**Files to Move** (example for nflverse):

```bash
# Before
data/raw/nflverse/
├── weekly/
│   ├── dt=2024-01-01/  # SAMPLE DATA
│   ├── dt=2025-10-01/  # PRODUCTION
│   ├── dt=2025-10-27/  # PRODUCTION
│   ├── weekly.csv      # SAMPLE DATA
│   └── weekly.parquet  # SAMPLE DATA

# After
data/raw/nflverse/
├── _samples/
│   ├── weekly/
│   │   └── dt=2024-01-01/
│   ├── weekly.csv
│   └── weekly.parquet
├── weekly/
│   ├── dt=2025-10-01/  # PRODUCTION
│   └── dt=2025-10-27/  # PRODUCTION
```

**Update tools/make_samples.py**:

Add a `samples: bool = True` parameter to the output path logic:

```python
def get_output_path(source, dataset, dt, samples=True):
    if samples:
        return f"data/raw/{source}/_samples/{dataset}/dt={dt}/"
    else:
        return f"data/raw/{source}/{dataset}/dt={dt}/"
```

## Testing

1. **Verify dbt doesn't read samples**:

   ```bash
   cd dbt/ff_analytics
   uv run dbt compile --select stg_nflverse__player_stats
   # Check compiled SQL - should not reference _samples paths
   ```

2. **Run Python tests**:

   ```bash
   uv run pytest tests/test_nflverse_samples_pk.py -v
   ```

3. **Test sample generator**:

   ```bash
   uv run python tools/make_samples.py nflverse --datasets weekly --seasons 2024 --out ./samples
   # Verify output goes to _samples/ directory
   ```

4. **Manual verification**:

   ```bash
   ls -R data/raw/nflverse/_samples/
   # Should show moved sample files

   ls -R data/raw/nflverse/weekly/dt=2024-01-01/
   # Should not exist (or be empty)
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Design Decision #2 (lines 91-105)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 1 Sample Relocation (lines 55-63)
- Tool: `tools/make_samples.py`
- Tests: `tests/test_nflverse_samples_pk.py`
