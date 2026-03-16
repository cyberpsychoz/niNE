"""
Класс брони для D&D 5e.

Поддерживает три типа брони:
- Light (Лёгкая): полный бонус DEX, без помех
- Medium (Средняя): макс. +2 DEX, некоторые дают помеху к скрытности
- Heavy (Тяжёлая): без бонуса DEX, помеха к скрытности, требование Силы
"""

from enum import Enum
from typing import Optional

from .base_equipment import Equipment, StatBonus, EquipmentRequirements
from .sh_equipment_slots import EquipmentSlot


class ArmorType(Enum):
    """Типы брони D&D 5e."""
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    SHIELD = "shield"


# Информация о типах брони
ARMOR_TYPE_INFO = {
    ArmorType.LIGHT: {
        "name_ru": "Лёгкая броня",
        "name_en": "Light Armor",
        "proficiency": "light_armor",
        "max_dex_bonus": None,  # Без ограничений
        "stealth_disadvantage": False,
    },
    ArmorType.MEDIUM: {
        "name_ru": "Средняя броня",
        "name_en": "Medium Armor",
        "proficiency": "medium_armor",
        "max_dex_bonus": 2,
        "stealth_disadvantage": False,  # Зависит от конкретной брони
    },
    ArmorType.HEAVY: {
        "name_ru": "Тяжёлая броня",
        "name_en": "Heavy Armor",
        "proficiency": "heavy_armor",
        "max_dex_bonus": 0,
        "stealth_disadvantage": True,
    },
    ArmorType.SHIELD: {
        "name_ru": "Щит",
        "name_en": "Shield",
        "proficiency": "shields",
        "max_dex_bonus": None,
        "stealth_disadvantage": False,
    },
}


class Armor(Equipment):
    """
    Базовый класс для брони.

    Особенности брони D&D 5e:
    - BASE_AC: Базовый класс брони
    - ARMOR_TYPE: Тип брони (light/medium/heavy)
    - MAX_DEX_BONUS: Максимальный бонус ловкости (None = без ограничений)
    - STEALTH_DISADVANTAGE: Помеха к скрытности

    Формула AC:
    - Лёгкая: BASE_AC + DEX modifier
    - Средняя: BASE_AC + DEX modifier (max +2)
    - Тяжёлая: BASE_AC (без DEX)
    - Щит: +2 к AC (добавляется к броне)

    Пример:
    ```python
    class ChainMail(Armor):
        CLASS_ID = "chainmail"
        NAME = "Кольчуга"
        ARMOR_TYPE = ArmorType.HEAVY
        BASE_AC = 16
        STEALTH_DISADVANTAGE = True
        REQUIREMENTS = EquipmentRequirements(min_strength=13)
    ```
    """

    CLASS_ID = "base_armor"
    NAME = "Armor"
    EQUIPMENT_TYPE = "armor"
    EQUIPMENT_SLOT = EquipmentSlot.CHEST

    # Тип брони
    ARMOR_TYPE: ArmorType = ArmorType.LIGHT

    # Базовый AC (без модификатора DEX)
    BASE_AC: int = 10

    # Максимальный бонус DEX (None = без ограничений, 0 = нет бонуса)
    MAX_DEX_BONUS: Optional[int] = None

    # Помеха к скрытности
    STEALTH_DISADVANTAGE: bool = False

    # Время надевания/снятия (в минутах, для RP)
    DON_TIME: int = 1   # 1 минута для лёгкой брони
    DOFF_TIME: int = 1

    def __init__(self, unique_id: Optional[str] = None):
        super().__init__(unique_id)

        # Устанавливаем слот для щита
        if self.ARMOR_TYPE == ArmorType.SHIELD:
            self.EQUIPMENT_SLOT = EquipmentSlot.OFF_HAND

    def get_armor_class(self, dex_modifier: int = 0) -> int:
        """
        Рассчитывает итоговый AC с учётом модификатора ловкости.

        Args:
            dex_modifier: Модификатор ловкости персонажа

        Returns:
            Итоговый AC
        """
        if self.ARMOR_TYPE == ArmorType.SHIELD:
            # Щит просто добавляет +2 к AC
            return self.BASE_AC

        if self.ARMOR_TYPE == ArmorType.HEAVY:
            # Тяжёлая броня не использует DEX
            return self.BASE_AC

        # Применяем ограничение MAX_DEX_BONUS
        effective_dex = dex_modifier
        if self.MAX_DEX_BONUS is not None:
            effective_dex = min(dex_modifier, self.MAX_DEX_BONUS)

        return self.BASE_AC + effective_dex

    def on_equip(self, player_uuid: str, slot: str) -> bool:
        """Экипировка брони."""
        # Проверяем правильный слот
        expected_slot = self.EQUIPMENT_SLOT.value if self.EQUIPMENT_SLOT else "chest"
        if slot != expected_slot:
            return False

        # Базовая логика экипировки
        if not super().on_equip(player_uuid, slot):
            return False

        # Отправляем событие об изменении AC
        # AC будет пересчитан на сервере с учётом DEX
        self.post_event("armor_equipped", {
            "uuid": player_uuid,
            "armor_id": self.CLASS_ID,
            "base_ac": self.BASE_AC,
            "armor_type": self.ARMOR_TYPE.value,
            "max_dex_bonus": self.MAX_DEX_BONUS,
            "stealth_disadvantage": self.STEALTH_DISADVANTAGE,
        })

        return True

    def on_unequip(self, player_uuid: str) -> bool:
        """Снятие брони."""
        if not super().on_unequip(player_uuid):
            return False

        # Отправляем событие о снятии брони
        self.post_event("armor_unequipped", {
            "uuid": player_uuid,
            "armor_id": self.CLASS_ID,
            "slot": self.EQUIPMENT_SLOT.value if self.EQUIPMENT_SLOT else "chest",
        })

        return True

    def get_tooltip(self) -> str:
        """Tooltip для брони."""
        lines = [self.NAME]

        if self.DESCRIPTION:
            lines.append(self.DESCRIPTION)

        lines.append("")

        # Тип брони
        type_info = ARMOR_TYPE_INFO.get(self.ARMOR_TYPE, {})
        type_name = type_info.get("name_ru", self.ARMOR_TYPE.value)
        lines.append(f"Тип: {type_name}")

        # AC
        if self.ARMOR_TYPE == ArmorType.SHIELD:
            lines.append(f"AC: +{self.BASE_AC}")
        elif self.ARMOR_TYPE == ArmorType.HEAVY:
            lines.append(f"AC: {self.BASE_AC}")
        elif self.MAX_DEX_BONUS is not None:
            lines.append(f"AC: {self.BASE_AC} + DEX (макс. +{self.MAX_DEX_BONUS})")
        else:
            lines.append(f"AC: {self.BASE_AC} + DEX")

        # Помеха к скрытности
        if self.STEALTH_DISADVANTAGE:
            lines.append("Помеха к Скрытности")

        # Требования
        req = self.REQUIREMENTS
        if req.min_strength > 0:
            lines.append(f"Требуется Сила: {req.min_strength}")

        # Требуемое владение
        proficiency = type_info.get("proficiency")
        if proficiency:
            prof_names = {
                "light_armor": "лёгкая броня",
                "medium_armor": "средняя броня",
                "heavy_armor": "тяжёлая броня",
                "shields": "щиты",
            }
            lines.append(f"Владение: {prof_names.get(proficiency, proficiency)}")

        # Время надевания (для RP)
        if self.DON_TIME > 1:
            lines.append(f"Надевание: {self.DON_TIME} мин.")

        # Прочность
        if self.DURABILITY_MAX > 0:
            lines.append(f"Прочность: {self.durability}/{self.DURABILITY_MAX}")

        # Вес
        if self.WEIGHT > 0:
            lines.append(f"Вес: {self.WEIGHT} фунтов")

        return "\n".join(lines)

    @classmethod
    def get_info(cls) -> dict:
        """Информация о классе брони."""
        info = super().get_info()
        info.update({
            "armor_type": cls.ARMOR_TYPE.value,
            "base_ac": cls.BASE_AC,
            "max_dex_bonus": cls.MAX_DEX_BONUS,
            "stealth_disadvantage": cls.STEALTH_DISADVANTAGE,
            "don_time": cls.DON_TIME,
            "doff_time": cls.DOFF_TIME,
        })
        return info


# =============================================================================
# Предустановленные типы брони D&D 5e
# =============================================================================

class LightArmor(Armor):
    """Базовый класс для лёгкой брони."""
    ARMOR_TYPE = ArmorType.LIGHT
    MAX_DEX_BONUS = None
    DON_TIME = 1
    DOFF_TIME = 1


class MediumArmor(Armor):
    """Базовый класс для средней брони."""
    ARMOR_TYPE = ArmorType.MEDIUM
    MAX_DEX_BONUS = 2
    DON_TIME = 5
    DOFF_TIME = 1


class HeavyArmor(Armor):
    """Базовый класс для тяжёлой брони."""
    ARMOR_TYPE = ArmorType.HEAVY
    MAX_DEX_BONUS = 0
    STEALTH_DISADVANTAGE = True
    DON_TIME = 10
    DOFF_TIME = 5


class Shield(Armor):
    """Базовый класс для щитов."""
    ARMOR_TYPE = ArmorType.SHIELD
    EQUIPMENT_SLOT = EquipmentSlot.OFF_HAND
    EQUIPMENT_TYPE = "shield"
    BASE_AC = 2
    DON_TIME = 1
    DOFF_TIME = 1
