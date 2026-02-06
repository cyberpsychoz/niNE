/**
 * Main entry point for niNE Web UI
 */

console.log('[Main] niNE Web UI starting...');

// Global chat window instance (persistent)
window.chatWindow = null;

// Wait for DOM ready
document.addEventListener('DOMContentLoaded', async () => {
    console.log('[Main] DOM ready');

    // Initialize persistent chat window
    window.chatWindow = new ChatWindow();
    await window.chatWindow.render();

    // Show main menu by default
    window.router.navigate('main-menu');

    console.log('[Main] niNE Web UI initialized');
});

// Debug: Log all Python messages
window.addEventListener('python-message', (event) => {
    console.log('[Main] Python message:', event.detail);
});
