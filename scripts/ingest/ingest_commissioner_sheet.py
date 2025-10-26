#!/usr/bin/env python3
"""Atomic ingest: rosters + transactions from Commissioner sheet.

This is the UNIFIED ingest script that ensures rosters and transactions are always
in sync by downloading and processing them atomically from a single sheet snapshot.

Architecture:
    1. Downloads all tabs (12 GM rosters + TRANSACTIONS) atomically
    2. Parses using pure functions (no I/O in parser)
    3. Writes using centralized writer (handles local/GCS)

Environment Variables:
    LEAGUE_SHEET_COPY_ID: Source sheet ID (required)
    OUTPUT_PATH: Base output path - "data/raw" (local) OR "gs://bucket/raw" (cloud)
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON
    OR GOOGLE_APPLICATION_CREDENTIALS_JSON: Base64-encoded JSON

Outputs:
    {OUTPUT_PATH}/commissioner/
      transactions/dt=YYYY-MM-DD/
        transactions.parquet
        _meta.json
      transactions_qa/dt=YYYY-MM-DD/
        unmapped_players.parquet
        unmapped_picks.parquet (optional)
      contracts_active/dt=YYYY-MM-DD/
        contracts_active.parquet
        _meta.json
      contracts_cut/dt=YYYY-MM-DD/
        contracts_cut.parquet
        _meta.json
      draft_picks/dt=YYYY-MM-DD/
        draft_picks.parquet
        _meta.json
      draft_pick_conditions/dt=YYYY-MM-DD/
        draft_pick_conditions.parquet
        _meta.json

Usage:
    # Local development
    python scripts/ingest/ingest_commissioner_sheet.py

    # CI/CD (cloud)
    OUTPUT_PATH=gs://ff-analytics/raw python scripts/ingest/ingest_commissioner_sheet.py
"""

import csv
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

from ingest.sheets import commissioner_parser, commissioner_writer

# Load environment variables
load_dotenv()


def get_gspread_client() -> gspread.Client:
    """Create authenticated gspread client from env credentials."""
    # Try JSON env var first (for CI/CD)
    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_json:
        import base64

        decoded = base64.b64decode(creds_json)
        creds_dict = json.loads(decoded)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ],
        )
        return gspread.authorize(creds)

    # Try file path (for local development)
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ],
        )
        return gspread.authorize(creds)

    raise OSError(
        "Missing Google credentials. Set GOOGLE_APPLICATION_CREDENTIALS or "
        "GOOGLE_APPLICATION_CREDENTIALS_JSON"
    )


def download_tab_to_csv(worksheet: gspread.Worksheet, output_path: Path) -> int:
    """Download a single worksheet tab to CSV.

    Args:
        worksheet: gspread Worksheet object
        output_path: Path to write CSV

    Returns:
        Number of rows downloaded

    """
    print(f"  Downloading {worksheet.title}...")
    all_values = worksheet.get_all_values()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(all_values)

    print(f"    ✅ {len(all_values)} rows → {output_path}")
    return len(all_values)


def download_all_tabs(sheet_id: str, output_dir: Path) -> dict[str, int]:
    """Download all GM roster tabs + TRANSACTIONS tab atomically.

    Args:
        sheet_id: Google Sheet ID
        output_dir: Temp directory for CSV files

    Returns:
        Dict of row counts by tab name

    """
    print("\n📥 Downloading all tabs from Commissioner sheet")
    print(f"  Sheet ID: {sheet_id}")
    print(f"  Output dir: {output_dir}")

    client = get_gspread_client()
    spreadsheet = client.open_by_key(sheet_id)

    # GM tabs (12 franchises)
    gm_tabs = [
        "Andy",
        "Chip",
        "Eric",
        "Gordon",
        "James",
        "Jason",
        "Joe",
        "JP",
        "Kevin",
        "McCreary",
        "Piper",
        "TJ",
    ]

    counts = {}

    # Download GM roster tabs
    for tab_name in gm_tabs:
        try:
            worksheet = spreadsheet.worksheet(tab_name)
            tab_dir = output_dir / tab_name
            tab_dir.mkdir(parents=True, exist_ok=True)
            csv_path = tab_dir / f"{tab_name}.csv"
            counts[tab_name] = download_tab_to_csv(worksheet, csv_path)
        except gspread.exceptions.WorksheetNotFound:
            print(f"  ⚠️  Tab '{tab_name}' not found - skipping")

    # Download TRANSACTIONS tab
    try:
        worksheet = spreadsheet.worksheet("TRANSACTIONS")
        transactions_dir = output_dir / "TRANSACTIONS"
        transactions_dir.mkdir(parents=True, exist_ok=True)
        csv_path = transactions_dir / "TRANSACTIONS.csv"
        counts["TRANSACTIONS"] = download_tab_to_csv(worksheet, csv_path)
    except gspread.exceptions.WorksheetNotFound:
        raise ValueError(
            "TRANSACTIONS tab not found in sheet. Cannot proceed without transaction history."
        ) from None

    print(f"\n  ✅ Downloaded {len(counts)} tabs ({sum(counts.values())} total rows)")
    return counts


def main():
    """Run the unified commissioner sheet ingest."""
    start_time = datetime.now(UTC)

    print("=" * 80)
    print("COMMISSIONER SHEET ATOMIC INGEST")
    print("=" * 80)
    print(f"Started: {start_time.isoformat()}")

    # Get config from env
    sheet_id = os.getenv("LEAGUE_SHEET_COPY_ID")
    if not sheet_id:
        raise OSError("Missing LEAGUE_SHEET_COPY_ID environment variable")

    output_base = os.getenv("OUTPUT_PATH", "data/raw")
    print("\nConfig:")
    print(f"  Sheet ID: {sheet_id}")
    print(f"  Output: {output_base} {'(GCS)' if output_base.startswith('gs://') else '(local)'}")

    # Create temp dir for downloads
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Step 1: Download all tabs atomically
        download_all_tabs(sheet_id, tmpdir_path)

        # Step 2: Parse roster tabs (pure parsing)
        print("\n🔄 Parsing roster tabs...")
        parsed_gms = commissioner_parser.parse_commissioner_dir(tmpdir_path)
        roster_tables = commissioner_parser.prepare_roster_tables(parsed_gms)
        print(f"  ✅ Parsed {len(parsed_gms)} GM tabs")
        print(f"    • contracts_active: {roster_tables['contracts_active'].height} rows")
        print(f"    • contracts_cut: {roster_tables['contracts_cut'].height} rows")
        print(f"    • draft_picks: {roster_tables['draft_picks'].height} rows")
        print(f"    • draft_pick_conditions: {roster_tables['draft_pick_conditions'].height} rows")

        # Step 3: Parse transactions tab (pure parsing)
        print("\n🔄 Parsing transactions...")
        transactions_csv = tmpdir_path / "TRANSACTIONS" / "TRANSACTIONS.csv"
        transactions_tables = commissioner_parser.parse_transactions(transactions_csv)
        print("  ✅ Parsed transactions")
        print(f"    • transactions: {transactions_tables['transactions'].height:,} rows")
        print(f"    • unmapped_players: {transactions_tables['unmapped_players'].height} rows")
        if "unmapped_picks" in transactions_tables:
            print(f"    • unmapped_picks: {transactions_tables['unmapped_picks'].height} rows")

        # Step 4: Write all tables atomically (cloud-ready)
        print(f"\n📝 Writing all tables to {output_base}...")
        write_counts = commissioner_writer.write_all_commissioner_tables(
            roster_tables=roster_tables,
            transactions_tables=transactions_tables,
            base_uri=f"{output_base}/commissioner",
        )

        print(f"  ✅ Wrote {len(write_counts)} tables:")
        for table_name, count in write_counts.items():
            print(f"    • {table_name}: {count} rows")

    # Summary
    end_time = datetime.now(UTC)
    duration = (end_time - start_time).total_seconds()

    print(f"\n{'=' * 80}")
    print("✅ COMMISSIONER SHEET INGEST COMPLETE")
    print(f"{'=' * 80}")
    print(f"Duration: {duration:.1f}s")
    print(f"Output: {output_base}/commissioner")
    print("\nNext steps:")
    print("  • Run dbt: make dbt-run")
    print("  • Run tests: make dbt-test")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
