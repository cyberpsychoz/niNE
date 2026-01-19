"""
Spells Plugin - Система заклинаний D&D 5e.

Предоставляет:
- Базу заклинаний из SRD
- Слоты заклинаний по классам и уровням
- UI книги заклинаний (K)
- Механику каста с концентрацией
- Интеграцию с боевой системой
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.spells",
    name="Spells",
    description="Система заклинаний D&D 5e",
    author="niNE Team",
    version="0.1.0",
    dependencies=["nine.combat"],
    load_order=52,  # После combat (50) и conditions (51)
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("Spells система загружена")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("Spells система выгружена")
