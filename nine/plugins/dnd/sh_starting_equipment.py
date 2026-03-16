"""
Mapping from starting_equipment strings in sh_constants.py
to (class_id, count) tuples for the inventory entity system.

Most items need no alias — their starting_equipment key matches
the CLASS_ID directly. This map handles the exceptions.
"""

# (class_id, count)
EQUIPMENT_ALIASES = {
    "chain_mail": ("chainmail", 1),
    "shield": ("steel_shield", 1),
    "shortswords": ("shortsword", 2),
    "handaxes": ("handaxe", 2),
    "darts": ("dart", 10),
    "staff": ("quarterstaff", 1),
    "small_knife": ("dagger", 1),
}


def resolve_equipment_key(key):
    """
    Resolve a starting_equipment key to (class_id, count).
    Returns the alias if one exists, otherwise (key, 1).
    """
    if key in EQUIPMENT_ALIASES:
        return EQUIPMENT_ALIASES[key]
    return (key, 1)
