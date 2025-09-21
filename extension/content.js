// 🔧 URL CONFIGURATION - CORRECTED
const OPENAI_CHAT_URL = "https://7b227064897c.ngrok-free.app/";        // Chatbot via ngrok (port 5000)
const MIGRATION_SERVICE_URL = "http://localhost:5001";                  // Selenium service LOCAL (port 5001)

function scrollToBottom() {
    const chatBody = document.querySelector(".chat-body");
    if (chatBody) {
        setTimeout(() => {
            chatBody.scrollTop = chatBody.scrollHeight;
            console.log('📍 Scrolled to bottom');
        }, 50);
    }
}

// ===== NEW: Lightbox function for viewing images full-screen =====
function showLightbox(src) {
    // Remove existing lightbox if any to prevent duplicates
    const existingLightbox = document.getElementById('image-lightbox-overlay');
    if (existingLightbox) {
        existingLightbox.remove();
    }

    const lightbox = document.createElement('div');
    lightbox.id = 'image-lightbox-overlay';
    lightbox.classList.add('lightbox-overlay');
    lightbox.innerHTML = `
        <span class="lightbox-close">&times;</span>
        <img src="${src}" class="lightbox-content" alt="Expanded Visualization">
    `;

    document.body.appendChild(lightbox);
    
    // Animate opacity for a smooth fade-in effect
    setTimeout(() => {
        lightbox.style.opacity = '1';
    }, 10);

    const close = () => {
        lightbox.style.opacity = '0';
        setTimeout(() => {
            if (lightbox.parentNode) {
                lightbox.remove();
            }
        }, 300); // This duration should match the CSS transition duration
    };

    // Add event listeners to close the lightbox
    lightbox.querySelector('.lightbox-close').addEventListener('click', close);
    lightbox.addEventListener('click', (e) => {
        // Only close if the dark background overlay is clicked, not the image itself
        if (e.target === lightbox) { 
            close();
        }
    });
}


// Start polling
setInterval(checkValidationStatus, 3000);

if (!window.chatbotInjected) {
    window.chatbotInjected = true;

    // The conflicting setupLightbox function has been removed to fix the issue.
    
    let chatIcon = document.createElement("div");
    chatIcon.id = "chatbot-icon";
    chatIcon.innerHTML = `<img src="${chrome.runtime.getURL("icon.png")}" alt="Chat Icon">`;

    let chatFrame = document.createElement("div");
    chatFrame.id = "chatbox";
    chatFrame.style.display = "none";
    chatFrame.innerHTML = `
        <div class="chat-body"></div>
        <div class="file-preview-container" id="file-preview" style="display: none;"></div>
        <div class="chat-input-container">
            <div class="input-wrapper">
                <button id="attach-btn" class="attach-button" title="Attach File">📎</button>
                <textarea id="chat-input" placeholder="Ask anything..."></textarea>
                <button id="send-btn">⌯⌲</button>
            </div>
            <input type="file" id="file-input" accept=".xml,.xlsx,.xls,.csv" style="display: none;">
        </div>
    `;

    document.body.appendChild(chatIcon);
    document.body.appendChild(chatFrame);

    // File upload state management
    let attachedFile = null;
    let isProcessingFile = false;

    function toggleChatbox() {
        if (chatFrame.style.display === "none") {
            chatFrame.style.display = "block";
            adjustIconPosition();
        } else {
            chatFrame.style.display = "none";
        }
    }

    function adjustIconPosition() {
        let chatRect = chatFrame.getBoundingClientRect();
        let iconRect = chatIcon.getBoundingClientRect();

        let overlap =
            iconRect.right > chatRect.left &&
            iconRect.left < chatRect.right &&
            iconRect.bottom > chatRect.top &&
            iconRect.top < chatRect.bottom;

        if (overlap) {
            let newLeft = chatRect.left - iconRect.width - 10;
            if (newLeft < 10) newLeft = 10;
            chatIcon.style.left = newLeft + "px";
            chatIcon.style.top = chatRect.top + "px";
        }
    }

    function makeDraggable(element) {
        let offsetX = 0, offsetY = 0, mouseX = 0, mouseY = 0;
        let isDragging = false;

        element.onmousedown = function (event) {
            event.preventDefault();
            isDragging = false;
            mouseX = event.clientX;
            mouseY = event.clientY;

            document.onmousemove = function (e) {
                e.preventDefault();
                isDragging = true;
                offsetX = mouseX - e.clientX;
                offsetY = mouseY - e.clientY;
                mouseX = e.clientX;
                mouseY = e.clientY;
                element.style.top = (element.offsetTop - offsetY) + "px";
                element.style.left = (element.offsetLeft - offsetX) + "px";
            };

            document.onmouseup = function () {
                document.onmousemove = null;
                document.onmouseup = null;
                if (isDragging) adjustIconPosition();
            };
        };

        element.onclick = function (event) {
            if (!isDragging) toggleChatbox();
        };
    }

    makeDraggable(chatIcon);

    // ===== UPDATED: Enhanced message function to support visual reports =====
    function addMessage(text, sender, fileInfo = null, taskId = null, reportData = null) {
        console.log('🔍 Adding message:', {
            textPreview: text?.substring(0, 50) + '...',
            sender: sender,
            hasReport: !!reportData
        });

        let chatBody = document.querySelector(".chat-body");
        if (!chatBody) {
            console.error('❌ Chat body not found!');
            return;
        }

        let msgDiv = document.createElement("div");
        msgDiv.classList.add("chat-message", sender);

        // Add file info for user uploads
        if (fileInfo) {
            let fileDiv = document.createElement("div");
            fileDiv.classList.add("file-attachment");
            fileDiv.innerHTML = `
                <div class="file-info">
                    <span class="file-icon">${getFileIcon(fileInfo.name)}</span>
                    <div class="file-details">
                        <div class="file-name">${fileInfo.name}</div>
                        <div class="file-size">${formatFileSize(fileInfo.size)}</div>
                        ${taskId ? `<div class="task-id">Task ID: ${taskId}</div>` : ''}
                    </div>
                </div>
            `;
            msgDiv.appendChild(fileDiv);
        }

        let messageText = text;

        // If it's a visual report from the AI, remove the raw links from the main text
        if (sender === 'ai' && reportData && reportData.visualization_urls) {
            const vizHeader = "📊 **Generated Visualizations:**";
            const headerIndex = messageText.indexOf(vizHeader);
            if (headerIndex !== -1) {
                messageText = messageText.substring(0, headerIndex).trim();
            }
        }

        // Add the main text content, with formatting
        if (messageText) {
            let textDiv = document.createElement("div");
            textDiv.classList.add("message-text");
            // Basic markdown for bold text and preserve newlines
            let formattedText = messageText
                .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
                .replace(/\n/g, '<br>');
            textDiv.innerHTML = formattedText;
            msgDiv.appendChild(textDiv);
        }

        // Add the visualization images if they exist in the report data
        if (sender === 'ai' && reportData && reportData.visualization_urls) {
            const vizContainer = document.createElement("div");
            vizContainer.classList.add("visualization-container");
            
            const vizTitle = document.createElement('b');
            vizTitle.innerText = "📊 Generated Visualizations:";
            vizContainer.appendChild(vizTitle);

            Object.entries(reportData.visualization_urls).forEach(([key, url]) => {
                const img = document.createElement("img");
                // Construct the full absolute URL for the image
                img.src = new URL(url, OPENAI_CHAT_URL).href;
                img.alt = `Visualization: ${key}`;
                img.classList.add("viz-image");
                // Add the click event listener to open the lightbox
                img.addEventListener('click', () => showLightbox(img.src));
                vizContainer.appendChild(img);
            });
            msgDiv.appendChild(vizContainer);
        }

        chatBody.appendChild(msgDiv);
        scrollToBottom();

        return msgDiv;
    }


    // Add processing status message
    function addProcessingMessage(taskId) {
        let chatBody = document.querySelector(".chat-body");
        let msgDiv = document.createElement("div");
        msgDiv.classList.add("chat-message", "ai", "processing");
        msgDiv.id = `processing-${taskId}`;
        msgDiv.innerHTML = `
            <div class="processing-indicator">
                <div class="spinner"></div>
                <div class="processing-text">Processing your file...</div>
                <div class="task-status">Task ID: ${taskId}</div>
            </div>
        `;
        
        chatBody.appendChild(msgDiv);
        scrollToBottom();
        
        return msgDiv;
    }

    // Enhanced update processing message with download functionality
    function updateProcessingMessage(taskId, result) {
        let processingMsg = document.getElementById(`processing-${taskId}`);
        if (!processingMsg) return;

        processingMsg.classList.remove("processing");
        
        if (result.status === "success") {
            processingMsg.innerHTML = `
                <div class="result-success">
                    <div class="result-icon">✅</div>
                    <div class="result-content">
                        <div class="result-text">Success!</div>
                        <div class="result-message">${result.message}</div>
                    </div>
                </div>
            `;
        } else if (result.status === "failed") {
            processingMsg.innerHTML = `
                <div class="result-error">
                    <div class="result-icon">❌</div>
                    <div class="result-content">
                        <div class="result-text">Processing failed</div>
                        <div class="result-message">${result.message || 'File validation failed'}</div>
                        ${result.download_url ? `
                            <div class="download-section">
                                <button class="download-error-btn" data-task-id="${taskId}">
                                    📥 Download Error Report
                                </button>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
            
            // Add proper event listener instead of onclick attribute
            if (result.download_url) {
                setTimeout(() => {
                    const downloadBtn = processingMsg.querySelector(`[data-task-id="${taskId}"]`);
                    if (downloadBtn) {
                        downloadBtn.addEventListener('click', function(e) {
                            e.preventDefault();
                            console.log('Download button clicked for task:', taskId);
                            downloadErrorReport(taskId, result.download_url);
                        });
                    }
                }, 100);
            }
        } else {
            processingMsg.innerHTML = `
                <div class="result-error">
                    <div class="result-icon">⚠️</div>
                    <div class="result-content">
                        <div class="result-text">Error</div>
                        <div class="result-message">${result.message}</div>
                    </div>
                </div>
            `;
        }
        
        scrollToBottom();
    }

    window.testDownload = function() {
        console.log('Testing download functionality...');
        
        // Create a test blob
        const testContent = 'This is a test file for download functionality.';
        const blob = new Blob([testContent], { type: 'text/plain' });
        
        downloadBlobFile(blob, 'test-download.txt')
            .then(() => {
                console.log('Test download successful!');
                addMessage("✅ Test download worked!", "ai");
            })
            .catch((error) => {
                console.error('Test download failed:', error);
                addMessage(`❌ Test download failed: ${error.message}`, "ai");
            });
    };
    // Download error report function
    window.downloadErrorReport = async function(taskId, downloadUrl) {
        try {
            console.log(`Starting download for task: ${taskId}`);
            console.log(`Download URL: ${MIGRATION_SERVICE_URL}${downloadUrl}`);
            
            // Show downloading indicator
            const downloadBtn = document.querySelector(`[data-task-id="${taskId}"]`);
            if (downloadBtn) {
                downloadBtn.innerHTML = '⏳ Downloading...';
                downloadBtn.disabled = true;
            }
            
            // Fetch the file
            const response = await fetch(`${MIGRATION_SERVICE_URL}${downloadUrl}`, {
                method: 'GET',
                mode: 'cors'
            });
            
            console.log('Download response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`Download failed: ${response.status} ${response.statusText}`);
            }
            
            // Get the blob
            const blob = await response.blob();
            console.log('Blob size:', blob.size, 'Blob type:', blob.type);
            
            if (blob.size === 0) {
                throw new Error('Downloaded file is empty');
            }
            
            // Create download
            const timestamp = new Date().getTime();
            const filename = `error_report_${taskId}_${timestamp}.xlsx`;
            
            // Use the reliable download method
            await downloadBlobFile(blob, filename);
            
            // Update button state
            if (downloadBtn) {
                downloadBtn.innerHTML = '✅ Downloaded';
                downloadBtn.style.backgroundColor = '#28a745';
                downloadBtn.disabled = false;
            }
            
            // Show success message
            addMessage("✅ Error report downloaded successfully!", "ai");
            
        } catch (error) {
            console.error('Download error:', error);
            
            // Reset button state
            const downloadBtn = document.querySelector(`[data-task-id="${taskId}"]`);
            if (downloadBtn) {
                downloadBtn.innerHTML = '❌ Download Failed - Retry';
                downloadBtn.disabled = false;
                downloadBtn.style.backgroundColor = '#dc3545';
            }
            
            addMessage(`❌ Download failed: ${error.message}`, "ai");
        }
    };

    async function downloadBlobFile(blob, filename) {
        return new Promise((resolve, reject) => {
            try {
                // Create blob URL
                const url = URL.createObjectURL(blob);
                
                // Create anchor element
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;
                
                // Add to DOM temporarily
                document.body.appendChild(a);
                
                // Trigger download with multiple methods for better compatibility
                setTimeout(() => {
                    try {
                        // Method 1: Direct click
                        a.click();
                        
                        // Method 2: Dispatch event (fallback)
                        if (!a.click) {
                            const event = new MouseEvent('click', {
                                view: window,
                                bubbles: true,
                                cancelable: true
                            });
                            a.dispatchEvent(event);
                        }
                        
                        // Cleanup
                        setTimeout(() => {
                            document.body.removeChild(a);
                            URL.revokeObjectURL(url);
                            resolve();
                        }, 100);
                        
                    } catch (err) {
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                        reject(err);
                    }
                }, 10);
                
            } catch (error) {
                reject(error);
            }
        });
    }

// Standard download method
function downloadUsingStandardMethod(blob, filename) {
    try {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        
        document.body.appendChild(a);
        a.click();
        
        // Cleanup with delay for browser compatibility
        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 100);
        
        return true;
    } catch (error) {
        console.error('Standard download method failed:', error);
        return false;
    }
}


// Fallback download method using dispatchEvent
function downloadUsingDispatchEvent(blob, filename) {
    try {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        
        // Use dispatchEvent for better browser compatibility
        document.body.appendChild(a);
        a.dispatchEvent(new MouseEvent('click', {
            bubbles: true,
            cancelable: true,
            view: window
        }));
        
        // Cleanup
        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 100);
        
    } catch (error) {
        console.error('Dispatch event download method failed:', error);
        throw error;
    }
}


    function getFileIcon(fileName) {
        let ext = fileName.split('.').pop().toLowerCase();
        switch (ext) {
            case 'xml': return '📄';
            case 'xlsx': case 'xls': return '📊';
            case 'csv': return '📈';
            default: return '📎';
        }
    }


    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        let k = 1024;
        let sizes = ['Bytes', 'KB', 'MB', 'GB'];
        let i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }


    function showFilePreview(file) {
        let previewContainer = document.getElementById("file-preview");
        previewContainer.style.display = "flex";
        previewContainer.innerHTML = `
            <div class="file-preview-item">
                <span class="file-icon">${getFileIcon(file.name)}</span>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
                <button class="remove-file-btn" id="remove-file-btn">✕</button>
            </div>
        `;
        
        // Add event listener to the remove button after creating it
        const removeBtn = document.getElementById("remove-file-btn");
        if (removeBtn) {
            removeBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                removeAttachedFile();
            });
        }
    }


    function hideFilePreview() {
        let previewContainer = document.getElementById("file-preview");
        previewContainer.style.display = "none";
        previewContainer.innerHTML = "";
    }


    function removeAttachedFile() {
        console.log("Removing attached file...");
        attachedFile = null;
        hideFilePreview();
        document.getElementById("file-input").value = "";
        addMessage("File received and sent to further processing.", "ai");
    }


    // File handling
    let attachBtn = document.getElementById("attach-btn");
    let fileInput = document.getElementById("file-input");


    attachBtn.addEventListener('click', function(e) {
        e.preventDefault();
        fileInput.click();
    });


    fileInput.addEventListener("change", function(e) {
        let file = e.target.files[0];
        if (file) {
            // Validate file type
            let allowedTypes = ['.xml', '.xlsx', '.xls', '.csv'];
            let fileExt = '.' + file.name.split('.').pop().toLowerCase();
            
            if (!allowedTypes.includes(fileExt)) {
                addMessage(`❌ File type not supported. Allowed types: ${allowedTypes.join(', ')}`, "ai");
                return;
            }


            // Validate file size (100MB limit)
            if (file.size > 100 * 1024 * 1024) {
                addMessage("❌ File too large. Maximum size: 100MB", "ai");
                return;
            }


            attachedFile = file;
            showFilePreview(file);
            addMessage("📎 File attached. You can now add a message and send.", "ai");
        }
    });


    // Enhanced send message function
    async function sendMessage() {
        let userMessage = chatInput.value.trim();
        
        if (!userMessage && !attachedFile) {
            addMessage("Please enter a message or attach a file.", "ai");
            return;
        }


        if (isProcessingFile) {
            addMessage("Please wait for the current file to finish processing.", "ai");
            return;
        }


        // Display user message with file if attached
        if (attachedFile) {
            addMessage(userMessage || "File uploaded for processing", "user", {
                name: attachedFile.name,
                size: attachedFile.size
            });
        } else {
            addMessage(userMessage, "user");
        }


        // Clear input
        chatInput.value = "";
        chatInput.style.height = "30px";


        try {
            if (attachedFile) {
                // Handle file processing
                isProcessingFile = true;
                await handleFileProcessing(attachedFile, userMessage);
                
                // Clear attached file after processing
                removeAttachedFile();
                isProcessingFile = false;
            } else {
                // Regular chat message
                handleRegularChat(userMessage);
            }
        } catch (error) {
            addMessage(`❌ Error: ${error.message}`, "ai");
            isProcessingFile = false;
        }
    }


    async function handleFileProcessing(file, message) {
        try {
            console.log('Starting file processing...');
            console.log('Sending to selenium service at:', MIGRATION_SERVICE_URL);
            
            let formData = new FormData();
            formData.append('file', file);


            // Submit file for processing to localhost:5001
            let response = await fetch(`${MIGRATION_SERVICE_URL}/process_migration`, {
                method: "POST",
                body: formData,
                mode: 'cors'
            });


            console.log('Response status:', response.status);
            console.log('Response headers:', [...response.headers.entries()]);


            if (!response.ok) {
                const errorText = await response.text();
                console.error('Server error response:', errorText);
                throw new Error(`Server error: ${response.status} - ${errorText}`);
            }


            let result = await response.json();
            console.log('Processing result:', result);
            
            if (result.task_id) {
                // Show processing indicator
                let processingMsg = addProcessingMessage(result.task_id);
                
                // Start polling for results
                let finalResult = await pollForResults(result.task_id);
                updateProcessingMessage(result.task_id, finalResult);
            } else {
                throw new Error("No task ID received from server");
            }


        } catch (error) {
            console.error("File processing error:", error);
            addMessage(`❌ File processing error: ${error.message}`, "ai");
        }
    }


    async function pollForResults(taskId, maxAttempts = 120) {
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            try {
                console.log(`Polling attempt ${attempt + 1} for task ${taskId}`);
                
                // Poll localhost:5001 for status
                let response = await fetch(`${MIGRATION_SERVICE_URL}/task_status/${taskId}`, {
                    mode: 'cors'
                });
                
                if (!response.ok) {
                    console.error(`Polling failed: ${response.statusText}`);
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    continue;
                }
                
                let result = await response.json();
                console.log(`Task ${taskId} status:`, result);
                
                // Check if processing is complete
                if (result.status === "success") {
                    return {
                        status: "success",
                        message: result.message || "File validation completed successfully"
                    };
                } else if (result.status === "failed") {
                    // ✅ ADD THIS: Fetch AI analysis when processing fails
                    console.log("🔍 Processing failed - fetching AI analysis...");
                    
                    // Wait a moment for analysis to complete
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    // Fetch AI analysis from chatbot service
                    try {
                        let analysisResponse = await fetch(`${OPENAI_CHAT_URL}/get_latest_response`, {
                            headers: { "ngrok-skip-browser-warning": "true" }  // ✅ FIXED: Skip ngrok warning
                        });
                        if (analysisResponse.ok) {
                            let analysisData = await analysisResponse.json();
                            if (analysisData.response && 
                                analysisData.response !== "No AI response available" &&
                                analysisData.response.length > 100) { // Check if it's a real analysis
                                
                                console.log("✅ Found AI analysis, displaying in chat");
                                // Display the AI analysis as a chat message
                                addMessage(analysisData.response, "ai");
                            }
                        }
                    } catch (error) {
                        console.log("⚠️ Could not fetch AI analysis:", error);
                    }
                    
                    return {
                        status: "failed",
                        message: result.message || "File validation failed",
                        download_url: result.download_url || null
                    };
                } else if (result.status === "error") {
                    return {
                        status: "error",
                        message: result.message || "Processing error occurred"
                    };
                } else {
                    // Still processing, wait and continue
                    await new Promise(resolve => setTimeout(resolve, 5000));
                }
                
            } catch (error) {
                console.error("Polling error:", error);
                await new Promise(resolve => setTimeout(resolve, 5000));
            }
        }
        
        return { 
            status: "timeout", 
            message: "Processing timed out after 10 minutes" 
        };
    }

    // ===== UPDATED: Handles both regular chat and visual reports =====
    async function handleRegularChat(message) {
        try {
            let response = await fetch(`${OPENAI_CHAT_URL}/get_response`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: message }),
            });

            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }

            let data = await response.json();
            // The `addMessage` function will now handle the `report_data` field if it exists
            addMessage(data.response, "ai", null, null, data.report_data);
        } catch (error) {
            console.error("Error fetching AI response:", error);
            addMessage(`Error: Unable to get AI response. ${error.message}`, "ai");
        }
    }


    // Event listeners
    let chatInput = document.getElementById("chat-input");
    let sendBtn = document.getElementById("send-btn");


    sendBtn.onclick = sendMessage;
    chatInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });


    chatInput.addEventListener("input", function () {
        this.style.height = "30px";
        this.style.height = Math.min(this.scrollHeight, 100) + "px";
    });


    // Existing validation status checking
    let previousStatus = "success";


    function checkValidationStatus() {
            fetch(`${OPENAI_CHAT_URL}/get_status`, {
                headers: { "ngrok-skip-browser-warning": "true" }  // ✅ FIXED: Skip ngrok warning
            })
                .then(response => response.json())
                .then(data => {
                    console.log('Status check:', data.status, 'Previous:', previousStatus);
                    
                    const chatIcon = document.getElementById("chatbot-icon");
                    if (data.status === "error") {
                        // Always fetch response when status is error, regardless of previous state
                        if (previousStatus === "success") {
                            console.log("🚨 Status changed to error - fetching AI response");
                            fetchAIResponse();
                        } else {
                            // Check if there's a new response even if status was already error
                            console.log("🔄 Status still error - checking for new response");
                            fetchAIResponseIfNew();
                        }
                        
                        chatIcon.style.borderColor = "red";
                        chatIcon.style.animation = "pulse-red 1s infinite";
                        previousStatus = "error";
                    } else {
                        chatIcon.style.borderColor = "green";
                        chatIcon.style.animation = "none";
                        previousStatus = "success";
                    }
                })
                .catch(error => console.error("Status check failed:", error));
        }




        setInterval(checkValidationStatus, 3000);


        // Store last response to avoid duplicates
    let lastFetchedResponse = "";


    function fetchAIResponse() {
        console.log('🤖 Fetching AI response...');
        fetch(`${OPENAI_CHAT_URL}/get_latest_response`, {
            headers: { "ngrok-skip-browser-warning": "true" }  // ✅ FIXED: Skip ngrok warning
        })
            .then(response => response.json())
            .then(data => {
                console.log('Response data:', data);
                
                if (data.response && 
                    data.response !== "No AI response available" && 
                    data.response !== lastFetchedResponse) {
                    
                    console.log('✅ Adding new message to chat');
                    addMessage(data.response, "ai");
                    lastFetchedResponse = data.response;
                    
                    // Force scroll to make sure message is visible
                    setTimeout(() => {
                        scrollToBottom();
                    }, 100);
                } else {
                    console.log('❌ No new response or duplicate');
                }
            })
            .catch(error => {
                console.error("❌ Error fetching AI response:", error);
            });
    }
    function fetchAIResponseIfNew() {
        fetch(`${OPENAI_CHAT_URL}/get_latest_response`, {
            headers: { "ngrok-skip-browser-warning": "true" }  // ✅ FIXED: Skip ngrok warning
        })
            .then(response => response.json())
            .then(data => {
                if (data.response && 
                    data.response !== "No AI response available" && 
                    data.response !== lastFetchedResponse) {
                    
                    console.log('✅ Found new response, adding to chat');
                    addMessage(data.response, "ai");
                    lastFetchedResponse = data.response;
                    
                    setTimeout(() => {
                        scrollToBottom();
                    }, 100);
                }
            })
            .catch(error => console.error("Error checking for new response:", error));
    }



    // Manual test function - call this in browser console
    window.testChatMessage = function() {
        console.log('🧪 Testing chat message display...');
        addMessage("🔍 TEST: This is a manual test message to verify chat display is working correctly.", "ai");
    };
}
