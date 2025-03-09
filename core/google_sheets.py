import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
CREDS = Credentials.from_service_account_file("config/credentials.json", scopes=SCOPES)

client = gspread.authorize(CREDS)

SPREADSHEET_NAME = "TEST AI"
sheet = client.open(SPREADSHEET_NAME).sheet1

sheet.update("A1", [["HelloWorld"]])
sheet.update("A2:B3", [["Hello", "World"], ["123", "456"]])

print("✅ Successfully wrote 'HelloWorld' in A1!")
