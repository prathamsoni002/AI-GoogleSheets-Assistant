if (!window.chatbotInjected) {
    window.chatbotInjected = true;

    let chatIcon = document.createElement("div");
    chatIcon.id = "chatbot-icon";
    chatIcon.innerHTML = `<img src="${chrome.runtime.getURL("icon.png")}" alt="Chat Icon">`;

    let chatFrame = document.createElement("div");
    chatFrame.id = "chatbox";
    chatFrame.style.display = "none";
    chatFrame.innerHTML = `
        <div class="chat-body"></div>
        <div class="chat-input-container">
            <textarea id="chat-input" placeholder="Ask anything..."></textarea>
            <button id="send-btn">Send</button>
        </div>
    `;

    document.body.appendChild(chatIcon);
    document.body.appendChild(chatFrame);

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
            // Move the icon to the left of the chatbox
            let newLeft = chatRect.left - iconRect.width - 10;
            if (newLeft < 10) newLeft = 10; // Ensure it doesn't go off-screen

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

    let chatBody = document.querySelector(".chat-body");
    let chatInput = document.getElementById("chat-input");
    let sendBtn = document.getElementById("send-btn");

    function addMessage(text, sender) {
        let chatBody = document.querySelector(".chat-body");
        let msgDiv = document.createElement("div");
        msgDiv.classList.add("chat-message", sender);
        msgDiv.innerText = text;
    
        chatBody.appendChild(msgDiv);
    
        // **Ensure scrolling works correctly**
        requestAnimationFrame(() => {
            chatBody.scrollTop = chatBody.scrollHeight;
        });
    }
    

    function sendMessage() {
        let userMessage = chatInput.value.trim();
        if (!userMessage) return;

        addMessage(userMessage, "user");
        chatInput.value = "";
        chatInput.style.height = "30px";

        // change the web link to the one which is hosted leave /get-response
        fetch("https://6518-110-226-182-1.ngrok-free.app/get_response", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: userMessage }),
        })
        .then(response => response.json())
        .then(data => addMessage(data.response, "ai"))
        .catch(error => addMessage("Error: Unable to get response", "ai"));
    }

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

    
    

    let previousStatus = "success"; // Track the previous status
    

    function checkValidationStatus() {
        fetch("http://localhost:5000/get_status")
            .then(response => response.json())
            .then(data => {
                const chatIcon = document.getElementById("chatbot-icon");
                if (data.status === "error") {
                    if (chatIcon.style.borderColor !== "red") {
                        chatIcon.style.borderColor = "red";
                        chatIcon.style.animation = "pulse-red 1s infinite";

                        // 🟢➡️🔴 If status changed from success to error, fetch AI response
                        if (previousStatus === "success") {
                            console.log("🚨 Error detected! Fetching AI response...");
                            fetchAIResponse();
                        }
                        previousStatus = "error";
                    }
                } else {
                    if (chatIcon.style.borderColor !== "green") {
                        chatIcon.style.borderColor = "green";
                        chatIcon.style.animation = "none";
                    }
                    previousStatus = "success";
                }
            })
            .catch(error => console.error("Error fetching validation status:", error));
    }

    
    setInterval(checkValidationStatus, 3000); // Check every 3 seconds    

   
    function fetchAIResponse() {
        fetch("http://localhost:5000/get_latest_response")
            .then(response => response.json())
            .then(data => {
                if (data.response) {
                    addMessage(data.response, "ai"); // Display AI response
                }
            })
            .catch(error => console.error("Error fetching AI response:", error));
    }
    
    
    
}
