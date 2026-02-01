"""
Turn Manager - управление ходами и выполнение боевых действий.
Валидирует и выполняет действия игроков в бою.
"""

from typing import Optional, Dict, Any
import math

from nine.core.plugins import PluginContext
from nine.plugins.combat.sh_dice import DiceRoller
from nine.plugins.combat.sh_action_economy import (
    COMBAT_ACTIONS, ActionCost, TargetType, get_action
)


class TurnManager:
    """
    Управляет выполнением действий в пошаговом бою.
    Валидирует действия, проверяет дальность, выполняет броски.
    """

    def __init__(self, context: PluginContext):
        self.context = context
        self.app = context.app
        self.logger = context.logger
        self.event_manager = context.event_manager

    def on_load(self):
        self.logger.info("Turn Manager loaded")

        # Получаем ссылку на combat manager (будет установлена позже)
        self._combat_manager = None

        # Подписки
        self.event_manager.subscribe("combat_action_execute", self._on_action_execute)
        self.event_manager.subscribe("combat_movement_request", self._on_movement_request)

    def on_unload(self):
        self.event_manager.unsubscribe("combat_action_execute", self._on_action_execute)
        self.event_manager.unsubscribe("combat_movement_request", self._on_movement_request)

        self.logger.info("Turn Manager unloaded")

    @property
    def combat_manager(self):
        """Ленивое получение combat manager."""
        if self._combat_manager is None:
            # Ищем в том же плагине
            if hasattr(self.app, 'plugin_manager'):
                combat_plugin = self.app.plugin_manager.get_plugin("nine.combat")
                if combat_plugin:
                    for module in combat_plugin.modules:
                        if hasattr(module, 'active_combats'):
                            self._combat_manager = module
                            break
        return self._combat_manager

    @property
    def equipment_module(self):
        """Ленивое получение equipment module."""
        if not hasattr(self, '_equipment_module'):
            self._equipment_module = None
        if self._equipment_module is None:
            if hasattr(self.app, 'plugin_manager'):
                inventory_plugin = self.app.plugin_manager.get_plugin("nine.inventory")
                if inventory_plugin:
                    for module in inventory_plugin.modules:
                        if hasattr(module, 'get_main_weapon'):
                            self._equipment_module = module
                            break
        return self._equipment_module

    # =========================================================================
    # Обработчики событий
    # =========================================================================

    def _on_action_execute(self, data: dict):
        """Выполняет запрошенное действие."""
        combat_id = data.get("combat_id")
        actor_id = data.get("actor_id")
        action_id = data.get("action_id")
        target_id = data.get("target_id")

        if not combat_id or not actor_id or not action_id:
            return

        manager = self.combat_manager
        if not manager:
            return

        combat = manager.active_combats.get(combat_id)
        if not combat:
            return

        participant = combat.get_participant(actor_id)
        if not participant:
            return

        # Проверяем, что это ход участника
        if combat.current_participant != participant:
            self._send_result(combat_id, actor_id, action_id, {
                "success": False,
                "error": "Сейчас не ваш ход",
            })
            return

        # Получаем действие
        action = get_action(action_id)
        if not action:
            self._send_result(combat_id, actor_id, action_id, {
                "success": False,
                "error": f"Неизвестное действие: {action_id}",
            })
            return

        # Валидируем экономику действий
        if not self._validate_action_economy(participant, action):
            self._send_result(combat_id, actor_id, action_id, {
                "success": False,
                "error": "Недостаточно ресурсов для этого действия",
            })
            return

        # Получаем цель если нужна
        target = None
        if action.target_type not in (TargetType.NONE, TargetType.SELF):
            if not target_id:
                self._send_result(combat_id, actor_id, action_id, {
                    "success": False,
                    "error": "Необходимо выбрать цель",
                })
                return

            target = combat.get_participant(target_id)
            if not target:
                self._send_result(combat_id, actor_id, action_id, {
                    "success": False,
                    "error": "Цель не найдена",
                })
                return

            # Проверяем дальность
            range_result = self._check_range(actor_id, target_id, action)
            if not range_result["in_range"]:
                self._send_result(combat_id, actor_id, action_id, {
                    "success": False,
                    "error": f"Цель вне досягаемости ({range_result['required_range']:.0f} футов)",
                })
                return

        # Выполняем действие
        result = self._execute_action(combat, participant, action, target)

        # Потребляем ресурсы
        self._consume_action_cost(participant, action.cost)

        # Отправляем результат
        self._send_result(combat_id, actor_id, action_id, result, target_id)

        # Если это end_turn, переходим к следующему ходу
        if action_id == "end_turn":
            combat.advance_turn()

    def _on_movement_request(self, data: dict):
        """Обрабатывает запрос на перемещение."""
        combat_id = data.get("combat_id")
        actor_id = data.get("actor_id")
        destination = data.get("destination")  # [x, y, z]

        if not combat_id or not actor_id or not destination:
            return

        manager = self.combat_manager
        if not manager:
            return

        combat = manager.active_combats.get(combat_id)
        if not combat:
            return

        participant = combat.get_participant(actor_id)
        if not participant:
            return

        # Проверяем ход
        if combat.current_participant != participant:
            return

        # Вычисляем расстояние
        current_pos = self._get_entity_position(actor_id)
        if not current_pos:
            return

        distance = self._calculate_distance(current_pos, destination)

        # Проверяем хватит ли движения
        if distance > participant.movement_remaining:
            self._send_error(actor_id, f"Недостаточно движения (осталось {int(participant.movement_remaining)} фт)")
            return

        # Потребляем движение
        participant.movement_remaining -= distance

        # Перемещаем сущность
        self._move_entity(actor_id, destination)

        # Оповещаем
        self.event_manager.post("combat_movement_result", {
            "combat_id": combat_id,
            "actor_id": actor_id,
            "destination": destination,
            "movement_remaining": participant.movement_remaining,
        })

    # =========================================================================
    # Выполнение действий
    # =========================================================================

    def _execute_action(self, combat, actor, action, target) -> dict:
        """Выполняет действие и возвращает результат."""
        result = {"success": True, "action": action.id}

        if action.id == "attack":
            result.update(self._execute_attack(combat, actor, target))

        elif action.id == "dash":
            # Удваиваем оставшееся движение
            actor.movement_remaining += actor.movement_speed
            result["effect"] = "movement_doubled"
            result["new_movement"] = actor.movement_remaining

        elif action.id == "disengage":
            # Помечаем что можно двигаться без провоцированных атак
            result["effect"] = "disengaged"
            # TODO: добавить флаг в participant

        elif action.id == "dodge":
            actor.conditions.append("dodging")
            result["effect"] = "dodging"

        elif action.id == "help":
            if target:
                # TODO: дать преимущество цели на следующий бросок
                result["effect"] = "helped"
                result["helped_target"] = target.entity_id

        elif action.id == "hide":
            # TODO: бросок скрытности
            actor.conditions.append("hidden")
            result["effect"] = "hidden"

        elif action.id == "ready":
            # TODO: система подготовленных действий
            result["effect"] = "readied"

        elif action.id == "end_turn":
            result["effect"] = "turn_ended"

        return result

    def _execute_attack(self, combat, attacker, target) -> dict:
        """Выполняет атаку по D&D правилам."""
        result = {
            "target_id": target.entity_id,
            "target_name": target.name,
        }

        # Получаем бонус атаки
        attack_bonus = self._get_attack_bonus(attacker.entity_id)

        # Получаем AC цели
        target_ac = target.armor_class

        # Проверяем преимущество/помеху
        advantage = "dodging" in attacker.conditions  # Скрыт = преимущество
        disadvantage = "dodging" in target.conditions  # Цель уклоняется = помеха

        # Бросок атаки
        attack_total, attack_roll = DiceRoller.roll_attack(
            attack_bonus,
            advantage=advantage,
            disadvantage=disadvantage
        )

        result["attack_roll"] = attack_roll.rolls[0]
        result["attack_bonus"] = attack_bonus
        result["attack_total"] = attack_total
        result["target_ac"] = target_ac
        result["is_critical"] = attack_roll.is_critical
        result["is_fumble"] = attack_roll.is_fumble

        if attack_roll.advantage:
            result["advantage"] = True
        if attack_roll.disadvantage:
            result["disadvantage"] = True

        # Определяем попадание
        if attack_roll.is_fumble:
            # Натуральная 1 всегда промах
            result["hit"] = False
            result["message"] = "Критический промах!"

        elif attack_roll.is_critical:
            # Натуральная 20 всегда попадание + крит урон
            result["hit"] = True
            result["message"] = "Критическое попадание!"

            # Бросок урона с удвоением кубов
            damage_dice = self._get_damage_dice(attacker.entity_id)
            damage_roll = DiceRoller.roll_damage(damage_dice, critical=True)
            result["damage"] = damage_roll.total
            result["damage_rolls"] = damage_roll.rolls

            # Применяем урон
            self._apply_damage(target, damage_roll.total)

        elif attack_total >= target_ac:
            # Попадание
            result["hit"] = True
            result["message"] = "Попадание!"

            # Бросок урона
            damage_dice = self._get_damage_dice(attacker.entity_id)
            damage_roll = DiceRoller.roll_damage(damage_dice)
            result["damage"] = damage_roll.total
            result["damage_rolls"] = damage_roll.rolls

            # Применяем урон
            self._apply_damage(target, damage_roll.total)

        else:
            # Промах
            result["hit"] = False
            result["message"] = "Промах"

        # Добавляем текущее HP цели
        result["target_hp_current"] = target.hp_current
        result["target_hp_max"] = target.hp_max
        result["target_is_dead"] = target.is_dead

        return result

    def _apply_damage(self, target, damage: int):
        """Применяет урон к цели."""
        target.hp_current = max(0, target.hp_current - damage)

        if target.hp_current <= 0:
            target.is_dead = True

            # Оповещаем о смерти
            self.event_manager.post("entity_died", {
                "entity_id": target.entity_id,
                "is_player": target.is_player,
            })

        # Оповещаем об уроне
        self.event_manager.post("entity_damaged", {
            "entity_id": target.entity_id,
            "damage": damage,
            "new_hp": target.hp_current,
        })

    # =========================================================================
    # Валидация
    # =========================================================================

    def _validate_action_economy(self, participant, action) -> bool:
        """Проверяет, есть ли у участника ресурсы для действия."""
        if action.cost == ActionCost.NONE:
            return True
        if action.cost == ActionCost.ACTION:
            return participant.has_action
        if action.cost == ActionCost.BONUS:
            return participant.has_bonus_action
        if action.cost == ActionCost.REACTION:
            return participant.has_reaction
        return True

    def _consume_action_cost(self, participant, cost: ActionCost):
        """Потребляет ресурс действия."""
        if cost == ActionCost.ACTION:
            participant.has_action = False
        elif cost == ActionCost.BONUS:
            participant.has_bonus_action = False
        elif cost == ActionCost.REACTION:
            participant.has_reaction = False

    def _check_range(self, actor_id: str, target_id: str, action) -> dict:
        """
        Проверяет, находится ли цель в пределах дальности.

        Для атак использует дальность экипированного оружия.
        Для других действий использует action.range_feet.

        Returns:
            {
                "in_range": bool,
                "distance": float,
                "required_range": float,
            }
        """
        actor_pos = self._get_entity_position(actor_id)
        target_pos = self._get_entity_position(target_id)

        if not actor_pos or not target_pos:
            # Не можем проверить - пропускаем
            return {"in_range": True, "distance": 0, "required_range": 0}

        distance = self._calculate_distance(actor_pos, target_pos)

        # Определяем требуемую дальность
        required_range = action.range_feet

        # Для атаки используем дальность оружия
        if action.id == "attack":
            # Пытаемся как игрока
            try:
                client_id = int(actor_id)
                player_data = self._get_player_combat_data(client_id)
                if player_data and "weapon_range" in player_data:
                    required_range = player_data["weapon_range"]
            except ValueError:
                # Пытаемся как NPC
                npc_data = self._get_npc_combat_data(actor_id)
                if npc_data and "weapon_range" in npc_data:
                    required_range = npc_data["weapon_range"]

        return {
            "in_range": distance <= required_range,
            "distance": distance,
            "required_range": required_range,
        }

    # =========================================================================
    # Утилиты
    # =========================================================================

    def _get_entity_position(self, entity_id: str) -> Optional[list]:
        """Получает позицию сущности."""
        # Пытаемся как игрока
        try:
            client_id = int(entity_id)
            if hasattr(self.app, 'world'):
                player = self.app.world.players.get(client_id)
                if player:
                    state = player.get_state()
                    return state.get("pos", [0, 0, 0])
        except ValueError:
            pass

        # Пытаемся как NPC
        if hasattr(self.app, 'plugin_manager'):
            npc_plugin = self.app.plugin_manager.get_plugin("nine.npc")
            if npc_plugin:
                for module in npc_plugin.modules:
                    if hasattr(module, 'get_npc_entity'):
                        entity = module.get_npc_entity(entity_id)
                        if entity:
                            from nine.plugins.npc.sh_components import PositionComponent
                            pos = entity.get_component(PositionComponent)
                            if pos:
                                return [pos.x, pos.y, pos.z]

        return None

    def _calculate_distance(self, pos1: list, pos2: list) -> float:
        """Вычисляет расстояние между двумя точками (2D)."""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return math.sqrt(dx * dx + dy * dy)

    def _move_entity(self, entity_id: str, destination: list):
        """Перемещает сущность в указанную точку."""
        # Отправляем событие перемещения
        self.event_manager.post("combat_entity_move", {
            "entity_id": entity_id,
            "destination": destination,
        })

    def _get_attack_bonus(self, entity_id: str) -> int:
        """Получает бонус атаки сущности."""
        # Пытаемся как игрока
        try:
            client_id = int(entity_id)
            player_data = self._get_player_combat_data(client_id)
            if player_data:
                return player_data.get("attack_bonus", 0)
        except ValueError:
            pass

        # Пытаемся как NPC
        npc_data = self._get_npc_combat_data(entity_id)
        if npc_data:
            return npc_data.get("attack_bonus", 0)

        return 0

    def _get_damage_dice(self, entity_id: str) -> str:
        """Получает кубы урона сущности."""
        # Пытаемся как игрока
        try:
            client_id = int(entity_id)
            player_data = self._get_player_combat_data(client_id)
            if player_data:
                return player_data.get("damage_dice", "1d6")
        except ValueError:
            pass

        # Пытаемся как NPC
        npc_data = self._get_npc_combat_data(entity_id)
        if npc_data:
            return npc_data.get("damage_dice", "1d6")

        return "1d6"

    def _get_player_combat_data(self, client_id: int) -> Optional[dict]:
        """
        Получает боевые данные игрока с учетом экипированного оружия.

        Учитывает:
        - Экипированное оружие в main_hand
        - Свойства оружия (finesse, ranged, reach)
        - Класс игрока и proficiency с оружием
        - Дальность оружия
        """
        if not hasattr(self.app, 'plugin_manager'):
            return None

        # Получаем персонажа
        dnd_plugin = self.app.plugin_manager.get_plugin("nine.dnd")
        if not dnd_plugin:
            return None

        char_uuid = None
        char = None
        for module in dnd_plugin.modules:
            if hasattr(module, 'active_characters'):
                char_uuid = module.active_characters.get(client_id)
                if char_uuid and hasattr(self.app, 'db'):
                    char = self.app.db.get_character(char_uuid)
                    break

        if not char:
            return None

        # Вычисляем модификаторы
        str_mod = (char.get("strength", 10) - 10) // 2
        dex_mod = (char.get("dexterity", 10) - 10) // 2
        prof = char.get("proficiency_bonus", 2)

        # Получаем экипированное оружие
        # ВАЖНО: EquipmentServerModule использует client_id как ключ (из event "player_joined")
        equipment_module = self.equipment_module
        weapon = None
        if equipment_module:
            weapon = equipment_module.get_main_weapon(client_id)

        # Если оружие экипировано
        if weapon:
            # Используем правильный модификатор (STR/DEX зависит от оружия)
            ability_mod = weapon.get_attack_modifier(str_mod, dex_mod)

            # Проверяем proficiency с оружием
            player_proficiencies = char.get("proficiencies", [])
            weapon_proficiency = weapon.required_proficiency
            has_proficiency = weapon_proficiency in player_proficiencies

            # Бонус атаки = ability modifier + proficiency (если есть)
            attack_bonus = ability_mod + (prof if has_proficiency else 0)

            # Кубы урона = weapon damage + ability modifier
            damage_dice = weapon.DAMAGE_DICE
            if ability_mod != 0:
                sign = "+" if ability_mod > 0 else ""
                damage_dice += f"{sign}{ability_mod}"

            # Дальность оружия
            weapon_range = 5.0  # По умолчанию melee 5 футов
            if weapon.REACH:
                weapon_range = 10.0  # Reach weapons 10 футов
            elif weapon.is_ranged:
                weapon_range = weapon.RANGE.normal if weapon.RANGE.normal > 0 else 80.0
            elif weapon.THROWN:
                weapon_range = weapon.RANGE.normal if weapon.RANGE.normal > 0 else 20.0

            return {
                "attack_bonus": attack_bonus,
                "damage_dice": damage_dice,
                "weapon_range": weapon_range,
                "is_ranged": weapon.is_ranged,
                "has_proficiency": has_proficiency,
            }

        # Без оружия - unarmed strike
        else:
            # Безоружная атака: 1 + STR modifier урона
            damage = 1 + str_mod
            damage_dice = "1" if damage <= 1 else f"1+{damage - 1}"

            return {
                "attack_bonus": str_mod + prof,  # STR + proficiency (все владеют безоружной атакой)
                "damage_dice": damage_dice,
                "weapon_range": 5.0,  # Unarmed strike 5 футов
                "is_ranged": False,
                "has_proficiency": True,
            }

    def _get_npc_combat_data(self, entity_id: str) -> Optional[dict]:
        """Получает боевые данные NPC."""
        if hasattr(self.app, 'plugin_manager'):
            npc_plugin = self.app.plugin_manager.get_plugin("nine.npc")
            if npc_plugin:
                for module in npc_plugin.modules:
                    if hasattr(module, 'get_npc_entity'):
                        entity = module.get_npc_entity(entity_id)
                        if entity:
                            from nine.plugins.npc.sh_components import CombatComponent
                            combat = entity.get_component(CombatComponent)
                            if combat:
                                # По умолчанию NPCs используют melee 5 футов
                                # TODO: добавить weapon_range в CombatComponent для NPC с ranged атаками
                                weapon_range = 5.0
                                if hasattr(combat, 'weapon_range'):
                                    weapon_range = combat.weapon_range

                                return {
                                    "attack_bonus": combat.attack_bonus,
                                    "damage_dice": f"{combat.damage_dice}+{combat.damage_bonus}",
                                    "weapon_range": weapon_range,
                                }
        return None

    def _send_result(self, combat_id: str, actor_id: str, action_id: str,
                     result: dict, target_id: str = None):
        """Отправляет результат действия."""
        self.event_manager.post("combat_action_result", {
            "combat_id": combat_id,
            "actor_id": actor_id,
            "action_id": action_id,
            "target_id": target_id,
            "result": result,
        })

    def _send_error(self, entity_id: str, message: str):
        """Отправляет сообщение об ошибке."""
        try:
            client_id = int(entity_id)
            self.event_manager.post("chat_send_to_clients", {
                "data": {
                    "type": "chat_broadcast",
                    "chat_type": "system",
                    "from_name": "Бой",
                    "message": message,
                },
                "recipients": [client_id]
            })
        except ValueError:
            pass  # NPC не получают сообщения
