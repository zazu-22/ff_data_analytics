# Ticket P4-006: Implement sleeper_pipeline Flow

**Phase**: 4 - Orchestration\
**Estimated Effort**: Medium (3 hours)\
**Dependencies**: P4-001

## Objective

Implement Prefect flow for Sleeper league platform data with governance integration (transaction date ordering, roster size validations).

## Context

Sleeper provides league rosters and transactions. Governance ensures transaction chronology is correct and roster sizes are within league settings.

## Tasks

- [ ] Create `src/flows/sleeper_pipeline.py`
- [ ] Define flow: Fetch Sleeper API → Parse → Write Parquet → Manifest
- [ ] Add governance: Transaction date ordering, roster size validations
- [ ] Test locally

## Acceptance Criteria

- [ ] Flow fetches Sleeper league data successfully
- [ ] Transaction ordering validated
- [ ] Roster sizes within expected ranges
- [ ] Flow testable locally

## Implementation Notes

**Governance Checks**:

- Transaction dates monotonic (no future-dated or out-of-order transactions)
- Roster sizes match league settings (e.g., 25-30 players per team for dynasty)
- No duplicate transactions (same player, team, date)

**Datasets**: league_data (combined rosters + transactions)

## Testing

```bash
uv run python src/flows/sleeper_pipeline.py
```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 4 Sleeper (lines 494-502)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 4 Sleeper (lines 332-343)
