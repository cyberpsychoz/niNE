"""
Плагин системы инвентаря.
Управляет предметами игроков.
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.inventory",
    name="Inventory System",
    description="Управление инвентарем игроков",
    author="niNE Team",
    version="1.0.0",
    dependencies=[],
    load_order=35,  # После health, перед chat
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("Система инвентаря инициализирована")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("Система инвентаря остановлена")
