"""
Entity definitions for inventory plugin.
Each entity is defined in its own file and auto-loaded.
"""

import importlib.util
from pathlib import Path
from typing import Dict, Type

from nine.core.entity import Entity, ENTITY_REGISTRY


def load_entities():
    """
    Автоматически загружает все entity из этой папки.
    Каждый .py файл (кроме __init__.py и base.py) считается entity.
    """
    entities_dir = Path(__file__).parent
    loaded = []

    for file_path in entities_dir.glob("*.py"):
        if file_path.name.startswith("_") or file_path.name == "base.py":
            continue

        module_name = file_path.stem

        try:
            spec = importlib.util.spec_from_file_location(
                f"inventory_entity_{module_name}",
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
                    attr.CLASS_ID != "base_entity" and
                    attr.CLASS_ID != "base_item"
                ):
                    if not ENTITY_REGISTRY.is_registered(attr.CLASS_ID):
                        ENTITY_REGISTRY.register(attr)
                        loaded.append(attr.CLASS_ID)

        except Exception as e:
            print(f"[Inventory] Failed to load entity {file_path.name}: {e}")

    return loaded
