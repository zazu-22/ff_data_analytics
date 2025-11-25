# CRITICAL-001: Duplicate Player IDs in dim_player_id_xref

**Status**: 🔴 **CRITICAL - BLOCKING ALL PLAYER-BASED ANALYTICS**
**Priority**: P0 - Must Fix Immediately
**Discovered**: 2025-11-25
**Impact**: All player identity resolution is broken

## Executive Summary

The `dim_player_id_xref` crosswalk contains **duplicate entries for every player** with different canonical `player_id` values. This breaks all downstream models that rely on player identity matching, including:

- Roster parity checks (321 spurious failures)
- Contract history tracking
- Fantasy projections
- Player valuations

**Root Cause**: The nflverse `ff_playerids` raw data partition `dt=2025-11-16` contains TWO parquet files with identical data, causing the staging model to produce duplicate rows.

## Evidence

### Duplicate Parquet Files

```
data/raw/nflverse/ff_playerids/dt=2025-11-16/
├── ff_playerids_86c3d6f9.parquet  (1,545,939 bytes)
└── ff_playerids_f1ce6766.parquet  (1,545,939 bytes)  ← DUPLICATE
```

### Row Counts by Partition

| Partition         | Rows       | Expected  |
| ----------------- | ---------- | --------- |
| dt=2025-10-01     | 12,133     | ✅        |
| dt=2025-11-09     | 12,155     | ✅        |
| dt=2025-11-10     | 12,155     | ✅        |
| **dt=2025-11-16** | **24,316** | ❌ DOUBLE |

### Impact on Crosswalk

Every player has two `player_id` values:

```sql
SELECT name, position, team, COUNT(DISTINCT player_id) as ids
FROM dim_player_id_xref
WHERE position IN ('QB', 'RB', 'WR', 'TE')
GROUP BY name, position, team
HAVING COUNT(DISTINCT player_id) > 1;
-- Returns 9,700+ rows (EVERY fantasy-relevant player)
```

Example - Patrick Mahomes:

| player_id | sleeper_id | mfl_id | Source              |
| --------- | ---------- | ------ | ------------------- |
| 6291      | 4046       | -1     | First parquet file  |
| 15977     | -1         | 13116  | Second parquet file |

### Downstream Impact

- **Sleeper rosters** join on `sleeper_id` → get player_id 6291
- **Commissioner sheets** use name matching → get player_id 15977
- **Roster parity test**: 321 failures (165 commissioner_only + 156 sleeper_only)
- **All player-based joins are incorrect**

## Root Cause Analysis

1. **Ingestion script ran twice** on 2025-11-16, writing two parquet files instead of one
2. **No deduplication at file level** - `read_parquet(dt=*/ff_playerids_*.parquet)` reads ALL files in the partition
3. **`snapshot_selection_strategy`** filters by partition date, not by file - so both files from latest partition are included
4. **Sequential player_id assignment** (line 711) assigns different IDs to the duplicate rows:
   ```sql
   row_number() over (order by mfl_id, gsis_id, name) as player_id
   ```

## Fix Strategy

### Immediate Fix (Manual)

Delete the duplicate parquet file:

```bash
rm data/raw/nflverse/ff_playerids/dt=2025-11-16/ff_playerids_f1ce6766.parquet
just dbt-run --select stg_nflverse__ff_playerids dim_player_id_xref
```

### Systemic Fixes Required

#### 1. Ingestion Layer - Prevent Duplicate Files

**File**: `src/ingest/nflverse/shim.py` (line 63)

**Current Problem**:

```python
file_name = f"{dataset}_{uuid.uuid4().hex[:8]}.parquet"  # Creates new file every run
```

Options:

- **A) Atomic write with overwrite**: Write to temp file, then `mv` to final location (overwrites existing)
- **B) Clear partition before write**: Delete existing files in partition before writing new data
- **C) Include unique run ID**: Use `{dataset}_{run_id}.parquet` naming but clean up old files

**Recommendation**: Option B - clear partition before write. This matches the "immutable snapshot" pattern where each partition should contain exactly one canonical version of the data.

**Implementation** (in `_write_parquet` function):

```python
import glob
import os

def _write_parquet(...):
    ...
    partition_uri = f"{base}/{dataset}/dt={dt}"

    # Clear existing files in partition before writing
    if not partition_uri.startswith("gs://"):  # Local filesystem
        existing_files = glob.glob(f"{partition_uri}/{dataset}_*.parquet")
        for f in existing_files:
            os.remove(f)
            logger.info(f"Removed existing file: {f}")

    file_name = f"{dataset}_{uuid.uuid4().hex[:8]}.parquet"
    ...
```

#### 2. Staging Model - Add Deduplication

**File**: `dbt/ff_data_transform/models/staging/stg_nflverse__ff_playerids.sql`

Add row-level deduplication in case duplicate files slip through:

```sql
raw_players as (
    select *, row_number() over (
        partition by mfl_id, gsis_id, name, birthdate
        order by dt desc  -- Keep latest if duplicates exist
    ) as _dedup_rank
    from read_parquet(...)
),
filtered as (
    select * exclude (_dedup_rank)
    from raw_players
    where _dedup_rank = 1  -- Deduplicate at source
    ...
)
```

#### 3. Add Data Quality Gate

**File**: `dbt/ff_data_transform/models/staging/_stg_nflverse__ff_playerids.yml`

Add test to catch duplicate player entries early:

```yaml
data_tests:
  - dbt_utils.unique_combination_of_columns:
      arguments:
        combination_of_columns:
          - name
          - position
          - team
          - birthdate
      config:
        severity: error
        error_if: ">0"
```

#### 4. Fix Prefect Flow Data Quality Gates

**File**: `src/flows/utils/validation.py`

**Current Problem**: `detect_row_count_anomaly` compares new ingestion count vs registry count, but registry stores count at WRITE time, not what's ACTUALLY in the partition.

**Missing Checks**:

1. No validation that partition contains single file
2. No validation of actual row count in partition after build
3. No crosswalk uniqueness validation

**Add New Validation Task**:

```python
@task(name="validate_partition_integrity")
def validate_partition_integrity(partition_path: str, expected_file_count: int = 1) -> dict:
    """Validate partition contains expected number of files.

    Args:
        partition_path: Path to partition directory
        expected_file_count: Expected number of parquet files (default 1)

    Returns:
        Validation result with file count and paths

    Raises:
        RuntimeError: If file count doesn't match expected
    """
    import glob
    files = glob.glob(f"{partition_path}/*.parquet")

    if len(files) != expected_file_count:
        raise RuntimeError(
            f"Partition integrity check failed: expected {expected_file_count} files, "
            f"found {len(files)}: {files}"
        )

    return {"valid": True, "file_count": len(files), "files": files}
```

**Add to Flow** (`nfl_data_pipeline.py`):

```python
# After writing, validate partition integrity
validate_partition_integrity(
    partition_path=manifest["partition_dir"],
    expected_file_count=1
)
```

#### 5. Add Crosswalk Uniqueness Test

**File**: `dbt/ff_data_transform/models/staging/_stg_nflverse__ff_playerids.yml`

Add dbt test to catch duplicate canonical IDs:

```yaml
data_tests:
  - dbt_utils.unique_combination_of_columns:
      arguments:
        combination_of_columns:
          - name
          - position
          - team
          - birthdate
      config:
        severity: error
        error_if: ">100"  # Allow some legitimate same-name players, but catch mass duplication
```

#### 6. Audit All Ingestion Scripts

Review ALL ingestion scripts for similar patterns:

- `src/ingest/nflverse/shim.py` ← **Source of this bug**
- `src/ingest/sleeper/loader.py`
- `src/ingest/ktc/loader.py`
- `src/ingest/ffanalytics/loader.py`
- `scripts/ingest/load_sleeper.py`

Ensure each follows atomic write pattern and cleans up previous files in partition.

#### 7. Add CI Pipeline Check

Consider adding to GitHub Actions:

```yaml
- name: Validate partition integrity
  run: |
    # Check no partition has multiple parquet files
    for dir in data/raw/*/*/dt=*; do
      count=$(ls -1 "$dir"/*.parquet 2>/dev/null | wc -l)
      if [ "$count" -gt 1 ]; then
        echo "ERROR: Multiple parquet files in $dir"
        exit 1
      fi
    done
```

## Acceptance Criteria

### Immediate (P0)

- [ ] Duplicate parquet file removed from `dt=2025-11-16`
- [ ] `dim_player_id_xref` has ~9,700 unique players (not ~19,500)
- [ ] Each player has exactly ONE canonical `player_id`
- [ ] Patrick Mahomes has ONE entry with BOTH `sleeper_id` AND `mfl_id` populated
- [ ] Roster parity test failures reduced from 321 to expected ~30 (streaming players)

### Systemic (P1)

- [ ] `src/ingest/nflverse/shim.py` updated to clear partition before write
- [ ] `stg_nflverse__ff_playerids.sql` has defensive row-level deduplication
- [ ] `_stg_nflverse__ff_playerids.yml` has uniqueness test (name+position+team+birthdate)
- [ ] `src/flows/utils/validation.py` has `validate_partition_integrity` task
- [ ] `nfl_data_pipeline.py` calls partition integrity check after write
- [ ] All other ingestion scripts audited and fixed if needed

## Verification Query

After fix, this should return 0 rows:

```sql
SELECT name, position, team, COUNT(DISTINCT player_id) as id_count
FROM main.dim_player_id_xref
WHERE position IN ('QB', 'RB', 'WR', 'TE')
  AND draft_year >= 2015
GROUP BY name, position, team
HAVING COUNT(DISTINCT player_id) > 1;
```

## Timeline

| Phase              | Action                                           | Owner | ETA       |
| ------------------ | ------------------------------------------------ | ----- | --------- |
| **P0 - Immediate** |                                                  |       |           |
| 1                  | Delete duplicate parquet file                    | -     | Immediate |
| 2                  | Rebuild crosswalk                                | -     | 5 min     |
| 3                  | Verify roster parity                             | -     | 5 min     |
| **P1 - Systemic**  |                                                  |       |           |
| 4                  | Update `shim.py` to clear partition before write | -     | 30 min    |
| 5                  | Add defensive deduplication to staging model     | -     | 30 min    |
| 6                  | Add `validate_partition_integrity` task          | -     | 30 min    |
| 7                  | Wire partition check into `nfl_data_pipeline.py` | -     | 15 min    |
| 8                  | Add crosswalk uniqueness dbt test                | -     | 15 min    |
| 9                  | Audit all other ingestion scripts                | -     | 2 hours   |
| 10                 | Add CI pipeline check (optional)                 | -     | 30 min    |

## Related Issues

- This may explain other data quality issues discovered in recent weeks
- Review all downstream models after fix for any cascading issues
- Consider adding crosswalk integrity check to CI pipeline

______________________________________________________________________

**This is a data corruption issue that breaks the foundational identity resolution layer. All player-based analytics are unreliable until fixed.**
