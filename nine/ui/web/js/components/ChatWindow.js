/**
 * Chat Window Component — Garry's Mod style RP chat.
 *
 * Two modes:
 * - Closed: floating text messages with fade-out (10s + 2.5s), no box
 * - Open:   history panel + input + command suggestions
 *
 * Faithfully reproduces the DirectGUI ChatWindow from nine/ui/chat_window.py.
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
        this.messageShowTime = 10000;
        this.fadeDuration = 2500;

        // Input history (arrow up/down)
        this.inputHistory = [];
        this.inputHistoryIndex = -1;
        this.maxInputHistory = 50;
        this.currentInputBackup = '';

        // Full command list from CHAT_COMMANDS_CLIENT
        this.commands = {
            'me':             '/me <действие> — действие от первого лица',
            'it':             '/it <текст> — безличное действие',
            'looc':           '/looc <текст> — локальный OOC чат',
            'ooc':            '/ooc <текст> — глобальный OOC чат',
            'help':           '/help — показать список команд',
            'pos':            '/pos — показать свои координаты',
            'whoami':         '/whoami — показать имя и ID',
            'myrole':         '/myrole — показать свою роль',
            'setrole':        '/setrole <role> — установить роль',
            'give':           '/give <id> [кол-во] — выдать предмет',
            'spawn':          '/spawn <id> [кол-во] — заспавнить предмет',
            'items':          '/items — список предметов',
            'spawnnpc':       '/spawnnpc <шаблон> [x y z] — заспавнить NPC',
            'listnpcs':       '/listnpcs — список активных NPC',
            'removenpc':      '/removenpc <id> — удалить NPC',
            'startcombat':    '/startcombat [радиус] — начать бой',
            'endcombat':      '/endcombat — завершить бой',
            'nextturn':       '/nextturn — следующий ход',
            'spectator':      '/spectator — режим спектатора',
            'charsetmodel':   '/charsetmodel <модель> — изменить модель',
            'charsetfaction': '/charsetfaction <фракция> — изменить фракцию',
            'music':          '/music <play|stop|track> — музыка',
            'ambient':        '/ambient <set|stop> — эмбиент',
        };
        this.currentSuggestions = [];
        this.selectedSuggestion = -1;
        this.maxSuggestions = 6;

        // Game state
        this.gameState = 'MENU';
    }

    async render() {
        const response = await fetch('templates/chat-window.html');
        const html = await response.text();

        const wrapper = document.createElement('div');
        wrapper.innerHTML = html;
        // Append only the style and the chat-window div
        while (wrapper.firstChild) {
            document.body.appendChild(wrapper.firstChild);
        }

        this.element = document.getElementById('chat-window');
        this.hintBar = document.getElementById('chat-hint-bar');
        this.tempContainer = document.getElementById('chat-temp-messages');
        this.chatFull = document.getElementById('chat-full');
        this.historyContent = document.getElementById('chat-history-content');
        this.historyScroll = document.getElementById('chat-history');
        this.input = document.getElementById('chat-input');
        this.suggestionsEl = document.getElementById('chat-suggestions');
        this.suggestionsContent = document.getElementById('chat-suggestions-content');

        this._attachEvents();

        this.pythonHandler = this._onPythonMessage.bind(this);
        window.addEventListener('python-message', this.pythonHandler);

        console.log('[ChatWindow] Rendered');
    }

    // ================================================================
    // Events
    // ================================================================

    _attachEvents() {
        this.input.addEventListener('keydown', (e) => this._onKeyDown(e));
        this.input.addEventListener('input', () => this._onInputChange());

        // Close on blur (small delay so click on suggestion works)
        this.input.addEventListener('blur', () => {
            setTimeout(() => { if (this.isOpen) this.close(); }, 150);
        });

        // Global T key to open
        this._globalKey = (e) => {
            if (this.gameState === 'MENU' || this.gameState === 'CHARACTER_SELECT') return;
            if (document.activeElement.tagName === 'INPUT' ||
                document.activeElement.tagName === 'TEXTAREA') return;

            if (e.key === 't' || e.key === 'T') {
                e.preventDefault();
                this.open();
            }
        };
        document.addEventListener('keydown', this._globalKey);

        console.log('[ChatWindow] Event listeners attached');
    }

    _onPythonMessage(event) {
        const { type, data } = event.detail;
        if (type === 'chat_message') this.addMessage(data);
        else if (type === 'game_state_changed') this._onGameState(data);
    }

    _onGameState(data) {
        const s = data.new_state || data.state || '';
        this.gameState = s;

        if (s === 'IN_GAME') {
            if (this.hintBar && !this.isOpen) this.hintBar.style.display = 'block';
            if (this.element) this.element.style.display = '';
        } else {
            if (this.hintBar) this.hintBar.style.display = 'none';
            if (this.isOpen) this.close();
        }
    }

    // ================================================================
    // Open / Close
    // ================================================================

    open() {
        if (this.isOpen) return;
        this.isOpen = true;

        this.tempContainer.style.display = 'none';
        if (this.hintBar) this.hintBar.style.display = 'none';
        this.chatFull.classList.add('open');

        PythonAPI.setChatActive(true);

        this._rebuildHistory();
        this.input.focus();
        this._scrollToBottom();
    }

    close() {
        if (!this.isOpen) return;
        this.isOpen = false;

        this.chatFull.classList.remove('open');
        this.tempContainer.style.display = '';
        if (this.hintBar && this.gameState === 'IN_GAME') {
            this.hintBar.style.display = 'block';
        }

        PythonAPI.setChatActive(false);

        this.input.value = '';
        this.input.blur();
        this._hideSuggestions();
        this.inputHistoryIndex = -1;
        this.currentInputBackup = '';
    }

    // ================================================================
    // Messages
    // ================================================================

    addMessage(data) {
        const chatType = data.chat_type || 'ic';
        const msg = {
            sender: data.from_name || data.sender || '',
            text: data.message || data.text || '',
            chatType: chatType,
            isSystem: data.is_system || chatType === 'system',
            formattedMessage: data.formatted_message || null,
            timestamp: Date.now(),
        };

        this.messageHistory.push(msg);
        if (this.messageHistory.length > this.maxHistory) this.messageHistory.shift();

        if (this.isOpen) {
            this._appendHistoryMsg(msg);
        } else {
            this._addTempMsg(msg);
        }
    }

    _appendHistoryMsg(msg) {
        const el = this._buildMsgEl(msg, 'chat-msg');
        this.historyContent.appendChild(el);
        this._scrollToBottom();
    }

    _addTempMsg(msg) {
        const el = this._buildMsgEl(msg, 'chat-temp-msg');
        this.tempContainer.appendChild(el);
        this.tempMessages.push(el);

        while (this.tempMessages.length > this.maxTempMessages) {
            this.tempMessages.shift().remove();
        }

        setTimeout(() => {
            el.classList.add('fading');
            setTimeout(() => {
                el.remove();
                const i = this.tempMessages.indexOf(el);
                if (i > -1) this.tempMessages.splice(i, 1);
            }, this.fadeDuration);
        }, this.messageShowTime);
    }

    /**
     * Build a message DOM element.
     * Matches _format_message_for_display from chat_window.py.
     */
    _buildMsgEl(msg, baseClass) {
        const div = document.createElement('div');
        div.className = baseClass;

        const sender = this._esc(msg.sender);
        const text = this._esc(msg.text);
        const fmt = msg.formattedMessage ? this._esc(msg.formattedMessage) : null;
        let html = '';

        if (msg.isSystem) {
            div.classList.add('msg-system');
            html = `<span class="chat-system-star">*</span> ${text}`;

        } else if (msg.chatType === 'emote' || msg.chatType === 'me') {
            div.classList.add('msg-emote');
            html = fmt || `<span class="chat-emote-stars">**</span><span class="chat-sender">${sender}</span> ${text}`;

        } else if (msg.chatType === 'it') {
            div.classList.add('msg-it');
            html = fmt || `<span class="chat-emote-stars">**</span>${text}`;

        } else if (msg.chatType === 'looc') {
            div.classList.add('msg-looc');
            html = `<span class="chat-tag-looc">[LOOC]</span> <span class="chat-sender">${sender}:</span> ${text}`;

        } else if (msg.chatType === 'ooc') {
            div.classList.add('msg-ooc');
            html = `<span class="chat-tag-ooc">[OOC]</span> <span class="chat-sender">${sender}:</span> ${text}`;

        } else {
            div.classList.add('msg-ic');
            html = `<span class="chat-sender">${sender}:</span> ${text}`;
        }

        div.innerHTML = html;
        return div;
    }

    _esc(s) {
        if (!s) return '';
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    // ================================================================
    // Input handling
    // ================================================================

    _onKeyDown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            this._send();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            this.close();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this._historyNav(-1);
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            this._historyNav(1);
        } else if (e.key === 'Tab') {
            e.preventDefault();
            e.shiftKey ? this._shiftTab() : this._tab();
        }
    }

    _onInputChange() {
        const v = this.input.value;
        if (v.startsWith('/')) {
            const parts = v.slice(1).split(/\s+/);
            // Show suggestions only while typing command name (no space after it yet)
            if (parts.length <= 1) {
                this._updateSuggestions(parts[0].toLowerCase());
                return;
            }
        }
        this._hideSuggestions();
    }

    _send() {
        const text = this.input.value.trim();
        if (!text) return;

        this.inputHistory.push(text);
        if (this.inputHistory.length > this.maxInputHistory) this.inputHistory.shift();
        this.inputHistoryIndex = -1;

        PythonAPI.sendChatMessage(text);
        this.input.value = '';
        this.close();
    }

    // ================================================================
    // Input history (arrow up/down)
    // ================================================================

    _historyNav(dir) {
        if (!this.inputHistory.length) return;

        if (this.inputHistoryIndex === -1) {
            this.currentInputBackup = this.input.value;
        }

        this.inputHistoryIndex += dir;
        if (this.inputHistoryIndex < -1) this.inputHistoryIndex = -1;
        if (this.inputHistoryIndex >= this.inputHistory.length) {
            this.inputHistoryIndex = this.inputHistory.length - 1;
        }

        this.input.value = this.inputHistoryIndex === -1
            ? this.currentInputBackup
            : this.inputHistory[this.inputHistory.length - 1 - this.inputHistoryIndex];
    }

    // ================================================================
    // Command suggestions
    // ================================================================

    _updateSuggestions(filter) {
        this.currentSuggestions = [];
        for (const [cmd, desc] of Object.entries(this.commands)) {
            if (cmd.startsWith(filter) || filter === '') {
                this.currentSuggestions.push({ cmd, desc });
            }
            if (this.currentSuggestions.length >= this.maxSuggestions) break;
        }

        if (this.currentSuggestions.length > 0) {
            this.selectedSuggestion = -1;
            this._renderSuggestions();
            this.suggestionsEl.classList.add('visible');
        } else {
            this._hideSuggestions();
        }
    }

    _renderSuggestions() {
        this.suggestionsContent.innerHTML = '';
        this.currentSuggestions.forEach((item, i) => {
            const div = document.createElement('div');
            div.className = 'chat-suggestion-item';
            if (i === this.selectedSuggestion) div.classList.add('selected');
            div.innerHTML = `<span class="cmd">/${item.cmd}</span><span class="desc">${item.desc}</span>`;
            div.addEventListener('click', () => {
                this.input.value = `/${item.cmd} `;
                this.input.focus();
                this._hideSuggestions();
            });
            this.suggestionsContent.appendChild(div);
        });
    }

    _hideSuggestions() {
        this.suggestionsEl.classList.remove('visible');
        this.currentSuggestions = [];
        this.selectedSuggestion = -1;
    }

    /**
     * Tab — cycle forward. If only one match, insert immediately.
     * If on last item, insert. Otherwise advance selection.
     */
    _tab() {
        if (!this.currentSuggestions.length) return;

        // Single match → insert right away
        if (this.currentSuggestions.length === 1) {
            this.selectedSuggestion = 0;
            this._insertSuggestion();
            return;
        }

        if (this.selectedSuggestion === -1) {
            this.selectedSuggestion = 0;
        } else {
            const next = this.selectedSuggestion + 1;
            if (next >= this.currentSuggestions.length) {
                this._insertSuggestion();
                return;
            }
            this.selectedSuggestion = next;
        }
        this._renderSuggestions();
    }

    /**
     * Shift-Tab — cycle backward, wrap around.
     */
    _shiftTab() {
        if (!this.currentSuggestions.length) return;

        if (this.selectedSuggestion <= 0) {
            this.selectedSuggestion = this.currentSuggestions.length - 1;
        } else {
            this.selectedSuggestion--;
        }
        this._renderSuggestions();
    }

    _insertSuggestion() {
        if (this.selectedSuggestion < 0) return;
        const item = this.currentSuggestions[this.selectedSuggestion];
        this.input.value = `/${item.cmd} `;
        this.input.focus();
        this._hideSuggestions();
    }

    // ================================================================
    // Helpers
    // ================================================================

    _scrollToBottom() {
        this.historyScroll.scrollTop = this.historyScroll.scrollHeight;
    }

    _rebuildHistory() {
        this.historyContent.innerHTML = '';
        const start = Math.max(0, this.messageHistory.length - 100);
        for (let i = start; i < this.messageHistory.length; i++) {
            this._appendHistoryMsg(this.messageHistory[i]);
        }
    }

    destroy() {
        document.removeEventListener('keydown', this._globalKey);
        window.removeEventListener('python-message', this.pythonHandler);
        if (this.element) { this.element.remove(); this.element = null; }
    }
}

window.ChatWindow = ChatWindow;
