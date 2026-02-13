/**
 * Main entry point for niNE Web UI
 */

console.log('[Main] niNE Web UI starting...');

// Global chat window instance (persistent)
window.chatWindow = null;
// Global game HUD instance (persistent)
window.gameHUD = null;
// Global panel instances (persistent)
window.characterSheet = null;
window.spellbookPanel = null;
window.questLog = null;
window.restDialog = null;
// Global context menu (persistent)
window.contextMenu = null;

// Wait for DOM ready
document.addEventListener('DOMContentLoaded', async () => {
    console.log('[Main] DOM ready');

    // Initialize persistent chat window
    window.chatWindow = new ChatWindow();
    await window.chatWindow.render();

    // Initialize persistent game HUD
    window.gameHUD = new GameHUD();
    await window.gameHUD.init();

    // Initialize in-game panels
    window.characterSheet = new CharacterSheet();
    await window.characterSheet.init();

    window.spellbookPanel = new SpellbookPanel();
    await window.spellbookPanel.init();

    window.questLog = new QuestLog();
    await window.questLog.init();

    window.restDialog = new RestDialog();
    await window.restDialog.init();

    // Initialize persistent context menu
    window.contextMenu = new ContextMenu();
    await window.contextMenu.init();

    // Register panels with PanelManager
    // (keyboard shortcuts handled Python-side in cef_manager.py: I, K, J)
    if (window.panelManager) {
        window.panelManager.register('character-sheet', window.characterSheet);
        window.panelManager.register('spellbook', window.spellbookPanel);
        window.panelManager.register('quest-log', window.questLog);
    }

    // Initialize sound manager (menu music + UI sounds)
    if (window.soundManager) {
        await window.soundManager.init();
    }

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
