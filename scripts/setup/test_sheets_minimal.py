#!/usr/bin/env python3
"""Minimal test - just check if we can read a single cell."""

import json
import os
import sys
from pathlib import Path

# Add timeout protection
import signal

def timeout_handler(signum, frame):
    print("\n⏱️ Operation timed out after 10 seconds")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("Missing packages. Install with: uv add gspread google-auth")
    sys.exit(1)


print("Testing Google Sheets cell read access...")

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

try:
    # Set 10 second timeout for entire operation
    signal.alarm(10)

    print("1. Authenticating...")
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)
    client = gspread.authorize(creds)

    print("2. Opening sheet...")
    sheet_id = sheet_url.split("/d/")[1].split("/")[0] if "docs.google.com" in sheet_url else sheet_url
    sheet = client.open_by_key(sheet_id)

    print("3. Getting worksheets...")
    worksheets = sheet.worksheets()
    print(f"   Found {len(worksheets)} worksheets")

    # Try to read from a specific worksheet by name
    print("4. Testing cell read...")

    # Try to find a small worksheet (not TRANSACTIONS)
    target_ws = None
    for ws in worksheets:
        if ws.title != "TRANSACTIONS":
            target_ws = ws
            break

    if not target_ws:
        target_ws = worksheets[0]

    print(f"   Reading from: {target_ws.title}")

    # Just try to get one cell
    cell_value = target_ws.acell('A1').value
    print(f"   ✓ Cell A1 value: {cell_value}")

    # Cancel timeout
    signal.alarm(0)

    print("\n✅ SUCCESS: Can read cells from Google Sheets!")

except Exception as e:
    signal.alarm(0)  # Cancel timeout
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    sys.exit(1)