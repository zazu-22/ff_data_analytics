# ADR-012: Name and Position Normalization for IDP Projection Matching

**Status:** Accepted
**Date:** 2025-10-29
**Decision Makers:** Jason Shaffer, Development Team
**Related:** ADR-011 (Sequential Surrogate Player ID), Phase 1 IDP Investigation

## Context

### Problem Discovery

During Phase 1 investigation of IDP (Individual Defensive Player) projection data flow (October 2025), we discovered that **100% of IDP projections were failing to map to canonical player IDs**, resulting in `player_id = -1` for all 5,839 IDP projection records.

**Root Cause Chain:**

1. **FantasySharks is the ONLY source** providing IDP projections (DL, LB, DB positions)
2. **FantasySharks uses "Last, First" name format** (e.g., "Parsons, Micah")
3. **Crosswalk uses "First Last" format** (e.g., "Micah Parsons")
4. **R mapping script did NOT normalize names** before matching
5. **Result:** "parsons, micah" ≠ "micah parsons" → NO MATCH → `player_id = -1`

**Impact:**

- 0% IDP mapping success (5,839 unmapped records)
- ~52% offensive player mapping (due to multiple sources; only FantasySharks failed)
- IDP projections completely filtered out in staging layer
- Zero IDP data reaching analytics marts or notebooks

### Secondary Issue: Position Mismatch

Even if names matched, there was a position format mismatch:

**FFAnalytics projections** (fantasy-generic):

- DL (Defensive Line) - combines DE + DT
- LB (Linebacker) - all LB types
- DB (Defensive Back) - combines CB + S

**Crosswalk positions** (NFL-specific):

- DE, DT (separate)
- LB (generic)
- CB, S (separate)

**Problem:** Position-agnostic name matching could match the wrong player if multiple players share a name (e.g., "Kyle Williams" as WR vs DT).

## Decision

**Implement two-layer normalization for player ID mapping:**

1. **Name normalization:** Detect and convert "Last, First" format to "First Last" before matching
2. **Position-aware matching:** Use fantasy position → NFL position translation during joins

### Solution 1: Name Normalization

**Implementation:** R mapping script (`scripts/R/ffanalytics_run.R`)

```r
# Before matching, normalize player names
consensus_df <- consensus_df %>%
  mutate(player_normalized = ifelse(
    grepl(",", player),
    # Convert "Last, First" → "First Last"
    paste(trimws(sub(".*,\\s*", "", player)),
          trimws(sub(",.*", "", player))),
    # Keep "First Last" as-is
    player
  )) %>%
  mutate(player_normalized = tolower(trimws(player_normalized)))
```

**How it works:**

```text
Input: "Parsons, Micah"
  → Detect comma: TRUE
  → Extract after comma: "Micah"
  → Extract before comma: "Parsons"
  → Recombine: "Micah Parsons"
  → Lowercase: "micah parsons"
  → Match against crosswalk ✅

Input: "Patrick Mahomes"
  → Detect comma: FALSE
  → Keep as-is: "Patrick Mahomes"
  → Lowercase: "patrick mahomes"
  → Match against crosswalk ✅
```

### Solution 2: Position Translation

**Implementation:** New seed + R script position-aware matching

**Seed:** `dbt/ff_analytics/seeds/dim_position_translation.csv`

```csv
fantasy_position,nfl_position,position_type,match_priority,notes
DL,DL,defense,100,"Exact match - generic defensive line"
DL,DE,defense,95,"Fantasy DL includes defensive ends"
DL,DT,defense,95,"Fantasy DL includes defensive tackles"
LB,LB,defense,100,"Exact match - linebacker (all types)"
LB,ILB,defense,95,"Fantasy LB includes inside linebackers"
LB,OLB,defense,95,"Fantasy LB includes outside linebackers"
DB,DB,defense,100,"Exact match - generic defensive back"
DB,CB,defense,95,"Fantasy DB includes cornerbacks"
DB,S,defense,95,"Fantasy DB includes safeties"
DB,SS,defense,95,"Fantasy DB includes strong safeties"
DB,FS,defense,95,"Fantasy DB includes free safeties"
QB,QB,offense,100,"Exact match - quarterback"
RB,RB,offense,100,"Exact match - running back"
... (19 total mappings)
```

**Matching logic:**

```r
# Expand projections to include compatible NFL positions
consensus_with_pos <- consensus_df %>%
  left_join(position_xref, by = c("pos" = "fantasy_position")) %>%
  mutate(nfl_position = coalesce(nfl_position, pos))

# Join with position-aware matching
consensus_df <- consensus_with_pos %>%
  left_join(xref_exact_match,
    by = c("player_normalized" = "name_normalized",
           "nfl_position" = "position")
  ) %>%
  # Group by original projection and pick best match
  group_by(player, season, week, pos, team) %>%
  arrange(desc(match_priority), desc(!is.na(mfl_id_exact))) %>%
  slice(1) %>%
  ungroup()
```

**How it works:**

```text
Projection: "Parsons, Micah", pos="DL"
  → Name normalized: "micah parsons"
  → Position expanded: DL → [DL, DE, DT] (from seed)

Crosswalk candidates:
  - "Micah Parsons", pos="DE" (match_priority=95) ✅ MATCH
  - "Micah Parsons", pos="QB" (no position match) ❌

Result: player_id = 2345 (Micah Parsons DE)
```

### Solution 3: Crosswalk Enhancement (Optional Redundancy)

**Implementation:** Add `name_last_first` column to crosswalk seed

**Rationale:** Defensive redundancy - if R script normalization fails, crosswalk provides pre-computed "Last, First" variant for direct matching.

**Generation:** `scripts/seeds/generate_dim_player_id_xref.py`

```python
# Add "Last, First" name variant
df_with_id = df_with_id.with_columns(
    pl.when(pl.col("name").str.contains(" "))
    .then(
        # Convert "First Last" → "Last, First"
        pl.concat_str([
            pl.col("name").str.split(" ").list.last(),
            pl.lit(", "),
            pl.col("name").str.split(" ").list.slice(0, -1).list.join(" ")
        ])
    )
    .otherwise(pl.col("name"))  # Single-word names unchanged
    .alias("name_last_first")
)
```

**Result:** Crosswalk now has 28 columns (was 27):

```csv
player_id,mfl_id,...,name,merge_name,name_last_first,position,team,...
1,17030,...,"Cam Ward","cam ward","Ward, Cam","QB","TEN",...
2,17031,...,"Shedeur Sanders","shedeur sanders","Sanders, Shedeur","QB","CLE",...
```

## Rationale

### 1. Immediate Fix for IDP Mapping Failure

**Before normalization:**

- IDP mapping: 0% (0 / 5,839 players)
- Offensive mapping: ~52% (varied by source)

**After normalization:**

- Expected IDP mapping: ~100% (5,839 / 5,839 players)
- Expected offensive mapping: ~100% (all sources handled)

**Why:** All IDP projections come from FantasySharks in "Last, First" format. Normalizing this format unlocks 5,839 previously unmapped records.

### 2. Position Disambiguation for Name Collisions

**Example collision:** "Kyle Williams"

**Without position matching:**

```sql
SELECT * FROM crosswalk WHERE name = 'Kyle Williams'
-- Returns: Kyle Williams (WR), Kyle Williams (DT), Kyle Williams (G)
-- Problem: Which one to use for "Williams, Kyle" DL projection?
```

**With position matching:**

```sql
SELECT * FROM crosswalk
WHERE name = 'Kyle Williams'
  AND position IN ('DL', 'DE', 'DT')  -- DL expanded to compatible positions
-- Returns: Kyle Williams (DT) only
-- Result: Correct player matched ✅
```

### 3. Extensibility to Other Sources

**Current benefit:** Fixes FantasySharks (IDP projections)

**Future benefit:** Any new projection source using "Last, First" format will work automatically

**Defensive redundancy:** Crosswalk `name_last_first` column provides a fallback if R script logic fails or if other ingestion paths (Python, SQL) need "Last, First" matching.

### 4. Alignment with Existing Patterns

**Commissioner sheet parser** already has position translation logic (Python):

```python
# src/ingest/sheets/commissioner_parser.py (lines 607-621)
def _normalize_position(txn_position: str) -> list[str]:
    position_map = {
        "DL": ["DE", "DT", "LB"],  # Includes edge rushers
        "DB": ["S", "CB", "LB"],   # Includes hybrid DBs
        "LB": ["LB", "DE", "S", "CB"],
        ...
    }
    return position_map.get(txn_position, [txn_position])
```

**New seed** provides centralized, reusable position mapping for R scripts, dbt models, and future use cases. (Note: Commissioner parser remains unchanged as its mapping is more permissive for hybrid roles.)

## Consequences

### Positive

1. **IDP projections now usable:** 5,839 IDP records flow through to marts and notebooks
2. **Higher overall mapping rate:** Offensive players improve from ~52% to ~100%
3. **Position-aware matching:** Prevents name collision mismatches
4. **Reusable pattern:** Position translation seed can be used by other ingestion processes
5. **Defensive redundancy:** Multiple normalization strategies (R script + crosswalk column)
6. **Documentation:** Clear precedent for future data source integrations

### Negative

1. **Additional complexity:** R script has more logic (name conversion, position join)
2. **Performance overhead:** Position translation adds join operation
3. **Maintenance:** Position translation seed requires updates if new position types emerge

### Risks Mitigated

**Risk:** Name normalization regex fails on edge cases (e.g., names with multiple commas, suffixes)

**Mitigation:**

- Test with edge cases: "Smith Jr., John", "Van Buren, Steve"
- Crosswalk `name_last_first` provides fallback
- Commissioner parser's fuzzy matching can catch missed cases

**Risk:** Position translation seed becomes stale or incomplete

**Mitigation:**

- Seed is version-controlled and documented
- Match priority allows "exact" (100) vs "compatible" (95) distinctions
- Future additions follow established pattern

## Implementation

### Files Modified

1. **R mapping script:** `scripts/R/ffanalytics_run.R`

   - Added name normalization (lines 346-356)
   - Added position translation loading (lines 349-359)
   - Added position-aware matching (lines 381-446)

2. **Crosswalk generation:** `scripts/seeds/generate_dim_player_id_xref.py`

   - Added `name_last_first` column generation (lines 65-80)
   - Updated seed columns list (28 columns)

3. **New seed:** `dbt/ff_analytics/seeds/dim_position_translation.csv`

   - 19 rows mapping fantasy positions to NFL positions
   - Includes match_priority for disambiguation

4. **Seed documentation:** `dbt/ff_analytics/seeds/seeds.yml`

   - Added dim_position_translation entry with column descriptions
   - Updated dim_player_id_xref description for new column

### Testing Strategy

**Pre-deployment validation:**

1. **Name normalization test:**

   ```r
   test_names <- c(
     "Parsons, Micah",      # Standard "Last, First"
     "Micah Parsons",       # Standard "First Last"
     "Smith Jr., John",     # Suffix with comma
     "Van Buren, Steve"     # Multi-word last name
   )
   # Expected all to normalize correctly
   ```

2. **Position translation test:**

   ```r
   test_cases <- data.frame(
     fantasy_pos = c("DL", "LB", "DB"),
     nfl_pos = c("DE", "ILB", "CB")
   )
   # Expected all to find compatible matches in seed
   ```

3. **End-to-end validation:**

   - Re-run ffanalytics ingestion
   - Check mapping statistics (target: >95% IDP mapped)
   - Query staging model for IDP records (target: >5,000 records)
   - Verify IDP appears in marts and notebooks

**Post-deployment monitoring:**

```sql
-- dbt test: IDP mapping coverage
SELECT
  pos,
  COUNT(*) as total,
  SUM(CASE WHEN player_id > 0 THEN 1 ELSE 0 END) as mapped,
  ROUND(100.0 * SUM(CASE WHEN player_id > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as pct_mapped
FROM {{ ref('stg_ffanalytics__projections') }}
WHERE pos IN ('DL', 'LB', 'DB')
GROUP BY pos
```

**Expected results:**

- DL: >95% mapped
- LB: >95% mapped
- DB: >95% mapped

## Alternatives Considered

### Alternative 1: Standardize FantasySharks to "First Last" (Upstream)

**Pros:**

- Solves problem at source
- No normalization logic needed

**Cons:**

- FantasySharks is external (we don't control their format)
- FFanalytics R package scrapes their website (would need to modify package)
- Fragile (could break with site redesign)

**Verdict:** Rejected as infeasible. We must handle data as provided.

### Alternative 2: Store Both Name Formats in Crosswalk Only (No R Script Logic)

**Pros:**

- Simpler R script (just add `name_last_first` to join columns)
- All logic in one place (crosswalk generation)

**Cons:**

- Crosswalk regeneration becomes critical path (can't fix without regenerating seed)
- Other sources with "Last, First" format would need crosswalk updates
- Less flexible than runtime normalization

**Verdict:** Rejected in favor of hybrid approach (R script normalization + crosswalk column for redundancy).

### Alternative 3: Fuzzy Matching with Levenshtein Distance

**Pros:**

- Handles typos, misspellings, format variations automatically
- More robust to edge cases

**Cons:**

- Much slower (O(n²) comparisons)
- Can produce false positives (wrong players matched)
- Harder to debug and validate

**Verdict:** Rejected as unnecessary. Name format is predictable; exact matching with normalization is sufficient and faster.

### Alternative 4: Manual Name Alias Seed

**Approach:** Create `dim_name_alias` seed mapping "Parsons, Micah" → "Micah Parsons"

**Pros:**

- Explicit, auditable mappings
- Can handle truly exceptional cases

**Cons:**

- Requires manual maintenance for 9,734 players
- Scales poorly (new players require manual additions)
- Duplicates logic already encodable as a rule

**Verdict:** Rejected as unmaintainable. Algorithmic normalization is superior for large datasets.

## References

- [Phase 1 IDP Investigation](../findings/PHASE_1_IDP_DATA_FLOW_INVESTIGATION.md)
- [ADR-011](./ADR-011-sequential-surrogate-player-id.md) (Player ID architecture)
- [scripts/R/ffanalytics_run.R](../../scripts/R/ffanalytics_run.R) (Implementation)
- [dim_position_translation.csv](../../dbt/ff_analytics/seeds/dim_position_translation.csv)
- [generate_dim_player_id_xref.py](../../scripts/seeds/generate_dim_player_id_xref.py)

## Revision History

- **2025-10-29:** Initial decision (v1.0) - Name and position normalization for IDP projections
