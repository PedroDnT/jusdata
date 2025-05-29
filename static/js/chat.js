/**
 * DataJud Chat - Client-side JavaScript
 * Handles the chat interface interactions, message sending, and display.
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM element references
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-btn');
    const typingIndicator = document.getElementById('typing-indicator');

    // Add welcome message
    appendMessage(
        'Olá! Sou o assistente do DataJud. Posso ajudar com consultas sobre processos judiciais brasileiros. Como posso ajudar você hoje?',
        'ai'
    );

    // Event listener for form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get user message
        const userMessage = chatInput.value.trim();
        
        // Don't proceed if message is empty
        if (!userMessage) return;
        
        // Display user message
        appendMessage(userMessage, 'user');
        
        // Clear and disable input
        chatInput.value = '';
        chatInput.disabled = true;
        sendButton.disabled = true;
        
        // Show typing indicator
        typingIndicator.classList.remove('d-none');
        
        // Send message to API
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: userMessage })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro na comunicação com o servidor');
            }
            return response.json();
        })
        .then(data => {
            // Hide typing indicator
            typingIndicator.classList.add('d-none');
            
            if (data.error) {
                // Display error message
                appendMessage(`Erro: ${data.error}`, 'error');
            } else {
                // Display AI response
                appendMessage(data.response, 'ai');
            }
        })
        .catch(error => {
            // Hide typing indicator
            typingIndicator.classList.add('d-none');
            
            // Display error message
            appendMessage(`Erro: ${error.message}`, 'error');
        })
        .finally(() => {
            // Re-enable input
            chatInput.disabled = false;
            sendButton.disabled = false;
            chatInput.focus();
        });
    });

    /**
     * Append a message to the chat area
     * @param {string} message - The message text
     * @param {string} sender - The message sender ('user', 'ai', or 'error')
     */
    function appendMessage(message, sender) {
        // Create message container
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `message-${sender}`, 'mb-3');
        
        // Create message content
        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');
        
        // Add appropriate styling based on sender
        if (sender === 'user') {
            contentDiv.classList.add('bg-primary', 'text-white', 'rounded', 'p-3', 'ms-auto');
            messageDiv.classList.add('text-end');
        } else if (sender === 'ai') {
            contentDiv.classList.add('bg-light', 'rounded', 'p-3', 'me-auto');
        } else if (sender === 'error') {
            contentDiv.classList.add('bg-danger', 'text-white', 'rounded', 'p-3', 'mx-auto');
        }
        
        // Format message text with line breaks
        message.split('\n').forEach((line, index, array) => {
            contentDiv.appendChild(document.createTextNode(line));
            if (index < array.length - 1) {
                contentDiv.appendChild(document.createElement('br'));
            }
        });
        
        // Assemble and append message
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        scrollToBottom();
    }

    /**
     * Scroll chat messages area to the bottom
     */
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    /**
     * Auto-resize textarea as user types
     */
    chatInput.addEventListener('input', function() {
        // Reset height to auto to get the correct scrollHeight
        this.style.height = 'auto';
        
        // Set new height based on scrollHeight (with max height of 150px)
        const newHeight = Math.min(this.scrollHeight, 150);
        this.style.height = newHeight + 'px';
    });

    // Allow pressing Enter to send (Shift+Enter for new line)
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });
});
