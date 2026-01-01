# nine/ui/manager.py
"""
Менеджер UI с системой игровых состояний.
Управляет жизненным циклом UI компонентов и переходами между состояниями.
"""

from direct.gui.DirectGui import DGG
from panda3d.core import TextNode

from nine.core.game_state import GameState
from .theme import NineTheme
from .main_menu import MainMenu
from .login_menu import LoginMenu
from .in_game_menu import InGameMenu
from .settings_menu import SettingsMenu


class UIManager:
    """
    Менеджер UI с поддержкой игровых состояний.

    Управляет:
    - Жизненным циклом UI компонентов
    - Переходами между состояниями (MENU, CONNECTING, IN_GAME)
    - Событиями смены состояния для плагинов
    """

    def __init__(self, base, callbacks: dict):
        self.base = base
        self.callbacks = callbacks
        self.loader = base.loader
        self.event_manager = base.event_manager

        # Текущее состояние игры
        self._game_state = GameState.MENU

        # Настройка стилей по умолчанию
        self.font = self._load_font()
        DGG.setDefaultFont(self.font)
        TextNode.setDefaultEncoding(TextNode.EUtf8)

        # Контейнеры для активных компонентов
        self.active_components = {}

    def _load_font(self):
        """Загружает пиксельный шрифт."""
        try:
            font = self.loader.loadFont(NineTheme.FONT_PATH)
            font.setPixelsPerUnit(NineTheme.FONT_PIXELS_PER_UNIT)
            # Отключаем сглаживание для пиксельного вида
            font.setMinfilter(0)  # FT_nearest
            font.setMagfilter(0)  # FT_nearest
            return font
        except Exception:
            # Fallback на старый шрифт
            try:
                font = self.loader.loadFont("nine/assets/fonts/DejaVuSans.ttf")
                font.setPixelsPerUnit(100)
                return font
            except Exception:
                return DGG.getDefaultFont()

    def _destroy_component(self, name: str):
        """Уничтожает компонент и удаляет его из активных."""
        if name in self.active_components:
            self.active_components[name].destroy()
            del self.active_components[name]

    # ========== Управление состояниями ==========

    @property
    def game_state(self) -> GameState:
        """Возвращает текущее состояние игры."""
        return self._game_state

    def set_game_state(self, state: GameState):
        """
        Устанавливает новое состояние игры и уведомляет подписчиков.

        Args:
            state: Новое состояние (GameState.MENU, IN_GAME, etc.)
        """
        if self._game_state == state:
            return

        old_state = self._game_state
        self._game_state = state

        # Уведомляем плагины о смене состояния
        self.event_manager.post("game_state_changed", {
            "old_state": old_state,
            "new_state": state,
        })

    # ========== Управление главным меню ==========

    def show_main_menu(self):
        """Показывает главное меню."""
        self._destroy_component('login_menu')
        self._destroy_component('settings_menu')
        self._destroy_component('in_game_menu')

        if 'main_menu' not in self.active_components:
            self.active_components['main_menu'] = MainMenu(self)
        else:
            # Показываем существующее меню (если было скрыто)
            self.active_components['main_menu'].show()

        self.set_game_state(GameState.MENU)

    def hide_main_menu(self):
        """Скрывает главное меню."""
        self._destroy_component('main_menu')

    # ========== Управление меню логина ==========

    def show_login_menu(self, default_ip, default_name):
        """Показывает меню входа."""
        # Только скрываем главное меню, не уничтожаем (для быстрого возврата)
        if 'main_menu' in self.active_components:
            self.active_components['main_menu'].hide()

        if 'login_menu' not in self.active_components:
            self.active_components['login_menu'] = LoginMenu(self, default_ip, default_name)

    def hide_login_menu(self):
        """Скрывает меню входа и возвращает главное меню."""
        self._destroy_component('login_menu')
        # Показываем главное меню обратно
        if 'main_menu' in self.active_components:
            self.active_components['main_menu'].show()

    def get_login_credentials(self) -> dict:
        """Возвращает введённые данные для входа."""
        if 'login_menu' in self.active_components:
            return self.active_components['login_menu'].get_credentials()
        return {}

    # ========== Управление In-Game меню ==========

    def show_in_game_menu(self, client):
        """Показывает игровое меню паузы."""
        if 'in_game_menu' not in self.active_components:
            self.active_components['in_game_menu'] = InGameMenu(self, client)
            self.active_components['in_game_menu'].show()

    def hide_in_game_menu(self):
        """Скрывает игровое меню паузы."""
        self._destroy_component('in_game_menu')

    # ========== Управление меню настроек ==========

    def show_settings_menu(self, client):
        """Показывает меню настроек."""
        # Только скрываем главное меню, не уничтожаем (для быстрого возврата)
        if 'main_menu' in self.active_components:
            self.active_components['main_menu'].hide()

        if 'settings_menu' not in self.active_components:
            self.active_components['settings_menu'] = SettingsMenu(self, client)
            self.active_components['settings_menu'].show()

    def hide_settings_menu(self):
        """Скрывает меню настроек и возвращает главное меню."""
        self._destroy_component('settings_menu')
        # Показываем главное меню обратно
        if 'main_menu' in self.active_components:
            self.active_components['main_menu'].show()

    # ========== Переход в игру ==========

    def enter_game(self):
        """Переход в игровое состояние (после подключения к серверу)."""
        self.hide_main_menu()
        self.hide_login_menu()
        self.set_game_state(GameState.IN_GAME)

    def exit_game(self):
        """Выход из игры обратно в меню."""
        self.set_game_state(GameState.MENU)

    # ========== Общее ==========

    def destroy_all(self):
        """Уничтожает все UI компоненты."""
        for name in list(self.active_components.keys()):
            self._destroy_component(name)
        self.active_components.clear()
