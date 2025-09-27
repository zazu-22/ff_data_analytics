#!/usr/bin/env python3
"""Debug why cell reads are timing out."""

import json
import os
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

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

# Get service account email
with open(creds_path) as f:
    sa_email = json.load(f).get("client_email")

print("Debug Information:")
print(f"Service Account: {sa_email}")
print(f"Sheet URL: {sheet_url[:50]}...")

try:
    # Try with both scopes
    print("\nTrying with full spreadsheets + drive scopes...")
    scope = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)
    client = gspread.authorize(creds)

    sheet_id = (
        sheet_url.split("/d/")[1].split("/")[0] if "docs.google.com" in sheet_url else sheet_url
    )
    sheet = client.open_by_key(sheet_id)

    # Get worksheet info
    worksheets = sheet.worksheets()
    print(f"✓ Can list {len(worksheets)} worksheets")

    # Try metadata instead of cells
    print("\nTrying to get worksheet metadata...")
    ws = worksheets[1]  # Eric worksheet
    print(f"Worksheet: {ws.title}")
    print(f"ID: {ws.id}")

    # Try to get properties without reading cells
    props = ws._properties
    print(f"Properties available: {list(props.keys())}")

    if "gridProperties" in props:
        grid = props["gridProperties"]
        print(f"Rows: {grid.get('rowCount', 'unknown')}")
        print(f"Columns: {grid.get('columnCount', 'unknown')}")

    print("\n" + "=" * 50)
    print("IMPORTANT: The issue appears to be with reading cell data.")
    print("This could mean:")
    print("1. The worksheet is shared but cell data is protected")
    print("2. The worksheet has special permissions")
    print("3. Network/firewall issue with data requests")
    print("\nTo fix:")
    print(f"1. Open the sheet: {sheet_url}")
    print(f"2. Check sharing settings - ensure {sa_email}")
    print("   has 'Viewer' access to the entire sheet")
    print("3. Check if there are any cell-level protections")

except Exception as e:
    print(f"\nError: {e}")
