#!/usr/bin/env python3
"""Quick test for Google Sheets API access - minimal read."""

import json
import os
import sys
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("Missing packages. Install with: uv add gspread google-auth")
    sys.exit(1)


def quick_test():
    """Quick minimal test of sheet access."""
    print("=" * 50)
    print("Google Sheets Quick Access Test")
    print("=" * 50)

    # Load .env
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value.strip("'\"")

    # Get paths
    creds_path = Path(__file__).parent.parent.parent / "config/secrets/gcp-service-account-key.json"
    sheet_url = os.environ.get("COMMISSIONER_SHEET_URL", "")

    if not creds_path.exists():
        print(f"❌ No credentials at: {creds_path}")
        return False

    if not sheet_url:
        print("❌ COMMISSIONER_SHEET_URL not set")
        return False

    print(f"\nCredentials: {creds_path}")
    print(f"Sheet URL: {sheet_url[:50]}...")

    try:
        # Get service account email first
        with open(creds_path) as f:
            creds_json = json.load(f)
            sa_email = creds_json.get("client_email")
            project_id = creds_json.get("project_id")

        print(f"Service Account: {sa_email}")
        print(f"Project: {project_id}")

        print("\nAuthenticating...")
        scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)
        client = gspread.authorize(creds)
        print("✓ Authenticated")

        print("\nOpening sheet...")
        # Extract sheet ID
        if "docs.google.com/spreadsheets" in sheet_url:
            sheet_id = sheet_url.split("/d/")[1].split("/")[0]
        else:
            sheet_id = sheet_url

        print(f"Sheet ID: {sheet_id}")

        # Just try to open it - don't read data yet
        sheet = client.open_by_key(sheet_id)
        print(f"✓ Opened: {sheet.title}")

        # Get worksheet list only
        print("\nGetting worksheet list...")
        worksheets = sheet.worksheets()
        print(f"✓ Found {len(worksheets)} worksheets")

        # Just list them, don't read
        for i, ws in enumerate(worksheets[:5]):
            print(f"  {i+1}. {ws.title}")

        # Now test actual cell reading on a smaller worksheet
        print("\nTesting cell read access...")
        # Use second worksheet (Eric) to avoid large TRANSACTIONS tab
        test_ws_idx = 1 if len(worksheets) > 1 else 0
        test_ws = worksheets[test_ws_idx]
        print(f"Reading from worksheet: '{test_ws.title}'")

        try:
            # Read just the first 3x3 cells
            sample_data = test_ws.get("A1:C3")
            if sample_data:
                print(f"✓ Successfully read {len(sample_data)} rows × {len(sample_data[0]) if sample_data else 0} columns")
                # Show first row as sample
                if sample_data[0]:
                    print(f"  First row sample: {sample_data[0][:3]}")
            else:
                print("✓ Can read cells (worksheet is empty)")
        except Exception as e:
            print(f"❌ Failed to read cells: {e}")
            return False

        print("\n" + "=" * 50)
        print("✅ SUCCESS: Sheet is fully accessible!")
        print("=" * 50)
        return True

    except gspread.exceptions.APIError as e:
        error_msg = str(e)
        if "403" in error_msg:
            if "has not been used in project" in error_msg:
                print("\n❌ Google Sheets API not enabled!")
                print(f"\nEnable it with:\ngcloud services enable sheets.googleapis.com --project={project_id}")
            else:
                print("\n❌ Permission denied!")
                print(f"\nShare your sheet with:\n{sa_email}")
                print("Give it 'Viewer' access")
        else:
            print(f"\n❌ API Error: {e}")
        return False

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    success = quick_test()
    sys.exit(0 if success else 1)