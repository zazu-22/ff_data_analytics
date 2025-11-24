"""Prefect flow for copying Commissioner sheet to working copy.

This flow copies all tabs from the Commissioner sheet to a working copy
for downstream parsing (P4-002b). Uses paste-values-only to avoid formula errors.

Architecture:
    1. Copy all tabs via Google Sheets API (batch operation)
    2. Validate all expected tabs were copied (governance)

Dependencies:
    - src/ingest/sheets/copier.py (sheet copy logic)
    - Google Sheets API v4

Production Hardening:
    - copy_league_sheet_tabs: 3 retries with 60s delay, 3min timeout (handles API transients)
    - validate_copy_completeness: 2 retries with 30s delay, 2min timeout (handles API transients)
"""

import os
import sys
from pathlib import Path

# Ensure src package is importable
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from google.oauth2 import service_account  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402
from prefect import flow, task  # noqa: E402

from src.flows.utils.notifications import log_error, log_info, log_warning  # noqa: E402
from src.ingest.sheets.copier import CopyOptions, copy_league_sheet  # noqa: E402


@task(
    name="copy_league_sheet_tabs",
    retries=3,
    retry_delay_seconds=60,
    timeout_seconds=180,
    tags=["external_api"],
)
def copy_tabs_task(src_sheet_id: str, dst_sheet_id: str, tabs: list[str]) -> dict:
    """Copy tabs from source sheet to destination sheet.

    Args:
        src_sheet_id: Commissioner sheet ID (from env var)
        dst_sheet_id: Working copy sheet ID (from env var)
        tabs: List of tab names to copy

    Returns:
        Copy results summary

    """
    log_info(
        "Starting sheet copy operation",
        context={"src_sheet_id": src_sheet_id, "dst_sheet_id": dst_sheet_id, "tabs": tabs},
    )

    # Use existing copier module
    result = copy_league_sheet(
        src_sheet_id=src_sheet_id,
        dst_sheet_id=dst_sheet_id,
        tabs=tabs,
        options=CopyOptions(paste_values_only=True),
    )

    if result["errors"] > 0:
        log_error("Sheet copy failed", context={"result": result})
    elif result["skipped"] > 0:
        log_warning("Some tabs skipped during copy", context={"result": result})
    else:
        log_info("All tabs copied successfully", context={"copied_count": result["copied"]})

    return result


@task(
    name="validate_copy_completeness",
    retries=2,
    retry_delay_seconds=30,
    timeout_seconds=120,
    tags=["external_api"],
)
def validate_copy_completeness(expected_tabs: list[str], copied_sheet_id: str) -> dict:
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
    # Build sheets service
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    service = build("sheets", "v4", credentials=credentials)

    # Get tabs from copied sheet
    sheet_metadata = service.spreadsheets().get(spreadsheetId=copied_sheet_id).execute()
    copied_tabs = [sheet["properties"]["title"] for sheet in sheet_metadata.get("sheets", [])]

    # Check for missing tabs
    missing_tabs = [tab for tab in expected_tabs if tab not in copied_tabs]

    if missing_tabs:
        log_error(
            "Sheets copy incomplete - missing tabs",
            context={
                "expected_tabs": expected_tabs,
                "copied_tabs": copied_tabs,
                "missing_tabs": missing_tabs,
                "sheet_id": copied_sheet_id,
            },
        )
        return {"valid": False, "missing_tabs": missing_tabs, "copied_tabs": copied_tabs}

    log_info(
        "All expected tabs copied successfully",
        context={"tab_count": len(expected_tabs), "tabs": copied_tabs},
    )
    return {"valid": True, "missing_tabs": [], "copied_tabs": copied_tabs}


@flow(name="copy_league_sheet_flow")
def copy_league_sheet_flow(
    src_sheet_id: str | None = None,
    dst_sheet_id: str | None = None,
    tabs: list[str] | None = None,
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

    log_info(
        "Starting copy_league_sheet_flow",
        context={"src_sheet_id": src_sheet_id, "dst_sheet_id": dst_sheet_id, "tabs": tabs},
    )

    # Copy tabs
    copy_result = copy_tabs_task(src_sheet_id, dst_sheet_id, tabs)

    # Validate copy completeness
    validation_result = validate_copy_completeness(tabs, dst_sheet_id)

    if not validation_result["valid"]:
        log_error(
            "Copy flow failed - incomplete copy detected",
            context={"missing_tabs": validation_result["missing_tabs"]},
        )
        # Flow will fail here due to log_error raising exception

    log_info(
        "Copy flow completed successfully",
        context={"copied_tabs": copy_result["copied"], "validation": "passed"},
    )

    return {
        "copy_result": copy_result,
        "validation_result": validation_result,
        "ready_for_parse": validation_result["valid"],
    }


if __name__ == "__main__":
    # For local testing
    result = copy_league_sheet_flow()
    print(f"Copy flow result: {result}")
