"""Prefect flow for parsing Commissioner league sheet to Parquet.

This flow parses the copied league sheet (from P4-002a copy flow) and writes
normalized tables to Parquet with governance validation.

Architecture:
    1. Validate copy completeness (ensure all tabs were copied)
    2. Download tabs to temp CSV files
    3. Parse with commissioner_parser (pure functions)
    4. Validate row counts and required columns
    5. Write Parquet files + manifests

Dependencies:
    - copy_league_sheet_flow (P4-002a) must run first
    - Uses src/ingest/sheets/commissioner_parser for parsing
    - Uses src/ingest/sheets/commissioner_writer for writing

Production Hardening:
    - create_gspread_client: 3 retries with 60s delay (handles auth transients)
    - download_sheet_tabs_to_csv: 2 retries with 30s delay (handles I/O transients)
"""

import csv
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Ensure src package is importable
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import gspread  # noqa: E402
from google.oauth2 import service_account  # noqa: E402
from prefect import flow, task  # noqa: E402

from src.flows.copy_league_sheet_flow import validate_copy_completeness  # noqa: E402
from src.flows.utils.notifications import log_error, log_info, log_warning  # noqa: E402
from src.flows.utils.validation import validate_manifests_task  # noqa: E402
from src.ingest.sheets import commissioner_parser, commissioner_writer  # noqa: E402


@task(
    name="create_gspread_client",
    retries=3,
    retry_delay_seconds=60,
    tags=["external_api"],
)
def create_gspread_client() -> gspread.Client:
    """Create authenticated gspread client from env credentials.

    Returns:
        Authenticated gspread client

    Raises:
        RuntimeError: If credentials are missing

    """
    # Try JSON env var first (for CI/CD)
    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_json:
        import base64

        decoded = base64.b64decode(creds_json)
        creds_dict = json.loads(decoded)
        creds = service_account.Credentials.from_service_account_info(
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
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ],
        )
        return gspread.authorize(creds)

    raise RuntimeError(
        "Missing Google credentials. Set GOOGLE_APPLICATION_CREDENTIALS or "
        "GOOGLE_APPLICATION_CREDENTIALS_JSON"
    )


@task(
    name="download_sheet_tabs_to_csv",
    retries=2,
    retry_delay_seconds=30,
    tags=["io"],
)
def download_tabs_to_csv(sheet_id: str, temp_dir: Path, expected_tabs: list[str]) -> dict:
    """Download all expected tabs from sheet to CSV files.

    Args:
        sheet_id: Google Sheet ID to download from
        temp_dir: Temporary directory for CSV files
        expected_tabs: List of tab names to download (GM names + TRANSACTIONS)

    Returns:
        Dict with download results and row counts

    """
    log_info(
        "Downloading tabs from Google Sheet",
        context={"sheet_id": sheet_id, "temp_dir": str(temp_dir), "tab_count": len(expected_tabs)},
    )

    client = create_gspread_client()
    spreadsheet = client.open_by_key(sheet_id)

    counts = {}
    downloaded = []
    missing = []

    for tab_name in expected_tabs:
        try:
            worksheet = spreadsheet.worksheet(tab_name)

            # Create tab directory structure
            if tab_name == "TRANSACTIONS":
                tab_dir = temp_dir / "TRANSACTIONS"
                csv_filename = "TRANSACTIONS.csv"
            else:
                # GM roster tabs
                tab_dir = temp_dir / tab_name
                csv_filename = f"{tab_name}.csv"

            tab_dir.mkdir(parents=True, exist_ok=True)
            csv_path = tab_dir / csv_filename

            # Download to CSV
            all_values = worksheet.get_all_values()
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(all_values)

            counts[tab_name] = len(all_values)
            downloaded.append(tab_name)
            log_info(
                f"Downloaded {tab_name}", context={"rows": len(all_values), "path": str(csv_path)}
            )

        except gspread.exceptions.WorksheetNotFound:
            missing.append(tab_name)
            log_warning(f"Tab '{tab_name}' not found in sheet", context={"tab": tab_name})

    if missing:
        log_error(
            "Missing required tabs in sheet",
            context={"missing_tabs": missing, "downloaded_tabs": downloaded},
        )

    log_info(
        "All tabs downloaded successfully",
        context={"downloaded_count": len(downloaded), "total_rows": sum(counts.values())},
    )

    return {"downloaded": downloaded, "missing": missing, "row_counts": counts}


@task(name="parse_commissioner_tabs")
def parse_commissioner_tabs(temp_dir: Path) -> dict:
    """Parse downloaded CSV files to DataFrames.

    Args:
        temp_dir: Directory containing downloaded CSV files

    Returns:
        Dict with parsed roster and transaction tables

    """
    log_info("Parsing roster tabs", context={"temp_dir": str(temp_dir)})

    # Parse roster tabs (GM rosters)
    parsed_gms = commissioner_parser.parse_commissioner_dir(temp_dir)
    roster_tables = commissioner_parser.prepare_roster_tables(parsed_gms)

    log_info(
        "Parsed roster tabs",
        context={
            "gm_count": len(parsed_gms),
            "contracts_active": roster_tables["contracts_active"].height,
            "contracts_cut": roster_tables["contracts_cut"].height,
            "draft_picks": roster_tables["draft_picks"].height,
            "draft_pick_conditions": roster_tables["draft_pick_conditions"].height,
            "cap_space": roster_tables["cap_space"].height,
        },
    )

    # Parse transactions tab
    transactions_csv = temp_dir / "TRANSACTIONS" / "TRANSACTIONS.csv"
    if not transactions_csv.exists():
        log_error(
            "TRANSACTIONS.csv not found",
            context={"expected_path": str(transactions_csv)},
        )

    transactions_tables = commissioner_parser.parse_transactions(transactions_csv)

    log_info(
        "Parsed transactions",
        context={
            "transactions": transactions_tables["transactions"].height,
            "unmapped_players": transactions_tables["unmapped_players"].height,
            "unmapped_picks": transactions_tables["unmapped_picks"].height,
        },
    )

    # Combine all tables
    return {
        "contracts_active": roster_tables["contracts_active"],
        "contracts_cut": roster_tables["contracts_cut"],
        "draft_picks": roster_tables["draft_picks"],
        "draft_pick_conditions": roster_tables["draft_pick_conditions"],
        "cap_space": roster_tables["cap_space"],
        "transactions": transactions_tables["transactions"],
        "transactions_qa": {
            "unmapped_players": transactions_tables["unmapped_players"],
            "unmapped_picks": transactions_tables["unmapped_picks"],
        },
    }


@task(name="validate_row_counts")
def validate_row_counts(data: dict, expected_min_rows: dict) -> dict:
    """Validate row counts against expected minimums.

    Args:
        data: Dict of DataFrames keyed by table name
        expected_min_rows: Dict of expected minimum row counts per table

    Returns:
        Validation results with any issues

    """
    issues = []

    for table_name, expected_min in expected_min_rows.items():
        if table_name not in data:
            issues.append({"table": table_name, "issue": "table_missing"})
            continue

        df = data[table_name]
        row_count = df.height if hasattr(df, "height") else len(df)

        if row_count < expected_min:
            issues.append(
                {
                    "table": table_name,
                    "row_count": row_count,
                    "expected_min": expected_min,
                    "issue": "below_minimum",
                }
            )

    if issues:
        log_warning("Row count validation warnings", context={"issues": issues})
    else:
        log_info("Row count validation passed")

    return {"valid": len(issues) == 0, "issues": issues}


@task(name="validate_required_columns")
def validate_required_columns(data: dict, required_columns: dict) -> dict:
    """Validate required columns exist in each table.

    Args:
        data: Dict of DataFrames keyed by table name
        required_columns: Dict of required column lists per table

    Returns:
        Validation results with any issues

    """
    issues = []

    for table_name, required_cols in required_columns.items():
        if table_name not in data:
            continue  # Already flagged in row count validation

        df = data[table_name]
        df_columns = df.columns if hasattr(df, "columns") else []
        missing_cols = [col for col in required_cols if col not in df_columns]

        if missing_cols:
            issues.append(
                {
                    "table": table_name,
                    "missing_columns": missing_cols,
                }
            )

    if issues:
        log_error("Missing required columns", context={"issues": issues})
    else:
        log_info("Required columns validation passed")

    return {"valid": len(issues) == 0, "issues": issues}


@task(name="write_commissioner_parquet")
def write_parquet_files(data: dict, output_dir: str, snapshot_date: str) -> dict:
    """Write all parsed tables to Parquet files.

    Args:
        data: Dict of DataFrames to write
        output_dir: Base output directory (e.g., "data/raw/sheets")
        snapshot_date: Snapshot date string (YYYY-MM-DD)

    Returns:
        Dict with write results

    """
    log_info(
        "Writing Parquet files",
        context={"output_dir": output_dir, "snapshot_date": snapshot_date},
    )

    # Use commissioner_writer to handle all writes
    results = commissioner_writer.write_all_commissioner_tables(
        roster_tables={
            "contracts_active": data["contracts_active"],
            "contracts_cut": data["contracts_cut"],
            "draft_picks": data["draft_picks"],
            "draft_pick_conditions": data["draft_pick_conditions"],
            "cap_space": data["cap_space"],
        },
        transactions_tables={
            "transactions": data["transactions"],
            "unmapped_players": data["transactions_qa"]["unmapped_players"],
            "unmapped_picks": data["transactions_qa"]["unmapped_picks"],
        },
        output_base=output_dir,
        source_sheet_id=os.getenv("LEAGUE_SHEET_COPY_ID", "unknown"),
        snapshot_date=snapshot_date,
    )

    log_info(
        "Parquet files written successfully",
        context={"files_written": len(results), "results": results},
    )

    return {"success": True, "write_results": results}


@flow(name="parse_league_sheet_flow")
def parse_league_sheet_flow(
    output_dir: str = "data/raw/sheets",
    snapshot_date: str | None = None,
    copy_flow_result: dict | None = None,
) -> dict:
    """Prefect flow for parsing Commissioner league sheet.

    This flow depends on copy_league_sheet_flow (P4-002a) completing first.
    It downloads tabs to temp CSV, parses with commissioner_parser, validates,
    and writes to Parquet.

    Args:
        output_dir: Output directory for Parquet files
        snapshot_date: Snapshot date (defaults to today)
        copy_flow_result: Result from copy_league_sheet_flow (optional, for validation)

    Returns:
        Flow result with validation and write status

    """
    if snapshot_date is None:
        snapshot_date = datetime.now().strftime("%Y-%m-%d")

    log_info(
        "Starting parse league sheet flow",
        context={
            "snapshot_date": snapshot_date,
            "output_dir": output_dir,
            "copy_completed": copy_flow_result is not None,
        },
    )

    # Configuration
    sheet_id = os.getenv("LEAGUE_SHEET_COPY_ID")
    if not sheet_id:
        log_error(
            "Missing LEAGUE_SHEET_COPY_ID environment variable",
            context={"required_var": "LEAGUE_SHEET_COPY_ID"},
        )

    # Expected tabs (12 GM rosters + TRANSACTIONS)
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
    expected_tabs = gm_tabs + ["TRANSACTIONS"]

    # Validation thresholds
    expected_min_rows = {
        "contracts_active": 50,  # At least 50 active contracts
        "transactions": 100,  # Expect many transactions
        "draft_picks": 20,  # Expect draft picks
        "cap_space": 10,  # At least some cap space records
    }

    required_columns = {
        "contracts_active": ["gm", "player", "year", "amount"],
        "transactions": ["transaction_id", "Player", "Time Frame"],
        "draft_picks": ["gm", "year", "round"],
        "cap_space": ["gm", "season", "available_cap_space"],
    }

    # If copy_flow_result provided, validate it completed successfully
    if copy_flow_result and not copy_flow_result.get("ready_for_parse", False):
        log_error(
            "Copy flow did not complete successfully - aborting parse",
            context={"copy_result": copy_flow_result},
        )

    # Governance: Validate copy completeness (BEFORE downloading)
    copy_result = validate_copy_completeness(expected_tabs, sheet_id)
    if not copy_result["valid"]:
        log_error(
            "Aborting pipeline - sheets copy incomplete",
            context={"missing_tabs": copy_result["missing_tabs"]},
        )

    # Create temp directory for CSV downloads
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)

        # Download tabs to CSV
        download_result = download_tabs_to_csv(sheet_id, temp_dir, expected_tabs)

        if download_result["missing"]:
            log_error(
                "Failed to download all tabs",
                context={"missing": download_result["missing"]},
            )

        # Parse CSV files
        parsed_data = parse_commissioner_tabs(temp_dir)

        # Governance: Validate row counts
        row_count_result = validate_row_counts(parsed_data, expected_min_rows)

        # Governance: Validate required columns
        column_result = validate_required_columns(parsed_data, required_columns)

        # Write to Parquet
        write_result = write_parquet_files(parsed_data, output_dir, snapshot_date)

    # Governance: Validate manifests
    manifest_result = validate_manifests_task(sources=["sheets"], fail_on_gaps=False)

    log_info(
        "Parse league sheet flow complete",
        context={
            "snapshot_date": snapshot_date,
            "validation": "passed" if row_count_result["valid"] else "warnings",
        },
    )

    return {
        "snapshot_date": snapshot_date,
        "download_result": download_result,
        "row_count_validation": row_count_result,
        "column_validation": column_result,
        "write_result": write_result,
        "manifest_validation": manifest_result,
    }


# Optional: Combined flow that sequences copy → parse
@flow(name="google_sheets_pipeline")
def google_sheets_pipeline(
    output_dir: str = "data/raw/sheets", snapshot_date: str | None = None
) -> dict:
    """Run copy then parse flows in sequence.

    For production, consider running these as separate scheduled flows
    (copy every 2-4 hours, parse 15-30 min after copy).

    Args:
        output_dir: Output directory for Parquet files
        snapshot_date: Snapshot date (defaults to today)

    Returns:
        Combined results from both flows

    """
    from src.flows.copy_league_sheet_flow import copy_league_sheet_flow

    # Run copy flow first
    copy_result = copy_league_sheet_flow()

    # Wait for copy to complete, then run parse
    if copy_result.get("ready_for_parse", False):
        parse_result = parse_league_sheet_flow(
            output_dir=output_dir,
            snapshot_date=snapshot_date,
            copy_flow_result=copy_result,
        )
        return {"copy": copy_result, "parse": parse_result}
    else:
        return {"copy": copy_result, "parse": None, "error": "Copy incomplete"}


if __name__ == "__main__":
    # For local testing - can run parse independently or combined
    # Option 1: Run parse only (assumes copy already completed)
    result = parse_league_sheet_flow()
    print(f"Parse flow result: {result}")

    # Option 2: Run combined (copy → parse)
    # result = google_sheets_pipeline()
    # print(f"Combined flow result: {result}")
