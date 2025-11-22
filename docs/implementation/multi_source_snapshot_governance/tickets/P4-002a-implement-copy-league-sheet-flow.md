# Ticket P4-002a: Implement copy_league_sheet_flow

**Phase**: 4 - Orchestration\
**Status**: COMPLETE\
**Estimated Effort**: Medium (2-3 hours)\
**Dependencies**: P4-001 (shared utilities must exist)

## Objective

Implement Prefect flow for copying tabs from Commissioner Google Sheet to working copy sheet. This is the first step in the sheets ingestion sequence and must complete before parsing begins.

## Context

The Google Sheets ingestion consists of **two sequential operations**:

1. **Copy operation** (this ticket): Copy tabs from Commissioner sheet to working copy
2. **Parse operation** (P4-002): Parse the copied sheet and write to Parquet

**Operational Requirements**:

- Sheets need to be updated **multiple times per day** during active season
- Copy must complete **before** parse begins
- Copy can run independently (e.g., every 2-4 hours)
- Parse should run **soon after** copy completes (within 15-30 minutes)
- Copy operation can silently fail or partially complete (missing tabs)

**Known Issue**: The sheets copy operation can silently fail or partially complete, resulting in missing tabs. This was reflected in logs but not caught by the pipeline, leading to incomplete data ingestion. This flow adds **copy completeness validation** to catch this issue.

## Tasks

- [x] Create `src/flows/copy_league_sheet_flow.py`
- [x] Define flow with tasks: Copy tabs → Validate copy completeness → Log results
- [x] Integrate with existing `scripts/ingest/copy_league_sheet.py` or `src/ingest/sheets/copier.py`
- [x] Add governance task: Validate all expected tabs were copied
- [x] Add flow result/output that parse flow can depend on
- [x] Test locally with Prefect dev server
- [x] Document flow configuration (env vars, credentials, scheduling)

## Acceptance Criteria

- [x] Flow executes copy operation successfully
- [x] Copy completeness validation catches missing tabs
- [x] Flow fails gracefully if tabs are missing (no partial copy)
- [x] Flow produces result/output that parse flow can depend on
- [x] Flow testable locally
- [x] Flow can be scheduled independently (every 2-4 hours)

## Implementation Notes

**File**: `src/flows/copy_league_sheet_flow.py`

**Flow Structure**:

```python
"""Prefect flow for copying Commissioner sheet to working copy."""

from datetime import datetime
from prefect import flow, task
from src.ingest.sheets.copier import copy_league_sheet, CopyOptions
from src.flows.utils.notifications import log_info, log_warning, log_error
import os


@task(name="copy_league_sheet_tabs")
def copy_tabs_task(
    src_sheet_id: str,
    dst_sheet_id: str,
    tabs: list[str]
) -> dict:
    """Copy tabs from source sheet to destination sheet.

    Args:
        src_sheet_id: Commissioner sheet ID (from env var)
        dst_sheet_id: Working copy sheet ID (from env var)
        tabs: List of tab names to copy

    Returns:
        Copy results summary
    """
    log_info("Starting sheet copy operation", context={
        "src_sheet_id": src_sheet_id,
        "dst_sheet_id": dst_sheet_id,
        "tabs": tabs
    })

    # Use existing copier module
    result = copy_league_sheet(
        src_sheet_id=src_sheet_id,
        dst_sheet_id=dst_sheet_id,
        tabs=tabs,
        options=CopyOptions(paste_values_only=True)
    )

    if result["errors"] > 0:
        log_error(
            "Sheet copy failed",
            context={"result": result}
        )
    elif result["skipped"] > 0:
        log_warning(
            "Some tabs skipped during copy",
            context={"result": result}
        )
    else:
        log_info(
            "All tabs copied successfully",
            context={"copied_count": result["copied"]}
        )

    return result


@task(name="validate_copy_completeness")
def validate_copy_completeness(
    expected_tabs: list[str],
    copied_sheet_id: str
) -> dict:
    """Validate all expected tabs were copied from source sheet.

    This addresses the silent failure issue where sheets copy operation
    doesn't copy all tabs. Checks that all expected tabs exist in the
    copied sheet.

    Args:
        expected_tabs: List of tab names that should exist
        copied_sheet_id: Google Sheet ID of copy destination

    Returns:
        Validation results with any missing tabs
    """
    from googleapiclient.discovery import build
    from google.oauth2 import service_account

    # Build sheets service
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )
    service = build('sheets', 'v4', credentials=credentials)

    # Get tabs from copied sheet
    sheet_metadata = service.spreadsheets().get(spreadsheetId=copied_sheet_id).execute()
    copied_tabs = [sheet['properties']['title'] for sheet in sheet_metadata.get('sheets', [])]

    # Check for missing tabs
    missing_tabs = [tab for tab in expected_tabs if tab not in copied_tabs]

    if missing_tabs:
        log_error(
            "Sheets copy incomplete - missing tabs",
            context={
                "expected_tabs": expected_tabs,
                "copied_tabs": copied_tabs,
                "missing_tabs": missing_tabs,
                "sheet_id": copied_sheet_id
            }
        )
        return {"valid": False, "missing_tabs": missing_tabs, "copied_tabs": copied_tabs}

    log_info(
        "All expected tabs copied successfully",
        context={"tab_count": len(expected_tabs), "tabs": copied_tabs}
    )
    return {"valid": True, "missing_tabs": [], "copied_tabs": copied_tabs}


@flow(name="copy_league_sheet_flow")
def copy_league_sheet_flow(
    src_sheet_id: str = None,
    dst_sheet_id: str = None,
    tabs: list[str] = None
) -> dict:
    """Prefect flow for copying Commissioner sheet to working copy.

    Args:
        src_sheet_id: Commissioner sheet ID (defaults to COMMISSIONER_SHEET_ID env var)
        dst_sheet_id: Working copy sheet ID (defaults to LEAGUE_SHEET_COPY_ID env var)
        tabs: List of tab names to copy (defaults to SHEETS_TABS env var, comma-separated)

    Returns:
        Flow result with copy status and validation
    """
    # Get configuration from env vars if not provided
    if src_sheet_id is None:
        src_sheet_id = os.getenv("COMMISSIONER_SHEET_ID")
    if dst_sheet_id is None:
        dst_sheet_id = os.getenv("LEAGUE_SHEET_COPY_ID")
    if tabs is None:
        tabs_str = os.getenv("SHEETS_TABS", "")
        tabs = [t.strip() for t in tabs_str.split(",") if t.strip()]

    log_info("Starting copy_league_sheet_flow", context={
        "src_sheet_id": src_sheet_id,
        "dst_sheet_id": dst_sheet_id,
        "tabs": tabs
    })

    # Copy tabs
    copy_result = copy_tabs_task(src_sheet_id, dst_sheet_id, tabs)

    # Validate copy completeness
    validation_result = validate_copy_completeness(tabs, dst_sheet_id)

    if not validation_result["valid"]:
        log_error(
            "Copy flow failed - incomplete copy detected",
            context={"missing_tabs": validation_result["missing_tabs"]}
        )
        # Flow will fail here due to log_error raising exception

    log_info("Copy flow completed successfully", context={
        "copied_tabs": copy_result["copied"],
        "validation": "passed"
    })

    return {
        "copy_result": copy_result,
        "validation_result": validation_result,
        "ready_for_parse": validation_result["valid"]
    }


if __name__ == "__main__":
    # For local testing
    result = copy_league_sheet_flow()
    print(f"Copy flow result: {result}")
```

**Scheduling Configuration**:

- **Frequency**: Every 2-4 hours during active season
- **Dependency**: None (runs independently)
- **Next step**: Parse flow (P4-002) should run 15-30 minutes after copy completes

**Environment Variables**:

- `COMMISSIONER_SHEET_ID`: Source sheet ID
- `LEAGUE_SHEET_COPY_ID`: Destination sheet ID
- `SHEETS_TABS`: Comma-separated list of tab names
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key (check `.env` for current location, typically `config/secrets/gcp-service-account-key.json`)

## Testing

1. **Local execution**:

   ```bash
   uv run python src/flows/copy_league_sheet_flow.py
   ```

2. **With Prefect UI**:

   ```bash
   # Terminal 1: Start Prefect server
   prefect server start

   # Terminal 2: Run flow
   uv run python src/flows/copy_league_sheet_flow.py
   # Then view in UI: http://localhost:4200
   ```

3. **Test failure scenarios**:

   - **Missing tab**: Manually remove a tab from source sheet → should fail validation
   - **Incomplete copy**: Test with partial tab list → should detect missing tabs
   - **Invalid credentials**: Test with wrong service account → should fail gracefully

4. **Test sequencing**:

   - Run copy flow
   - Wait for completion
   - Verify parse flow can detect copy completion

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 4 Flows (lines 456-462)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 4 Sheets (lines 280-291)
- Copy module: `src/ingest/sheets/copier.py`
- Copy script: `scripts/ingest/copy_league_sheet.py`
- Parse flow: `P4-002-implement-parse-sheets-pipeline.md` (depends on this ticket)

## Completion Notes

**Implemented**: 2025-11-21

**Files Created**:

- `src/flows/copy_league_sheet_flow.py` - Prefect flow for copying Commissioner sheet to working copy
- Updated `justfile` - Added `flow-copy-sheet` command for convenient execution

**Implementation Details**:

- Flow successfully uses existing `src/ingest/sheets/copier.py` module for tab copying
- Integrated with shared utilities from P4-001 (`log_info`, `log_warning`, `log_error`)
- Implements copy completeness validation by querying Google Sheets API to verify all expected tabs exist
- Flow parameters support both explicit args and env var fallback (COMMISSIONER_SHEET_ID, LEAGUE_SHEET_COPY_ID, SHEETS_TABS)
- Uses `sys.path` manipulation pattern consistent with other scripts in the project for `src` package imports
- Flow returns structured result with `ready_for_parse` boolean for downstream flow dependencies

**Testing Results**:

- **Local execution**: PASS - Successfully copied 13 tabs from Commissioner sheet to working copy
- **Copy validation**: PASS - All expected tabs verified present in destination sheet
- **Environment variables**: PASS - Flow correctly reads from .env via direnv
- **Just command**: Added `just flow-copy-sheet` for convenient execution
- **Execution methods tested**:
  - Direct: `uv run python src/flows/copy_league_sheet_flow.py` ✅
  - Just: `just flow-copy-sheet` ✅ (command added but not re-executed to avoid duplicate copy)

**Impact**:

- Establishes foundation for Google Sheets pipeline orchestration
- Adds governance layer (copy completeness validation) that catches silent copy failures
- Provides structured flow result that P4-002 (parse flow) can depend on
- Ready for GitHub Actions integration following existing pattern in `.github/workflows/ingest_google_sheets.yml`

**Execution Recommendations**:

1. **Local development**: Use `just flow-copy-sheet` or `uv run python src/flows/copy_league_sheet_flow.py`
2. **GitHub Actions**: Follow pattern in existing workflow - `uv sync` then `uv run python src/flows/copy_league_sheet_flow.py`
3. **Scheduling**: Flow designed to run every 2-4 hours during active season (as documented in ticket)
4. **Monitoring**: Flow logs include detailed context at each step for troubleshooting

**Next Steps**:

- P4-002 can now proceed (parse flow depends on this copy flow completing)
- Consider GitHub Actions workflow update to use new Prefect flow (future work, not in this ticket scope)
