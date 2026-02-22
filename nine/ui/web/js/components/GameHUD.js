/**
 * GameHUD Component - Persistent in-game HUD overlay.
 *
 * Sections:
 *  1. Stats bar (top-left): HP, AC, level
 *  2. Conditions (below stats)
 *  3. Combat panel (bottom-center, combat only): action bar, turn info
 *  4. Initiative tracker (right side, combat only)
 */

class GameHUD {
    constructor() {
        this.element = null;
        this.inCombat = false;
        this.isMyTurn = false;
        this._resultTimeout = null;
        this._combatStartOverlay = null;
        this._combatCountdownInterval = null;

        // Participants cache (from combat_started) for name lookups
        this._participants = {};

        // Combat resources
        this._resources = { action: true, bonus: true, reaction: true };
        this._movementCurrent = 30;
        this._movementMax = 30;
    }

    async init() {
        // Load template
        try {
            const response = await fetch('templates/game-hud.html');
            const html = await response.text();

            // Insert into body (persistent, not in #app)
            const container = document.createElement('div');
            container.innerHTML = html;
            document.body.appendChild(container.firstElementChild);

            this.element = document.getElementById('game-hud');
        } catch (e) {
            console.error('[GameHUD] Failed to load template:', e);
            return;
        }

        // Bind action buttons
        this._bindActionButtons();

        // Bind keyboard hotkeys for combat
        this._bindCombatHotkeys();

        // Listen for Python events
        this._subscribeEvents();

        console.log('[GameHUD] Initialized');
    }

    // ================================================================
    // Visibility
    // ================================================================

    show() {
        if (this.element) {
            this.element.classList.remove('hidden');
        }
    }

    hide() {
        if (this.element) {
            this.element.classList.add('hidden');
        }
        this.hideCombat();
    }

    // ================================================================
    // Stats
    // ================================================================

    updateStats(character) {
        if (!character) return;

        const name = character.name || '---';
        const stats = character.stats || {};
        const currentHp = stats.current_hp || 0;
        const maxHp = stats.max_hp || 1;
        const tempHp = stats.temp_hp || 0;
        const ac = stats.armor_class || 10;
        const level = stats.level || 1;

        const nameEl = document.getElementById('hud-char-name');
        const hpFill = document.getElementById('hud-hp-fill');
        const hpText = document.getElementById('hud-hp-text');
        const acEl = document.getElementById('hud-ac');
        const levelEl = document.getElementById('hud-level');

        if (nameEl) nameEl.textContent = name;

        if (hpFill) {
            const ratio = Math.max(0, Math.min(1, currentHp / maxHp)) * 100;
            hpFill.style.width = ratio + '%';

            // Color based on HP ratio
            if (ratio > 50) {
                hpFill.className = 'hud-hp-fill hp-high';
            } else if (ratio > 25) {
                hpFill.className = 'hud-hp-fill hp-mid';
            } else {
                hpFill.className = 'hud-hp-fill hp-low';
            }
        }

        if (hpText) {
            let text = `HP: ${currentHp}/${maxHp}`;
            if (tempHp > 0) text += ` (+${tempHp})`;
            hpText.textContent = text;
        }

        if (acEl) acEl.textContent = `AC: ${ac}`;
        if (levelEl) levelEl.textContent = `Ур ${level}`;
    }

    // ================================================================
    // Conditions
    // ================================================================

    updateConditions(conditions) {
        const container = document.getElementById('hud-conditions');
        if (!container) return;

        container.innerHTML = '';

        if (!conditions || conditions.length === 0) return;

        conditions.forEach(cond => {
            const el = document.createElement('span');
            el.className = 'hud-condition-badge';
            const name = cond.name_ru || cond.name || cond.id || '?';
            const duration = cond.duration;
            el.textContent = duration > 0 ? `${name} (${duration})` : name;
            container.appendChild(el);
        });
    }

    // ================================================================
    // Combat
    // ================================================================

    showCombat(data) {
        this.inCombat = true;

        // Cache participants for name lookups
        if (data && data.participants) {
            this._participants = {};
            data.participants.forEach(p => {
                this._participants[p.entity_id] = p;
            });
        }

        const combatEl = document.getElementById('hud-combat');
        const initEl = document.getElementById('hud-initiative');
        if (combatEl) combatEl.classList.remove('hidden');
        if (initEl) initEl.classList.remove('hidden');

        // Update initiative list
        if (data && data.participants) {
            this.updateInitiativeList(data.participants, data.turn_order);
        }

        const roundEl = document.getElementById('hud-round');
        if (roundEl) roundEl.textContent = `Раунд ${data?.round || 1}`;

        // Show "НАЧАЛО БОЯ" overlay with countdown
        this._showCombatStartOverlay();
    }

    hideCombat() {
        this.inCombat = false;
        this.isMyTurn = false;
        this._participants = {};

        const combatEl = document.getElementById('hud-combat');
        const initEl = document.getElementById('hud-initiative');
        if (combatEl) combatEl.classList.add('hidden');
        if (initEl) initEl.classList.add('hidden');

        // Hide movement bar
        const moveSection = document.getElementById('hud-movement-section');
        if (moveSection) moveSection.style.display = 'none';

        // Remove combat start overlay if still showing
        this._removeCombatStartOverlay();
    }

    _getParticipantName(entityId) {
        const p = this._participants[entityId];
        if (p && p.name) return p.name;
        return '???';
    }

    _showCombatStartOverlay() {
        this._removeCombatStartOverlay();

        const overlay = document.createElement('div');
        overlay.id = 'combat-start-overlay';
        overlay.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            background: rgba(0, 0, 0, 0.6); z-index: 9999;
            pointer-events: none; animation: fadeIn 0.3s ease;
        `;

        const title = document.createElement('div');
        title.textContent = 'НАЧАЛО БОЯ';
        title.style.cssText = `
            font-family: 'Cinzel', serif; font-size: 64px; font-weight: bold;
            color: #ff4444; text-shadow: 0 0 20px rgba(255, 68, 68, 0.8),
            0 0 40px rgba(255, 68, 68, 0.4); letter-spacing: 8px;
        `;

        const countdown = document.createElement('div');
        countdown.id = 'combat-countdown';
        countdown.style.cssText = `
            font-family: 'Cinzel', serif; font-size: 48px; font-weight: bold;
            color: #ffcc00; margin-top: 20px;
            text-shadow: 0 0 15px rgba(255, 204, 0, 0.6);
        `;
        countdown.textContent = '3';

        overlay.appendChild(title);
        overlay.appendChild(countdown);
        document.body.appendChild(overlay);
        this._combatStartOverlay = overlay;

        let count = 3;
        this._combatCountdownInterval = setInterval(() => {
            count--;
            if (count > 0) {
                countdown.textContent = String(count);
            } else {
                this._removeCombatStartOverlay();
            }
        }, 1000);
    }

    _removeCombatStartOverlay() {
        if (this._combatCountdownInterval) {
            clearInterval(this._combatCountdownInterval);
            this._combatCountdownInterval = null;
        }
        if (this._combatStartOverlay) {
            this._combatStartOverlay.remove();
            this._combatStartOverlay = null;
        }
    }

    onTurnStart(data) {
        // Use is_your_turn (set by webview_api) instead of is_player
        this.isMyTurn = data.is_your_turn || false;
        const entityId = data.entity_id || '';
        const entityName = data.entity_name || this._getParticipantName(entityId);
        const round = data.round || 1;

        const turnEl = document.getElementById('hud-turn');
        const roundEl = document.getElementById('hud-round');

        if (roundEl) roundEl.textContent = `Раунд ${round}`;

        if (turnEl) {
            if (this.isMyTurn) {
                turnEl.textContent = 'ВАШ ХОД!';
                turnEl.className = 'hud-turn your-turn';
            } else {
                turnEl.textContent = `Ход: ${entityName}`;
                turnEl.className = 'hud-turn';
            }
        }

        // Highlight in initiative list
        this._highlightInitiative(entityId);

        // Enable/disable action buttons
        this._setActionButtonsEnabled(this.isMyTurn);

        // Reset resources on turn start
        if (this.isMyTurn) {
            const resources = data.resources || {};
            this._resources = {
                action: resources.has_action !== undefined ? resources.has_action : true,
                bonus: resources.has_bonus_action !== undefined ? resources.has_bonus_action : true,
                reaction: resources.has_reaction !== undefined ? resources.has_reaction : true,
            };
            this._movementMax = resources.movement_max || resources.movement || 30;
            this._movementCurrent = resources.movement || this._movementMax;
            this._updateResources();
            this._updateMovement();
        }
    }

    onRoundStart(data) {
        const round = data.round || 1;
        const roundEl = document.getElementById('hud-round');
        if (roundEl) roundEl.textContent = `Раунд ${round}`;
    }

    onActionResult(data) {
        const result = data.result || {};
        const resultEl = document.getElementById('hud-action-result');
        if (!resultEl) return;

        let text = '';
        let className = 'hud-action-result';

        if (!result.success) {
            text = result.error || 'Действие не удалось';
            className += ' result-fail';
        } else {
            const action = result.action || data.action_id || '';
            if (action === 'attack') {
                if (result.is_critical) {
                    text = `КРИТИЧЕСКИЙ УДАР! ${result.damage || 0} урона!`;
                    className += ' result-crit';
                } else if (result.hit) {
                    text = `Попадание! ${result.damage || 0} урона`;
                    className += ' result-hit';
                } else {
                    text = 'Промах!';
                    className += ' result-miss';
                }
            } else if (action === 'end_turn') {
                text = 'Ход окончен';
                className += ' result-info';
            } else {
                text = `${action} использовано`;
                className += ' result-info';
            }
        }

        resultEl.textContent = text;
        resultEl.className = className;

        // Update resources after action
        if (result.resources) {
            if (result.resources.action !== undefined) this._resources.action = result.resources.action;
            if (result.resources.bonus !== undefined) this._resources.bonus = result.resources.bonus;
            if (result.resources.reaction !== undefined) this._resources.reaction = result.resources.reaction;
            if (result.resources.movement_remaining !== undefined) this._movementCurrent = result.resources.movement_remaining;
            this._updateResources();
            this._updateMovement();
        }

        // Update initiative tracker HP if attack result has target HP data
        if (result.action === 'attack' || data.action_id === 'attack') {
            const targetId = result.target_id || data.target_id;
            if (targetId && result.target_hp_current !== undefined) {
                this._updateInitiativeHP(targetId, result.target_hp_current, result.target_hp_max, result.target_is_dead);
            }
        }

        // Auto-hide after 3 seconds
        if (this._resultTimeout) clearTimeout(this._resultTimeout);
        this._resultTimeout = setTimeout(() => {
            resultEl.classList.add('hidden');
        }, 3000);
    }

    // ================================================================
    // Combat Resources & Movement
    // ================================================================

    _updateResources() {
        const actionEl = document.getElementById('hud-res-action');
        const bonusEl = document.getElementById('hud-res-bonus');
        const reactionEl = document.getElementById('hud-res-reaction');

        if (actionEl) {
            actionEl.className = `hud-resource ${this._resources.action ? 'resource-available' : 'resource-spent'}`;
        }
        if (bonusEl) {
            bonusEl.className = `hud-resource ${this._resources.bonus ? 'resource-available' : 'resource-spent'}`;
        }
        if (reactionEl) {
            reactionEl.className = `hud-resource ${this._resources.reaction ? 'resource-available' : 'resource-spent'}`;
        }
    }

    _updateMovement() {
        const section = document.getElementById('hud-movement-section');
        const fill = document.getElementById('hud-movement-fill');
        const text = document.getElementById('hud-movement-text');

        if (section) {
            section.style.display = this.inCombat && this.isMyTurn ? '' : 'none';
        }

        if (fill && this._movementMax > 0) {
            const ratio = Math.max(0, Math.min(1, this._movementCurrent / this._movementMax)) * 100;
            fill.style.width = ratio + '%';
        }

        if (text) {
            text.textContent = `${Math.floor(this._movementCurrent)}/${Math.floor(this._movementMax)} фт`;
        }
    }

    // ================================================================
    // Initiative Tracker
    // ================================================================

    updateInitiativeList(participants, turnOrder) {
        const listEl = document.getElementById('hud-initiative-list');
        if (!listEl) return;

        listEl.innerHTML = '';

        const order = turnOrder || participants.map(p => p.entity_id);

        order.forEach(entityId => {
            const p = participants.find(x => x.entity_id === entityId);
            if (!p) return;

            const el = document.createElement('div');
            el.className = 'hud-init-entry';
            el.dataset.entityId = entityId;

            if (p.is_player) el.classList.add('init-player');
            if (p.is_dead) el.classList.add('init-dead');

            const hpRatio = p.hp_max > 0 ? (p.hp_current / p.hp_max) : 0;

            el.innerHTML = `
                <span class="init-order">${Math.floor(p.initiative || 0)}</span>
                <span class="init-name">${(p.name || '???').substring(0, 12)}</span>
                <div class="init-hp-bar">
                    <div class="init-hp-fill" style="width:${hpRatio * 100}%"></div>
                </div>
                <span class="init-hp-text">${p.is_dead ? 'X' : `${p.hp_current}/${p.hp_max}`}</span>
            `;

            listEl.appendChild(el);
        });
    }

    _highlightInitiative(entityId) {
        const entries = document.querySelectorAll('.hud-init-entry');
        entries.forEach(el => {
            if (el.dataset.entityId === entityId) {
                el.classList.add('init-active');
            } else {
                el.classList.remove('init-active');
            }
        });
    }

    _updateInitiativeHP(entityId, hpCurrent, hpMax, isDead) {
        const entry = document.querySelector(`.hud-init-entry[data-entity-id="${entityId}"]`);
        if (!entry) return;

        if (isDead) {
            entry.classList.add('init-dead');
        }

        const hpFill = entry.querySelector('.init-hp-fill');
        const hpText = entry.querySelector('.init-hp-text');

        if (hpFill && hpMax > 0) {
            const ratio = Math.max(0, Math.min(1, hpCurrent / hpMax)) * 100;
            hpFill.style.width = ratio + '%';
        }

        if (hpText) {
            hpText.textContent = isDead ? 'X' : `${hpCurrent}/${hpMax}`;
        }
    }

    // ================================================================
    // Action Buttons
    // ================================================================

    _bindActionButtons() {
        const bar = document.getElementById('hud-action-bar');
        if (!bar) return;

        bar.querySelectorAll('.hud-action-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (!this.isMyTurn) return;
                const action = btn.dataset.action;
                console.log('[GameHUD] Action clicked:', action);
                if (action === 'spell') {
                    if (window.panelManager) window.panelManager.toggle('spellbook');
                } else if (action === 'item') {
                    if (window.panelManager) window.panelManager.open('character-sheet', { tab: 'inventory' });
                } else {
                    PythonAPI.combatAction(action, '');
                }
            });
        });

        // Cancel combat button
        const cancelBtn = document.getElementById('hud-cancel-combat');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                if (!this.inCombat) return;
                PythonAPI.getApi().vote_cancel_combat();
            });
        }
    }

    _setActionButtonsEnabled(enabled) {
        const bar = document.getElementById('hud-action-bar');
        if (!bar) return;

        bar.querySelectorAll('.hud-action-btn').forEach(btn => {
            btn.disabled = !enabled;
            if (enabled) {
                btn.classList.remove('btn-disabled');
            } else {
                btn.classList.add('btn-disabled');
            }
        });
    }

    // ================================================================
    // Combat Hotkeys
    // ================================================================

    _bindCombatHotkeys() {
        document.addEventListener('keydown', (e) => {
            // Only when in combat and it's our turn
            if (!this.inCombat || !this.isMyTurn) return;

            // Skip when typing
            const tag = document.activeElement?.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

            // Skip if panel is open
            if (window.panelManager && window.panelManager.isAnyOpen()) return;

            // Skip modifiers
            if (e.ctrlKey || e.altKey || e.metaKey) return;

            const keyMap = {
                '1': 'attack',
                '2': 'dash',
                '3': 'dodge',
                '4': 'item',
                'e': 'end_turn'
            };

            const action = keyMap[e.key.toLowerCase()];
            if (action) {
                if (action === 'spell') {
                    if (window.panelManager) window.panelManager.toggle('spellbook');
                } else if (action === 'item') {
                    if (window.panelManager) window.panelManager.open('character-sheet', { tab: 'inventory' });
                } else {
                    PythonAPI.combatAction(action, '');
                }
                e.preventDefault();
                e.stopPropagation();
            }
        });
    }

    /**
     * Handle combat hotkey from Python (CEF can't reliably produce event.key).
     */
    _onCombatHotkey(data) {
        if (!this.inCombat || !this.isMyTurn) return;

        const keyMap = {
            '1': 'attack',
            '2': 'dash',
            '3': 'dodge',
            '4': 'item',
            'e': 'end_turn'
        };

        const action = keyMap[data?.key];
        if (action) {
            console.log('[GameHUD] Combat hotkey:', action);
            if (action === 'spell') {
                if (window.panelManager) window.panelManager.toggle('spellbook');
            } else if (action === 'item') {
                if (window.panelManager) window.panelManager.open('character-sheet', { tab: 'inventory' });
            } else {
                PythonAPI.combatAction(action, '');
            }
        }
    }

    // ================================================================
    // Event Subscriptions
    // ================================================================

    _subscribeEvents() {
        window.addEventListener('python-message', (event) => {
            const { type, data } = event.detail;

            switch (type) {
                case 'character_sheet':
                    this.updateStats(data?.character);
                    break;
                case 'conditions_update':
                    this.updateConditions(data?.conditions);
                    break;
                case 'combat_started':
                    this.showCombat(data);
                    break;
                case 'combat_ended':
                    this.hideCombat();
                    break;
                case 'combat_turn_start':
                    this.onTurnStart(data);
                    break;
                case 'combat_round_start':
                    this.onRoundStart(data);
                    break;
                case 'combat_action_result':
                    this.onActionResult(data);
                    break;
                case 'game_state_changed':
                    this._onGameStateChanged(data);
                    break;
                case 'combat_hotkey':
                    this._onCombatHotkey(data);
                    break;
                case 'navigate':
                    // Show HUD when entering game (hidden screen), hide in menus
                    if (data?.screen === 'hidden') {
                        this.show();
                    } else {
                        this.hide();
                    }
                    break;
            }
        });
    }

    _onGameStateChanged(data) {
        const newState = data?.new_state;
        if (newState === 'MENU' || newState === 0) {
            this.hide();
        }
    }

    // ================================================================
    // Cleanup
    // ================================================================

    destroy() {
        this._removeCombatStartOverlay();
        if (this.element) {
            this.element.remove();
            this.element = null;
        }
        if (this._resultTimeout) {
            clearTimeout(this._resultTimeout);
        }
    }
}
