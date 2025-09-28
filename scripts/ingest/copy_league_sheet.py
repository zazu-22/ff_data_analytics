# copy_league_sheet.py
"""
Programmatically copy specific tabs from the heavy “commissioner” workbook
to a destination workbook via server-side copyTo, freeze to values, and do
atomic rename + protection + metadata + logging.

Now wired to the helpers in `google_drive_helper.py` for:
- Drive client creation
- Drive modifiedTime checks
- Folder path resolution / creation
- Creating (or locating) a log spreadsheet inside a Drive folder
- Moving files into folders (optional)

Usage
-----
- Configure the constants below, or override via environment variables.
- Service account must have Viewer on SOURCE and Editor on DEST and on the
  target logs folder (if using a separate log workbook).

Env overrides (optional)
------------------------
# Commissioner's Google Sheet ID (source sheet)
COMMISSIONER_SHEET_ID="1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY"
# Owner tab names
OWNER_TABS="Eric,Gordon,Joe,JP,Andy,Chip,McCreary,TJ,James,Jason,Kevin,Piper"
# Google Sheet ID for for leage_sheet_copy (destination)
LEAGUE_SHEET_COPY_ID="1HktJj-VB5Rc35U6EXQJLwa_h4ytiur6A8QSJGN0tRy0"
# Set to "1" or "true" to skip run if source sheet unchanged since last run
ENTIRE_RUN_SKIP_IF_UNCHANGED=1
# Configure pause between tab copy
PAUSE_BETWEEN_TABS_SEC=0.5
# Number of rows and columns to confirm
CHECKSUM_ROWS=50
CHECKSUM_COLS=50
# Set to "1" or "true" to enable separate logs workbook
LOG_IN_SEPARATE_SHEET=1
# Drive folder ID of the project root folder
LOG_PARENT_ID="1mvfnVtbWkf96U8jEbgbOJe2FZEHPovna"
# Subfolder pathname for where log workbook is stored
LOG_FOLDER_PATH="data/raw"
LOG_SHEET_BASENAME="league_sheet_ingest_logs"
"""

import hashlib
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from typing import cast

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound
from gspread.spreadsheet import Spreadsheet
from gspread.worksheet import ValueRenderOption
from rich.pretty import pprint

# Load environment variables from .env file
load_dotenv()

# === Import helpers ===
try:
    # Preferred when running as a module (e.g. python -m scripts.ingest.copy_league_sheet_v2)
    from ff_analytics_utils import (
        build_drive,
        ensure_folder,
        ensure_spreadsheet_in_folder,
        get_drive_info,
        get_file_metadata,
        get_file_modified_time_utc,
        is_shared_drive,
        parse_rfc3339,
    )
except Exception:
    try:
        # Preferred when package is importable from project root
        from ff_analytics_utils.google_drive_helper import (
            build_drive,
            ensure_folder,
            ensure_spreadsheet_in_folder,
            get_drive_info,
            get_file_metadata,
            get_file_modified_time_utc,
            is_shared_drive,
            parse_rfc3339,
        )
    except Exception:
        # Fallback when running the script directly; ensure script dir is on sys.path
        # os and sys are already imported at the top of this module; reuse them here.
        sys.path.insert(0, os.path.dirname(__file__))
        from ff_analytics_utils.google_drive_helper import (
            build_drive,
            ensure_folder,
            ensure_spreadsheet_in_folder,
            get_drive_info,
            get_file_metadata,
            get_file_modified_time_utc,
            is_shared_drive,
            parse_rfc3339,
        )

# -----------------------
# Summary Helpers
# -----------------------


def _resolve_parents(drive, parent_ids: list[str] | None):
    """Return [{'id':..., 'name':...}, ...] for parent folders; tolerates missing perms.
    Accepts None when the metadata has no 'parents' field."""
    out = []
    for pid in parent_ids or []:
        try:
            meta = drive.files().get(fileId=pid, fields="id,name").execute()
            out.append({"id": meta.get("id"), "name": meta.get("name")})
        except Exception:
            out.append({"id": pid, "name": None})
    return out


def print_run_summary(
    *,
    run_id: str,
    started_iso: str,
    finished_iso: str,
    src_sheet_id: str,
    dst_sheet_id: str,
    drive,
    separate_logs: bool,
    logs_folder_id: str | None,
    logs_folder_path: str | None,
    log_file_id: str | None,
    src_modified_iso: str,
    stats: dict[str, int],
    tab_results: list[dict[str, object]],
):
    # File metadata + parents (names if visible)
    src_meta = get_file_metadata(drive, src_sheet_id, fields="id,name,parents,modifiedTime,version")
    dst_meta = get_file_metadata(drive, dst_sheet_id, fields="id,name,parents,modifiedTime,version")
    src_parents = _resolve_parents(drive, src_meta.get("parents"))
    dst_parents = _resolve_parents(drive, dst_meta.get("parents"))

    payload = {
        "run": {
            "run_id": run_id,
            "started_at_utc": started_iso,
            "finished_at_utc": finished_iso,
            "source_modifiedTime_utc": src_modified_iso,
        },
        "source_spreadsheet": {
            "id": src_meta.get("id"),
            "name": src_meta.get("name"),
            "parents": src_parents,
            "modifiedTime": src_meta.get("modifiedTime"),
            "version": src_meta.get("version"),
        },
        "destination_spreadsheet": {
            "id": dst_meta.get("id"),
            "name": dst_meta.get("name"),
            "parents": dst_parents,
            "modifiedTime": dst_meta.get("modifiedTime"),
            "version": dst_meta.get("version"),
        },
        "logging": {
            "separate_log_workbook": bool(separate_logs),
            "log_folder_id": logs_folder_id,
            "log_folder_path": logs_folder_path,
            "log_spreadsheet_id": log_file_id if separate_logs else dst_sheet_id,
        },
        "stats": {
            "tabs_total": len(tab_results),
            "copied": stats.get("copied", 0),
            "skipped": stats.get("skipped", 0),
            "errors": stats.get("errors", 0),
        },
        "tabs": tab_results,  # per-tab status summaries
    }

    print("\n===== League Sheets Copy Summary =====")
    # Pretty-print but keep it compact
    pprint(payload)
    print("===== End Summary =====\n")


# ------------------------------------


# -----------------------
# CONFIG (can be overridden by env)
# -----------------------
COMMISSIONER_SHEET_ID: str = os.getenv(
    "COMMISSIONER_SHEET_ID", "1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY"
)
LEAGUE_SHEET_COPY_ID: str = os.getenv(
    "LEAGUE_SHEET_COPY_ID", "1HktJj-VB5Rc35U6EXQJLwa_h4ytiur6A8QSJGN0tRy0"
)

DEFAULT_TABS: list[str] = [
    "Eric",
    "Gordon",
    "Joe",
    "JP",
    "Andy",
    "Chip",
    "McCreary",
    "TJ",
    "James",
    "Jason",
    "Kevin",
    "Piper",
]
TABS_TO_COPY: list[str] = [
    t.strip() for t in os.getenv("OWNER_TABS", "").split(",") if t.strip()
] or DEFAULT_TABS

# Logging destination
LOG_IN_SEPARATE_SPREADSHEET: bool = os.getenv("LOG_IN_SEPARATE_SHEET", "").lower() in {
    "1",
    "true",
    "yes",
    "y",
}
LOG_PARENT_ID: str = os.getenv("LOG_PARENT_ID", "root")
LOG_FOLDER_PATH: str = os.getenv("LOG_FOLDER_PATH", "BellKeg/Logs/Prod")
LOG_SHEET_BASENAME: str = os.getenv("LOG_SHEET_BASENAME", "BK_INGEST_LOGS")

# Behavior
ENTIRE_RUN_SKIP_IF_UNCHANGED: bool = os.getenv("ENTIRE_RUN_SKIP_IF_UNCHANGED", "").lower() in {
    "1",
    "true",
    "yes",
    "y",
}
PAUSE_BETWEEN_TABS_SEC = float(os.getenv("PAUSE_BETWEEN_TABS_SEC", "0.5"))
CHECKSUM_ROWS = int(os.getenv("CHECKSUM_ROWS", "60"))
CHECKSUM_COLS = int(os.getenv("CHECKSUM_COLS", "20"))

# Sheet-local names
LOG_SHEET_NAME = "BK_INGEST_LOG"
STATE_SHEET_NAME = "BK_STATE"

# Service account location (env may point elsewhere)
GOOGLE_APPLICATION_CREDENTIALS: str = (
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    or "config/secrets/gcp-service-account-key.json"
)

SCOPES: list[str] = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# -----------------------
# Utility helpers (local)
# -----------------------
def ensure_log_sheet(spreadsheet: Spreadsheet, name=LOG_SHEET_NAME):
    try:
        ws = spreadsheet.worksheet(name)
        # Check if we need to add the new column for existing sheets
        headers = ws.row_values(1) if ws.row_count > 0 else []
        if headers and "src_modifiedTime_utc" not in headers:
            # Add the new column header
            col_index = len(headers) + 1
            ws.update_cell(1, col_index, "src_modifiedTime_utc")
    except WorksheetNotFound:
        ws = spreadsheet.add_worksheet(name, rows=5000, cols=20)
        ws.append_row(
            [
                "run_id",
                "tab",
                "status",
                "started_at_utc",
                "finished_at_utc",
                "duration_ms",
                "src_sheet_id",
                "src_tab_title",
                "dst_sheet_id",
                "dst_tab_id",
                "rows",
                "cols",
                "checksum",
                "src_modifiedTime_utc",
            ]
        )
    return ws


def ensure_state_sheet(spreadsheet: Spreadsheet, name=STATE_SHEET_NAME):
    try:
        ws = spreadsheet.worksheet(name)
    except WorksheetNotFound:
        ws = spreadsheet.add_worksheet(name, rows=100, cols=4)
        ws.append_row(["key", "value"])
    return ws


def state_get(ws, key: str):
    vals = ws.get_all_values()
    for row in vals[1:]:
        if len(row) >= 2 and row[0] == key:
            return row[1]
    return None


def state_set(ws, key: str, value: str) -> None:
    vals = ws.get_all_values()
    for r, row in enumerate(vals[1:], start=2):
        if len(row) >= 2 and row[0] == key:
            ws.update_cell(r, 2, value)
            return
    ws.append_row([key, value])


def last_success_utc_by_tab(log_ws) -> dict[str, datetime]:
    out: dict[str, datetime] = {}
    rows = log_ws.get_all_values()
    if not rows:
        return out
    hdr = rows[0]
    idx_tab = hdr.index("tab")
    idx_status = hdr.index("status")
    idx_finished = hdr.index("finished_at_utc")
    for row in rows[1:]:
        if len(row) <= max(idx_tab, idx_status, idx_finished):
            continue
        tab = row[idx_tab]
        status = row[idx_status]
        if not status.startswith("OK"):
            continue
        try:
            ts = parse_rfc3339(row[idx_finished])
        except Exception:
            continue
        if tab not in out or ts > out[tab]:
            out[tab] = ts
    return out


def log_row(log_ws, **k) -> None:
    log_ws.append_row(
        [
            k.get("run_id"),
            k.get("tab"),
            k.get("status"),
            k.get("started_at"),
            k.get("finished_at"),
            k.get("duration_ms"),
            k.get("src_sheet_id"),
            k.get("src_tab_title"),
            k.get("dst_sheet_id"),
            k.get("dst_tab_id"),
            k.get("rows"),
            k.get("cols"),
            k.get("checksum"),
            k.get("src_modifiedTime_utc"),
        ],
        value_input_option="RAW",
    )


def a1(r: int, c: int) -> str:
    return gspread.utils.rowcol_to_a1(r, c)


# -----------------------
# Main
# -----------------------
def main() -> int:
    # Auth
    creds = Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS, scopes=SCOPES)
    gc = gspread.authorize(creds)
    drive = build_drive(creds)
    gc.set_timeout((10, 180))  # (connect, read)

    # Open spreadsheets
    try:
        src = gc.open_by_key(COMMISSIONER_SHEET_ID)
    except Exception as e:
        print(f"ERROR: cannot open SOURCE spreadsheet: {e}", file=sys.stderr)
        sys.exit(2)
    try:
        dst = gc.open_by_key(LEAGUE_SHEET_COPY_ID)
    except Exception as e:
        print(f"ERROR: cannot open DEST spreadsheet: {e}", file=sys.stderr)
        sys.exit(2)

    # Decide where logs live
    separate_logs_enabled = LOG_IN_SEPARATE_SPREADSHEET
    folder_id = None
    log_file_id = None

    if separate_logs_enabled:
        try:
            # Check if we're working with a Shared Drive
            if is_shared_drive(LOG_PARENT_ID):
                drive_info = get_drive_info(drive, LOG_PARENT_ID)
                if drive_info:
                    print(f"Using Shared Drive: {drive_info.get('name')} ({LOG_PARENT_ID})")
                else:
                    print(f"Using Shared Drive: {LOG_PARENT_ID}")

            # Create or find the folder path
            folder_id = ensure_folder(
                drive, LOG_FOLDER_PATH, parent_id=LOG_PARENT_ID, create_missing=True
            )
            print(f"Using log folder at path: {LOG_FOLDER_PATH}")

            # Create or find the spreadsheet in the folder
            log_file_id = ensure_spreadsheet_in_folder(drive, folder_id, LOG_SHEET_BASENAME)
            logs_ss = gc.open_by_key(log_file_id)
            print(f"Using log spreadsheet: {LOG_SHEET_BASENAME}")
        except Exception as e:
            print(f"WARNING: Could not create/access separate log sheet: {e}", file=sys.stderr)
            print("Falling back to using destination sheet for logging.", file=sys.stderr)
            logs_ss = dst
            separate_logs_enabled = False  # Update flag for summary
    else:
        logs_ss = dst

    log_ws = ensure_log_sheet(logs_ss)
    state_ws = ensure_state_sheet(logs_ss)

    # Drive file-level modifiedTime
    src_modified_utc, src_meta = get_file_modified_time_utc(drive, COMMISSIONER_SHEET_ID)

    # Whole-run skip (optional)
    prev_src_mtime = state_get(state_ws, "src_modifiedTime_utc")
    if ENTIRE_RUN_SKIP_IF_UNCHANGED and prev_src_mtime:
        try:
            prev_dt: datetime = parse_rfc3339(prev_src_mtime)
            if prev_dt >= src_modified_utc:
                print(f"[SKIP] Source workbook unchanged since {prev_dt.isoformat()} – exiting.")

                # Log the whole-run skip
                run_id: str = uuid.uuid4().hex
                started_iso = datetime.now(UTC).isoformat()
                log_row(
                    log_ws,
                    run_id=run_id,
                    tab="[ENTIRE_RUN]",  # Special marker for whole-run entries
                    status="SKIP_UNCHANGED",
                    started_at=started_iso,
                    finished_at=started_iso,  # Same as start for skipped runs
                    duration_ms=0,
                    src_sheet_id=COMMISSIONER_SHEET_ID,
                    src_tab_title="[ALL]",
                    dst_sheet_id=LEAGUE_SHEET_COPY_ID,
                    dst_tab_id=None,
                    rows=None,
                    cols=None,
                    checksum=None,
                    src_modifiedTime_utc=src_modified_utc.isoformat(),
                )
                return 0
        except Exception:
            pass

    # Source worksheets (metadata only)
    src_map = {ws.title: ws for ws in src.worksheets()}

    # Last per-tab OK
    last_ok_map: dict[str, datetime] = last_success_utc_by_tab(log_ws)

    run_id: str = uuid.uuid4().hex
    print(f"Starting BK extract run {run_id} at {datetime.now(UTC).isoformat()}")

    run_started_iso = datetime.now(UTC).isoformat()

    stats: dict[str, int] = {"copied": 0, "skipped": 0, "errors": 0}
    tab_results: list[dict[str, object]] = []  # collect brief per-tab records for the summary

    for title in TABS_TO_COPY:
        # Per-tab skip: if we already refreshed this tab at/after the file's modifiedTime, skip it
        last_ok: datetime | None = last_ok_map.get(title)
        if last_ok and last_ok >= src_modified_utc:
            message = (
                f"[SKIP] {title}: already refreshed at {last_ok.isoformat()} "
                f"(src modified {src_modified_utc.isoformat()})"
            )
            print(message)

            # Log the individual tab skip
            skip_time = datetime.now(UTC).isoformat()
            log_row(
                log_ws,
                run_id=run_id,
                tab=title,
                status="SKIP_CURRENT",
                started_at=skip_time,
                finished_at=skip_time,
                duration_ms=0,
                src_sheet_id=COMMISSIONER_SHEET_ID,
                src_tab_title=title,
                dst_sheet_id=LEAGUE_SHEET_COPY_ID,
                dst_tab_id=None,
                rows=None,
                cols=None,
                checksum=None,
                src_modifiedTime_utc=src_modified_utc.isoformat(),
            )

            tab_results.append(
                {
                    "tab": title,
                    "status": "SKIP",
                    "reason": "unchanged_since_source_modifiedTime",
                }
            )
            stats["skipped"] += 1

            continue

        t0 = time.perf_counter()
        started_iso = datetime.now(UTC).isoformat()
        status = "OK"
        checksum = ""
        dst_tab_id = None
        rows = cols = None
        new_id = None

        try:
            if title not in src_map:
                raise WorksheetNotFound(f"Source tab '{title}' not found")

            src_ws = src_map[title]

            # 1) Server-side copyTo (no value reads)
            new_props = src_ws.copy_to(LEAGUE_SHEET_COPY_ID)  # returns dict with 'sheetId'
            new_id = new_props["sheetId"]

            # Get the new sheet by id
            new_ws = next(w for w in dst.worksheets() if w.id == new_id)
            temp_name = f"__incoming_{title}_{run_id[:8]}"
            new_ws.update_title(temp_name)

            # Grid size
            rows, cols = new_ws.row_count, new_ws.col_count

            # Detect old tab
            old_id = None
            try:
                old_ws = dst.worksheet(title)
                old_id = old_ws.id
            except WorksheetNotFound:
                pass

            # 2) Atomic batchUpdate
            now_iso = datetime.now(UTC).isoformat()
            requests = [
                {  # Freeze formulas -> values
                    "copyPaste": {
                        "source": {
                            "sheetId": new_id,
                            "startRowIndex": 0,
                            "endRowIndex": rows,
                            "startColumnIndex": 0,
                            "endColumnIndex": cols,
                        },
                        "destination": {
                            "sheetId": new_id,
                            "startRowIndex": 0,
                            "startColumnIndex": 0,
                        },
                        "pasteType": "PASTE_VALUES",
                        "pasteOrientation": "NORMAL",
                    }
                },
                *([{"deleteSheet": {"sheetId": old_id}}] if old_id is not None else []),
                {  # Rename
                    "updateSheetProperties": {
                        "properties": {"sheetId": new_id, "title": title},
                        "fields": "title",
                    }
                },
                # Developer metadata for observability
                {
                    "createDeveloperMetadata": {
                        "developerMetadata": {
                            "metadataKey": "bk_last_refresh_iso",
                            "metadataValue": now_iso,
                            "visibility": "DOCUMENT",
                            "location": {"sheetId": new_id},
                        }
                    }
                },
                {
                    "createDeveloperMetadata": {
                        "developerMetadata": {
                            "metadataKey": "bk_source_spreadsheet_id",
                            "metadataValue": COMMISSIONER_SHEET_ID,
                            "visibility": "DOCUMENT",
                            "location": {"sheetId": new_id},
                        }
                    }
                },
                {
                    "createDeveloperMetadata": {
                        "developerMetadata": {
                            "metadataKey": "bk_source_tab_title",
                            "metadataValue": title,
                            "visibility": "DOCUMENT",
                            "location": {"sheetId": new_id},
                        }
                    }
                },
                {
                    "createDeveloperMetadata": {
                        "developerMetadata": {
                            "metadataKey": "bk_run_id",
                            "metadataValue": run_id,
                            "visibility": "DOCUMENT",
                            "location": {"sheetId": new_id},
                        }
                    }
                },
                {
                    "createDeveloperMetadata": {
                        "developerMetadata": {
                            "metadataKey": "bk_src_modifiedTime_utc",
                            "metadataValue": get_file_metadata(
                                drive, COMMISSIONER_SHEET_ID, "modifiedTime"
                            )["modifiedTime"],
                            "visibility": "DOCUMENT",
                            "location": {"sheetId": new_id},
                        }
                    }
                },
                {  # Warning-only protection
                    "addProtectedRange": {
                        "protectedRange": {
                            "range": {"sheetId": new_id},
                            "description": "Values-only extract – prefer editing the source sheet.",
                            "warningOnly": True,
                        }
                    }
                },
            ]

            dst.batch_update({"requests": requests})

            # 3) Lightweight checksum (DEST only)
            rng = f"{a1(1, 1)}:{a1(min(CHECKSUM_ROWS, rows), min(CHECKSUM_COLS, cols))}"
            # ValueRenderOption is a typing Literal; cast the string to satisfy type checkers
            top = dst.worksheet(title).get(
                rng, value_render_option=cast(ValueRenderOption, "UNFORMATTED_VALUE")
            )
            m = hashlib.sha256()
            for r in top:
                m.update(("|".join(str(c) for c in r)).encode("utf-8"))
            checksum = m.hexdigest()[:16]

            dst_tab_id = new_id

        except Exception as e:
            status = f"ERROR: {type(e).__name__}: {e}"

            # Cleanup temp sheet if created (best-effort)
            if new_id is not None:
                try:
                    dst.batch_update({"requests": [{"deleteSheet": {"sheetId": new_id}}]})
                except Exception:
                    # ignore cleanup errors
                    pass

        finally:
            finished_iso = datetime.now(UTC).isoformat()
            duration_ms = int((time.perf_counter() - t0) * 1000)
            log_row(
                log_ws,
                run_id=run_id,
                tab=title,
                status=status,
                started_at=started_iso,
                finished_at=finished_iso,
                duration_ms=duration_ms,
                src_sheet_id=COMMISSIONER_SHEET_ID,
                src_tab_title=title,
                dst_sheet_id=LEAGUE_SHEET_COPY_ID,
                dst_tab_id=dst_tab_id,
                rows=rows,
                cols=cols,
                checksum=checksum,
                src_modifiedTime_utc=src_modified_utc.isoformat(),
            )
            if status == "OK":
                stats["copied"] += 1
            else:
                stats["errors"] += 1

            tab_results.append(
                {
                    "tab": title,
                    "status": status if status != "OK" else "COPIED",
                    "dst_tab_id": dst_tab_id,
                    "rows": rows,
                    "cols": cols,
                    "duration_ms": duration_ms,
                    "checksum16": checksum,
                }
            )

            time.sleep(PAUSE_BETWEEN_TABS_SEC)

    # Persist last seen source modifiedTime (for whole-run skip next time)
    state_set(state_ws, "src_modifiedTime_utc", src_modified_utc.isoformat())

    finished_iso: str = datetime.now(UTC).isoformat()

    # Add a run summary entry if this was a forced run where everything was skipped
    # (Different from the whole-run skip at the beginning which exits early)
    if (
        not ENTIRE_RUN_SKIP_IF_UNCHANGED
        and stats["skipped"] == len(TABS_TO_COPY)
        and stats["copied"] == 0
    ):
        # This was a forced run but all tabs were already current
        log_row(
            log_ws,
            run_id=run_id,
            tab="[RUN_SUMMARY]",
            status="FORCED_RUN_ALL_CURRENT",
            started_at=run_started_iso,
            finished_at=finished_iso,
            duration_ms=int(
                (datetime.now(UTC) - datetime.fromisoformat(run_started_iso)).total_seconds() * 1000
            ),
            src_sheet_id=COMMISSIONER_SHEET_ID,
            src_tab_title="[ALL]",
            dst_sheet_id=LEAGUE_SHEET_COPY_ID,
            dst_tab_id=None,
            rows=None,
            cols=None,
            checksum=None,
            src_modifiedTime_utc=src_modified_utc.isoformat(),
        )

    # Use the separate_logs_enabled flag which may have been updated if fallback occurred
    separate_logs: bool = separate_logs_enabled

    # These variables were set earlier in the script
    logs_folder_id: str | None = folder_id
    logs_folder_path: str | None = LOG_FOLDER_PATH  # Use the constant defined at the top
    # log_file_id is already defined above

    # Print the summary
    print_run_summary(
        run_id=run_id,
        started_iso=run_started_iso,
        finished_iso=finished_iso,
        src_sheet_id=COMMISSIONER_SHEET_ID,
        dst_sheet_id=LEAGUE_SHEET_COPY_ID,
        drive=drive,
        separate_logs=separate_logs,
        logs_folder_id=logs_folder_id,
        logs_folder_path=logs_folder_path,
        log_file_id=log_file_id,
        src_modified_iso=src_modified_utc.isoformat(),
        stats=stats,
        tab_results=tab_results,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
