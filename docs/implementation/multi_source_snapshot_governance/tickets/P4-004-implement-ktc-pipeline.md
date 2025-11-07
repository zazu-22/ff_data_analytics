# Ticket P4-004: Implement ktc_pipeline Flow

**Phase**: 4 - Orchestration\
**Estimated Effort**: Medium (3-4 hours)\
**Dependencies**: P4-001

## Objective

Implement Prefect flow for KTC (Keep Trade Cut) dynasty valuations ingestion with governance integration (valuation range checks, player mapping validation).

## Context

KTC provides dynasty player and pick valuations (1QB default). Governance focuses on ensuring valuations are reasonable and players map to our crosswalk.

## Tasks

- [ ] Create `src/flows/ktc_pipeline.py`
- [ ] Define flow with tasks: Fetch KTC API → Parse → Write Parquet → Manifest
- [ ] Add governance: Valuation range checks, player mapping validation
- [ ] Test locally

## Acceptance Criteria

- [ ] Flow fetches KTC data successfully
- [ ] Valuation range checks catch anomalies
- [ ] Player mapping validation reports coverage
- [ ] Flow testable locally

## Implementation Notes

**Key Governance Checks**:

- Valuation ranges: Min 0, Max 10000 (sanity check)
- Player mapping: >90% of KTC players should map to dim_player_id_xref
- Missing players: Report top 10 unmapped for investigation

**Datasets**: players, picks

## Testing

```bash
uv run python src/flows/ktc_pipeline.py
```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 4 KTC Flow (lines 474-482)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 4 KTC (lines 307-318)
