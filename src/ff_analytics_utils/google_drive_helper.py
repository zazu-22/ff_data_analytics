# drive_helper.py
from datetime import UTC, datetime
from typing import Any

from googleapiclient.discovery import build


def build_drive(creds):
    """Return an authenticated Drive v3 client."""
    # cache_discovery=False avoids local cache warnings in CI
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def is_shared_drive(drive_id: str) -> bool:
    """
    Check if a drive ID appears to be a Shared Drive ID.
    Shared Drive IDs typically start with '0A'.
    """
    return drive_id and drive_id.startswith("0A")


def get_drive_info(drive, drive_id: str) -> dict[str, Any] | None:
    """
    Get information about a Shared Drive.
    Returns None if it's not a Shared Drive or not accessible.
    """
    if not is_shared_drive(drive_id):
        return None

    try:
        return drive.drives().get(driveId=drive_id).execute()
    except Exception:
        return None


def get_file_metadata(
    drive, file_id: str, fields: str = "id,name,modifiedTime,version,owners"
) -> dict[str, Any]:
    """
    Fetch Drive file metadata with selected fields.
    Useful fields:
      - modifiedTime (RFC3339)
      - version (monotonic integer, often increments with content edits)
    """
    try:
        # Try with Shared Drive support first
        return drive.files().get(fileId=file_id, fields=fields, supportsAllDrives=True).execute()
    except Exception:
        # Fallback to regular file access
        return drive.files().get(fileId=file_id, fields=fields).execute()


def parse_rfc3339(ts: str) -> datetime:
    """Parse RFC3339 'modifiedTime' to aware UTC datetime."""
    # e.g., '2025-09-26T22:01:23.456Z'
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(UTC)


def get_file_modified_time_utc(drive, file_id: str) -> tuple[datetime, dict[str, Any]]:
    """Return (modifiedTime_utc, full_meta)."""
    meta = get_file_metadata(drive, file_id)
    mt = parse_rfc3339(meta["modifiedTime"])
    return mt, meta


def ensure_spreadsheet_in_folder(drive, folder_id: str, name: str) -> str:
    """
    Return the fileId of a Google Sheets file named `name` inside `folder_id`.
    If it doesn't exist, create it in that folder and return its id.
    Works with both regular folders and Shared Drives.
    """
    # Check if the parent is a Shared Drive
    use_shared_drive = is_shared_drive(folder_id)

    # Drive query strings use single quotes; escape any single quotes in the name
    escaped_name = name.replace("'", "\\'")
    q = (
        "mimeType='application/vnd.google-apps.spreadsheet' "
        f"and name='{escaped_name}' "
        f"and '{folder_id}' in parents and trashed=false"
    )

    # Search with appropriate parameters
    list_params = {
        "q": q,
        "spaces": "drive",
        "fields": "files(id,name,parents)",
        "pageSize": 50,
    }

    if use_shared_drive:
        list_params.update(
            {
                "corpora": "drive",
                "driveId": folder_id,
                "includeItemsFromAllDrives": True,
                "supportsAllDrives": True,
            }
        )
    else:
        list_params.update(
            {
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
            }
        )

    res = drive.files().list(**list_params).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]

    # Create the spreadsheet
    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "parents": [folder_id],
    }

    # Create with appropriate parameters
    create_params = {
        "body": file_metadata,
        "fields": "id",
        "supportsAllDrives": True,
    }

    created = drive.files().create(**create_params).execute()
    return created["id"]


def move_file_to_folder(drive, file_id: str, folder_id: str) -> dict:
    """
    Move an existing file to the target Drive folder by replacing its parents.
    Safe if the file has zero or many parents.
    """
    meta = drive.files().get(fileId=file_id, fields="parents").execute()
    prev_parents_list = meta.get("parents", [])
    prev_parents = ",".join(prev_parents_list)

    kwargs = {
        "fileId": file_id,
        "addParents": folder_id,
        "fields": "id,parents",
    }
    if prev_parents:
        kwargs["removeParents"] = prev_parents

    return drive.files().update(**kwargs).execute()


# --- PATH-LIKE FOLDER ENSURER ----------------------------------------------


def folder_id_from_url(url: str) -> str:
    """
    Extract a Google Drive folder ID from a standard folder URL.
    Example: https://drive.google.com/drive/folders/<FOLDER_ID>
    """
    import re

    m = re.search(r"/folders/([a-zA-Z0-9_-]+)", url)
    if not m:
        raise ValueError("Not a recognizable Drive folder URL")
    return m.group(1)


def ensure_folder(drive, path: str, parent_id: str = "root", create_missing: bool = True) -> str:
    """
    Resolve/ensure a nested folder PATH under PARENT_ID (default 'root').
    - PATH uses '/' separators, e.g. "BellKeg/Logs/Prod"
    - For 'My Drive', keep parent_id='root' (default).
    - For Shared drives, pass the shared drive's ID as parent_id.
    Returns the folderId of the final (leaf) folder.

    NOTE: Service account must have at least Viewer on each ancestor + Editor where creating.
    """

    def _escape(s: str) -> str:
        return s.replace("'", "\\'")

    # Check if we're working with a Shared Drive
    use_shared_drive = is_shared_drive(parent_id)
    drive_id = parent_id if use_shared_drive else None

    # normalize: strip leading/trailing slashes and ignore empty segments
    parts = [seg for seg in (path or "").split("/") if seg and seg != "."]

    # If no path parts, just return the parent
    if not parts:
        return parent_id

    current = parent_id  # start at root (or provided parent)
    for name in parts:
        # Find existing child folder with this name under current parent
        q = (
            "mimeType='application/vnd.google-apps.folder' "
            f"and name='{_escape(name)}' and '{current}' in parents and trashed=false"
        )

        # Set up list parameters based on drive type
        list_params = {
            "q": q,
            "spaces": "drive",
            "fields": "files(id,name,parents)",
            "pageSize": 100,
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }

        if use_shared_drive:
            list_params.update(
                {
                    "corpora": "drive",
                    "driveId": drive_id,
                }
            )

        res = drive.files().list(**list_params).execute()
        files = res.get("files", [])

        if files:
            # Use the first exact match under this parent
            current = files[0]["id"]
            continue

        if not create_missing:
            raise FileNotFoundError(f"Folder '{name}' not found under parent {current}")

        # Create the missing folder under current
        meta = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [current],
        }

        created = (
            drive.files()
            .create(
                body=meta,
                fields="id,parents",
                supportsAllDrives=True,
            )
            .execute()
        )

        current = created["id"]

    return current
