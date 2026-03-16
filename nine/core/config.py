# nine/core/config.py
import json
from pathlib import Path

class Config:
    """
    Handles loading and saving application configuration.
    """
    _instance = None
    CONFIG_FILE = Path("config.json")
    
    DEFAULT_SETTINGS = {
<<<<<<< HEAD
        "nickname": "Player",
        "resolution": "1280x720",
        "available_resolutions": ["800x600", "1024x768", "1280x720", "1920x1080"]
=======
        # Общие
        "nickname": "Player",
        "resolution": "1280x720",
        "available_resolutions": ["800x600", "1024x768", "1280x720", "1920x1080"],
        # Управление
        "camera_sensitivity": 1.0,
        "invert_mouse_x": False,
        "invert_mouse_y": False,
        "third_person_camera": True,  # True = от третьего лица, False = от первого лица
        # Графика
        "fov": 70,  # Поле зрения (для first-person)
        "ps1_effect_enabled": False,  # PS1-стиль пикселизация
        "ps1_effect_resolution": 1,   # 0=Low (320x240), 1=Medium (640x480), 2=High (800x600)
        # Звук
        "audio_master_volume": 100,  # Общая громкость (0-100)
        "audio_bgm_volume": 70,      # Громкость музыки (0-100)
        "audio_sfx_volume": 80,      # Громкость звуковых эффектов (0-100)
        "audio_ambient_volume": 60,  # Громкость эмбиента/окружения (0-100)
        "audio_ui_volume": 70,       # Громкость звуков интерфейса (0-100)
        "ui_sound_pack": "fantasy",  # Звуковой пак UI: fantasy, piano, skyward
        "ui_sounds_enabled": True,   # Включить звуки интерфейса
>>>>>>> main-core-engine
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._settings = cls.DEFAULT_SETTINGS.copy()
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Loads configuration from config.json."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    loaded_settings = json.load(f)
                    self._settings.update(loaded_settings)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config file: {e}. Using default settings.")
        else:
            self._save_config() # Create config file with defaults if it doesn't exist

    def _save_config(self):
        """Saves current configuration to config.json."""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self._settings, f, indent=4)
        except IOError as e:
            print(f"Error saving config file: {e}")

    def get(self, key: str, default=None):
        """Retrieves a setting by key."""
        return self._settings.get(key, default)

    def set(self, key: str, value):
        """Sets a setting by key and saves the config."""
        self._settings[key] = value
        self._save_config()

# Global instance for easy access
config = Config()
