async function sendMessage() {
    const input = document.getElementById("userInput");
    const chatBox = document.getElementById("chatBox");

    const message = input.value.trim();
    if (!message) return;

    chatBox.innerHTML += `<div class="text-end mb-2"><span class="badge bg-primary">${message}</span></div>`;
    input.value = "";
    chatBox.scrollTop = chatBox.scrollHeight;

    // Show typing indicator
    const loaderId = "loader-" + Date.now();
    chatBox.innerHTML += `<div id="${loaderId}" class="text-start mb-2"><em>AI is thinking...</em></div>`;
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const res = await axios.post("/genai/chat", {
            message: message
        });

        document.getElementById(loaderId).remove();

        chatBox.innerHTML += `<div class="text-start mb-2"><span class="badge bg-secondary">${res.data.reply}</span></div>`;
        chatBox.scrollTop = chatBox.scrollHeight;

    } catch (error) {
        document.getElementById(loaderId).remove();
        chatBox.innerHTML += `<div class="text-danger">Error contacting AI</div>`;
    }
}

function handleKey(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
}