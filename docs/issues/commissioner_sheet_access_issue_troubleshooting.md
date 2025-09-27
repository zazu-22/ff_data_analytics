# Commissioner Sheet Access Issue Troubleshooting Plan

## What most often causes “read hangs” on a specific Google Sheet

1. **Sheet complexity + recalculation debt**
   Heavy use of volatile functions (e.g., `NOW()`, `TODAY()`, `RAND()`, `RANDBETWEEN()`), wide open-ended ranges (`A:A`), cross-file imports (`IMPORTRANGE`, `IMPORT*`), big conditional formatting, or massive formulas can make a sheet slow to evaluate on access; API reads block until values resolve. Google’s own guidance: prefer local references, limit open ranges, and be sparing with volatile functions and imports. ([Google Help][1])
1. **Published/CSV endpoints and caching realities**
   “Publish to the web” and CSV/HTML endpoints aren’t real-time; updates commonly propagate ~5 minutes (sometimes longer) and can stall if a collaborator has the file open. This misleads health checks and can look like timeouts/empties. ([Google Help][2])
1. **Hitting quota/rate limits or per-minute windows**
   Even modest loops can spike Sheets API quotas (e.g., project read limit ~300/minute; per-user windows may be lower), resulting in throttling or slowdowns. Batch your reads and back off. ([Google for Developers][3])
1. **Client-side timeouts set too low for a slow workbook**
   gspread defaults can be too aggressive under heavy calc; you can raise the request timeout and/or use the backoff client. ([gspread][4])
1. **Workbook is near “limits” territory**
   Very large files (approaching the **10M-cell** limit) or tabs with huge grids can feel fine for metadata calls but choke when returning values or CSV. ([Google Help][5])
1. **Genuinely “stuck” evaluation** (rare but real)
   Some combinations of `IMPORTRANGE` + volatile functions + filter/pivot chains can deadlock until a human opens the file, forces a recalc, or the graph settles. (Known in the wild; typical community remedies are reducing volatile/IMPORT usage or forcing recalcs with Apps Script.) ([Stack Overflow][6])

## A rigorous, 60–90 minute troubleshooting flow (do these in order)

### A. Prove it’s the sheet, not the stack\*\*

1. **Single-cell API probe** (values.get or gspread)
   Read `Sheet1!A1` and `Sheet1!A1:B2` with `ValueRenderOption=UNFORMATTED_VALUE` (skips formatting). If this still stalls while other files are instant, it’s sheet-bound latency. ([Google for Developers][7])
1. **BatchGet** minimal test
   Fetch two tiny ranges with a single `values.batchGet` request; confirms you aren’t blowing a per-minute window with small loops. ([Google for Developers][8])
1. **Manual CSV vs Publish**
   Try the **CSV export** URL and a **Publish-to-web** CSV (if enabled). If publish shows data after several minutes but export keeps stalling, the workbook is spending its time in recalc for “live” reads. Note: publish often lags ~5 minutes. ([Stack Overflow][9])

### B. Measure the workbook’s “cost”\*\*

1. **Check limits & layout**
   Look for: (a) open ranges (`A:A` instead of `A1:A5000`), (b) volatile functions count, (c) `IMPORTRANGE` / `IMPORTHTML/XML/DATA` usage, (d) heavy conditional formatting, (e) large pivots or arrays. Google’s performance notes explicitly call these out. ([Google Help][10])
1. **Copy-to-new workbook tests**
   - Make a **“Values-only Extract”** copy (Edit → Paste special → Paste values only for each tab) and hit it with the same API call.
   - Make a **Structurally identical** copy (formulas intact) and test again. If values-only is instant and formula copy still hangs, the culprit is recalculation overhead.

### C. Reduce API/HTTP variables\*\*

1. **Bump timeouts & add backoff**
   In gspread: `gc.set_timeout((10, 180))` and/or use `BackoffClient` to tolerate sporadic slowness and quota wobble. ([gspread][4])
1. **Throttle & batch**
   Ensure you’re using `batchGet` for multiple ranges and sleeping between pages to respect per-minute windows. ([Google for Developers][3])

## Concrete fixes & workarounds (ranked: fastest relief → durable)

### A. “Today” unblockers (≤30 minutes)

1. Raise timeouts + retries in the ingestor\*\* (often enough if recalc is borderline):
   *gspread pattern* → `gc.set_timeout((10, 180))` then fetch **tiny ranges first** (e.g., header row) before full range; switch to `UNFORMATTED_VALUE` to skip locale formatting costs. ([gspread][4])
1. Enable “Publish to the web” for the exact tabs you ingest\*\* and point the pipeline to the published CSV endpoints (accepting ~5-minute cache).
   This avoids live recalculation on every read. ([Google Help][11])
1. Temporary “Values-Only Extract” workbook\*\*
   Create a second spreadsheet that holds **only values** (no formulas/conditional formats). Share it to the service account and flip the pipeline to read there. This typically returns instantly and isolates the analytics pipeline from collaborator edits.

### B. Near-term hardening (today → next few days)

1. Refactor costly patterns per Google’s guidance
   - Replace open ranges (`A:A`) with bounded ranges.
   - Minimize `IMPORTRANGE` / `IMPORT*`; prefer same-file references.
   - Corral `NOW()`, `TODAY()`, `RAND*()` into **single cells** and reference those, or replace with static values updated daily. ([Google Help][10])
1. Split logic vs. data
   Keep one **commissioner-input sheet** (data entry) and one **calc/reporting sheet** (formulas/visuals). Point the pipeline at the **input (values) file**.
1. Apps Script micro-service (server-side read)
   A 20-line Apps Script “export” endpoint can `getDisplayValues()` and return JSON/CSV via `ContentService`. This runs close to the data and can be more tolerant of calc latency. (Use a time-based trigger to pre-compute into a values tab if needed.) ([Ben Collins][12])
1. Batch & cache in the pipeline\*\*
   Use `values.batchGet` and add exponential backoff if you ever see 429s; monitor per-minute windows. ([Google for Developers][3])

### C. Durable solutions (this sprint)

1. Standardize a “Publisher” job\*\*
   A tiny Apps Script (or a Scheduled user action) that, at 08:00 & 16:00 UTC, **copies values** from the live workbook into a dedicated **Extract workbook** (or publishes those tabs). The pipeline then reads that artifact, not the live calc file. This makes your twice-daily runs deterministic.
1. Move canonical data entry off formulas\*\*
   Keep the commissioner sheet as a **UI**, but store canonical rows in a lightweight database (e.g., Supabase/Postgres) or a **values-only** tab that never contains formulas. This removes recalc from the ingestion path while preserving the sheet UX your league wants.

## Minimal code patterns you can apply immediately

### gspread: add timeouts + backoff and fetch unformatted values

```python
import gspread
from google.oauth2.service_account import Credentials

scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = Credentials.from_service_account_file("sa.json", scopes=scope)
gc = gspread.authorize(creds)

# Raise connect/read timeouts (sec)
gc.set_timeout((10, 180))  # connect=10s, read=180s

sh = gc.open_by_key(SHEET_ID)
ws = sh.worksheet("Commissioner")
# Ask for a tiny probe first, then the full range
hdr = ws.get("A1:B1", value_render_option="UNFORMATTED_VALUE")
data = ws.get("A1:Z", value_render_option="UNFORMATTED_VALUE")
```

(Timeout/backoff knobs documented in gspread.) ([gspread][4])

### Sheets API: batchGet + unformatted values (Python/any)

- Use `spreadsheets.values.batchGet` with `valueRenderOption=UNFORMATTED_VALUE` to minimize server-side work and reduce calls. ([Google for Developers][8])

### Publish-to-web CSV (accepting cache)

- After publishing an individual tab:
  `https://docs.google.com/spreadsheets/d/<SHEET_ID>/gviz/tq?tqx=out:csv&sheet=<TAB_NAME>`
  (Quick to wire up; refresh typically ~5 minutes.) ([Spark Shipping][13])

### Apps Script “extract” (server-side values)

- When “live” reads are stubborn, a bound Apps Script web app that returns `getDisplayValues()` can sidestep client timeouts and let you **pre-compute** to a values-only tab before your pipeline hits it. (This is a common community workaround for sheets that recalc slowly.) ([Ben Collins][12])

## Triage checklist (use this to decide the fix path)

- Does **values-only copy** read instantly? → Keep the copy as the pipeline source and schedule a values refresh at 08:00/16:00 UTC.
- Do **publish CSV** links return quickly while API calls hang? → Point the pipeline at the published CSV (with a “freshness ≤10 min” gate). ([Google Help][2])
- Are there lots of `IMPORTRANGE`/`IMPORT*`/open ranges/volatile functions? → Refactor per Google’s performance guidance. ([Google Help][10])
- Seeing quota errors/slowdowns during loops? → Switch to `batchGet` + exponential backoff and cap requests/minute. ([Google for Developers][3])

## Recommended path (opinionated)

### Immediate unblock (today)

1. Bump gspread timeouts and flip value rendering to **UNFORMATTED_VALUE**. ([gspread][4])
1. Create a **Values-Only Extract** workbook and point the pipeline there.
1. In parallel, **Publish CSV** for the key tabs and wire a fallback reader to those endpoints (accepting 5–10 min cache). ([Google Help][11])

### Within the week

1. Reduce or eliminate `IMPORTRANGE`/open ranges/volatile functions in the live sheet per Google’s guidance; keep volatile values isolated. ([Google Help][10])
1. Add `batchGet` + backoff to your ingestor; monitor per-minute quotas. ([Google for Developers][3])

### Longer term

1. Treat Google Sheets as the **UI only** and persist commissioner data as cleaned **values** (or in Supabase), keeping formulas out of the ingestion path entirely.

______________________________________________________________________

[1]: https://support.google.com/docs/answer/11468464?hl=en&utm_source=chatgpt.com "Learn how to improve Sheets performance - Google Docs Editors Help"
[2]: https://support.google.com/docs/thread/4836432/published-google-sheets-refresh-rate?hl=en&utm_source=chatgpt.com "Published Google Sheets Refresh Rate"
[3]: https://developers.google.com/workspace/sheets/api/limits?utm_source=chatgpt.com "Usage limits | Google Sheets"
[4]: https://docs.gspread.org/en/latest/api/client.html?utm_source=chatgpt.com "Client — gspread 6.1.2 documentation"
[5]: https://support.google.com/drive/answer/37603?hl=en&utm_source=chatgpt.com "Files you can store in Google Drive"
[6]: https://stackoverflow.com/questions/71312818/fixing-a-spreadsheet-reliant-on-importrange-that-is-now-super-slow?utm_source=chatgpt.com "Fixing a spreadsheet reliant on importrange that is now ..."
[7]: https://developers.google.com/workspace/sheets/api/reference/rest/v4/ValueRenderOption?utm_source=chatgpt.com "ValueRenderOption | Google Sheets"
[8]: https://developers.google.com/workspace/sheets/api/samples/reading?utm_source=chatgpt.com "Basic reading | Google Sheets"
[9]: https://stackoverflow.com/questions/37705553/how-to-export-a-csv-from-google-sheet-api?utm_source=chatgpt.com "How to export a csv from Google Sheet API?"
[10]: https://support.google.com/docs/answer/12159115?hl=en&utm_source=chatgpt.com "Optimize your data references to improve Sheets ..."
[11]: https://support.google.com/docs/answer/183965?co=GENIE.Platform%3DDesktop&hl=en&utm_source=chatgpt.com "Make Google Docs, Sheets, Slides & Forms public"
[12]: https://www.benlcollins.com/spreadsheets/slow-google-sheets/?utm_source=chatgpt.com "Slow Google Sheets? Here are 27 Ideas to Try Today"
[13]: https://kb.sparkshipping.com/creating-google-sheets-direct-download-links-to-a-csv-file?utm_source=chatgpt.com "Creating Google Sheets Direct Download Links to a CSV File"
