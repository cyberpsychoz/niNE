/**
 * Chat Window Component - Garry's Mod style
 *
 * Two modes:
 * - Closed: Temporary messages with fade-out (10s show + 2.5s fade)
 * - Open: Full history + input field
 */

class ChatWindow {
    constructor(params = {}) {
        this.params = params;
        this.isOpen = false;

        // Message history
        this.messageHistory = [];
        this.maxHistory = 500;

        // Temporary messages (closed mode)
        this.tempMessages = [];
        this.maxTempMessages = 10;
        this.messageShowTime = 10000; // 10 seconds
        this.fadeDuration = 2500; // 2.5 seconds

        // Input history (arrow up/down)
        this.inputHistory = [];
        this.inputHistoryIndex = -1;
        this.maxInputHistory = 50;
        this.currentInputBackup = '';

        // Command suggestions
        this.commands = {
            'me': '/me <action> — action in first person',
            'it': '/it <text> — impersonal action',
            'looc': '/looc <text> — local OOC chat',
            'ooc': '/ooc <text> — global OOC chat',
            'help': '/help — show command list',
            'pos': '/pos — show your coordinates',
            'give': '/give <id> [amount] — give item',
            'startcombat': '/startcombat [radius] — start combat (DM)',
            'endcombat': '/endcombat — end combat (DM)',
            'spawnnpc': '/spawnnpc <template> [x y z] — spawn NPC (DM)',
        };
        this.currentSuggestions = [];
        this.selectedSuggestion = -1;

        console.log('[ChatWindow] Created');
    }

    async render() {
        // Load template
        const response = await fetch('templates/chat-window.html');
        const html = await response.text();

        // Insert into DOM (doesn't replace app, adds to body)
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        document.body.appendChild(tempDiv.firstElementChild);

        // Get element references
        this.element = document.getElementById('chat-window');
        this.tempMessagesContainer = document.getElementById('chat-temp-messages');
        this.chatFull = document.getElementById('chat-full');
        this.historyContent = document.getElementById('chat-history-content');
        this.historyContainer = document.getElementById('chat-history');
        this.input = document.getElementById('chat-input');
        this.suggestionsContainer = document.getElementById('chat-suggestions');
        this.suggestionsContent = document.getElementById('chat-suggestions-content');

        // Attach event listeners
        this.attachEventListeners();

        // Listen for messages from Python
        this.pythonMessageHandler = this._handlePythonMessage.bind(this);
        window.addEventListener('python-message', this.pythonMessageHandler);

        console.log('[ChatWindow] Rendered');
    }

    attachEventListeners() {
        // Input field
        this.input.addEventListener('keydown', (e) => this._onInputKeyDown(e));
        this.input.addEventListener('input', () => this._onInputChange());
        this.input.addEventListener('blur', () => {
            // Delay to allow clicking suggestions
            setTimeout(() => {
                if (this.isOpen) {
                    this.close();
                }
            }, 100);
        });

        // Global key listener for T to open chat
        this.globalKeyHandler = (e) => {
            if (e.key === 't' || e.key === 'T') {
                // Don't open if already typing in another input
                if (document.activeElement.tagName === 'INPUT' ||
                    document.activeElement.tagName === 'TEXTAREA') {
                    return;
                }
                e.preventDefault();
                this.open();
            }
        };
        document.addEventListener('keydown', this.globalKeyHandler);

        console.log('[ChatWindow] Event listeners attached');
    }

    /**
     * Handle messages from Python.
     */
    _handlePythonMessage(event) {
        const { type, data } = event.detail;

        if (type === 'chat_message') {
            this.addMessage(data);
        }
    }

    /**
     * Open chat (show history + input).
     */
    open() {
        if (this.isOpen) return;

        this.isOpen = true;
        this.chatFull.style.display = 'block';
        this.tempMessagesContainer.style.display = 'none';

        // Block game input while chat is open
        PythonAPI.setChatActive(true);

        // Focus input
        this.input.focus();

        // Scroll to bottom
        this._scrollToBottom();

        console.log('[ChatWindow] Opened');
    }

    /**
     * Close chat (hide history + input, show temp messages).
     */
    close() {
        if (!this.isOpen) return;

        this.isOpen = false;
        this.chatFull.style.display = 'none';
        this.tempMessagesContainer.style.display = 'block';

        // Restore game input
        PythonAPI.setChatActive(false);

        // Clear input
        this.input.value = '';
        this.input.blur();

        // Hide suggestions
        this._hideSuggestions();

        // Reset input history
        this.inputHistoryIndex = -1;
        this.currentInputBackup = '';

        console.log('[ChatWindow] Closed');
    }

    /**
     * Add a message to chat.
     * @param {Object} data - {sender, text, chat_type, is_system}
     */
    addMessage(data) {
        const messageData = {
            sender: data.sender || 'System',
            text: data.text || '',
            chatType: data.chat_type || 'ic',
            isSystem: data.is_system || false,
            timestamp: Date.now()
        };

        // Add to history
        this.messageHistory.push(messageData);
        if (this.messageHistory.length > this.maxHistory) {
            this.messageHistory.shift();
        }

        // If chat is open, add to history display
        if (this.isOpen) {
            this._addMessageToHistory(messageData);
        } else {
            // Add as temporary message
            this._addTemporaryMessage(messageData);
        }
    }

    /**
     * Add message to history display.
     */
    _addMessageToHistory(data) {
        const messageEl = this._createMessageElement(data);
        this.historyContent.appendChild(messageEl);

        // Scroll to bottom
        this._scrollToBottom();
    }

    /**
     * Add temporary message (fade out after time).
     */
    _addTemporaryMessage(data) {
        const messageEl = this._createMessageElement(data, true);
        messageEl.classList.add('chat-temp-message');

        this.tempMessagesContainer.appendChild(messageEl);
        this.tempMessages.push(messageEl);

        // Remove old messages if too many
        while (this.tempMessages.length > this.maxTempMessages) {
            const oldMsg = this.tempMessages.shift();
            oldMsg.remove();
        }

        // Fade out after show time
        setTimeout(() => {
            messageEl.classList.add('fading');

            // Remove after fade duration
            setTimeout(() => {
                messageEl.remove();
                const index = this.tempMessages.indexOf(messageEl);
                if (index > -1) {
                    this.tempMessages.splice(index, 1);
                }
            }, this.fadeDuration);
        }, this.messageShowTime);
    }

    /**
     * Create message HTML element.
     */
    _createMessageElement(data, isTemp = false) {
        const div = document.createElement('div');
        div.className = isTemp ? 'chat-temp-message' : 'chat-message';

        // Add type class
        if (data.isSystem) {
            div.classList.add('system');
        } else if (data.chatType === 'emote' || data.chatType === 'it') {
            div.classList.add('emote');
        } else if (data.chatType === 'ooc' || data.chatType === 'looc') {
            div.classList.add('ooc');
        }

        // Format message
        let html = '';

        // Add timestamp for history
        if (!isTemp) {
            const time = new Date(data.timestamp);
            const timeStr = `${time.getHours().toString().padStart(2, '0')}:${time.getMinutes().toString().padStart(2, '0')}`;
            html += `<span class="timestamp">[${timeStr}]</span> `;
        }

        // Format based on type
        if (data.isSystem) {
            html += `<span style="color: #d4af37;">${data.text}</span>`;
        } else if (data.chatType === 'emote' || data.chatType === 'me') {
            html += `<span class="sender">${data.sender}</span> ${data.text}`;
        } else if (data.chatType === 'it') {
            html += `<span style="color: #ffda66;">${data.text}</span>`;
        } else if (data.chatType === 'ooc') {
            html += `<span style="color: #e63939;">[OOC]</span> <span class="sender">${data.sender}:</span> ${data.text}`;
        } else if (data.chatType === 'looc') {
            html += `<span style="color: #e63939;">[LOOC]</span> <span class="sender">${data.sender}:</span> ${data.text}`;
        } else {
            // Normal IC message
            html += `<span class="sender">${data.sender}:</span> ${data.text}`;
        }

        div.innerHTML = html;
        return div;
    }

    /**
     * Handle input keydown.
     */
    _onInputKeyDown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            this._sendMessage();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            this.close();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this._navigateInputHistory(-1);
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            this._navigateInputHistory(1);
        } else if (e.key === 'Tab') {
            e.preventDefault();
            this._selectSuggestion();
        }
    }

    /**
     * Handle input change (for command suggestions).
     */
    _onInputChange() {
        const text = this.input.value;

        // Show suggestions for commands starting with /
        if (text.startsWith('/')) {
            const cmdPart = text.slice(1).toLowerCase();
            this._updateSuggestions(cmdPart);
        } else {
            this._hideSuggestions();
        }
    }

    /**
     * Update command suggestions.
     */
    _updateSuggestions(filter) {
        this.currentSuggestions = [];

        // Find matching commands
        for (const [cmd, desc] of Object.entries(this.commands)) {
            if (cmd.startsWith(filter) || filter === '') {
                this.currentSuggestions.push({ cmd, desc });
            }
        }

        if (this.currentSuggestions.length > 0) {
            this._showSuggestions();
        } else {
            this._hideSuggestions();
        }
    }

    /**
     * Show command suggestions.
     */
    _showSuggestions() {
        this.suggestionsContent.innerHTML = '';
        this.selectedSuggestion = -1;

        this.currentSuggestions.forEach((item, index) => {
            const div = document.createElement('div');
            div.className = 'chat-suggestion-item';
            div.innerHTML = `<span class="cmd">/${item.cmd}</span> — <span class="desc">${item.desc}</span>`;

            div.addEventListener('click', () => {
                this.input.value = `/${item.cmd} `;
                this.input.focus();
                this._hideSuggestions();
            });

            this.suggestionsContent.appendChild(div);
        });

        this.suggestionsContainer.style.display = 'block';
    }

    /**
     * Hide command suggestions.
     */
    _hideSuggestions() {
        this.suggestionsContainer.style.display = 'none';
        this.currentSuggestions = [];
        this.selectedSuggestion = -1;
    }

    /**
     * Select suggestion with Tab.
     */
    _selectSuggestion() {
        if (this.currentSuggestions.length === 0) return;

        // Auto-complete first suggestion
        const first = this.currentSuggestions[0];
        this.input.value = `/${first.cmd} `;
        this._hideSuggestions();
    }

    /**
     * Navigate input history with arrow keys.
     */
    _navigateInputHistory(direction) {
        if (this.inputHistory.length === 0) return;

        // Backup current input if starting navigation
        if (this.inputHistoryIndex === -1) {
            this.currentInputBackup = this.input.value;
        }

        // Navigate
        this.inputHistoryIndex += direction;

        // Clamp
        if (this.inputHistoryIndex < -1) {
            this.inputHistoryIndex = -1;
        }
        if (this.inputHistoryIndex >= this.inputHistory.length) {
            this.inputHistoryIndex = this.inputHistory.length - 1;
        }

        // Update input
        if (this.inputHistoryIndex === -1) {
            this.input.value = this.currentInputBackup;
        } else {
            this.input.value = this.inputHistory[this.inputHistory.length - 1 - this.inputHistoryIndex];
        }
    }

    /**
     * Send message.
     */
    _sendMessage() {
        const text = this.input.value.trim();
        if (!text) return;

        // Add to input history
        this.inputHistory.push(text);
        if (this.inputHistory.length > this.maxInputHistory) {
            this.inputHistory.shift();
        }
        this.inputHistoryIndex = -1;

        // Send to Python
        console.log(`[ChatWindow] Sending message: ${text}`);
        PythonAPI.sendChatMessage(text);

        // Clear input
        this.input.value = '';

        // Close chat
        this.close();
    }

    /**
     * Scroll history to bottom.
     */
    _scrollToBottom() {
        this.historyContainer.scrollTop = this.historyContainer.scrollHeight;
    }

    /**
     * Rebuild history display (when opening chat).
     */
    _rebuildHistory() {
        this.historyContent.innerHTML = '';

        // Show last N messages
        const start = Math.max(0, this.messageHistory.length - 100);
        for (let i = start; i < this.messageHistory.length; i++) {
            this._addMessageToHistory(this.messageHistory[i]);
        }
    }

    /**
     * Clean up and destroy the component.
     */
    destroy() {
        document.removeEventListener('keydown', this.globalKeyHandler);
        window.removeEventListener('python-message', this.pythonMessageHandler);

        if (this.element) {
            this.element.remove();
            this.element = null;
        }

        console.log('[ChatWindow] Destroyed');
    }
}

// ChatWindow is persistent, not managed by router
window.ChatWindow = ChatWindow;
