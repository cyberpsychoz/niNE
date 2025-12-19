"""
Серверный модуль чата.
Обрабатывает и рассылает сообщения чата.
"""

from nine.core.plugins import PluginModule


class ChatBroadcastModule(PluginModule):
    """
    Серверный модуль для обработки и рассылки сообщений чата.
    Основная логика чата находится в ядре сервера (game_server.py).
    Этот модуль можно использовать для кастомизации сообщений.
    """

    def on_load(self):
        self.logger.info("Серверный модуль чата загружен")
        # В будущем: подписка на события для модификации сообщений
        # self.event_manager.subscribe("chat_message_pre_broadcast", self.modify_message)

    def on_unload(self):
        # self.event_manager.unsubscribe("chat_message_pre_broadcast", self.modify_message)
        pass

    def modify_message(self, data):
        """
        Пример хука для модификации сообщений.
        Можно добавлять префиксы, фильтровать слова и т.д.
        """
        # message = data.get('message', '')
        # from_name = data.get('from_name', '')
        # Логика кастомизации сообщений
        pass
