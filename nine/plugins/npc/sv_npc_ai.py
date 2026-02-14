"""
AI systems for NPC.

Handles NPC behavior: patrolling, pursuit, attacks, etc.

Optimizations:
- AI LOD (Level of Detail): Distant NPCs think less frequently
- Spatial partitioning integration for O(k) enemy detection
- Async pathfinding support
"""

from __future__ import annotations

import random
import math
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional, Dict, Tuple, TYPE_CHECKING
from panda3d.core import Vec3
import logging

from nine.core.ecs import System, Entity, ECSWorld
from nine.core.pathfinder import GridPathfinder, SteeringBehaviors

from nine.plugins.npc.sh_components import (
    PositionComponent,
    ModelComponent,
    AIComponent,
    PathfindingComponent,
    CombatComponent,
    FactionComponent,
    NPCInfoComponent,
    AIBehavior,
    AIState,
)

if TYPE_CHECKING:
    from nine.plugins.npc.sv_npc_manager import NPCManager
    from nine.core.spatial import SpatialHash

logger = logging.getLogger(__name__)


# =============================================================================
# AI Level of Detail (LOD) System
# =============================================================================

class AILODLevel(IntEnum):
    """AI Level of Detail levels."""
    NEAR = 0        # Full AI, fast updates
    MEDIUM = 1      # Full AI, slower updates
    FAR = 2         # Basic AI, minimal updates
    VERY_FAR = 3    # Minimal AI, rare updates
    SLEEPING = 4    # No updates (frozen)


@dataclass
class AILODConfig:
    """Configuration for AI LOD distances and intervals."""
    # Distance thresholds (world units)
    near_distance: float = 30.0
    medium_distance: float = 60.0
    far_distance: float = 100.0
    very_far_distance: float = 200.0

    # Think intervals for each level (seconds)
    near_interval: float = 0.5
    medium_interval: float = 1.0
    far_interval: float = 2.0
    very_far_interval: float = 5.0

    # Behavior modifiers
    disable_pathfinding_far: bool = True     # No pathfinding recalc at FAR+
    disable_combat_very_far: bool = True     # No combat at VERY_FAR
    skip_perception_far: bool = True         # No enemy detection at FAR+


class AILODSystem:
    """
    Manages AI Level of Detail based on distance to nearest player.

    NPCs far from players think less frequently, saving CPU time.
    Essential for scaling to 300+ NPCs.

    Usage:
        lod_system = AILODSystem()

        # Get LOD level for NPC
        level = lod_system.get_lod_level(npc_pos, player_positions)
        interval = lod_system.get_think_interval(level)

        # Check if NPC should think this tick
        if lod_system.should_think(entity_id, level, current_time):
            # Process AI...
    """

    def __init__(self, config: Optional[AILODConfig] = None):
        """
        Initialize LOD system.

        Args:
            config: Optional custom configuration
        """
        self.config = config or AILODConfig()

        # Track last think time per entity
        self._last_think: Dict[str, float] = {}

        # Cache LOD levels (updated periodically)
        self._lod_cache: Dict[str, AILODLevel] = {}
        self._cache_timestamp: float = 0.0
        self._cache_lifetime: float = 0.5  # Refresh every 0.5s

        # Statistics
        self._stats = {
            "total_npcs": 0,
            "near_count": 0,
            "medium_count": 0,
            "far_count": 0,
            "very_far_count": 0,
            "sleeping_count": 0,
            "thinks_skipped": 0,
        }

    def get_lod_level(
        self,
        npc_x: float,
        npc_y: float,
        player_positions: List[Tuple[float, float]]
    ) -> AILODLevel:
        """
        Determine LOD level based on distance to nearest player.

        Args:
            npc_x, npc_y: NPC position
            player_positions: List of (x, y) player positions

        Returns:
            AILODLevel for this NPC
        """
        if not player_positions:
            return AILODLevel.SLEEPING

        # Find distance to nearest player
        min_dist_sq = float('inf')
        for px, py in player_positions:
            dx = npc_x - px
            dy = npc_y - py
            dist_sq = dx * dx + dy * dy
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq

        min_dist = math.sqrt(min_dist_sq)

        # Determine LOD level
        if min_dist <= self.config.near_distance:
            return AILODLevel.NEAR
        elif min_dist <= self.config.medium_distance:
            return AILODLevel.MEDIUM
        elif min_dist <= self.config.far_distance:
            return AILODLevel.FAR
        elif min_dist <= self.config.very_far_distance:
            return AILODLevel.VERY_FAR
        else:
            return AILODLevel.SLEEPING

    def get_think_interval(self, lod_level: AILODLevel) -> float:
        """
        Get think interval for LOD level.

        Args:
            lod_level: The LOD level

        Returns:
            Think interval in seconds (float('inf') for SLEEPING)
        """
        intervals = {
            AILODLevel.NEAR: self.config.near_interval,
            AILODLevel.MEDIUM: self.config.medium_interval,
            AILODLevel.FAR: self.config.far_interval,
            AILODLevel.VERY_FAR: self.config.very_far_interval,
            AILODLevel.SLEEPING: float('inf'),
        }
        return intervals.get(lod_level, self.config.far_interval)

    def should_think(
        self,
        entity_id: str,
        lod_level: AILODLevel,
        current_time: float
    ) -> bool:
        """
        Check if NPC should think this tick.

        Args:
            entity_id: Entity ID
            lod_level: Current LOD level
            current_time: Current game time

        Returns:
            True if NPC should process AI this tick
        """
        if lod_level == AILODLevel.SLEEPING:
            self._stats["thinks_skipped"] += 1
            return False

        interval = self.get_think_interval(lod_level)
        last_think = self._last_think.get(entity_id, 0.0)

        if current_time - last_think >= interval:
            self._last_think[entity_id] = current_time
            return True
        else:
            self._stats["thinks_skipped"] += 1
            return False

    def should_do_pathfinding(self, lod_level: AILODLevel) -> bool:
        """Check if pathfinding should be recalculated at this LOD level."""
        if self.config.disable_pathfinding_far:
            return lod_level <= AILODLevel.MEDIUM
        return True

    def should_do_perception(self, lod_level: AILODLevel) -> bool:
        """Check if perception (enemy detection) should run at this LOD level."""
        if self.config.skip_perception_far:
            return lod_level <= AILODLevel.MEDIUM
        return True

    def should_do_combat(self, lod_level: AILODLevel) -> bool:
        """Check if combat should be processed at this LOD level."""
        if self.config.disable_combat_very_far:
            return lod_level <= AILODLevel.FAR
        return True

    def remove_entity(self, entity_id: str) -> None:
        """Remove entity from tracking."""
        self._last_think.pop(entity_id, None)
        self._lod_cache.pop(entity_id, None)

    def update_stats(
        self,
        near: int,
        medium: int,
        far: int,
        very_far: int,
        sleeping: int
    ) -> None:
        """Update LOD distribution statistics."""
        self._stats["near_count"] = near
        self._stats["medium_count"] = medium
        self._stats["far_count"] = far
        self._stats["very_far_count"] = very_far
        self._stats["sleeping_count"] = sleeping
        self._stats["total_npcs"] = near + medium + far + very_far + sleeping

    def get_stats(self) -> Dict:
        """Get LOD statistics."""
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            "total_npcs": 0,
            "near_count": 0,
            "medium_count": 0,
            "far_count": 0,
            "very_far_count": 0,
            "sleeping_count": 0,
            "thinks_skipped": 0,
        }


# =============================================================================
# AI System — основная логика поведения
# =============================================================================

class AISystem(System):
    """
    Main AI system. Updates state and makes decisions.

    Optimizations:
    - LOD-based think throttling (distant NPCs think less frequently)
    - Spatial hash for O(k) enemy detection (if available)
    - Batch player position caching
    """

    required_components = [PositionComponent, AIComponent]
    priority = 10  # Executes early

    # Faction hostility matrix — True = these factions attack each other on sight
    # Keys are sorted tuples for order-independent lookup
    FACTION_HOSTILITY = {
        ("guards", "monsters"): True,
        ("guards", "undead"): True,
        ("monsters", "undead"): True,
        ("neutral", "monsters"): False,  # merchants don't fight
        ("neutral", "undead"): False,
    }

    def __init__(
        self,
        npc_manager: 'NPCManager' = None,
        lod_system: Optional[AILODSystem] = None,
        spatial_hash: Optional['SpatialHash'] = None,
        event_manager: Optional['EventManager'] = None
    ):
        super().__init__()
        self.npc_manager = npc_manager  # DEPRECATED: kept for backward compatibility
        self.event_manager = event_manager
        self._think_accumulators: Dict[str, float] = {}

        # AI LOD system for distance-based throttling
        self.lod_system = lod_system or AILODSystem()

        # Spatial hash for fast neighbor queries (set by NPCManager)
        self.spatial_hash: Optional['SpatialHash'] = spatial_hash

        # Cached player positions (updated via set_player_positions)
        self._player_positions: List[Tuple[float, float]] = []
        self._player_positions_dict: Dict[str, Tuple[float, float, float]] = {}
        self._player_data: List[Dict] = []  # Full player data for targeting

        # Behavior overrides from living world (needs, schedule)
        # entity_id -> override behavior string
        self._behavior_overrides: Dict[str, str] = {}

        # Subscribe to living world events
        if event_manager:
            event_manager.subscribe("npc_urgent_need", self._on_urgent_need)
            event_manager.subscribe("npc_activity_changed", self._on_activity_changed)

        # Performance tracking
        self._tick_count = 0
        self._total_think_time = 0.0

    def set_player_positions(self, players: List[Dict]) -> None:
        """
        Set player positions for AI targeting and LOD calculations.

        This method should be called before update() to provide current player data.
        Replaces the dependency on NPCManager.get_players().

        Args:
            players: List of player dicts with 'uuid', 'position', 'name' keys
                    position dict should have 'x', 'y', 'z' keys
        """
        self._player_data = players
        self._player_positions.clear()
        self._player_positions_dict.clear()

        for player in players:
            player_pos = player.get("position", {})
            px = player_pos.get("x", 0)
            py = player_pos.get("y", 0)
            pz = player_pos.get("z", 0)

            self._player_positions.append((px, py))
            player_uuid = player.get("uuid", "")
            if player_uuid:
                self._player_positions_dict[player_uuid] = (px, py, pz)

    def update(self, dt: float, entities: List[Entity]) -> None:
        """
        Update AI for all entities.

        Uses LOD-based throttling to reduce CPU usage for distant NPCs.
        """
        self._tick_count += 1
        current_time = time.time()

        # Player positions should be set via set_player_positions() before update()
        # Fallback to old method for backward compatibility
        if not self._player_data and self.npc_manager:
            self._update_player_cache_legacy()

        # Track LOD distribution for stats
        lod_counts = {level: 0 for level in AILODLevel}

        for entity in entities:
            ai = entity.get_component(AIComponent)
            pos = entity.get_component(PositionComponent)

            # Dead NPCs don't think
            combat = entity.get_component(CombatComponent)
            if combat:
                # Auto-set is_dead flag if HP reaches zero
                if combat.hp_current <= 0 and not combat.is_dead:
                    combat.is_dead = True
                    combat.death_time = time.time()

                if combat.is_dead:
                    ai.state = AIState.DEAD
                    continue

            entity_id = entity.id

            # Calculate LOD level based on distance to players
            # When no players connected, treat all NPCs as NEAR so they still think
            if not self._player_positions:
                lod_level = AILODLevel.NEAR
            else:
                lod_level = self.lod_system.get_lod_level(
                    pos.x, pos.y, self._player_positions
                )
            lod_counts[lod_level] += 1

            # Store LOD level on AI component for other systems
            ai.lod_level = int(lod_level)

            # Check if NPC should think this tick (LOD-based throttling)
            if not self.lod_system.should_think(entity_id, lod_level, current_time):
                continue

            # Check for behavior overrides from living world (needs, schedule)
            override = self._behavior_overrides.get(entity_id)
            if override:
                self._update_override(entity, ai, pos, dt, override, lod_level)
                continue

            # Update AI based on behavior
            if ai.behavior == AIBehavior.IDLE:
                self._update_idle(entity, ai, pos, dt, lod_level)
            elif ai.behavior == AIBehavior.NEUTRAL:
                self._update_neutral(entity, ai, pos, dt, lod_level)
            elif ai.behavior == AIBehavior.PATROL:
                self._update_patrol(entity, ai, pos, dt, lod_level)
            elif ai.behavior == AIBehavior.HOSTILE:
                self._update_hostile(entity, ai, pos, dt, lod_level)
            elif ai.behavior == AIBehavior.WANDER:
                self._update_wander(entity, ai, pos, dt, lod_level)
            elif ai.behavior == AIBehavior.FOLLOW:
                self._update_follow(entity, ai, pos, dt, lod_level)

        # Update LOD statistics
        self.lod_system.update_stats(
            near=lod_counts[AILODLevel.NEAR],
            medium=lod_counts[AILODLevel.MEDIUM],
            far=lod_counts[AILODLevel.FAR],
            very_far=lod_counts[AILODLevel.VERY_FAR],
            sleeping=lod_counts[AILODLevel.SLEEPING]
        )

    def _update_player_cache_legacy(self) -> None:
        """
        DEPRECATED: Update cached player positions from NPCManager.

        This method is kept for backward compatibility.
        New code should use set_player_positions() instead.
        """
        self._player_positions.clear()
        self._player_positions_dict.clear()

        if not self.npc_manager:
            return

        players = self.npc_manager.get_players()
        self._player_data = players

        for player in players:
            player_pos = player.get("position", {})
            px = player_pos.get("x", 0)
            py = player_pos.get("y", 0)
            pz = player_pos.get("z", 0)

            self._player_positions.append((px, py))
            player_uuid = player.get("uuid", "")
            if player_uuid:
                self._player_positions_dict[player_uuid] = (px, py, pz)

    def _update_idle(
        self,
        entity: Entity,
        ai: AIComponent,
        pos: PositionComponent,
        dt: float,
        lod_level: AILODLevel = AILODLevel.NEAR
    ):
        """Idle - stands in place, but can react to enemies and occasionally wanders."""
        ai.state = AIState.IDLE

        # Skip perception at high LOD levels
        if not self.lod_system.should_do_perception(lod_level):
            return

        # Check for player enemies first
        target = self._find_nearest_enemy(entity, ai, pos)
        if target:
            ai.target_entity_id = target.id
            ai.behavior = AIBehavior.HOSTILE
            ai.state = AIState.PURSUING
            self._post_aggro_event(entity.id, target.id)
            return

        # Check for NPC enemies
        npc_target = self._find_nearest_npc_enemy(entity, ai, pos)
        if npc_target:
            ai.target_entity_id = npc_target.id
            ai.behavior = AIBehavior.HOSTILE
            ai.state = AIState.PURSUING
            self._post_npc_aggro_event(entity.id, npc_target.id)
            return

        # Idle NPCs occasionally fidget/wander near their post
        ai.wander_timer += ai.think_interval
        if ai.wander_timer >= 8.0:  # Every 8 seconds
            ai.wander_timer = 0.0
            if random.random() < 0.3:  # 30% chance to wander
                if ai.wander_center is None:
                    ai.wander_center = (pos.x, pos.y, pos.z)
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(0.5, 2.0)
                target_x = ai.wander_center[0] + math.cos(angle) * dist
                target_y = ai.wander_center[1] + math.sin(angle) * dist
                self._set_pathfinding_target_pos(entity, Vec3(target_x, target_y, pos.z))
                ai.state = AIState.MOVING

    def _update_neutral(
        self,
        entity: Entity,
        ai: AIComponent,
        pos: PositionComponent,
        dt: float,
        lod_level: AILODLevel = AILODLevel.NEAR
    ):
        """Neutral - stands in place, does NOT attack first (only if attacked)."""
        ai.state = AIState.IDLE
        # Neutral NPCs do not search for enemies automatically
        # They will only react if attacked (handled by damage events)

    def _update_patrol(
        self,
        entity: Entity,
        ai: AIComponent,
        pos: PositionComponent,
        dt: float,
        lod_level: AILODLevel = AILODLevel.NEAR
    ):
        """Patrol - walks between patrol points."""
        if not ai.patrol_points:
            ai.state = AIState.IDLE
            return

        # Check for enemies (skip at high LOD levels)
        if self.lod_system.should_do_perception(lod_level):
            target = self._find_nearest_enemy(entity, ai, pos)
            if target:
                ai.target_entity_id = target.id
                ai.state = AIState.PURSUING
                self._set_pathfinding_target(entity, target)
                self._post_aggro_event(entity.id, target.id)
                return

            # Check for NPC enemies
            npc_target = self._find_nearest_npc_enemy(entity, ai, pos)
            if npc_target:
                ai.target_entity_id = npc_target.id
                ai.behavior = AIBehavior.HOSTILE
                ai.state = AIState.PURSUING
                self._post_npc_aggro_event(entity.id, npc_target.id)
                return

        current_point = ai.patrol_points[ai.current_patrol_index]

        # If reached point - wait
        distance = pos.distance_to(current_point[0], current_point[1])
        if distance < 1.0:
            ai.patrol_timer += ai.think_interval
            ai.state = AIState.IDLE

            if ai.patrol_timer >= ai.patrol_wait_time:
                # Move to next point
                ai.patrol_timer = 0.0
                ai.current_patrol_index = (ai.current_patrol_index + 1) % len(ai.patrol_points)
                next_point = ai.patrol_points[ai.current_patrol_index]

                # Skip pathfinding recalc at high LOD levels
                if self.lod_system.should_do_pathfinding(lod_level):
                    self._set_pathfinding_target_pos(entity, Vec3(*next_point))
        else:
            ai.state = AIState.MOVING
            if self.lod_system.should_do_pathfinding(lod_level):
                self._set_pathfinding_target_pos(entity, Vec3(*current_point))

    def _update_hostile(
        self,
        entity: Entity,
        ai: AIComponent,
        pos: PositionComponent,
        dt: float,
        lod_level: AILODLevel = AILODLevel.NEAR
    ):
        """Hostile - attacks enemies."""
        # Dead NPCs don't act
        combat = entity.get_component(CombatComponent)
        if combat and combat.is_dead:
            ai.state = AIState.DEAD
            return

        # Skip combat processing at very far distances
        if not self.lod_system.should_do_combat(lod_level):
            return

        # If no target - search
        if not ai.target_entity_id:
            if not self.lod_system.should_do_perception(lod_level):
                ai.state = AIState.IDLE
                return

            target = self._find_nearest_enemy(entity, ai, pos)
            if target:
                ai.target_entity_id = target.id
                target_pos_comp = target.get_component(PositionComponent)
                if target_pos_comp:
                    ai.last_known_target_pos = (target_pos_comp.x, target_pos_comp.y, target_pos_comp.z)
                self._post_aggro_event(entity.id, target.id)
            else:
                # Check for NPC enemies
                npc_target = self._find_nearest_npc_enemy(entity, ai, pos)
                if npc_target:
                    ai.target_entity_id = npc_target.id
                    npc_pos = npc_target.get_component(PositionComponent)
                    if npc_pos:
                        ai.last_known_target_pos = (npc_pos.x, npc_pos.y, npc_pos.z)
                    self._post_npc_aggro_event(entity.id, npc_target.id)
                else:
                    # No enemies - return to idle or patrol
                    ai.state = AIState.IDLE
                    return

        # Get target position (can be NPC or player)
        target_position = self._get_target_position(ai.target_entity_id)
        if not target_position:
            # Target lost
            ai.target_entity_id = None
            ai.state = AIState.IDLE
            return

        target_x, target_y, target_z = target_position
        distance = pos.distance_to(target_x, target_y)

        # Update known target position
        ai.last_known_target_pos = (target_x, target_y, target_z)

        # Check leash radius (distance from NPC's starting point)
        if not hasattr(ai, '_home_position'):
            ai._home_position = (pos.x, pos.y, pos.z)
        home = ai._home_position
        dist_from_home = pos.distance_to(home[0], home[1])
        if dist_from_home > ai.leash_radius:
            # Too far from home - return
            ai.target_entity_id = None
            ai.state = AIState.IDLE
            if self.lod_system.should_do_pathfinding(lod_level):
                self._set_pathfinding_target_pos(entity, Vec3(*home))
            return

        # In attack range?
        if distance <= ai.attack_range:
            ai.state = AIState.ATTACKING
            # Attack is processed in CombatAISystem
        else:
            ai.state = AIState.PURSUING
            if self.lod_system.should_do_pathfinding(lod_level):
                self._set_pathfinding_target_pos(entity, Vec3(target_x, target_y, target_z))

    def _update_wander(
        self,
        entity: Entity,
        ai: AIComponent,
        pos: PositionComponent,
        dt: float,
        lod_level: AILODLevel = AILODLevel.NEAR
    ):
        """Wander - random wandering."""
        if ai.wander_center is None:
            ai.wander_center = (pos.x, pos.y, pos.z)

        # Check for enemies (skip at high LOD levels)
        if self.lod_system.should_do_perception(lod_level):
            target = self._find_nearest_enemy(entity, ai, pos)
            if target:
                ai.target_entity_id = target.id
                ai.behavior = AIBehavior.HOSTILE
                return

            # Check for NPC enemies
            npc_target = self._find_nearest_npc_enemy(entity, ai, pos)
            if npc_target:
                ai.target_entity_id = npc_target.id
                ai.behavior = AIBehavior.HOSTILE
                self._post_npc_aggro_event(entity.id, npc_target.id)
                return

        ai.wander_timer += ai.think_interval
        if ai.wander_timer >= ai.wander_interval:
            ai.wander_timer = 0.0

            # Skip new wander target at high LOD levels
            if not self.lod_system.should_do_pathfinding(lod_level):
                return

            # Choose random point
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, ai.wander_radius)
            new_x = ai.wander_center[0] + math.cos(angle) * distance
            new_y = ai.wander_center[1] + math.sin(angle) * distance
            self._set_pathfinding_target_pos(entity, Vec3(new_x, new_y, pos.z))
            ai.state = AIState.MOVING

    def _update_follow(
        self,
        entity: Entity,
        ai: AIComponent,
        pos: PositionComponent,
        dt: float,
        lod_level: AILODLevel = AILODLevel.NEAR
    ):
        """Follow - follows a target."""
        if not ai.target_entity_id:
            ai.state = AIState.IDLE
            return

        target = self._get_target_entity(ai.target_entity_id)
        if not target:
            ai.target_entity_id = None
            ai.state = AIState.IDLE
            return

        target_pos = target.get_component(PositionComponent)
        if not target_pos:
            return

        distance = pos.distance_to(target_pos.x, target_pos.y)

        # Maintain distance
        if distance > 3.0:
            ai.state = AIState.MOVING
            if self.lod_system.should_do_pathfinding(lod_level):
                self._set_pathfinding_target(entity, target)
        else:
            ai.state = AIState.IDLE

    # =========================================================================
    # Living World Integration (needs, schedule overrides)
    # =========================================================================

    def _on_urgent_need(self, data: dict):
        """Handle urgent need from living systems — override NPC behavior."""
        npc_id = data.get("npc_id", "")
        need = data.get("need", "")
        if not npc_id:
            return

        if need == "hunger":
            self._behavior_overrides[npc_id] = "SEEK_FOOD"
        elif need == "energy":
            self._behavior_overrides[npc_id] = "SEEK_REST"
        elif need == "safety":
            self._behavior_overrides[npc_id] = "FLEE"

        logger.debug(f"NPC {npc_id[:8]} urgent need: {need} -> override {self._behavior_overrides.get(npc_id)}")

    def _on_activity_changed(self, data: dict):
        """Handle activity change from schedule — override NPC behavior."""
        npc_id = data.get("npc_id", "")
        activity = data.get("activity", "")
        if not npc_id:
            return

        if activity == "sleeping":
            self._behavior_overrides[npc_id] = "SEEK_REST"
        elif activity == "eating":
            self._behavior_overrides[npc_id] = "SEEK_FOOD"
        elif activity in ("patrolling", "idle", "working", "trading"):
            # Return to default behavior
            self._behavior_overrides.pop(npc_id, None)

        logger.debug(f"NPC {npc_id[:8]} activity changed: {activity}")

    def _update_override(
        self,
        entity: Entity,
        ai: AIComponent,
        pos: PositionComponent,
        dt: float,
        override: str,
        lod_level: AILODLevel = AILODLevel.NEAR
    ):
        """Process behavior override from living world systems."""
        # Placeholder interest points (until proper location system exists)
        FOOD_LOCATION = (5.0, 0.0, 0.0)   # Near merchant
        REST_LOCATION = (0.0, -5.0, 0.0)

        if override == "SEEK_FOOD":
            target = Vec3(*FOOD_LOCATION)
            dist = pos.distance_to(target.x, target.y)
            if dist < 1.5:
                # Arrived at food — satisfy need and clear override
                ai.state = AIState.IDLE
                self._behavior_overrides.pop(entity.id, None)
                if self.event_manager:
                    self.event_manager.post("npc_need_satisfied", {
                        "npc_id": entity.id, "need": "hunger"
                    })
            else:
                ai.state = AIState.MOVING
                if self.lod_system.should_do_pathfinding(lod_level):
                    self._set_pathfinding_target_pos(entity, target)

        elif override == "SEEK_REST":
            target = Vec3(*REST_LOCATION)
            dist = pos.distance_to(target.x, target.y)
            if dist < 1.5:
                ai.state = AIState.IDLE
                self._behavior_overrides.pop(entity.id, None)
                if self.event_manager:
                    self.event_manager.post("npc_need_satisfied", {
                        "npc_id": entity.id, "need": "energy"
                    })
            else:
                ai.state = AIState.MOVING
                if self.lod_system.should_do_pathfinding(lod_level):
                    self._set_pathfinding_target_pos(entity, target)

        elif override == "FLEE":
            # Move away from last known threat
            if ai.last_known_target_pos:
                tx, ty, _ = ai.last_known_target_pos
                dx = pos.x - tx
                dy = pos.y - ty
                length = max(0.1, (dx*dx + dy*dy) ** 0.5)
                flee_x = pos.x + (dx / length) * 10.0
                flee_y = pos.y + (dy / length) * 10.0
                if self.lod_system.should_do_pathfinding(lod_level):
                    self._set_pathfinding_target_pos(entity, Vec3(flee_x, flee_y, pos.z))
                ai.state = AIState.FLEEING
            else:
                # No known threat — clear override
                self._behavior_overrides.pop(entity.id, None)
                ai.state = AIState.IDLE

    # =========================================================================
    # Вспомогательные методы
    # =========================================================================

    def _find_nearest_enemy(
        self,
        entity: Entity,
        ai: AIComponent,
        pos: PositionComponent
    ) -> Optional[Entity]:
        """
        Find nearest enemy within aggro radius.

        Uses spatial hash when available for O(k) complexity instead of O(n).

        Behavior:
        - If FactionComponent exists: uses faction.hostile_to_players
        - If no FactionComponent: uses AIBehavior.HOSTILE to determine hostility
        """
        # No players available
        if not self._player_data:
            return None

        # Check hostility
        faction = entity.get_component(FactionComponent)
        if faction:
            # Use faction disposition
            is_hostile = faction.hostile_to_players or self._is_enemy_faction(faction, "player")
        else:
            # Fallback: HOSTILE behavior attacks players automatically
            is_hostile = (ai.behavior == AIBehavior.HOSTILE)

        if not is_hostile:
            return None

        nearest = None
        nearest_dist = float('inf')

        # Use spatial hash for nearby players if available
        if self.spatial_hash:
            # Get nearby player entities from spatial hash
            nearby_ids = self.spatial_hash.get_nearby_entities(
                pos.x, pos.y, ai.aggro_radius, exclude_entity=entity.id
            )

            for player_id in nearby_ids:
                # Check if this is a player (in our cached positions)
                player_pos = self._player_positions_dict.get(player_id)
                if player_pos:
                    px, py, pz = player_pos
                    dist = pos.distance_to(px, py)

                    if dist <= ai.aggro_radius and dist < nearest_dist:
                        nearest_dist = dist
                        # Find original player data to create entity
                        for player in self._player_data:
                            if player.get("uuid") == player_id:
                                nearest = self._create_player_entity(player)
                                break
        else:
            # Fallback: check all players (O(n))
            for player in self._player_data:
                player_pos = player.get("position", {})
                px, py = player_pos.get("x", 0), player_pos.get("y", 0)
                dist = pos.distance_to(px, py)

                if dist <= ai.aggro_radius and dist < nearest_dist:
                    nearest_dist = dist
                    # Create temporary entity for player
                    nearest = self._create_player_entity(player)

        return nearest

    def _find_nearest_npc_enemy(
        self,
        entity: Entity,
        ai: AIComponent,
        pos: PositionComponent
    ) -> Optional[Entity]:
        """
        Find nearest hostile NPC within aggro radius.

        Scans other NPC entities in the ECS world using faction hostility.
        Uses spatial hash when available for O(k) complexity.
        """
        if not self._world:
            return None

        faction = entity.get_component(FactionComponent)
        if not faction:
            return None

        nearest = None
        nearest_dist = float('inf')

        if self.spatial_hash:
            nearby_ids = self.spatial_hash.get_nearby_entities(
                pos.x, pos.y, ai.aggro_radius, exclude_entity=entity.id
            )
            for other_id in nearby_ids:
                other = self._world.get_entity(other_id)
                if not other or other.id == entity.id:
                    continue
                other_faction = other.get_component(FactionComponent)
                other_combat = other.get_component(CombatComponent)
                other_pos = other.get_component(PositionComponent)
                if not other_faction or not other_combat or not other_pos:
                    continue
                if other_combat.is_dead:
                    continue
                if not self._is_enemy_faction(faction, other_faction.faction_id):
                    continue
                dist = pos.distance_to(other_pos.x, other_pos.y)
                if dist <= ai.aggro_radius and dist < nearest_dist:
                    nearest_dist = dist
                    nearest = other
        else:
            # Fallback: iterate all entities with FactionComponent
            for other in self._world.get_entities_with_components(FactionComponent):
                if other.id == entity.id:
                    continue
                other_faction = other.get_component(FactionComponent)
                other_combat = other.get_component(CombatComponent)
                other_pos = other.get_component(PositionComponent)
                if not other_faction or not other_combat or not other_pos:
                    continue
                if other_combat.is_dead:
                    continue
                if not self._is_enemy_faction(faction, other_faction.faction_id):
                    continue
                dist = pos.distance_to(other_pos.x, other_pos.y)
                if dist <= ai.aggro_radius and dist < nearest_dist:
                    nearest_dist = dist
                    nearest = other

        return nearest

    def _is_enemy_faction(self, faction: FactionComponent, target_faction: str) -> bool:
        """Check if faction is hostile to target faction."""
        if target_faction in faction.disposition_overrides:
            return faction.disposition_overrides[target_faction] < 0
        # Check global hostility matrix (order-independent key)
        pair = tuple(sorted([faction.faction_id, target_faction]))
        return self.FACTION_HOSTILITY.get(pair, False)

    def _get_target_entity(self, entity_id: str) -> Optional[Entity]:
        """Получает entity цели."""
        if not self._world:
            return None
        return self._world.get_entity(entity_id)

    def _get_target_position(self, target_id: str) -> Optional[tuple]:
        """
        Получает позицию цели (NPC или игрока).

        Args:
            target_id: ID цели (entity_id для NPC или client_id для игрока)

        Returns:
            (x, y, z) или None если цель не найдена
        """
        # Сначала проверяем NPC в ECS world
        if self._world:
            entity = self._world.get_entity(target_id)
            if entity:
                pos = entity.get_component(PositionComponent)
                if pos:
                    return (pos.x, pos.y, pos.z)

        # Проверяем игроков в кэше
        for player in self._player_data:
            if player.get("uuid") == target_id:
                pos = player.get("position", {})
                return (pos.get("x", 0), pos.get("y", 0), pos.get("z", 0))

        return None

    def _set_pathfinding_target(self, entity: Entity, target: Entity) -> None:
        """Устанавливает цель pathfinding на другую entity."""
        pathfinding = entity.get_component(PathfindingComponent)
        target_pos = target.get_component(PositionComponent)

        if pathfinding and target_pos:
            pathfinding.target_position = Vec3(target_pos.x, target_pos.y, target_pos.z)
            pathfinding.needs_repath = True

    def _set_pathfinding_target_pos(self, entity: Entity, target: Vec3) -> None:
        """Устанавливает цель pathfinding на позицию."""
        pathfinding = entity.get_component(PathfindingComponent)
        if pathfinding:
            pathfinding.target_position = target
            pathfinding.needs_repath = True

    def _create_player_entity(self, player_data: dict) -> Entity:
        """Создаёт временную entity для игрока (для targeting)."""
        entity = Entity(player_data.get("uuid", "player"))
        pos = player_data.get("position", {})
        entity.add_component(PositionComponent(
            x=pos.get("x", 0),
            y=pos.get("y", 0),
            z=pos.get("z", 0)
        ))
        return entity

    def _post_aggro_event(self, npc_id: str, target_id: str) -> None:
        """Post aggro event to start combat."""
        # Use injected event_manager, fallback to npc_manager for compatibility
        event_mgr = self.event_manager
        if not event_mgr and self.npc_manager:
            event_mgr = self.npc_manager.event_manager

        if event_mgr:
            event_mgr.post("npc_aggro_player", {
                "npc_id": npc_id,
                "player_id": target_id
            })
            logger.debug(f"NPC {npc_id[:8]} aggro on {target_id[:8]}")

    def _post_npc_aggro_event(self, npc_id: str, target_npc_id: str) -> None:
        """Post aggro event for NPC-on-NPC combat."""
        event_mgr = self.event_manager
        if not event_mgr and self.npc_manager:
            event_mgr = self.npc_manager.event_manager

        if event_mgr:
            event_mgr.post("npc_aggro_npc", {
                "attacker_id": npc_id,
                "target_id": target_npc_id,
            })
            logger.debug(f"NPC {npc_id[:8]} aggro on NPC {target_npc_id[:8]}")

    def on_entity_removed(self, entity: Entity) -> None:
        """Called when entity is removed from the system."""
        # Clean up LOD tracking
        self.lod_system.remove_entity(entity.id)
        self._think_accumulators.pop(entity.id, None)
        self._behavior_overrides.pop(entity.id, None)

    def get_lod_stats(self) -> Dict:
        """Get AI LOD statistics."""
        return self.lod_system.get_stats()

    def set_spatial_hash(self, spatial_hash: 'SpatialHash') -> None:
        """Set spatial hash for fast neighbor queries."""
        self.spatial_hash = spatial_hash


# =============================================================================
# Pathfinding System — движение NPC
# =============================================================================

class PathfindingSystem(System):
    """
    Система навигации. Вычисляет пути и двигает NPC.
    """

    required_components = [PositionComponent, PathfindingComponent]
    priority = 20  # После AI

    def __init__(self, pathfinder: GridPathfinder = None):
        super().__init__()
        self.pathfinder = pathfinder

    def update(self, dt: float, entities: List[Entity]) -> None:
        for entity in entities:
            pos = entity.get_component(PositionComponent)
            pathfinding = entity.get_component(PathfindingComponent)
            ai = entity.get_component(AIComponent)

            # Пропускаем мёртвых
            combat = entity.get_component(CombatComponent)
            if combat and combat.is_dead:
                continue

            # Нужно пересчитать путь?
            if pathfinding.needs_repath and pathfinding.target_position:
                self._calculate_path(entity, pos, pathfinding)

            # Двигаемся по пути
            if pathfinding.current_path:
                self._follow_path(entity, pos, pathfinding, ai, dt)

    def _calculate_path(self, entity: Entity, pos: PositionComponent, pathfinding: PathfindingComponent):
        """Вычисляет путь к цели."""
        pathfinding.needs_repath = False

        if not self.pathfinder:
            # Без pathfinder — идём напрямую
            pathfinding.current_path = [pathfinding.target_position]
            pathfinding.current_waypoint_index = 0
            return

        start = (pos.x, pos.y, pos.z)
        end = (pathfinding.target_position.x, pathfinding.target_position.y, pathfinding.target_position.z)

        result = self.pathfinder.find_path(start, end)
        if result.found:
            pathfinding.current_path = result.path
            pathfinding.current_waypoint_index = 0
            pathfinding.is_stuck = False
        else:
            pathfinding.current_path = []
            logger.debug(f"No path found for entity {entity.id[:8]}")

    def _follow_path(self, entity: Entity, pos: PositionComponent, pathfinding: PathfindingComponent, ai: Optional[AIComponent], dt: float):
        """Следует по пути."""
        if pathfinding.current_waypoint_index >= len(pathfinding.current_path):
            pathfinding.current_path = []
            self._set_npc_animation(entity, "idle")
            return

        target = pathfinding.current_path[pathfinding.current_waypoint_index]
        current_pos = Vec3(pos.x, pos.y, pos.z)

        # Вычисляем steering force
        move_speed = ai.move_speed if ai else pathfinding.max_speed

        steering, new_index = SteeringBehaviors.follow_path(
            current_pos,
            pathfinding.velocity,
            pathfinding.current_path,
            pathfinding.current_waypoint_index,
            move_speed,
            pathfinding.max_force,
            pathfinding.waypoint_radius
        )

        pathfinding.current_waypoint_index = new_index

        # Обновляем velocity
        pathfinding.velocity = pathfinding.velocity + steering * dt
        if pathfinding.velocity.length() > move_speed:
            pathfinding.velocity.normalize()
            pathfinding.velocity *= move_speed

        # Обновляем позицию
        new_pos = current_pos + pathfinding.velocity * dt
        pos.x = new_pos.x
        pos.y = new_pos.y
        # Z обновляется отдельно (из heightmap или collision)

        pos.velocity_x = pathfinding.velocity.x
        pos.velocity_y = pathfinding.velocity.y

        # Поворачиваем в направлении движения (Panda3D heading convention)
        speed = pathfinding.velocity.length()
        if speed > 0.1:
            # Model faces -Y at H=0.  atan2(vx, vy) gives angle from +Y,
            # so add 180° to flip the model to face the movement direction.
            pos.rotation = 180.0 - math.degrees(math.atan2(pathfinding.velocity.x, pathfinding.velocity.y))

        # Обновляем анимацию NPC на основе скорости
        if speed > 0.1:
            self._set_npc_animation(entity, "walk_forward")
        else:
            self._set_npc_animation(entity, "idle")

        # Проверяем застревание
        if speed < 0.1:
            pathfinding.stuck_timer += dt
            if pathfinding.stuck_timer > pathfinding.stuck_threshold:
                pathfinding.is_stuck = True
                pathfinding.needs_repath = True
                pathfinding.stuck_timer = 0.0
        else:
            pathfinding.stuck_timer = 0.0

        # Достигли конца пути?
        if pathfinding.current_waypoint_index >= len(pathfinding.current_path):
            pathfinding.current_path = []
            pathfinding.velocity = Vec3(0, 0, 0)
            pos.velocity_x = 0
            pos.velocity_y = 0
            self._set_npc_animation(entity, "idle")

    @staticmethod
    def _set_npc_animation(entity: Entity, anim_name: str):
        """Updates the NPC's ModelComponent animation state."""
        model = entity.get_component(ModelComponent)
        if model and model.current_animation != anim_name:
            model.current_animation = anim_name


# =============================================================================
# Combat AI System — боевые решения
# =============================================================================

class CombatAISystem(System):
    """
    Система боевого AI. Обрабатывает атаки NPC.
    """

    required_components = [AIComponent, CombatComponent, PositionComponent]
    priority = 30  # После pathfinding

    def __init__(self, npc_manager: 'NPCManager' = None, event_manager: Optional['EventManager'] = None):
        super().__init__()
        self.npc_manager = npc_manager  # DEPRECATED: kept for backward compatibility
        self.event_manager = event_manager

    def update(self, dt: float, entities: List[Entity]) -> None:
        for entity in entities:
            ai = entity.get_component(AIComponent)
            combat = entity.get_component(CombatComponent)
            pos = entity.get_component(PositionComponent)

            if combat.is_dead:
                continue

            # Обновляем кулдаун атаки
            if combat.attack_timer > 0:
                combat.attack_timer -= dt

            # Атакуем если в состоянии атаки
            if ai.state == AIState.ATTACKING and combat.attack_timer <= 0:
                self._perform_attack(entity, ai, combat, pos)

    def _perform_attack(self, entity: Entity, ai: AIComponent, combat: CombatComponent, pos: PositionComponent):
        """Выполняет атаку."""
        if not ai.target_entity_id:
            return

        # Use injected event_manager, fallback to npc_manager for compatibility
        event_mgr = self.event_manager
        if not event_mgr and self.npc_manager:
            event_mgr = self.npc_manager.event_manager

        if not event_mgr:
            return

        # Сбрасываем кулдаун
        combat.attack_timer = combat.attack_cooldown

        # Отправляем событие атаки
        event_mgr.post("npc_attack", {
            "attacker_id": entity.id,
            "target_id": ai.target_entity_id,
            "attack_bonus": combat.attack_bonus,
            "damage_dice": combat.damage_dice,
            "damage_bonus": combat.damage_bonus,
            "damage_type": combat.damage_type,
            "position": {"x": pos.x, "y": pos.y, "z": pos.z}
        })

        logger.debug(f"NPC {entity.id[:8]} attacks {ai.target_entity_id[:8]}")
