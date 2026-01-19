"""
Серверный модуль DM Panel.

Обрабатывает запросы от клиентской панели DM:
- Проверка роли DM
- Список игроков и действия с ними
- Список боёв и управление
- Спавн/деспавн NPC
- Аудио команды
- Глобальные объявления
"""

from typing import Dict, List, Optional
import importlib.util
from pathlib import Path

from nine.core.plugins import PluginModule


class DMPanelServerModule(PluginModule):
    """
    Серверный модуль DM Panel.
    """

    def on_load(self):
        # Кеш данных
        self._players_cache: Dict[int, dict] = {}

        # Подписки на сетевые сообщения
        self.event_manager.subscribe("dm_role_check", self._on_role_check)
        self.event_manager.subscribe("dm_panel_player_list_request", self._on_player_list_request)
        self.event_manager.subscribe("dm_panel_combat_list_request", self._on_combat_list_request)
        self.event_manager.subscribe("dm_panel_npc_list_request", self._on_npc_list_request)
        self.event_manager.subscribe("dm_panel_npc_templates_request", self._on_npc_templates_request)
        self.event_manager.subscribe("dm_panel_player_action", self._on_player_action)
        self.event_manager.subscribe("dm_announcement", self._on_announcement)

        # Подписки на обновления для отправки в панель
        self.event_manager.subscribe("player_joined", self._update_players_cache)
        self.event_manager.subscribe("player_left", self._on_player_left)

        self.logger.info("DM Panel серверный модуль загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("dm_role_check", self._on_role_check)
        self.event_manager.unsubscribe("dm_panel_player_list_request", self._on_player_list_request)
        self.event_manager.unsubscribe("dm_panel_combat_list_request", self._on_combat_list_request)
        self.event_manager.unsubscribe("dm_panel_npc_list_request", self._on_npc_list_request)
        self.event_manager.unsubscribe("dm_panel_npc_templates_request", self._on_npc_templates_request)
        self.event_manager.unsubscribe("dm_panel_player_action", self._on_player_action)
        self.event_manager.unsubscribe("dm_announcement", self._on_announcement)
        self.event_manager.unsubscribe("player_joined", self._update_players_cache)
        self.event_manager.unsubscribe("player_left", self._on_player_left)
        self.logger.info("DM Panel серверный модуль выгружен")

    # =========================================================================
    # Role checking
    # =========================================================================

    def _get_player_role(self, client_id: int) -> str:
        """Получает роль игрока."""
        # Dev-клиенты автоматически получают роль admin для тестирования
        if hasattr(self.app, 'allow_dev_client') and self.app.allow_dev_client:
            # Проверяем, это dev-клиент (нет в authenticated_clients)
            if not hasattr(self.app, 'authenticated_clients'):
                return "admin"
            client_data = self.app.authenticated_clients.get(client_id)
            if not client_data:
                return "admin"

        # Получаем account_uuid из authenticated_clients (D&D плагин)
        if not hasattr(self.app, 'authenticated_clients'):
            return "player"

        client_data = self.app.authenticated_clients.get(client_id)
        if not client_data:
            return "player"

        account_uuid = client_data.get("account_uuid")
        if not account_uuid:
            return "player"

        # Запрашиваем роль из базы данных
        if hasattr(self.app, 'db'):
            return self.app.db.get_player_role(account_uuid)

        return "player"

    def _is_dm(self, client_id: int) -> bool:
        """Проверяет, является ли клиент DM или Admin."""
        role = self._get_player_role(client_id)
        return role in ("dm", "admin")

    def _on_role_check(self, data: dict):
        """Проверка роли DM."""
        client_id = data.get("client_id", -1)
        is_dm = self._is_dm(client_id)

        self._send_to_client(client_id, {
            "type": "dm_role_check_result",
            "is_dm": is_dm,
        })

    # =========================================================================
    # Player list
    # =========================================================================

    def _update_players_cache(self, data: dict):
        """Обновляет кеш игроков."""
        player_id = data.get("id", -1)
        if player_id >= 0:
            self._players_cache[player_id] = {
                "id": player_id,
                "name": data.get("name", "Unknown"),
                "pos": data.get("pos", [0, 0, 0]),
            }

    def _on_player_left(self, data: dict):
        """Удаляет игрока из кеша."""
        player_id = data.get("id", -1)
        if player_id in self._players_cache:
            del self._players_cache[player_id]

    def _on_player_list_request(self, data: dict):
        """Запрос списка игроков."""
        client_id = data.get("client_id", -1)

        if not self._is_dm(client_id):
            return

        players = []

        # Собираем данные об игроках
        if hasattr(self.app, 'players'):
            for pid, pdata in self.app.players.items():
                player_info = {
                    "id": pid,
                    "name": pdata.get("name", "Unknown"),
                    "class": "",
                    "level": 1,
                    "hp_current": 0,
                    "hp_max": 0,
                    "pos": pdata.get("pos", [0, 0, 0]),
                }

                # Получаем данные персонажа из authenticated_clients
                if hasattr(self.app, 'authenticated_clients'):
                    auth_data = self.app.authenticated_clients.get(pid, {})
                    char_data = auth_data.get("character_data", {})
                    if char_data:
                        player_info["class"] = char_data.get("class", "")
                        player_info["level"] = char_data.get("level", 1)
                        player_info["hp_current"] = char_data.get("hp_current", 0)
                        player_info["hp_max"] = char_data.get("hp_max", 0)

                players.append(player_info)

        self._send_to_client(client_id, {
            "type": "dm_panel_player_list",
            "players": players,
        })

    def _on_player_action(self, data: dict):
        """Действие над игроком."""
        client_id = data.get("client_id", -1)

        if not self._is_dm(client_id):
            return

        action = data.get("action", "")
        target_player_id = data.get("player_id", -1)
        amount = data.get("amount", 0)

        if action == "teleport_to":
            self._teleport_to_player(client_id, target_player_id)
        elif action == "heal":
            self._heal_player(target_player_id, amount)
        elif action == "damage":
            self._damage_player(target_player_id, amount)
        elif action == "kill":
            self._kill_player(target_player_id)

        # Обновляем список игроков для DM
        self._on_player_list_request({"client_id": client_id})

    def _teleport_to_player(self, dm_client_id: int, target_player_id: int):
        """Телепортирует DM к игроку."""
        if not hasattr(self.app, 'players'):
            return

        target_data = self.app.players.get(target_player_id)
        if not target_data:
            return

        target_pos = target_data.get("pos", [0, 0, 0])

        # Телепортируем DM
        if dm_client_id in self.app.players:
            self.app.players[dm_client_id]["pos"] = target_pos.copy()

    def _heal_player(self, player_id: int, amount: int):
        """Хилит игрока."""
        if not hasattr(self.app, 'authenticated_clients'):
            return

        auth_data = self.app.authenticated_clients.get(player_id, {})
        char_data = auth_data.get("character_data")
        if not char_data:
            return

        hp_current = char_data.get("hp_current", 0)
        hp_max = char_data.get("hp_max", 1)

        new_hp = min(hp_current + amount, hp_max)
        char_data["hp_current"] = new_hp

        # Уведомляем клиента
        self._send_to_client(player_id, {
            "type": "character_sheet",
            "character": char_data,
        })

        self.logger.info(f"DM healed player {player_id} for {amount} HP (now {new_hp}/{hp_max})")

    def _damage_player(self, player_id: int, amount: int):
        """Наносит урон игроку."""
        if not hasattr(self.app, 'authenticated_clients'):
            return

        auth_data = self.app.authenticated_clients.get(player_id, {})
        char_data = auth_data.get("character_data")
        if not char_data:
            return

        hp_current = char_data.get("hp_current", 0)
        new_hp = max(hp_current - amount, 0)
        char_data["hp_current"] = new_hp

        # Уведомляем клиента
        self._send_to_client(player_id, {
            "type": "character_sheet",
            "character": char_data,
        })

        self.logger.info(f"DM damaged player {player_id} for {amount} HP (now {new_hp})")

    def _kill_player(self, player_id: int):
        """Убивает игрока (HP = 0)."""
        if not hasattr(self.app, 'authenticated_clients'):
            return

        auth_data = self.app.authenticated_clients.get(player_id, {})
        char_data = auth_data.get("character_data")
        if not char_data:
            return

        char_data["hp_current"] = 0

        # Уведомляем клиента
        self._send_to_client(player_id, {
            "type": "character_sheet",
            "character": char_data,
        })

        self.logger.info(f"DM killed player {player_id}")

    # =========================================================================
    # Combat list
    # =========================================================================

    def _on_combat_list_request(self, data: dict):
        """Запрос списка боёв."""
        client_id = data.get("client_id", -1)

        if not self._is_dm(client_id):
            return

        combats = []

        # Получаем данные о боях из combat manager
        # Ищем модуль combat manager через плагины
        combat_manager = self._get_combat_manager()
        if combat_manager and hasattr(combat_manager, '_combats'):
            for combat_id, combat in combat_manager._combats.items():
                combats.append({
                    "id": combat_id,
                    "round": getattr(combat, 'round_number', 1),
                    "participants_count": len(getattr(combat, 'participants', [])),
                    "current_turn": getattr(combat, 'current_turn_entity_id', ""),
                })

        self._send_to_client(client_id, {
            "type": "dm_panel_combat_list",
            "combats": combats,
        })

    def _get_combat_manager(self):
        """Получает CombatManager из плагинов."""
        if not hasattr(self.app, 'plugin_manager'):
            return None

        for plugin in self.app.plugin_manager.plugins.values():
            for module in plugin.modules:
                if hasattr(module, '_combats'):
                    return module
        return None

    # =========================================================================
    # NPC list
    # =========================================================================

    def _on_npc_list_request(self, data: dict):
        """Запрос списка NPC."""
        client_id = data.get("client_id", -1)

        if not self._is_dm(client_id):
            return

        npcs = []

        # Получаем данные об NPC из NPC manager
        npc_manager = self._get_npc_manager()
        if npc_manager:
            npc_states = npc_manager.get_npc_states() if hasattr(npc_manager, 'get_npc_states') else {}
            for npc_id, npc_data in npc_states.items():
                npcs.append({
                    "id": npc_id,
                    "name": npc_data.get("name", "NPC"),
                    "template": npc_data.get("template_id", "unknown"),
                    "position": npc_data.get("position", [0, 0, 0]),
                })

        self._send_to_client(client_id, {
            "type": "dm_panel_npc_list",
            "npcs": npcs,
        })

    def _on_npc_templates_request(self, data: dict):
        """Запрос списка шаблонов NPC."""
        client_id = data.get("client_id", -1)

        if not self._is_dm(client_id):
            return

        templates = []

        # Получаем шаблоны из NPC manager
        npc_manager = self._get_npc_manager()
        if npc_manager and hasattr(npc_manager, '_templates'):
            templates = list(npc_manager._templates.keys())

        if not templates:
            templates = ["guard", "goblin", "merchant", "skeleton"]

        self._send_to_client(client_id, {
            "type": "dm_panel_npc_templates",
            "templates": templates,
        })

    def _get_npc_manager(self):
        """Получает NPCManager из плагинов."""
        if not hasattr(self.app, 'plugin_manager'):
            return None

        for plugin in self.app.plugin_manager.plugins.values():
            for module in plugin.modules:
                if hasattr(module, 'spawn_npc') and hasattr(module, 'despawn_npc'):
                    return module
        return None

    # =========================================================================
    # Announcements
    # =========================================================================

    def _on_announcement(self, data: dict):
        """Глобальное объявление."""
        client_id = data.get("client_id", -1)

        if not self._is_dm(client_id):
            return

        message = data.get("message", "")
        if not message.strip():
            return

        # Отправляем всем игрокам
        announcement = {
            "type": "chat_message",
            "chat_type": "announcement",
            "message": f"[DM] {message}",
            "color": [0.9, 0.7, 0.3, 1],  # Золотой цвет
        }

        self._broadcast_to_all(announcement)

        self.logger.info(f"DM announcement: {message}")

    # =========================================================================
    # Helpers
    # =========================================================================

    def _send_to_client(self, client_id: int, message: dict):
        """Отправляет сообщение клиенту."""
        if hasattr(self.app, 'send_to_client'):
            self.app.send_to_client(client_id, message)
        else:
            # Fallback через event manager
            self.event_manager.post(f"send_to_client_{client_id}", message)

    def _broadcast_to_all(self, message: dict):
        """Отправляет сообщение всем клиентам."""
        if hasattr(self.app, 'broadcast'):
            self.app.broadcast(message)
        elif hasattr(self.app, 'players'):
            for pid in self.app.players:
                self._send_to_client(pid, message)
