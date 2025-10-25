## Convenience tasks for local iteration

.PHONY: help samples-nflverse dbt-run dbt-test quickstart-local sqlfix

help:
	@echo "Available targets:"
	@echo "  samples-nflverse  Generate minimal nflverse samples (players, weekly)"
	@echo "  dbt-run           Run dbt models locally (DuckDB)"
	@echo "  dbt-test          Run dbt tests locally"
	@echo "  quickstart-local  Samples -> dbt run -> dbt test"
	@echo "  sqlfix            Run sqlfluff auto-fix on dbt models"

samples-nflverse:
	PYTHONPATH=. uv run python tools/make_samples.py nflverse \
		--datasets players weekly --seasons 2024 --weeks 1 --out ./samples

dbt-run:
	@echo "Running dbt (ensure dbt-duckdb is installed)"
	cd dbt/ff_analytics && EXTERNAL_ROOT="../../data/raw" dbt run --profiles-dir .

dbt-test:
	@echo "Testing dbt models"
	cd dbt/ff_analytics && EXTERNAL_ROOT="../../data/raw" dbt test --profiles-dir .

quickstart-local: samples-nflverse dbt-run dbt-test
	@echo "Done."

sqlfix:
	uv run pre-commit run --hook-stage manual sqlfluff-fix --all-files
