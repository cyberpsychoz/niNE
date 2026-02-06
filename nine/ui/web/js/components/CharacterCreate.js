/**
 * Character Create Component
 *
 * D&D 5e character creation form.
 */

class CharacterCreate {
    constructor(params = {}) {
        this.params = params;
        this.element = null;

        console.log('[CharacterCreate] Created');
    }

    async render() {
        // Load template
        const response = await fetch('templates/character-create.html');
        const html = await response.text();

        // Insert into DOM
        const app = document.getElementById('app');
        app.innerHTML = html;

        // Get element references
        this.element = document.getElementById('character-create-screen');
        this.nameInput = document.getElementById('input-char-name');
        this.raceSelect = document.getElementById('input-race');
        this.classSelect = document.getElementById('input-class');
        this.backgroundInput = document.getElementById('input-background');

        // Attach event listeners
        this.attachEventListeners();

        // Focus name input
        this.nameInput.focus();

        console.log('[CharacterCreate] Rendered');
    }

    attachEventListeners() {
        // Create button
        const createBtn = document.getElementById('btn-create-char');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                this.createCharacter();
            });
        }

        // Cancel button
        const cancelBtn = document.getElementById('btn-cancel');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                console.log('[CharacterCreate] Cancel');
                window.router.navigate('character-select');
            });
        }

        console.log('[CharacterCreate] Event listeners attached');
    }

    /**
     * Create character.
     */
    createCharacter() {
        const name = this.nameInput.value.trim();
        const race = this.raceSelect.value;
        const className = this.classSelect.value;
        const background = this.backgroundInput.value.trim();

        // Validation
        if (!name) {
            alert('Please enter a character name');
            this.nameInput.focus();
            return;
        }

        const characterData = {
            name,
            race,
            class_name: className,
            background: background || 'None'
        };

        console.log('[CharacterCreate] Creating character:', characterData);

        // TODO: Send to Python
        // PythonAPI.createCharacter(characterData);

        // For now, go back to character select
        alert(`Character "${name}" created!\n(Placeholder - not implemented yet)`);
        window.router.navigate('character-select');
    }

    /**
     * Clean up and destroy the component.
     */
    destroy() {
        if (this.element) {
            this.element.remove();
            this.element = null;
        }

        console.log('[CharacterCreate] Destroyed');
    }
}

// Register with router
window.router.registerScreen('character-create', CharacterCreate);
