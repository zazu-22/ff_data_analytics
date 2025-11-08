"""Parse Commissioner sheets from local CSV → normalized Parquet (dev tool).

⚠️  DEVELOPMENT TOOL ONLY
For production ingestion, use scripts/ingest/ingest_commissioner_sheet.py instead.

This tool is for local development and testing. It parses GM roster tabs from
local CSV files (or downloads them from Sheets) and writes normalized Parquet.

IMPORTANT: This tool does NOT guarantee atomic consistency between rosters and
transactions. For production, always use the unified ingest script which ensures
rosters and transactions are from the same sheet snapshot.

Options:
- Pull tabs from a Google Sheet (by URL) into a local temp dir, then parse
- Or parse an existing local directory exported earlier (e.g., from samples)

Outputs:
- Writes normalized Parquet to `--out-raw` via commissioner_writer
- Writes human-readable CSV previews to `--out-csv` for manual review

Credentials (for --sheet-url mode):
- GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_APPLICATION_CREDENTIALS_JSON
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
from dotenv import load_dotenv

from ingest.sheets.commissioner_parser import (
    ParsedGM,
    parse_commissioner_dir,
    prepare_roster_tables,
)
from ingest.sheets.commissioner_writer import write_all_commissioner_tables


def _export_tabs(sheet_url: str, tabs: list[str], out_dir: Path, max_rows: int = 2000) -> Path:
    import gspread
    from google.oauth2.service_account import Credentials

    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_json:
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
    elif creds_path:
        creds = Credentials.from_service_account_file(
            creds_path, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
    else:
        raise SystemExit(
            "Set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_APPLICATION_CREDENTIALS_JSON "
            "for Sheets access."
        )

    gc = gspread.authorize(creds)
    sh = gc.open_by_url(sheet_url)

    base = out_dir
    base.mkdir(parents=True, exist_ok=True)

    for tab in tabs:
        ws = sh.worksheet(tab)
        values = ws.get_all_values()
        cols = values[0] if values else []
        rows = values[1 : max_rows + 1] if values else []
        # ensure per-tab folder like samples/sheets/<Tab>/<Tab>.csv
        tdir = base / tab
        tdir.mkdir(parents=True, exist_ok=True)
        csv_path = tdir / f"{tab}.csv"
        # de-duplicate header names minimally
        if cols:
            seen: dict[str, int] = {}
            headers = []
            for c in cols:
                if c in seen:
                    seen[c] += 1
                    headers.append(f"{c}_{seen[c]}")
                else:
                    seen[c] = 0
                    headers.append(c)
        else:
            headers = []
        import csv

        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if headers:
                w.writerow(headers)
            w.writerows(rows)

    return base


def _concat(parsed: list[ParsedGM]) -> dict[str, pl.DataFrame]:
    """Concatenate per-GM frames into whole-league tables."""
    roster = (
        pl.concat([p.roster for p in parsed if p.roster.height > 0], how="diagonal")
        if parsed
        else pl.DataFrame()
    )
    cuts = (
        pl.concat([p.cuts for p in parsed if p.cuts.height > 0], how="diagonal")
        if parsed
        else pl.DataFrame()
    )
    picks = (
        pl.concat([p.picks for p in parsed if p.picks.height > 0], how="diagonal")
        if parsed
        else pl.DataFrame()
    )
    return {"roster": roster, "cut_contracts": cuts, "draft_picks": picks}


def main() -> int:
    """Run extraction (optional) + parsing and write Parquet and CSV previews."""
    # Load .env so credential paths in .env are available
    load_dotenv()
    """Run extraction (optional) + parsing and write Parquet and CSV previews."""
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--sheet-url", help="Google Sheets URL (copied league sheet)")
    g.add_argument("--input-dir", help="Local directory of per-tab CSVs (like samples/sheets)")
    p.add_argument("--tabs", nargs="*", help="Tabs to pull when using --sheet-url")
    # Default out-raw uses GCS_BUCKET if present
    default_out_raw = (
        f"gs://{os.environ.get('GCS_BUCKET')}/raw/commissioner"
        if os.environ.get("GCS_BUCKET")
        else "data/raw/commissioner"
    )
    p.add_argument(
        "--out-raw", default=default_out_raw, help="Parquet output base (local or gs://)"
    )
    p.add_argument(
        "--out-csv", default="data/review/commissioner", help="CSV preview output base (local only)"
    )
    default_raw_tabs = (
        f"gs://{os.environ.get('GCS_BUCKET')}/raw/commissioner_tabs"
        if os.environ.get("GCS_BUCKET")
        else None
    )
    p.add_argument(
        "--out-raw-tabs",
        default=default_raw_tabs,
        help="Optional raw tabs Parquet base (e.g., gs://.../raw/commissioner_tabs)",
    )
    p.add_argument("--max-rows", type=int, default=2000)
    args = p.parse_args()

    if args.sheet_url:
        tmp_dir = Path(".tmp_commissioner_extract") / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        tabs = args.tabs or [
            "TRANSACTIONS",
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
        input_dir = _export_tabs(args.sheet_url, tabs, tmp_dir, max_rows=args.max_rows)
    else:
        input_dir = Path(args.input_dir)

    parsed = parse_commissioner_dir(Path(input_dir))

    # Transform to long-form tables using parser function
    roster_tables = prepare_roster_tables(parsed)

    # Write normalized Parquet via writer
    write_all_commissioner_tables(
        roster_tables=roster_tables,
        transactions_tables={
            "transactions": pl.DataFrame(),
            "unmapped_players": pl.DataFrame(),
        },  # Not parsing TRANSACTIONS tab here
        base_uri=args.out_raw,
    )

    # Optionally write raw tabs (Tier 0) to Parquet if requested
    if args.out_raw_tabs:
        from ingest.common.storage import write_parquet_any

        dt = datetime.now(UTC).strftime("%Y-%m-%d")
        base = args.out_raw_tabs.rstrip("/")
        for gm_dir in sorted([p for p in Path(input_dir).iterdir() if p.is_dir()]):
            tab = gm_dir.name
            csv_file = gm_dir / f"{tab}.csv"
            if not csv_file.exists():
                continue
            table_data = pl.read_csv(csv_file)
            uri = f"{base}/{tab}/dt={dt}/{tab}.parquet"
            write_parquet_any(table_data, uri)

    # Write CSV previews for review
    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    out_csv_base = Path(args.out_csv)
    out_csv_base.mkdir(parents=True, exist_ok=True)

    for name, frame in roster_tables.items():
        if frame.is_empty():
            continue
        tdir = out_csv_base / name / f"dt={dt}"
        tdir.mkdir(parents=True, exist_ok=True)
        (tdir / f"{name}.csv").write_text(frame.write_csv())
    print(json.dumps({k: int(v.height) for k, v in roster_tables.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
