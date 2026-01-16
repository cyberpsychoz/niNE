"""
Quests Plugin - Система квестов.

Предоставляет:
- Структуру квестов с целями
- Трекинг прогресса
- Журнал квестов (J)
- Награды за выполнение
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.quests",
    name="Quests",
    description="Система квестов D&D",
    author="niNE Team",
    version="0.1.0",
    dependencies=[],
    load_order=50,
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("Quests система загружена")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("Quests система выгружена")
