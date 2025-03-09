// Function to toggle chatbox visibility on single click
function toggleChatbox() {
    let chatbox = document.getElementById("chatbox");
    chatbox.style.display = chatbox.style.display === "none" ? "block" : "none";
}

// Function to make the chatbot icon draggable and distinguish between drag & click
function makeDraggable(element) {
    let offsetX = 0, offsetY = 0, mouseX = 0, mouseY = 0;
    let isDragging = false; // Flag to detect dragging
    let clickTimeout = null; // Timer for detecting double clicks

    element.onmousedown = function(event) {
        event.preventDefault();
        isDragging = false; // Reset dragging flag
        
        // Get initial mouse position
        mouseX = event.clientX;
        mouseY = event.clientY;
        
        document.onmousemove = function(e) {
            e.preventDefault();

            let dx = Math.abs(e.clientX - mouseX);
            let dy = Math.abs(e.clientY - mouseY);

            // If movement is significant, mark as dragging
            if (dx > 5 || dy > 5) {  
                isDragging = true;
            }

            // Move the element if dragging
            if (isDragging) {
                offsetX = mouseX - e.clientX;
                offsetY = mouseY - e.clientY;
                
                mouseX = e.clientX;
                mouseY = e.clientY;
                
                element.style.top = (element.offsetTop - offsetY) + "px";
                element.style.left = (element.offsetLeft - offsetX) + "px";
            }
        };
        
        document.onmouseup = function() {
            document.onmousemove = null;
            document.onmouseup = null;
        };
    };

    // Handle single click vs double click
    element.onclick = function(event) {
        if (isDragging) {
            return; // Ignore clicks if the icon was dragged
        }

        if (clickTimeout) {
            clearTimeout(clickTimeout); // If a second click occurs, clear the timeout
            clickTimeout = null;
        } else {
            clickTimeout = setTimeout(() => {
                toggleChatbox(); // Open chatbox only on single click
                clickTimeout = null;
            }, 250); // 300ms delay to detect double-click
        }
    };
}

// Wait until the document is loaded
document.addEventListener("DOMContentLoaded", function () {
    let chatbotIcon = document.getElementById("chatbot-icon");
    makeDraggable(chatbotIcon);
});

document.addEventListener("DOMContentLoaded", function () {
    let chatbox = document.getElementById("chatbox");
    let chatBody = document.createElement("div");
    chatBody.classList.add("chat-body");
    chatbox.appendChild(chatBody);

    let chatInput = document.createElement("textarea");
    chatInput.id = "chat-input";
    chatInput.placeholder = "Ask anything...";

    let sendBtn = document.createElement("button");
    sendBtn.id = "send-btn";
    sendBtn.innerText = "Send";

    let inputContainer = document.createElement("div");
    inputContainer.classList.add("chat-input-container");
    inputContainer.appendChild(chatInput);
    inputContainer.appendChild(sendBtn);

    chatbox.appendChild(inputContainer);

    function addMessage(text, sender) {
        let msgDiv = document.createElement("div");
        msgDiv.classList.add("chat-message", sender);
        msgDiv.innerText = text;
        chatBody.appendChild(msgDiv);

        // Auto-scroll to the latest message
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function sendMessage() {
        let userMessage = chatInput.value.trim();
        if (!userMessage) return;

        addMessage(userMessage, "user");
        chatInput.value = "";
        chatInput.style.height = "30px"; // Reset height

        // Simulate AI response (replace with backend call)
        setTimeout(() => addMessage("This is AI's response", "ai"), 1000);
    }

    sendBtn.onclick = sendMessage;
    chatInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    chatInput.addEventListener("input", function () {
        this.style.height = "30px"; // Reset first
        this.style.height = Math.min(this.scrollHeight, 100) + "px"; // Max 8 lines
    });
});
