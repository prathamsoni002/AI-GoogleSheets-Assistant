import json
from core.google_sheets import GoogleSheetsManager
from core.openai_api import get_ai_response
from langdetect import detect

def handle_translation():
    try:
        print("🔎 Fetching selected cells for translation...")
        gs_manager = GoogleSheetsManager("TEST AI")

        # Step 1: Get selected range
        selected_range = gs_manager.get_selected_range(sheet_name='Bin')

        if not selected_range:
            return "❗ No valid selection detected. Please try again."

        # Step 2: Fetch the data from the selected range
        selected_cells = gs_manager.get_selected_cells(sheet_name='Bin')

        if not selected_cells:
            print("❗ No data found in the selected range.")
            return "No data found for translation."

        print("📊 Selected Cells for Translation:")
        for row in selected_cells:
            print(row)

        # Step 3: Determine the language using the first cell
        sample_text = selected_cells[0][0] if selected_cells[0] else ""
        if not sample_text.strip():
            print("❗ First cell is empty, cannot determine language.")
            return "Cannot detect language from empty cell."

        language_direction = "English to Spanish" if is_english(sample_text) else "Spanish to English"
        print(f"🧾 Detected Language: {language_direction}")

        # Step 4: Prepare structured data and prompt
        prompt_data = json.dumps(selected_cells)
        prompt = f"""
        You are a translation assistant.
        Translate the following data from {language_direction}.
        Maintain the same format (rows and columns) in the translated output.
        Respond using a valid JSON array format with rows and columns.
        Do not merge or combine the sentences. 

        Data:
        {prompt_data}
        """

        # Step 5: Call OpenAI API to perform the translation
        print("🔄 Sending data for translation...")
        translated_response = get_ai_response(prompt)

        # Step 6: Parse and validate response
        try:
            translated_data = json.loads(translated_response)

            if not isinstance(translated_data, list) or not all(isinstance(row, list) for row in translated_data):
                print("❗ Invalid response format. Expected a 2D matrix.")
                return "Translation failed: Invalid response format."
        except Exception as e:
            print(f"❗ Failed to parse AI response: {e}")
            return "Translation failed: Invalid response data."

        print("✅ Translated Data:")
        for row in translated_data:
            print(row)

        # Step 7: Update the translated data back to the original range
        print(f"⬆️ Updating translated data to {selected_range}...")
        gs_manager.update_data(sheet_name='Bin', data=translated_data, cell_range=selected_range)

        print("✅ Translation successfully updated in Google Sheets.")
        return "✅ Translation successful and updated in Google Sheets."

    except Exception as e:
        print(f"❗ Error in handle_translation: {e}")
        return "An error occurred while processing the translation request."

def is_english(text):
    """Detect if the given text is in English."""
    try:
        detected_lang = detect(text)
        return detected_lang == "en"
    except Exception as e:
        print(f"❗ Error detecting language: {e}")
        return False


def handle_custom_update(user_request):
    try:
        print("📥 Fetching all sheet data for modification...")
        gs_manager = GoogleSheetsManager("TEST AI")

        # ✅ Fetch entire sheet data
        all_data = gs_manager.fetch_data(sheet_name='Bin')

        if not all_data:
            return "❗ No data found in the sheet."

        headers = all_data[0]  # First row as headers
        body_data = all_data[1:]  # Rest as data

        # 📝 Prepare prompt for AI
        prompt = f"""
        You are a data processing assistant.
        Below is the dataset structure:

        Headers: {headers}
        Data:
        {json.dumps(body_data)}

        User Request: "{user_request}"

        Modify the data accordingly and return it in JSON format:
        {{
            "headers": [...],   // Keep headers unchanged
            "data": [ [...], [...], ... ]  // Modified row data
        }}
        """

        print("🔄 Sending data for modification...")
        modified_response = get_ai_response(prompt)

        # ✅ Parse AI response
        try:
            response_json = json.loads(modified_response)
            
            if isinstance(response_json, dict) and "headers" in response_json and "data" in response_json:
                modified_headers = response_json["headers"]
                modified_data = response_json["data"]
            else:
                return "❗ AI Response Invalid Format."

        except json.JSONDecodeError:
            return "❗ AI Response Parsing Failed. Invalid JSON."

        print("✅ Modified Data:")
        for row in modified_data:
            print(row)

        # ✅ Combine headers + modified data
        full_data = [modified_headers] + modified_data

        print("⬆️ Updating Google Sheets with modified data...")
        gs_manager.update_data(sheet_name='Bin', data=full_data, cell_range="A1")

        return "✅ Data modification successful and updated in Google Sheets."

    except Exception as e:
        print(f"❗ Error in handle_custom_update: {e}")
        return "An error occurred while processing the custom update request."
    

def handle_delete_duplicates():
    try:
        print("📥 Fetching all sheet data for duplicate removal...")
        gs_manager = GoogleSheetsManager("TEST AI")

        # ✅ Fetch entire sheet data
        all_data = gs_manager.fetch_data(sheet_name='Bin')

        if not all_data:
            return "❗ No data found in the sheet."

        headers = all_data[0]  # First row as headers
        body_data = all_data[1:]  # Rest as data (actual rows)

        # ✅ Remove duplicate rows, keeping only the first occurrence
        seen = set()
        duplicate_indices = []  # Store row indices of duplicates

        for i, row in enumerate(body_data, start=2):  # Start index at 2 (1-based row index)
            row_tuple = tuple(row)  # Convert list to tuple (hashable)
            if row_tuple in seen:
                duplicate_indices.append(i)  # Store duplicate row index
            else:
                seen.add(row_tuple)

        if not duplicate_indices:
            return "✅ No duplicate rows found."

        print(f"🗑️ Deleting {len(duplicate_indices)} duplicate rows...")

        # ✅ Call new method to delete specific rows
        gs_manager.delete_rows_by_indices(sheet_name="Bin", row_indices=duplicate_indices)

        return f"✅ {len(duplicate_indices)} duplicate rows deleted."

    except Exception as e:
        print(f"❗ Error in handle_delete_duplicates: {e}")
        return "An error occurred while deleting duplicate rows."


