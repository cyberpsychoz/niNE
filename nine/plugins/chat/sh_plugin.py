"""
Плагин системы чата.
Обеспечивает коммуникацию между игроками.
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.chat",
    name="Chat System",
    description="Система чата для общения игроков",
    author="niNE Team",
    version="1.0.0",
    dependencies=[],
    load_order=40,  # Загружается раньше, т.к. другие плагины могут использовать
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("Система чата инициализирована")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("Система чата остановлена")
