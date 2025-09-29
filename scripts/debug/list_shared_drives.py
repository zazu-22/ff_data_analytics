#!/usr/bin/env python3
"""List all Shared Drives accessible to the service account.

This script discovers and validates Shared Drive access by:
- Listing all Shared Drives the service account can see
- Testing access to each drive by listing contents
- Checking if a specific drive ID from environment is accessible
- Distinguishing between Shared Drives and regular folders

Useful for setting up or debugging Shared Drive configurations,
especially when migrating from My Drive folders to Shared Drives.

Usage:
    python scripts/debug/list_shared_drives.py

Environment Variables:
    LOG_PARENT_ID: Optional drive ID to specifically check
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account key

Returns:
    0 on success, displays list of accessible Shared Drives
    Non-zero on error

Note:
    Shared Drive IDs typically start with "0A" while regular folder
    IDs have different patterns. Service accounts work best with
    Shared Drives as they can have full permissions without the
    quota limitations of personal My Drive folders.

"""

import os

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

GOOGLE_APPLICATION_CREDENTIALS = (
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "config/secrets/gcp-service-account-key.json"
)

SCOPES = ["https://www.googleapis.com/auth/drive"]


def main():
    """List and validate all accessible Shared Drives.

    Enumerates Shared Drives, tests access, and checks if LOG_PARENT_ID
    from environment is a valid Shared Drive.

    Returns:
        int: 0 on success, non-zero on error

    """
    # Authenticate
    creds = Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS, scopes=SCOPES)
    drive = build("drive", "v3", credentials=creds)

    print("Shared Drives accessible to service account:")
    print("-" * 60)

    try:
        # List all shared drives
        page_token = None
        while True:
            response = (
                drive.drives()
                .list(pageSize=10, fields="nextPageToken, drives(id, name)", pageToken=page_token)
                .execute()
            )

            drives = response.get("drives", [])

            if not drives and not page_token:
                print("No shared drives found.")
            else:
                for drive_item in drives:
                    print(f"\nName: {drive_item['name']}")
                    print(f"ID: {drive_item['id']}")

                    # Check if we can access it
                    try:
                        # Try to list root contents
                        files = (
                            drive.files()
                            .list(
                                q=f"'{drive_item['id']}' in parents and trashed=false",
                                fields="files(name)",
                                pageSize=5,
                                supportsAllDrives=True,
                                includeItemsFromAllDrives=True,
                                driveId=drive_item["id"],
                                corpora="drive",
                            )
                            .execute()
                        )

                        file_count = len(files.get("files", []))
                        print(f"Access: ✓ Can list contents ({file_count} items visible)")

                        # Check capabilities
                        drive.about().get(fields="canCreateDrives").execute()

                    except Exception as e:
                        print(f"Access: ✗ Cannot access ({e})")

            page_token = response.get("nextPageToken")
            if not page_token:
                break

    except Exception as e:
        print(f"Error listing shared drives: {e}")

    # Also check if the specific drive from env is accessible
    print("\n" + "=" * 60)
    print("Checking LOG_PARENT_ID from environment...")

    LOG_PARENT_ID = os.getenv("LOG_PARENT_ID", "0AOi29KXdvnd7Uk9PVA")
    print(f"LOG_PARENT_ID: {LOG_PARENT_ID}")

    # First try as a shared drive
    try:
        drive_meta = drive.drives().get(driveId=LOG_PARENT_ID).execute()
        print(f"✓ Found as Shared Drive: {drive_meta.get('name')}")
    except Exception as e:
        print(f"✗ Not a Shared Drive: {e}")

        # Try as a regular folder
        try:
            file_meta = (
                drive.files()
                .get(fileId=LOG_PARENT_ID, fields="id,name,mimeType", supportsAllDrives=True)
                .execute()
            )
            print(f"✓ Found as Folder: {file_meta.get('name')} ({file_meta.get('mimeType')})")
        except Exception as e2:
            print(f"✗ Not accessible as folder either: {e2}")


if __name__ == "__main__":
    main()
