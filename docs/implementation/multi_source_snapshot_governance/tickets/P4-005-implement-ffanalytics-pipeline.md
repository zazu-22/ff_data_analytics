# Ticket P4-005: Implement ffanalytics_pipeline Flow

**Phase**: 4 - Orchestration\
**Estimated Effort**: Medium (3 hours)\
**Dependencies**: P4-001

## Objective

Implement Prefect flow for FFAnalytics projections with governance integration (projection reasonableness checks, min/max/sum validations).

## Context

FFAnalytics projections come from R package. Governance ensures projections are statistically reasonable (no negative values, totals within expected ranges).

## Tasks

- [ ] Create `src/flows/ffanalytics_pipeline.py`
- [ ] Define flow: Run R projections → Export Parquet → Manifest
- [ ] Add governance: Projection reasonableness checks (min/max/sum validations)
- [ ] Test locally

## Acceptance Criteria

- [ ] Flow runs R projections successfully
- [ ] Reasonableness checks catch invalid projections
- [ ] Projections compared to historical baselines
- [ ] Flow testable locally

## Implementation Notes

**Governance Checks**:

- No negative projections (pass_yds, rush_yds, etc. >= 0)
- Sum validations (team totals reasonable, e.g., 32 teams * ~400 pass yards avg)
- Outlier detection (flag players with projections >3 std devs from position mean)

**R Integration**: Call `scripts/R/run_projections.R` from Python subprocess

## Testing

```bash
uv run python src/flows/ffanalytics_pipeline.py
```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 4 FFAnalytics (lines 484-492)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 4 FFAnalytics (lines 320-330)
