import os
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
import json

# Load environment variables from .env
load_dotenv()

# Load OpenAI Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Load Google API Credentials from JSON stored as env variable
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
if GOOGLE_CREDENTIALS:
    CREDS_DICT = json.loads(GOOGLE_CREDENTIALS)
    GOOGLE_CREDS = Credentials.from_service_account_info(CREDS_DICT)
else:
    GOOGLE_CREDS = None
