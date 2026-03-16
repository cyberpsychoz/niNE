"""
Серверный модуль системы инвентаря с поддержкой Entity.
Управляет инвентарями игроков на сервере.
"""

from typing import Dict, List, Optional
from nine.core.plugins import PluginModule
from nine.core.entity import Entity, ENTITY_REGISTRY, EntityManager


class InventoryServerModule(PluginModule):
    """
    Серверный модуль управления инвентарем.
    Использует Entity систему для предметов.
    """

    def on_load(self):
        # {player_uuid: [Entity, ...]} - инвентарь каждого игрока
        self.inventories: Dict[str, List[Entity]] = {}
        # Максимальный размер инвентаря
        self.max_slots = 20

        # Entity manager для предметов в мире (с физикой)
        self.entity_manager: Optional[EntityManager] = None
        if hasattr(self.app, 'world'):
            physics_world = getattr(self.app, 'physics_world', None)
            render_node = getattr(self.app, 'render', None)
            self.entity_manager = EntityManager(
                self.app.world,
                self.event_manager,
                physics_world=physics_world,
                render_node=render_node
            )

        # Загружаем entity из папки entities
        from nine.plugins.inventory.entities import load_entities
        loaded = load_entities()
        self.logger.info(f"Загружено entity: {', '.join(loaded) if loaded else 'нет'}")

        # Подписки на события
        self.event_manager.subscribe("player_joined", self.on_player_join)
        self.event_manager.subscribe("player_left", self.on_player_leave)
        self.event_manager.subscribe("item_pickup", self.on_item_pickup)
        self.event_manager.subscribe("item_drop", self.on_item_drop)
        self.event_manager.subscribe("item_use", self.on_item_use)
        self.event_manager.subscribe("give_item", self.on_give_item)

        self.logger.info("Серверный модуль инвентаря загружен (Entity система)")

    def on_unload(self):
        self.event_manager.unsubscribe("player_joined", self.on_player_join)
        self.event_manager.unsubscribe("player_left", self.on_player_leave)
        self.event_manager.unsubscribe("item_pickup", self.on_item_pickup)
        self.event_manager.unsubscribe("item_drop", self.on_item_drop)
        self.event_manager.unsubscribe("item_use", self.on_item_use)
        self.event_manager.unsubscribe("give_item", self.on_give_item)

        self.logger.info("Серверный модуль инвентаря выгружен")

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------

    def on_player_join(self, data: dict):
        """Игрок присоединился - инициализируем инвентарь."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        # TODO: Загрузить инвентарь из БД
        self.inventories[player_uuid] = []

        # Grant starting equipment from class + background
        character_data = data.get("character_data")
        if character_data:
            self._grant_starting_equipment(player_uuid, character_data)

        self.logger.debug(f"Инвентарь игрока {player_uuid} инициализирован")

        # Отправляем текущий инвентарь клиенту
        self._send_inventory_update(player_uuid)

    def on_player_leave(self, data: dict):
        """Игрок вышел - сохраняем и очищаем данные."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        # TODO: Сохранить инвентарь в БД
        if player_uuid in self.inventories:
            del self.inventories[player_uuid]

    def on_give_item(self, data: dict):
        """
        Выдать предмет игроку.
        data: {uuid, class_id, count?, data?}
        """
        player_uuid = data.get("uuid")
        class_id = data.get("class_id")
        count = data.get("count", 1)
        extra_data = data.get("data", {})

        if not player_uuid or not class_id:
            return

        success = self.give_item(player_uuid, class_id, count, extra_data)
        if success:
            self.logger.debug(f"Выдан {count}x {class_id} игроку {player_uuid}")
        else:
            # Отправляем сообщение об ошибке
            self.event_manager.post("system_message_to_client", {
                "client_id": player_uuid,
                "message": f"Предмет '{class_id}' не существует. Используйте /items для списка.",
            })

    def on_item_pickup(self, data: dict):
        """Игрок подобрал предмет из мира."""
        player_uuid = data.get("uuid")
        entity_id = data.get("entity_id")  # unique_id entity в мире

        if not player_uuid or not entity_id:
            return

        if player_uuid not in self.inventories:
            return

        # Получаем entity из мира
        entity = None
        if self.entity_manager:
            entity = self.entity_manager.get(entity_id)

        if not entity:
            # Fallback: создаём по class_id
            class_id = data.get("class_id")
            count = data.get("count", 1)
            if class_id:
                self.give_item(player_uuid, class_id, count)
            return

        # Проверяем можно ли подобрать
        if hasattr(entity, 'on_pickup'):
            if not entity.on_pickup(player_uuid):
                return

        # Удаляем из мира
        if self.entity_manager:
            self.entity_manager.remove(entity_id)

        # Добавляем в инвентарь
        self._add_entity_to_inventory(player_uuid, entity)

        self.logger.debug(f"Игрок {player_uuid} подобрал {entity.CLASS_ID}")
        self._send_inventory_update(player_uuid)

    def on_item_drop(self, data: dict):
        """Игрок выбросил предмет."""
        player_uuid = data.get("uuid")
        slot_index = data.get("slot")
        count = data.get("count", 1)
        position = data.get("position")  # Позиция для спавна

        if player_uuid not in self.inventories:
            return

        inventory = self.inventories[player_uuid]
        if slot_index < 0 or slot_index >= len(inventory):
            return

        entity = inventory[slot_index]

        # Проверяем можно ли выбросить
        if hasattr(entity, 'on_drop'):
            if not entity.on_drop(player_uuid, position):
                self.logger.debug(f"Предмет {entity.CLASS_ID} нельзя выбросить")
                return

        # Уменьшаем количество или удаляем
        if entity.count <= count:
            dropped_entity = inventory.pop(slot_index)
        else:
            entity.count -= count
            # Создаём копию для мира
            dropped_entity = ENTITY_REGISTRY.create(entity.CLASS_ID)
            if dropped_entity:
                dropped_entity.count = count
                dropped_entity.data = entity.data.copy()

        # Спавним в мире
        if dropped_entity and self.entity_manager and position:
            self.entity_manager.spawn(dropped_entity, position)

        self.logger.debug(f"Игрок {player_uuid} выбросил {count}x {entity.CLASS_ID}")
        self._send_inventory_update(player_uuid)

    def on_item_use(self, data: dict):
        """Игрок использовал предмет."""
        player_uuid = data.get("uuid")
        slot_index = data.get("slot")

        if player_uuid not in self.inventories:
            return

        inventory = self.inventories[player_uuid]
        if slot_index < 0 or slot_index >= len(inventory):
            return

        entity = inventory[slot_index]

        # Устанавливаем event_manager для entity
        if hasattr(entity, 'set_event_manager'):
            entity.set_event_manager(self.event_manager)

        # Вызываем on_use
        consumed = False
        if hasattr(entity, 'on_use'):
            consumed = entity.on_use(player_uuid)

        if consumed:
            # Уменьшаем количество
            if entity.count <= 1:
                inventory.pop(slot_index)
            else:
                entity.count -= 1

            self.logger.debug(f"Игрок {player_uuid} использовал {entity.CLASS_ID}")
            self._send_inventory_update(player_uuid)

    # -------------------------------------------------------------------------
    # Inventory operations
    # -------------------------------------------------------------------------

    def give_item(
        self,
        player_uuid: str,
        class_id: str,
        count: int = 1,
        extra_data: dict = None
    ) -> bool:
        """
        Выдать предмет игроку.
        Возвращает True если успешно.
        """
        if player_uuid not in self.inventories:
            return False

        # Создаём entity
        entity = ENTITY_REGISTRY.create(class_id)
        if not entity:
            self.logger.warning(f"Неизвестный предмет: {class_id}")
            return False

        entity.count = count
        if extra_data:
            entity.data.update(extra_data)

        # Устанавливаем event_manager
        if hasattr(entity, 'set_event_manager'):
            entity.set_event_manager(self.event_manager)

        # Добавляем в инвентарь
        self._add_entity_to_inventory(player_uuid, entity)
        self._send_inventory_update(player_uuid)

        return True

    def _add_entity_to_inventory(self, player_uuid: str, entity: Entity):
        """Добавляет entity в инвентарь, объединяя стеки если возможно."""
        inventory = self.inventories[player_uuid]

        # Пытаемся добавить в существующий стек
        for existing in inventory:
            can_stack = existing.can_stack_with(entity)
            self.logger.debug(
                f"Stack check: {existing.CLASS_ID}(count={existing.count}) + "
                f"{entity.CLASS_ID}(count={entity.count}) = {can_stack}"
            )
            if can_stack:
                existing.count += entity.count
                self.logger.debug(f"Stacked! New count: {existing.count}")
                return

        # Проверяем свободные слоты
        if len(inventory) >= self.max_slots:
            self.event_manager.post("inventory_full", {"uuid": player_uuid})
            return

        # Добавляем как новый предмет
        inventory.append(entity)
        self.logger.debug(f"Added new slot: {entity.CLASS_ID} (count={entity.count})")

    def _send_inventory_update(self, player_uuid: str):
        """Отправляет обновление инвентаря клиенту."""
        inventory = self.inventories.get(player_uuid, [])

        items = []
        for entity in inventory:
            item_data = {
                "class_id": entity.CLASS_ID,
                "unique_id": entity.unique_id,
                "count": entity.count,
                "data": entity.data,
                "name": getattr(entity, 'NAME', entity.CLASS_ID),
                "description": getattr(entity, 'DESCRIPTION', ''),
                "category": getattr(entity, 'CATEGORY', 'misc'),
                "icon": getattr(entity, 'ICON', ''),
                "rarity": getattr(entity, 'RARITY', 'common'),
                "weight": getattr(entity, 'WEIGHT', 0.0),
                "droppable": getattr(entity, 'DROPPABLE', True),
                "can_equip": hasattr(entity, 'EQUIPMENT_SLOT') and getattr(entity, 'EQUIPMENT_SLOT', None) is not None,
                "can_use": getattr(entity, 'CATEGORY', 'misc') == 'consumable',
                "tooltip": entity.get_tooltip() if hasattr(entity, 'get_tooltip') else '',
                "value": entity.get_value() if hasattr(entity, 'get_value') else 0,
            }
            items.append(item_data)

        # Отправляем клиенту через событие
        self.event_manager.post("inventory_send_to_client", {
            "client_id": player_uuid,
            "data": {
                "type": "inventory_update",
                "inventory": items,
                "max_slots": self.max_slots,
            }
        })

    # -------------------------------------------------------------------------
    # Starting equipment
    # -------------------------------------------------------------------------

    def _grant_starting_equipment(self, player_uuid: str, character_data: dict):
        """Grant class + background starting equipment to a new character."""
        from nine.plugins.dnd.sh_constants import CLASSES, BACKGROUNDS
        from nine.plugins.dnd.sh_starting_equipment import resolve_equipment_key

        char_class = character_data.get("class", "")
        background = character_data.get("background", "")
        granted = []

        # Class starting equipment
        class_info = CLASSES.get(char_class)
        if class_info:
            for key in class_info.get("starting_equipment", []):
                class_id, count = resolve_equipment_key(key)
                if self.give_item(player_uuid, class_id, count):
                    granted.append(f"{count}x {class_id}")
                else:
                    self.logger.warning(
                        f"Starting equipment: unknown item '{class_id}' "
                        f"(from class '{char_class}' key '{key}')"
                    )

        # Background equipment
        bg_info = BACKGROUNDS.get(background)
        if bg_info:
            for key in bg_info.get("equipment", []):
                class_id, count = resolve_equipment_key(key)
                if self.give_item(player_uuid, class_id, count):
                    granted.append(f"{count}x {class_id}")
                else:
                    self.logger.warning(
                        f"Starting equipment: unknown item '{class_id}' "
                        f"(from background '{background}' key '{key}')"
                    )

            # Background gold as n_bucks
            gold = bg_info.get("gold", 0)
            if gold > 0:
                if self.give_item(player_uuid, "n_bucks", gold):
                    granted.append(f"{gold}x n_bucks")

        if granted:
            self.logger.info(
                f"Granted starting equipment to {player_uuid}: "
                + ", ".join(granted)
            )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_inventory(self, player_uuid: str) -> List[Entity]:
        """Получить инвентарь игрока."""
        return self.inventories.get(player_uuid, [])

    def has_item(self, player_uuid: str, class_id: str, count: int = 1) -> bool:
        """Проверить наличие предмета у игрока."""
        total = 0
        for entity in self.inventories.get(player_uuid, []):
            if entity.CLASS_ID == class_id:
                total += entity.count
                if total >= count:
                    return True
        return False

    def remove_item(self, player_uuid: str, class_id: str, count: int = 1) -> bool:
        """Удалить предмет из инвентаря."""
        if not self.has_item(player_uuid, class_id, count):
            return False

        remaining = count
        inventory = self.inventories.get(player_uuid, [])
        to_remove = []

        for i, entity in enumerate(inventory):
            if entity.CLASS_ID == class_id and remaining > 0:
                if entity.count <= remaining:
                    remaining -= entity.count
                    to_remove.append(i)
                else:
                    entity.count -= remaining
                    remaining = 0

        # Удаляем пустые слоты (в обратном порядке)
        for i in reversed(to_remove):
            inventory.pop(i)

        self._send_inventory_update(player_uuid)
        return True

    def get_registered_items(self) -> Dict[str, dict]:
        """Получить список всех зарегистрированных предметов."""
        result = {}
        for class_id, cls in ENTITY_REGISTRY.get_all_classes().items():
            if hasattr(cls, 'get_info'):
                result[class_id] = cls.get_info()
            else:
                result[class_id] = {
                    "class_id": class_id,
                    "name": getattr(cls, 'NAME', class_id),
                }
        return result
