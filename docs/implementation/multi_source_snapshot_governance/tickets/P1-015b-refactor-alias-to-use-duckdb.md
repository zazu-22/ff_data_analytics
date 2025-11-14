# Ticket P1-015b: Refactor Name Alias Loading to Use DuckDB

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-015 (discovered during KTC ingestion validation)\
**Status**: COMPLETE

## Objective

Refactor ingestion scripts to load `dim_name_alias` from DuckDB table (with CSV fallback) instead of reading CSV directly, matching the pattern established for `dim_player_id_xref`.

## Context

Currently, the player ID crosswalk (`dim_player_id_xref`) uses a DuckDB-first approach with parquet fallback via `get_player_xref()` utility. However, the name alias table (`dim_name_alias`) is still loaded directly from CSV at ingestion time.

**Current State**:

- `get_player_xref()`: Reads from DuckDB → fallback to parquet → error ✅
- `_apply_name_aliases()`: Reads from CSV only ⚠️

**Inconsistency Discovered**: During P1-015 validation, we found that:

- Staging models (dbt) use `{{ ref("dim_name_alias") }}` (DuckDB table)
- Ingestion scripts use `pl.read_csv("dim_name_alias.csv")` (CSV file)
- This creates two paths to the same data

**Why This Matters**:

- Single source of truth (DuckDB after `dbt seed`)
- Architectural consistency with xref pattern
- Enables future enhancements (computed aliases, versioning, tests)
- Simpler mental model for developers

## Tasks

### Part 1: Create Utility Function

- [x] Create `src/ff_analytics_utils/name_alias.py`
- [x] Implement `get_name_alias()` function following `get_player_xref()` pattern:
  - [x] DuckDB-first approach (`main.dim_name_alias`)
  - [x] CSV fallback (`dbt/ff_data_transform/seeds/dim_name_alias.csv`)
  - [x] Auto/duckdb/csv source parameter
  - [x] Optional column selection
  - [x] Proper error handling and messages
- [x] Add docstring with usage examples
- [defer] Add unit tests (optional but recommended - not required for completion)

### Part 2: Refactor Ingestion Scripts

- [x] Update `src/ingest/sheets/commissioner_parser.py`:
  - [x] Import `get_name_alias` from new utility
  - [x] Replace `pl.read_csv(alias_path)` with `get_name_alias()`
  - [x] Remove hardcoded CSV path reference
  - [x] Update error messages if any
- [x] Check for other scripts using alias CSV:
  - [x] Search codebase: `grep -r "dim_name_alias.csv" src/ scripts/`
  - [x] Refactor any other occurrences found (none found)

### Part 3: Testing & Validation

- [x] Test DuckDB path: Run after `make dbt-seed`
- [x] Test CSV fallback: Run without seeded table
- [x] Verify ingestion still works: `make ingest-sheets`
- [x] Verify unmapped players file reflects alias usage
- [x] Run staging models: `make dbt-run --select stg_sheets__contracts_active`
- [x] Verify no regressions in player mapping

## Acceptance Criteria

- [x] New utility `get_name_alias()` exists in `src/ff_analytics_utils/name_alias.py`
- [x] Function matches `get_player_xref()` pattern (DuckDB-first, fallback)
- [x] All ingestion scripts use `get_name_alias()` instead of direct CSV reads
- [x] No hardcoded CSV paths remain in ingestion code
- [x] Both DuckDB and CSV fallback paths tested and working
- [x] No regressions in player name mapping behavior
- [x] Documentation updated (docstrings, comments)

## Implementation Notes

### Reference Implementation

Follow the pattern from `src/ff_analytics_utils/player_xref.py`:

```python
# src/ff_analytics_utils/name_alias.py
from pathlib import Path
import polars as pl
from ff_analytics_utils.duckdb_helper import fetch_table_as_polars

DEFAULT_DUCKDB_TABLE = "main.dim_name_alias"
DEFAULT_CSV_PATH = "dbt/ff_data_transform/seeds/dim_name_alias.csv"

def get_name_alias(
    *,
    source: str = "auto",
    duckdb_table: str = DEFAULT_DUCKDB_TABLE,
    db_path: str | Path | None = None,
    csv_path: str | Path | None = None,
    columns: Sequence[str] | None = None,
) -> pl.DataFrame:
    """Return the name alias table as a Polars DataFrame.

    Args:
        source: 'duckdb', 'csv', or 'auto' to try DuckDB then CSV fallback.
        duckdb_table: Fully qualified DuckDB table name to query.
        db_path: Override path to DuckDB database (defaults to DBT_DUCKDB_PATH/env).
        csv_path: Path to CSV seed file (defaults to dim_name_alias.csv).
        columns: Optional subset of columns to select.

    Returns:
        DataFrame with columns: alias_name, canonical_name, alias_type, notes, position, treat_as_position

    Raises:
        RuntimeError: If unable to load from any source

    Example:
        # DuckDB-first (requires dbt seed)
        alias_df = get_name_alias()

        # Force CSV (for testing)
        alias_df = get_name_alias(source="csv")
    """
    errors: list[str] = []
    csv_path = csv_path or DEFAULT_CSV_PATH

    if source in {"auto", "duckdb"}:
        try:
            return fetch_table_as_polars(duckdb_table, columns=columns, db_path=db_path)
        except Exception as exc:
            errors.append(f"DuckDB: {exc}")
            if source == "duckdb":
                raise RuntimeError(
                    f"Failed to load name alias from DuckDB table '{duckdb_table}'"
                ) from exc

    if source in {"auto", "csv"}:
        try:
            df = pl.read_csv(csv_path)
            if columns:
                df = df.select(columns)
            return df
        except Exception as exc:
            errors.append(f"CSV: {exc}")
            if source == "csv":
                raise RuntimeError(
                    f"Failed to load name alias from CSV '{csv_path}'"
                ) from exc

    error_detail = "; ".join(errors) if errors else "unknown error"
    raise RuntimeError(
        "Unable to load name alias from DuckDB or CSV. "
        "Ensure `dbt seed --select dim_name_alias` has completed or provide "
        f"a valid CSV path.\nDetails: {error_detail}"
    )
```

### Usage in commissioner_parser.py

**Before**:

```python
def _apply_name_aliases(player_df: pl.DataFrame, has_position: bool) -> pl.DataFrame:
    """Apply name alias corrections from seed file."""
    alias_path = Path("dbt/ff_data_transform/seeds/dim_name_alias.csv")
    if not alias_path.exists():
        return player_df

    alias_seed = pl.read_csv(alias_path)
    # ... rest of logic
```

**After**:

```python
from ff_analytics_utils.name_alias import get_name_alias

def _apply_name_aliases(player_df: pl.DataFrame, has_position: bool) -> pl.DataFrame:
    """Apply name alias corrections from DuckDB table (with CSV fallback)."""
    try:
        alias_seed = get_name_alias()
    except RuntimeError:
        # No aliases available - return unchanged
        return player_df

    # ... rest of logic (unchanged)
```

### Files to Update

1. **Create**: `src/ff_analytics_utils/name_alias.py`
2. **Update**: `src/ingest/sheets/commissioner_parser.py` (lines 747-750)
3. **Search**: Any other scripts using `dim_name_alias.csv` directly

### Testing Strategy

**Test 1: DuckDB Path (Normal Operation)**

```bash
# Ensure seed is loaded
make dbt-seed --select dim_name_alias

# Run ingestion
make ingest-sheets

# Should use DuckDB table
```

**Test 2: CSV Fallback**

```bash
# Clear DuckDB table (simulate missing seed)
EXTERNAL_ROOT="$(pwd)/data/raw" duckdb "$(pwd)/dbt/ff_data_transform/target/dev.duckdb" -c "DROP TABLE IF EXISTS main.dim_name_alias;"

# Run ingestion
make ingest-sheets

# Should fall back to CSV
```

**Test 3: Alias Functionality**

```bash
# Verify Zonovan Knight mapping works
# Should map to player_id 8284 (Bam Knight)
make ingest-sheets
uv run python -c "import polars as pl; df = pl.read_parquet('data/raw/commissioner/transactions_qa/dt=*/unmapped_players.parquet'); print(df.filter(pl.col('Player').str.contains('(?i)knight')))"
```

## Benefits

1. **Architectural Consistency**: Matches xref pattern established during prerequisite work
2. **Single Source of Truth**: DuckDB table is authoritative after `dbt seed`
3. **Resilience**: CSV fallback ensures ingestion works even without dbt
4. **Future-Ready**: Enables computed aliases, versioning, effective dates
5. **Developer Experience**: One pattern for all seed-based lookups

## References

- **Pattern Source**: `src/ff_analytics_utils/player_xref.py` (lines 21-80)
- **Usage Example**: `src/ingest/sheets/commissioner_parser.py` (line 1073)
- **Related Work**: Prerequisite project to remove xref CSV dependency
- **Discovery**: P1-015 validation (2025-11-10)

## Related Tickets

- **P1-015**: Update stg_ktc_assets Model (parent ticket)
- **Prerequisite Work**: Conversion of xref from CSV to DuckDB model

## Notes

This is a code quality improvement with no functional changes. The behavior should be identical - aliases work the same way, just loaded from a more consistent source.

If additional scripts are found that use the alias CSV, consider whether they should also be refactored as part of this ticket or tracked separately.

## Completion Notes

**Implemented**: 2025-11-10

**Files Changed**:

- Created: `src/ff_analytics_utils/name_alias.py` (new utility module)
- Updated: `src/ingest/sheets/commissioner_parser.py:32` (added import)
- Updated: `src/ingest/sheets/commissioner_parser.py:748-754` (refactored \_apply_name_aliases function)

**Tests**: All passing

- DuckDB path: ✅ Loaded 92 alias rows from seeded table
- CSV fallback: ✅ Loaded from CSV when DuckDB table absent
- Ingestion: ✅ `make ingest-sheets` completed in 31.1s
- Staging model: ✅ `stg_sheets__contracts_active` ran successfully
- Player mapping: ✅ No regressions, alias functionality preserved (e.g., Zonovan Knight → Bam Knight → player_id 8284)

**Impact**:

- Achieved architectural consistency with `get_player_xref()` pattern
- Single source of truth: DuckDB table is now authoritative after `dbt seed`
- Resilient: CSV fallback ensures ingestion works in all scenarios
- No other scripts using dim_name_alias.csv found in codebase

**Next Steps**: Consider adding unit tests for `get_name_alias()` function (marked as optional in ticket)
