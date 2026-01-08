"""
Серверный модуль плагина.

Этот файл загружается ТОЛЬКО на сервере.
Используйте для игровой логики, обработки данных игроков, физики и т.д.
"""
from nine.core.plugins import PluginModule
from typing import Dict, Any


class ServerModule(PluginModule):
    """
    Серверный модуль обрабатывает игровую логику.

    События, на которые подписывается:
    - player_joined: Инициализация данных игрока
    - player_left: Очистка данных игрока
    - app_tick: Обновление логики (осторожно, вызывается каждый тик!)

    События, которые отправляет:
    - author.plugin_name.data_updated: Когда данные обновлены
    """

    def on_load(self):
        """
        Вызывается при загрузке модуля.
        Подпишитесь на события и инициализируйте данные здесь.
        """
        self.logger.info("🔧 Серверный модуль загружен")

        # Инициализация данных модуля
        self.player_data: Dict[str, Any] = {}

        # Подписка на события
        self.event_manager.subscribe("player_joined", self.on_player_joined)
        self.event_manager.subscribe("player_left", self.on_player_left)

        # Доступ к shared_data
        self.context.shared_data["server_module"] = self

        # Доступ к серверу
        # self.app.world - GameWorld (физика, игроки)
        # self.app.clients - Подключенные клиенты

    def on_unload(self):
        """
        Вызывается при выгрузке модуля.
        ОБЯЗАТЕЛЬНО отпишитесь от событий!
        """
        # Отписка от событий
        self.event_manager.unsubscribe("player_joined", self.on_player_joined)
        self.event_manager.unsubscribe("player_left", self.on_player_left)

        # Очистка данных
        self.player_data.clear()

        self.logger.info("🔧 Серверный модуль выгружен")

    # ========================================================================
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # ========================================================================

    def on_player_joined(self, data: dict):
        """
        Обработчик события player_joined.

        Args:
            data (dict): Данные события
                - id (int): ID игрока
                - name (str): Имя игрока
                - pos (list): Позиция спавна [x, y, z]
                - uuid (str): UUID игрока
        """
        player_id = data.get("id")
        player_name = data.get("name", "Unknown")
        player_uuid = str(player_id)

        self.logger.info(f"👤 Игрок {player_name} (ID: {player_id}) присоединился")

        # Инициализация данных игрока
        self.player_data[player_uuid] = {
            "name": player_name,
            "score": 0,
            "joined_at": self.get_current_time()
        }

        # Отправка приветствия
        self.send_welcome_message(player_id, player_name)

    def on_player_left(self, data: dict):
        """
        Обработчик события player_left.

        Args:
            data (dict): Данные события
                - id (int): ID игрока
        """
        player_id = data.get("id")
        player_uuid = str(player_id)

        self.logger.info(f"👋 Игрок {player_id} покинул сервер")

        # Очистка данных игрока
        if player_uuid in self.player_data:
            del self.player_data[player_uuid]

    # ========================================================================
    # МЕТОДЫ МОДУЛЯ
    # ========================================================================

    def send_welcome_message(self, player_id: int, player_name: str):
        """
        Отправляет приветственное сообщение в чат.

        Args:
            player_id: ID игрока
            player_name: Имя игрока
        """
        message = f"Добро пожаловать, {player_name}!"

        self.event_manager.post("chat_send_to_clients", {
            "data": {
                "type": "system",
                "sender": "Система",
                "message": message,
                "color": (0.5, 1.0, 0.5, 1.0)  # Зеленый
            },
            "recipients": [player_id]  # Только этому игроку
        })

    def get_current_time(self) -> float:
        """Получить текущее время (timestamp)."""
        import time
        return time.time()

    def get_player_data(self, player_uuid: str) -> dict:
        """
        Получить данные игрока.

        Args:
            player_uuid: UUID игрока

        Returns:
            Словарь с данными или пустой словарь
        """
        return self.player_data.get(player_uuid, {})

    def update_player_score(self, player_uuid: str, score_delta: int):
        """
        Обновить счет игрока.

        Args:
            player_uuid: UUID игрока
            score_delta: Изменение счета (может быть отрицательным)
        """
        if player_uuid in self.player_data:
            self.player_data[player_uuid]["score"] += score_delta

            # Отправить событие об обновлении
            self.event_manager.post("author.plugin_name.score_updated", {
                "uuid": player_uuid,
                "score": self.player_data[player_uuid]["score"]
            })

            self.logger.info(f"Счет игрока {player_uuid}: {self.player_data[player_uuid]['score']}")
