"""
Серверный модуль системы знакомств.

Управляет системой знакомств между персонажами:
- Игроки видят "Незнакомец" для людей, с которыми не знакомы
- Можно представиться через меню курсора (C)
- Игрок выбирает, каким именем представиться
- Описание персонажа видно всегда
"""

from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from nine.core.plugins import PluginModule


@dataclass
class Acquaintance:
    """Информация о знакомстве с другим персонажем."""
    # UUID того, кого мы знаем
    target_uuid: str
    # Имя, которым он представился
    known_name: str
    # Когда познакомились (timestamp)
    met_at: float = 0.0
    # Заметки игрока (опционально)
    notes: str = ""


@dataclass
class PlayerAcquaintances:
    """Список знакомств одного игрока."""
    # {target_uuid: Acquaintance}
    known: Dict[str, Acquaintance] = field(default_factory=dict)

    def knows(self, target_uuid: str) -> bool:
        """Знаком ли игрок с этим персонажем."""
        return target_uuid in self.known

    def get_name_for(self, target_uuid: str) -> Optional[str]:
        """Получить имя, которым представился персонаж."""
        acq = self.known.get(target_uuid)
        if acq:
            return acq.known_name
        return None

    def add(self, target_uuid: str, name: str, timestamp: float = 0.0):
        """Добавить знакомство."""
        self.known[target_uuid] = Acquaintance(
            target_uuid=target_uuid,
            known_name=name,
            met_at=timestamp,
        )

    def update_name(self, target_uuid: str, new_name: str):
        """Обновить имя знакомого (если он представился заново)."""
        if target_uuid in self.known:
            self.known[target_uuid].known_name = new_name

    def to_dict(self) -> dict:
        """Сериализация в словарь."""
        return {
            uuid: {
                "name": acq.known_name,
                "met_at": acq.met_at,
                "notes": acq.notes,
            }
            for uuid, acq in self.known.items()
        }


class AcquaintanceServerModule(PluginModule):
    """
    Серверный модуль системы знакомств.

    Основная логика:
    1. Игрок подходит к другому игроку
    2. Видит "Незнакомец" и описание
    3. Через меню курсора (C) выбирает "Представиться"
    4. Выбирает имя для представления
    5. Другой игрок получает запрос на знакомство
    6. После принятия оба видят имена друг друга

    Особенности:
    - Можно представиться любым именем
    - Можно представиться заново (сменить имя)
    - Описание видно всегда, даже для незнакомцев
    """

    def on_load(self):
        # {player_uuid: PlayerAcquaintances}
        self.acquaintances: Dict[str, PlayerAcquaintances] = {}

        # Ожидающие запросы на знакомство
        # {target_uuid: {requester_uuid: offered_name}}
        self.pending_introductions: Dict[str, Dict[str, str]] = {}

        # Подписки на события
        self.event_manager.subscribe("player_joined", self.on_player_join)
        self.event_manager.subscribe("player_left", self.on_player_leave)
        self.event_manager.subscribe("introduce_request", self.on_introduce_request)
        self.event_manager.subscribe("introduce_accept", self.on_introduce_accept)
        self.event_manager.subscribe("introduce_decline", self.on_introduce_decline)
        self.event_manager.subscribe("request_player_name", self.on_request_player_name)
        self.event_manager.subscribe("character_name_changed", self.on_character_name_changed)
        self.event_manager.subscribe("add_note_to_acquaintance", self.on_add_note)

        self.logger.info("Серверный модуль системы знакомств загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("player_joined", self.on_player_join)
        self.event_manager.unsubscribe("player_left", self.on_player_leave)
        self.event_manager.unsubscribe("introduce_request", self.on_introduce_request)
        self.event_manager.unsubscribe("introduce_accept", self.on_introduce_accept)
        self.event_manager.unsubscribe("introduce_decline", self.on_introduce_decline)
        self.event_manager.unsubscribe("request_player_name", self.on_request_player_name)
        self.event_manager.unsubscribe("character_name_changed", self.on_character_name_changed)
        self.event_manager.unsubscribe("add_note_to_acquaintance", self.on_add_note)

        self.logger.info("Серверный модуль системы знакомств выгружен")

    # =========================================================================
    # Event handlers
    # =========================================================================

    def on_player_join(self, data: dict):
        """Игрок присоединился — загружаем список знакомств."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        # TODO: Загрузить из БД
        self.acquaintances[player_uuid] = PlayerAcquaintances()
        self.pending_introductions[player_uuid] = {}

        self.logger.debug(f"Знакомства игрока {player_uuid} загружены")

    def on_player_leave(self, data: dict):
        """Игрок вышел — сохраняем и очищаем."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        # TODO: Сохранить в БД
        if player_uuid in self.acquaintances:
            del self.acquaintances[player_uuid]
        if player_uuid in self.pending_introductions:
            del self.pending_introductions[player_uuid]

        # Удаляем ожидающие запросы от этого игрока
        for pending in self.pending_introductions.values():
            pending.pop(player_uuid, None)

    def on_introduce_request(self, data: dict):
        """
        Игрок хочет представиться другому.

        data: {
            uuid: str,           # Кто представляется
            target_uuid: str,    # Кому представляется
            name: str,           # Каким именем
        }
        """
        requester_uuid = data.get("uuid")
        target_uuid = data.get("target_uuid")
        offered_name = data.get("name", "").strip()

        if not requester_uuid or not target_uuid or not offered_name:
            return

        if target_uuid not in self.acquaintances:
            self.event_manager.post("system_message_to_client", {
                "client_id": requester_uuid,
                "message": "Этот игрок недоступен.",
            })
            return

        # Ограничиваем длину имени
        offered_name = offered_name[:50]

        # Сохраняем запрос
        if target_uuid not in self.pending_introductions:
            self.pending_introductions[target_uuid] = {}
        self.pending_introductions[target_uuid][requester_uuid] = offered_name

        # Получаем описание представляющегося
        description = self._get_character_description(requester_uuid)

        # Отправляем запрос целевому игроку
        self.event_manager.post("introduction_request_to_client", {
            "client_id": target_uuid,
            "data": {
                "type": "introduction_request",
                "requester_uuid": requester_uuid,
                "offered_name": offered_name,
                "description": description,
            }
        })

        self.logger.debug(
            f"Игрок {requester_uuid} представляется игроку {target_uuid} как '{offered_name}'"
        )

    def on_introduce_accept(self, data: dict):
        """
        Игрок принял представление.

        data: {
            uuid: str,              # Кто принимает
            requester_uuid: str,    # Кто представлялся
            my_name: str,           # Каким именем представиться в ответ
        }
        """
        acceptor_uuid = data.get("uuid")
        requester_uuid = data.get("requester_uuid")
        acceptor_name = data.get("my_name", "").strip()

        if not acceptor_uuid or not requester_uuid or not acceptor_name:
            return

        # Проверяем, есть ли такой запрос
        pending = self.pending_introductions.get(acceptor_uuid, {})
        offered_name = pending.pop(requester_uuid, None)

        if not offered_name:
            return

        import time
        now = time.time()

        # Добавляем взаимное знакомство
        if acceptor_uuid in self.acquaintances:
            self.acquaintances[acceptor_uuid].add(requester_uuid, offered_name, now)

        if requester_uuid in self.acquaintances:
            self.acquaintances[requester_uuid].add(acceptor_uuid, acceptor_name, now)

        # Уведомляем обоих
        self.event_manager.post("introduction_completed_to_client", {
            "client_id": acceptor_uuid,
            "data": {
                "type": "introduction_completed",
                "other_uuid": requester_uuid,
                "other_name": offered_name,
            }
        })

        self.event_manager.post("introduction_completed_to_client", {
            "client_id": requester_uuid,
            "data": {
                "type": "introduction_completed",
                "other_uuid": acceptor_uuid,
                "other_name": acceptor_name,
            }
        })

        self.logger.debug(
            f"Знакомство: {requester_uuid}('{offered_name}') <-> {acceptor_uuid}('{acceptor_name}')"
        )

    def on_introduce_decline(self, data: dict):
        """
        Игрок отклонил представление.

        data: {
            uuid: str,              # Кто отклоняет
            requester_uuid: str,    # Кто представлялся
        }
        """
        decliner_uuid = data.get("uuid")
        requester_uuid = data.get("requester_uuid")

        if not decliner_uuid or not requester_uuid:
            return

        # Удаляем запрос
        pending = self.pending_introductions.get(decliner_uuid, {})
        pending.pop(requester_uuid, None)

        # Уведомляем того, кто представлялся
        self.event_manager.post("introduction_declined_to_client", {
            "client_id": requester_uuid,
            "data": {
                "type": "introduction_declined",
                "target_uuid": decliner_uuid,
            }
        })

    def on_request_player_name(self, data: dict):
        """
        Запрос имени игрока (для отображения над головой).

        data: {
            uuid: str,           # Кто запрашивает
            target_uuid: str,    # Чьё имя нужно
        }
        """
        requester_uuid = data.get("uuid")
        target_uuid = data.get("target_uuid")

        if not requester_uuid or not target_uuid:
            return

        # Определяем, какое имя показать
        name = self.get_displayed_name(requester_uuid, target_uuid)

        self.event_manager.post("player_name_response_to_client", {
            "client_id": requester_uuid,
            "data": {
                "type": "player_name",
                "target_uuid": target_uuid,
                "name": name,
            }
        })

    def on_character_name_changed(self, data: dict):
        """
        Персонаж сменил имя.

        Обновляем имя для всех, кто знает этого персонажа,
        если он представлялся этим именем.
        """
        player_uuid = data.get("uuid")
        old_name = data.get("old_name")
        new_name = data.get("new_name")

        if not player_uuid or not old_name or not new_name:
            return

        # Находим всех, кто знает этого игрока под старым именем
        for other_uuid, acq_list in self.acquaintances.items():
            if other_uuid == player_uuid:
                continue

            acq = acq_list.known.get(player_uuid)
            if acq and acq.known_name == old_name:
                # Обновляем имя
                acq.known_name = new_name

                # Уведомляем клиента
                self.event_manager.post("acquaintance_name_updated_to_client", {
                    "client_id": other_uuid,
                    "data": {
                        "type": "acquaintance_name_updated",
                        "target_uuid": player_uuid,
                        "new_name": new_name,
                    }
                })

    def on_add_note(self, data: dict):
        """
        Добавить заметку о знакомом.

        data: {
            uuid: str,
            target_uuid: str,
            note: str,
        }
        """
        player_uuid = data.get("uuid")
        target_uuid = data.get("target_uuid")
        note = data.get("note", "")

        if not player_uuid or not target_uuid:
            return

        acq_list = self.acquaintances.get(player_uuid)
        if not acq_list:
            return

        acq = acq_list.known.get(target_uuid)
        if not acq:
            return

        # Ограничиваем длину заметки
        acq.notes = note[:500]

    # =========================================================================
    # Helpers
    # =========================================================================

    def _get_character_description(self, player_uuid: str) -> dict:
        """Получить описание персонажа для отображения."""
        # Ищем модуль листа персонажа
        from nine.plugins.inventory.sv_character_sheet import CharacterSheetServerModule

        if hasattr(self.app, 'plugin_manager'):
            for plugin in self.app.plugin_manager.plugins.values():
                for module in plugin.get('modules', {}).values():
                    if isinstance(module, CharacterSheetServerModule):
                        desc = module.get_character_description(player_uuid)
                        if desc:
                            return {
                                "appearance": desc.appearance,
                                "age": desc.age,
                                "build": desc.build,
                                "features": desc.features,
                                "demeanor": desc.demeanor,
                            }

        return {}

    # =========================================================================
    # Public API
    # =========================================================================

    def knows(self, viewer_uuid: str, target_uuid: str) -> bool:
        """Знаком ли viewer с target."""
        acq_list = self.acquaintances.get(viewer_uuid)
        if not acq_list:
            return False
        return acq_list.knows(target_uuid)

    def get_known_name(self, viewer_uuid: str, target_uuid: str) -> Optional[str]:
        """Получить имя, которым target представился viewer."""
        acq_list = self.acquaintances.get(viewer_uuid)
        if not acq_list:
            return None
        return acq_list.get_name_for(target_uuid)

    def get_displayed_name(self, viewer_uuid: str, target_uuid: str) -> str:
        """
        Получить имя для отображения.

        Возвращает имя, если знакомы, или "Незнакомец" если нет.
        """
        # Всегда знаем себя
        if viewer_uuid == target_uuid:
            # Возвращаем настоящее имя персонажа
            return self._get_character_name(target_uuid)

        # Проверяем знакомство
        known_name = self.get_known_name(viewer_uuid, target_uuid)
        if known_name:
            return known_name

        return "Незнакомец"

    def _get_character_name(self, player_uuid: str) -> str:
        """Получить настоящее имя персонажа из модуля листа персонажа."""
        from nine.plugins.inventory.sv_character_sheet import CharacterSheetServerModule

        if hasattr(self.app, 'plugin_manager'):
            for plugin in self.app.plugin_manager.plugins.values():
                for module in plugin.get('modules', {}).values():
                    if isinstance(module, CharacterSheetServerModule):
                        return module.get_character_name(player_uuid)

        return "Игрок"

    def get_all_acquaintances(self, player_uuid: str) -> Dict[str, str]:
        """Получить всех знакомых игрока {uuid: name}."""
        acq_list = self.acquaintances.get(player_uuid)
        if not acq_list:
            return {}

        return {
            uuid: acq.known_name
            for uuid, acq in acq_list.known.items()
        }

    def force_introduce(self, player1_uuid: str, player2_uuid: str, name1: str, name2: str):
        """
        Принудительное знакомство (для GM или системы).

        Оба игрока сразу узнают друг друга.
        """
        import time
        now = time.time()

        if player1_uuid in self.acquaintances:
            self.acquaintances[player1_uuid].add(player2_uuid, name2, now)

        if player2_uuid in self.acquaintances:
            self.acquaintances[player2_uuid].add(player1_uuid, name1, now)

        self.logger.debug(
            f"Принудительное знакомство: {player1_uuid}('{name1}') <-> {player2_uuid}('{name2}')"
        )
