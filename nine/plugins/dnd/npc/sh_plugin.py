"""
Метаданные NPC плагина.

Определяет информацию о плагине для системы плагинов niNE.
"""

from nine.core.plugins import PluginInfo, PluginModule, PluginContext

# Метаданные плагина
PLUGIN_INFO = PluginInfo(
    unique_id="nine.dnd.npc",
    name="D&D NPC System",
    description="ECS-based NPC система с AI, pathfinding и диалогами",
    author="niNE Team",
    version="0.1.0",
    dependencies=[],  # Без зависимостей для упрощения
    load_order=40,  # Загружается после базовых систем
    enabled=True
)


class SharedNPCModule(PluginModule):
    """
    Общий модуль NPC (загружается на сервере и клиенте).

    Содержит общие константы и утилиты.
    """

    def __init__(self, context: PluginContext):
        super().__init__(context)

    def on_load(self):
        self.logger.info("Shared NPC Module loaded")

    def on_unload(self):
        self.logger.info("Shared NPC Module unloaded")
