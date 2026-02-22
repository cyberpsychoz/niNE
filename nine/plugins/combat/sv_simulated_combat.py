"""
Simulated Combat System — lightweight NPC vs NPC auto-resolve combat.

NPCs fight each other in real-time using D&D stats (d20 + attack_bonus vs AC).
No turns, no initiative — just attack cooldowns.

When a player enters proximity (~30m), the fight freezes and transitions
to D&D 5e turn-based combat via simulated_combat_to_turnbased event.

Loot only drops if a player is nearby when an NPC dies.
"""

from __future__ import annotations

import math
import random
import uuid
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from nine.plugins.combat.sh_dice import DiceRoller
from nine.plugins.npc.sh_components import (
    PositionComponent,
    CombatComponent,
    FactionComponent,
    NPCInfoComponent,
    InventoryComponent,
    AIComponent,
    AIState,
)

if TYPE_CHECKING:
    from nine.core.ecs import ECSWorld, Entity
    from nine.core.events import EventManager
    from nine.core.plugins import PluginContext

logger = logging.getLogger(__name__)


# Radius within which players trigger turn-based transition
PLAYER_PROXIMITY_RADIUS = 30.0

# Radius within which loot drops for nearby player deaths
LOOT_PROXIMITY_RADIUS = 50.0


@dataclass
class SimParticipant:
    """One NPC in a simulated fight."""
    entity_id: str
    faction: str
    name: str = "NPC"
    hp_current: int = 10
    hp_max: int = 10
    armor_class: int = 10
    attack_bonus: int = 0
    damage_dice: str = "1d6"
    damage_bonus: int = 0
    attack_cooldown: float = 2.0
    attack_timer: float = 0.0
    target_id: Optional[str] = None
    is_dead: bool = False
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class SimulatedFight:
    """One ongoing NPC vs NPC fight."""
    fight_id: str
    participants: Dict[str, SimParticipant] = field(default_factory=dict)
    center_x: float = 0.0
    center_y: float = 0.0
    center_z: float = 0.0
    radius: float = PLAYER_PROXIMITY_RADIUS
    frozen: bool = False  # True when transitioning to turn-based

    def get_living_participants(self) -> List[SimParticipant]:
        """Return all living participants."""
        return [p for p in self.participants.values() if not p.is_dead]

    def get_living_factions(self) -> Set[str]:
        """Return set of factions with living members."""
        return {p.faction for p in self.participants.values() if not p.is_dead}

    def update_center(self):
        """Recalculate fight center from living participant positions."""
        living = self.get_living_participants()
        if not living:
            return
        self.center_x = sum(p.position[0] for p in living) / len(living)
        self.center_y = sum(p.position[1] for p in living) / len(living)
        self.center_z = sum(p.position[2] for p in living) / len(living)


class SimulatedCombatManager:
    """
    Manages all simulated (real-time) NPC vs NPC fights.

    Listens for npc_aggro_npc events, creates/merges fights,
    runs auto-resolve combat each tick, and transitions to
    turn-based when a player enters proximity.
    """

    def __init__(self, context: 'PluginContext'):
        self.context = context
        self.app = context.app
        self.event_manager: EventManager = context.event_manager
        self.logger = context.logger

        self.fights: Dict[str, SimulatedFight] = {}
        self.entity_fight_map: Dict[str, str] = {}  # entity_id -> fight_id

        # Cached player positions (updated via player_update event)
        self._player_positions: List[Dict] = []

    def on_load(self):
        """Subscribe to events."""
        self.event_manager.subscribe("npc_aggro_npc", self._on_npc_aggro_npc)
        self.event_manager.subscribe("entity_died", self._on_entity_died)
        self.event_manager.subscribe("player_update", self._on_player_update)
        self.logger.info("SimulatedCombatManager loaded")

    def on_unload(self):
        """Unsubscribe from events."""
        self.event_manager.unsubscribe("npc_aggro_npc", self._on_npc_aggro_npc)
        self.event_manager.unsubscribe("entity_died", self._on_entity_died)
        self.event_manager.unsubscribe("player_update", self._on_player_update)
        self.fights.clear()
        self.entity_fight_map.clear()
        self.logger.info("SimulatedCombatManager unloaded")

    # =========================================================================
    # Main update loop
    # =========================================================================

    def update(self, dt: float):
        """Called each server tick. Updates all active simulated fights."""
        for fight in list(self.fights.values()):
            if fight.frozen:
                continue
            # Check player proximity FIRST — freeze fight before NPCs can die
            self._check_player_proximity(fight)
            if fight.frozen:
                continue  # Fight was frozen by proximity check
            self._update_fight(fight, dt)
            self._check_fight_end(fight)

    # =========================================================================
    # Fight lifecycle
    # =========================================================================

    def _on_npc_aggro_npc(self, data: dict):
        """Handle NPC detecting a hostile NPC."""
        attacker_id = data.get("attacker_id")
        target_id = data.get("target_id")
        if not attacker_id or not target_id:
            return

        # Skip if either is already in turn-based combat
        if self._is_in_turnbased_combat(attacker_id) or self._is_in_turnbased_combat(target_id):
            return

        attacker_fight_id = self.entity_fight_map.get(attacker_id)
        target_fight_id = self.entity_fight_map.get(target_id)

        if attacker_fight_id and target_fight_id:
            if attacker_fight_id == target_fight_id:
                return  # Already in the same fight
            # Merge two fights
            self._merge_fights(attacker_fight_id, target_fight_id)
        elif attacker_fight_id:
            # Add target to attacker's fight
            self._add_npc_to_fight(self.fights[attacker_fight_id], target_id)
        elif target_fight_id:
            # Add attacker to target's fight
            self._add_npc_to_fight(self.fights[target_fight_id], attacker_id)
        else:
            # Create new fight
            self._create_fight(attacker_id, target_id)

    def _create_fight(self, attacker_id: str, target_id: str):
        """Create a new simulated fight between two NPCs."""
        fight_id = str(uuid.uuid4())
        fight = SimulatedFight(fight_id=fight_id)

        self._add_npc_to_fight(fight, attacker_id)
        self._add_npc_to_fight(fight, target_id)

        if len(fight.participants) < 2:
            # Failed to add one of the participants
            for eid in list(fight.participants.keys()):
                self.entity_fight_map.pop(eid, None)
            return

        fight.update_center()
        self.fights[fight_id] = fight

        self.logger.info(
            f"[SimCombat] Fight {fight_id[:8]} started: "
            f"{fight.participants[attacker_id].name} vs {fight.participants[target_id].name}"
        )

    def _add_npc_to_fight(self, fight: SimulatedFight, entity_id: str):
        """Add an NPC to a simulated fight by reading its ECS components."""
        if entity_id in fight.participants:
            return

        entity = self._get_entity(entity_id)
        if not entity:
            return

        combat = entity.get_component(CombatComponent)
        faction = entity.get_component(FactionComponent)
        info = entity.get_component(NPCInfoComponent)
        pos = entity.get_component(PositionComponent)

        if not combat or not faction or not pos:
            return

        if combat.is_dead:
            return

        participant = SimParticipant(
            entity_id=entity_id,
            faction=faction.faction_id,
            name=info.display_name if info else "NPC",
            hp_current=combat.hp_current,
            hp_max=combat.hp_max,
            armor_class=combat.armor_class,
            attack_bonus=combat.attack_bonus,
            damage_dice=combat.damage_dice,
            damage_bonus=combat.damage_bonus,
            attack_cooldown=combat.attack_cooldown,
            attack_timer=0.0,
            position=(pos.x, pos.y, pos.z),
        )

        fight.participants[entity_id] = participant
        self.entity_fight_map[entity_id] = fight.fight_id

        # Set NPC AI state to ATTACKING so it stops wandering/patrolling
        ai = entity.get_component(AIComponent)
        if ai:
            ai.state = AIState.ATTACKING

    def _merge_fights(self, fight_id_a: str, fight_id_b: str):
        """Merge fight B into fight A."""
        fight_a = self.fights.get(fight_id_a)
        fight_b = self.fights.get(fight_id_b)
        if not fight_a or not fight_b:
            return

        # Move all participants from B to A
        for entity_id, participant in fight_b.participants.items():
            if entity_id not in fight_a.participants:
                fight_a.participants[entity_id] = participant
                self.entity_fight_map[entity_id] = fight_a.fight_id

        # Remove fight B
        del self.fights[fight_id_b]
        fight_a.update_center()

        self.logger.info(
            f"[SimCombat] Merged fight {fight_id_b[:8]} into {fight_id_a[:8]} "
            f"({len(fight_a.participants)} participants)"
        )

    # =========================================================================
    # Fight update (auto-resolve combat)
    # =========================================================================

    def _update_fight(self, fight: SimulatedFight, dt: float):
        """Process one tick of a simulated fight."""
        living = fight.get_living_participants()
        if len(living) < 2:
            return

        for participant in living:
            # Decrement attack timer
            participant.attack_timer -= dt
            if participant.attack_timer > 0:
                continue

            # Reset cooldown
            participant.attack_timer = participant.attack_cooldown

            # Update position from ECS
            entity = self._get_entity(participant.entity_id)
            if entity:
                pos = entity.get_component(PositionComponent)
                if pos:
                    participant.position = (pos.x, pos.y, pos.z)

            # Pick a target (nearest enemy faction participant)
            target = self._pick_target(fight, participant)
            if not target:
                continue

            participant.target_id = target.entity_id

            # Roll attack: d20 + attack_bonus vs target AC
            attack_total, attack_roll = DiceRoller.roll_attack(participant.attack_bonus)

            if attack_roll.is_fumble:
                # Natural 1 — auto miss
                logger.debug(
                    f"[SimCombat] {participant.name} misses {target.name} (nat 1)"
                )
                continue

            if attack_roll.is_critical or attack_total >= target.armor_class:
                # Hit — roll damage
                damage_roll = DiceRoller.roll_damage(
                    participant.damage_dice, critical=attack_roll.is_critical
                )
                total_damage = max(1, damage_roll.total + participant.damage_bonus)

                target.hp_current -= total_damage

                logger.debug(
                    f"[SimCombat] {participant.name} hits {target.name} "
                    f"({attack_total} vs AC {target.armor_class}) for {total_damage} dmg "
                    f"(HP: {target.hp_current}/{target.hp_max})"
                )

                # Sync damage back to ECS CombatComponent
                target_entity = self._get_entity(target.entity_id)
                if target_entity:
                    target_combat = target_entity.get_component(CombatComponent)
                    if target_combat:
                        target_combat.hp_current = target.hp_current

                # Check death
                if target.hp_current <= 0:
                    target.is_dead = True
                    self._handle_simulated_death(fight, target, participant)
            else:
                logger.debug(
                    f"[SimCombat] {participant.name} misses {target.name} "
                    f"({attack_total} vs AC {target.armor_class})"
                )

        # Update fight center
        fight.update_center()

    def _pick_target(
        self, fight: SimulatedFight, attacker: SimParticipant
    ) -> Optional[SimParticipant]:
        """Pick nearest enemy faction participant as target."""
        nearest = None
        nearest_dist = float('inf')

        for other in fight.participants.values():
            if other.is_dead or other.entity_id == attacker.entity_id:
                continue
            if other.faction == attacker.faction:
                continue  # Same faction — don't attack allies

            dx = attacker.position[0] - other.position[0]
            dy = attacker.position[1] - other.position[1]
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < nearest_dist:
                nearest_dist = dist
                nearest = other

        return nearest

    def _handle_simulated_death(
        self,
        fight: SimulatedFight,
        dead: SimParticipant,
        killer: SimParticipant
    ):
        """Handle an NPC dying in simulated combat."""
        # Mark dead in ECS
        entity = self._get_entity(dead.entity_id)
        if entity:
            combat = entity.get_component(CombatComponent)
            if combat:
                combat.is_dead = True
                combat.death_time = time.time()
                combat.hp_current = 0

            ai = entity.get_component(AIComponent)
            if ai:
                ai.state = AIState.DEAD

        self.logger.info(
            f"[SimCombat] {dead.name} killed by {killer.name} in fight {fight.fight_id[:8]}"
        )

        # Post death event
        self.event_manager.post("simulated_npc_died", {
            "entity_id": dead.entity_id,
            "killer_id": killer.entity_id,
            "position": dead.position,
            "fight_id": fight.fight_id,
        })

        # Post entity_died for other systems (combat manager, etc.)
        self.event_manager.post("entity_died", {
            "entity_id": dead.entity_id,
            "killer_id": killer.entity_id,
        })

        # Check loot — only drop if a player is nearby
        self._check_loot_drop(dead)

    def _check_loot_drop(self, dead: SimParticipant):
        """Check if loot should drop (player nearby)."""
        if not self._player_positions:
            return  # No players — discard loot

        px, py, pz = dead.position
        for player in self._player_positions:
            player_pos = player.get("position", {})
            ppx = player_pos.get("x", 0)
            ppy = player_pos.get("y", 0)
            dx = px - ppx
            dy = py - ppy
            dist = math.sqrt(dx * dx + dy * dy)

            if dist <= LOOT_PROXIMITY_RADIUS:
                # Player is close enough — drop loot
                self.event_manager.post("npc_loot_drop", {
                    "entity_id": dead.entity_id,
                    "position": {"x": px, "y": py, "z": pz},
                    "near_player": True,
                })
                logger.debug(
                    f"[SimCombat] Loot dropped for {dead.name} (player within {dist:.1f}m)"
                )
                return

        # No player nearby — discard loot
        logger.debug(f"[SimCombat] Loot discarded for {dead.name} (no player nearby)")

    # =========================================================================
    # Player proximity — transition to turn-based
    # =========================================================================

    def _check_player_proximity(self, fight: SimulatedFight):
        """Check if any player is close enough to trigger turn-based combat."""
        if fight.frozen or not self._player_positions:
            return

        nearby_players = []
        for player in self._player_positions:
            player_pos = player.get("position", {})
            ppx = player_pos.get("x", 0)
            ppy = player_pos.get("y", 0)
            dx = fight.center_x - ppx
            dy = fight.center_y - ppy
            dist = math.sqrt(dx * dx + dy * dy)

            if dist <= fight.radius:
                player_uuid = player.get("uuid", "")
                # Skip players already in turn-based combat
                if player_uuid and not self._is_in_turnbased_combat(str(player_uuid)):
                    nearby_players.append(player_uuid)

        if nearby_players:
            self._transition_to_turnbased(fight, nearby_players)

    def _transition_to_turnbased(self, fight: SimulatedFight, nearby_players: List):
        """Freeze simulated fight and post event for turn-based transition."""
        fight.frozen = True

        # Build participant data for the combat manager
        participants_data = []
        for p in fight.participants.values():
            participants_data.append({
                "entity_id": p.entity_id,
                "faction": p.faction,
                "name": p.name,
                "hp_current": p.hp_current,
                "hp_max": p.hp_max,
                "armor_class": p.armor_class,
                "is_dead": p.is_dead,
            })

        self.event_manager.post("simulated_combat_to_turnbased", {
            "fight_id": fight.fight_id,
            "participants": participants_data,
            "nearby_players": nearby_players,
            "center": {"x": fight.center_x, "y": fight.center_y, "z": fight.center_z},
        })

        self.logger.info(
            f"[SimCombat] Fight {fight.fight_id[:8]} transitioning to turn-based "
            f"({len(nearby_players)} players nearby)"
        )

        # Clean up the simulated fight — it's now handled by CombatManager
        self._cleanup_fight(fight.fight_id)

    # =========================================================================
    # Fight end / cleanup
    # =========================================================================

    def _check_fight_end(self, fight: SimulatedFight):
        """Check if fight should end (only one faction remains)."""
        if fight.frozen:
            return

        living_factions = fight.get_living_factions()
        if len(living_factions) <= 1:
            self._end_fight(fight)

    def _end_fight(self, fight: SimulatedFight):
        """End a simulated fight. Survivors return to default behavior."""
        self.logger.info(
            f"[SimCombat] Fight {fight.fight_id[:8]} ended "
            f"(survivors: {len(fight.get_living_participants())})"
        )

        # Return survivors to default behavior
        for participant in fight.get_living_participants():
            entity = self._get_entity(participant.entity_id)
            if entity:
                ai = entity.get_component(AIComponent)
                if ai:
                    ai.state = AIState.IDLE
                    ai.target_entity_id = None

        self._cleanup_fight(fight.fight_id)

    def _cleanup_fight(self, fight_id: str):
        """Remove fight from tracking."""
        fight = self.fights.pop(fight_id, None)
        if fight:
            for entity_id in fight.participants:
                self.entity_fight_map.pop(entity_id, None)

    # =========================================================================
    # Event handlers
    # =========================================================================

    def _on_entity_died(self, data: dict):
        """Handle entity death — remove from simulated fight if present."""
        entity_id = data.get("entity_id")
        if not entity_id:
            return

        fight_id = self.entity_fight_map.get(entity_id)
        if not fight_id:
            return

        fight = self.fights.get(fight_id)
        if fight:
            participant = fight.participants.get(entity_id)
            if participant:
                participant.is_dead = True

    def _on_player_update(self, data: dict):
        """Cache player positions for proximity checks."""
        self._player_positions = data.get("players", [])

    # =========================================================================
    # Helpers
    # =========================================================================

    def _get_entity(self, entity_id: str) -> Optional['Entity']:
        """Get ECS entity by ID."""
        if hasattr(self.app, 'npc_manager') and self.app.npc_manager:
            return self.app.npc_manager.get_npc_entity(entity_id)
        return None

    def _is_in_turnbased_combat(self, entity_id: str) -> bool:
        """Check if entity is in turn-based combat."""
        if hasattr(self.app, 'combat_manager') and self.app.combat_manager:
            return self.app.combat_manager.is_entity_in_combat(entity_id)
        return False

    def is_entity_in_simulated_fight(self, entity_id: str) -> bool:
        """Check if entity is in a simulated fight."""
        return entity_id in self.entity_fight_map

    def get_fight_for_entity(self, entity_id: str) -> Optional[SimulatedFight]:
        """Get the simulated fight an entity is in."""
        fight_id = self.entity_fight_map.get(entity_id)
        if fight_id:
            return self.fights.get(fight_id)
        return None

    def get_stats(self) -> dict:
        """Get simulated combat statistics."""
        total_participants = sum(len(f.participants) for f in self.fights.values())
        total_living = sum(len(f.get_living_participants()) for f in self.fights.values())
        return {
            "active_fights": len(self.fights),
            "total_participants": total_participants,
            "total_living": total_living,
        }
