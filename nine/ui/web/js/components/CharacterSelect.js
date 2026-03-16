/**
 * Character Select Component
 *
 * Displays list of player's characters for selection.
 */

class CharacterSelect {
    constructor(params = {}) {
        this.params = params;
        this.element = null;
        this.characters = params.characters || [];
        this.selectedCharacter = null;

        console.log('[CharacterSelect] Created');
    }

    async render() {
        // Load template
        const response = await fetch('templates/character-select.html');
        const html = await response.text();

        // Insert into DOM
        const app = document.getElementById('app');
        app.innerHTML = html;

        // Get element references
        this.element = document.getElementById('character-select-screen');
        this.characterList = document.getElementById('character-list');
        this.selectBtn = document.getElementById('btn-select');

        // Render character list
        this._renderCharacters();

        // Attach event listeners
        this.attachEventListeners();

        // Listen for updates from Python
        this.pythonMessageHandler = this._handlePythonMessage.bind(this);
        window.addEventListener('python-message', this.pythonMessageHandler);

        console.log('[CharacterSelect] Rendered');
    }

    /**
     * Handle messages from Python.
     */
    _handlePythonMessage(event) {
        const { type, data } = event.detail;

        if (type === 'update_characters') {
            this.characters = data.characters || [];
            this._renderCharacters();
        }
    }

    /**
     * Render character list.
     */
    _renderCharacters() {
        if (this.characters.length === 0) {
            this.characterList.innerHTML = `
                <p style="color: var(--color-text-hint); text-align: center;">
                    Персонажи не найдены. Создайте первого персонажа!
                </p>
            `;
            return;
        }

        this.characterList.innerHTML = '';

        this.characters.forEach((char) => {
            const card = document.createElement('div');
            card.className = 'character-card';
            card.dataset.charId = char.uuid;

            card.innerHTML = `
                <div class="name">${char.character_name}</div>
                <div class="details">
                    ${char.race} ${char.class || ''} — Уровень ${char.level || 1}
                </div>
                <button class="char-delete-btn" data-uuid="${char.uuid}" title="Удалить персонажа">&times;</button>
            `;

            card.addEventListener('click', (e) => {
                if (e.target.classList.contains('char-delete-btn')) return;
                this._selectCharacter(char);
            });

            const delBtn = card.querySelector('.char-delete-btn');
            if (delBtn) {
                delBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this._confirmDelete(char);
                });
            }

            this.characterList.appendChild(card);
        });
    }

    /**
     * Select a character.
     */
    _selectCharacter(char) {
        this.selectedCharacter = char;

        // Update UI
        document.querySelectorAll('.character-card').forEach(card => {
            if (card.dataset.charId === String(char.uuid)) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
        });

        // Enable select button
        this.selectBtn.disabled = false;
    }

    _confirmDelete(char) {
        // Show inline confirmation instead of alert() (CEF offscreen has no alert)
        const existing = document.getElementById('delete-confirm-overlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.id = 'delete-confirm-overlay';
        overlay.className = 'panel-overlay';
        overlay.innerHTML = `
            <div class="panel-container" style="width:400px;padding:24px;text-align:center;">
                <div class="panel-header"><span class="panel-title">УДАЛИТЬ ПЕРСОНАЖА?</span></div>
                <p style="color:var(--color-text-primary);margin:16px 0;">
                    Вы уверены, что хотите удалить <strong>${char.character_name}</strong>? Это действие необратимо.
                </p>
                <div style="display:flex;gap:8px;justify-content:center;">
                    <button class="bg1-button admin-btn-darkred" id="confirm-delete-yes">УДАЛИТЬ</button>
                    <button class="bg1-button" id="confirm-delete-no">ОТМЕНА</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        document.getElementById('confirm-delete-yes').addEventListener('click', () => {
            console.log('[CharacterSelect] Deleting character:', char.uuid);
            PythonAPI.deleteCharacter(char.uuid);
            overlay.remove();
        });
        document.getElementById('confirm-delete-no').addEventListener('click', () => {
            overlay.remove();
        });
    }

    attachEventListeners() {
        // Select button
        this.selectBtn.addEventListener('click', () => {
            if (this.selectedCharacter) {
                console.log('[CharacterSelect] Character selected:', this.selectedCharacter.uuid);
                PythonAPI.selectCharacter(this.selectedCharacter.uuid);
            }
        });

        // Create button
        const createBtn = document.getElementById('btn-create');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                console.log('[CharacterSelect] Create new character');
                window.router.navigate('character-create');
            });
        }

        // Back button (disconnect)
        const backBtn = document.getElementById('btn-back');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                console.log('[CharacterSelect] Disconnect');
                PythonAPI.disconnect();
            });
        }

        console.log('[CharacterSelect] Event listeners attached');
    }

    /**
     * Clean up and destroy the component.
     */
    destroy() {
        window.removeEventListener('python-message', this.pythonMessageHandler);

        if (this.element) {
            this.element.remove();
            this.element = null;
        }

        console.log('[CharacterSelect] Destroyed');
    }
}

// Register with router
window.router.registerScreen('character-select', CharacterSelect);
