"""Sheets copier core logic (library API).

Provides a testable function to copy selected tabs from a source spreadsheet
to a destination spreadsheet using the Google Sheets API `copyTo` method, with
optional value-only conversion.

High-level API:
- `copy_league_sheet(src_sheet_id, dst_sheet_id, tabs, options)`

Credentials:
- Uses `google.oauth2.service_account.Credentials` built from either
  `GOOGLE_APPLICATION_CREDENTIALS_JSON` (inline JSON) or
  `GOOGLE_APPLICATION_CREDENTIALS` (path). You can also pass a premade
  credentials object.

This module does not print or do I/O — callers can log/print as desired.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


@dataclass
class CopyOptions:
    """Options controlling tab copy behavior."""

    paste_values_only: bool = True
    pause_between_tabs_sec: float = 0.0  # caller can sleep


def _load_credentials(creds: Any | None):
    if creds is not None:
        return creds
    import json
    import os

    from google.oauth2.service_account import Credentials

    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_json:
        info = json.loads(creds_json)
        return Credentials.from_service_account_info(info, scopes=[SHEETS_SCOPE])
    if creds_path:
        return Credentials.from_service_account_file(creds_path, scopes=[SHEETS_SCOPE])
    raise RuntimeError(
        "Missing credentials: set GOOGLE_APPLICATION_CREDENTIALS_JSON or "
        "GOOGLE_APPLICATION_CREDENTIALS"
    )


def _get_sheet_id_by_title(svc, spreadsheet_id: str, title: str) -> int | None:
    meta = (
        svc.spreadsheets().get(spreadsheetId=spreadsheet_id, fields="sheets.properties").execute()
    )
    for s in meta.get("sheets", []):
        props = s.get("properties", {})
        if props.get("title") == title:
            return int(props.get("sheetId"))
    return None


def _get_sheet_grid_size(svc, spreadsheet_id: str, sheet_id: int) -> tuple[int, int]:
    meta = (
        svc.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets(properties(sheetId,gridProperties))")
        .execute()
    )
    for s in meta.get("sheets", []):
        props = s.get("properties", {})
        if int(props.get("sheetId")) == sheet_id:
            gp = props.get("gridProperties", {})
            return int(gp.get("rowCount", 1000)), int(gp.get("columnCount", 26))
    return 1000, 26


def _paste_values_over_self(svc, spreadsheet_id: str, sheet_id: int) -> None:
    rows, cols = _get_sheet_grid_size(svc, spreadsheet_id, sheet_id)
    rng = {
        "sheetId": sheet_id,
        "startRowIndex": 0,
        "endRowIndex": rows,
        "startColumnIndex": 0,
        "endColumnIndex": cols,
    }
    req = {
        "copyPaste": {
            "source": rng,
            "destination": rng,
            "pasteType": "PASTE_VALUES",
            "pasteOrientation": "NORMAL",
        }
    }
    svc.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": [req]}).execute()


def copy_league_sheet(
    src_sheet_id: str,
    dst_sheet_id: str,
    tabs: Iterable[str],
    options: CopyOptions | None = None,
    *,
    credentials: Any | None = None,
) -> dict[str, Any]:
    """Copy tabs by title from `src_sheet_id` into `dst_sheet_id`.

    Returns a summary dict with per-tab results.
    """
    options = options or CopyOptions()
    creds = _load_credentials(credentials)
    svc = build("sheets", "v4", credentials=creds, cache_discovery=False)

    results: list[dict[str, Any]] = []
    copied = skipped = failed = 0

    for title in tabs:
        try:
            sheet_id = _get_sheet_id_by_title(svc, src_sheet_id, title)
            if sheet_id is None:
                results.append({"tab": title, "status": "skip", "reason": "not found in source"})
                skipped += 1
                continue
            # Copy the sheet into destination
            resp = (
                svc.spreadsheets()
                .sheets()
                .copyTo(
                    spreadsheetId=src_sheet_id,
                    sheetId=sheet_id,
                    body={"destinationSpreadsheetId": dst_sheet_id},
                )
                .execute()
            )
            new_sheet_id = int(resp.get("sheetId"))
            if options.paste_values_only:
                _paste_values_over_self(svc, dst_sheet_id, new_sheet_id)
            results.append({"tab": title, "status": "copied", "new_sheet_id": new_sheet_id})
            copied += 1
        except HttpError as e:
            results.append({"tab": title, "status": "error", "http_error": str(e)})
            failed += 1
        except Exception as e:  # pragma: no cover - defensive
            results.append({"tab": title, "status": "error", "error": str(e)})
            failed += 1

    return {"copied": copied, "skipped": skipped, "errors": failed, "tabs": results}
