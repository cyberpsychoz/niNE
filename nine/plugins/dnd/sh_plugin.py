"""
D&D Character System Plugin.
Основной файл плагина с метаданными.
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.dnd",
    name="D&D Character System",
    description="Система персонажей D&D 5e с выбором расы, класса, характеристик",
    author="niNE Team",
    version="1.0.0",
    dependencies=[],
    load_order=10,  # Загружается раньше других - базовая система
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("D&D Character System инициализирована")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("D&D Character System остановлена")
