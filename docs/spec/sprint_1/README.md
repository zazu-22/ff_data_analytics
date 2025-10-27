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

### Phase 1: Critical Path for Wednesday FASA (0-24 hours)

| Task | File | Priority | Duration | Status |
|------|------|----------|----------|--------|
| 1.1 | [01_task_cap_space_foundation.md](./01_task_cap_space_foundation.md) | CRITICAL | 4h | ✅ Complete |
| 1.2 | [02_task_sleeper_production_integration.md](./02_task_sleeper_production_integration.md) | CRITICAL | 8h | ✅ Complete |
| 1.3 | [03_task_fasa_target_mart.md](./03_task_fasa_target_mart.md) | CRITICAL | 8h | ✅ Complete |
| 1.4 | [04_task_fasa_strategy_notebook.md](./04_task_fasa_strategy_notebook.md) | CRITICAL | 4h | ⬜ Not Started |

**Milestone:** FASA notebook ready for Wednesday bids (24 hours before deadline)

### Phase 2: Trade Intelligence (24-48 hours)

| Task | File | Priority | Duration | Status |
|------|------|----------|----------|--------|
| 2.1 | [05_task_baseline_valuation_model.md](./05_task_baseline_valuation_model.md) | HIGH | 8h | ⬜ Not Started |
| 2.2 | [06_task_trade_target_marts.md](./06_task_trade_target_marts.md) | HIGH | 8h | ⬜ Not Started |
| 2.3 | [07_task_trade_analysis_notebook.md](./07_task_trade_analysis_notebook.md) | MEDIUM | 4h | ⬜ Not Started |
| 2.4 | [08_task_historical_backfill.md](./08_task_historical_backfill.md) | MEDIUM | 8h (background) | ⬜ Not Started |

**Milestone:** Trade analysis toolkit operational

### Phase 3: Automation & Production (48-60 hours)

| Task | File | Priority | Duration | Status |
|------|------|----------|----------|--------|
| 3.1 | [09_task_github_actions_workflows.md](./09_task_github_actions_workflows.md) | HIGH | 6h | ⬜ Not Started |
| 3.2 | [10_task_documentation_polish.md](./10_task_documentation_polish.md) | MEDIUM | 6h | ⬜ Not Started |

**Milestone:** Daily automated refreshes operational

______________________________________________________________________

## Task Execution Guidelines

### For Human Developers

1. **Read the task file** - Contains all context, code, and validation steps
1. **Check dependencies** - Ensure prerequisite tasks are complete
1. **Implement the task** - Follow the technical specifications
1. **Validate** - Run the validation commands in the task file
1. **Commit** - Use the suggested commit message
1. **Update status** - Mark task as complete in this README and in `00_SPRINT_PLAN.md`

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
Task 1.1 (Cap Space)
  ⬇
Task 1.2 (Sleeper) ──────┐
  ⬇                       ⬇
Task 1.3 (FASA Mart) ←────┘
  ⬇
Task 1.4 (FASA Notebook)
  ⬇
✅ Wednesday FASA Ready

Task 2.1 (Valuation Model) ──┐
  ⬇                           ⬇
Task 2.2 (Trade Marts) ←──────┘
  ⬇
Task 2.3 (Trade Notebook)
  ⬇
✅ Trade Analysis Ready

Task 2.4 (Backfill) [runs in parallel, not blocking]

Task 3.1 (GitHub Actions) ──┐
  ⬇                          ⬇
Task 3.2 (Documentation) ←───┘
  ⬇
✅ Production Ready
```

**Key:**

- Arrows show hard dependencies (must wait for completion)
- Task 2.4 can run in background while other tasks proceed
- Task 1.1 is optional for Task 1.2 (helpful but not blocking)

______________________________________________________________________

## Progress Tracking

Update task status here and in `00_SPRINT_PLAN.md`:

**Legend:**

- ⬜ Not Started
- 🟦 In Progress
- ✅ Complete
- ❌ Blocked

### Phase 1 Progress (Critical: Must complete in 24 hours)

- ✅ Task 1.1: Cap Space Foundation
- ✅ Task 1.2: Sleeper Production Integration
- ✅ Task 1.3: FASA Target Mart
- ⬜ Task 1.4: FASA Strategy Notebook

### Phase 2 Progress

- ⬜ Task 2.1: Baseline Valuation Model
- ⬜ Task 2.2: Trade Target Marts
- ⬜ Task 2.3: Trade Analysis Notebook
- ⬜ Task 2.4: Historical Backfill

### Phase 3 Progress

- ⬜ Task 3.1: GitHub Actions Workflows
- ⬜ Task 3.2: Documentation & Polish

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
1. **dbt source freshness:** Not enabled yet (files, not tables)
1. **Player ID mapping:** Some players won't map (expected ~5% unmapped)
1. **Manual cap adjustments:** Reconciliation differences are expected
1. **Test failures:** Check logs carefully - often data quality issues, not code bugs

______________________________________________________________________

## Success Criteria

Sprint is complete when:

✅ **Primary Goal (Wednesday FASA):**

- [ ] FASA notebook runs without errors
- [ ] Top 10 RBs + 15 WRs + 8 TEs identified with bid recommendations
- [ ] Drop scenarios calculated
- [ ] Delivered by Tuesday 11:59 PM EST

✅ **Secondary Goal (Trade Analysis):**

- [ ] Trade analysis notebook runs without errors
- [ ] Buy-low and sell-high candidates identified
- [ ] Valuation model trained (MAE < 5.0, R² > 0.50)

✅ **Tertiary Goal (Production):**

- [ ] Daily automated refreshes operational
- [ ] All dbt tests passing (>95%)
- [ ] Documentation complete

______________________________________________________________________

## Communication

### Reporting Progress

When completing a task:

1. Update status in this README (⬜ → ✅)
1. Update status in `00_SPRINT_PLAN.md` Progress Tracking section
1. Commit with suggested commit message from task file

### Reporting Blockers

If blocked on a task:

1. Update status to ❌ Blocked
1. Document blocker in task file
1. Note dependencies or missing prerequisites
1. Escalate if critical path is affected

______________________________________________________________________

## Task File Template Structure

Each task file contains:

1. **Header** - Sprint, phase, duration, priority
1. **Objective** - What and why
1. **Context** - Current state, dependencies
1. **Files to Create/Modify** - Complete code listings
1. **Implementation Steps** - Step-by-step guide
1. **Success Criteria** - Definition of done
1. **Validation Commands** - Exact commands to test
1. **Commit Message** - Suggested conventional commit format
1. **Notes** - Gotchas, tips, future considerations

______________________________________________________________________

**Sprint Start:** 2025-10-27
**Sprint End:** 2025-10-29 (Wednesday 11:59 PM EST)
**Next Review:** Post-FASA (2025-10-30)
