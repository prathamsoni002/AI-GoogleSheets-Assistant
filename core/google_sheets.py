import gspread
import os
import csv
from google.oauth2.service_account import Credentials

class GoogleSheetsManager:
    def __init__(self, spreadsheet_name):
        self.spreadsheet_name = spreadsheet_name
        self.client = self._authenticate()
        self.spreadsheet = self.client.open(self.spreadsheet_name)

    def _authenticate(self):
        try:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = Credentials.from_service_account_file("config/credentials.json", scopes=scopes)
            return gspread.authorize(creds)
        except Exception as e:
            print(f"❗ Error during authentication: {e}")
            raise

    def fetch_data(self, sheet_name='Bin', cell_range=None, save_to_file=False):
        try:
            sheet = self.spreadsheet.worksheet(sheet_name)
            data = sheet.get(cell_range) if cell_range else sheet.get_all_values()

            if save_to_file:
                self._save_to_csv(data, sheet_name)

            print("✅ Data fetched successfully.")
            return data
        except Exception as e:
            print(f"❗ Error fetching data: {e}")
            return None

    def update_data(self, sheet_name='Bin', data=None, cell_range=None):
        try:
            if not data:
                raise ValueError("Data cannot be empty.")
            
            sheet = self.spreadsheet.worksheet(sheet_name)
            
            if cell_range:
                sheet.update(cell_range, data)
            else:
                sheet.clear()
                sheet.update('A1', data)

            print("✅ Data updated successfully.")
        except Exception as e:
            print(f"❗ Error updating data: {e}")

    def update_from_csv(self, sheet_name='Bin', csv_path=None):
        if not csv_path or not os.path.isfile(csv_path):
            print(f"❗ Invalid or missing CSV file: {csv_path}")
            return

        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                data = list(reader)
            
            self.update_data(sheet_name, data)
            print(f"✅ Data updated from CSV: {csv_path}")
        except Exception as e:
            print(f"❗ Error updating from CSV: {e}")

    def _save_to_csv(self, data, sheet_name):
        try:
            os.makedirs('core/fetched_data', exist_ok=True)
            file_path = f'core/fetched_data/{sheet_name}.csv'
            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerows(data)
            print(f"📁 Data saved to {file_path}")
        except Exception as e:
            print(f"❗ Error saving data to CSV: {e}")


    def get_selected_range(self, sheet_name='Bin'):
        """Fetch the selected range stored in Z1."""
        try:
            sheet = self.spreadsheet.worksheet(sheet_name)
            selected_range = sheet.acell('Z1').value
            
            if not selected_range or selected_range == "No selection":
                print("❗ No valid range found in Z1.")
                return None

            print(f"📍 Selected Range from Z1: {selected_range}")
            return selected_range
        except Exception as e:
            print(f"❗ Error fetching selected range: {e}")
            return None

    def get_selected_cells(self, sheet_name='Bin'):
        """Fetch actual data from the selected range."""
        try:
            selected_range = self.get_selected_range(sheet_name)
            
            if not selected_range:
                return None

            sheet = self.spreadsheet.worksheet(sheet_name)
            data = sheet.get(selected_range)
            print("✅ Selected cell data fetched successfully.")
            return data
        except Exception as e:
            print(f"❗ Error fetching selected cells: {e}")
            return None
        
    def delete_rows_by_indices(self, sheet_name='Bin', row_indices=[]):
        """
        Deletes specific rows from the Google Sheet.

        :param sheet_name: Name of the sheet (default is 'Bin').
        :param row_indices: List of row indices to delete (1-based index).
        """
        try:
            sheet = self.spreadsheet.worksheet(sheet_name)
            
            # Sort indices in descending order (to avoid shifting row issues)
            row_indices.sort(reverse=True)

            for row in row_indices:
                sheet.delete_rows(row)
                print(f"🗑️ Deleted row {row}")

            print("✅ All specified rows deleted successfully.")
        except Exception as e:
            print(f"❗ Error deleting rows: {e}")



# Example for CSV Update
# gs_manager = GoogleSheetsManager("TEST AI")
# gs_manager.update_from_csv(sheet_name='Bin', csv_path='path_to_file.csv')
