/**
 * Python API Wrapper - JavaScript interface to Python backend
 *
 * Supports both pywebview and CEF (cefpython3) backends.
 *
 * Usage:
 *   await PythonAPI.exitGame()
 *   await PythonAPI.attemptLogin(ip, name, pw)
 *   await PythonAPI.call('method_name', {arg1: 'val'})
 */

class PythonAPI {
    /**
     * Get the Python API object (works with both pywebview and CEF).
     */
    static getApi() {
        // CEF: pyapi object injected via SetJavascriptBindings
        if (typeof pyapi !== 'undefined') {
            return pyapi;
        }
        // pywebview: pywebview.api
        if (typeof pywebview !== 'undefined' && pywebview.api) {
            return pywebview.api;
        }
        console.warn('[API] No Python API available');
        return null;
    }

    /**
     * Generic call to Python method.
     * @param {string} method - Method name
     * @param {Object} data - Arguments (optional)
     */
    static async call(method, data = null) {
        const api = this.getApi();
        if (!api) return;

        console.log(`[API] Calling Python: ${method}()`, data);
        try {
            if (api[method]) {
                if (data) {
                    return await api[method](data);
                }
                return await api[method]();
            } else {
                console.warn(`[API] Method not found: ${method}`);
            }
        } catch (error) {
            console.error(`[API] Error calling ${method}:`, error);
        }
    }

    /**
     * Exit the game.
     */
    static async exitGame() {
        console.log('[API] Calling Python: exit_game()');
        const api = this.getApi();
        if (!api) return;
        try {
            await api.exit_game();
        } catch (error) {
            console.error('[API] Error calling exit_game:', error);
        }
    }

    /**
     * Open login menu.
     */
    static async openLoginMenu() {
        console.log('[API] Calling Python: open_login_menu()');
        const api = this.getApi();
        if (!api) return;
        try {
            await api.open_login_menu();
        } catch (error) {
            console.error('[API] Error calling open_login_menu:', error);
        }
    }

    /**
     * Attempt login to server.
     * @param {string} ip - Server IP
     * @param {string} nickname - Player nickname
     * @param {string} password - Server password
     */
    static async attemptLogin(ip, nickname, password) {
        console.log(`[API] Calling Python: attempt_login(${ip}, ${nickname})`);
        const api = this.getApi();
        if (!api) return;
        try {
            await api.attempt_login(ip, nickname, password);
        } catch (error) {
            console.error('[API] Error calling attempt_login:', error);
        }
    }

    /**
     * Close login menu.
     */
    static async closeLoginMenu() {
        console.log('[API] Calling Python: close_login_menu()');
        const api = this.getApi();
        if (!api) return;
        try {
            await api.close_login_menu();
        } catch (error) {
            console.error('[API] Error calling close_login_menu:', error);
        }
    }

    /**
     * Open settings menu.
     */
    static async openSettings() {
        console.log('[API] Calling Python: open_settings()');
        const api = this.getApi();
        if (!api) return;
        try {
            await api.open_settings();
        } catch (error) {
            console.error('[API] Error calling open_settings:', error);
        }
    }

    /**
     * Save settings.
     * @param {Object} settings - Settings object
     */
    static async saveSettings(settings) {
        console.log('[API] Calling Python: save_settings()', settings);
        const api = this.getApi();
        if (!api) return;
        try {
            await api.save_settings(settings);
        } catch (error) {
            console.error('[API] Error calling save_settings:', error);
        }
    }

    /**
     * Send chat message.
     * @param {string} message - Chat message
     */
    static async sendChatMessage(message) {
        console.log(`[API] Calling Python: send_chat_message("${message}")`);
        const api = this.getApi();
        if (!api) return;
        try {
            await api.send_chat_message(message);
        } catch (error) {
            console.error('[API] Error calling send_chat_message:', error);
        }
    }

    /**
     * Disconnect from server.
     */
    static async disconnect() {
        console.log('[API] Calling Python: disconnect()');
        const api = this.getApi();
        if (!api) return;
        try {
            await api.disconnect();
        } catch (error) {
            console.error('[API] Error calling disconnect:', error);
        }
    }

    /**
     * Hide in-game menu and resume game.
     */
    static async hideInGameMenu() {
        console.log('[API] Calling Python: hide_in_game_menu()');
        const api = this.getApi();
        if (!api) return;
        try {
            await api.hide_in_game_menu();
        } catch (error) {
            console.error('[API] Error calling hide_in_game_menu:', error);
        }
    }

    /**
     * Open web page in WebViewer.
     * @param {string} url - URL to open
     * @param {string} title - Window title
     */
    static async openWebPage(url, title = 'Document') {
        console.log(`[API] Calling Python: open_web_page("${url}")`);
        const api = this.getApi();
        if (!api) return;
        try {
            await api.open_web_page(url, title);
        } catch (error) {
            console.error('[API] Error calling open_web_page:', error);
        }
    }

    /**
     * Close WebViewer.
     */
    static async closeWebPage() {
        console.log('[API] Calling Python: close_web_page()');
        const api = this.getApi();
        if (!api) return;
        try {
            await api.close_web_page();
        } catch (error) {
            console.error('[API] Error calling close_web_page:', error);
        }
    }
}

/**
 * Receive messages from Python.
 * Called by Python via webview.evaluate_js("window.receiveFromPython(...)")
 *
 * @param {Object} message - Message from Python {type: "event_type", data: {...}}
 */
window.receiveFromPython = function(message) {
    console.log('[API] Received from Python:', message);

    const { type, data } = message;

    // Dispatch custom event
    const event = new CustomEvent('python-message', {
        detail: { type, data }
    });
    window.dispatchEvent(event);
};

// Export to global scope
window.PythonAPI = PythonAPI;
