/**
 * SpellbookPanel - Persistent overlay for spell management.
 *
 * Shows spell slots, spell list with filters, spell details,
 * and actions for preparing/casting spells.
 *
 * Data sources: character_sheet (spellcasting), spellcasting_update, spell_cast_result
 */

class SpellbookPanel {
    constructor() {
        this.element = null;
        this.activeFilter = 'all';
        this.selectedSpellId = null;

        // Cached data
        this._spellcasting = null; // { ability, spells_known, spells_prepared, spell_slots_current, spell_slots_max }
        this._spellsData = {};     // spell_id -> full spell data (from character_sheet)

        // School translations
        this.SCHOOLS = {
            abjuration: 'Ограждение',
            conjuration: 'Вызов',
            divination: 'Прорицание',
            enchantment: 'Очарование',
            evocation: 'Воплощение',
            illusion: 'Иллюзия',
            necromancy: 'Некромантия',
            transmutation: 'Преобразование'
        };

        // Level names
        this.LEVEL_NAMES = {
            0: 'Заговор',
            1: '1 круг', 2: '2 круг', 3: '3 круг',
            4: '4 круг', 5: '5 круг', 6: '6 круг',
            7: '7 круг', 8: '8 круг', 9: '9 круг'
        };

        // Level colors for spell list
        this.LEVEL_COLORS = {
            0: '#a0a0a0',
            1: '#6090d0', 2: '#50b050', 3: '#d0a040',
            4: '#d06040', 5: '#c050c0', 6: '#5080b0',
            7: '#b07030', 8: '#8050c0', 9: '#d04040'
        };
    }

    async init() {
        try {
            const response = await fetch('templates/spellbook.html');
            const html = await response.text();

            const container = document.createElement('div');
            container.innerHTML = html;
            document.body.appendChild(container.firstElementChild);

            this.element = document.getElementById('spellbook-panel');
        } catch (e) {
            console.error('[SpellbookPanel] Failed to load template:', e);
            return;
        }

        this._bindClose();
        this._bindFilters();
        this._subscribeEvents();

        console.log('[SpellbookPanel] Initialized');
    }

    // ================================================================
    // Show / Hide
    // ================================================================

    show() {
        if (!this.element) return;
        this.element.classList.remove('hidden');
        this._renderSlots();
        this._renderSpellList();
    }

    hide() {
        if (!this.element) return;
        this.element.classList.add('hidden');
    }

    // ================================================================
    // Bindings
    // ================================================================

    _bindClose() {
        const btn = document.getElementById('sb-close-btn');
        if (btn) {
            btn.addEventListener('click', () => {
                if (window.panelManager) {
                    window.panelManager.closeActive();
                } else {
                    this.hide();
                }
            });
        }
    }

    _bindFilters() {
        const filtersEl = document.getElementById('sb-filters');
        if (!filtersEl) return;

        filtersEl.querySelectorAll('.sb-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.activeFilter = btn.dataset.filter;
                filtersEl.querySelectorAll('.sb-filter-btn').forEach(b =>
                    b.classList.toggle('active', b === btn)
                );
                this._renderSpellList();
            });
        });
    }

    // ================================================================
    // Spell Slots Bar
    // ================================================================

    _renderSlots() {
        const bar = document.getElementById('sb-slots-bar');
        if (!bar || !this._spellcasting) {
            if (bar) bar.innerHTML = '';
            return;
        }

        const current = this._spellcasting.spell_slots_current || {};
        const max = this._spellcasting.spell_slots_max || {};

        let html = '';
        for (let level = 1; level <= 9; level++) {
            const maxSlots = max[level] || max[String(level)] || 0;
            if (maxSlots === 0) continue;
            const curSlots = current[level] || current[String(level)] || 0;

            html += `
                <div class="sb-slot-group">
                    <span class="sb-slot-level">${level}</span>
                    <span class="sb-slot-count ${curSlots === 0 ? 'depleted' : ''}">${curSlots}/${maxSlots}</span>
                </div>
            `;
        }

        bar.innerHTML = html || '<div class="sb-no-slots">Нет ячеек заклинаний</div>';
    }

    // ================================================================
    // Spell List
    // ================================================================

    _renderSpellList() {
        const listEl = document.getElementById('sb-spell-list');
        if (!listEl) return;

        if (!this._spellcasting) {
            listEl.innerHTML = '<div class="sb-empty-message">Нет данных о заклинаниях</div>';
            return;
        }

        const known = this._spellcasting.spells_known || [];
        const prepared = this._spellcasting.spells_prepared || [];

        // Get spell data objects
        let spells = known.map(id => {
            return this._spellsData[id] || { id, name: id, name_ru: id, level: 0, school: '' };
        });

        // Apply filter
        if (this.activeFilter === 'cantrip') {
            spells = spells.filter(s => s.level === 0);
        } else if (this.activeFilter === 'prepared') {
            spells = spells.filter(s => prepared.includes(s.id) || s.level === 0);
        }

        // Sort by level, then name
        spells.sort((a, b) => {
            if (a.level !== b.level) return a.level - b.level;
            return (a.name_ru || a.name || '').localeCompare(b.name_ru || b.name || '');
        });

        if (spells.length === 0) {
            listEl.innerHTML = '<div class="sb-empty-message">Нет заклинаний</div>';
            return;
        }

        listEl.innerHTML = spells.map(spell => {
            const isPrepared = prepared.includes(spell.id);
            const levelColor = this.LEVEL_COLORS[spell.level] || '#a0a0a0';
            const schoolName = this.SCHOOLS[spell.school] || spell.school || '';
            const levelLabel = this.LEVEL_NAMES[spell.level] || `${spell.level} круг`;
            const selected = this.selectedSpellId === spell.id ? 'selected' : '';

            return `
                <div class="sb-spell-entry ${selected}" data-spell-id="${spell.id}">
                    <span class="sb-spell-prepared">${isPrepared ? '&#9733;' : ''}</span>
                    <span class="sb-spell-name" style="color: ${levelColor}">${spell.name_ru || spell.name || spell.id}</span>
                    <span class="sb-spell-info">${levelLabel} &middot; ${schoolName}</span>
                </div>
            `;
        }).join('');

        // Bind click on spell entries
        listEl.querySelectorAll('.sb-spell-entry').forEach(entry => {
            entry.addEventListener('click', () => {
                this.selectedSpellId = entry.dataset.spellId;
                // Update selection visual
                listEl.querySelectorAll('.sb-spell-entry').forEach(e =>
                    e.classList.toggle('selected', e === entry)
                );
                this._renderSpellDetail();
            });
        });
    }

    // ================================================================
    // Spell Detail
    // ================================================================

    _renderSpellDetail() {
        const detailEl = document.getElementById('sb-spell-detail');
        if (!detailEl) return;

        if (!this.selectedSpellId || !this._spellcasting) {
            detailEl.innerHTML = '<div class="sb-detail-placeholder">Выберите заклинание</div>';
            return;
        }

        const spell = this._spellsData[this.selectedSpellId];
        if (!spell) {
            detailEl.innerHTML = '<div class="sb-detail-placeholder">Данные заклинания не найдены</div>';
            return;
        }

        const prepared = (this._spellcasting.spells_prepared || []).includes(spell.id);
        const levelLabel = this.LEVEL_NAMES[spell.level] || `${spell.level} круг`;
        const schoolName = this.SCHOOLS[spell.school] || spell.school || '';

        // Range display
        let rangeStr = '';
        if (spell.range_ft === 0) rangeStr = 'На себя';
        else if (spell.range_ft === -1) rangeStr = 'Касание';
        else rangeStr = `${spell.range_ft} фт`;

        // Components
        const components = (spell.components || []).join(', ');
        const material = spell.material ? ` (${spell.material})` : '';

        // Tags
        const tags = [];
        if (spell.ritual) tags.push('Ритуал');
        if (spell.concentration) tags.push('Концентрация');

        // Slot level selector for casting (only for non-cantrips)
        let castSection = '';
        if (spell.level > 0) {
            const current = this._spellcasting.spell_slots_current || {};
            const max = this._spellcasting.spell_slots_max || {};

            let slotOptions = '';
            for (let lvl = spell.level; lvl <= 9; lvl++) {
                const maxSlots = max[lvl] || max[String(lvl)] || 0;
                if (maxSlots === 0) continue;
                const curSlots = current[lvl] || current[String(lvl)] || 0;
                slotOptions += `<option value="${lvl}" ${curSlots === 0 ? 'disabled' : ''}>${lvl} круг (${curSlots}/${maxSlots})</option>`;
            }

            castSection = `
                <div class="sb-cast-section">
                    <select class="sb-slot-select" id="sb-cast-slot">${slotOptions}</select>
                    <button class="btn btn-primary sb-cast-btn" id="sb-cast-btn">Использовать</button>
                </div>
            `;
        } else {
            castSection = `
                <div class="sb-cast-section">
                    <button class="btn btn-primary sb-cast-btn" id="sb-cast-btn">Использовать</button>
                </div>
            `;
        }

        // Prepare/unprepare button (only for non-cantrips)
        let prepareBtn = '';
        if (spell.level > 0) {
            if (prepared) {
                prepareBtn = `<button class="btn btn-secondary sb-prepare-btn" id="sb-prepare-btn" data-action="unprepare">Отменить подготовку</button>`;
            } else {
                prepareBtn = `<button class="btn btn-primary sb-prepare-btn" id="sb-prepare-btn" data-action="prepare">Подготовить</button>`;
            }
        }

        detailEl.innerHTML = `
            <div class="sb-detail-header">
                <div class="sb-detail-name">${spell.name_ru || spell.name || spell.id}</div>
                <div class="sb-detail-level">${levelLabel} &middot; ${schoolName}</div>
                ${tags.length > 0 ? `<div class="sb-detail-tags">${tags.map(t => `<span class="sb-tag">${t}</span>`).join('')}</div>` : ''}
            </div>

            <div class="sb-detail-props">
                <div class="sb-prop"><span class="sb-prop-label">Время накладывания:</span> ${spell.casting_time || '?'}</div>
                <div class="sb-prop"><span class="sb-prop-label">Дальность:</span> ${rangeStr}</div>
                <div class="sb-prop"><span class="sb-prop-label">Компоненты:</span> ${components}${material}</div>
                <div class="sb-prop"><span class="sb-prop-label">Длительность:</span> ${spell.duration || '?'}</div>
            </div>

            <div class="sb-detail-desc">${spell.description_ru || spell.description || ''}</div>

            ${spell.higher_levels_ru || spell.higher_levels ? `
                <div class="sb-detail-higher">
                    <span class="sb-prop-label">На более высоких кругах:</span>
                    ${spell.higher_levels_ru || spell.higher_levels}
                </div>
            ` : ''}

            <div class="sb-detail-actions">
                ${prepareBtn}
                ${castSection}
            </div>
        `;

        // Bind actions
        const castBtn = document.getElementById('sb-cast-btn');
        if (castBtn) {
            castBtn.addEventListener('click', () => {
                const slotSelect = document.getElementById('sb-cast-slot');
                const slotLevel = slotSelect ? parseInt(slotSelect.value) : spell.level;
                PythonAPI.call('cast_spell', { spell_id: spell.id, slot_level: slotLevel });
            });
        }

        const prepBtn = document.getElementById('sb-prepare-btn');
        if (prepBtn) {
            prepBtn.addEventListener('click', () => {
                const action = prepBtn.dataset.action;
                if (action === 'prepare') {
                    PythonAPI.call('prepare_spell', { spell_id: spell.id });
                } else {
                    PythonAPI.call('unprepare_spell', { spell_id: spell.id });
                }
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
                    if (char?.spellcasting) {
                        this._spellcasting = char.spellcasting;

                        // Extract spell data if provided inline
                        if (char.spellcasting.spells_data) {
                            char.spellcasting.spells_data.forEach(spell => {
                                this._spellsData[spell.id] = spell;
                            });
                        }
                    }
                    if (this.element && !this.element.classList.contains('hidden')) {
                        this._renderSlots();
                        this._renderSpellList();
                        if (this.selectedSpellId) this._renderSpellDetail();
                    }
                    break;
                }

                case 'spellcasting_update': {
                    if (this._spellcasting) {
                        if (data.spells_known) this._spellcasting.spells_known = data.spells_known;
                        if (data.spells_prepared) this._spellcasting.spells_prepared = data.spells_prepared;
                        if (data.spell_slots_current) this._spellcasting.spell_slots_current = data.spell_slots_current;
                        if (data.spell_slots_max) this._spellcasting.spell_slots_max = data.spell_slots_max;
                        if (data.spells_data) {
                            data.spells_data.forEach(spell => {
                                this._spellsData[spell.id] = spell;
                            });
                        }
                    }
                    if (this.element && !this.element.classList.contains('hidden')) {
                        this._renderSlots();
                        this._renderSpellList();
                        if (this.selectedSpellId) this._renderSpellDetail();
                    }
                    break;
                }

                case 'spell_cast_result': {
                    if (data.spell_slots_current && this._spellcasting) {
                        this._spellcasting.spell_slots_current = data.spell_slots_current;
                    }
                    if (this.element && !this.element.classList.contains('hidden')) {
                        this._renderSlots();
                        if (this.selectedSpellId) this._renderSpellDetail();
                    }
                    break;
                }
            }
        });
    }
}
