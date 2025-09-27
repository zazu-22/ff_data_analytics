#!/usr/bin/env python3
"""Test the copied sheet with raw Google API (no gspread)."""

import json
from pathlib import Path

# Get sheet ID from env
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "COMMISSIONER_SHEET_URL" in line and "=" in line:
                sheet_url = line.split("=", 1)[1].strip().strip("'\"")
                break

# New sheet ID (your copy)
SHEET_ID = "1w8ZGzwlmBYBdRW1MLkKO7-KO1TwHojeHRenZwgDsDnY"
print(f"Testing copied sheet: {SHEET_ID}")

creds_path = Path(__file__).parent.parent.parent / "config/secrets/gcp-service-account-key.json"

# Get service account email
with open(creds_path) as f:
    sa_email = json.load(f).get("client_email")

print(f"Service Account: {sa_email}")
print("\n" + "=" * 50)
print("IMPORTANT: Share the copied sheet with this email!")
print("=" * 50 + "\n")

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    print("1. Creating credentials...")
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)

    print("2. Building service...")
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)

    print("3. Getting spreadsheet metadata...")
    # Just try to get the title - minimal API call
    request = service.spreadsheets().get(spreadsheetId=SHEET_ID, fields="properties.title")

    result = request.execute()
    title = result.get("properties", {}).get("title", "Unknown")
    print(f"   ✓ SUCCESS! Sheet title: {title}")

    print("\n4. Trying to read A1 from first sheet...")
    request = service.spreadsheets().values().get(spreadsheetId=SHEET_ID, range="A1")

    result = request.execute()
    values = result.get("values", [])
    if values:
        print(f"   ✓ Cell A1: {values[0]}")
    else:
        print("   ✓ Can read (cell is empty)")

    print("\n✅ The copied sheet works with the service account!")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"Details: {e}")

    if "HttpError" in str(type(e)):
        print("\nThis is likely a permission issue.")
        print(f"Please share the sheet with: {sa_email}")
