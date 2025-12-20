"""
Серверный модуль чата.
Обрабатывает RP команды и рассылает сообщения с учётом радиуса.

Поддерживаемые команды:
- /me <действие> - действие от первого лица: "**Имя игрока <действие>"
- /it <текст> - безличное действие: "**<текст>"
- /looc <сообщение> - локальный неигровой чат (с радиусом)
- /ooc <сообщение> - глобальный неигровой чат (без радиуса)
- обычное сообщение - IC чат с радиусом
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


@dataclass
class ParsedMessage:
    """Результат парсинга сообщения."""
    chat_type: ChatType
    content: str


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
