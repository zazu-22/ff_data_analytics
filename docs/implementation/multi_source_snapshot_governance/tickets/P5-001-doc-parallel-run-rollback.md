# Ticket P5-001: Document Parallel Run and Rollback Strategy

**Phase**: 5 - CI Planning\
**Estimated Effort**: Medium (2-3 hours)\
**Dependencies**: P3-006 (ci_transition_plan doc created), P4-002 through P4-006 (flows implemented)

## Objective

Document the parallel run strategy with timeline and rollback procedures for GitHub Actions → Prefect transition.

## Context

This ticket is partially complete — P3-006 created the full `ci_transition_plan.md`. This ticket validates that document and adds any missing parallel run details or rollback scenarios based on actual Prefect flow implementation.

## Tasks

- [ ] Review `docs/ops/ci_transition_plan.md` for completeness
- [ ] Add parallel run timeline (Weeks 1-4+)
- [ ] Document rollback procedures for each failure scenario
- [ ] Add validation queries and comparison scripts
- [ ] Test rollback procedure (dry run)

## Acceptance Criteria

- [ ] Parallel run strategy documented with clear timeline
- [ ] Rollback procedures cover major failure scenarios
- [ ] Decision tree for cut-over approval included
- [ ] Validation queries provided and tested

## Implementation Notes

**Document**: `docs/ops/ci_transition_plan.md` (already created in P3-006)

**Key Sections to Verify**:

1. Parallel Run Strategy (Weeks 1-4+)
2. Cut-Over Validation Criteria (5 must-pass criteria)
3. Rollback Procedures (4 scenarios)
4. Comparison Process (automated + manual)
5. Decision Framework (flowchart)

**Additional Details** (if missing):

- Automated comparison script (`tools/compare_pipeline_outputs.py`)
- Rollback scripts for each scenario
- Post-cut-over monitoring checklist

## Testing

1. **Dry run rollback procedure**: Simulate failure, execute rollback steps
2. **Validate comparison queries**: Test SQL queries against actual data
3. **Review with team**: Get stakeholder feedback on plan

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 5 (lines 517-573)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 5 Parallel Run (lines 375-404)
- Doc: `docs/ops/ci_transition_plan.md` (created in P3-006)
