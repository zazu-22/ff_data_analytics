#!/usr/bin/env python3
"""Test Google Sheets access using raw API instead of gspread."""

import json
import os
from pathlib import Path

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Installing required packages...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "uv", "add", "google-api-python-client"])
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

print("=" * 50)
print("Testing with Raw Google Sheets API")
print("=" * 50)

# Load .env
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value.strip("'\"")

creds_path = Path(__file__).parent.parent.parent / "config/secrets/gcp-service-account-key.json"
sheet_url = os.environ.get("COMMISSIONER_SHEET_URL", "")

# Extract sheet ID
if "docs.google.com/spreadsheets" in sheet_url:
    sheet_id = sheet_url.split("/d/")[1].split("/")[0]
else:
    sheet_id = sheet_url

print(f"Sheet ID: {sheet_id}")
print(f"Credentials: {creds_path}")

try:
    # Authenticate
    print("\n1. Authenticating...")
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)

    # Build the service
    print("2. Building Sheets service...")
    service = build('sheets', 'v4', credentials=creds)

    # Get spreadsheet metadata
    print("3. Getting spreadsheet metadata...")
    spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    print(f"   ✓ Title: {spreadsheet['properties']['title']}")
    print(f"   ✓ Sheets: {len(spreadsheet['sheets'])} worksheets")

    # List first few sheet names
    for i, sheet in enumerate(spreadsheet['sheets'][:5]):
        title = sheet['properties']['title']
        rows = sheet['properties']['gridProperties']['rowCount']
        cols = sheet['properties']['gridProperties']['columnCount']
        print(f"      {i+1}. {title} ({rows}×{cols})")

    # Try to read a specific range from a smaller sheet
    print("\n4. Testing cell read from 'Eric' worksheet...")
    range_name = 'Eric!A1:C3'  # Small range from Eric sheet

    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()

        values = result.get('values', [])

        if not values:
            print('   ⚠ No data found in range')
        else:
            print(f'   ✓ Successfully read {len(values)} rows')
            for i, row in enumerate(values):
                print(f'      Row {i+1}: {row[:3]}')  # Show first 3 columns

        print("\n" + "=" * 50)
        print("✅ SUCCESS: Can read cells using raw API!")
        print("=" * 50)

    except HttpError as error:
        print(f'   ❌ API Error reading cells: {error}')
        print(f'   Error details: {error.resp.status} - {error.content}')

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()