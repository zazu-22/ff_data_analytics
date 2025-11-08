# Ticket P2-004: Extend analyze_snapshot_coverage - Gap Detection

**Phase**: 2 - Governance\
**Estimated Effort**: Medium (2-3 hours)\
**Dependencies**: P2-003 (builds on delta reporting functionality)

## Objective

Add season/week coverage gap detection to `tools/analyze_snapshot_coverage.py` to identify missing weeks within expected season ranges and missing player mappings.

## Context

Beyond row count deltas, we need to detect structural coverage gaps:

- Missing weeks within a season (e.g., Week 5-7 present but Week 6 missing)
- Incomplete seasons (expected weeks not yet loaded)
- Player mapping gaps (players in snapshot not in `dim_player_id_xref`)

These gaps indicate data quality issues or incomplete loads that should be resolved before downstream consumption.

## Tasks

### Add Season/Week Gap Detection

- [ ] Parse season and week from snapshot data (nflverse weekly)
- [ ] Identify expected week range for each season
- [ ] Detect missing weeks within range
- [ ] Cross-reference with registry coverage expectations

### Add Player Mapping Rate Checks

- [ ] Sample-join snapshot data to `dim_player_id_xref`
- [ ] Calculate mapping coverage by dataset/week
- [ ] Flag datasets with \<90% mapping rate
- [ ] Report top unmapped players for investigation

### Update Output Format

- [ ] Add "Coverage Gaps" section to output
- [ ] List missing weeks with expected dates
- [ ] Report mapping rates by dataset
- [ ] Include gap information in JSON output

### Test with Real Data

- [ ] Run against complete seasons (should show no gaps)
- [ ] Run against in-progress season (may show future weeks as expected gaps)
- [ ] Verify mapping rate calculation accurate

## Acceptance Criteria

- [ ] Tool detects missing weeks within season ranges
- [ ] Player mapping rates calculated and reported
- [ ] Gaps clearly identified in output (both formats)
- [ ] Tool distinguishes between actual gaps and expected future weeks
- [ ] Documentation updated with gap detection features

## Implementation Notes

**File**: `tools/analyze_snapshot_coverage.py`

**Gap Detection Function**:

```python
def detect_coverage_gaps(
    source: str,
    dataset: str,
    snapshot_path: Path,
    registry_df: DataFrame
) -> dict:
    """Detect season/week coverage gaps in snapshot data.

    Args:
        source: Data source (e.g., 'nflverse')
        dataset: Dataset within source (e.g., 'weekly')
        snapshot_path: Path to snapshot Parquet files
        registry_df: Snapshot registry for expected coverage

    Returns:
        Dictionary with gap analysis
    """
    # Read snapshot data
    df = pl.read_parquet(snapshot_path)

    # Get expected coverage from registry
    registry_entry = (
        registry_df
        .filter(
            (pl.col('source') == source) &
            (pl.col('dataset') == dataset) &
            (pl.col('status') == 'current')
        )
        .select(['coverage_start_season', 'coverage_end_season'])
        .first()
    )

    if not registry_entry:
        return {'error': 'No current snapshot in registry'}

    start_season = registry_entry['coverage_start_season']
    end_season = registry_entry['coverage_end_season']

    # Detect missing weeks
    gaps = []
    for season in range(start_season, end_season + 1):
        season_data = df.filter(pl.col('season') == season)
        weeks_present = set(season_data['week'].unique())

        # Expected weeks (1-18 for NFL regular season + playoffs)
        expected_weeks = set(range(1, 19))
        missing_weeks = expected_weeks - weeks_present

        if missing_weeks and season < end_season:  # Don't flag in-progress season
            for week in sorted(missing_weeks):
                gaps.append({
                    'season': season,
                    'week': week,
                    'expected_by': estimate_availability_date(season, week)
                })

    return {
        'source': source,
        'dataset': dataset,
        'gaps': gaps,
        'gap_count': len(gaps)
    }
```

**Player Mapping Rate Function**:

```python
def calculate_mapping_rate(
    snapshot_path: Path,
    xref_path: str = 'dbt/ff_data_transform/target/dev.duckdb'
) -> dict:
    """Calculate player mapping rate to dim_player_id_xref.

    Args:
        snapshot_path: Path to snapshot Parquet files
        xref_path: Path to DuckDB database with dim_player_id_xref

    Returns:
        Dictionary with mapping statistics
    """
    import duckdb

    # Read snapshot
    snapshot_df = pl.read_parquet(snapshot_path)

    # Sample players (take distinct player IDs)
    sample_players = snapshot_df.select(['player_id', 'player_name']).unique()

    # Connect to DuckDB and join to xref
    conn = duckdb.connect(xref_path, read_only=True)

    mapped_count = conn.execute(f"""
        SELECT COUNT(DISTINCT s.player_id)
        FROM sample_players s
        JOIN dim_player_id_xref x ON s.player_id = x.gsis_id
    """).fetchone()[0]

    total_count = len(sample_players)
    mapping_rate = (mapped_count / total_count * 100) if total_count > 0 else 0

    # Get top unmapped players
    unmapped_players = conn.execute(f"""
        SELECT s.player_id, s.player_name
        FROM sample_players s
        LEFT JOIN dim_player_id_xref x ON s.player_id = x.gsis_id
        WHERE x.mfl_id IS NULL
        ORDER BY s.player_name
        LIMIT 10
    """).fetchall()

    conn.close()

    return {
        'total_players': total_count,
        'mapped_players': mapped_count,
        'mapping_rate': mapping_rate,
        'unmapped_sample': [
            {'player_id': p[0], 'player_name': p[1]}
            for p in unmapped_players
        ]
    }
```

**Expected Output Format** (from plan line 160):

```
Coverage Gaps:
- Week 10 missing for 2025 season (expected by 2025-11-12)

Player Mapping Rates:
- nflverse.weekly: 98.7% mapped (15 unmapped players)
  Top unmapped: John Doe (12345), Jane Smith (67890)
```

## Testing

1. **Run gap detection**:

   ```bash
   uv run python tools/analyze_snapshot_coverage.py \
       --sources nflverse \
       --detect-gaps \
       --check-mappings
   ```

2. **Test with complete season**:

   ```python
   # Should show no gaps for 2024 season (complete)
   gaps = detect_coverage_gaps('nflverse', 'weekly', 'data/raw/nflverse/weekly/dt=2025-10-27/*.parquet', registry)
   assert gaps['gap_count'] == 0
   ```

3. **Test with in-progress season**:

   ```python
   # May show future weeks as expected gaps for 2025 season
   # Tool should distinguish these from actual gaps
   ```

4. **Test mapping rate**:

   ```bash
   uv run python tools/analyze_snapshot_coverage.py \
       --sources nflverse \
       --check-mappings \
       --output-format json \
       > mapping_rates.json

   cat mapping_rates.json | jq '.mapping_rates'
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Design Decision #4 (lines 148-162)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 2 Validation (lines 117-123)
- Crosswalk table: `dbt/ff_data_transform/seeds/dim_player_id_xref.csv`
- Risk: Mapping gaps for offensive linemen (plan line 688)
