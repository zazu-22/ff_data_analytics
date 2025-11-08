# Task 3.1: GitHub Actions Workflows

**Sprint:** Sprint 1
**Phase:** Phase 3
**Duration:** 6h
**Priority:** HIGH

## Objective

Create 4 GitHub Actions workflows for automated data refreshes.

## Files to Create

1. `.github/workflows/nflverse_weekly.yml` - Mon 8am EST
2. `.github/workflows/projections_weekly.yml` - Tue 8am EST
3. `.github/workflows/league_data_daily.yml` - Daily 6am/6pm EST
4. `.github/workflows/backfill_historical.yml` - Manual trigger

**Full YAML:** See `00_SPRINT_PLAN.md` lines 1493-1579

**Key features:**

- Cron schedules
- Discord webhook notifications
- dbt run + test steps
- Environment variables from secrets

## Success Criteria

- ✅ All 4 workflows created
- ✅ Test with manual trigger
- ✅ Discord notifications work

## Validation

```bash
# Test locally first
make dbt-run
make dbt-test

# Commit and trigger via GitHub UI
git push
# Go to Actions tab → Run workflow
```

## Commit

```
feat: add GitHub Actions workflows for daily automation
Resolves: Sprint 1 Task 3.1
```
