"""Commissioner Sheets end-to-end parser runner.

Options:
- Pull tabs from a Google Sheet (by URL) into a local temp dir, then parse
- Or parse an existing local directory exported earlier (e.g., from samples)

Outputs:
- Writes normalized Parquet to `--out-raw` via the storage helper (local or gs://)
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
    write_normalized,
)


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
            seen = {}
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
    p.add_argument(
        "--out-raw", default="data/raw/commissioner", help="Parquet output base (local or gs://)"
    )
    p.add_argument(
        "--out-csv", default="data/review/commissioner", help="CSV preview output base (local only)"
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

    # Write Parquet via helper
    write_normalized(parsed, out_dir=args.out_raw)

    # Write CSV previews for review
    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    out_csv_base = Path(args.out_csv)
    out_csv_base.mkdir(parents=True, exist_ok=True)
    tables = _concat(parsed)
    for name, df in tables.items():
        if df.height == 0:
            continue
        tdir = out_csv_base / name / f"dt={dt}"
        tdir.mkdir(parents=True, exist_ok=True)
        (tdir / f"{name}.csv").write_text(df.write_csv())
    print(json.dumps({k: int(v.height) for k, v in tables.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
