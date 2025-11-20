from nine.core.plugins import BasePlugin

class ChatPlugin(BasePlugin):
    """
    Плагин для кастомизации чата.
    Основная логика чата теперь находится в server.py.
    Этот плагин можно использовать для изменения цветов,
    добавления команд или другой кастомизации.
    """
    name = "Chat"

    def on_load(self):
        # В будущем здесь можно будет подписаться на события,
        # например, 'chat_message_broadcasted', чтобы изменить сообщение
        # или добавить префикс.
        print(f"Плагин '{self.name}' загружен (логика в ядре).")

    def on_unload(self):
        pass
