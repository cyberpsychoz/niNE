"""
Система экипировки D&D.

Базовые классы для экипируемых предметов:
- Equipment — базовый класс
- Armor — броня (лёгкая, средняя, тяжёлая)
- Weapon — оружие (ближний бой, дальний бой)
- Accessory — аксессуары (кольца, амулеты, плащи)

Также содержит готовые предметы из D&D 5e PHB.
"""

from .sh_equipment_slots import EquipmentSlot, get_slot_name, slot_accepts
from .base_equipment import Equipment, StatBonus, EquipmentRequirements
from .armor import Armor, ArmorType, LightArmor, MediumArmor, HeavyArmor, Shield
from .weapon import (
    Weapon, WeaponType, DamageType, WeaponRange,
    SimpleMeleeWeapon, SimpleRangedWeapon, MartialMeleeWeapon, MartialRangedWeapon
)
from .accessory import Accessory, AccessoryType, Ring, Amulet, Cloak, Belt

# Предметы из PHB
from .items import armors, weapons, accessories

__all__ = [
    # Слоты
    "EquipmentSlot",
    "get_slot_name",
    "slot_accepts",
    # Базовые классы
    "Equipment",
    "StatBonus",
    "EquipmentRequirements",
    # Броня
    "Armor",
    "ArmorType",
    "LightArmor",
    "MediumArmor",
    "HeavyArmor",
    "Shield",
    # Оружие
    "Weapon",
    "WeaponType",
    "DamageType",
    "WeaponRange",
    "SimpleMeleeWeapon",
    "SimpleRangedWeapon",
    "MartialMeleeWeapon",
    "MartialRangedWeapon",
    # Аксессуары
    "Accessory",
    "AccessoryType",
    "Ring",
    "Amulet",
    "Cloak",
    "Belt",
    # Предметы
    "armors",
    "weapons",
    "accessories",
]
