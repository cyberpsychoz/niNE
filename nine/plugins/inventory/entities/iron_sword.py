"""
Железный меч - базовое оружие.
Пример экипируемого предмета.
"""

from nine.plugins.inventory.entities.base import Item


class IronSword(Item):
    """Простой железный меч."""

    CLASS_ID = "iron_sword"
    NAME = "Железный меч"
    DESCRIPTION = "Ну куда же без него?"
    CATEGORY = "weapon"
    MAX_STACK = 1  # Оружие не стакается
    WEIGHT = 3.0
    RARITY = "common"

    # Характеристики оружия
    DAMAGE = 15
    ATTACK_SPEED = 1.0
    DURABILITY_MAX = 100

    def __init__(self, unique_id=None):
        super().__init__(unique_id)
        # Прочность хранится в data для каждого экземпляра
        self.data["durability"] = self.DURABILITY_MAX

    @property
    def durability(self) -> int:
        return self.data.get("durability", self.DURABILITY_MAX)

    @durability.setter
    def durability(self, value: int):
        self.data["durability"] = max(0, min(value, self.DURABILITY_MAX))

    def on_equip(self, player_uuid: str, slot: str) -> bool:
        """Экипировка меча."""
        if slot != "weapon":
            return False

        # Уведомляем о бонусе к урону
        self.post_event("player_stat_changed", {
            "uuid": player_uuid,
            "stat": "damage",
            "change": self.DAMAGE,
            "source": self.CLASS_ID,
        })

        return True

    def on_unequip(self, player_uuid: str) -> bool:
        """Снятие меча."""
        # Убираем бонус к урону
        self.post_event("player_stat_changed", {
            "uuid": player_uuid,
            "stat": "damage",
            "change": -self.DAMAGE,
            "source": self.CLASS_ID,
        })

        return True

    def on_attack(self, player_uuid: str, target_uuid: str) -> int:
        """
        Вызывается при атаке этим оружием.
        Возвращает нанесённый урон.
        """
        # Уменьшаем прочность
        self.durability -= 1

        if self.durability <= 0:
            # Оружие сломалось
            self.post_event("item_broken", {
                "uuid": player_uuid,
                "item_id": self.CLASS_ID,
                "unique_id": self.unique_id,
            })
            return 0

        return self.DAMAGE

    def get_tooltip(self) -> str:
        """Расширенный tooltip с характеристиками."""
        lines = [
            self.NAME,
            self.DESCRIPTION,
            "",
            f"Урон: {self.DAMAGE}",
            f"Скорость атаки: {self.ATTACK_SPEED:.1f}",
            f"Прочность: {self.durability}/{self.DURABILITY_MAX}",
        ]
        return "\n".join(lines)

    def get_value(self) -> int:
        # Цена зависит от прочности
        durability_ratio = self.durability / self.DURABILITY_MAX
        base_value = 100
        return int(base_value * durability_ratio)
