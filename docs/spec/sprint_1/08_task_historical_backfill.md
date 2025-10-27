# Task 2.4: Historical Backfill

**Sprint:** Sprint 1
**Phase:** Phase 2
**Duration:** 8h (background)
**Priority:** MEDIUM

## Objective

Backfill nflverse data 2012-2024 for aging curve analysis.

## Command

```bash
# Run in tmux/screen (takes hours)
for year in {2012..2024}; do
  uv run python scripts/ingest/load_nflverse.py \
    --seasons $year \
    --datasets weekly,snap_counts,ff_opportunity \
    --out data/raw/nflverse
done

# After complete, refresh dbt
export EXTERNAL_ROOT="$PWD/data/raw"
make dbt-run --full-refresh
```

## Success Criteria

- ✅ 2012-2024 data loaded
- ✅ `fact_player_stats` contains historical data

## Commit

```
feat: backfill historical nflverse data (2012-2024)
Resolves: Sprint 1 Task 2.4
```
