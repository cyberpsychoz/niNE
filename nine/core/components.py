"""
Unified ECS Components for niNE.

This module contains ALL components used by Players, NPCs, and world objects.
Components from npc/sh_components.py and living_npc/sh_living_components.py
have been merged here as the single source of truth.

Pawn Components - for creatures with physics (players, NPCs, monsters)
NPC Components - AI, pathfinding, combat, dialogue, living world
Entity Components - for world objects (items, interactables)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum, auto

from panda3d.core import Vec3

from nine.core.ecs import Component


# =============================================================================
# Enums
# =============================================================================

class PawnType(Enum):
    """Type of Pawn entity."""
    PLAYER = auto()     # Player-controlled pawn
    NPC = auto()        # AI-controlled NPC
    CREATURE = auto()   # Generic creature


class AIBehavior(Enum):
    """AI behavior patterns."""
    IDLE = auto()       # Stand in place
    NEUTRAL = auto()    # Don't attack unless provoked
    PATROL = auto()     # Patrol between points
    HOSTILE = auto()    # Attack on sight
    FOLLOW = auto()     # Follow target
    FLEE = auto()       # Run away
    SCHEDULE = auto()   # Follow daily schedule
    WANDER = auto()     # Random movement


class AIState(Enum):
    """Current AI state."""
    IDLE = auto()           # Doing nothing
    MOVING = auto()         # Moving to target
    ATTACKING = auto()      # Performing attack
    PURSUING = auto()       # Chasing target
    FLEEING = auto()        # Running away
    INTERACTING = auto()    # In dialogue/interaction
    DEAD = auto()           # Dead
    IN_COMBAT = auto()      # Frozen during turn-based combat


class ObjectType(Enum):
    """Type of world object."""
    STATIC = auto()         # Static decoration
    PICKUP = auto()         # Can be picked up
    INTERACTIVE = auto()    # Can be interacted with


class PhysicsTier(Enum):
    """Physics simulation detail level."""
    FULL = auto()       # Full Panda3D collision (players, bosses)
    SIMPLE = auto()     # Ground clamp only (regular NPC)
    NONE = auto()       # No physics (sleeping/distant NPC)


class InteractionType(Enum):
    """Types of NPC interaction."""
    TALK = auto()       # Dialogue
    TRADE = auto()      # Trading
    ATTACK = auto()     # Attack
    LOOT = auto()       # Loot collection


# --- Living NPC enums (string values preserved for compatibility) ---

class PersonalityTrait(Enum):
    """NPC personality traits."""
    # Positive
    BRAVE = "brave"
    KIND = "kind"
    HONEST = "honest"
    LOYAL = "loyal"
    WISE = "wise"
    PATIENT = "patient"
    GENEROUS = "generous"
    HUMBLE = "humble"
    # Negative
    COWARDLY = "cowardly"
    CRUEL = "cruel"
    DECEITFUL = "deceitful"
    TREACHEROUS = "treacherous"
    FOOLISH = "foolish"
    IMPATIENT = "impatient"
    GREEDY = "greedy"
    ARROGANT = "arrogant"
    # Neutral
    CURIOUS = "curious"
    CAUTIOUS = "cautious"
    AMBITIOUS = "ambitious"
    PRAGMATIC = "pragmatic"


class Activity(Enum):
    """NPC activities for schedule system."""
    IDLE = "idle"
    SLEEPING = "sleeping"
    EATING = "eating"
    WORKING = "working"
    PATROLLING = "patrolling"
    SOCIALIZING = "socializing"
    TRADING = "trading"
    PRAYING = "praying"
    TRAINING = "training"
    CRAFTING = "crafting"
    WANDERING = "wandering"


class MemoryType(Enum):
    """Types of NPC memories."""
    PLAYER_HELPED = "player_helped"
    PLAYER_ATTACKED = "player_attacked"
    PLAYER_GAVE_ITEM = "player_gave_item"
    PLAYER_INSULTED = "player_insulted"
    PLAYER_COMPLIMENTED = "player_complimented"
    WITNESSED_CRIME = "witnessed_crime"
    WITNESSED_HEROIC_ACT = "witnessed_heroic_act"
    RECEIVED_GIFT = "received_gift"
    WAS_ROBBED = "was_robbed"
    CONVERSATION = "conversation"


# =============================================================================
# Transform Components (shared by all entities)
# =============================================================================

@dataclass
class TransformComponent(Component):
    """
    Position and rotation in world space.
    Used by both Pawns and world objects.
    Includes velocity fields for client-side interpolation (from NPC PositionComponent).
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0  # Rotation around Z axis (degrees)

    # Velocity for client interpolation (from NPC PositionComponent)
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    velocity_z: float = 0.0

    def get_pos(self) -> Vec3:
        """Return position as Vec3."""
        return Vec3(self.x, self.y, self.z)

    def set_pos(self, pos) -> None:
        """Set position from Vec3 or tuple."""
        if hasattr(pos, 'x'):
            self.x, self.y, self.z = pos.x, pos.y, pos.z
        else:
            self.x, self.y, self.z = pos[0], pos[1], pos[2]

    def distance_to(self, other_x: float, other_y: float) -> float:
        """Calculate 2D distance to a point."""
        dx = self.x - other_x
        dy = self.y - other_y
        return (dx * dx + dy * dy) ** 0.5

    def distance_to_3d(self, other_x: float, other_y: float, other_z: float) -> float:
        """Calculate 3D distance to a point."""
        dx = self.x - other_x
        dy = self.y - other_y
        dz = self.z - other_z
        return (dx * dx + dy * dy + dz * dz) ** 0.5


@dataclass
class VelocityComponent(Component):
    """Velocity vector for moving entities."""
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0

    def speed_horizontal(self) -> float:
        """Get horizontal speed (ignoring Z)."""
        return (self.vx * self.vx + self.vy * self.vy) ** 0.5

    def speed(self) -> float:
        """Get total speed."""
        return (self.vx * self.vx + self.vy * self.vy + self.vz * self.vz) ** 0.5


# =============================================================================
# Visual Components
# =============================================================================

@dataclass
class ModelComponent(Component):
    """
    Visual representation of an entity.
    Merged: core fields + NPC fields (current_animation, tint).
    """
    model_path: str = ""
    scale: float = 1.0
    animation: str = "idle"
    current_animation: str = "idle"  # NPC alias (kept for NPC code compat)
    animation_speed: float = 1.0
    visible: bool = True
    # Tint color (from NPC version)
    tint_r: float = 1.0
    tint_g: float = 1.0
    tint_b: float = 1.0


# =============================================================================
# Pawn Components (for creatures - players, NPCs, monsters)
# =============================================================================

@dataclass
class PawnComponent(Component):
    """
    Core component that identifies an entity as a Pawn (creature).
    All pawns have physics and can move around the world.
    """
    pawn_type: PawnType = PawnType.NPC
    display_name: str = ""
    owner_id: Optional[int] = None  # client_id for players, None for NPCs
    template_id: str = ""           # NPC template ID
    tags: List[str] = field(default_factory=list)


@dataclass
class PhysicsComponent(Component):
    """
    Physics properties for a Pawn.
    Controls movement, collision, and physics simulation.
    """
    # Physics tier (NEW for unified physics)
    tier: PhysicsTier = PhysicsTier.FULL

    # Movement speeds (reduced to match animation playback)
    walk_speed: float = 0.8
    run_speed: float = 1.6
    rotation_speed: float = 10.0

    # Physics parameters
    gravity: float = 25.0
    jump_speed: float = 10.0
    max_fall_speed: float = 40.0

    # Source-like movement
    ground_accel: float = 10.0
    air_accel: float = 2.0
    friction: float = 6.0

    # Collision
    has_collision: bool = True
    collision_radius: float = 0.4
    collision_height: float = 1.8

    # State
    is_on_ground: bool = False
    is_jumping: bool = False
    is_running: bool = False


@dataclass
class HealthComponent(Component):
    """Health and death state for a Pawn."""
    hp_current: int = 10
    hp_max: int = 10
    is_dead: bool = False
    death_time: float = 0.0

    # D&D combat stats
    armor_class: int = 10
    temp_hp: int = 0

    def take_damage(self, amount: int) -> int:
        """Apply damage and return actual damage taken."""
        if self.temp_hp > 0:
            if amount <= self.temp_hp:
                self.temp_hp -= amount
                return 0
            amount -= self.temp_hp
            self.temp_hp = 0

        actual = min(amount, self.hp_current)
        self.hp_current -= actual

        if self.hp_current <= 0:
            self.hp_current = 0
            self.is_dead = True

        return actual

    def heal(self, amount: int) -> int:
        """Heal and return actual amount healed."""
        if self.is_dead:
            return 0
        actual = min(amount, self.hp_max - self.hp_current)
        self.hp_current += actual
        return actual


@dataclass
class InputComponent(Component):
    """Input state for player-controlled Pawns."""
    keys: Dict[str, bool] = field(default_factory=lambda: {
        "w": False, "a": False, "s": False, "d": False,
        "space": False, "shift": False
    })
    camera_yaw: float = 0.0
    mouse_x: float = 0.0
    mouse_y: float = 0.0


# =============================================================================
# AI Components
# =============================================================================

@dataclass
class AIControllerComponent(Component):
    """
    DEPRECATED: Use AIComponent instead.
    Kept for backward compatibility with core/systems.py AISystem.
    """
    behavior: AIBehavior = AIBehavior.IDLE
    state: AIState = AIState.IDLE

    aggro_radius: float = 10.0
    leash_radius: float = 30.0
    attack_range: float = 2.0

    target_entity_id: Optional[str] = None
    last_known_target_pos: Optional[tuple] = None

    patrol_points: List[tuple] = field(default_factory=list)
    current_patrol_index: int = 0
    patrol_wait_time: float = 2.0
    patrol_timer: float = 0.0

    wander_radius: float = 5.0
    wander_center: Optional[tuple] = None
    wander_timer: float = 0.0
    wander_interval: float = 5.0

    move_speed: float = 0.6
    think_interval: float = 0.5
    think_timer: float = 0.0


@dataclass
class AIComponent(Component):
    """
    AI behavior for NPC (canonical version from npc/sh_components.py).
    Replaces AIControllerComponent with richer NPC support.
    """
    behavior: AIBehavior = AIBehavior.IDLE
    state: AIState = AIState.IDLE

    # Aggression parameters
    aggro_radius: float = 10.0     # Enemy detection radius
    leash_radius: float = 30.0     # Maximum pursuit distance
    attack_range: float = 2.0      # Attack distance

    # Patrolling
    patrol_points: List[tuple] = field(default_factory=list)  # [(x, y, z), ...]
    current_patrol_index: int = 0
    patrol_wait_time: float = 2.0  # Wait time at each point
    patrol_timer: float = 0.0

    # Pursuit
    target_entity_id: Optional[str] = None  # Target ID (player/NPC)
    last_known_target_pos: Optional[tuple] = None

    # Wander (random wandering)
    wander_radius: float = 5.0
    wander_center: Optional[tuple] = None
    wander_timer: float = 0.0
    wander_interval: float = 5.0   # Interval for choosing new point

    # General parameters
    move_speed: float = 0.6        # Movement speed
    think_interval: float = 0.5    # AI update interval

    # LOD (Level of Detail) - set by AISystem
    lod_level: int = 0             # 0=NEAR, 1=MEDIUM, 2=FAR, 3=VERY_FAR, 4=SLEEPING

    # Spawn position (for leash/return behavior)
    spawn_position: Optional[tuple] = None


@dataclass
class PathfindingComponent(Component):
    """
    Pathfinding state for AI-controlled Pawns.
    Uses Vec3 types (from NPC version) for Panda3D compatibility.
    """
    # Current path
    current_path: List[Vec3] = field(default_factory=list)
    current_waypoint_index: int = 0

    # Target
    target_position: Optional[Vec3] = None
    needs_repath: bool = False

    # Movement parameters
    waypoint_radius: float = 0.5   # Waypoint reach radius
    repath_interval: float = 1.0   # Repath interval
    repath_timer: float = 0.0

    # State
    is_stuck: bool = False
    stuck_timer: float = 0.0
    stuck_threshold: float = 3.0   # Time until considered stuck

    # Steering
    velocity: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    max_speed: float = 0.6
    max_force: float = 2.0  # Gentle steering for smooth turns


# =============================================================================
# Combat Components
# =============================================================================

@dataclass
class CombatStatsComponent(Component):
    """
    D&D-style combat statistics.
    Also serves as the canonical CombatComponent for NPC (via COMPONENT_REGISTRY alias).
    """
    # Health (NPC CombatComponent fields)
    hp_current: int = 10
    hp_max: int = 10

    # Defense
    armor_class: int = 10

    # Attack
    attack_bonus: int = 0
    damage_dice: str = "1d6"
    damage_bonus: int = 0
    damage_type: str = "slashing"

    # Combat timing
    attack_cooldown: float = 2.0
    attack_timer: float = 0.0

    # D&D saves
    save_str: int = 0
    save_dex: int = 0
    save_con: int = 0
    save_int: int = 0
    save_wis: int = 0
    save_cha: int = 0

    # Challenge rating (for XP calculation)
    cr: float = 0.25

    # State (from NPC CombatComponent)
    is_dead: bool = False
    death_time: float = 0.0
    corpse_despawn_time: float = 60.0  # Time until corpse despawns


@dataclass
class CombatSessionComponent(Component):
    """
    Turn-based combat participation state.
    Added to entities when entering combat, removed when leaving.
    Copied as-is from npc/sh_components.py.
    """
    # Combat identification
    combat_id: str = ""                      # Combat session UUID

    # Initiative
    initiative: int = 0                       # Initiative roll result
    initiative_modifier: int = 0              # Modifier (usually DEX)
    turn_order_position: int = 0              # Position in turn order

    # Action economy (reset at turn start)
    movement_remaining: float = 30.0          # Remaining movement in feet
    movement_speed: float = 30.0              # Base speed
    has_action: bool = True
    has_bonus_action: bool = True
    has_reaction: bool = True

    # Turn state
    is_current_turn: bool = False
    is_incapacitated: bool = False
    has_used_movement: bool = False

    # Conditions
    conditions: List[str] = field(default_factory=list)  # ["poisoned", "prone"]
    condition_durations: Dict[str, int] = field(default_factory=dict)
    condition_sources: Dict[str, str] = field(default_factory=dict)

    # Concentration
    concentrating_on: Optional[str] = None
    concentration_target: Optional[str] = None

    # Readied action
    readied_action: Optional[str] = None
    readied_trigger: str = ""

    # Current target
    selected_target_id: Optional[str] = None

    def reset_turn_resources(self):
        """Reset resources at turn start."""
        self.movement_remaining = self.movement_speed
        self.has_action = True
        self.has_bonus_action = True
        self.has_reaction = True
        self.has_used_movement = False
        self.readied_action = None
        self.readied_trigger = ""

    def consume_action(self) -> bool:
        if self.has_action and not self.is_incapacitated:
            self.has_action = False
            return True
        return False

    def consume_bonus_action(self) -> bool:
        if self.has_bonus_action and not self.is_incapacitated:
            self.has_bonus_action = False
            return True
        return False

    def consume_reaction(self) -> bool:
        if self.has_reaction and not self.is_incapacitated:
            self.has_reaction = False
            return True
        return False

    def consume_movement(self, feet: float) -> bool:
        if self.movement_remaining >= feet and not self.is_incapacitated:
            self.movement_remaining -= feet
            self.has_used_movement = True
            return True
        return False

    def add_condition(self, condition_id: str, duration: int = -1, source: str = ""):
        if condition_id not in self.conditions:
            self.conditions.append(condition_id)
        if duration > 0:
            self.condition_durations[condition_id] = duration
        if source:
            self.condition_sources[condition_id] = source

    def remove_condition(self, condition_id: str):
        if condition_id in self.conditions:
            self.conditions.remove(condition_id)
        self.condition_durations.pop(condition_id, None)
        self.condition_sources.pop(condition_id, None)

    def has_condition(self, condition_id: str) -> bool:
        return condition_id in self.conditions

    def tick_conditions(self):
        expired = []
        for cond, duration in list(self.condition_durations.items()):
            if duration > 0:
                self.condition_durations[cond] = duration - 1
                if self.condition_durations[cond] <= 0:
                    expired.append(cond)
        for cond in expired:
            self.remove_condition(cond)


@dataclass
class TargetableComponent(Component):
    """Makes an entity selectable as a target."""
    is_targetable: bool = True
    target_priority: int = 0
    highlight_color: tuple = (1.0, 0.0, 0.0, 0.5)
    is_highlighted: bool = False
    is_selected: bool = False


@dataclass
class FactionComponent(Component):
    """Faction affiliation and relationships."""
    faction_id: str = "neutral"
    hostile_to_players: bool = False
    disposition_overrides: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# NPC Info & Interaction Components
# =============================================================================

@dataclass
class NPCInfoComponent(Component):
    """NPC identity and template data."""
    template_id: str = ""
    display_name: str = "NPC"
    title: str = ""                # Title (e.g., "Merchant")
    is_unique: bool = False        # Unique NPC (doesn't respawn)
    is_essential: bool = False     # Cannot die
    tags: List[str] = field(default_factory=list)


@dataclass
class InteractionComponent(Component):
    """
    NPC interaction capabilities.
    Replaces core InteractableComponent.
    """
    interactions: List[InteractionType] = field(
        default_factory=lambda: [InteractionType.TALK]
    )
    interaction_radius: float = 2.0
    interaction_prompt: str = "Interact"
    is_interactable: bool = True


# Keep old name as alias for backward compat
InteractableComponent = InteractionComponent


@dataclass
class DialogueComponent(Component):
    """NPC dialogue system (richer NPC version with dialogue_flags)."""
    dialogue_id: str = ""
    current_node_id: str = "start"
    is_in_dialogue: bool = False
    dialogue_partner_id: Optional[str] = None
    dialogue_flags: Dict[str, Any] = field(default_factory=dict)
    greeting_text: str = ""
    greeting_radius: float = 3.0


@dataclass
class InventoryComponent(Component):
    """Inventory for NPCs (merchants, loot)."""
    items: List[Dict[str, Any]] = field(default_factory=list)
    gold: int = 0
    loot_table_id: Optional[str] = None
    is_merchant: bool = False
    buy_modifier: float = 1.0
    sell_modifier: float = 0.5
    looted: bool = False


# =============================================================================
# Living World Components (from living_npc, with Component inheritance added)
# =============================================================================

@dataclass
class NeedsComponent(Component):
    """
    NPC needs system.
    Values from 0 (critically low) to 100 (fully satisfied).
    """
    hunger: float = 100.0
    energy: float = 100.0
    social: float = 50.0
    safety: float = 80.0
    comfort: float = 70.0

    # Decay rates (per game hour)
    hunger_decay: float = 2.0
    energy_decay: float = 1.5
    social_decay: float = 0.5

    def update(self, delta_hours: float, is_active: bool = True):
        """Update needs over time."""
        self.hunger = max(0, self.hunger - self.hunger_decay * delta_hours)
        if is_active:
            self.energy = max(0, self.energy - self.energy_decay * delta_hours)
        self.social = max(0, self.social - self.social_decay * delta_hours)

    def eat(self, amount: float = 30.0):
        self.hunger = min(100, self.hunger + amount)

    def sleep(self, hours: float):
        self.energy = min(100, self.energy + hours * 12.5)

    def socialize(self, quality: float = 1.0):
        self.social = min(100, self.social + 10 * quality)

    @property
    def most_urgent_need(self) -> str:
        needs = {
            "hunger": self.hunger,
            "energy": self.energy,
            "social": self.social,
            "safety": self.safety,
        }
        return min(needs, key=needs.get)

    @property
    def is_critical(self) -> bool:
        return min(self.hunger, self.energy, self.safety) < 20


@dataclass
class PersonalityComponent(Component):
    """NPC personality traits with behavior modifiers."""
    traits: List[str] = field(default_factory=list)  # PersonalityTrait values

    # Numeric characteristics (0.0 - 1.0)
    chattiness: float = 0.5
    aggression: float = 0.3
    curiosity: float = 0.5
    greed: float = 0.3
    kindness: float = 0.5
    courage: float = 0.5

    def has_trait(self, trait: str) -> bool:
        return trait.lower() in [t.lower() for t in self.traits]

    def get_reaction_modifier(self, event_type: str) -> float:
        modifiers = {
            "threat": self.courage - 0.5,
            "gift": self.kindness,
            "insult": -self.aggression,
            "trade": self.greed - 0.5,
        }
        return modifiers.get(event_type, 0.0)


@dataclass
class RelationshipData:
    """Relationship with another entity."""
    entity_id: str = ""
    disposition: float = 50.0   # -100 (enemy) to 100 (friend)
    trust: float = 50.0         # 0 (no trust) to 100 (full trust)
    familiarity: float = 0.0    # 0 (stranger) to 100 (well known)
    last_interaction: Optional[str] = None  # ISO timestamp

    @property
    def relationship_level(self) -> str:
        if self.disposition >= 80:
            return "friend"
        elif self.disposition >= 60:
            return "friendly"
        elif self.disposition >= 40:
            return "neutral"
        elif self.disposition >= 20:
            return "unfriendly"
        else:
            return "hostile"


@dataclass
class RelationshipsComponent(Component):
    """NPC relationships with other entities."""
    relationships: Dict[str, RelationshipData] = field(default_factory=dict)
    default_disposition: float = 50.0
    default_trust: float = 30.0

    def get_relationship(self, entity_id: str) -> RelationshipData:
        if entity_id not in self.relationships:
            self.relationships[entity_id] = RelationshipData(
                entity_id=entity_id,
                disposition=self.default_disposition,
                trust=self.default_trust,
            )
        return self.relationships[entity_id]

    def modify_disposition(self, entity_id: str, amount: float):
        rel = self.get_relationship(entity_id)
        rel.disposition = max(-100, min(100, rel.disposition + amount))
        rel.familiarity = min(100, rel.familiarity + abs(amount) * 0.1)

    def modify_trust(self, entity_id: str, amount: float):
        rel = self.get_relationship(entity_id)
        rel.trust = max(0, min(100, rel.trust + amount))

    def get_disposition(self, entity_id: str) -> float:
        return self.get_relationship(entity_id).disposition

    def is_hostile_to(self, entity_id: str) -> bool:
        return self.get_disposition(entity_id) < 20


@dataclass
class Memory:
    """Single memory entry."""
    memory_type: str    # MemoryType value
    entity_id: str      # Who was involved
    details: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5  # 0-1, affects forgetting
    timestamp: str = ""      # ISO timestamp
    location: Optional[List[float]] = None  # Where it happened


@dataclass
class MemoryComponent(Component):
    """NPC memory system."""
    memories: List[Memory] = field(default_factory=list)
    max_memories: int = 50
    forget_threshold: float = 0.2

    def add_memory(self, memory: Memory):
        self.memories.append(memory)
        if len(self.memories) > self.max_memories:
            self._forget_least_important()

    def _forget_least_important(self):
        self.memories.sort(key=lambda m: m.importance, reverse=True)
        self.memories = self.memories[:self.max_memories]

    def get_memories_about(self, entity_id: str) -> List[Memory]:
        return [m for m in self.memories if m.entity_id == entity_id]

    def get_memories_of_type(self, memory_type: str) -> List[Memory]:
        return [m for m in self.memories if m.memory_type == memory_type]

    def has_memory_of(self, entity_id: str, memory_type: str) -> bool:
        for m in self.memories:
            if m.entity_id == entity_id and m.memory_type == memory_type:
                return True
        return False

    def decay_memories(self, amount: float = 0.01):
        for memory in self.memories:
            memory.importance = max(0, memory.importance - amount)
        self.memories = [m for m in self.memories if m.importance > self.forget_threshold]


@dataclass
class ScheduleEntry:
    """Single schedule entry."""
    hour_start: int = 0
    hour_end: int = 24
    activity: str = "idle"   # Activity value
    location: Optional[List[float]] = None
    location_id: Optional[str] = None
    priority: int = 1


@dataclass
class ScheduleComponent(Component):
    """NPC daily schedule (living_npc version with typed entries)."""
    entries: List[ScheduleEntry] = field(default_factory=list)
    current_activity: str = "idle"
    deviation_chance: float = 0.1

    def get_activity_for_hour(self, hour: int) -> Optional[ScheduleEntry]:
        best_entry = None
        best_priority = -1

        for entry in self.entries:
            if entry.hour_start <= entry.hour_end:
                in_range = entry.hour_start <= hour < entry.hour_end
            else:
                # Range across midnight (e.g., 22-6)
                in_range = hour >= entry.hour_start or hour < entry.hour_end

            if in_range and entry.priority > best_priority:
                best_entry = entry
                best_priority = entry.priority

        return best_entry

    def add_entry(self, entry: ScheduleEntry):
        self.entries.append(entry)
        self.entries.sort(key=lambda e: e.hour_start)


# =============================================================================
# World Components
# =============================================================================

@dataclass
class WorldObjectComponent(Component):
    """Component for world objects (items, decorations, etc)."""
    object_type: ObjectType = ObjectType.STATIC
    item_id: Optional[str] = None
    is_interactable: bool = False
    respawn_time: float = 0.0


@dataclass
class WorldBoundsComponent(Component):
    """World boundaries. Attached to a single world entity."""
    min_x: float = -500.0
    max_x: float = 500.0
    min_y: float = -500.0
    max_y: float = 500.0
    min_z: float = -10.0
    max_z: float = 200.0


# =============================================================================
# Network Sync Component
# =============================================================================

@dataclass
class NetworkSyncComponent(Component):
    """Network synchronization state."""
    needs_full_sync: bool = True
    last_sync_time: float = 0.0
    sync_priority: int = 0

    prev_x: float = 0.0
    prev_y: float = 0.0
    prev_z: float = 0.0
    prev_rotation: float = 0.0


# =============================================================================
# Component Registry (unified — includes legacy aliases)
# =============================================================================

COMPONENT_REGISTRY: Dict[str, type] = {
    # Transform
    "TransformComponent": TransformComponent,
    "PositionComponent": TransformComponent,      # NPC legacy alias
    "VelocityComponent": VelocityComponent,

    # Visual
    "ModelComponent": ModelComponent,

    # Identity
    "PawnComponent": PawnComponent,
    "FactionComponent": FactionComponent,

    # Physics
    "PhysicsComponent": PhysicsComponent,

    # Health & Combat
    "HealthComponent": HealthComponent,
    "CombatStatsComponent": CombatStatsComponent,
    "CombatComponent": CombatStatsComponent,      # NPC legacy alias
    "CombatSessionComponent": CombatSessionComponent,
    "TargetableComponent": TargetableComponent,

    # AI
    "AIComponent": AIComponent,
    "AIControllerComponent": AIControllerComponent,  # deprecated

    # Pathfinding
    "PathfindingComponent": PathfindingComponent,

    # Input
    "InputComponent": InputComponent,

    # NPC
    "NPCInfoComponent": NPCInfoComponent,
    "InteractionComponent": InteractionComponent,
    "InteractableComponent": InteractionComponent,   # core legacy alias
    "DialogueComponent": DialogueComponent,
    "InventoryComponent": InventoryComponent,

    # Living World
    "NeedsComponent": NeedsComponent,
    "PersonalityComponent": PersonalityComponent,
    "ScheduleComponent": ScheduleComponent,
    "RelationshipsComponent": RelationshipsComponent,
    "MemoryComponent": MemoryComponent,

    # World
    "WorldObjectComponent": WorldObjectComponent,
    "WorldBoundsComponent": WorldBoundsComponent,

    # Network
    "NetworkSyncComponent": NetworkSyncComponent,
}
