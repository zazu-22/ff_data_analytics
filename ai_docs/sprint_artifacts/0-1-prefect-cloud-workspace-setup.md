# Story 0.1: Prefect Cloud Workspace Setup

Status: ready-for-dev

## Story

As a **data engineer**,
I want **a configured Prefect Cloud workspace with local execution verified**,
so that **I can orchestrate analytics tasks with monitoring, retry logic, and alerting from Day 1**.

## Acceptance Criteria

**From Tech Spec AC-1: Prefect Cloud Workspace Operational**

1. Workspace `ff-analytics` created and accessible via Prefect Cloud UI
2. API key stored in `.env` file as `PREFECT_API_KEY`
3. Simple test flow deploys and executes successfully from local Mac environment
4. Flow run visible in Prefect Cloud UI with state transitions logged

## Tasks / Subtasks

- [ ] **Task 1: Install Prefect and configure environment** (AC: #1, #2)

  - [ ] Add `prefect>=3.6.2` to pyproject.toml dependencies
  - [ ] Run `uv add prefect` to install package
  - [ ] Verify installation: `uv run prefect version`
  - [ ] Create `.env` file in project root (if not exists)
  - [ ] Add `.env` to `.gitignore` to prevent accidental commit of secrets

- [ ] **Task 2: Create and authenticate Prefect Cloud workspace** (AC: #1, #2)

  - [ ] Run `prefect cloud login` (interactive authentication)
  - [ ] Create workspace: `prefect workspace create ff-analytics`
  - [ ] Copy API key from Prefect Cloud UI
  - [ ] Add `PREFECT_API_KEY=<value>` to `.env` file
  - [ ] Verify environment variable loading: `echo $PREFECT_API_KEY` should show key

- [ ] **Task 3: Create and deploy simple test flow** (AC: #3, #4)

  - [ ] Create `flows/` directory: `mkdir -p flows`
  - [ ] Create test flow file: `flows/test_workspace_setup.py`
  - [ ] Implement minimal flow with single task (e.g., print "Hello from Prefect")
  - [ ] Execute flow locally: `python flows/test_workspace_setup.py`
  - [ ] Verify execution completes without errors

- [ ] **Task 4: Verify Prefect Cloud integration** (AC: #4)

  - [ ] Open Prefect Cloud UI in browser
  - [ ] Navigate to Flow Runs section
  - [ ] Locate test flow run by timestamp
  - [ ] Verify state transitions visible: Scheduled → Running → Completed
  - [ ] Check task logs are captured and readable in UI
  - [ ] Verify flow run metadata (duration, parameters, artifacts)

- [ ] **Task 5: Document workspace configuration** (AC: #1, #2)

  - [ ] Document workspace URL in project README or docs
  - [ ] Document `.env` file structure (required variables)
  - [ ] Add setup instructions for team members
  - [ ] Verify documentation complete: New developer can follow steps to authenticate

## Dev Notes

### Architecture Patterns and Constraints

**ADR-001: Prefect-First Development**

- All analytics tasks will be `@task`-decorated from Day 1 (no standalone scripts)
- Flows execute locally on Mac (Prefect Cloud for orchestration UI only)
- Retry logic, monitoring, and alerting built-in via Prefect decorators

**Integration with Existing Infrastructure:**

- Prefect extends existing snapshot governance patterns (error handling, Discord alerts)
- No changes to dbt models, ingestion scripts, or data storage
- New `flows/` directory added alongside `src/`, `dbt/`, `scripts/`

**Local Execution Requirements:**

- Python 3.13.6 (existing .python-version)
- Environment variables loaded via `.env` file (use direnv or manual `export`)
- Network access required for Prefect Cloud API communication

### Source Tree Components to Touch

**New Files to Create:**

```
flows/
├── __init__.py                    # Empty package marker
└── test_workspace_setup.py        # Simple test flow for validation

.env                                # Environment variables (gitignored)
```

**Files to Modify:**

```
pyproject.toml                      # Add prefect>=3.6.2 to dependencies
.gitignore                          # Add .env if not already present
README.md (optional)                # Add Prefect workspace setup instructions
```

**Directories to Create:**

```
flows/                              # Prefect flows directory (foundation for Epics 1-5)
.prefect/                           # Local Prefect config (auto-created, gitignored)
```

### Testing Standards Summary

**Unit Tests (Not Required for This Story):**

- Infrastructure setup story (no logic to unit test)
- Test coverage: Manual verification via acceptance criteria

**Integration Tests:**

- Test flow execution validates end-to-end integration
- Prefect Cloud API connectivity verified via UI inspection

**Manual Testing Checklist:**

- [ ] Workspace visible in Prefect Cloud UI
- [ ] Test flow run appears in Flow Runs section
- [ ] State transitions logged (Scheduled → Running → Completed)
- [ ] `.env` file excluded from git (`git status` should not show `.env`)
- [ ] `uv pip list | grep prefect` shows prefect>=3.6.2
- [ ] API key loaded: `python -c "import os; print(os.getenv('PREFECT_API_KEY'))"` returns key

**Edge Cases to Handle:**

- Missing `PREFECT_API_KEY` environment variable → Flow fails with clear error message
- Network connectivity issues → Prefect CLI shows authentication error
- Workspace already exists → `prefect workspace create` returns error (acceptable, use existing)

### Project Structure Notes

**Alignment with unified-project-structure.md:**

- `flows/` directory added at project root (same level as `src/`, `dbt/`, `scripts/`)
- Follows existing Python package patterns (\_\_init\_\_.py markers)
- Matches data directory structure conventions (`data/analytics/` created in Story 3)

**No Conflicts Detected:**

- Prefect flows isolated in `flows/` directory
- No changes to existing `src/ingest/`, `dbt/`, or `scripts/` modules
- `.env` file pattern already established (existing `.gitignore` includes `.env`)

### References

**Primary Sources:**

- [Tech Spec Epic 0](./tech-spec-epic-0.md#ac-1-prefect-cloud-workspace-operational) - AC-1 acceptance criteria
- [Architecture Document](../architecture.md#adr-001-prefect-first-vs-post-mvp-orchestration) - ADR-001: Prefect-First Development
- [Architecture Document](../architecture.md#91-prerequisites) - Environment setup guidance

**Prefect Documentation:**

- [Prefect Cloud Quickstart](https://docs.prefect.io/latest/cloud/cloud-quickstart/) - Workspace setup steps
- [Prefect Authentication](https://docs.prefect.io/latest/cloud/users/api-keys/) - API key management
- [Prefect Flows](https://docs.prefect.io/latest/concepts/flows/) - Flow decorator usage

**Existing Patterns:**

- Snapshot governance flows (reference for error handling patterns - to be reviewed in Story 4)
- `.env` file handling (existing pattern from GCS integration)

## Dev Agent Record

### Context Reference

- `ai_docs/sprint_artifacts/0-1-prefect-cloud-workspace-setup.context.xml` (Generated: 2025-11-20)

### Agent Model Used

<!-- To be filled by dev agent -->

### Debug Log References

<!-- To be filled by dev agent during implementation -->

### Completion Notes List

<!-- To be filled by dev agent after story completion -->

### File List

<!-- To be filled by dev agent: NEW, MODIFIED, DELETED files -->

## Change Log

| Date       | Author | Change Description                                    |
| ---------- | ------ | ----------------------------------------------------- |
| 2025-11-19 | SM     | Initial story draft created via create-story workflow |
