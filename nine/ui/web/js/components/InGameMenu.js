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
     * Disconnect from server - show inline confirmation.
     */
    onDisconnect() {
        this.showDisconnectConfirm();
    }

    /**
     * Show inline disconnect confirmation overlay.
     * Replaces confirm() which silently returns false in offscreen CEF.
     */
    showDisconnectConfirm() {
        // Don't stack multiple overlays
        if (document.getElementById('disconnect-confirm-overlay')) return;

        const overlay = document.createElement('div');
        overlay.id = 'disconnect-confirm-overlay';
        overlay.style.cssText = 'position: absolute; top: 0; left: 0; width: 100%; height: 100%; ' +
            'background: rgba(0, 0, 0, 0.7); display: flex; flex-direction: column; ' +
            'align-items: center; justify-content: center; z-index: 100; gap: 20px;';

        const message = document.createElement('p');
        message.textContent = 'Are you sure you want to disconnect?';
        message.style.cssText = 'color: #fff; font-size: 18px; margin: 0;';

        const btnRow = document.createElement('div');
        btnRow.style.cssText = 'display: flex; gap: 16px;';

        const yesBtn = document.createElement('button');
        yesBtn.className = 'bg1-button bg1-button-primary';
        yesBtn.textContent = 'YES';
        yesBtn.addEventListener('click', () => {
            console.log('[InGameMenu] Disconnecting...');
            PythonAPI.disconnect();
        });

        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'bg1-button';
        cancelBtn.textContent = 'CANCEL';
        cancelBtn.addEventListener('click', () => {
            this.hideDisconnectConfirm();
        });

        btnRow.appendChild(yesBtn);
        btnRow.appendChild(cancelBtn);
        overlay.appendChild(message);
        overlay.appendChild(btnRow);

        const screenContent = this.element ? this.element.querySelector('.screen-content') : null;
        if (screenContent) {
            screenContent.style.position = 'relative';
            screenContent.appendChild(overlay);
        }
    }

    /**
     * Hide the inline disconnect confirmation overlay.
     */
    hideDisconnectConfirm() {
        const overlay = document.getElementById('disconnect-confirm-overlay');
        if (overlay) {
            overlay.remove();
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
