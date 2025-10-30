# Sprint 1: FASA Optimization & Trade Intelligence

**Duration:** 60 hours (ends Wednesday 2025-10-29 11:59 PM EST)
**Status:** 🟡 In Progress
**Primary Goal:** Deliver actionable FASA bidding strategy for Week 9 + trade analysis infrastructure

______________________________________________________________________

## Sprint Overview

See **[00_SPRINT_PLAN.md](./00_SPRINT_PLAN.md)** for complete sprint details, context, and architecture.

This folder contains **atomic, executable tasks** designed for LLM coding agents. Each task is:

- ✅ Standalone (contains all necessary context)
- ✅ Committable (can be committed independently)
- ✅ Validatable (includes test commands and success criteria)

______________________________________________________________________

## Task Index

### Phase 1: Foundation (FASA Critical Path)

| Task | File                                                                                     | Priority | Duration | Status      |
| ---- | ---------------------------------------------------------------------------------------- | -------- | -------- | ----------- |
| 1.1  | [01_task_cap_space_foundation.md](./01_task_cap_space_foundation.md)                     | CRITICAL | 4h       | ✅ Complete |
| 1.2  | [02_task_sleeper_production_integration.md](./02_task_sleeper_production_integration.md) | CRITICAL | 8h       | ✅ Complete |
| 1.3  | [03_task_fasa_target_mart.md](./03_task_fasa_target_mart.md)                             | CRITICAL | 8h       | ✅ Complete |

**Milestone:** Basic FASA infrastructure ready

### Phase 2: FASA Intelligence Enhancements

| Task     | File                                                                     | Priority | Duration | Status         |
| -------- | ------------------------------------------------------------------------ | -------- | -------- | -------------- |
| 2.4 (11) | [11_task_fa_acquisition_history.md](./11_task_fa_acquisition_history.md) | HIGH     | 6h       | ⬜ Not Started |
| 2.5 (12) | [12_task_league_roster_depth.md](./12_task_league_roster_depth.md)       | HIGH     | 4h       | ⬜ Not Started |
| 2.6 (13) | [13_task_enhance_fasa_targets.md](./13_task_enhance_fasa_targets.md)     | HIGH     | 4h       | ⬜ Not Started |
| 1.4      | [04_task_fasa_strategy_notebook.md](./04_task_fasa_strategy_notebook.md) | CRITICAL | 4h       | 🟦 In Progress |

**Milestone:** Enhanced FASA notebook with market intelligence ready

### Phase 3: Trade Intelligence (Deferred)

| Task | File                                                                         | Priority | Duration | Status                                                             |
| ---- | ---------------------------------------------------------------------------- | -------- | -------- | ------------------------------------------------------------------ |
| 2.1  | [05_task_historical_backfill.md](./05_task_historical_backfill.md)           | MEDIUM   | 8h       | 🟡 Partial (2020-2025 complete, 2012-2019 deferred to later phase) |
| 2.2  | [06_task_baseline_valuation_model.md](./06_task_baseline_valuation_model.md) | MEDIUM   | 8h       | ❌ Blocked by 2.1                                                  |
| 2.3  | [07_task_trade_target_marts.md](./07_task_trade_target_marts.md)             | MEDIUM   | 8h       | ❌ Blocked by 2.2                                                  |
| 2.4  | [08_task_trade_analysis_notebook.md](./08_task_trade_analysis_notebook.md)   | MEDIUM   | 4h       | ❌ Blocked by 2.3                                                  |

**Milestone:** Trade analysis toolkit (deferred to future sprint)

### Phase 4: Automation & Production (Future)

| Task | File                                                                         | Priority | Duration | Status         |
| ---- | ---------------------------------------------------------------------------- | -------- | -------- | -------------- |
| 3.1  | [09_task_github_actions_workflows.md](./09_task_github_actions_workflows.md) | LOW      | 6h       | ⬜ Not Started |
| 3.2  | [10_task_documentation_polish.md](./10_task_documentation_polish.md)         | LOW      | 6h       | ⬜ Not Started |

**Milestone:** Daily automated refreshes operational

______________________________________________________________________

## Task Execution Guidelines

### For Human Developers

1. **Read the task file** - Contains all context, code, and validation steps
2. **Check dependencies** - Ensure prerequisite tasks are complete
3. **Implement the task** - Follow the technical specifications
4. **Validate** - Run the validation commands in the task file
5. **Commit** - Use the suggested commit message
6. **Update status** - Mark task as complete in this README and in `00_SPRINT_PLAN.md`

### For LLM Coding Agents (Claude Code, etc.)

Each task file is optimized for LLM execution:

- ✅ **Complete context** - No need to search for additional files
- ✅ **Explicit instructions** - Step-by-step implementation guide
- ✅ **Code templates** - Copy-paste-ready code snippets
- ✅ **Validation commands** - Exact commands to verify success
- ✅ **Success criteria** - Clear definition of done

**Recommended prompt for Claude Code:**

```text
Execute Sprint 1 Task [NUMBER]: [TASK NAME]

Please read docs/spec/sprint_1/[TASK_FILE].md and implement the task completely.
Follow these steps:
1. Read the task file to understand the objective and context
2. Implement all code as specified in the technical specs
3. Run all validation commands to verify success
4. Report any issues or blockers
5. Confirm all success criteria are met

When complete, use the suggested commit message from the task file.
```

______________________________________________________________________

## Dependencies Between Tasks

```text
PHASE 1: Foundation
Task 1.1 (Cap Space)
  ⬇
Task 1.2 (Sleeper) ──────┐
  ⬇                       ⬇
Task 1.3 (FASA Mart) ←────┘
  ⬇
✅ Basic Infrastructure Ready

PHASE 2: FASA Enhancements
Task 1.3 (FASA Mart)
  ⬇
Task 11 (FA Acquisition History) ──┐
  ⬇                                  ⬇
Task 12 (League Roster Depth) ──────┤
  ⬇                                  ⬇
Task 13 (Enhance FASA Targets) ←────┘
  ⬇
Task 1.4 (FASA Notebook)
  ⬇
✅ Enhanced FASA Ready

PHASE 3: Trade Intelligence (DEFERRED)
Task 2.1 (Historical Backfill) ──┐ [PARTIAL - 2020-2025 complete]
  ⬇                               ⬇
Task 2.2 (Valuation Model) ←──────┘ [BLOCKED - needs 2012-2019 data]
  ⬇
Task 2.3 (Trade Marts)
  ⬇
Task 2.4 (Trade Notebook)
  ⬇
🔄 Trade Analysis (Future Sprint)

PHASE 4: Automation (FUTURE)
Task 3.1 (GitHub Actions) ──┐
  ⬇                          ⬇
Task 3.2 (Documentation) ←───┘
  ⬇
🔄 Production Ready (Future Sprint)
```

**Key:**

- Arrows show hard dependencies (must wait for completion)
- Tasks 11, 12, 13 can run in parallel after Task 1.3
- Task 2.1 partially complete (2020-2025), remainder deferred
- Phase 3 & 4 deferred to future sprints

______________________________________________________________________

## Progress Tracking

Update task status here and in `00_SPRINT_PLAN.md`:

**Legend:**

- ⬜ Not Started
- 🟦 In Progress
- ✅ Complete
- 🟡 Partial
- ❌ Blocked

### Phase 1: Foundation (COMPLETE ✅)

- ✅ Task 1.1: Cap Space Foundation
- ✅ Task 1.2: Sleeper Production Integration
- ✅ Task 1.3: FASA Target Mart (basic version)
- ✅ IDP Historical Data (2020-2025 defensive stats + snap counts) - *bonus infrastructure work*

### Phase 2: FASA Intelligence Enhancements (CURRENT FOCUS)

- ⬜ Task 11 (2.4): FA Acquisition History Analysis
- ⬜ Task 12 (2.5): League Roster Depth Analysis
- ⬜ Task 13 (2.6): Enhance FASA Targets with Market Intelligence
- 🟦 Task 1.4: FASA Strategy Notebook (in progress, awaiting enhancements)

### Phase 3: Trade Intelligence (DEFERRED)

- 🟡 Task 2.1: Historical Backfill (2020-2025 ✅, 2012-2019 deferred to future sprint)
- ❌ Task 2.2: Baseline Valuation Model (blocked - needs full 2012-2024 backfill)
- ❌ Task 2.3: Trade Target Marts (blocked by 2.2)
- ❌ Task 2.4: Trade Analysis Notebook (blocked by 2.3)

### Phase 4: Automation & Production (FUTURE)

- ⬜ Task 3.1: GitHub Actions Workflows (deferred)
- ⬜ Task 3.2: Documentation & Polish (deferred)

______________________________________________________________________

## Quick Reference

### Environment Variables Needed

```bash
export SLEEPER_LEAGUE_ID="1230330435511275520"
export EXTERNAL_ROOT="$PWD/data/raw"
export GOOGLE_APPLICATION_CREDENTIALS_JSON="..." # For sheets
```

### Common Validation Commands

```bash
# Run dbt models
make dbt-run --select [MODEL_NAME]

# Run dbt tests
make dbt-test --select [MODEL_NAME]

# Code quality
make lint
make sqlcheck
make typecheck

# Show dbt model output
dbt show --select [MODEL_NAME]
```

### Common Gotchas

1. **DuckDB path resolution:** Always set `EXTERNAL_ROOT` before running dbt
2. **dbt source freshness:** Not enabled yet (files, not tables)
3. **Player ID mapping:** Some players won't map (expected ~5% unmapped)
4. **Manual cap adjustments:** Reconciliation differences are expected
5. **Test failures:** Check logs carefully - often data quality issues, not code bugs

______________________________________________________________________

## Success Criteria

**Current Sprint Focus:**

✅ **Phase 1: Foundation (COMPLETE)**

- [x] Cap space data ingested and staged
- [x] Sleeper rosters loaded
- [x] Basic FASA targets mart created
- [x] IDP historical data loaded (2020-2025)

✅ **Phase 2: FASA Intelligence (IN PROGRESS)**

- [ ] FA acquisition history mart built (Task 11)
- [ ] League roster depth analysis complete (Task 12)
- [ ] FASA targets enhanced with market intelligence (Task 13)
- [ ] FASA notebook runs with enhanced recommendations (Task 1.4)
- [ ] Bid recommendations incorporate market data and league context

**Deferred to Future Sprints:**

⏸️ **Phase 3: Trade Intelligence**

- [ ] Full historical backfill (2012-2019) - *partially complete: 2020-2025 done*
- [ ] Valuation model trained
- [ ] Trade analysis notebook operational

⏸️ **Phase 4: Automation**

- [ ] Daily automated refreshes operational
- [ ] All dbt tests passing (>95%)
- [ ] Documentation complete

______________________________________________________________________

## Communication

### Reporting Progress

When completing a task:

1. Update status in this README (⬜ → ✅)
2. Update status in `00_SPRINT_PLAN.md` Progress Tracking section
3. Commit with suggested commit message from task file

### Reporting Blockers

If blocked on a task:

1. Update status to ❌ Blocked
2. Document blocker in task file
3. Note dependencies or missing prerequisites
4. Escalate if critical path is affected

______________________________________________________________________

## Task File Template Structure

Each task file contains:

1. **Header** - Sprint, phase, duration, priority
2. **Objective** - What and why
3. **Context** - Current state, dependencies
4. **Files to Create/Modify** - Complete code listings
5. **Implementation Steps** - Step-by-step guide
6. **Success Criteria** - Definition of done
7. **Validation Commands** - Exact commands to test
8. **Commit Message** - Suggested conventional commit format
9. **Notes** - Gotchas, tips, future considerations

______________________________________________________________________

**Sprint Start:** 2025-10-27
**Sprint End:** 2025-10-29 (Wednesday 11:59 PM EST)
**Next Review:** Post-FASA (2025-10-30)
