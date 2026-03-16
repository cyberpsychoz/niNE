"""
Living NPC Plugin - Живой мир NPC.

Добавляет:
- Потребности (голод, усталость, социальность)
- Личностные черты
- Отношения между сущностями
- Память о событиях
- Расписания дня
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.living_npc",
    name="Living NPC",
    description="Живой мир NPC с потребностями и отношениями",
    author="niNE Team",
    version="0.1.0",
    dependencies=["nine.npc"],
    load_order=70,  # После всех основных систем
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("Living NPC система загружена")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("Living NPC система выгружена")
