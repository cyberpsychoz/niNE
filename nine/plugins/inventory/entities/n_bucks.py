"""
n_bucks - основная валюта.
"""

from nine.plugins.inventory.entities.base import Item


class GoldCoin(Item):
    """Вот они - робуксы"""

    CLASS_ID = "n_bucks"
    NAME = "Най-Бакс"
    DESCRIPTION = "Основная валюта"
    CATEGORY = "currency"
    MAX_STACK = 9999
    WEIGHT = 0.01
    DROPPABLE = False  # Нельзя выбросить
    TRADEABLE = True
    RARITY = "common"

    def on_use(self, player_uuid: str) -> bool:
        """Монеты нельзя использовать напрямую."""
        return False

    def on_drop(self, player_uuid: str, position=None) -> bool:
        """Монеты нельзя выбросить."""
        return False

    def get_value(self) -> int:
        """Стоимость = количество."""
        return self.count
