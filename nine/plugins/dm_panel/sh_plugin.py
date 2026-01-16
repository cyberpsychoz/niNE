"""
DM Panel Plugin - Панель управления для Игрового Мастера.

Предоставляет GUI интерфейс (F2) для:
- Управления игроками (телепорт, хил, урон)
- Управления боем (начать/завершить, инициатива)
- Спавна NPC
- Управления аудио (музыка, эмбиент)
- Мировых событий
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.dm_panel",
    name="DM Panel",
    description="Панель управления для Игрового Мастера",
    author="niNE Team",
    version="0.1.0",
    dependencies=["nine.combat", "nine.npc"],
    load_order=60,  # После combat и npc
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("DM Panel загружена")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("DM Panel выгружена")
