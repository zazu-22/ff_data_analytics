# ADR-005: Commissioner Sheet Ingestion via Server-Side Copy Strategy

**Status:** Accepted
**Date:** 2025-09-28
**Decision Makers:** Jason Shaffer, Development Team

## Context

The Commissioner Google Sheet (ID: `1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY`) experiences intermittent API access failures when attempting to read data directly via the Google Sheets API. This critical sheet contains authoritative league data including rosters, contracts, and draft assets.

### Problem Statement

- Direct API reads timeout after 30 seconds, even for single cell access
- Sheet metadata can be retrieved, but actual cell values cannot be read
- Issue is specific to this particular sheet (other sheets work fine)
- Failures occur in both GitHub Actions and local development environments
- Root cause appears to be sheet complexity (formulas, external data connections, or size)

### Constraints

- Service accounts have 0GB Drive quota and cannot create files in their own Drive
- Service accounts have limited permissions in shared My Drive folders
- Need automated twice-daily updates without manual intervention
- Must preserve data lineage and audit trail

## Decision

Implement a **server-side copy strategy** that:

1. Uses Google Sheets API's `copyTo()` method to duplicate worksheet tabs server-side
2. Freezes formulas to values using batch operations
3. Performs atomic rename/swap operations to maintain consistency
4. Logs all operations to a Shared Drive for observability
5. Implements intelligent skip logic based on source file modification times

### Architecture Components

```
Commissioner Sheet (Complex/Source)
    ↓ [Server-side copyTo]
Temporary Tab in Destination Sheet
    ↓ [Freeze formulas → values]
    ↓ [Atomic rename + metadata]
League Sheet Copy (Simple/Values-only)
    ↓
Downstream Pipeline (reads values successfully)
```

### Implementation Details

1. **Storage Strategy**

   - Use Google Shared Drive for log storage (service accounts can create files there)
   - Destination sheet remains in regular Drive for compatibility
   - Separate log workbook tracks all ingestion activity

2. **Copy Process** (per tab)

   - Server-side `copyTo()` - no data read required
   - Batch update to freeze formulas to values
   - Atomic operations: delete old tab, rename new tab
   - Add developer metadata for lineage tracking
   - Warning-only protection on copied tabs

3. **Skip Logic**

   - Track source file's `modifiedTime` via Drive API
   - Skip entire run if source unchanged since last success
   - Per-tab skip if already refreshed after source modification
   - Log all skips for observability

4. **Error Handling**

   - Fallback to destination sheet for logging if Shared Drive fails
   - Continue with unaffected tabs if individual tab fails
   - Preserve last-known-good data on failures

## Consequences

### Positive

- **Reliability**: Eliminates timeout issues by avoiding cell reads entirely
- **Performance**: Server-side copy is faster than reading/writing values
- **Scalability**: Process handles large/complex sheets without memory issues
- **Observability**: Complete audit trail of all copy operations
- **Efficiency**: Intelligent skip logic reduces unnecessary API calls
- **Maintainability**: Clean separation between complex source and simple destination

### Negative

- **Additional Infrastructure**: Requires Shared Drive setup for logging
- **Intermediate Storage**: Need destination sheet as intermediary
- **Slight Delay**: Data is one copy removed from source
- **Complexity**: More moving parts than direct read approach

### Neutral

- Service account permissions must be managed for multiple resources
- Requires monitoring both source and destination sheets

## Alternatives Considered

1. **Direct API Reads** (Original approach)

   - ❌ Failed due to timeouts on complex sheet

2. **Manual Export Process**

   - ❌ Not scalable for twice-daily updates
   - ❌ Introduces human error risk

3. **Google Apps Script Proxy**

   - ❌ Additional complexity with script deployment
   - ❌ Still subject to execution time limits

4. **Browser Automation**

   - ❌ Fragile and resource-intensive
   - ❌ Difficult to run in CI/CD environment

5. **Publish to Web + Scraping**

   - ❌ Security concerns with public data
   - ❌ HTML parsing complexity

## Implementation Notes

### Key Files

- `scripts/ingest/copy_league_sheet.py` - Main ingestion script

- `src/ff_analytics_utils/google_drive_helper.py` - Drive/Sheets utilities

- `.env` configuration:

  ```text
  COMMISSIONER_SHEET_ID="1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY"
  LEAGUE_SHEET_COPY_ID="1HktJj-VB5Rc35U6EXQJLwa_h4ytiur6A8QSJGN0tRy0"
  LOG_IN_SEPARATE_SHEET=1
  LOG_PARENT_ID="0AOi29KXdvnd7Uk9PVA"  # Shared Drive ID
  LOG_FOLDER_PATH="data/ingest/logs"
  ```

### Monitoring

- Log entries include source modification time for each operation
- Special `[ENTIRE_RUN]` entries track whole-run skips
- Debug utilities available:
  - `scripts/debug/view_log_sheet.py` - View recent log entries
  - `scripts/debug/check_shared_folder.py` - Verify permissions
  - `scripts/debug/list_shared_drives.py` - Discover available drives

## References

- Original issue: `docs/issues/commissioner_sheet_access_issue.md`
- Google Sheets API copyTo: <https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.sheets/copyTo>
- Service Account Drive Quotas: <https://support.google.com/a/answer/7338880>

## Decision Record

This approach has been implemented and tested successfully, resolving the critical blocking issue with Commissioner Sheet access. The solution is now in production use with automated twice-daily runs.
