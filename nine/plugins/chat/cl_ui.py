"""
Клиентский модуль UI чата.
Отображает окно чата и обрабатывает ввод пользователя.
"""

from direct.showbase.DirectObject import DirectObject
from nine.core.plugins import PluginModule
from nine.ui.chat_window import ChatWindow


class ChatUIModule(PluginModule, DirectObject):
    """
    Клиентский модуль UI чата.
    Создает окно чата, обрабатывает ввод и отображает сообщения.
    """

    def on_load(self):
        self.logger.info("Клиентский модуль UI чата загружен")

        # Инициализация UI
        # app.ui - экземпляр UIManager
        self.ui_window = ChatWindow(self.app.ui)

        # Callbacks и события
        self.ui_window.on_send_callback = self.send_chat_message
        self.event_manager.subscribe("chat_broadcast", self.add_incoming_message)

        # Keybindings
        self.accept('t', self.ui_window.toggle_input)

        # Monkey-patch для проверки активности чата
        self.app.is_chat_active = self.is_active

    def on_unload(self):
        # Отписываемся от клавиш
        self.ignoreAll()

        # Отписываемся от событий
        if self.event_manager:
            self.event_manager.unsubscribe("chat_broadcast", self.add_incoming_message)

        # Уничтожаем UI
        if self.ui_window:
            self.ui_window.destroy()

        # Очищаем monkey-patch
        if hasattr(self.app, 'is_chat_active'):
            del self.app.is_chat_active

        self.logger.info("Клиентский модуль UI чата выгружен")

    def send_chat_message(self, message: str):
        """Отправка сообщения через event system."""
        self.event_manager.post("client_send_chat_message", message)
        # Скрываем ввод после отправки
        self.ui_window.toggle_input()

    def add_incoming_message(self, data: dict):
        """Обработка входящего сообщения от сервера."""
        self.ui_window.add_message(data['from_name'], data['message'])

    def is_active(self) -> bool:
        """Активно ли поле ввода чата."""
        if not self.ui_window:
            return False
        return self.ui_window.is_visible()
