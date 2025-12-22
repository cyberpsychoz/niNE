"""
Зелье маны - восстанавливает MP игрока.
"""

from nine.plugins.inventory.entities.base import Item


class ManaPotion(Item):
    """Зелье, восстанавливающее ману."""

    CLASS_ID = "sushi"
    NAME = "Суси"
    DESCRIPTION = "М-м-м ом-ном-ном"
    CATEGORY = "consumable"
    MAX_STACK = 8
    WEIGHT = 0.5
    RARITY = "common"

    # Кастомные свойства
    RESTORE_AMOUNT = 50

    def on_use(self, player_uuid: str) -> bool:
        """Использование суси - восстанавливает голод"""
        if not self.can_use(player_uuid):
            return False

        self.post_event("player_restore_hunger", {
            "uuid": player_uuid,
            "amount": self.RESTORE_AMOUNT,
            "source": "sushi",
        })

        return True

    def get_value(self) -> int:
        return 25
