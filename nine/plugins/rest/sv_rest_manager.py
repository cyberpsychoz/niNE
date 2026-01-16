"""
Серверный модуль управления отдыхом.

Обрабатывает:
- Short Rest: трата Hit Dice для лечения
- Long Rest: полное восстановление
"""

import random
from typing import Dict, Optional

from nine.core.plugins import PluginModule
from .sh_rest_data import RestType, RestResult, get_hit_die


class RestManagerServerModule(PluginModule):
    """
    Серверный модуль управления отдыхом.
    """

    def on_load(self):
        # Подписки на события
        self.event_manager.subscribe("rest_request", self._on_rest_request)
        self.event_manager.subscribe("spend_hit_die", self._on_spend_hit_die)

        self.logger.info("Rest Manager серверный модуль загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("rest_request", self._on_rest_request)
        self.event_manager.unsubscribe("spend_hit_die", self._on_spend_hit_die)

        self.logger.info("Rest Manager серверный модуль выгружен")

    # =========================================================================
    # Rest Processing
    # =========================================================================

    def _on_rest_request(self, data: dict):
        """Запрос на отдых."""
        client_id = data.get("client_id", -1)
        rest_type = data.get("rest_type", "short")

        # Получаем данные персонажа
        char_data = self._get_character_data(client_id)
        if not char_data:
            self._send_rest_result(client_id, None, "No character data")
            return

        if rest_type == "long":
            result = self._process_long_rest(client_id, char_data)
        else:
            result = self._process_short_rest(client_id, char_data)

        self._send_rest_result(client_id, result)

    def _process_short_rest(self, client_id: int, char_data: dict) -> RestResult:
        """Обрабатывает короткий отдых."""
        result = RestResult(
            rest_type="short",
            hp_new=char_data.get("hp_current", 0),
            hp_max=char_data.get("hp_max", 1),
            hit_dice_remaining=char_data.get("hit_dice_current", 1),
            hit_dice_max=char_data.get("hit_dice_max", 1),
        )

        # Публикуем событие для других систем (например, Warlock восстанавливает слоты)
        self.event_manager.post("short_rest_completed", {
            "client_id": client_id,
        })

        self.logger.info(f"Client {client_id} completed short rest")

        return result

    def _process_long_rest(self, client_id: int, char_data: dict) -> RestResult:
        """Обрабатывает длинный отдых."""
        hp_max = char_data.get("hp_max", 1)
        hp_current = char_data.get("hp_current", 0)
        hit_dice_max = char_data.get("hit_dice_max", 1)
        hit_dice_current = char_data.get("hit_dice_current", 1)

        # Полное восстановление HP
        hp_restored = hp_max - hp_current

        # Восстанавливаем половину Hit Dice (минимум 1)
        hit_dice_to_restore = max(1, hit_dice_max // 2)
        hit_dice_new = min(hit_dice_current + hit_dice_to_restore, hit_dice_max)

        result = RestResult(
            rest_type="long",
            hp_restored=hp_restored,
            hp_new=hp_max,
            hp_max=hp_max,
            hit_dice_remaining=hit_dice_new,
            hit_dice_max=hit_dice_max,
            spell_slots_restored=True,
        )

        # Обновляем данные персонажа
        self._update_character_data(client_id, {
            "hp_current": hp_max,
            "hit_dice_current": hit_dice_new,
        })

        # Публикуем событие для других систем
        self.event_manager.post("long_rest_completed", {
            "client_id": client_id,
        })

        # Снимаем некоторые состояния (exhaustion снижается на 1)
        self.event_manager.post("reduce_exhaustion", {
            "entity_id": str(client_id),
            "amount": 1,
        })

        self.logger.info(f"Client {client_id} completed long rest (restored {hp_restored} HP)")

        return result

    def _on_spend_hit_die(self, data: dict):
        """Трата Hit Die для лечения во время Short Rest."""
        client_id = data.get("client_id", -1)
        count = data.get("count", 1)

        char_data = self._get_character_data(client_id)
        if not char_data:
            return

        hit_dice_current = char_data.get("hit_dice_current", 0)
        if hit_dice_current <= 0:
            self._send_to_client(client_id, {
                "type": "hit_die_result",
                "success": False,
                "message": "No hit dice remaining",
            })
            return

        # Определяем размер кубика по классу
        char_class = char_data.get("class", "fighter")
        die_size = get_hit_die(char_class)

        # Получаем модификатор Constitution
        con_mod = self._get_ability_modifier(client_id, "CON")

        # Бросаем кубик
        total_healing = 0
        dice_spent = 0

        for _ in range(min(count, hit_dice_current)):
            roll = random.randint(1, die_size)
            healing = max(1, roll + con_mod)  # Минимум 1 HP
            total_healing += healing
            dice_spent += 1
            hit_dice_current -= 1

        # Применяем лечение
        hp_current = char_data.get("hp_current", 0)
        hp_max = char_data.get("hp_max", 1)
        new_hp = min(hp_current + total_healing, hp_max)

        # Обновляем данные персонажа
        self._update_character_data(client_id, {
            "hp_current": new_hp,
            "hit_dice_current": hit_dice_current,
        })

        self.logger.info(
            f"Client {client_id} spent {dice_spent} hit dice, healed {total_healing} HP "
            f"({hp_current} -> {new_hp})"
        )

        self._send_to_client(client_id, {
            "type": "hit_die_result",
            "success": True,
            "dice_spent": dice_spent,
            "healing": total_healing,
            "hp_new": new_hp,
            "hp_max": hp_max,
            "hit_dice_remaining": hit_dice_current,
            "hit_dice_max": char_data.get("hit_dice_max", 1),
        })

        # Обновляем character sheet
        self._send_character_update(client_id)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _get_character_data(self, client_id: int) -> Optional[dict]:
        """Получает данные персонажа."""
        if hasattr(self.app, 'authenticated_clients'):
            auth_data = self.app.authenticated_clients.get(client_id, {})
            return auth_data.get("character_data")
        return None

    def _update_character_data(self, client_id: int, updates: dict):
        """Обновляет данные персонажа."""
        if hasattr(self.app, 'authenticated_clients'):
            auth_data = self.app.authenticated_clients.get(client_id, {})
            char_data = auth_data.get("character_data", {})
            char_data.update(updates)

    def _get_ability_modifier(self, client_id: int, ability: str) -> int:
        """Получает модификатор способности."""
        char_data = self._get_character_data(client_id)
        if not char_data:
            return 0

        # Способности хранятся как отдельные поля или в словаре
        ability_lower = ability.lower()
        ability_map = {
            "str": "strength",
            "dex": "dexterity",
            "con": "constitution",
            "int": "intelligence",
            "wis": "wisdom",
            "cha": "charisma",
        }

        field_name = ability_map.get(ability_lower, ability_lower)
        score = char_data.get(field_name, 10)
        return (score - 10) // 2

    def _send_rest_result(self, client_id: int, result: Optional[RestResult], error: str = ""):
        """Отправляет результат отдыха."""
        if result:
            self._send_to_client(client_id, {
                "type": "rest_result",
                "success": True,
                "rest_type": result.rest_type,
                "hp_restored": result.hp_restored,
                "hp_new": result.hp_new,
                "hp_max": result.hp_max,
                "hit_dice_remaining": result.hit_dice_remaining,
                "hit_dice_max": result.hit_dice_max,
                "spell_slots_restored": result.spell_slots_restored,
            })
        else:
            self._send_to_client(client_id, {
                "type": "rest_result",
                "success": False,
                "error": error,
            })

    def _send_character_update(self, client_id: int):
        """Отправляет обновление персонажа."""
        char_data = self._get_character_data(client_id)
        if char_data:
            self._send_to_client(client_id, {
                "type": "character_sheet",
                "character": char_data,
            })

    def _send_to_client(self, client_id: int, message: dict):
        """Отправляет сообщение клиенту."""
        if hasattr(self.app, 'send_to_client'):
            self.app.send_to_client(client_id, message)
        else:
            self.event_manager.post(f"send_to_client_{client_id}", message)
