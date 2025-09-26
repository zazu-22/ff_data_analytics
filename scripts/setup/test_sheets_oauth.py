#!/usr/bin/env python3
"""Test if YOU can read the sheet (not service account) using OAuth."""

import os
from pathlib import Path

# First, let's just test with a simple HTTP request to see if the sheet is accessible
import urllib.request
import json

print("Testing Commissioner Sheet accessibility...\n")

# Your sheet ID
SHEET_ID = "1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY"

# Test 1: Can we access the sheet's public metadata?
print("1. Testing if sheet is publicly accessible via HTTP...")
try:
    # This URL provides public access to sheet metadata if sharing is enabled
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
    response = urllib.request.urlopen(url, timeout=5)
    print("   ✓ Sheet is accessible via web")
except Exception as e:
    print(f"   ✗ Cannot access sheet via web: {e}")

# Test 2: Try the sheets export URL (CSV export)
print("\n2. Testing CSV export (if publicly readable)...")
try:
    # Try to export the Eric sheet as CSV
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=242463565"  # Eric's sheet gid
    response = urllib.request.urlopen(csv_url, timeout=10)
    data = response.read().decode('utf-8')
    lines = data.split('\n')[:3]  # Get first 3 lines
    print(f"   ✓ Can export as CSV! First line has {len(lines[0].split(','))} columns")
    print(f"   First row preview: {lines[0][:100]}...")
except Exception as e:
    print(f"   ✗ Cannot export as CSV: {e}")

# Test 3: Check the published web version
print("\n3. Testing published web version...")
try:
    # Sometimes sheets are published to web separately
    pub_url = f"https://docs.google.com/spreadsheets/d/e/{SHEET_ID}/pubhtml"
    response = urllib.request.urlopen(pub_url, timeout=5)
    print("   ✓ Sheet has a published version")
except:
    print("   ✗ Sheet is not published to web")

print("\n" + "="*50)
print("Alternative Solutions:")
print("\n1. Use CSV Export URL directly:")
print(f"   https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=SHEET_GID")
print("\n2. Ask the commissioner to:")
print("   - File → Share → Get Link → Change to 'Anyone with link can edit' temporarily")
print("   - File → Publish to web → Publish as CSV")
print("\n3. Create a mirror sheet (as suggested earlier)")
print("="*50)