"""
Плагин системы здоровья.
Управляет здоровьем игроков.
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.health",
    name="Health System",
    description="Управление здоровьем игроков",
    author="niNE Team",
    version="1.0.0",
    dependencies=[],
    load_order=30,  # Загружается раньше чата
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("Система здоровья инициализирована")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("Система здоровья остановлена")
