from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
import os
import time
import tempfile
import shutil
import glob
import logging
import hashlib
import threading
import traceback
import sys
import requests
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Concise logging setup - INFO level only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/selenium.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Set Flask's logger to INFO level
app.logger.setLevel(logging.INFO)

# Set maximum upload size
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# Chatbot service configuration
CHATBOT_SERVICE_URL = "http://localhost:5000"  # Your chatbot service

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    logger.warning("File upload rejected - exceeds 100MB limit")
    return jsonify({
        "error": "File size exceeds maximum allowed limit of 100MB. Please upload a smaller file."
    }), 413

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions with detailed logging"""
    logger.error(f"Unhandled exception: {str(e)}")
    return jsonify({
        "error": "Internal server error",
        "message": str(e),
        "type": type(e).__name__
    }), 500

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 Internal Server Error: {str(error)}")
    return jsonify({
        "error": "Internal server error", 
        "message": "The server encountered an unexpected condition"
    }), 500

# Configuration
PORT = 5001
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {'.xml', '.xlsx', '.xls', '.csv'}

# In-memory storage for processing status
processing_status = {}
processing_lock = threading.Lock()

def send_error_file_to_chatbot(error_file_path: str, task_id: str) -> bool:
    """
    Send error file path to chatbot service for analysis (CORRECTED VERSION)
    """
    try:
        logger.info(f"Sending error file to chatbot for analysis: {task_id}")
        
        # Prepare analysis payload
        analysis_payload = {
            "type": "error_analysis", 
            "file_path": error_file_path,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send analysis request to chatbot - CORRECTED ENDPOINT
        analysis_response = requests.post(
            f"{CHATBOT_SERVICE_URL}/send_to_chatbot",  # ✅ FIXED
            json=analysis_payload,
            timeout=60
        )
        
        if analysis_response.status_code == 200:
            logger.info(f"Successfully initiated error analysis for task: {task_id}")
            return True
        else:
            logger.warning(f"Failed to initiate analysis: {analysis_response.status_code} - {analysis_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error in error analysis workflow: {str(e)}")
        return False

class FileProcessor:
    """Handles file processing with proper validation and cleanup"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix='migration_')
        self.download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        
        # Verify directories are writable
        if not os.access(self.temp_dir, os.W_OK):
            raise Exception(f"Cannot write to temp directory: {self.temp_dir}")
        if not os.access(self.download_dir, os.W_OK):
            raise Exception(f"Cannot write to download directory: {self.download_dir}")
        
        logger.info("FileProcessor initialized successfully")

    def validate_file(self, file):
        """Validate uploaded file"""
        if not file or file.filename == '':
            return False, "No file provided"
        
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in ALLOWED_EXTENSIONS:
            return False, f"File type {file_ext} not allowed. Allowed: {ALLOWED_EXTENSIONS}"
        
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return False, f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        
        if file_size == 0:
            return False, "File is empty"
        
        return True, f"File validated: {file.filename} ({file_size} bytes)"

    def save_uploaded_file(self, file):
        """Securely save uploaded file"""
        try:
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_hash = hashlib.md5(f"{filename}{timestamp}".encode()).hexdigest()[:8]
            secure_name = f"{timestamp}_{file_hash}_{filename}"
            file_path = os.path.join(self.temp_dir, secure_name)
            
            file.save(file_path)
            
            if not os.path.exists(file_path):
                raise Exception("File save failed")
            
            return file_path, secure_name
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise Exception(f"Failed to save file: {e}")

    def wait_for_upload_completion(self, driver, waitUpload, waitUploaddots):
        """Wait for file upload to complete by monitoring upload indicators"""
        upload_timeout = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < upload_timeout:
            try:
                upload_element = driver.find_element(By.XPATH, waitUpload)
                upload_text = upload_element.text.strip().lower()
                
                if any(keyword in upload_text for keyword in ['complete', 'uploaded', 'finished', '100%', 'done']):
                    logger.info("File upload completed successfully")
                    return True
            except NoSuchElementException:
                try:
                    driver.find_element(By.XPATH, waitUploaddots)
                except NoSuchElementException:
                    logger.info("Upload indicators disappeared - upload complete")
                    return True
            except Exception:
                pass
            
            time.sleep(2)
        
        logger.warning("Upload timeout reached - proceeding anyway")
        return False

    def click_show_message(self, driver):
        """Click Show Messages using the working parent element method"""
        try:
            element_id = "application-DataMigration-manage-component---StagingTableList--ObjectStatus2-application-DataMigration-manage-component---StagingTableList--UploadCollection-0-text"
            parent_element = driver.find_element(By.ID, element_id).find_element(By.XPATH, "./..")
            parent_element.click()
            time.sleep(3)
            return True
        except Exception as e:
            logger.error(f"Failed to click Show Messages: {e}")
            return False

    def headless_file_upload(self, driver, file_path, upload_selectors):
        """Headless-compatible file upload methods"""
        upload_success = False
        
        # Method 1: Direct send_keys to file input
        for selector in upload_selectors:
            try:
                file_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                file_input.send_keys(file_path)
                time.sleep(3)
                logger.info("File uploaded via send_keys method")
                upload_success = True
                break
            except Exception:
                continue
        
        # Method 2: JavaScript-based file upload
        if not upload_success:
            try:
                file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
                if file_inputs:
                    import base64
                    with open(file_path, 'rb') as f:
                        file_data = base64.b64encode(f.read()).decode()
                    
                    js_script = f"""
                    var input = arguments[0];
                    var fileName = '{os.path.basename(file_path)}';
                    var fileData = '{file_data}';
                    
                    var byteCharacters = atob(fileData);
                    var byteNumbers = new Array(byteCharacters.length);
                    for (var i = 0; i < byteCharacters.length; i++) {{
                        byteNumbers[i] = byteCharacters.charCodeAt(i);
                    }}
                    var byteArray = new Uint8Array(byteNumbers);
                    var file = new File([byteArray], fileName);
                    
                    var dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    input.files = dataTransfer.files;
                    
                    var event = new Event('change', {{ bubbles: true }});
                    input.dispatchEvent(event);
                    """
                    
                    driver.execute_script(js_script, file_inputs[0])
                    time.sleep(3)
                    logger.info("File uploaded via JavaScript method")
                    upload_success = True
            except Exception as e:
                logger.error(f"JavaScript upload method failed: {e}")
        
        return upload_success

    def process_migration_file(self, file_path, task_id):
        """Enhanced process with proper post-login handling and headless support + Error Analysis Integration"""
        driver = None
        try:
            logger.info(f"Starting processing for task: {task_id}")
            
            # Update status
            with processing_lock:
                processing_status[task_id]["status"] = "processing"
                processing_status[task_id]["message"] = "Starting Selenium automation..."

            # Import credentials
            try:
                from _selenium.credentials import niktestUN, niktestPW
                from _selenium.dataMigrationKeyFieldsXPATH import (
                    url, username, password, _continue, upload, validationStatus, 
                    showMessage, print as print_btn, waitUpload, waitUploaddots
                )
            except ImportError as e:
                logger.error(f"Failed to import credentials: {e}")
                raise Exception(f"Import error: {e}")

            # Verify file exists
            if not os.path.exists(file_path):
                raise Exception(f"File not found: {file_path}")

            # Verify EdgeDriver exists
            edge_driver_path = r"C:\Users\prath\OneDrive\Project Codes\selenium - edge\msedgedriver.exe"
            if not os.path.exists(edge_driver_path):
                raise Exception(f"EdgeDriver not found at: {edge_driver_path}")

            # Setup WebDriver
            logger.info("Setting up headless WebDriver")
            service = Service(edge_driver_path)
            options = Options()
            
            # Headless configuration
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            # Set download directory
            prefs = {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            options.add_experimental_option("prefs", prefs)
            
            driver = webdriver.Edge(service=service, options=options)
            wait = WebDriverWait(driver, 30)

            # Step 1: Navigate and login
            logger.info("Navigating to website and logging in")
            with processing_lock:
                processing_status[task_id]["message"] = "Logging in..."
            
            driver.get(url)
            wait.until(EC.presence_of_element_located((By.XPATH, username))).send_keys(niktestUN)
            wait.until(EC.presence_of_element_located((By.XPATH, password))).send_keys(niktestPW)
            wait.until(EC.element_to_be_clickable((By.XPATH, _continue))).click()
            
            # Wait for login completion
            time.sleep(10)

            # Step 2: File upload
            logger.info("Starting file upload")
            with processing_lock:
                processing_status[task_id]["message"] = "Uploading file..."
            
            time.sleep(5)

            # Try to navigate to migration page if needed
            if "migration" not in driver.current_url.lower():
                migration_links = [
                    "//a[contains(text(), 'Migration')]",
                    "//a[contains(text(), 'Upload')]",
                    "//a[contains(text(), 'Data Migration')]"
                ]
                for link_xpath in migration_links:
                    try:
                        migration_link = driver.find_element(By.XPATH, link_xpath)
                        migration_link.click()
                        time.sleep(3)
                        break
                    except NoSuchElementException:
                        continue

            # Upload file
            file_input_selectors = [
                "//input[@type='file']",
                "//input[contains(@class, 'file')]",
                upload
            ]
            
            upload_success = self.headless_file_upload(driver, file_path, file_input_selectors)

            if not upload_success:
                raise Exception("All upload methods failed")

            # Step 3: Wait for upload and validation
            logger.info("Waiting for upload completion and validation")
            with processing_lock:
                processing_status[task_id]["message"] = "Validating file..."
            
            self.wait_for_upload_completion(driver, waitUpload, waitUploaddots)
            time.sleep(5)

            # Check validation status
            validation_complete = False
            for i in range(60):
                try:
                    status_elem = wait.until(EC.presence_of_element_located((By.XPATH, validationStatus)))
                    status_text = status_elem.text.strip().lower()
                    
                    if any(keyword in status_text for keyword in ['success', 'failed', 'complete']):
                        validation_complete = True
                        break
                except Exception:
                    pass
                time.sleep(1)

            # Handle validation result
            try:
                status_elem = driver.find_element(By.XPATH, validationStatus)
                status_text = status_elem.text.strip().lower()

                if 'failed' in status_text or 'error' in status_text:
                    logger.warning(f"Validation failed for task {task_id}")
                    with processing_lock:
                        processing_status[task_id]["message"] = "Downloading error report..."
                    
                    if self.click_show_message(driver):
                        try:
                            wait.until(EC.element_to_be_clickable((By.XPATH, print_btn))).click()
                            time.sleep(10)
                            
                            # Get latest downloaded file
                            list_of_files = glob.glob(os.path.join(self.download_dir, '*'))
                            if list_of_files:
                                latest_file = max(list_of_files, key=os.path.getctime)
                                result_filename = f"error_report_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                                result_path = os.path.join(self.temp_dir, result_filename)
                                shutil.copy2(latest_file, result_path)
                                
                                # ===== NEW: SEND ERROR FILE TO CHATBOT FOR ANALYSIS =====
                                logger.info(f"Sending error file to chatbot for analysis: {task_id}")
                                with processing_lock:
                                    processing_status[task_id]["message"] = "Analyzing errors with AI..."
                                
                                # Send error file to chatbot service for analysis
                                analysis_sent = send_error_file_to_chatbot(result_path, task_id)
                                
                                if analysis_sent:
                                    logger.info(f"Error analysis initiated for task: {task_id}")
                                    analysis_message = "Error analysis completed - check chatbot for detailed insights"
                                else:
                                    logger.warning(f"Failed to send error file for analysis: {task_id}")
                                    analysis_message = "Error report ready for download (analysis service unavailable)"
                                
                                with processing_lock:
                                    processing_status[task_id]["status"] = "failed"
                                    processing_status[task_id]["result_file"] = result_path
                                    processing_status[task_id]["message"] = analysis_message
                                    processing_status[task_id]["analysis_sent"] = analysis_sent
                                
                                logger.info(f"Error report generated and analyzed for task {task_id}")
                                return {
                                    "status": "failed", 
                                    "result_file": result_path,
                                    "analysis_sent": analysis_sent,
                                    "message": analysis_message
                                }
                            else:
                                return {"status": "failed", "message": "No error report downloaded"}
                        except Exception as e:
                            logger.error(f"Could not download error report: {e}")
                            return {"status": "failed", "message": f"Validation failed: {e}"}
                    else:
                        return {"status": "failed", "message": "Could not access error details"}
                else:
                    logger.info(f"Validation successful for task {task_id}")
                    with processing_lock:
                        processing_status[task_id]["status"] = "success"
                        processing_status[task_id]["message"] = "File validation completed successfully"
                    return {"status": "success", "message": "File validation completed successfully"}

            except Exception as e:
                logger.error(f"Validation check failed for task {task_id}: {e}")
                return {"status": "error", "message": f"Validation check failed: {e}"}

        except Exception as e:
            logger.error(f"Processing failed for task {task_id}: {str(e)}")
            with processing_lock:
                processing_status[task_id]["status"] = "error"
                processing_status[task_id]["message"] = str(e)
            return {"status": "error", "message": str(e)}
        
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    logger.error(f"Error closing WebDriver: {e}")

    def cleanup(self):
        """Clean up temporary files"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# Global file processor instance
file_processor = FileProcessor()

@app.route('/', methods=['GET'])
def home():
    """Service info endpoint"""
    return jsonify({
        "service": "Enhanced Migration Automation Service (Headless) + AI Error Analysis",
        "version": "4.1.0",
        "port": PORT,
        "status": "running",
        "mode": "headless",
        "features": ["automated_migration", "error_analysis", "ai_integration"],
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health (GET)",
            "process_migration": "/process_migration (POST)",
            "task_status": "/task_status/<task_id> (GET)",
            "download_result": "/download_result/<task_id> (GET)"
        },
        "limits": {
            "max_file_size_mb": MAX_FILE_SIZE // (1024*1024),
            "allowed_extensions": list(ALLOWED_EXTENSIONS)
        },
        "integrations": {
            "chatbot_service": CHATBOT_SERVICE_URL,
            "error_analysis": "enabled"
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    # Check chatbot service health
    chatbot_status = "unknown"
    try:
        response = requests.get(f"{CHATBOT_SERVICE_URL}/migration/health", timeout=5)
        chatbot_status = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        chatbot_status = "unavailable"
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Enhanced Migration Automation Service (Headless) + AI Error Analysis",
        "port": PORT,
        "active_tasks": len(processing_status),
        "integrations": {
            "chatbot_service": chatbot_status,
            "error_analysis": "enabled"
        }
    })

@app.route('/process_migration', methods=['POST'])
def process_migration():
    """Main API endpoint to process migration files"""
    try:
        if 'file' not in request.files:
            logger.warning("File upload request with no file")
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        
        # Validate file
        is_valid, message = file_processor.validate_file(file)
        if not is_valid:
            logger.warning(f"File validation failed: {message}")
            return jsonify({"error": message}), 400

        logger.info(f"Processing file: {file.filename}")

        # Generate task ID
        task_id = hashlib.md5(f"{file.filename}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # Initialize task status
        with processing_lock:
            processing_status[task_id] = {
                "status": "uploading",
                "message": "Receiving file...",
                "created_at": datetime.now().isoformat(),
                "filename": file.filename,
                "analysis_sent": False
            }

        # Save uploaded file
        try:
            file_path, secure_name = file_processor.save_uploaded_file(file)
            
            with processing_lock:
                processing_status[task_id]["status"] = "uploaded"
                processing_status[task_id]["message"] = "File uploaded successfully, starting processing..."
                processing_status[task_id]["file_path"] = file_path

            # Start processing in background thread
            def process_in_background():
                try:
                    file_processor.process_migration_file(file_path, task_id)
                except Exception as e:
                    logger.error(f"Background processing error for task {task_id}: {str(e)}")
                    with processing_lock:
                        processing_status[task_id]["status"] = "error"
                        processing_status[task_id]["message"] = f"Processing error: {str(e)}"

            thread = threading.Thread(target=process_in_background)
            thread.daemon = True
            thread.start()

            logger.info(f"Task {task_id} started for file: {secure_name}")
            
            return jsonify({
                "task_id": task_id,
                "status": "accepted",
                "message": "File received and processing started in headless mode with AI error analysis",
                "filename": secure_name,
                "check_status_url": f"/task_status/{task_id}",
                "features": ["automated_processing", "error_analysis", "ai_insights"]
            }), 202

        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            with processing_lock:
                processing_status[task_id]["status"] = "error"
                processing_status[task_id]["message"] = str(e)
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({"error": f"API error: {str(e)}"}), 500

@app.route('/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get status of processing task"""
    try:
        with processing_lock:
            if task_id not in processing_status:
                return jsonify({"error": "Task not found"}), 404
            
            task = processing_status[task_id].copy()
            
        # Add download URL if result file is ready
        if task["status"] == "failed" and "result_file" in task:
            task["download_url"] = f"/download_result/{task_id}"
            
        # Add analysis status
        if task.get("analysis_sent"):
            task["ai_analysis"] = "Analysis sent to chatbot - check chatbot for insights"
        
        return jsonify(task)
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/download_result/<task_id>', methods=['GET'])
def download_result(task_id):
    """Download result file for completed task"""
    try:
        with processing_lock:
            if task_id not in processing_status:
                return jsonify({"error": "Task not found"}), 404
            
            task = processing_status[task_id]
            
            if task["status"] != "failed" or "result_file" not in task:
                return jsonify({"error": "No result file available"}), 404
            
            result_file = task["result_file"]
        
        if not os.path.exists(result_file):
            return jsonify({"error": "Result file not found"}), 404
        
        logger.info(f"Downloading error report for task: {task_id}")
        
        # Create response with proper headers
        response = send_file(
            result_file,
            as_attachment=True,
            download_name=f"error_report_{task_id}.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Add CORS headers
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Content-Disposition'] = f'attachment; filename="error_report_{task_id}.xlsx"'
        
        return response
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/cleanup/<task_id>', methods=['DELETE'])
def cleanup_task(task_id):
    """Clean up completed task"""
    try:
        with processing_lock:
            if task_id in processing_status:
                task = processing_status.pop(task_id)
                
                # Clean up files
                if "file_path" in task and os.path.exists(task["file_path"]):
                    os.remove(task["file_path"])
                if "result_file" in task and os.path.exists(task["result_file"]):
                    os.remove(task["result_file"])
        
        return jsonify({"message": "Task cleaned up successfully"})
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Starting Enhanced Migration Automation Service + AI Error Analysis on port {PORT}")
    logger.info("Mode: Fully Headless - No GUI interactions")
    logger.info(f"Chatbot Integration: {CHATBOT_SERVICE_URL}")
    logger.info("Features: Automated Processing + AI Error Analysis")
    
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
    except KeyboardInterrupt:
        logger.info("Service shutting down...")
        file_processor.cleanup()
    except Exception as e:
        logger.error(f"Service error: {e}")
        file_processor.cleanup()
