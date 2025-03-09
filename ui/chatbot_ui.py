from flask import Flask, render_template, request, jsonify
import openai
import os

app = Flask(__name__)

# Load API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/")
def index():
    return render_template("chatbot.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    
    # Dummy AI response (Replace with OpenAI call if needed)
    ai_response = f"I received: {user_message}"
    
    return jsonify({"reply": ai_response})

if __name__ == "__main__":
    app.run(debug=True)
