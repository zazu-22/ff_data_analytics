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

## v2.3 — sample scaffolding + checklist refresh (2025-10-24)

- Added commissioner GM tab samples plus transactions snapshot to repo for test coverage.
- Updated `tools/make_samples.py` to load .env defaults, bound Sheets range (faster, no hanging).
- Documented sheets sampler defaults in developer guide; implementation status now reflects green pytest run with bundled fixtures.
- Promoted implementation checklist to v2.3 and captured Track A/B status plus packaged samples.
