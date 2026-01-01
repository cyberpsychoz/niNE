"""
Клиентский модуль UI чата.
Отображает окно чата в стиле Garry's Mod.
Поддерживает RP команды: /me, /it, /looc, /ooc
"""

import importlib.util
from pathlib import Path

from direct.showbase.DirectObject import DirectObject
from nine.core.game_state import GameState
from nine.core.plugins import PluginModule
from nine.ui.chat_window import ChatWindow


def _load_config(plugin_path: Path):
    """Загружает конфиг из папки плагина."""
    config_path = plugin_path / "sh_config.py"
    if not config_path.exists():
        return None

    spec = importlib.util.spec_from_file_location("chat_config", config_path)
    if spec is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ChatUIModule(PluginModule, DirectObject):
    """
    Клиентский модуль UI чата.

    Режимы работы:
    - Закрытый: сообщения появляются и fade out
    - Открытый (T): полная история + ввод

    Поддерживаемые типы сообщений:
    - ic: обычный внутриигровой чат
    - emote: /me действие
    - it: /it безличное действие
    - looc: локальный OOC
    - ooc: глобальный OOC

    Конфигурация загружается из sh_config.py
    """

    def on_load(self):
        self.logger.info("Клиентский модуль UI чата загружен")

        # Загружаем конфиг из папки плагина
        self.config = _load_config(self.plugin_path)

        # Инициализация UI с конфигом из плагина
        self.ui_window = ChatWindow(self.app.ui, config=self.config)

        # Callback для отправки сообщений
        self.ui_window.on_send_callback = self.send_chat_message

        # Подписываемся на события
        self.event_manager.subscribe("chat_broadcast", self.on_chat_broadcast)
        self.event_manager.subscribe("client_disconnected", self.on_disconnect)
        self.event_manager.subscribe("game_state_changed", self.on_game_state_changed)

        # Keybindings
        self.accept('t', self.on_chat_key)
        self.accept('escape', self.on_escape_key)

        # Предоставляем методы клиенту
        self.app.is_chat_active = self.is_active
        self.app.chat_window = self.ui_window

        # Скрываем чат при старте если мы в меню
        if self.app.ui.game_state == GameState.MENU:
            self._hide_chat_ui()

    def on_unload(self):
        # Отписываемся от клавиш
        self.ignoreAll()

        # Отписываемся от событий
        if self.event_manager:
            self.event_manager.unsubscribe("chat_broadcast", self.on_chat_broadcast)
            self.event_manager.unsubscribe("client_disconnected", self.on_disconnect)
            self.event_manager.unsubscribe("game_state_changed", self.on_game_state_changed)

        # Уничтожаем UI
        if self.ui_window:
            self.ui_window.destroy()
            self.ui_window = None

        # Очищаем ссылки
        if hasattr(self.app, 'is_chat_active'):
            del self.app.is_chat_active
        if hasattr(self.app, 'chat_window'):
            del self.app.chat_window

        self.logger.info("Клиентский модуль UI чата выгружен")

    def on_game_state_changed(self, data: dict):
        """Обработка смены состояния игры."""
        new_state = data.get("new_state")

        if new_state == GameState.MENU:
            # Скрываем чат в меню
            self._hide_chat_ui()
        elif new_state == GameState.IN_GAME:
            # Показываем чат в игре
            self._show_chat_ui()

    def _hide_chat_ui(self):
        """Скрывает UI чата."""
        if self.ui_window and hasattr(self.ui_window, 'root'):
            self.ui_window.root.hide()
            # Закрываем чат если он открыт
            if self.ui_window.is_open():
                self.ui_window.close()
            self.logger.debug("UI чата скрыт")

    def _show_chat_ui(self):
        """Показывает UI чата."""
        if self.ui_window and hasattr(self.ui_window, 'root'):
            self.ui_window.root.show()
            self.logger.debug("UI чата показан")

    def on_chat_key(self):
        """Нажатие T - открыть чат."""
        # Не открываем чат если мы в меню
        if self.app.ui.game_state != GameState.IN_GAME:
            return

        if not self.ui_window.is_open():
            self.ui_window.open()

    def on_escape_key(self):
        """Нажатие Escape - закрыть чат если открыт."""
        if self.ui_window.is_open():
            self.ui_window.close()

    def send_chat_message(self, message: str):
        """Отправка сообщения через event system."""
        self.event_manager.post("client_send_chat_message", message)

    def on_chat_broadcast(self, data: dict):
        """Обработка входящего сообщения от сервера."""
        sender = data.get('from_name', 'Unknown')
        message = data.get('message', '')
        chat_type = data.get('chat_type', 'ic')
        formatted_message = data.get('formatted_message')
        is_system = data.get('is_system', False)

        # Передаем в UI с типом сообщения
        self.ui_window.add_rp_message(
            sender=sender,
            message=message,
            chat_type=chat_type,
            formatted_message=formatted_message,
            is_system=is_system
        )

    def on_disconnect(self, data: dict = None):
        """При отключении от сервера - очищаем историю."""
        if self.ui_window:
            self.ui_window.clear_history()
            self.logger.debug("История чата очищена при отключении")

    def is_active(self) -> bool:
        """Активно ли поле ввода чата."""
        if not self.ui_window:
            return False
        return self.ui_window.is_open()
