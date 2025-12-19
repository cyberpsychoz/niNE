"""
Общие классы и определения предметов.
Доступны и на сервере, и на клиенте.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ItemDefinition:
    """
    Определение типа предмета.
    Описывает свойства класса предметов.
    """
    item_id: str                    # Уникальный ID типа предмета
    name: str                       # Отображаемое имя
    description: str = ""           # Описание
    max_stack: int = 1              # Максимальный размер стака
    weight: float = 0.0             # Вес одной единицы
    category: str = "misc"          # Категория (weapon, armor, consumable, misc)
    icon: str = ""                  # Путь к иконке
    tradeable: bool = True          # Можно ли продавать/обменивать
    droppable: bool = True          # Можно ли выбросить


@dataclass
class ItemStack:
    """
    Стек предметов в инвентаре.
    Представляет конкретные предметы у игрока.
    """
    item_id: str                    # ID типа предмета
    count: int = 1                  # Количество
    data: Optional[Dict[str, Any]] = None  # Дополнительные данные (прочность и т.д.)

    def to_dict(self) -> dict:
        """Сериализация для передачи по сети."""
        return {
            "item_id": self.item_id,
            "count": self.count,
            "data": self.data or {},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ItemStack":
        """Десериализация из словаря."""
        return cls(
            item_id=data["item_id"],
            count=data.get("count", 1),
            data=data.get("data"),
        )


# Реестр предметов (заполняется при загрузке)
ITEM_REGISTRY: Dict[str, ItemDefinition] = {}


def register_item(item_def: ItemDefinition):
    """Регистрирует новый тип предмета."""
    ITEM_REGISTRY[item_def.item_id] = item_def


def get_item_definition(item_id: str) -> Optional[ItemDefinition]:
    """Получает определение предмета по ID."""
    return ITEM_REGISTRY.get(item_id)


# Базовые предметы
_BASE_ITEMS = [
    ItemDefinition(
        item_id="health_potion",
        name="Зелье здоровья",
        description="Восстанавливает 50 HP",
        max_stack=10,
        weight=0.5,
        category="consumable",
    ),
    ItemDefinition(
        item_id="mana_potion",
        name="Зелье маны",
        description="Восстанавливает 50 MP",
        max_stack=10,
        weight=0.5,
        category="consumable",
    ),
    ItemDefinition(
        item_id="gold_coin",
        name="Золотая монета",
        description="Основная валюта",
        max_stack=9999,
        weight=0.01,
        category="misc",
        droppable=False,
    ),
]

# Регистрируем базовые предметы
for item in _BASE_ITEMS:
    register_item(item)
