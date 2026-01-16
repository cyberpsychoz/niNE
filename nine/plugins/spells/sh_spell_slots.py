"""
Таблицы слотов заклинаний по классам и уровням D&D 5e.
"""

from typing import Dict, List, Optional

# Полные заклинатели (Wizard, Cleric, Druid, Bard, Sorcerer)
# Уровень персонажа -> слоты по уровням заклинаний [1, 2, 3, 4, 5, 6, 7, 8, 9]
FULL_CASTER_SLOTS: Dict[int, List[int]] = {
    1:  [2, 0, 0, 0, 0, 0, 0, 0, 0],
    2:  [3, 0, 0, 0, 0, 0, 0, 0, 0],
    3:  [4, 2, 0, 0, 0, 0, 0, 0, 0],
    4:  [4, 3, 0, 0, 0, 0, 0, 0, 0],
    5:  [4, 3, 2, 0, 0, 0, 0, 0, 0],
    6:  [4, 3, 3, 0, 0, 0, 0, 0, 0],
    7:  [4, 3, 3, 1, 0, 0, 0, 0, 0],
    8:  [4, 3, 3, 2, 0, 0, 0, 0, 0],
    9:  [4, 3, 3, 3, 1, 0, 0, 0, 0],
    10: [4, 3, 3, 3, 2, 0, 0, 0, 0],
    11: [4, 3, 3, 3, 2, 1, 0, 0, 0],
    12: [4, 3, 3, 3, 2, 1, 0, 0, 0],
    13: [4, 3, 3, 3, 2, 1, 1, 0, 0],
    14: [4, 3, 3, 3, 2, 1, 1, 0, 0],
    15: [4, 3, 3, 3, 2, 1, 1, 1, 0],
    16: [4, 3, 3, 3, 2, 1, 1, 1, 0],
    17: [4, 3, 3, 3, 2, 1, 1, 1, 1],
    18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
    19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
    20: [4, 3, 3, 3, 3, 2, 2, 1, 1],
}

# Полузаклинатели (Paladin, Ranger) - начинают со 2 уровня
HALF_CASTER_SLOTS: Dict[int, List[int]] = {
    1:  [0, 0, 0, 0, 0],
    2:  [2, 0, 0, 0, 0],
    3:  [3, 0, 0, 0, 0],
    4:  [3, 0, 0, 0, 0],
    5:  [4, 2, 0, 0, 0],
    6:  [4, 2, 0, 0, 0],
    7:  [4, 3, 0, 0, 0],
    8:  [4, 3, 0, 0, 0],
    9:  [4, 3, 2, 0, 0],
    10: [4, 3, 2, 0, 0],
    11: [4, 3, 3, 0, 0],
    12: [4, 3, 3, 0, 0],
    13: [4, 3, 3, 1, 0],
    14: [4, 3, 3, 1, 0],
    15: [4, 3, 3, 2, 0],
    16: [4, 3, 3, 2, 0],
    17: [4, 3, 3, 3, 1],
    18: [4, 3, 3, 3, 1],
    19: [4, 3, 3, 3, 2],
    20: [4, 3, 3, 3, 2],
}

# Третьзаклинатели (Eldritch Knight, Arcane Trickster) - начинают с 3 уровня
THIRD_CASTER_SLOTS: Dict[int, List[int]] = {
    1:  [0, 0, 0, 0],
    2:  [0, 0, 0, 0],
    3:  [2, 0, 0, 0],
    4:  [3, 0, 0, 0],
    5:  [3, 0, 0, 0],
    6:  [3, 0, 0, 0],
    7:  [4, 2, 0, 0],
    8:  [4, 2, 0, 0],
    9:  [4, 2, 0, 0],
    10: [4, 3, 0, 0],
    11: [4, 3, 0, 0],
    12: [4, 3, 0, 0],
    13: [4, 3, 2, 0],
    14: [4, 3, 2, 0],
    15: [4, 3, 2, 0],
    16: [4, 3, 3, 0],
    17: [4, 3, 3, 0],
    18: [4, 3, 3, 0],
    19: [4, 3, 3, 1],
    20: [4, 3, 3, 1],
}

# Warlock использует Pact Magic (меньше слотов, но восстанавливаются на short rest)
WARLOCK_SLOTS: Dict[int, Dict[str, int]] = {
    1:  {"slots": 1, "level": 1},
    2:  {"slots": 2, "level": 1},
    3:  {"slots": 2, "level": 2},
    4:  {"slots": 2, "level": 2},
    5:  {"slots": 2, "level": 3},
    6:  {"slots": 2, "level": 3},
    7:  {"slots": 2, "level": 4},
    8:  {"slots": 2, "level": 4},
    9:  {"slots": 2, "level": 5},
    10: {"slots": 2, "level": 5},
    11: {"slots": 3, "level": 5},
    12: {"slots": 3, "level": 5},
    13: {"slots": 3, "level": 5},
    14: {"slots": 3, "level": 5},
    15: {"slots": 3, "level": 5},
    16: {"slots": 3, "level": 5},
    17: {"slots": 4, "level": 5},
    18: {"slots": 4, "level": 5},
    19: {"slots": 4, "level": 5},
    20: {"slots": 4, "level": 5},
}

# Классы и их тип заклинательства
CLASS_CASTER_TYPE: Dict[str, str] = {
    "wizard": "full",
    "cleric": "full",
    "druid": "full",
    "bard": "full",
    "sorcerer": "full",
    "warlock": "warlock",
    "paladin": "half",
    "ranger": "half",
    "fighter": "third",  # Eldritch Knight (subclass, но для простоты)
    "rogue": "third",    # Arcane Trickster (subclass)
    "barbarian": "none",
    "monk": "none",
}

# Основная способность для заклинаний по классам
CLASS_SPELLCASTING_ABILITY: Dict[str, str] = {
    "wizard": "INT",
    "cleric": "WIS",
    "druid": "WIS",
    "bard": "CHA",
    "sorcerer": "CHA",
    "warlock": "CHA",
    "paladin": "CHA",
    "ranger": "WIS",
    "fighter": "INT",  # Eldritch Knight
    "rogue": "INT",    # Arcane Trickster
}

# Количество известных cantrip'ов по классам и уровням
CANTRIPS_KNOWN: Dict[str, Dict[int, int]] = {
    "wizard": {1: 3, 4: 4, 10: 5},
    "cleric": {1: 3, 4: 4, 10: 5},
    "druid": {1: 2, 4: 3, 10: 4},
    "bard": {1: 2, 4: 3, 10: 4},
    "sorcerer": {1: 4, 4: 5, 10: 6},
    "warlock": {1: 2, 4: 3, 10: 4},
}


def get_spell_slots_for_class(character_class: str, level: int) -> Dict[int, int]:
    """
    Возвращает словарь слотов заклинаний для класса и уровня.

    Args:
        character_class: Класс персонажа (lowercase)
        level: Уровень персонажа (1-20)

    Returns:
        Dict[spell_level, slot_count] - слоты по уровням заклинаний
    """
    level = max(1, min(20, level))
    caster_type = CLASS_CASTER_TYPE.get(character_class.lower(), "none")

    if caster_type == "none":
        return {}

    if caster_type == "warlock":
        warlock_data = WARLOCK_SLOTS.get(level, {"slots": 0, "level": 1})
        # Warlock имеет только слоты одного уровня
        slot_level = warlock_data["level"]
        slot_count = warlock_data["slots"]
        return {slot_level: slot_count}

    # Получаем таблицу слотов
    if caster_type == "full":
        slots_table = FULL_CASTER_SLOTS
        max_spell_level = 9
    elif caster_type == "half":
        slots_table = HALF_CASTER_SLOTS
        max_spell_level = 5
    else:  # third
        slots_table = THIRD_CASTER_SLOTS
        max_spell_level = 4

    slots_list = slots_table.get(level, [0] * max_spell_level)

    # Конвертируем список в словарь (только ненулевые)
    result = {}
    for spell_level, count in enumerate(slots_list, start=1):
        if count > 0:
            result[spell_level] = count

    return result


def get_spellcasting_ability(character_class: str) -> Optional[str]:
    """Возвращает основную способность для заклинаний класса."""
    return CLASS_SPELLCASTING_ABILITY.get(character_class.lower())


def get_cantrips_known(character_class: str, level: int) -> int:
    """Возвращает количество известных cantrip'ов."""
    cantrips = CANTRIPS_KNOWN.get(character_class.lower())
    if not cantrips:
        return 0

    result = 0
    for req_level, count in sorted(cantrips.items()):
        if level >= req_level:
            result = count
    return result


def calculate_spell_save_dc(ability_modifier: int, proficiency_bonus: int) -> int:
    """Вычисляет DC спасброска от заклинаний."""
    return 8 + ability_modifier + proficiency_bonus


def calculate_spell_attack_bonus(ability_modifier: int, proficiency_bonus: int) -> int:
    """Вычисляет бонус атаки заклинанием."""
    return ability_modifier + proficiency_bonus


def get_max_spell_level(character_class: str, level: int) -> int:
    """Возвращает максимальный доступный уровень заклинаний."""
    slots = get_spell_slots_for_class(character_class, level)
    if not slots:
        return 0
    return max(slots.keys())
