/**
 * RestDialog - Modal overlay for short/long rest.
 *
 * Triggered by server event (show_rest_dialog), NOT managed by PanelManager.
 * Shows HP status, hit dice, and rest actions.
 *
 * Data sources: show_rest_dialog, rest_result, hit_die_result, character_sheet
 */

class RestDialog {
    constructor() {
        this.element = null;
        this.restType = null; // 'short' or 'long'

        // Cached character stats
        this._hpCurrent = 0;
        this._hpMax = 1;
        this._hitDiceCurrent = 0;
        this._hitDiceMax = 0;
    }

    async init() {
        try {
            const response = await fetch('templates/rest-dialog.html');
            const html = await response.text();

            const container = document.createElement('div');
            container.innerHTML = html;
            document.body.appendChild(container.firstElementChild);

            this.element = document.getElementById('rest-dialog');
        } catch (e) {
            console.error('[RestDialog] Failed to load template:', e);
            return;
        }

        this._bindButtons();
        this._subscribeEvents();

        console.log('[RestDialog] Initialized');
    }

    // ================================================================
    // Show / Hide
    // ================================================================

    show(restType) {
        if (!this.element) return;
        this.restType = restType;

        // Set title
        const titleEl = document.getElementById('rest-title');
        if (titleEl) {
            titleEl.textContent = restType === 'short' ? 'Короткий отдых' : 'Длинный отдых';
        }

        // Set description
        const descEl = document.getElementById('rest-description');
        if (descEl) {
            if (restType === 'short') {
                descEl.textContent = 'Вы можете потратить кости хитов для восстановления здоровья. Короткий отдых длится минимум 1 час.';
            } else {
                descEl.textContent = 'Длинный отдых восстанавливает все очки здоровья и половину максимума костей хитов. Длится минимум 8 часов.';
            }
        }

        // Show/hide spend hit die button (short rest only)
        const spendBtn = document.getElementById('rest-spend-hitdie');
        if (spendBtn) {
            spendBtn.style.display = restType === 'short' ? '' : 'none';
        }

        // Clear result
        const resultEl = document.getElementById('rest-result');
        if (resultEl) {
            resultEl.classList.add('hidden');
            resultEl.textContent = '';
        }

        this._updateHP();
        this._updateHitDice();
        this.element.classList.remove('hidden');
    }

    hide() {
        if (!this.element) return;
        this.element.classList.add('hidden');
        this.restType = null;
    }

    // ================================================================
    // UI Updates
    // ================================================================

    _updateHP() {
        const fill = document.getElementById('rest-hp-fill');
        const text = document.getElementById('rest-hp-text');

        if (fill) {
            const ratio = this._hpMax > 0 ? Math.max(0, Math.min(1, this._hpCurrent / this._hpMax)) : 0;
            fill.style.width = (ratio * 100) + '%';

            // Color
            if (ratio > 0.5) {
                fill.className = 'rest-hp-fill hp-high';
            } else if (ratio > 0.25) {
                fill.className = 'rest-hp-fill hp-mid';
            } else {
                fill.className = 'rest-hp-fill hp-low';
            }
        }

        if (text) {
            text.textContent = `${this._hpCurrent} / ${this._hpMax}`;
        }

        // Disable spend hit die if full HP
        const spendBtn = document.getElementById('rest-spend-hitdie');
        if (spendBtn) {
            spendBtn.disabled = this._hpCurrent >= this._hpMax || this._hitDiceCurrent <= 0;
        }
    }

    _updateHitDice() {
        const text = document.getElementById('rest-hitdice-text');
        if (text) {
            text.textContent = `${this._hitDiceCurrent} / ${this._hitDiceMax}`;
        }

        // Update spend button state
        const spendBtn = document.getElementById('rest-spend-hitdie');
        if (spendBtn) {
            spendBtn.disabled = this._hpCurrent >= this._hpMax || this._hitDiceCurrent <= 0;
        }
    }

    _showResult(message, isSuccess = true) {
        const resultEl = document.getElementById('rest-result');
        if (!resultEl) return;

        resultEl.textContent = message;
        resultEl.className = `rest-result ${isSuccess ? 'rest-result-success' : 'rest-result-error'}`;
        resultEl.classList.remove('hidden');
    }

    // ================================================================
    // Bindings
    // ================================================================

    _bindButtons() {
        const spendBtn = document.getElementById('rest-spend-hitdie');
        if (spendBtn) {
            spendBtn.addEventListener('click', () => {
                PythonAPI.call('spend_hit_die', { count: 1 });
            });
        }

        const finishBtn = document.getElementById('rest-finish');
        if (finishBtn) {
            finishBtn.addEventListener('click', () => {
                PythonAPI.call('finish_rest', { rest_type: this.restType });
            });
        }
    }

    // ================================================================
    // Event Subscriptions
    // ================================================================

    _subscribeEvents() {
        window.addEventListener('python-message', (event) => {
            const { type, data } = event.detail;

            switch (type) {
                case 'character_sheet': {
                    const char = data?.character || data;
                    const stats = char?.stats || {};
                    this._hpCurrent = stats.current_hp || 0;
                    this._hpMax = stats.max_hp || 1;
                    this._hitDiceCurrent = stats.hit_dice_current || 0;
                    this._hitDiceMax = stats.hit_dice_max || 0;

                    if (this.element && !this.element.classList.contains('hidden')) {
                        this._updateHP();
                        this._updateHitDice();
                    }
                    break;
                }

                case 'show_rest_dialog':
                    this.show(data?.rest_type || 'short');
                    break;

                case 'rest_result': {
                    if (data.success) {
                        this._hpCurrent = data.hp_new || this._hpCurrent;
                        this._hpMax = data.hp_max || this._hpMax;
                        this._hitDiceCurrent = data.hit_dice_remaining !== undefined ? data.hit_dice_remaining : this._hitDiceCurrent;
                        this._hitDiceMax = data.hit_dice_max || this._hitDiceMax;

                        const restored = data.hp_restored || 0;
                        this._showResult(`Отдых завершён. Восстановлено ${restored} ОЗ.`, true);
                    } else {
                        this._showResult(data.error || 'Не удалось завершить отдых', false);
                    }
                    this._updateHP();
                    this._updateHitDice();

                    // Auto-close after a short rest result
                    if (data.success) {
                        setTimeout(() => this.hide(), 2000);
                    }
                    break;
                }

                case 'hit_die_result': {
                    if (data.success) {
                        this._hpCurrent = data.hp_new || this._hpCurrent;
                        this._hpMax = data.hp_max || this._hpMax;
                        this._hitDiceCurrent = data.hit_dice_remaining !== undefined ? data.hit_dice_remaining : this._hitDiceCurrent;
                        this._hitDiceMax = data.hit_dice_max || this._hitDiceMax;

                        const healing = data.healing || 0;
                        this._showResult(`Кость хитов: +${healing} ОЗ`, true);
                    } else {
                        this._showResult(data.message || 'Не удалось использовать кость хитов', false);
                    }
                    this._updateHP();
                    this._updateHitDice();
                    break;
                }
            }
        });
    }
}
