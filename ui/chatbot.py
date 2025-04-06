from flask import Flask, request, jsonify
from flask_cors import CORS
from core.openai_api import get_ai_response
from core.processor import handle_translation, handle_custom_update, handle_delete_duplicates

app = Flask(__name__)
CORS(app)

validation_status = {"status": "success"}

@app.before_request
def log_request_info():
    # print(f"\n📥 Incoming Request: {request.method} {request.url}")
    # print(f"🔍 Headers: {dict(request.headers)}")
    if request.method == "POST":
        print(f"📝 Body: {request.get_data(as_text=True)}")

@app.route("/", methods=["GET"])
def home():
    return "<h2>Welcome! Chatbot API is running smoothly. 🚀</h2>", 200

@app.route("/get_response", methods=["POST"])
def get_response():
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"error": "Invalid request, please send a 'message' field"}), 400
    
    user_message = data["message"]

    # 🟢 Check if the user wants to translate
    if "translate" in user_message.lower():
        print("🌐 Translation request detected.")
        translation_response = handle_translation()
        return jsonify({"response": translation_response})
    
    # 🔄 Detect Custom Update Requests
    if user_message.lower().startswith("update:"):
        print("🔄 Custom Update request detected.")
        update_response = handle_custom_update(user_message)
        return jsonify({"response": update_response})
    
    # ✅ Check for "delete: rows"
    if user_message.startswith("delete duplicate rows"):
        print("🗑️ Duplicate row deletion request detected.")
        delete_response = handle_delete_duplicates()
        return jsonify({"response": delete_response})

    bot_response = get_ai_response(user_message)
    return jsonify({"response": bot_response})

@app.route("/update_icon", methods=["POST"])
def update_icon():
    data = request.get_json()
    if not data or "status" not in data:
        return jsonify({"error": "Missing 'status' field"}), 400

    validation_status["status"] = data["status"]
    print(f"🔔 Icon Status Updated: {validation_status['status']}")
    return jsonify({"message": "Status updated successfully"}), 200

@app.route("/get_status", methods=["GET"])
def get_status():
    return jsonify(validation_status)


latest_response = ""

@app.route('/send_to_chatbot', methods=['POST'])
def receive_response():
    global latest_response
    data = request.get_json()
    latest_response = data.get("response", "")
    return jsonify({"message": "Response received successfully"}), 200

@app.route('/get_latest_response', methods=['GET'])
def get_latest_response():
    global latest_response
    if latest_response:
        return jsonify({"response": latest_response}), 200
    else:
        return jsonify({"response": "No AI response available"}), 404



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
