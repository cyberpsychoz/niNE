/**
 * In-Game Menu Component
 *
 * Pause menu shown during gameplay with blur overlay.
 */

class InGameMenu {
    constructor(params = {}) {
        this.params = params;
        this.element = null;

        console.log('[InGameMenu] Created');
    }

    async render() {
        // Load template
        const response = await fetch('templates/in-game-menu.html');
        const html = await response.text();

        // Insert into DOM
        const app = document.getElementById('app');
        app.innerHTML = html;

        // Get element reference
        this.element = document.getElementById('in-game-menu-screen');

        // Attach event listeners
        this.attachEventListeners();

        console.log('[InGameMenu] Rendered');
    }

    attachEventListeners() {
        // Resume button
        const resumeBtn = document.getElementById('btn-resume');
        if (resumeBtn) {
            resumeBtn.addEventListener('click', () => {
                console.log('[InGameMenu] Resume clicked');
                this.onResume();
            });
        }

        // Settings button
        const settingsBtn = document.getElementById('btn-settings');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                console.log('[InGameMenu] Settings clicked');
                this.onSettings();
            });
        }

        // Disconnect button
        const disconnectBtn = document.getElementById('btn-disconnect');
        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => {
                console.log('[InGameMenu] Disconnect clicked');
                this.onDisconnect();
            });
        }

        // ESC key to resume
        this.escHandler = (e) => {
            if (e.key === 'Escape') {
                this.onResume();
            }
        };
        document.addEventListener('keydown', this.escHandler);

        console.log('[InGameMenu] Event listeners attached');
    }

    /**
     * Resume game.
     */
    onResume() {
        console.log('[InGameMenu] Resuming game...');
        PythonAPI.hideInGameMenu();
    }

    /**
     * Open settings.
     */
    onSettings() {
        // TODO: Navigate to settings menu
        console.log('[InGameMenu] Opening settings...');
        PythonAPI.openSettings();
    }

    /**
     * Disconnect from server.
     */
    onDisconnect() {
        if (confirm('Are you sure you want to disconnect?')) {
            console.log('[InGameMenu] Disconnecting...');
            PythonAPI.disconnect();
        }
    }

    /**
     * Clean up and destroy the component.
     */
    destroy() {
        document.removeEventListener('keydown', this.escHandler);

        if (this.element) {
            this.element.remove();
            this.element = null;
        }

        console.log('[InGameMenu] Destroyed');
    }
}

// Register with router
window.router.registerScreen('in-game-menu', InGameMenu);
