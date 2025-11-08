# Ticket P2-001: Create Snapshot Registry Seed

**Phase**: 2 - Governance\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: None (can start after Phase 1 kickoff)

## Objective

Create the snapshot registry seed file structure and schema that will serve as the single source of truth for tracking snapshot lifecycle across all 5 data sources.

## Context

The snapshot registry seed provides deterministic selection logic, CI validation against expected snapshots, audit trail for snapshot promotion/retirement, and LLM-friendly documentation of available data. This is the foundation of the governance system.

This ticket creates the file structure and documents the schema. The next ticket (P2-002) will populate it with actual snapshot data.

## Tasks

- [ ] Create `dbt/ff_data_transform/seeds/snapshot_registry.csv` file
- [ ] Define column schema with header row
- [ ] Add initial test entry to verify seed loads
- [ ] Document column definitions in seed schema file
- [ ] Test seed loading: `uv run dbt seed --select snapshot_registry`
- [ ] Verify seed accessible in dbt models

## Acceptance Criteria

- [ ] File exists at `dbt/ff_data_transform/seeds/snapshot_registry.csv`
- [ ] Header row with all required columns defined
- [ ] At least one test entry for validation
- [ ] `dbt seed` loads file without errors
- [ ] Column documentation complete

## Implementation Notes

**File**: `dbt/ff_data_transform/seeds/snapshot_registry.csv`

**Column Schema** (from plan Design Decision #3):

| Column                  | Type    | Description                                                  |
| ----------------------- | ------- | ------------------------------------------------------------ |
| `source`                | string  | Data provider (nflverse, sheets, ktc, ffanalytics, sleeper)  |
| `dataset`               | string  | Specific dataset within source (weekly, snap_counts, etc.)   |
| `snapshot_date`         | date    | Partition date (dt value in YYYY-MM-DD format)               |
| `status`                | string  | Lifecycle stage (pending, current, historical, archived)     |
| `coverage_start_season` | integer | Earliest season in snapshot (nullable for non-seasonal data) |
| `coverage_end_season`   | integer | Latest season in snapshot (nullable for non-seasonal data)   |
| `row_count`             | integer | Total rows for validation                                    |
| `notes`                 | string  | Freeform description                                         |

**Initial File Content** (with test entry):

```csv
source,dataset,snapshot_date,status,coverage_start_season,coverage_end_season,row_count,notes
nflverse,weekly,2025-10-27,historical,2020,2024,89145,Test entry - Historical baseline
```

**Lifecycle States**:

- `pending` - Snapshot loaded but not yet validated/promoted
- `current` - Active snapshot used in production dbt models
- `historical` - Previous snapshot kept for continuity (e.g., baseline)
- `archived` - Retained for audit but not actively used

**Benefits** (from plan):

- Deterministic selection logic referencing single source of truth
- CI validation against expected snapshots
- Audit trail for snapshot promotion/retirement
- LLM-friendly documentation of available data

**Schema Documentation**:

Create or update `dbt/ff_data_transform/seeds/schema.yml`:

```yaml
version: 2

seeds:
  - name: snapshot_registry
    description: "Registry tracking snapshot lifecycle across all data sources"
    columns:
      - name: source
        description: "Data provider (nflverse, sheets, ktc, ffanalytics, sleeper)"
        tests:
          - not_null
          - accepted_values:
              values: ['nflverse', 'sheets', 'ktc', 'ffanalytics', 'sleeper']

      - name: dataset
        description: "Specific dataset within source"
        tests:
          - not_null

      - name: snapshot_date
        description: "Partition date (dt value)"
        tests:
          - not_null

      - name: status
        description: "Lifecycle stage"
        tests:
          - not_null
          - accepted_values:
              values: ['pending', 'current', 'historical', 'archived']

      - name: coverage_start_season
        description: "Earliest season in snapshot (nullable)"

      - name: coverage_end_season
        description: "Earliest season in snapshot (nullable)"

      - name: row_count
        description: "Total rows for validation"
        tests:
          - not_null

      - name: notes
        description: "Freeform description"
```

## Testing

1. **Load seed**:

   ```bash
   cd dbt/ff_data_transform
   uv run dbt seed --select snapshot_registry
   ```

2. **Verify seed in DuckDB**:

   ```bash
   duckdb target/dev.duckdb
   SELECT * FROM snapshot_registry;
   ```

3. **Test schema validation**:

   ```bash
   uv run dbt test --select snapshot_registry
   ```

4. **Verify seed accessible in models**:

   ```sql
   -- Test query
   {{ ref('snapshot_registry') }}
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Design Decision #3 (lines 107-139)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 2 Registry (lines 90-106)
- Example entries: Plan lines 125-131
