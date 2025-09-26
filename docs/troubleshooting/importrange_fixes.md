# IMPORTRANGE Troubleshooting Guide

## Common Fixes for "Loading..." Error

### 1. Try Different Formula Formats

Instead of:
```
=IMPORTRANGE("1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY", "Eric!A:AZ")
```

Try these variations:

**Option A - Full URL:**
```
=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY", "Eric!A:AZ")
```

**Option B - Smaller range first:**
```
=IMPORTRANGE("1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY", "Eric!A1:C10")
```

**Option C - Different sheet:**
```
=IMPORTRANGE("1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY", "Gordon!A1:C10")
```

### 2. Force Authorization

1. Create a new sheet
2. In cell A1, put just the sheet ID: `1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY`
3. In cell A2, put: `=IMPORTRANGE(A1, "Eric!A1")`
4. This sometimes triggers the auth dialog

### 3. Browser/Account Issues

1. **Try incognito/private mode** - Rules out extensions blocking it
2. **Different browser** - Chrome vs Firefox vs Safari
3. **Clear Google Sheets cache:**
   - Go to drive.google.com
   - Settings (gear icon) → Settings
   - Manage Apps → Google Sheets → Options → Delete hidden app data

### 4. Manual Authorization Trick

1. Open YOUR new sheet
2. Open the Commissioner sheet in another tab
3. In the Commissioner sheet URL, copy everything after `/d/` and before `/edit`
4. Back in your sheet, try IMPORTRANGE again
5. Sometimes having both sheets open triggers the auth

### 5. Test with a Different Source

Create a test to see if IMPORTRANGE works at all:

```
=IMPORTRANGE("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Class Data!A1:C5")
```

This uses Google's public example sheet. If this works, the issue is specific to the Commissioner sheet.

### 6. Use Google Apps Script Instead

If IMPORTRANGE won't work, we can try a script approach:

```javascript
function fetchCommissionerData() {
  var sourceId = "1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY";
  try {
    var sourceSheet = SpreadsheetApp.openById(sourceId);
    var ericSheet = sourceSheet.getSheetByName("Eric");
    var data = ericSheet.getRange(1, 1, 10, 10).getValues();

    var targetSheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    targetSheet.getRange(1, 1, data.length, data[0].length).setValues(data);
  } catch (e) {
    Logger.log("Error: " + e.toString());
  }
}
```

### 7. Alternative: Published CSV URL

Since the sheet is viewable by anyone with the link, try accessing it as CSV:

For the Eric sheet (gid=242463565):
```
https://docs.google.com/spreadsheets/d/1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY/export?format=csv&gid=242463565
```

You could set up a script to fetch this URL and import the data.