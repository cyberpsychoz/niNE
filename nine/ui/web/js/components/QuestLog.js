/**
 * QuestLog - Persistent overlay for quest management.
 *
 * Shows quest list with filters, quest details with objectives and rewards.
 * Data sources: quest_list, quest_accepted, quest_completed, quest_objective_progress, quest_ready_to_turn_in
 */

class QuestLog {
    constructor() {
        this.element = null;
        this.activeFilter = 'active';
        this.selectedQuestId = null;

        // Cached data
        this._quests = [];

        // Status labels
        this.STATUS_LABELS = {
            active: 'В процессе',
            completed: 'Готов к сдаче',
            available: 'Доступен',
            turned_in: 'Завершён'
        };

        // Status colors
        this.STATUS_COLORS = {
            active: '#60c060',
            completed: '#d4af37',
            available: '#5090e0',
            turned_in: '#808080'
        };
    }

    async init() {
        try {
            const response = await fetch('templates/quest-log.html');
            const html = await response.text();

            const container = document.createElement('div');
            container.innerHTML = html;
            document.body.appendChild(container.firstElementChild);

            this.element = document.getElementById('quest-log-panel');
        } catch (e) {
            console.error('[QuestLog] Failed to load template:', e);
            return;
        }

        this._bindClose();
        this._bindFilters();
        this._subscribeEvents();

        console.log('[QuestLog] Initialized');
    }

    // ================================================================
    // Show / Hide
    // ================================================================

    show() {
        if (!this.element) return;
        this.element.classList.remove('hidden');
        // Request quest list from server
        PythonAPI.call('quest_list_request', { filter: 'all' });
        this._renderQuestList();
    }

    hide() {
        if (!this.element) return;
        this.element.classList.add('hidden');
    }

    // ================================================================
    // Bindings
    // ================================================================

    _bindClose() {
        const btn = document.getElementById('ql-close-btn');
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
        const filtersEl = document.getElementById('ql-filters');
        if (!filtersEl) return;

        filtersEl.querySelectorAll('.ql-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.activeFilter = btn.dataset.filter;
                filtersEl.querySelectorAll('.ql-filter-btn').forEach(b =>
                    b.classList.toggle('active', b === btn)
                );
                this._renderQuestList();
            });
        });
    }

    // ================================================================
    // Quest List
    // ================================================================

    _renderQuestList() {
        const listEl = document.getElementById('ql-quest-list');
        if (!listEl) return;

        let quests = this._quests;

        // Apply filter
        if (this.activeFilter !== 'all') {
            quests = quests.filter(q => q.status === this.activeFilter);
        }

        if (quests.length === 0) {
            listEl.innerHTML = '<div class="ql-empty-message">Нет заданий</div>';
            return;
        }

        // Group by status
        const groups = {};
        quests.forEach(q => {
            const status = q.status || 'active';
            if (!groups[status]) groups[status] = [];
            groups[status].push(q);
        });

        let html = '';
        const statusOrder = ['active', 'completed', 'available', 'turned_in'];

        statusOrder.forEach(status => {
            const group = groups[status];
            if (!group || group.length === 0) return;

            if (this.activeFilter === 'all') {
                html += `<div class="ql-group-header">${this.STATUS_LABELS[status] || status}</div>`;
            }

            group.forEach(quest => {
                const selected = this.selectedQuestId === quest.id ? 'selected' : '';
                const color = this.STATUS_COLORS[status] || '#c9b896';
                const name = quest.name_ru || quest.name || quest.id;

                // Objectives progress
                const objectives = quest.objectives || [];
                const totalObj = objectives.length;
                const completedObj = objectives.filter(o => o.completed).length;
                const progressText = totalObj > 0 ? `${completedObj}/${totalObj}` : '';

                html += `
                    <div class="ql-quest-entry ${selected}" data-quest-id="${quest.id}">
                        <span class="ql-quest-status" style="color: ${color}">&bull;</span>
                        <span class="ql-quest-name">${name}</span>
                        ${progressText ? `<span class="ql-quest-progress">${progressText}</span>` : ''}
                    </div>
                `;
            });
        });

        listEl.innerHTML = html;

        // Bind click
        listEl.querySelectorAll('.ql-quest-entry').forEach(entry => {
            entry.addEventListener('click', () => {
                this.selectedQuestId = entry.dataset.questId;
                listEl.querySelectorAll('.ql-quest-entry').forEach(e =>
                    e.classList.toggle('selected', e === entry)
                );
                this._renderQuestDetail();
            });
        });
    }

    // ================================================================
    // Quest Detail
    // ================================================================

    _renderQuestDetail() {
        const detailEl = document.getElementById('ql-quest-detail');
        if (!detailEl) return;

        if (!this.selectedQuestId) {
            detailEl.innerHTML = '<div class="ql-detail-placeholder">Выберите задание</div>';
            return;
        }

        const quest = this._quests.find(q => q.id === this.selectedQuestId);
        if (!quest) {
            detailEl.innerHTML = '<div class="ql-detail-placeholder">Задание не найдено</div>';
            return;
        }

        const statusLabel = this.STATUS_LABELS[quest.status] || quest.status;
        const statusColor = this.STATUS_COLORS[quest.status] || '#c9b896';

        // Objectives
        let objectivesHtml = '';
        const objectives = quest.objectives || [];
        if (objectives.length > 0) {
            objectivesHtml = `
                <div class="ql-detail-section">
                    <div class="ql-detail-section-title">Цели</div>
                    ${objectives.map(obj => {
                        const current = obj.current_count !== undefined ? obj.current_count : (obj.current || 0);
                        const target = obj.target_count !== undefined ? obj.target_count : (obj.target || 1);
                        const completed = obj.completed || current >= target;
                        const progress = target > 1 ? `(${current}/${target})` : '';
                        const desc = obj.description_ru || obj.description || '';
                        const optionalTag = obj.optional ? ' <span class="ql-optional">(необязательно)</span>' : '';

                        return `
                            <div class="ql-objective ${completed ? 'completed' : ''}">
                                <span class="ql-obj-check">${completed ? '&#10003;' : '&#9675;'}</span>
                                <span class="ql-obj-desc">${desc}${optionalTag}</span>
                                ${progress ? `<span class="ql-obj-progress">${progress}</span>` : ''}
                                ${target > 1 ? `
                                    <div class="ql-obj-bar">
                                        <div class="ql-obj-fill" style="width: ${Math.min(100, (current / target) * 100)}%"></div>
                                    </div>
                                ` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }

        // Rewards
        let rewardsHtml = '';
        const rewards = quest.rewards || {};
        const hasRewards = rewards.experience || rewards.gold || (rewards.items && rewards.items.length > 0);
        if (hasRewards) {
            let rewardItems = [];
            if (rewards.experience) rewardItems.push(`<span class="ql-reward-item">&#9733; ${rewards.experience} XP</span>`);
            if (rewards.gold) rewardItems.push(`<span class="ql-reward-item">&#9679; ${rewards.gold} зол.</span>`);
            if (rewards.items) {
                rewards.items.forEach(item => {
                    rewardItems.push(`<span class="ql-reward-item">&#8226; ${item.name || item.id} x${item.count || 1}</span>`);
                });
            }

            rewardsHtml = `
                <div class="ql-detail-section">
                    <div class="ql-detail-section-title">Награды</div>
                    <div class="ql-rewards">${rewardItems.join('')}</div>
                </div>
            `;
        }

        // Abandon button (only for active quests)
        let abandonBtn = '';
        if (quest.status === 'active') {
            abandonBtn = `<button class="btn btn-secondary ql-abandon-btn" id="ql-abandon-btn">Отказаться</button>`;
        }

        detailEl.innerHTML = `
            <div class="ql-detail-header">
                <div class="ql-detail-name">${quest.name_ru || quest.name || quest.id}</div>
                <div class="ql-detail-status" style="color: ${statusColor}">${statusLabel}</div>
            </div>

            <div class="ql-detail-desc">${quest.description_ru || quest.description || ''}</div>

            ${objectivesHtml}
            ${rewardsHtml}

            ${abandonBtn ? `<div class="ql-detail-actions">${abandonBtn}</div>` : ''}
        `;

        // Bind abandon
        const abBtn = document.getElementById('ql-abandon-btn');
        if (abBtn) {
            abBtn.addEventListener('click', () => {
                PythonAPI.call('quest_abandon', { quest_id: quest.id });
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
                case 'quest_list':
                    this._quests = data?.quests || [];
                    if (this.element && !this.element.classList.contains('hidden')) {
                        this._renderQuestList();
                        if (this.selectedQuestId) this._renderQuestDetail();
                    }
                    break;

                case 'quest_accepted':
                case 'quest_completed':
                case 'quest_ready_to_turn_in':
                    // Request refreshed quest list
                    PythonAPI.call('quest_list_request', { filter: 'all' });
                    break;

                case 'quest_objective_progress': {
                    // Update objective in-place
                    const quest = this._quests.find(q => q.id === data?.quest_id);
                    if (quest) {
                        const obj = (quest.objectives || []).find(o => o.id === data?.objective_id);
                        if (obj) {
                            obj.current = data.current;
                            obj.current_count = data.current;
                            obj.completed = obj.current >= (obj.target_count || obj.target || 1);
                        }
                        if (this.element && !this.element.classList.contains('hidden')) {
                            this._renderQuestList();
                            if (this.selectedQuestId === data.quest_id) this._renderQuestDetail();
                        }
                    }
                    break;
                }
            }
        });
    }
}
