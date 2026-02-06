/**
 * SPA Router - manages screen navigation
 *
 * Fixes bug: Combat windows remain when exiting to main menu
 * -> Router automatically cleans up previous screen
 */

class Router {
    constructor() {
        this.currentScreen = null;
        this.screens = new Map();

        console.log('[Router] Initialized');
    }

    /**
     * Register a screen component.
     * @param {string} name - Screen name (e.g., "main-menu")
     * @param {Function} ScreenClass - Screen component class
     */
    registerScreen(name, ScreenClass) {
        this.screens.set(name, ScreenClass);
        console.log(`[Router] Registered screen: ${name}`);
    }

    /**
     * Navigate to a screen.
     * @param {string} screenName - Screen name to navigate to
     * @param {Object} params - Optional parameters for screen
     */
    async navigate(screenName, params = {}) {
        console.log(`[Router] Navigating to: ${screenName}`, params);

        // Special case: "hidden" screen (hide UI completely)
        if (screenName === 'hidden') {
            if (this.currentScreen) {
                this.currentScreen.destroy();
                this.currentScreen = null;
            }
            document.getElementById('app').innerHTML = '';
            console.log('[Router] UI hidden');
            return;
        }

        // Destroy current screen
        if (this.currentScreen) {
            console.log(`[Router] Destroying previous screen: ${this.currentScreen.constructor.name}`);
            this.currentScreen.destroy();
            this.currentScreen = null;
        }

        // Get screen class
        const ScreenClass = this.screens.get(screenName);
        if (!ScreenClass) {
            console.error(`[Router] Screen not found: ${screenName}`);
            return;
        }

        // Create and render new screen
        try {
            this.currentScreen = new ScreenClass(params);
            await this.currentScreen.render();
            console.log(`[Router] Rendered screen: ${screenName}`);
        } catch (error) {
            console.error(`[Router] Error rendering screen ${screenName}:`, error);
        }
    }

    /**
     * Get current screen.
     * @returns {Object|null} Current screen instance
     */
    getCurrentScreen() {
        return this.currentScreen;
    }
}

// Create global router instance
window.router = new Router();

// Listen for navigation events from Python
window.addEventListener('python-message', (event) => {
    const { type, data } = event.detail;

    if (type === 'navigate') {
        const { screen, params } = data;
        window.router.navigate(screen, params);
    }
});
