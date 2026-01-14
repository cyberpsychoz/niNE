"""
Класс аксессуаров для D&D 5e.

Аксессуары — это магические предметы, которые носятся в специальных слотах:
- Кольца (2 слота)
- Амулеты/ожерелья
- Плащи/накидки
- Пояса

Большинство магических аксессуаров требуют настройки (attunement).
"""

from enum import Enum
from typing import Optional, List

from .base_equipment import Equipment, StatBonus, EquipmentRequirements
from .sh_equipment_slots import EquipmentSlot


class AccessoryType(Enum):
    """Типы аксессуаров."""
    RING = "ring"           # Кольцо
    AMULET = "amulet"       # Амулет, ожерелье
    CLOAK = "cloak"         # Плащ, накидка
    BELT = "belt"           # Пояс
    CIRCLET = "circlet"     # Диадема, обруч (головной убор)
    BRACERS = "bracers"     # Наручи
    BOOTS = "boots"         # Волшебные сапоги
    GLOVES = "gloves"       # Волшебные перчатки


# Информация о типах аксессуаров
ACCESSORY_TYPE_INFO = {
    AccessoryType.RING: {
        "name_ru": "Кольцо",
        "name_en": "Ring",
        "slots": [EquipmentSlot.RING_1, EquipmentSlot.RING_2],
        "default_slot": EquipmentSlot.RING_1,
    },
    AccessoryType.AMULET: {
        "name_ru": "Амулет",
        "name_en": "Amulet",
        "slots": [EquipmentSlot.AMULET],
        "default_slot": EquipmentSlot.AMULET,
    },
    AccessoryType.CLOAK: {
        "name_ru": "Плащ",
        "name_en": "Cloak",
        "slots": [EquipmentSlot.CLOAK],
        "default_slot": EquipmentSlot.CLOAK,
    },
    AccessoryType.BELT: {
        "name_ru": "Пояс",
        "name_en": "Belt",
        "slots": [EquipmentSlot.BELT],
        "default_slot": EquipmentSlot.BELT,
    },
    AccessoryType.CIRCLET: {
        "name_ru": "Диадема",
        "name_en": "Circlet",
        "slots": [EquipmentSlot.HEAD],
        "default_slot": EquipmentSlot.HEAD,
    },
    AccessoryType.BRACERS: {
        "name_ru": "Наручи",
        "name_en": "Bracers",
        "slots": [EquipmentSlot.HANDS],
        "default_slot": EquipmentSlot.HANDS,
    },
    AccessoryType.BOOTS: {
        "name_ru": "Сапоги",
        "name_en": "Boots",
        "slots": [EquipmentSlot.FEET],
        "default_slot": EquipmentSlot.FEET,
    },
    AccessoryType.GLOVES: {
        "name_ru": "Перчатки",
        "name_en": "Gloves",
        "slots": [EquipmentSlot.HANDS],
        "default_slot": EquipmentSlot.HANDS,
    },
}


class Accessory(Equipment):
    """
    Базовый класс для аксессуаров.

    Аксессуары обычно магические и дают различные бонусы:
    - Бонусы к характеристикам
    - Сопротивления к урону
    - Иммунитет к состояниям
    - Особые способности

    Большинство требуют настройки (attunement), что ограничивает
    количество используемых магических предметов до 3.

    Пример:
    ```python
    class RingOfProtection(Accessory):
        CLASS_ID = "ring_of_protection"
        NAME = "Кольцо защиты"
        ACCESSORY_TYPE = AccessoryType.RING
        ATTUNEMENT = True
        STAT_BONUS = StatBonus(armor_class=1)
        RARITY = "rare"
    ```
    """

    CLASS_ID = "base_accessory"
    NAME = "Accessory"
    CATEGORY = "equipment"
    EQUIPMENT_TYPE = "accessory"

    # Тип аксессуара
    ACCESSORY_TYPE: AccessoryType = AccessoryType.RING

    # Аксессуары обычно магические
    MAGICAL: bool = True

    # Активируемая способность (если есть)
    ABILITY_NAME: Optional[str] = None
    ABILITY_DESCRIPTION: Optional[str] = None
    ABILITY_USES: int = 0           # 0 = неограниченно
    ABILITY_RECHARGE: str = ""      # "dawn" = на рассвете, "short_rest", "long_rest"

    def __init__(self, unique_id: Optional[str] = None):
        super().__init__(unique_id)

        # Текущие использования способности
        if self.ABILITY_USES > 0:
            self.data["ability_charges"] = self.ABILITY_USES

        # Устанавливаем слот по типу
        type_info = ACCESSORY_TYPE_INFO.get(self.ACCESSORY_TYPE, {})
        self.EQUIPMENT_SLOT = type_info.get("default_slot", EquipmentSlot.RING_1)

    @property
    def ability_charges(self) -> int:
        """Текущие заряды способности."""
        if self.ABILITY_USES == 0:
            return -1  # Неограниченно
        return self.data.get("ability_charges", self.ABILITY_USES)

    @ability_charges.setter
    def ability_charges(self, value: int):
        if self.ABILITY_USES > 0:
            self.data["ability_charges"] = max(0, min(value, self.ABILITY_USES))

    def get_valid_slots(self) -> List[EquipmentSlot]:
        """Получить список допустимых слотов для этого аксессуара."""
        type_info = ACCESSORY_TYPE_INFO.get(self.ACCESSORY_TYPE, {})
        return type_info.get("slots", [self.EQUIPMENT_SLOT])

    def can_equip_in_slot(self, slot: str) -> bool:
        """Проверить, можно ли экипировать в данный слот."""
        valid_slots = self.get_valid_slots()
        return any(s.value == slot for s in valid_slots)

    def on_equip(self, player_uuid: str, slot: str) -> bool:
        """Экипировка аксессуара."""
        # Проверяем допустимый слот
        if not self.can_equip_in_slot(slot):
            return False

        if not super().on_equip(player_uuid, slot):
            return False

        # Отправляем событие
        self.post_event("accessory_equipped", {
            "uuid": player_uuid,
            "accessory_id": self.CLASS_ID,
            "slot": slot,
            "ability": self.ABILITY_NAME,
        })

        return True

    def use_ability(self, player_uuid: str) -> bool:
        """
        Использовать активируемую способность аксессуара.

        Args:
            player_uuid: UUID игрока

        Returns:
            True если способность использована успешно
        """
        if not self.ABILITY_NAME:
            return False

        # Проверяем заряды
        if self.ABILITY_USES > 0 and self.ability_charges <= 0:
            self.post_event("item_no_charges", {
                "uuid": player_uuid,
                "item_id": self.CLASS_ID,
                "ability": self.ABILITY_NAME,
            })
            return False

        # Расходуем заряд
        if self.ABILITY_USES > 0:
            self.ability_charges -= 1

        # Отправляем событие использования
        self.post_event("accessory_ability_used", {
            "uuid": player_uuid,
            "accessory_id": self.CLASS_ID,
            "ability": self.ABILITY_NAME,
            "charges_remaining": self.ability_charges,
        })

        return True

    def recharge(self, amount: Optional[int] = None):
        """
        Восстановить заряды способности.

        Args:
            amount: Количество зарядов (None = полное восстановление)
        """
        if self.ABILITY_USES == 0:
            return

        if amount is None:
            self.ability_charges = self.ABILITY_USES
        else:
            self.ability_charges += amount

    def get_tooltip(self) -> str:
        """Tooltip для аксессуара."""
        lines = [self.NAME]

        if self.DESCRIPTION:
            lines.append(self.DESCRIPTION)

        lines.append("")

        # Тип
        type_info = ACCESSORY_TYPE_INFO.get(self.ACCESSORY_TYPE, {})
        type_name = type_info.get("name_ru", "Аксессуар")
        lines.append(f"Тип: {type_name}")

        # Редкость
        rarity_names = {
            "common": "Обычный",
            "uncommon": "Необычный",
            "rare": "Редкий",
            "very_rare": "Очень редкий",
            "legendary": "Легендарный",
            "artifact": "Артефакт",
        }
        rarity = rarity_names.get(self.RARITY, self.RARITY)
        lines.append(f"Редкость: {rarity}")

        # Бонусы
        bonus = self.STAT_BONUS
        bonuses = []

        if bonus.armor_class != 0:
            bonuses.append(f"AC {'+' if bonus.armor_class > 0 else ''}{bonus.armor_class}")
        if bonus.strength != 0:
            bonuses.append(f"СИЛ {'+' if bonus.strength > 0 else ''}{bonus.strength}")
        if bonus.dexterity != 0:
            bonuses.append(f"ЛОВ {'+' if bonus.dexterity > 0 else ''}{bonus.dexterity}")
        if bonus.constitution != 0:
            bonuses.append(f"ТЕЛ {'+' if bonus.constitution > 0 else ''}{bonus.constitution}")
        if bonus.intelligence != 0:
            bonuses.append(f"ИНТ {'+' if bonus.intelligence > 0 else ''}{bonus.intelligence}")
        if bonus.wisdom != 0:
            bonuses.append(f"МДР {'+' if bonus.wisdom > 0 else ''}{bonus.wisdom}")
        if bonus.charisma != 0:
            bonuses.append(f"ХАР {'+' if bonus.charisma > 0 else ''}{bonus.charisma}")
        if bonus.speed != 0:
            bonuses.append(f"Скорость {'+' if bonus.speed > 0 else ''}{bonus.speed} фт.")

        if bonuses:
            lines.append("")
            lines.append("Бонусы: " + ", ".join(bonuses))

        # Сопротивления
        if bonus.damage_resistance:
            lines.append(f"Сопротивление: {', '.join(bonus.damage_resistance)}")
        if bonus.condition_immunity:
            lines.append(f"Иммунитет: {', '.join(bonus.condition_immunity)}")

        # Способность
        if self.ABILITY_NAME:
            lines.append("")
            lines.append(f"Способность: {self.ABILITY_NAME}")
            if self.ABILITY_DESCRIPTION:
                lines.append(f"  {self.ABILITY_DESCRIPTION}")
            if self.ABILITY_USES > 0:
                lines.append(f"  Заряды: {self.ability_charges}/{self.ABILITY_USES}")
                if self.ABILITY_RECHARGE:
                    recharge_names = {
                        "dawn": "на рассвете",
                        "short_rest": "после короткого отдыха",
                        "long_rest": "после длительного отдыха",
                    }
                    recharge = recharge_names.get(self.ABILITY_RECHARGE, self.ABILITY_RECHARGE)
                    lines.append(f"  Восстановление: {recharge}")

        # Требует настройки
        if self.ATTUNEMENT:
            lines.append("")
            lines.append("[Требует настройки]")

        return "\n".join(lines)

    @classmethod
    def get_info(cls) -> dict:
        """Информация о классе аксессуара."""
        info = super().get_info()
        info.update({
            "accessory_type": cls.ACCESSORY_TYPE.value,
            "ability_name": cls.ABILITY_NAME,
            "ability_uses": cls.ABILITY_USES,
            "ability_recharge": cls.ABILITY_RECHARGE,
        })
        return info


# =============================================================================
# Предустановленные базовые типы аксессуаров
# =============================================================================

class Ring(Accessory):
    """Базовый класс для колец."""
    ACCESSORY_TYPE = AccessoryType.RING
    EQUIPMENT_SLOT = EquipmentSlot.RING_1


class Amulet(Accessory):
    """Базовый класс для амулетов."""
    ACCESSORY_TYPE = AccessoryType.AMULET
    EQUIPMENT_SLOT = EquipmentSlot.AMULET


class Cloak(Accessory):
    """Базовый класс для плащей."""
    ACCESSORY_TYPE = AccessoryType.CLOAK
    EQUIPMENT_SLOT = EquipmentSlot.CLOAK


class Belt(Accessory):
    """Базовый класс для поясов."""
    ACCESSORY_TYPE = AccessoryType.BELT
    EQUIPMENT_SLOT = EquipmentSlot.BELT
