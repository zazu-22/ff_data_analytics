'''
This script provides functions to interact with Google Sheets and export data
from a specified Google Sheet to CSV files in Google Drive.

It requires the user to authenticate with Google and have the 'gspread' and
'pandas' libraries installed. Authentication is handled using Google Colab's
built-in authentication methods, making it suitable for use within a Colab environment.

The script defines the following key functions:
- get_worksheet_names: Retrieves the names of all worksheets within a given Google Sheet.
- make_df_from_sheet: Reads data from a specific worksheet into a pandas DataFrame.
- make_dfs_from_ws_list: Reads data from multiple worksheets into a dictionary of DataFrames.
- df_to_csv: Converts a pandas DataFrame to a CSV formatted string.
- save_to_drive: Saves a CSV formatted string as a file in Google Drive, with an optional folder specification.
- export_to_drive: Orchestrates the process of fetching data from all worksheets in a Google Sheet and saving them as individual CSV files in Google Drive.

The main part of the script prompts the user for the Google Sheet name and an
optional Google Drive folder ID, then calls the export_to_drive function to
perform the export.
'''

import pandas as pd
from typing import List, Dict, Any

# Note: The following lines assume authentication has been handled prior to running this script.
# In a Google Colab environment, 'google.colab.auth' and 'gspread' with 'google.auth'
# are typically used for authentication. Make sure these steps are executed before
# calling the functions in this script if running outside of the existing notebook flow.
#
# from google.colab import auth
# auth.authenticate_user()
# import gspread
# from google.auth import default
# creds, _ = default()
# gc = gspread.authorize(creds)
#
# Also requires 'pydrive2' for saving to Google Drive.
# from pydrive2.auth import GoogleAuth
# from pydrive2.drive import GoogleDrive
# from google.colab import auth
# from oauth2client.client import GoogleCredentials
# auth.authenticate_user()
# gauth = GoogleAuth()
# gauth.credentials = GoogleCredentials.get_application_default()
# drive = GoogleDrive(gauth)


# sh = 'wingman_payload_rev001' # This variable is now taken as input in the main script

def get_worksheet_names(sh: str) -> List[str]:
  '''Takes Google Sheet name and returns a list of worksheet titles.'''
  worksheet_names = gc.open(sh).worksheets()
  return [worksheet.title for worksheet in worksheet_names]

def make_df_from_sheet(sh: str, ws: str) -> pd.DataFrame:
  '''Takes Google Sheet name and worksheet name and returns a DataFrame.'''
  worksheet = gc.open(sh).worksheet(ws)
  rows = worksheet.get_all_values()
  # Assuming the first row contains headers
  df = pd.DataFrame.from_records(rows[1:], columns=rows[0])
  return df

def make_dfs_from_ws_list(sh: str, ws_list: List[str]) -> Dict[str, pd.DataFrame]:
  '''Takes Google Sheet name and a list of worksheet names and returns a dictionary of DataFrames.'''
  dfs = {}
  for ws in ws_list:
    dfs[ws] = make_df_from_sheet(sh, ws)
  return dfs

def df_to_csv(df: pd.DataFrame) -> str:
  '''Takes a DataFrame and converts it to a CSV string.'''
  return df.to_csv(index=False)

def save_to_drive(csv_file_content: str, sheet_name: str, worksheet_name: str, drive_folder_id: str = None):
  '''Takes CSV content and saves it to a specified Drive folder with a programmatic file name.'''
  file_name = f"{sheet_name}_{worksheet_name}.csv"
  file_metadata = {'title': file_name}
  if drive_folder_id:
      file_metadata['parents'] = [{'id': drive_folder_id}]

  uploaded = drive.CreateFile(file_metadata)
  uploaded.SetContentString(csv_file_content)
  uploaded.Upload()
  print(f'Uploaded file "{file_name}" with ID {uploaded.get("id")}')


def export_to_drive(sh: str, drive_folder_id: str = None):
  '''Orchestrates the above functions to export a Google Sheet to CSV files in Drive.'''
  ws_list = get_worksheet_names(sh)
  dfs = make_dfs_from_ws_list(sh, ws_list)
  for ws in ws_list:
    csv_file_content = df_to_csv(dfs[ws])
    save_to_drive(csv_file_content, sh, ws, drive_folder_id)

# Main script to take user input and run the export
if __name__ == '__main__':
  sheet_name_input = input("Enter the Google Sheet name: ")
  drive_folder_id_input = input("Enter the Drive folder ID (optional, press Enter to save to root): ")

  if drive_folder_id_input:
    export_to_drive(sheet_name_input, drive_folder_id=drive_folder_id_input)
  else:
    export_to_drive(sheet_name_input)
