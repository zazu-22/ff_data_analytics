# R Scripts Context

**Location**: `scripts/R/`
**Purpose**: R-based data loaders (used when Python alternatives unavailable)

## Scripts Overview

### ffanalytics_run.R

**Purpose**: Scrape weekly fantasy projections from multiple sources with weighted consensus aggregation

**Status**: ✅ Production-ready

**Features**:

- Weighted consensus from 9+ sources (CBS, ESPN, FantasyPros, FantasySharks, etc.)
- Site weights from `config/projections/ffanalytics_projection_weights_mapped.csv`
- Player name → ID mapping via `dim_player_id_xref` seed
- **DST (Team Defense) mapping** via `seed_team_defense_xref` seed (added 2025-11-13)
- Both raw projections and consensus output

**Invoked by**: Python via `subprocess` from `src/ingest/ffanalytics/loader.py`

#### CLI Parameters

| Parameter         | Type   | Default                                                      | Description                               |
| ----------------- | ------ | ------------------------------------------------------------ | ----------------------------------------- |
| `--sources`       | string | All 9 sources                                                | Comma-separated source list or "all"      |
| `--positions`     | string | QB,RB,WR,TE,K,DST,DL,LB,DB                                   | Comma-separated position list             |
| `--season`        | int    | 2024                                                         | Season year                               |
| `--week`          | int    | 0                                                            | Week number (0 for season-long)           |
| `--out_dir`       | string | data/raw/ffanalytics                                         | Output directory                          |
| `--weights_csv`   | string | config/projections/ffanalytics_projection_weights_mapped.csv | Site weights CSV path                     |
| `--player_xref`   | string | dbt/ff_data_transform/seeds/dim_player_id_xref.csv           | Player ID crosswalk seed path             |
| `--position_xref` | string | dbt/ff_data_transform/seeds/dim_position_translation.csv     | Position translation seed path            |
| `--name_alias`    | string | dbt/ff_data_transform/seeds/dim_name_alias.csv               | Player name alias seed path               |
| `--defense_xref`  | string | dbt/ff_data_transform/seeds/seed_team_defense_xref.csv       | Team defense crosswalk seed path (P1-028) |

#### Player Mapping Logic

**Individual Players** (lines 592-714):

1. Load `player_xref` (player ID crosswalk from NFLverse)
2. Load `position_xref` (fantasy position → NFL position translation)
3. Load `name_alias` (nickname/typo → canonical name mapping)
4. Apply name normalization:
   - Lowercase and trim whitespace
   - Reverse "Last, First" to "First Last" format
   - Strip periods (A.J. Brown → aj brown)
   - Strip suffixes (Jr, Sr, II, III, IV, V)
5. Match players on:
   - **Exact match**: normalized name + position + team
   - **Fallback**: merge_name + position + team
6. Assign `player_id` from crosswalk (or -1 if unmapped)

**Team Defenses (DST)** (lines 729-832, added P1-028):

1. Load `defense_xref` (team defense crosswalk seed)
2. Identify unmapped DST projections (positions: D, DST, D/ST, DEF)
3. Prepare defense xref for matching:
   - Normalize all team name alias columns
   - Pivot to long format (one row per team name variant)
4. Match unmapped DST projections to defense xref:
   - **Primary strategy**: Match by team abbreviation (most reliable)
   - **Fallback strategy**: Match by team name variants
5. Assign `defense_id` (90001-90036) for matched DST
6. Retain `player_id = -1` for unmatched DST (log as warning)
7. Report mapping statistics separately from individual players

**Defense ID Range**: 90001-90036

- Current teams: 90001-90028 (32 teams)
- Historical teams: 90029-90032 (LA, OAK, SD, STL)
- Rationale: Clear separation from player IDs (~9,757 current, ~28K max expected)

**Team Name Matching Strategy**:

The DST mapping handles multiple team name formats from different FFAnalytics providers:

- **Primary match**: Team abbreviation (normalized via `normalize_team_abbrev()`)
- **Name variants**: 5 aliases per team in seed:
  - Full name: "Arizona Cardinals"
  - Reversed: "Cardinals, Arizona"
  - Nickname: "Cardinals"
  - City: "Arizona"
  - With suffix: "Cardinals D/ST"

**Position Normalization**:

All DST position variations map to canonical defense_id:

- `D` → defense_id
- `DST` → defense_id
- `D/ST` → defense_id
- `DEF` → defense_id

#### Outputs

**Parquet files** (in `data/raw/ffanalytics/projections/dt=YYYY-MM-DD/`):

1. `projections_raw_*.parquet` - Individual source projections (pre-consensus)
2. `projections_consensus_*.parquet` - Weighted consensus aggregation

**Metadata** (`_meta.json`):

```json
{
  "dataset": "ffanalytics_projections",
  "player_mapping": {
    "total_players": 1234,
    "mapped_players": 1100,
    "unmapped_players": 134,
    "mapping_coverage": 0.8913
  },
  "dst_mapping": {
    "mapped_defenses": 612,
    "unmapped_defenses": 0,
    "mapping_coverage": 1.0
  }
}
```

#### Mapping Coverage

**Before P1-028** (DST support):

- Total: ~89% mapped
- Unmapped: ~138 projections (including ~90 DST)

**After P1-028** (DST support):

- Total: ~93% mapped
- Unmapped: ~657 projections (0 DST, primarily IDP deep roster)
- DST coverage: 100% (612/612 projections)

#### Integration

**Python → R subprocess workflow**:

1. Python loader (`src/ingest/ffanalytics/loader.py`) creates temp CSVs:
   - Player xref temp file via `_player_xref_csv()` context manager
   - Defense xref temp file via `_defense_xref_csv()` context manager
2. Python invokes R script with temp CSV paths:
   ```bash
   Rscript scripts/R/ffanalytics_run.R \
     --player_xref /tmp/player_xref_abc123.csv \
     --defense_xref /tmp/defense_xref_def456.csv \
     --week 11 --season 2025
   ```
3. R script loads both crosswalks and performs mapping
4. Parquet output → dbt staging model (`stg_ffanalytics__projections`) → marts

**Why temp CSV files?**

- R script is self-contained (doesn't require DuckDB access)
- Python utility functions (`get_player_xref()`, `get_defense_xref()`) query DuckDB for performance
- Temp CSV bridges the gap: DuckDB → Python → temp CSV → R → Parquet

### nflverse_load.R

**Purpose**: Fallback loader when `nflreadpy` unavailable

**Called by**: `src/ingest/nflverse/shim.py`

**Usage**: Automatic fallback, not invoked directly

**Outputs**: Parquet + `_meta.json` (same format as Python loader)

## Development Notes

**Testing R script changes**:

```bash
# Test player mapping logic
Rscript scripts/R/ffanalytics_run.R \
  --week 1 --season 2024 \
  --player_xref dbt/ff_data_transform/seeds/dim_player_id_xref.csv \
  --defense_xref dbt/ff_data_transform/seeds/seed_team_defense_xref.csv

# Check mapping coverage in output
cat data/raw/ffanalytics/projections/dt=*/projections_consensus_*.parquet | \
  duckdb -c "SELECT COUNT(*) FILTER (player_id > 0) AS mapped, \
              COUNT(*) FILTER (player_id = -1) AS unmapped \
              FROM read_parquet('/dev/stdin')"
```

**Common issues**:

1. **DST not mapping**: Check team abbreviation normalization in `normalize_team_abbrev()` function
2. **Position mismatch**: Verify position aliases in `seed_team_defense_xref.csv`
3. **Team name variations**: Add new aliases to seed CSV and reload

**Adding new team (relocation/expansion)**:

1. Add team to `seed_team_defense_xref.csv` with next defense_id (90033+)
2. Include 5 name aliases and 4 position aliases
3. Run `just dbt-seed --select seed_team_defense_xref`
4. Re-run FFAnalytics ingestion: `just ingest-ffanalytics`
5. Verify DST mapping coverage maintained at 100%

## References

- **Python loader**: `src/ingest/ffanalytics/loader.py`
- **Defense xref seed**: `dbt/ff_data_transform/seeds/seed_team_defense_xref.csv`
- **Python utility**: `src/ff_analytics_utils/defense_xref.py`
- **Staging model**: `dbt/ff_data_transform/models/staging/stg_ffanalytics__projections.sql`
- **Implementation ticket**: `docs/implementation/multi_source_snapshot_governance/tickets/P1-028-add-dst-team-defense-seed.md`
