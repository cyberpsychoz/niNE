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


def _load_dnd_constants():
    """Загружает константы D&D для валидации моделей и фракций."""
    try:
        constants_path = Path(__file__).parent.parent / "dnd" / "sh_constants.py"
        if constants_path.exists():
            spec = importlib.util.spec_from_file_location("dnd_constants", constants_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    except Exception:
        pass
    return None


_dnd_constants = _load_dnd_constants()
AVAILABLE_MODELS = getattr(_dnd_constants, 'AVAILABLE_MODELS', []) if _dnd_constants else []
FACTIONS = getattr(_dnd_constants, 'FACTIONS', {}) if _dnd_constants else {}


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
            self._handle_command(client_id, player_name, parsed)
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

    def _handle_command(self, client_id: int, player_name: str, parsed: ParsedMessage):
        """Обрабатывает серверные команды."""
        command = parsed.command
        args = parsed.args

        if command == "give":
            # /give <class_id> [count]
            if len(args) >= 1:
                class_id = args[0]
                count = args[1] if len(args) > 1 else 1

                # Отправляем событие плагину инвентаря
                self.event_manager.post("give_item", {
                    "uuid": client_id,
                    "class_id": class_id,
                    "count": count,
                })

                # Отправляем подтверждение игроку
                self._send_system_message(client_id, f"Выдано: {count}x {class_id}")
                self.logger.info(f"{player_name} использовал /give {class_id} {count}")

        elif command == "spawn":
            # /spawn <class_id> [count] - пока просто выдаём в инвентарь
            if len(args) >= 1:
                class_id = args[0]
                count = args[1] if len(args) > 1 else 1

                self.event_manager.post("give_item", {
                    "uuid": client_id,
                    "class_id": class_id,
                    "count": count,
                })

                self._send_system_message(client_id, f"Заспавнено: {count}x {class_id}")
                self.logger.info(f"{player_name} использовал /spawn {class_id} {count}")

        elif command == "items":
            # /items - список всех доступных предметов
            from nine.core.entity import ENTITY_REGISTRY
            items = ENTITY_REGISTRY.get_all_classes()
            if items:
                item_list = ", ".join(items.keys())
                self._send_system_message(client_id, f"Доступные предметы: {item_list}")
            else:
                self._send_system_message(client_id, "Нет зарегистрированных предметов")

        elif command == "charsetmodel":
            # /charsetmodel <model> - только для админов
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            if len(args) < 1:
                self._send_system_message(client_id, "Использование: /charsetmodel <название_модели>")
                return

            model = args[0]
            if AVAILABLE_MODELS and model not in AVAILABLE_MODELS:
                models_list = ", ".join(AVAILABLE_MODELS)
                self._send_system_message(client_id, f"Недопустимая модель. Доступные: {models_list}")
                return

            char_uuid = self._get_active_character(client_id)
            if not char_uuid:
                self._send_system_message(client_id, "Нет активного персонажа")
                return

            if hasattr(self.app, 'db') and self.app.db.update_character_model(char_uuid, model):
                self._send_system_message(client_id, f"Модель персонажа изменена на: {model}")
                self.logger.info(f"{player_name} использовал /charsetmodel {model}")
            else:
                self._send_system_message(client_id, "Ошибка при изменении модели")

        elif command == "charsetfaction":
            # /charsetfaction <faction> - только для админов
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            if len(args) < 1:
                self._send_system_message(client_id, "Использование: /charsetfaction <фракция>")
                return

            faction = args[0]
            if FACTIONS and faction not in FACTIONS:
                factions_list = ", ".join(FACTIONS.keys())
                self._send_system_message(client_id, f"Недопустимая фракция. Доступные: {factions_list}")
                return

            char_uuid = self._get_active_character(client_id)
            if not char_uuid:
                self._send_system_message(client_id, "Нет активного персонажа")
                return

            if hasattr(self.app, 'db') and self.app.db.update_character_faction(char_uuid, faction):
                faction_name = FACTIONS.get(faction, {}).get("name_ru", faction)
                self._send_system_message(client_id, f"Фракция персонажа изменена на: {faction_name}")
                self.logger.info(f"{player_name} использовал /charsetfaction {faction}")
            else:
                self._send_system_message(client_id, "Ошибка при изменении фракции")

        # =========================================================================
        # GM/DM команды NPC
        # =========================================================================

        elif command == "spawnnpc":
            # /spawnnpc <template> [x y z] - заспавнить NPC
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            if len(args) < 1:
                self._send_system_message(client_id, "Использование: /spawnnpc <шаблон> [x y z]")
                return

            template = args[0]
            coords = args[1:4] if len(args) >= 4 else None
            self._handle_spawnnpc(client_id, player_name, template, coords)

        elif command == "listnpcs":
            # /listnpcs - список активных NPC
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            self._handle_listnpcs(client_id, player_name)

        elif command == "removenpc":
            # /removenpc <entity_id> - удалить NPC
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            if len(args) < 1:
                self._send_system_message(client_id, "Использование: /removenpc <entity_id>")
                return

            entity_id = args[0]
            self._handle_removenpc(client_id, player_name, entity_id)

        # =========================================================================
        # GM/DM боевые команды
        # =========================================================================

        elif command == "startcombat":
            # /startcombat [radius] - начать бой с враждебными NPC
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            radius = args[0] if args else 30.0
            self._handle_startcombat(client_id, player_name, radius)

        elif command == "endcombat":
            # /endcombat - завершить текущий бой
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            self._handle_endcombat(client_id, player_name)

        elif command == "spectator":
            # /spectator - переключить режим спектатора
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            self._handle_spectator(client_id, player_name)

        elif command == "addtocombat":
            # /addtocombat <entity_id> - добавить сущность в бой
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            if len(args) < 1:
                self._send_system_message(client_id, "Использование: /addtocombat <entity_id>")
                return

            entity_id = args[0]
            self._handle_addtocombat(client_id, player_name, entity_id)

        elif command == "nextturn":
            # /nextturn - принудительно следующий ход
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            self._handle_nextturn(client_id, player_name)

        elif command == "setinit":
            # /setinit <entity_id> <value> - установить инициативу
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            if len(args) < 2:
                self._send_system_message(client_id, "Использование: /setinit <entity_id> <значение>")
                return

            entity_id = args[0]
            value = args[1]
            self._handle_setinit(client_id, player_name, entity_id, value)

        elif command == "setrole":
            # /setrole <role> - установить роль (только для тех кто в admins.txt)
            if not args:
                self._send_system_message(client_id, "Использование: /setrole <player|dm|admin>")
                return
            self._handle_setrole(client_id, player_name, args[0])

        elif command == "myrole":
            # /myrole - показать текущую роль
            role = self._get_player_role(client_id)
            self._send_system_message(client_id, f"Ваша роль: {role}")

        elif command == "whoami":
            # /whoami - показать своё имя и ID
            self._send_system_message(client_id, f"Имя: {player_name}, Client ID: {client_id}")

        elif command == "pos":
            # /pos - показать свои координаты
            self._handle_pos_command(client_id)

        # =========================================================================
        # GM/DM аудио команды
        # =========================================================================

        elif command == "music":
            # /music <subcommand> [args] - управление музыкой
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            self._handle_music_command(client_id, player_name, args)

        elif command == "ambient":
            # /ambient <subcommand> [args] - управление эмбиентом
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            self._handle_ambient_command(client_id, player_name, args)

        elif command == "sfx":
            # /sfx <subcommand> [args] - звуковые эффекты
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            self._handle_sfx_command(client_id, player_name, args)

        elif command == "volume":
            # /volume <channel> <value> - управление громкостью
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return

            self._handle_volume_command(client_id, player_name, args)

        # =========================================================================
        # Дебаг команды симулированного боя
        # =========================================================================

        elif command == "simfights":
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return
            self._handle_simfights(client_id)

        elif command == "forcefight":
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return
            if len(args) < 2:
                self._send_system_message(client_id, "Использование: /forcefight <template1> <template2>")
                return
            self._handle_forcefight(client_id, player_name, args[0], args[1])

        elif command == "stopsimfight":
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return
            fight_id = args[0] if args and args[0] else ""
            self._handle_stopsimfight(client_id, fight_id)

        elif command == "factions":
            if not self._is_admin(client_id):
                self._send_system_message(client_id, "Недостаточно прав для этой команды")
                return
            self._handle_factions(client_id)

        elif command == "help":
            # /help - показать список команд
            self._handle_help_command(client_id)

    def _handle_help_command(self, client_id: int):
        """Обрабатывает /help - показывает список доступных команд."""
        is_admin = self._is_admin(client_id)

        # Формируем список команд в зависимости от роли
        lines = ["Доступные команды:"]

        for cmd_name, cmd_info in CHAT_COMMANDS.items():
            # Пропускаем админские команды для обычных игроков
            if cmd_info["role"] == "admin" and not is_admin:
                continue

            lines.append(f"  {cmd_info['description']}")

        # Отправляем сообщение
        help_text = "\n".join(lines)
        self._send_system_message(client_id, help_text)

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

    def _handle_pos_command(self, client_id: int):
        """Показывает координаты игрока."""
        if not hasattr(self.app, 'world') or client_id not in self.app.world.players:
            self._send_system_message(client_id, "Не удалось получить позицию")
            return

        player = self.app.world.players[client_id]
        pos = player.get_state().get("pos", [0, 0, 0])
        x, y, z = pos[0], pos[1], pos[2]
        self._send_system_message(client_id, f"Позиция: X={x:.2f}, Y={y:.2f}, Z={z:.2f}")

    def _handle_setrole(self, client_id: int, player_name: str, role: str):
        """Устанавливает роль игроку."""
        role = role.lower()
        valid_roles = ("player", "dm", "admin")

        if role not in valid_roles:
            self._send_system_message(client_id, f"Недопустимая роль. Доступные: {', '.join(valid_roles)}")
            return

        # Проверяем, есть ли игрок в admins.txt
        if not self._is_in_admins_file(player_name):
            self._send_system_message(client_id, "Вы не в списке администраторов (admins.txt)")
            return

        # Получаем account_uuid
        account_uuid = None
        if hasattr(self.app, 'plugin_manager'):
            dnd_plugin = self.app.plugin_manager.get_plugin("nine.dnd")
            if dnd_plugin:
                for module in dnd_plugin.modules:
                    if hasattr(module, 'authenticated_clients'):
                        account_uuid = module.authenticated_clients.get(client_id)
                        break

        if account_uuid and hasattr(self.app, 'db'):
            success = self.app.db.set_player_role(account_uuid, role)
            if success:
                self._send_system_message(client_id, f"Ваша роль изменена на: {role}")
                self.logger.info(f"Player {player_name} set their role to {role}")
            else:
                self._send_system_message(client_id, "Ошибка изменения роли")
        else:
            # Для dev-клиентов роль устанавливается автоматически
            self._send_system_message(client_id, f"Dev-клиент: роль автоматически admin")

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

    # =========================================================================
    # GM/DM боевые команды - обработчики
    # =========================================================================

    def _get_combat_manager(self):
        """Получает CombatManager из плагина боя."""
        if hasattr(self.app, 'plugin_manager'):
            combat_plugin = self.app.plugin_manager.get_plugin("nine.combat")
            if combat_plugin:
                for module in combat_plugin.modules:
                    if hasattr(module, 'combat_manager'):
                        return module.combat_manager
                    if module.__class__.__name__ == 'CombatManager':
                        return module
        return None

    def _get_player_position(self, client_id: int) -> Optional[List[float]]:
        """Получает позицию игрока."""
        if hasattr(self.app, 'world'):
            player = self.app.world.players.get(client_id)
            if player:
                state = player.get_state()
                return state.get("pos", [0, 0, 0])
        return None

    # =========================================================================
    # Обработчики команд NPC
    # =========================================================================

    def _handle_spawnnpc(self, client_id: int, player_name: str, template: str, coords=None):
        """Обрабатывает /spawnnpc - спавнит NPC."""
        self.logger.info(f"[SPAWNNPC] Запрос от {player_name}: template={template}, coords={coords}")

        # Получаем позицию игрока если координаты не указаны
        if coords is None:
            coords = self._get_player_position(client_id)
            self.logger.info(f"[SPAWNNPC] Получена позиция игрока: {coords}")
            if not coords:
                self._send_system_message(client_id, "Не удалось определить позицию")
                return

        # Преобразуем координаты в нужный формат
        if isinstance(coords, list) and len(coords) >= 3:
            pos_dict = {"x": coords[0], "y": coords[1], "z": coords[2]}
        else:
            pos_dict = {"x": 0, "y": 0, "z": 1}

        self.logger.info(f"[SPAWNNPC] Отправляем событие dm_npc_spawn: template_id={template}, position={pos_dict}")

        # Отправляем событие в NPC плагин (dm_npc_spawn с правильным форматом)
        self.event_manager.post("dm_npc_spawn", {
            "template_id": template,
            "position": pos_dict,
            "spawner_id": client_id,
        })

        self.logger.info(f"[SPAWNNPC] Событие dm_npc_spawn отправлено")
        self._send_system_message(client_id, f"Спавн NPC '{template}' на позиции X={pos_dict['x']:.1f}, Y={pos_dict['y']:.1f}, Z={pos_dict['z']:.1f}")
        self.logger.info(f"{player_name} spawned NPC {template} at {pos_dict}")

    def _handle_listnpcs(self, client_id: int, player_name: str):
        """Обрабатывает /listnpcs - показывает список активных NPC."""
        if not hasattr(self.app, 'plugin_manager'):
            self._send_system_message(client_id, "Plugin manager не найден")
            return

        npc_plugin = self.app.plugin_manager.get_plugin("nine.npc")
        if not npc_plugin:
            self._send_system_message(client_id, "NPC плагин не загружен")
            return

        # Получаем список NPC
        npcs = []
        for module in npc_plugin.modules:
            if hasattr(module, 'get_all_npcs'):
                npcs = module.get_all_npcs()
                break

        if not npcs:
            self._send_system_message(client_id, "Нет активных NPC")
            return

        # Формируем список
        lines = ["=== Активные NPC ==="]
        for npc in npcs[:20]:  # Максимум 20
            npc_id = npc.get("entity_id", "unknown")
            template = npc.get("template", "unknown")
            pos = npc.get("position", [0, 0, 0])
            lines.append(f"{npc_id}: {template} @ ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})")

        if len(npcs) > 20:
            lines.append(f"... и ещё {len(npcs) - 20} NPC")

        self._send_system_message(client_id, "\n".join(lines))

    def _handle_removenpc(self, client_id: int, player_name: str, entity_id: str):
        """Обрабатывает /removenpc - удаляет NPC."""
        # Отправляем событие в NPC плагин (dm_npc_despawn)
        self.event_manager.post("dm_npc_despawn", {
            "entity_id": entity_id,
            "remover_id": client_id,
        })
        self._send_system_message(client_id, f"Удаление NPC '{entity_id}'")
        self.logger.info(f"{player_name} removed NPC {entity_id}")

    # =========================================================================
    # Обработчики боевых команд
    # =========================================================================

    def _handle_startcombat(self, client_id: int, player_name: str, radius: float):
        """Обрабатывает /startcombat - начинает бой с враждебными NPC в радиусе."""
        combat_manager = self._get_combat_manager()
        if not combat_manager:
            self._send_system_message(client_id, "Боевая система не загружена")
            return

        # Получаем позицию игрока
        player_pos = self._get_player_position(client_id)
        if not player_pos:
            self._send_system_message(client_id, "Не удалось определить позицию игрока")
            return

        # Ищем враждебных NPC в радиусе
        hostile_npcs = []
        if hasattr(self.app, 'plugin_manager'):
            npc_plugin = self.app.plugin_manager.get_plugin("nine.npc")
            if npc_plugin:
                for module in npc_plugin.modules:
                    if hasattr(module, 'get_npcs_in_radius'):
                        npcs = module.get_npcs_in_radius(player_pos, radius)
                        for npc_id, npc_data in npcs.items():
                            # Проверяем враждебность
                            if npc_data.get("is_hostile", False):
                                hostile_npcs.append(npc_id)

        if not hostile_npcs:
            self._send_system_message(client_id, f"Нет враждебных NPC в радиусе {radius} футов")
            return

        # Собираем участников боя (игрок + NPC)
        participants = [str(client_id)] + hostile_npcs

        # Запускаем бой через событие
        self.event_manager.post("dm_start_combat", {
            "initiator_id": str(client_id),
            "participants": participants,
            "forced_by_dm": True,
        })

        self._send_system_message(
            client_id,
            f"Бой начат! Участники: {len(participants)} (враждебных NPC: {len(hostile_npcs)})"
        )
        self.logger.info(f"{player_name} начал бой через /startcombat (радиус {radius})")

    def _handle_endcombat(self, client_id: int, player_name: str):
        """Обрабатывает /endcombat - принудительно завершает текущий бой."""
        combat_manager = self._get_combat_manager()
        if not combat_manager:
            self._send_system_message(client_id, "Боевая система не загружена")
            return

        # Ищем бой, в котором участвует игрок
        combat = None
        if hasattr(combat_manager, 'get_combat_for_entity'):
            combat = combat_manager.get_combat_for_entity(str(client_id))

        if not combat:
            # Пробуем завершить любой активный бой (GM может всё)
            if hasattr(combat_manager, 'active_combats') and combat_manager.active_combats:
                combat_id = next(iter(combat_manager.active_combats.keys()))
                combat = combat_manager.active_combats.get(combat_id)

        if not combat:
            self._send_system_message(client_id, "Нет активного боя для завершения")
            return

        # Завершаем бой через событие
        self.event_manager.post("dm_end_combat", {
            "combat_id": combat.combat_id if hasattr(combat, 'combat_id') else str(combat),
            "reason": "DM_ENDED",
        })

        self._send_system_message(client_id, "Бой принудительно завершён")
        self.logger.info(f"{player_name} завершил бой через /endcombat")

    def _handle_spectator(self, client_id: int, player_name: str):
        """Обрабатывает /spectator - переключает режим спектатора."""
        # Отправляем событие клиенту для переключения режима
        self.event_manager.post("chat_send_to_clients", {
            "data": {
                "type": "dm_command",
                "command": "spectator_toggle",
            },
            "recipients": [client_id]
        })

        # Также постим событие для серверной стороны
        self.event_manager.post("dm_spectator_toggle", {
            "client_id": client_id,
        })

        self._send_system_message(client_id, "Режим спектатора переключён")
        self.logger.info(f"{player_name} переключил режим спектатора")

    def _handle_addtocombat(self, client_id: int, player_name: str, entity_id: str):
        """Обрабатывает /addtocombat - добавляет сущность в текущий бой."""
        combat_manager = self._get_combat_manager()
        if not combat_manager:
            self._send_system_message(client_id, "Боевая система не загружена")
            return

        # Ищем текущий бой игрока
        combat = None
        if hasattr(combat_manager, 'get_combat_for_entity'):
            combat = combat_manager.get_combat_for_entity(str(client_id))

        if not combat:
            self._send_system_message(client_id, "Вы не находитесь в бою")
            return

        # Добавляем сущность через событие
        self.event_manager.post("dm_add_to_combat", {
            "combat_id": combat.combat_id if hasattr(combat, 'combat_id') else str(combat),
            "entity_id": entity_id,
        })

        self._send_system_message(client_id, f"Сущность {entity_id} добавлена в бой")
        self.logger.info(f"{player_name} добавил {entity_id} в бой через /addtocombat")

    def _handle_nextturn(self, client_id: int, player_name: str):
        """Обрабатывает /nextturn - принудительно переходит к следующему ходу."""
        combat_manager = self._get_combat_manager()
        if not combat_manager:
            self._send_system_message(client_id, "Боевая система не загружена")
            return

        # Ищем текущий бой
        combat = None
        if hasattr(combat_manager, 'get_combat_for_entity'):
            combat = combat_manager.get_combat_for_entity(str(client_id))

        if not combat:
            # Пробуем найти любой активный бой
            if hasattr(combat_manager, 'active_combats') and combat_manager.active_combats:
                combat_id = next(iter(combat_manager.active_combats.keys()))
                combat = combat_manager.active_combats.get(combat_id)

        if not combat:
            self._send_system_message(client_id, "Нет активного боя")
            return

        # Переход к следующему ходу через событие
        self.event_manager.post("dm_force_next_turn", {
            "combat_id": combat.combat_id if hasattr(combat, 'combat_id') else str(combat),
        })

        self._send_system_message(client_id, "Принудительный переход к следующему ходу")
        self.logger.info(f"{player_name} использовал /nextturn")

    def _handle_setinit(self, client_id: int, player_name: str, entity_id: str, value: int):
        """Обрабатывает /setinit - устанавливает инициативу сущности."""
        combat_manager = self._get_combat_manager()
        if not combat_manager:
            self._send_system_message(client_id, "Боевая система не загружена")
            return

        # Отправляем событие для изменения инициативы
        self.event_manager.post("dm_set_initiative", {
            "entity_id": entity_id,
            "initiative": value,
        })

        self._send_system_message(client_id, f"Инициатива {entity_id} установлена на {value}")
        self.logger.info(f"{player_name} установил инициативу {entity_id} = {value}")

    # =========================================================================
    # Дебаг команды симулированного боя - обработчики
    # =========================================================================

    def _get_simulated_combat_manager(self):
        """Получает SimulatedCombatManager."""
        if hasattr(self.app, 'simulated_combat') and self.app.simulated_combat:
            return self.app.simulated_combat
        return None

    def _handle_simfights(self, client_id: int):
        """Обрабатывает /simfights — список активных NPC-vs-NPC боёв."""
        sim = self._get_simulated_combat_manager()
        if not sim:
            self._send_system_message(client_id, "SimulatedCombatManager не загружен")
            return

        if not sim.fights:
            self._send_system_message(client_id, "Нет активных симулированных боёв")
            return

        lines = [f"=== Симулированные бои ({len(sim.fights)}) ==="]
        for fight in sim.fights.values():
            living = fight.get_living_participants()
            factions = fight.get_living_factions()
            frozen_tag = " [FROZEN]" if fight.frozen else ""
            lines.append(
                f"Fight {fight.fight_id[:8]}...{frozen_tag} "
                f"| {len(living)}/{len(fight.participants)} alive "
                f"| factions: {', '.join(factions)} "
                f"| center: ({fight.center_x:.1f}, {fight.center_y:.1f})"
            )
            for p in fight.participants.values():
                dead_tag = " [DEAD]" if p.is_dead else ""
                lines.append(
                    f"  {p.name} ({p.faction}) "
                    f"HP: {p.hp_current}/{p.hp_max} "
                    f"AC: {p.armor_class} "
                    f"ATK: +{p.attack_bonus} {p.damage_dice}+{p.damage_bonus}"
                    f"{dead_tag}"
                )

        # Also show overall stats
        stats = sim.get_stats()
        lines.append(
            f"--- Total: {stats['active_fights']} fights, "
            f"{stats['total_living']}/{stats['total_participants']} alive"
        )

        self._send_system_message(client_id, "\n".join(lines))

    def _handle_forcefight(self, client_id: int, player_name: str, template1: str, template2: str):
        """Обрабатывает /forcefight — спавнит двух NPC рядом и сталкивает их."""
        # Get player position
        player_pos = self._get_player_position(client_id)
        if not player_pos:
            self._send_system_message(client_id, "Не удалось определить позицию")
            return

        # Spawn NPC 1 slightly to the left of the player
        pos1 = {"x": player_pos[0] - 3.0, "y": player_pos[1] + 5.0, "z": player_pos[2]}
        # Spawn NPC 2 slightly to the right
        pos2 = {"x": player_pos[0] + 3.0, "y": player_pos[1] + 5.0, "z": player_pos[2]}

        self.event_manager.post("dm_npc_spawn", {
            "template_id": template1,
            "position": pos1,
            "spawner_id": client_id,
        })
        self.event_manager.post("dm_npc_spawn", {
            "template_id": template2,
            "position": pos2,
            "spawner_id": client_id,
        })

        self._send_system_message(
            client_id,
            f"Spawned {template1} and {template2} near you. "
            f"If their factions are hostile, they will fight automatically. "
            f"Use /simfights to monitor. Use /factions to check hostility."
        )
        self.logger.info(f"{player_name} used /forcefight {template1} vs {template2}")

    def _handle_stopsimfight(self, client_id: int, fight_id: str):
        """Обрабатывает /stopsimfight — останавливает симулированный бой."""
        sim = self._get_simulated_combat_manager()
        if not sim:
            self._send_system_message(client_id, "SimulatedCombatManager не загружен")
            return

        if not sim.fights:
            self._send_system_message(client_id, "Нет активных симулированных боёв")
            return

        if fight_id:
            # Find fight by prefix match
            matched = None
            for fid in sim.fights:
                if fid.startswith(fight_id):
                    matched = fid
                    break

            if matched:
                fight = sim.fights[matched]
                sim._end_fight(fight)
                self._send_system_message(client_id, f"Бой {matched[:8]}... остановлен")
            else:
                self._send_system_message(client_id, f"Бой с ID '{fight_id}' не найден")
        else:
            # Stop all fights
            count = len(sim.fights)
            for fight in list(sim.fights.values()):
                sim._end_fight(fight)
            self._send_system_message(client_id, f"Остановлено {count} боёв")

    def _handle_factions(self, client_id: int):
        """Обрабатывает /factions — показывает матрицу враждебности."""
        from nine.plugins.npc.sv_npc_ai import AISystem

        lines = ["=== Faction Hostility Matrix ==="]
        for pair, hostile in AISystem.FACTION_HOSTILITY.items():
            status = "HOSTILE" if hostile else "neutral"
            lines.append(f"  {pair[0]} vs {pair[1]}: {status}")

        lines.append("")
        lines.append("Factions not in the matrix are neutral to each other.")
        lines.append("Players are attacked by NPCs with hostile_to_players=True.")

        self._send_system_message(client_id, "\n".join(lines))

    # =========================================================================
    # GM/DM аудио команды - обработчики
    # =========================================================================

    def _handle_music_command(self, client_id: int, player_name: str, args: list):
        """
        Обрабатывает /music команды.
        - /music play <playlist> - включить плейлист
        - /music stop [fadeout] - остановить музыку
        - /music track <filename> - включить конкретный трек
        """
        if not args:
            self._send_system_message(
                client_id,
                "Использование: /music play <playlist> | /music stop [fadeout] | /music track <filename>"
            )
            return

        subcommand = args[0]
        subargs = args[1:] if len(args) > 1 else []

        if subcommand == "play":
            # /music play <playlist>
            playlist = subargs[0] if subargs else "adventure"
            valid_playlists = ["adventure", "combat", "catacombs", "city", "dark_forest"]

            if playlist not in valid_playlists:
                self._send_system_message(
                    client_id,
                    f"Доступные плейлисты: {', '.join(valid_playlists)}"
                )
                return

            # Отправляем команду всем клиентам
            self._broadcast_dm_audio_command("music_play", [playlist])
            self._send_system_message(client_id, f"Музыка: плейлист '{playlist}' включен")
            self.logger.info(f"{player_name} включил плейлист {playlist}")

        elif subcommand == "stop":
            # /music stop [fadeout]
            fadeout = float(subargs[0]) if subargs else 2.0
            self._broadcast_dm_audio_command("music_stop", [fadeout])
            self._send_system_message(client_id, f"Музыка остановлена (fadeout: {fadeout}s)")
            self.logger.info(f"{player_name} остановил музыку")

        elif subcommand == "track":
            # /music track <filename>
            if not subargs:
                self._send_system_message(client_id, "Использование: /music track <filename>")
                return

            track = subargs[0]
            self._broadcast_dm_audio_command("music_track", [track])
            self._send_system_message(client_id, f"Музыка: трек '{track}' включен")
            self.logger.info(f"{player_name} включил трек {track}")

        else:
            self._send_system_message(
                client_id,
                "Неизвестная подкоманда. Доступные: play, stop, track"
            )

    def _handle_ambient_command(self, client_id: int, player_name: str, args: list):
        """
        Обрабатывает /ambient команды.
        - /ambient set <zone> - установить эмбиент
        - /ambient stop [fadeout] - остановить эмбиент
        """
        if not args:
            self._send_system_message(
                client_id,
                "Использование: /ambient set <zone> | /ambient stop [fadeout]"
            )
            return

        subcommand = args[0]
        subargs = args[1:] if len(args) > 1 else []

        if subcommand == "set":
            # /ambient set <zone>
            if not subargs:
                valid_ambients = [
                    "beach", "cave", "forest_day", "forest_night",
                    "inside_day", "inside_night", "sea",
                    "beach_rain", "forest_day_rain", "forest_day_storm"
                ]
                self._send_system_message(
                    client_id,
                    f"Использование: /ambient set <zone>\nДоступные: {', '.join(valid_ambients)}"
                )
                return

            zone = subargs[0]
            self._broadcast_dm_audio_command("ambient_set", [zone])
            self._send_system_message(client_id, f"Эмбиент: '{zone}' установлен")
            self.logger.info(f"{player_name} установил эмбиент {zone}")

        elif subcommand == "stop":
            # /ambient stop [fadeout]
            fadeout = float(subargs[0]) if subargs else 2.0
            self._broadcast_dm_audio_command("ambient_stop", [fadeout])
            self._send_system_message(client_id, f"Эмбиент остановлен (fadeout: {fadeout}s)")
            self.logger.info(f"{player_name} остановил эмбиент")

        else:
            self._send_system_message(
                client_id,
                "Неизвестная подкоманда. Доступные: set, stop"
            )

    def _handle_sfx_command(self, client_id: int, player_name: str, args: list):
        """
        Обрабатывает /sfx команды.
        - /sfx play <sound> - воспроизвести звуковой эффект
        """
        if not args:
            self._send_system_message(
                client_id,
                "Использование: /sfx play <sound>"
            )
            return

        subcommand = args[0]
        subargs = args[1:] if len(args) > 1 else []

        if subcommand == "play":
            if not subargs:
                valid_sfx = [
                    "sword_attack", "sword_hit", "sword_blocked",
                    "bow_draw", "bow_release", "arrow_hit",
                    "door_open", "door_close", "chest_open",
                    "sword_unsheath", "sword_sheath"
                ]
                self._send_system_message(
                    client_id,
                    f"Использование: /sfx play <sound>\nДоступные: {', '.join(valid_sfx)}"
                )
                return

            sound = subargs[0]
            self._broadcast_dm_audio_command("sfx_play", [sound])
            self._send_system_message(client_id, f"SFX: '{sound}' воспроизведен")
            self.logger.info(f"{player_name} воспроизвел SFX {sound}")

        else:
            self._send_system_message(
                client_id,
                "Неизвестная подкоманда. Доступные: play"
            )

    def _handle_volume_command(self, client_id: int, player_name: str, args: list):
        """
        Обрабатывает /volume команды.
        - /volume master <0-100> - установить общую громкость
        """
        if len(args) < 2:
            self._send_system_message(
                client_id,
                "Использование: /volume master <0-100>"
            )
            return

        channel = args[0]
        value = args[1]

        if channel == "master":
            if not (0 <= value <= 100):
                self._send_system_message(client_id, "Значение должно быть от 0 до 100")
                return

            self._broadcast_dm_audio_command("volume_master", [value])
            self._send_system_message(client_id, f"Громкость: master = {value}%")
            self.logger.info(f"{player_name} установил громкость {value}%")

        else:
            self._send_system_message(
                client_id,
                "Неизвестный канал. Доступные: master"
            )

    def _broadcast_dm_audio_command(self, command: str, args: list):
        """
        Отправляет DM аудио команду всем клиентам.
        Клиенты обрабатывают команду через AudioIntegration._on_dm_audio_command().
        """
        self.event_manager.post("chat_send_to_clients", {
            "data": {
                "type": "dm_audio_command",
                "command": command,
                "args": args,
            },
            "recipients": None  # Всем клиентам
        })
