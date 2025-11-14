# Seeds

Dictionaries, scoring rules, id crosswalks.

**Note**: `dim_player_id_xref` has been migrated to a staging model (`stg_nflverse__ff_playerids`)
as of 2025-11-06. See `dbt/ff_data_transform/models/core/dim_player_id_xref.sql` for the backward
compatibility model.

Example seed names: `dim_scoring_rule.csv`, `dim_franchise.csv`, `dim_timeframe.csv`.

## Team Defense Crosswalk

**File**: `seed_team_defense_xref.csv`
**Purpose**: Map team defenses (DST) to canonical defense_id for FFAnalytics projection mapping
**Model**: `core/dim_team_defense_xref.sql` (references this seed)

### Overview

This seed provides a crosswalk between NFL team defenses and canonical defense_ids, enabling FFAnalytics projection mapping for DST positions. The seed includes multiple name and position aliases to handle variations across different fantasy projection sources.

### Structure

| Column              | Type    | Description                                         |
| ------------------- | ------- | --------------------------------------------------- |
| `defense_id`        | INTEGER | Sequential ID (90001-90036) for team defenses       |
| `team_abbrev`       | VARCHAR | Canonical 3-letter team abbreviation (ARI, ATL,...) |
| `team_name_primary` | VARCHAR | Full team name (e.g., "Arizona Cardinals")          |
| `team_name_alias_1` | VARCHAR | Reversed format (e.g., "Cardinals, Arizona")        |
| `team_name_alias_2` | VARCHAR | Short nickname (e.g., "Cardinals")                  |
| `team_name_alias_3` | VARCHAR | City only (e.g., "Arizona")                         |
| `team_name_alias_4` | VARCHAR | With D/ST suffix (e.g., "Cardinals D/ST")           |
| `position_primary`  | VARCHAR | Always "DST"                                        |
| `position_alias_1`  | VARCHAR | Position variation "D"                              |
| `position_alias_2`  | VARCHAR | Position variation "D/ST"                           |
| `position_alias_3`  | VARCHAR | Position variation "DEF"                            |

### Defense ID Range: 90001-90036

**Rationale**:

- Current player IDs: ~9,757 (max expected ~28,000 across NFL history)
- Buffer: ~80,000 IDs between max expected players and min defense IDs
- Benefits: Clear separation in sort order, no collision risk, future extensibility
- Range supports: 32 current teams + 4 historical teams (LA, OAK, SD, STL)

### Team Coverage

**Current Teams (32)**:

- All active NFL franchises as of 2025 season
- Abbreviations match `dim_team_conference_division` seed

**Historical Teams (4)**:

- LA (90029) - Pre-STL Rams (1946-1994)
- OAK (90030) - Pre-LV Raiders (1960-2019)
- SD (90031) - Pre-LAC Chargers (1960-2016)
- STL (90032) - Pre-LA Rams (1995-2015)

### Maintenance

**When to update**:

1. **Team relocations**: Add new team entry, mark old team as historical
2. **Team rebranding**: Update name aliases to include both old and new names
3. **Expansion teams**: Add new team with next available defense_id (90033+)

**Update process**:

1. Edit `seed_team_defense_xref.csv` with new team data
2. Run `just dbt-seed --select seed_team_defense_xref` to reload seed
3. Re-run FFAnalytics ingestion to remap projections: `just ingest-ffanalytics`
4. Verify mapping coverage improved

**Coordination**:

- Keep team abbreviations synchronized with `dim_team_conference_division` seed
- Update R script team alias map (`scripts/R/ffanalytics_run.R`) if new abbreviation variations appear

### Usage

**In dbt models**: Reference via `{{ ref('dim_team_defense_xref') }}`

**In Python**: Use `ff_analytics_utils.get_defense_xref()` function

**In R script**: Loaded automatically via `--defense_xref` CLI parameter (passed by Python loader)

### Related Components

- **dbt model**: `models/core/dim_team_defense_xref.sql`
- **Python utility**: `src/ff_analytics_utils/defense_xref.py`
- **R mapping logic**: `scripts/R/ffanalytics_run.R` (lines 729-832)
- **Python loader**: `src/ingest/ffanalytics/loader.py` (passes seed to R via context manager)

### Performance Impact

Adding DST mapping improved FFAnalytics coverage:

- **Before**: ~89% mapped (138/1291 unmapped, including ~90 DST)
- **After**: ~93% mapped (612 DST projections now fully mapped)
- **Remaining unmapped**: Primarily IDP deep roster and practice squad players
