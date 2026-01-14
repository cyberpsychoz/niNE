"""
Стандартная броня D&D 5e из Player's Handbook.
"""

from nine.plugins.inventory.entities.equipment.armor import LightArmor, MediumArmor, HeavyArmor, Shield, ArmorType
from nine.plugins.inventory.entities.equipment.base_equipment import EquipmentRequirements


# =============================================================================
# Лёгкая броня (Light Armor)
# =============================================================================

class PaddedArmor(LightArmor):
    """Стёганая броня — AC 11 + DEX, помеха к скрытности."""
    CLASS_ID = "padded_armor"
    NAME = "Стёганая броня"
    NAME_EN = "Padded Armor"
    DESCRIPTION = "Несколько слоёв стёганой ткани и ваты."
    BASE_AC = 11
    STEALTH_DISADVANTAGE = True
    WEIGHT = 8.0
    VALUE = 500  # 5 gp


class LeatherArmor(LightArmor):
    """Кожаная броня — AC 11 + DEX."""
    CLASS_ID = "leather_armor"
    NAME = "Кожаная броня"
    NAME_EN = "Leather Armor"
    DESCRIPTION = "Нагрудник и наплечники из выделанной кожи."
    BASE_AC = 11
    WEIGHT = 10.0
    VALUE = 1000  # 10 gp


class StuddedLeatherArmor(LightArmor):
    """Проклёпанная кожаная броня — AC 12 + DEX."""
    CLASS_ID = "studded_leather"
    NAME = "Проклёпанная кожаная броня"
    NAME_EN = "Studded Leather"
    DESCRIPTION = "Жёсткая кожа, усиленная стальными заклёпками."
    BASE_AC = 12
    WEIGHT = 13.0
    VALUE = 4500  # 45 gp


# =============================================================================
# Средняя броня (Medium Armor)
# =============================================================================

class HideArmor(MediumArmor):
    """Шкурная броня — AC 12 + DEX (макс. +2)."""
    CLASS_ID = "hide_armor"
    NAME = "Шкурная броня"
    NAME_EN = "Hide Armor"
    DESCRIPTION = "Грубая броня из толстых звериных шкур."
    BASE_AC = 12
    WEIGHT = 12.0
    VALUE = 1000  # 10 gp


class ChainShirt(MediumArmor):
    """Кольчужная рубаха — AC 13 + DEX (макс. +2)."""
    CLASS_ID = "chain_shirt"
    NAME = "Кольчужная рубаха"
    NAME_EN = "Chain Shirt"
    DESCRIPTION = "Кольчуга, которую можно носить под одеждой."
    BASE_AC = 13
    WEIGHT = 20.0
    VALUE = 5000  # 50 gp


class ScaleMail(MediumArmor):
    """Чешуйчатый доспех — AC 14 + DEX (макс. +2), помеха к скрытности."""
    CLASS_ID = "scale_mail"
    NAME = "Чешуйчатый доспех"
    NAME_EN = "Scale Mail"
    DESCRIPTION = "Кожаная куртка с нашитыми металлическими пластинами."
    BASE_AC = 14
    STEALTH_DISADVANTAGE = True
    WEIGHT = 45.0
    VALUE = 5000  # 50 gp


class Breastplate(MediumArmor):
    """Кираса — AC 14 + DEX (макс. +2)."""
    CLASS_ID = "breastplate"
    NAME = "Кираса"
    NAME_EN = "Breastplate"
    DESCRIPTION = "Металлический нагрудник с кожаными ремнями."
    BASE_AC = 14
    WEIGHT = 20.0
    VALUE = 40000  # 400 gp


class HalfPlate(MediumArmor):
    """Полулаты — AC 15 + DEX (макс. +2), помеха к скрытности."""
    CLASS_ID = "half_plate"
    NAME = "Полулаты"
    NAME_EN = "Half Plate"
    DESCRIPTION = "Пластинчатый доспех, не защищающий ноги полностью."
    BASE_AC = 15
    STEALTH_DISADVANTAGE = True
    WEIGHT = 40.0
    VALUE = 75000  # 750 gp


# =============================================================================
# Тяжёлая броня (Heavy Armor)
# =============================================================================

class RingMail(HeavyArmor):
    """Кольчатый доспех — AC 14."""
    CLASS_ID = "ring_mail"
    NAME = "Кольчатый доспех"
    NAME_EN = "Ring Mail"
    DESCRIPTION = "Кожаная броня с пришитыми толстыми кольцами."
    BASE_AC = 14
    WEIGHT = 40.0
    VALUE = 3000  # 30 gp


class ChainMail(HeavyArmor):
    """Кольчуга — AC 16, требует Силу 13."""
    CLASS_ID = "chainmail"
    NAME = "Кольчуга"
    NAME_EN = "Chain Mail"
    DESCRIPTION = "Полная кольчуга с подкладкой и капюшоном."
    BASE_AC = 16
    REQUIREMENTS = EquipmentRequirements(min_strength=13)
    WEIGHT = 55.0
    VALUE = 7500  # 75 gp


class SplintArmor(HeavyArmor):
    """Наборный доспех — AC 17, требует Силу 15."""
    CLASS_ID = "splint_armor"
    NAME = "Наборный доспех"
    NAME_EN = "Splint Armor"
    DESCRIPTION = "Узкие вертикальные пластины, приклёпанные к коже."
    BASE_AC = 17
    REQUIREMENTS = EquipmentRequirements(min_strength=15)
    WEIGHT = 60.0
    VALUE = 20000  # 200 gp


class PlateArmor(HeavyArmor):
    """Латы — AC 18, требует Силу 15."""
    CLASS_ID = "plate_armor"
    NAME = "Латы"
    NAME_EN = "Plate Armor"
    DESCRIPTION = "Полный латный доспех, покрывающий всё тело."
    BASE_AC = 18
    REQUIREMENTS = EquipmentRequirements(min_strength=15)
    WEIGHT = 65.0
    VALUE = 150000  # 1500 gp


# =============================================================================
# Щиты
# =============================================================================

class WoodenShield(Shield):
    """Деревянный щит — +2 AC."""
    CLASS_ID = "wooden_shield"
    NAME = "Деревянный щит"
    NAME_EN = "Wooden Shield"
    DESCRIPTION = "Простой круглый щит из дерева."
    BASE_AC = 2
    WEIGHT = 6.0
    VALUE = 1000  # 10 gp


class SteelShield(Shield):
    """Стальной щит — +2 AC."""
    CLASS_ID = "steel_shield"
    NAME = "Стальной щит"
    NAME_EN = "Steel Shield"
    DESCRIPTION = "Прочный щит из закалённой стали."
    BASE_AC = 2
    WEIGHT = 6.0
    VALUE = 1000  # 10 gp


# Экспорт
__all__ = [
    # Лёгкая
    "PaddedArmor",
    "LeatherArmor",
    "StuddedLeatherArmor",
    # Средняя
    "HideArmor",
    "ChainShirt",
    "ScaleMail",
    "Breastplate",
    "HalfPlate",
    # Тяжёлая
    "RingMail",
    "ChainMail",
    "SplintArmor",
    "PlateArmor",
    # Щиты
    "WoodenShield",
    "SteelShield",
]
