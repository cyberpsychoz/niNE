"""
Базовый класс Item для инвентарных предметов.
Все предметы в папке entities должны наследоваться от него.
"""

from typing import Optional, Dict, Any
from nine.core.entity import Entity, Component


class Item(Entity):
    """
    Базовый класс для предметов инвентаря.
    Наследуйте от него для создания своих предметов.

    Пример использования:
    ```python
    from nine.plugins.inventory.entities.base import Item

    class HealthPotion(Item):
        CLASS_ID = "health_potion"
        NAME = "Зелье здоровья"
        DESCRIPTION = "Восстанавливает 50 HP"
        CATEGORY = "consumable"
        MAX_STACK = 10
        WEIGHT = 0.5

        # Кастомные свойства
        HEAL_AMOUNT = 50

        def on_use(self, player_uuid: str) -> bool:
            # Вызов лечения через event manager
            self.post_event("player_heal", {
                "uuid": player_uuid,
                "amount": self.HEAL_AMOUNT,
            })
            return True  # Предмет потреблён
    ```
    """

    CLASS_ID = "base_item"
    NAME = "Item"
    DESCRIPTION = ""
    CATEGORY = "misc"  # consumable, weapon, armor, tool, misc
    MAX_STACK = 1
    WEIGHT = 0.0
    DROPPABLE = True
    TRADEABLE = True
    MODEL = ""  # Пустая строка = жёлтый куб
    ICON = ""

    # Опциональные свойства
    RARITY = "common"  # common, uncommon, rare, epic, legendary
    LEVEL_REQUIREMENT = 0
    USE_TIME = 0.0  # Время использования в секундах (0 = мгновенно)
    COOLDOWN = 0.0  # Кулдаун после использования

    def __init__(self, unique_id: Optional[str] = None):
        super().__init__(unique_id)
        self._event_manager = None
        self._last_use_time = 0.0

    def set_event_manager(self, event_manager):
        """Устанавливает event manager для отправки событий."""
        self._event_manager = event_manager

    def post_event(self, event_type: str, data: dict):
        """Отправляет событие через event manager."""
        if self._event_manager:
            self._event_manager.post(event_type, data)

    # -------------------------------------------------------------------------
    # Хуки для переопределения (Helix-style)
    # -------------------------------------------------------------------------

    def on_use(self, player_uuid: str) -> bool:
        """
        Вызывается при использовании предмета.

        Args:
            player_uuid: UUID игрока, использующего предмет

        Returns:
            True если предмет был потреблён (нужно уменьшить count)
            False если использование не удалось
        """
        return False

    def on_pickup(self, player_uuid: str) -> bool:
        """
        Вызывается когда игрок подбирает предмет.

        Args:
            player_uuid: UUID игрока

        Returns:
            True если подбор разрешён
            False чтобы отменить подбор
        """
        self._owner_uuid = player_uuid
        return True

    def on_drop(self, player_uuid: str, position=None) -> bool:
        """
        Вызывается когда игрок выбрасывает предмет.

        Args:
            player_uuid: UUID игрока
            position: Позиция для спавна предмета в мире

        Returns:
            True если выброс разрешён
            False чтобы отменить
        """
        if not self.DROPPABLE:
            return False
        self._owner_uuid = None
        return True

    def on_equip(self, player_uuid: str, slot: str) -> bool:
        """
        Вызывается при экипировке предмета.

        Args:
            player_uuid: UUID игрока
            slot: Слот экипировки (head, chest, hands, legs, feet, weapon, etc.)

        Returns:
            True если экипировка разрешена
        """
        return True

    def on_unequip(self, player_uuid: str) -> bool:
        """
        Вызывается при снятии экипировки.

        Args:
            player_uuid: UUID игрока

        Returns:
            True если снятие разрешено
        """
        return True

    def on_spawn(self, world, position=None):
        """Вызывается когда предмет появляется в мире (выброшен)."""
        super().on_spawn(world, position)

    def on_remove(self):
        """Вызывается когда предмет удаляется из мира."""
        super().on_remove()

    # -------------------------------------------------------------------------
    # Утилитные методы
    # -------------------------------------------------------------------------

    def get_display_name(self) -> str:
        """Получить отображаемое имя с учётом количества."""
        if self.count > 1:
            return f"{self.NAME} x{self.count}"
        return self.NAME

    def get_tooltip(self) -> str:
        """Получить текст для tooltip."""
        lines = [self.NAME]
        if self.DESCRIPTION:
            lines.append(self.DESCRIPTION)
        if self.WEIGHT > 0:
            lines.append(f"Вес: {self.WEIGHT:.1f}")
        if self.RARITY != "common":
            lines.append(f"Редкость: {self.RARITY}")
        return "\n".join(lines)

    def can_use(self, player_uuid: str) -> bool:
        """Проверить можно ли использовать предмет."""
        # Переопределите для проверки требований
        return True

    def get_value(self) -> int:
        """Получить стоимость предмета (для торговли)."""
        # Переопределите для кастомной стоимости
        return 0

    @classmethod
    def get_info(cls) -> dict:
        """Получить информацию о классе предмета."""
        return {
            "class_id": cls.CLASS_ID,
            "name": cls.NAME,
            "description": cls.DESCRIPTION,
            "category": cls.CATEGORY,
            "max_stack": cls.MAX_STACK,
            "weight": cls.WEIGHT,
            "droppable": cls.DROPPABLE,
            "tradeable": cls.TRADEABLE,
            "rarity": cls.RARITY,
            "model": cls.MODEL,
            "icon": cls.ICON,
        }
