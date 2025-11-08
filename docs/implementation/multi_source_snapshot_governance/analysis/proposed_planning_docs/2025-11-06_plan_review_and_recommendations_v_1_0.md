______________________________________________________________________

## title: NFLverse & Multi-Source Snapshot Governance Plan Review and Recommendations version: 1.0 date: 2025-11-06

# NFLverse & Multi-Source Snapshot Governance Plan Review

**Date:** November 6, 2025\
**Reviewer:** AI Analysis\
**Status:** Recommendations for Plan Revision

## Executive Summary

The proposed plan addresses real technical debt in the data pipeline with a well-structured approach. However, analysis of the current codebase reveals **scope ambiguity**, **sequencing issues**, and **missing transition planning** that should be addressed before execution.

**Overall Assessment:** ✅ **Approve with Modifications**

**Key Recommendations:**

1. **Resequence:** Freshness tests → Snapshot governance → Prefect Phase 1 only → Cloud blueprint (doc only)
2. **Clarify Prefect scope:** Phase 1 only (8 hours) vs full 4-phase plan (36 hours)
3. **Update SPEC v2.3 checklist FIRST**, then write new docs
4. **Add cut-over plan** for CI transition with parallel run period

______________________________________________________________________

## Current State Analysis

### What's Working Well

✅ **Robust dbt test coverage**: 147/149 tests passing (98.7%)\
✅ **GCS write capability exists**: `src/ingest/common/storage.py` has PyArrow FS helpers\
✅ **Comprehensive Prefect plan**: `docs/spec/prefect_dbt_sources_migration_20251026.md` (1273 lines)\
✅ **Manifest metadata pattern**: All sources write `_meta.json` with lineage\
✅ **Latest snapshot macro exists**: `latest_snapshot_only()` used in `stg_nflverse__ff_opportunity`

### Current Pain Points

❌ **Inconsistent snapshot selection**:

- `stg_nflverse__player_stats`: Hardcoded `dt IN ('2025-10-01', '2025-10-27')`
- `stg_nflverse__snap_counts`: Hardcoded `dt IN ('2025-10-01', '2025-10-28')`
- `stg_nflverse__ff_opportunity`: Uses `latest_snapshot_only()` macro ✅

❌ **Sample artifacts mixed with production**:

- `data/raw/nflverse/weekly/dt=2024-01-01/` contains old CSV/Parquet samples
- Root-level `weekly.csv`, `weekly.parquet` files alongside dated partitions

❌ **No unified snapshot governance**:

- No snapshot registry or metadata model
- No cross-source validation tooling
- Inconsistent coverage documentation

❌ **Documentation drift**:

- SPEC v2.3 checklist mentions `latest_snapshot_only()` for ff_opportunity ✅
- But doesn't note that player_stats/snap_counts still hardcoded ❌
- Two Prefect "sources of truth" (Oct 26 plan + this new plan)

______________________________________________________________________

## Detailed Feedback by Step

### 1. Stabilize Current Pipelines

**Proposed:**

> Update stg_nflverse\_\_player_stats and stg_nflverse\_\_snap_counts to use a parameterized latest_snapshot_only() pattern (retain one historical baseline + rolling current snapshot)

**Current Implementation:**

```sql
-- stg_nflverse__player_stats.sql (lines 123-126)
and (
  w.dt = '2025-10-01'  -- Historical: 2020-2024 + partial 2025
  or w.dt = '2025-10-27'  -- Latest: Complete 2024-2025
)
```

**Feedback:**

✅ **Good:** Addresses real inconsistency\
⚠️ **Concern:** "Retain one historical baseline + rolling current snapshot" might be **too rigid**

**Recommendation:** Create a flexible `snapshot_selection_strategy` macro:

```sql
-- dbt/ff_data_transform/macros/snapshot_selection.sql
{% macro snapshot_selection_strategy(source_glob, strategy='latest_only', baseline_dt=none) %}
  {% if strategy == 'latest_only' %}
    and {{ latest_snapshot_only(source_glob) }}
  {% elif strategy == 'baseline_plus_latest' %}
    and (dt = '{{ baseline_dt }}' or {{ latest_snapshot_only(source_glob) }})
  {% elif strategy == 'all' %}
    -- No filter, load all snapshots (for backfills)
  {% endif %}
{% endmacro %}
```

**Sample Relocation:**

✅ **Good idea** to move samples to `_samples/`

🔴 **Critical:** Before relocating, verify:

- Are `data/raw/nflverse/weekly/dt=2024-01-01/` files used by tests?
- Check `tests/test_nflverse_samples_pk.py` for path dependencies
- Does CI rely on these sample paths?

**Action Items:**

1. Implement flexible snapshot strategy macro
2. Add `_samples` read/write guards in `src/ingest/nflverse/shim.py`
3. Update all three staging models to use the macro
4. Relocate samples and update test fixtures

______________________________________________________________________

### 2. Align Multi-Source Snapshot Governance

**Proposed:**

> Define a shared snapshot selection macro + metadata model in dbt/ff_data_transform/models/sources/

**Feedback:**

✅ **Good:** Centralized governance is the right approach

🔴 **Missing Piece:** Plan doesn't address **who decides what the "latest" snapshot is**

**Critical Addition:** Create a **snapshot registry seed**:

```csv
# dbt/ff_data_transform/seeds/snapshot_registry.csv
source,dataset,snapshot_date,status,coverage_start_season,coverage_end_season,row_count,notes
nflverse,weekly,2025-11-05,current,2020,2025,97302,Complete 2020-2025
nflverse,weekly,2025-10-27,historical,2020,2024,89145,Historical baseline
nflverse,snap_counts,2025-11-05,current,2020,2025,136974,Complete
nflverse,ff_opportunity,2025-11-05,current,2020,2025,31339,Complete
```

**Benefits:**

1. **Deterministic selection**: Models reference registry instead of hardcoded dates
2. **CI validation**: Fail builds if expected snapshots missing
3. **Audit trail**: Track snapshot promotion/retirement
4. **LLM-friendly**: Single source of truth for what data exists

**Manifest Validation Enhancement:**

Proposed tool extension:

```python
# tools/validate_manifests.py (NEW)
def validate_snapshot_coverage(source: str, dataset: str):
    """
    Cross-check:
    - Manifest row counts vs actual Parquet
    - Season/week coverage gaps
    - Player mapping coverage vs dim_player_id_xref
    - Compare to snapshot_registry expectations
    """
```

**Action Items:**

1. Create `snapshot_registry` seed with current snapshots
2. Implement `tools/validate_manifests.py`
3. Add manifest validation to CI (GitHub Actions or Prefect)
4. Document governance model in `models/sources/README.md`

______________________________________________________________________

### 3. Cloud-Ready Storage Transition

**Proposed:**

> Draft storage migration blueprint, prototype sync utility

**Current State:**

- GCS write support exists: `tools/smoke_gcs_write.py` validates it works
- dbt profiles default to `EXTERNAL_ROOT=data/raw` (local)
- No migration docs yet (`docs/ops/` doesn't exist)

**Feedback:**

✅ **Good:** Keeping this as **blueprint documentation** rather than immediate implementation

⚠️ **Sequencing Issue:** Cloud storage transition should come **AFTER** Prefect, not before

**Why?**

1. Prefect flows will abstract storage destination (local vs GCS)
2. Cloud transition becomes an **env var change** in Prefect config
3. No need to update individual ingest scripts
4. Can test Prefect locally first, then flip to cloud

**Revised Sequencing:**

1. Implement Prefect flows (local storage)
2. Validate Prefect works correctly
3. Change `EXTERNAL_ROOT` env var to GCS path
4. Test cloud storage with established flows

**Critical Addition:** Migration blueprint must document **IAM requirements**:

````markdown
# docs/ops/cloud_storage_migration.md

## GCS Permissions Required
- `storage.objects.create` (write Parquet)
- `storage.objects.get` (DuckDB read)
- `storage.objects.list` (glob patterns)

## Service Account Setup
```bash
# Create dedicated service account
gcloud iam service-accounts create ff-analytics-ingestion \
    --display-name="FF Analytics Ingestion"

# Grant GCS permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:ff-analytics-ingestion@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Download key (for local dev/CI)
gcloud iam service-accounts keys create gcp-service-account-key.json \
    --iam-account=ff-analytics-ingestion@PROJECT_ID.iam.gserviceaccount.com
````

## DuckDB GCS Configuration

```sql
-- Install httpfs extension (if not already)
INSTALL httpfs;
LOAD httpfs;

-- Configure GCS access
SET gcs_access_key_id = '...';
SET gcs_secret_access_key = '...';

-- Test read
SELECT * FROM read_parquet('gs://ff-analytics/raw/nflverse/weekly/dt=*/weekly.parquet')
LIMIT 10;
```

````

**Action Items:**
1. Move Step 3 to **after** Prefect implementation (becomes Step 5)
2. Create `docs/ops/cloud_storage_migration.md` (documentation only)
3. Document IAM requirements and service account setup
4. Create migration checklist (no code changes in this phase)

---

### 4. Prefect-Orchestrated Ingestion

**Proposed:**
> Model Prefect flows for nflverse ingestion, reference refresh, Sleeper updates, and dbt runs

**Current State:**
- Comprehensive plan exists: `docs/spec/prefect_dbt_sources_migration_20251026.md` (1273 lines, 4-week timeline)
- No implementation yet: `src/flows/` doesn't exist
- Current orchestration: Mix of GitHub Actions (sheets copy) + manual `make` commands

**Feedback:**

✅ **Excellent:** The existing Prefect plan is thorough and well-sequenced

⚠️ **Scope Creep Risk:** This step mentions "Prefect" but doesn't clarify **which parts** of the existing 4-week plan are in scope

**Existing Prefect Plan Breakdown:**
- **Phase 1 (Week 1):** 7 hours - Setup + Google Sheets flow
- **Phase 2 (Week 2):** 10 hours - Add all data sources (nflverse, KTC, FFAnalytics, Sleeper)
- **Phase 3 (Week 3):** 10 hours - Backfill + monitoring
- **Phase 4 (Week 4):** 9 hours - GH Actions integration + documentation
- **Total:** 36 hours over 4 weeks

**Critical Question:** Is this initiative implementing:
1. Full 4-week Prefect plan? (36 hours)
2. Just Phase 1 (Week 1)? (7 hours)
3. Only flow definitions without deployment?

**Recommendation:** **Clarify scope explicitly**:

```markdown
## 4. Prefect-Orchestrated Ingestion

**Scope for this initiative:** Phase 1 only (Week 1 from existing plan)
- Create `src/flows/` structure
- Wrap nflverse/sheets ingestion as Prefect tasks
- Local testing with Prefect UI
- **NOT included:** Cloud deployment, monitoring, backfill flows

**Dependencies:** Completes after Steps 1-2 (stable pipelines, snapshot governance)

**Follow-up work:** Full Prefect deployment (Phases 2-4) in separate initiative

**Timeline:** 7-8 hours (Week 1 scope only)
````

**Critical Gap:** Existing Prefect doc (Oct 26) predates your snapshot governance concerns. Make sure:

- Prefect flows respect snapshot registry (if implemented)
- Flows use `snapshot_selection_strategy` macro in dbt calls
- Snapshot metadata validation runs before dbt execution

**Action Items:**

1. Clarify Prefect scope (Phase 1 only vs full plan)
2. Update Prefect plan to reference snapshot governance
3. Implement Phase 1 only: Google Sheets + nflverse basic flows
4. Keep deployment/monitoring for separate initiative

______________________________________________________________________

### 5. Documentation Review & Refresh

**Proposed:**

> Audit docs, identify inaccuracies, decide per doc whether to revise/replace/retire

**Current State:**

- **SPEC v2.3 checklist:** Comprehensive but showing drift
  - ✅ Notes ff_opportunity uses `latest_snapshot_only()`
  - ❌ Doesn't mention player_stats/snap_counts still hardcoded
  - ✅ Documents KTC 100% complete
  - ❌ Doesn't reflect Prefect plan exists but not implemented
- **ADRs:** Up to date (ADR-010 mfl_id matches implementation)
- **No `docs/ops/` directory yet**

**Feedback:**

✅ **Good:** Audit before writing prevents duplication

🔴 **Priority Inversion:** Plan suggests creating new docs before updating checklist

**Recommendation:** **Update checklist FIRST**, then write new docs

**Why?**

- Implementation checklist is **most valuable doc for LLMs**
- New contributors check checklist to understand current state
- Creating new docs without updating checklist causes drift
- Checklist should be "source of truth" that links to detailed docs

**Documentation Consolidation Issue:**

You currently have:

1. `docs/spec/prefect_dbt_sources_migration_20251026.md` (1273 lines, very detailed)
2. This new plan (NFLverse alignment)

**Risk:** Two "sources of truth" for orchestration strategy

**Recommendation:**

- Rename Oct 26 doc → `prefect_implementation_guide.md` (HOW to implement)
- This plan becomes → `snapshot_governance_plan.md` (WHAT to standardize)
- Create → `docs/ops/orchestration_architecture.md` (CURRENT STATE reference for LLMs)

**Priority: "Current State" Over "Future Plans"**

LLMs need to understand **what exists NOW**, not just what's planned. Create:

1. `docs/ops/snapshot_management_current_state.md`

   - What snapshot selection logic exists today per source?
   - Which models use hardcoded dates vs macros?
   - Where are samples stored?

2. `docs/ops/ingestion_triggers_current_state.md`

   - How do loads run today? (GH Actions? Manual make commands?)
   - What's the schedule for each source?
   - Where are credentials stored?

3. `docs/ops/data_freshness_current_state.md`

   - How do you know if data is stale?
   - Are there alerts? Monitoring?
   - What's the expected refresh cadence per source?

**Action Items:**

1. **Update SPEC v2.3 checklist** with current snapshot selection state
2. Create "current state" docs (3 listed above)
3. Consolidate Prefect documentation (rename/reorganize)
4. Update README.md with new doc structure
5. THEN create new governance design docs

______________________________________________________________________

### 6. Monitoring & CI Pathway

**Proposed:**

> Add dbt freshness/anomaly tests plus interim GitHub Actions hooks

**Current State:**

- dbt tests are robust (147/149 passing)
- No freshness tests yet: Models don't use dbt `freshness:` checks
- GitHub Actions exist: `data-pipeline.yml`, `ingest_google_sheets.yml`

**Feedback:**

⚠️ **Sequencing Issue:** Should add freshness tests **BEFORE** Prefect, not after

**Why?**

1. Freshness tests help **validate Prefect flows are working**
2. Provide safety net during migration
3. Simpler to implement (YAML config, no Python)
4. Can test locally before orchestration changes

**Example freshness test** (add to `dbt/ff_data_transform/models/sources/src_nflverse.yml`):

```yaml
sources:
  - name: nflverse
    description: "NFLverse datasets loaded via Python/R shim"

    freshness:
      warn_after: {count: 7, period: day}
      error_after: {count: 14, period: day}
    loaded_at_field: dt  # Use partition date as freshness indicator

    tables:
      - name: weekly
        description: "Weekly player stats (71 stat types)"
        identifier: "weekly/dt=*/*.parquet"

        # Override source-level freshness for more frequent updates
        freshness:
          warn_after: {count: 3, period: day}
          error_after: {count: 7, period: day}
```

**Critical Gap:** "Interim GH Actions hooks (until Prefect fully replaces CI triggers)"

Plan doesn't explain **what happens during transition**. Need:

1. **Cut-over plan:** When do you turn off GitHub Actions?
2. **Parallel run period:** Run both GH Actions AND Prefect for 1-2 weeks
3. **Rollback plan:** If Prefect fails, how do you revert?
4. **Validation criteria:** How do you know Prefect is working correctly?

**Recommended Transition Plan:**

```markdown
## CI Transition: GitHub Actions → Prefect

### Week 1: Add Freshness Tests
- Implement dbt source freshness for all providers
- Validate current data meets thresholds
- Add freshness checks to GH Actions workflow

### Week 2: Parallel Run
- Deploy Prefect flows (Phase 1)
- Keep GitHub Actions running
- Compare outputs (row counts, manifests, timing)
- Monitor both systems for 1-2 weeks

### Week 3: Cut-Over
- Disable GH Actions schedules (keep webhook triggers as backup)
- Prefect becomes primary orchestrator
- GH Actions remain available for manual fallback

### Week 4: Cleanup
- Remove GH Actions if Prefect stable for 2+ weeks
- Update documentation
- Archive old workflows (don't delete immediately)

### Rollback Procedure
If Prefect fails during parallel run:
1. Re-enable GH Actions schedules
2. Disable Prefect deployments
3. Debug Prefect locally
4. Retry parallel run when fixed
```

**Action Items:**

1. **Move freshness tests to Step 2** (after snapshot governance)
2. Add freshness thresholds for all sources
3. Document CI transition plan (parallel run + rollback)
4. Track in SPEC v2.3 checklist

______________________________________________________________________

## Recommended Revised Sequencing

Based on implementation state, dependencies, and risk mitigation:

### Phase 1: Foundation (Week 1, ~8 hours)

**Step 1: Stabilize Snapshot Selection**

- Implement flexible `snapshot_selection_strategy` macro
- Document current hardcoded dt logic in staging models
- Relocate samples to `data/raw/nflverse/_samples/`
- Update test fixtures and verify no CI breakage
- **Deliverable:** All nflverse staging models use consistent macro

**Step 2: Add dbt Freshness Tests**

- Define freshness thresholds per source in `sources/` YAMLs
- Validate current data meets thresholds (baseline)
- Add `dbt source freshness` to local validation workflow
- **Deliverable:** Safety net before orchestration changes

### Phase 2: Governance (Week 2, ~10 hours)

**Step 3: Implement Multi-Source Snapshot Governance**

- Create `snapshot_registry` seed (optional but recommended)
- Implement shared snapshot selection macro
- Extend `tools/validate_manifests.py` for cross-source checks
- Update all staging models to use governance pattern
- **Deliverable:** Consistent snapshot strategy across all sources

**Step 4: Documentation Audit & Refresh**

- **Update SPEC v2.3 checklist** with current state
- Create "current state" docs (3 files in `docs/ops/`)
- Consolidate Prefect documentation
- Create `docs/ops/orchestration_architecture.md`
- **Deliverable:** LLM-friendly current state documentation

### Phase 3: Orchestration (Week 3-4, ~8 hours)

**Step 5: Prefect Phase 1 Implementation**

- Create `src/flows/` structure
- Implement Google Sheets pipeline flow
- Implement nflverse ingestion flow
- Local testing only (no cloud deployment)
- Wire freshness checks into flows
- **Deliverable:** Working Prefect flows (local execution)
- **Scope:** Phase 1 only from existing plan (7-8 hours)

**Step 6: CI Transition Planning**

- Document parallel run strategy (GH Actions + Prefect)
- Create rollback procedure
- Define cut-over validation criteria
- **Deliverable:** Transition plan document
- **Note:** Actual transition execution is out of scope

### Phase 4: Cloud Readiness (Week 5, ~4 hours - Documentation Only)

**Step 7: Cloud Storage Migration Blueprint**

- Draft `docs/ops/cloud_storage_migration.md`
- Document GCS bucket layout and retention policy
- Document IAM requirements and service account setup
- Create migration checklist
- Prototype `tools/sync_snapshots.py` (optional)
- **Deliverable:** Migration blueprint (no implementation)
- **Note:** Actual migration is future work

**Total Estimated Effort:** 30-32 hours over 5 weeks

______________________________________________________________________

## Critical Missing Pieces

### 1. Rollback Strategy

**Question:** What if snapshot governance changes break existing queries or notebooks?

**Need:**

- Backwards compatibility testing
- Version control for snapshot selection logic
- Ability to revert to hardcoded dates if macro fails

### 2. Testing Strategy

**Question:** How do you validate new snapshot selection doesn't change results?

**Need:**

- Comparison test: Old query results vs new query results
- Row count validation
- Statistical checks (min/max/sum of key stats)

**Example test:**

```sql
-- dbt/ff_data_transform/tests/assert_snapshot_selection_consistency.sql
-- Compare row counts before/after snapshot strategy change
WITH old_logic AS (
  SELECT COUNT(*) as cnt FROM {{ ref('stg_nflverse__player_stats') }}
  WHERE dt IN ('2025-10-01', '2025-10-27')
),
new_logic AS (
  SELECT COUNT(*) as cnt FROM {{ ref('stg_nflverse__player_stats') }}
  -- Uses new snapshot_selection_strategy macro
)
SELECT * FROM old_logic
EXCEPT
SELECT * FROM new_logic
-- Expect 0 rows (counts should match)
```

### 3. Backward Compatibility

**Question:** Will old notebook code break after snapshot changes?

**Impact Analysis:**

- Jupyter notebooks with hardcoded date filters
- Ad-hoc SQL queries in `docs/analysis/`
- External reports or dashboards

**Recommendation:**

- Audit notebooks for hardcoded `dt=` filters
- Add deprecation warnings for direct Parquet reads
- Encourage using dbt refs instead of raw Parquet

### 4. Performance Implications

**Question:** Loading multiple snapshots with UNION could be slow — profiled?

**Current Implementation:**

```sql
-- stg_nflverse__snap_counts.sql (line 182)
deduplicated as (
  -- Deduplicate overlapping seasons (2025 appears in both snapshots)
  select * from unpivoted
  qualify row_number() over (
    partition by player_key, game_id, stat_name
    order by season desc, week desc
  ) = 1
)
```

**Concern:** This pattern:

1. Reads 2 snapshots (double data volume)
2. Performs deduplication with window function
3. Could be slow for large datasets

**Recommendation:**

- Profile query performance with `EXPLAIN` before/after
- Consider materialized view if slow
- Document expected query time in model

### 5. Snapshot Promotion Policy

**Question:** When does a snapshot move from "latest" to "historical"?

**Need:**

- Clear promotion criteria (e.g., "after 2 weeks of stability")
- Who approves snapshot promotion? (Manual review? Automated?)
- How are snapshots retired? (Archive vs delete)

**Suggested Policy:**

```markdown
## Snapshot Lifecycle

1. **New snapshot loaded** → status='pending'
2. **After 48 hours + validation** → status='current' (promoted)
3. **Previous current** → status='historical'
4. **After 90 days** → status='archived' (move to cold storage)
5. **After 1 year** → Delete archived (unless needed for compliance)
```

______________________________________________________________________

## Next Steps

### Immediate Actions (Before Starting Implementation)

1. **Decision Required:** Confirm Prefect scope

   - [ ] Phase 1 only (7-8 hours) - RECOMMENDED
   - [ ] Full 4-phase plan (36 hours)
   - [ ] Something in between?

2. **Decision Required:** Snapshot registry seed

   - [ ] Implement registry (recommended for governance)
   - [ ] Skip registry (use macro only for now)

3. **Review:** Revised sequencing

   - [ ] Approve resequenced plan
   - [ ] Request modifications
   - [ ] Discuss concerns

### Week 1 Kickoff (If Approved)

1. Create feature branch: `feature/snapshot-governance`
2. Implement Step 1: Stabilize snapshot selection
3. Implement Step 2: Add freshness tests
4. Update SPEC v2.3 checklist with progress
5. Daily standup: Check progress, unblock issues

### Success Criteria

By end of Phase 2 (2 weeks), you should have:

✅ **Consistent snapshot selection** across all nflverse staging models\
✅ **Freshness tests** providing safety net\
✅ **Snapshot governance pattern** documented and tested\
✅ **Current state docs** up to date for LLMs\
✅ **Updated checklist** reflecting reality\
✅ **Foundation ready** for Prefect implementation

By end of Phase 4 (5 weeks), you should have:

✅ **Working Prefect flows** (local execution)\
✅ **CI transition plan** documented\
✅ **Cloud migration blueprint** complete\
✅ **Zero manual data loads** for nflverse/sheets\
✅ **Clear path** to production orchestration

______________________________________________________________________

## Appendix: Detailed File Changes

### Files to Create

01. `dbt/ff_data_transform/macros/snapshot_selection.sql` - Flexible snapshot strategy macro
02. `dbt/ff_data_transform/seeds/snapshot_registry.csv` - Snapshot governance registry (optional)
03. `tools/validate_manifests.py` - Cross-source manifest validation
04. `docs/ops/snapshot_management_current_state.md` - Current state reference
05. `docs/ops/ingestion_triggers_current_state.md` - Orchestration current state
06. `docs/ops/data_freshness_current_state.md` - Freshness monitoring current state
07. `docs/ops/cloud_storage_migration.md` - GCS migration blueprint
08. `docs/ops/ci_transition_plan.md` - GitHub Actions → Prefect transition
09. `src/flows/google_sheets_pipeline.py` - Prefect flow for sheets
10. `src/flows/nfl_data_pipeline.py` - Prefect flow for nflverse

### Files to Update

1. `dbt/ff_data_transform/models/staging/stg_nflverse__player_stats.sql` - Use snapshot macro
2. `dbt/ff_data_transform/models/staging/stg_nflverse__snap_counts.sql` - Use snapshot macro
3. `dbt/ff_data_transform/models/sources/src_nflverse.yml` - Add freshness tests
4. `dbt/ff_data_transform/models/sources/src_sheets.yml` - Add freshness tests
5. `dbt/ff_data_transform/models/sources/src_ktc.yml` - Add freshness tests
6. `docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md` - Update with current state
7. `src/ingest/nflverse/shim.py` - Add `_samples` guards
8. `tests/test_nflverse_samples_pk.py` - Update sample paths if relocated
9. `README.md` - Update with new doc structure

### Files to Relocate

1. `data/raw/nflverse/weekly/dt=2024-01-01/*` → `data/raw/nflverse/_samples/weekly/`
2. `data/raw/nflverse/weekly/weekly.csv` → `data/raw/nflverse/_samples/weekly.csv`
3. `data/raw/nflverse/weekly/weekly.parquet` → `data/raw/nflverse/_samples/weekly.parquet`
4. `data/raw/nflverse/players/players.csv` → `data/raw/nflverse/_samples/players.csv`
5. `data/raw/nflverse/players/players.parquet` → `data/raw/nflverse/_samples/players.parquet`

______________________________________________________________________

## Questions for Clarification

Before proceeding, please clarify:

1. **Prefect Scope:** Phase 1 only (7-8 hours) or full plan (36 hours)?
2. **Snapshot Registry:** Implement seed or skip for now?
3. **Timeline:** 5-week timeline acceptable? Or compress/extend?
4. **Resources:** Solo implementation or team collaboration?
5. **Priorities:** Any steps that can be deferred or descoped?
6. **Dependencies:** Any external blockers (e.g., GCS access, Prefect Cloud account)?

______________________________________________________________________

## Conclusion

The proposed plan addresses important infrastructure improvements with solid technical reasoning. The main areas for adjustment are:

1. **Sequencing:** Freshness → Governance → Prefect → Cloud (not Cloud before Prefect)
2. **Scope:** Clarify Prefect is Phase 1 only (not full 36-hour plan)
3. **Documentation:** Update checklist first, then create new docs
4. **Transition:** Add parallel run period and rollback plan for CI cut-over

With these modifications, the plan becomes more executable, lower-risk, and better aligned with the current codebase state.

**Recommendation:** ✅ **Approve with modifications outlined above**
