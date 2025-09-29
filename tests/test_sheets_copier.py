from __future__ import annotations

from typing import Any

from ingest.sheets.copier import CopyOptions, copy_league_sheet


class _FakeCall:
    def __init__(self, response: Any | None = None):
        self._response = response or {}

    def execute(self):
        return self._response


class _FakeSheets:
    def __init__(self, parent):
        self._parent = parent
        self._copy_response = {"sheetId": 999}

    def copyTo(self, spreadsheetId: str, sheetId: int, body: dict):  # noqa: N802,N803
        self._parent._copied.append(
            {
                "spreadsheetId": spreadsheetId,
                "sheetId": sheetId,
                "body": body,
            }
        )
        return _FakeCall(self._copy_response)


class _FakeSpreadsheets:
    def __init__(self):
        self._get_response = {
            "sheets": [
                {
                    "properties": {
                        "title": "Tab1",
                        "sheetId": 123,
                        "gridProperties": {"rowCount": 10, "columnCount": 5},
                    }
                }
            ]
        }
        self._batch_updates: list[dict] = []
        self._copied: list[dict] = []

    def get(self, spreadsheetId: str, fields: str):  # noqa: N802,N803
        return _FakeCall(self._get_response)

    def batchUpdate(self, spreadsheetId: str, body: dict):  # noqa: N802,N803
        self._batch_updates.append({"spreadsheetId": spreadsheetId, "body": body})
        return _FakeCall({"ok": True})

    def sheets(self):
        return _FakeSheets(self)


class _FakeService:
    def __init__(self):
        self._spreadsheets = _FakeSpreadsheets()

    def spreadsheets(self):  # noqa: D401
        return self._spreadsheets


def test_copy_league_sheet_minimal(monkeypatch):
    """Copy a present tab, skip a missing tab; validate summary output."""

    # Monkeypatch googleapiclient.discovery.build to return our fake service
    def _fake_build(api, ver, credentials=None, cache_discovery=False):  # noqa: ARG001
        return _FakeService()

    import ingest.sheets.copier as copier

    monkeypatch.setattr(copier, "build", _fake_build)

    summary = copy_league_sheet(
        src_sheet_id="SRC",
        dst_sheet_id="DST",
        tabs=["Tab1", "Missing"],
        options=CopyOptions(paste_values_only=True),
        credentials=object(),  # bypass env creds loader
    )

    assert summary["copied"] == 1
    assert summary["skipped"] == 1
    assert summary["errors"] == 0
    tabs = {t["tab"]: t for t in summary["tabs"]}
    assert tabs["Tab1"]["status"] == "copied"
    assert tabs["Tab1"]["new_sheet_id"] == 999
    assert tabs["Missing"]["status"] == "skip"
