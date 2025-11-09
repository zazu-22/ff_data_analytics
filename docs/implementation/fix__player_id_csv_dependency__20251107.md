# Fix: Eliminate CSV Dependency from Ingest Pipeline

| \--- | --- |
| **Version:** | 1.1.0 |
| **Status:** | Draft |
| **Date created:** | 2025-11-07 |
| **Date modified:** | 2025-11-08 |

## Overview

### Problem Statement

The Google Sheets ingestion script (and two others: FFanalytics and Sleeper) hardcode a path to `dbt/ff_analytics/seeds/dim_player_id_xref.csv` and read it directly during raw data ingestion - which happens before dbt runs.

This design creates a classic dependency inversion: ingestion needs player mappings, but those mappings are now produced by dbt, which runs after ingestion.

### Desired End State

- Keep the current architecture (sheets/ffanalytics map during ingestion).
- Replace the hardcoded CSV path with a smart utility
- The smart utility should:
  - Read from DuckDB as primary (always fresh from dbt)
  - Read from Parquet as fallback (raw nflverse snapshots)
  - Automatically handle local vs GCS paths for cloud readiness

### Benefits

- Fixes CSV dependency (no more manual CSV exports)
- Automated local workflow (make ingest-all)
- Cloud-ready (PyArrow handles local + GCS transparently)
- Preserves early validation for sheets/ffanalytics
- Maintains architectural soundness (providers with stable IDs use dbt mapping)
- Compatible with multi-source governance plan (no conflicts)
- Clear failure modes (missing xref → clear error message)

## Implementation Plan

### Phase 1: Create Shared Utilities

#### Task 1.1: Add DuckDB helper

src/ff_analytics_utils/duckdb_helper.py

- `get_duckdb_connection()` — respects DBT_DUCKDB_PATH env var
- `query_table()` — generic DuckDB query to Polars DataFrame
- `get_player_xref()` — convenience wrapper fordim_player_id_xref

#### Task 1.2: Extend storage helper

src/ff_analytics_utils/storage.py

- Move/extend `src/ingest/common/storage.py` patterns to shared utils
- Add `read_parquet_any()` — PyArrow filesystem abstraction for local + GCS
- Add `get_player_xref_from_parquet(` — read raw nflverse ff_playerids

#### Task 1.3: Create xref resolver

src/ff_analytics_utils/player_xref.py

- `get_player_xref(source=‘auto’)` — smart source
  selection:
  - Try DuckDB first (if dbt has run)
  - Fallback to latest Parquet snapshot
  - Raise clear error if neither available
  - Returns Polars DataFrame with all xref columns

### Phase 2: Update Ingestion Providers

#### Task 2.1: Refactor sheets

src/ingest/sheets/commissioner_parser.py

- Replace hardcoded CSV path (line 1025) with `get_player_xref()`
- Keep all mapping logic unchanged (fuzzy matching, position awareness)
- Update docstring to note dependency resolution

#### Task 2.2: Refactor `ffanalytics`

scripts/R/ffanalytics_run.R

- Create Python helper: `src/ingest/ffanalytics/get_xref.py`
  - Calls `get_player_xref()` from utils
  - Exports to temp CSV for R script compatibility
  - R script reads from temp path (no logic changes)
- Alternative: Port R logic to Python (more invasive, defer to future)

#### Task 2.3: Update loader interfaces

- Remove hardcoded paths from function signatures
- Document dependency on dbt xref model in docstrings

### Phase 3: Orchestration & Automation

#### Task 3.1: Add Makefile targets

##### 3.1.1: Build the player xref

```Makefile
.PHONY: dbt-xref
dbt-xref: uv run dbt run
—select dim_player_id_xref
—project-dir dbt/ff_analytics
—profiles-dir dbt/ff_analytics
```

##### 3.1.2: Ingest sources that need xref

```Makefile
.PHONY: ingest-with-xref
ingest-with-xref: dbt-xref
$(MAKE) ingest-sheets
$(MAKE) ingest-ffanalytics
```

##### 3.1.3 Full automated ingestion flow

```Makefile
.PHONY: ingest-all
ingest-all:
$(MAKE) ingest-nflverse  # NFLverse first (source for xref)
$(MAKE) dbt-xref  # Build xref from nflverse
$(MAKE) ingest-sheets  # Now sheets can use xref
$(MAKE) ingest-ffanalytics  # And ffanalytics
$(MAKE) ingest-sleeper-players  # Other sources (no xref dependency)
$(MAKE) ingest-ktc  # Other sources
```

#### Task 3.2: Update GitHub Actions workflows

- `.github/workflows/ingest_google_sheets.yml` — add dbt-xref step before sheets ingestion
- Document dependency chain in workflow comments

### Phase 4: Testing & Validation

#### Task 4.1: Add unit tests

tests/test_player_xref_utils.py

- Test DuckDB reading (mock connection)
- Test Parquet reading (use test fixtures)
- Test fallback logic (DuckDB fails → Parquet succeeds)
- Test error handling (both sources unavailable)

#### Task 4.2: Add integration tests

- Test sheets ingestion with xref from DuckDB
- Test ffanalytics ingestion with xref from DuckDB
- Verify output matches previous CSV-based approach

#### Task 4.3: Update dbt tests

- Evaluate existing tests for mapping coverage validation
- Extend as needed to ensure mapping coverage
- Fix any testing errors identified

### Phase 5: Quality Control, Documentation, and Cleanup

#### Task 5.1: Check for dependencies and references

- Search for any remaining dependencies and references to old workflow
- Refactor to reference and work with new workflow

#### Task 5.2: Update documentation

- `src/ff_analytics_utils/README.md` — document new utilities
- `src/ingest/CLAUDE.md` — note xref dependency pattern
- `dbt/ff_analytics/CLAUDE.md` — note xref is now used by ingestion
- Add `ADR-0015.md` (or next available ADR in sequence) — documents new xref architecture and rationale
- Update any `CLAUDE.md` and `AGENT.md` files that reference these topics

#### Task 5.3: Remove obsolete artifacts

- Delete `dbt/ff_analytics/seeds/dim_player_id_xref.csv` (if exists)
- Remove seed configuration from `seeds.yml`
- Clean up migration notes
- Search for any other obsolete artifacts and either move or archive

#### Task 5.4: Add or update troubleshooting guide

- Document common errors (DuckDB not found, xref table missing)
- Explain resolution (run make dbt-xref first)

### Phase 6: Cloud Readiness (Future-Proof)

#### Task 6.1: GCS compatibility (built-in via PyArrow)

- Confirm PyArrow setup properly to handle `gs://` URIs
- If not, configure PyArrow
- Document environment variables for GCS:
  - `GOOGLE_APPLICATION_CREDENTIALS` (see `.env`)
  - `GCS_BUCKET=ff-analytics` (see `.env`)

#### Task 6.2: Prefect integration (governance plan Phase 4)

- Review relevant documentation and tickets for Phase 4 of the snapshot governance plan (see `docs/implementation/`)
- Update as needed to reflect new xref design, including:
  - Add xref task: `@task def build_player_xref()`
  - Define dependencies: nflverse_task >> build_xref_task >> sheets_task
- Confirm ingestion that no code changes needed, due to utilities having been designed to abstract source

## Implementation Order

Suggested implementation order to allow for testing and validating components of the fix:

1. Utilities first (why: can test in isolation)
2. Sheets provider (why: authoritative fantasy league data)
3. FFanalytics provider (why: core prediction data source)
4. Orchestration (why: enables automated workflows)
5. Quality Control & Documentation (why: prevents breaking changes; explains new patterns for future development)
6. Cleanup (why: remove obsolete CSV artifacts not until validating everything works and is documented)

______________________________________________________________________

Annotations: 0,7160 SHA-256 8eb4aeeb4f8ce1c28e56c7a7c358ee26\
&Claude: 223,232 462,146 629,130 795,5 801,7 811,7 820,22 856,8 867,35 904,20 925,323 1249,139 1410,53 1464,18 1483,42 1528,23 1552 1554,36 1591,12 1605 1607,44 1652,17 1670 1672,132 1805,28 1834,19 1854,12 1867,18 1886 1888,35 1924,7 1932,10 1943,29 1973 1975,18 1994,93 2088,30 2119 2121,26 2148,36 2185,38 2224,41 2266,104 2371,16 2388,41 2430,47 2478,17 2496,61 2558,74 2633,10 2644,11 2658,27 2686,25 2712,34 2747 2749,8 2758,17 2776,12 2789,49 2839,136 2976,25 3002,160 3163,21 3185 3199,20 3220 3234,26 3261,14 3276,57 3334,30 3368,2 3384,28 3425,43 3469,57 3530,2 3536 3543,30 3586,55 3643,51 3696,48 3746,20 3767,31 3800,49 3850,24 3875,30 3906,16 3926,15 3942,32 3975,3 3979,42 4022 4024,141 4166,15 4183,31 4215,203 4419,22 4442,164 4607,17 4625,3 4638,14 4655,17 4765,15 4797,13 4816,7 5000,14 5016,21 5038,3 5042,32 5075 5077,26 5104,20 5125 5127,32 5160,26 5187 5189,42 5232,3 5402,14 5418,26 5445,10 5456,45 5502,46 5549,9 5559,27 5655,14 5671,4 5685,22 5708,171 5880,41 5922,3 6006,43 6050,2 6053,30 6084,2 6091,4 6096,2 6099,2 6102,23 6126,2 6133,4 6138,16 6155,46 6377 6379,17 6397,29 6427 6429,55 6485,17 6509,11 6528,19 6556,9 6590,18 6611,21 6723,20 6749,21 6771,20 6797,14 6826,20 6890,18 6914,27 6942,4 6964,14 7011,21 7056,12 7074,29\
@Jason Shaffer <jason@swarmint.com>: 0,93 95,11 108,9 119,17 138,13 154,18 174,49 455,7 608,21 759,36 800 808,3 818,2 842,14 864,3 902,2 924 1248 1388,22 1482 1525,3 1551 1553 1590 1603,2 1606 1651 1669 1671 1804 1833 1853 1866 1885 1887 1923 1931 1942 1972 1974 1993 2087 2118 2120 2147 2184 2223 2265 2370 2387 2429 2477 2495 2557 2632 2643 2655,3 2685 2711 2746 2748 2757 2775 2788 2838 3001 3184 3186,13 3219 3221,13 3260 3275 3333 3364,4 3370,14 3412,13 3468 3526,4 3532,4 3537,6 3573,13 3641,2 3694,2 3744,2 3766 3798,2 3849 3874 3905 3922,4 3974 3978 4021 4023 4181,2 4214 4441 4624 4628,10 4652,3 4672,93 4780,17 4810,6 4823,177 5014 5037 5041 5074 5076 5103 5124 5126 5159 5186 5188 5231 5235,167 5416 5444 5455 5501 5548 5558 5586,69 5669 5675,10 5707 5921 5925,81 6049 6052 6083 6086,5 6095 6098 6101 6125 6128,5 6137 6201,176 6378 6396 6426 6428 6484 6502,7 6520,8 6547,9 6565,25 6608,3 6632,91 6743,6 6770 6791,6 6811,15 6846,44 6908,6 6941 6946,18 6978,33 7032,24 7068,6 7103,57\
...
