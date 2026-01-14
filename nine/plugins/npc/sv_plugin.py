"""
Серверный модуль NPC системы.

Этот файл автоматически загружается системой плагинов для серверной части.
Содержит NPCManager как основной класс модуля.
"""

from nine.core.plugins import PluginModule, PluginContext
from nine.plugins.npc.sv_npc_manager import NPCManager


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

    # Делегирование методов для поиска через plugin.modules
    def get_npc_entity(self, entity_id: str):
        """Получает NPC entity по ID."""
        if self.npc_manager:
            return self.npc_manager.get_npc_entity(entity_id)
        return None

    def get_npcs_in_radius(self, pos, radius: float):
        """Возвращает NPC в радиусе от позиции."""
        if self.npc_manager:
            entities = self.npc_manager.get_npcs_in_radius(pos[0], pos[1], radius)
            result = {}
            for entity in entities:
                from nine.plugins.npc.sh_components import (
                    FactionComponent, NPCInfoComponent, AIComponent, AIBehavior
                )
                faction = entity.get_component(FactionComponent)
                info = entity.get_component(NPCInfoComponent)
                ai = entity.get_component(AIComponent)

                is_hostile = False
                if faction and faction.hostile_to_players:
                    is_hostile = True
                if ai and ai.behavior == AIBehavior.HOSTILE:
                    is_hostile = True

                result[entity.id] = {
                    "name": info.display_name if info else "NPC",
                    "is_hostile": is_hostile,
                }
            return result
        return {}

    def spawn_npc(self, template_id: str, x: float, y: float, z: float, **kwargs):
        """Спавнит NPC по шаблону."""
        if self.npc_manager:
            return self.npc_manager.spawn_npc(template_id, x, y, z, **kwargs)
        return None

    def despawn_npc(self, entity_id: str) -> bool:
        """Удаляет NPC."""
        if self.npc_manager:
            return self.npc_manager.despawn_npc(entity_id)
        return False
