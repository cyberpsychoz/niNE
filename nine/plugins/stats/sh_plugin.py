"""
Плагин системы характеристик игрока.
Управляет здоровьем, голодом и другими статами.
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.stats",
    name="Stats System",
    description="Управление характеристиками игроков (здоровье, голод)",
    author="niNE Team",
    version="1.0.0",
    dependencies=[],
    load_order=30,
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("Система характеристик инициализирована")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("Система характеристик остановлена")
