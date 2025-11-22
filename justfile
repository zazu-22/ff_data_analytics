# justfile for ff_data_analytics
# Task runner replacing Makefile with cleaner syntax
# Run `just --list` or `just help` to see available commands

set dotenv-load := true
set shell := ["bash", "-uc"]

# ============================================================================
# VARIABLES & REUSABLE COMPONENTS
# ============================================================================

# Common DBT paths - using justfile_directory() for absolute paths
project_root := justfile_directory()
dbt_project_dir := "dbt/ff_data_transform"
dbt_project_path := project_root + "/" + dbt_project_dir
dbt_target_dir := dbt_project_path + "/target"
external_root := project_root + "/data/raw"
dbt_db_path := dbt_target_dir + "/dev.duckdb"

# Helper function to run dbt commands with standard environment
_dbt_run command *args:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p "{{dbt_target_dir}}"
    cd "{{project_root}}"

    cleanup_seed_link() {
        if [[ -n "${SEED_LINK_CREATED:-}" ]]; then
            rm -f seeds
        fi
    }
    trap cleanup_seed_link EXIT

    if [[ ! -e seeds ]]; then
        ln -s "{{dbt_project_dir}}/seeds" seeds
        SEED_LINK_CREATED=1
    fi

    uv run env \
        EXTERNAL_ROOT="{{external_root}}" \
        DBT_DUCKDB_PATH="{{dbt_db_path}}" \
        dbt {{command}} --project-dir {{dbt_project_dir}} --profiles-dir {{dbt_project_dir}} {{args}}

# ============================================================================
# HELP & DEFAULT
# ============================================================================

# Default recipe - show help
default: help

# Show all available commands organized by category
help:
    @echo "═══════════════════════════════════════════════════════════════"
    @echo "  ff_data_analytics - Available Commands"
    @echo "═══════════════════════════════════════════════════════════════"
    @echo ""
    @echo "🚀 QUICK START WORKFLOWS:"
    @echo "  ingest-quick         Fast ingestion (nflverse → xref → sheets, sleeper, ktc)"
    @echo "  ingest-full          Full ingestion (includes ffanalytics - 15-20 min)"
    @echo "  quality-all          Run all code quality checks (Python + SQL + dbt)"
    @echo "  quality-python       Run all Python quality checks"
    @echo "  quality-sql          Run all SQL quality checks"
    @echo ""
    @echo "📥 DATA INGESTION:"
    @echo "  ingest-nflverse      Ingest NFLverse datasets (weekly, snaps, opportunity, playerids)"
    @echo "  ingest-sheets        Ingest Commissioner Google Sheets"
    @echo "  ingest-sleeper       Ingest Sleeper player database"
    @echo "  ingest-ktc           Ingest KeepTradeCut dynasty values (1QB)"
    @echo "  ingest-ffanalytics   Ingest FFanalytics projections (slow - 15-20 min)"
    @echo ""
    @echo "🔄 DBT WORKFLOWS:"
    @echo "  dbt-xref             Build dim_player_id_xref (required for ingestion)"
    @echo "  dbt-deps [args]      Install dbt package dependencies"
    @echo "  dbt-seed [args]      Seed dbt sources"
    @echo "  dbt-run [args]       Run dbt models"
    @echo "  dbt-test [args]      Run dbt tests"
    @echo "  dbt-compile          Compile dbt models (syntax validation)"
    @echo "  dbt-lint             Check dbt best practices (dbt-opiner)"
    @echo ""
    @echo "✅ PYTHON QUALITY:"
    @echo "  python-lint          Check Python/YAML/Markdown code (ruff, yamllint, mdformat)"
    @echo "  python-fix           Auto-fix Python/YAML/Markdown issues"
    @echo "  python-typecheck     Run type checks (pyrefly)"
    @echo "  python-typeinfer <path>  Auto-add type annotations to file/directory"
    @echo ""
    @echo "✅ SQL QUALITY:"
    @echo "  sql-lint             Check SQL formatting and linting (sqlfmt, sqlfluff)"
    @echo "  sql-fix              Auto-fix SQL formatting and linting issues"
    @echo ""
    @echo "🎯 OTHER:"
    @echo "  pre-commit           Run all pre-commit hooks"
    @echo ""
    @echo "═══════════════════════════════════════════════════════════════"

# ============================================================================
# QUICK START WORKFLOWS
# ============================================================================

# Fast ingestion workflow (excludes FFanalytics)
ingest-quick:
    #!/usr/bin/env bash
    set -euo pipefail
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Fast Ingestion Workflow"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "[1/5] Ingesting NFLverse data..."
    just ingest-nflverse
    echo ""
    echo "[2/5] Building player ID crosswalk..."
    just dbt-xref
    echo ""
    echo "[3/5] Ingesting Commissioner sheets..."
    just ingest-sheets
    echo ""
    echo "[4/5] Ingesting Sleeper data..."
    just ingest-sleeper
    echo ""
    echo "[5/5] Ingesting KTC dynasty values..."
    just ingest-ktc
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  ✅ Fast ingestion complete!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Note: Run 'just ingest-ffanalytics' separately if needed (15-20 min)"

# Full ingestion workflow (includes FFanalytics - SLOW!)
ingest-full:
    #!/usr/bin/env bash
    set -euo pipefail
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Full Ingestion Workflow (includes FFanalytics - SLOW!)"
    echo "═══════════════════════════════════════════════════════════════"
    just ingest-quick
    echo ""
    echo "[6/6] Ingesting FFanalytics projections (⚠️  15-20 min)..."
    just ingest-ffanalytics
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  ✅ Full ingestion complete!"
    echo "═══════════════════════════════════════════════════════════════"

# Run all code quality checks (Python + SQL + dbt)
quality-all:
    @echo "Running all code quality checks..."
    @echo ""
    just quality-python
    @echo ""
    just quality-sql
    @echo ""
    @echo "Checking dbt compilation and best practices..."
    just dbt-compile
    just dbt-lint
    @echo ""
    @echo "✅ All quality checks complete!"

# Run all Python quality checks
quality-python:
    @echo "Running Python quality checks..."
    just python-lint
    just python-typecheck

# Run all SQL quality checks
quality-sql:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=========================================="
    echo "SQL QUALITY CHECKS"
    echo "=========================================="
    echo ""
    echo "[1/2] Checking SQL formatting and linting..."
    just sql-lint
    echo ""
    echo "[2/2] Auto-fixing SQL issues (if needed)..."
    echo "(Run 'just sql-fix' manually if fixes are needed)"
    echo ""
    echo "=========================================="
    echo "✅ SQL QUALITY CHECKS COMPLETE"
    echo "=========================================="

# ============================================================================
# DATA INGESTION
# ============================================================================

# Ingest NFLverse datasets (weekly, snaps, opportunity, playerids)
ingest-nflverse:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Ingesting NFLverse datasets..."
    echo "→ ff_playerids (player ID crosswalk)"
    uv run python -c "from src.ingest.nflverse.shim import load_nflverse; load_nflverse('ff_playerids')"
    echo "→ weekly player stats (2025 season)"
    uv run python -c "from src.ingest.nflverse.shim import load_nflverse; load_nflverse('weekly', seasons=[2025])"
    echo "→ snap counts (2025 season)"
    uv run python -c "from src.ingest.nflverse.shim import load_nflverse; load_nflverse('snap_counts', seasons=[2025])"
    echo "→ fantasy opportunity (2025 season)"
    uv run python -c "from src.ingest.nflverse.shim import load_nflverse; load_nflverse('ff_opportunity', seasons=[2025])"
    echo "✅ NFLverse ingestion complete"

# Ingest Commissioner Google Sheets
ingest-sheets:
    @echo "Ingesting Commissioner Google Sheets..."
    @uv run python scripts/ingest/ingest_commissioner_sheet.py
    @echo "✅ Sheets ingestion complete"

# Ingest Sleeper player database
ingest-sleeper:
    @echo "Ingesting Sleeper player database..."
    @uv run python -m src.ingest.sleeper.loader players
    @echo "✅ Sleeper ingestion complete"

# Ingest KeepTradeCut dynasty values (1QB)
ingest-ktc:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Ingesting KeepTradeCut dynasty values..."
    echo "→ players"
    uv run python -c "from ingest.ktc.registry import load_players; load_players()"
    echo "→ picks"
    uv run python -c "from ingest.ktc.registry import load_picks; load_picks()"
    echo "✅ KTC ingestion complete"

# Ingest FFanalytics projections (rest-of-season, slow - 15-20 min)
ingest-ffanalytics:
    @echo "Ingesting FFanalytics projections (this takes 15-20 minutes)..."
    @uv run python -c "from src.ingest.ffanalytics.loader import load_projections_ros; load_projections_ros()"
    @echo "✅ FFanalytics ingestion complete"

# ============================================================================
# PREFECT FLOWS
# ============================================================================

# Run copy league sheet flow (Commissioner sheet → working copy)
flow-copy-sheet:
    @echo "Running copy_league_sheet_flow..."
    @uv run python src/flows/copy_league_sheet_flow.py
    @echo "✅ Sheet copy flow complete"

# ============================================================================
# DBT WORKFLOWS
# ============================================================================

# Build dim_player_id_xref (required for ingestion)
dbt-xref:
    @echo "Building dim_player_id_xref..."
    @just _dbt_run run --select dim_player_id_xref
    @echo "✅ Player ID crosswalk built"

# Install dbt package dependencies
dbt-deps *ARGS:
    @echo "Installing dbt package dependencies..."
    @just _dbt_run deps {{ARGS}}

# Seed dbt sources
dbt-seed *ARGS:
    @echo "Seeding dbt sources..."
    @just _dbt_run seed {{ARGS}}

# Run dbt models
dbt-run *ARGS:
    @echo "Running dbt models..."
    @just _dbt_run run {{ARGS}}

# Run dbt tests
dbt-test *ARGS:
    @echo "Running dbt tests..."
    @just _dbt_run test {{ARGS}}

# Compile dbt models (syntax validation)
dbt-compile:
    @echo "Compiling dbt models (syntax validation)..."
    @just _dbt_run compile
    @echo "✅ dbt compilation successful"

# Check dbt best practices (dbt-opiner)
dbt-lint:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Checking dbt best practices..."
    echo "→ Installing dbt dependencies..."
    cd {{dbt_project_dir}} && \
        EXTERNAL_ROOT="$(pwd)/../../data/raw" \
        DBT_DUCKDB_PATH="$(pwd)/target/dev.duckdb" \
        uv run dbt deps --project-dir . --profiles-dir . || true
    echo "→ Running dbt-opiner..."
    cd {{dbt_project_dir}} && \
        EXTERNAL_ROOT="$(pwd)/../../data/raw" \
        DBT_DUCKDB_PATH="$(pwd)/target/dev.duckdb" \
        uv run dbt-opiner lint --all-files --force-compile
    echo "✅ dbt-opiner check complete"

# ============================================================================
# PYTHON QUALITY
# ============================================================================

# Check Python/YAML/Markdown code (ruff, yamllint, mdformat, lintr)
python-lint:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=========================================="
    echo "PYTHON/YAML/MARKDOWN LINTING"
    echo "=========================================="
    echo ""
    echo "[1/4] ruff check..."
    uv run ruff check . && echo "  ✓ ruff OK" || echo "  ✗ ruff found issues"
    echo ""
    echo "[2/4] yamllint..."
    uv run yamllint --list-files . && echo "  ✓ yamllint OK" || echo "  ✗ yamllint found issues"
    echo ""
    echo "[3/4] mdformat check..."
    uv run mdformat --check . && echo "  ✓ mdformat OK" || echo "  ✗ mdformat found issues"
    echo ""
    echo "[4/4] lintr (R)..."
    Rscript -e "lintr::lint_dir('scripts/R')" && echo "  ✓ lintr OK" || echo "  ✗ lintr found issues"
    echo ""
    echo "=========================================="

# Auto-fix Python/YAML/Markdown issues
python-fix:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=========================================="
    echo "PYTHON/YAML/MARKDOWN AUTO-FIX"
    echo "=========================================="
    echo ""
    echo "[1/4] ruff format..."
    uv run ruff format . && echo "  ✓ ruff format complete"
    echo ""
    echo "[2/4] ruff fix..."
    uv run ruff check . --fix && echo "  ✓ ruff fix complete"
    echo ""
    echo "[3/4] mdformat..."
    uv run mdformat . && echo "  ✓ mdformat complete"
    echo ""
    echo "[4/4] styler (R)..."
    Rscript -e "styler::style_dir('scripts/R')" && echo "  ✓ styler complete"
    echo ""
    echo "=========================================="

# Run type checks (pyrefly)
python-typecheck:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=========================================="
    echo "TYPE CHECKING"
    echo "=========================================="
    echo ""
    uv run pyrefly check && echo "  ✓ Type checks passed" || echo "  ✗ Type errors found"
    echo ""
    echo "=========================================="

# Auto-add type annotations to file or directory
python-typeinfer PATH:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Running type inference on {{PATH}}..."
    uv run pyrefly infer {{PATH}} && echo "✅ Type inference complete" || echo "❌ Type inference failed"

# ============================================================================
# SQL QUALITY
# ============================================================================

# Check SQL formatting and linting (sqlfmt, sqlfluff)
sql-lint:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=========================================="
    echo "SQL LINTING"
    echo "=========================================="
    echo ""
    echo "[1/2] Checking SQL formatting (sqlfmt)..."
    uv run sqlfmt --check {{dbt_project_dir}}/models/**/*.sql && echo "  ✓ sqlfmt OK" || echo "  ✗ sqlfmt found issues (run 'just sql-fix' to fix)"
    echo ""
    echo "[2/2] Linting SQL (sqlfluff)..."
    uv run sqlfluff lint {{dbt_project_dir}}/models/ && echo "  ✓ sqlfluff OK" || echo "  ✗ sqlfluff found issues (run 'just sql-fix' to fix)"
    echo ""
    echo "=========================================="

# Auto-fix SQL formatting and linting issues
sql-fix:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=========================================="
    echo "SQL AUTO-FIX"
    echo "=========================================="
    echo ""
    echo "[1/2] Formatting SQL (sqlfmt)..."
    uv run sqlfmt {{dbt_project_dir}}/models/**/*.sql && echo "  ✓ sqlfmt formatting complete"
    echo ""
    echo "[2/2] Fixing SQL linting issues (sqlfluff)..."
    uv run sqlfluff fix {{dbt_project_dir}}/models/ && echo "  ✓ sqlfluff fixes complete"
    echo ""
    echo "=========================================="
    echo "✅ SQL AUTO-FIX COMPLETE"
    echo "=========================================="

# ============================================================================
# OTHER
# ============================================================================

# Run all pre-commit hooks
pre-commit:
    @echo "Running pre-commit hooks..."
    @uv run pre-commit run --all-files && echo "✅ Pre-commit passed" || echo "❌ Pre-commit failed"
