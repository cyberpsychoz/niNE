/**
 * Settings Menu Component
 *
 * Multi-tab settings menu with General, Graphics, Audio, and Controls tabs.
 */

class SettingsMenu {
    constructor(params = {}) {
        this.params = params;
        this.element = null;

        console.log('[SettingsMenu] Created');
    }

    async render() {
        // Load template
        const response = await fetch('templates/settings-menu.html');
        const html = await response.text();

        // Insert into DOM
        const app = document.getElementById('app');
        app.innerHTML = html;

        // Get element reference
        this.element = document.getElementById('settings-menu-screen');

        // Load current settings from params (with async fallback)
        await this.loadSettings();

        // Attach event listeners
        this.attachEventListeners();

        // Attach slider value updates
        this.attachSliderListeners();

        // Replace native <select> with custom dropdowns (CEF offscreen fix)
        if (window.initCustomSelects) initCustomSelects();

        console.log('[SettingsMenu] Rendered');
    }

    /**
     * Load settings from params, falling back to Python API.
     */
    async loadSettings() {
        let settings = this.params.settings;
        if (!settings) {
            try {
                settings = await PythonAPI.getSettings();
                console.log('[SettingsMenu] Settings loaded from Python API');
            } catch (e) {
                console.warn('[SettingsMenu] Failed to load settings from API:', e);
                settings = {};
            }
        }
        if (!settings) settings = {};

        // General
        this.setInputValue('setting-nickname', settings.nickname || 'Player');
        this.setSelectValue('setting-resolution', settings.resolution || '1920x1080');

        // Graphics
        this.setSliderValue('setting-fov', settings.fov || 70);
        this.setCheckboxValue('setting-ps1-effect', settings.ps1_effect_enabled || false);
        this.setSliderValue('setting-ps1-res', settings.ps1_effect_resolution || 2);

        // Audio
        this.setSliderValue('setting-volume-master', settings.audio_master_volume ?? 100);
        this.setSliderValue('setting-volume-bgm', settings.audio_bgm_volume ?? 100);
        this.setSliderValue('setting-volume-sfx', settings.audio_sfx_volume ?? 100);

        // Controls
        this.setSliderValue('setting-camera-sens', settings.camera_sensitivity || 1.0, true);
        this.setCheckboxValue('setting-invert-x', settings.invert_mouse_x || false);
        this.setCheckboxValue('setting-invert-y', settings.invert_mouse_y || false);
        this.setCheckboxValue('setting-third-person', settings.third_person_camera !== false);

        console.log('[SettingsMenu] Settings loaded');
    }

    /**
     * Set input value.
     */
    setInputValue(id, value) {
        const el = document.getElementById(id);
        if (el) el.value = value;
    }

    /**
     * Set select value.
     */
    setSelectValue(id, value) {
        const el = document.getElementById(id);
        if (el) el.value = value;
    }

    /**
     * Set checkbox value.
     */
    setCheckboxValue(id, checked) {
        const el = document.getElementById(id);
        if (el) el.checked = checked;
    }

    /**
     * Set slider value and update display.
     */
    setSliderValue(id, value, isFloat = false) {
        const slider = document.getElementById(id);
        const valueDisplay = document.getElementById(`${id}-value`);

        if (slider) {
            slider.value = value;
        }
        if (valueDisplay) {
            valueDisplay.textContent = isFloat ? parseFloat(value).toFixed(2) : Math.round(value);
        }
    }

    attachEventListeners() {
        // Tab switching
        const tabs = document.querySelectorAll('.tab-btn');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                this.switchTab(tab.dataset.tab);
            });
        });

        // Save button
        const saveBtn = document.getElementById('btn-save');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveSettings();
            });
        }

        // Back button
        const backBtn = document.getElementById('btn-back');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                console.log('[SettingsMenu] Back clicked');
                window.router.navigate('main-menu');
            });
        }

        console.log('[SettingsMenu] Event listeners attached');
    }

    /**
     * Attach slider value update listeners.
     */
    attachSliderListeners() {
        const sliders = [
            { id: 'setting-fov', isFloat: false },
            { id: 'setting-ps1-res', isFloat: false },
            { id: 'setting-volume-master', isFloat: false },
            { id: 'setting-volume-bgm', isFloat: false },
            { id: 'setting-volume-sfx', isFloat: false },
            { id: 'setting-camera-sens', isFloat: true }
        ];

        sliders.forEach(({ id, isFloat }) => {
            const slider = document.getElementById(id);
            const valueDisplay = document.getElementById(`${id}-value`);

            if (slider && valueDisplay) {
                slider.addEventListener('input', () => {
                    const value = isFloat
                        ? parseFloat(slider.value).toFixed(2)
                        : Math.round(slider.value);
                    valueDisplay.textContent = value;
                });
            }
        });
    }

    /**
     * Switch to a different tab.
     */
    switchTab(tabName) {
        // Update tab buttons
        const tabs = document.querySelectorAll('.tab-btn');
        tabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Update tab content
        const contents = document.querySelectorAll('.tab-content');
        contents.forEach(content => {
            content.classList.toggle('active', content.id === `tab-${tabName}`);
        });

        console.log(`[SettingsMenu] Switched to tab: ${tabName}`);
    }

    /**
     * Collect and save settings.
     */
    async saveSettings() {
        const settings = {
            // General
            nickname: document.getElementById('setting-nickname').value.trim(),
            resolution: document.getElementById('setting-resolution').value,

            // Graphics
            fov: parseInt(document.getElementById('setting-fov').value),
            ps1_effect_enabled: document.getElementById('setting-ps1-effect').checked,
            ps1_effect_resolution: parseInt(document.getElementById('setting-ps1-res').value),

            // Audio
            audio_master_volume: parseInt(document.getElementById('setting-volume-master').value),
            audio_bgm_volume: parseInt(document.getElementById('setting-volume-bgm').value),
            audio_sfx_volume: parseInt(document.getElementById('setting-volume-sfx').value),

            // Controls
            camera_sensitivity: parseFloat(document.getElementById('setting-camera-sens').value),
            invert_mouse_x: document.getElementById('setting-invert-x').checked,
            invert_mouse_y: document.getElementById('setting-invert-y').checked,
            third_person_camera: document.getElementById('setting-third-person').checked,
        };

        console.log('[SettingsMenu] Saving settings:', settings);

        try {
            await PythonAPI.saveSettings(settings);
            this.showSaveConfirmation();
        } catch (e) {
            console.error('[SettingsMenu] Save failed:', e);
        }
    }

    /**
     * Show save confirmation.
     */
    showSaveConfirmation() {
        const saveBtn = document.getElementById('btn-save');
        if (saveBtn) {
            const originalText = saveBtn.innerHTML;
            saveBtn.innerHTML = '<span class="btn-icon">&#10003;</span> SAVED!';
            saveBtn.style.pointerEvents = 'none';

            setTimeout(() => {
                saveBtn.innerHTML = originalText;
                saveBtn.style.pointerEvents = '';
            }, 1500);
        }
    }

    /**
     * Clean up and destroy the component.
     */
    destroy() {
        if (this.element) {
            this.element.remove();
            this.element = null;
        }
        console.log('[SettingsMenu] Destroyed');
    }
}

// Register with router
window.router.registerScreen('settings-menu', SettingsMenu);
