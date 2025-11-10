## Convenience tasks for local iteration

.PHONY: help samples-nflverse dbt-run dbt-test dbt-seed quickstart-local sqlfix sqlfmt sqlfmt-check dbt-compile-check dbt-opiner-check sql-all validate-franchise-mapping ingest-ffanalytics ingest-ktc dbt-xref ingest-with-xref ingest-all ingest-nflverse ingest-sheets ingest-sleeper-players

help:
	@echo "Available targets:"
	@echo "  ingest-nflverse      Ingest all NFLverse datasets (weekly, snap_counts, ff_opportunity, ff_playerids)"
	@echo "  ingest-sheets        Ingest league sheets locally"
	@echo "  ingest-sleeper-players  Ingest Sleeper player database (for crosswalk validation)"
	@echo "  ingest-ffanalytics   Ingest FFanalytics projections (rest-of-season)"
	@echo "  ingest-ktc           Ingest KeepTradeCut dynasty market values (1QB)"
	@echo "  dbt-xref             Build dim_player_id_xref for ingestion dependencies"
	@echo "  ingest-with-xref     Fast ingestion workflow (nflverse → xref → sheets, sleeper, ktc)"
	@echo "  ingest-all           Full ingestion workflow (includes ffanalytics - slow!)"
	@echo "  dbt-deps             Install dbt package dependencies"
	@echo "  dbt-seed             Seed dbt sources (use 'make dbt-seed ARGS=<dbt seed args>')"
	@echo "  dbt-run              Run dbt models locally (DuckDB) (use 'make dbt-run ARGS=<dbt run args>')"
	@echo "  dbt-test             Run dbt tests locally (use 'make dbt-test ARGS=<dbt test args>')"
	@echo "  lintcheck            Run linter checks	"
	@echo "  lintfix              Run linter auto-fixes"
	@echo "  typecheck            Run type checks"
	@echo "  typeinfer            Automatically add type annotations; use 'make typeinfer ARGS=<file or directory>'"
	@echo "  sqlfmt               Format SQL files with sqlfmt"
	@echo "  sqlfmt-check         Check SQL formatting without modifying files"
	@echo "  sqlcheck             Run sqlfluff checks on dbt models (selective)"
	@echo "  sqlfix               Run sqlfluff auto-fixes on dbt models"
	@echo "  dbt-compile-check    Run dbt compile for SQL syntax validation"
	@echo "  dbt-opiner-check     Run dbt-opiner for dbt best practices"
	@echo "  sql-all              Run all SQL quality checks (format + lint + compile + opiner)"
	@echo "  pre-commit           Run pre-commit hooks"

ingest-nflverse:
	@echo "Ingesting all NFLverse datasets..."
	@echo "→ Ingesting ff_playerids (player ID crosswalk)"
	uv run python -c "from src.ingest.nflverse.shim import load_nflverse; load_nflverse('ff_playerids')"
	@echo "→ Ingesting weekly player stats (2025 season)"
	uv run python -c "from src.ingest.nflverse.shim import load_nflverse; load_nflverse('weekly', seasons=[2025])"
	@echo "→ Ingesting snap counts (2025 season)"
	uv run python -c "from src.ingest.nflverse.shim import load_nflverse; load_nflverse('snap_counts', seasons=[2025])"
	@echo "→ Ingesting fantasy opportunity (2025 season)"
	uv run python -c "from src.ingest.nflverse.shim import load_nflverse; load_nflverse('ff_opportunity', seasons=[2025])"
	@echo "✅ NFLverse ingestion complete"

ingest-sheets:
	@echo "Ingesting league sheets locally"
	uv run python scripts/ingest/ingest_commissioner_sheet.py

ingest-sleeper-players:
	@echo "Ingesting Sleeper player database"
	uv run python -m src.ingest.sleeper.loader players

ingest-ffanalytics:
	@echo "Ingesting FFanalytics projections (rest-of-season)"
	uv run python -c "from src.ingest.ffanalytics.loader import load_projections_ros; load_projections_ros()"

ingest-ktc:
	@echo "Ingesting KeepTradeCut dynasty market values (1QB)"
	@echo "→ Ingesting players"
	uv run python -c "from ingest.ktc.registry import load_players; load_players()"
	@echo "→ Ingesting picks"
	uv run python -c "from ingest.ktc.registry import load_picks; load_picks()"
	@echo "✅ KTC ingestion complete"

dbt-xref:
	@echo "Building dim_player_id_xref"
	@mkdir -p dbt/ff_data_transform/target
	uv run env \
		EXTERNAL_ROOT="$$(pwd)/data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/dbt/ff_data_transform/target/dev.duckdb" \
		dbt run --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform --select dim_player_id_xref

ingest-with-xref:
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  Fast Ingestion Workflow (excludes FFanalytics)"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "[1/5] Ingesting NFLverse data (provides player IDs)..."
	@echo "───────────────────────────────────────────────────────────────"
	$(MAKE) ingest-nflverse
	@echo ""
	@echo "[2/5] Building dim_player_id_xref (player name crosswalk)..."
	@echo "───────────────────────────────────────────────────────────────"
	$(MAKE) dbt-xref
	@echo ""
	@echo "[3/5] Ingesting Commissioner sheets (requires xref)..."
	@echo "───────────────────────────────────────────────────────────────"
	$(MAKE) ingest-sheets
	@echo ""
	@echo "[4/5] Ingesting Sleeper data (requires xref)..."
	@echo "───────────────────────────────────────────────────────────────"
	$(MAKE) ingest-sleeper-players
	@echo ""
	@echo "[5/5] Ingesting KTC dynasty values (requires xref)..."
	@echo "───────────────────────────────────────────────────────────────"
	$(MAKE) ingest-ktc
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  ✅ Fast ingestion complete!"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Note: Run 'make ingest-ffanalytics' separately if needed (15-20 min)"
	@echo ""

ingest-all:
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  Full Ingestion Workflow (includes FFanalytics - SLOW!)"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "[1/6] Ingesting NFLverse data (provides player IDs)..."
	@echo "───────────────────────────────────────────────────────────────"
	$(MAKE) ingest-nflverse
	@echo ""
	@echo "[2/6] Building dim_player_id_xref (player name crosswalk)..."
	@echo "───────────────────────────────────────────────────────────────"
	$(MAKE) dbt-xref
	@echo ""
	@echo "[3/6] Ingesting Commissioner sheets (requires xref)..."
	@echo "───────────────────────────────────────────────────────────────"
	$(MAKE) ingest-sheets
	@echo ""
	@echo "[4/6] Ingesting Sleeper data (requires xref)..."
	@echo "───────────────────────────────────────────────────────────────"
	$(MAKE) ingest-sleeper-players
	@echo ""
	@echo "[5/6] Ingesting KTC dynasty values (requires xref)..."
	@echo "───────────────────────────────────────────────────────────────"
	$(MAKE) ingest-ktc
	@echo ""
	@echo "[6/6] Ingesting FFanalytics projections (⚠️  15-20 min)..."
	@echo "───────────────────────────────────────────────────────────────"
	$(MAKE) ingest-ffanalytics
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  ✅ Full ingestion workflow complete!"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""

dbt-deps:
	@echo "Installing dbt package dependencies"
	uv run env \
		DBT_DUCKDB_PATH="$$(pwd)/dbt/ff_data_transform/target/dev.duckdb" \
		dbt deps --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform $(ARGS)

dbt-seed:
	@echo "Seeding dbt sources"
	@mkdir -p dbt/ff_data_transform/target
	uv run env \
		EXTERNAL_ROOT="$$(pwd)/data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/dbt/ff_data_transform/target/dev.duckdb" \
		dbt seed --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform $(ARGS)

dbt-run:
	@echo "Running dbt (ensure dbt-duckdb is installed)"
	@mkdir -p dbt/ff_data_transform/target
	uv run env \
		EXTERNAL_ROOT="$$(pwd)/data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/dbt/ff_data_transform/target/dev.duckdb" \
		dbt run --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform $(ARGS)

dbt-test:
	@echo "Testing dbt models"
	@mkdir -p dbt/ff_data_transform/target
	uv run env \
		EXTERNAL_ROOT="$$(pwd)/data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/dbt/ff_data_transform/target/dev.duckdb" \
		dbt test --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform $(ARGS)

validate-franchise-mapping:
	@echo "Validating franchise mapping..."
	@mkdir -p dbt/ff_data_transform/target
	uv run env \
		EXTERNAL_ROOT="$$(pwd)/data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/dbt/ff_data_transform/target/dev.duckdb" \
		dbt test \
			--select tag:franchise_mapping \
			--project-dir dbt/ff_data_transform \
			--profiles-dir dbt/ff_data_transform
	@echo "✅ Franchise mapping validation complete"

lintcheck:
	@echo "=========================================="
	@echo "LINTER CHECKS"
	@echo "=========================================="
	@echo ""
	@echo "[1/5] Running ruff check..."
	@uv run ruff check . && echo "  ✓ ruff completed successfully" || echo "  ✗ ruff had errors (continuing...)"
	@echo ""
	@echo "[2/5] Running sqlfluff lint..."
	@uv run sqlfluff lint . && echo "  ✓ sqlfluff completed successfully" || echo "  ✗ sqlfluff had errors (continuing...)"
	@echo ""
	@echo "[3/5] Running yamllint..."
	@uv run yamllint --list-files . && echo "  ✓ yamllint completed successfully" || echo "  ✗ yamllint had errors (continuing...)"
	@echo ""
	@echo "[4/5] Running mdformat check..."
	@uv run mdformat --check . && echo "  ✓ mdformat completed successfully" || echo "  ✗ mdformat had errors (continuing...)"
	@echo ""
	@echo "[5/5] Running lintr (R)..."
	@Rscript -e "lintr::lint_dir('scripts/R')" && echo "  ✓ lintr completed successfully" || echo "  ✗ lintr had errors (continuing...)"
	@echo ""
	@echo "=========================================="
	@echo "LINTING CHECKS COMPLETE"
	@echo "=========================================="

lintfix:
	@echo "=========================================="
	@echo "LINTER AUTO-FIX"
	@echo "=========================================="
	@echo ""
	@echo "[1/5] Running ruff format ..."
	@uv run ruff format . && echo "  ✓ ruff format completed successfully" || echo "  ✗ ruff format had errors (continuing...)"
	@echo ""
	@echo "[2/5] Running ruff fix..."
	@uv run ruff check . --fix && echo "  ✓ ruff completed successfully" || echo "  ✗ ruff had errors (continuing...)"
	@echo ""
	@echo "[3/5] Running sqlfluff fix..."
	@uv run sqlfluff fix . && echo "  ✓ sqlfluff completed successfully" || echo "  ✗ sqlfluff had errors (continuing...)"
	@echo ""
	@echo "[4/5] Running mdformat..."
	@uv run mdformat . && echo "  ✓ mdformat completed successfully" || echo "  ✗ mdformat had errors (continuing...)"
	@echo ""
	@echo "[5/5] Running styler (R)..."
	@Rscript -e "styler::style_dir('scripts/R')" && echo "  ✓ styler completed successfully" || echo "  ✗ styler had errors (continuing...)"
	@echo ""
	@echo "=========================================="
	@echo "LINTING FIXES COMPLETE"
	@echo "=========================================="

typecheck:
	@echo "=========================================="
	@echo "TYPE CHECKING"
	@echo "=========================================="
	@echo ""
	@echo "Running pyrefly check (using config from pyproject.toml)..."
	@uv run pyrefly check && echo "  ✓ pyrefly completed successfully" || echo "  ✗ pyrefly found type errors"
	@echo ""
	@echo "=========================================="
	@echo "TYPE CHECKING COMPLETE"
	@echo "=========================================="

typeinfer:
	@echo "=========================================="
	@echo "TYPE INFERENCE"
	@echo "=========================================="
	@echo ""
	@echo "Running pyrefly infer on $(ARGS)..."
	@uv run pyrefly infer $(ARGS) && echo "  ✓ pyrefly infer completed successfully" || echo "  ✗ pyrefly infer had errors"
	@echo ""
	@echo "=========================================="
	@echo "TYPE INFERENCE COMPLETE"
	@echo "=========================================="

pre-commit:
	@echo "=========================================="
	@echo "PRE-COMMIT HOOKS"
	@echo "=========================================="
	@echo ""
	@echo "Running all pre-commit hooks..."
	@uv run pre-commit run --all-files && echo "  ✓ pre-commit completed successfully" || echo "  ✗ pre-commit had failures"
	@echo ""
	@echo "=========================================="
	@echo "PRE-COMMIT COMPLETE"
	@echo "=========================================="

sqlcheck:
	@echo "=========================================="
	@echo "SQL LINTING (dbt models)"
	@echo "=========================================="
	@echo ""
	@echo "Running sqlfluff lint..."
	@echo "Note: DuckDB-specific files excluded via .sqlfluffignore"
	@uv run sqlfluff lint dbt/ff_data_transform/models/ && echo "  ✓ sqlfluff completed successfully" || echo "  ✗ sqlfluff found issues"
	@echo ""
	@echo "=========================================="
	@echo "SQL LINTING COMPLETE"
	@echo "=========================================="

sqlfix:
	@echo "=========================================="
	@echo "SQL AUTO-FIX (dbt models)"
	@echo "=========================================="
	@echo ""
	@echo "Running sqlfluff fix..."
	@uv run sqlfluff fix dbt/ff_data_transform/models/ && echo "  ✓ sqlfluff completed successfully" || echo "  ✗ sqlfluff had errors"
	@echo ""
	@echo "=========================================="
	@echo "SQL AUTO-FIX COMPLETE"
	@echo "=========================================="

sqlfmt:
	@echo "=========================================="
	@echo "SQL FORMATTING (sqlfmt)"
	@echo "=========================================="
	@echo ""
	@echo "Formatting SQL files with sqlfmt..."
	@uv run sqlfmt dbt/ff_data_transform/models/**/*.sql && echo "  ✓ sqlfmt completed successfully" || echo "  ✗ sqlfmt had errors"
	@echo ""
	@echo "=========================================="
	@echo "SQL FORMATTING COMPLETE"
	@echo "=========================================="

sqlfmt-check:
	@echo "=========================================="
	@echo "SQL FORMAT CHECK (sqlfmt)"
	@echo "=========================================="
	@echo ""
	@echo "Checking SQL formatting..."
	@uv run sqlfmt --check dbt/ff_data_transform/models/**/*.sql && echo "  ✓ All files properly formatted" || echo "  ✗ Some files need formatting (run 'make sqlfmt' to fix)"
	@echo ""
	@echo "=========================================="
	@echo "SQL FORMAT CHECK COMPLETE"
	@echo "=========================================="

dbt-compile-check:
	@echo "=========================================="
	@echo "DBT COMPILE CHECK (SQL syntax validation)"
	@echo "=========================================="
	@echo ""
	@echo "Compiling dbt project to validate SQL syntax..."
	@mkdir -p dbt/ff_data_transform/target
	@uv run env \
		EXTERNAL_ROOT="$$(pwd)/data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/dbt/ff_data_transform/target/dev.duckdb" \
		dbt compile --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform && echo "  ✓ dbt compile completed successfully" || echo "  ✗ dbt compile found syntax errors"
	@echo ""
	@echo "=========================================="
	@echo "DBT COMPILE CHECK COMPLETE"
	@echo "=========================================="

dbt-opiner-check:
	@echo "=========================================="
	@echo "DBT-OPINER CHECK (dbt best practices)"
	@echo "=========================================="
	@echo ""
	@echo "[1/3] Installing dbt dependencies..."
	@mkdir -p dbt/ff_data_transform/target
	@cd dbt/ff_data_transform && \
		EXTERNAL_ROOT="$$(pwd)/../../data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/target/dev.duckdb" \
		uv run dbt deps --project-dir . --profiles-dir . || true
	@echo ""
	@echo "[2/3] Running dbt-opiner lint with compilation..."
	@echo "Note: Test files (tests/*.sql) are excluded - they're not dbt project nodes"
	@cd dbt/ff_data_transform && \
		EXTERNAL_ROOT="$$(pwd)/../../data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/target/dev.duckdb" \
		uv run dbt-opiner lint --all-files --force-compile
	@echo ""
	@echo "=========================================="
	@echo "DBT-OPINER CHECK COMPLETE"
	@echo "=========================================="

sql-all:
	@echo "=========================================="
	@echo "ALL SQL QUALITY CHECKS"
	@echo "=========================================="
	@echo ""
	@echo "[1/4] Checking SQL formatting..."
	@uv run sqlfmt --check dbt/ff_data_transform/models/**/*.sql && echo "  ✓ Formatting OK" || echo "  ✗ Formatting issues found (run 'make sqlfmt' to fix)"
	@echo ""
	@echo "[2/4] Running sqlfluff lint (selective)..."
	@uv run sqlfluff lint dbt/ff_data_transform/models/ && echo "  ✓ sqlfluff OK" || echo "  ✗ sqlfluff found issues"
	@echo ""
	@echo "[3/4] Validating SQL syntax (dbt compile)..."
	@mkdir -p dbt/ff_data_transform/target
	@uv run env \
		EXTERNAL_ROOT="$$(pwd)/data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/dbt/ff_data_transform/target/dev.duckdb" \
		dbt compile --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform && echo "  ✓ Syntax validation OK" || echo "  ✗ Syntax errors found"
	@echo ""
	@echo "[4/4] Checking dbt best practices (dbt-opiner)..."
	@cd dbt/ff_data_transform && \
		EXTERNAL_ROOT="$$(pwd)/../../data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/target/dev.duckdb" \
		uv run dbt deps --project-dir . --profiles-dir . || true
	@cd dbt/ff_data_transform && \
		EXTERNAL_ROOT="$$(pwd)/../../data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/target/dev.duckdb" \
		uv run dbt-opiner lint --all-files --force-compile
	@echo ""
	@echo "=========================================="
	@echo "ALL SQL QUALITY CHECKS COMPLETE"
	@echo "=========================================="
