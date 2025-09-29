"""Commissioner sheet parser → normalized tables.

Parses exported per-GM CSV tabs like those under `samples/sheets/<GM>/<GM>.csv`
into normalized dataframes:
  - roster: active roster with contract columns by year
  - cut_contracts: dead cap commitments
  - draft_picks: current draft pick ownership

Writes Parquet to `data/raw/commissioner/<table>/dt=YYYY-MM-DD/` via storage helper.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from ingest.common.storage import write_parquet_any


@dataclass
class ParsedGM:
    """Parsed outputs for a single GM tab.

    - gm: display name
    - roster: active contracts table
    - cuts: cut contracts (dead cap) table
    - picks: draft picks/ownership table
    """

    gm: str
    roster: pl.DataFrame
    cuts: pl.DataFrame
    picks: pl.DataFrame


def _read_csv_rows(path: Path) -> list[list[str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        return [list(row) for row in reader]


def _extract_gm_name(rows: list[list[str]]) -> str | None:
    for row in rows[:5]:
        if row and row[0].strip().lower().startswith("gm:"):
            return row[0].split(":", 1)[1].strip()
    return None


def _find_header_index(rows: list[list[str]]) -> int | None:
    """Return the first row index whose first cell equals 'Pos.'."""
    for i, row in enumerate(rows):
        if row and row[0].strip() == "Pos.":
            return i
    return None


def _find_block_starts(header: list[str]) -> tuple[list[int], int | None, int | None]:
    """Return (roster_cols, cut_start, picks_start) offsets based on header cells."""
    roster_cols = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10]
    cut_start = None
    for j in range(11, len(header)):
        if header[j].strip() == "Player":
            cut_start = j
            break
    picks_start = None
    for j in range(0, len(header)):
        if header[j].strip() == "Draft Pick Owner":
            picks_start = j
            break
    return roster_cols, cut_start, picks_start


def _slice_roster_row(row: list[str], roster_cols: list[int]) -> list[str] | None:
    player_val = row[1].strip() if len(row) > 1 else ""
    if not player_val:
        return None
    return [row[c].strip() if c < len(row) else "" for c in roster_cols]


def _slice_cuts_row(row: list[str], cut_start: int | None) -> list[str] | None:
    if cut_start is None or len(row) <= cut_start + 6:
        return None
    sub = [cell.strip() for cell in row[cut_start : cut_start + 8]]
    return sub if sub[0] else None


def _slice_picks_row(row: list[str], picks_start: int | None) -> list[str] | None:
    if picks_start is None or len(row) <= picks_start + 6:
        return None
    sub = [cell.strip() for cell in row[picks_start : picks_start + 7]]
    return sub if sub[0] else None


def _parse_blocks(rows: list[list[str]]) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Parse three side-by-side blocks starting at the header row with 'Pos.'."""
    header_idx = _find_header_index(rows)
    if header_idx is None:
        return pl.DataFrame(), pl.DataFrame(), pl.DataFrame()

    hdr = rows[header_idx]
    roster_cols, cut_start, picks_start = _find_block_starts(hdr)

    roster_rows: list[list[str]] = []
    cut_rows: list[list[str]] = []
    picks_rows: list[list[str]] = []

    for row in rows[header_idx + 1 :]:
        if not any(cell.strip() for cell in row):
            continue
        sliced = _slice_roster_row(row, roster_cols)
        if sliced is not None:
            roster_rows.append(sliced)
        sliced = _slice_cuts_row(row, cut_start)
        if sliced is not None:
            cut_rows.append(sliced)
        sliced = _slice_picks_row(row, picks_start)
        if sliced is not None:
            picks_rows.append(sliced)

    if roster_rows:
        roster_df = pl.DataFrame(
            roster_rows,
            schema=[
                "position",
                "player",
                "y2025",
                "y2026",
                "y2027",
                "y2028",
                "y2029",
                "total",
                "rfa",
                "fr",
            ],
            orient="row",
        )
    else:
        roster_df = pl.DataFrame(
            schema=[
                "position",
                "player",
                "y2025",
                "y2026",
                "y2027",
                "y2028",
                "y2029",
                "total",
                "rfa",
                "fr",
            ]
        )

    if cut_rows:
        cuts_df = pl.DataFrame(
            cut_rows,
            schema=[
                "player",
                "position",
                "y2025",
                "y2026",
                "y2027",
                "y2028",
                "y2029",
                "total",
            ],
            orient="row",
        )
    else:
        cuts_df = pl.DataFrame(
            schema=["player", "position", "y2025", "y2026", "y2027", "y2028", "y2029", "total"]
        )

    if picks_rows:
        picks_df = pl.DataFrame(
            picks_rows,
            schema=[
                "owner",
                "y2026",
                "y2027",
                "y2028",
                "y2029",
                "y2030",
                "trade_conditions",
            ],
            orient="row",
        )
    else:
        picks_df = pl.DataFrame(
            schema=["owner", "y2026", "y2027", "y2028", "y2029", "y2030", "trade_conditions"]
        )

    return roster_df, cuts_df, picks_df


def parse_gm_tab(csv_path: Path) -> ParsedGM:
    """Parse a single GM CSV tab and return normalized DataFrames for that GM."""
    rows = _read_csv_rows(csv_path)
    gm = _extract_gm_name(rows) or csv_path.parent.name
    roster, cuts, picks = _parse_blocks(rows)

    # Add GM column and basic cleaning
    roster = roster.with_columns(
        gm=pl.lit(gm),
    )[["gm", *roster.columns]]
    cuts = cuts.with_columns(gm=pl.lit(gm))[["gm", *cuts.columns]]
    picks = picks.with_columns(gm=pl.lit(gm))[["gm", *picks.columns]]
    return ParsedGM(gm=gm, roster=roster, cuts=cuts, picks=picks)


def parse_commissioner_dir(in_dir: Path) -> list[ParsedGM]:
    """Parse all GM tabs in a directory structure like `samples/sheets`.

    Expects each GM subfolder to contain a single CSV named `<GM>.csv`.
    Non-matching folders are skipped.
    """
    results: list[ParsedGM] = []
    for gm_dir in sorted([p for p in in_dir.iterdir() if p.is_dir()]):
        # Each GM subfolder should contain `<GM>.csv`.
        # Skip others (e.g., folders with only _meta.json).
        csv_file = gm_dir / f"{gm_dir.name}.csv"
        if csv_file.exists():
            results.append(parse_gm_tab(csv_file))
    return results


def write_normalized(
    outputs: Iterable[ParsedGM], out_dir: str = "data/raw/commissioner"
) -> dict[str, int]:
    """Write normalized parquet snapshots for roster, cuts, picks.

    Returns counts by table.
    """
    import uuid
    from datetime import UTC, datetime

    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    base = out_dir.rstrip("/")
    counts = {"roster": 0, "cut_contracts": 0, "draft_picks": 0}

    if outputs:
        roster_list = [o.roster for o in outputs if o.roster.height > 0]
        cuts_list = [o.cuts for o in outputs if o.cuts.height > 0]
        picks_list = [o.picks for o in outputs if o.picks.height > 0]
        roster_all = pl.concat(roster_list, how="diagonal") if roster_list else pl.DataFrame()
        cuts_all = pl.concat(cuts_list, how="diagonal") if cuts_list else pl.DataFrame()
        picks_all = pl.concat(picks_list, how="diagonal") if picks_list else pl.DataFrame()
    else:
        roster_all = pl.DataFrame()
        cuts_all = pl.DataFrame()
        picks_all = pl.DataFrame()

    if roster_all.height:
        uri = f"{base}/roster/dt={dt}/roster_{uuid.uuid4().hex[:8]}.parquet"
        write_parquet_any(roster_all, uri)
        counts["roster"] = roster_all.height
    if cuts_all.height:
        uri = f"{base}/cut_contracts/dt={dt}/cut_contracts_{uuid.uuid4().hex[:8]}.parquet"
        write_parquet_any(cuts_all, uri)
        counts["cut_contracts"] = cuts_all.height
    if picks_all.height:
        uri = f"{base}/draft_picks/dt={dt}/draft_picks_{uuid.uuid4().hex[:8]}.parquet"
        write_parquet_any(picks_all, uri)
        counts["draft_picks"] = picks_all.height

    return counts
