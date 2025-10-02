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
# V3: TRANSACTIONS parser
# -----------------------------


def _derive_transaction_type(period_type: str, txn_type: str, rfa_matched: str) -> str:
    """Derive precise transaction type using dim_timeframe.period_type.

    Args:
        period_type: From dim_timeframe (e.g., 'rookie_draft', 'faad', 'regular')
        txn_type: Raw Type column value
        rfa_matched: RFA Matched column value

    Returns:
        Refined transaction type string
    """
    # Rookie draft selections
    if period_type == "rookie_draft":
        return "rookie_draft_selection"

    # Franchise tags (offseason only)
    if txn_type == "Franchise":
        return "franchise_tag"

    # FAAD signings (period_type='faad')
    if period_type == "faad":
        if txn_type == "Signing" and rfa_matched == "yes":
            return "faad_rfa_matched"
        elif txn_type in ["Signing", "FA"]:
            return "faad_ufa_signing"

    # FASA signings (in-season, preseason, offseason, deadline)
    if period_type in ["regular", "deadline", "preseason", "offseason"]:
        if txn_type == "Signing":
            return "fasa_signing"

    # Offseason free agency (FA type outside FAAD)
    if period_type == "offseason" and txn_type == "FA":
        return "offseason_ufa_signing"

    # Straightforward mappings
    if txn_type == "Trade":
        return "trade"
    if txn_type == "Cut":
        return "cut"
    if txn_type == "Waivers":
        return "waiver_claim"
    if txn_type == "Extension":
        return "contract_extension"
    if txn_type == "Amnesty":
        return "amnesty_cut"

    return "unknown"


def _infer_asset_type(player_str: str, position_str: str) -> str:
    """Infer asset type from player name and position.

    Args:
        player_str: Player column value
        position_str: Position column value

    Returns:
        Asset type: player, pick, cap_space, defense, or unknown
    """
    if not player_str or player_str == "-":
        return "unknown"
    elif "Round" in player_str:
        return "pick"
    elif "Cap Space" in player_str:
        return "cap_space"
    elif position_str == "D/ST":
        return "defense"
    elif position_str and position_str != "-":
        return "player"
    else:
        return "unknown"


def _normalize_player_name(name: str) -> str:
    """Normalize player name for fuzzy matching.

    Removes periods from initials, removes suffixes, lowercase, strip.

    Args:
        name: Raw player name

    Returns:
        Normalized name for matching
    """
    if not name:
        return ""
    # Remove periods from initials (A.J. → AJ)
    normalized = name.replace(".", "")
    # Remove common suffixes
    for suffix in [" Jr", " Jr.", " II", " III", " IV", " Sr", " Sr."]:
        normalized = normalized.replace(suffix, "")
    # Lowercase and strip
    return normalized.lower().strip()


def _parse_pick_id(player_str: str, pick_col: str) -> str | None:
    """Parse pick reference to standardized pick_id.

    Args:
        player_str: Player column value (e.g., "2025 1st Round")
        pick_col: Pick column value (slot number or "TBD")

    Returns:
        pick_id in format YYYY_R#_P## or YYYY_R#_TBD, or None if not a pick
    """
    import re

    if not player_str:
        return None

    match = re.match(r"(\d{4}) (\d)(?:st|nd|rd|th) Round", player_str)
    if not match:
        return None

    season, round_num = int(match.group(1)), int(match.group(2))

    if pick_col and pick_col != "TBD" and pick_col != "-":
        slot = int(pick_col)
        return f"{season}_R{round_num}_P{slot:02d}"
    else:
        return f"{season}_R{round_num}_TBD"  # Synthetic ID


def _parse_contract_fields(df: pl.DataFrame) -> pl.DataFrame:
    """Parse contract and split columns into structured fields.

    Args:
        df: DataFrame with Contract and Split columns

    Returns:
        DataFrame with added columns: total, years, split_array
    """

    def parse_contract(contract_str, split_str):
        if not contract_str or contract_str == "-":
            return {"total": None, "years": None, "split_array": None}

        parts = contract_str.split("/")
        if len(parts) != 2:
            return {"total": None, "years": None, "split_array": None}

        total, years = int(parts[0]), int(parts[1])

        if split_str and split_str != "-":
            split_array = [int(x) for x in split_str.split("-")]
            # Validate (but keep data even if validation fails)
            if len(split_array) != years or sum(split_array) != total:
                pass  # Log warning in production
            return {"total": total, "years": years, "split_array": split_array}
        else:
            # Even distribution
            per_year = total // years
            return {"total": total, "years": years, "split_array": [per_year] * years}

    contract_struct_type = pl.Struct(
        {"total": pl.Int64, "years": pl.Int64, "split_array": pl.List(pl.Int64)}
    )

    contract_parsed = df.select(
        pl.struct(["Contract", "Split"])
        .map_elements(lambda x: parse_contract(x["Contract"], x["Split"]), return_dtype=contract_struct_type)
        .alias("contract_parsed")
    ).unnest("contract_parsed")

    return df.hstack(contract_parsed)


def _map_player_names(df: pl.DataFrame) -> pl.DataFrame:
    """Map player names to player_id using crosswalk and alias seeds.

    Args:
        df: DataFrame with Player and asset_type columns

    Returns:
        DataFrame with added player_id column (-1 for unmapped)
    """
    xref_path = Path("dbt/ff_analytics/seeds/dim_player_id_xref.csv")
    if not xref_path.exists():
        raise FileNotFoundError(f"dim_player_id_xref seed not found at {xref_path}")

    xref = pl.read_csv(xref_path)

    # Load name alias seed for typo corrections
    alias_path = Path("dbt/ff_analytics/seeds/dim_name_alias.csv")
    if alias_path.exists():
        alias_seed = pl.read_csv(alias_path)
        # Apply aliases first (replace Player with canonical_name where alias exists)
        df = df.join(
            alias_seed.select(["alias_name", "canonical_name"]),
            left_on="Player",
            right_on="alias_name",
            how="left",
        ).with_columns(pl.coalesce([pl.col("canonical_name"), pl.col("Player")]).alias("Player")).drop(
            "canonical_name"
        )

    # Exact match
    df = df.join(
        xref.select(["name", "player_id"]).rename({"player_id": "player_id_exact"}),
        left_on="Player",
        right_on="name",
        how="left",
    )

    # Enhanced fuzzy match for nulls
    df = df.with_columns(
        pl.when(pl.col("player_id_exact").is_null() & (pl.col("asset_type") == "player"))
        .then(pl.col("Player").map_elements(_normalize_player_name, return_dtype=pl.String))
        .alias("player_normalized")
    )

    df = df.join(
        xref.select(["merge_name", "player_id"]).rename({"player_id": "player_id_fuzzy"}),
        left_on="player_normalized",
        right_on="merge_name",
        how="left",
    )

    # Coalesce exact and fuzzy
    df = df.with_columns(
        pl.coalesce([pl.col("player_id_exact"), pl.col("player_id_fuzzy")])
        .fill_null(-1)  # Unmapped marker
        .alias("player_id")
    ).drop(["player_id_exact", "player_id_fuzzy", "player_normalized"])

    return df


def parse_transactions(csv_path: Path) -> dict[str, pl.DataFrame]:
    """Parse TRANSACTIONS tab to normalized format.

    Returns:
        dict with keys:
            'transactions': Main transaction table (one row per asset)
            'unmapped_players': QA table for manual review
            'unmapped_picks': QA table for TBD picks
    """
    from datetime import UTC, datetime

    # Load raw transactions
    df = pl.read_csv(csv_path)

    # Join to dim_timeframe for period_type classification
    timeframe_seed_path = Path("dbt/ff_analytics/seeds/dim_timeframe.csv")
    if not timeframe_seed_path.exists():
        raise FileNotFoundError(f"dim_timeframe seed not found at {timeframe_seed_path}")

    timeframe_seed = pl.read_csv(timeframe_seed_path)
    df = df.join(
        timeframe_seed.select(
            ["timeframe_string", "season", "period_type", "week", "sort_sequence"]
        ),
        left_on="Time Frame",
        right_on="timeframe_string",
        how="left",
    )

    # Derive transaction_type_refined using helper
    df = df.with_columns(
        pl.struct(["period_type", "Type", "RFA Matched"])
        .map_elements(
            lambda x: _derive_transaction_type(x["period_type"], x["Type"], x["RFA Matched"]),
            return_dtype=pl.String,
        )
        .alias("transaction_type_refined")
    )

    # Infer asset_type using helper
    df = df.with_columns(
        pl.struct(["Player", "Position"])
        .map_elements(
            lambda x: _infer_asset_type(x["Player"], x["Position"]),
            return_dtype=pl.String,
        )
        .alias("asset_type")
    )

    # Parse contract fields using helper
    df = _parse_contract_fields(df)

    # Handle cap_space amounts (use Split column instead of Contract)
    df = df.with_columns(
        pl.when(pl.col("asset_type") == "cap_space")
        .then(pl.col("Split").cast(pl.Int32, strict=False))
        .otherwise(pl.col("total"))
        .alias("total")
    )

    # Map player names to player_id using helper
    df = _map_player_names(df)

    # Map pick references to pick_id using helper
    df = df.with_columns(
        pl.struct(["Player", "Pick"])
        .map_elements(
            lambda x: _parse_pick_id(x["Player"], x["Pick"]),
            return_dtype=pl.String,
        )
        .alias("pick_id")
    )

    # Clean transaction_id (Sort column)
    df = df.with_columns(
        pl.col("Sort")
        .str.replace_all(",", "")
        .str.replace_all('"', "")
        .cast(pl.Int64, strict=False)
        .alias("transaction_id")
    )

    # Handle duplicate transaction_ids
    df = df.with_columns(
        (
            pl.col("transaction_id").cast(pl.String)
            + "_"
            + pl.arange(0, pl.len()).over("transaction_id").cast(pl.String)
        ).alias("transaction_id_unique")
    )

    # Select final columns
    transactions = df.select(
        [
            "transaction_id_unique",
            "transaction_id",
            "transaction_type_refined",
            "asset_type",
            "Time Frame",
            "season",
            "period_type",
            "week",
            "sort_sequence",
            "From",
            "To",
            "Original Order",
            "Round",
            "Pick",
            "Position",
            "Player",
            "player_id",
            "pick_id",
            "Contract",
            "Split",
            "total",
            "years",
            "split_array",
            "RFA Matched",
            "FAAD Comp",
            "Type",
        ]
    )

    # QA tables
    unmapped_players = df.filter(
        (pl.col("asset_type") == "player") & (pl.col("player_id") == -1)
    ).select(["Player", "Position", "Time Frame", "From", "To"])

    unmapped_picks = df.filter(
        (pl.col("asset_type") == "pick") & (pl.col("pick_id").is_null())
    ).select(["Player", "Pick", "Time Frame", "From", "To"])

    # Write output
    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    base_path = "data/raw/commissioner/transactions"

    # Main transactions table
    uri = f"{base_path}/dt={dt}/transactions.parquet"
    write_parquet_any(transactions, uri)

    # QA tables for observability
    qa_base = "data/raw/commissioner/transactions_qa"
    if unmapped_players.height > 0:
        unmapped_uri = f"{qa_base}/dt={dt}/unmapped_players.parquet"
        write_parquet_any(unmapped_players, unmapped_uri)

    if unmapped_picks.height > 0:
        unmapped_picks_uri = f"{qa_base}/dt={dt}/unmapped_picks.parquet"
        write_parquet_any(unmapped_picks, unmapped_picks_uri)

    return {
        "transactions": transactions,
        "unmapped_players": unmapped_players,
        "unmapped_picks": unmapped_picks,
    }


# -----------------------------
# V2: normalized long-form tables
# -----------------------------


def _to_long_roster(roster_all: pl.DataFrame) -> pl.DataFrame:
    if roster_all.is_empty():
        return roster_all
    value_cols = [c for c in roster_all.columns if c.startswith("y20")]
    out = (
        roster_all.unpivot(
            index=["gm", "position", "player", "total", "rfa", "fr"],
            on=value_cols,
            variable_name="year_str",
            value_name="amount_str",
        )
        .with_columns(
            year=pl.col("year_str").str.replace("y", "").cast(pl.Int32),
            amount=pl.col("amount_str")
            .str.replace_all(r"[,$]", "")
            .str.replace("", "0")
            .cast(pl.Float64, strict=False),
            rfa=pl.col("rfa")
            .fill_null("")
            .cast(pl.Utf8)
            .str.strip_chars()
            .map_elements(lambda x: x.lower() == "x"),
            franchise=pl.col("fr")
            .fill_null("")
            .cast(pl.Utf8)
            .str.strip_chars()
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
        cuts_all.unpivot(
            index=["gm", "player", "position", "total"],
            on=value_cols,
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
    # Unpivot to long and interpret values as rounds
    long = base.unpivot(
        index=["gm", "owner", "trade_conditions"],
        on=year_cols,
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
        condition_flag=pl.col("trade_conditions")
        .fill_null("")
        .cast(pl.Utf8)
        .str.strip_chars()
        .ne(""),
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
        pl.col("trade_conditions").is_not_null()
        & (pl.col("trade_conditions").cast(pl.Utf8).str.strip_chars() != "")
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
