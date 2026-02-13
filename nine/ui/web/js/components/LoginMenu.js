/**
 * Login Menu Component
 *
 * Connection screen with IP, name, and password inputs.
 */

class LoginMenu {
    constructor(params = {}) {
        this.params = params;
        this.element = null;
        this.form = null;
        this.ipInput = null;
        this.nameInput = null;
        this.passwordInput = null;
        this.errorEl = null;
        this.connectBtn = null;

        console.log('[LoginMenu] Created');
    }

    async render() {
        // Load template
        const response = await fetch('templates/login-menu.html');
        const html = await response.text();

        // Insert into DOM
        const app = document.getElementById('app');
        app.innerHTML = html;

        // Get element references
        this.element = document.getElementById('login-menu-screen');
        this.form = document.getElementById('login-form');
        this.ipInput = document.getElementById('input-ip');
        this.nameInput = document.getElementById('input-name');
        this.passwordInput = document.getElementById('input-password');
        this.errorEl = document.getElementById('login-error');
        this.connectBtn = document.getElementById('btn-connect');

        // Set default values from params
        if (this.params.ip) {
            this.ipInput.value = this.params.ip;
        }
        if (this.params.name) {
            this.nameInput.value = this.params.name;
        }

        // Focus first empty field
        if (!this.ipInput.value) {
            this.ipInput.focus();
        } else if (!this.nameInput.value) {
            this.nameInput.focus();
        }

        // Attach event listeners
        this.attachEventListeners();

        console.log('[LoginMenu] Rendered');
    }

    attachEventListeners() {
        // Form submit (Enter key or Connect button)
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.attemptLogin();
        });

        // Connect button
        if (this.connectBtn) {
            this.connectBtn.addEventListener('click', () => {
                this.attemptLogin();
            });
        }

        // Back button
        const backBtn = document.getElementById('btn-back');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                console.log('[LoginMenu] Back clicked');
                PythonAPI.closeLoginMenu();
            });
        }

        // Clear error on input
        [this.ipInput, this.nameInput, this.passwordInput].forEach(input => {
            if (input) {
                input.addEventListener('input', () => this.hideError());
            }
        });

        console.log('[LoginMenu] Event listeners attached');
    }

    /**
     * Validate and attempt login.
     */
    attemptLogin() {
        const ip = this.ipInput.value.trim();
        const name = this.nameInput.value.trim();
        const password = this.passwordInput.value;

        // Validation
        if (!ip) {
            this.showError('Введите адрес сервера');
            this.ipInput.focus();
            return;
        }

        if (!name) {
            this.showError('Введите имя персонажа');
            this.nameInput.focus();
            return;
        }

        if (name.length < 2) {
            this.showError('Имя должно быть не менее 2 символов');
            this.nameInput.focus();
            return;
        }

        if (name.length > 20) {
            this.showError('Имя должно быть не более 20 символов');
            this.nameInput.focus();
            return;
        }

        // Show connecting state
        this.setConnecting(true);

        console.log(`[LoginMenu] Attempting login: ${name} -> ${ip}`);

        // Call Python API
        PythonAPI.attemptLogin(ip, name, password);

        // Reset state after delay (in case of no response)
        setTimeout(() => this.setConnecting(false), 10000);
    }

    /**
     * Show error message.
     */
    showError(message) {
        if (this.errorEl) {
            this.errorEl.textContent = message;
            this.errorEl.classList.add('visible');
        }
    }

    /**
     * Hide error message.
     */
    hideError() {
        if (this.errorEl) {
            this.errorEl.classList.remove('visible');
        }
    }

    /**
     * Set connecting state (disable inputs, show loading).
     */
    setConnecting(connecting) {
        if (this.connectBtn) {
            this.connectBtn.disabled = connecting;
            this.connectBtn.innerHTML = connecting
                ? '<span class="btn-icon">&#8987;</span> ПОДКЛЮЧЕНИЕ...'
                : '<span class="btn-icon">&#10148;</span> ПОДКЛЮЧИТЬСЯ';
        }

        [this.ipInput, this.nameInput, this.passwordInput].forEach(input => {
            if (input) input.disabled = connecting;
        });
    }

    /**
     * Handle connection error from Python.
     */
    onConnectionError(error) {
        this.setConnecting(false);
        this.showError(error || 'Ошибка подключения');
    }

    /**
     * Clean up and destroy the component.
     */
    destroy() {
        if (this.element) {
            this.element.remove();
            this.element = null;
        }
        console.log('[LoginMenu] Destroyed');
    }
}

// Register with router
window.router.registerScreen('login-menu', LoginMenu);
