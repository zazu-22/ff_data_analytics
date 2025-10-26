/*
Dead Cap Reconciliation Analysis

Purpose: Compare three sources of 2025 salary cap obligations to identify gaps:
1. Active contracts (from roster) - Players currently on teams
2. Transaction-derived obligations (from mart) - Contract history view
3. Dead cap obligations (from cut contracts) - Commissioner's source of truth

Expected Finding: mart_contract_snapshot_current ($2,270) includes BOTH:
- Active roster contracts ($2,236)
- Some dead cap from past cuts (portion of $455 total)

Key Question: Where is the missing ~$312 in dead cap obligations?

Run with:
  dbt compile --select reconcile_dead_cap_vs_active_contracts
  EXTERNAL_ROOT="$PWD/data/raw" duckdb dbt/ff_analytics/target/dev.duckdb < target/compiled/ff_analytics/analyses/reconcile_dead_cap_vs_active_contracts.sql
*/

-- ====================================================================================
-- Source 1: Active Roster Contracts (what's on rosters now)
-- ====================================================================================
WITH active_roster AS (
  SELECT
    franchise_id,
    franchise_name,
    player_id,
    player_name,
    obligation_year,
    cap_hit as annual_cap_hit
  FROM {{ ref('stg_sheets__contracts_active') }}
  WHERE obligation_year = 2025
    AND snapshot_date = (SELECT MAX(snapshot_date) FROM {{ ref('stg_sheets__contracts_active') }})
),

-- ====================================================================================
-- Source 2: Transaction-Derived Contract Obligations (mart view)
-- ====================================================================================
transaction_derived AS (
  SELECT
    franchise_id,
    franchise_name,
    player_id,
    player_name,
    obligation_year,
    annual_cap_hit
  FROM {{ ref('mart_contract_snapshot_current') }}
  WHERE obligation_year = 2025
),

-- ====================================================================================
-- Source 3: Dead Cap Obligations (Commissioner's source of truth)
-- ====================================================================================
dead_cap_obligations AS (
  SELECT
    franchise_id,
    franchise_name,
    player_id,
    player_name,
    obligation_year,
    dead_cap_amount
  FROM {{ ref('stg_sheets__contracts_cut') }}
  WHERE obligation_year = 2025
    AND snapshot_date = (SELECT MAX(snapshot_date) FROM {{ ref('stg_sheets__contracts_cut') }})
),

-- ====================================================================================
-- Analysis 1: High-Level Totals
-- ====================================================================================
summary AS (
  SELECT 'Active Roster' as source, COUNT(DISTINCT player_id) as players, SUM(annual_cap_hit) as total_cap
  FROM active_roster
  UNION ALL
  SELECT 'Transaction-Derived Mart', COUNT(DISTINCT player_id), SUM(annual_cap_hit)
  FROM transaction_derived
  UNION ALL
  SELECT 'Dead Cap Obligations', COUNT(DISTINCT player_id), SUM(dead_cap_amount)
  FROM dead_cap_obligations
),

-- ====================================================================================
-- Analysis 2: Players in Mart but NOT on Active Roster (the $34 gap)
-- ====================================================================================
mart_not_roster AS (
  SELECT
    td.franchise_name,
    td.player_name,
    td.annual_cap_hit as mart_cap_hit,
    dc.dead_cap_amount,
    CASE
      WHEN dc.player_id IS NOT NULL THEN 'Has Dead Cap Entry'
      ELSE 'No Dead Cap Entry (Waiver Release?)'
    END as dead_cap_status
  FROM transaction_derived td
  LEFT JOIN active_roster ar
    ON td.player_id = ar.player_id
  LEFT JOIN dead_cap_obligations dc
    ON td.player_id = dc.player_id
  WHERE ar.player_id IS NULL  -- Not on active roster
  ORDER BY td.annual_cap_hit DESC
),

-- ====================================================================================
-- Analysis 3: Dead Cap in Commissioner CSV but NOT in Mart (the $312 missing)
-- ====================================================================================
dead_cap_not_mart AS (
  SELECT
    dc.franchise_name,
    dc.player_name,
    dc.dead_cap_amount,
    td.annual_cap_hit as mart_cap_hit
  FROM dead_cap_obligations dc
  LEFT JOIN transaction_derived td
    ON dc.player_id = td.player_id
  WHERE td.player_id IS NULL  -- Not in transaction-derived mart
  ORDER BY dc.dead_cap_amount DESC
),

-- ====================================================================================
-- Analysis 4: Players in BOTH Mart and Dead Cap (overlap validation)
-- ====================================================================================
overlap AS (
  SELECT
    td.franchise_name,
    td.player_name,
    td.annual_cap_hit as mart_amount,
    dc.dead_cap_amount,
    td.annual_cap_hit - dc.dead_cap_amount as difference
  FROM transaction_derived td
  INNER JOIN dead_cap_obligations dc
    ON td.player_id = dc.player_id
  ORDER BY ABS(td.annual_cap_hit - dc.dead_cap_amount) DESC
)

-- ====================================================================================
-- Output Results
-- ====================================================================================
SELECT '=== SUMMARY: Total Cap Obligations by Source ===' as section,
  CAST(NULL AS VARCHAR) as detail,
  CAST(NULL AS DOUBLE) as amount,
  CAST(NULL AS VARCHAR) as notes

UNION ALL SELECT '', '', NULL, ''
UNION ALL

SELECT '', source || ': ' || players || ' players', total_cap, ''
FROM summary

UNION ALL SELECT '', '', NULL, ''
UNION ALL SELECT '=== GAP ANALYSIS ===' as section, '', NULL, ''
UNION ALL

SELECT '',
  'Gap: Mart - Roster',
  (SELECT total_cap FROM summary WHERE source = 'Transaction-Derived Mart') -
  (SELECT total_cap FROM summary WHERE source = 'Active Roster'),
  'Players in mart but not on roster'

UNION ALL

SELECT '',
  'Gap: Dead Cap - Mart',
  (SELECT total_cap FROM summary WHERE source = 'Dead Cap Obligations') -
  (SELECT total_cap FROM summary WHERE source = 'Transaction-Derived Mart'),
  'Dead cap obligations not captured in mart'

UNION ALL SELECT '', '', NULL, ''
UNION ALL SELECT '=== Players in Mart but NOT on Roster (explains $34 gap) ===' as section, '', NULL, ''
UNION ALL

SELECT '',
  franchise_name || ': ' || player_name,
  mart_cap_hit,
  dead_cap_status
FROM mart_not_roster
LIMIT 25

UNION ALL SELECT '', '', NULL, ''
UNION ALL SELECT '=== Dead Cap NOT in Mart (explains $312 missing) ===' as section, '', NULL, ''
UNION ALL

SELECT '',
  franchise_name || ': ' || player_name,
  dead_cap_amount,
  'Missing from transaction-derived mart'
FROM dead_cap_not_mart
LIMIT 25

UNION ALL SELECT '', '', NULL, ''
UNION ALL SELECT '=== Players in BOTH Mart and Dead Cap (overlap) ===' as section, '', NULL, ''
UNION ALL

SELECT '',
  franchise_name || ': ' || player_name,
  mart_amount,
  'Dead cap: $' || dead_cap_amount || ' | Diff: $' || difference
FROM overlap
LIMIT 10;
