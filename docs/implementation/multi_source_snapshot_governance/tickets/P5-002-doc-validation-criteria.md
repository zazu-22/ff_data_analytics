# Ticket P5-002: Document Validation Criteria and Comparison Process

**Phase**: 5 - CI Planning\
**Estimated Effort**: Small (2 hours)\
**Dependencies**: P5-001

## Objective

Document cut-over validation criteria with objective metrics and the comparison process for validating Prefect outputs match GitHub Actions.

## Context

This ticket is also partially complete from P3-006. It validates the validation criteria section and adds the automated comparison tool (`tools/compare_pipeline_outputs.py`) if missing.

## Tasks

- [ ] Review cut-over validation criteria (5 must-pass)
- [ ] Add objective metrics and measurement queries
- [ ] Document comparison process (automated + manual)
- [ ] Create `tools/compare_pipeline_outputs.py` (if doesn't exist)
- [ ] Test comparison tool with real data

## Acceptance Criteria

- [ ] 5 validation criteria documented with metrics
- [ ] Comparison process documented
- [ ] Automated comparison tool created
- [ ] Tool tested and working

## Implementation Notes

**Validation Criteria** (from plan):

1. Row Count Parity (±1% acceptable)
2. Manifest Quality (all fields populated)
3. Query Performance (±10% acceptable)
4. Freshness Tests (no failures 3+ days)
5. Team Approval (unanimous)

**Comparison Tool**: `tools/compare_pipeline_outputs.py`

- Compare manifests (row counts, metadata)
- Compare Parquet files (row counts, sample data)
- Output JSON report for CI

## Testing

```bash
uv run python tools/compare_pipeline_outputs.py \
    --gh-actions-dir data/raw \
    --prefect-dir data/raw_prefect \
    --output comparison_report.json
```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 5 Validation (lines 539-557)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 5 Validation (lines 428-443)
- Doc: `docs/ops/ci_transition_plan.md` (validation section)
