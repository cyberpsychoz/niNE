"""
Combat Manager - серверный менеджер боевых сессий.
Координирует все пошаговые бои в игре.
"""

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum, auto

from nine.core.plugins import PluginContext
from nine.plugins.combat.sh_dice import DiceRoller


class CombatEndReason(Enum):
    """Причина окончания боя."""
    VICTORY = auto()        # Победа (все враги побеждены)
    DEFEAT = auto()         # Поражение (все союзники побеждены)
    FLED = auto()           # Бегство
    DM_ENDED = auto()       # GM принудительно завершил
    TIMEOUT = auto()        # Таймаут
    CANCELLED = auto()      # Игроки проголосовали за отмену


@dataclass
class CombatParticipant:
    """Участник боя."""
    entity_id: str                      # ID сущности (player client_id или NPC entity_id)
    is_player: bool = False             # Это игрок?
    name: str = ""                      # Отображаемое имя
    faction: str = "neutral"            # Фракция

    # Инициатива
    initiative: int = 0                 # Результат броска
    initiative_modifier: int = 0        # Модификатор (DEX)

    # Характеристики (кешируются при добавлении)
    hp_current: int = 0
    hp_max: int = 0
    armor_class: int = 10
    movement_speed: float = 30.0

    # Экономика действий
    movement_remaining: float = 30.0
    has_action: bool = True
    has_bonus_action: bool = True
    has_reaction: bool = True

    # Состояние
    is_incapacitated: bool = False
    is_dead: bool = False
    conditions: List[str] = field(default_factory=list)

    def roll_initiative(self) -> int:
        """Бросает инициативу."""
        self.initiative, roll = DiceRoller.roll_initiative(self.initiative_modifier)
        return self.initiative

    def reset_turn(self):
        """Сбрасывает ресурсы в начале хода."""
        self.movement_remaining = self.movement_speed
        self.has_action = True
        self.has_bonus_action = True
        self.has_reaction = True


class CombatInstance:
    """
    Одна боевая сессия.
    Управляет участниками, инициативой и ходами.
    """

    def __init__(self, combat_id: str, manager: 'CombatManager'):
        self.combat_id = combat_id
        self.manager = manager

        # Участники
        self.participants: Dict[str, CombatParticipant] = {}
        self.turn_order: List[str] = []  # Отсортировано по инициативе

        # Состояние
        self.round_number: int = 0
        self.current_turn_index: int = -1
        self.is_active: bool = True
        self.is_started: bool = False

        # Центр боя (для определения радиуса)
        self.center_x: float = 0.0
        self.center_y: float = 0.0
        self.center_z: float = 0.0
        self.radius: float = 30.0  # футов

        # Opposing faction pairs (for combat end detection)
        self.opposing_factions: Set[Tuple[str, str]] = set()

        # Vote cancel system
        self.cancel_votes: Set[str] = set()
        self.cancel_timer_task = None

    @property
    def current_participant(self) -> Optional[CombatParticipant]:
        """Возвращает участника, чей сейчас ход."""
        if 0 <= self.current_turn_index < len(self.turn_order):
            entity_id = self.turn_order[self.current_turn_index]
            return self.participants.get(entity_id)
        return None

    def add_participant(self, entity_id: str, is_player: bool, name: str,
                        faction: str, hp_current: int, hp_max: int,
                        armor_class: int, dex_modifier: int,
                        movement_speed: float = 30.0) -> CombatParticipant:
        """Добавляет участника в бой."""
        participant = CombatParticipant(
            entity_id=entity_id,
            is_player=is_player,
            name=name,
            faction=faction,
            hp_current=hp_current,
            hp_max=hp_max,
            armor_class=armor_class,
            initiative_modifier=dex_modifier,
            movement_speed=movement_speed,
            movement_remaining=movement_speed,
        )

        self.participants[entity_id] = participant
        return participant

    def remove_participant(self, entity_id: str):
        """Удаляет участника из боя."""
        if entity_id in self.participants:
            del self.participants[entity_id]
            if entity_id in self.turn_order:
                self.turn_order.remove(entity_id)

    def roll_all_initiative(self):
        """Бросает инициативу для всех участников и сортирует."""
        for participant in self.participants.values():
            participant.roll_initiative()

        # Сортируем по инициативе (больше = раньше), тайбрейкер по DEX
        self.turn_order = sorted(
            self.participants.keys(),
            key=lambda eid: (
                self.participants[eid].initiative,
                self.participants[eid].initiative_modifier
            ),
            reverse=True
        )

    def start_combat(self):
        """Начинает бой."""
        if self.is_started:
            return

        self.is_started = True
        self.round_number = 1
        self.current_turn_index = 0

        # Оповещаем ПЕРЕД первым ходом (клиенты должны узнать о бое до turn_start)
        self.manager.event_manager.post("combat_started", {
            "combat_id": self.combat_id,
            "participants": self._get_participants_data(),
            "turn_order": self.turn_order,
            "round": self.round_number,
        })

        # Log combat start with initiative order
        self.manager._broadcast_combat_log(self, self._format_combat_start_log())

        # Delay first turn by 3s (warmup countdown) — all participants stay frozen
        self.manager.app.taskMgr.doMethodLater(
            3.0, self._delayed_first_turn, f"combat-warmup-{self.combat_id}"
        )

    def _delayed_first_turn(self, task):
        """Start the first turn after warmup countdown."""
        self._start_current_turn()
        return task.done

    def _format_combat_start_log(self) -> str:
        """Format combat start message with initiative order."""
        parts = []
        for eid in self.turn_order:
            p = self.participants.get(eid)
            if p:
                parts.append(f"{p.name} (инициатива {p.initiative})")
        return "Бой начался! Участники: " + ", ".join(parts)

    def advance_turn(self):
        """Переходит к следующему ходу."""
        # Завершаем текущий ход
        self._end_current_turn()

        # Пропускаем мёртвых/недееспособных
        attempts = len(self.turn_order)
        while attempts > 0:
            self.current_turn_index += 1

            # Новый раунд?
            if self.current_turn_index >= len(self.turn_order):
                self.current_turn_index = 0
                self.round_number += 1

                self.manager.event_manager.post("combat_round_start", {
                    "combat_id": self.combat_id,
                    "round": self.round_number,
                })

                # Log new round
                self.manager._broadcast_combat_log(
                    self, f"--- Раунд {self.round_number} ---"
                )

            current = self.current_participant
            if current and not current.is_dead and not current.is_incapacitated:
                break

            attempts -= 1

        # Начинаем новый ход
        self._start_current_turn()

        # Проверяем окончание боя
        end_reason = self.check_combat_end()
        if end_reason:
            self.manager.end_combat(self.combat_id, end_reason)

    def _start_current_turn(self):
        """Начинает ход текущего участника."""
        participant = self.current_participant
        if not participant:
            return

        participant.reset_turn()

        # Log turn start
        self.manager._broadcast_combat_log(self, f"Ход: {participant.name}")

        # Tick conditions
        # TODO: уменьшить длительность состояний

        self.manager.event_manager.post("combat_turn_start", {
            "combat_id": self.combat_id,
            "entity_id": participant.entity_id,
            "entity_name": participant.name,
            "is_player": participant.is_player,
            "round": self.round_number,
            "turn_order": self.turn_order,
            "current_index": self.current_turn_index,
            "resources": {
                "movement": participant.movement_remaining,
                "has_action": participant.has_action,
                "has_bonus_action": participant.has_bonus_action,
                "has_reaction": participant.has_reaction,
            },
        })

    def _end_current_turn(self):
        """Завершает ход текущего участника."""
        participant = self.current_participant
        if not participant:
            return

        self.manager.event_manager.post("combat_turn_end", {
            "combat_id": self.combat_id,
            "entity_id": participant.entity_id,
        })

    def check_combat_end(self) -> Optional[CombatEndReason]:
        """Проверяет, должен ли бой закончиться."""
        alive_factions: Set[str] = set()
        for p in self.participants.values():
            if not p.is_dead:
                alive_factions.add(p.faction)

        # Check if any opposing pair still has both sides alive
        for faction_a, faction_b in self.opposing_factions:
            if faction_a in alive_factions and faction_b in alive_factions:
                return None  # Opposing sides still fighting

        # No active opposition remains — determine outcome
        for p in self.participants.values():
            if p.is_player and not p.is_dead:
                return CombatEndReason.VICTORY
        return CombatEndReason.DEFEAT

    def get_participant(self, entity_id: str) -> Optional[CombatParticipant]:
        """Получает участника по ID."""
        return self.participants.get(entity_id)

    def update_participant_hp(self, entity_id: str, hp: int):
        """Обновляет HP участника."""
        participant = self.participants.get(entity_id)
        if participant:
            participant.hp_current = max(0, hp)
            if participant.hp_current <= 0:
                participant.is_dead = True

    def _get_participants_data(self) -> List[dict]:
        """Возвращает данные участников для сетевой передачи."""
        return [
            {
                "entity_id": p.entity_id,
                "is_player": p.is_player,
                "name": p.name,
                "faction": p.faction,
                "initiative": int(p.initiative),
                "hp_current": p.hp_current,
                "hp_max": p.hp_max,
                "armor_class": p.armor_class,
                "is_dead": p.is_dead,
                "conditions": p.conditions,
            }
            for p in self.participants.values()
        ]

    def recalculate_center(self):
        """Пересчитывает центр боя на основе позиций участников."""
        # TODO: получить позиции из ECS и пересчитать центр
        pass


class CombatManager:
    """
    Менеджер всех боевых сессий.
    Координирует создание, управление и завершение боёв.
    """

    def __init__(self, context: PluginContext):
        self.context = context
        self.app = context.app
        self.logger = context.logger
        self.event_manager = context.event_manager

    def on_load(self):
        self.logger.info("Combat Manager loaded")

        # Активные бои
        self.active_combats: Dict[str, CombatInstance] = {}

        # Маппинги для быстрого поиска
        self.player_combat_map: Dict[int, str] = {}  # client_id -> combat_id
        self.npc_combat_map: Dict[str, str] = {}     # entity_id -> combat_id

        # Cached player positions for auto-join proximity checks
        self._player_positions: List[Dict] = []

        # Cooldown after combat cancel (entity_id -> timestamp)
        self._last_cancelled_at: Dict[str, float] = {}

        # Подписки на события
        self.event_manager.subscribe("npc_aggro_player", self._on_npc_aggro)
        self.event_manager.subscribe("player_attack_request", self._on_player_attack)
        self.event_manager.subscribe("combat_action_request", self._on_action_request)
        self.event_manager.subscribe("combat_end_turn_request", self._on_end_turn_request)
        self.event_manager.subscribe("dm_start_combat", self._on_dm_start_combat)
        self.event_manager.subscribe("dm_end_combat", self._on_dm_end_combat)
        self.event_manager.subscribe("dm_add_to_combat", self._on_dm_add_to_combat)
        self.event_manager.subscribe("dm_force_next_turn", self._on_dm_force_next_turn)
        self.event_manager.subscribe("dm_set_initiative", self._on_dm_set_initiative)
        self.event_manager.subscribe("entity_damaged", self._on_entity_damaged)
        self.event_manager.subscribe("entity_died", self._on_entity_died)
        self.event_manager.subscribe("player_left", self._on_player_left)
        self.event_manager.subscribe("simulated_combat_to_turnbased", self._on_simulated_to_turnbased)
        self.event_manager.subscribe("player_update", self._on_player_update_for_autojoin)
        self.event_manager.subscribe("combat_turn_start", self._on_npc_turn_start)
        self.event_manager.subscribe("combat_action_result", self._on_npc_action_result)
        self.event_manager.subscribe("combat_vote_cancel", self._on_vote_cancel)

    def on_unload(self):
        # Отписываемся
        self.event_manager.unsubscribe("npc_aggro_player", self._on_npc_aggro)
        self.event_manager.unsubscribe("player_attack_request", self._on_player_attack)
        self.event_manager.unsubscribe("combat_action_request", self._on_action_request)
        self.event_manager.unsubscribe("combat_end_turn_request", self._on_end_turn_request)
        self.event_manager.unsubscribe("dm_start_combat", self._on_dm_start_combat)
        self.event_manager.unsubscribe("dm_end_combat", self._on_dm_end_combat)
        self.event_manager.unsubscribe("dm_add_to_combat", self._on_dm_add_to_combat)
        self.event_manager.unsubscribe("dm_force_next_turn", self._on_dm_force_next_turn)
        self.event_manager.unsubscribe("dm_set_initiative", self._on_dm_set_initiative)
        self.event_manager.unsubscribe("entity_damaged", self._on_entity_damaged)
        self.event_manager.unsubscribe("entity_died", self._on_entity_died)
        self.event_manager.unsubscribe("player_left", self._on_player_left)
        self.event_manager.unsubscribe("simulated_combat_to_turnbased", self._on_simulated_to_turnbased)
        self.event_manager.unsubscribe("player_update", self._on_player_update_for_autojoin)
        self.event_manager.unsubscribe("combat_turn_start", self._on_npc_turn_start)
        self.event_manager.unsubscribe("combat_action_result", self._on_npc_action_result)
        self.event_manager.unsubscribe("combat_vote_cancel", self._on_vote_cancel)

        # Cancel any pending NPC AI tasks and cancel timers
        for combat in self.active_combats.values():
            self.app.taskMgr.remove(f"npc-ai-{combat.combat_id}")
            self.app.taskMgr.remove(f"cancel-combat-{combat.combat_id}")

        self.logger.info("Combat Manager unloaded")

    # =========================================================================
    # Публичные методы
    # =========================================================================

    def start_combat(self, initiator_id: str, target_ids: List[str],
                     forced_by_dm: bool = False) -> Optional[CombatInstance]:
        """
        Создаёт новую боевую сессию.

        Args:
            initiator_id: ID инициатора боя
            target_ids: Список ID целей
            forced_by_dm: Принудительно начато DM

        Returns:
            CombatInstance или None при ошибке
        """
        combat_id = str(uuid.uuid4())

        # Cooldown check: prevent starting combat if recently cancelled
        now = time.time() if hasattr(time, 'time') else 0
        all_ids = [initiator_id] + target_ids
        for eid in all_ids:
            if self._last_cancelled_at.get(eid, 0) > now - 5.0:
                self.logger.info(f"Combat blocked: cooldown after cancel for {eid}")
                return None

        combat = CombatInstance(combat_id, self)
        self.active_combats[combat_id] = combat

        # Добавляем участников
        for entity_id in all_ids:
            self._add_entity_to_combat(combat, entity_id)

        # Record opposing faction pairs
        initiator_p = combat.get_participant(initiator_id)
        if initiator_p:
            for tid in target_ids:
                target_p = combat.get_participant(tid)
                if target_p and target_p.faction != initiator_p.faction:
                    pair = tuple(sorted([initiator_p.faction, target_p.faction]))
                    combat.opposing_factions.add(pair)

        # Бросаем инициативу
        combat.roll_all_initiative()

        # Начинаем бой
        combat.start_combat()

        self.logger.info(
            f"Combat {combat_id} started with {len(combat.participants)} participants"
        )

        return combat

    def end_combat(self, combat_id: str, reason: CombatEndReason = CombatEndReason.DM_ENDED):
        """Завершает боевую сессию."""
        combat = self.active_combats.get(combat_id)
        if not combat:
            return

        combat.is_active = False

        # Собираем победителей для XP
        winners = []
        losers = []
        for p in combat.participants.values():
            if not p.is_dead:
                winners.append(p.entity_id)
            else:
                losers.append(p.entity_id)

        # Cancel any pending cancel timer
        if combat.cancel_timer_task:
            self.app.taskMgr.remove(f"cancel-combat-{combat_id}")

        # Log combat end
        reason_labels = {
            CombatEndReason.VICTORY: "ПОБЕДА",
            CombatEndReason.DEFEAT: "ПОРАЖЕНИЕ",
            CombatEndReason.FLED: "БЕГСТВО",
            CombatEndReason.DM_ENDED: "ЗАВЕРШЁН DM",
            CombatEndReason.TIMEOUT: "ТАЙМАУТ",
            CombatEndReason.CANCELLED: "ОТМЕНЁН ИГРОКАМИ",
        }
        self._broadcast_combat_log(
            combat, f"Бой окончен: {reason_labels.get(reason, reason.name)}"
        )

        # Очищаем маппинги и unfreeze NPC AI
        for p in combat.participants.values():
            if p.is_player:
                self.player_combat_map.pop(int(p.entity_id), None)
            else:
                self.npc_combat_map.pop(p.entity_id, None)
                # Restore NPC AI state (IDLE if alive, DEAD stays DEAD)
                if not p.is_dead:
                    self._set_npc_ai_state(p.entity_id, "IDLE")

        # Оповещаем
        self.event_manager.post("combat_ended", {
            "combat_id": combat_id,
            "reason": reason.name,
            "winners": winners,
            "losers": losers,
        })

        # Удаляем из активных
        del self.active_combats[combat_id]

        self.logger.info(f"Combat {combat_id} ended: {reason.name}")

    def get_combat_for_entity(self, entity_id: str) -> Optional[CombatInstance]:
        """Получает бой, в котором участвует сущность."""
        # Проверяем как игрока
        try:
            client_id = int(entity_id)
            combat_id = self.player_combat_map.get(client_id)
        except ValueError:
            # Это NPC
            combat_id = self.npc_combat_map.get(entity_id)

        if combat_id:
            return self.active_combats.get(combat_id)
        return None

    def is_entity_in_combat(self, entity_id: str) -> bool:
        """Проверяет, находится ли сущность в бою."""
        return self.get_combat_for_entity(entity_id) is not None

    # =========================================================================
    # Приватные методы
    # =========================================================================

    def _add_entity_to_combat(self, combat: CombatInstance, entity_id: str):
        """Добавляет сущность в бой, получая данные из игрового мира."""
        # Пытаемся определить тип сущности
        try:
            client_id = int(entity_id)
            # Это игрок
            self._add_player_to_combat(combat, client_id)
        except ValueError:
            # Это NPC
            self._add_npc_to_combat(combat, entity_id)

    def _add_player_to_combat(self, combat: CombatInstance, client_id: int):
        """Добавляет игрока в бой."""
        # Получаем данные игрока из игрового мира
        player_data = self._get_player_data(client_id)
        if not player_data:
            self.logger.warning(f"Player {client_id} not found for combat")
            return

        combat.add_participant(
            entity_id=str(client_id),
            is_player=True,
            name=player_data.get("name", f"Player {client_id}"),
            faction=player_data.get("faction", "players"),
            hp_current=player_data.get("hp_current", 10),
            hp_max=player_data.get("hp_max", 10),
            armor_class=player_data.get("armor_class", 10),
            dex_modifier=player_data.get("dex_modifier", 0),
            movement_speed=player_data.get("movement_speed", 30.0),
        )

        self.player_combat_map[client_id] = combat.combat_id

    def _add_npc_to_combat(self, combat: CombatInstance, entity_id: str):
        """Добавляет NPC в бой."""
        # Получаем данные NPC из ECS
        npc_data = self._get_npc_data(entity_id)
        if not npc_data:
            self.logger.warning(f"NPC {entity_id} not found for combat")
            return

        combat.add_participant(
            entity_id=entity_id,
            is_player=False,
            name=npc_data.get("name", "NPC"),
            faction=npc_data.get("faction", "monsters"),
            hp_current=npc_data.get("hp_current", 10),
            hp_max=npc_data.get("hp_max", 10),
            armor_class=npc_data.get("armor_class", 10),
            dex_modifier=npc_data.get("dex_modifier", 0),
            movement_speed=npc_data.get("movement_speed", 30.0),
        )

        self.npc_combat_map[entity_id] = combat.combat_id

        # Freeze NPC AI — prevent patrol/wander during turn-based combat
        self._set_npc_ai_state(entity_id, "IN_COMBAT")

    def _set_npc_ai_state(self, entity_id: str, state_name: str):
        """Set NPC AI state (e.g. IN_COMBAT or IDLE) via ECS."""
        if not hasattr(self.app, 'plugin_manager'):
            return
        npc_plugin = self.app.plugin_manager.get_plugin("nine.npc")
        if not npc_plugin:
            return
        for module in npc_plugin.modules:
            if hasattr(module, 'get_npc_entity'):
                entity = module.get_npc_entity(entity_id)
                if entity:
                    from nine.plugins.npc.sh_components import AIComponent, AIState
                    ai = entity.get_component(AIComponent)
                    if ai:
                        try:
                            ai.state = AIState[state_name]
                        except KeyError:
                            pass
                break

    def _sync_npc_entity_hp(self, entity_id: str, new_hp: int, is_dead: bool = False):
        """Sync combat damage back to the NPC entity's CombatComponent."""
        if not hasattr(self.app, 'plugin_manager'):
            return
        npc_plugin = self.app.plugin_manager.get_plugin("nine.npc")
        if not npc_plugin:
            return
        for module in npc_plugin.modules:
            if hasattr(module, 'get_npc_entity'):
                entity = module.get_npc_entity(entity_id)
                if entity:
                    from nine.plugins.npc.sh_components import CombatComponent
                    combat_comp = entity.get_component(CombatComponent)
                    if combat_comp:
                        combat_comp.hp_current = new_hp
                        if is_dead:
                            combat_comp.is_dead = True
                break

    def _get_player_data(self, client_id: int) -> Optional[dict]:
        """Получает данные игрока из игрового мира."""
        # Сначала пробуем получить из D&D плагина (полные данные персонажа)
        if hasattr(self.app, 'plugin_manager'):
            dnd_plugin = self.app.plugin_manager.get_plugin("nine.dnd")
            if dnd_plugin:
                for module in dnd_plugin.modules:
                    if hasattr(module, 'active_characters'):
                        char_uuid = module.active_characters.get(client_id)
                        if char_uuid and hasattr(self.app, 'db'):
                            char = self.app.db.get_character(char_uuid)
                            if char:
                                # Вычисляем DEX модификатор
                                dex = char.get("dexterity", 10)
                                dex_mod = (dex - 10) // 2

                                return {
                                    "name": char.get("character_name", "Unknown"),
                                    "faction": char.get("faction", "players"),
                                    "hp_current": char.get("hp_current", 10),
                                    "hp_max": char.get("hp_max", 10),
                                    "armor_class": char.get("armor_class", 10),
                                    "dex_modifier": dex_mod,
                                    "movement_speed": 30.0,
                                }

        # Fallback: получаем базовые данные из GameWorld
        if hasattr(self.app, 'world') and self.app.world:
            player = self.app.world.players.get(client_id)
            if player:
                return {
                    "name": player.name,
                    "faction": "players",
                    "hp_current": 10,
                    "hp_max": 10,
                    "armor_class": 10,
                    "dex_modifier": 0,
                    "movement_speed": 30.0,
                }

        return None

    def _get_npc_data(self, entity_id: str) -> Optional[dict]:
        """Получает данные NPC из ECS."""
        entity = None

        # Сначала проверяем прямую ссылку на npc_manager
        if hasattr(self.app, 'npc_manager') and self.app.npc_manager:
            entity = self.app.npc_manager.get_npc_entity(entity_id)

        # Fallback: через plugin_manager
        if not entity and hasattr(self.app, 'plugin_manager'):
            npc_plugin = self.app.plugin_manager.get_plugin("nine.npc")
            if npc_plugin:
                for module in npc_plugin.modules:
                    if hasattr(module, 'get_npc_entity'):
                        entity = module.get_npc_entity(entity_id)
                        if entity:
                            break

        if entity:
            from nine.plugins.npc.sh_components import (
                CombatComponent, FactionComponent, NPCInfoComponent
            )

            combat = entity.get_component(CombatComponent)
            faction = entity.get_component(FactionComponent)
            info = entity.get_component(NPCInfoComponent)

            dex_mod = 0
            if combat:
                # Используем save_dex как приближение
                dex_mod = combat.save_dex

            return {
                "name": info.display_name if info else "NPC",
                "faction": faction.faction_id if faction else "monsters",
                "hp_current": combat.hp_current if combat else 10,
                "hp_max": combat.hp_max if combat else 10,
                "armor_class": combat.armor_class if combat else 10,
                "dex_modifier": dex_mod,
                "movement_speed": 30.0,
            }

        return None

    def _add_nearby_npcs_to_combat(self, combat: CombatInstance):
        """Scan for NPCs within combat radius and add them as participants.

        Pulls in guards, merchants, and other NPCs that were not part of the
        original simulated fight but are standing close enough to be drawn
        into the turn-based encounter.
        """
        npc_manager = getattr(self.app, 'npc_manager', None)
        if not npc_manager or not hasattr(npc_manager, 'get_npcs_in_radius'):
            return

        nearby_entities = npc_manager.get_npcs_in_radius(
            combat.center_x, combat.center_y, combat.radius
        )

        for entity in nearby_entities:
            entity_id = entity.id
            # Skip NPCs already in this combat or another combat
            if entity_id in combat.participants:
                continue
            if self.is_entity_in_combat(entity_id):
                continue

            self._add_npc_to_combat(combat, entity_id)
            if entity_id in combat.participants:
                self.logger.info(
                    f"[Combat] Nearby NPC {combat.participants[entity_id].name} "
                    f"({entity_id}) pulled into combat {combat.combat_id[:8]}"
                )

    # =========================================================================
    # Обработчики событий
    # =========================================================================

    def _on_npc_aggro(self, data: dict):
        """Обрабатывает событие агро NPC на игрока."""
        npc_id = data.get("npc_id")
        player_id = data.get("player_id")

        if not npc_id or player_id is None:
            return

        # Проверяем, не в бою ли уже
        if self.is_entity_in_combat(npc_id) or self.is_entity_in_combat(str(player_id)):
            return

        # Начинаем бой
        self.start_combat(npc_id, [str(player_id)])

    def _on_player_attack(self, data: dict):
        """Обрабатывает запрос атаки от игрока."""
        client_id = data.get("client_id")
        target_id = data.get("target_id")

        if client_id is None or not target_id:
            return

        # Проверяем, в бою ли игрок
        combat = self.get_combat_for_entity(str(client_id))
        if not combat:
            # Начинаем новый бой
            self.start_combat(str(client_id), [target_id])
        else:
            # Передаём событие в turn manager
            self.event_manager.post("combat_action_execute", {
                "combat_id": combat.combat_id,
                "actor_id": str(client_id),
                "action_id": "attack",
                "target_id": target_id,
            })

    def _on_action_request(self, data: dict):
        """Обрабатывает запрос действия в бою."""
        client_id = data.get("client_id")
        action_id = data.get("action_id")
        target_id = data.get("target_id")

        if client_id is None or not action_id:
            return

        combat = self.get_combat_for_entity(str(client_id))
        if not combat:
            return

        # Проверяем, что сейчас ход этого игрока
        current = combat.current_participant
        if not current or current.entity_id != str(client_id):
            self._send_error(client_id, "Сейчас не ваш ход")
            return

        # Передаём в turn manager для выполнения
        self.event_manager.post("combat_action_execute", {
            "combat_id": combat.combat_id,
            "actor_id": str(client_id),
            "action_id": action_id,
            "target_id": target_id,
        })

    def _on_end_turn_request(self, data: dict):
        """Обрабатывает запрос завершения хода."""
        client_id = data.get("client_id")
        if client_id is None:
            return

        combat = self.get_combat_for_entity(str(client_id))
        if not combat:
            return

        # Проверяем, что сейчас ход этого игрока
        current = combat.current_participant
        if not current or current.entity_id != str(client_id):
            self._send_error(client_id, "Сейчас не ваш ход")
            return

        combat.advance_turn()

    def _on_dm_start_combat(self, data: dict):
        """DM принудительно начинает бой."""
        initiator_id = data.get("initiator_id")
        participants = data.get("participants", [])
        target_ids = data.get("target_ids", [])

        # Поддерживаем оба формата: participants (список) и target_ids
        if participants:
            # Первый участник - инициатор, остальные - цели
            if len(participants) > 1:
                initiator_id = participants[0]
                target_ids = participants[1:]
            elif len(participants) == 1:
                initiator_id = participants[0]
                target_ids = []

        if initiator_id:
            self.start_combat(initiator_id, target_ids, forced_by_dm=True)

    def _on_dm_end_combat(self, data: dict):
        """DM принудительно завершает бой."""
        combat_id = data.get("combat_id")
        reason = data.get("reason", "DM_ENDED")

        # Если не указан combat_id, завершаем ближайший бой к DM
        if not combat_id:
            client_id = data.get("client_id")
            if client_id:
                combat = self.get_combat_for_entity(str(client_id))
                if combat:
                    combat_id = combat.combat_id

        if combat_id:
            # Преобразуем строку reason в enum
            try:
                end_reason = CombatEndReason[reason]
            except KeyError:
                end_reason = CombatEndReason.DM_ENDED
            self.end_combat(combat_id, end_reason)

    def _on_dm_add_to_combat(self, data: dict):
        """DM добавляет сущность в существующий бой."""
        combat_id = data.get("combat_id")
        entity_id = data.get("entity_id")

        if not combat_id or not entity_id:
            return

        combat = self.active_combats.get(combat_id)
        if not combat:
            return

        # Проверяем, что сущность ещё не в бою
        if entity_id in combat.participants:
            return

        # Добавляем участника
        self._add_entity_to_combat(combat, entity_id)

        # Бросаем инициативу для нового участника
        participant = combat.participants.get(entity_id)
        if participant:
            participant.roll_initiative()

            # Вставляем в правильное место в turn_order
            inserted = False
            for i, eid in enumerate(combat.turn_order):
                other = combat.participants.get(eid)
                if other and participant.initiative > other.initiative:
                    combat.turn_order.insert(i, entity_id)
                    inserted = True
                    break
            if not inserted:
                combat.turn_order.append(entity_id)

            # Оповещаем клиентов
            self.event_manager.post("combat_participant_added", {
                "combat_id": combat_id,
                "participant": {
                    "entity_id": entity_id,
                    "is_player": participant.is_player,
                    "name": participant.name,
                    "initiative": participant.initiative,
                    "hp_current": participant.hp_current,
                    "hp_max": participant.hp_max,
                },
                "turn_order": combat.turn_order,
            })

            self.logger.info(f"DM added {entity_id} to combat {combat_id}")

    def _on_dm_force_next_turn(self, data: dict):
        """DM принудительно переходит к следующему ходу."""
        combat_id = data.get("combat_id")

        if not combat_id:
            return

        combat = self.active_combats.get(combat_id)
        if not combat or not combat.is_active:
            return

        # Принудительно переходим к следующему ходу
        combat.advance_turn()
        self.logger.info(f"DM forced next turn in combat {combat_id}")

    def _on_dm_set_initiative(self, data: dict):
        """DM устанавливает инициативу сущности."""
        entity_id = data.get("entity_id")
        initiative = data.get("initiative")

        if not entity_id or initiative is None:
            return

        # Находим бой этой сущности
        combat = self.get_combat_for_entity(entity_id)
        if not combat:
            return

        participant = combat.participants.get(entity_id)
        if not participant:
            return

        # Устанавливаем инициативу
        participant.initiative = int(initiative)

        # Пересортировываем turn_order
        combat.turn_order = sorted(
            combat.participants.keys(),
            key=lambda eid: (
                combat.participants[eid].initiative,
                combat.participants[eid].initiative_modifier
            ),
            reverse=True
        )

        # Оповещаем клиентов
        self.event_manager.post("combat_initiative_changed", {
            "combat_id": combat.combat_id,
            "entity_id": entity_id,
            "new_initiative": initiative,
            "turn_order": combat.turn_order,
        })

        self.logger.info(f"DM set initiative of {entity_id} to {initiative}")

    def _on_entity_damaged(self, data: dict):
        """Обрабатывает получение урона сущностью."""
        entity_id = data.get("entity_id")
        damage = data.get("damage", 0)
        new_hp = data.get("new_hp")

        if not entity_id:
            return

        combat = self.get_combat_for_entity(entity_id)
        if combat and new_hp is not None:
            combat.update_participant_hp(entity_id, new_hp)
            # Sync HP back to NPC entity so network data reflects damage
            self._sync_npc_entity_hp(entity_id, new_hp)

    def _on_entity_died(self, data: dict):
        """Обрабатывает смерть сущности."""
        entity_id = data.get("entity_id")

        if not entity_id:
            return

        combat = self.get_combat_for_entity(entity_id)
        if combat:
            participant = combat.get_participant(entity_id)
            if participant:
                participant.is_dead = True
            # Sync death to NPC entity
            self._sync_npc_entity_hp(entity_id, 0, is_dead=True)

            # Проверяем окончание боя
            end_reason = combat.check_combat_end()
            if end_reason:
                self.end_combat(combat.combat_id, end_reason)

    def _on_player_left(self, data: dict):
        """Обрабатывает отключение игрока."""
        client_id = data.get("client_id") or data.get("uuid")
        if client_id is None:
            return

        combat = self.get_combat_for_entity(str(client_id))
        if combat:
            combat.remove_participant(str(client_id))
            self.player_combat_map.pop(client_id, None)

            # Проверяем окончание боя
            end_reason = combat.check_combat_end()
            if end_reason:
                self.end_combat(combat.combat_id, end_reason)

    def _on_simulated_to_turnbased(self, data: dict):
        """
        Handle transition from simulated NPC combat to turn-based.

        Creates a CombatInstance, adds all surviving NPC participants
        with their current HP, forces nearby players in, rolls initiative.
        """
        fight_id = data.get("fight_id")
        participants = data.get("participants", [])
        nearby_players = data.get("nearby_players", [])
        center = data.get("center", {})

        combat_id = str(uuid.uuid4())
        combat = CombatInstance(combat_id, self)
        combat.center_x = center.get("x", 0.0)
        combat.center_y = center.get("y", 0.0)
        combat.center_z = center.get("z", 0.0)
        self.active_combats[combat_id] = combat

        # Add NPC participants with their CURRENT HP from simulation
        for p in participants:
            if p.get("is_dead") or (p.get("hp_current", 0) <= 0):
                continue
            entity_id = p.get("entity_id")
            if not entity_id:
                continue
            # Skip NPCs already in another combat
            if self.is_entity_in_combat(entity_id):
                continue

            self._add_npc_to_combat(combat, entity_id)
            # Override HP with simulation values
            participant = combat.participants.get(entity_id)
            if participant:
                participant.hp_current = p.get("hp_current", participant.hp_current)

        # Force nearby players into combat (no Join button)
        for player_id in nearby_players:
            try:
                client_id = int(player_id)
            except (ValueError, TypeError):
                continue
            if not self.is_entity_in_combat(str(client_id)):
                self._add_player_to_combat(combat, client_id)

        # Pull in nearby NPCs that weren't in the simulated fight
        # (guards, merchants, etc. within combat radius)
        self._add_nearby_npcs_to_combat(combat)

        if len(combat.participants) < 2:
            # Not enough participants for a fight
            del self.active_combats[combat_id]
            return

        # Record opposing faction pairs from participants
        factions_list = [(p.entity_id, p.faction) for p in combat.participants.values()]
        for i, (eid_a, fac_a) in enumerate(factions_list):
            for eid_b, fac_b in factions_list[i+1:]:
                if fac_a != fac_b:
                    pair = tuple(sorted([fac_a, fac_b]))
                    combat.opposing_factions.add(pair)

        # Roll initiative and start
        combat.roll_all_initiative()
        combat.start_combat()

        self.logger.info(
            f"[Combat] Simulated fight {fight_id[:8] if fight_id else '?'} "
            f"transitioned to turn-based {combat_id[:8]} "
            f"with {len(combat.participants)} participants"
        )

    def _on_player_update_for_autojoin(self, data: dict):
        """
        Check if any player walked into range of an existing turn-based combat.
        Auto-joins them with initiative roll.
        """
        players = data.get("players", [])
        if not players or not self.active_combats:
            return

        for combat in list(self.active_combats.values()):
            if not combat.is_active or not combat.is_started:
                continue

            for player in players:
                player_uuid = player.get("uuid", "")
                if not player_uuid:
                    continue
                # Skip players already in combat
                if self.is_entity_in_combat(str(player_uuid)):
                    continue

                player_pos = player.get("position", {})
                ppx = player_pos.get("x", 0)
                ppy = player_pos.get("y", 0)
                dx = combat.center_x - ppx
                dy = combat.center_y - ppy
                dist = math.sqrt(dx * dx + dy * dy)

                if dist <= combat.radius:
                    try:
                        client_id = int(player_uuid)
                    except (ValueError, TypeError):
                        continue
                    self._add_player_to_combat(combat, client_id)

                    # Roll initiative and insert into turn order
                    participant = combat.participants.get(str(client_id))
                    if participant:
                        participant.roll_initiative()
                        inserted = False
                        for i, eid in enumerate(combat.turn_order):
                            other = combat.participants.get(eid)
                            if other and participant.initiative > other.initiative:
                                combat.turn_order.insert(i, str(client_id))
                                inserted = True
                                break
                        if not inserted:
                            combat.turn_order.append(str(client_id))

                        self.event_manager.post("combat_participant_added", {
                            "combat_id": combat.combat_id,
                            "participant": {
                                "entity_id": str(client_id),
                                "is_player": True,
                                "name": participant.name,
                                "initiative": participant.initiative,
                                "hp_current": participant.hp_current,
                                "hp_max": participant.hp_max,
                            },
                            "turn_order": combat.turn_order,
                        })

                        self.logger.info(
                            f"[Combat] Player {client_id} auto-joined combat "
                            f"{combat.combat_id[:8]} (proximity)"
                        )

    # =========================================================================
    # NPC Turn-Based Combat AI
    # =========================================================================

    def _on_npc_turn_start(self, data: dict):
        """Handle turn start — if it's an NPC's turn, schedule AI decision."""
        is_player = data.get("is_player", True)
        if is_player:
            return  # Player turns are handled by the client

        combat_id = data.get("combat_id")
        entity_id = data.get("entity_id")
        if not combat_id or not entity_id:
            return

        combat = self.active_combats.get(combat_id)
        if not combat or not combat.is_active:
            return

        # Schedule NPC AI decision with a small delay (simulate "thinking")
        self.app.taskMgr.remove(f"npc-ai-{combat_id}")
        self.app.taskMgr.doMethodLater(
            1.0, self._npc_ai_decide,
            f"npc-ai-{combat_id}",
            extraArgs=[combat_id, entity_id],
            appendTask=True,
        )

    def _npc_ai_decide(self, combat_id: str, entity_id: str, task):
        """NPC AI decision-making for turn-based combat."""
        combat = self.active_combats.get(combat_id)
        if not combat or not combat.is_active:
            return task.done

        participant = combat.get_participant(entity_id)
        if not participant or participant.is_dead:
            # Skip dead NPC — advance turn
            combat.advance_turn()
            return task.done

        # Ensure it's still this NPC's turn
        current = combat.current_participant
        if not current or current.entity_id != entity_id:
            return task.done

        # Neutral NPCs (merchants, etc.) — dodge and end turn, never attack
        if participant.faction == "neutral":
            if participant.has_action:
                self.event_manager.post("combat_action_execute", {
                    "combat_id": combat_id,
                    "actor_id": entity_id,
                    "action_id": "dodge",
                    "target_id": None,
                })
            else:
                self.event_manager.post("combat_action_execute", {
                    "combat_id": combat_id,
                    "actor_id": entity_id,
                    "action_id": "end_turn",
                    "target_id": None,
                })
            return task.done

        # Find best target (nearest enemy by faction)
        target = self._npc_pick_target(combat, participant)

        if target and participant.has_action:
            # Try to move into range first
            self._npc_move_toward_target(combat, participant, target)

            # Attack the target
            self.event_manager.post("combat_action_execute", {
                "combat_id": combat_id,
                "actor_id": entity_id,
                "action_id": "attack",
                "target_id": target.entity_id,
            })
            # After the action result comes back, _on_npc_action_result will
            # decide whether to continue or end the turn.
        else:
            # No target or no action left — check if we should dodge
            if participant.has_action and participant.hp_current < participant.hp_max * 0.3:
                # Low HP, dodge for survival
                self.event_manager.post("combat_action_execute", {
                    "combat_id": combat_id,
                    "actor_id": entity_id,
                    "action_id": "dodge",
                    "target_id": None,
                })
            else:
                # Nothing useful to do — end turn
                self.event_manager.post("combat_action_execute", {
                    "combat_id": combat_id,
                    "actor_id": entity_id,
                    "action_id": "end_turn",
                    "target_id": None,
                })

        return task.done

    def _on_npc_action_result(self, data: dict):
        """After an NPC action executes, decide next step or end turn."""
        combat_id = data.get("combat_id")
        actor_id = data.get("actor_id")
        action_id = data.get("action_id")

        if not combat_id or not actor_id:
            return

        combat = self.active_combats.get(combat_id)
        if not combat or not combat.is_active:
            return

        participant = combat.get_participant(actor_id)
        if not participant or participant.is_player:
            return  # Only handle NPC follow-up decisions

        # Don't schedule follow-up if turn already ended or advanced
        current = combat.current_participant
        if not current or current.entity_id != actor_id:
            return

        # If the action was end_turn, the turn manager already advanced
        if action_id == "end_turn":
            return

        # Schedule follow-up: if NPC still has bonus action, might use it,
        # otherwise end turn after a short delay
        self.app.taskMgr.remove(f"npc-ai-{combat_id}")
        self.app.taskMgr.doMethodLater(
            0.8, self._npc_ai_followup,
            f"npc-ai-{combat_id}",
            extraArgs=[combat_id, actor_id],
            appendTask=True,
        )

    def _npc_ai_followup(self, combat_id: str, entity_id: str, task):
        """NPC follow-up after first action — typically ends turn."""
        combat = self.active_combats.get(combat_id)
        if not combat or not combat.is_active:
            return task.done

        participant = combat.get_participant(entity_id)
        if not participant or participant.is_dead:
            return task.done

        current = combat.current_participant
        if not current or current.entity_id != entity_id:
            return task.done

        # End turn
        self.event_manager.post("combat_action_execute", {
            "combat_id": combat_id,
            "actor_id": entity_id,
            "action_id": "end_turn",
            "target_id": None,
        })

        return task.done

    def _npc_pick_target(self, combat: CombatInstance, npc: CombatParticipant) -> Optional[CombatParticipant]:
        """Pick the best target for an NPC in turn-based combat."""
        best_target = None
        best_score = -1

        for p in combat.participants.values():
            if p.entity_id == npc.entity_id:
                continue
            if p.is_dead:
                continue
            if p.faction == npc.faction:
                continue  # Don't attack allies
            if p.faction == "neutral":
                continue  # Don't attack neutral NPCs (merchants, etc.)

            # Score: prefer low HP targets, players over NPCs
            score = 100.0
            if p.is_player:
                score += 50  # Prefer attacking players
            # Prefer wounded targets (ratio of missing HP)
            if p.hp_max > 0:
                hp_ratio = p.hp_current / p.hp_max
                score += (1.0 - hp_ratio) * 30  # More wounded = higher score

            if score > best_score:
                best_score = score
                best_target = p

        return best_target

    # =========================================================================
    # NPC Movement AI
    # =========================================================================

    def _npc_move_toward_target(self, combat: CombatInstance, npc: CombatParticipant, target: CombatParticipant):
        """Move NPC toward target if not in melee range."""
        # Get TurnManager for position lookups
        turn_manager = self._get_turn_manager()
        if not turn_manager:
            return

        npc_pos = turn_manager._get_entity_position(npc.entity_id)
        target_pos = turn_manager._get_entity_position(target.entity_id)
        if not npc_pos or not target_pos:
            return

        distance = turn_manager._calculate_distance(npc_pos, target_pos)
        weapon_range = 5.0  # melee default

        if distance <= weapon_range:
            return  # Already in range

        # Calculate how much to move
        move_needed = distance - weapon_range
        move_available = min(move_needed, npc.movement_remaining)

        if move_available <= 0:
            return

        # Direction vector (2D)
        dx = target_pos[0] - npc_pos[0]
        dy = target_pos[1] - npc_pos[1]
        dist_2d = math.sqrt(dx * dx + dy * dy)
        if dist_2d == 0:
            return

        # Normalize and scale
        ratio = move_available / dist_2d
        dest = [
            npc_pos[0] + dx * ratio,
            npc_pos[1] + dy * ratio,
            npc_pos[2] if len(npc_pos) > 2 else 0,
        ]

        # Post movement request (processed synchronously by TurnManager)
        self.event_manager.post("combat_movement_request", {
            "combat_id": combat.combat_id,
            "actor_id": npc.entity_id,
            "destination": dest,
        })

    def _get_turn_manager(self):
        """Get TurnManager reference from the combat plugin."""
        if hasattr(self, '_turn_manager_ref') and self._turn_manager_ref:
            return self._turn_manager_ref

        if hasattr(self.app, 'plugin_manager'):
            combat_plugin = self.app.plugin_manager.get_plugin("nine.combat")
            if combat_plugin:
                for module in combat_plugin.modules:
                    if hasattr(module, '_on_action_execute'):
                        self._turn_manager_ref = module
                        return module
        return None

    # =========================================================================
    # Vote Cancel Combat
    # =========================================================================

    def _on_vote_cancel(self, data: dict):
        """Handle vote to cancel combat from a player."""
        client_id = data.get("client_id")
        if client_id is None:
            return

        combat = self.get_combat_for_entity(str(client_id))
        if not combat:
            return

        combat.cancel_votes.add(str(client_id))

        # Check if ALL alive players voted
        player_ids = [p.entity_id for p in combat.participants.values()
                      if p.is_player and not p.is_dead]
        if all(pid in combat.cancel_votes for pid in player_ids):
            # Start 5-second countdown
            self._broadcast_combat_log(
                combat,
                "Все игроки проголосовали за отмену боя. Бой закончится через 5 секунд..."
            )
            if combat.cancel_timer_task:
                self.app.taskMgr.remove(f"cancel-combat-{combat.combat_id}")
            combat.cancel_timer_task = self.app.taskMgr.doMethodLater(
                5.0, self._cancel_combat_timer,
                f"cancel-combat-{combat.combat_id}",
                extraArgs=[combat.combat_id],
                appendTask=True,
            )
        else:
            # Notify progress
            voted = len(combat.cancel_votes)
            total = len(player_ids)
            self._broadcast_combat_log(
                combat, f"Голос за отмену боя ({voted}/{total})"
            )

    def _cancel_combat_timer(self, combat_id: str, task):
        """Timer callback: cancel combat after 5s vote."""
        combat = self.active_combats.get(combat_id)
        if not combat or not combat.is_active:
            return task.done

        # Record cooldown for all participants
        now = time.time()
        for p in combat.participants.values():
            self._last_cancelled_at[p.entity_id] = now

        self.end_combat(combat_id, CombatEndReason.CANCELLED)
        return task.done

    def _broadcast_combat_log(self, combat: CombatInstance, message: str):
        """Broadcast a combat log message to all player participants."""
        recipients = []
        for p in combat.participants.values():
            if p.is_player:
                try:
                    recipients.append(int(p.entity_id))
                except ValueError:
                    pass
        if recipients:
            self.event_manager.post("chat_send_to_clients", {
                "data": {
                    "type": "chat_broadcast",
                    "chat_type": "system",
                    "from_name": "Бой",
                    "message": message,
                },
                "recipients": recipients
            })

    def _send_error(self, client_id: int, message: str):
        """Отправляет сообщение об ошибке клиенту."""
        self.event_manager.post("chat_send_to_clients", {
            "data": {
                "type": "chat_broadcast",
                "chat_type": "system",
                "from_name": "Бой",
                "message": message,
            },
            "recipients": [client_id]
        })
