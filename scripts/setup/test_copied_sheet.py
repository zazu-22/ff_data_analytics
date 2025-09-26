#!/usr/bin/env python3
"""Test if the copied Commissioner Sheet works with the service account."""

import json
import os
from pathlib import Path

# Load environment
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    print("Loading .env file...")
    with open(env_file) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value.strip("'\"")

print("="*50)
print("Testing Copied Commissioner Sheet")
print("="*50)

# Get the new sheet URL from env
sheet_url = os.environ.get("COMMISSIONER_SHEET_URL", "")
print(f"Sheet URL: {sheet_url[:60]}...")

# Extract sheet ID
if "docs.google.com/spreadsheets" in sheet_url:
    sheet_id = sheet_url.split("/d/")[1].split("/")[0]
else:
    sheet_id = sheet_url

print(f"Sheet ID: {sheet_id}")

# Test with gspread first (simpler API)
try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("Missing gspread. Install with: uv add gspread google-auth")
    exit(1)

creds_path = Path(__file__).parent.parent.parent / "config/secrets/gcp-service-account-key.json"

# Get service account email
with open(creds_path) as f:
    sa_email = json.load(f).get("client_email")
print(f"Service Account: {sa_email}")

print("\n" + "-"*50)
print("IMPORTANT: Make sure you've shared the copied sheet with:")
print(f"  {sa_email}")
print("Give it 'Viewer' or 'Editor' access")
print("-"*50 + "\n")

try:
    print("1. Authenticating...")
    scope = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)
    gc = gspread.authorize(creds)
    print("   ✓ Authenticated")

    print("\n2. Opening sheet...")
    sheet = gc.open_by_key(sheet_id)
    print(f"   ✓ Opened: {sheet.title}")

    print("\n3. Listing worksheets...")
    worksheets = sheet.worksheets()
    print(f"   ✓ Found {len(worksheets)} worksheets:")
    for i, ws in enumerate(worksheets[:10]):
        print(f"      {i+1}. {ws.title}")

    print("\n4. Testing data read from 'Eric' tab...")
    eric_ws = None
    for ws in worksheets:
        if ws.title == "Eric":
            eric_ws = ws
            break

    if not eric_ws:
        print("   ⚠ 'Eric' tab not found, trying first worksheet...")
        eric_ws = worksheets[0]

    print(f"   Reading from: {eric_ws.title}")

    # Try different read methods
    print("\n   Method 1: Single cell (A1)...")
    try:
        value = eric_ws.acell('A1').value
        print(f"   ✓ Cell A1 = '{value}'")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    print("\n   Method 2: Small range (A1:C3)...")
    try:
        values = eric_ws.get('A1:C3')
        print(f"   ✓ Got {len(values)} rows")
        if values:
            print(f"   First row: {values[0]}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    print("\n   Method 3: Batch get...")
    try:
        values = eric_ws.batch_get(['A1:C1', 'A2:C2'])
        print(f"   ✓ Batch get succeeded")
        for i, val in enumerate(values):
            print(f"   Range {i+1}: {val}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    print("\n" + "="*50)
    print("✅ SUCCESS! The copied sheet works!")
    print("="*50)
    print("\nYou can now use this copied sheet for your pipeline.")
    print("Update your .env file with:")
    print(f"COMMISSIONER_SHEET_URL={sheet_url}")

except gspread.exceptions.APIError as e:
    if "403" in str(e):
        print(f"\n❌ Permission denied!")
        print(f"\nMake sure you've shared the copied sheet with:")
        print(f"  {sa_email}")
    else:
        print(f"\n❌ API Error: {e}")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()