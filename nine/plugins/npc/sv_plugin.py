"""
Серверный модуль NPC системы.

Этот файл автоматически загружается системой плагинов для серверной части.
Содержит NPCManager как основной класс модуля.
"""

from nine.core.plugins import PluginModule, PluginContext
from .sv_npc_manager import NPCManager


class NPCServerModule(PluginModule):
    """
    Серверный модуль NPC системы.

    Создаёт и управляет NPCManager.
    """

    def __init__(self, context: PluginContext):
        super().__init__(context)
        self.npc_manager = None

    def on_load(self):
        """Загружает NPC Manager."""
        # Создаём NPC Manager с тем же контекстом
        self.npc_manager = NPCManager(self.context)
        self.npc_manager.on_load()

        # Регистрируем в app для доступа из game_server
        self.app.npc_manager = self.npc_manager

        self.logger.info("NPC Server Module loaded")

    def on_unload(self):
        """Выгружает NPC Manager."""
        if self.npc_manager:
            self.npc_manager.on_unload()
            self.npc_manager = None

        if hasattr(self.app, 'npc_manager'):
            delattr(self.app, 'npc_manager')

        self.logger.info("NPC Server Module unloaded")
