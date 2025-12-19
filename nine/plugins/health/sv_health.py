"""
Серверный модуль системы здоровья.
Управляет здоровьем игроков на сервере.
"""

from typing import Dict
from nine.core.plugins import PluginModule
from .sh_constants import DEFAULT_HEALTH, MAX_HEALTH, MIN_HEALTH


class HealthServerModule(PluginModule):
    """
    Серверный модуль управления здоровьем.
    Отслеживает здоровье игроков и обрабатывает урон.
    """

    def on_load(self):
        self.health_data: Dict[str, int] = {}  # {player_uuid: health}

        # Подписки на события
        self.event_manager.subscribe("player_joined", self.on_player_join)
        self.event_manager.subscribe("player_left", self.on_player_leave)
        self.event_manager.subscribe("player_damage", self.on_player_damage)
        self.event_manager.subscribe("player_heal", self.on_player_heal)

        self.logger.info("Серверный модуль здоровья загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("player_joined", self.on_player_join)
        self.event_manager.unsubscribe("player_left", self.on_player_leave)
        self.event_manager.unsubscribe("player_damage", self.on_player_damage)
        self.event_manager.unsubscribe("player_heal", self.on_player_heal)

        self.logger.info("Серверный модуль здоровья выгружен")

    def on_player_join(self, data: dict):
        """Игрок присоединился - инициализируем здоровье."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        # TODO: Загрузить здоровье из БД
        # Пока устанавливаем дефолтное значение
        self.health_data[player_uuid] = DEFAULT_HEALTH

        self.logger.debug(f"Здоровье игрока {player_uuid}: {DEFAULT_HEALTH}")

    def on_player_leave(self, data: dict):
        """Игрок вышел - сохраняем и очищаем данные."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        # TODO: Сохранить здоровье в БД
        if player_uuid in self.health_data:
            del self.health_data[player_uuid]

    def on_player_damage(self, data: dict):
        """Игрок получил урон."""
        player_uuid = data.get("uuid")
        damage = data.get("damage", 0)
        damage_type = data.get("damage_type", "physical")

        if player_uuid not in self.health_data:
            return

        # Применяем урон
        old_health = self.health_data[player_uuid]
        new_health = max(MIN_HEALTH, old_health - damage)
        self.health_data[player_uuid] = new_health

        self.logger.debug(
            f"Игрок {player_uuid} получил {damage} урона ({damage_type}): "
            f"{old_health} -> {new_health}"
        )

        # Отправляем обновление клиенту
        self.event_manager.post("health_updated", {
            "uuid": player_uuid,
            "health": new_health,
            "max_health": MAX_HEALTH,
            "damage": damage,
            "damage_type": damage_type,
        })

        # Проверяем смерть
        if new_health <= MIN_HEALTH:
            self.event_manager.post("player_death", {
                "uuid": player_uuid,
                "cause": damage_type,
            })

    def on_player_heal(self, data: dict):
        """Игрок получил лечение."""
        player_uuid = data.get("uuid")
        heal_amount = data.get("amount", 0)

        if player_uuid not in self.health_data:
            return

        # Применяем лечение
        old_health = self.health_data[player_uuid]
        new_health = min(MAX_HEALTH, old_health + heal_amount)
        self.health_data[player_uuid] = new_health

        self.logger.debug(
            f"Игрок {player_uuid} исцелен на {heal_amount}: "
            f"{old_health} -> {new_health}"
        )

        # Отправляем обновление клиенту
        self.event_manager.post("health_updated", {
            "uuid": player_uuid,
            "health": new_health,
            "max_health": MAX_HEALTH,
            "healed": heal_amount,
        })

    def get_health(self, player_uuid: str) -> int:
        """Получить текущее здоровье игрока."""
        return self.health_data.get(player_uuid, 0)

    def set_health(self, player_uuid: str, health: int):
        """Установить здоровье игрока напрямую."""
        if player_uuid in self.health_data:
            self.health_data[player_uuid] = max(MIN_HEALTH, min(MAX_HEALTH, health))
