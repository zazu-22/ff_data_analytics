# Ticket CC-002: Audit Notebooks for Hardcoded Date Filters

**Phase**: Cross-Cutting\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: None (can be done anytime)

## Objective

Audit Jupyter notebooks for hardcoded `dt=` filters and encourage using dbt refs instead of raw Parquet reads.

## Context

Notebooks may have hardcoded snapshot dates that become stale when new snapshots are loaded. This audit identifies issues and adds deprecation warnings to encourage best practices.

## Tasks

- [ ] Scan `notebooks/` directory for hardcoded dt= filters
- [ ] Identify notebooks reading raw Parquet files directly
- [ ] Add deprecation warnings in affected notebooks
- [ ] Update notebooks to use dbt refs where possible
- [ ] Document notebook best practices

## Acceptance Criteria

- [ ] All notebooks audited
- [ ] Hardcoded dates identified and documented
- [ ] Deprecation warnings added
- [ ] Best practices guide created for notebook authors

## Implementation Notes

**Notebooks to Audit**:

- `notebooks/fasa_enhanced_v2.ipynb`
- `notebooks/fasa_weekly_strategy.ipynb`
- Any other notebooks in `notebooks/`

**Search Pattern**:

```bash
grep -r "dt=" notebooks/*.ipynb
grep -r "read_parquet.*raw" notebooks/*.ipynb
```

**Best Practice**: Encourage using dbt refs:

```python
# BAD: Direct Parquet read with hardcoded date
df = pl.read_parquet('data/raw/nflverse/weekly/dt=2025-10-27/*.parquet')

# BETTER: Read dbt model output
import duckdb
conn = duckdb.connect('dbt/ff_data_transform/target/dev.duckdb')
df = conn.execute('SELECT * FROM stg_nflverse__player_stats').pl()

# BEST: Use dbt-generated views
# (Set up dbt to create views that notebooks can reference)
```

**Deprecation Warning Cell** (add to affected notebooks):

```markdown
## ⚠️ DEPRECATION WARNING

This notebook reads raw Parquet files directly with hardcoded dates.
This approach will break when new snapshots are loaded.

**Recommended**: Use dbt model outputs instead of raw files.

See: `docs/ops/snapshot_management_current_state.md`
```

## Testing

1. **Audit completion**: Verify all notebooks scanned
2. **Warning visibility**: Ensure warnings display correctly
3. **dbt ref examples**: Test that dbt-based reads work

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Cross-Cutting Notebook Audit (lines 590-595)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Notebook Audit (lines 590-595)
- Notebooks: `notebooks/` directory
