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
                    No characters found. Create your first character!
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
                    ${char.race} ${char.class || ''} — Level ${char.level || 1}
                </div>
            `;

            card.addEventListener('click', () => {
                this._selectCharacter(char);
            });

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
