import openai

def get_ai_response(user_input):
    client = openai.OpenAI()

    # Check if the input is a translation request
    if isinstance(user_input, dict) and user_input.get("task") == "translate":
        return handle_translation_request(client, user_input)
    
    # Handle regular chatbot messages
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": user_input}]
    )
    
    return response.choices[0].message.content

def handle_translation_request(client, data):
    try:
        direction = data.get("direction", "English to Spanish")
        cells = data.get("data", [])

        # Format cells into readable string for the AI
        formatted_data = "\n".join([", ".join(map(str, row)) for row in cells])

        prompt = f"""
        You are a translation assistant. 
        Translate the following data from {direction}.
        Maintain the same format (rows and columns).
        
        Data:
        {formatted_data}
        """

        print(f"📝 Translation Prompt:\n{prompt}")

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )

        # Expect AI to return data in the same format
        translated_text = response.choices[0].message.content.strip()

        # Convert translated text back to row-column format
        translated_rows = [row.split(", ") for row in translated_text.split("\n")]
        return translated_rows

    except Exception as e:
        print(f"❗ Error during translation request: {e}")
        return []
    
def get_ai_response(user_input):
    client = openai.OpenAI()

    if isinstance(user_input, dict) and user_input.get("task") == "translate":
        return handle_translation_request(client, user_input)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": user_input}]
    )

    return response.choices[0].message.content
