"""
Conditions Plugin - Система состояний D&D 5e.

Реализует все стандартные состояния из D&D 5e:
- Blinded, Charmed, Deafened, Frightened
- Grappled, Incapacitated, Invisible
- Paralyzed, Petrified, Poisoned
- Prone, Restrained, Stunned, Unconscious
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.conditions",
    name="Conditions",
    description="Система состояний D&D 5e",
    author="niNE Team",
    version="0.1.0",
    dependencies=["nine.combat"],
    load_order=51,  # После combat (50)
    enabled=True,
)


def on_plugin_load(context):
    """Вызывается после загрузки всех модулей плагина."""
    context.logger.info("Conditions система загружена")


def on_plugin_unload(context):
    """Вызывается перед выгрузкой плагина."""
    context.logger.info("Conditions система выгружена")
