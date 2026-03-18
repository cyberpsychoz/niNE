"""
Серверный модуль системы экипировки.

Управляет надетой экипировкой игроков:
- Слоты экипировки (голова, тело, руки, оружие и т.д.)
- Экипировка/снятие предметов
- Расчёт бонусов от экипировки
- Синхронизация с клиентом
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from nine.core.plugins import PluginModule
from nine.core.entity import Entity, ENTITY_REGISTRY

from nine.plugins.inventory.entities.equipment.sh_equipment_slots import EquipmentSlot, ALL_SLOTS


@dataclass
class PlayerEquipment:
    """Экипировка одного игрока."""
    # {slot_value: Entity}
    slots: Dict[str, Entity] = field(default_factory=dict)
    # Предметы с attunement (максимум 3 в D&D)
    attuned_items: List[str] = field(default_factory=list)  # unique_id предметов

    def get(self, slot: str) -> Optional[Entity]:
        """Получить предмет в слоте."""
        return self.slots.get(slot)

    def set(self, slot: str, entity: Optional[Entity]):
        """Установить предмет в слот."""
        if entity is None:
            self.slots.pop(slot, None)
        else:
            self.slots[slot] = entity

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        result = {}
        for slot, entity in self.slots.items():
            result[slot] = {
                "class_id": entity.CLASS_ID,
                "unique_id": entity.unique_id,
                "name": getattr(entity, 'NAME', entity.CLASS_ID),
                "icon": getattr(entity, 'ICON', ''),
                "data": entity.data,
            }
        return result


class EquipmentServerModule(PluginModule):
    """
    Серверный модуль управления экипировкой.

    Работает совместно с InventoryServerModule.
    Предметы из инвентаря можно экипировать в слоты.
    """

    # Максимум предметов с attunement (по правилам D&D)
    MAX_ATTUNED_ITEMS = 3

    def on_load(self):
        # {player_uuid: PlayerEquipment}
        self.equipment: Dict[str, PlayerEquipment] = {}
        # {player_uuid: character_uuid} - mapping for DB persistence
        self._player_char_map: Dict[str, str] = {}

        # Ссылка на модуль инвентаря
        self.inventory_module = None

        # Подписки на события
        self.event_manager.subscribe("player_joined", self.on_player_join)
        self.event_manager.subscribe("player_left", self.on_player_leave)
        self.event_manager.subscribe("equip_item", self.on_equip_item)
        self.event_manager.subscribe("unequip_item", self.on_unequip_item)
        self.event_manager.subscribe("swap_equipment", self.on_swap_equipment)
        self.event_manager.subscribe("request_equipment", self.on_request_equipment)

        self.logger.info("Серверный модуль экипировки загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("player_joined", self.on_player_join)
        self.event_manager.unsubscribe("player_left", self.on_player_leave)
        self.event_manager.unsubscribe("equip_item", self.on_equip_item)
        self.event_manager.unsubscribe("unequip_item", self.on_unequip_item)
        self.event_manager.unsubscribe("swap_equipment", self.on_swap_equipment)
        self.event_manager.unsubscribe("request_equipment", self.on_request_equipment)

        self.logger.info("Серверный модуль экипировки выгружен")

    def _get_inventory_module(self):
        """Получить ссылку на модуль инвентаря."""
        if self.inventory_module is None:
            pm = getattr(self.app, 'plugin_manager', None)
            if pm:
                loaded = pm.loaded_plugins.get("nine.inventory")
                if loaded:
                    for module in loaded.modules:
                        if hasattr(module, 'inventories') and hasattr(module, 'get_inventory'):
                            self.inventory_module = module
                            break
        return self.inventory_module

    # =========================================================================
    # Event handlers
    # =========================================================================

    def on_player_join(self, data: dict):
        """Игрок присоединился — загружаем экипировку из БД."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        character_uuid = data.get("character_uuid")
        if character_uuid:
            self._player_char_map[player_uuid] = character_uuid

        # Try to load equipment from DB
        loaded_from_db = False
        if character_uuid and hasattr(self.app, 'db') and self.app.db:
            char_data = self.app.db.get_character(character_uuid)
            if char_data:
                saved_equipment = char_data.get("equipment")
                if saved_equipment and isinstance(saved_equipment, dict) and len(saved_equipment) > 0:
                    self.equipment[player_uuid] = self._deserialize_equipment(saved_equipment)
                    loaded_from_db = True
                    self.logger.info(
                        f"Loaded {len(self.equipment[player_uuid].slots)} equipped items "
                        f"from DB for player {player_uuid}"
                    )

        if not loaded_from_db:
            self.equipment[player_uuid] = PlayerEquipment()

        self.logger.debug(f"Экипировка игрока {player_uuid} инициализирована")

        # Отправляем текущую экипировку клиенту
        self._send_equipment_update(player_uuid)

    def on_player_leave(self, data: dict):
        """Игрок вышел — сохраняем экипировку в БД и очищаем данные."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        # Save equipment to DB
        character_uuid = self._player_char_map.get(player_uuid)
        if character_uuid and hasattr(self.app, 'db') and self.app.db:
            serialized = self._serialize_equipment(player_uuid)
            self.app.db.update_character(character_uuid, {"equipment": serialized})
            self.logger.info(
                f"Saved {len(serialized)} equipped items to DB for player {player_uuid}"
            )

        # Cleanup
        self._player_char_map.pop(player_uuid, None)
        if player_uuid in self.equipment:
            del self.equipment[player_uuid]

    def on_equip_item(self, data: dict):
        """
        Экипировать предмет из инвентаря.

        data: {
            uuid: str,           # UUID игрока
            inventory_slot: int, # Слот в инвентаре
            equipment_slot: str, # Слот экипировки (опционально, авто-определение)
        }
        """
        player_uuid = data.get("uuid")
        inventory_slot = data.get("inventory_slot")
        target_slot = data.get("equipment_slot")

        if not player_uuid or inventory_slot is None:
            return

        result = self.equip_from_inventory(
            player_uuid, inventory_slot, target_slot
        )

        if result["success"]:
            self.logger.debug(
                f"Игрок {player_uuid} экипировал {result.get('item_id', '?')} "
                f"в слот {result.get('slot', '?')}"
            )
        else:
            # Отправляем сообщение об ошибке
            self.event_manager.post("system_message_to_client", {
                "client_id": player_uuid,
                "message": result.get("error", "Не удалось экипировать предмет"),
            })

    def on_unequip_item(self, data: dict):
        """
        Снять экипировку в инвентарь.

        data: {
            uuid: str,
            equipment_slot: str,
        }
        """
        player_uuid = data.get("uuid")
        slot = data.get("equipment_slot")

        if not player_uuid or not slot:
            return

        result = self.unequip_to_inventory(player_uuid, slot)

        if result["success"]:
            self.logger.debug(
                f"Игрок {player_uuid} снял {result.get('item_id', '?')} "
                f"из слота {slot}"
            )
        else:
            self.event_manager.post("system_message_to_client", {
                "client_id": player_uuid,
                "message": result.get("error", "Не удалось снять предмет"),
            })

    def on_swap_equipment(self, data: dict):
        """
        Поменять местами предметы между слотами.

        data: {
            uuid: str,
            slot_from: str,
            slot_to: str,
        }
        """
        player_uuid = data.get("uuid")
        slot_from = data.get("slot_from")
        slot_to = data.get("slot_to")

        if not player_uuid or not slot_from or not slot_to:
            return

        result = self.swap_slots(player_uuid, slot_from, slot_to)

        if not result["success"]:
            self.event_manager.post("system_message_to_client", {
                "client_id": player_uuid,
                "message": result.get("error", "Не удалось поменять предметы"),
            })

    def on_request_equipment(self, data: dict):
        """Запрос текущей экипировки от клиента."""
        player_uuid = data.get("uuid")
        if player_uuid:
            self._send_equipment_update(player_uuid)

    # =========================================================================
    # Persistence (serialize / deserialize)
    # =========================================================================

    def _serialize_equipment(self, player_uuid: str) -> dict:
        """Serialize player equipment to a dict for DB storage."""
        if player_uuid not in self.equipment:
            return {}

        player_eq = self.equipment[player_uuid]
        result = {}
        for slot, entity in player_eq.slots.items():
            if entity:
                result[slot] = entity.to_dict()
        return result

    def _deserialize_equipment(self, data: dict) -> PlayerEquipment:
        """Deserialize equipment dict from DB into a PlayerEquipment instance."""
        player_eq = PlayerEquipment()
        for slot, item_dict in data.items():
            if not item_dict or not isinstance(item_dict, dict):
                continue

            class_id = item_dict.get("class_id")
            if not class_id:
                continue

            entity = ENTITY_REGISTRY.create(class_id, unique_id=item_dict.get("unique_id"))
            if entity is None:
                self.logger.warning(
                    f"Cannot deserialize equipment: unknown class_id '{class_id}' "
                    f"in slot '{slot}', skipping"
                )
                continue

            entity.count = item_dict.get("count", 1)
            entity.data = item_dict.get("data", {})
            entity._owner_uuid = item_dict.get("owner_uuid")

            player_eq.set(slot, entity)

        return player_eq

    # =========================================================================
    # Equipment operations
    # =========================================================================

    def equip_from_inventory(
        self,
        player_uuid: str,
        inventory_slot: int,
        target_slot: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Экипировать предмет из инвентаря.

        Args:
            player_uuid: UUID игрока
            inventory_slot: Индекс слота в инвентаре
            target_slot: Целевой слот (None = автоопределение)

        Returns:
            {"success": bool, "error"?: str, "slot"?: str, "item_id"?: str}
        """
        if player_uuid not in self.equipment:
            return {"success": False, "error": "Игрок не найден"}

        # Получаем инвентарь
        inv_module = self._get_inventory_module()
        if not inv_module:
            return {"success": False, "error": "Модуль инвентаря не найден"}

        inventory = inv_module.get_inventory(player_uuid)
        if inventory_slot < 0 or inventory_slot >= len(inventory):
            return {"success": False, "error": "Неверный слот инвентаря"}

        entity = inventory[inventory_slot]

        # Проверяем, что это экипировка
        if not hasattr(entity, 'EQUIPMENT_SLOT'):
            return {"success": False, "error": "Этот предмет нельзя экипировать"}

        # Определяем слот
        if target_slot is None:
            if entity.EQUIPMENT_SLOT:
                target_slot = entity.EQUIPMENT_SLOT.value
            else:
                return {"success": False, "error": "Не указан слот экипировки"}

        # Проверяем допустимость слота
        if hasattr(entity, 'can_equip_in_slot'):
            if not entity.can_equip_in_slot(target_slot):
                return {"success": False, "error": f"Предмет нельзя надеть в слот {target_slot}"}

        # Получаем статы игрока для проверки требований
        player_stats = self._get_player_stats(player_uuid)

        # Проверяем требования
        if hasattr(entity, 'can_equip'):
            can_equip, reason = entity.can_equip(player_uuid, player_stats)
            if not can_equip:
                return {"success": False, "error": reason}

        # Проверяем attunement
        if hasattr(entity, 'ATTUNEMENT') and entity.ATTUNEMENT:
            if not self._can_attune(player_uuid, entity):
                return {
                    "success": False,
                    "error": f"Достигнут лимит настройки ({self.MAX_ATTUNED_ITEMS})"
                }

        player_eq = self.equipment[player_uuid]

        # Если слот занят, снимаем старый предмет
        old_item = player_eq.get(target_slot)
        if old_item:
            unequip_result = self.unequip_to_inventory(player_uuid, target_slot)
            if not unequip_result["success"]:
                return unequip_result

        # Удаляем из инвентаря
        inventory.pop(inventory_slot)

        # Надеваем
        player_eq.set(target_slot, entity)

        # Вызываем on_equip
        if hasattr(entity, 'set_event_manager'):
            entity.set_event_manager(self.event_manager)
        if hasattr(entity, 'on_equip'):
            entity.on_equip(player_uuid, target_slot)

        # Добавляем в список attuned если нужно
        if hasattr(entity, 'ATTUNEMENT') and entity.ATTUNEMENT:
            if entity.unique_id not in player_eq.attuned_items:
                player_eq.attuned_items.append(entity.unique_id)

        # Обновляем клиентов
        self._send_equipment_update(player_uuid)
        inv_module._send_inventory_update(player_uuid)

        # Отправляем событие об изменении статов
        self._recalculate_stats(player_uuid)

        return {
            "success": True,
            "slot": target_slot,
            "item_id": entity.CLASS_ID,
        }

    def unequip_to_inventory(
        self,
        player_uuid: str,
        slot: str
    ) -> Dict[str, Any]:
        """
        Снять предмет из слота в инвентарь.

        Args:
            player_uuid: UUID игрока
            slot: Слот экипировки

        Returns:
            {"success": bool, "error"?: str, "item_id"?: str}
        """
        if player_uuid not in self.equipment:
            return {"success": False, "error": "Игрок не найден"}

        player_eq = self.equipment[player_uuid]
        entity = player_eq.get(slot)

        if not entity:
            return {"success": False, "error": "Слот пуст"}

        # Проверяем можно ли снять (проклятые предметы)
        if hasattr(entity, 'on_unequip'):
            if hasattr(entity, 'set_event_manager'):
                entity.set_event_manager(self.event_manager)
            if not entity.on_unequip(player_uuid):
                return {"success": False, "error": "Этот предмет нельзя снять"}

        # Получаем инвентарь
        inv_module = self._get_inventory_module()
        if not inv_module:
            return {"success": False, "error": "Модуль инвентаря не найден"}

        # Проверяем место в инвентаре
        inventory = inv_module.get_inventory(player_uuid)
        if len(inventory) >= inv_module.max_slots:
            return {"success": False, "error": "Инвентарь полон"}

        # Снимаем
        player_eq.set(slot, None)

        # Убираем из attuned
        if entity.unique_id in player_eq.attuned_items:
            player_eq.attuned_items.remove(entity.unique_id)

        # Добавляем в инвентарь
        inventory.append(entity)

        # Обновляем клиентов
        self._send_equipment_update(player_uuid)
        inv_module._send_inventory_update(player_uuid)

        # Пересчитываем статы
        self._recalculate_stats(player_uuid)

        return {
            "success": True,
            "item_id": entity.CLASS_ID,
        }

    def swap_slots(
        self,
        player_uuid: str,
        slot_from: str,
        slot_to: str
    ) -> Dict[str, Any]:
        """
        Поменять местами предметы между слотами.

        Используется для колец (ring_1 <-> ring_2).
        """
        if player_uuid not in self.equipment:
            return {"success": False, "error": "Игрок не найден"}

        player_eq = self.equipment[player_uuid]
        item_from = player_eq.get(slot_from)
        item_to = player_eq.get(slot_to)

        # Проверяем совместимость слотов
        if item_from and hasattr(item_from, 'can_equip_in_slot'):
            if not item_from.can_equip_in_slot(slot_to):
                return {"success": False, "error": "Предмет не подходит для этого слота"}

        if item_to and hasattr(item_to, 'can_equip_in_slot'):
            if not item_to.can_equip_in_slot(slot_from):
                return {"success": False, "error": "Предмет не подходит для этого слота"}

        # Меняем местами
        player_eq.set(slot_from, item_to)
        player_eq.set(slot_to, item_from)

        self._send_equipment_update(player_uuid)

        return {"success": True}

    # =========================================================================
    # Helpers
    # =========================================================================

    def _can_attune(self, player_uuid: str, entity: Entity) -> bool:
        """Проверить, можно ли настроиться на предмет."""
        if player_uuid not in self.equipment:
            return False

        player_eq = self.equipment[player_uuid]

        # Если уже настроен на этот предмет
        if entity.unique_id in player_eq.attuned_items:
            return True

        # Проверяем лимит
        return len(player_eq.attuned_items) < self.MAX_ATTUNED_ITEMS

    def _get_player_stats(self, player_uuid: str) -> dict:
        """Получить статы игрока для проверки требований."""
        # TODO: Интеграция с системой персонажей
        # Пока возвращаем базовые статы
        return {
            "level": 1,
            "strength": 10,
            "dexterity": 10,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10,
            "proficiencies": ["simple_weapons", "light_armor"],
        }

    def _recalculate_stats(self, player_uuid: str):
        """Пересчитать бонусы от экипировки."""
        if player_uuid not in self.equipment:
            return

        player_eq = self.equipment[player_uuid]

        # Собираем все бонусы
        total_bonuses = {
            "armor_class": 0,
            "strength": 0,
            "dexterity": 0,
            "constitution": 0,
            "intelligence": 0,
            "wisdom": 0,
            "charisma": 0,
            "attack_bonus": 0,
            "damage_bonus": 0,
            "speed": 0,
            "damage_resistance": [],
            "condition_immunity": [],
        }

        base_ac = 10  # Без брони
        has_armor = False
        has_shield = False

        for slot, entity in player_eq.slots.items():
            if not entity:
                continue

            # Бонусы от STAT_BONUS
            if hasattr(entity, 'STAT_BONUS'):
                bonus = entity.STAT_BONUS
                total_bonuses["strength"] += bonus.strength
                total_bonuses["dexterity"] += bonus.dexterity
                total_bonuses["constitution"] += bonus.constitution
                total_bonuses["intelligence"] += bonus.intelligence
                total_bonuses["wisdom"] += bonus.wisdom
                total_bonuses["charisma"] += bonus.charisma
                total_bonuses["attack_bonus"] += bonus.attack_bonus
                total_bonuses["damage_bonus"] += bonus.damage_bonus
                total_bonuses["speed"] += bonus.speed
                total_bonuses["armor_class"] += bonus.armor_class
                total_bonuses["damage_resistance"].extend(bonus.damage_resistance)
                total_bonuses["condition_immunity"].extend(bonus.condition_immunity)

            # AC от брони
            if hasattr(entity, 'ARMOR_TYPE') and hasattr(entity, 'BASE_AC'):
                from nine.plugins.inventory.entities.equipment.armor import ArmorType
                if entity.ARMOR_TYPE == ArmorType.SHIELD:
                    has_shield = True
                    # Щит добавляет свой AC отдельно
                else:
                    has_armor = True
                    base_ac = entity.BASE_AC

        # Определяем ограничение DEX от брони
        max_dex_bonus = None  # None = unlimited
        for slot, entity in player_eq.slots.items():
            if entity and hasattr(entity, 'ARMOR_TYPE') and hasattr(entity, 'MAX_DEX_BONUS'):
                from nine.plugins.inventory.entities.equipment.armor import ArmorType
                if entity.ARMOR_TYPE != ArmorType.SHIELD:
                    max_dex_bonus = entity.MAX_DEX_BONUS

        # Отправляем событие с обновлёнными бонусами
        self.event_manager.post("equipment_stats_updated", {
            "uuid": player_uuid,
            "bonuses": total_bonuses,
            "base_ac": base_ac,
            "has_armor": has_armor,
            "has_shield": has_shield,
            "max_dex_bonus": max_dex_bonus,
        })

    def _send_equipment_update(self, player_uuid: str):
        """Отправить обновление экипировки клиенту."""
        if player_uuid not in self.equipment:
            return

        player_eq = self.equipment[player_uuid]

        # Формируем данные для клиента
        slots_data = {}
        for slot in ALL_SLOTS:
            slot_value = slot.value
            entity = player_eq.get(slot_value)

            if entity:
                slots_data[slot_value] = {
                    "class_id": entity.CLASS_ID,
                    "unique_id": entity.unique_id,
                    "name": getattr(entity, 'NAME', entity.CLASS_ID),
                    "icon": getattr(entity, 'ICON', ''),
                    "rarity": getattr(entity, 'RARITY', 'common'),
                    "tooltip": entity.get_tooltip() if hasattr(entity, 'get_tooltip') else '',
                }
            else:
                slots_data[slot_value] = None

        # Отправляем
        self.event_manager.post("equipment_send_to_client", {
            "client_id": player_uuid,
            "data": {
                "type": "equipment_update",
                "slots": slots_data,
                "attuned_count": len(player_eq.attuned_items),
                "max_attuned": self.MAX_ATTUNED_ITEMS,
            }
        })

    # =========================================================================
    # Public API
    # =========================================================================

    def get_equipment(self, player_uuid: str) -> Optional[PlayerEquipment]:
        """Получить экипировку игрока."""
        return self.equipment.get(player_uuid)

    def get_equipped_item(self, player_uuid: str, slot: str) -> Optional[Entity]:
        """Получить предмет в слоте."""
        player_eq = self.equipment.get(player_uuid)
        if player_eq:
            return player_eq.get(slot)
        return None

    def get_main_weapon(self, player_uuid: str) -> Optional[Entity]:
        """Получить оружие в основной руке."""
        return self.get_equipped_item(player_uuid, "main_hand")

    def get_off_hand(self, player_uuid: str) -> Optional[Entity]:
        """Получить предмет во второй руке."""
        return self.get_equipped_item(player_uuid, "off_hand")

    def get_armor(self, player_uuid: str) -> Optional[Entity]:
        """Получить надетую броню."""
        return self.get_equipped_item(player_uuid, "chest")

    def calculate_ac(self, player_uuid: str, dex_modifier: int = 0) -> int:
        """
        Рассчитать итоговый AC игрока.

        Args:
            player_uuid: UUID игрока
            dex_modifier: Модификатор ловкости

        Returns:
            Итоговый Armor Class
        """
        if player_uuid not in self.equipment:
            return 10 + dex_modifier  # Без брони

        player_eq = self.equipment[player_uuid]

        base_ac = 10  # Без брони
        max_dex = None
        shield_bonus = 0
        misc_bonus = 0

        for slot, entity in player_eq.slots.items():
            if not entity:
                continue

            # Броня
            if hasattr(entity, 'get_armor_class') and hasattr(entity, 'ARMOR_TYPE'):
                from nine.plugins.inventory.entities.equipment.armor import ArmorType
                if entity.ARMOR_TYPE == ArmorType.SHIELD:
                    shield_bonus += entity.BASE_AC
                else:
                    base_ac = entity.BASE_AC
                    if hasattr(entity, 'MAX_DEX_BONUS'):
                        max_dex = entity.MAX_DEX_BONUS

            # Бонусы к AC от аксессуаров
            if hasattr(entity, 'STAT_BONUS'):
                misc_bonus += entity.STAT_BONUS.armor_class

        # Применяем ограничение DEX
        effective_dex = dex_modifier
        if max_dex is not None:
            effective_dex = min(dex_modifier, max_dex)

        return base_ac + effective_dex + shield_bonus + misc_bonus
