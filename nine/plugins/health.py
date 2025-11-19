from nine.core.plugins import BasePlugin, MessageReceivedEvent, ClientDisconnectedEvent

class HealthPlugin(BasePlugin):
    """
    Управляет здоровьем игроков.
    - Загружает здоровье при входе.
    - Сохраняет здоровье при выходе.
    - Добавляет команду /hp для проверки здоровья.
    """
    name = "Health"
    DEFAULT_HEALTH = 100

    def on_load(self):
        self.health_data = {}  # {player_uuid: int}
        print(f"Плагин '{self.name}' загружен.")

    def on_message_received(self, event: MessageReceivedEvent):
        msg_type = event.data.get("type")
        client_id = event.client_id

        if msg_type == "auth":
            # Игрок аутентифицировался, загружаем его здоровье
            player_uuid = event.data.get("uuid")
            if player_uuid:
                health = self.app.db.get_player_attribute(player_uuid, "health")
                if health is None:
                    health = self.DEFAULT_HEALTH
                
                self.health_data[player_uuid] = health
                print(f"[Health] Здоровье для {player_uuid} загружено: {health}")

        elif msg_type == "chat_message":
            # Проверяем на команды
            message = event.data.get("message", "").strip()
            if message == "/hp":
                player_uuid = self.app.client_id_to_uuid.get(client_id)
                if player_uuid and player_uuid in self.health_data:
                    player_health = self.health_data[player_uuid]
                    
                    response_text = f"Здоровье: {player_health}/{self.DEFAULT_HEALTH}"
                    
                    response_data = {
                        "type": "chat_broadcast",
                        "from_name": "System",
                        "message": response_text
                    }
                    # Отправляем только этому клиенту
                    self.app.asyncio_loop.create_task(
                        self.app.network.send_message(client_id, response_data)
                    )

    def on_client_disconnected(self, event: ClientDisconnectedEvent):
        client_id = event.client_id
        player_uuid = self.app.client_id_to_uuid.get(client_id)

        if player_uuid and player_uuid in self.health_data:
            # Сохраняем здоровье и удаляем из памяти
            health_to_save = self.health_data[player_uuid]
            self.app.db.set_player_attribute(player_uuid, "health", health_to_save)
            print(f"[Health] Здоровье для {player_uuid} сохранено.")
            del self.health_data[player_uuid]
