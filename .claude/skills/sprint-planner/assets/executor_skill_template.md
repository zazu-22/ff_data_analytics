---
name: {sprint-name}-executor
description: Execute {SPRINT_NAME} tasks for {brief description of sprint goals}. This skill should be used when the user requests execution of any {SPRINT_NAME} task (Tasks {FIRST_TASK} through {LAST_TASK}), including {list key task areas}. Each task is atomic, standalone, and designed for independent execution with built-in validation.
---

# {SPRINT_NAME} Executor

Execute {SPRINT_NAME} tasks for {project description}. This skill provides structured, atomic task execution with validation and progress tracking.

## When to Use This Skill

Use this skill proactively when:

- User requests execution of any {SPRINT_NAME} task (e.g., "Execute Task {X.Y}", "Start {SPRINT_NAME} Task {X.Y}")
- User asks to work on {list sprint-specific work areas}
- User references {sprint_directory} documentation or task files
- User wants to continue sprint work after a break

## Sprint Overview

**Sprint Goal:** {Primary sprint goal and deadline if applicable}

**Sprint Structure:**

- **Phase 1:** {Phase 1 description}
  - Tasks {X.Y}-{X.Z}: {List task names}
- **Phase 2:** {Phase 2 description}
  - Tasks {X.Y}-{X.Z}: {List task names}
- **Phase 3:** {Phase 3 description} (if applicable)
  - Tasks {X.Y}-{X.Z}: {List task names}

## Task Execution Workflow

When user requests task execution:

1. **Identify the task** - Determine which task from user request

2. **Load task file** - Read the corresponding task file from `references/`:
   - Task {X.Y}: `references/{XX}_task_{name}.md`
   - {List all tasks}

3. **Check dependencies** - Review the "Dependencies" section in the task file
   - Verify prerequisite tasks are complete
   - If blocked, inform user and suggest completing prerequisites first

4. **Implement the task** - Follow the task file's implementation steps:
   - Create/modify all files listed in "Files to Create/Modify" section
   - Use exact code templates and SQL from task file
   - Follow step-by-step implementation guide
   - For tasks that reference `00_SPRINT_PLAN.md`: Load `references/00_SPRINT_PLAN.md` and extract the full code from the specified line ranges

5. **Validate the implementation** - Run all validation commands from task file:
   - Execute validation bash commands exactly as written
   - Verify all success criteria are met
   - Check code quality: `make lint`, `make typecheck`, `make sqlcheck` (as applicable)
   - Run tests: {project-specific test commands}

6. **Report results** - Communicate clearly to user:
   - ✅ What was implemented
   - ✅ Validation results (pass/fail)
   - ⚠️ Any issues or warnings
   - ❌ Blockers (if any)
   - 📝 Next recommended task (if applicable)

7. **Commit changes** - Use the suggested commit message from task file:
   - Copy exact commit message from "Commit Message" section
   - Ensure conventional commit format (feat:/docs:/etc.)
   - Reference task number: "Resolves: {SPRINT_NAME} Task {X.Y}"

8. **Update progress tracking** - After successful commit:
   - Mark task complete in `references/README.md` (⬜ → ✅)
   - Update `references/00_SPRINT_PLAN.md` Progress Tracking section
   - Suggest next task if user wants to continue

## Task File Structure

Each task file contains these sections (use them in order):

1. **Objective** - What and why
2. **Context** - Current state, dependencies, why it matters
3. **Files to Create/Modify** - Complete code listings with templates
4. **Implementation Steps** - Step-by-step guide (follow exactly)
5. **Success Criteria** - Definition of done (validate against this)
6. **Validation Commands** - Exact bash commands to test
7. **Commit Message** - Suggested message (use exactly)
8. **Notes** - Gotchas, tips, future considerations

## Special Handling by Task Type

{Customize based on your sprint's task types. Examples:}

### Python Implementation Tasks

- Create modules in appropriate source directories
- Follow existing patterns from similar files
- Include type hints and docstrings
- Run code quality checks

### SQL/dbt Model Tasks

- Create models in appropriate dbt directories
- Always create both `.sql` and `.yml` files
- Include comprehensive tests in `.yml`
- Set required environment variables before dbt commands
- Validate with test and show commands

### Notebook Tasks

- Create in notebooks directory
- Include visualizations
- Test execution to ensure reproducibility
- Ensure no hardcoded paths

### Documentation Tasks

- Create in appropriate docs directories
- Include examples and code snippets
- Link from main README or relevant docs
- Follow markdown formatting standards

## Environment Setup

Before executing tasks, ensure:

```bash
{List required environment setup commands}
```

## Common Validation Patterns

{Provide common validation command patterns used throughout the sprint}

## Progress Reference

Check current sprint progress in `references/README.md` Task Index table.

Full sprint plan and technical specifications in `references/00_SPRINT_PLAN.md`.

## Key Success Factors

1. **Follow task files exactly** - They contain complete, tested specifications
2. **Validate thoroughly** - Run all validation commands, check all success criteria
3. **Check dependencies** - Don't skip prerequisite tasks
4. **Commit atomically** - One task = one commit with provided commit message
5. **Update tracking** - Mark tasks complete in README and sprint plan
6. **Report clearly** - Tell user what worked, what didn't, what's next

## Handling Issues

If validation fails:

1. Review error messages carefully
2. Check common gotchas (see `references/README.md`)
3. Re-read task file for missed details
4. Verify prerequisites completed
5. Report specific error to user with context

If blocked by dependencies:

1. Identify which prerequisite task is missing
2. Inform user: "Task {X.Y} requires Task {A.B} to be complete first"
3. Offer to execute prerequisite task or wait

## Task Dependencies Quick Reference

{Provide a simple text summary of task dependencies}

See `references/README.md` dependency diagram for full details.

## Output Format

When reporting task completion:

```text
✅ {SPRINT_NAME} Task {X.Y} Complete: {Task Name}

**Implemented:**
- {List of files created/modified}

**Validation Results:**
- ✅ All tests passing (X/X)
- ✅ Code quality checks passed
- ✅ Success criteria met

**Committed:**
- Commit message: {exact message from task file}
- Branch: {current branch}

**Next Steps:**
- Task {X.Z}: {Next task name} {priority level}
- [or] {SPRINT_NAME} Phase {X} complete! Ready for Phase {Y}
```

If issues encountered:

```text
⚠️ {SPRINT_NAME} Task {X.Y}: Partial Completion / Issues

**Completed:**
- {What worked}

**Issues:**
- ❌ {Specific error/failure}
- ⚠️ {Warnings or concerns}

**Validation Status:**
- ✅ {Passed checks}
- ❌ {Failed checks}

**Recommended Action:**
- {Specific next steps to resolve}
```
