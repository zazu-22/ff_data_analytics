# ADR-011: Sequential Surrogate Key for player_id

**Status:** Accepted
**Date:** 2025-10-29
**Decision Makers:** Jason Shaffer, Development Team
**Supersedes:** ADR-010 (mfl_id as Canonical Player Identity)
**Related:** ADR-012 (Name and Position Normalization for IDP Projections)

## Context

ADR-010 (dated 2025-09-30) established that `mfl_id` should be the canonical `player_id` throughout the dimensional model, with the rationale that it provides platform-agnostic identity from nflverse.

However, during implementation (October 2025), a sequential surrogate key architecture was adopted instead. This ADR documents the actual implemented architecture and provides rationale for diverging from ADR-010.

### What Was Implemented

```sql
-- dim_player_id_xref (actual implementation)
CREATE TABLE dim_player_id_xref (
    player_id BIGINT PRIMARY KEY,   -- Sequential surrogate (1, 2, 3, ..., 9734)
    mfl_id BIGINT,                  -- External ID from nflverse (17030, 17031, ...)
    gsis_id VARCHAR,                -- NFL GSIS ID
    sleeper_id INTEGER,             -- Sleeper platform
    -- ... 18 other provider IDs
    name VARCHAR,                   -- "First Last" format
    merge_name VARCHAR,             -- Normalized for matching
    name_last_first VARCHAR,        -- "Last, First" format (added ADR-012)
    position VARCHAR,               -- NFL-specific (DE, DT, CB, S, etc.)
    team VARCHAR,
    birthdate DATE,
    draft_year INTEGER
);
```

**Key Difference:** `player_id` is a sequential integer (1-N), NOT equal to `mfl_id`.

### Why the Change?

The sequential surrogate approach was chosen during the October 2025 implementation for practical reasons:

1. **Simpler joins:** Integer primary keys are smaller and faster than VARCHAR joins
2. **Stable ordering:** Sequential keys maintain consistent sort order regardless of raw data ordering
3. **Easy filtering:** Can select subsets by ID ranges for testing/sampling
4. **No collisions:** Guaranteed unique without checking external system
5. **Compact indexes:** Integer indexes are smaller in memory and on disk

## Decision

**Use a sequential surrogate key (1-N) as canonical `player_id`, with `mfl_id` retained as an attribute for cross-platform integration.**

### Architecture

```text
Canonical Identity Layer:
    player_id (sequential surrogate: 1, 2, 3, ..., 9734)
        ↓
    Managed by: scripts/seeds/generate_dim_player_id_xref.py
        ↓
    Assigned as: pl.int_range(1, df_filtered.height + 1)

External ID Integration Layer:
    mfl_id, gsis_id, sleeper_id, espn_id, yahoo_id, ktc_id, ...
        ↓
    Source: nflverse ff_playerids dataset
        ↓
    Used for: Mapping external provider IDs → canonical player_id
```

### Generation Process

```python
# scripts/seeds/generate_dim_player_id_xref.py
def generate_dim_player_id_xref(raw_path, output_path):
    # 1. Load nflverse ff_playerids
    df = pl.read_parquet(raw_path)  # ~12,133 rows

    # 2. Filter team placeholders (only mfl_id, no other IDs)
    df_filtered = df.filter(
        pl.col("gsis_id").is_not_null()
        | pl.col("sleeper_id").is_not_null()
        | ... # 5 criteria total
    )  # ~9,734 valid players remaining

    # 3. Assign sequential player_id
    df_with_id = df_filtered.with_columns(
        pl.int_range(1, df_filtered.height + 1).alias("player_id")
    )

    # 4. Export to CSV seed
    df_with_id.write_csv("dbt/ff_analytics/seeds/dim_player_id_xref.csv")
```

## Rationale

### 1. Performance

**Integer vs VARCHAR Primary Keys:**

| Metric           | Sequential INT            | VARCHAR (mfl_id)           |
| ---------------- | ------------------------- | -------------------------- |
| Index size       | 4-8 bytes/row             | 12-24 bytes/row            |
| Join performance | Fast (integer comparison) | Slower (string comparison) |
| Memory footprint | 39-78 KB (9,734 rows)     | 117-234 KB (9,734 rows)    |
| Sort performance | O(n log n) integer        | O(n log n) string (slower) |

For a dataset of 9,734 players with potentially millions of fact table rows, integer joins provide measurable performance benefits.

### 2. Stability Within Version

**Sequential surrogate stability:**

- ✅ Stable within a crosswalk version (regenerating with same source data produces same IDs)
- ✅ Deterministic assignment order (sorted by some criterion)
- ❌ Changes when crosswalk is regenerated with new players added

**mfl_id stability:**

- ✅ Stable across nflverse updates (mfl_id doesn't change)
- ✅ Stable across team changes, retirements
- ✅ Globally unique (assigned by MyFantasyLeague)

**Trade-off accepted:** We prioritize performance and simplicity over absolute cross-version stability. When the crosswalk is regenerated (new players added, old players removed), player_id assignments may shift. This is acceptable because:

1. Crosswalk regeneration is infrequent (monthly or quarterly)
2. dbt models rebuild from scratch each run, maintaining referential integrity
3. The `mfl_id` attribute provides a stable external reference if needed

### 3. Simplified Seed Management

**Sequential surrogate approach:**

```python
# Simple, deterministic generation
df.with_columns(pl.int_range(1, n + 1).alias("player_id"))
```

**mfl_id as primary key approach:**

```python
# Must handle:
# - What if mfl_id is null?
# - What if mfl_id has gaps?
# - What if mfl_id duplicates (unlikely but possible in raw data)?
df.with_columns(pl.col("mfl_id").cast(pl.String).alias("player_id"))
```

The sequential approach eliminates edge cases and simplifies seed generation logic.

### 4. Alignment with External Dependencies

**mfl_id as an attribute allows:**

- Mapping to Sleeper API (Sleeper → mfl_id → player_id)
- Mapping to KTC (KTC → mfl_id → player_id)
- Mapping to FFAnalytics (name → mfl_id → player_id)
- Mapping to Commissioner sheets (name → mfl_id → player_id)

The crosswalk still serves its purpose of cross-platform integration, with player_id providing an internal canonical key and mfl_id serving as the external integration point.

## Consequences

### Positive

1. **Faster joins:** Integer primary keys improve query performance
2. **Smaller indexes:** Reduced memory and storage footprint
3. **Simpler generation:** Sequential assignment eliminates edge cases
4. **Testing convenience:** Easy to select player subsets by ID ranges
5. **All ADR-010 benefits retained:** Cross-platform integration still works via mfl_id attribute

### Negative

1. **Cross-version instability:** player_id values may change when crosswalk is regenerated
2. **ADR-010 inconsistency:** Documented decision differs from implementation
3. **Migration awareness:** External tools referencing player_id must understand it's not mfl_id

### Mitigation for Cross-Version Instability

**Strategy:** Treat crosswalk regeneration as a breaking change:

1. **Version the seed:** Include generation date/version in commit message
2. **Rebuild all models:** dbt run rebuilds fact tables with new player_id mappings
3. **External references use mfl_id:** If external systems need stable IDs, use mfl_id
4. **Documentation:** Clearly state that player_id is version-specific

### Comparison to ADR-010

| Aspect                 | ADR-010 (mfl_id)                 | ADR-011 (Sequential)                 | Status    |
| ---------------------- | -------------------------------- | ------------------------------------ | --------- |
| Platform agnosticism   | ✅ mfl_id is neutral             | ✅ mfl_id available as attribute     | Preserved |
| Separation of concerns | ✅ Explicit joins via crosswalk  | ✅ Same architecture                 | Preserved |
| Stability              | ✅ mfl_id never changes          | ⚠️ player_id changes on regeneration | Trade-off |
| Provider coverage      | ✅ 20 provider IDs               | ✅ Same 20 IDs                       | Preserved |
| Name resolution        | ✅ merge_name for fuzzy matching | ✅ Same + name_last_first (ADR-012)  | Enhanced  |
| Performance            | ⚠️ VARCHAR joins                 | ✅ Integer joins                     | Improved  |
| Simplicity             | ⚠️ Must handle nulls/gaps        | ✅ Sequential is simpler             | Improved  |

**Verdict:** ADR-011 preserves all key benefits of ADR-010 while improving performance and simplicity. The trade-off is cross-version stability, which is acceptable given infrequent regeneration and dbt's full-rebuild model.

## Implementation Status

**Current State:** ✅ Fully implemented (October 2025)

- Seed generation script: `scripts/seeds/generate_dim_player_id_xref.py`
- Seed file: `dbt/ff_analytics/seeds/dim_player_id_xref.csv` (9,734 rows)
- dim_player model: `dbt/ff_analytics/models/core/dim_player.sql`
- All fact tables: Use player_id as foreign key
- All staging models: Map provider IDs → player_id via crosswalk join

**Evidence:**

```sql
-- From dim_player.sql (lines 21-27)
/*
Key Design Decision: player_id (sequential surrogate key) is the canonical
identifier used throughout the pipeline. mfl_id remains available as an
attribute for provider integration but is NOT the primary key.
*/

SELECT
    -- Primary key (canonical player identifier - sequential from crosswalk)
    player_id,

    -- Provider ID mappings (20 platforms for cross-platform integration)
    mfl_id,
    gsis_id,
    sleeper_id,
    -- ... 17 more IDs
```

## Alternatives Considered

### Alternative 1: Implement ADR-010 as Written (mfl_id as player_id)

**Pros:**

- Aligns with documented decision
- Provides cross-version stability
- More "pure" dimensional modeling (natural key)

**Cons:**

- VARCHAR joins are slower
- Must handle mfl_id gaps/nulls in edge cases
- Larger index footprint

**Verdict:** Rejected in favor of performance and simplicity. The benefits of sequential surrogates outweigh the downsides for this use case.

### Alternative 2: Use Hybrid Approach (player_id + player_mfl_id)

**Pros:**

- Makes relationship between internal and external IDs explicit
- Could version player_id (player_id_v1, player_id_v2) for cross-version tracking

**Cons:**

- More complex schema (two ID columns)
- Confusing naming (when to use player_id vs player_mfl_id?)
- Doesn't solve core trade-off

**Verdict:** Rejected as unnecessary complexity. Current approach is clear: player_id is internal canonical, mfl_id is external integration point.

### Alternative 3: Generate UUID/GUID Surrogate Keys

**Pros:**

- Globally unique (no collisions even across systems)
- Stable across regenerations if deterministically derived from mfl_id

**Cons:**

- 16-byte keys (vs 4-8 for integer)
- Slower joins than integer
- More complex generation logic

**Verdict:** Rejected as over-engineering. Simple sequential integers meet all requirements.

## References

- [ADR-010](./ADR-010-mfl-id-canonical-player-identity.md) (Superseded decision)
- [ADR-012](./ADR-012-name-position-normalization-idp.md) (Related: Name/position normalization)
- [dim_player.sql](../../dbt/ff_analytics/models/core/dim_player.sql) (Implementation)
- [generate_dim_player_id_xref.py](../../scripts/seeds/generate_dim_player_id_xref.py) (Seed generation)
- [SPEC-1 v2.2](../spec/SPEC-1_v_2.2.md) (Identity resolution requirements)

## Revision History

- **2025-10-29:** Initial decision (v1.0) - Documents actual implementation, supersedes ADR-010
