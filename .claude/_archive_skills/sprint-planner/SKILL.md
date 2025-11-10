---
name: sprint-planner
description: Design and structure development sprints with atomic, LLM-ready task files. This skill should be used when the user wants to plan a new development sprint, break down complex projects into executable tasks, or create a sprint execution framework. Produces sprint plans, atomic task specifications, and corresponding executor skills for LLM coding agents.
---

# Sprint Planner

Create structured, executable development sprints optimized for LLM coding agents. This skill guides the collaborative process of transforming project goals into atomic task specifications with complete context, validation commands, and execution skills.

## When to Use This Skill

Use this skill proactively when:

- User wants to plan a new development sprint or iteration
- User needs to break down a complex project into manageable tasks
- User mentions creating "task files" or "sprint documentation"
- User references creating an "executor skill" for a sprint
- User wants to structure work for LLM coding agent execution
- User is starting a new phase of work that would benefit from structured planning

## Sprint Planning Philosophy

The sprint planning approach used here follows these principles:

1. **Atomic Tasks** - Each task is standalone, committable, and validatable independently
2. **Complete Context** - Task files contain everything an LLM needs without external searches
3. **LLM-Optimized** - Designed specifically for coding agent execution with explicit instructions
4. **Validation-First** - Every task includes exact validation commands and success criteria
5. **Executor Skills** - Each sprint gets a dedicated skill for task execution

## Sprint Planning Workflow

Follow this five-step process to create a complete sprint:

### Step 1: Collaborative Sprint Planning

Work with the user to develop an overarching sprint plan. The sprint plan should include:

**Sprint Metadata:**

- Sprint name and duration
- Primary goal and success criteria
- Target milestones and deadlines

**Technical Architecture:**

- System context and current state
- Key components to build/modify
- Integration points and dependencies
- Data flows and transformations

**Task Breakdown:**

- Phases with milestones
- Individual tasks with objectives
- Dependencies between tasks
- Estimated durations and priorities

**Implementation Specifications:**

- For each major task, include complete technical specs
- SQL queries, Python code templates, API schemas
- File paths and directory structures
- Configuration and environment variables

**Ask clarifying questions:**

- "What are the success criteria for this sprint?"
- "Which tasks are on the critical path?"
- "What existing code/data can we build on?"
- "Are there any hard deadlines or dependencies?"
- "What should the task priorities be?"

**Output:** Create `00_SPRINT_PLAN.md` with comprehensive sprint details. See `references/example_sprint_plan.md` for structure.

### Step 2: Design Atomic Task Units

Break down the sprint plan into atomic, standalone task files. Each task should be:

- **Self-contained** - No need to read other files to understand context
- **Executable** - Complete code templates and step-by-step instructions
- **Validatable** - Exact commands to verify success
- **Committable** - Can be committed as a single, coherent unit

**Task Design Principles:**

- One task = one logical unit of work (e.g., "build X", "integrate Y")
- Include complete context: why it matters, current state, dependencies
- Provide full code templates, not just descriptions
- Specify exact validation commands with expected output
- Include suggested commit messages following project conventions
- Add notes about gotchas, future considerations, related tasks

**Determining Task Boundaries:**

- Can this be implemented and tested independently?
- Does it have clear success criteria?
- Is it small enough to complete in one focused session?
- Does it map to a single commit?

**For each task, define:**

- Objective and context
- Files to create/modify with complete code
- Implementation steps
- Success criteria
- Validation commands
- Commit message
- Notes and gotchas

Use `assets/task_template.md` as the structure for each task file.

### Step 3: Create Sprint Directory Structure

Create the sprint directory following this structure:

```
docs/spec/{sprint_directory}/
├── 00_SPRINT_PLAN.md              # Complete sprint plan and specifications
├── README.md                        # Sprint overview and task index
├── 01_task_{name}.md               # Task 1.1
├── 02_task_{name}.md               # Task 1.2
├── ...                              # Additional tasks
└── {NN}_task_{name}.md             # Task N.M
```

**Naming Conventions:**

- Sprint directory: `sprint_N` or descriptive name (e.g., `sprint_authentication`)
- Task files: `{NN}_task_{descriptive_name}.md` (zero-padded, snake_case)
- Use consistent numbering: 01, 02, ..., 10, 11 (not 1, 2, ..., 10, 11)

**Directory Location:**

- Project specs: `docs/spec/{sprint_directory}/`
- Or appropriate location based on project structure

### Step 4: Generate Task Files and README

Create all task files using the task template:

1. **For each task in the sprint:**
   - Copy `assets/task_template.md` structure
   - Fill in all sections with content from sprint plan
   - Include complete code templates extracted from sprint plan
   - Specify exact validation commands
   - Write clear success criteria

2. **Create sprint README:**
   - Copy `assets/sprint_readme_template.md` structure
   - Fill in sprint metadata and overview
   - Create task index table with all tasks
   - Include dependency diagram (ASCII art)
   - Document environment variables and common commands
   - Add progress tracking section

3. **Copy sprint plan:**
   - Move/copy the `00_SPRINT_PLAN.md` to sprint directory
   - Ensure all code/SQL is included in full
   - Link to task files where appropriate

**Quality Checklist:**

- [ ] Each task file is self-contained (no "see other file" references)
- [ ] All code templates are complete and copy-paste ready
- [ ] Validation commands are exact (not "run the tests")
- [ ] Dependencies are clearly marked in each task
- [ ] README task index matches all task files
- [ ] File numbering is consistent (01, 02, etc.)

### Step 5: Create Sprint Executor Skill

Create a dedicated skill for executing the sprint tasks using the skill-creator skill:

1. **Initialize the executor skill:**

   ```
   Use the skill-creator skill to create a new skill named "{sprint-name}-executor"
   ```

2. **Set up skill structure:**
   - Create `.claude/skills/{sprint-name}-executor/` directory
   - Use `assets/executor_skill_template.md` as starting point

3. **Populate the skill:**
   - **SKILL.md**: Customize executor template with sprint-specific details
   - **references/**: Copy ALL task files from sprint directory
     - Copy `00_SPRINT_PLAN.md` → `references/00_SPRINT_PLAN.md`
     - Copy `README.md` → `references/README.md`
     - Copy all task files → `references/{NN}_task_{name}.md`

4. **Customize SKILL.md:**
   - Update description with sprint goals and task range
   - List all tasks in "Load task file" section
   - Customize "Special Handling" for sprint-specific task types
   - Update environment setup for sprint requirements
   - Tailor validation patterns to sprint needs

5. **Validate the skill:**
   - Use skill-creator's packaging script to validate
   - Test that all references are accessible
   - Verify SKILL.md has complete information

**The executor skill enables:**

- User can say "Execute Sprint N Task X.Y" and Claude has all context
- No need to search for files during task execution
- Consistent execution workflow across all tasks
- Progress tracking and status updates
- Clear validation and reporting

## Resources Provided

### references/

Sprint 1 examples demonstrating the sprint planning structure:

- **example_sprint_plan.md** - Complete sprint plan with technical specs (00_SPRINT_PLAN.md from Sprint 1)
- **example_task_file.md** - Atomic task specification with full context (Task 1.1 from Sprint 1)
- **example_sprint_readme.md** - Sprint overview and task index (README.md from Sprint 1)
- **example_executor_skill.md** - Executor skill for running sprint tasks (Sprint 1 executor SKILL.md)

Load these references when creating a new sprint to understand the structure and level of detail expected.

### assets/

Templates for creating new sprint artifacts:

- **task_template.md** - Template for individual task files with all required sections
- **sprint_readme_template.md** - Template for sprint README with task index and tracking
- **executor_skill_template.md** - Template for creating the sprint executor skill

Use these templates directly when generating sprint artifacts in Steps 4 and 5.

## Best Practices

### Sprint Planning

1. **Front-load technical details** - Include complete code in sprint plan, extract to task files
2. **Make dependencies explicit** - Mark prerequisite tasks clearly
3. **Include validation commands** - Specify exact commands, not just "test it"
4. **Provide complete context** - Each task should be understandable standalone
5. **Use real examples** - Show expected output, file structures, commands

### Task File Quality

1. **No external references** - Don't say "see sprint plan"; include the code in the task
2. **Complete code templates** - Provide full implementation, not sketches
3. **Exact validation** - `make dbt-run --select model_name`, not "run the model"
4. **Clear success criteria** - Specific, measurable, testable conditions
5. **Practical notes** - Include gotchas, common mistakes, future considerations

### Executor Skill Quality

1. **Copy all task files** - Don't reference external directories; bundle everything
2. **Customize for sprint** - Tailor task types, validation patterns, environment setup
3. **Make it autonomous** - Skill should enable Claude to execute without user searches
4. **Include examples** - Show expected output format for success and failure cases

## Common Patterns

### Sprint Phases

Organize sprints into phases with milestones:

- **Phase 1: Critical Path** - Must-have features for deadline
- **Phase 2: Core Features** - Important but not blocking
- **Phase 3: Polish** - Automation, documentation, optimization

### Task Types

Common task categories seen in sprints:

- **Data ingestion** - API integration, parsing, validation
- **dbt modeling** - Staging, dimensional models, marts
- **Analysis notebooks** - Jupyter notebooks with visualizations
- **Automation** - CI/CD workflows, scheduled jobs
- **Documentation** - README updates, architecture docs, guides

### Validation Commands

Standard validation patterns to include:

```bash
# Python code quality
make lint
make typecheck

# dbt models
make dbt-run --select [model]
make dbt-test --select [model]
dbt show --select [model] --limit 10

# Data outputs
ls -lh data/raw/[source]/[dataset]/dt=*/
# Check row counts, schema, sample data

# Notebooks
uv run jupyter nbconvert --execute --to notebook --inplace [notebook]
```

## Output Format

When helping user create a sprint:

1. **After Step 1 (Sprint Planning):**

   ```text
   ✅ Sprint Plan Complete: {SPRINT_NAME}

   Created: 00_SPRINT_PLAN.md
   - {X} phases defined
   - {N} tasks identified
   - Complete technical specifications included

   Ready to proceed with task breakdown (Step 2)?
   ```

2. **After Step 2 (Task Design):**

   ```text
   ✅ Task Units Designed

   Created task specifications for:
   - Phase 1: Tasks {X.Y} through {X.Z} ({N} tasks)
   - Phase 2: Tasks {X.Y} through {X.Z} ({N} tasks)
   - Phase 3: Tasks {X.Y} through {X.Z} ({N} tasks)

   Each task includes: objective, context, code templates, validation, success criteria

   Ready to create sprint directory (Step 3)?
   ```

3. **After Step 4 (Files Generated):**

   ```text
   ✅ Sprint Directory Created: docs/spec/{sprint_directory}/

   Generated:
   - 00_SPRINT_PLAN.md (complete sprint plan)
   - README.md (sprint overview and task index)
   - {N} task files (01_task_*.md through {NN}_task_*.md)

   Ready to create executor skill (Step 5)?
   ```

4. **After Step 5 (Executor Skill):**

   ```text
   ✅ Sprint Setup Complete!

   Created:
   - Sprint directory: docs/spec/{sprint_directory}/
   - Executor skill: .claude/skills/{sprint-name}-executor/

   To execute sprint tasks, say:
   "Execute {SPRINT_NAME} Task {X.Y}"

   The executor skill has all task context bundled and ready.
   ```

## Handling User Scenarios

### Scenario: User wants to plan a new sprint

**User says:** "I want to plan a sprint for implementing user authentication"

**Response:**

1. Acknowledge and begin Step 1 (Sprint Planning)
2. Ask clarifying questions about goals, timeline, tech stack
3. Collaborate to create comprehensive sprint plan
4. Guide through Steps 2-5 to complete sprint setup

### Scenario: User has sprint plan, needs task breakdown

**User says:** "I have a sprint plan, help me break it into task files"

**Response:**

1. Read the sprint plan
2. Begin Step 2 (Task Design)
3. Propose task boundaries and dependencies
4. Get user approval, then proceed with Steps 3-5

### Scenario: User wants to modify existing sprint

**User says:** "Add a new task to Sprint 1"

**Response:**

1. Read existing sprint directory
2. Create new task file following established patterns
3. Update README task index
4. Update executor skill references/
5. Maintain numbering consistency

### Scenario: User wants sprint best practices

**User says:** "How should I structure my sprint?"

**Response:**

1. Share sprint planning philosophy
2. Explain atomic task principles
3. Provide examples from references/
4. Offer to help create a sprint following the workflow

## Troubleshooting

**Issue: Task files too large or complex**

- Break task into smaller subtasks
- Each subtask should be committable independently
- Ensure each task has single focus

**Issue: Tasks have circular dependencies**

- Review dependency graph
- Identify which task should come first
- Consider if tasks need to be combined or split differently

**Issue: Validation commands unclear**

- Make commands copy-paste ready with exact paths
- Show expected output for success case
- Include commands for both happy path and error cases

**Issue: Executor skill references not working**

- Ensure all task files copied to `references/` directory
- Check file paths match between task index and actual files
- Verify SKILL.md references correct file names

## Integration with Other Skills

This skill works well with:

- **skill-creator** - Use in Step 5 to create the executor skill
- **Project-specific executor skills** - Once created, use the executor skill for task execution
