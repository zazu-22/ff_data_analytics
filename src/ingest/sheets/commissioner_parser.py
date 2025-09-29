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
    owner = sub[0]
    # Drop header-like rows and repeated headings inside the picks block
    owner_l = owner.lower()
    if not owner:
        return None
    if owner_l in {"owner", "draft pick owner", "draft pick acquired", "draft pick acquried"}:
        return None
    # If the year columns look like headers (e.g., '2026','2027',...), skip
    header_years = {"2026", "2027", "2028", "2029", "2030"}
    if any(v in header_years for v in sub[1:6]):
        return None
    return sub


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
    skip_dirs = {"transactions"}
    for gm_dir in sorted([p for p in in_dir.iterdir() if p.is_dir()]):
        if gm_dir.name.lower() in skip_dirs:
            continue
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


# -----------------------------
# V2: normalized long-form tables
# -----------------------------


def _to_long_roster(roster_all: pl.DataFrame) -> pl.DataFrame:
    if roster_all.is_empty():
        return roster_all
    value_cols = [c for c in roster_all.columns if c.startswith("y20")]
    out = (
        roster_all.melt(
            id_vars=["gm", "position", "player", "total", "rfa", "fr"],
            value_vars=value_cols,
            variable_name="year_str",
            value_name="amount_str",
        )
        .with_columns(
            year=pl.col("year_str").str.replace("y", "").cast(pl.Int32),
            amount=pl.col("amount_str")
            .str.replace_all(r"[,$]", "")
            .str.replace("", "0")
            .cast(pl.Float64, strict=False),
            rfa=pl.col("rfa").fill_null("").str.strip().map_elements(lambda x: x.lower() == "x"),
            franchise=pl.col("fr")
            .fill_null("")
            .str.strip()
            .map_elements(lambda x: x.lower() == "x"),
        )
        .drop(["year_str", "amount_str", "total", "fr"])
        .filter(pl.col("amount").is_not_null() & (pl.col("amount") > 0))
    )
    return out


def _to_long_cuts(cuts_all: pl.DataFrame) -> pl.DataFrame:
    if cuts_all.is_empty():
        return cuts_all
    value_cols = [c for c in cuts_all.columns if c.startswith("y20")]
    out = (
        cuts_all.melt(
            id_vars=["gm", "player", "position", "total"],
            value_vars=value_cols,
            variable_name="year_str",
            value_name="amount_str",
        )
        .with_columns(
            year=pl.col("year_str").str.replace("y", "").cast(pl.Int32),
            dead_cap_amount=pl.col("amount_str")
            .str.replace_all(r"[,$]", "")
            .str.replace("", "0")
            .cast(pl.Float64, strict=False),
        )
        .drop(["year_str", "amount_str", "total"])
        .filter(pl.col("dead_cap_amount").is_not_null() & (pl.col("dead_cap_amount") > 0))
    )
    return out


def _to_picks_tables(picks_all: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    if picks_all.is_empty():
        return picks_all, pl.DataFrame()
    # picks_all: gm, owner, y2026..y2030, trade_conditions
    year_cols = [c for c in picks_all.columns if c.startswith("y20")]
    base = picks_all.select(["gm", "owner", *year_cols, "trade_conditions"])
    # Melt to long and interpret values as rounds
    long = base.melt(
        id_vars=["gm", "owner", "trade_conditions"],
        value_vars=year_cols,
        variable_name="year_str",
        value_name="round_str",
    ).with_columns(
        year=pl.col("year_str").str.replace("y", "").cast(pl.Int32),
        round=pl.col("round_str").cast(pl.Int32, strict=False),
    )
    # Keep only actual picks where round is present (1..5)
    long = long.filter(pl.col("round").is_not_null())

    def _source_type(owner: str, gm: str) -> str:
        o = (owner or "").lower()
        if o == gm.lower():
            return "owned"
        # treat anything else as acquired; capture details
        return "acquired"

    picks = long.with_columns(
        source_type=pl.struct(["owner", "gm"]).map_elements(
            lambda s: _source_type(s["owner"], s["gm"])  # noqa: E731
        )
    )

    # Extract acquisition fields
    picks = picks.with_columns(
        acquired_from=pl.when(pl.col("source_type") == "acquired")
        .then(pl.col("owner"))
        .otherwise(pl.lit(None)),
        original_owner=pl.when(pl.col("source_type") == "owned")
        .then(pl.col("owner"))
        .otherwise(pl.lit(None)),
        acquisition_note=pl.when(pl.col("source_type") == "acquired")
        .then(pl.col("owner"))
        .otherwise(pl.lit(None)),
        condition_flag=pl.col("trade_conditions").fill_null("").str.strip().ne(""),
    )

    picks_tbl = picks.select(
        [
            "gm",
            "year",
            "round",
            "source_type",
            "original_owner",
            "acquired_from",
            "acquisition_note",
            "condition_flag",
        ]
    )

    # Conditions table
    conds = long.filter(
        pl.col("trade_conditions").is_not_null() & (pl.col("trade_conditions").str.strip() != "")
    ).select(["gm", "year", "round", pl.col("trade_conditions").alias("condition_text")])
    return picks_tbl, conds


def write_normalized_v2(
    outputs: Iterable[ParsedGM], out_dir: str = "data/raw/commissioner"
) -> dict[str, int]:
    """Write long-form normalized tables for contracts and picks."""
    import uuid
    from datetime import UTC, datetime

    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    base = out_dir.rstrip("/")
    counts: dict[str, int] = {
        "contracts_active": 0,
        "contracts_cut": 0,
        "draft_picks": 0,
        "draft_pick_conditions": 0,
    }

    roster_all = (
        pl.concat([o.roster for o in outputs if o.roster.height > 0], how="diagonal")
        if outputs
        else pl.DataFrame()
    )
    cuts_all = (
        pl.concat([o.cuts for o in outputs if o.cuts.height > 0], how="diagonal")
        if outputs
        else pl.DataFrame()
    )
    picks_all = (
        pl.concat([o.picks for o in outputs if o.picks.height > 0], how="diagonal")
        if outputs
        else pl.DataFrame()
    )

    contracts_active = _to_long_roster(roster_all)
    contracts_cut = _to_long_cuts(cuts_all)
    picks_tbl, conds_tbl = _to_picks_tables(picks_all)

    if not contracts_active.is_empty():
        uri = f"{base}/contracts_active/dt={dt}/contracts_active_{uuid.uuid4().hex[:8]}.parquet"
        write_parquet_any(contracts_active, uri)
        counts["contracts_active"] = int(contracts_active.height)
    if not contracts_cut.is_empty():
        uri = f"{base}/contracts_cut/dt={dt}/contracts_cut_{uuid.uuid4().hex[:8]}.parquet"
        write_parquet_any(contracts_cut, uri)
        counts["contracts_cut"] = int(contracts_cut.height)
    if not picks_tbl.is_empty():
        uri = f"{base}/draft_picks/dt={dt}/draft_picks_{uuid.uuid4().hex[:8]}.parquet"
        write_parquet_any(picks_tbl, uri)
        counts["draft_picks"] = int(picks_tbl.height)
    if not conds_tbl.is_empty():
        uri = (
            f"{base}/draft_pick_conditions/dt={dt}/draft_pick_conditions_"
            f"{uuid.uuid4().hex[:8]}.parquet"
        )
        write_parquet_any(conds_tbl, uri)
        counts["draft_pick_conditions"] = int(conds_tbl.height)

    return counts
