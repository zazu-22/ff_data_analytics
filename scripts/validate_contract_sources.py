#!/usr/bin/env python3
"""Validate that transaction-derived contracts match roster snapshot contracts.

Compares:
- mart_contract_snapshot_current (from dim_player_contract_history via fact_league_transactions)
- mart_contract_snapshot_history (from stg_sheets__contracts_active via GM roster tabs)

Expected: High match rate (>95%) indicates transaction log accurately reconstructs contracts.

Usage:
    python scripts/validate_contract_sources.py
    # or
    uv run python scripts/validate_contract_sources.py
"""

from pathlib import Path

import duckdb

# Get repo root (parent of scripts directory)
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
DB_PATH = REPO_ROOT / "dbt/ff_analytics/target/dev.duckdb"


def validate_contracts():
    """Run contract validation queries and print results."""
    if not Path(DB_PATH).exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("   Run 'make dbt-run' first to build models.")
        return 1

    print("=" * 80)
    print("CONTRACT SOURCE VALIDATION")
    print("=" * 80)
    print()

    conn = duckdb.connect(DB_PATH, read_only=True)

    # Step 1: Latest snapshot date
    print("📅 Latest Snapshot Date:")
    result = conn.execute("""
        SELECT max(snapshot_date) as latest_date
        FROM main.mart_contract_snapshot_history
    """).fetchone()
    latest_snapshot = result[0] if result is not None else None
    print(f"   {latest_snapshot}")
    print()

    # Step 2: Record counts
    print("📊 Record Counts:")
    results = conn.execute("""
        SELECT
          'Transaction-derived (current)' as source,
          count(*) as contract_years,
          count(distinct player_id) as players,
          count(distinct franchise_id) as franchises
        FROM main.mart_contract_snapshot_current

        UNION ALL

        SELECT
          'Roster snapshot (latest)' as source,
          count(*) as contract_years,
          count(distinct player_id) as players,
          count(distinct franchise_id) as franchises
        FROM main.mart_contract_snapshot_history
        WHERE snapshot_date = (SELECT max(snapshot_date) FROM main.mart_contract_snapshot_history)
    """).fetchall()

    for row in results:
        print(
            f"   {row[0]:35s} {row[1]:5d} contract-years, "
            f"{row[2]:3d} players, {row[3]:2d} franchises"
        )
    print()

    # Step 3: Match statistics
    print("🔍 Match Analysis:")

    # Get latest snapshot date first
    row = conn.execute("""
        SELECT max(snapshot_date) FROM main.mart_contract_snapshot_history
    """).fetchone()
    latest_date = row[0] if row is not None else None

    # Create temp tables to avoid subquery issues
    conn.execute(
        """
        CREATE OR REPLACE TEMP TABLE txn_current AS
        SELECT player_id, obligation_year, annual_cap_hit
        FROM main.mart_contract_snapshot_current;

        CREATE OR REPLACE TEMP TABLE snap_current AS
        SELECT player_id, obligation_year, cap_hit
        FROM main.mart_contract_snapshot_history
        WHERE snapshot_date = ?;
    """,
        [latest_date],
    )

    results = conn.execute("""
        WITH comparison AS (
          SELECT
            CASE
              WHEN t.player_id IS NOT NULL AND s.player_id IS NOT NULL THEN 'both'
              WHEN t.player_id IS NOT NULL THEN 'txn_only'
              ELSE 'snapshot_only'
            END as status,
            t.annual_cap_hit = s.cap_hit as amounts_match
          FROM txn_current t
          FULL OUTER JOIN snap_current s
            ON t.player_id = s.player_id
            AND t.obligation_year = s.obligation_year
        )
        SELECT
          count(*) as total,
          count(case when status = 'both' then 1 end) as matched,
          count(case when status = 'txn_only' then 1 end) as txn_only,
          count(case when status = 'snapshot_only' then 1 end) as snap_only,
          count(case when status = 'both' and amounts_match then 1 end) as exact_matches,
          count(case when status = 'both' and not amounts_match then 1 end) as amt_mismatches
        FROM comparison
    """).fetchone()

    # Defensive: handle missing row (None) to avoid TypeError on unpacking
    if results is None:
        print("❌ Could not retrieve match statistics. Table may be missing or empty.")
        return 1

    total, matched, txn_only, snap_only, exact, mismatches = results

    # DuckDB may return None for aggregates if table is empty; coalesce to zero for math/printing
    total = total or 0
    matched = matched or 0
    txn_only = txn_only or 0
    snap_only = snap_only or 0
    exact = exact or 0
    mismatches = mismatches or 0

    match_pct = 100.0 * matched / total if total > 0 else 0
    exact_pct = 100.0 * exact / matched if matched > 0 else 0

    print(f"   Total contract-years:        {total:5d}")
    print(f"   Matched (both sources):      {matched:5d}  ({match_pct:.1f}%)")
    print(f"   Transaction-only:            {txn_only:5d}")
    print(f"   Snapshot-only:               {snap_only:5d}")
    print()
    print("   Of matched records:")
    print(f"     Exact amount match:        {exact:5d}  ({exact_pct:.1f}%)")
    print(f"     Amount mismatch:           {mismatches:5d}")
    print()

    # Step 4: Show discrepancies
    if mismatches > 0 or txn_only > 0 or snap_only > 0:
        print("⚠️  Top Discrepancies:")

        # Create temp tables with full details
        conn.execute(
            """
            CREATE OR REPLACE TEMP TABLE txn_detail AS
            SELECT player_id, player_name, franchise_name, obligation_year, annual_cap_hit
            FROM main.mart_contract_snapshot_current;

            CREATE OR REPLACE TEMP TABLE snap_detail AS
            SELECT player_id, player_name, franchise_name, obligation_year, cap_hit
            FROM main.mart_contract_snapshot_history
            WHERE snapshot_date = ?;
        """,
            [latest_date],
        )

        discrepancies = conn.execute("""
            SELECT
              COALESCE(t.player_name, s.player_name) as player,
              COALESCE(t.franchise_name, s.franchise_name) as franchise,
              COALESCE(t.obligation_year, s.obligation_year) as year,
              t.annual_cap_hit as txn_amt,
              s.cap_hit as snap_amt,
              CASE
                WHEN t.player_id IS NULL THEN 'snapshot_only'
                WHEN s.player_id IS NULL THEN 'txn_only'
                ELSE 'amount_diff'
              END as issue
            FROM txn_detail t
            FULL OUTER JOIN snap_detail s
              ON t.player_id = s.player_id
              AND t.obligation_year = s.obligation_year
            WHERE t.annual_cap_hit IS DISTINCT FROM s.cap_hit
            ORDER BY abs(COALESCE(t.annual_cap_hit, 0) - COALESCE(s.cap_hit, 0)) DESC
            LIMIT 15
        """).fetchall()

        for row in discrepancies:
            player, franchise, year, txn, snap, issue = row
            txn_str = f"${txn}M" if txn else "---"
            snap_str = f"${snap}M" if snap else "---"
            print(
                f"   {player:25s} {franchise:15s} {year} | "
                f"TXN: {txn_str:6s} SNAP: {snap_str:6s} ({issue})"
            )
    else:
        print("✅ Perfect match! All contracts agree between sources.")

    print()
    print("=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)

    # Summary assessment
    if match_pct >= 95 and exact_pct >= 90:
        print("✅ EXCELLENT: Transaction log accurately reconstructs contracts")
    elif match_pct >= 85:
        print("⚠️  GOOD: Minor discrepancies - review details above")
    else:
        print("❌ POOR: Significant discrepancies - investigate transaction log gaps")

    conn.close()
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(validate_contracts())
