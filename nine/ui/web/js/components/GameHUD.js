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
        if (levelEl) levelEl.textContent = `Lv ${level}`;
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

        const combatEl = document.getElementById('hud-combat');
        const initEl = document.getElementById('hud-initiative');
        if (combatEl) combatEl.classList.remove('hidden');
        if (initEl) initEl.classList.remove('hidden');

        // Update initiative list
        if (data && data.participants) {
            this.updateInitiativeList(data.participants, data.turn_order);
        }

        const roundEl = document.getElementById('hud-round');
        if (roundEl) roundEl.textContent = `Round ${data?.round || 1}`;
    }

    hideCombat() {
        this.inCombat = false;
        this.isMyTurn = false;

        const combatEl = document.getElementById('hud-combat');
        const initEl = document.getElementById('hud-initiative');
        if (combatEl) combatEl.classList.add('hidden');
        if (initEl) initEl.classList.add('hidden');
    }

    onTurnStart(data) {
        this.isMyTurn = data.is_player || false;
        const entityId = data.entity_id || '';
        const round = data.round || 1;

        const turnEl = document.getElementById('hud-turn');
        const roundEl = document.getElementById('hud-round');

        if (roundEl) roundEl.textContent = `Round ${round}`;

        if (turnEl) {
            if (this.isMyTurn) {
                turnEl.textContent = 'YOUR TURN!';
                turnEl.className = 'hud-turn your-turn';
            } else {
                turnEl.textContent = `Turn: ${entityId.substring(0, 8)}...`;
                turnEl.className = 'hud-turn';
            }
        }

        // Highlight in initiative list
        this._highlightInitiative(entityId);

        // Enable/disable action buttons
        this._setActionButtonsEnabled(this.isMyTurn);
    }

    onRoundStart(data) {
        const round = data.round || 1;
        const roundEl = document.getElementById('hud-round');
        if (roundEl) roundEl.textContent = `Round ${round}`;
    }

    onActionResult(data) {
        const result = data.result || {};
        const resultEl = document.getElementById('hud-action-result');
        if (!resultEl) return;

        let text = '';
        let className = 'hud-action-result';

        if (!result.success) {
            text = result.error || 'Action failed';
            className += ' result-fail';
        } else {
            const action = result.action || data.action_id || '';
            if (action === 'attack') {
                if (result.is_critical) {
                    text = `CRITICAL HIT! ${result.damage || 0} damage!`;
                    className += ' result-crit';
                } else if (result.hit) {
                    text = `Hit! ${result.damage || 0} damage`;
                    className += ' result-hit';
                } else {
                    text = 'Miss!';
                    className += ' result-miss';
                }
            } else if (action === 'end_turn') {
                text = 'Turn ended';
                className += ' result-info';
            } else {
                text = `${action} used`;
                className += ' result-info';
            }
        }

        resultEl.textContent = text;
        resultEl.className = className;

        // Auto-hide after 3 seconds
        if (this._resultTimeout) clearTimeout(this._resultTimeout);
        this._resultTimeout = setTimeout(() => {
            resultEl.classList.add('hidden');
        }, 3000);
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
                <span class="init-order">${p.initiative || 0}</span>
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
                PythonAPI.combatAction(action, '');
            });
        });
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
        if (this.element) {
            this.element.remove();
            this.element = null;
        }
        if (this._resultTimeout) {
            clearTimeout(this._resultTimeout);
        }
    }
}
