/**
 * AdminPanel Component — DM/Admin control panel (F2).
 *
 * Tabs: Players, Combat, Spawn, Tools.
 * Communicates with sv_dm_panel.py via admin_action messages.
 *
 * Note: All user-facing text is escaped via _esc() (textContent-based)
 * before insertion. This is a local-only game UI, not a public web app.
 */

class AdminPanel {
    constructor() {
        this.element = null;
        this.activeTab = 'players';
        this._visible = false;
    }

    async init() {
        try {
            const response = await fetch('templates/admin-panel.html');
            const html = await response.text();

            const container = document.createElement('div');
            container.innerHTML = html;
            document.body.appendChild(container.firstElementChild);

            this.element = document.getElementById('admin-panel');
        } catch (e) {
            console.error('[AdminPanel] Failed to load template:', e);
            return;
        }

        this._bindTabs();
        this._bindActions();
        this._subscribeEvents();

        console.log('[AdminPanel] Initialized');
    }

    // ================================================================
    // Show / Hide (PanelManager interface)
    // ================================================================

    show() {
        if (!this.element) return;
        this._visible = true;
        this.element.classList.remove('hidden');
        this._requestData();
    }

    hide() {
        if (!this.element) return;
        this._visible = false;
        this.element.classList.add('hidden');
    }

    // ================================================================
    // Tabs
    // ================================================================

    _bindTabs() {
        const tabs = document.getElementById('admin-tabs');
        if (!tabs) return;

        tabs.addEventListener('click', (e) => {
            const btn = e.target.closest('.tab-btn');
            if (!btn) return;

            const tab = btn.dataset.tab;
            if (!tab) return;

            this.activeTab = tab;

            tabs.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            this.element.querySelectorAll('.panel-tab-content').forEach(c => c.classList.remove('active'));
            const content = document.getElementById(`admin-tab-${tab}`);
            if (content) content.classList.add('active');
        });
    }

    // ================================================================
    // Actions
    // ================================================================

    _bindActions() {
        const closeBtn = document.getElementById('admin-panel-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                if (window.panelManager) window.panelManager.closeActive();
            });
        }

        this._bindClick('admin-start-combat', () => this._adminAction('start_combat', { radius: 30 }));
        this._bindClick('admin-end-combat', () => this._adminAction('end_combat'));
        this._bindClick('admin-next-turn', () => this._adminAction('next_turn'));

        this._bindClick('admin-spawn-btn', () => {
            const select = document.getElementById('admin-spawn-template');
            const template = select ? select.value : 'guard';
            this._adminAction('spawn_npc', { template_id: template });
        });

        this._bindClick('admin-announce-btn', () => {
            const input = document.getElementById('admin-announce-text');
            const message = input ? input.value.trim() : '';
            if (message) {
                this._adminAction('announcement', { message });
                if (input) input.value = '';
            }
        });

        this._bindClick('admin-noclip-btn', () => {
            PythonAPI.call('noclip_request');
        });
    }

    _bindClick(id, handler) {
        const el = document.getElementById(id);
        if (el) el.addEventListener('click', handler);
    }

    _adminAction(action, extra = {}) {
        const data = JSON.stringify({ action, ...extra });
        PythonAPI.call('admin_action', { data });
    }

    // ================================================================
    // Data Requests
    // ================================================================

    _requestData() {
        this._adminAction('request_player_list');
        this._adminAction('request_combat_list');
        this._adminAction('request_npc_templates');
    }

    // ================================================================
    // Event Subscriptions
    // ================================================================

    _subscribeEvents() {
        window.addEventListener('python-message', (event) => {
            const { type, data } = event.detail;

            switch (type) {
                case 'dm_panel_player_list':
                    this._renderPlayers(data?.players || []);
                    break;
                case 'dm_panel_combat_list':
                    this._renderCombats(data?.combats || []);
                    break;
                case 'dm_panel_npc_templates':
                    this._updateTemplates(data?.templates || []);
                    break;
            }
        });
    }

    // ================================================================
    // Rendering (safe DOM construction — no raw HTML injection)
    // ================================================================

    _renderPlayers(players) {
        const list = document.getElementById('admin-player-list');
        if (!list) return;
        list.textContent = '';

        if (players.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'admin-empty';
            empty.textContent = 'No players connected';
            list.appendChild(empty);
            return;
        }

        players.forEach(p => {
            const entry = document.createElement('div');
            entry.className = 'admin-player-entry';

            const info = document.createElement('div');
            info.className = 'admin-player-info';

            const name = document.createElement('span');
            name.className = 'admin-player-name';
            name.textContent = p.name || '?';

            const detail = document.createElement('span');
            detail.className = 'admin-player-detail';
            detail.textContent = `${p.class || '?'} Lv${p.level || 1}`;

            const hp = document.createElement('span');
            hp.className = 'admin-player-hp';
            hp.textContent = `HP: ${p.hp_current || 0}/${p.hp_max || 0}`;

            info.appendChild(name);
            info.appendChild(detail);
            info.appendChild(hp);

            const actions = document.createElement('div');
            actions.className = 'admin-player-actions';

            const makeBtn = (label, cls, action, amount) => {
                const btn = document.createElement('button');
                btn.className = `btn btn-xs${cls ? ' ' + cls : ''}`;
                btn.textContent = label;
                btn.addEventListener('click', () => this._playerAction(p.id, action, amount));
                return btn;
            };

            actions.appendChild(makeBtn('+10 HP', '', 'heal', 10));
            actions.appendChild(makeBtn('-10 HP', 'btn-danger', 'damage', 10));
            actions.appendChild(makeBtn('Full Heal', '', 'heal', 9999));
            actions.appendChild(makeBtn('Kill', 'btn-danger', 'kill', 0));

            entry.appendChild(info);
            entry.appendChild(actions);
            list.appendChild(entry);
        });
    }

    _renderCombats(combats) {
        const list = document.getElementById('admin-combat-list');
        if (!list) return;
        list.textContent = '';

        if (combats.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'admin-empty';
            empty.textContent = 'No active combats';
            list.appendChild(empty);
            return;
        }

        combats.forEach(c => {
            const entry = document.createElement('div');
            entry.className = 'admin-combat-entry';

            const id = document.createElement('span');
            id.textContent = `Combat #${(c.id || '?').substring(0, 8)}`;

            const round = document.createElement('span');
            round.textContent = `Round ${c.round || 1}`;

            const count = document.createElement('span');
            count.textContent = `${c.participants_count || 0} participants`;

            entry.appendChild(id);
            entry.appendChild(round);
            entry.appendChild(count);
            list.appendChild(entry);
        });
    }

    _updateTemplates(templates) {
        const select = document.getElementById('admin-spawn-template');
        if (!select) return;
        select.textContent = '';

        templates.forEach(t => {
            const option = document.createElement('option');
            option.value = t;
            option.textContent = t;
            select.appendChild(option);
        });
    }

    // ================================================================
    // Player Actions
    // ================================================================

    _playerAction(playerId, action, amount = 0) {
        this._adminAction('player_action', {
            player_action: action,
            player_id: playerId,
            amount: amount,
        });
        setTimeout(() => this._adminAction('request_player_list'), 300);
    }

    destroy() {
        if (this.element) {
            this.element.remove();
            this.element = null;
        }
    }
}

window.AdminPanel = AdminPanel;
