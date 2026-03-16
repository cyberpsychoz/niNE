"""
Класс оружия для D&D 5e.

Поддерживает все свойства оружия из PHB:
- Finesse (Фехтовальное): можно использовать DEX вместо STR
- Light (Лёгкое): можно использовать для двойного оружия
- Heavy (Тяжёлое): помеха для маленьких существ
- Two-Handed (Двуручное): требует две руки
- Versatile (Универсальное): разный урон одной/двумя руками
- Reach (Досягаемость): атака на 10 футов
- Thrown (Метательное): можно бросать
- Loading (Перезарядка): одна атака за ход
- Ammunition (Боеприпасы): требует стрелы/болты
- Special (Особое): уникальные правила
"""

from enum import Enum
from typing import Optional, Tuple, List
from dataclasses import dataclass

from .base_equipment import Equipment, StatBonus, EquipmentRequirements
from .sh_equipment_slots import EquipmentSlot


class WeaponType(Enum):
    """Типы оружия D&D 5e."""
    SIMPLE_MELEE = "simple_melee"       # Простое рукопашное
    SIMPLE_RANGED = "simple_ranged"     # Простое дальнобойное
    MARTIAL_MELEE = "martial_melee"     # Воинское рукопашное
    MARTIAL_RANGED = "martial_ranged"   # Воинское дальнобойное


class DamageType(Enum):
    """Типы урона D&D 5e."""
    SLASHING = "slashing"       # Рубящий
    PIERCING = "piercing"       # Колющий
    BLUDGEONING = "bludgeoning" # Дробящий

    # Магические типы (для магического оружия)
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    THUNDER = "thunder"
    POISON = "poison"
    ACID = "acid"
    NECROTIC = "necrotic"
    RADIANT = "radiant"
    FORCE = "force"
    PSYCHIC = "psychic"


# Локализация типов урона
DAMAGE_TYPE_NAMES = {
    DamageType.SLASHING: "рубящий",
    DamageType.PIERCING: "колющий",
    DamageType.BLUDGEONING: "дробящий",
    DamageType.FIRE: "огненный",
    DamageType.COLD: "холод",
    DamageType.LIGHTNING: "молния",
    DamageType.THUNDER: "громовой",
    DamageType.POISON: "яд",
    DamageType.ACID: "кислота",
    DamageType.NECROTIC: "некротический",
    DamageType.RADIANT: "излучение",
    DamageType.FORCE: "силовой",
    DamageType.PSYCHIC: "психический",
}


@dataclass
class WeaponRange:
    """Дальность оружия (для дальнобойного и метательного)."""
    normal: int = 0     # Нормальная дальность (футы)
    long: int = 0       # Максимальная дальность (с помехой)

    def __str__(self) -> str:
        if self.normal == 0:
            return "—"
        if self.long == 0:
            return f"{self.normal} фт."
        return f"{self.normal}/{self.long} фт."


class Weapon(Equipment):
    """
    Базовый класс для оружия.

    Свойства оружия D&D 5e:
    - DAMAGE_DICE: Кубы урона ("1d8", "2d6")
    - DAMAGE_TYPE: Тип урона (slashing, piercing, bludgeoning)
    - WEAPON_TYPE: Тип оружия (simple/martial, melee/ranged)

    Свойства (properties):
    - FINESSE: Можно использовать DEX вместо STR
    - LIGHT: Лёгкое (для боя двумя оружиями)
    - HEAVY: Тяжёлое (помеха для Small существ)
    - TWO_HANDED: Двуручное
    - VERSATILE: Универсальное (другой урон двумя руками)
    - REACH: Досягаемость 10 футов
    - THROWN: Метательное
    - LOADING: Требует перезарядки
    - AMMUNITION: Требует боеприпасы
    - SPECIAL: Особые правила

    Пример:
    ```python
    class Longsword(Weapon):
        CLASS_ID = "longsword"
        NAME = "Длинный меч"
        DAMAGE_DICE = "1d8"
        DAMAGE_TYPE = DamageType.SLASHING
        WEAPON_TYPE = WeaponType.MARTIAL_MELEE
        VERSATILE = "1d10"
    ```
    """

    CLASS_ID = "base_weapon"
    NAME = "Weapon"
    EQUIPMENT_TYPE = "weapon"
    EQUIPMENT_SLOT = EquipmentSlot.MAIN_HAND

    # Урон
    DAMAGE_DICE: str = "1d4"            # Кубы урона
    DAMAGE_TYPE: DamageType = DamageType.BLUDGEONING
    BONUS_DAMAGE: int = 0               # Фиксированный бонус к урону

    # Тип оружия
    WEAPON_TYPE: WeaponType = WeaponType.SIMPLE_MELEE

    # Дальность (для ranged и thrown)
    RANGE: WeaponRange = WeaponRange()

    # Свойства оружия D&D
    FINESSE: bool = False       # Можно использовать DEX вместо STR
    LIGHT: bool = False         # Лёгкое (для двойного оружия)
    HEAVY: bool = False         # Тяжёлое (помеха для маленьких)
    TWO_HANDED: bool = False    # Двуручное
    VERSATILE: Optional[str] = None  # Урон при двуручном хвате ("1d10")
    REACH: bool = False         # Досягаемость 10 футов
    THROWN: bool = False        # Метательное
    LOADING: bool = False       # Требует перезарядки
    AMMUNITION: bool = False    # Требует боеприпасы
    SPECIAL: bool = False       # Особые правила

    # Дополнительный урон (для магического оружия)
    EXTRA_DAMAGE_DICE: Optional[str] = None      # "1d6"
    EXTRA_DAMAGE_TYPE: Optional[DamageType] = None  # DamageType.FIRE

    def __init__(self, unique_id: Optional[str] = None):
        super().__init__(unique_id)

    @property
    def is_melee(self) -> bool:
        """Рукопашное ли оружие."""
        return self.WEAPON_TYPE in (WeaponType.SIMPLE_MELEE, WeaponType.MARTIAL_MELEE)

    @property
    def is_ranged(self) -> bool:
        """Дальнобойное ли оружие."""
        return self.WEAPON_TYPE in (WeaponType.SIMPLE_RANGED, WeaponType.MARTIAL_RANGED)

    @property
    def is_martial(self) -> bool:
        """Воинское ли оружие."""
        return self.WEAPON_TYPE in (WeaponType.MARTIAL_MELEE, WeaponType.MARTIAL_RANGED)

    @property
    def required_proficiency(self) -> str:
        """Требуемое владение."""
        if self.WEAPON_TYPE == WeaponType.SIMPLE_MELEE:
            return "simple_weapons"
        elif self.WEAPON_TYPE == WeaponType.SIMPLE_RANGED:
            return "simple_weapons"
        elif self.WEAPON_TYPE == WeaponType.MARTIAL_MELEE:
            return "martial_weapons"
        elif self.WEAPON_TYPE == WeaponType.MARTIAL_RANGED:
            return "martial_weapons"
        return "simple_weapons"

    def get_attack_modifier(self, str_mod: int, dex_mod: int) -> int:
        """
        Определяет модификатор атаки.

        Args:
            str_mod: Модификатор силы
            dex_mod: Модификатор ловкости

        Returns:
            Лучший модификатор для этого оружия
        """
        if self.is_ranged:
            # Дальнобойное всегда использует DEX
            return dex_mod
        elif self.FINESSE:
            # Фехтовальное — лучший из STR/DEX
            return max(str_mod, dex_mod)
        elif self.THROWN:
            # Метательное — STR (или DEX если finesse)
            return str_mod
        else:
            # Обычное рукопашное — STR
            return str_mod

    def get_damage_string(self, two_handed: bool = False) -> str:
        """
        Получить строку урона.

        Args:
            two_handed: Используется двумя руками (для versatile)

        Returns:
            Строка вида "1d8 рубящий"
        """
        # Основной урон
        if two_handed and self.VERSATILE:
            dice = self.VERSATILE
        else:
            dice = self.DAMAGE_DICE

        damage_type_name = DAMAGE_TYPE_NAMES.get(self.DAMAGE_TYPE, self.DAMAGE_TYPE.value)

        result = f"{dice}"
        if self.BONUS_DAMAGE != 0:
            sign = "+" if self.BONUS_DAMAGE > 0 else ""
            result += f"{sign}{self.BONUS_DAMAGE}"

        result += f" {damage_type_name}"

        # Дополнительный урон (магическое оружие)
        if self.EXTRA_DAMAGE_DICE and self.EXTRA_DAMAGE_TYPE:
            extra_type_name = DAMAGE_TYPE_NAMES.get(self.EXTRA_DAMAGE_TYPE, "")
            result += f" + {self.EXTRA_DAMAGE_DICE} {extra_type_name}"

        return result

    def get_properties_list(self) -> List[str]:
        """Получить список свойств оружия на русском."""
        properties = []

        if self.FINESSE:
            properties.append("Фехтовальное")
        if self.LIGHT:
            properties.append("Лёгкое")
        if self.HEAVY:
            properties.append("Тяжёлое")
        if self.TWO_HANDED:
            properties.append("Двуручное")
        if self.VERSATILE:
            properties.append(f"Универсальное ({self.VERSATILE})")
        if self.REACH:
            properties.append("Досягаемость")
        if self.THROWN:
            properties.append(f"Метательное ({self.RANGE})")
        if self.LOADING:
            properties.append("Перезарядка")
        if self.AMMUNITION:
            properties.append("Боеприпасы")
        if self.SPECIAL:
            properties.append("Особое")

        return properties

    def on_equip(self, player_uuid: str, slot: str) -> bool:
        """Экипировка оружия."""
        # Проверяем слот
        if slot not in ("main_hand", "off_hand"):
            return False

        # Двуручное нельзя в off_hand
        if self.TWO_HANDED and slot == "off_hand":
            return False

        if not super().on_equip(player_uuid, slot):
            return False

        # Отправляем событие о смене оружия
        self.post_event("weapon_equipped", {
            "uuid": player_uuid,
            "weapon_id": self.CLASS_ID,
            "slot": slot,
            "damage_dice": self.DAMAGE_DICE,
            "damage_type": self.DAMAGE_TYPE.value,
            "properties": self.get_properties_list(),
        })

        return True

    def on_unequip(self, player_uuid: str) -> bool:
        """Снятие оружия."""
        if not super().on_unequip(player_uuid):
            return False

        self.post_event("weapon_unequipped", {
            "uuid": player_uuid,
            "weapon_id": self.CLASS_ID,
        })

        return True

    def on_attack(self, attacker_uuid: str, target_uuid: str, two_handed: bool = False) -> dict:
        """
        Вызывается при атаке этим оружием.

        Args:
            attacker_uuid: UUID атакующего
            target_uuid: UUID цели
            two_handed: Атака двумя руками (для versatile)

        Returns:
            Словарь с данными атаки для системы боя
        """
        # Уменьшаем прочность
        self.damage_durability(1)

        return {
            "weapon_id": self.CLASS_ID,
            "damage_dice": self.VERSATILE if (two_handed and self.VERSATILE) else self.DAMAGE_DICE,
            "damage_type": self.DAMAGE_TYPE.value,
            "bonus_damage": self.BONUS_DAMAGE,
            "extra_damage_dice": self.EXTRA_DAMAGE_DICE,
            "extra_damage_type": self.EXTRA_DAMAGE_TYPE.value if self.EXTRA_DAMAGE_TYPE else None,
            "is_magical": self.MAGICAL,
        }

    def get_tooltip(self) -> str:
        """Tooltip для оружия."""
        lines = [self.NAME]

        if self.DESCRIPTION:
            lines.append(self.DESCRIPTION)

        lines.append("")

        # Тип оружия
        type_names = {
            WeaponType.SIMPLE_MELEE: "Простое рукопашное",
            WeaponType.SIMPLE_RANGED: "Простое дальнобойное",
            WeaponType.MARTIAL_MELEE: "Воинское рукопашное",
            WeaponType.MARTIAL_RANGED: "Воинское дальнобойное",
        }
        lines.append(type_names.get(self.WEAPON_TYPE, "Оружие"))

        # Урон
        lines.append(f"Урон: {self.get_damage_string()}")
        if self.VERSATILE:
            lines.append(f"Двумя руками: {self.get_damage_string(two_handed=True)}")

        # Дальность
        if self.is_ranged or self.THROWN:
            lines.append(f"Дальность: {self.RANGE}")

        # Свойства
        properties = self.get_properties_list()
        if properties:
            lines.append("")
            lines.append("Свойства:")
            for prop in properties:
                lines.append(f"  • {prop}")

        # Прочность
        if self.DURABILITY_MAX > 0:
            lines.append("")
            lines.append(f"Прочность: {self.durability}/{self.DURABILITY_MAX}")

        # Вес
        if self.WEIGHT > 0:
            lines.append(f"Вес: {self.WEIGHT} фунтов")

        # Магические свойства
        if self.MAGICAL:
            lines.append("")
            lines.append("[Магическое]")

        return "\n".join(lines)

    @classmethod
    def get_info(cls) -> dict:
        """Информация о классе оружия."""
        info = super().get_info()
        info.update({
            "weapon_type": cls.WEAPON_TYPE.value,
            "damage_dice": cls.DAMAGE_DICE,
            "damage_type": cls.DAMAGE_TYPE.value,
            "bonus_damage": cls.BONUS_DAMAGE,
            "range_normal": cls.RANGE.normal,
            "range_long": cls.RANGE.long,
            "finesse": cls.FINESSE,
            "light": cls.LIGHT,
            "heavy": cls.HEAVY,
            "two_handed": cls.TWO_HANDED,
            "versatile": cls.VERSATILE,
            "reach": cls.REACH,
            "thrown": cls.THROWN,
            "loading": cls.LOADING,
            "ammunition": cls.AMMUNITION,
        })
        return info


# =============================================================================
# Предустановленные базовые типы оружия
# =============================================================================

class SimpleMeleeWeapon(Weapon):
    """Базовый класс для простого рукопашного оружия."""
    WEAPON_TYPE = WeaponType.SIMPLE_MELEE


class SimpleRangedWeapon(Weapon):
    """Базовый класс для простого дальнобойного оружия."""
    WEAPON_TYPE = WeaponType.SIMPLE_RANGED
    AMMUNITION = True


class MartialMeleeWeapon(Weapon):
    """Базовый класс для воинского рукопашного оружия."""
    WEAPON_TYPE = WeaponType.MARTIAL_MELEE


class MartialRangedWeapon(Weapon):
    """Базовый класс для воинского дальнобойного оружия."""
    WEAPON_TYPE = WeaponType.MARTIAL_RANGED
    AMMUNITION = True
