"""Commissioner sheet parser → normalized DataFrames (pure parsing, no I/O).

PURE PARSING: This module contains only parsing logic (CSV → DataFrames).
All file I/O has been extracted to `commissioner_writer.py` for clean separation.

Parses exported per-GM CSV tabs like those under `samples/sheets/<GM>/<GM>.csv`
into normalized DataFrames:
  - roster: active roster with contract columns by year
  - cut_contracts: dead cap commitments
  - draft_picks: current draft pick ownership

Parsing Functions:
  - parse_gm_tab(csv_path) → ParsedGM
  - parse_commissioner_dir(dir_path) → List[ParsedGM]
  - parse_transactions(csv_path) → dict[str, pl.DataFrame]
  - prepare_roster_tables(parsed_gms) → dict[str, pl.DataFrame]

For file writing, see `commissioner_writer.py`.
For orchestration, see `scripts/ingest/ingest_commissioner_sheet.py`.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import polars as pl

from ff_analytics_utils.name_alias import get_name_alias
from ff_analytics_utils.player_xref import get_player_xref

_FALSE_CONDITION_MARKERS = {
    "",
    "-",
    "none",
    "n/a",
    "na",
    "no",
    "false",
    "0",
}


@dataclass
class ParsedGM:
    """Parsed outputs for a single GM tab.

    - gm: display name
    - roster: active contracts table
    - cuts: cut contracts (dead cap) table
    - picks: draft picks/ownership table
    - cap_space: cap space by season table
    """

    gm: str
    roster: pl.DataFrame
    cuts: pl.DataFrame
    picks: pl.DataFrame
    cap_space: pl.DataFrame


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

    # Allow empty player names if there's a contract amount
    # Business rule: Required roster spots (QB, RB, WR, TE, FLEX, DL, LB, DB, K, D/ST)
    # that don't have a signed player get a $1 placeholder for mandatory weekly pickups.
    # These are legitimate cap obligations that must be included.
    if not player_val:
        # Check if there's a 2025 contract amount (column 2)
        amount_val = row[2].strip() if len(row) > 2 else ""
        amount_clean = amount_val.replace("$", "").replace(",", "").strip()
        if not amount_clean or amount_clean == "0":
            return None  # Truly empty row

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
                "roster_slot",
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
                "roster_slot",
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


def parse_cap_space(rows: list[list[str]], gm_name: str, tab_name: str) -> pl.DataFrame:
    """Parse cap space section from GM roster tab (row 3).

    Input: Raw CSV rows with row 3 format (all three sections in same row):
        Row 3: Available Cap Space,,$80,$80,$158,$183,$250,,,,,,
               Dead Cap Space,,$26,$13,$6,$0,$0,,Traded Cap Space,$7,$0,$0,$0,$0...

    Column structure:
        - Available Cap Space: columns 2-6 (years 2025-2029)
        - Dead Cap Space: columns 14-18 (years 2025-2029)
        - Traded Cap Space: columns 21-25 (years 2025-2029)

    Output: Long-form DataFrame
        Columns: gm, gm_tab, season, available_cap_space, dead_cap_space, traded_cap_space
        Rows: One per (gm, season) - typically 5 rows (2025-2029)

    Args:
        rows: Raw CSV rows from GM tab
        gm_name: GM display name (full name from sheet)
        tab_name: Tab/directory name (short identifier)

    Returns:
        DataFrame with cap space by season

    """
    # Find cap space row (row 3, contains "Available Cap Space")
    cap_space_row = None
    for _i, row in enumerate(rows[:10]):  # Cap space is in first 10 rows
        if not row:
            continue
        if "available cap space" in row[0].strip().lower():
            cap_space_row = row
            break

    # If no cap space data found, return empty DataFrame
    if not cap_space_row:
        return pl.DataFrame(
            schema={
                "gm": pl.Utf8,
                "gm_tab": pl.Utf8,
                "season": pl.Int32,
                "available_cap_space": pl.Int32,
                "dead_cap_space": pl.Int32,
                "traded_cap_space": pl.Int32,
            }
        )

    # Column offsets for the three cap space sections
    # Available Cap Space: columns 2-6
    # Dead Cap Space: columns 14-18
    # Traded Cap Space: columns 21-25
    available_start = 2
    dead_start = 14
    traded_start = 21

    seasons = [2025, 2026, 2027, 2028, 2029]
    cap_data = []

    for idx, season in enumerate(seasons):
        # Extract values from their respective column positions
        available_col = available_start + idx
        dead_col = dead_start + idx
        traded_col = traded_start + idx

        # Get values, handling missing columns
        available = cap_space_row[available_col] if available_col < len(cap_space_row) else "0"
        dead = cap_space_row[dead_col] if dead_col < len(cap_space_row) else "0"
        traded = cap_space_row[traded_col] if traded_col < len(cap_space_row) else "0"

        # Clean values (remove $ and commas)
        available_clean = available.strip().replace("$", "").replace(",", "") or "0"
        dead_clean = dead.strip().replace("$", "").replace(",", "") or "0"
        traded_clean = traded.strip().replace("$", "").replace(",", "") or "0"

        cap_data.append(
            {
                "gm": gm_name,
                "gm_tab": tab_name,
                "season": season,
                "available_cap_space": int(available_clean),
                "dead_cap_space": int(dead_clean),
                "traded_cap_space": int(traded_clean),
            }
        )

    return pl.DataFrame(cap_data)


def parse_gm_tab(csv_path: Path) -> ParsedGM:
    """Parse a single GM CSV tab and return normalized DataFrames for that GM."""
    rows = _read_csv_rows(csv_path)
    tab_name = csv_path.parent.name  # Tab/directory name (short identifier)
    gm_full_name = _extract_gm_name(rows) or tab_name  # Full name from sheet, fallback to tab
    roster, cuts, picks = _parse_blocks(rows)
    cap_space = parse_cap_space(rows, gm_full_name, tab_name)

    # Add GM columns (both full name and tab identifier) and basic cleaning
    roster = roster.with_columns(
        gm=pl.lit(gm_full_name),
        gm_tab=pl.lit(tab_name),
    )[["gm", "gm_tab", *roster.columns]]
    cuts = cuts.with_columns(
        gm=pl.lit(gm_full_name),
        gm_tab=pl.lit(tab_name),
    )[["gm", "gm_tab", *cuts.columns]]
    picks = picks.with_columns(
        gm=pl.lit(gm_full_name),
        gm_tab=pl.lit(tab_name),
    )[["gm", "gm_tab", *picks.columns]]
    return ParsedGM(gm=gm_full_name, roster=roster, cuts=cuts, picks=picks, cap_space=cap_space)


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


# -----------------------------
# TRANSACTIONS parser
# -----------------------------


def _derive_transaction_type(
    period_type: str, txn_type: str, rfa_matched: str, from_owner: str, to_owner: str
) -> str:
    """Derive precise transaction type using dim_timeframe.period_type.

    Args:
        period_type: From dim_timeframe (e.g., 'rookie_draft', 'faad', 'regular')
        txn_type: Raw Type column value
        rfa_matched: RFA Matched column value
        from_owner: Source owner/franchise name
        to_owner: Destination owner/franchise name

    Returns:
        Refined transaction type string

    """
    # Normalize owner strings (case-insensitive, strip whitespace)
    from_normalized = (from_owner or "").strip().lower()

    # Waiver claim special handling: Type="Cut" but From="Waiver Wire" or "Cap Space"
    if txn_type == "Cut":
        if from_normalized in ["waiver wire", "cap space"]:
            return "waiver_claim"
        return "cut"

    # Simple mappings
    simple_map = {
        "Trade": "trade",
        "Waivers": "waiver_claim",
        "Extension": "contract_extension",
        "Amnesty": "amnesty_cut",
    }
    if txn_type in simple_map:
        return simple_map[txn_type]

    # Period-specific logic
    if period_type == "rookie_draft":
        return "rookie_draft_selection"

    if txn_type == "Franchise":
        return "franchise_tag"

    if period_type == "faad":
        return "faad_rfa_matched" if rfa_matched == "yes" else "faad_ufa_signing"

    if period_type in ["regular", "deadline", "preseason", "offseason"]:
        if txn_type == "Signing":
            return "fasa_signing"
        if period_type == "offseason" and txn_type == "FA":
            return "offseason_ufa_signing"

    return "unknown"


def _infer_asset_type(player_str: str | None, position_str: str) -> str:
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


def _extract_suffix(name: str | None) -> tuple[str, str | None]:
    """Extract generational suffix from player name.

    Handles Jr/Jr./Junior, Sr/Sr./Senior, II, III, IV, V variations.

    Args:
        name: Raw player name (e.g., "Marvin Harrison Jr.")

    Returns:
        Tuple of (base_name, suffix) where suffix is normalized or None

    Examples:
        >>> _extract_suffix("Marvin Harrison Jr.")
        ("Marvin Harrison", "Jr.")
        >>> _extract_suffix("Patrick Mahomes II")
        ("Patrick Mahomes", "II")
        >>> _extract_suffix("Tom Brady")
        ("Tom Brady", None)

    """
    if not name:
        return "", None

    # Remove periods from initials (A.J. → AJ) but preserve suffix periods
    name_clean = name.strip()

    # Define suffix patterns (order matters - check longer patterns first)
    suffix_patterns = [
        (" Junior", " Jr."),  # Normalize "Junior" to "Jr."
        (" Jr.", " Jr."),
        (" Jr", " Jr."),
        (" Senior", " Sr."),  # Normalize "Senior" to "Sr."
        (" Sr.", " Sr."),
        (" Sr", " Sr."),
        (" II", " II"),
        (" III", " III"),
        (" IV", " IV"),
        (" V", " V"),
    ]

    for pattern, normalized_suffix in suffix_patterns:
        if name_clean.endswith(pattern):
            base_name = name_clean[: -len(pattern)].strip()
            return base_name, normalized_suffix.strip()

    return name_clean, None


def _normalize_player_name(name: str | None) -> str:
    """Normalize player name for fuzzy matching.

    Removes periods from initials, removes suffixes, lowercase, strip.
    This is used for the legacy fuzzy matching tier.

    Args:
        name: Raw player name

    Returns:
        Normalized name for matching

    """
    if not name:
        return ""

    # Extract base name (removes suffix)
    base_name, _ = _extract_suffix(name)

    # Remove periods from initials (A.J. → AJ)
    normalized = base_name.replace(".", "")

    # Lowercase and strip
    return normalized.lower().strip()


def _calculate_player_score(
    player_row: dict,
    input_suffix: str | None,
    has_position: bool,
    input_position: str | None,
) -> float:
    """Calculate disambiguation score for a player candidate.

    Higher score = better match. Used to disambiguate when multiple players
    have the same base name (e.g., Marvin Harrison Sr. vs Jr.).

    Scoring factors:
    - Suffix match: +1000 (exact suffix match)
    - Suffix expectation: +500 (no input suffix, but candidate has Jr/II/III → likely newer player)
    - Active player: +100 (team is not FA/FA*/RET)
    - Draft year recency: +0 to +50 (more recent = higher score, capped at 50 years)

    Args:
        player_row: Row dict from crosswalk with keys: name, position, team, draft_year
        input_suffix: Extracted suffix from input name (Jr., Sr., II, etc.) or None
        has_position: Whether position filtering is available
        input_position: Position from input (if has_position=True)

    Returns:
        Disambiguation score (higher = better match)

    """
    score = 0.0

    # Extract suffix from crosswalk name
    _, xref_suffix = _extract_suffix(player_row.get("name", ""))

    # 1. Suffix matching
    if input_suffix and xref_suffix:
        if input_suffix == xref_suffix:
            score += 1000  # Perfect suffix match
    elif not input_suffix and xref_suffix:
        # No suffix in input, but candidate has Jr/II/III
        # Assume user means the newer player (common case: "Marvin Harrison" in 2024 → Jr.)
        if xref_suffix in ["Jr.", "II", "III", "IV", "V"]:
            score += 500
    elif input_suffix and not xref_suffix:
        # Input has suffix but candidate doesn't → less likely match
        score -= 500

    # 2. Activity status (active players preferred)
    team = player_row.get("team", "")
    if team and team not in ["FA", "FA*", "RET", "", None]:
        score += 100

    # 3. Draft year recency (more recent = higher score)
    draft_year = player_row.get("draft_year")
    if draft_year:
        try:
            year_int = int(draft_year)
            # Add up to 50 points for recency (2024 = 50, 2023 = 49, ..., 1974 = 0)
            recency_score = max(0, min(50, year_int - 1974))
            score += recency_score
        except (ValueError, TypeError):
            pass

    return score


def _normalize_position(txn_position: str | None) -> list[str]:
    """Normalize commissioner position labels to crosswalk position labels.

    The commissioner uses IDP fantasy position labels (DL, DB, LB, K) while the
    crosswalk uses specific NFL positions (DE, DT, S, CB, PK). This function
    maps commissioner labels to a list of possible crosswalk positions.

    Args:
        txn_position: Position from TRANSACTIONS sheet (DL, DB, LB, K, QB, RB, etc.)

    Returns:
        List of equivalent crosswalk positions (e.g., DL → ['DE', 'DT'])

    Examples:
        >>> _normalize_position("DL")
        ['DE', 'DT']
        >>> _normalize_position("QB")
        ['QB']
        >>> _normalize_position(None)
        []

    """
    if not txn_position:
        return []

    position_map = {
        # Defensive positions with hybrid role support
        "DL": ["DE", "DT", "LB"],  # Defensive Line → includes edge rushers (LB/DE hybrid)
        "DB": ["S", "CB", "LB"],  # Defensive Back → includes hybrid safety/linebackers
        "LB": ["LB", "DE", "S", "CB"],  # Linebacker → includes edge rushers and hybrid DBs
        "K": ["PK"],  # Kicker → Place Kicker
        # Offensive positions - permissive for position changes and multi-role players
        "QB": ["QB", "TE", "WR", "RB"],  # QB → includes Taysom Hill types and position changers
        "RB": ["RB", "WR", "TE"],  # RB → includes players who switched positions
        "WR": ["WR", "RB", "TE"],  # WR → includes players who switched positions
        "TE": ["TE", "WR", "QB"],  # TE → includes H-backs and position changes
        "FB": ["FB", "RB", "TE"],  # FB → fullback variants
        # Special cases
        "D/ST": ["DST"],
        "DST": ["DST"],
        # Multi-position (Travis Hunter type)
        "WR/DB": ["WR", "CB", "S", "LB"],  # Multi-position players
        "RB/WR": ["RB", "WR"],
    }

    return position_map.get(txn_position.strip().upper(), [txn_position.strip().upper()])


def _parse_pick_id(player_str: str | None, pick_col: str) -> dict | None:
    """Parse pick reference to structured pick information.

    Args:
        player_str: Player column value (e.g., "2025 1st Round")
        pick_col: Pick column value (overall pick number or "TBD")

    Returns:
        dict with:
          - pick_season: Draft year (int)
          - pick_round: Round number (int)
          - pick_overall_number: Overall pick number from sheet (int or None)
          - pick_id_raw: Raw combined format YYYY_R#_P## (str)
        or None if not a pick

    Note:
        The Pick column contains OVERALL pick numbers (1-60+), not within-round slots.
        Example: "23" means the 23rd overall pick, which with comp picks could be
        Round 2, Slot 11 (if R1 had 5 comp picks making 17 total R1 picks).

        Canonical pick_id assignment happens in dbt by matching overall pick numbers
        to dim_pick after compensatory picks are properly sequenced.

    """
    import re

    if not player_str:
        return None

    match = re.match(r"(\d{4}) (\d)(?:st|nd|rd|th) Round", player_str)
    if not match:
        return None

    season = int(match.group(1))
    round_num = int(match.group(2))

    if pick_col and pick_col != "TBD" and pick_col != "-":
        overall_pick = int(pick_col)
        # Raw pick_id uses overall pick number as-is (will be corrected in dbt)
        pick_id_raw = f"{season}_R{round_num}_P{overall_pick:02d}"
    else:
        overall_pick = None
        pick_id_raw = f"{season}_R{round_num}_TBD"

    return {
        "pick_season": season,
        "pick_round": round_num,
        "pick_overall_number": overall_pick,
        "pick_id_raw": pick_id_raw,
    }


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

        # Handle typo: "4.4" should be "4/4" (period instead of slash)
        contract_str = contract_str.replace(".", "/")

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
        .map_elements(
            lambda x: parse_contract(x["Contract"], x["Split"]), return_dtype=contract_struct_type
        )
        .alias("contract_parsed")
    ).unnest("contract_parsed")

    return df.hstack(contract_parsed)


def _apply_name_aliases(player_df: pl.DataFrame, has_position: bool) -> pl.DataFrame:
    """Apply name alias corrections from DuckDB table (with CSV fallback)."""
    try:
        alias_seed = get_name_alias()
    except RuntimeError:
        # No aliases available - return unchanged
        return player_df
    alias_has_position = "position" in alias_seed.columns

    if alias_has_position and has_position:
        alias_cols = ["alias_name", "canonical_name", "position"]
        if "treat_as_position" in alias_seed.columns:
            alias_cols.append("treat_as_position")

        player_df = player_df.join(
            alias_seed.select(alias_cols),
            left_on="Player",
            right_on="alias_name",
            how="left",
        )
        player_df = player_df.with_columns(
            pl.when(
                pl.col("canonical_name").is_null()
                | pl.col("position").is_null()
                | (pl.col("Position") == pl.col("position"))
            )
            .then(pl.coalesce([pl.col("canonical_name"), pl.col("Player")]))
            .otherwise(pl.col("Player"))
            .alias("Player")
        )

        if "treat_as_position" in player_df.columns:
            player_df = player_df.with_columns(
                pl.when(pl.col("treat_as_position").is_not_null())
                .then(pl.col("treat_as_position"))
                .otherwise(pl.col("Position"))
                .alias("Position")
            )
            player_df = player_df.drop(["canonical_name", "position", "treat_as_position"])
        else:
            player_df = player_df.drop(["canonical_name", "position"])
    else:
        player_df = (
            player_df.join(
                alias_seed.select(["alias_name", "canonical_name"]),
                left_on="Player",
                right_on="alias_name",
                how="left",
            )
            .with_columns(pl.coalesce([pl.col("canonical_name"), pl.col("Player")]).alias("Player"))
            .drop("canonical_name")
        )
    return player_df


def _score_and_select_best_match(
    df_joined: pl.DataFrame, row_idx_col: str, has_position: bool
) -> pl.DataFrame:
    """Score player matches and select best candidate per row."""
    scored_matches = []
    for row in df_joined.iter_rows(named=True):
        if row["player_id"] is None:
            scored_matches.append({row_idx_col: row[row_idx_col], "player_id": None, "score": -1.0})
        else:
            _, input_suffix = _extract_suffix(row["Player"])
            _, xref_suffix = _extract_suffix(row["name"])

            base_score = _calculate_player_score(
                player_row={
                    "name": row["name"],
                    "position": row.get("position"),
                    "team": row["team"],
                    "draft_year": row["draft_year"],
                },
                input_suffix=input_suffix,
                has_position=has_position,
                input_position=row.get("Position"),
            )

            if row["Player"] == row["name"]:
                if input_suffix and xref_suffix and input_suffix == xref_suffix:
                    base_score += 10000
                elif input_suffix is None and xref_suffix is None:
                    base_score += 100
                else:
                    base_score -= 100

            scored_matches.append(
                {row_idx_col: row[row_idx_col], "player_id": row["player_id"], "score": base_score}
            )

    df_scored = pl.DataFrame(scored_matches)
    return df_scored.sort("score", descending=True).unique(
        subset=[row_idx_col], keep="first", maintain_order=False
    )


def _exact_match_with_position(df: pl.DataFrame, xref: pl.DataFrame) -> pl.DataFrame:
    """Perform exact match with position filtering and suffix disambiguation."""
    df_with_idx = df.with_row_index("_row_idx_exact").with_columns(
        pl.col("Player")
        .map_elements(_normalize_player_name, return_dtype=pl.String)
        .alias("player_base_name")
    )

    df_exact = df_with_idx.join(
        xref.select(["merge_name", "player_id", "position", "name", "team", "draft_year"]),
        left_on="player_base_name",
        right_on="merge_name",
        how="left",
    )

    df_exact = df_exact.with_columns(
        pl.when(pl.col("player_id").is_null())
        .then(False)
        .otherwise(
            pl.col("Position")
            .map_elements(lambda p: _normalize_position(p), return_dtype=pl.List(pl.String))
            .list.contains(pl.col("position"))
        )
        .alias("position_compatible_exact")
    ).filter(pl.col("position_compatible_exact") | pl.col("player_id").is_null())

    df_exact_ids = _score_and_select_best_match(df_exact, "_row_idx_exact", True).select(
        ["_row_idx_exact", pl.col("player_id").alias("player_id_exact")]
    )

    return df_with_idx.join(df_exact_ids, on="_row_idx_exact", how="left").drop(
        ["_row_idx_exact", "player_base_name"]
    )


def _exact_match_no_position(df: pl.DataFrame, xref: pl.DataFrame) -> pl.DataFrame:
    """Perform exact match without position (roster parsing)."""
    df_with_idx = df.with_row_index("_row_idx_exact").with_columns(
        pl.col("Player")
        .map_elements(_normalize_player_name, return_dtype=pl.String)
        .alias("player_base_name")
    )

    df_exact = df_with_idx.join(
        xref.select(["merge_name", "player_id", "name", "team", "draft_year"]),
        left_on="player_base_name",
        right_on="merge_name",
        how="left",
    )

    df_exact_ids = _score_and_select_best_match(df_exact, "_row_idx_exact", False).select(
        ["_row_idx_exact", pl.col("player_id").alias("player_id_exact")]
    )

    return df_with_idx.join(df_exact_ids, on="_row_idx_exact", how="left").drop(
        ["_row_idx_exact", "player_base_name"]
    )


def _fuzzy_match_with_position(df: pl.DataFrame, xref: pl.DataFrame) -> pl.DataFrame:
    """Perform fuzzy match with position filtering."""
    df_with_idx = df.with_row_index("_row_idx_fuzzy")

    df_fuzzy = df_with_idx.join(
        xref.select(["merge_name", "player_id", "position", "name", "team", "draft_year"]),
        left_on="player_normalized",
        right_on="merge_name",
        how="left",
    )

    df_fuzzy = df_fuzzy.with_columns(
        pl.when(pl.col("player_id").is_null())
        .then(False)
        .otherwise(
            pl.col("Position")
            .map_elements(lambda p: _normalize_position(p), return_dtype=pl.List(pl.String))
            .list.contains(pl.col("position"))
        )
        .alias("position_compatible_fuzzy")
    ).filter(pl.col("position_compatible_fuzzy") | pl.col("player_id").is_null())

    df_fuzzy_ids = _score_and_select_best_match(df_fuzzy, "_row_idx_fuzzy", True).select(
        ["_row_idx_fuzzy", pl.col("player_id").alias("player_id_fuzzy")]
    )

    return df_with_idx.join(df_fuzzy_ids, on="_row_idx_fuzzy", how="left").drop("_row_idx_fuzzy")


def _fuzzy_match_no_position(df: pl.DataFrame, xref: pl.DataFrame) -> pl.DataFrame:
    """Perform fuzzy match without position."""
    df_with_idx = df.with_row_index("_row_idx_fuzzy")

    df_fuzzy = df_with_idx.join(
        xref.select(["merge_name", "player_id", "name", "team", "draft_year"]),
        left_on="player_normalized",
        right_on="merge_name",
        how="left",
    )

    df_fuzzy_ids = _score_and_select_best_match(df_fuzzy, "_row_idx_fuzzy", False).select(
        ["_row_idx_fuzzy", pl.col("player_id").alias("player_id_fuzzy")]
    )

    return df_with_idx.join(df_fuzzy_ids, on="_row_idx_fuzzy", how="left").drop("_row_idx_fuzzy")


def _partial_match(player_df: pl.DataFrame, xref: pl.DataFrame) -> pl.DataFrame:
    """Perform partial name matching for difficult cases."""
    player_df = player_df.with_columns(
        pl.coalesce([pl.col("player_id_exact"), pl.col("player_id_fuzzy")]).alias(
            "player_id_prelim"
        )
    )

    unmapped_mask = (pl.col("player_id_prelim").is_null()) & (pl.col("asset_type") == "player")

    player_df = player_df.with_columns(
        pl.when(unmapped_mask)
        .then(pl.col("Player").str.split(" ").list.first())
        .alias("first_name_token"),
        pl.when(unmapped_mask)
        .then(pl.col("Player").str.split(" ").list.last())
        .alias("last_name_token"),
    )

    df_unmapped_for_partial = player_df.filter(unmapped_mask)

    partial_matches: list[int | None] = []
    for row in df_unmapped_for_partial.iter_rows(named=True):
        if not row["first_name_token"] or not row["last_name_token"]:
            partial_matches.append(None)
            continue

        compatible_positions = _normalize_position(row["Position"])
        candidates = xref.filter(pl.col("position").is_in(compatible_positions))

        match = candidates.filter(
            pl.col("name").str.contains(row["first_name_token"], literal=True)
            & pl.col("name").str.contains(row["last_name_token"], literal=True)
        )

        partial_matches.append(match["player_id"][0] if match.height > 0 else None)

    df_partial = df_unmapped_for_partial.with_columns(
        pl.Series("player_id_partial", partial_matches)
    )
    df_unmapped = player_df.filter(~unmapped_mask).with_columns(
        pl.lit(None).cast(pl.Int64).alias("player_id_partial")
    )

    player_df = pl.concat([df_unmapped, df_partial], how="diagonal")

    return player_df.with_columns(
        pl.coalesce(
            [pl.col("player_id_exact"), pl.col("player_id_fuzzy"), pl.col("player_id_partial")]
        )
        .fill_null(-1)
        .alias("player_id")
    ).drop(
        [
            "player_id_exact",
            "player_id_fuzzy",
            "player_id_prelim",
            "player_id_partial",
            "first_name_token",
            "last_name_token",
            "player_normalized",
        ]
    )


def _map_player_names(player_df: pl.DataFrame) -> pl.DataFrame:
    """Map player names to player_id using crosswalk and alias seeds.

    Enhanced with position-aware disambiguation: when fuzzy matching finds multiple
    candidates (e.g., "Josh Allen" matches both Josh Allen QB and Josh Hines-Allen DE),
    the Position column (if present) is used to select the correct match.

    Args:
        player_df: DataFrame with Player and asset_type columns, optionally Position

    Returns:
        DataFrame with added player_id column (-1 for unmapped)

    """
    xref = _player_xref().clone()
    has_position = "Position" in player_df.columns

    # Apply name aliases
    player_df = _apply_name_aliases(player_df, has_position)

    # Exact match
    player_df = (
        _exact_match_with_position(player_df, xref)
        if has_position
        else _exact_match_no_position(player_df, xref)
    )

    # Fuzzy match
    player_df = player_df.with_columns(
        pl.when(pl.col("player_id_exact").is_null() & (pl.col("asset_type") == "player"))
        .then(pl.col("Player").map_elements(_normalize_player_name, return_dtype=pl.String))
        .alias("player_normalized")
    )

    player_df = (
        _fuzzy_match_with_position(player_df, xref)
        if has_position
        else _fuzzy_match_no_position(player_df, xref)
    )

    # Partial match (position only) or final coalesce
    if has_position:
        player_df = _partial_match(player_df, xref)
    else:
        player_df = player_df.with_columns(
            pl.coalesce([pl.col("player_id_exact"), pl.col("player_id_fuzzy")])
            .fill_null(-1)
            .alias("player_id")
        ).drop(["player_id_exact", "player_id_fuzzy", "player_normalized"])

    return player_df


@lru_cache(maxsize=1)
def _player_xref() -> pl.DataFrame:
    """Load the canonical player crosswalk, caching per process."""
    try:
        return get_player_xref()
    except Exception as exc:  # pragma: no cover - depends on local env
        raise RuntimeError(
            "Unable to load dim_player_id_xref. Ensure `make dbt-xref` has been run "
            "or set PLAYER_XREF_PARQUET_ROOT to a directory containing "
            "nflverse/ff_playerids parquet snapshots."
        ) from exc


def parse_transactions(csv_path: Path) -> dict[str, pl.DataFrame]:
    """Parse TRANSACTIONS tab to normalized format.

    Returns:
        dict with keys:
            'transactions': Main transaction table (one row per asset)
            'unmapped_players': QA table for manual review
            'unmapped_picks': QA table for TBD picks

    """
    # Load raw transactions
    transactions_df = pl.read_csv(csv_path)

    # Join to dim_timeframe for period_type classification
    timeframe_seed_path = Path("dbt/ff_data_transform/seeds/dim_timeframe.csv")
    if not timeframe_seed_path.exists():
        raise FileNotFoundError(f"dim_timeframe seed not found at {timeframe_seed_path}")

    timeframe_seed = pl.read_csv(timeframe_seed_path)
    transactions_df = transactions_df.join(
        timeframe_seed.select(
            ["timeframe_string", "season", "period_type", "week", "sort_sequence"]
        ),
        left_on="Time Frame",
        right_on="timeframe_string",
        how="left",
    )

    # Derive transaction_type_refined using helper
    transactions_df = transactions_df.with_columns(
        pl.struct(["period_type", "Type", "RFA Matched", "From", "To"])
        .map_elements(
            lambda x: _derive_transaction_type(
                x["period_type"], x["Type"], x["RFA Matched"], x["From"], x["To"]
            ),
            return_dtype=pl.String,
        )
        .alias("transaction_type_refined")
    )

    # Infer asset_type using helper
    transactions_df = transactions_df.with_columns(
        pl.struct(["Player", "Position"])
        .map_elements(
            lambda x: _infer_asset_type(x["Player"], x["Position"]),
            return_dtype=pl.String,
        )
        .alias("asset_type")
    )

    # Parse contract fields using helper
    transactions_df = _parse_contract_fields(transactions_df)

    # Handle cap_space amounts (use Split column instead of Contract)
    transactions_df = transactions_df.with_columns(
        pl.when(pl.col("asset_type") == "cap_space")
        .then(pl.col("Split").cast(pl.Int32, strict=False))
        .otherwise(pl.col("total"))
        .alias("total")
    )

    # Map player names to player_id using helper
    transactions_df = _map_player_names(transactions_df)

    # Map pick references to pick_id using helper (returns struct with multiple fields)
    def parse_pick_safe(x):
        """Handle None return from _parse_pick_id."""
        result = _parse_pick_id(x["Player"], x["Pick"])
        if result is None:
            # Return None values for non-pick rows
            return {
                "pick_season": None,
                "pick_round": None,
                "pick_overall_number": None,
                "pick_id_raw": None,
            }
        return result

    transactions_df = (
        transactions_df.with_columns(
            pl.struct(["Player", "Pick"])
            .map_elements(
                parse_pick_safe,
                return_dtype=pl.Struct(
                    {
                        "pick_season": pl.Int64,
                        "pick_round": pl.Int64,
                        "pick_overall_number": pl.Int64,
                        "pick_id_raw": pl.String,
                    }
                ),
            )
            .alias("pick_struct")
        )
        .unnest("pick_struct")
        .with_columns(
            # Rename pick_id_raw to pick_id for backward compatibility
            pl.col("pick_id_raw").alias("pick_id")
        )
    )

    # Clean transaction_id (Sort column)
    transactions_df = transactions_df.with_columns(
        pl.col("Sort")
        .str.replace_all(",", "")
        .str.replace_all('"', "")
        .cast(pl.Int64, strict=False)
        .alias("transaction_id")
    )

    # Handle duplicate transaction_ids
    transactions_df = transactions_df.with_columns(
        (
            pl.col("transaction_id").cast(pl.String)
            + "_"
            + pl.arange(0, pl.len()).over("transaction_id").cast(pl.String)
        ).alias("transaction_id_unique")
    )

    # Calculate FAAD award sequence (v2 architecture - immutable sequence tracking)
    # This assigns a 1-indexed chronological sequence to FAAD UFA signings per season
    # The sequence is persisted at ingestion time and never recalculated, ensuring
    # that comp pick ordering remains stable even if transaction_ids are manually corrected
    transactions_df = transactions_df.with_columns(
        pl.when(pl.col("transaction_type_refined") == "faad_ufa_signing")
        .then(
            pl.col("transaction_id")
            .rank(method="ordinal")
            .over(["season", "transaction_type_refined"])
        )
        .otherwise(pl.lit(None).cast(pl.Int64))
        .alias("faad_award_sequence")
    )

    # Select final columns
    transactions = transactions_df.select(
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
            # New pick fields for matching to dim_pick
            "pick_season",
            "pick_round",
            "pick_overall_number",
            "pick_id_raw",
            "Contract",
            "Split",
            "total",
            "years",
            "split_array",
            "RFA Matched",
            "FAAD Comp",
            "faad_award_sequence",  # v2: Immutable FAAD sequence
            "Type",
        ]
    )

    # QA tables
    unmapped_players = transactions_df.filter(
        (pl.col("asset_type") == "player") & (pl.col("player_id") == -1)
    ).select(["Player", "Position", "Time Frame", "From", "To"])

    unmapped_picks = transactions_df.filter(
        (pl.col("asset_type") == "pick") & (pl.col("pick_id").is_null())
    ).select(["Player", "Pick", "Time Frame", "From", "To"])

    # Return DataFrames (no I/O - that's handled by commissioner_writer.py)
    return {
        "transactions": transactions,
        "unmapped_players": unmapped_players,
        "unmapped_picks": unmapped_picks,
    }


# -----------------------------
# Roster table preparation (transforms parsed GM tabs to long-form)
# -----------------------------


def prepare_roster_tables(outputs: Iterable[ParsedGM]) -> dict[str, pl.DataFrame]:
    """Transform parsed GM tabs into long-form normalized tables.

    This function aggregates all parsed GM tabs and transforms them into
    the final table structures. It does NOT perform any file I/O - for writing,
    use commissioner_writer.write_all_commissioner_tables().

    Args:
        outputs: Iterable of ParsedGM objects (from parse_commissioner_dir)

    Returns:
        Dict with keys:
            - 'contracts_active': Active roster contracts (long-form)
            - 'contracts_cut': Dead cap obligations (long-form)
            - 'draft_picks': Draft pick ownership
            - 'draft_pick_conditions': Conditional picks
            - 'cap_space': Cap space by season

    Example:
        parsed_gms = parse_commissioner_dir(Path("samples/sheets"))
        tables = prepare_roster_tables(parsed_gms)
        # tables['contracts_active'] is ready for writing

    """
    # Aggregate DataFrames from all GM tabs
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
    cap_space_all = (
        pl.concat([o.cap_space for o in outputs if o.cap_space.height > 0], how="diagonal")
        if outputs
        else pl.DataFrame()
    )

    # Transform to long-form tables
    contracts_active = _to_long_roster(roster_all)
    contracts_cut = _to_long_cuts(cuts_all)
    picks_tbl, conds_tbl = _to_picks_tables(picks_all)

    return {
        "contracts_active": contracts_active,
        "contracts_cut": contracts_cut,
        "draft_picks": picks_tbl,
        "draft_pick_conditions": conds_tbl,
        "cap_space": cap_space_all,
    }


# -----------------------------
# V2: normalized long-form tables (internal helpers)
# -----------------------------


def _to_long_roster(roster_all: pl.DataFrame) -> pl.DataFrame:
    if roster_all.is_empty():
        return roster_all
    value_cols = [c for c in roster_all.columns if c.startswith("y20")]
    out = (
        roster_all.unpivot(
            index=["gm", "gm_tab", "roster_slot", "player", "total", "rfa", "fr"],
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
            rfa=pl.col("rfa").fill_null("").cast(pl.Utf8).str.strip_chars().str.to_lowercase()
            == "x",
            franchise=pl.col("fr").fill_null("").cast(pl.Utf8).str.strip_chars().str.to_lowercase()
            == "x",
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
            index=["gm", "gm_tab", "player", "position", "total"],
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


def _alias_tokens(value: str | None) -> set[str]:
    """Extract alias tokens from a name value."""
    if not value:
        return set()
    base = value.lower().strip()
    if not base:
        return set()
    tokens = {base}
    clean = base.replace(".", " ").replace("-", " ")
    tokens.update(part for part in clean.split() if part)
    return tokens


def _add_source_type_columns(picks_df: pl.DataFrame) -> pl.DataFrame:
    """Add source_type and related columns to picks DataFrame."""
    picks_df = picks_df.with_columns(
        owner_clean=pl.col("owner").fill_null("").cast(pl.Utf8).str.strip_chars(),
        owner_lower=pl.col("owner")
        .fill_null("")
        .cast(pl.Utf8)
        .str.strip_chars()
        .str.to_lowercase(),
        gm_clean=pl.col("gm").fill_null("").cast(pl.Utf8).str.strip_chars(),
    )

    picks_df = picks_df.with_columns(
        gm_lower=pl.col("gm_clean").str.to_lowercase(),
        gm_tokens=pl.col("gm_clean")
        .str.replace_all(r"[^\w\s]", " ")
        .str.to_lowercase()
        .str.split(" "),
    )

    picks_df = picks_df.with_columns(
        owner_matches=pl.col("gm_tokens").list.contains(pl.col("owner_lower"))
        | (pl.col("owner_lower") == pl.col("gm_lower"))
    )

    picks_df = picks_df.with_columns(
        source_type=pl.when(pl.col("owner_lower").str.starts_with("traded to"))
        .then(pl.lit("trade_out"))
        .when(pl.col("owner_matches"))
        .then(pl.lit("owned"))
        .otherwise(pl.lit("acquired")),
        trade_recipient=pl.when(pl.col("owner_lower").str.starts_with("traded to"))
        .then(pl.col("owner_clean").str.replace_all(r"(?i)^traded to[: ]*", "").str.strip_chars())
        .when(pl.col("owner_lower").str.starts_with("trade to"))
        .then(pl.col("owner_clean").str.replace_all(r"(?i)^trade to[: ]*", "").str.strip_chars())
        .otherwise(pl.lit(None)),
    )

    picks_df = picks_df.with_columns(
        acquired_from=pl.when(pl.col("source_type") == "acquired")
        .then(pl.col("owner_clean"))
        .otherwise(pl.lit(None)),
        original_owner=pl.when(pl.col("source_type") == "owned")
        .then(pl.col("owner_clean"))
        .when(pl.col("source_type") == "trade_out")
        .then(pl.col("gm_clean"))
        .otherwise(pl.lit(None)),
        acquisition_note=pl.when(pl.col("source_type") == "acquired")
        .then(pl.col("owner_clean"))
        .when(pl.col("source_type") == "trade_out")
        .then(pl.col("trade_recipient"))
        .otherwise(pl.lit(None)),
    )

    return picks_df


def _add_condition_flag(picks_df: pl.DataFrame) -> pl.DataFrame:
    """Add condition_flag column based on trade_conditions."""
    picks_df = picks_df.with_columns(
        condition_text=pl.col("trade_conditions").fill_null("").cast(pl.Utf8).str.strip_chars(),
    )

    condition_lower = pl.col("condition_text").str.to_lowercase()
    picks_df = picks_df.with_columns(
        condition_flag=(
            condition_lower.is_in(list(_FALSE_CONDITION_MARKERS)).not_()
            & (
                condition_lower.str.contains(r"\bif\b")
                | condition_lower.str.contains("conting")
                | condition_lower.str.contains("pending")
                | condition_lower.str.contains("conditional")
                | condition_lower.str.contains("unless")
                | condition_lower.str.contains("upon")
            )
        )
    )

    return picks_df


def _add_gm_name_columns(picks_df: pl.DataFrame) -> pl.DataFrame:
    """Add GM name normalization columns."""
    picks_df = picks_df.with_columns(
        gm_first=pl.col("gm_clean")
        .str.replace_all(r"[^\w\s]", " ")
        .str.strip_chars()
        .str.split(" ")
        .list.first()
        .str.to_lowercase(),
        gm_last=pl.col("gm_clean")
        .str.replace_all(r"[^\w\s]", " ")
        .str.strip_chars()
        .str.split(" ")
        .list.last()
        .str.to_lowercase(),
        gm_full_lower=pl.col("gm_clean").str.to_lowercase(),
        trade_recipient_lower=pl.col("trade_recipient")
        .fill_null("")
        .str.strip_chars()
        .str.to_lowercase(),
        acquisition_note_lower=pl.col("acquisition_note")
        .fill_null("")
        .str.strip_chars()
        .str.to_lowercase(),
    )

    return picks_df


def _build_acquired_lookup(
    records: list[dict],
) -> dict[tuple[int, int], list[tuple[set[str], set[str], bool]]]:
    """Build lookup dictionary for acquired picks."""
    from collections import defaultdict

    acquired_lookup: dict[tuple[int, int], list[tuple[set[str], set[str], bool]]] = defaultdict(
        list
    )
    for rec in records:
        if rec.get("source_type") != "acquired":
            continue
        year = rec["year"]
        rnd = rec["round"]
        gm_aliases = _alias_tokens(rec.get("gm_clean"))
        gm_aliases.update(_alias_tokens(rec.get("gm_first")))
        gm_aliases.update(_alias_tokens(rec.get("gm_last")))
        from_aliases = _alias_tokens(rec.get("acquisition_note_lower"))
        acquired_lookup[(year, rnd)].append(
            (gm_aliases, from_aliases, bool(rec.get("condition_flag")))
        )
    return acquired_lookup


def _update_trade_out_flags(
    records: list[dict],
    acquired_lookup: dict[tuple[int, int], list[tuple[set[str], set[str], bool]]],
) -> None:
    """Update condition flags for trade_out records based on acquired lookup."""
    for rec in records:
        if rec.get("source_type") != "trade_out" or rec.get("condition_flag"):
            continue
        year = rec["year"]
        rnd = rec["round"]
        recipient_aliases = _alias_tokens(rec.get("trade_recipient_lower"))
        gm_aliases = _alias_tokens(rec.get("gm_clean"))
        gm_aliases.update(_alias_tokens(rec.get("gm_first")))
        gm_aliases.update(_alias_tokens(rec.get("gm_last")))

        partner_pending = False
        for to_aliases, from_aliases, pending_flag in acquired_lookup.get((year, rnd), []):
            if not pending_flag:
                continue
            if recipient_aliases and not (recipient_aliases & to_aliases):
                continue
            if not gm_aliases & from_aliases:
                continue
            partner_pending = True
            break
        if partner_pending:
            rec["condition_flag"] = True


def _propagate_pending_flags(picks_df: pl.DataFrame) -> pl.DataFrame:
    """Propagate pending flags symmetrically between trade partners."""
    records = picks_df.to_dicts()
    if not records:
        return picks_df

    acquired_lookup = _build_acquired_lookup(records)
    _update_trade_out_flags(records, acquired_lookup)

    return pl.DataFrame(records)


def _to_picks_tables(picks_all: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    if picks_all.is_empty():
        return picks_all, pl.DataFrame()
    # picks_all: gm, gm_tab, owner, y2026..y2030, trade_conditions
    year_cols = [c for c in picks_all.columns if c.startswith("y20")]
    base = picks_all.select(["gm", "gm_tab", "owner", *year_cols, "trade_conditions"])
    # Unpivot to long and interpret values as rounds
    long = base.unpivot(
        index=["gm", "gm_tab", "owner", "trade_conditions"],
        on=year_cols,
        variable_name="year_str",
        value_name="round_str",
    ).with_columns(
        year=pl.col("year_str").str.replace("y", "").cast(pl.Int32),
        round=pl.col("round_str").cast(pl.Int32, strict=False),
    )
    # Keep only actual picks where round is present (1..5)
    long = long.filter(pl.col("round").is_not_null())

    picks = _add_source_type_columns(long)
    picks = _add_condition_flag(picks)
    picks = _add_gm_name_columns(picks)
    picks = _propagate_pending_flags(picks)

    picks_tbl = picks.select(
        [
            "gm",
            "gm_tab",
            "year",
            "round",
            "source_type",
            "original_owner",
            "acquired_from",
            "acquisition_note",
            "trade_recipient",
            "condition_flag",
        ]
    )

    conds = picks.filter(pl.col("condition_flag")).select(
        [
            "gm",
            "gm_tab",
            "year",
            "round",
            pl.col("condition_text").alias("condition_text"),
            "trade_recipient",
        ]
    )
    return picks_tbl, conds
