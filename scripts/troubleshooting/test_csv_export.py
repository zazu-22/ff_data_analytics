#!/usr/bin/env python3
"""Test accessing the Commissioner Sheet via CSV export URLs."""

import csv
import io
import urllib.request

print("Testing CSV Export Method...")
print("=" * 50)

SHEET_ID = "1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY"

# Sheet GIDs we discovered earlier
sheets = {
    "Eric": "242463565",
    # Add more as needed
}

for sheet_name, gid in sheets.items():
    print(f"\nTrying to export '{sheet_name}' sheet as CSV...")
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"

    try:
        # Try with a user agent to appear more like a browser
        req = urllib.request.Request(
            csv_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
        )

        # Short timeout to avoid hanging
        response = urllib.request.urlopen(req, timeout=5)
        data = response.read().decode("utf-8")

        # Parse CSV
        reader = csv.reader(io.StringIO(data))
        rows = list(reader)

        print(f"✅ SUCCESS! Downloaded {len(rows)} rows")
        if rows:
            print(f"   Columns in first row: {len(rows[0])}")
            print(f"   First 3 columns: {rows[0][:3]}")

            # Save a sample
            output_file = f"samples/{sheet_name}_sample.csv"
            print(f"   Saving sample to {output_file}")
            import os

            os.makedirs("samples", exist_ok=True)
            with open(output_file, "w") as f:
                writer = csv.writer(f)
                for row in rows[:10]:  # First 10 rows
                    writer.writerow(row)

    except Exception as e:
        print(f"❌ Failed: {e}")

print("\n" + "=" * 50)
print("If CSV export works, we can use this method instead of the Sheets API!")
print("The data can be fetched periodically and stored in GCS.")
