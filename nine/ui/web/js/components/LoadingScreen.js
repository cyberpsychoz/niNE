/**
 * Loading Screen Component
 *
 * Shows loading progress with title, status text, progress bar, and hint.
 */

class LoadingScreen {
    constructor(params = {}) {
        this.params = params;
        this.element = null;
        this.progressBar = null;
        this.currentProgress = 0;

        console.log('[LoadingScreen] Created');
    }

    async render() {
        // Load template
        const response = await fetch('templates/loading-screen.html');
        const html = await response.text();

        // Insert into DOM
        const app = document.getElementById('app');
        app.innerHTML = html;

        // Get element references
        this.element = document.getElementById('loading-screen');
        this.titleEl = document.getElementById('loading-title');
        this.statusEl = document.getElementById('loading-status');
        this.progressBar = document.getElementById('loading-progress-bar');
        this.hintEl = document.getElementById('loading-hint');

        // Set initial values from params
        if (this.params.title) {
            this.setTitle(this.params.title);
        }
        if (this.params.status) {
            this.setStatus(this.params.status);
        }
        if (this.params.progress !== undefined) {
            this.setProgress(this.params.progress);
        }
        if (this.params.hint) {
            this.setHint(this.params.hint);
        }

        // Listen for updates from Python
        this.pythonMessageHandler = this._handlePythonMessage.bind(this);
        window.addEventListener('python-message', this.pythonMessageHandler);

        console.log('[LoadingScreen] Rendered');
    }

    /**
     * Handle messages from Python.
     */
    _handlePythonMessage(event) {
        const { type, data } = event.detail;

        if (type === 'loading_text') {
            this.setStatus(data.text);
        } else if (type === 'loading_progress') {
            if (data.progress !== undefined) {
                this.setProgress(data.progress);
            }
            if (data.text) {
                this.setStatus(data.text);
            }
        }
    }

    /**
     * Set loading title.
     */
    setTitle(title) {
        if (this.titleEl) {
            this.titleEl.textContent = title;
        }
    }

    /**
     * Set loading status text.
     */
    setStatus(status) {
        if (this.statusEl) {
            this.statusEl.textContent = status;
        }
    }

    /**
     * Set loading progress (0.0 to 1.0).
     */
    setProgress(progress) {
        this.currentProgress = Math.max(0, Math.min(1, progress));
        if (this.progressBar) {
            const percentage = Math.round(this.currentProgress * 100);
            this.progressBar.style.width = `${percentage}%`;
        }
    }

    /**
     * Set hint text.
     */
    setHint(hint) {
        if (this.hintEl) {
            this.hintEl.textContent = hint;
        }
    }

    /**
     * Clean up and destroy the component.
     */
    destroy() {
        window.removeEventListener('python-message', this.pythonMessageHandler);

        if (this.element) {
            this.element.remove();
            this.element = null;
        }

        console.log('[LoadingScreen] Destroyed');
    }
}

// Register with router
window.router.registerScreen('loading-screen', LoadingScreen);
