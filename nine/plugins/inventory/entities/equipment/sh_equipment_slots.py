"""
Определения слотов экипировки D&D.

Слоты соответствуют стандартной системе D&D 5e с небольшими расширениями.
"""

from enum import Enum
from typing import Dict, List, Set


class EquipmentSlot(Enum):
    """Слоты экипировки персонажа."""

    # Броня
    HEAD = "head"           # Шлем, шляпа, капюшон
    CHEST = "chest"         # Нагрудник, кираса, роба
    HANDS = "hands"         # Перчатки, рукавицы, наручи
    LEGS = "legs"           # Поножи, штаны
    FEET = "feet"           # Сапоги, ботинки

    # Оружие
    MAIN_HAND = "main_hand"  # Основная рука (оружие)
    OFF_HAND = "off_hand"    # Вторая рука (щит, второе оружие, факел)

    # Аксессуары
    RING_1 = "ring_1"        # Кольцо (левая рука)
    RING_2 = "ring_2"        # Кольцо (правая рука)
    AMULET = "amulet"        # Амулет, ожерелье
    CLOAK = "cloak"          # Плащ, накидка
    BELT = "belt"            # Пояс


# Информация о каждом слоте
SLOT_INFO: Dict[EquipmentSlot, dict] = {
    EquipmentSlot.HEAD: {
        "name_ru": "Голова",
        "name_en": "Head",
        "accepts": ["helmet", "hat", "hood", "circlet"],
        "icon": "slot_head",
    },
    EquipmentSlot.CHEST: {
        "name_ru": "Тело",
        "name_en": "Chest",
        "accepts": ["armor", "robe", "shirt", "vest"],
        "icon": "slot_chest",
    },
    EquipmentSlot.HANDS: {
        "name_ru": "Руки",
        "name_en": "Hands",
        "accepts": ["gloves", "gauntlets", "bracers"],
        "icon": "slot_hands",
    },
    EquipmentSlot.LEGS: {
        "name_ru": "Ноги",
        "name_en": "Legs",
        "accepts": ["greaves", "pants", "leggings"],
        "icon": "slot_legs",
    },
    EquipmentSlot.FEET: {
        "name_ru": "Ступни",
        "name_en": "Feet",
        "accepts": ["boots", "shoes", "sandals"],
        "icon": "slot_feet",
    },
    EquipmentSlot.MAIN_HAND: {
        "name_ru": "Основная рука",
        "name_en": "Main Hand",
        "accepts": ["weapon", "staff", "wand"],
        "icon": "slot_main_hand",
    },
    EquipmentSlot.OFF_HAND: {
        "name_ru": "Вторая рука",
        "name_en": "Off Hand",
        "accepts": ["shield", "weapon", "torch", "orb"],
        "icon": "slot_off_hand",
    },
    EquipmentSlot.RING_1: {
        "name_ru": "Кольцо (Л)",
        "name_en": "Ring (L)",
        "accepts": ["ring"],
        "icon": "slot_ring",
    },
    EquipmentSlot.RING_2: {
        "name_ru": "Кольцо (П)",
        "name_en": "Ring (R)",
        "accepts": ["ring"],
        "icon": "slot_ring",
    },
    EquipmentSlot.AMULET: {
        "name_ru": "Амулет",
        "name_en": "Amulet",
        "accepts": ["amulet", "necklace", "pendant"],
        "icon": "slot_amulet",
    },
    EquipmentSlot.CLOAK: {
        "name_ru": "Плащ",
        "name_en": "Cloak",
        "accepts": ["cloak", "cape", "mantle"],
        "icon": "slot_cloak",
    },
    EquipmentSlot.BELT: {
        "name_ru": "Пояс",
        "name_en": "Belt",
        "accepts": ["belt", "sash"],
        "icon": "slot_belt",
    },
}


# Группы слотов
ARMOR_SLOTS: Set[EquipmentSlot] = {
    EquipmentSlot.HEAD,
    EquipmentSlot.CHEST,
    EquipmentSlot.HANDS,
    EquipmentSlot.LEGS,
    EquipmentSlot.FEET,
}

WEAPON_SLOTS: Set[EquipmentSlot] = {
    EquipmentSlot.MAIN_HAND,
    EquipmentSlot.OFF_HAND,
}

ACCESSORY_SLOTS: Set[EquipmentSlot] = {
    EquipmentSlot.RING_1,
    EquipmentSlot.RING_2,
    EquipmentSlot.AMULET,
    EquipmentSlot.CLOAK,
    EquipmentSlot.BELT,
}

ALL_SLOTS: List[EquipmentSlot] = list(EquipmentSlot)


def get_slot_name(slot: EquipmentSlot, lang: str = "ru") -> str:
    """Получить локализованное название слота."""
    info = SLOT_INFO.get(slot, {})
    if lang == "ru":
        return info.get("name_ru", slot.value)
    return info.get("name_en", slot.value)


def slot_accepts(slot: EquipmentSlot, item_type: str) -> bool:
    """Проверить, принимает ли слот данный тип предмета."""
    info = SLOT_INFO.get(slot, {})
    accepts = info.get("accepts", [])
    return item_type.lower() in accepts


def get_slots_for_type(item_type: str) -> List[EquipmentSlot]:
    """Получить список слотов, которые принимают данный тип предмета."""
    result = []
    for slot, info in SLOT_INFO.items():
        if item_type.lower() in info.get("accepts", []):
            result.append(slot)
    return result
