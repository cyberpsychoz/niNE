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

    def _is_admin(self, client_id: int) -> bool:
        """Проверяет, является ли игрок администратором или DM."""
        role = self._get_player_role(client_id)
        return role in ("admin", "dm")

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
            combat_plugin = self.app.plugin_manager.get_plugin("nine.dnd.combat")
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
            npc_plugin = self.app.plugin_manager.get_plugin("nine.dnd.npc")
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
