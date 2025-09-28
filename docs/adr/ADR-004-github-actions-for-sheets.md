# ADR-004: Use GitHub Actions for Commissioner Sheet Ingestion

## Status

Accepted (2025-09-26)

## Context

The Commissioner Google Sheet is the authoritative source for league roster, contract, and transaction data. During implementation, we discovered that while the service account has proper permissions, local API access to the Commissioner Sheet consistently times out, likely due to network-level blocking (ISP/firewall/VPN).

Testing confirmed:

- ✅ Service account CAN read the Commissioner Sheet when running in GitHub Actions
- ❌ Local access times out (even with 30+ second timeouts)
- ❌ Direct CSV export URLs also timeout locally
- ✅ Other Google Sheets work fine locally (confirming sheet-specific issue)

## Decision

Use GitHub Actions as the primary orchestration platform for Commissioner Sheet data ingestion, running all Google Sheets API calls from GitHub's cloud infrastructure rather than attempting local access.

## Consequences

### Positive

- **Working solution**: Confirmed access works in GitHub Actions
- **No infrastructure**: No GCP resources to manage/pay for initially
- **Version controlled**: Workflows live in the repo with the code
- **Free tier sufficient**: 2000 minutes/month covers twice-daily runs
- **Manual triggers**: `workflow_dispatch` for ad-hoc updates
- **Integrated secrets**: GitHub Secrets for credentials management

### Negative

- **No local testing**: Cannot test sheet access locally
- **GitHub dependency**: Pipeline depends on GitHub infrastructure
- **Debugging harder**: Must push changes to test (no local iteration)

### Neutral

- **Future migration path**: Can move to GCP Cloud Functions/Run if needed
- **Matches SPEC**: Already specified GitHub Actions as orchestrator

## Implementation Notes

1. **Commissioner Sheet workflow** (`commissioner_sheet_ingest.yml`):

   - Runs at 08:00 and 16:00 UTC (per SPEC)
   - Reads all owner tabs (avoiding large TRANSACTIONS tab)
   - Writes to `gs://ff-analytics/raw/commissioner/rosters/{owner}/dt={date}/`
   - Includes manual trigger for ad-hoc updates

1. **Error handling**:

   - Last-known-good (LKG) pattern if sheet is unavailable
   - Discord notifications on failure (optional)
   - Retry logic with exponential backoff

1. **Testing strategy**:

   - Use sample data for local development
   - Test workflow in separate branch before merging
   - Monitor first few runs closely

## Alternatives Considered

1. **Google Colab**: Would work but requires manual execution or complex scheduling
1. **GCP Cloud Functions**: More complex setup, unnecessary for MVP
1. **Local proxy/VPN**: Unreliable, adds complexity
1. **Manual exports**: Not sustainable for automated pipeline

## References

- SPEC-1 v2.2: Specifies GitHub Actions for orchestration
- Test results: `.github/workflows/test-sheets-access.yml` confirmed access works
- Issue: Local network blocks Google Sheets API calls to Commissioner Sheet
