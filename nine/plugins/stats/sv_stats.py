"""
Серверный модуль системы характеристик.
Управляет здоровьем и голодом игроков на сервере.
"""

import importlib.util
from pathlib import Path
from typing import Dict
from nine.core.plugins import PluginModule


def _load_constants():
    """Загружает константы из sh_constants.py в той же папке."""
    constants_path = Path(__file__).parent / "sh_constants.py"
    spec = importlib.util.spec_from_file_location("stats_constants", constants_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_constants = _load_constants()
DEFAULT_HEALTH = _constants.DEFAULT_HEALTH
MAX_HEALTH = _constants.MAX_HEALTH
MIN_HEALTH = _constants.MIN_HEALTH
DEFAULT_HUNGER = _constants.DEFAULT_HUNGER
MAX_HUNGER = _constants.MAX_HUNGER
MIN_HUNGER = _constants.MIN_HUNGER
HUNGER_DECAY_RATE = _constants.HUNGER_DECAY_RATE
HUNGER_DAMAGE_THRESHOLD = _constants.HUNGER_DAMAGE_THRESHOLD
HUNGER_DAMAGE_RATE = _constants.HUNGER_DAMAGE_RATE


class StatsServerModule(PluginModule):
    """
    Серверный модуль управления характеристиками.
    Отслеживает здоровье и голод игроков.
    """

    def on_load(self):
        # {player_uuid: {"health": int, "hunger": int}}
        self.stats_data: Dict[str, dict] = {}
        self._hunger_timer = 0.0

        # Подписки на события
        self.event_manager.subscribe("player_joined", self.on_player_join)
        self.event_manager.subscribe("player_left", self.on_player_leave)
        self.event_manager.subscribe("player_damage", self.on_player_damage)
        self.event_manager.subscribe("player_heal", self.on_player_heal)
        self.event_manager.subscribe("player_feed", self.on_player_feed)
        self.event_manager.subscribe("stats_request", self.on_stats_request)

        self.logger.info("Серверный модуль характеристик загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("player_joined", self.on_player_join)
        self.event_manager.unsubscribe("player_left", self.on_player_leave)
        self.event_manager.unsubscribe("player_damage", self.on_player_damage)
        self.event_manager.unsubscribe("player_heal", self.on_player_heal)
        self.event_manager.unsubscribe("player_feed", self.on_player_feed)
        self.event_manager.unsubscribe("stats_request", self.on_stats_request)

        self.logger.info("Серверный модуль характеристик выгружен")

    def on_player_join(self, data: dict):
        """Игрок присоединился - инициализируем характеристики."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        self.stats_data[player_uuid] = {
            "health": DEFAULT_HEALTH,
            "hunger": DEFAULT_HUNGER,
        }

        # Отправляем начальные значения клиенту
        self._send_stats_update(player_uuid)
        self.logger.debug(f"Характеристики игрока {player_uuid} инициализированы")

    def on_player_leave(self, data: dict):
        """Игрок вышел - сохраняем и очищаем данные."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        # TODO: Сохранить в БД
        if player_uuid in self.stats_data:
            del self.stats_data[player_uuid]

    def on_stats_request(self, data: dict):
        """Клиент запросил свои характеристики."""
        player_uuid = data.get("uuid")
        if player_uuid:
            self._send_stats_update(player_uuid)

    def on_player_damage(self, data: dict):
        """Игрок получил урон."""
        player_uuid = data.get("uuid")
        damage = data.get("damage", 0)
        damage_type = data.get("damage_type", "physical")

        if player_uuid not in self.stats_data:
            return

        stats = self.stats_data[player_uuid]
        old_health = stats["health"]
        new_health = max(MIN_HEALTH, old_health - damage)
        stats["health"] = new_health

        self.logger.debug(
            f"Игрок {player_uuid} получил {damage} урона: {old_health} -> {new_health}"
        )

        self._send_stats_update(player_uuid)

        if new_health <= MIN_HEALTH:
            self.event_manager.post("player_death", {
                "uuid": player_uuid,
                "cause": damage_type,
            })

    def on_player_heal(self, data: dict):
        """Игрок получил лечение."""
        player_uuid = data.get("uuid")
        amount = data.get("amount", 0)

        if player_uuid not in self.stats_data:
            return

        stats = self.stats_data[player_uuid]
        old_health = stats["health"]
        new_health = min(MAX_HEALTH, old_health + amount)
        stats["health"] = new_health

        self.logger.debug(
            f"Игрок {player_uuid} исцелен на {amount}: {old_health} -> {new_health}"
        )

        self._send_stats_update(player_uuid)

    def on_player_feed(self, data: dict):
        """Игрок поел."""
        player_uuid = data.get("uuid")
        amount = data.get("amount", 0)

        if player_uuid not in self.stats_data:
            return

        stats = self.stats_data[player_uuid]
        old_hunger = stats["hunger"]
        new_hunger = min(MAX_HUNGER, old_hunger + amount)
        stats["hunger"] = new_hunger

        self.logger.debug(
            f"Игрок {player_uuid} поел на {amount}: {old_hunger} -> {new_hunger}"
        )

        self._send_stats_update(player_uuid)

    def _send_stats_update(self, player_uuid: str):
        """Отправляет обновление характеристик клиенту."""
        if player_uuid not in self.stats_data:
            return

        stats = self.stats_data[player_uuid]
        self.event_manager.post("stats_updated", {
            "uuid": player_uuid,
            "health": stats["health"],
            "max_health": MAX_HEALTH,
            "hunger": stats["hunger"],
            "max_hunger": MAX_HUNGER,
        })

    # Публичные методы
    def get_health(self, player_uuid: str) -> int:
        stats = self.stats_data.get(player_uuid, {})
        return stats.get("health", 0)

    def get_hunger(self, player_uuid: str) -> int:
        stats = self.stats_data.get(player_uuid, {})
        return stats.get("hunger", 0)

    def set_health(self, player_uuid: str, value: int):
        if player_uuid in self.stats_data:
            self.stats_data[player_uuid]["health"] = max(MIN_HEALTH, min(MAX_HEALTH, value))
            self._send_stats_update(player_uuid)

    def set_hunger(self, player_uuid: str, value: int):
        if player_uuid in self.stats_data:
            self.stats_data[player_uuid]["hunger"] = max(MIN_HUNGER, min(MAX_HUNGER, value))
            self._send_stats_update(player_uuid)
