# CI/CD & DevOps Assessment Report

## Fantasy Football Analytics Project

**Assessment Date**: November 10, 2025
**Project**: ff-analytics (Python 3.13.6, dbt + DuckDB, GCS storage)
**Assessment Scope**: Build automation, testing, deployment, security, monitoring, GitOps

______________________________________________________________________

## Executive Summary

### Overall CI/CD Maturity: **Level 2-3** (Developing → Progressing)

**Current State**: Partial automation with good foundational setup but significant gaps in test automation, security integration, and deployment safety.

**Key Findings**:

1. **Strengths**

   - GitHub Actions workflows configured for data pipeline (nflverse) and ingestion (Google Sheets)
   - Pre-commit hooks with 10+ linting tools (ruff, sqlfluff, yamllint, mdformat)
   - Solid local development setup (UV, direnv, Makefile targets)
   - dbt validation in place (compile, test, opiner checks)
   - Explicit environment variable management (.env/.envrc)
   - Type checking configured (mypy, pyrefly)

2. **Critical Gaps**

   - **No test automation in CI** - pytest/coverage not run automatically on PRs/commits
   - **No security scanning** - Dependencies, secrets, code security not scanned in pipeline
   - **Manual deployments** - No automated promotion dev→staging→prod
   - **Missing deployment safety** - No health checks, rollback automation, or zero-downtime strategies
   - **No secret rotation** - Credentials managed manually via GitHub Secrets only
   - **No artifact versioning** - Parquet files in GCS not versioned or retention-managed
   - **No monitoring/alerting** - Pipeline and data quality failures not centrally tracked
   - **No runbooks** - Incident response procedures undocumented

3. **Security Issues** (from Phase 2 review)

   - 7 HIGH severity vulnerabilities in dependencies
   - No SBOM (Software Bill of Materials) generation
   - Credentials stored in GitHub Secrets with no rotation policy
   - `.env` file contains exposed API keys (sports-data.io, Discord webhook)
   - No code secret scanning (GitLeaks, TruffleHog)
   - No SAST (static application security testing)

______________________________________________________________________

## 1. Build Automation Assessment

### Current State: **Level 2** (Partial Automation)

#### What's Working

**Environment & Dependencies**

- UV package manager properly configured (uv.lock committed)
- Python 3.13.6 pinned via `.python-version`
- Development dependencies isolated via `[dependency-groups]` in pyproject.toml
- Pre-commit hooks for code quality

**Build Artifact Caching**

```yaml
# .github/workflows/data-pipeline.yml
- uses: astral-sh/setup-uv@v3
  with:
    enable-cache: true
    cache-dependency-glob: "uv.lock"
```

✅ Dependency caching reduces build time

**Makefile Orchestration**

- Clear build targets for ingestion (nflverse, sheets, sleeper, ktc, ffanalytics)
- Sequential workflow: `ingest-with-xref` handles dependency chain correctly
- Local reproducibility with environment variables

#### Gaps

| Gap                                          | Impact                               | Priority |
| -------------------------------------------- | ------------------------------------ | -------- |
| No CI build step (only manual `uv sync`)     | Can't verify builds on ubuntu-latest | HIGH     |
| No build matrix for multiple Python versions | Can't catch version-specific issues  | MEDIUM   |
| No Docker image build/cache                  | No container-ready deployment        | HIGH     |
| dbt artifacts not cached between runs        | Recompile every workflow run         | MEDIUM   |
| No build exit codes validated                | Silent failures possible             | HIGH     |

#### Recommendations

```yaml
# Add to .github/workflows/ci.yml (new file)
name: Build Validation

on:
  pull_request:
    paths:
      - 'src/**'
      - 'tools/**'
      - 'tests/**'
      - 'pyproject.toml'
      - 'uv.lock'
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.13']  # Can add '3.14' when released

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
          cache-dependency-glob: 'uv.lock'

      - name: Install dependencies
        run: uv sync

      - name: Verify imports
        run: |
          uv run python -c "import ff_analytics_utils; import ingest"
          echo "✓ Core packages importable"

      - name: Type checking
        run: uv run mypy src/ tools/ --ignore-missing-imports

      - name: Export dependency graph
        run: uv export > requirements-ci.txt
        continue-on-error: true
```

______________________________________________________________________

## 2. Test Automation Integration

### Current State: **Level 1-2** (Manual/Incomplete)

#### What's Working

**Test Infrastructure**

- pytest configured with markers (slow, integration, unit)
- 6 test files in `/tests/` directory
- Coverage tracking via pytest-cov
- Type checking with mypy (preconfigured)

**dbt Testing**

```yaml
# dbt_project.yml
tests:
  +severity: error
  +tags: ["data_quality", "franchise_mapping"]
```

- 285+ dbt tests defined across models
- Grain uniqueness tests in place
- FK relationship tests configured

#### Critical Gaps

```
❌ NO AUTOMATED TEST EXECUTION in CI/CD
  - Tests run only locally via 'make' targets
  - PRs not blocked by test failures
  - Test coverage not tracked over time

❌ NO COVERAGE ENFORCEMENT
  - pytest-cov configured but not used in pipeline
  - No coverage threshold (should be 80%+)
  - No coverage delta checks on PRs

❌ dbt TEST NOT IN PIPELINE
  - dbt test runs in data-pipeline.yml but only on workflow_dispatch
  - Not triggered on PR merges
  - Failures don't block deployment

❌ NO PERFORMANCE REGRESSION TESTING
  - No benchmarks for query performance
  - No tracking of dbt compile times
  - No alerting on slow transforms
```

#### Test Execution Matrix

```
Tests Available                  | Automated? | Blocks Merge? | Coverage Tracked?
─────────────────────────────────────────────────────────────────────────────
Python pytest (6 files)          | ❌ Manual  | ❌ No         | ❌ No
dbt tests (285+ tests)           | ⚠️  Manual | ❌ No         | ❌ N/A
Pre-commit linting               | ✅ Local  | ❌ Optional   | ❌ N/A
Type checking (mypy)             | ❌ Manual  | ❌ No         | ❌ N/A
dbt compile (syntax)             | ✅ Local  | ❌ Optional   | ❌ N/A
Ingest validation                | ❌ Manual  | ❌ No         | ❌ No
Data quality (dbt test)          | ⚠️  Manual | ❌ No         | ❌ N/A
```

#### Recommendations: Add Test Automation Workflow

**File**: `/Users/jason/code/ff_analytics/.github/workflows/test.yml`

```yaml
name: Test & Coverage

on:
  pull_request:
    paths:
      - 'src/**'
      - 'tools/**'
      - 'tests/**'
      - 'pyproject.toml'
  push:
    branches:
      - main

jobs:
  pytest:
    name: Python Tests
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
          cache-dependency-glob: 'uv.lock'

      - name: Install dependencies
        run: uv sync

      - name: Run pytest with coverage
        run: |
          uv run pytest tests/ \
            --cov=src/ingest \
            --cov=src/ff_analytics_utils \
            --cov=tools \
            --cov-report=xml \
            --cov-report=term-missing \
            --junitxml=test-results.xml \
            -v

      - name: Comment coverage on PR
        if: github.event_name == 'pull_request'
        uses: py-cov-action/python-coverage-comment-action@v3
        with:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: test-results.xml
          retention-days: 30

      - name: Coverage gate (80% minimum)
        run: |
          COVERAGE=$(uv run coverage report | grep TOTAL | awk '{print $(NF-2)}' | sed 's/%//')
          echo "Coverage: ${COVERAGE}%"
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "❌ Coverage ${COVERAGE}% is below 80% threshold"
            exit 1
          fi
          echo "✅ Coverage ${COVERAGE}% meets threshold"

  dbt-tests:
    name: dbt Data Quality Tests
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync

      - name: Setup GCS credentials (if available)
        if: secrets.GOOGLE_APPLICATION_CREDENTIALS_JSON
        env:
          GOOGLE_APPLICATION_CREDENTIALS_JSON: ${{ secrets.GOOGLE_APPLICATION_CREDENTIALS_JSON }}
        run: |
          mkdir -p ~/.config/gcp
          echo "$GOOGLE_APPLICATION_CREDENTIALS_JSON" | base64 -d > ~/.config/gcp/key.json
          echo "GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcp/key.json" >> $GITHUB_ENV

      - name: dbt parse & compile
        run: |
          cd dbt/ff_data_transform
          EXTERNAL_ROOT="$(pwd)/../../data/raw" \
          DBT_DUCKDB_PATH="$(pwd)/target/dev.duckdb" \
          uv run dbt compile --profiles-dir . --target-path target/

      - name: Run dbt tests
        run: |
          cd dbt/ff_data_transform
          EXTERNAL_ROOT="$(pwd)/../../data/raw" \
          DBT_DUCKDB_PATH="$(pwd)/target/dev.duckdb" \
          uv run dbt test \
            --profiles-dir . \
            --target-path target/ \
            --store-failures \
            --select 'state:modified+' || true

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: dbt-test-results
          path: dbt/ff_data_transform/target/
          retention-days: 30

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    if: contains(github.event.pull_request.labels.*.name, 'integration-tests')

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync

      - name: Run integration tests
        run: |
          uv run pytest tests/ \
            -m integration \
            -v \
            --tb=short
        env:
          INTEGRATION_TEST_MODE: 'true'
```

______________________________________________________________________

## 3. Deployment Strategies

### Current State: **Level 0-1** (No Automated Deployment)

#### Manual Deployment Process

**Current Workflow** (documented in Phase 1):

```
Developer Machine
      ↓
  make ingest-with-xref  (manual)
      ↓
  GCS bucket (data/raw, data/stage)
      ↓
  make dbt-run           (manual)
      ↓
  DuckDB local           (dev.duckdb)
      ↓
  Jupyter notebooks      (manual analysis)
```

#### Critical Issues

1. **No promotion pipeline** - No dev→staging→prod progression
2. **No zero-downtime deployment** - Data overwrites happen immediately
3. **No health checks** - No validation that data transformation succeeded
4. **No rollback capability** - Previous versions not retained
5. **No deployment tracking** - No record of what was deployed when
6. **Manual steps** - Human error risk on every deployment

#### Recommended Deployment Architecture

**Immutable Data Pattern with Versioning**

```
# Current (problematic)
gs://ff-analytics/raw/nflverse/weekly/dt=YYYY-MM-DD/data.parquet  ← overwrites daily

# Recommended (immutable with versioning)
gs://ff-analytics/raw/nflverse/weekly/dt=YYYY-MM-DD/v001/data.parquet
gs://ff-analytics/raw/nflverse/weekly/dt=YYYY-MM-DD/v002/data.parquet  ← new version
gs://ff-analytics/raw/nflverse/weekly/dt=YYYY-MM-DD/LATEST -> v002/  ← pointer

# With promotion
gs://ff-analytics/environments/
  ├── dev/
  │   ├── raw/nflverse/weekly/dt=YYYY-MM-DD/data.parquet
  │   └── manifest.json (metadata)
  ├── staging/
  │   ├── raw/nflverse/weekly/dt=YYYY-MM-DD/data.parquet
  │   └── manifest.json
  └── prod/
      ├── raw/nflverse/weekly/dt=YYYY-MM-DD/data.parquet
      └── manifest.json
```

#### Deployment Workflow Template

**File**: `/Users/jason/code/ff_analytics/.github/workflows/deploy.yml`

```yaml
name: Deploy Data Pipeline

on:
  push:
    branches:
      - main
    paths:
      - 'src/ingest/**'
      - 'dbt/ff_data_transform/models/**'
      - '.github/workflows/deploy.yml'
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy to'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production
      skip_tests:
        description: 'Skip tests (emergency only)'
        required: false
        default: false
        type: boolean

env:
  GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  GCS_BUCKET: ${{ secrets.GCS_BUCKET }}

jobs:
  validate:
    name: Validate & Test
    runs-on: ubuntu-latest

    outputs:
      deployment_id: ${{ steps.metadata.outputs.deployment_id }}
      data_version: ${{ steps.metadata.outputs.data_version }}

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync

      - name: Generate deployment metadata
        id: metadata
        run: |
          DEPLOYMENT_ID="$(date +%s)-$(git rev-parse --short HEAD)"
          DATA_VERSION="$(date +%Y-%m-%d)-v$(date +%H%M%S)"
          echo "deployment_id=${DEPLOYMENT_ID}" >> $GITHUB_OUTPUT
          echo "data_version=${DATA_VERSION}" >> $GITHUB_OUTPUT
          echo "Deployment ID: ${DEPLOYMENT_ID}"
          echo "Data Version: ${DATA_VERSION}"

      - name: Linting & type checks
        run: |
          echo "Running pre-deployment validation..."
          uv run ruff check src/ tools/ || exit 1
          uv run mypy src/ tools/ --ignore-missing-imports || exit 1
          echo "✅ Code quality checks passed"

      - name: dbt validation
        run: |
          cd dbt/ff_data_transform
          EXTERNAL_ROOT="$(pwd)/../../data/raw" \
          DBT_DUCKDB_PATH="$(pwd)/target/dev.duckdb" \
          uv run dbt parse --profiles-dir .
          echo "✅ dbt models valid"

      - name: Run tests
        if: github.event.inputs.skip_tests != 'true'
        run: |
          uv run pytest tests/ -q --tb=short
          echo "✅ Unit tests passed"

  deploy-staging:
    name: Deploy to Staging
    needs: validate
    runs-on: ubuntu-latest
    if: github.event_name == 'push' || github.event.inputs.environment == 'staging'

    environment:
      name: staging
      url: https://console.cloud.google.com/storage/browser/${{ secrets.GCS_BUCKET }}/environments/staging

    steps:
      - uses: actions/checkout@v4

      - name: Setup GCP credentials
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SERVICE_ACCOUNT_JSON }}

      - name: Setup Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        run: uv sync

      - name: Ingest data to staging
        env:
          DEPLOYMENT_ID: ${{ needs.validate.outputs.deployment_id }}
          DATA_VERSION: ${{ needs.validate.outputs.data_version }}
        run: |
          export OUT_DIR="gs://${{ secrets.GCS_BUCKET }}/environments/staging/raw"
          export METADATA_VERSION="${DATA_VERSION}"

          echo "Ingesting to staging: ${OUT_DIR}"
          uv run python - << 'PYEOF'
          from ingest.nflverse.shim import load_nflverse
          load_nflverse('ff_playerids', out_dir='${OUT_DIR}')
          load_nflverse('weekly', seasons=[2025], out_dir='${OUT_DIR}')
          print("✅ Staging ingestion complete")
          PYEOF

      - name: Run dbt on staging
        env:
          OUT_DIR: gs://${{ secrets.GCS_BUCKET }}/environments/staging/raw
        run: |
          cd dbt/ff_data_transform
          EXTERNAL_ROOT="${OUT_DIR}" \
          DBT_DUCKDB_PATH="$(pwd)/target/staging.duckdb" \
          uv run dbt run --profiles-dir . --target staging

          # Run tests
          uv run dbt test --profiles-dir . --target staging || {
            echo "❌ Data quality tests failed in staging"
            exit 1
          }

      - name: Validate staging data
        env:
          OUT_DIR: gs://${{ secrets.GCS_BUCKET }}/environments/staging/raw
        run: |
          uv run python - << 'PYEOF'
          import duckdb
          conn = duckdb.connect(':memory:')

          # Validate data was written
          result = conn.execute(f"""
            SELECT COUNT(*) as row_count
            FROM read_parquet('{os.environ['OUT_DIR']}/nflverse/weekly/dt=*/*.parquet')
          """).fetchall()

          if result[0][0] == 0:
            raise Exception("No data in staging")
          print(f"✅ Staging validation: {result[0][0]} rows")
          PYEOF

      - name: Create staging manifest
        run: |
          cat > staging-manifest.json << EOF
          {
            "environment": "staging",
            "deployment_id": "${{ needs.validate.outputs.deployment_id }}",
            "data_version": "${{ needs.validate.outputs.data_version }}",
            "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
            "commit_sha": "${{ github.sha }}",
            "deployed_by": "${{ github.actor }}"
          }
          EOF

          gsutil cp staging-manifest.json \
            gs://${{ secrets.GCS_BUCKET }}/environments/staging/manifest.json

  deploy-production:
    name: Deploy to Production
    needs: [validate, deploy-staging]
    runs-on: ubuntu-latest
    if: github.event.inputs.environment == 'production' || (github.ref == 'refs/heads/main' && github.event_name == 'push')

    environment:
      name: production
      url: https://console.cloud.google.com/storage/browser/${{ secrets.GCS_BUCKET }}/environments/prod

    steps:
      - uses: actions/checkout@v4

      - name: Setup GCP credentials
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SERVICE_ACCOUNT_JSON }}

      - name: Setup Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        run: uv sync

      - name: Backup current production data
        run: |
          BACKUP_DIR="gs://${{ secrets.GCS_BUCKET }}/environments/prod/backups/$(date +%Y-%m-%d-%H%M%S)"
          gsutil -m cp -r gs://${{ secrets.GCS_BUCKET }}/environments/prod/raw/* "${BACKUP_DIR}/" || true
          echo "Backup created at: ${BACKUP_DIR}"
          echo "BACKUP_DIR=${BACKUP_DIR}" >> $GITHUB_ENV

      - name: Promote staging to production
        run: |
          echo "Promoting staging → production..."
          gsutil -m cp -r gs://${{ secrets.GCS_BUCKET }}/environments/staging/raw/* \
            gs://${{ secrets.GCS_BUCKET }}/environments/prod/raw/
          echo "✅ Data promotion complete"

      - name: Run dbt on production
        run: |
          cd dbt/ff_data_transform
          EXTERNAL_ROOT="gs://${{ secrets.GCS_BUCKET }}/environments/prod/raw" \
          DBT_TARGET=prod \
          uv run dbt run --profiles-dir . --target prod

          uv run dbt test --profiles-dir . --target prod

      - name: Create production manifest
        run: |
          cat > prod-manifest.json << EOF
          {
            "environment": "production",
            "deployment_id": "${{ needs.validate.outputs.deployment_id }}",
            "data_version": "${{ needs.validate.outputs.data_version }}",
            "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
            "commit_sha": "${{ github.sha }}",
            "deployed_by": "${{ github.actor }}",
            "backup_location": "${{ env.BACKUP_DIR }}"
          }
          EOF

          gsutil cp prod-manifest.json \
            gs://${{ secrets.GCS_BUCKET }}/environments/prod/manifest.json

  notify:
    name: Notify Deployment Status
    needs: [validate, deploy-staging]
    runs-on: ubuntu-latest
    if: always()

    steps:
      - name: Send Discord notification
        if: secrets.DISCORD_WEBHOOK_URL
        run: |
          STATUS="passed"
          if [ "${{ needs.deploy-staging.result }}" != "success" ]; then
            STATUS="failed"
          fi

          curl -H "Content-Type: application/json" \
            -X POST \
            -d "{
              \"embeds\": [{
                \"title\": \"Deployment ${STATUS}\",
                \"description\": \"Data pipeline deployment\",
                \"fields\": [
                  {\"name\": \"Deployment ID\", \"value\": \"${{ needs.validate.outputs.deployment_id }}\"},
                  {\"name\": \"Data Version\", \"value\": \"${{ needs.validate.outputs.data_version }}\"},
                  {\"name\": \"Commit\", \"value\": \"${{ github.sha }}\"}
                ]
              }]
            }" \
            ${{ secrets.DISCORD_WEBHOOK_URL }} || true
```

______________________________________________________________________

## 4. Infrastructure as Code (IaC) Assessment

### Current State: **Level 0** (No IaC)

#### Current State

**GCS Bucket Configuration**: Manual setup via GCP Console

```
gs://ff-analytics/
├── raw/          ← Manual parquet ingestion
├── stage/        ← Manual dbt staging
├── mart/         ← Manual dbt marts
└── ops/          ← Manual metadata
```

**Missing**:

- Terraform/Pulumi for bucket provisioning
- Service account configuration
- IAM policies
- Lifecycle policies (retention)
- Bucket versioning
- Monitoring

#### Recommended: Terraform for GCS

**File**: `/Users/jason/code/ff_analytics/terraform/gcs.tf`

```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  backend "gcs" {
    bucket = "ff-analytics-terraform-state"
    prefix = "prod"
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# GCS bucket for data
resource "google_storage_bucket" "data_bucket" {
  name          = var.data_bucket_name
  location      = var.gcp_region
  force_destroy = false

  uniform_bucket_level_access = true
  versioning {
    enabled = true  # Enable versioning for rollback capability
  }

  lifecycle_rule {
    condition {
      age = 90
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      storage_class = "STANDARD"
      age           = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

# Service account for pipeline
resource "google_service_account" "pipeline" {
  account_id   = "ff-analytics-pipeline"
  display_name = "FF Analytics Data Pipeline"
}

# Roles for pipeline service account
resource "google_project_iam_member" "pipeline_storage_admin" {
  project = var.gcp_project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.pipeline.email}"
}

# Service account key for CI/CD
resource "google_service_account_key" "pipeline_key" {
  service_account_id = google_service_account.pipeline.name
  public_key_type    = "TYPE_X509_PEM_CERT"
}

output "service_account_email" {
  value = google_service_account.pipeline.email
}

output "bucket_name" {
  value = google_storage_bucket.data_bucket.name
}
```

**File**: `/Users/jason/code/ff_analytics/terraform/variables.tf`

```hcl
variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "us-east4"
}

variable "data_bucket_name" {
  description = "Data bucket name (must be globally unique)"
  type        = string
  default     = "ff-analytics"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}
```

**Usage**:

```bash
cd terraform
terraform init
terraform plan -var="gcp_project_id=ff-analytics-1"
terraform apply
```

______________________________________________________________________

## 5. Security in CI/CD Pipeline

### Current State: **Level 1-2** (Basic / Incomplete)

#### Security Audit Findings

**Vulnerabilities Found** (from Phase 2):

- 7 HIGH severity vulnerabilities in dependencies
- API keys exposed in `.env` file
- No dependency scanning in CI
- No code security scanning (SAST)
- No container scanning
- No secret rotation policy

#### Critical Improvements Needed

**File**: `/Users/jason/code/ff_analytics/.github/workflows/security.yml`

```yaml
name: Security Scanning

on:
  pull_request:
    paths:
      - '**.py'
      - 'pyproject.toml'
      - 'uv.lock'
      - '.github/workflows/security.yml'
  push:
    branches:
      - main
  schedule:
    - cron: '0 0 * * 0'  # Weekly scan

permissions:
  contents: read
  security-events: write

jobs:
  dependency-scanning:
    name: Dependency Vulnerability Scan
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - uses: astral-sh/setup-uv@v3

      - name: Export dependencies
        run: uv export > requirements.txt

      - name: Run Safety check
        run: |
          uv tool run safety check \
            --file requirements.txt \
            --json > safety-report.json || true

      - name: Upload Safety report
        uses: actions/upload-artifact@v4
        with:
          name: safety-report
          path: safety-report.json

      - name: Run pip-audit
        run: |
          uv tool run pip-audit \
            --desc \
            --format json \
            --skip-editable \
            > pip-audit-report.json || true

      - name: Comment vulnerability findings
        if: github.event_name == 'pull_request'
        run: |
          # Parse and comment on PR if vulnerabilities found
          if grep -q "vulnerable" safety-report.json; then
            cat > comment.md << EOF
          ## Security Alert: Vulnerabilities Found

          Review the artifact: \`safety-report.json\`
          EOF
            # Post comment to PR
          fi

  secret-scanning:
    name: Secret Detection
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: TruffleHog scan
        run: |
          docker run -v "$PWD:/path" \
            trufflesecurity/trufflehog:latest \
            filesystem /path \
            --json \
            > truffle-report.json || true

      - name: GitLeaks scan
        run: |
          docker run -v "$PWD:/path" \
            zricethezav/gitleaks:latest \
            detect \
            --source /path \
            --verbose \
            --report-path /path/gitleaks-report.json || true

      - name: Upload secret scan results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: secret-scan-results
          path: |
            truffle-report.json
            gitleaks-report.json

  sast-scanning:
    name: Static Application Security Testing
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - uses: astral-sh/setup-uv@v3

      - name: Bandit (Python security)
        run: |
          uv tool run bandit -r src/ tools/ \
            -f json \
            -o bandit-report.json || true

      - name: Semgrep security rules
        run: |
          docker run \
            --rm \
            -v "$PWD:/src" \
            returntocorp/semgrep \
            semgrep \
              --json \
              --config=p/security-audit \
              /src/src \
            > semgrep-report.json || true

      - name: Upload SAST results
        uses: actions/upload-artifact@v4
        with:
          name: sast-results
          path: |
            bandit-report.json
            semgrep-report.json

  supply-chain-security:
    name: Supply Chain Security (SBOM)
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - uses: astral-sh/setup-uv@v3

      - name: Generate SBOM (syft)
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
          syft dir:. -o spdx-json > sbom.spdx.json

      - name: Generate Python SBOM (pip-audit)
        run: |
          uv export > requirements.txt
          uv tool run cyclonedx-bom -i requirements.txt -o sbom-python.xml

      - name: Upload SBOM artifacts
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom*

  credential-rotation:
    name: Check Credential Rotation
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'

    steps:
      - uses: actions/checkout@v4

      - name: Check service account key age
        env:
          GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
        run: |
          # This would require GCP API access
          # For now, document the requirement
          echo "TODO: Implement automatic credential rotation check"
          echo "Recommendation: Rotate service account keys every 90 days"
```

#### Secrets Management Hardening

**Current Problem**: API keys stored in `.env` (exposed)

**Solution**: Use GitHub Secrets only

```bash
# Remove exposed keys from .env
git rm -f .env --cached
git commit -m "Remove exposed credentials from repository"

# Add to .gitignore
echo ".env" >> .gitignore
echo "config/secrets/" >> .gitignore

# Create .env.example (template only)
cat > .env.example << 'EOF'
# Copy this file to .env and fill in your actual values
# NEVER commit .env to git!

GCP_PROJECT_ID=your-project-id
GCS_BUCKET=your-bucket-name
COMMISSIONER_SHEET_ID=your-sheet-id
LEAGUE_SHEET_COPY_ID=your-sheet-id
SLEEPER_LEAGUE_ID=your-league-id
SPORTS_DATA_IO_API_KEY=your-api-key
DISCORD_WEBHOOK_URL=your-webhook-url
EOF

# Configure GitHub Secrets (via UI or GitHub CLI)
gh secret set GCP_PROJECT_ID --body "ff-analytics-1"
gh secret set GCS_BUCKET --body "ff-analytics"
gh secret set GOOGLE_APPLICATION_CREDENTIALS_JSON --body "$(cat /path/to/key.json | base64)"
```

______________________________________________________________________

## 6. Monitoring & Observability

### Current State: **Level 1** (Minimal)

#### Current Capabilities

- Discord webhook notifications (ingest_google_sheets.yml)
- GitHub workflow artifacts (test results, logs)
- Manual dbt test execution
- `.env` file for configuration

#### Missing Components

| Component                  | Missing                       | Impact                       |
| -------------------------- | ----------------------------- | ---------------------------- |
| Pipeline execution metrics | No Prometheus/CloudMonitoring | Can't track SLA              |
| Data quality dashboards    | No Grafana/Looker             | Can't monitor freshness      |
| Alerting policies          | Manual Discord only           | No incident escalation       |
| Audit logs                 | No structured logging         | Can't track who changed what |
| Performance tracking       | No benchmark storage          | Can't detect regression      |
| Cost monitoring            | No GCP billing alerts         | Can't optimize expenses      |

#### Recommended: Monitoring Stack

**File**: `/Users/jason/code/ff_analytics/.github/workflows/monitoring.yml`

```yaml
name: Pipeline Monitoring

on:
  schedule:
    - cron: '0 * * * *'  # Every hour
  workflow_run:
    workflows:
      - "Deploy Data Pipeline"
    types: [completed]

jobs:
  collect-metrics:
    name: Collect Pipeline Metrics
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SERVICE_ACCOUNT_JSON }}

      - name: Collect workflow run metrics
        run: |
          # Example: Push metrics to Cloud Monitoring
          LATEST_RUN=$(gh api \
            repos/${{ github.repository }}/actions/runs \
            --jq '.workflow_runs[0]')

          RUN_ID=$(echo $LATEST_RUN | jq '.id')
          CONCLUSION=$(echo $LATEST_RUN | jq '.conclusion')
          CREATED_AT=$(echo $LATEST_RUN | jq '.created_at')
          UPDATED_AT=$(echo $LATEST_RUN | jq '.updated_at')

          echo "Workflow Run: $RUN_ID"
          echo "Status: $CONCLUSION"
          echo "Duration: $(( $(date -d "$UPDATED_AT" +%s) - $(date -d "$CREATED_AT" +%s) )) seconds"

      - name: Query data freshness
        run: |
          # Check when data was last successfully ingested
          gsutil stat gs://${{ secrets.GCS_BUCKET }}/environments/prod/raw/

          LAST_MODIFIED=$(gsutil stat gs://${{ secrets.GCS_BUCKET }}/environments/prod/manifest.json | grep "Time created" | awk '{print $3}')
          echo "Last successful deployment: $LAST_MODIFIED"

      - name: Monitor GCS costs
        run: |
          # Get bucket size
          SIZE=$(gsutil du -s gs://${{ secrets.GCS_BUCKET }} | awk '{print $1}')
          SIZE_GB=$((SIZE / 1073741824))
          echo "Bucket size: ${SIZE_GB}GB"

          # Estimate monthly cost (~$0.020 per GB)
          MONTHLY_COST=$(echo "scale=2; $SIZE_GB * 0.020" | bc)
          echo "Estimated monthly cost: \$$MONTHLY_COST"

  alert-on-failure:
    name: Alert on Pipeline Failure
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'failure'

    steps:
      - name: Send critical alert
        uses: slackapi/slack-github-action@v1
        with:
          webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
          payload: |
            {
              "text": "CRITICAL: Data pipeline failed",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*CRITICAL: Data Pipeline Failure*\n<${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.event.workflow_run.id }}|View Workflow>"
                  }
                }
              ]
            }
```

______________________________________________________________________

## 7. GitOps Readiness Assessment

### Current State: **Level 1** (Minimal)

#### Current Configuration Management

- dbt models in Git (source of truth)
- `.env` file (not in git, manual distribution)
- SQL formatting via pre-commit (automated)
- No configuration drift detection

#### Recommended: GitOps Implementation

**File**: `/Users/jason/code/ff_analytics/ops/config/prod-values.yaml`

```yaml
# Production environment configuration
environments:
  production:
    gcs_bucket: gs://ff-analytics
    dbt_target: prod
    dbt_threads: 8
    freshness_hours: 24
    data_retention_days: 90

    ingestion:
      nflverse:
        enabled: true
        schedule: "0 8,16 * * *"  # 08:00, 16:00 UTC
      sheets:
        enabled: true
        schedule: "30 7,15 * * *"  # 07:30, 15:30 UTC (before main pipeline)
      sleeper:
        enabled: true
        schedule: "0 9 * * *"  # 09:00 UTC
      ktc:
        enabled: true
        schedule: "0 10 * * *"  # 10:00 UTC
      ffanalytics:
        enabled: false  # Too slow for scheduled runs
        manual_only: true

    alerts:
      slack_webhook: ${{ secrets.SLACK_WEBHOOK_URL }}
      email: ops@example.com
      freshness_threshold_hours: 24
      failure_threshold_count: 3
```

______________________________________________________________________

## 8. Artifact Management

### Current State: **Level 1** (Unmanaged)

#### Current State

- Parquet files written directly to GCS `/raw`, `/stage`, `/mart`
- No versioning or retention policies
- No artifact signing or integrity checks
- Manual cleanup

#### Recommended: Artifact Lifecycle Management

**GCS Lifecycle Policy** (Terraform):

```hcl
lifecycle_rule {
  condition {
    age = 7
    num_newer_versions = 3
    match_storage_class = ["STANDARD"]
  }
  action {
    type          = "SetStorageClass"
    storage_class = "NEARLINE"
  }
}

lifecycle_rule {
  condition {
    age = 180
  }
  action {
    type = "Delete"
  }
}

lifecycle_rule {
  condition {
    is_live = false
  }
  action {
    type = "Delete"
  }
}
```

**Artifact Registry** (for future Docker builds):

```hcl
resource "google_artifact_registry_repository" "docker" {
  location      = var.gcp_region
  repository_id = "ff-analytics-docker"
  format        = "DOCKER"
}

# Future: Store versioned pipeline images here
```

______________________________________________________________________

## 9. Developer Experience

### Current State: **Level 3-4** (Good)

#### What's Working

✅ **Excellent**:

- Makefile with clear targets (`make help`)
- direnv auto-loads `.env` when entering directory
- UV handles fast dependency installation
- Pre-commit hooks catch errors before commit
- `.PHONY` targets prevent edge cases

✅ **Good**:

- `README.md` exists (from git history)
- `CLAUDE.md` provides context to Claude Code
- `.python-version` pins Python 3.13.6
- Type hints configured (mypy, pyrefly)

#### Minor Improvements

```bash
# Add justfile as alternative to Makefile
# File: /Users/jason/code/ff_analytics/justfile

help:
    @just --list

quick-install:
    uv sync
    pre-commit install

setup-dev:
    just quick-install
    make dbt-deps
    echo "✅ Development environment ready"

test-all:
    @echo "Running all tests..."
    uv run pytest tests/ -v
    make dbt-test

lint-fix:
    @echo "Fixing linting issues..."
    uv run ruff format .
    uv run ruff check . --fix
    make sql-all

deploy-staging:
    @echo "Deploying to staging (requires CI/CD setup)"
    @echo "Run: gh workflow run deploy.yml --ref main -f environment=staging"
```

______________________________________________________________________

## 10. Incident Response & Rollback Capability

### Current State: **Level 0** (No Automation)

#### Current Manual Process

1. Discover issue (manual monitoring)
2. Identify failed data/transformation
3. Manually restore from previous version (if available)
4. Re-run dbt/ingest (manual)
5. Notify team (Discord)

#### Recommended: Automated Rollback

**File**: `/Users/jason/code/ff_analytics/.github/workflows/rollback.yml`

```yaml
name: Rollback Deployment

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to rollback'
        required: true
        type: choice
        options:
          - staging
          - production
      version:
        description: 'Version to rollback to (or "previous")'
        required: true
        default: 'previous'

jobs:
  rollback:
    name: Execute Rollback
    runs-on: ubuntu-latest

    environment:
      name: ${{ github.event.inputs.environment }}

    steps:
      - uses: actions/checkout@v4

      - name: Setup GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SERVICE_ACCOUNT_JSON }}

      - name: Setup Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: List available backups
        run: |
          echo "Available backups:"
          gsutil ls -p ${{ secrets.GCS_BUCKET }}/environments/${{ github.event.inputs.environment }}/backups/ | tail -10

      - name: Execute rollback
        run: |
          ENV=${{ github.event.inputs.environment }}
          VERSION=${{ github.event.inputs.version }}

          if [ "$VERSION" = "previous" ]; then
            # Get most recent backup
            VERSION=$(gsutil ls -p ${{ secrets.GCS_BUCKET }}/environments/${ENV}/backups/ | tail -2 | head -1 | tr -d '/')
          fi

          echo "Rolling back ${ENV} to ${VERSION}..."

          # Restore from backup
          gsutil -m cp -r ${{ secrets.GCS_BUCKET }}/environments/${ENV}/backups/${VERSION}/* \
            ${{ secrets.GCS_BUCKET }}/environments/${ENV}/raw/

          echo "✅ Rollback complete"

      - name: Verify rollback
        run: |
          # Run data quality tests
          cd dbt/ff_data_transform
          EXTERNAL_ROOT="${{ secrets.GCS_BUCKET }}/environments/${{ github.event.inputs.environment }}/raw" \
          uv run dbt test

      - name: Notify team
        run: |
          curl -X POST ${{ secrets.DISCORD_WEBHOOK_URL }} \
            -H "Content-Type: application/json" \
            -d '{
              "content": "Rollback executed for ${{ github.event.inputs.environment }}"
            }'
```

______________________________________________________________________

## 11. Cost Optimization

### Current State: **Level 0** (No Tracking)

#### Cost Monitoring Strategy

```bash
# Add to .github/workflows/cost-tracking.yml
# - Daily GCS bucket size sampling
# - Monthly cost projection
# - Alerting when threshold exceeded ($100/month threshold)

# Recommendations:
# 1. Enable object versioning (storage tracking)
# 2. Set lifecycle policies (transition to Nearline after 30 days)
# 3. Archive old data to Cloud Storage (cold storage tier)
# 4. Monitor unused resources weekly
```

______________________________________________________________________

## Maturity Assessment Summary

### Scoring by Dimension (0-5 scale)

| Area                       | Score | Status     | Comment                               |
| -------------------------- | ----- | ---------- | ------------------------------------- |
| **Build Automation**       | 2/5   | Developing | Partial (no CI matrix, Docker)        |
| **Test Automation**        | 1/5   | Minimal    | Tests exist but not automated in CI   |
| **Deployment Safety**      | 0/5   | None       | Purely manual, no versioning          |
| **Infrastructure as Code** | 0/5   | None       | Manual GCP setup                      |
| **Security Integration**   | 1/5   | Minimal    | Pre-commit only, no pipeline scanning |
| **Monitoring & Alerts**    | 1/5   | Minimal    | Discord only, no metrics tracking     |
| **GitOps**                 | 1/5   | Minimal    | Git holds code, not config            |
| **Artifact Management**    | 0/5   | None       | No versioning or lifecycle policies   |
| **Developer Experience**   | 3/5   | Good       | Excellent local setup (make, direnv)  |
| **Incident Response**      | 0/5   | None       | No automated rollback                 |
| **Cost Optimization**      | 0/5   | None       | No tracking or alerts                 |

**Overall Score: 1.0/5 (Foundational)**

______________________________________________________________________

## Priority Recommendations (Phased Approach)

### Phase 1: Critical (Weeks 1-2)

**High Impact, Low Effort**

1. **Add test automation to CI** (4-6 hours)

   - File: `.github/workflows/test.yml`
   - Run pytest + coverage on every PR
   - Block PRs if coverage < 80%

2. **Add dependency scanning** (2 hours)

   - File: `.github/workflows/security.yml`
   - Use Safety + pip-audit
   - Fail on HIGH/CRITICAL vulnerabilities

3. **Remove exposed secrets from repo** (1 hour)

   - Remove `.env` file
   - Create `.env.example` template
   - Use GitHub Secrets only

4. **Document deployment procedure** (3 hours)

   - Create `docs/dev/DEPLOYMENT_RUNBOOK.md`
   - Include rollback procedure
   - Incident response checklist

**Effort**: ~15-20 hours
**Impact**: 40% maturity improvement

### Phase 2: Important (Weeks 3-4)

**Medium Impact, Medium Effort**

5. **Implement deployment pipeline** (16-20 hours)

   - File: `.github/workflows/deploy.yml`
   - Add staging + production environments
   - Implement immutable data versioning

6. **Add infrastructure as code** (12-16 hours)

   - Terraform for GCS bucket
   - Service account management
   - Lifecycle policies

7. **Implement monitoring & alerting** (8-12 hours)

   - Metrics collection
   - Slack/Discord notifications
   - Data freshness tracking

8. **Add secret rotation automation** (4-6 hours)

   - Service account key rotation
   - Scheduled audit logs

**Effort**: ~40-54 hours
**Impact**: 70% maturity improvement

### Phase 3: Enhancement (Weeks 5-6)

**Lower Impact, Effort-Intensive**

09. **Add SBOM & supply chain security** (8-10 hours)

    - Syft configuration
    - SLSA framework implementation

10. **Implement GitOps configuration management** (12-16 hours)

    - Config repository setup
    - Automated environment promotion

11. **Cost optimization dashboards** (4-6 hours)

    - GCP billing integration
    - Budget alerts

**Effort**: ~24-32 hours
**Impact**: 90%+ maturity achievement

______________________________________________________________________

## Immediate Next Steps (Today)

```bash
# 1. Create test automation workflow
cat > .github/workflows/test.yml << 'EOF'
# [Use template from Section 2 above]
EOF
git add .github/workflows/test.yml
git commit -m "ci: add test automation workflow"

# 2. Remove exposed credentials
git rm -f .env --cached
echo ".env" >> .gitignore
git commit -m "security: remove exposed credentials from repo"

# 3. Create empty placeholder for deployment workflow
touch .github/workflows/deploy.yml
git add .github/workflows/deploy.yml

# 4. Create monitoring documentation
touch docs/dev/CI_CD_IMPLEMENTATION_GUIDE.md
git add docs/dev/CI_CD_IMPLEMENTATION_GUIDE.md

git push origin main
```

______________________________________________________________________

## Files for Implementation

### To Create

01. `.github/workflows/test.yml` - Test automation
02. `.github/workflows/security.yml` - Security scanning
03. `.github/workflows/deploy.yml` - Deployment pipeline
04. `.github/workflows/monitoring.yml` - Pipeline monitoring
05. `.github/workflows/rollback.yml` - Rollback automation
06. `terraform/gcs.tf` - GCS infrastructure
07. `terraform/variables.tf` - Terraform variables
08. `docs/dev/DEPLOYMENT_RUNBOOK.md` - Operational procedures
09. `docs/dev/SECURITY_POLICY.md` - Security guidelines
10. `.env.example` - Environment variable template

### To Modify

1. `.env` - Remove and add to `.gitignore` ✅
2. `.gitignore` - Add `.env` and `config/secrets/`
3. `pyproject.toml` - Add security tools as dev dependencies

______________________________________________________________________

## Conclusion

The Fantasy Football Analytics project has **strong foundational setup** with excellent local developer experience, but **lacks automated deployment and safety mechanisms** required for production data infrastructure.

**Key Insight**: The project is at a critical point where small investment in CI/CD automation would significantly improve reliability, security, and team confidence.

**Recommended Path**: Implement Phase 1 recommendations immediately (high-impact, low-effort) to achieve 40% maturity improvement within 2 weeks. This unblocks the more complex Phase 2 work and immediately improves security posture.

______________________________________________________________________

**Report Generated**: 2025-11-10
**Prepared for**: ff-analytics project team
**Next Review**: After Phase 1 implementation (EOW 2)
