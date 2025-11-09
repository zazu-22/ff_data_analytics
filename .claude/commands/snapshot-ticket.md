# Execute Snapshot Governance Ticket: $ARGUMENTS

You are working on the **Multi-Source Snapshot Governance** implementation epic for the FF Analytics project.

## Epic Context

**Objective**: Fix all 13 staging models that currently use `dt=*` wildcard patterns, causing duplicate row issues (2,088 total duplicates across multiple models). Replace hardcoded/wildcard snapshot selection with a flexible macro-based approach.

**Current Status**: Phase 1 (Foundation) — 16 tickets covering macro creation + 13 staging model updates

## Your Task

Execute ticket **$ARGUMENTS** following the implementation plan.

## Key Documentation

**Read these files in order**:

1. **Ticket file** (your primary instructions):

   ```
   docs/implementation/multi_source_snapshot_governance/tickets/$ARGUMENTS*.md
   ```

2. **Epic overview** (for context if needed):

   ```
   docs/implementation/multi_source_snapshot_governance/2025-11-07_README_v_2_0.md
   ```

3. **Implementation plan** (for design decisions):
   ```
   docs/implementation/multi_source_snapshot_governance/2025-11-07_plan_v_2_0.md
   ```

## Execution Guidelines

### Before You Start

- [ ] Read the ticket file completely
- [ ] Understand dependencies (check if P1-001 macro is required)
- [ ] Review the model file mentioned in the ticket
- [ ] Understand the expected impact (duplicate fixes, downstream effects)

### Implementation Steps

Follow the ticket's **Tasks** section exactly. Typical workflow:

1. Locate the staging model SQL file
2. Find the `read_parquet()` with `dt=*` pattern
3. Replace with `snapshot_selection_strategy` macro call
4. Use correct strategy (`latest_only` or `baseline_plus_latest`)
5. Test compilation: `make dbt-run --select <model>`
6. Verify row counts and snapshot filtering
7. Run related tests to verify duplicate fixes

### Testing Requirements

**Minimum tests** (from ticket's Testing section):

- [ ] Compilation test passes
- [ ] Execution test passes
- [ ] Row count verification (should match expected)
- [ ] Snapshot count = 1 for `latest_only` models
- [ ] Duplicate tests pass (if applicable)

**For high-priority tickets** (P1-013, P1-016):

- [ ] Run full test suite: `make dbt-test`
- [ ] Verify duplicate count reduction as documented
- [ ] Check downstream model impacts

## After Completion

### 1. Update Ticket Tracking

**File**: `docs/implementation/multi_source_snapshot_governance/tickets/00-OVERVIEW.md`

Mark ticket status:

```markdown
- [x] **$ARGUMENTS** — <ticket description>
```

Update progress summary:

```markdown
**Completed**: X/47 (X%)
**Remaining**: Y/47
```

### 2. Update Tasks Checklist

**File**: `docs/implementation/multi_source_snapshot_governance/2025-11-07_tasks_checklist_v_2_0.md`

Find the corresponding task in Phase 1 "Staging Model Updates" section and mark sub-tasks complete:

```markdown
- [x] Update `stg_<source>__<model>`:
  - [x] Replace dt=\* with macro call
  - [x] Test compilation and execution
  - [x] Verify duplicate fix (if applicable)
```

### 3. Update Ticket Status

**File**: `docs/implementation/multi_source_snapshot_governance/tickets/$ARGUMENTS*.md` (the ticket you just completed)

Confirm that you completed all tasks in the ticket checklist, and mark them as complete, if so.

If the ticket has a **Completion Notes** or **Results** section, add:

- Implementation date
- Test results summary
- Any notable findings or deviations from plan

If no such section exists, add one at the end:

```markdown
## Completion Notes

**Implemented**: YYYY-MM-DD
**Tests**: All passing
**Impact**: <duplicate reduction or other measurable outcome>
```

Then update the ticket's **Status** field at the top of the file, depending on the completion status (e.g. COMPLETE, IN PROGRESS, BLOCKED):

```markdown
**Status**: COMPLETE
```

### 4. Document Results

**In your final response to the user**, provide:

1. **Summary**: What was changed (file path, line numbers)
2. **Verification**: Test results showing success
3. **Impact**: Duplicate reduction (before → after counts)
4. **Next steps**: Recommended next ticket or any blockers discovered

### 5. Commit Changes

Create a commit with this format:

```
feat(snapshot): implement $ARGUMENTS - <model_name>

- Replace dt=* pattern with snapshot_selection_strategy macro
- Use <strategy> strategy for <reasoning>
- Fixes: <duplicate_count> duplicates in <downstream_model> (if applicable)

Testing:
- Compilation: PASS
- Execution: PASS
- Row count: <count> rows from latest snapshot
- Duplicate tests: PASS (was <before>, now <after>)

Refs: docs/implementation/multi_source_snapshot_governance/tickets/$ARGUMENTS*.md
```

## Important Notes

- **Do not skip testing** — Each ticket has specific verification steps
- **Do not batch tickets** — Complete one ticket fully before moving to next
- **Check dependencies** — P1-001 (macro) must be done before model updates
- **Verify impact** — High-priority tickets should eliminate specific duplicate counts
- **Ask questions** — If ticket is unclear or you encounter blockers, ask user

## Common Issues

**Macro not found**: If `snapshot_selection_strategy` is undefined, ticket P1-001 hasn't been completed yet.

**Wrong strategy**:

- NFLverse uses `baseline_plus_latest` (historical continuity)
- All other sources use `latest_only` (current state only)

**Path construction**: Use `var("external_root", "data/raw") ~ '/path/to/data'` for path concatenation in Jinja.

**Testing failures**: If tests fail after implementation, review the ticket's "Impact" section to understand expected behavior.

---

**Ready to begin ticket $ARGUMENTS!**
