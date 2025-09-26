#!/usr/bin/env python3
"""
Use browser automation to export Google Sheets when API access fails.
This simulates what you do manually but programmatically.
"""

import time
import os
from pathlib import Path

# Check if selenium is installed
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    print("✓ Selenium is installed")
except ImportError:
    print("Installing Selenium for browser automation...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "uv", "add", "selenium"])
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

def export_sheet_as_csv(sheet_url, output_dir="data/raw/commissioner"):
    """
    Open Google Sheet in browser and export as CSV.
    Requires Chrome/Chromium installed.
    """
    print("Setting up browser automation...")

    # Configure Chrome options
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in background
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # Set download directory
    output_path = Path(output_dir).absolute()
    output_path.mkdir(parents=True, exist_ok=True)

    prefs = {
        "download.default_directory": str(output_path),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    try:
        # Start browser
        print("Starting browser...")
        driver = webdriver.Chrome(options=options)

        # Open the sheet
        print(f"Opening sheet: {sheet_url}")
        driver.get(sheet_url)

        # Wait for sheet to load
        time.sleep(5)

        # Try to find and click File menu
        print("Looking for File menu...")
        file_menu = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@aria-label, 'File')]"))
        )
        file_menu.click()

        time.sleep(1)

        # Click Download
        download_option = driver.find_element(By.XPATH, "//div[contains(text(), 'Download')]")
        download_option.click()

        time.sleep(1)

        # Click CSV option
        csv_option = driver.find_element(By.XPATH, "//div[contains(text(), 'Comma-separated values')]")
        csv_option.click()

        # Wait for download
        print("Downloading CSV...")
        time.sleep(5)

        print(f"✅ CSV exported to {output_path}")

    except Exception as e:
        print(f"❌ Browser automation failed: {e}")
        print("\nAlternative: Use Google Colab")
        print("Since you can view the sheet, you could:")
        print("1. Create a Google Colab notebook")
        print("2. Use Colab's built-in auth to access the sheet")
        print("3. Export data to CSV or GCS from there")

    finally:
        driver.quit()

# Alternative approach using Google Apps Script
def create_apps_script_exporter():
    """
    Generate a Google Apps Script that can be added to YOUR Google Drive
    to periodically export the Commissioner sheet.
    """
    script = '''
// Google Apps Script to export Commissioner Sheet data
// Add this to your Google Drive: drive.google.com → New → More → Google Apps Script

function exportCommissionerData() {
  var sourceSheetId = "1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY";
  var targetFolderId = "YOUR_GOOGLE_DRIVE_FOLDER_ID"; // Create a folder and put its ID here

  try {
    // Open the source sheet
    var sourceSheet = SpreadsheetApp.openById(sourceSheetId);
    var sheets = sourceSheet.getSheets();

    // Create a new spreadsheet with just values (no formulas)
    var newSheet = SpreadsheetApp.create("Commissioner_Export_" + new Date().toISOString());

    sheets.forEach(function(sheet) {
      var data = sheet.getDataRange().getValues();
      var targetSheet = newSheet.insertSheet(sheet.getName());

      if (data.length > 0 && data[0].length > 0) {
        targetSheet.getRange(1, 1, data.length, data[0].length).setValues(data);
      }
    });

    // Move to folder
    var file = DriveApp.getFileById(newSheet.getId());
    var folder = DriveApp.getFolderById(targetFolderId);
    folder.addFile(file);
    DriveApp.getRootFolder().removeFile(file);

    // Export as CSV to GCS (if you set up Cloud Storage API in Apps Script)
    // ... additional code for GCS export ...

    return newSheet.getUrl();
  } catch (e) {
    console.error("Export failed:", e);
    throw e;
  }
}

// Set up a time-based trigger to run daily
function setupTrigger() {
  ScriptApp.newTrigger('exportCommissionerData')
    .timeBased()
    .everyDays(1)
    .atHour(8)
    .create();
}
'''

    print("="*60)
    print("Google Apps Script Solution")
    print("="*60)
    print(script)
    print("="*60)
    print("\nHow to use:")
    print("1. Go to script.google.com")
    print("2. Create a new project")
    print("3. Paste the code above")
    print("4. Run setupTrigger() once to schedule daily exports")
    print("5. The script will create a copy of the Commissioner sheet with just values")
    print("6. Share the exported sheet with your service account")

if __name__ == "__main__":
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY"

    print("Option 1: Browser Automation")
    print("-" * 30)
    # Uncomment to try:
    # export_sheet_as_csv(SHEET_URL)

    print("\nOption 2: Google Apps Script")
    print("-" * 30)
    create_apps_script_exporter()