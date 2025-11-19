from nine.core.plugins import BasePlugin, MessageReceivedEvent, ClientDisconnectedEvent

class InventoryPlugin(BasePlugin):
    """
    Управляет инвентарем игроков.
    - Загружает инвентарь при входе.
    - Сохраняет инвентарь при выходе.
    - Добавляет команду /inventory для просмотра инвентаря.
    """
    name = "Inventory"

    def on_load(self):
        self.inventories = {}  # {player_uuid: [items]}
        print(f"Плагин '{self.name}' загружен.")

    def on_message_received(self, event: MessageReceivedEvent):
        msg_type = event.data.get("type")
        client_id = event.client_id

        if msg_type == "auth":
            # Игрок аутентифицировался, загружаем его инвентарь
            player_uuid = event.data.get("uuid")
            if player_uuid:
                inventory = self.app.db.get_player_inventory(player_uuid)
                if inventory is None:
                    # Если инвентаря нет, создаем пустой
                    inventory = ["Old bread", "Rusty sword"]
                    self.app.db.save_player_inventory(player_uuid, inventory)
                
                self.inventories[player_uuid] = inventory
                print(f"[Inventory] Инвентарь для {player_uuid} загружен: {inventory}")

        elif msg_type == "chat_message":
            # Проверяем на команды
            message = event.data.get("message", "").strip()
            if message == "/inventory":
                player_uuid = self.app.client_id_to_uuid.get(client_id)
                if player_uuid and player_uuid in self.inventories:
                    player_inventory = self.inventories[player_uuid]
                    # Отправляем сообщение обратно игроку
                    # Для этого нужен новый тип сообщения или использовать существующий чат
                    response_text = f"Инвентарь: {', '.join(player_inventory) if player_inventory else 'пусто'}"
                    
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

        if player_uuid and player_uuid in self.inventories:
            # Сохраняем инвентарь и удаляем из памяти
            inventory_to_save = self.inventories[player_uuid]
            self.app.db.save_player_inventory(player_uuid, inventory_to_save)
            print(f"[Inventory] Инвентарь для {player_uuid} сохранен.")
            del self.inventories[player_uuid]
