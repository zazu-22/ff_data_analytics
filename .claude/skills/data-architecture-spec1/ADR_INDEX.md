# Architecture Decision Records (ADR) Index

Quick reference catalog of all architecture decisions for the FF Analytics data platform. For full details, see individual ADR files in `reference/adr/`.

## Core Architecture

### ADR-001: Canonical Stat Dictionary

**Status:** Accepted
**Summary:** Use neutral stat names in canonical schema; provider-specific names mapped in staging layer.

**Key Points:**

- Stat dictionary with provider mappings
- Staging models normalize to canonical names
- Enables multi-provider stat aggregation
- Reduces coupling to any single data source

**Impact:** All staging models, fact tables, stat naming conventions

---

### ADR-002: Twice-Daily Batch Schedule

**Status:** Accepted
**Summary:** Run batch ingestion at 08:00 and 16:00 UTC daily.

**Key Points:**

- Fixed schedule: 08:00 UTC (post-waiver), 16:00 UTC (mid-day updates)
- All timestamps stored in UTC
- Notebooks display in ET for user convenience
- GitHub Actions `schedule` triggers

**Impact:** Ingestion scripts, orchestration, freshness thresholds

---

### ADR-003: Schema Versioning Strategy

**Status:** Accepted
**Summary:** Breaking schema changes use `_vN` suffixes with compatibility views.

**Key Points:**

- Non-breaking changes: in-place updates
- Breaking changes: `table_name_v2`, `table_name_v3`
- Compatibility views: `table_name` → latest version
- Backfill strategy for version migrations

**Impact:** dbt model naming, migration scripts, documentation

---

## Data Sources

### ADR-004: GitHub Actions for Sheets Access

**Status:** Accepted
**File:** [`reference/adr/ADR-004-github-actions-for-sheets.md`](../../docs/adr/ADR-004-github-actions-for-sheets.md)

**Summary:** Use service account authentication in GitHub Actions for Commissioner Sheet access.

**Key Points:**

- Service account with Sheets API access
- Store credentials in GitHub Secrets
- CI/CD can copy and parse sheets
- Enables automated twice-daily ingestion

**Impact:** CI/CD configuration, authentication, sheet access patterns

---

### ADR-005: Commissioner Sheet Server-Side Copy Strategy

**Status:** Accepted
**File:** [`reference/adr/ADR-005-commissioner-sheet-ingestion-strategy.md`](../../docs/adr/ADR-005-commissioner-sheet-ingestion-strategy.md)

**Summary:** Copy complex Commissioner Sheet server-side with value freezing before parsing.

**Key Points:**

- Complex formulas/IMPORTRANGE → frozen copy
- Server-side `copyTo` API (not export)
- Intelligent skip logic based on modification times
- Shared Drive logging for service account quota
- Last-known-good (LKG) fallback on failures

**Impact:** Sheets ingestion, error handling, CI/CD workflow

**Workflow:**

```
1. copy_league_sheet.py → frozen copy with values only
2. commissioner_parser.py → parse to Parquet
3. dbt run/test → validate and build models
```

---

### ADR-006: GCS Integration Strategy

**Status:** Accepted
**File:** [`reference/adr/ADR-006-gcs-integration-strategy.md`](../../docs/adr/ADR-006-gcs-integration-strategy.md)

**Summary:** Environment-based configuration for local vs cloud storage paths.

**Key Points:**

- Local dev: `data/{raw,stage,mart}/`
- Cloud: `gs://ff-analytics/{raw,stage,mart}/`
- PyArrow FS abstraction for write operations
- DuckDB httpfs for read operations
- Single codebase, environment-specific paths

**Impact:** Ingestion scripts, dbt profiles, storage helpers

**Configuration:**

```python
# src/ingest/common/storage.py
out_dir = os.getenv('EXTERNAL_ROOT', 'data') + '/raw/nflverse'
```

---

## Data Model

### ADR-007: Separate Fact Tables for Actuals vs Projections

**Status:** Accepted
**File:** [`reference/adr/ADR-007-separate-fact-tables-actuals-vs-projections.md`](../../docs/adr/ADR-007-separate-fact-tables-actuals-vs-projections.md)

**Summary:** Implement separate fact tables for actuals (per-game grain) and projections (weekly/season grain).

**Key Points:**

- **`fact_player_stats`:** Per-game actuals from nflverse
  - Grain: `(player_key, game_id, stat_name, provider, measure_domain, stat_kind)`
  - Includes `game_id` (NOT NULL)
- **`fact_player_projections`:** Weekly/season projections from FFanalytics
  - Grain: `(player_id, season, week, horizon, stat_name, provider, measure_domain, asof_date)`
  - Includes `horizon` column, NO `game_id`
- No nullable keys in grain
- 2×2 model alignment (actuals vs projections on separate axis)

**Impact:** Fact table design, grain definitions, 2×2 model implementation

**Architecture:**

```
2×2 Model Implementation:

                 Real-World Stats              Fantasy Points
                 ────────────────              ──────────────
Actuals          fact_player_stats        →    mart_fantasy_actuals_weekly
                 (per-game grain)              (apply scoring rules)

Projections      fact_player_projections  →    mart_fantasy_projections
                 (weekly/season grain)         (apply scoring rules)
```

---

### ADR-008: League Transaction History Integration

**Status:** Accepted
**File:** [`reference/adr/ADR-008-league-transaction-history-integration.md`](../../docs/adr/ADR-008-league-transaction-history-integration.md)

**Summary:** Parse TRANSACTIONS tab from Commissioner Sheet into normalized transaction history.

**Key Points:**

- Source: TRANSACTIONS tab (Sort, Timeframe, From, To, Player/Pick, Contract Terms, Notes)
- Normalized to long-form (one row per asset per transaction)
- Map player names → `player_id` via `dim_player_id_xref`
- Map pick strings → `pick_id` via `dim_pick`
- Group multi-asset trades via `transaction_id`
- Asset types: player, pick, cap_space

**Impact:** Commissioner sheet parsing, fact_league_transactions, trade analysis marts

**Dependencies:** Phase 1 seeds (dim_player_id_xref, dim_pick, dim_asset, dim_timeframe)

---

### ADR-009: Single Consolidated Fact Table for NFL Stats

**Status:** Accepted
**File:** [`reference/adr/ADR-009-single-consolidated-fact-table-nfl-stats.md`](../../docs/adr/ADR-009-single-consolidated-fact-table-nfl-stats.md)

**Summary:** UNION all NFL stat types (base, snaps, opportunity) into single `fact_player_stats`.

**Key Points:**

- Single fact table for all NFL actuals
- UNION ALL from multiple staging sources:
  - `stg_nflverse__player_stats` (50 base stats)
  - `stg_nflverse__snap_counts` (6 snap stats)
  - `stg_nflverse__ff_opportunity` (32 opportunity metrics)
- Total: 88 stat types
- Consistent grain across all stat types
- Simplifies downstream queries

**Impact:** fact_player_stats design, staging model structure

---

### ADR-010: mfl_id as Canonical Player Identity

**Status:** Accepted
**File:** [`reference/adr/ADR-010-mfl-id-canonical-player-identity.md`](../../docs/adr/ADR-010-mfl-id-canonical-player-identity.md)

**Summary:** Use nflverse `mfl_id` as canonical `player_id` throughout dimensional model.

**Key Points:**

- **Canonical ID:** `mfl_id` (from nflverse ff_playerids dataset)
- **Not** `gsis_id` (NFL-specific, couples to single provider)
- Platform-agnostic, stable across team changes
- Comprehensive coverage: 19 provider IDs in crosswalk
- Built-in support for name-based fuzzy matching via `merge_name`

**Provider IDs Supported:**

- `mfl_id` (canonical)
- `gsis_id`, `sleeper_id`, `espn_id`, `yahoo_id`, `pfr_id`
- `fantasypros_id`, `pff_id`, `cbs_id`, `ktc_id`
- `sportradar_id`, `fleaflicker_id`, `rotowire_id`, `rotoworld_id`
- `stats_id`, `stats_global_id`, `fantasy_data_id`
- `swish_id`, `cfbref_id`, `nfl_id`

**Impact:** dim_player_id_xref seed, all staging models, identity resolution patterns

**Crosswalk Pattern:**

```sql
left join {{ ref('dim_player_id_xref') }} xref
  on source.gsis_id = xref.gsis_id  -- or sleeper_id, espn_id, etc.
select
  coalesce(xref.player_id, source.gsis_id) as player_key,
  xref.player_id,  -- mfl_id (canonical)
  -- ... other columns
```

---

## Quick Decision Lookup

**When to use which ADR:**

| Question | See ADR |
|----------|---------|
| How should I name stats across providers? | ADR-001 |
| What schedule for batch jobs? | ADR-002 |
| How to handle schema changes? | ADR-003 |
| How to access Commissioner Sheet in CI? | ADR-004 |
| How to parse Commissioner Sheet? | ADR-005 |
| Where to store data (local vs cloud)? | ADR-006 |
| Actuals and projections in same table? | ADR-007 |
| How to parse TRANSACTIONS tab? | ADR-008 |
| Separate fact per stat type? | ADR-009 |
| Which ID to use for players? | ADR-010 |

## ADR Status Summary

| ADR | Status | Implementation Status |
|-----|--------|----------------------|
| ADR-001 | Accepted | ✅ Implemented |
| ADR-002 | Accepted | ✅ Implemented (schedule configured) |
| ADR-003 | Accepted | ✅ Pattern documented |
| ADR-004 | Accepted | ✅ Service account configured |
| ADR-005 | Accepted | ✅ Copy script implemented |
| ADR-006 | Accepted | ✅ GCS write support added |
| ADR-007 | Accepted | ⚠️ fact_player_stats complete, fact_player_projections pending |
| ADR-008 | Accepted | ⏳ Pending (blocked by seeds, Phase 2B) |
| ADR-009 | Accepted | ✅ Implemented (88 stats UNION'd) |
| ADR-010 | Accepted | ✅ Implemented (dim_player_id_xref seed created) |

## References

- **Full ADRs:** `reference/adr/` directory
- **SPEC-1 v2.2:** `reference/SPEC-1_v_2.2.md` (see § Architecture Decision Records)
- **Implementation Status:** `reference/SPEC-1_v_2.3_implementation_checklist_v_0.md`
