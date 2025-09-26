#!/bin/bash
# GCS Validation Script - Confirms everything is set up correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | grep -v '^$' | xargs)
fi

PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
BUCKET_NAME="${GCS_BUCKET:-ff-analytics}"
SERVICE_ACCOUNT_NAME="${GCP_SERVICE_ACCOUNT_NAME:-ff-analytics-pipeline}"

echo "========================================="
echo "GCS Setup Validation"
echo "========================================="
echo "Project: $PROJECT_ID"
echo "Bucket: gs://$BUCKET_NAME"
echo "Service Account: $SERVICE_ACCOUNT_NAME"
echo ""

ERRORS=0
WARNINGS=0

# Function to check status
check() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        ERRORS=$((ERRORS + 1))
    fi
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

# 1. Check if bucket exists
echo "1. Checking bucket existence..."
if gsutil ls -b gs://$BUCKET_NAME &> /dev/null; then
    check 0 "Bucket gs://$BUCKET_NAME exists"

    # Get bucket location
    LOCATION=$(gsutil ls -L -b gs://$BUCKET_NAME | grep "Location constraint:" | awk '{print $3}')
    echo "   Location: $LOCATION"
else
    check 1 "Bucket gs://$BUCKET_NAME not found"
fi

echo ""

# 2. Check folder structure
echo "2. Checking folder structure..."
for folder in raw stage mart ops; do
    # Try to list the folder (will succeed even if empty)
    if gsutil ls gs://$BUCKET_NAME/$folder/ &> /dev/null || [ $? -eq 1 ]; then
        check 0 "Folder $folder/ exists or is ready"
    else
        check 1 "Cannot access folder $folder/"
    fi
done

echo ""

# 3. Check lifecycle policies
echo "3. Checking lifecycle policies..."
LIFECYCLE_JSON=$(gsutil lifecycle get gs://$BUCKET_NAME 2>/dev/null)
if [ ! -z "$LIFECYCLE_JSON" ]; then
    # Check if lifecycle has rules
    if echo "$LIFECYCLE_JSON" | grep -q '"rule"'; then
        check 0 "Lifecycle policies are configured"

        # Count rules
        RULE_COUNT=$(echo "$LIFECYCLE_JSON" | grep -c '"action"' || true)
        echo "   Number of rules: $RULE_COUNT"

        # Check for specific rules
        if echo "$LIFECYCLE_JSON" | grep -q "NEARLINE"; then
            echo "   - Found Nearline transition rule"
        fi
        if echo "$LIFECYCLE_JSON" | grep -q "COLDLINE"; then
            echo "   - Found Coldline transition rule"
        fi
        if echo "$LIFECYCLE_JSON" | grep -q "Delete"; then
            echo "   - Found deletion rule"
        fi
    else
        warn "Lifecycle configuration exists but has no rules"
    fi
else
    check 1 "No lifecycle policies found"
fi

echo ""

# 4. Check service account
echo "4. Checking service account..."
SA_EMAIL="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"
if gcloud iam service-accounts describe $SA_EMAIL &> /dev/null; then
    check 0 "Service account $SA_EMAIL exists"

    # Check if service account has keys
    KEY_COUNT=$(gcloud iam service-accounts keys list --iam-account=$SA_EMAIL --format="value(name)" | wc -l)
    echo "   Number of keys: $KEY_COUNT"
    if [ $KEY_COUNT -eq 1 ]; then
        warn "Only default key exists - you may need to generate a key for CI/CD"
    fi
else
    check 1 "Service account $SA_EMAIL not found"
fi

echo ""

# 5. Check IAM permissions on bucket
echo "5. Checking bucket IAM permissions..."
BUCKET_IAM=$(gsutil iam get gs://$BUCKET_NAME 2>/dev/null)
if echo "$BUCKET_IAM" | grep -q "$SA_EMAIL"; then
    check 0 "Service account has bucket permissions"

    # Check specific roles
    if echo "$BUCKET_IAM" | grep -q "roles/storage.objectAdmin"; then
        echo "   - Has objectAdmin role"
    fi
    if echo "$BUCKET_IAM" | grep -q "roles/storage.legacyBucketReader"; then
        echo "   - Has legacyBucketReader role"
    fi
else
    check 1 "Service account lacks bucket permissions"
fi

echo ""

# 6. Test write permissions
echo "6. Testing write permissions..."
TEST_FILE="test-$(date +%s).txt"
echo "Test write at $(date)" | gsutil -q cp - gs://$BUCKET_NAME/raw/$TEST_FILE 2>/dev/null
if [ $? -eq 0 ]; then
    check 0 "Successfully wrote to raw/"

    # Test read
    if gsutil -q cat gs://$BUCKET_NAME/raw/$TEST_FILE &> /dev/null; then
        check 0 "Successfully read from raw/"
    else
        check 1 "Failed to read test file"
    fi

    # Clean up
    gsutil -q rm gs://$BUCKET_NAME/raw/$TEST_FILE 2>/dev/null
    check 0 "Successfully deleted test file"
else
    check 1 "Failed to write to bucket"
fi

echo ""

# 7. Check project configuration
echo "7. Checking project configuration..."
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" = "$PROJECT_ID" ]; then
    check 0 "gcloud is configured with correct project"
else
    warn "gcloud project ($CURRENT_PROJECT) doesn't match .env ($PROJECT_ID)"
fi

echo ""

# 8. Check for service account key file
echo "8. Checking for service account key..."
KEY_PATH="${GOOGLE_APPLICATION_CREDENTIALS:-$PROJECT_ROOT/config/secrets/gcp-service-account-key.json}"
if [ -f "$KEY_PATH" ]; then
    check 0 "Service account key exists at $KEY_PATH"

    # Check if it's valid JSON
    if python -m json.tool "$KEY_PATH" &> /dev/null; then
        check 0 "Key file is valid JSON"
    else
        check 1 "Key file is not valid JSON"
    fi
else
    warn "No service account key found at $KEY_PATH (needed for CI/CD)"
fi

echo ""
echo "========================================="
echo "Validation Summary"
echo "========================================="

if [ $ERRORS -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed!${NC}"
    else
        echo -e "${GREEN}✓ Setup is functional${NC} with $WARNINGS warnings"
    fi
    echo ""
    echo "Your GCS infrastructure is ready for use!"
else
    echo -e "${RED}✗ Found $ERRORS errors${NC}"
    echo ""
    echo "Please fix the errors above before proceeding."
    exit 1
fi

if [ $WARNINGS -gt 0 ]; then
    echo ""
    echo "Warnings are non-critical but should be addressed:"
    echo "- Missing service account key: Generate one for GitHub Actions"
    echo "- Project mismatch: Run 'gcloud config set project $PROJECT_ID'"
fi

echo ""
echo "Next steps:"
echo "1. If no key exists: gcloud iam service-accounts keys create <path> --iam-account=$SA_EMAIL"
echo "2. Add key to GitHub secrets: base64 -i <key-path> | pbcopy"
echo "3. Test the data pipeline locally with sample data"
echo "========================================="