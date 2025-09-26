#!/bin/bash
# GCS Setup Script for FF Analytics Data Pipeline
# This script creates the bucket structure, lifecycle policies, and service accounts

set -e  # Exit on error

# Get the project root directory (two levels up from scripts/setup)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Load environment variables from .env file if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "Loading configuration from .env file..."
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | grep -v '^$' | xargs)
fi

# Configuration (with defaults from environment or fallback values)
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
BUCKET_NAME="${GCS_BUCKET:-ff-analytics}"
SERVICE_ACCOUNT_NAME="${GCP_SERVICE_ACCOUNT_NAME:-ff-analytics-pipeline}"
REGION="${GCS_REGION:-us-central1}"

echo "========================================="
echo "FF Analytics GCS Setup"
echo "========================================="
echo "Project ID: $PROJECT_ID"
echo "Bucket: gs://$BUCKET_NAME"
echo "Region: $REGION"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Prompt for project ID if not set
if [ "$PROJECT_ID" = "your-project-id" ]; then
    read -p "Enter your GCP Project ID: " PROJECT_ID
fi

echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Create bucket if it doesn't exist
echo ""
echo "Creating bucket gs://$BUCKET_NAME..."
if gsutil ls -b gs://$BUCKET_NAME &> /dev/null; then
    echo "Bucket already exists, skipping creation"
else
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME
    echo "Bucket created successfully"
fi

# Create folder structure
echo ""
echo "Creating folder structure..."
echo "test" | gsutil cp - gs://$BUCKET_NAME/raw/.keep
echo "test" | gsutil cp - gs://$BUCKET_NAME/stage/.keep
echo "test" | gsutil cp - gs://$BUCKET_NAME/mart/.keep
echo "test" | gsutil cp - gs://$BUCKET_NAME/ops/.keep
gsutil rm gs://$BUCKET_NAME/**/.keep
echo "Folder structure created"

# TODO(human): Implement lifecycle policy configuration
# Your task is to create the lifecycle.json file that defines storage class transitions
# Consider: Standard -> Nearline (30 days) -> Coldline (180 days) for raw/
# Keep mart/ in Standard for performance

# Apply lifecycle policy
echo ""
echo "Applying lifecycle policies..."
if [ -f "$PROJECT_ROOT/config/gcs/lifecycle.json" ]; then
    gsutil lifecycle set "$PROJECT_ROOT/config/gcs/lifecycle.json" gs://$BUCKET_NAME
    echo "Lifecycle policies applied"
else
    echo "Warning: config/gcs/lifecycle.json not found, skipping lifecycle setup"
fi

# Create service account
echo ""
echo "Creating service account..."
SA_EMAIL="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"

if gcloud iam service-accounts describe $SA_EMAIL &> /dev/null; then
    echo "Service account already exists"
else
    gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
        --display-name="FF Analytics Pipeline Service Account" \
        --description="Service account for FF Analytics data pipeline"
    echo "Service account created"
fi

# Grant necessary permissions
echo ""
echo "Granting IAM permissions..."
# Storage permissions for the bucket
gsutil iam ch serviceAccount:$SA_EMAIL:objectAdmin gs://$BUCKET_NAME
gsutil iam ch serviceAccount:$SA_EMAIL:legacyBucketReader gs://$BUCKET_NAME

# BigQuery permissions (for future dbt integration)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/bigquery.dataEditor" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/bigquery.jobUser" \
    --condition=None

echo "Permissions granted"

# Generate service account key
echo ""
read -p "Generate service account key? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    KEY_FILE="$PROJECT_ROOT/config/secrets/gcp-service-account-key.json"
    mkdir -p "$PROJECT_ROOT/config/secrets"
    gcloud iam service-accounts keys create $KEY_FILE \
        --iam-account=$SA_EMAIL
    echo "Service account key saved to $KEY_FILE"
    echo ""
    echo "IMPORTANT: Add $KEY_FILE to .gitignore and never commit it!"
    echo "For GitHub Actions, encode it with: base64 -i $KEY_FILE | pbcopy"
    echo "Then add as GOOGLE_APPLICATION_CREDENTIALS_JSON secret"
else
    echo "Skipping key generation"
fi

echo ""
echo "========================================="
echo "Setup Summary"
echo "========================================="
echo "✅ Bucket: gs://$BUCKET_NAME"
echo "✅ Service Account: $SA_EMAIL"
echo "✅ Folder Structure: raw/, stage/, mart/, ops/"
echo ""
echo "Next Steps:"
echo "1. Add service account key to GitHub Secrets"
echo "2. Test with: gsutil ls gs://$BUCKET_NAME/"
echo "========================================="
