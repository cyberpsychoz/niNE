"""
NPC Plugin - D&D NPC System.
ECS-based NPC система с AI, pathfinding и диалогами.
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.npc",
    name="D&D NPC System",
    description="ECS-based NPC система с AI и pathfinding",
    author="niNE Team",
    version="0.1.0",
    dependencies=[],
    load_order=40,  # После базовых систем, перед combat
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("D&D NPC System инициализирована")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("D&D NPC System остановлена")
