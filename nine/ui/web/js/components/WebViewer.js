/**
 * WebViewer Component - In-game web page viewer
 *
 * Allows DM and players to open external web pages (D&D Beyond, wikis, etc.)
 * directly in the game without alt-tabbing.
 *
 * Usage from Python:
 *   ui_manager.api.open_web_page("https://www.dndbeyond.com/spells", "Spells")
 *
 * Chat command:
 *   /dm openweb https://www.dndbeyond.com/spells
 */

class WebViewer {
    constructor() {
        this.element = null;
        this.iframe = null;
        this.isOpen = false;
        this.currentUrl = null;

        console.log('[WebViewer] Created');
    }

    /**
     * Render the WebViewer overlay (hidden by default).
     */
    async render() {
        // Load template
        const response = await fetch('templates/web-viewer.html');
        const html = await response.text();

        // Create wrapper element
        const wrapper = document.createElement('div');
        wrapper.innerHTML = html;
        this.element = wrapper.firstElementChild;

        // Append to body (outside main app container for overlay)
        document.body.appendChild(this.element);

        // Get references
        this.iframe = this.element.querySelector('#webviewer-iframe');
        this.titleEl = this.element.querySelector('#webviewer-title');
        this.urlEl = this.element.querySelector('#webviewer-url');

        // Attach event listeners
        this.attachEventListeners();

        // Subscribe to Python events
        this.subscribeToEvents();

        console.log('[WebViewer] Rendered');
    }

    /**
     * Attach event listeners.
     */
    attachEventListeners() {
        // Close button
        const closeBtn = this.element.querySelector('#webviewer-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }

        // Minimize button
        const minimizeBtn = this.element.querySelector('#webviewer-minimize');
        if (minimizeBtn) {
            minimizeBtn.addEventListener('click', () => this.minimize());
        }

        // Fullscreen button
        const fullscreenBtn = this.element.querySelector('#webviewer-fullscreen');
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
        }

        // Refresh button
        const refreshBtn = this.element.querySelector('#webviewer-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refresh());
        }

        // Back button
        const backBtn = this.element.querySelector('#webviewer-back');
        if (backBtn) {
            backBtn.addEventListener('click', () => this.back());
        }

        // Forward button
        const forwardBtn = this.element.querySelector('#webviewer-forward');
        if (forwardBtn) {
            forwardBtn.addEventListener('click', () => this.forward());
        }

        // Drag header
        const header = this.element.querySelector('#webviewer-header');
        if (header) {
            this.enableDrag(header);
        }

        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });

        console.log('[WebViewer] Event listeners attached');
    }

    /**
     * Subscribe to Python events.
     */
    subscribeToEvents() {
        window.addEventListener('python-message', (event) => {
            const { type, data } = event.detail;

            if (type === 'open_webview') {
                this.open(data.url, data.title);
            } else if (type === 'close_webview') {
                this.close();
            }
        });
    }

    /**
     * Open a web page in the viewer.
     * @param {string} url - URL to open
     * @param {string} title - Window title
     */
    open(url, title = 'Document') {
        console.log(`[WebViewer] Opening: ${url}`);

        this.currentUrl = url;
        this.isOpen = true;

        // Set content
        if (this.titleEl) {
            this.titleEl.textContent = title;
        }
        if (this.urlEl) {
            this.urlEl.textContent = url;
        }
        if (this.iframe) {
            this.iframe.src = url;
        }

        // Show element
        this.element.classList.add('visible');

        // Notify Python
        PythonAPI.call('on_webviewer_opened', { url, title });
    }

    /**
     * Close the web viewer.
     */
    close() {
        console.log('[WebViewer] Closing');

        this.isOpen = false;

        // Hide element
        this.element.classList.remove('visible');
        this.element.classList.remove('fullscreen');

        // Clear iframe
        if (this.iframe) {
            this.iframe.src = 'about:blank';
        }

        // Notify Python
        PythonAPI.call('on_webviewer_closed', {});
    }

    /**
     * Minimize the viewer.
     */
    minimize() {
        this.element.classList.toggle('minimized');
    }

    /**
     * Toggle fullscreen mode.
     */
    toggleFullscreen() {
        this.element.classList.toggle('fullscreen');
    }

    /**
     * Refresh current page.
     */
    refresh() {
        if (this.iframe && this.currentUrl) {
            this.iframe.src = this.currentUrl;
        }
    }

    /**
     * Go back in history.
     */
    back() {
        if (this.iframe && this.iframe.contentWindow) {
            try {
                this.iframe.contentWindow.history.back();
            } catch (e) {
                console.warn('[WebViewer] Cannot go back:', e);
            }
        }
    }

    /**
     * Go forward in history.
     */
    forward() {
        if (this.iframe && this.iframe.contentWindow) {
            try {
                this.iframe.contentWindow.history.forward();
            } catch (e) {
                console.warn('[WebViewer] Cannot go forward:', e);
            }
        }
    }

    /**
     * Enable dragging for the viewer window.
     * @param {HTMLElement} handle - Drag handle element
     */
    enableDrag(handle) {
        let isDragging = false;
        let startX, startY, startLeft, startTop;

        handle.addEventListener('mousedown', (e) => {
            // Don't drag if clicking buttons
            if (e.target.tagName === 'BUTTON') return;

            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;

            const rect = this.element.getBoundingClientRect();
            startLeft = rect.left;
            startTop = rect.top;

            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            this.element.style.left = `${startLeft + deltaX}px`;
            this.element.style.top = `${startTop + deltaY}px`;
            this.element.style.transform = 'none';
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });
    }

    /**
     * Destroy the component.
     */
    destroy() {
        if (this.element) {
            this.element.remove();
            this.element = null;
        }
        console.log('[WebViewer] Destroyed');
    }
}

// Create global instance
window.webViewer = null;

// Initialize after DOM ready
document.addEventListener('DOMContentLoaded', async () => {
    window.webViewer = new WebViewer();
    await window.webViewer.render();
});
