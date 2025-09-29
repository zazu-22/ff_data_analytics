#!/usr/bin/env python3
"""Check service account's Google Drive quota and list files.

This script helps diagnose Drive storage issues with service accounts by:
- Displaying the storage quota and current usage
- Listing files owned by the service account
- Showing total file count

Useful for debugging "storage quota exceeded" errors when service accounts
have 0GB quota and cannot create files in their own Drive space.

Usage:
    python scripts/debug/check_service_account_drive.py

Returns:
    0 on success, displays quota info and file list
    Non-zero on error

Note:
    Service accounts typically have 0GB quota and cannot create files
    in their own Drive. They must create files in shared folders or
    Shared Drives where they have been granted access.

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
    """Check service account Drive quota and list owned files.

    Returns:
        int: 0 on success, non-zero on error

    """
    # Authenticate
    creds = Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS, scopes=SCOPES)
    drive = build("drive", "v3", credentials=creds)

    # Get About info (includes storage quota)
    try:
        about = drive.about().get(fields="storageQuota, user").execute()
        quota = about.get("storageQuota", {})
        user = about.get("user", {})

        print(f"Service Account: {user.get('emailAddress')}")
        print(f"Display Name: {user.get('displayName')}")
        print("\nStorage Quota:")

        limit = quota.get("limit")
        usage = quota.get("usage")
        usage_in_drive = quota.get("usageInDrive")
        usage_in_trash = quota.get("usageInDriveTrash")

        if limit:
            print(f"  Limit: {int(limit) / 1024 / 1024 / 1024:.2f} GB")
        else:
            print("  Limit: No limit set (using default)")

        if usage:
            usage_gb = int(usage) / 1024 / 1024 / 1024
            print(f"  Total Usage: {usage_gb:.2f} GB")

        if usage_in_drive:
            print(f"  Usage in Drive: {int(usage_in_drive) / 1024 / 1024 / 1024:.2f} GB")

        if usage_in_trash:
            print(f"  Usage in Trash: {int(usage_in_trash) / 1024 / 1024 / 1024:.2f} GB")
    except Exception as e:
        print(f"Could not get quota info: {e}")

    # List files owned by the service account
    print("\n\nFiles owned by service account (first 20):")
    print("-" * 60)

    try:
        results = (
            drive.files()
            .list(
                q="'me' in owners",
                pageSize=20,
                fields="files(id, name, mimeType, size, createdTime, modifiedTime, parents)",
                orderBy="modifiedTime desc",
            )
            .execute()
        )

        files = results.get("files", [])

        if not files:
            print("No files found.")
        else:
            for file in files:
                size = file.get("size", "0")
                size_mb = int(size) / 1024 / 1024 if size else 0
                print(f"\nName: {file.get('name')}")
                print(f"  ID: {file.get('id')}")
                print(f"  Type: {file.get('mimeType')}")
                print(f"  Size: {size_mb:.2f} MB")
                print(f"  Created: {file.get('createdTime')}")
                print(f"  Modified: {file.get('modifiedTime')}")
                print(f"  Parents: {file.get('parents', [])}")

        # Count total files
        all_results = (
            drive.files().list(q="'me' in owners", fields="files(id)", pageSize=1000).execute()
        )
        total_count = len(all_results.get("files", []))

        if total_count > 20:
            print(f"\n... and {total_count - 20} more files (total: {total_count})")

    except Exception as e:
        print(f"Could not list files: {e}")


if __name__ == "__main__":
    main()
