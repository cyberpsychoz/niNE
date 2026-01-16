"""
Серверные системы для Living World NPC.

Включает:
- NeedsSystem - управление потребностями
- ScheduleSystem - выполнение расписания
- RelationshipSystem - изменение отношений
- MemorySystem - запись и забывание событий
"""

import random
from datetime import datetime
from typing import Dict, List, Optional, Any

from nine.core.plugins import PluginModule
from .sh_living_components import (
    NeedsComponent, PersonalityComponent, RelationshipsComponent,
    MemoryComponent, ScheduleComponent, Memory, ScheduleEntry,
    Activity, MemoryType
)


class LivingSystemsServerModule(PluginModule):
    """
    Серверный модуль систем Living World NPC.
    """

    def on_load(self):
        # Компоненты NPC
        # npc_id -> components dict
        self._npc_components: Dict[str, Dict[str, Any]] = {}

        # Текущий игровой час (0-23)
        self._current_hour: int = 8

        # Подписки на события
        self.event_manager.subscribe("npc_spawned", self._on_npc_spawned)
        self.event_manager.subscribe("npc_despawned", self._on_npc_despawned)
        self.event_manager.subscribe("game_tick", self._on_game_tick)
        self.event_manager.subscribe("game_hour_changed", self._on_hour_changed)

        # События взаимодействия
        self.event_manager.subscribe("player_interacted_npc", self._on_player_interaction)
        self.event_manager.subscribe("player_attacked_npc", self._on_player_attacked_npc)
        self.event_manager.subscribe("player_gave_item_npc", self._on_player_gave_item)
        self.event_manager.subscribe("npc_witnessed_event", self._on_npc_witnessed)

        # Запросы состояния
        self.event_manager.subscribe("npc_relationship_request", self._on_relationship_request)
        self.event_manager.subscribe("npc_needs_request", self._on_needs_request)

        self.logger.info("Living Systems серверный модуль загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("npc_spawned", self._on_npc_spawned)
        self.event_manager.unsubscribe("npc_despawned", self._on_npc_despawned)
        self.event_manager.unsubscribe("game_tick", self._on_game_tick)
        self.event_manager.unsubscribe("game_hour_changed", self._on_hour_changed)
        self.event_manager.unsubscribe("player_interacted_npc", self._on_player_interaction)
        self.event_manager.unsubscribe("player_attacked_npc", self._on_player_attacked_npc)
        self.event_manager.unsubscribe("player_gave_item_npc", self._on_player_gave_item)
        self.event_manager.unsubscribe("npc_witnessed_event", self._on_npc_witnessed)
        self.event_manager.unsubscribe("npc_relationship_request", self._on_relationship_request)
        self.event_manager.unsubscribe("npc_needs_request", self._on_needs_request)

        self.logger.info("Living Systems серверный модуль выгружен")

    # =========================================================================
    # NPC Lifecycle
    # =========================================================================

    def _on_npc_spawned(self, data: dict):
        """NPC появился - инициализируем компоненты."""
        npc_id = data.get("npc_id", "")
        template_data = data.get("template_data", {})
        living_data = template_data.get("living", {})

        if not npc_id:
            return

        # Создаём компоненты
        components = {}

        # Needs
        if living_data.get("has_needs", False):
            needs_data = living_data.get("needs", {})
            components["needs"] = NeedsComponent(
                hunger=needs_data.get("hunger", 100.0),
                energy=needs_data.get("energy", 100.0),
                social=needs_data.get("social", 50.0),
            )

        # Personality
        if living_data.get("has_personality", False):
            personality_data = living_data.get("personality", {})
            components["personality"] = PersonalityComponent(
                traits=personality_data.get("traits", []),
                chattiness=personality_data.get("chattiness", 0.5),
                aggression=personality_data.get("aggression", 0.3),
                curiosity=personality_data.get("curiosity", 0.5),
                kindness=personality_data.get("kindness", 0.5),
                courage=personality_data.get("courage", 0.5),
            )

        # Relationships
        if living_data.get("has_relationships", True):
            rel_data = living_data.get("relationships", {})
            components["relationships"] = RelationshipsComponent(
                default_disposition=rel_data.get("default_disposition", 50.0),
                default_trust=rel_data.get("default_trust", 30.0),
            )

        # Memory
        if living_data.get("has_memory", True):
            mem_data = living_data.get("memory", {})
            components["memory"] = MemoryComponent(
                max_memories=mem_data.get("max_memories", 50),
            )

        # Schedule
        if living_data.get("has_schedule", False):
            schedule_data = living_data.get("schedule", [])
            schedule = ScheduleComponent()
            for entry_data in schedule_data:
                entry = ScheduleEntry(
                    hour_start=entry_data.get("hour_start", 0),
                    hour_end=entry_data.get("hour_end", 24),
                    activity=entry_data.get("activity", "idle"),
                    location=entry_data.get("location"),
                    location_id=entry_data.get("location_id"),
                    priority=entry_data.get("priority", 1),
                )
                schedule.add_entry(entry)
            components["schedule"] = schedule

        self._npc_components[npc_id] = components
        self.logger.debug(f"Initialized living components for NPC {npc_id}")

    def _on_npc_despawned(self, data: dict):
        """NPC исчез - удаляем компоненты."""
        npc_id = data.get("npc_id", "")
        if npc_id in self._npc_components:
            del self._npc_components[npc_id]

    # =========================================================================
    # Time Processing
    # =========================================================================

    def _on_game_tick(self, data: dict):
        """Игровой тик - обновляем системы."""
        delta_hours = data.get("delta_hours", 0.01)

        for npc_id, components in self._npc_components.items():
            # Update needs
            needs = components.get("needs")
            if needs:
                self._update_needs(npc_id, needs, delta_hours)

            # Decay memories
            memory = components.get("memory")
            if memory:
                memory.decay_memories(delta_hours * 0.001)

    def _on_hour_changed(self, data: dict):
        """Сменился игровой час - проверяем расписания."""
        self._current_hour = data.get("hour", 0)

        for npc_id, components in self._npc_components.items():
            schedule = components.get("schedule")
            if schedule:
                self._process_schedule(npc_id, schedule)

    def _update_needs(self, npc_id: str, needs: NeedsComponent, delta_hours: float):
        """Обновляет потребности NPC."""
        schedule = self._npc_components[npc_id].get("schedule")
        is_sleeping = schedule and schedule.current_activity == "sleeping"

        needs.update(delta_hours, is_active=not is_sleeping)

        # Если потребность критическая - меняем поведение
        if needs.is_critical:
            urgent = needs.most_urgent_need
            self.event_manager.post("npc_urgent_need", {
                "npc_id": npc_id,
                "need": urgent,
                "value": getattr(needs, urgent),
            })

    def _process_schedule(self, npc_id: str, schedule: ScheduleComponent):
        """Обрабатывает расписание NPC."""
        entry = schedule.get_activity_for_hour(self._current_hour)

        if not entry:
            new_activity = "idle"
            target_location = None
        else:
            new_activity = entry.activity
            target_location = entry.location

        # Шанс отклониться от расписания
        if random.random() < schedule.deviation_chance:
            needs = self._npc_components[npc_id].get("needs")
            if needs and needs.is_critical:
                # Приоритет потребностям
                urgent = needs.most_urgent_need
                if urgent == "hunger":
                    new_activity = "eating"
                elif urgent == "energy":
                    new_activity = "sleeping"
                elif urgent == "social":
                    new_activity = "socializing"

        if new_activity != schedule.current_activity:
            schedule.current_activity = new_activity

            self.event_manager.post("npc_activity_changed", {
                "npc_id": npc_id,
                "activity": new_activity,
                "target_location": target_location,
            })

            self.logger.debug(f"NPC {npc_id} activity changed to {new_activity}")

    # =========================================================================
    # Player Interactions
    # =========================================================================

    def _on_player_interaction(self, data: dict):
        """Игрок взаимодействовал с NPC."""
        npc_id = data.get("npc_id", "")
        player_id = data.get("player_id", "")
        interaction_type = data.get("interaction_type", "talk")

        components = self._npc_components.get(npc_id, {})

        # Обновляем отношения
        relationships = components.get("relationships")
        if relationships:
            # Обычное взаимодействие слегка улучшает отношения
            relationships.modify_disposition(player_id, 1.0)
            relationships.get_relationship(player_id).last_interaction = datetime.now().isoformat()

        # Обновляем потребности
        needs = components.get("needs")
        if needs and interaction_type == "talk":
            needs.socialize(0.5)

        # Записываем в память
        memory = components.get("memory")
        if memory:
            memory.add_memory(Memory(
                memory_type=MemoryType.CONVERSATION.value,
                entity_id=player_id,
                importance=0.3,
                timestamp=datetime.now().isoformat(),
            ))

    def _on_player_attacked_npc(self, data: dict):
        """Игрок атаковал NPC."""
        npc_id = data.get("npc_id", "")
        player_id = data.get("player_id", "")
        damage = data.get("damage", 0)

        components = self._npc_components.get(npc_id, {})

        # Сильно ухудшаем отношения
        relationships = components.get("relationships")
        if relationships:
            penalty = -20 - (damage * 0.5)
            relationships.modify_disposition(player_id, penalty)
            relationships.modify_trust(player_id, -30)

        # Записываем важное воспоминание
        memory = components.get("memory")
        if memory:
            memory.add_memory(Memory(
                memory_type=MemoryType.PLAYER_ATTACKED.value,
                entity_id=player_id,
                importance=0.9,  # Очень важное воспоминание
                timestamp=datetime.now().isoformat(),
                details={"damage": damage},
            ))

        # Уменьшаем чувство безопасности
        needs = components.get("needs")
        if needs:
            needs.safety = max(0, needs.safety - 30)

        self.logger.info(f"NPC {npc_id} was attacked by player {player_id}")

    def _on_player_gave_item(self, data: dict):
        """Игрок дал предмет NPC."""
        npc_id = data.get("npc_id", "")
        player_id = data.get("player_id", "")
        item_id = data.get("item_id", "")
        item_value = data.get("value", 10)

        components = self._npc_components.get(npc_id, {})

        # Улучшаем отношения в зависимости от ценности подарка
        relationships = components.get("relationships")
        if relationships:
            bonus = 5 + (item_value * 0.1)

            # Учитываем личность
            personality = components.get("personality")
            if personality:
                bonus *= (1 + personality.kindness)
                if personality.has_trait("greedy"):
                    bonus *= 1.5

            relationships.modify_disposition(player_id, bonus)
            relationships.modify_trust(player_id, bonus * 0.5)

        # Записываем в память
        memory = components.get("memory")
        if memory:
            memory.add_memory(Memory(
                memory_type=MemoryType.RECEIVED_GIFT.value,
                entity_id=player_id,
                importance=0.6,
                timestamp=datetime.now().isoformat(),
                details={"item_id": item_id, "value": item_value},
            ))

        self.logger.info(f"NPC {npc_id} received gift from player {player_id}")

    def _on_npc_witnessed(self, data: dict):
        """NPC стал свидетелем события."""
        npc_id = data.get("npc_id", "")
        event_type = data.get("event_type", "")
        actor_id = data.get("actor_id", "")
        details = data.get("details", {})

        components = self._npc_components.get(npc_id, {})

        # Записываем в память
        memory = components.get("memory")
        if memory:
            importance = 0.5
            if event_type == "crime":
                importance = 0.8
            elif event_type == "heroic":
                importance = 0.7

            memory.add_memory(Memory(
                memory_type=event_type,
                entity_id=actor_id,
                importance=importance,
                timestamp=datetime.now().isoformat(),
                details=details,
            ))

        # Изменяем отношение к актору
        relationships = components.get("relationships")
        if relationships:
            if event_type == "crime":
                relationships.modify_disposition(actor_id, -15)
            elif event_type == "heroic":
                relationships.modify_disposition(actor_id, 10)

    # =========================================================================
    # State Requests
    # =========================================================================

    def _on_relationship_request(self, data: dict):
        """Запрос отношения NPC к сущности."""
        client_id = data.get("client_id", -1)
        npc_id = data.get("npc_id", "")
        target_id = data.get("target_id", "")

        components = self._npc_components.get(npc_id, {})
        relationships = components.get("relationships")

        if relationships:
            rel = relationships.get_relationship(target_id)
            self._send_to_client(client_id, {
                "type": "npc_relationship",
                "npc_id": npc_id,
                "target_id": target_id,
                "disposition": rel.disposition,
                "trust": rel.trust,
                "familiarity": rel.familiarity,
                "relationship_level": rel.relationship_level,
            })

    def _on_needs_request(self, data: dict):
        """Запрос потребностей NPC (для DM)."""
        client_id = data.get("client_id", -1)
        npc_id = data.get("npc_id", "")

        components = self._npc_components.get(npc_id, {})
        needs = components.get("needs")

        if needs:
            self._send_to_client(client_id, {
                "type": "npc_needs",
                "npc_id": npc_id,
                "hunger": needs.hunger,
                "energy": needs.energy,
                "social": needs.social,
                "safety": needs.safety,
                "most_urgent": needs.most_urgent_need,
            })

    # =========================================================================
    # Helpers
    # =========================================================================

    def _send_to_client(self, client_id: int, message: dict):
        """Отправляет сообщение клиенту."""
        if hasattr(self.app, 'send_to_client'):
            self.app.send_to_client(client_id, message)
        else:
            self.event_manager.post(f"send_to_client_{client_id}", message)

    # =========================================================================
    # Public API
    # =========================================================================

    def get_npc_disposition(self, npc_id: str, target_id: str) -> float:
        """Возвращает отношение NPC к сущности."""
        components = self._npc_components.get(npc_id, {})
        relationships = components.get("relationships")
        if relationships:
            return relationships.get_disposition(target_id)
        return 50.0

    def is_npc_hostile_to(self, npc_id: str, target_id: str) -> bool:
        """Проверяет, враждебен ли NPC к сущности."""
        components = self._npc_components.get(npc_id, {})
        relationships = components.get("relationships")
        if relationships:
            return relationships.is_hostile_to(target_id)
        return False

    def get_npc_activity(self, npc_id: str) -> str:
        """Возвращает текущую активность NPC."""
        components = self._npc_components.get(npc_id, {})
        schedule = components.get("schedule")
        if schedule:
            return schedule.current_activity
        return "idle"

    def npc_remembers(self, npc_id: str, entity_id: str, memory_type: str) -> bool:
        """Проверяет, помнит ли NPC событие."""
        components = self._npc_components.get(npc_id, {})
        memory = components.get("memory")
        if memory:
            return memory.has_memory_of(entity_id, memory_type)
        return False
