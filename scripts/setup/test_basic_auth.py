#!/usr/bin/env python3
"""Minimal test to see where the timeout occurs."""

import json
import os
import sys
import time
from pathlib import Path

print("Starting basic auth test...")
start_time = time.time()

# Load env
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value.strip("'\"")

sheet_url = os.environ.get("COMMISSIONER_SHEET_URL", "")
if "docs.google.com/spreadsheets" in sheet_url:
    sheet_id = sheet_url.split("/d/")[1].split("/")[0]
else:
    sheet_id = sheet_url

print(f"Sheet ID: {sheet_id}")
print(f"Time: {time.time() - start_time:.2f}s")

try:
    print("\n1. Importing libraries...")
    import gspread
    from google.oauth2.service_account import Credentials
    print(f"   ✓ Imports done ({time.time() - start_time:.2f}s)")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

creds_path = Path(__file__).parent.parent.parent / "config/secrets/gcp-service-account-key.json"

try:
    print("\n2. Loading credentials...")
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)
    print(f"   ✓ Credentials loaded ({time.time() - start_time:.2f}s)")

    print("\n3. Authorizing gspread...")
    gc = gspread.authorize(creds)
    print(f"   ✓ Authorized ({time.time() - start_time:.2f}s)")

    print("\n4. Opening sheet by key...")
    print(f"   Attempting to open: {sheet_id}")
    sheet = gc.open_by_key(sheet_id)
    print(f"   ✓ Sheet opened! ({time.time() - start_time:.2f}s)")
    print(f"   Title: {sheet.title}")

    print("\n5. Getting worksheets...")
    worksheets = sheet.worksheets()
    print(f"   ✓ Got {len(worksheets)} worksheets ({time.time() - start_time:.2f}s)")

    print("\n6. Trying to read one cell...")
    ws = worksheets[0]
    print(f"   From worksheet: {ws.title}")
    cell = ws.acell('A1')
    print(f"   ✓ Read cell A1: '{cell.value}' ({time.time() - start_time:.2f}s)")

    print("\n✅ ALL TESTS PASSED!")

except Exception as e:
    print(f"\n❌ Failed at step: {e}")
    print(f"   Time when failed: {time.time() - start_time:.2f}s")
    import traceback
    traceback.print_exc()