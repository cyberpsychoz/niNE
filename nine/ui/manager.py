# nine/ui/manager.py
from direct.gui.DirectGui import DGG
from panda3d.core import TextNode, Loader

# Импортируем наши новые компоненты
from .main_menu import MainMenu
from .login_menu import LoginMenu
from .in_game_menu import InGameMenu
from .settings_menu import SettingsMenu # <--- ADD THIS LINE
# TODO: Добавить сюда другие компоненты, как console, ingame_menu и т.д.

class UIManager:
    """
    Новый менеджер UI.
    Действует как контроллер, управляя жизненным циклом отдельных компонентов UI.
    """
    def __init__(self, base, callbacks: dict):
        self.base = base
        self.callbacks = callbacks # Callbacks из client.py
        self.loader = base.loader
        
        # Настройка стилей по умолчанию
        self.font = self._load_font()
        DGG.setDefaultFont(self.font)
        TextNode.setDefaultEncoding(TextNode.EUtf8)

        # Контейнеры для активных компонентов
        self.active_components = {}
        self._create_persistent_components()

    def _create_persistent_components(self):
        """Создает компоненты, которые должны существовать всегда."""
        pass

    def _load_font(self):
        """Загружает кастомный шрифт."""
        font_path = "nine/assets/fonts/DejaVuSans.ttf"
        try:
            font = self.loader.loadFont(font_path)
            font.setPixelsPerUnit(100)
            return font
        except Exception:
            return DGG.getDefaultFont()

    def _destroy_component(self, name: str):
        """Уничтожает компонент и удаляет его из активных."""
        if name in self.active_components:
            self.active_components[name].destroy()
            del self.active_components[name]
    
    # --- Управление главным меню ---
    def show_main_menu(self):
        self._destroy_component('login_menu')
        self._destroy_component('settings_menu') # <--- ADD THIS LINE to ensure settings menu is hidden
        if 'main_menu' not in self.active_components:
            self.active_components['main_menu'] = MainMenu(self)

    def hide_main_menu(self):
        self._destroy_component('main_menu')

    # --- Управление меню логина ---
    def show_login_menu(self, default_ip, default_name):
        self.hide_main_menu()
        if 'login_menu' not in self.active_components:
            self.active_components['login_menu'] = LoginMenu(self, default_ip, default_name)

    def hide_login_menu(self):
        self._destroy_component('login_menu')

    def get_login_credentials(self) -> dict:
        if 'login_menu' in self.active_components:
            return self.active_components['login_menu'].get_credentials()
        return {}

    # --- Управление In-Game Меню ---
    def show_in_game_menu(self, client):
        if 'in_game_menu' not in self.active_components:
            self.active_components['in_game_menu'] = InGameMenu(self, client)
            self.active_components['in_game_menu'].show()

    def hide_in_game_menu(self):
        self._destroy_component('in_game_menu')

    # --- Управление Меню Настроек ---
    def show_settings_menu(self, client):
        self.hide_main_menu() # Hide main menu when showing settings
        if 'settings_menu' not in self.active_components:
            self.active_components['settings_menu'] = SettingsMenu(self, client)
            self.active_components['settings_menu'].show()

    def hide_settings_menu(self):
        self._destroy_component('settings_menu')

    # --- Общее ---
    def destroy_all(self):
        """Уничтожает все UI и пересоздает постоянные компоненты."""
        for name in list(self.active_components.keys()):
            self._destroy_component(name)
        
        self.active_components.clear()
        
        # Пересоздаем постоянные компоненты для следующей сессии
        self._create_persistent_components()
