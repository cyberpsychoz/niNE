/**
 * ContextMenu - RPG-style right-click context menu for world interactions.
 *
 * Persistent overlay appended to document.body (outside #app).
 * Controlled by Python events: show_context_menu / hide_context_menu.
 */
class ContextMenu {
    constructor() {
        this.el = null;
        this.headerEl = null;
        this.actionsEl = null;
        this.entityId = null;
        this.visible = false;

        // Action labels (Russian)
        this.actionLabels = {
            talk:    'Поговорить',
            trade:   'Торговать',
            attack:  'Атаковать',
            loot:    'Обыскать',
            pickup:  'Подобрать',
            inspect: 'Осмотреть',
        };

        // Bound handlers for cleanup
        this._onClickOutside = this._onClickOutside.bind(this);
        this._onEscape = this._onEscape.bind(this);
    }

    async init() {
        // Load template
        try {
            const resp = await fetch('templates/context-menu.html');
            const html = await resp.text();
            const wrapper = document.createElement('div');
            wrapper.innerHTML = html.trim();
            this.el = wrapper.firstElementChild;
        } catch (e) {
            // Fallback: create manually
            this.el = document.createElement('div');
            this.el.className = 'ctx-menu';
            this.el.style.display = 'none';
            this.el.innerHTML = '<div class="ctx-menu-header"></div><div class="ctx-menu-actions"></div>';
        }

        document.body.appendChild(this.el);
        this.headerEl = this.el.querySelector('.ctx-menu-header');
        this.actionsEl = this.el.querySelector('.ctx-menu-actions');

        // Listen for Python events
        window.addEventListener('python-message', (e) => {
            const { type, data } = e.detail;
            if (type === 'show_context_menu') {
                this.show(data);
            } else if (type === 'hide_context_menu') {
                this.hide();
            }
        });

        console.log('[ContextMenu] Initialized');
    }

    /**
     * Show context menu at mouse position.
     * @param {Object} data - { entity_id, mouse_x, mouse_y, display_name, actions, entity_type }
     */
    show(data) {
        if (!data || !data.actions || data.actions.length === 0) return;

        this.entityId = data.entity_id;

        // Set header
        this.headerEl.textContent = data.display_name || 'Entity';

        // Build action buttons
        this.actionsEl.innerHTML = '';
        for (const action of data.actions) {
            const btn = document.createElement('div');
            btn.className = 'ctx-menu-action';
            btn.textContent = this.actionLabels[action] || action;
            btn.dataset.action = action;
            btn.addEventListener('click', () => {
                this._executeAction(action);
            });
            this.actionsEl.appendChild(btn);
        }

        // Convert Panda3D mouse coords [-1,1] to browser pixels
        const mx = data.mouse_x || 0;
        const my = data.mouse_y || 0;
        const px = Math.round((mx + 1.0) * 0.5 * window.innerWidth);
        const py = Math.round((1.0 - my) * 0.5 * window.innerHeight);

        // Position the menu (show first to measure size)
        this.el.style.display = 'block';
        this.visible = true;

        // Clamp to viewport edges
        const rect = this.el.getBoundingClientRect();
        let x = px;
        let y = py;

        if (x + rect.width > window.innerWidth) {
            x = window.innerWidth - rect.width - 4;
        }
        if (y + rect.height > window.innerHeight) {
            y = window.innerHeight - rect.height - 4;
        }
        if (x < 0) x = 4;
        if (y < 0) y = 4;

        this.el.style.left = x + 'px';
        this.el.style.top = y + 'px';

        // Add close listeners (delayed to avoid immediate close from same click)
        setTimeout(() => {
            document.addEventListener('mousedown', this._onClickOutside);
            document.addEventListener('keydown', this._onEscape);
        }, 50);

        console.log('[ContextMenu] Shown for', data.display_name, data.actions);
    }

    hide() {
        if (!this.visible) return;
        this.el.style.display = 'none';
        this.visible = false;
        this.entityId = null;

        document.removeEventListener('mousedown', this._onClickOutside);
        document.removeEventListener('keydown', this._onEscape);
    }

    _executeAction(action) {
        if (!this.entityId) return;
        console.log('[ContextMenu] Action:', action, 'on', this.entityId);
        PythonAPI.interactWith(this.entityId, action);
        this.hide();
    }

    _onClickOutside(e) {
        if (this.el && !this.el.contains(e.target)) {
            this.hide();
        }
    }

    _onEscape(e) {
        if (e.key === 'Escape') {
            this.hide();
        }
    }
}

window.ContextMenu = ContextMenu;
