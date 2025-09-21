import gspread
import os
import csv
import pandas as pd
from google.oauth2.service_account import Credentials
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self, spreadsheet_name=None):
        self.spreadsheet_name = spreadsheet_name  # Workbook name = "database" name (can be set dynamically)
        self.client = self._authenticate()
        self.spreadsheet = None  # Loaded on demand
        self.dataframes = {}  # Dictionary to store DataFrames (subsheet_name: df)

        if self.spreadsheet_name:
            try:
                self.spreadsheet = self.client.open(self.spreadsheet_name)
            except Exception as e:
                logger.error(f"❗ Could not open spreadsheet '{self.spreadsheet_name}': {e}")

    def _authenticate(self):
        try:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = Credentials.from_service_account_file("config/credentials.json", scopes=scopes)
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"❗ Error during authentication: {e}")
            raise

    def fetch_data(self, sheet_name='Bin', cell_range=None, save_to_file=False):
        try:
            sheet = self.spreadsheet.worksheet(sheet_name)
            data = sheet.get(cell_range) if cell_range else sheet.get_all_values()

            if save_to_file:
                self._save_to_csv(data, sheet_name)

            logger.info("✅ Data fetched successfully.")
            return data
        except Exception as e:
            logger.error(f"❗ Error fetching data: {e}")
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

            logger.info("✅ Data updated successfully.")
        except Exception as e:
            logger.error(f"❗ Error updating data: {e}")

    def update_from_csv(self, sheet_name='Bin', csv_path=None):
        if not csv_path or not os.path.isfile(csv_path):
            logger.error(f"❗ Invalid or missing CSV file: {csv_path}")
            return

        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                data = list(reader)
            
            self.update_data(sheet_name, data)
            logger.info(f"✅ Data updated from CSV: {csv_path}")
        except Exception as e:
            logger.error(f"❗ Error updating from CSV: {e}")

    def _save_to_csv(self, data, sheet_name):
        try:
            os.makedirs('core/fetched_data', exist_ok=True)
            file_path = f'core/fetched_data/{sheet_name}.csv'
            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerows(data)
            logger.info(f"📁 Data saved to {file_path}")
        except Exception as e:
            logger.error(f"❗ Error saving data to CSV: {e}")

    def get_selected_range(self, sheet_name='Bin'):
        """Fetch the selected range stored in Z1."""
        try:
            sheet = self.spreadsheet.worksheet(sheet_name)
            selected_range = sheet.acell('Z1').value
            
            if not selected_range or selected_range == "No selection":
                logger.warning("❗ No valid range found in Z1.")
                return None

            logger.info(f"📍 Selected Range from Z1: {selected_range}")
            return selected_range
        except Exception as e:
            logger.error(f"❗ Error fetching selected range: {e}")
            return None

    def get_selected_cells(self, sheet_name='Bin'):
        """Fetch actual data from the selected range."""
        try:
            selected_range = self.get_selected_range(sheet_name)
            
            if not selected_range:
                return None

            sheet = self.spreadsheet.worksheet(sheet_name)
            data = sheet.get(selected_range)
            logger.info("✅ Selected cell data fetched successfully.")
            return data
        except Exception as e:
            logger.error(f"❗ Error fetching selected cells: {e}")
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
                logger.info(f"🗑️ Deleted row {row}")

            logger.info("✅ All specified rows deleted successfully.")
        except Exception as e:
            logger.error(f"❗ Error deleting rows: {e}")


    def save_dataframes_to_csv(self, output_dir='core/dataframes'):
        """
        Save DataFrames to CSV files organized by workbook name.
        Creates: ./core/dataframes/WorkbookName/SheetName.csv
        Updates existing files if they already exist.
        """
        if not self.dataframes:
            logger.warning("❗ No DataFrames to save.")
            return
        
        try:
            # Create workbook-specific directory
            workbook_dir = os.path.join(output_dir, self.spreadsheet_name)
            os.makedirs(workbook_dir, exist_ok=True)
            logger.info(f"📁 Created/verified directory: {workbook_dir}")
            
            updated_files = []
            new_files = []
            
            for sheet_name, df in self.dataframes.items():
                # Clean sheet name for filename (remove invalid characters)
                safe_sheet_name = "".join(c for c in sheet_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                file_path = os.path.join(workbook_dir, f"{safe_sheet_name}.csv")
                
                # Check if file already exists
                file_exists = os.path.exists(file_path)
                
                # Save DataFrame to CSV
                df.to_csv(file_path, index=False, encoding='utf-8')
                
                if file_exists:
                    updated_files.append(safe_sheet_name)
                    logger.info(f"🔄 Updated existing file: {file_path}")
                else:
                    new_files.append(safe_sheet_name)
                    logger.info(f"💾 Created new file: {file_path}")
            
            # Summary logging
            total_files = len(updated_files) + len(new_files)
            logger.info(f"✅ Saved {total_files} DataFrames for '{self.spreadsheet_name}':")
            if new_files:
                logger.info(f"   📝 New files: {', '.join(new_files)}")
            if updated_files:
                logger.info(f"   🔄 Updated files: {', '.join(updated_files)}")
            
            return {
                "status": "success",
                "workbook": self.spreadsheet_name,
                "directory": workbook_dir,
                "new_files": new_files,
                "updated_files": updated_files,
                "total_files": total_files
            }
            
        except Exception as e:
            logger.error(f"❗ Error saving DataFrames to CSV: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


    def list_existing_csv_files(self, output_dir='core/dataframes'):
        """
        List existing CSV files for the current workbook.
        Returns dictionary with file info.
        """
        workbook_dir = os.path.join(output_dir, self.spreadsheet_name)
        
        if not os.path.exists(workbook_dir):
            return {"exists": False, "files": []}
        
        csv_files = [f for f in os.listdir(workbook_dir) if f.endswith('.csv')]
        file_info = []
        
        for csv_file in csv_files:
            file_path = os.path.join(workbook_dir, csv_file)
            file_stat = os.stat(file_path)
            file_info.append({
                "name": csv_file,
                "sheet_name": csv_file[:-4],  # Remove .csv extension
                "size_bytes": file_stat.st_size,
                "last_modified": file_stat.st_mtime
            })
        
        return {
            "exists": True,
            "directory": workbook_dir,
            "files": file_info,
            "total_files": len(csv_files)
        }

    
    # NEW: Convert subsheet to DataFrame (headers row 5, data row 9+)
    def sheet_to_dataframe(self, sheet_name, header_row=5, data_start_row=9, min_total_rows=5):
        try:
            sheet = self.spreadsheet.worksheet(sheet_name)
            values = sheet.get_all_values()
            
            total_rows = len(values)
            logger.info(f"Sheet '{sheet_name}' has {total_rows} total rows")
            
            # Check for minimum total rows (just enough for headers; adjust if needed)
            if total_rows < min_total_rows:
                logger.warning(f"❗ Sheet '{sheet_name}' has fewer than {min_total_rows} rows (only {total_rows}). Skipping.")
                return None
            
            # Headers from specified row (0-based: header_row - 1)
            headers = values[header_row - 1]
            logger.info(f"Headers from row {header_row}: {headers[:5]}...")  # Show first 5 headers
            
            # Data from specified start row (0-based: data_start_row - 1) to end
            data_rows = values[data_start_row - 1:]
            potential_data_rows = len(data_rows)
            logger.info(f"Potential data rows from row {data_start_row}: {potential_data_rows} available")
            
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            
            # Clean: Replace empty strings with NA and drop rows that are ALL NA (entirely empty)
            # This keeps rows with partial data (e.g., some columns filled, others blank)
            original_shape = df.shape
            df = df.replace('', pd.NA).dropna(how='all')
            cleaned_shape = df.shape
            logger.info(f"DataFrame shape: {original_shape} → {cleaned_shape} after cleaning (dropped {original_shape[0] - cleaned_shape[0]} fully empty rows)")
            
            # If no data rows remain after cleaning, skip the sheet
            if df.empty:
                logger.warning(f"❗ Sheet '{sheet_name}' has no valid data rows from row {data_start_row} (all empty after cleaning). Skipping.")
                return None
            
            # Optional: Drop fully empty columns if desired (uncomment if needed)
            # df = df.dropna(axis=1, how='all')
            
            return df
        except Exception as e:
            logger.error(f"❗ Error converting sheet '{sheet_name}' to DataFrame: {e}")
            return None

    
    #  Return a dict of {sheet-name: DataFrame}, skipping unwanted tabs
    # ------------------------------------------------------------------
    def fetch_workbook_as_dataframes(self, force_update=False):
        if self.spreadsheet is None:
            logger.error("Spreadsheet not loaded; cannot fetch worksheets")
            return None

        try:
            self.dataframes = {}
            subsheets = self.spreadsheet.worksheets()
            logger.info(f"Found {len(subsheets)} total sheets in workbook")
            
            for subsheet in subsheets:
                sheet_name = subsheet.title
                logger.info(f"Processing sheet: '{sheet_name}'")
                
                # Skip unwanted sheets
                if sheet_name.lower() in ["introduction", "field list"]:
                    logger.info(f"Skipping sheet '{sheet_name}' (excluded by design)")
                    continue
                
                df = self.sheet_to_dataframe(sheet_name, header_row=5, data_start_row=9, min_total_rows=5)
                if df is not None:
                    logger.info(f"Successfully created DataFrame for '{sheet_name}' with shape {df.shape}")
                    self.dataframes[sheet_name] = df
                else:
                    logger.warning(f"No DataFrame created for '{sheet_name}' (no valid data)")

            logger.info(f"✅ Total DataFrames created: {len(self.dataframes)} sheets")
            return self.dataframes
        except Exception as e:
            logger.error(f"❗ Error fetching workbook as DataFrames: {e}")
            return {}

    # NEW: Parse message to extract workbook name and trigger on "ready for analysis"
    def process_message(self, message):
        msg_lower = message.strip().lower()
        if msg_lower.endswith("ready for analysis"):
            # Extract workbook name from the message (everything before "ready for analysis")
            extracted_name = message[: -len("ready for analysis")].strip()
            if extracted_name:
                self.spreadsheet_name = extracted_name
                logger.info(f"✅ Workbook name extracted: '{self.spreadsheet_name}'")
                try:
                    self.spreadsheet = self.client.open(self.spreadsheet_name)
                except Exception as e:
                    logger.error(f"❗ Could not open workbook '{self.spreadsheet_name}': {e}")
                    return None
                return self.fetch_workbook_as_dataframes(force_update=True)  # Force update if already exists
            else:
                logger.warning("❗ No workbook name provided in message.")
                return None
        else:
            logger.info("❗ Message does not match trigger. No action taken.")
            return None
