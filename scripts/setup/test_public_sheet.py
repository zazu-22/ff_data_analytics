#!/usr/bin/env python3
"""Test if service account can read ANY sheet, using a public test sheet."""

import json
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

print("Testing Google Sheets API with a public sheet...")

# Use a known public Google Sheet for testing
# This is a public demo sheet that anyone can read
TEST_SHEET_ID = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"  # Google's example sheet

creds_path = Path(__file__).parent.parent.parent / "config/secrets/gcp-service-account-key.json"

try:
    print("\n1. Authenticating...")
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)

    print("2. Building service...")
    service = build('sheets', 'v4', credentials=creds)

    print("3. Reading public test sheet...")
    # Try to read from Google's example sheet
    result = service.spreadsheets().values().get(
        spreadsheetId=TEST_SHEET_ID,
        range='Class Data!A1:C3'
    ).execute()

    values = result.get('values', [])
    if values:
        print(f"✓ Successfully read {len(values)} rows from public sheet")
        print(f"  First row: {values[0]}")
    else:
        print("⚠ No data in public sheet")

    print("\n✅ Service account CAN read Google Sheets!")
    print("The issue is specific to your Commissioner Sheet.")

except Exception as e:
    print(f"\n❌ Cannot read even public sheets: {e}")
    print("This suggests a service account or API configuration issue.")