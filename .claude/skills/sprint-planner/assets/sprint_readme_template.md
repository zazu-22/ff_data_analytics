# {SPRINT_NAME}: {SPRINT_TITLE}

**Duration:** {DURATION} (ends {END_DATE})
**Status:** {STATUS_EMOJI} {STATUS_TEXT}
**Primary Goal:** {PRIMARY_GOAL}

______________________________________________________________________

## Sprint Overview

See **[00_SPRINT_PLAN.md](./00_SPRINT_PLAN.md)** for complete sprint details, context, and architecture.

This folder contains **atomic, executable tasks** designed for LLM coding agents. Each task is:

- ✅ Standalone (contains all necessary context)
- ✅ Committable (can be committed independently)
- ✅ Validatable (includes test commands and success criteria)

______________________________________________________________________

## Task Index

### Phase 1: {PHASE_1_NAME} ({PHASE_1_HOURS})

| Task | File | Priority | Duration | Status |
|------|------|----------|----------|--------|
| {TASK_ID} | [{TASK_FILE}](./{TASK_FILE}) | {PRIORITY} | {DURATION} | {STATUS} |

**Milestone:** {PHASE_1_MILESTONE}

### Phase 2: {PHASE_2_NAME} ({PHASE_2_HOURS})

| Task | File | Priority | Duration | Status |
|------|------|----------|----------|--------|
| {TASK_ID} | [{TASK_FILE}](./{TASK_FILE}) | {PRIORITY} | {DURATION} | {STATUS} |

**Milestone:** {PHASE_2_MILESTONE}

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
Execute {SPRINT_NAME} Task [NUMBER]: [TASK NAME]

Please read docs/spec/{sprint_directory}/[TASK_FILE].md and implement the task completely.
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
{ASCII diagram showing task dependencies}
```

**Key:**

- Arrows show hard dependencies (must wait for completion)
- {Notes about parallel or independent tasks}

______________________________________________________________________

## Progress Tracking

Update task status here and in `00_SPRINT_PLAN.md`:

**Legend:**

- ⬜ Not Started
- 🟦 In Progress
- ✅ Complete
- ❌ Blocked

### Phase 1 Progress

- {STATUS} Task {ID}: {NAME}

### Phase 2 Progress

- {STATUS} Task {ID}: {NAME}

______________________________________________________________________

## Quick Reference

### Environment Variables Needed

```bash
{List of environment variables required for this sprint}
```

### Common Validation Commands

```bash
{Common commands used throughout the sprint}
```

### Common Gotchas

1. **{Gotcha 1}:** {Description}
2. **{Gotcha 2}:** {Description}

______________________________________________________________________

## Success Criteria

Sprint is complete when:

✅ **Primary Goal:**

- [ ] {Criterion 1}
- [ ] {Criterion 2}

✅ **Secondary Goal:**

- [ ] {Criterion 1}
- [ ] {Criterion 2}

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

**Sprint Start:** {START_DATE}
**Sprint End:** {END_DATE}
**Next Review:** {REVIEW_DATE}
