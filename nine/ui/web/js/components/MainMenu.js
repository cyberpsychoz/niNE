/**
 * Main Menu Screen Component
 */

class MainMenu {
    constructor(params = {}) {
        this.params = params;
        this.backgrounds = params.backgrounds || [];
        this.element = null;
        console.log('[MainMenu] Created');
    }

    /**
     * Render the main menu.
     */
    async render() {
        // Load template
        const response = await fetch('templates/main-menu.html');
        const html = await response.text();

        // Insert into DOM
        const app = document.getElementById('app');
        app.innerHTML = html;

        // Get element reference
        this.element = document.getElementById('main-menu-screen');

        // Set random background
        this._setBackground();

        // Attach event listeners
        this.attachEventListeners();

        console.log('[MainMenu] Rendered');
    }

    /**
     * Set a random background image from available backgrounds.
     */
    _setBackground() {
        if (!this.element || this.backgrounds.length === 0) return;
        const bg = this.backgrounds[Math.floor(Math.random() * this.backgrounds.length)];
        this.element.style.backgroundImage = `url('${bg}')`;
        this.element.style.backgroundSize = 'cover';
        this.element.style.backgroundPosition = 'center';
        console.log(`[MainMenu] Background set: ${bg}`);
    }

    /**
     * Attach event listeners to buttons.
     */
    attachEventListeners() {
        // PLAY button
        const playBtn = document.getElementById('btn-play');
        if (playBtn) {
            playBtn.addEventListener('click', () => {
                console.log('[MainMenu] PLAY clicked');
                PythonAPI.openLoginMenu();
            });
        }

        // SETTINGS button
        const settingsBtn = document.getElementById('btn-settings');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                console.log('[MainMenu] SETTINGS clicked');
                PythonAPI.openSettings();
            });
        }

        // EXIT button
        const exitBtn = document.getElementById('btn-exit');
        if (exitBtn) {
            exitBtn.addEventListener('click', () => {
                console.log('[MainMenu] EXIT clicked');
                PythonAPI.exitGame();
            });
        }

        console.log('[MainMenu] Event listeners attached');
    }

    /**
     * Clean up and destroy the component.
     */
    destroy() {
        if (this.element) {
            this.element.remove();
            this.element = null;
        }
        console.log('[MainMenu] Destroyed');
    }
}

// Register with router
window.router.registerScreen('main-menu', MainMenu);
