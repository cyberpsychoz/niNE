"""
Зелье здоровья - восстанавливает HP игрока.
"""

from nine.plugins.inventory.entities.base import Item


class HealthPotion(Item):
    """Зелье, восстанавливающее здоровье."""

    CLASS_ID = "health_potion"
    NAME = "Медицинский препарат"
    DESCRIPTION = "Восстанавливает 50 HP"
    CATEGORY = "consumable"
    MAX_STACK = 10
    WEIGHT = 0.5
    RARITY = "common"

    # Кастомные свойства этого предмета
    HEAL_AMOUNT = 50

    def on_use(self, player_uuid: str) -> bool:
        """Использование зелья - лечит игрока."""
        if not self.can_use(player_uuid):
            return False

        # Отправляем событие лечения
        self.post_event("player_heal", {
            "uuid": player_uuid,
            "amount": self.HEAL_AMOUNT,
            "source": "health_potion",
        })

        # Возвращаем True - предмет потреблён
        return True

    def can_use(self, player_uuid: str) -> bool:
        """Проверка - можно использовать только если HP не полное."""
        # TODO: Проверить текущее HP игрока
        return True

    def get_value(self) -> int:
        """Стоимость зелья."""
        return 25
