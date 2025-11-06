## Convenience tasks for local iteration

.PHONY: help samples-nflverse dbt-run dbt-test dbt-seed quickstart-local sqlfix validate-franchise-mapping

help:
	@echo "Available targets:"
	@echo "  ingest-sheets        Ingest league sheets locally"
	@echo "  ingest-sleeper-players  Ingest Sleeper player database (for crosswalk validation)"
	@echo "  dbt-seed             Seed dbt sources (use 'make dbt-seed ARGS=<dbt seed args>')"
	@echo "  dbt-run              Run dbt models locally (DuckDB) (use 'make dbt-run ARGS=<dbt run args>')"
	@echo "  dbt-test             Run dbt tests locally (use 'make dbt-test ARGS=<dbt test args>')"
	@echo "  lintcheck            Run linter checks	"
	@echo "  lintfix              Run linter auto-fixes"
	@echo "  typecheck            Run type checks"
	@echo "  typeinfer            Automatically add type annotations; use 'make typeinfer ARGS=<file or directory>'"
	@echo "  sqlcheck             Run sqlfluff checks on dbt models"
	@echo "  sqlfix               Run sqlfluff auto-fixes on dbt models"
	@echo "  pre-commit           Run pre-commit hooks"

ingest-sheets:
	@echo "Ingesting league sheets locally"
	uv run python scripts/ingest/ingest_commissioner_sheet.py

ingest-sleeper-players:
	@echo "Ingesting Sleeper player database"
	uv run python -m src.ingest.sleeper.loader players

dbt-seed:
	@echo "Seeding dbt sources"
	@mkdir -p dbt/ff_analytics/target
	uv run env \
		EXTERNAL_ROOT="$$(pwd)/data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/dbt/ff_analytics/target/dev.duckdb" \
		dbt seed --project-dir dbt/ff_analytics --profiles-dir dbt/ff_analytics $(ARGS)

dbt-run:
	@echo "Running dbt (ensure dbt-duckdb is installed)"
	@mkdir -p dbt/ff_analytics/target
	uv run env \
		EXTERNAL_ROOT="$$(pwd)/data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/dbt/ff_analytics/target/dev.duckdb" \
		dbt run --project-dir dbt/ff_analytics --profiles-dir dbt/ff_analytics $(ARGS)

dbt-test:
	@echo "Testing dbt models"
	@mkdir -p dbt/ff_analytics/target
	uv run env \
		EXTERNAL_ROOT="$$(pwd)/data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/dbt/ff_analytics/target/dev.duckdb" \
		dbt test --project-dir dbt/ff_analytics --profiles-dir dbt/ff_analytics $(ARGS)

validate-franchise-mapping:
	@echo "Validating franchise mapping..."
	@mkdir -p dbt/ff_analytics/target
	uv run env \
		EXTERNAL_ROOT="$$(pwd)/data/raw" \
		DBT_DUCKDB_PATH="$$(pwd)/dbt/ff_analytics/target/dev.duckdb" \
		dbt test \
			--select tag:franchise_mapping \
			--project-dir dbt/ff_analytics \
			--profiles-dir dbt/ff_analytics
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
	@uv run sqlfluff lint dbt/ff_analytics/models/ && echo "  ✓ sqlfluff completed successfully" || echo "  ✗ sqlfluff found issues"
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
	@uv run sqlfluff fix dbt/ff_analytics/models/ && echo "  ✓ sqlfluff completed successfully" || echo "  ✗ sqlfluff had errors"
	@echo ""
	@echo "=========================================="
	@echo "SQL AUTO-FIX COMPLETE"
	@echo "=========================================="
