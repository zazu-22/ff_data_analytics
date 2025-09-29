#!/usr/bin/env python3
"""View recent entries from the league sheet ingestion log.

This script provides visibility into the ingestion process by:
- Displaying the last 5 log entries with key details
- Showing total entry count and column information
- Counting whole-run skips vs actual processing runs
- Highlighting the source modification time for each entry

Useful for monitoring ingestion health, debugging skip logic,
and understanding when and why data was or wasn't copied.

Usage:
    python scripts/debug/view_log_sheet.py

Environment Variables:
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account key

Returns:
    0 on success, displays log entries
    Non-zero on error

Note:
    The log sheet ID is hardcoded based on the current deployment.
    Update LOG_SHEET_ID if the log spreadsheet is recreated.

    Special entries with tab='[ENTIRE_RUN]' indicate whole-run skips
    where the source hadn't changed since the last successful run.

"""

import os

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# Load environment variables
load_dotenv()

GOOGLE_APPLICATION_CREDENTIALS = (
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "config/secrets/gcp-service-account-key.json"
)

LOG_SHEET_ID = "1wbykU_-3kkSXT-sQXQOuMToUu2PPIzBJDrxZWaqdnsk"  # From the test output

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def main():
    """Display recent log entries from the ingestion log sheet.

    Shows the last 5 entries, column headers, and counts of
    different entry types including whole-run skips.

    Returns:
        int: Always returns 0 (success)

    """
    # Authenticate
    creds = Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS, scopes=SCOPES)
    gc = gspread.authorize(creds)

    # Open the log spreadsheet
    logs_ss = gc.open_by_key(LOG_SHEET_ID)
    log_ws = logs_ss.worksheet("BK_INGEST_LOG")

    # Get all data
    all_rows = log_ws.get_all_records()

    if not all_rows:
        print("No log entries found.")
        return

    # Show the last 5 entries
    print(f"Last 5 log entries (total: {len(all_rows)}):")
    print("-" * 80)

    for row in all_rows[-5:]:
        run_id = str(row.get("run_id", ""))
        print(f"\nRun ID: {run_id[:8] if run_id else 'N/A'}...")
        print(f"  Tab: {row.get('tab', '')}")
        print(f"  Status: {row.get('status', '')}")
        print(f"  Started: {row.get('started_at_utc', '')}")
        print(f"  Source Modified: {row.get('src_modifiedTime_utc', '[NOT TRACKED]')}")
        print(f"  Duration: {row.get('duration_ms', 0)}ms")

    # Check column headers
    headers = log_ws.row_values(1)
    print("\n" + "=" * 80)
    print(f"Total columns: {len(headers)}")
    print(f"Columns: {', '.join(headers)}")

    # Count whole-run skips
    whole_run_skips = [r for r in all_rows if r.get("tab") == "[ENTIRE_RUN]"]
    print(f"\nWhole-run skips logged: {len(whole_run_skips)}")


if __name__ == "__main__":
    main()
