/**
 * AdminPanel - SAM-style admin panel with 4 tabs.
 *
 * Tabs: Players, Combat, World, Bans
 * Toggled by F2 (Python-side key handler).
 */

class AdminPanel {
    constructor() {
        this.element = null;
        this.activeTab = 'players';
        this.noclipEnabled = false;

        // Cached data
        this._players = [];
        this._combats = [];
        this._npcTemplates = [];
        this._bannedIps = [];

        // D&D conditions list
        this.CONDITIONS = [
            'blinded', 'charmed', 'deafened', 'frightened', 'grappled',
            'incapacitated', 'invisible', 'paralyzed', 'petrified',
            'poisoned', 'prone', 'restrained', 'stunned', 'unconscious',
            'exhaustion'
        ];
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
        this._bindClose();
        this._bindControls();
        this._subscribeEvents();

        console.log('[AdminPanel] Initialized');
    }

    // ================================================================
    // Show / Hide
    // ================================================================

    show() {
        if (!this.element) return;
        this.element.classList.remove('hidden');
        // Request data from server
        this._requestData();
    }

    hide() {
        if (!this.element) return;
        this.element.classList.add('hidden');
    }

    // ================================================================
    // Tabs
    // ================================================================

    _bindTabs() {
        const tabsContainer = document.getElementById('admin-tabs');
        if (!tabsContainer) return;

        tabsContainer.querySelectorAll('.panel-tab').forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                if (tab) this._switchTab(tab);
            });
        });
    }

    _switchTab(tab) {
        this.activeTab = tab;

        // Update tab buttons
        document.querySelectorAll('#admin-tabs .panel-tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });

        // Update tab content
        document.querySelectorAll('#admin-body .panel-tab-content').forEach(content => {
            content.classList.toggle('active', content.dataset.tab === tab);
        });

        // Request relevant data
        if (tab === 'bans') {
            this._adminAction('request_ban_list');
        }
    }

    _bindClose() {
        const closeBtn = document.getElementById('admin-panel-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.hide();
                if (window.panelManager) {
                    window.panelManager.closeActive();
                }
            });
        }
    }

    // ================================================================
    // Controls
    // ================================================================

    _bindControls() {
        // Combat controls
        const endCombat = document.getElementById('admin-end-combat');
        if (endCombat) {
            endCombat.addEventListener('click', () => this._adminAction('end_combat'));
        }

        const nextTurn = document.getElementById('admin-next-turn');
        if (nextTurn) {
            nextTurn.addEventListener('click', () => this._adminAction('next_turn'));
        }

        // Spawn NPC
        const spawnBtn = document.getElementById('admin-spawn-npc');
        if (spawnBtn) {
            spawnBtn.addEventListener('click', () => {
                const template = document.getElementById('admin-npc-template')?.value || 'guard';
                const x = parseFloat(document.getElementById('admin-spawn-x')?.value || '0');
                const y = parseFloat(document.getElementById('admin-spawn-y')?.value || '0');
                this._adminAction('spawn_npc', { template_id: template, position: [x, y, 1] });
            });
        }

        // Announcement
        const sendAnnouncement = document.getElementById('admin-send-announcement');
        if (sendAnnouncement) {
            sendAnnouncement.addEventListener('click', () => {
                const input = document.getElementById('admin-announcement-text');
                const msg = input?.value?.trim();
                if (msg) {
                    this._adminAction('announcement', { message: msg });
                    if (input) input.value = '';
                }
            });
        }

        // Noclip toggle
        const noclipBtn = document.getElementById('admin-noclip-toggle');
        if (noclipBtn) {
            noclipBtn.addEventListener('click', () => {
                if (window.pyapi) window.pyapi.noclip_request();
            });
        }

        // Ban IP
        const banIpBtn = document.getElementById('admin-ban-ip-btn');
        if (banIpBtn) {
            banIpBtn.addEventListener('click', () => {
                const input = document.getElementById('admin-ban-ip-input');
                const ip = input?.value?.trim();
                if (ip) {
                    this._adminAction('ban_ip', { ip });
                    if (input) input.value = '';
                }
            });
        }
    }

    // ================================================================
    // Data Requests
    // ================================================================

    _requestData() {
        this._adminAction('request_player_list');
        this._adminAction('request_combat_list');
        this._adminAction('request_npc_templates');
    }

    _adminAction(action, params) {
        if (window.pyapi) {
            window.pyapi.admin_action(JSON.stringify({
                action: action,
                ...(params || {})
            }));
        }
    }

    // ================================================================
    // Event Subscriptions
    // ================================================================

    _subscribeEvents() {
        window.addEventListener('python-message', (event) => {
            const { type, data } = event.detail || {};

            switch (type) {
                case 'dm_panel_player_list':
                    this._players = data?.players || [];
                    this._renderPlayers();
                    break;
                case 'dm_panel_combat_list':
                    this._combats = data?.combats || [];
                    this._renderCombats();
                    break;
                case 'dm_panel_npc_templates':
                    this._npcTemplates = data?.templates || [];
                    this._renderTemplateDropdown();
                    break;
                case 'admin_panel_ban_list':
                    this._bannedIps = data?.banned_ips || [];
                    this._renderBanList();
                    break;
                case 'noclip_toggled':
                    this.noclipEnabled = !!data?.enabled;
                    this._updateNoclipButton();
                    break;
            }
        });
    }

    // ================================================================
    // Renderers
    // ================================================================

    _renderPlayers() {
        const container = document.getElementById('admin-player-list');
        if (!container) return;

        if (!this._players.length) {
            container.innerHTML = '<div class="admin-empty-message">No players connected</div>';
            return;
        }

        container.innerHTML = this._players.map(p => this._renderPlayerRow(p)).join('');

        // Bind action buttons
        container.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                const playerId = parseInt(btn.dataset.playerId);
                const amount = parseInt(btn.dataset.amount || '0');
                const condition = btn.dataset.condition || '';

                this._adminAction('player_action', {
                    player_action: action, player_id: playerId, amount, condition
                });
            });
        });

        // Bind condition apply/remove
        container.querySelectorAll('.admin-condition-apply').forEach(btn => {
            btn.addEventListener('click', () => {
                const playerId = parseInt(btn.dataset.playerId);
                const select = container.querySelector(`#admin-condition-select-${playerId}`);
                const condition = select?.value;
                if (condition) {
                    this._adminAction('player_action', {
                        player_action: 'apply_condition', player_id: playerId, condition
                    });
                }
            });
        });

        container.querySelectorAll('.admin-condition-remove').forEach(btn => {
            btn.addEventListener('click', () => {
                const playerId = parseInt(btn.dataset.playerId);
                const select = container.querySelector(`#admin-condition-select-${playerId}`);
                const condition = select?.value;
                if (condition) {
                    this._adminAction('player_action', {
                        player_action: 'remove_condition', player_id: playerId, condition
                    });
                }
            });
        });

        // Replace native <select> with custom dropdowns (CEF offscreen fix)
        if (window.initCustomSelects) initCustomSelects(container);

        // Bind custom HP input
        container.querySelectorAll('.admin-hp-set-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const playerId = parseInt(btn.dataset.playerId);
                const input = container.querySelector(`#admin-hp-input-${playerId}`);
                const value = parseInt(input?.value || '0');
                if (!isNaN(value)) {
                    this._adminAction('player_action', {
                        player_action: 'set_hp', player_id: playerId, amount: value
                    });
                }
            });
        });
    }

    _renderPlayerRow(player) {
        const { id, name, ip } = player;
        const cls = player['class'] || '?';
        const level = player.level || 1;
        const hp = player.hp_current || 0;
        const hpMax = player.hp_max || 1;
        const pct = Math.round((hp / hpMax) * 100);
        const hpClass = pct > 50 ? 'hp-high' : pct > 25 ? 'hp-mid' : 'hp-low';

        const condOptions = this.CONDITIONS.map(c =>
            `<option value="${c}">${c}</option>`
        ).join('');

        return `
        <div class="admin-player-row">
            <div class="admin-player-info">
                <span class="admin-player-name">${name}</span>
                <span class="admin-player-meta">${cls} Lv.${level}</span>
                <span class="admin-player-ip">${ip || ''}</span>
            </div>
            <div class="admin-hp-bar">
                <div class="admin-hp-fill ${hpClass}" style="width:${pct}%"></div>
                <span class="admin-hp-text">${hp}/${hpMax}</span>
            </div>
            <div class="admin-player-actions">
                <button class="admin-action-btn admin-btn-green" data-action="heal" data-player-id="${id}" data-amount="10">+10</button>
                <button class="admin-action-btn admin-btn-green" data-action="heal" data-player-id="${id}" data-amount="50">+50</button>
                <button class="admin-action-btn admin-btn-green" data-action="heal" data-player-id="${id}" data-amount="9999">Full</button>
                <button class="admin-action-btn admin-btn-red" data-action="damage" data-player-id="${id}" data-amount="10">-10</button>
                <button class="admin-action-btn admin-btn-red" data-action="damage" data-player-id="${id}" data-amount="50">-50</button>
                <button class="admin-action-btn admin-btn-darkred" data-action="kill" data-player-id="${id}">Kill</button>
                <button class="admin-action-btn" data-action="teleport_to" data-player-id="${id}">TP</button>
            </div>
            <div class="admin-player-actions" style="margin-top:4px;">
                <input type="number" id="admin-hp-input-${id}" class="bg1-input admin-hp-input" value="${hp}" style="width:60px;">
                <button class="admin-action-btn admin-hp-set-btn" data-player-id="${id}">Set HP</button>
                <select id="admin-condition-select-${id}" class="bg1-input" style="width:110px;font-size:11px;">${condOptions}</select>
                <button class="admin-action-btn admin-btn-green admin-condition-apply" data-player-id="${id}">Apply</button>
                <button class="admin-action-btn admin-btn-red admin-condition-remove" data-player-id="${id}">Remove</button>
                <button class="admin-action-btn admin-btn-orange" data-action="kick" data-player-id="${id}">Kick</button>
                <button class="admin-action-btn admin-btn-darkred" data-action="ban" data-player-id="${id}">Ban</button>
            </div>
        </div>`;
    }

    _renderCombats() {
        const container = document.getElementById('admin-combat-list');
        if (!container) return;

        if (!this._combats.length) {
            container.innerHTML = '<div class="admin-empty-message">No active combats</div>';
            return;
        }

        container.innerHTML = this._combats.map(c => `
            <div class="admin-combat-row">
                <span>Combat #${(c.id || '').substring(0, 8)}...</span>
                <span>Round ${c.round || 1}</span>
                <span>${c.participants_count || 0} participants</span>
            </div>
        `).join('');
    }

    _renderTemplateDropdown() {
        const select = document.getElementById('admin-npc-template');
        if (!select) return;

        const templates = this._npcTemplates.length ? this._npcTemplates
            : ['guard', 'goblin', 'merchant', 'skeleton'];

        select.innerHTML = templates.map(t =>
            `<option value="${t}">${t}</option>`
        ).join('');

        // Replace native <select> with custom dropdown (CEF offscreen fix)
        if (window.initCustomSelects) initCustomSelects(select.parentElement);
    }

    _renderBanList() {
        const container = document.getElementById('admin-ban-list');
        if (!container) return;

        if (!this._bannedIps.length) {
            container.innerHTML = '<div class="admin-empty-message">No banned IPs</div>';
            return;
        }

        container.innerHTML = this._bannedIps.map(ip => `
            <div class="admin-ban-row">
                <span class="admin-ban-ip">${ip}</span>
                <button class="admin-action-btn admin-btn-green admin-unban-btn" data-ip="${ip}">Unban</button>
            </div>
        `).join('');

        // Bind unban buttons
        container.querySelectorAll('.admin-unban-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._adminAction('unban_ip', { ip: btn.dataset.ip });
            });
        });
    }

    _updateNoclipButton() {
        const btn = document.getElementById('admin-noclip-toggle');
        if (btn) {
            btn.textContent = `Noclip: ${this.noclipEnabled ? 'ON' : 'OFF'}`;
            btn.classList.toggle('admin-btn-green', this.noclipEnabled);
        }
    }
}
