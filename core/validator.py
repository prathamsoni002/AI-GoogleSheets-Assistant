import requests
from core.google_sheets import GoogleSheetsManager
from core.openai_api import get_ai_response
import re

class Validator:
    def __init__(self, spreadsheet_name="TEST AI"):
        self.gs_manager = GoogleSheetsManager(spreadsheet_name)
        self.rules = self.gs_manager.fetch_data(sheet_name='Rules')[1:]  # Skip headers
        self.errors = []

    def validate(self):
        for rule in self.rules:
            rule_code, rule_text, columns, values = rule
            columns = columns.split(',')
            
            if hasattr(self, rule_code):
                getattr(self, rule_code)(columns, values)
            else:
                print(f"❗ No validation function found for rule: {rule_code}")

        # If errors exist, send to AI for suggestions
        if self.errors:
            print("🧠 Sending errors to OpenAI for analysis...")
            self._send_errors_to_ai()
        else:
            self._report_status()  # Report success if no errors
        
        return self.errors

    def wh(self, columns, values):
        data = self.gs_manager.fetch_data(sheet_name='Bin')[1:]  # Skip header row
        col_index = ord(columns[0].upper()) - 65
        valid_values = values.split(',')

        for i, row in enumerate(data, start=2):
            if len(row) > col_index and row[col_index] not in valid_values:
                self._record_error("If warehouse column have right values or not", f"Row {i}: Invalid value '{row[col_index]}' in Column {columns[0]}.", 'wh')

    def dup(self, columns, values):
        data = self.gs_manager.fetch_data(sheet_name='Bin')[1:]  # Skip header row
        col_index = ord(columns[0].upper()) - 65
        seen = set()

        for i, row in enumerate(data, start=2):
            if len(row) > col_index:
                cell_value = row[col_index]
                if cell_value in seen:
                    self._record_error("If we find any duplicate values or not", f"Row {i}: Duplicate value '{cell_value}' found in Column {columns[0]}.", 'dup')
                else:
                    seen.add(cell_value)

    def row_dup(self, columns, values):
        data = self.gs_manager.fetch_data(sheet_name='Bin')[1:]  # Skip header row
        seen = set()

        for i, row in enumerate(data, start=2):
            row_tuple = tuple(row)
            if row_tuple in seen:
                self._record_error("If Rows are repeated or not", f"Row {i}: Duplicate row detected.", 'row_dup')
            else:
                seen.add(row_tuple)

    def bin_for(self, columns, values):
        data = self.gs_manager.fetch_data(sheet_name='Bin')[1:]  # Skip header row
        col_index = ord(columns[0].upper()) - 65
        pattern = re.compile(r'^[A-Z]{2}-\d{2}-\d{3}$')

        for i, row in enumerate(data, start=2):
            if len(row) > col_index and not pattern.match(row[col_index]):
                self._record_error("If the values in the column Bin matches the given format", f"Row {i}: Invalid bin format '{row[col_index]}' in Column {columns[0]}.", 'bin_for')

    def map_false(self, columns, values):
        data = self.gs_manager.fetch_data(sheet_name='Bin')[1:]  # Skip header row
        col1_index = ord(columns[0].upper()) - 65
        col2_index = ord(columns[1].upper()) - 65
        val1, val2 = values.split(',')

        for i, row in enumerate(data, start=2):
            if len(row) > max(col1_index, col2_index) and row[col1_index] == val1 and row[col2_index] == val2:
                self._record_error("If the combination of values entered in Storage type and storage section are right or wrong", f"Row {i}: Invalid combination of '{val1}' and '{val2}' in Columns {columns[0]} and {columns[1]}.", 'map_false')

    def _record_error(self, action, error_message, rule_code):
        backend_message = (f"This is from the backend. We performed the validation method '{rule_code}' to check {action} "
                            f"It failed because: {error_message}")
        self.errors.append(backend_message)
        print(f"❗ {backend_message}")

    def _report_status(self):
        status = "error" if self.errors else "success"
        try:
            requests.post('http://localhost:5000/update_icon', json={'status': status})
            print(f"✅ Status reported to server: {status}")
        except requests.RequestException as e:
            print(f"❗ Failed to report status: {e}")

    def _send_errors_to_ai(self):
        ai_input = f"While performing the python code to check errors in google sheet we found some errors:\n\n" + "\n".join(self.errors) + "\n Please generate a simple 2-3 lines response for my users explaining what is the error. Make it short no need to explain the function names or anything. Just important thing necessary to understand what and where is the issue in the google sheets."
        print("📤 Sending errors to AI via API...")

        try:
            response = requests.post(
                "http://localhost:5000/get_response",
                json={"message": ai_input},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "No response from AI")
                print("\n🧠 AI Response:")
                print(ai_response)

                # Forward to chatbot and THEN report error status
                self._forward_to_chatbot(ai_response)
                self._report_status()
            else:
                print(f"❗ API Error: {response.status_code} - {response.json()}")

        except requests.RequestException as e:
            print(f"❗ Failed to communicate with AI API: {e}")

    def _forward_to_chatbot(self, ai_response):
        print("📤 Forwarding AI response to chatbot...")
        try:
            response = requests.post(
                "http://localhost:5000/send_to_chatbot",
                json={"response": ai_response},
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                print("✅ Response successfully sent to chatbot.")
            else:
                print(f"❗ Failed to send to chatbot: {response.status_code} - {response.json()}")

        except requests.RequestException as e:
            print(f"❗ Error while sending to chatbot: {e}")


# Example usage
validator = Validator()
errors = validator.validate()
if errors:
    print("\nValidation completed with errors:")
    for error in errors:
        print(error)
else:
    print("✅ All validations passed.")
