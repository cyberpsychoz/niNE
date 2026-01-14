"""
Combat Plugin - D&D 5e Turn-Based Combat System.
Пошаговая боевая система в стиле Baldur's Gate 3.
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.combat",
    name="D&D Combat System",
    description="Пошаговая боевая система D&D 5e",
    author="niNE Team",
    version="0.1.0",
    dependencies=["nine.dnd"],
    load_order=50,  # После dnd плагина
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("D&D Combat System инициализирована")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("D&D Combat System остановлена")
