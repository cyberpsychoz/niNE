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

        # Admin panel actions (CEF)
        self.event_manager.subscribe("dm_panel_admin_action", self._on_admin_action)
        self.event_manager.subscribe("admin_toggle_noclip", self._on_toggle_noclip)

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
        self.event_manager.unsubscribe("dm_panel_admin_action", self._on_admin_action)
        self.event_manager.unsubscribe("admin_toggle_noclip", self._on_toggle_noclip)
        self.event_manager.unsubscribe("player_joined", self._update_players_cache)
        self.event_manager.unsubscribe("player_left", self._on_player_left)
        self.logger.info("DM Panel серверный модуль выгружен")

    # =========================================================================
    # Role checking
    # =========================================================================

    def _get_dnd_module(self):
        """Find the DnD character module from loaded plugins."""
        pm = getattr(self.app, 'plugin_manager', None)
        if not pm:
            return None
        loaded = pm.loaded_plugins.get("nine.dnd")
        if not loaded:
            return None
        for module in loaded.modules:
            if hasattr(module, 'active_characters') and hasattr(module, 'authenticated_clients'):
                return module
        return None

    def _get_character_sheet_module(self):
        """Find the sv_character_sheet module from loaded plugins."""
        pm = getattr(self.app, 'plugin_manager', None)
        if not pm:
            return None
        loaded = pm.loaded_plugins.get("nine.inventory")
        if not loaded:
            return None
        for module in loaded.modules:
            if hasattr(module, 'characters') and hasattr(module, '_send_character_sheet'):
                return module
        return None

    def _get_player_role(self, client_id: int) -> str:
        """Получает роль игрока."""
        # Dev-клиенты автоматически получают роль admin для тестирования
        if hasattr(self.app, 'allow_dev_client') and self.app.allow_dev_client:
            return "admin"

        # Получаем account_uuid из DnD character module
        dnd = self._get_dnd_module()
        if not dnd:
            return "player"

        account_uuid = dnd.authenticated_clients.get(client_id)
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

        # Собираем данные об игроках из world.players
        dnd = self._get_dnd_module()
        db = self.app.db if hasattr(self.app, 'db') else None

        if hasattr(self.app, 'world') and hasattr(self.app.world, 'players'):
            for pid, player in self.app.world.players.items():
                state = player.get_state()
                player_info = {
                    "id": pid,
                    "name": player.name,
                    "class": "",
                    "level": 1,
                    "hp_current": 0,
                    "hp_max": 0,
                    "pos": state.get("pos", [0, 0, 0]),
                }

                # Get IP (masked last octet for display)
                ip = ""
                if hasattr(self.app, 'client_addresses'):
                    raw_ip = self.app.client_addresses.get(pid, "")
                    if raw_ip:
                        parts = raw_ip.split(".")
                        if len(parts) == 4:
                            ip = f"{parts[0]}.{parts[1]}.{parts[2]}.*"
                        else:
                            ip = raw_ip
                player_info["ip"] = ip

                # Получаем данные персонажа из DB через DnD module
                if dnd and db:
                    char_uuid = dnd.active_characters.get(pid)
                    if char_uuid:
                        char_data = db.get_character(char_uuid)
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
        elif action == "set_hp":
            self._set_hp(target_player_id, amount)
        elif action == "kick":
            reason = data.get("reason", "")
            if hasattr(self.app, 'kick_player'):
                self.app.kick_player(target_player_id, reason)
        elif action == "ban":
            reason = data.get("reason", "")
            if hasattr(self.app, 'ban_player'):
                self.app.ban_player(target_player_id, reason)
        elif action == "apply_condition":
            condition = data.get("condition", "")
            if condition:
                self.event_manager.post("apply_condition", {
                    "client_id": target_player_id,
                    "condition": condition,
                })
        elif action == "remove_condition":
            condition = data.get("condition", "")
            if condition:
                self.event_manager.post("remove_condition", {
                    "client_id": target_player_id,
                    "condition": condition,
                })

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

    def _get_char_data(self, player_id: int):
        """Get character data from DB for a player. Returns (char_uuid, char_data) or (None, None)."""
        dnd = self._get_dnd_module()
        db = self.app.db if hasattr(self.app, 'db') else None
        if not dnd or not db:
            return None, None
        char_uuid = dnd.active_characters.get(player_id)
        if not char_uuid:
            return None, None
        char_data = db.get_character(char_uuid)
        return char_uuid, char_data

    def _update_hp_and_notify(self, player_id: int, char_uuid: str, char_data: dict, new_hp: int):
        """Update HP in DB and send properly formatted character_sheet to client."""
        db = self.app.db if hasattr(self.app, 'db') else None
        if not db:
            return
        hp_max = char_data.get("hp_max", 1)
        new_hp = max(0, min(new_hp, hp_max))
        db.update_character(char_uuid, {"hp_current": new_hp})

        # Route through sv_character_sheet so the HUD gets the proper nested format
        # (GameHUD reads character.stats.current_hp, not character.hp_current)
        # Note: sv_character_sheet indexes by client_id (character_selected posts uuid=client_id)
        cs = self._get_character_sheet_module()
        if cs and player_id in cs.characters:
            cs.characters[player_id]["hp_current"] = new_hp
            if "stats" in cs.characters[player_id]:
                cs.characters[player_id]["stats"]["current_hp"] = new_hp
            cs._send_character_sheet(player_id)
            return

        # Fallback: send with minimal stats sub-object
        char_data["hp_current"] = new_hp
        char_data.setdefault("stats", {})
        char_data["stats"]["current_hp"] = new_hp
        char_data["stats"]["max_hp"] = hp_max
        self._send_to_client(player_id, {
            "type": "character_sheet",
            "character": char_data,
        })

    def _heal_player(self, player_id: int, amount: int):
        """Хилит игрока."""
        char_uuid, char_data = self._get_char_data(player_id)
        if not char_data:
            return
        hp_current = char_data.get("hp_current", 0)
        hp_max = char_data.get("hp_max", 1)
        new_hp = min(hp_current + amount, hp_max)
        self._update_hp_and_notify(player_id, char_uuid, char_data, new_hp)
        self.logger.info(f"DM healed player {player_id} for {amount} HP (now {new_hp}/{hp_max})")

    def _damage_player(self, player_id: int, amount: int):
        """Наносит урон игроку."""
        char_uuid, char_data = self._get_char_data(player_id)
        if not char_data:
            return
        hp_current = char_data.get("hp_current", 0)
        new_hp = max(hp_current - amount, 0)
        self._update_hp_and_notify(player_id, char_uuid, char_data, new_hp)
        self.logger.info(f"DM damaged player {player_id} for {amount} HP (now {new_hp})")

    def _kill_player(self, player_id: int):
        """Убивает игрока (HP = 0)."""
        char_uuid, char_data = self._get_char_data(player_id)
        if not char_data:
            return
        self._update_hp_and_notify(player_id, char_uuid, char_data, 0)
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

        for plugin in self.app.plugin_manager.loaded_plugins.values():
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

        for plugin in self.app.plugin_manager.loaded_plugins.values():
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
    # Admin Actions (CEF panel)
    # =========================================================================

    def _on_admin_action(self, data: dict):
        """Generic admin action handler from CEF panel."""
        client_id = data.get("client_id", -1)

        if not self._is_dm(client_id):
            return

        action = data.get("action", "")

        if action == "player_action":
            # Delegate to existing player action handler
            # JS sends inner action as "player_action" key to avoid collision
            inner_action = data.get("player_action", "")
            self._on_player_action({**data, "action": inner_action})
        elif action == "start_combat":
            radius = data.get("radius", 30)
            self.event_manager.post("dm_start_combat", {
                "client_id": client_id,
                "radius": radius,
            })
        elif action == "end_combat":
            self.event_manager.post("dm_end_combat", {
                "client_id": client_id,
            })
        elif action == "next_turn":
            self.event_manager.post("dm_force_next_turn", {
                "client_id": client_id,
            })
        elif action == "spawn_npc":
            template_id = data.get("template_id", "guard")
            position = data.get("position", [0, 0, 1])
            self.event_manager.post("dm_npc_spawn", {
                "client_id": client_id,
                "template_id": template_id,
                "position": position,
            })
        elif action == "announcement":
            self._on_announcement(data)
        elif action == "unban_ip":
            ip = data.get("ip", "")
            if ip and hasattr(self.app, 'unban_ip'):
                self.app.unban_ip(ip)
                self._send_ban_list(client_id)
        elif action == "ban_ip":
            ip = data.get("ip", "")
            if ip and hasattr(self.app, 'banned_ips'):
                self.app.banned_ips.add(ip)
                self.app._save_banlist()
                self._send_ban_list(client_id)
        elif action == "request_ban_list":
            self._send_ban_list(client_id)
        elif action == "request_player_list":
            self._on_player_list_request({"client_id": client_id})
        elif action == "request_combat_list":
            self._on_combat_list_request({"client_id": client_id})
        elif action == "request_npc_templates":
            self._on_npc_templates_request({"client_id": client_id})
        else:
            self.logger.warning(f"Unknown admin action: {action}")

    def _on_toggle_noclip(self, data: dict):
        """Toggle noclip mode for a client."""
        client_id = data.get("client_id", -1)

        if not self._is_dm(client_id):
            return

        noclip_set = getattr(self.app, 'noclip_clients', set())
        if client_id in noclip_set:
            noclip_set.discard(client_id)
            enabled = False
        else:
            noclip_set.add(client_id)
            enabled = True

        # Toggle on the character controller
        if hasattr(self.app, 'world') and hasattr(self.app.world, 'players'):
            player = self.app.world.players.get(client_id)
            if player and hasattr(player, 'character_controller'):
                if enabled:
                    player.character_controller.enable_noclip()
                else:
                    player.character_controller.disable_noclip()

        # Notify client
        import asyncio
        asyncio.run_coroutine_threadsafe(
            self.app.send_to_client(client_id, {
                "type": "noclip_toggled",
                "enabled": enabled,
            }),
            self.app.asyncio_loop
        )
        self.logger.info(f"Noclip {'enabled' if enabled else 'disabled'} for client {client_id}")

    def _set_hp(self, player_id: int, value: int):
        """Set a player's HP to an exact value."""
        char_uuid, char_data = self._get_char_data(player_id)
        if not char_data:
            return
        hp_max = char_data.get("hp_max", 1)
        new_hp = max(0, min(value, hp_max))
        self._update_hp_and_notify(player_id, char_uuid, char_data, new_hp)
        self.logger.info(f"DM set player {player_id} HP to {new_hp}/{hp_max}")

    def _send_ban_list(self, client_id: int):
        """Send the ban list to a client."""
        banned = []
        if hasattr(self.app, 'banned_ips'):
            banned = sorted(self.app.banned_ips)
        self._send_to_client(client_id, {
            "type": "admin_panel_ban_list",
            "banned_ips": banned,
        })

    # =========================================================================
    # Helpers
    # =========================================================================

    def _send_to_client(self, client_id: int, message: dict):
        """Отправляет сообщение клиенту."""
        import asyncio
        if hasattr(self.app, 'send_to_client') and hasattr(self.app, 'asyncio_loop'):
            asyncio.run_coroutine_threadsafe(
                self.app.send_to_client(client_id, message),
                self.app.asyncio_loop
            )
        elif hasattr(self.app, 'send_to_client'):
            self.app.send_to_client(client_id, message)
        else:
            self.event_manager.post(f"send_to_client_{client_id}", message)

    def _broadcast_to_all(self, message: dict):
        """Отправляет сообщение всем клиентам."""
        import asyncio
        if hasattr(self.app, 'broadcast') and hasattr(self.app, 'asyncio_loop'):
            asyncio.run_coroutine_threadsafe(
                self.app.broadcast(message),
                self.app.asyncio_loop
            )
        elif hasattr(self.app, 'clients'):
            for pid in self.app.clients:
                self._send_to_client(pid, message)
