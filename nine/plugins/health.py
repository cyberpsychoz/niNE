from nine.core.plugins import BasePlugin

class HealthPlugin(BasePlugin):
    """
    Управляет здоровьем игроков.
    - Загружает здоровье при входе.
    - Сохраняет здоровье при выходе.
    - Добавляет команду /hp для проверки здоровья.
    
    NOTE: Функциональность временно отключена для совместимости с новой
          архитектурой плагинов. Требуется рефакторинг с использованием
          прямых подписок на события.
    """
    name = "Health"
    DEFAULT_HEALTH = 100

    def on_load(self):
        self.health_data = {}  # {player_uuid: int}
        print(f"Плагин '{self.name}' загружен (функциональность отключена).")

    # def on_message_received(self, event: MessageReceivedEvent):
    #     ... (логика закомментирована до рефакторинга)

    # def on_client_disconnected(self, event: ClientDisconnectedEvent):
    #     ... (логика закомментирована до рефакторинга)
