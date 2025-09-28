#!/bin/bash
# Prepare secrets for GitHub Actions configuration

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "========================================="
echo "GitHub Secrets Preparation"
echo "========================================="
echo ""

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | grep -v '^$' | xargs)
fi

# Check for service account key
KEY_PATH="${GOOGLE_APPLICATION_CREDENTIALS:-$PROJECT_ROOT/config/secrets/gcp-service-account-key.json}"

if [ ! -f "$KEY_PATH" ]; then
    echo -e "${YELLOW}⚠ Service account key not found at $KEY_PATH${NC}"
    echo "Please run ./scripts/setup/gcs_setup.sh first to generate the key"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found service account key at $KEY_PATH"
echo ""

# Encode the key for GitHub
echo "Encoding service account key for GitHub..."
ENCODED_KEY=$(base64 -i "$KEY_PATH" | tr -d '\n')

echo -e "${GREEN}✓${NC} Key encoded successfully"
echo ""

# Save to temporary file for easy access
TEMP_FILE="$PROJECT_ROOT/.github_secrets_temp.txt"
cat > "$TEMP_FILE" << EOF
========================================
GitHub Secrets to Configure
========================================

REQUIRED SECRETS:
-----------------
1. GOOGLE_APPLICATION_CREDENTIALS_JSON
   Value has been copied to your clipboard!
   Purpose: Authenticates with GCS and Google Sheets

2. GCP_PROJECT_ID
   Value: ${GCP_PROJECT_ID}
   Purpose: Identifies the GCP project for resources

3. GCS_BUCKET
   Value: ${GCS_BUCKET}
   Purpose: Target bucket for data storage

4. COMMISSIONER_SHEET_URL
   Value: ${COMMISSIONER_SHEET_URL:-not set in .env}
   Purpose: Google Sheet with league data (source of truth)

5. COMMISSIONER_SHEET_ID
   Value: ${COMMISSIONER_SHEET_ID:-not set in .env}
   Purpose: Commissioner Sheet ID for copy workflow

6. LEAGUE_SHEET_COPY_ID
   Value: ${LEAGUE_SHEET_COPY_ID:-not set in .env}
   Purpose: Destination sheet for Commissioner data copy

7. LOG_PARENT_ID
   Value: ${LOG_PARENT_ID:-not set in .env}
   Purpose: Shared Drive ID for ingestion logs

8. SLEEPER_LEAGUE_ID
   Value: ${SLEEPER_LEAGUE_ID}
   Purpose: Identifies your Sleeper league for API calls

OPTIONAL SECRETS:
-----------------
9. SPORTS_DATA_IO_API_KEY
   Value: ${SPORTS_DATA_IO_API_KEY:-not set in .env}
   Purpose: Sports Data IO API access for additional data

10. DISCORD_WEBHOOK_URL
   Value: ${DISCORD_WEBHOOK_URL:-not set in .env}
   Purpose: Notifications for pipeline status (recommended)

========================================
How to add these to GitHub:
========================================

1. Go to your repository on GitHub
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret with the name and value above
5. Save each secret

Repository URL:
https://github.com/YOUR_USERNAME/ff_data_analytics/settings/secrets/actions

========================================
EOF

# Copy to clipboard based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "$ENCODED_KEY" | pbcopy
    echo -e "${GREEN}✓${NC} Service account key copied to clipboard!"
elif command -v xclip &> /dev/null; then
    echo "$ENCODED_KEY" | xclip -selection clipboard
    echo -e "${GREEN}✓${NC} Service account key copied to clipboard!"
else
    echo -e "${YELLOW}Note: Could not copy to clipboard automatically${NC}"
    echo "The encoded key has been saved to: $TEMP_FILE"
fi

echo ""
echo -e "${BLUE}Instructions:${NC}"
echo "1. The encoded service account key is in your clipboard"
echo "2. Go to your GitHub repository settings"
echo "3. Navigate to Secrets and variables → Actions"
echo "4. Create a new secret named: GOOGLE_APPLICATION_CREDENTIALS_JSON"
echo "5. Paste the value from your clipboard"
echo ""
echo "Core secrets to add:"
echo "  - GCP_PROJECT_ID = ${GCP_PROJECT_ID}"
echo "  - GCS_BUCKET = ${GCS_BUCKET}"
echo "  - COMMISSIONER_SHEET_ID = ${COMMISSIONER_SHEET_ID:-not set in .env}"
echo "  - LEAGUE_SHEET_COPY_ID = ${LEAGUE_SHEET_COPY_ID:-not set in .env}"
echo "  - LOG_PARENT_ID = ${LOG_PARENT_ID:-not set in .env}"
echo ""

# Show the secrets file
echo "Full instructions saved to: $TEMP_FILE"
echo ""
echo -e "${YELLOW}⚠ Important:${NC}"
echo "- Delete $TEMP_FILE after adding secrets to GitHub"
echo "- Never commit these values to your repository"
echo ""

# Ask if user wants to see all configured values
read -p "Show all configured secret values? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Required Secrets:"
    echo "  - GCP_PROJECT_ID = ${GCP_PROJECT_ID}"
    echo "  - GCS_BUCKET = ${GCS_BUCKET}"
    echo "  - SLEEPER_LEAGUE_ID = ${SLEEPER_LEAGUE_ID}"
    echo "  - COMMISSIONER_SHEET_URL = ${COMMISSIONER_SHEET_URL:-not configured}"
    echo "  - COMMISSIONER_SHEET_ID = ${COMMISSIONER_SHEET_ID:-not configured}"
    echo "  - LEAGUE_SHEET_COPY_ID = ${LEAGUE_SHEET_COPY_ID:-not configured}"
    echo "  - LOG_PARENT_ID = ${LOG_PARENT_ID:-not configured}"
    echo ""
    echo "Optional Secrets:"
    echo "  - SPORTS_DATA_IO_API_KEY = ${SPORTS_DATA_IO_API_KEY:-not configured}"
    echo "  - DISCORD_WEBHOOK_URL = ${DISCORD_WEBHOOK_URL:-not configured}"
fi

echo ""
echo "========================================="
