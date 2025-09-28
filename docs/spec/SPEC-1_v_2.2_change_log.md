# SPEC-1_Consolidated_v2.2_change_log.md

## v2.2 — nflverse shim + projections config surface

- Added **nflverse Python shim** (try `nflreadpy` → fallback `nflreadr` via Rscript), with repo layout and contract guarantees.
- Clarified **FFanalytics** runner boundary (R-native, invoked from Python).
- Recorded version pins as of 2025-09-24 (nflreadr 1.5.0; nflreadpy 0.1.1).
- Confirmed storage path convention, identity seeds, change capture, and freshness banners.

## v2.2.1 — Commissioner Sheet ingestion strategy (2025-09-28)

- Added **Commissioner Sheet server-side copy strategy** (ADR-005) to handle complex sheets that timeout on direct API reads.
- Implemented intelligent skip logic based on Drive file modification times.
- Configured Shared Drive for ingestion logging to work around service account 0GB quota limitation.
- Solution deployed and tested: `scripts/ingest/copy_league_sheet.py` with full observability.
