from nine.core.plugins import BasePlugin
from nine.core.network import MessageReceivedEvent

class ChatPlugin(BasePlugin):
    """
    Простой плагин чата, который рассылает сообщения всем клиентам.
    Работает через подписку на кастомное событие.
    """
    name = "Chat"

    def on_load(self):
        """Подписывается на событие чата при загрузке."""
        self.event_manager.subscribe("server_on_chat_message", self.handle_chat_message)
        print(f"Плагин '{self.name}' загружен и подписан на 'server_on_chat_message'.")

    def on_unload(self):
        """Отписывается от события при выгрузке."""
        self.event_manager.unsubscribe("server_on_chat_message", self.handle_chat_message)
        print(f"Плагин '{self.name}' выгружен.")

    def handle_chat_message(self, event_data: dict):
        """
        Обрабатывает событие с сообщением чата.
        event_data приходит из server.py и содержит {'client_id': ..., 'data': ...}
        """
        client_id = event_data.get("client_id")
        data = event_data.get("data", {})
        message = data.get("message", "")

        if not message or client_id is None:
            return

        sender_name = self.app.players.get(client_id, {}).get('name', f'Player {client_id}')
        print(f"[ChatPlugin] Получено сообщение от {sender_name}: {message}")

        broadcast_data = {
            "type": "chat_broadcast",
            "from_name": sender_name,
            "message": message
        }

        # Отправляем событие для рассылки всем
        self.event_manager.post(
            "server_broadcast",
            {"data": broadcast_data}
        )
