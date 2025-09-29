#!/bin/bash
# Helper script to create your .env file from template

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "Setting up your .env file"
echo "========================================="

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing .env file"
        exit 0
    fi
fi

# Copy template
cp .env.template .env
echo "✓ Created .env from template"

# Get current GCP project if available
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")

echo ""
echo "Please provide your configuration values:"
echo ""

# GCP Project ID
if [ ! -z "$CURRENT_PROJECT" ]; then
    read -p "GCP Project ID [$CURRENT_PROJECT]: " PROJECT_ID
    PROJECT_ID=${PROJECT_ID:-$CURRENT_PROJECT}
else
    read -p "GCP Project ID: " PROJECT_ID
fi

# Update .env file with actual values
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/GCP_PROJECT_ID=.*/GCP_PROJECT_ID=$PROJECT_ID/" .env
else
    # Linux
    sed -i "s/GCP_PROJECT_ID=.*/GCP_PROJECT_ID=$PROJECT_ID/" .env
fi

echo ""
echo "✓ Updated .env with GCP_PROJECT_ID=$PROJECT_ID"
echo ""
echo "Your .env file has been created with:"
echo "  - GCP_PROJECT_ID=$PROJECT_ID"
echo "  - GCS_BUCKET=ff-analytics"
echo "  - GCS_REGION=us-central1"
echo ""
echo "You can edit .env directly to change other values like:"
echo "  - COMMISSIONER_SHEET_URL"
echo "  - SLEEPER_LEAGUE_ID"
echo "  - DISCORD_WEBHOOK_URL (optional)"
echo ""
echo "Next step: Run ./scripts/setup/gcs_setup.sh to create your GCS infrastructure"
