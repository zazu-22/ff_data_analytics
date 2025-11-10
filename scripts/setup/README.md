# Setup Scripts

This directory contains one-time setup and validation scripts for the FF Analytics pipeline infrastructure.

## Scripts

### 1. `env_setup.sh`

**Purpose**: Interactive helper to create your `.env` file from the template

**Usage**:

```bash
./scripts/setup/env_setup.sh
```

**What it does**:

- Copies `.env.example` to `.env`
- Prompts for your GCP project ID
- Auto-detects current gcloud project
- Updates the `.env` file with your values

### 2. `gcs_setup.sh`

**Purpose**: Creates and configures the complete GCS infrastructure

**Usage**:

```bash
./scripts/setup/gcs_setup.sh
```

**What it does**:

- Creates GCS bucket with folder structure (raw/, stage/, mart/, ops/)
- Applies lifecycle policies for cost optimization
- Creates service account with appropriate IAM roles
- Optionally generates service account key for CI/CD

**Prerequisites**:

- `.env` file with GCP_PROJECT_ID configured
- `gcloud` CLI installed and authenticated
- Appropriate permissions to create buckets and service accounts

### 3. `gcs_validate.sh`

**Purpose**: Validates that GCS infrastructure is correctly configured

**Usage**:

```bash
./scripts/setup/gcs_validate.sh
```

**What it does**:

- Verifies bucket exists and is accessible
- Checks folder structure
- Validates lifecycle policies are applied
- Confirms service account exists with proper permissions
- Tests read/write operations
- Checks for service account key (needed for CI/CD)

**Output**: Color-coded validation report with any errors or warnings

## Setup Workflow

1. **First time setup**:

   ```bash
   # 1. Create your .env file
   ./scripts/setup/env_setup.sh

   # 2. Create GCS infrastructure
   ./scripts/setup/gcs_setup.sh

   # 3. Validate everything works
   ./scripts/setup/gcs_validate.sh
   ```

2. **Generate service account key for GitHub Actions**:

   ```bash
   # If not done during setup
   gcloud iam service-accounts keys create \
     config/secrets/gcp-service-account-key.json \
     --iam-account=ff-analytics-pipeline@YOUR_PROJECT.iam.gserviceaccount.com

   # Encode for GitHub secrets
   base64 -i config/secrets/gcp-service-account-key.json | pbcopy
   ```

3. **Add to GitHub Secrets**:

   - Go to Settings → Secrets and variables → Actions
   - Add secret named `GOOGLE_APPLICATION_CREDENTIALS_JSON`
   - Paste the base64-encoded key

## Notes

- All scripts automatically load configuration from the project root `.env` file
- Scripts are idempotent - safe to run multiple times
- Service account keys should NEVER be committed to git
- The `config/secrets/` directory is gitignored for security
