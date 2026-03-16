/**
 * PanelManager - Central manager for in-game overlay panels.
 *
 * Panel toggle shortcuts are handled Python-side (Panda3D accept()) because
 * CEF offscreen doesn't reliably produce event.key for RAWKEYDOWN on Linux.
 * Python sends "toggle_panel" events via send_to_js().
 *
 * Responsibilities:
 *  - Register panels by name
 *  - Toggle panels via Python events (I, K, J keys handled in cef_manager.py)
 *  - Mutual exclusion: only one panel open at a time
 *  - Close on Escape (via Python special key handler)
 */

class PanelManager {
    constructor() {
        /** @type {Map<string, {component: Object}>} */
        this.panels = new Map();

        /** @type {string|null} Currently open panel name */
        this.activePanel = null;

        // Listen for Python-sent panel toggle events
        this._subscribePythonEvents();

        console.log('[PanelManager] Initialized');
    }

    /**
     * Register a panel component.
     * @param {string} name - Panel name (e.g. 'character-sheet')
     * @param {Object} component - Component with show()/hide() methods
     */
    register(name, component) {
        this.panels.set(name, { component });
        console.log(`[PanelManager] Registered panel: ${name}`);
    }

    /**
     * Toggle a panel by name.
     * @param {string} name - Panel name
     * @param {Object} [options] - Extra options passed to show()
     */
    toggle(name, options) {
        if (this.activePanel === name) {
            this.closeActive();
        } else {
            this.open(name, options);
        }
    }

    /**
     * Open a panel (closes any currently open panel first).
     * @param {string} name - Panel name
     * @param {Object} [options] - Extra options passed to show()
     */
    open(name, options) {
        const entry = this.panels.get(name);
        if (!entry) return;

        // Close current panel if different
        if (this.activePanel && this.activePanel !== name) {
            this.closeActive();
        }

        entry.component.show(options);
        this.activePanel = name;
    }

    /**
     * Close the currently active panel.
     */
    closeActive() {
        if (!this.activePanel) return;

        const entry = this.panels.get(this.activePanel);
        if (entry) {
            entry.component.hide();
        }
        this.activePanel = null;

        // Notify Python so it can track panel state for escape handling
        if (window.pyapi) window.pyapi.panel_closed();
    }

    /**
     * Check if any panel is currently open.
     * @returns {boolean}
     */
    isAnyOpen() {
        return this.activePanel !== null;
    }

    // ================================================================
    // Python Event Handling
    // ================================================================

    _subscribePythonEvents() {
        window.addEventListener('python-message', (event) => {
            const { type, data } = event.detail;

            if (type === 'toggle_panel') {
                const panel = data?.panel;
                if (panel) {
                    this.toggle(panel, data?.options);
                }
            } else if (type === 'close_panel') {
                this.closeActive();
            }
        });
    }
}

// Global instance
window.panelManager = new PanelManager();
