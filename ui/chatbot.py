from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import requests
import json
import os
import tempfile
import re
import logging
import gspread  # For exceptions like SpreadsheetNotFound
from core.google_sheets import GoogleSheetsManager
from core.openai_api import get_ai_response
from core.processor import handle_translation, handle_custom_update, handle_delete_duplicates
from dataWarehouse.dataExtract import extract_validation_errors
from werkzeug.exceptions import RequestEntityTooLarge
from ui.email_handler import EmailHandler
from dataWarehouse.visual_product_analyzer import generate_visual_product_report

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CORRECTED FLASK APP INITIALIZATION ---
# Determine the absolute path to the project's root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
# Define the absolute path to the static folder
static_folder_path = os.path.join(project_root, 'static')

# Initialize Flask, telling it exactly where to find the static files.
# This is a more robust solution than using a relative path like '../static'.
app = Flask(__name__, static_folder=static_folder_path, static_url_path='/static')
# ------------------------------------------

CORS(app)

email_handler = EmailHandler()

# CRITICAL: Set high upload limit
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return jsonify({
        "error": "File size exceeds maximum allowed limit of 100MB"
    }), 413

# Selenium service configuration
SELENIUM_SERVICE_URL = "http://localhost:5001"  # Your selenium service

validation_status = {"status": "success"}
latest_response = ""

@app.before_request
def log_request_info():
    if request.method == "POST":
        print(f"📝 Body: {request.get_data(as_text=True)}")

# ===== ERROR ANALYSIS FUNCTIONS (SIMPLIFIED) =====

def create_error_analysis_prompt(error_data: dict) -> str:
    """Create AI prompt from error data - simple like validator"""
    error_summary = error_data.get("error_summary", [])
    metadata = error_data.get("metadata", {})
    
    # Create simple error descriptions
    error_descriptions = []
    for error in error_summary[:5]:  # Limit to top 5 errors
        error_descriptions.append(
            f"• Message #{error['message_number']}: {error['message_title']} "
            f"({error['total_occurrences']} occurrences)"
        )
    
    # Simple prompt like validator
    prompt = prompt = f"""Migration validation found {len(error_summary)} types of errors:

        {chr(10).join(error_descriptions)}

        Total error occurrences: {metadata.get('total_error_occurrences', 0)}

        Please provide a clear analysis of these migration errors including:
        1. What each error means and its business impact
        2. Which errors should be prioritized (most frequent first)
        3. Specific steps to fix these issues
        4. How to prevent similar errors in future migrations

        Keep the response comprehensive but well-structured for the migration team."""
    
    return prompt

def handle_error_file_analysis_direct(error_file_path: str) -> bool:
    """
    Handle error analysis directly - set latest_response and trigger status
    """
    global latest_response
    
    try:
        print(f"🔍 Processing error file: {error_file_path}")
        
        # Step 1: Extract error data
        error_data = extract_validation_errors(error_file_path)
        
        if error_data["status"] != "success":
            latest_response = f"❌ Error Analysis Failed: {error_data.get('message', 'Unknown error')}"
            return False
        
        # Step 2: Create AI prompt
        ai_prompt = create_error_analysis_prompt(error_data)
        print(f"📝 Created prompt (length: {len(ai_prompt)})")
        
        # Step 3: Get AI response directly (same as get_response does)
        print("🤖 Getting AI analysis...")
        ai_response = get_ai_response(ai_prompt)
        
        print(f"✅ AI analysis completed (length: {len(ai_response)})")
        
        # Step 4: Set the response directly
        latest_response = ai_response
        
        # Step 5: FIRST set status to success, THEN to error to trigger fetch
        print("📤 Resetting status to success first...")
        try:
            # First set to success
            requests.post(
                'http://localhost:5000/update_icon', 
                json={'status': 'success'},
                timeout=5
            )
            print("✅ Status set to success")
            
            # Wait a moment
            import time
            time.sleep(1)
            
            # Then set to error to trigger the fetch
            requests.post(
                'http://localhost:5000/update_icon', 
                json={'status': 'error'},
                timeout=5
            )
            print("✅ Status set to error - frontend should fetch the analysis now")
            
        except Exception as e:
            print(f"❗ Failed to update status: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error analysis failed: {str(e)}")
        latest_response = f"❌ Error Analysis System Error: {str(e)}"
        return False

# ===== MAIN ENDPOINTS =====

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "MITRA AI Chatbot + Migration Proxy + Error Analyzer + Email Intelligence + Visual Product Report",
        "version": "4.1.0",
        "endpoints": {
            "chat": "/get_response (POST)",
            "status": "/get_status (GET)",
            "latest": "/get_latest_response (GET)",
            "migration": "/migration/* (Proxied to selenium service)"
        }
    })

@app.route("/get_response", methods=["POST"])
def get_response():
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"error": "Invalid request, please send a 'message' field"}), 400

    user_message = data["message"]

    # ── VISUAL PRODUCT MASTER REPORT CHECK (UPDATED) ─────────────────────────────
    if "report:" in user_message.lower():
        try:
            logger.info(f"📊 Visual product report request detected: {user_message}")
            
            # Parse the report request: "report: {product_number} in {workbook_name}"
            report_content = user_message.replace("report:", "").strip()
            
            # Expected format: "product_number in workbook_name"
            if " in " in report_content:
                parts = report_content.split(" in ")
                if len(parts) == 2:
                    product_number = parts[0].strip()
                    workbook_name = parts[1].strip()
                    
                    print(f"📊 Generating visual report - Product: '{product_number}', Workbook: '{workbook_name}'")
                    logger.info(f"Visual product report request - Product: {product_number}, Workbook: {workbook_name}")
                    
                    # Generate the visual product master report
                    report_result = generate_visual_product_report(workbook_name, product_number)
                    
                    # Check if report generation was successful
                    if report_result.get('status') == 'error':
                        error_msg = f"❌ Report generation failed: {report_result.get('message', 'Unknown error')}"
                        logger.error(error_msg)
                        return jsonify({"response": error_msg})
                    
                    # Format successful response with visual report data
                    success_msg = f"✅ Visual product report generated successfully for '{product_number}' in '{workbook_name}'\n\n"
                    
                    # Add AI insights if available
                    if report_result.get('ai_insights'):
                        success_msg += "🤖 **AI Analysis:**\n"
                        success_msg += report_result['ai_insights'] + "\n\n"
                    
                    # Add visualization information
                    if report_result.get('visualization_urls'):
                        success_msg += "📊 **Generated Visualizations:**\n"
                        viz_urls = report_result['visualization_urls']
                        
                        viz_names = {
                            'hierarchy': 'Product Hierarchy Tree',
                            'coverage': 'Organizational Coverage Chart', 
                            'warehouse': 'Warehouse Operations Flow',
                            'completeness': 'Data Completeness Dashboard'
                        }
                        
                        for viz_key, url in viz_urls.items():
                            display_name = viz_names.get(viz_key, viz_key.title())
                            success_msg += f"- {display_name}: {url}\n"
                    
                    # Log successful generation
                    logger.info(f"✅ Visual report generated successfully for {product_number}")
                    print(f"✅ PNG files saved to static/visual_outputs/{workbook_name}/{product_number}/")
                    
                    return jsonify({
                        "response": success_msg,
                        "report_data": report_result  # Include full report data for frontend
                    })
                    
                else:
                    error_msg = "❌ Invalid report format. Use: report: {product_number} in {workbook_name}"
                    logger.warning(f"Invalid report format: {user_message}")
                    return jsonify({"response": error_msg})
            else:
                error_msg = "❌ Invalid report format. Expected 'report: {product_number} in {workbook_name}'"
                logger.warning(f"Missing 'in' keyword: {user_message}")
                return jsonify({"response": error_msg})
                
        except Exception as e:
            error_msg = f"❌ Visual product report generation error: {str(e)}"
            logger.error(f"Visual product report error: {e}")
            print(error_msg)
            return jsonify({"response": error_msg})

    # ── EMAIL INTELLIGENCE CHECK (UPDATED) ─────────────────────────────────
    if email_handler.is_email_query(user_message):
        logger.info(f"📧 Email query detected: {user_message[:50]}...")
        email_response = email_handler.process_email_query(user_message)
        return jsonify({"response": email_response})

    # ── 1. Preprocess message to remove brackets and extra spaces ──────────
    cleaned_message = re.sub(r'[\[\]\(\)\{\}]', '', user_message).strip()
    lower_cleaned = cleaned_message.lower()

    trigger_phrases = ["ready", "ready for analysis"]
    for trigger in trigger_phrases:
        if lower_cleaned.endswith(trigger):
            workbook_name = cleaned_message[:-len(trigger)].strip()
            if not workbook_name:
                return jsonify({"response": "❌ Please provide a workbook name before the trigger phrase."})
            
            print(f"📊 Trigger detected → workbook = '{workbook_name}'")
            try:
                gs_mgr = GoogleSheetsManager(workbook_name)
                
                # Explicitly load the spreadsheet (this mimics what your test does)
                gs_mgr.spreadsheet = gs_mgr.client.open(workbook_name)
                logger.info(f"✅ Spreadsheet '{workbook_name}' loaded successfully.")
                
                # Now fetch DataFrames
                dfs = gs_mgr.fetch_workbook_as_dataframes()
                
                # Optional: Save to CSV if using that method
                gs_mgr.save_dataframes_to_csv()
                
                # In the get_response() function, after dfs = gs_mgr.fetch_workbook_as_dataframes()
                if dfs:
                    # Save DataFrames to CSV with enhanced functionality
                    save_result = gs_mgr.save_dataframes_to_csv()
                    
                    sheets = ", ".join(dfs.keys())
                    
                    if save_result["status"] == "success":
                        msg = f"✅ DataFrames created and saved for '{workbook_name}'. "
                        msg += f"Sheets processed: {sheets}. "
                        msg += f"Directory: {save_result['directory']}. "
                        
                        if save_result["new_files"]:
                            msg += f"New files: {len(save_result['new_files'])}. "
                        if save_result["updated_files"]:
                            msg += f"Updated files: {len(save_result['updated_files'])}."
                    else:
                        msg = f"✅ DataFrames created for '{workbook_name}' (Sheets: {sheets}) but CSV save failed: {save_result['message']}"
                else:
                    msg = f"❌ No valid sheets found in '{workbook_name}' (check data from row 9)."

            except gspread.exceptions.SpreadsheetNotFound:
                msg = f"❌ Workbook '{workbook_name}' not found. Check the name and sharing settings."
            except Exception as err:
                msg = f"❌ Error processing '{workbook_name}': {err}"
                logger.error(f"❗ Detailed error: {err}")
            
            return jsonify({"response": msg})

    # ── 3. other special commands ─────────────────────────────────────────
    if "translate" in user_message.lower():
        return jsonify({"response": handle_translation()})

    if user_message.lower().startswith("update:"):
        return jsonify({"response": handle_custom_update(user_message)})

    if user_message.lower().startswith("delete duplicate rows"):
        return jsonify({"response": handle_delete_duplicates()})

    # ── 4. normal AI reply ────────────────────────────────────────────────
    return jsonify({"response": get_ai_response(user_message)})

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

@app.route('/get_latest_response', methods=['GET'])
def get_latest_response():
    global latest_response
    print(f"DEBUG: Frontend requesting latest response (length: {len(latest_response) if latest_response else 0})")
    
    if latest_response:
        response_to_send = latest_response
        print(f"DEBUG: Sending response: {response_to_send[:100]}...")
        return jsonify({"response": response_to_send}), 200
    else:
        print("DEBUG: No response available")
        return jsonify({"response": "No AI response available"}), 404

@app.route('/send_to_chatbot', methods=['POST'])
def receive_response():
    global latest_response
    data = request.get_json()
    
    # Handle error analysis requests from Selenium service
    if data.get("type") == "error_analysis" and data.get("file_path"):
        print("📊 Error file analysis request received from Selenium service...")
        
        success = handle_error_file_analysis_direct(data["file_path"])
        
        if success:
            print("✅ Error analysis completed - response ready for frontend")
        else:
            print("❌ Error analysis failed")
            
        return jsonify({"message": "Error analysis processed"}), 200
    
    # Handle regular response forwarding (like validator)
    if "response" in data:
        latest_response = data.get("response", "")
        print(f"DEBUG: Regular response received (length: {len(latest_response)})")
        return jsonify({"message": "Response received successfully"}), 200
    
    return jsonify({"message": "No valid data received"}), 400

# ===== DIRECT ERROR ANALYSIS ENDPOINT =====

@app.route('/analyze_error_file', methods=['POST'])
def analyze_error_file():
    """
    Direct endpoint for error file analysis via upload
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Validate file type
        allowed_extensions = ['.xlsx', '.xls', '.csv']
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            return jsonify({"error": "Invalid file type. Please upload .xlsx, .xls, or .csv files"}), 400
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        print(f"📊 Analyzing uploaded error file: {file.filename}")
        
        # Process the file
        success = handle_error_file_analysis_direct(temp_file_path)
        
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Error analysis completed - check chatbot for results"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Error analysis failed"
            }), 400
            
    except Exception as e:
        print(f"❌ Error in analyze_error_file endpoint: {str(e)}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

# ===== DEBUG ENDPOINTS =====

@app.route('/debug/latest_response', methods=['GET'])
def debug_latest_response():
    """Debug endpoint to check latest response"""
    global latest_response
    return jsonify({
        "has_response": bool(latest_response),
        "response_length": len(latest_response) if latest_response else 0,
        "response_preview": latest_response[:300] if latest_response else "No response",
        "full_response": latest_response
    })

@app.route('/test_short_response', methods=['POST'])
def test_short_response():
    global latest_response
    latest_response = "🔍 TEST: Short error analysis - 2 duplicate values found in Basic Data sheet."
    print(f"DEBUG: Set short test response: {latest_response}")
    
    # Trigger status change
    try:
        requests.post('http://localhost:5000/update_icon', json={'status': 'error'})
        print("✅ Status updated for test")
    except:
        print("❗ Failed to update status for test")
    
    return jsonify({"message": "Short test response set and status updated"}), 200

# ===== PROXY ENDPOINTS FOR MIGRATION (UNCHANGED) =====

def proxy_to_selenium(path, method='GET'):
    """Enhanced proxy with proper file streaming for large uploads"""
    try:
        url = f"{SELENIUM_SERVICE_URL}/{path}"
        print(f"🔄 Proxying {method} request to: {url}")
        
        headers = {key: value for key, value in request.headers 
                   if key.lower() not in ['host', 'content-length', 'connection', 'content-type']}
        
        if method == 'POST':
            if request.files:
                files = {}
                for key, file_storage in request.files.items():
                    file_storage.seek(0)
                    files[key] = (
                        file_storage.filename,
                        file_storage.stream,
                        file_storage.mimetype
                    )
                
                print(f"📤 Uploading file: {file_storage.filename}")
                response = requests.post(url, files=files, timeout=600)
            else:
                data = request.get_json() if request.is_json else request.get_data()
                if request.is_json:
                    response = requests.post(url, json=data, headers=headers, timeout=120)
                else:
                    response = requests.post(url, data=data, headers=headers, timeout=120)
        else:
            response = requests.get(url, headers=headers, timeout=120)
        
        print(f"✅ Response status: {response.status_code}")
        
        content_type = response.headers.get('content-type', '')
        
        if 'application/json' in content_type:
            return jsonify(response.json()), response.status_code
        elif 'xlsx' in content_type or 'octet-stream' in content_type:
            return Response(
                response.iter_content(chunk_size=8192),
                mimetype=response.headers.get('content-type'),
                headers={'Content-Disposition': response.headers.get('Content-Disposition', '')}
            ), response.status_code
        else:
            return Response(response.content, mimetype=content_type), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error proxying to selenium service: {e}")
        return jsonify({"error": f"Selenium service error: {str(e)}"}), 503

@app.route('/migration/process', methods=['POST'])
def migration_process():
    """Proxy migration file processing to selenium service"""
    print("📤 Received migration process request - proxying to selenium service...")
    return proxy_to_selenium('process_migration', 'POST')

@app.route('/migration/status/<task_id>', methods=['GET'])
def migration_status(task_id):
    """Proxy migration status check to selenium service"""
    print(f"📋 Checking status for task {task_id} - proxying to selenium service...")
    return proxy_to_selenium(f'task_status/{task_id}', 'GET')

@app.route('/migration/result/<task_id>', methods=['GET'])
def migration_result(task_id):
    """Proxy migration result download to selenium service"""
    print(f"📥 Downloading result for task {task_id} - proxying to selenium service...")
    return proxy_to_selenium(f'download_result/{task_id}', 'GET')

@app.route('/migration/health', methods=['GET'])
def migration_health():
    """Check selenium service health"""
    try:
        response = requests.get(f"{SELENIUM_SERVICE_URL}/health", timeout=5)
        return jsonify({
            "selenium_service": "healthy" if response.status_code == 200 else "unhealthy",
            "chatbot_service": "healthy",
            "email_intelligence": "enabled"
        })
    except:
        return jsonify({
            "selenium_service": "unavailable",
            "chatbot_service": "healthy"
        }), 503

if __name__ == "__main__":
    print("🚀 Starting MITRA AI Chatbot + Migration Proxy + Error Analyzer + Email Intelligence + Visual Product Reports...")
    print("📧 Email Intelligence: Integrated with chat endpoint")
    print("📊 Visual Product Reports: Integrated with visual_product_analyzer.py")
    print("📍 Chatbot URL: http://localhost:5000")
    print("💬 Chat: POST /get_response")
    print("📊 Latest Response: GET /get_latest_response")
    print("📤 Migration: POST /migration/process (proxied to selenium service)")
    print("📋 Status: GET /migration/status/<task_id> (proxied)")
    print("📥 Result: GET /migration/result/<task_id> (proxied)")
    print("❤️ Health: GET /migration/health")
    print("🔧 Debug: GET /debug/latest_response")
    app.run(host="0.0.0.0", port=5000, debug=True)

