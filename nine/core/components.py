"""
Unified ECS Components for niNE.

This module contains all shared components used by both Players and NPCs
through the Pawn system, as well as world objects (Entity).

Pawn Components - for creatures with physics (players, NPCs, monsters)
Entity Components - for world objects (items, interactables)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum, auto

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
    PATROL = auto()     # Patrol between points
    HOSTILE = auto()    # Attack on sight
    FOLLOW = auto()     # Follow target
    FLEE = auto()       # Run away
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


class ObjectType(Enum):
    """Type of world object."""
    STATIC = auto()         # Static decoration
    PICKUP = auto()         # Can be picked up
    INTERACTIVE = auto()    # Can be interacted with


# =============================================================================
# Transform Components (shared by all entities)
# =============================================================================

@dataclass
class TransformComponent(Component):
    """
    Position and rotation in world space.
    Used by both Pawns and world objects.
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0  # Rotation around Z axis (degrees)

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
    """
    Velocity vector for moving entities.
    """
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
    """
    model_path: str = "human_male"
    animation: str = "idle"
    scale: float = 1.0
    animation_speed: float = 1.0
    visible: bool = True


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
    # Movement speeds
    walk_speed: float = 1.5
    run_speed: float = 3.0
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
    """
    Health and death state for a Pawn.
    """
    hp_current: int = 10
    hp_max: int = 10
    is_dead: bool = False
    death_time: float = 0.0

    # D&D combat stats
    armor_class: int = 10
    temp_hp: int = 0

    def take_damage(self, amount: int) -> int:
        """Apply damage and return actual damage taken."""
        # First consume temp HP
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
    """
    Input state for player-controlled Pawns.
    Stores current key states and camera orientation.
    """
    keys: Dict[str, bool] = field(default_factory=lambda: {
        "w": False, "a": False, "s": False, "d": False,
        "space": False, "shift": False
    })
    camera_yaw: float = 0.0
    mouse_x: float = 0.0
    mouse_y: float = 0.0


@dataclass
class AIControllerComponent(Component):
    """
    AI controller for NPC Pawns.
    Determines behavior and decision-making.
    """
    behavior: AIBehavior = AIBehavior.IDLE
    state: AIState = AIState.IDLE

    # Aggression
    aggro_radius: float = 10.0
    leash_radius: float = 30.0
    attack_range: float = 2.0

    # Targeting
    target_entity_id: Optional[str] = None
    last_known_target_pos: Optional[tuple] = None

    # Patrol
    patrol_points: List[tuple] = field(default_factory=list)
    current_patrol_index: int = 0
    patrol_wait_time: float = 2.0
    patrol_timer: float = 0.0

    # Wander
    wander_radius: float = 5.0
    wander_center: Optional[tuple] = None
    wander_timer: float = 0.0
    wander_interval: float = 5.0

    # Movement
    move_speed: float = 0.6
    think_interval: float = 0.5
    think_timer: float = 0.0


@dataclass
class PathfindingComponent(Component):
    """
    Pathfinding state for AI-controlled Pawns.
    """
    current_path: List[tuple] = field(default_factory=list)
    current_waypoint_index: int = 0
    target_position: Optional[tuple] = None
    needs_repath: bool = False

    waypoint_radius: float = 0.5
    repath_interval: float = 1.0
    repath_timer: float = 0.0

    is_stuck: bool = False
    stuck_timer: float = 0.0
    stuck_threshold: float = 3.0


# =============================================================================
# Combat Components
# =============================================================================

@dataclass
class CombatStatsComponent(Component):
    """
    D&D-style combat statistics.
    """
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


@dataclass
class FactionComponent(Component):
    """
    Faction affiliation and relationships.
    """
    faction_id: str = "neutral"
    hostile_to_players: bool = False
    disposition_overrides: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# Interaction Components
# =============================================================================

@dataclass
class InteractableComponent(Component):
    """
    Makes an entity interactable by players.
    """
    interaction_radius: float = 2.0
    interaction_prompt: str = "Interact"
    is_interactable: bool = True


@dataclass
class DialogueComponent(Component):
    """
    Dialogue capability for NPCs.
    """
    dialogue_id: str = ""
    current_node_id: str = "start"
    is_in_dialogue: bool = False
    dialogue_partner_id: Optional[str] = None
    greeting_text: str = ""
    greeting_radius: float = 3.0


@dataclass
class InventoryComponent(Component):
    """
    Inventory for NPCs (merchants, loot).
    """
    items: List[Dict[str, Any]] = field(default_factory=list)
    gold: int = 0
    loot_table_id: Optional[str] = None
    is_merchant: bool = False
    buy_modifier: float = 1.0
    sell_modifier: float = 0.5
    looted: bool = False


# =============================================================================
# World Object Components
# =============================================================================

@dataclass
class WorldObjectComponent(Component):
    """
    Component for world objects (items, decorations, etc).
    """
    object_type: ObjectType = ObjectType.STATIC
    item_id: Optional[str] = None
    is_interactable: bool = False
    respawn_time: float = 0.0  # 0 = no respawn


# =============================================================================
# Network Sync Component
# =============================================================================

@dataclass
class NetworkSyncComponent(Component):
    """
    Network synchronization state.
    Used to track what needs to be sent to clients.
    """
    needs_full_sync: bool = True  # Send all data on next tick
    last_sync_time: float = 0.0
    sync_priority: int = 0  # Higher = more frequent updates

    # Interpolation data for clients
    prev_x: float = 0.0
    prev_y: float = 0.0
    prev_z: float = 0.0
    prev_rotation: float = 0.0


# =============================================================================
# Component Registry
# =============================================================================

COMPONENT_REGISTRY: Dict[str, type] = {
    # Transform
    "TransformComponent": TransformComponent,
    "VelocityComponent": VelocityComponent,

    # Visual
    "ModelComponent": ModelComponent,

    # Pawn
    "PawnComponent": PawnComponent,
    "PhysicsComponent": PhysicsComponent,
    "HealthComponent": HealthComponent,
    "InputComponent": InputComponent,
    "AIControllerComponent": AIControllerComponent,
    "PathfindingComponent": PathfindingComponent,

    # Combat
    "CombatStatsComponent": CombatStatsComponent,
    "FactionComponent": FactionComponent,

    # Interaction
    "InteractableComponent": InteractableComponent,
    "DialogueComponent": DialogueComponent,
    "InventoryComponent": InventoryComponent,

    # World objects
    "WorldObjectComponent": WorldObjectComponent,

    # Network
    "NetworkSyncComponent": NetworkSyncComponent,
}
