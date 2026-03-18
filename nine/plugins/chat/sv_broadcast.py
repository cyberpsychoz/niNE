"""
Серверный модуль чата.
Обрабатывает RP команды и рассылает сообщения с учётом радиуса.

Поддерживаемые команды:
- /me <действие> - действие от первого лица: "**Имя игрока <действие>"
- /it <текст> - безличное действие: "**<текст>"
- /looc <сообщение> - локальный неигровой чат (с радиусом)
- /ooc <сообщение> - глобальный неигровой чат (без радиуса)
- обычное сообщение - IC чат с радиусом

Команды предметов:
- /give <class_id> [count] - выдать предмет себе
- /spawn <class_id> [count] - заспавнить предмет
- /items - список доступных предметов

Админские команды:
- /charsetmodel <model> - изменить модель персонажа (admin/dm)
- /charsetfaction <faction> - изменить фракцию персонажа (admin/dm)

GM/DM боевые команды:
- /startcombat [radius] - начать бой с враждебными NPC в радиусе (admin/dm)
- /endcombat - принудительно завершить текущий бой (admin/dm)
- /spectator - переключить режим спектатора (admin/dm)
- /addtocombat <entity_id> - добавить сущность в текущий бой (admin/dm)
- /nextturn - принудительно перейти к следующему ходу (admin/dm)
- /setinit <entity_id> <value> - установить инициативу (admin/dm)

GM/DM аудио команды:
- /music play <playlist> - включить плейлист (adventure, combat, catacombs, city, dark_forest)
- /music stop [fadeout] - остановить музыку (fadeout в секундах, по умолчанию 2)
- /music track <filename> - включить конкретный трек из bgm/
- /ambient set <zone> - установить эмбиент (forest_day, cave, beach, sea, inside_day и др.)
- /ambient stop [fadeout] - остановить эмбиент
- /sfx play <sound> - воспроизвести звуковой эффект
- /volume master <0-100> - установить общую громкость
"""

import math
import importlib.util
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List

from nine.core.plugins import PluginModule


class ChatType(Enum):
    """Типы сообщений чата."""
    IC = "ic"           # Обычный внутриигровой чат
    EMOTE = "emote"     # /me действие
    IT = "it"           # /it безличное действие
    LOOC = "looc"       # Локальный OOC
    OOC = "ooc"         # Глобальный OOC
    COMMAND = "command" # Серверная команда (не отправляется в чат)
    INVALID_COMMAND = "invalid_command"  # Неизвестная команда


@dataclass
class ParsedMessage:
    """Результат парсинга сообщения."""
    chat_type: ChatType
    content: str
    command: str = ""      # Для команд: имя команды
    args: list = None      # Для команд: аргументы

    def __post_init__(self):
        if self.args is None:
            self.args = []


def _load_config(plugin_path: Path):
    """Загружает конфиг из папки плагина."""
    config_path = plugin_path / "sh_config.py"
    if not config_path.exists():
        return None

    spec = importlib.util.spec_from_file_location("chat_config", config_path)
    if spec is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Определение команд с описаниями и правами доступа
# role: "all" - все игроки, "admin" - только admin/dm
CHAT_COMMANDS = {
    # RP команды (доступны всем)
    "me": {
        "description": "/me <действие> — действие от первого лица",
        "role": "all",
        "usage": "/me машет рукой",
    },
    "it": {
        "description": "/it <текст> — безличное действие",
        "role": "all",
        "usage": "/it Ветер усиливается",
    },
    "looc": {
        "description": "/looc <текст> — локальный OOC чат (с радиусом)",
        "role": "all",
        "usage": "/looc Подожди секунду",
    },
    "ooc": {
        "description": "/ooc <текст> — глобальный OOC чат",
        "role": "all",
        "usage": "/ooc Всем привет!",
    },

    # Предметы (доступны всем)
    "give": {
        "description": "/give <id> [кол-во] — выдать предмет себе",
        "role": "all",
        "usage": "/give health_potion 5",
    },
    "spawn": {
        "description": "/spawn <id> [кол-во] — заспавнить предмет",
        "role": "all",
        "usage": "/spawn iron_sword",
    },
    "items": {
        "description": "/items — список доступных предметов",
        "role": "all",
        "usage": "/items",
    },

    # Админские команды персонажа
    "charsetmodel": {
        "description": "/charsetmodel <модель> — изменить модель персонажа",
        "role": "admin",
        "usage": "/charsetmodel human_male",
    },
    "charsetfaction": {
        "description": "/charsetfaction <фракция> — изменить фракцию",
        "role": "admin",
        "usage": "/charsetfaction guards",
    },

    # GM команды NPC
    "spawnnpc": {
        "description": "/spawnnpc <шаблон> [x y z] — заспавнить NPC",
        "role": "admin",
        "usage": "/spawnnpc goblin",
    },
    "listnpcs": {
        "description": "/listnpcs — список активных NPC",
        "role": "admin",
        "usage": "/listnpcs",
    },
    "removenpc": {
        "description": "/removenpc <id> — удалить NPC",
        "role": "admin",
        "usage": "/removenpc npc_goblin_1",
    },

    # GM боевые команды
    "startcombat": {
        "description": "/startcombat [радиус] — начать бой с NPC",
        "role": "admin",
        "usage": "/startcombat 30",
    },
    "endcombat": {
        "description": "/endcombat — завершить текущий бой",
        "role": "admin",
        "usage": "/endcombat",
    },
    "spectator": {
        "description": "/spectator — режим спектатора",
        "role": "admin",
        "usage": "/spectator",
    },
    "addtocombat": {
        "description": "/addtocombat <id> — добавить в бой",
        "role": "admin",
        "usage": "/addtocombat npc_goblin_1",
    },
    "nextturn": {
        "description": "/nextturn — следующий ход",
        "role": "admin",
        "usage": "/nextturn",
    },
    "setinit": {
        "description": "/setinit <id> <значение> — установить инициативу",
        "role": "admin",
        "usage": "/setinit player1 15",
    },
    "setrole": {
        "description": "/setrole <player|dm|admin> — установить себе роль (только из admins.txt)",
        "role": "all",
        "usage": "/setrole admin",
    },
    "myrole": {
        "description": "/myrole — показать свою текущую роль",
        "role": "all",
        "usage": "/myrole",
    },
    "whoami": {
        "description": "/whoami — показать своё имя и ID",
        "role": "all",
        "usage": "/whoami",
    },
    "pos": {
        "description": "/pos — показать свои координаты",
        "role": "all",
        "usage": "/pos",
    },

    # GM аудио команды
    "music": {
        "description": "/music <play|stop|track> — управление музыкой",
        "role": "admin",
        "usage": "/music play combat",
    },
    "ambient": {
        "description": "/ambient <set|stop> — управление эмбиентом",
        "role": "admin",
        "usage": "/ambient set forest_day",
    },
    "sfx": {
        "description": "/sfx play <звук> — воспроизвести SFX",
        "role": "admin",
        "usage": "/sfx play sword_attack",
    },
    "volume": {
        "description": "/volume master <0-100> — громкость",
        "role": "admin",
        "usage": "/volume master 50",
    },

    # Дебаг команды симулированного боя
    "simfights": {
        "description": "/simfights — список активных NPC-vs-NPC боёв",
        "role": "admin",
        "usage": "/simfights",
    },
    "forcefight": {
        "description": "/forcefight <template1> <template2> — заспавнить двух NPC и столкнуть",
        "role": "admin",
        "usage": "/forcefight guard goblin",
    },
    "stopsimfight": {
        "description": "/stopsimfight [fight_id] — остановить симулированный бой (или все)",
        "role": "admin",
        "usage": "/stopsimfight",
    },
    "factions": {
        "description": "/factions — показать матрицу враждебности фракций",
        "role": "admin",
        "usage": "/factions",
    },

    # Справка
    "help": {
        "description": "/help — показать список команд",
        "role": "all",
        "usage": "/help",
    },
}


class ChatBroadcastModule(PluginModule):
    """
    Серверный модуль для обработки и рассылки сообщений чата.
    Поддерживает RP команды и радиус чата.
    """

    def on_load(self):
        self.logger.info("Серверный модуль чата загружен")

        # Загружаем конфиг
        self.config = _load_config(self.plugin_path)

        # Радиусы чата
        self.radius_ic = getattr(self.config, 'CHAT_RADIUS_IC', 15.0) if self.config else 15.0
        self.radius_emote = getattr(self.config, 'CHAT_RADIUS_EMOTE', 15.0) if self.config else 15.0
        self.radius_looc = getattr(self.config, 'CHAT_RADIUS_LOOC', 15.0) if self.config else 15.0

        # Создаём обработчик команд
        from nine.plugins.chat.sv_commands import ChatCommandHandler
        self.command_handler = ChatCommandHandler(self)

        # Подписываемся на событие обработки сообщения
        self.event_manager.subscribe("chat_message_received", self.handle_chat_message)

    def on_unload(self):
        self.event_manager.unsubscribe("chat_message_received", self.handle_chat_message)

    def parse_message(self, raw_message: str) -> ParsedMessage:
        """
        Парсит сырое сообщение и определяет его тип.
        """
        message = raw_message.strip()

        # /me <действие>
        if message.lower().startswith("/me "):
            content = message[4:].strip()
            return ParsedMessage(ChatType.EMOTE, content)

        # /it <текст>
        if message.lower().startswith("/it "):
            content = message[4:].strip()
            return ParsedMessage(ChatType.IT, content)

        # /looc <сообщение>
        if message.lower().startswith("/looc "):
            content = message[6:].strip()
            return ParsedMessage(ChatType.LOOC, content)

        # /ooc <сообщение>
        if message.lower().startswith("/ooc "):
            content = message[5:].strip()
            return ParsedMessage(ChatType.OOC, content)

        # /give <class_id> [count] - выдать предмет себе
        if message.lower().startswith("/give "):
            parts = message[6:].strip().split()
            if parts:
                class_id = parts[0]
                count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
                return ParsedMessage(ChatType.COMMAND, "", command="give", args=[class_id, count])

        # /spawn <class_id> [count] - заспавнить предмет (пока = give)
        if message.lower().startswith("/spawn "):
            parts = message[7:].strip().split()
            if parts:
                class_id = parts[0]
                count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
                return ParsedMessage(ChatType.COMMAND, "", command="spawn", args=[class_id, count])

        # /items - список доступных предметов
        if message.lower().strip() == "/items":
            return ParsedMessage(ChatType.COMMAND, "", command="items", args=[])

        # /charsetmodel <model> - изменить модель персонажа (admin)
        if message.lower().startswith("/charsetmodel "):
            parts = message[14:].strip().split()
            if parts:
                model = parts[0]
                return ParsedMessage(ChatType.COMMAND, "", command="charsetmodel", args=[model])

        # /charsetfaction <faction> - изменить фракцию персонажа (admin)
        if message.lower().startswith("/charsetfaction "):
            parts = message[16:].strip().split()
            if parts:
                faction = parts[0].lower()
                return ParsedMessage(ChatType.COMMAND, "", command="charsetfaction", args=[faction])

        # =========================================================================
        # GM/DM команды NPC
        # =========================================================================

        # /spawnnpc <template> [x y z] - заспавнить NPC
        if message.lower().startswith("/spawnnpc "):
            parts = message[10:].strip().split()
            if parts:
                template = parts[0]
                coords = []
                if len(parts) >= 4:
                    try:
                        coords = [float(parts[1]), float(parts[2]), float(parts[3])]
                    except ValueError:
                        pass
                return ParsedMessage(ChatType.COMMAND, "", command="spawnnpc", args=[template] + coords)

        # /listnpcs - список активных NPC
        if message.lower().strip() == "/listnpcs":
            return ParsedMessage(ChatType.COMMAND, "", command="listnpcs", args=[])

        # /removenpc <entity_id> - удалить NPC
        if message.lower().startswith("/removenpc "):
            parts = message[11:].strip().split()
            if parts:
                entity_id = parts[0]
                return ParsedMessage(ChatType.COMMAND, "", command="removenpc", args=[entity_id])

        # =========================================================================
        # GM/DM боевые команды
        # =========================================================================

        # /startcombat [radius] - начать бой с враждебными NPC в радиусе (dm/admin)
        if message.lower().startswith("/startcombat"):
            parts = message[12:].strip().split()
            radius = float(parts[0]) if parts and parts[0].replace('.', '').isdigit() else 30.0
            return ParsedMessage(ChatType.COMMAND, "", command="startcombat", args=[radius])

        # /endcombat - принудительно завершить текущий бой (dm/admin)
        if message.lower().strip() == "/endcombat":
            return ParsedMessage(ChatType.COMMAND, "", command="endcombat", args=[])

        # /spectator - переключить режим спектатора (dm/admin)
        if message.lower().strip() == "/spectator":
            return ParsedMessage(ChatType.COMMAND, "", command="spectator", args=[])

        # /addtocombat <entity_id> - добавить сущность в текущий бой (dm/admin)
        if message.lower().startswith("/addtocombat "):
            parts = message[13:].strip().split()
            if parts:
                entity_id = parts[0]
                return ParsedMessage(ChatType.COMMAND, "", command="addtocombat", args=[entity_id])

        # /nextturn - принудительно перейти к следующему ходу (dm/admin)
        if message.lower().strip() == "/nextturn":
            return ParsedMessage(ChatType.COMMAND, "", command="nextturn", args=[])

        # /setinit <entity_id> <value> - установить инициативу (dm/admin)
        if message.lower().startswith("/setinit "):
            parts = message[9:].strip().split()
            if len(parts) >= 2:
                entity_id = parts[0]
                try:
                    value = int(parts[1])
                    return ParsedMessage(ChatType.COMMAND, "", command="setinit", args=[entity_id, value])
                except ValueError:
                    pass

        # =========================================================================
        # GM/DM аудио команды
        # =========================================================================

        # /music <subcommand> [args] - управление музыкой (dm/admin)
        if message.lower().startswith("/music "):
            parts = message[7:].strip().split()
            if parts:
                subcommand = parts[0].lower()
                subargs = parts[1:] if len(parts) > 1 else []
                return ParsedMessage(ChatType.COMMAND, "", command="music", args=[subcommand] + subargs)

        # /ambient <subcommand> [args] - управление эмбиентом (dm/admin)
        if message.lower().startswith("/ambient "):
            parts = message[9:].strip().split()
            if parts:
                subcommand = parts[0].lower()
                subargs = parts[1:] if len(parts) > 1 else []
                return ParsedMessage(ChatType.COMMAND, "", command="ambient", args=[subcommand] + subargs)

        # /sfx play <sound> - воспроизвести звуковой эффект (dm/admin)
        if message.lower().startswith("/sfx "):
            parts = message[5:].strip().split()
            if parts:
                subcommand = parts[0].lower()
                subargs = parts[1:] if len(parts) > 1 else []
                return ParsedMessage(ChatType.COMMAND, "", command="sfx", args=[subcommand] + subargs)

        # /volume <channel> <value> - управление громкостью (dm/admin)
        if message.lower().startswith("/volume "):
            parts = message[8:].strip().split()
            if len(parts) >= 2:
                channel = parts[0].lower()
                try:
                    value = int(parts[1])
                    return ParsedMessage(ChatType.COMMAND, "", command="volume", args=[channel, value])
                except ValueError:
                    pass

        # /help - показать список команд
        if message.lower().strip() == "/help":
            return ParsedMessage(ChatType.COMMAND, "", command="help", args=[])

        # /setrole <role> - установить роль
        if message.lower().startswith("/setrole "):
            parts = message[9:].strip().split()
            if parts:
                role = parts[0]
                return ParsedMessage(ChatType.COMMAND, "", command="setrole", args=[role])

        # /myrole - показать свою роль
        if message.lower().strip() == "/myrole":
            return ParsedMessage(ChatType.COMMAND, "", command="myrole", args=[])

        # /whoami - показать своё имя и ID
        if message.lower().strip() == "/whoami":
            return ParsedMessage(ChatType.COMMAND, "", command="whoami", args=[])

        # /pos - показать свои координаты
        if message.lower().strip() == "/pos":
            return ParsedMessage(ChatType.COMMAND, "", command="pos", args=[])

        # =========================================================================
        # Дебаг команды симулированного боя
        # =========================================================================

        # /simfights — список активных NPC-vs-NPC боёв
        if message.lower().strip() == "/simfights":
            return ParsedMessage(ChatType.COMMAND, "", command="simfights", args=[])

        # /forcefight <template1> <template2> — заспавнить и столкнуть
        if message.lower().startswith("/forcefight "):
            parts = message[12:].strip().split()
            if len(parts) >= 2:
                return ParsedMessage(ChatType.COMMAND, "", command="forcefight", args=[parts[0], parts[1]])

        # /stopsimfight [fight_id] — остановить симулированный бой
        if message.lower().startswith("/stopsimfight"):
            parts = message[13:].strip().split()
            fight_id = parts[0] if parts else ""
            return ParsedMessage(ChatType.COMMAND, "", command="stopsimfight", args=[fight_id])

        # /factions — матрица враждебности
        if message.lower().strip() == "/factions":
            return ParsedMessage(ChatType.COMMAND, "", command="factions", args=[])

        # Проверка на неизвестную команду (начинается с /, но не распознана)
        if message.startswith("/"):
            # Извлекаем имя команды для сообщения об ошибке
            cmd_parts = message[1:].split()
            unknown_cmd = cmd_parts[0] if cmd_parts else ""
            return ParsedMessage(ChatType.INVALID_COMMAND, message, command=unknown_cmd)

        # Обычное сообщение (IC)
        return ParsedMessage(ChatType.IC, message)

    def get_distance(self, pos1: list, pos2: list) -> float:
        """Вычисляет расстояние между двумя позициями."""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        dz = pos1[2] - pos2[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def get_players_in_radius(self, sender_pos: list, radius: float) -> List[int]:
        """
        Возвращает список client_id игроков в радиусе от отправителя.
        """
        if not hasattr(self.app, 'world'):
            return list(self.app.clients.keys()) if hasattr(self.app, 'clients') else []

        nearby_players = []
        for client_id, player in self.app.world.players.items():
            player_pos = player.get_state()["pos"]
            distance = self.get_distance(sender_pos, player_pos)
            if distance <= radius:
                nearby_players.append(client_id)

        return nearby_players

    def handle_chat_message(self, data: dict):
        """
        Обрабатывает входящее сообщение чата.
        data = {
            "client_id": int,
            "player_name": str,
            "message": str,
            "player_pos": [x, y, z]
        }
        """
        client_id = data.get("client_id")
        player_name = data.get("player_name", "Unknown")
        raw_message = data.get("message", "")
        sender_pos = data.get("player_pos", [0, 0, 0])

        if not raw_message.strip():
            return

        # Парсим сообщение
        parsed = self.parse_message(raw_message)

        # Обрабатываем команды (не отправляем в чат)
        if parsed.chat_type == ChatType.COMMAND:
            self.command_handler.dispatch(client_id, player_name, parsed)
            return

        # Обрабатываем неизвестные команды (отправляем ошибку только отправителю)
        if parsed.chat_type == ChatType.INVALID_COMMAND:
            self._send_system_message(
                client_id,
                f"Неизвестная команда: /{parsed.command}. Используйте /help для списка команд."
            )
            return

        # Формируем данные для отправки в зависимости от типа
        broadcast_data = {
            "type": "chat_broadcast",
            "chat_type": parsed.chat_type.value,
            "from_name": player_name,
        }

        # Определяем получателей и формат сообщения
        if parsed.chat_type == ChatType.IC:
            # Обычный IC чат с радиусом
            broadcast_data["message"] = parsed.content
            recipients = self.get_players_in_radius(sender_pos, self.radius_ic)

        elif parsed.chat_type == ChatType.EMOTE:
            # /me - "**Имя игрока <действие>"
            broadcast_data["message"] = parsed.content
            broadcast_data["formatted_message"] = f"**{player_name} {parsed.content}"
            recipients = self.get_players_in_radius(sender_pos, self.radius_emote)

        elif parsed.chat_type == ChatType.IT:
            # /it - "**<текст>"
            broadcast_data["message"] = parsed.content
            broadcast_data["formatted_message"] = f"**{parsed.content}"
            broadcast_data["from_name"] = ""  # Безличное
            recipients = self.get_players_in_radius(sender_pos, self.radius_emote)

        elif parsed.chat_type == ChatType.LOOC:
            # LOOC - локальный с радиусом
            broadcast_data["message"] = parsed.content
            recipients = self.get_players_in_radius(sender_pos, self.radius_looc)

        elif parsed.chat_type == ChatType.OOC:
            # OOC - глобальный, без радиуса
            broadcast_data["message"] = parsed.content
            recipients = None  # Всем

        else:
            recipients = None

        # Отправляем через событие
        self.event_manager.post("chat_send_to_clients", {
            "data": broadcast_data,
            "recipients": recipients  # None = всем, list = конкретным клиентам
        })

    # =========================================================================
    # Helper methods
    # =========================================================================

    def _get_player_role(self, client_id: int) -> str:
        """Получает роль игрока по client_id."""
        # Получаем имя игрока для проверки admins.txt
        player_name = self._get_player_name_by_id(client_id)

        # Проверяем admins.txt - если игрок там, он автоматически admin
        if player_name and self._is_in_admins_file(player_name):
            return "admin"

        # Dev-клиенты автоматически получают роль admin для тестирования
        if hasattr(self.app, 'allow_dev_client') and self.app.allow_dev_client:
            # Проверяем, это dev-клиент (нет в authenticated_clients)
            is_dev_client = True
            if hasattr(self.app, 'plugin_manager'):
                dnd_plugin = self.app.plugin_manager.get_plugin("nine.dnd")
                if dnd_plugin:
                    for module in dnd_plugin.modules:
                        if hasattr(module, 'authenticated_clients'):
                            if client_id in module.authenticated_clients:
                                is_dev_client = False
                            break
            if is_dev_client:
                return "admin"

        if not hasattr(self.app, 'db'):
            return "player"

        # Получаем account_uuid из D&D плагина
        if hasattr(self.app, 'plugin_manager'):
            dnd_plugin = self.app.plugin_manager.get_plugin("nine.dnd")
            if dnd_plugin:
                for module in dnd_plugin.modules:
                    if hasattr(module, 'authenticated_clients'):
                        account_uuid = module.authenticated_clients.get(client_id)
                        if account_uuid:
                            return self.app.db.get_player_role(account_uuid)
        return "player"

    def _get_player_name_by_id(self, client_id: int) -> str:
        """Получает имя игрока по client_id."""
        if hasattr(self.app, 'world') and hasattr(self.app.world, 'players'):
            player = self.app.world.players.get(client_id)
            if player:
                return player.name
        return ""

    def _is_admin(self, client_id: int) -> bool:
        """Проверяет, является ли игрок администратором или DM."""
        role = self._get_player_role(client_id)
        return role in ("admin", "dm")

    def _is_in_admins_file(self, player_name: str) -> bool:
        """Проверяет, есть ли игрок в файле admins.txt."""
        import os
        admins_file = "admins.txt"
        if not os.path.exists(admins_file):
            return False
        try:
            with open(admins_file, 'r', encoding='utf-8') as f:
                admins = [line.strip().lower() for line in f if line.strip() and not line.startswith('#')]
            return player_name.lower() in admins
        except Exception:
            return False

    def _get_active_character(self, client_id: int) -> Optional[str]:
        """Получает UUID активного персонажа клиента."""
        if hasattr(self.app, 'plugin_manager'):
            dnd_plugin = self.app.plugin_manager.get_plugin("nine.dnd")
            if dnd_plugin:
                for module in dnd_plugin.modules:
                    if hasattr(module, 'active_characters'):
                        return module.active_characters.get(client_id)
        return None

    def _send_system_message(self, client_id: int, message: str):
        """Отправляет системное сообщение игроку."""
        self.event_manager.post("chat_send_to_clients", {
            "data": {
                "type": "chat_broadcast",
                "chat_type": "system",
                "from_name": "Система",
                "message": message,
            },
            "recipients": [client_id]
        })

    def _get_player_position(self, client_id: int) -> Optional[List[float]]:
        """Получает позицию игрока."""
        if hasattr(self.app, 'world'):
            player = self.app.world.players.get(client_id)
            if player:
                state = player.get_state()
                return state.get("pos", [0, 0, 0])
        return None
