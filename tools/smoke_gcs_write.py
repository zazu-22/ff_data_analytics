"""Smoke test for storage writing (local and GCS).

Usage:
  uv run python tools/smoke_gcs_write.py --dest gs://my-bucket/test/ff_analytics
  uv run python tools/smoke_gcs_write.py --dest data/tmp/gcs_smoke

Env:
  - GOOGLE_APPLICATION_CREDENTIALS or GCS_SERVICE_ACCOUNT_JSON for GCS
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

import polars as pl
from dotenv import load_dotenv

from ingest.common.storage import write_parquet_any, write_text_sidecar


def main() -> int:
    """Write a tiny DataFrame to a local or GCS destination for smoke testing."""
    # Load .env to pick up GOOGLE_APPLICATION_CREDENTIALS or GCS_SERVICE_ACCOUNT_JSON
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("--dest", required=True, help="Base destination path or gs:// URI")
    args = p.parse_args()

    now = datetime.now(UTC).isoformat()
    frame = pl.DataFrame(
        {
            "ts": [now],
            "msg": ["storage smoke test"],
        }
    )

    parquet_uri = (
        args.dest.rstrip("/") + f"/smoke/dt={now[:10]}/smoke_{now[11:19].replace(':', '')}.parquet"
    )
    meta_uri = args.dest.rstrip("/") + f"/smoke/dt={now[:10]}/_meta.json"

    write_parquet_any(frame, parquet_uri)
    write_text_sidecar("{" + f'\n  "ts": "{now}",\n  "note": "ok"\n' + "}", meta_uri)

    print(parquet_uri)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
