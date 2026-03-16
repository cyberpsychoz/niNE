"""
World Configuration Plugin
Загружает конфигурацию мира из server_config.json и отправляет клиентам при подключении.
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.world_config",
    name="World Configuration",
    description="Серверная конфигурация мира (карта, освещение, скайбокс)",
    author="niNE Team",
    version="1.0.0",
    dependencies=[],
    load_order=10,
    enabled=True,
)


def on_plugin_load(context):
    context.logger.info("World Config плагин инициализирован")


def on_plugin_unload(context):
    context.logger.info("World Config плагин остановлен")
