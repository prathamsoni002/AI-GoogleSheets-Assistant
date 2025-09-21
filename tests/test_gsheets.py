import gspread
from google.oauth2.service_account import Credentials
import logging

logging.basicConfig(level=logging.INFO)

def test_access():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("config/credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    try:
        spreadsheet = client.open("P1")  # Use your exact name
        logging.info("✅ Access successful! Sheets: " + str([s.title for s in spreadsheet.worksheets()]))
    except Exception as e:
        logging.error(f"❌ Test failed: {e}")

test_access()
