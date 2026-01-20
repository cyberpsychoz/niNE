"""
Серверный модуль управления состояниями.

Обрабатывает:
- Применение/снятие состояний
- Отслеживание длительности
- Интеграцию с боевой системой
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

from nine.core.plugins import PluginModule
from nine.plugins.conditions.sh_conditions import get_condition, get_combined_effects, CONDITIONS


@dataclass
class ActiveCondition:
    """Активное состояние на существе."""
    condition_id: str
    source_id: str  # ID источника (кто наложил)
    duration_rounds: int  # -1 = бессрочно
    save_dc: int = 0  # DC для спасброска в конце хода
    save_ability: str = ""  # Способность для спасброска


@dataclass
class EntityConditions:
    """Состояния существа."""
    entity_id: str
    conditions: Dict[str, ActiveCondition] = field(default_factory=dict)

    def add_condition(self, condition: ActiveCondition) -> bool:
        """Добавляет состояние. Возвращает True если добавлено новое."""
        cond_id = condition.condition_id
        if cond_id in self.conditions:
            # Обновляем длительность если новая больше
            if condition.duration_rounds > self.conditions[cond_id].duration_rounds:
                self.conditions[cond_id].duration_rounds = condition.duration_rounds
            return False
        self.conditions[cond_id] = condition
        return True

    def remove_condition(self, condition_id: str) -> bool:
        """Удаляет состояние. Возвращает True если было удалено."""
        if condition_id in self.conditions:
            del self.conditions[condition_id]
            return True
        return False

    def has_condition(self, condition_id: str) -> bool:
        """Проверяет наличие состояния."""
        return condition_id in self.conditions

    def get_all_condition_ids(self) -> List[str]:
        """Возвращает список ID всех активных состояний."""
        return list(self.conditions.keys())

    def tick_durations(self) -> List[str]:
        """Уменьшает длительность. Возвращает список истёкших состояний."""
        expired = []
        for cond_id, cond in list(self.conditions.items()):
            if cond.duration_rounds > 0:
                cond.duration_rounds -= 1
                if cond.duration_rounds <= 0:
                    expired.append(cond_id)
                    del self.conditions[cond_id]
        return expired


class ConditionManagerServerModule(PluginModule):
    """
    Серверный модуль управления состояниями.
    """

    def on_load(self):
        # entity_id -> EntityConditions
        self._entity_conditions: Dict[str, EntityConditions] = {}

        # Подписки на события
        self.event_manager.subscribe("apply_condition", self._on_apply_condition)
        self.event_manager.subscribe("remove_condition", self._on_remove_condition)
        self.event_manager.subscribe("apply_buff", self._on_apply_buff)
        self.event_manager.subscribe("remove_buff", self._on_remove_buff)

        # Интеграция с боем
        self.event_manager.subscribe("combat_turn_start", self._on_turn_start)
        self.event_manager.subscribe("combat_turn_end", self._on_turn_end)
        self.event_manager.subscribe("entity_death", self._on_entity_death)

        # Запросы от клиента
        self.event_manager.subscribe("conditions_request", self._on_conditions_request)

        # Модификаторы для боевой системы
        self.event_manager.subscribe("get_attack_modifiers", self._on_get_attack_modifiers)
        self.event_manager.subscribe("get_save_modifiers", self._on_get_save_modifiers)
        self.event_manager.subscribe("check_can_act", self._on_check_can_act)

        self.logger.info("Condition Manager серверный модуль загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("apply_condition", self._on_apply_condition)
        self.event_manager.unsubscribe("remove_condition", self._on_remove_condition)
        self.event_manager.unsubscribe("apply_buff", self._on_apply_buff)
        self.event_manager.unsubscribe("remove_buff", self._on_remove_buff)
        self.event_manager.unsubscribe("combat_turn_start", self._on_turn_start)
        self.event_manager.unsubscribe("combat_turn_end", self._on_turn_end)
        self.event_manager.unsubscribe("entity_death", self._on_entity_death)
        self.event_manager.unsubscribe("conditions_request", self._on_conditions_request)
        self.event_manager.unsubscribe("get_attack_modifiers", self._on_get_attack_modifiers)
        self.event_manager.unsubscribe("get_save_modifiers", self._on_get_save_modifiers)
        self.event_manager.unsubscribe("check_can_act", self._on_check_can_act)

        self.logger.info("Condition Manager серверный модуль выгружен")

    # =========================================================================
    # Condition Application
    # =========================================================================

    def _on_apply_condition(self, data: dict):
        """Применяет состояние к существу."""
        target_id = data.get("target_id", "")
        condition_id = data.get("condition", "").lower()
        source_id = data.get("source_id", "")
        duration_rounds = data.get("duration_rounds", -1)
        save_dc = data.get("save_dc", 0)
        save_ability = data.get("save_ability", "")

        if not target_id or not condition_id:
            return

        # Проверяем, существует ли такое состояние
        condition_def = get_condition(condition_id)
        if not condition_def:
            self.logger.warning(f"Unknown condition: {condition_id}")
            return

        # Получаем или создаём запись для существа
        if target_id not in self._entity_conditions:
            self._entity_conditions[target_id] = EntityConditions(entity_id=target_id)

        entity = self._entity_conditions[target_id]

        # Создаём активное состояние
        active_cond = ActiveCondition(
            condition_id=condition_id,
            source_id=source_id,
            duration_rounds=duration_rounds,
            save_dc=save_dc,
            save_ability=save_ability,
        )

        is_new = entity.add_condition(active_cond)

        # Применяем включённые состояния
        for included_id in condition_def.includes:
            included_cond = ActiveCondition(
                condition_id=included_id,
                source_id=source_id,
                duration_rounds=duration_rounds,
            )
            entity.add_condition(included_cond)

        if is_new:
            self.logger.info(f"Applied condition {condition_id} to {target_id} (source: {source_id})")

            # Уведомляем клиентов
            self._broadcast_condition_update(target_id)

            # Публикуем событие
            self.event_manager.post("condition_applied", {
                "target_id": target_id,
                "condition_id": condition_id,
                "source_id": source_id,
            })

            # Особые эффекты при наложении
            effects = condition_def.effects
            if effects.falls_prone:
                entity.add_condition(ActiveCondition(
                    condition_id="prone",
                    source_id=source_id,
                    duration_rounds=-1,
                ))
            if effects.drops_held_items:
                self.event_manager.post("drop_held_items", {"entity_id": target_id})

    def _on_remove_condition(self, data: dict):
        """Снимает состояние с существа."""
        target_id = data.get("target_id", "")
        condition_id = data.get("condition", "").lower()

        if not target_id or not condition_id:
            return

        entity = self._entity_conditions.get(target_id)
        if not entity:
            return

        if entity.remove_condition(condition_id):
            self.logger.info(f"Removed condition {condition_id} from {target_id}")

            # Уведомляем клиентов
            self._broadcast_condition_update(target_id)

            # Публикуем событие
            self.event_manager.post("condition_removed", {
                "target_id": target_id,
                "condition_id": condition_id,
            })

    def _on_apply_buff(self, data: dict):
        """Применяет бафф (синоним apply_condition)."""
        self._on_apply_condition(data)

    def _on_remove_buff(self, data: dict):
        """Снимает бафф (синоним remove_condition)."""
        data["condition"] = data.get("buff", "")
        self._on_remove_condition(data)

    # =========================================================================
    # Turn Processing
    # =========================================================================

    def _on_turn_start(self, data: dict):
        """Начало хода существа."""
        entity_id = data.get("entity_id", "")
        entity = self._entity_conditions.get(entity_id)
        if not entity:
            return

        # Некоторые состояния позволяют спасбросок в начале хода
        # (например, Frightened если источник не виден)
        pass

    def _on_turn_end(self, data: dict):
        """Конец хода существа."""
        entity_id = data.get("entity_id", "")
        entity = self._entity_conditions.get(entity_id)
        if not entity:
            return

        # Уменьшаем длительность состояний
        expired = entity.tick_durations()

        for cond_id in expired:
            self.logger.info(f"Condition {cond_id} expired on {entity_id}")
            self.event_manager.post("condition_expired", {
                "target_id": entity_id,
                "condition_id": cond_id,
            })

        if expired:
            self._broadcast_condition_update(entity_id)

        # Спасброски в конце хода
        for cond_id, cond in entity.conditions.items():
            if cond.save_dc > 0 and cond.save_ability:
                # Запрашиваем спасбросок
                self.event_manager.post("request_saving_throw", {
                    "entity_id": entity_id,
                    "ability": cond.save_ability,
                    "dc": cond.save_dc,
                    "on_success": {
                        "event": "remove_condition",
                        "data": {"target_id": entity_id, "condition": cond_id},
                    },
                })

    def _on_entity_death(self, data: dict):
        """Существо умерло - снимаем все состояния."""
        entity_id = data.get("entity_id", "")
        if entity_id in self._entity_conditions:
            del self._entity_conditions[entity_id]
            self.logger.info(f"Cleared all conditions from dead entity {entity_id}")

    # =========================================================================
    # Combat Integration
    # =========================================================================

    def _on_get_attack_modifiers(self, data: dict):
        """Возвращает модификаторы атаки на основе состояний."""
        attacker_id = data.get("attacker_id", "")
        target_id = data.get("target_id", "")
        distance = data.get("distance", 10)  # Дистанция в футах

        result = {
            "advantage": False,
            "disadvantage": False,
            "auto_crit": False,
        }

        # Состояния атакующего
        attacker = self._entity_conditions.get(attacker_id)
        if attacker:
            effects = get_combined_effects(attacker.get_all_condition_ids())
            if effects.attack_advantage:
                result["advantage"] = True
            if effects.attack_disadvantage:
                result["disadvantage"] = True

        # Состояния цели
        target = self._entity_conditions.get(target_id)
        if target:
            target_conds = target.get_all_condition_ids()
            effects = get_combined_effects(target_conds)
            if effects.attacks_against_advantage:
                result["advantage"] = True
            if effects.attacks_against_disadvantage:
                result["disadvantage"] = True
            if effects.auto_crit_within_5ft and distance <= 5:
                result["auto_crit"] = True

            # Особый случай: Prone
            if "prone" in target_conds:
                if distance <= 5:
                    result["advantage"] = True
                else:
                    result["disadvantage"] = True

        # Отвечаем через callback или возвращаем результат
        callback = data.get("callback")
        if callback:
            callback(result)

        return result

    def _on_get_save_modifiers(self, data: dict):
        """Возвращает модификаторы спасброска на основе состояний."""
        entity_id = data.get("entity_id", "")
        ability = data.get("ability", "").upper()

        result = {
            "advantage": False,
            "disadvantage": False,
            "auto_fail": False,
        }

        entity = self._entity_conditions.get(entity_id)
        if not entity:
            return result

        effects = get_combined_effects(entity.get_all_condition_ids())

        # Автопровалы
        if ability == "STR" and effects.auto_fail_str_saves:
            result["auto_fail"] = True
        elif ability == "DEX" and effects.auto_fail_dex_saves:
            result["auto_fail"] = True

        # Advantage/Disadvantage
        if ability == "STR":
            if effects.str_save_advantage:
                result["advantage"] = True
            if effects.str_save_disadvantage:
                result["disadvantage"] = True
        elif ability == "DEX":
            if effects.dex_save_advantage:
                result["advantage"] = True
            if effects.dex_save_disadvantage:
                result["disadvantage"] = True
        elif ability == "CON":
            if effects.con_save_advantage:
                result["advantage"] = True
            if effects.con_save_disadvantage:
                result["disadvantage"] = True

        callback = data.get("callback")
        if callback:
            callback(result)

        return result

    def _on_check_can_act(self, data: dict):
        """Проверяет, может ли существо действовать."""
        entity_id = data.get("entity_id", "")
        action_type = data.get("action_type", "action")  # action, reaction, move, bonus_action

        result = {"can_act": True, "reason": ""}

        entity = self._entity_conditions.get(entity_id)
        if not entity:
            callback = data.get("callback")
            if callback:
                callback(result)
            return result

        effects = get_combined_effects(entity.get_all_condition_ids())

        if action_type == "action" and effects.cannot_take_actions:
            result["can_act"] = False
            result["reason"] = "Incapacitated"
        elif action_type == "reaction" and effects.cannot_take_reactions:
            result["can_act"] = False
            result["reason"] = "Cannot take reactions"
        elif action_type == "move" and (effects.cannot_move or effects.speed_zero):
            result["can_act"] = False
            result["reason"] = "Cannot move"

        callback = data.get("callback")
        if callback:
            callback(result)

        return result

    # =========================================================================
    # Client Communication
    # =========================================================================

    def _on_conditions_request(self, data: dict):
        """Запрос состояний существа."""
        client_id = data.get("client_id", -1)
        entity_id = data.get("entity_id", "")

        conditions_list = []
        entity = self._entity_conditions.get(entity_id)
        if entity:
            for cond_id, active_cond in entity.conditions.items():
                cond_def = get_condition(cond_id)
                if cond_def:
                    conditions_list.append({
                        "id": cond_id,
                        "name": cond_def.name,
                        "name_ru": cond_def.name_ru,
                        "icon": cond_def.icon,
                        "color": cond_def.color,
                        "duration": active_cond.duration_rounds,
                    })

        self._send_to_client(client_id, {
            "type": "conditions_update",
            "entity_id": entity_id,
            "conditions": conditions_list,
        })

    def _broadcast_condition_update(self, entity_id: str):
        """Рассылает обновление состояний всем клиентам."""
        conditions_list = []
        entity = self._entity_conditions.get(entity_id)
        if entity:
            for cond_id, active_cond in entity.conditions.items():
                cond_def = get_condition(cond_id)
                if cond_def:
                    conditions_list.append({
                        "id": cond_id,
                        "name": cond_def.name,
                        "name_ru": cond_def.name_ru,
                        "icon": cond_def.icon,
                        "color": cond_def.color,
                        "duration": active_cond.duration_rounds,
                    })

        self._broadcast({
            "type": "conditions_update",
            "entity_id": entity_id,
            "conditions": conditions_list,
        })

    # =========================================================================
    # Helpers
    # =========================================================================

    def _send_to_client(self, client_id: int, message: dict):
        """Отправляет сообщение клиенту."""
        if hasattr(self.app, 'send_to_client'):
            self.app.send_to_client(client_id, message)
        else:
            self.event_manager.post(f"send_to_client_{client_id}", message)

    def _broadcast(self, message: dict):
        """Рассылает сообщение всем клиентам."""
        if hasattr(self.app, 'broadcast'):
            self.app.broadcast(message)
        elif hasattr(self.app, 'players'):
            for pid in self.app.players:
                self._send_to_client(pid, message)

    # =========================================================================
    # Public API
    # =========================================================================

    def get_entity_conditions(self, entity_id: str) -> List[str]:
        """Возвращает список ID активных состояний существа."""
        entity = self._entity_conditions.get(entity_id)
        if not entity:
            return []
        return entity.get_all_condition_ids()

    def has_condition(self, entity_id: str, condition_id: str) -> bool:
        """Проверяет, есть ли у существа состояние."""
        entity = self._entity_conditions.get(entity_id)
        if not entity:
            return False
        return entity.has_condition(condition_id.lower())

    def get_speed_modifier(self, entity_id: str) -> float:
        """Возвращает модификатор скорости."""
        entity = self._entity_conditions.get(entity_id)
        if not entity:
            return 1.0

        effects = get_combined_effects(entity.get_all_condition_ids())

        if effects.speed_zero or effects.cannot_move:
            return 0.0
        if effects.speed_halved:
            return 0.5

        return effects.speed_multiplier

    def get_ac_bonus(self, entity_id: str) -> int:
        """Возвращает бонус к AC от состояний."""
        entity = self._entity_conditions.get(entity_id)
        if not entity:
            return 0

        effects = get_combined_effects(entity.get_all_condition_ids())
        return effects.ac_bonus
