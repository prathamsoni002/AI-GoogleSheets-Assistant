import requests
import os

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # Ensure your key is set in environment variables

API_URL = "https://api.deepseek.com/v1/chat/completions"

def get_ai_response(user_input):
    if not DEEPSEEK_API_KEY:
        return "DeepSeek API key not found. Please set DEEPSEEK_API_KEY in your environment variables."

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": user_input}],
        "temperature": 0.7,
        "max_tokens": 200
    }

    response = requests.post(API_URL, json=data, headers=headers)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.json()}"  
