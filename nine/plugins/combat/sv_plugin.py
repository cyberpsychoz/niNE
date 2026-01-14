"""
Серверный модуль боевой системы.

Этот файл автоматически загружается системой плагинов для серверной части.
Создаёт и управляет CombatManager и TurnManager.
"""

from nine.core.plugins import PluginModule, PluginContext
from nine.plugins.combat.sv_combat_manager import CombatManager
from nine.plugins.combat.sv_turn_manager import TurnManager


class CombatServerModule(PluginModule):
    """
    Серверный модуль боевой системы.

    Создаёт и управляет CombatManager и TurnManager.
    """

    def __init__(self, context: PluginContext):
        super().__init__(context)
        self.combat_manager = None
        self.turn_manager = None

    def on_load(self):
        """Загружает боевую систему."""
        # Создаём Combat Manager
        self.combat_manager = CombatManager(self.context)
        self.combat_manager.on_load()

        # Создаём Turn Manager
        self.turn_manager = TurnManager(self.context)
        self.turn_manager.on_load()

        # Регистрируем в app для доступа из других модулей
        self.app.combat_manager = self.combat_manager
        self.app.turn_manager = self.turn_manager

        self.logger.info("Combat Server Module loaded")

    def on_unload(self):
        """Выгружает боевую систему."""
        if self.turn_manager:
            self.turn_manager.on_unload()
            self.turn_manager = None

        if self.combat_manager:
            self.combat_manager.on_unload()
            self.combat_manager = None

        if hasattr(self.app, 'combat_manager'):
            delattr(self.app, 'combat_manager')
        if hasattr(self.app, 'turn_manager'):
            delattr(self.app, 'turn_manager')

        self.logger.info("Combat Server Module unloaded")

    # Делегирование методов для поиска через plugin.modules
    @property
    def active_combats(self):
        """Активные бои (для доступа из других модулей)."""
        return self.combat_manager.active_combats if self.combat_manager else {}

    def get_combat_for_entity(self, entity_id: str):
        """Получает бой, в котором участвует сущность."""
        if self.combat_manager:
            return self.combat_manager.get_combat_for_entity(entity_id)
        return None

    def is_entity_in_combat(self, entity_id: str) -> bool:
        """Проверяет, находится ли сущность в бою."""
        if self.combat_manager:
            return self.combat_manager.is_entity_in_combat(entity_id)
        return False
