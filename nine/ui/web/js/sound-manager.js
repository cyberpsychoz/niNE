/**
 * SoundManager — HTML5 Audio for menu BGM and UI sounds.
 *
 * Uses the CEF HTTP server to serve audio assets from /assets/.
 * Independent of Panda3D AudioManager (which loads after login).
 */

class SoundManager {
    constructor() {
        this.bgm = null;
        this.bgmVolume = 0.69;
        this.masterVolume = 0.65;
        this.uiVolume = 0.70;
        this.uiEnabled = true;

        // Pre-loaded hover/click buffers
        this._hoverBuffer = null;
        this._clickBuffer = null;
    }

    async init() {
        // Load volumes from config
        try {
            const s = await PythonAPI.getSettings();
            this.masterVolume = (s.audio_master_volume ?? 65) / 100;
            this.bgmVolume = (s.audio_bgm_volume ?? 69) / 100;
            this.uiVolume = (s.audio_ui_volume ?? 70) / 100;
            this.uiEnabled = s.ui_sounds_enabled !== false;
        } catch (e) {
            console.warn('[SoundManager] Could not load settings, using defaults');
        }

        // Listen for events from Python
        window.addEventListener('python-message', (e) => {
            const { type, data } = e.detail;
            if (type === 'game_state_changed') {
                const st = data.new_state || data.state || '';
                if (st === 'IN_GAME') this.stopMenuMusic();
            } else if (type === 'audio_volume_changed') {
                this.masterVolume = data.master_volume ?? this.masterVolume;
                this.bgmVolume = data.bgm_volume ?? this.bgmVolume;
                this.uiVolume = data.ui_volume ?? this.uiVolume;
                if (this.bgm) {
                    this.bgm.volume = this.masterVolume * this.bgmVolume;
                }
            }
        });

        // Global button sounds via event delegation (capture phase)
        document.addEventListener('mouseenter', (e) => {
            if (e.target.closest('.btn, .tab-btn, .hud-action-btn, button')) {
                this.playHover();
            }
        }, true);

        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn, .tab-btn, .hud-action-btn, button')) {
                this.playClick();
            }
        }, true);

        console.log('[SoundManager] Initialized');
    }

    playMenuMusic() {
        if (this.bgm) return;
        this._startBgm();
    }

    _startBgm() {
        this.bgm = new Audio('/assets/materials/sounds/bgm/show_me_the_sky.mp3');
        this.bgm.loop = true;
        this.bgm.volume = this.masterVolume * this.bgmVolume;
        this.bgm.play().then(() => {
            console.log('[SoundManager] Menu music started');
        }).catch(() => {
            // Autoplay blocked — wait for first user interaction to start
            console.log('[SoundManager] Autoplay blocked, waiting for user gesture');
            this.bgm = null;
            const resumeOnClick = () => {
                document.removeEventListener('click', resumeOnClick, true);
                if (!this.bgm) this._startBgm();
            };
            document.addEventListener('click', resumeOnClick, true);
        });
    }

    stopMenuMusic() {
        if (!this.bgm) return;
        this.bgm.pause();
        this.bgm = null;
        console.log('[SoundManager] Menu music stopped');
    }

    playHover() {
        if (!this.uiEnabled) return;
        const s = new Audio('/assets/materials/sounds/ui/Fantasy/Fantasy_UI (1).wav');
        s.volume = this.masterVolume * this.uiVolume * 0.5;
        s.play().catch(() => {});
    }

    playClick() {
        if (!this.uiEnabled) return;
        const s = new Audio('/assets/materials/sounds/ui/Fantasy/Fantasy_UI (10).wav');
        s.volume = this.masterVolume * this.uiVolume * 0.7;
        s.play().catch(() => {});
    }
}

window.soundManager = new SoundManager();
