/**
 * CharacterSheet - Persistent overlay panel with 6 tabs.
 *
 * Tabs: Stats, Skills, Abilities, Inventory, Equipment, Description
 * Data sources: character_sheet, inventory_update, equipment_update events
 */

class CharacterSheet {
    constructor() {
        this.element = null;
        this.activeTab = 'stats';

        // Cached data
        this._character = null;
        this._inventory = [];
        this._maxSlots = 20;
        this._equipment = {};
        this._selectedInvSlot = null;
        this._invFilter = 'all';

        // Rarity colors
        this.RARITY_COLORS = {
            common: '#c9b896',
            uncommon: '#60c060',
            rare: '#5090e0',
            very_rare: '#a050d0',
            legendary: '#d4af37',
            artifact: '#e05050'
        };

        // Ability names
        this.ABILITY_NAMES = {
            strength: 'Сила',
            dexterity: 'Ловкость',
            constitution: 'Телосложение',
            intelligence: 'Интеллект',
            wisdom: 'Мудрость',
            charisma: 'Харизма'
        };

        // Skill data
        this.SKILLS = {
            acrobatics:       { name: 'Акробатика',         ability: 'dexterity' },
            animal_handling:  { name: 'Уход за животными',  ability: 'wisdom' },
            arcana:           { name: 'Магия',              ability: 'intelligence' },
            athletics:        { name: 'Атлетика',           ability: 'strength' },
            deception:        { name: 'Обман',              ability: 'charisma' },
            history:          { name: 'История',            ability: 'intelligence' },
            insight:          { name: 'Проницательность',   ability: 'wisdom' },
            intimidation:     { name: 'Запугивание',        ability: 'charisma' },
            investigation:    { name: 'Расследование',      ability: 'intelligence' },
            medicine:         { name: 'Медицина',           ability: 'wisdom' },
            nature:           { name: 'Природа',            ability: 'intelligence' },
            perception:       { name: 'Внимание',           ability: 'wisdom' },
            performance:      { name: 'Выступление',        ability: 'charisma' },
            persuasion:       { name: 'Убеждение',          ability: 'charisma' },
            religion:         { name: 'Религия',            ability: 'intelligence' },
            sleight_of_hand:  { name: 'Ловкость рук',       ability: 'dexterity' },
            stealth:          { name: 'Скрытность',         ability: 'dexterity' },
            survival:         { name: 'Выживание',          ability: 'wisdom' }
        };

        // Equipment slot names
        this.EQUIP_SLOTS = {
            head:      'Голова',
            chest:     'Тело',
            hands:     'Руки',
            main_hand: 'Основная рука',
            off_hand:  'Вторая рука',
            feet:      'Ноги',
            amulet:    'Ожерелье',
            cloak:     'Плащ',
            ring_1:    'Кольцо 1',
            ring_2:    'Кольцо 2',
            belt:      'Пояс',
            legs:      'Ноги (одежда)'
        };

        // Description sub-tabs
        this.DESC_TABS = [
            { key: 'appearance', label: 'Описание персонажа' },
            { key: 'backstory', label: 'Предыстория' },
            { key: 'notes', label: 'Заметки' },
        ];
        this._activeDescTab = 'appearance';
    }

    async init() {
        try {
            const response = await fetch('templates/character-sheet.html');
            const html = await response.text();

            const container = document.createElement('div');
            container.innerHTML = html;
            document.body.appendChild(container.firstElementChild);

            this.element = document.getElementById('character-sheet-panel');
        } catch (e) {
            console.error('[CharacterSheet] Failed to load template:', e);
            return;
        }

        this._bindTabs();
        this._bindClose();
        this._subscribeEvents();

        console.log('[CharacterSheet] Initialized');
    }

    // ================================================================
    // Show / Hide
    // ================================================================

    show(options) {
        if (!this.element) return;
        if (options && options.tab) {
            this._switchTab(options.tab);
        }
        this.element.classList.remove('hidden');
        this._renderActiveTab();
    }

    hide() {
        if (!this.element) return;
        this.element.classList.add('hidden');
    }

    // ================================================================
    // Tabs
    // ================================================================

    _bindTabs() {
        const tabsContainer = document.getElementById('cs-tabs');
        if (!tabsContainer) return;

        tabsContainer.querySelectorAll('.panel-tab').forEach(btn => {
            btn.addEventListener('click', () => {
                this._switchTab(btn.dataset.tab);
            });
        });
    }

    _switchTab(tabName) {
        this.activeTab = tabName;

        // Update tab buttons
        const tabs = document.getElementById('cs-tabs');
        if (tabs) {
            tabs.querySelectorAll('.panel-tab').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.tab === tabName);
            });
        }

        // Update tab content
        this.element.querySelectorAll('.panel-tab-content').forEach(content => {
            content.classList.toggle('active', content.dataset.tab === tabName);
        });

        this._renderActiveTab();
    }

    _renderActiveTab() {
        switch (this.activeTab) {
            case 'stats': this._renderStats(); break;
            case 'skills': this._renderSkills(); break;
            case 'abilities': this._renderAbilities(); break;
            case 'inventory': this._renderInventory(); break;
            case 'equipment': this._renderEquipment(); break;
            case 'description': this._renderDescription(); break;
        }
    }

    _bindClose() {
        const btn = document.getElementById('cs-close-btn');
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

    // ================================================================
    // Stats Tab
    // ================================================================

    _renderStats() {
        const char = this._character;
        if (!char) return;

        const abilities = char.abilities || {};
        const saves = char.saving_throws || {};
        const stats = char.stats || {};

        // Ability scores grid
        const abilitiesEl = document.getElementById('cs-abilities');
        if (abilitiesEl) {
            abilitiesEl.innerHTML = Object.entries(this.ABILITY_NAMES).map(([key, name]) => {
                const ab = abilities[key] || {};
                const value = ab.value || 10;
                const mod = ab.modifier || Math.floor((value - 10) / 2);
                const modStr = mod >= 0 ? `+${mod}` : `${mod}`;
                return `
                    <div class="cs-ability-card">
                        <div class="cs-ability-name">${name}</div>
                        <div class="cs-ability-value">${value}</div>
                        <div class="cs-ability-mod">${modStr}</div>
                    </div>
                `;
            }).join('');
        }

        // Saving throws
        const savesEl = document.getElementById('cs-saves');
        if (savesEl) {
            savesEl.innerHTML = Object.entries(this.ABILITY_NAMES).map(([key, name]) => {
                const save = saves[key] || {};
                const mod = save.modifier || 0;
                const prof = save.proficient || false;
                const modStr = mod >= 0 ? `+${mod}` : `${mod}`;
                return `
                    <div class="cs-save-row">
                        <span class="cs-save-prof ${prof ? 'proficient' : ''}">${prof ? '&#9679;' : '&#9675;'}</span>
                        <span class="cs-save-name">${name}</span>
                        <span class="cs-save-mod">${modStr}</span>
                    </div>
                `;
            }).join('');
        }

        // Derived stats
        const derivedEl = document.getElementById('cs-derived');
        if (derivedEl) {
            const ac = stats.armor_class || 10;
            const init = stats.initiative || 0;
            const speed = stats.base_speed || 30;
            const hp = stats.current_hp || 0;
            const hpMax = stats.max_hp || 1;
            const tempHp = stats.temp_hp || 0;
            const hitDice = stats.hit_dice_current || 0;
            const hitDiceMax = stats.hit_dice_max || 0;
            const hitDie = stats.hit_die || 'd8';
            const profBonus = stats.proficiency_bonus || 2;
            const passPerc = stats.passive_perception || 10;
            const initStr = init >= 0 ? `+${init}` : `${init}`;

            derivedEl.innerHTML = `
                <div class="cs-derived-grid">
                    <div class="cs-derived-item">
                        <div class="cs-derived-value">${ac}</div>
                        <div class="cs-derived-label">КЗ</div>
                    </div>
                    <div class="cs-derived-item">
                        <div class="cs-derived-value">${initStr}</div>
                        <div class="cs-derived-label">Инициатива</div>
                    </div>
                    <div class="cs-derived-item">
                        <div class="cs-derived-value">${speed} фт</div>
                        <div class="cs-derived-label">Скорость</div>
                    </div>
                    <div class="cs-derived-item">
                        <div class="cs-derived-value">${hp}/${hpMax}${tempHp > 0 ? ` (+${tempHp})` : ''}</div>
                        <div class="cs-derived-label">Здоровье</div>
                    </div>
                    <div class="cs-derived-item">
                        <div class="cs-derived-value">${hitDice}/${hitDiceMax} ${hitDie}</div>
                        <div class="cs-derived-label">Кости хитов</div>
                    </div>
                    <div class="cs-derived-item">
                        <div class="cs-derived-value">+${profBonus}</div>
                        <div class="cs-derived-label">Бонус мастерства</div>
                    </div>
                    <div class="cs-derived-item">
                        <div class="cs-derived-value">${passPerc}</div>
                        <div class="cs-derived-label">Пасс. внимание</div>
                    </div>
                </div>
            `;
        }
    }

    // ================================================================
    // Skills Tab
    // ================================================================

    _renderSkills() {
        const char = this._character;
        if (!char) return;

        const skills = char.skills || {};
        const listEl = document.getElementById('cs-skills-list');
        if (!listEl) return;

        listEl.innerHTML = Object.entries(this.SKILLS).map(([key, info]) => {
            const skill = skills[key] || {};
            const mod = skill.modifier || 0;
            const prof = skill.proficient || false;
            const modStr = mod >= 0 ? `+${mod}` : `${mod}`;
            const abilityAbbr = (skill.ability || info.ability).substring(0, 3).toUpperCase();

            return `
                <div class="cs-skill-row">
                    <span class="cs-skill-prof ${prof ? 'proficient' : ''}">${prof ? '&#9679;' : '&#9675;'}</span>
                    <span class="cs-skill-name">${info.name}</span>
                    <span class="cs-skill-ability">${abilityAbbr}</span>
                    <span class="cs-skill-mod">${modStr}</span>
                </div>
            `;
        }).join('');
    }

    // ================================================================
    // Abilities/Features Tab
    // ================================================================

    _renderAbilities() {
        const char = this._character;
        if (!char) return;

        const features = char.features || {};
        const proficiencies = char.proficiencies || {};
        const container = document.getElementById('cs-features');
        if (!container) return;

        let html = '';

        // Racial features
        const racial = Array.isArray(features.racial) ? features.racial : (Array.isArray(features) ? features : []);
        if (features.racial && features.racial.length > 0) {
            html += this._renderFeatureSection('Расовые черты', features.racial);
        }

        // Class features
        if (features.class && features.class.length > 0) {
            html += this._renderFeatureSection('Классовые черты', features.class);
        }

        // Background features
        if (features.background && features.background.length > 0) {
            html += this._renderFeatureSection('Черты предыстории', features.background);
        }

        // If features is just an array (flat list)
        if (Array.isArray(features) && features.length > 0) {
            html += this._renderFeatureSection('Черты', features);
        }

        // Proficiencies
        const profSections = [
            { key: 'armor', label: 'Доспехи' },
            { key: 'weapons', label: 'Оружие' },
            { key: 'tools', label: 'Инструменты' },
            { key: 'languages', label: 'Языки' }
        ];

        let profHtml = '';
        profSections.forEach(({ key, label }) => {
            const items = proficiencies[key] || [];
            if (items.length > 0) {
                profHtml += `
                    <div class="cs-prof-group">
                        <span class="cs-prof-label">${label}:</span>
                        <span class="cs-prof-items">${items.join(', ')}</span>
                    </div>
                `;
            }
        });

        if (profHtml) {
            html += `
                <div class="cs-feature-section">
                    <div class="cs-section-title">Владения</div>
                    ${profHtml}
                </div>
            `;
        }

        if (!html) {
            html = '<div class="cs-empty-message">Нет способностей</div>';
        }

        container.innerHTML = html;
    }

    _renderFeatureSection(title, features) {
        const items = features.map(f => `
            <div class="cs-feature-item">
                <div class="cs-feature-name">${f.name || f.name_ru || '?'}</div>
                <div class="cs-feature-desc">${f.description || f.description_ru || ''}</div>
            </div>
        `).join('');

        return `
            <div class="cs-feature-section">
                <div class="cs-section-title">${title}</div>
                ${items}
            </div>
        `;
    }

    // ================================================================
    // Inventory Tab (Fallout-style: list + detail panel)
    // ================================================================

    _renderInventory() {
        const container = document.getElementById('cs-inventory-container');
        if (!container) return;

        // Category filter
        const CATEGORIES = [
            { key: 'all', label: 'Все' },
            { key: 'weapon', label: 'Оружие' },
            { key: 'armor', label: 'Доспехи' },
            { key: 'equipment', label: 'Снаряжение' },
            { key: 'consumable', label: 'Расходные' },
            { key: 'misc', label: 'Прочее' },
        ];

        const activeFilter = this._invFilter || 'all';

        // Build equipped items list from equipment slots (Fallout-style: show in inventory with [E])
        const equippedItems = [];
        if (this._equipment) {
            for (const [slotKey, eqItem] of Object.entries(this._equipment)) {
                if (eqItem) {
                    equippedItems.push({
                        ...eqItem,
                        _equipped: true,
                        _equipSlot: slotKey,
                        category: eqItem.category || (slotKey === 'main_hand' || slotKey === 'off_hand' ? 'weapon' : 'armor'),
                    });
                }
            }
        }

        // Filter inventory items
        const filtered = activeFilter === 'all'
            ? this._inventory
            : this._inventory.filter(item => item.category === activeFilter);

        // Filter equipped items
        const filteredEquipped = activeFilter === 'all'
            ? equippedItems
            : equippedItems.filter(item => item.category === activeFilter);

        // Category filter bar
        const filterHtml = CATEGORIES.map(c =>
            `<button class="cs-inv-filter-btn ${activeFilter === c.key ? 'active' : ''}" data-cat="${c.key}">${c.label}</button>`
        ).join('');

        // Item list: equipped items first, then inventory
        let listHtml = '';

        // Equipped items with [E] badge
        const equippedHtml = filteredEquipped.map(item => {
            const rarityColor = this.RARITY_COLORS[item.rarity] || this.RARITY_COLORS.common;
            const slotName = this.EQUIP_SLOTS[item._equipSlot] || item._equipSlot;
            return `<div class="cs-inv-item cs-inv-equipped" data-equip-slot="${item._equipSlot}">
                <span class="cs-inv-item-name" style="color: ${rarityColor}"><span class="cs-inv-equip-badge" title="${slotName}">E</span>${item.name || '?'}</span>
                <span class="cs-inv-item-weight">${slotName}</span>
            </div>`;
        }).join('');

        // Regular inventory items
        const invHtml = filtered.length === 0 && filteredEquipped.length === 0
            ? '<div class="cs-inv-empty">Пусто</div>'
            : filtered.map((item, idx) => {
                const origIdx = this._inventory.indexOf(item);
                const rarityColor = this.RARITY_COLORS[item.rarity] || this.RARITY_COLORS.common;
                const selected = this._selectedInvSlot === origIdx;
                const countText = item.count > 1 ? ` (${item.count})` : '';
                return `<div class="cs-inv-item ${selected ? 'selected' : ''}" data-slot="${origIdx}">
                    <span class="cs-inv-item-name" style="color: ${rarityColor}">${item.name || '?'}${countText}</span>
                    <span class="cs-inv-item-weight">${item.weight ? (item.weight * (item.count || 1)).toFixed(1) : ''}</span>
                </div>`;
            }).join('');

        listHtml = equippedHtml + invHtml;

        // Detail panel for selected item
        let detailHtml = '<div class="cs-inv-detail-empty">Выберите предмет</div>';
        const selItem = this._inventory[this._selectedInvSlot];
        if (selItem) {
            detailHtml = this._renderItemDetail(selItem, this._selectedInvSlot);
        }

        // Total weight
        const totalWeight = this._inventory.reduce((sum, item) =>
            sum + (item.weight || 0) * (item.count || 1), 0);

        container.innerHTML = `
            <div class="cs-inv-filters">${filterHtml}</div>
            <div class="cs-inv-columns">
                <div class="cs-inv-list">${listHtml}</div>
                <div class="cs-inv-detail">${detailHtml}</div>
            </div>
            <div class="cs-inv-footer">
                <span>Вес: ${totalWeight.toFixed(1)} фн</span>
                <span>Предметы: ${this._inventory.length}/${this._maxSlots}</span>
            </div>
        `;

        // Bind filter buttons
        container.querySelectorAll('.cs-inv-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._invFilter = btn.dataset.cat;
                this._renderInventory();
            });
        });

        // Bind equipped item click — show detail and allow unequip
        container.querySelectorAll('.cs-inv-equipped').forEach(el => {
            el.addEventListener('click', () => {
                this._selectedInvSlot = null;
                const slotKey = el.dataset.equipSlot;
                const eqItem = this._equipment[slotKey];
                if (eqItem) {
                    const detailPanel = container.querySelector('.cs-inv-detail');
                    if (detailPanel) {
                        const slotName = this.EQUIP_SLOTS[slotKey] || slotKey;
                        const rarityColor = this.RARITY_COLORS[eqItem.rarity] || this.RARITY_COLORS.common;
                        detailPanel.innerHTML = `
                            <div class="cs-inv-detail-header" style="color: ${rarityColor}">${eqItem.name || '?'}</div>
                            <div class="cs-inv-detail-props">
                                <div class="cs-inv-prop"><span class="cs-inv-prop-label">Слот:</span> ${slotName}</div>
                            </div>
                            ${eqItem.tooltip ? `<div class="cs-inv-tooltip-stats">${eqItem.tooltip.split('\\n').map(l => `<div class="cs-inv-stat-line">${l}</div>`).join('')}</div>` : ''}
                            <div class="cs-inv-actions">
                                <button class="cs-inv-action-btn cs-inv-unequip-btn" data-equip-slot="${slotKey}">Снять</button>
                            </div>
                        `;
                        detailPanel.querySelector('.cs-inv-unequip-btn')?.addEventListener('click', () => {
                            PythonAPI.call('unequip_item', { equipment_slot: slotKey });
                        });
                    }
                }
                // Update selection visuals
                container.querySelectorAll('.cs-inv-item').forEach(i => i.classList.remove('selected'));
                el.classList.add('selected');
            });
        });

        // Bind item selection
        container.querySelectorAll('.cs-inv-item:not(.cs-inv-equipped)').forEach(el => {
            el.addEventListener('click', () => {
                this._selectedInvSlot = parseInt(el.dataset.slot);
                this._renderInventory();
            });
        });

        // Bind action buttons
        this._bindInventoryActions(container);
    }

    _renderItemDetail(item, slotIdx) {
        const rarityColor = this.RARITY_COLORS[item.rarity] || this.RARITY_COLORS.common;

        const RARITY_NAMES = {
            common: 'Обычный', uncommon: 'Необычный', rare: 'Редкий',
            very_rare: 'Очень редкий', epic: 'Эпический',
            legendary: 'Легендарный', artifact: 'Артефакт'
        };

        const CATEGORY_NAMES = {
            weapon: 'Оружие', armor: 'Доспехи', consumable: 'Расходный',
            equipment: 'Снаряжение', tool: 'Инструмент', misc: 'Прочее'
        };

        // Item properties
        let propsHtml = '';
        propsHtml += `<div class="cs-inv-prop"><span class="cs-inv-prop-label">Категория:</span> ${CATEGORY_NAMES[item.category] || item.category}</div>`;
        propsHtml += `<div class="cs-inv-prop"><span class="cs-inv-prop-label">Редкость:</span> <span style="color: ${rarityColor}">${RARITY_NAMES[item.rarity] || item.rarity}</span></div>`;
        if (item.weight > 0) {
            propsHtml += `<div class="cs-inv-prop"><span class="cs-inv-prop-label">Вес:</span> ${item.weight} фн</div>`;
        }
        if (item.value > 0) {
            propsHtml += `<div class="cs-inv-prop"><span class="cs-inv-prop-label">Цена:</span> ${item.value} зм</div>`;
        }
        if (item.count > 1) {
            propsHtml += `<div class="cs-inv-prop"><span class="cs-inv-prop-label">Кол-во:</span> ${item.count}</div>`;
        }

        // Description
        const descHtml = item.description
            ? `<div class="cs-inv-desc">${item.description}</div>`
            : '';

        // Tooltip (contains formatted stats like damage, durability, etc.)
        let tooltipHtml = '';
        if (item.tooltip) {
            // Parse tooltip lines (skip name and description, they're already shown)
            const lines = item.tooltip.split('\n');
            const statLines = lines.filter(l =>
                l.trim() && l !== item.name && l !== item.description
            );
            if (statLines.length > 0) {
                tooltipHtml = `<div class="cs-inv-tooltip-stats">${statLines.map(l =>
                    `<div class="cs-inv-stat-line">${l}</div>`
                ).join('')}</div>`;
            }
        }

        // Action buttons
        let actionsHtml = '';
        if (item.can_use) {
            const useLabel = item.category === 'consumable' ? 'Использовать' : 'Использовать';
            actionsHtml += `<button class="cs-inv-action-btn cs-inv-use-btn" data-slot="${slotIdx}">Использовать</button>`;
        }
        if (item.can_equip) {
            actionsHtml += `<button class="cs-inv-action-btn cs-inv-equip-btn" data-slot="${slotIdx}">Экипировать</button>`;
        }
        if (item.droppable !== false) {
            actionsHtml += `<button class="cs-inv-action-btn cs-inv-drop-btn" data-slot="${slotIdx}">Выбросить</button>`;
        }

        return `
            <div class="cs-inv-detail-header" style="color: ${rarityColor}">${item.name || '?'}</div>
            <div class="cs-inv-detail-props">${propsHtml}</div>
            ${descHtml}
            ${tooltipHtml}
            ${actionsHtml ? `<div class="cs-inv-actions">${actionsHtml}</div>` : ''}
        `;
    }

    _bindInventoryActions(container) {
        container.querySelectorAll('.cs-inv-equip-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                PythonAPI.call('equip_item', { inventory_slot: parseInt(btn.dataset.slot) });
            });
        });
        container.querySelectorAll('.cs-inv-use-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                PythonAPI.call('item_use', { slot: parseInt(btn.dataset.slot) });
            });
        });
        container.querySelectorAll('.cs-inv-drop-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                PythonAPI.call('item_drop', { slot: parseInt(btn.dataset.slot) });
            });
        });
    }

    // ================================================================
    // Equipment Tab
    // ================================================================

    _renderEquipment() {
        const container = document.getElementById('cs-equipment-slots');
        if (!container) return;

        const slotOrder = ['head', 'chest', 'cloak', 'amulet', 'hands', 'main_hand', 'off_hand', 'ring_1', 'ring_2', 'belt', 'legs', 'feet'];

        container.innerHTML = slotOrder.map(slotKey => {
            const item = this._equipment[slotKey] || null;
            const slotName = this.EQUIP_SLOTS[slotKey] || slotKey;

            if (item) {
                const rarityColor = this.RARITY_COLORS[item.rarity] || this.RARITY_COLORS.common;
                return `
                    <div class="cs-equip-slot filled" data-slot="${slotKey}" title="${item.tooltip || item.name || ''}">
                        <span class="cs-equip-slot-name">${slotName}</span>
                        <span class="cs-equip-item-name" style="color: ${rarityColor}">${item.name || '?'}</span>
                        <button class="cs-equip-unequip-btn" data-slot="${slotKey}" title="Снять">&#x2716;</button>
                    </div>
                `;
            } else {
                return `
                    <div class="cs-equip-slot empty" data-slot="${slotKey}">
                        <span class="cs-equip-slot-name">${slotName}</span>
                        <span class="cs-equip-item-name cs-empty-slot">---</span>
                    </div>
                `;
            }
        }).join('');

        // Bind click to unequip
        container.querySelectorAll('.cs-equip-unequip-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const slotKey = btn.dataset.slot;
                PythonAPI.call('unequip_item', { equipment_slot: slotKey });
            });
        });
    }

    // ================================================================
    // Description Tab
    // ================================================================

    _renderDescription() {
        const container = document.getElementById('cs-description-form');
        if (!container) return;

        const char = this._character;
        const desc = char?.description || {};

        // Sub-tab buttons
        const tabsHtml = this.DESC_TABS.map(({ key, label }) =>
            `<button class="cs-desc-tab-btn ${this._activeDescTab === key ? 'active' : ''}" data-desc-tab="${key}">${label}</button>`
        ).join('');

        // Active sub-tab content
        const activeTab = this.DESC_TABS.find(t => t.key === this._activeDescTab) || this.DESC_TABS[0];
        const value = typeof desc === 'string'
            ? (activeTab.key === 'appearance' ? desc : '')
            : (desc[activeTab.key] || '');

        container.innerHTML = `
            <div class="cs-desc-tabs">${tabsHtml}</div>
            <div class="cs-desc-field">
                <textarea class="cs-desc-textarea cs-desc-full" data-field="${activeTab.key}">${this._escapeHtml(value)}</textarea>
            </div>
        `;

        // Bind sub-tab switching
        container.querySelectorAll('.cs-desc-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._activeDescTab = btn.dataset.descTab;
                this._renderDescription();
            });
        });

        // Bind blur to save
        container.querySelectorAll('.cs-desc-textarea').forEach(textarea => {
            textarea.addEventListener('blur', () => {
                const field = textarea.dataset.field;
                const value = textarea.value;
                PythonAPI.call('update_description', { field, value });
            });
        });
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ================================================================
    // Event Subscriptions
    // ================================================================

    _subscribeEvents() {
        window.addEventListener('python-message', (event) => {
            const { type, data } = event.detail;

            switch (type) {
                case 'character_sheet':
                    this._character = data?.character || data;
                    if (this.element && !this.element.classList.contains('hidden')) {
                        this._renderActiveTab();
                    }
                    break;

                case 'inventory_update':
                    this._inventory = data?.inventory || [];
                    this._maxSlots = data?.max_slots || 20;
                    if (this.activeTab === 'inventory' && this.element && !this.element.classList.contains('hidden')) {
                        this._renderInventory();
                    }
                    break;

                case 'equipment_update':
                    this._equipment = data?.slots || data || {};
                    if (this.element && !this.element.classList.contains('hidden')) {
                        if (this.activeTab === 'equipment') {
                            this._renderEquipment();
                        } else if (this.activeTab === 'inventory') {
                            this._renderInventory();
                        }
                    }
                    break;

                case 'open_character_sheet_tab':
                    if (data?.tab) {
                        if (window.panelManager) {
                            window.panelManager.open('character-sheet', { tab: data.tab });
                        } else {
                            this.show({ tab: data.tab });
                        }
                    }
                    break;
            }
        });
    }
}
