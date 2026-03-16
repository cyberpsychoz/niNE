"""
Lighting Plugin
Применяет настройки освещения, полученные от сервера.
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.lighting",
    name="Dynamic Lighting",
    description="Система динамического освещения",
    author="niNE Team",
    version="1.0.0",
    dependencies=["nine.world_config"],
    load_order=20,
    enabled=True,
)


def on_plugin_load(context):
    context.logger.info("Lighting плагин инициализирован")


def on_plugin_unload(context):
    context.logger.info("Lighting плагин остановлен")
