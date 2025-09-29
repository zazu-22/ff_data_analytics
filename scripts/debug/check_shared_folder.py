#!/usr/bin/env python3
"""Check shared folder access and permissions for service account.

This script verifies service account access to shared folders by:
- Checking folder metadata and permissions
- Displaying service account capabilities on the folder
- Navigating subfolder paths to verify full path access
- Listing files in the target folder
- Checking for Shared Drive access

Useful for diagnosing permission issues when setting up log folders
or data directories that need to be accessed by service accounts.

Usage:
    python scripts/debug/check_shared_folder.py

Environment Variables:
    LOG_PARENT_ID: The folder ID to check (default from .env)
    LOG_FOLDER_PATH: Subfolder path to navigate (default from .env)
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account key

Returns:
    0 on success, displays folder access details
    Non-zero on error

Note:
    Service accounts need specific permissions:
    - "Can List Children" to browse folder contents
    - "Can Add Children" or "Can Create" to add new files
    - For Shared Drives, must have appropriate role assigned

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

# Get the folder IDs from environment
LOG_PARENT_ID = os.getenv("LOG_PARENT_ID", "1mvfnVtbWkf96U8jEbgbOJe2FZEHPovna")
LOG_FOLDER_PATH = os.getenv("LOG_FOLDER_PATH", "data/raw")

SCOPES = ["https://www.googleapis.com/auth/drive"]


def main():
    """Check access permissions for configured shared folders.

    Verifies the service account can access and use the folders
    specified in LOG_PARENT_ID and LOG_FOLDER_PATH environment variables.

    Returns:
        int: 0 on success, 1 if folder access fails

    """
    # Authenticate
    creds = Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS, scopes=SCOPES)
    drive = build("drive", "v3", credentials=creds)

    print(f"Checking folder: {LOG_PARENT_ID}")
    print(f"Looking for subfolder path: {LOG_FOLDER_PATH}")
    print("-" * 60)

    # Check parent folder
    try:
        parent_meta = (
            drive.files()
            .get(fileId=LOG_PARENT_ID, fields="id,name,mimeType,owners,permissions,capabilities")
            .execute()
        )

        print("\nParent Folder Info:")
        print(f"  Name: {parent_meta.get('name')}")
        print(f"  ID: {parent_meta.get('id')}")
        print(f"  Type: {parent_meta.get('mimeType')}")

        # Check capabilities
        caps = parent_meta.get("capabilities", {})
        print("\nService Account Capabilities:")
        print(f"  Can Add Children: {caps.get('canAddChildren', False)}")
        print(f"  Can Create: {caps.get('canCreate', False)}")
        print(f"  Can Edit: {caps.get('canEdit', False)}")
        print(f"  Can List Children: {caps.get('canListChildren', False)}")

    except Exception as e:
        print(f"Error accessing parent folder: {e}")
        return

    # Try to find the data/raw subfolder
    print(f"\n\nSearching for subfolder '{LOG_FOLDER_PATH}'...")

    def find_folder(parent_id, folder_name):
        """Recursively find a folder by name under parent."""
        q = (
            f"mimeType='application/vnd.google-apps.folder' "
            f"and name='{folder_name}' "
            f"and '{parent_id}' in parents "
            f"and trashed=false"
        )

        try:
            results = (
                drive.files()
                .list(
                    q=q,
                    spaces="drive",
                    fields="files(id, name, parents)",
                    pageSize=100,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )

            files = results.get("files", [])
            if files:
                return files[0]
        except Exception as e:
            print(f"Error searching for folder: {e}")

        return None

    # Navigate the path
    current_parent = LOG_PARENT_ID
    parts = LOG_FOLDER_PATH.split("/")

    for part in parts:
        folder = find_folder(current_parent, part)
        if folder:
            print(f"  Found: {part} -> {folder['id']}")
            current_parent = folder["id"]
        else:
            print(f"  NOT FOUND: {part}")
            break

    if current_parent != LOG_PARENT_ID:
        print(f"\nFinal folder ID: {current_parent}")

        # List files in the final folder
        print("\nFiles in the folder:")
        q = f"'{current_parent}' in parents and trashed=false"

        try:
            results = (
                drive.files()
                .list(
                    q=q,
                    spaces="drive",
                    fields="files(id, name, mimeType)",
                    pageSize=20,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )

            files = results.get("files", [])
            if not files:
                print("  No files found")
            else:
                for f in files:
                    print(f"  - {f['name']} ({f['mimeType']}) [{f['id']}]")
        except Exception as e:
            print(f"  Error listing files: {e}")

    # Check if we can see shared drives
    print("\n\nShared Drives accessible to service account:")
    try:
        drives_response = drive.drives().list(pageSize=10).execute()
        drives = drives_response.get("drives", [])

        if not drives:
            print("  No shared drives found")
        else:
            for d in drives:
                print(f"  - {d['name']} [{d['id']}]")
    except Exception as e:
        print(f"  Error listing shared drives: {e}")


if __name__ == "__main__":
    main()
