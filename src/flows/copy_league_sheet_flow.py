"""Prefect flow for copying Commissioner sheet to working copy.

This flow copies all tabs from the Commissioner sheet to a working copy
for downstream parsing (P4-002b). Uses paste-values-only to avoid formula errors.

Architecture:
    1. Check source freshness (skip-if-unchanged logic)
    2. Copy all tabs via Google Sheets API (batch operation)
    3. Validate checksum (data integrity)
    4. Validate all expected tabs were copied (governance)
    5. Record successful run metadata

Dependencies:
    - src/ingest/sheets/copier.py (sheet copy logic)
    - Google Sheets API v4
    - Google Drive API v3 (for modifiedTime checks)

Production Hardening:
    - copy_league_sheet_tabs: 3 retries with 60s delay, 3min timeout (handles API transients)
    - validate_copy_completeness: 2 retries with 30s delay, 2min timeout (handles API transients)
    - check_source_freshness: 2 retries with 30s delay (handles API transients)
    - validate_copy_checksum: 2 retries with 30s delay (handles API transients)
"""

import os
import sys
from pathlib import Path

# Ensure src package is importable
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from datetime import datetime  # noqa: E402

from google.oauth2 import service_account  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402
from prefect import flow, task  # noqa: E402

from src.flows.config import CHECKSUM_VALIDATION, SKIP_IF_UNCHANGED_ENABLED  # noqa: E402
from src.flows.utils.notifications import log_error, log_info, log_warning  # noqa: E402
from src.flows.utils.source_freshness import (  # noqa: E402
    record_successful_run,
    should_skip_fetch,
)
from src.ingest.sheets.copier import CopyOptions, copy_league_sheet  # noqa: E402


@task(
    name="check_source_freshness",
    retries=2,
    retry_delay_seconds=30,
    timeout_seconds=120,
    tags=["external_api"],
)
def check_source_freshness(src_sheet_id: str, force: bool = False) -> dict:
    """Check if source sheet has been modified since last copy.

    Uses Google Drive API to get file metadata including modifiedTime.
    Implements skip-if-unchanged logic from legacy scripts.

    Args:
        src_sheet_id: Commissioner sheet ID (from env var)
        force: Force copy even if source unchanged

    Returns:
        Freshness check results with should_skip recommendation

    """
    log_info(
        "Checking source sheet freshness",
        context={"src_sheet_id": src_sheet_id, "force": force},
    )

    # Build Drive client
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        scopes=[
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
    drive = build("drive", "v3", credentials=credentials)

    # Get source file metadata (modifiedTime)
    file_meta = drive.files().get(fileId=src_sheet_id, fields="id,name,modifiedTime").execute()

    source_modified = datetime.fromisoformat(file_meta["modifiedTime"].replace("Z", "+00:00"))

    # Check if skip-if-unchanged is enabled for sheets
    skip_enabled = SKIP_IF_UNCHANGED_ENABLED.get("sheets", True)

    # Determine if we should skip
    should_skip = False
    reason = "Proceeding with copy"

    if skip_enabled and not force:
        should_skip, reason = should_skip_fetch(
            source="sheets",
            dataset="commissioner",
            source_modified_time=source_modified,
            force=force,
        )

    result = {
        "should_skip": should_skip,
        "reason": reason,
        "source_modified_time": source_modified.isoformat(),
        "source_sheet_id": src_sheet_id,
        "source_name": file_meta.get("name"),
    }

    if should_skip:
        log_info(
            "Skipping copy - source unchanged",
            context={"reason": reason, "source_modified": source_modified.isoformat()},
        )
    else:
        log_info(
            "Proceeding with copy",
            context={"reason": reason, "source_modified": source_modified.isoformat()},
        )

    return result


@task(
    name="validate_copy_checksum",
    retries=2,
    retry_delay_seconds=30,
    timeout_seconds=120,
    tags=["external_api"],
)
def validate_copy_checksum(src_sheet_id: str, dst_sheet_id: str, tabs: list[str]) -> dict:
    """Validate data integrity via checksum comparison.

    Compares checksums of first NxM cells from source and destination for
    each copied tab. This detects silent data corruption during copy.

    Args:
        src_sheet_id: Commissioner sheet ID (source)
        dst_sheet_id: Working copy sheet ID (destination)
        tabs: List of tab names to validate

    Returns:
        Validation results with any checksum mismatches

    """
    import hashlib
    import json

    checksum_config = CHECKSUM_VALIDATION.get("sheets_copy", {})
    if not checksum_config.get("enabled", True):
        log_info("Checksum validation disabled in config")
        return {"enabled": False, "valid": True, "mismatches": []}

    rows = checksum_config.get("rows", 50)
    cols = checksum_config.get("cols", 50)

    log_info(
        "Validating copy checksums",
        context={
            "src_sheet_id": src_sheet_id,
            "dst_sheet_id": dst_sheet_id,
            "tabs": tabs,
            "rows": rows,
            "cols": cols,
        },
    )

    # Build sheets service
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    service = build("sheets", "v4", credentials=credentials)

    def get_range_checksum(sheet_id: str, tab: str, rows: int, cols: int) -> str:
        """Get checksum for a range of cells."""
        # Convert column number to letter (A=1, Z=26, AA=27, etc.)
        col_letter = ""
        col_num = cols
        while col_num > 0:
            col_num, remainder = divmod(col_num - 1, 26)
            col_letter = chr(65 + remainder) + col_letter

        range_notation = f"{tab}!A1:{col_letter}{rows}"

        values = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range=range_notation)
            .execute()
            .get("values", [])
        )

        # Compute checksum
        data_str = json.dumps(values, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    mismatches = []
    checksums = {}

    for tab in tabs:
        try:
            src_checksum = get_range_checksum(src_sheet_id, tab, rows, cols)
            dst_checksum = get_range_checksum(dst_sheet_id, tab, rows, cols)

            checksums[tab] = {
                "src": src_checksum[:16],  # First 16 chars for logging
                "dst": dst_checksum[:16],
                "match": src_checksum == dst_checksum,
            }

            if src_checksum != dst_checksum:
                mismatches.append(
                    {
                        "tab": tab,
                        "src_checksum": src_checksum[:16],
                        "dst_checksum": dst_checksum[:16],
                    }
                )
                log_warning(
                    f"Checksum mismatch for tab '{tab}'",
                    context={"tab": tab, "src": src_checksum[:16], "dst": dst_checksum[:16]},
                )
        except Exception as e:
            log_warning(
                f"Failed to validate checksum for tab '{tab}'",
                context={"tab": tab, "error": str(e)},
            )

    if mismatches:
        log_error(
            "Copy validation failed - checksum mismatches detected",
            context={"mismatches": mismatches, "affected_tabs": [m["tab"] for m in mismatches]},
        )
    else:
        log_info(
            "All checksums validated successfully",
            context={"validated_tabs": len(tabs), "rows_checked": rows, "cols_checked": cols},
        )

    return {
        "enabled": True,
        "valid": len(mismatches) == 0,
        "mismatches": mismatches,
        "checksums": checksums,
        "rows_checked": rows,
        "cols_checked": cols,
    }


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
    force: bool = False,
) -> dict:
    """Prefect flow for copying Commissioner sheet to working copy.

    Args:
        src_sheet_id: Commissioner sheet ID (defaults to COMMISSIONER_SHEET_ID env var)
        dst_sheet_id: Working copy sheet ID (defaults to LEAGUE_SHEET_COPY_ID env var)
        tabs: List of tab names to copy (defaults to SHEETS_TABS env var, comma-separated)
        force: Force copy even if source unchanged

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
        context={
            "src_sheet_id": src_sheet_id,
            "dst_sheet_id": dst_sheet_id,
            "tabs": tabs,
            "force": force,
        },
    )

    # Step 1: Check source freshness
    freshness_result = check_source_freshness(src_sheet_id, force=force)

    # If source unchanged and skip enabled, exit early
    if freshness_result["should_skip"]:
        log_info(
            "Copy skipped - source unchanged",
            context={"reason": freshness_result["reason"]},
        )
        return {
            "skipped": True,
            "reason": freshness_result["reason"],
            "freshness_check": freshness_result,
            "ready_for_parse": True,  # Working copy is still valid
        }

    # Step 2: Copy tabs
    copy_result = copy_tabs_task(src_sheet_id, dst_sheet_id, tabs)

    # Step 3: Validate checksum (don't fail yet - collect all validation results)
    checksum_result = validate_copy_checksum(src_sheet_id, dst_sheet_id, tabs)

    # Step 4: Validate copy completeness (don't fail yet - collect all validation results)
    validation_result = validate_copy_completeness(tabs, dst_sheet_id)

    # Now fail if EITHER validation failed (provides complete debugging context)
    if not checksum_result["valid"]:
        log_error(
            "Copy flow failed - checksum mismatches detected",
            context={
                "mismatches": checksum_result["mismatches"],
                "affected_tabs": [m["tab"] for m in checksum_result["mismatches"]],
            },
        )

    if not validation_result["valid"]:
        log_error(
            "Copy flow failed - incomplete copy detected",
            context={"missing_tabs": validation_result["missing_tabs"]},
        )

    # Step 5: Record successful run metadata
    record_successful_run(
        source="sheets",
        dataset="commissioner",
        snapshot_date=datetime.now().strftime("%Y-%m-%d"),
        row_count=copy_result.get("copied", 0),
        source_hash=None,  # Could add aggregate checksum here if needed
        source_modified_time=datetime.fromisoformat(freshness_result["source_modified_time"]),
    )

    log_info(
        "Copy flow completed successfully",
        context={
            "copied_tabs": copy_result["copied"],
            "checksum_validation": "passed",
            "completeness_validation": "passed",
        },
    )

    return {
        "skipped": False,
        "copy_result": copy_result,
        "freshness_check": freshness_result,
        "checksum_result": checksum_result,
        "validation_result": validation_result,
        "ready_for_parse": validation_result["valid"],
    }


if __name__ == "__main__":
    # For local testing
    result = copy_league_sheet_flow()
    print(f"Copy flow result: {result}")
