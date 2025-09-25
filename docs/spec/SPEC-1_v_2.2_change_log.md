# SPEC-1_Consolidated_v2.2_change_log.md

## v2.2 — nflverse shim + projections config surface
- Added **nflverse Python shim** (try `nflreadpy` → fallback `nflreadr` via Rscript), with repo layout and contract guarantees.
- Clarified **FFanalytics** runner boundary (R-native, invoked from Python).
- Recorded version pins as of 2025-09-24 (nflreadr 1.5.0; nflreadpy 0.1.1).
- Confirmed storage path convention, identity seeds, change capture, and freshness banners.
