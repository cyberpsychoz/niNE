"""
Skybox Plugin
Создаёт скайбокс на основе конфигурации от сервера.
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.skybox",
    name="Skybox System",
    description="Система скайбокса",
    author="niNE Team",
    version="1.0.0",
    dependencies=["nine.world_config"],
    load_order=20,
    enabled=True,
)


def on_plugin_load(context):
    context.logger.info("Skybox плагин инициализирован")


def on_plugin_unload(context):
    context.logger.info("Skybox плагин остановлен")
