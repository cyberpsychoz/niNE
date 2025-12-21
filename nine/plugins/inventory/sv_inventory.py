"""
Серверный модуль системы инвентаря.
Управляет инвентарями игроков на сервере.
"""

import importlib.util
from pathlib import Path
from typing import Dict, List, Optional
from nine.core.plugins import PluginModule


def _load_items_module():
    """Загружает модуль sh_items.py из той же папки."""
    items_path = Path(__file__).parent / "sh_items.py"
    spec = importlib.util.spec_from_file_location("inventory_items", items_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_items = _load_items_module()
ItemStack = _items.ItemStack
get_item_definition = _items.get_item_definition


class InventoryServerModule(PluginModule):
    """
    Серверный модуль управления инвентарем.
    Отслеживает предметы игроков и обрабатывает операции.
    """

    def on_load(self):
        # {player_uuid: [ItemStack, ...]}
        self.inventories: Dict[str, List[ItemStack]] = {}
        # Максимальный размер инвентаря
        self.max_slots = 20

        # Подписки на события
        self.event_manager.subscribe("player_joined", self.on_player_join)
        self.event_manager.subscribe("player_left", self.on_player_leave)
        self.event_manager.subscribe("item_pickup", self.on_item_pickup)
        self.event_manager.subscribe("item_drop", self.on_item_drop)
        self.event_manager.subscribe("item_use", self.on_item_use)

        self.logger.info("Серверный модуль инвентаря загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("player_joined", self.on_player_join)
        self.event_manager.unsubscribe("player_left", self.on_player_leave)
        self.event_manager.unsubscribe("item_pickup", self.on_item_pickup)
        self.event_manager.unsubscribe("item_drop", self.on_item_drop)
        self.event_manager.unsubscribe("item_use", self.on_item_use)

        self.logger.info("Серверный модуль инвентаря выгружен")

    def on_player_join(self, data: dict):
        """Игрок присоединился - инициализируем инвентарь."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        # TODO: Загрузить инвентарь из БД
        # Пока создаем пустой инвентарь
        self.inventories[player_uuid] = []

        self.logger.debug(f"Инвентарь игрока {player_uuid} инициализирован")

    def on_player_leave(self, data: dict):
        """Игрок вышел - сохраняем и очищаем данные."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        # TODO: Сохранить инвентарь в БД
        if player_uuid in self.inventories:
            del self.inventories[player_uuid]

    def on_item_pickup(self, data: dict):
        """Игрок подобрал предмет."""
        player_uuid = data.get("uuid")
        item_id = data.get("item_id")
        count = data.get("count", 1)

        if player_uuid not in self.inventories:
            return

        # Проверяем существование предмета
        item_def = get_item_definition(item_id)
        if not item_def:
            self.logger.warning(f"Неизвестный предмет: {item_id}")
            return

        # Пытаемся добавить в существующий стак
        added = self._add_to_existing_stack(player_uuid, item_id, count, item_def.max_stack)

        # Если не удалось добавить в стак, создаем новый
        if not added:
            if len(self.inventories[player_uuid]) >= self.max_slots:
                self.logger.debug(f"Инвентарь игрока {player_uuid} полон")
                self.event_manager.post("inventory_full", {"uuid": player_uuid})
                return

            self.inventories[player_uuid].append(ItemStack(item_id, count))

        self.logger.debug(f"Игрок {player_uuid} подобрал {count}x {item_id}")

        # Уведомляем клиента
        self._send_inventory_update(player_uuid)

    def on_item_drop(self, data: dict):
        """Игрок выбросил предмет."""
        player_uuid = data.get("uuid")
        slot_index = data.get("slot")
        count = data.get("count", 1)

        if player_uuid not in self.inventories:
            return

        inventory = self.inventories[player_uuid]
        if slot_index < 0 or slot_index >= len(inventory):
            return

        item_stack = inventory[slot_index]
        item_def = get_item_definition(item_stack.item_id)

        if item_def and not item_def.droppable:
            self.logger.debug(f"Предмет {item_stack.item_id} нельзя выбросить")
            return

        # Уменьшаем количество или удаляем стак
        if item_stack.count <= count:
            inventory.pop(slot_index)
        else:
            item_stack.count -= count

        self.logger.debug(f"Игрок {player_uuid} выбросил {count}x {item_stack.item_id}")

        # Уведомляем клиента
        self._send_inventory_update(player_uuid)

        # Создаем предмет в мире
        self.event_manager.post("item_spawned", {
            "item_id": item_stack.item_id,
            "count": count,
            "player_uuid": player_uuid,  # Для определения позиции спавна
        })

    def on_item_use(self, data: dict):
        """Игрок использовал предмет."""
        player_uuid = data.get("uuid")
        slot_index = data.get("slot")

        if player_uuid not in self.inventories:
            return

        inventory = self.inventories[player_uuid]
        if slot_index < 0 or slot_index >= len(inventory):
            return

        item_stack = inventory[slot_index]
        item_def = get_item_definition(item_stack.item_id)

        if not item_def:
            return

        # Обрабатываем использование в зависимости от типа
        if item_def.category == "consumable":
            self._use_consumable(player_uuid, item_stack, slot_index)

        self.logger.debug(f"Игрок {player_uuid} использовал {item_stack.item_id}")

    def _add_to_existing_stack(
        self,
        player_uuid: str,
        item_id: str,
        count: int,
        max_stack: int
    ) -> bool:
        """Пытается добавить предметы в существующий стак."""
        for stack in self.inventories[player_uuid]:
            if stack.item_id == item_id and stack.count < max_stack:
                space = max_stack - stack.count
                to_add = min(count, space)
                stack.count += to_add
                return to_add == count  # True если все добавлено
        return False

    def _use_consumable(
        self,
        player_uuid: str,
        item_stack: ItemStack,
        slot_index: int
    ):
        """Использует расходуемый предмет."""
        # Обрабатываем эффект
        if item_stack.item_id == "health_potion":
            self.event_manager.post("player_heal", {
                "uuid": player_uuid,
                "amount": 50,
            })
        elif item_stack.item_id == "mana_potion":
            self.event_manager.post("player_restore_mana", {
                "uuid": player_uuid,
                "amount": 50,
            })

        # Уменьшаем количество
        inventory = self.inventories[player_uuid]
        if item_stack.count <= 1:
            inventory.pop(slot_index)
        else:
            item_stack.count -= 1

        self._send_inventory_update(player_uuid)

    def _send_inventory_update(self, player_uuid: str):
        """Отправляет обновление инвентаря клиенту."""
        inventory = self.inventories.get(player_uuid, [])
        self.event_manager.post("inventory_updated", {
            "uuid": player_uuid,
            "inventory": [stack.to_dict() for stack in inventory],
            "max_slots": self.max_slots,
        })

    def get_inventory(self, player_uuid: str) -> List[ItemStack]:
        """Получить инвентарь игрока."""
        return self.inventories.get(player_uuid, [])

    def has_item(self, player_uuid: str, item_id: str, count: int = 1) -> bool:
        """Проверить наличие предмета у игрока."""
        total = 0
        for stack in self.inventories.get(player_uuid, []):
            if stack.item_id == item_id:
                total += stack.count
                if total >= count:
                    return True
        return False
