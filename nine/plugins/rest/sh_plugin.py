"""
Rest Plugin - Система отдыха D&D 5e.

Реализует:
- Short Rest (1 час): тратим Hit Dice для лечения
- Long Rest (8 часов): полное восстановление HP и слотов
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.rest",
    name="Rest",
    description="Система отдыха D&D 5e",
    author="niNE Team",
    version="0.1.0",
    dependencies=["nine.spells"],
    load_order=55,  # После spells
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("Rest система загружена")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("Rest система выгружена")
