#!/usr/bin/env python3
"""Ingest TRANSACTIONS tab from copied league sheet and parse to data/raw.

Reads from LEAGUE_SHEET_COPY_ID (already copied by copy_league_sheet.py),
downloads TRANSACTIONS tab, parses via commissioner_parser.parse_transactions(),
and writes to data/raw/commissioner/transactions/dt=YYYY-MM-DD/

This follows the two-step pattern:
1. copy_league_sheet.py: Commissioner → League Copy (avoids timeouts)
2. THIS SCRIPT: League Copy → parse → data/raw/

Usage
-----
python scripts/ingest/run_commissioner_transactions.py

Environment Variables
--------------------
LEAGUE_SHEET_COPY_ID=<sheet-id>  # Copied league sheet (destination from copy_league_sheet.py)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
# OR
GOOGLE_APPLICATION_CREDENTIALS_JSON=<base64-encoded-json>

Outputs
-------
data/raw/commissioner/transactions/dt=YYYY-MM-DD/
  - transactions.parquet
  - _meta.json
data/raw/commissioner/transactions_qa/dt=YYYY-MM-DD/
  - unmapped_players.parquet (should be empty with dim_name_alias)
"""

import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# Load environment variables
load_dotenv()

# Import parser
try:
    from src.ingest.sheets.commissioner_parser import parse_transactions
except ImportError:
    # Fallback if running from different directory
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.ingest.sheets.commissioner_parser import parse_transactions


def get_gspread_client() -> gspread.Client:
    """Create authenticated gspread client from env credentials."""
    # Try JSON env var first
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
            ]
        )
        return gspread.authorize(creds)

    # Try file path
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
        )
        return gspread.authorize(creds)

    raise EnvironmentError(
        "Missing Google credentials. Set GOOGLE_APPLICATION_CREDENTIALS or "
        "GOOGLE_APPLICATION_CREDENTIALS_JSON"
    )


def download_transactions_tab(sheet_id: str, output_path: Path) -> None:
    """Download TRANSACTIONS tab from Google Sheet to CSV.

    Args:
        sheet_id: Google Sheet ID (LEAGUE_SHEET_COPY_ID)
        output_path: Path to write CSV
    """
    print(f"📥 Downloading TRANSACTIONS tab from sheet: {sheet_id}")

    client = get_gspread_client()
    spreadsheet = client.open_by_key(sheet_id)

    # Get TRANSACTIONS tab
    try:
        worksheet = spreadsheet.worksheet("TRANSACTIONS")
    except gspread.exceptions.WorksheetNotFound:
        raise ValueError(
            f"TRANSACTIONS tab not found in sheet {sheet_id}. "
            "Ensure copy_league_sheet.py has been run first."
        )

    # Get all values
    print(f"  Fetching all values...")
    all_values = worksheet.get_all_values()

    # Write to CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(all_values)

    print(f"  ✅ Downloaded {len(all_values)} rows to {output_path}")


def main():
    """Main ingestion workflow."""
    print("="*80)
    print("COMMISSIONER TRANSACTIONS INGESTION")
    print("="*80)

    # Get config from env
    sheet_id = os.getenv("LEAGUE_SHEET_COPY_ID")
    if not sheet_id:
        raise EnvironmentError(
            "Missing LEAGUE_SHEET_COPY_ID. Set this to the copied league sheet ID."
        )

    # Set up paths
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    output_base = Path("data/raw/commissioner")
    transactions_dir = output_base / "transactions" / f"dt={today}"
    qa_dir = output_base / "transactions_qa" / f"dt={today}"

    # Create temp dir for downloaded CSV
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "TRANSACTIONS.csv"

        # Step 1: Download TRANSACTIONS tab
        download_transactions_tab(sheet_id, csv_path)

        # Step 2: Parse transactions
        print(f"\n🔄 Parsing transactions...")
        result = parse_transactions(csv_path)

        print(f"  ✅ Parsed {result['transactions'].height:,} transaction rows")
        print(f"  ✅ Unmapped players: {result['unmapped_players'].height}")

        # Step 3: Write to data/raw
        transactions_dir.mkdir(parents=True, exist_ok=True)
        qa_dir.mkdir(parents=True, exist_ok=True)

        # Write transactions parquet
        transactions_path = transactions_dir / "transactions.parquet"
        result['transactions'].write_parquet(transactions_path)
        print(f"  📝 Wrote transactions: {transactions_path}")

        # Write unmapped players (QA)
        unmapped_path = qa_dir / "unmapped_players.parquet"
        result['unmapped_players'].write_parquet(unmapped_path)
        print(f"  📝 Wrote unmapped QA: {unmapped_path}")

        # Write metadata
        meta_path = transactions_dir / "_meta.json"
        metadata = {
            "dataset": "transactions",
            "source_sheet_id": sheet_id,
            "source_tab": "TRANSACTIONS",
            "asof_datetime": datetime.now(UTC).isoformat(),
            "loader_path": "scripts.ingest.run_commissioner_transactions",
            "parser_function": "src.ingest.sheets.commissioner_parser.parse_transactions",
            "output_parquet": [transactions_path.name],
            "row_count": result['transactions'].height,
            "unmapped_players": result['unmapped_players'].height,
            "dt": today,
        }

        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"  📝 Wrote metadata: {meta_path}")

    print(f"\n{'='*80}")
    print(f"✅ TRANSACTIONS INGESTION COMPLETE")
    print(f"{'='*80}")
    print(f"Output: {transactions_dir}")
    print(f"QA: {qa_dir}")
    print(f"\nNext step: Run dbt models")
    print(f"  cd dbt/ff_analytics")
    print(f"  dbt run --select stg_sheets__transactions fact_league_transactions")
    print(f"  dbt test --select stg_sheets__transactions fact_league_transactions")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)
