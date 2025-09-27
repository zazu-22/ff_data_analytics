# Issue: Commissioner Sheet API Access Intermittently Failing in GitHub Actions

**Issue Type:** Critical Bug
**Priority:** High
**Component:** Data Ingestion Pipeline / Google Sheets API
**Date:** 2025-09-26

## Summary

The Commissioner Google Sheet (ID: `1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY`) cannot be read programmatically via the Google Sheets API, despite proper authentication and permissions. This is blocking the critical Commissioner data ingestion pipeline.

## Current Status

- ❌ **Production workflow fails** - All reads timeout after 30 seconds
- ❌ **Debug workflows fail** - Even reading a single cell (A1) times out
- ✅ **Authentication works** - Service account authenticates successfully
- ✅ **Metadata access works** - Can list worksheets and get properties
- ✅ **Other sheets work** - Same code successfully reads other Google Sheets
- ❌ **Local access fails** - All API calls timeout from local development environment

## Evidence of Intermittent Behavior

### Successful Test (2025-09-26 ~01:00 UTC)

```
Testing Commissioner Sheet Access from GitHub Actions
Sheet ID: 1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY
✓ Opened: The Bell Keg Excel
✓ Found 28 worksheets
Reading from: Eric
✓ Read 3 rows
First row: ['Active Roster']
SUCCESS! Sheet access works in GitHub Actions!
```

### Failed Production Run (2025-09-26 06:08 UTC)

```
Reading worksheet: Eric
  Worksheet size: 37 rows × 39 columns
  Testing with small read (A1:C3)...
ERROR: Even small read timed out for Eric
```

## Technical Details

### Environment

- **GitHub Actions Runner:** ubuntu-latest
- **Python Version:** 3.13.7
- **Libraries:** gspread 6.1.4, google-auth 2.37.0
- **Service Account:** ff-analytics-pipeline@ff-analytics-1.iam.gserviceaccount.com

### Code That Times Out

```python
import gspread
from google.oauth2.service_account import Credentials

# This works - authentication and metadata
scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = Credentials.from_service_account_file('/tmp/gcp-key.json', scopes=scope)
gc = gspread.authorize(creds)

sheet = gc.open_by_key('1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY')
worksheets = sheet.worksheets()  # ✓ This works

# This times out - any cell read
ws = worksheets[0]
value = ws.acell('A1').value  # ❌ Hangs indefinitely
values = ws.get('A1:C3')      # ❌ Hangs indefinitely
```

### Debugging Attempted

1. **Different read methods** - All timeout:

   - `worksheet.get_all_values()`
   - `worksheet.get('A1:C3')`
   - `worksheet.acell('A1').value`
   - `worksheet.batch_get(['A1:C1'])`

1. **Different API approaches**:

   - gspread library - times out
   - Google Sheets API v4 directly - times out
   - CSV export URL - times out

1. **Different environments**:

   - Local development - times out
   - GitHub Actions - times out (but worked once)
   - Google Colab - not tested successfully

## Key Observations

1. **Metadata vs Data**: Can retrieve sheet metadata (title, worksheet list, dimensions) but cannot read actual cell values
1. **Intermittent Success**: The exact same code worked once in GitHub Actions but now consistently fails
1. **Sheet-Specific**: Other Google Sheets work fine with identical code
1. **Not Permission Issue**: Sheet is shared with service account and set to "Anyone with link can view"

## Hypothesis

The Commissioner Sheet appears to have characteristics that prevent programmatic data access:

- Complex formulas or external data connections causing calculation delays
- Sheet-level settings or protections that block API reads
- Google's anti-automation measures triggered by the sheet's structure
- Possible corruption or sync issues with the sheet

## Impact

- **Blocked Pipeline**: Cannot ingest Commissioner roster/contract data
- **Manual Process Required**: Data must be manually exported
- **Schedule Risk**: Twice-daily automated updates cannot run

## Requested Actions

1. **Investigate Sheet Configuration**:

   - Check for IMPORTDATA, IMPORTRANGE, or QUERY functions
   - Look for array formulas or volatile functions
   - Verify no cell-level protections are set

1. **Test Alternative Approaches**:

   - Try accessing with owner's personal credentials
   - Test if "Publish to Web" enables programmatic access
   - Create a simplified copy with values only (no formulas)

1. **Contact Sheet Owner**:

   - Ask if any recent changes were made to the sheet
   - Request they check sharing settings and permissions
   - See if they can enable "Offline Access" or other settings

1. **Escalation Options**:

   - File Google Support ticket if enterprise account
   - Try Google Apps Script within the sheet itself
   - Implement manual export process as temporary workaround

## Workaround Options

1. **Manual Export**: Commissioner manually exports CSVs periodically
1. **Google Apps Script**: Script within the sheet that exports to GCS
1. **Different Sheet**: Create a simpler mirror sheet with just values
1. **API Proxy**: Use Google Apps Script as a proxy to serve data

## References

- Test workflow: `.github/workflows/test-sheets-access.yml`
- Production script: `scripts/ingest/commissioner_sheet.py`
- Working test output: \[GitHub Actions run link\]
- Failed production runs: \[GitHub Actions run links\]

## Next Steps

Need team input on:

1. Best approach for working around this blocking issue
1. Whether to escalate to Google Support
1. Acceptable temporary manual processes

______________________________________________________________________

**Note**: This appears to be an issue specific to this particular Google Sheet rather than our code or infrastructure, as evidenced by successful reads of other sheets and the intermittent success with this sheet.
