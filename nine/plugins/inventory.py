from nine.core.plugins import BasePlugin

class InventoryPlugin(BasePlugin):
    """
    Управляет инвентарем игроков.
    - Загружает инвентарь при входе.
    - Сохраняет инвентарь при выходе.
    - Добавляет команду /inventory для просмотра инвентаря.
    
    NOTE: Функциональность временно отключена для совместимости с новой
          архитектурой плагинов. Требуется рефакторинг с использованием
          прямых подписок на события.
    """
    name = "Inventory"

    def on_load(self):
        self.inventories = {}  # {player_uuid: [items]}
        print(f"Плагин '{self.name}' загружен (функциональность отключена).")

    # def on_message_received(self, event: MessageReceivedEvent):
    #     ... (логика закомментирована до рефакторинга)

    # def on_client_disconnected(self, event: ClientDisconnectedEvent):
    #     ... (логика закомментирована до рефакторинга)
