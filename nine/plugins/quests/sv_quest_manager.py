"""
Серверный модуль управления квестами.

Обрабатывает:
- Принятие/сдачу квестов
- Трекинг прогресса целей
- Выдачу наград
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from nine.core.plugins import PluginModule
from nine.plugins.quests.sh_quest_data import Quest, QuestObjective, QuestReward, PlayerQuestState, QuestStatus


class QuestManagerServerModule(PluginModule):
    """
    Серверный модуль управления квестами.
    """

    def on_load(self):
        # Данные квестов
        self._quests: Dict[str, Quest] = {}

        # Состояния квестов игроков
        # client_id -> {quest_id -> PlayerQuestState}
        self._player_quests: Dict[int, Dict[str, PlayerQuestState]] = {}

        # Загружаем данные квестов
        self._load_quests_data()

        # Подписки на события
        self.event_manager.subscribe("quest_list_request", self._on_quest_list_request)
        self.event_manager.subscribe("quest_accept", self._on_quest_accept)
        self.event_manager.subscribe("quest_abandon", self._on_quest_abandon)
        self.event_manager.subscribe("quest_turn_in", self._on_quest_turn_in)

        # Игровые события для трекинга прогресса
        self.event_manager.subscribe("entity_killed", self._on_entity_killed)
        self.event_manager.subscribe("item_collected", self._on_item_collected)
        self.event_manager.subscribe("npc_talked", self._on_npc_talked)
        self.event_manager.subscribe("location_reached", self._on_location_reached)
        self.event_manager.subscribe("object_interacted", self._on_object_interacted)

        # Управление игроками
        self.event_manager.subscribe("player_authenticated", self._on_player_authenticated)
        self.event_manager.subscribe("player_left", self._on_player_left)

        self.logger.info("Quest Manager серверный модуль загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("quest_list_request", self._on_quest_list_request)
        self.event_manager.unsubscribe("quest_accept", self._on_quest_accept)
        self.event_manager.unsubscribe("quest_abandon", self._on_quest_abandon)
        self.event_manager.unsubscribe("quest_turn_in", self._on_quest_turn_in)
        self.event_manager.unsubscribe("entity_killed", self._on_entity_killed)
        self.event_manager.unsubscribe("item_collected", self._on_item_collected)
        self.event_manager.unsubscribe("npc_talked", self._on_npc_talked)
        self.event_manager.unsubscribe("location_reached", self._on_location_reached)
        self.event_manager.unsubscribe("object_interacted", self._on_object_interacted)
        self.event_manager.unsubscribe("player_authenticated", self._on_player_authenticated)
        self.event_manager.unsubscribe("player_left", self._on_player_left)

        self.logger.info("Quest Manager серверный модуль выгружен")

    # =========================================================================
    # Data Loading
    # =========================================================================

    def _load_quests_data(self):
        """Загружает данные квестов из JSON."""
        quests_path = Path(__file__).parent / "data" / "quests.json"

        try:
            with open(quests_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for quest_data in data.get("quests", []):
                quest = self._parse_quest(quest_data)
                self._quests[quest.id] = quest

            self.logger.info(f"Загружено {len(self._quests)} квестов")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки квестов: {e}")

    def _parse_quest(self, data: dict) -> Quest:
        """Парсит данные квеста из JSON."""
        objectives = []
        for obj_data in data.get("objectives", []):
            obj = QuestObjective(
                id=obj_data.get("id", ""),
                type=obj_data.get("type", ""),
                description=obj_data.get("description", ""),
                description_ru=obj_data.get("description_ru", ""),
                target_id=obj_data.get("target_id", ""),
                target_count=obj_data.get("target_count", 1),
                location=obj_data.get("location"),
                radius=obj_data.get("radius", 5.0),
                hidden=obj_data.get("hidden", False),
                optional=obj_data.get("optional", False),
            )
            objectives.append(obj)

        rewards_data = data.get("rewards", {})
        rewards = QuestReward(
            experience=rewards_data.get("experience", 0),
            gold=rewards_data.get("gold", 0),
            items=rewards_data.get("items", []),
            reputation=rewards_data.get("reputation", {}),
        )

        return Quest(
            id=data.get("id", ""),
            name=data.get("name", ""),
            name_ru=data.get("name_ru", ""),
            description=data.get("description", ""),
            description_ru=data.get("description_ru", ""),
            level_requirement=data.get("level_requirement", 1),
            repeatable=data.get("repeatable", False),
            chain_id=data.get("chain_id"),
            chain_order=data.get("chain_order", 0),
            giver_npc_id=data.get("giver_npc_id", ""),
            turn_in_npc_id=data.get("turn_in_npc_id", "") or data.get("giver_npc_id", ""),
            objectives=objectives,
            rewards=rewards,
            prerequisites=data.get("prerequisites", []),
            required_class=data.get("required_class"),
            required_faction=data.get("required_faction"),
            dialog_accept=data.get("dialog_accept", ""),
            dialog_progress=data.get("dialog_progress", ""),
            dialog_complete=data.get("dialog_complete", ""),
        )

    # =========================================================================
    # Player Management
    # =========================================================================

    def _on_player_authenticated(self, data: dict):
        """Игрок авторизовался - загружаем его квесты."""
        client_id = data.get("client_id", -1)
        character_data = data.get("character_data", {})

        if client_id < 0:
            return

        # Загружаем сохранённые квесты
        quests_data = character_data.get("quests", {})
        self._player_quests[client_id] = {}

        for quest_id, state_data in quests_data.items():
            state = PlayerQuestState(
                quest_id=quest_id,
                status=state_data.get("status", "active"),
                objectives_progress=state_data.get("objectives_progress", {}),
                accepted_at=state_data.get("accepted_at"),
                completed_at=state_data.get("completed_at"),
            )
            self._player_quests[client_id][quest_id] = state

        self.logger.info(f"Загружено {len(self._player_quests[client_id])} квестов для клиента {client_id}")

    def _on_player_left(self, data: dict):
        """Игрок вышел - сохраняем квесты."""
        client_id = data.get("client_id", -1)
        if client_id in self._player_quests:
            # Данные должны быть сохранены через character_data
            del self._player_quests[client_id]

    # =========================================================================
    # Quest List
    # =========================================================================

    def _on_quest_list_request(self, data: dict):
        """Запрос списка квестов."""
        client_id = data.get("client_id", -1)
        filter_type = data.get("filter", "active")  # active, available, completed, all

        player_quests = self._player_quests.get(client_id, {})
        player_level = self._get_player_level(client_id)

        quest_list = []

        for quest_id, quest in self._quests.items():
            state = player_quests.get(quest_id)

            # Применяем фильтр
            if filter_type == "active":
                if not state or state.status != "active":
                    continue
            elif filter_type == "available":
                if state and state.status in ("active", "turned_in"):
                    continue
                if not self._can_accept_quest(client_id, quest):
                    continue
            elif filter_type == "completed":
                if not state or state.status not in ("completed", "turned_in"):
                    continue

            # Формируем данные квеста
            quest_data = {
                "id": quest.id,
                "name": quest.name,
                "name_ru": quest.name_ru,
                "description": quest.description,
                "description_ru": quest.description_ru,
                "level_requirement": quest.level_requirement,
                "status": state.status if state else "available",
                "objectives": [],
                "rewards": {
                    "experience": quest.rewards.experience,
                    "gold": quest.rewards.gold,
                    "items": quest.rewards.items,
                },
            }

            # Добавляем цели с прогрессом
            for obj in quest.objectives:
                if obj.hidden and state and state.get_progress(obj.id) == 0:
                    continue  # Скрываем скрытые невыполненные цели

                obj_data = {
                    "id": obj.id,
                    "description": obj.description,
                    "description_ru": obj.description_ru,
                    "type": obj.type,
                    "target_count": obj.target_count,
                    "current_count": state.get_progress(obj.id) if state else 0,
                    "optional": obj.optional,
                }
                quest_data["objectives"].append(obj_data)

            quest_list.append(quest_data)

        self._send_to_client(client_id, {
            "type": "quest_list",
            "filter": filter_type,
            "quests": quest_list,
        })

    # =========================================================================
    # Quest Actions
    # =========================================================================

    def _on_quest_accept(self, data: dict):
        """Принятие квеста."""
        client_id = data.get("client_id", -1)
        quest_id = data.get("quest_id", "")

        quest = self._quests.get(quest_id)
        if not quest:
            self._send_quest_result(client_id, False, "Quest not found")
            return

        if not self._can_accept_quest(client_id, quest):
            self._send_quest_result(client_id, False, "Cannot accept this quest")
            return

        # Создаём состояние квеста
        state = PlayerQuestState(
            quest_id=quest_id,
            status="active",
            objectives_progress={obj.id: 0 for obj in quest.objectives},
            accepted_at=datetime.now().isoformat(),
        )

        if client_id not in self._player_quests:
            self._player_quests[client_id] = {}

        self._player_quests[client_id][quest_id] = state

        self.logger.info(f"Client {client_id} accepted quest {quest_id}")

        # Отправляем подтверждение
        self._send_to_client(client_id, {
            "type": "quest_accepted",
            "quest_id": quest_id,
            "quest_name": quest.name,
            "dialog": quest.dialog_accept,
        })

        # Публикуем событие
        self.event_manager.post("quest_accepted", {
            "client_id": client_id,
            "quest_id": quest_id,
        })

    def _on_quest_abandon(self, data: dict):
        """Отказ от квеста."""
        client_id = data.get("client_id", -1)
        quest_id = data.get("quest_id", "")

        player_quests = self._player_quests.get(client_id, {})
        state = player_quests.get(quest_id)

        if not state or state.status != "active":
            return

        del self._player_quests[client_id][quest_id]

        self.logger.info(f"Client {client_id} abandoned quest {quest_id}")

        self._send_to_client(client_id, {
            "type": "quest_abandoned",
            "quest_id": quest_id,
        })

    def _on_quest_turn_in(self, data: dict):
        """Сдача квеста."""
        client_id = data.get("client_id", -1)
        quest_id = data.get("quest_id", "")

        quest = self._quests.get(quest_id)
        if not quest:
            return

        player_quests = self._player_quests.get(client_id, {})
        state = player_quests.get(quest_id)

        if not state or state.status not in ("active", "completed"):
            return

        # Проверяем выполнение целей
        if not self._check_quest_complete(quest, state):
            self._send_to_client(client_id, {
                "type": "quest_turn_in_failed",
                "quest_id": quest_id,
                "reason": "Objectives not complete",
                "dialog": quest.dialog_progress,
            })
            return

        # Выдаём награды
        self._give_rewards(client_id, quest.rewards)

        # Обновляем статус
        state.status = "turned_in"
        state.completed_at = datetime.now().isoformat()

        self.logger.info(f"Client {client_id} completed quest {quest_id}")

        self._send_to_client(client_id, {
            "type": "quest_completed",
            "quest_id": quest_id,
            "quest_name": quest.name,
            "rewards": {
                "experience": quest.rewards.experience,
                "gold": quest.rewards.gold,
                "items": quest.rewards.items,
            },
            "dialog": quest.dialog_complete,
        })

        # Публикуем событие
        self.event_manager.post("quest_completed", {
            "client_id": client_id,
            "quest_id": quest_id,
        })

    # =========================================================================
    # Progress Tracking
    # =========================================================================

    def _on_entity_killed(self, data: dict):
        """Убито существо."""
        killer_id = data.get("killer_id")
        entity_type = data.get("entity_type", "")

        try:
            client_id = int(killer_id)
        except (ValueError, TypeError):
            return

        self._update_objective_progress(client_id, "kill", entity_type)

    def _on_item_collected(self, data: dict):
        """Собран предмет."""
        client_id = data.get("client_id", -1)
        item_id = data.get("item_id", "")

        self._update_objective_progress(client_id, "collect", item_id)

    def _on_npc_talked(self, data: dict):
        """Разговор с NPC."""
        client_id = data.get("client_id", -1)
        npc_id = data.get("npc_id", "")

        self._update_objective_progress(client_id, "talk", npc_id)

    def _on_location_reached(self, data: dict):
        """Достигнута локация."""
        client_id = data.get("client_id", -1)
        location_id = data.get("location_id", "")

        self._update_objective_progress(client_id, "reach_location", location_id)

    def _on_object_interacted(self, data: dict):
        """Взаимодействие с объектом."""
        client_id = data.get("client_id", -1)
        object_id = data.get("object_id", "")

        self._update_objective_progress(client_id, "interact", object_id)

    def _update_objective_progress(self, client_id: int, obj_type: str, target_id: str):
        """Обновляет прогресс целей квестов."""
        player_quests = self._player_quests.get(client_id, {})

        for quest_id, state in player_quests.items():
            if state.status != "active":
                continue

            quest = self._quests.get(quest_id)
            if not quest:
                continue

            updated = False
            for obj in quest.objectives:
                if obj.type != obj_type or obj.target_id != target_id:
                    continue

                current = state.get_progress(obj.id)
                if current >= obj.target_count:
                    continue  # Уже выполнено

                new_count = state.increment_progress(obj.id)
                updated = True

                self.logger.info(
                    f"Quest {quest_id} objective {obj.id} progress: "
                    f"{new_count}/{obj.target_count} for client {client_id}"
                )

                # Уведомляем клиента
                self._send_to_client(client_id, {
                    "type": "quest_objective_progress",
                    "quest_id": quest_id,
                    "objective_id": obj.id,
                    "current": new_count,
                    "target": obj.target_count,
                    "description": obj.description,
                })

                # Проверяем завершение цели
                if new_count >= obj.target_count:
                    self._send_to_client(client_id, {
                        "type": "quest_objective_complete",
                        "quest_id": quest_id,
                        "objective_id": obj.id,
                        "description": obj.description,
                    })

            # Проверяем завершение квеста
            if updated and self._check_quest_complete(quest, state):
                state.status = "completed"
                self._send_to_client(client_id, {
                    "type": "quest_ready_to_turn_in",
                    "quest_id": quest_id,
                    "quest_name": quest.name,
                })

    # =========================================================================
    # Helpers
    # =========================================================================

    def _can_accept_quest(self, client_id: int, quest: Quest) -> bool:
        """Проверяет, может ли игрок принять квест."""
        player_quests = self._player_quests.get(client_id, {})

        # Уже есть активный или завершённый этот квест
        state = player_quests.get(quest.id)
        if state:
            if state.status == "active":
                return False
            if state.status == "turned_in" and not quest.repeatable:
                return False

        # Проверка уровня
        player_level = self._get_player_level(client_id)
        if player_level < quest.level_requirement:
            return False

        # Проверка пререквизитов
        for prereq_id in quest.prerequisites:
            prereq_state = player_quests.get(prereq_id)
            if not prereq_state or prereq_state.status != "turned_in":
                return False

        return True

    def _check_quest_complete(self, quest: Quest, state: PlayerQuestState) -> bool:
        """Проверяет, выполнены ли все обязательные цели."""
        for obj in quest.objectives:
            if obj.optional:
                continue
            if state.get_progress(obj.id) < obj.target_count:
                return False
        return True

    def _give_rewards(self, client_id: int, rewards: QuestReward):
        """Выдаёт награды за квест."""
        if rewards.experience > 0:
            self.event_manager.post("give_experience", {
                "client_id": client_id,
                "amount": rewards.experience,
            })

        if rewards.gold > 0:
            self.event_manager.post("give_gold", {
                "client_id": client_id,
                "amount": rewards.gold,
            })

        for item in rewards.items:
            self.event_manager.post("give_item", {
                "client_id": client_id,
                "item_id": item.get("id"),
                "count": item.get("count", 1),
            })

        for faction_id, amount in rewards.reputation.items():
            self.event_manager.post("modify_reputation", {
                "client_id": client_id,
                "faction_id": faction_id,
                "amount": amount,
            })

    def _get_player_level(self, client_id: int) -> int:
        """Получает уровень игрока."""
        if hasattr(self.app, 'authenticated_clients'):
            auth_data = self.app.authenticated_clients.get(client_id, {})
            char_data = auth_data.get("character_data", {})
            return char_data.get("level", 1)
        return 1

    def _send_quest_result(self, client_id: int, success: bool, message: str):
        """Отправляет результат операции с квестом."""
        self._send_to_client(client_id, {
            "type": "quest_result",
            "success": success,
            "message": message,
        })

    def _send_to_client(self, client_id: int, message: dict):
        """Отправляет сообщение клиенту."""
        if hasattr(self.app, 'send_to_client'):
            self.app.send_to_client(client_id, message)
        else:
            self.event_manager.post(f"send_to_client_{client_id}", message)

    # =========================================================================
    # Public API
    # =========================================================================

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Возвращает квест по ID."""
        return self._quests.get(quest_id)

    def get_player_quest_state(self, client_id: int, quest_id: str) -> Optional[PlayerQuestState]:
        """Возвращает состояние квеста игрока."""
        player_quests = self._player_quests.get(client_id, {})
        return player_quests.get(quest_id)

    def get_active_quests(self, client_id: int) -> List[str]:
        """Возвращает список ID активных квестов игрока."""
        player_quests = self._player_quests.get(client_id, {})
        return [qid for qid, state in player_quests.items() if state.status == "active"]
