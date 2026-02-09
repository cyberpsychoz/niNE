/**
 * Main entry point for niNE Web UI
 */

console.log('[Main] niNE Web UI starting...');

// Global chat window instance (persistent)
window.chatWindow = null;
// Global game HUD instance (persistent)
window.gameHUD = null;

// Wait for DOM ready
document.addEventListener('DOMContentLoaded', async () => {
    console.log('[Main] DOM ready');

    // Initialize persistent chat window
    window.chatWindow = new ChatWindow();
    await window.chatWindow.render();

    // Initialize persistent game HUD
    window.gameHUD = new GameHUD();
    await window.gameHUD.init();

    // Do NOT navigate here - Python side controls initial navigation
    // via show_main_menu() which also passes background images.
    // Navigating here would cause a double-render flash.

    console.log('[Main] niNE Web UI initialized, waiting for Python navigation');
});

// Debug: Log Python messages (skip frequent events)
window.addEventListener('python-message', (event) => {
    const type = event.detail && event.detail.type;
    if (type !== 'world_state') {
        console.log('[Main] Python message:', type);
    }
});
