"""
Entity definitions for inventory plugin.
Each entity is defined in its own file and auto-loaded.
"""

import importlib.util
from pathlib import Path
from typing import List

from nine.core.entity import Entity, ENTITY_REGISTRY


# Базовые классы, которые не нужно регистрировать как предметы
EXCLUDED_CLASS_IDS = {
    "base_entity",
    "base_item",
    "base_equipment",
    "base_armor",
    "base_weapon",
    "base_accessory",
}


def _load_module(file_path: Path, prefix: str = "inventory_entity") -> List[str]:
    """Загружает модуль и регистрирует Entity классы."""
    loaded = []
    module_name = file_path.stem

    try:
        spec = importlib.util.spec_from_file_location(
            f"{prefix}_{module_name}",
            file_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Найти и зарегистрировать все Entity классы в модуле
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type) and
                issubclass(attr, Entity) and
                attr is not Entity and
                hasattr(attr, 'CLASS_ID') and
                attr.CLASS_ID not in EXCLUDED_CLASS_IDS
            ):
                if not ENTITY_REGISTRY.is_registered(attr.CLASS_ID):
                    ENTITY_REGISTRY.register(attr)
                    loaded.append(attr.CLASS_ID)

    except Exception as e:
        print(f"[Inventory] Failed to load entity {file_path.name}: {e}")

    return loaded


def load_entities() -> List[str]:
    """
    Автоматически загружает все entity из этой папки и подпапок.

    Загружает:
    - entities/*.py — базовые предметы
    - entities/equipment/items/*.py — экипировка D&D
    """
    entities_dir = Path(__file__).parent
    loaded = []

    # Загружаем базовые предметы из корневой папки
    for file_path in entities_dir.glob("*.py"):
        if file_path.name.startswith("_") or file_path.name == "base.py":
            continue
        loaded.extend(_load_module(file_path, "inventory_entity"))

    # Загружаем экипировку из equipment/items
    equipment_items_dir = entities_dir / "equipment" / "items"
    if equipment_items_dir.exists():
        for file_path in equipment_items_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
            loaded.extend(_load_module(file_path, "inventory_equipment"))

    return loaded
