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
     * Set chat active state (blocks game input while chat is open).
     * @param {boolean} active - Whether chat is open
     */
    static async setChatActive(active) {
        const api = this.getApi();
        if (!api) return;
        try {
            await api.set_chat_active({ active: !!active });
        } catch (error) {
            console.error('[API] Error calling set_chat_active:', error);
        }
    }

    /**
     * Select a character to play.
     * @param {string} characterUuid - Character UUID
     */
    static async selectCharacter(characterUuid) {
        console.log(`[API] Calling Python: select_character(${characterUuid})`);
        const api = this.getApi();
        if (!api) return;
        try {
            await api.select_character(characterUuid);
        } catch (error) {
            console.error('[API] Error calling select_character:', error);
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
     * Get current settings from Python.
     */
    static async getSettings() {
        console.log('[API] Calling Python: get_settings()');
        const api = this.getApi();
        if (!api) return {};
        try {
            return await api.get_settings();
        } catch (error) {
            console.error('[API] Error calling get_settings:', error);
            return {};
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
     * Create a character.
     * @param {Object} data - Character data {name, race, class_name, background}
     */
    static async createCharacter(data) {
        console.log('[API] Calling Python: create_character()', data);
        const api = this.getApi();
        if (!api) return;
        try {
            await api.create_character(data);
        } catch (error) {
            console.error('[API] Error calling create_character:', error);
        }
    }

    /**
     * Execute a combat action.
     * @param {string} action - Action ID (attack, dash, dodge, etc.)
     * @param {string} target - Target entity ID (optional)
     */
    static async combatAction(action, target = '') {
        console.log(`[API] Calling Python: combat_action(${action}, ${target})`);
        const api = this.getApi();
        if (!api) return;
        try {
            await api.combat_action(action, target);
        } catch (error) {
            console.error('[API] Error calling combat_action:', error);
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

    /**
     * Equip an item from inventory.
     * @param {number} slot - Inventory slot index
     */
    static async equipItem(slot) {
        return this.call('equip_item', { inventory_slot: slot });
    }

    /**
     * Unequip an item from equipment slot.
     * @param {string} slot - Equipment slot name
     */
    static async unequipItem(slot) {
        return this.call('unequip_item', { equipment_slot: slot });
    }

    /**
     * Cast a spell.
     * @param {string} spellId - Spell ID
     * @param {number} slotLevel - Spell slot level to use
     */
    static async castSpell(spellId, slotLevel) {
        return this.call('cast_spell', { spell_id: spellId, slot_level: slotLevel });
    }

    /**
     * Prepare a spell.
     * @param {string} spellId - Spell ID
     */
    static async prepareSpell(spellId) {
        return this.call('prepare_spell', { spell_id: spellId });
    }

    /**
     * Unprepare a spell.
     * @param {string} spellId - Spell ID
     */
    static async unprepareSpell(spellId) {
        return this.call('unprepare_spell', { spell_id: spellId });
    }

    /**
     * Request quest list from server.
     * @param {string} filter - Filter type (all, active, available, completed)
     */
    static async questListRequest(filter = 'all') {
        return this.call('quest_list_request', { filter });
    }

    /**
     * Abandon a quest.
     * @param {string} questId - Quest ID
     */
    static async questAbandon(questId) {
        return this.call('quest_abandon', { quest_id: questId });
    }

    /**
     * Spend a hit die during rest.
     */
    static async spendHitDie() {
        return this.call('spend_hit_die', { count: 1 });
    }

    /**
     * Finish a rest.
     * @param {string} restType - Rest type (short, long)
     */
    static async finishRest(restType) {
        return this.call('finish_rest', { rest_type: restType });
    }

    /**
     * Update character description field.
     * @param {string} field - Field name
     * @param {string} value - New value
     */
    static async updateDescription(field, value) {
        return this.call('update_description', { field, value });
    }

    /**
     * Use an inventory item.
     * @param {number} slot - Inventory slot index
     */
    static async itemUse(slot) {
        return this.call('item_use', { slot });
    }

    /**
     * Drop an inventory item.
     * @param {number} slot - Inventory slot index
     * @param {number} count - Number to drop
     */
    static async itemDrop(slot, count = 1) {
        return this.call('item_drop', { slot, count });
    }

    /**
     * Execute an interaction with an entity (from context menu).
     * @param {string} entityId - Entity ID
     * @param {string} action - Action name (talk, trade, attack, loot, pickup, inspect)
     */
    static async interactWith(entityId, action) {
        return this.call('interact_with', { entity_id: entityId, action: action });
    }
}

/**
 * Receive messages from Python.
 * Called by Python via webview.evaluate_js("window.receiveFromPython(...)")
 *
 * @param {Object} message - Message from Python {type: "event_type", data: {...}}
 */
window.receiveFromPython = function(message) {
    const { type, data } = message;

    // Dispatch custom event
    const event = new CustomEvent('python-message', {
        detail: { type, data }
    });
    window.dispatchEvent(event);
};

// Export to global scope
window.PythonAPI = PythonAPI;
