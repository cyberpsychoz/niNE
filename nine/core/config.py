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
        "nickname": "Player",
        "resolution": "1280x720",
        "available_resolutions": ["800x600", "1024x768", "1280x720", "1920x1080"]
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
