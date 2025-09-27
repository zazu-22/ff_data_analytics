#!/usr/bin/env python3
"""Test different API methods to diagnose the timeout issue."""

import time
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

print("Diagnostic test for Commissioner Sheet access...")

creds_path = Path(__file__).parent.parent.parent / "config/secrets/gcp-service-account-key.json"

# Your Commissioner Sheet
SHEET_ID = "1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY"

try:
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)
    service = build("sheets", "v4", credentials=creds)

    print("\n1. Testing metadata access (this works)...")
    start = time.time()
    spreadsheet = (
        service.spreadsheets()
        .get(spreadsheetId=SHEET_ID, fields="properties.title,sheets.properties")
        .execute()
    )
    print(f"   ✓ Got metadata in {time.time()-start:.2f}s")
    print(f"   Title: {spreadsheet['properties']['title']}")

    # Try batchGet with very specific parameters
    print("\n2. Testing batchGet with minimal range...")
    start = time.time()
    try:
        result = (
            service.spreadsheets()
            .values()
            .batchGet(
                spreadsheetId=SHEET_ID,
                ranges=["Eric!A1"],  # Just one cell
                majorDimension="ROWS",
                valueRenderOption="UNFORMATTED_VALUE",  # Raw values, no formatting
                dateTimeRenderOption="FORMATTED_STRING",
            )
            .execute()
        )
        print(f"   ✓ BatchGet succeeded in {time.time()-start:.2f}s")
        print(f"   Result: {result.get('valueRanges', [])}")
    except Exception as e:
        print(f"   ✗ BatchGet failed after {time.time()-start:.2f}s: {e}")

    # Try with different API parameters
    print("\n3. Testing with FORMULA valueRenderOption...")
    start = time.time()
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SHEET_ID,
                range="Eric!A1",
                valueRenderOption="FORMULA",  # Get formulas instead of values
            )
            .execute()
        )
        print(f"   ✓ Formula read succeeded in {time.time()-start:.2f}s")
        print(f"   Result: {result.get('values', [])}")
    except Exception as e:
        print(f"   ✗ Formula read failed after {time.time()-start:.2f}s: {e}")

    # Try getting just the sheet properties without values
    print("\n4. Testing sheet properties only...")
    start = time.time()
    try:
        result = (
            service.spreadsheets()
            .get(
                spreadsheetId=SHEET_ID,
                ranges=["Eric"],
                includeGridData=False,  # Don't include cell data
            )
            .execute()
        )
        print(f"   ✓ Properties succeeded in {time.time()-start:.2f}s")
        eric_sheet = next(s for s in result["sheets"] if s["properties"]["title"] == "Eric")
        print(f"   Eric sheet ID: {eric_sheet['properties']['sheetId']}")
    except Exception as e:
        print(f"   ✗ Properties failed: {e}")

    print("\n" + "=" * 50)
    print("Summary:")
    print("- Metadata access: ✓ Works")
    print("- Cell value reads: ✗ Timeout")
    print("\nThis pattern suggests the issue is specifically with")
    print("reading cell VALUES (not metadata) from this sheet.")

except Exception as e:
    print(f"\nError: {e}")
