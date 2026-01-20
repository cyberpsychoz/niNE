"""
DnD Audio Plugin - метаданные плагина звуковой системы.

Предоставляет:
- BGM (фоновая музыка) с плейлистами
- BGS (эмбиент окружения)
- SFX (звуковые эффекты)
- Система шагов с учётом поверхности
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.dnd.audio",
    name="DnD Audio",
    description="Звуковая система для D&D режима: BGM, эмбиент, SFX, шаги",
    author="niNE Team",
    version="1.0.0",
    dependencies=["nine.dnd"],
    load_order=15,  # После dnd (10), перед другими плагинами
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("DnD Audio система загружена")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("DnD Audio система выгружена")
