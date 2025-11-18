from nine.core.plugins import BasePlugin, MessageReceivedEvent

class ChatPlugin(BasePlugin):
    """
    Простой плагин чата, который рассылает сообщения всем клиентам.
    """
    name = "Chat"

    def on_load(self):
        print(f"Плагин '{self.name}' загружен.")

    def on_message_received(self, event: MessageReceivedEvent):
        """
        Обрабатывает входящие сообщения от клиентов.
        """
        if event.data.get("type") == "chat_message":
            message = event.data.get("message", "")
            if not message:
                return

            print(f"[ChatPlugin] Получено сообщение от клиента {event.client_id}: {message}")

            broadcast_data = {
                "type": "chat_broadcast",
                "from_client": event.client_id,
                "message": message
            }

            # Отправляем событие для рассылки всем, кроме отправителя
            self.event_manager.post(
                "server_broadcast",
                {"data": broadcast_data, "exclude_ids": [event.client_id]}
            )
