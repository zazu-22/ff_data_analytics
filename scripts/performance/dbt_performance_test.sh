#!/bin/bash
# dbt Performance Testing Script
# Measures transformation times for key models

set -e

PROJECT_ROOT="/Users/jason/code/ff_analytics"
cd "$PROJECT_ROOT"

export EXTERNAL_ROOT="$(pwd)/data/raw"
export DBT_DUCKDB_PATH="$(pwd)/dbt/ff_data_transform/target/dev.duckdb"

echo "================================================================================"
echo "dbt Performance Testing"
echo "================================================================================"

# Test 1: Full dbt run
echo ""
echo "[1/5] Testing full dbt run..."
START_TIME=$(date +%s)
uv run dbt run --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform --quiet
END_TIME=$(date +%s)
FULL_RUN_TIME=$((END_TIME - START_TIME))
echo "  ✓ Full dbt run: ${FULL_RUN_TIME}s"

# Test 2: Staging model (large unpivot)
echo ""
echo "[2/5] Testing stg_nflverse__player_stats (1,568 LOC unpivot)..."
START_TIME=$(date +%s)
uv run dbt run --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform --select stg_nflverse__player_stats --quiet
END_TIME=$(date +%s)
STAGING_TIME=$((END_TIME - START_TIME))
echo "  ✓ Staging model: ${STAGING_TIME}s"

# Test 3: Fact table build
echo ""
echo "[3/5] Testing fct_player_stats..."
START_TIME=$(date +%s)
uv run dbt run --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform --select fct_player_stats --quiet
END_TIME=$(date +%s)
FACT_TIME=$((END_TIME - START_TIME))
echo "  ✓ Fact table: ${FACT_TIME}s"

# Test 4: Complex mart
echo ""
echo "[4/5] Testing mrt_fasa_targets (1,017 LOC mart)..."
START_TIME=$(date +%s)
uv run dbt run --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform --select mrt_fasa_targets --quiet
END_TIME=$(date +%s)
MART_TIME=$((END_TIME - START_TIME))
echo "  ✓ Mart model: ${MART_TIME}s"

# Test 5: dbt test
echo ""
echo "[5/5] Testing dbt test suite..."
START_TIME=$(date +%s)
uv run dbt test --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform --quiet
END_TIME=$(date +%s)
TEST_TIME=$((END_TIME - START_TIME))
echo "  ✓ Test suite: ${TEST_TIME}s"

# Summary
echo ""
echo "================================================================================"
echo "Summary:"
echo "  Full dbt run:     ${FULL_RUN_TIME}s"
echo "  Staging unpivot:  ${STAGING_TIME}s"
echo "  Fact table:       ${FACT_TIME}s"
echo "  Complex mart:     ${MART_TIME}s"
echo "  Test suite:       ${TEST_TIME}s"
echo "================================================================================"
