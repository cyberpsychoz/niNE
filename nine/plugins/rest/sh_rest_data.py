"""
Dataclasses для системы отдыха.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class RestType(Enum):
    """Тип отдыха."""
    SHORT = "short"  # 1 час
    LONG = "long"    # 8 часов


# Hit Die по классам D&D 5e
CLASS_HIT_DIE: Dict[str, int] = {
    "barbarian": 12,
    "fighter": 10,
    "paladin": 10,
    "ranger": 10,
    "bard": 8,
    "cleric": 8,
    "druid": 8,
    "monk": 8,
    "rogue": 8,
    "warlock": 8,
    "sorcerer": 6,
    "wizard": 6,
}


def get_hit_die(character_class: str) -> int:
    """Возвращает размер Hit Die для класса."""
    return CLASS_HIT_DIE.get(character_class.lower(), 8)


@dataclass
class RestResult:
    """Результат отдыха."""
    rest_type: str
    hp_restored: int = 0
    hp_new: int = 0
    hp_max: int = 0
    hit_dice_spent: int = 0
    hit_dice_remaining: int = 0
    hit_dice_max: int = 0
    spell_slots_restored: bool = False
    conditions_removed: list = None

    def __post_init__(self):
        if self.conditions_removed is None:
            self.conditions_removed = []


@dataclass
class HitDicePool:
    """Пул Hit Dice персонажа."""
    current: int = 1
    maximum: int = 1
    die_size: int = 8  # d8 по умолчанию

    def spend(self, count: int = 1) -> int:
        """Тратит Hit Dice. Возвращает фактически потраченное количество."""
        actual = min(count, self.current)
        self.current -= actual
        return actual

    def restore(self, count: int = 1) -> int:
        """Восстанавливает Hit Dice. Возвращает фактически восстановленное количество."""
        old = self.current
        self.current = min(self.current + count, self.maximum)
        return self.current - old

    def restore_half(self) -> int:
        """Восстанавливает половину Hit Dice (минимум 1). Для Long Rest."""
        to_restore = max(1, self.maximum // 2)
        return self.restore(to_restore)
