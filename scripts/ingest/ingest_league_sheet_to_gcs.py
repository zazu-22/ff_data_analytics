#!/usr/bin/env python3
"""Ingest Commissioner Google Sheet data to GCS.
Designed to run in GitHub Actions where network access works.
"""

import argparse
import json
import logging
import signal
import sys
from datetime import UTC, datetime
from pathlib import Path

import gspread
import pandas as pd
from google.cloud import storage
from google.oauth2.service_account import Credentials


# Timeout handler for hung operations
class TimeoutError(Exception):
    """Exception raised when an operation times out."""

    pass


def timeout_handler(signum, frame):
    """Signal handler that raises TimeoutError."""
    raise TimeoutError("Operation timed out")


signal.signal(signal.SIGALRM, timeout_handler)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("commissioner_sheet_ingest.log"),
    ],
)
logger = logging.getLogger(__name__)

# Define the owner tabs to export (avoiding TRANSACTIONS and other large tabs)
# TODO: Update these based on actual league owner names
OWNER_TABS = [
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

# Other tabs to optionally export
ADDITIONAL_TABS = [
    "TRANSACTIONS",  # Large, skip by default
    # Add other relevant tabs
]


def authenticate_sheets(creds_path: Path):
    """Authenticate with Google Sheets API."""
    logger.info(f"Authenticating with credentials from {creds_path}")

    scope = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)
    client = gspread.authorize(creds)

    logger.info("Successfully authenticated with Google Sheets API")
    return client


def authenticate_gcs(creds_path: Path):
    """Authenticate with Google Cloud Storage."""
    logger.info("Authenticating with Google Cloud Storage")

    creds = Credentials.from_service_account_file(str(creds_path))
    client = storage.Client(credentials=creds)

    logger.info("Successfully authenticated with GCS")
    return client


def export_worksheet(worksheet, owner_name: str) -> pd.DataFrame:
    """Export a single worksheet to DataFrame."""
    logger.info(f"Reading worksheet: {owner_name}")

    try:
        # First, get worksheet dimensions
        logger.info("  Getting worksheet properties...")
        props = worksheet._properties
        if "gridProperties" in props:
            rows = props["gridProperties"].get("rowCount", 100)
            cols = props["gridProperties"].get("columnCount", 50)
            logger.info(f"  Worksheet size: {rows} rows × {cols} columns")
        else:
            rows, cols = 100, 50  # Default if properties not available
            logger.info(f"  Using default range: {rows} rows × {cols} columns")

        # First try a small test read to verify access works
        logger.info("  Testing with small read (A1:C3)...")
        signal.alarm(10)
        try:
            test_values = worksheet.get("A1:C3")
            signal.alarm(0)
            logger.info(f"  ✓ Small read successful: {len(test_values)} rows")
        except TimeoutError:
            logger.error(f"  ✗ Even small read timed out for {owner_name}")
            signal.alarm(0)
            return pd.DataFrame()

        # Read in smaller chunks to avoid timeout
        # Read 10 rows at a time
        chunk_size = 10
        max_rows = min(rows, 40)  # Limit to 40 rows for owner sheets
        max_cols = min(cols, 40)  # Limit to 40 columns

        all_values = []

        for start_row in range(1, max_rows + 1, chunk_size):
            end_row = min(start_row + chunk_size - 1, max_rows)

            # Convert column number to letter
            col_letter = ""
            n = max_cols
            while n > 0:
                n, remainder = divmod(n - 1, 26)
                col_letter = chr(65 + remainder) + col_letter

            range_str = f"A{start_row}:{col_letter}{end_row}"
            logger.info(f"  Reading chunk: {range_str}")

            signal.alarm(15)  # 15 second timeout per chunk
            try:
                chunk_values = worksheet.get(range_str)
                signal.alarm(0)
                if chunk_values:
                    all_values.extend(chunk_values)
                    logger.info(f"    ✓ Got {len(chunk_values)} rows")
            except TimeoutError:
                logger.error(f"    ✗ Timeout reading chunk {range_str}")
                signal.alarm(0)
                break

        values = all_values

        if not values or len(values) < 2:
            logger.warning(f"  No data found in {owner_name}")
            return pd.DataFrame()

        # Convert to DataFrame (first row as headers)
        df = pd.DataFrame(values[1:], columns=values[0])

        # Clean up empty columns
        df = df.loc[:, (df != "").any(axis=0)]

        # Clean up empty rows
        df = df[df.astype(bool).any(axis=1)]

        logger.info(f"  ✓ Exported {len(df)} rows × {len(df.columns)} columns from {owner_name}")
        return df

    except Exception as e:
        logger.error(f"  ✗ Failed to export {owner_name}: {e}")
        import traceback

        traceback.print_exc()
        return pd.DataFrame()


def upload_to_gcs(
    df: pd.DataFrame, bucket_name: str, owner_name: str, gcs_client: storage.Client
) -> bool:
    """Upload DataFrame to GCS in partitioned structure."""
    if df.empty:
        logger.warning(f"Skipping upload for {owner_name} - empty DataFrame")
        return False

    # Generate paths
    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    timestamp = datetime.now(UTC).isoformat()

    # Path structure: raw/commissioner/rosters/{owner}/dt={date}/
    blob_path = f"raw/commissioner/rosters/{owner_name}/dt={dt}/data.parquet"

    try:
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        # Add metadata
        blob.metadata = {
            "source": "commissioner_sheet",
            "owner": owner_name,
            "export_timestamp": timestamp,
            "rows": str(len(df)),
            "columns": str(len(df.columns)),
        }

        # Convert to parquet and upload
        parquet_buffer = df.to_parquet()
        blob.upload_from_string(parquet_buffer, content_type="application/octet-stream")

        logger.info(f"  ✓ Uploaded {owner_name} to gs://{bucket_name}/{blob_path}")

        # Also save metadata JSON
        meta_path = f"raw/commissioner/rosters/{owner_name}/dt={dt}/_meta.json"
        meta_blob = bucket.blob(meta_path)
        meta_data = {
            "export_timestamp": timestamp,
            "owner": owner_name,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "data_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }
        meta_blob.upload_from_string(
            json.dumps(meta_data, indent=2), content_type="application/json"
        )

        return True

    except Exception as e:
        logger.error(f"  ✗ Failed to upload {owner_name}: {e}")
        return False


def main():
    """Ingest Commissioner Sheet to GCS."""
    parser = argparse.ArgumentParser(description="Ingest Commissioner Sheet to GCS")
    parser.add_argument("--creds", required=True, help="Path to GCP service account key")
    parser.add_argument("--sheet-url", required=True, help="Commissioner Sheet URL")
    parser.add_argument("--bucket", required=True, help="GCS bucket name")
    parser.add_argument("--owners-only", default="true", help="Export only owner tabs")

    args = parser.parse_args()

    # Extract sheet ID from URL
    if "docs.google.com" in args.sheet_url:
        sheet_id = args.sheet_url.split("/d/")[1].split("/")[0]
    else:
        sheet_id = args.sheet_url

    logger.info("=" * 60)
    logger.info("Commissioner Sheet Ingestion")
    logger.info("=" * 60)
    logger.info(f"Sheet ID: {sheet_id}")
    logger.info(f"Bucket: gs://{args.bucket}")
    logger.info(f"Owners only: {args.owners_only}")

    try:
        # Authenticate
        sheets_client = authenticate_sheets(Path(args.creds))
        gcs_client = authenticate_gcs(Path(args.creds))

        # Open sheet
        logger.info(f"Opening sheet {sheet_id}...")
        sheet = sheets_client.open_by_key(sheet_id)
        logger.info(f"Opened: {sheet.title}")

        # Get all worksheets
        all_worksheets = {ws.title: ws for ws in sheet.worksheets()}
        logger.info(f"Found {len(all_worksheets)} worksheets")

        # Determine which tabs to export
        if args.owners_only.lower() == "true":
            tabs_to_export = [tab for tab in OWNER_TABS if tab in all_worksheets]
            logger.info(f"Exporting {len(tabs_to_export)} owner tabs")
        else:
            tabs_to_export = list(all_worksheets.keys())
            logger.info(f"Exporting all {len(tabs_to_export)} tabs")

        # Export each tab
        success_count = 0
        for tab_name in tabs_to_export:
            worksheet = all_worksheets[tab_name]
            df = export_worksheet(worksheet, tab_name)

            if not df.empty and upload_to_gcs(df, args.bucket, tab_name, gcs_client):
                success_count += 1

        logger.info("=" * 60)
        logger.info(f"✅ Ingestion complete: {success_count}/{len(tabs_to_export)} tabs uploaded")
        logger.info("=" * 60)

        # Write summary for workflow artifact
        summary = {
            "timestamp": datetime.now(UTC).isoformat(),
            "sheet_id": sheet_id,
            "sheet_title": sheet.title,
            "tabs_processed": tabs_to_export,
            "success_count": success_count,
            "total_tabs": len(tabs_to_export),
        }

        with Path("ingestion_summary.json").open("w") as f:
            json.dump(summary, f, indent=2)

        return 0 if success_count > 0 else 1

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
