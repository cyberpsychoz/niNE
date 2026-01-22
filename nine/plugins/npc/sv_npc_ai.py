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

    def __init__(
        self,
        npc_manager: 'NPCManager' = None,
        lod_system: Optional[AILODSystem] = None,
        spatial_hash: Optional['SpatialHash'] = None
    ):
        super().__init__()
        self.npc_manager = npc_manager
        self._think_accumulators: Dict[str, float] = {}

        # AI LOD system for distance-based throttling
        self.lod_system = lod_system or AILODSystem()

        # Spatial hash for fast neighbor queries (set by NPCManager)
        self.spatial_hash: Optional['SpatialHash'] = spatial_hash

        # Cached player positions (updated each tick)
        self._player_positions: List[Tuple[float, float]] = []
        self._player_positions_dict: Dict[str, Tuple[float, float, float]] = {}

        # Performance tracking
        self._tick_count = 0
        self._total_think_time = 0.0

    def update(self, dt: float, entities: List[Entity]) -> None:
        """
        Update AI for all entities.

        Uses LOD-based throttling to reduce CPU usage for distant NPCs.
        """
        self._tick_count += 1
        current_time = time.time()

        # Update cached player positions
        self._update_player_cache()

        # Track LOD distribution for stats
        lod_counts = {level: 0 for level in AILODLevel}

        for entity in entities:
            ai = entity.get_component(AIComponent)
            pos = entity.get_component(PositionComponent)

            # Dead NPCs don't think
            combat = entity.get_component(CombatComponent)
            if combat and combat.is_dead:
                ai.state = AIState.DEAD
                continue

            entity_id = entity.id

            # Calculate LOD level based on distance to players
            lod_level = self.lod_system.get_lod_level(
                pos.x, pos.y, self._player_positions
            )
            lod_counts[lod_level] += 1

            # Store LOD level on AI component for other systems
            ai.lod_level = int(lod_level)

            # Check if NPC should think this tick (LOD-based throttling)
            if not self.lod_system.should_think(entity_id, lod_level, current_time):
                continue

            # Update AI based on behavior
            if ai.behavior == AIBehavior.IDLE:
                self._update_idle(entity, ai, pos, dt, lod_level)
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

    def _update_player_cache(self) -> None:
        """Update cached player positions for LOD calculations."""
        self._player_positions.clear()
        self._player_positions_dict.clear()

        if not self.npc_manager:
            return

        for player in self.npc_manager.get_players():
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
        """Idle - stands in place, but can react to enemies."""
        ai.state = AIState.IDLE

        # Skip perception at high LOD levels
        if not self.lod_system.should_do_perception(lod_level):
            return

        # Check for enemies
        if self.npc_manager:
            target = self._find_nearest_enemy(entity, ai, pos)
            if target:
                ai.target_entity_id = target.id
                ai.behavior = AIBehavior.HOSTILE
                ai.state = AIState.PURSUING
                # Post aggro event to start combat
                self._post_aggro_event(entity.id, target.id)

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
        if self.npc_manager and self.lod_system.should_do_perception(lod_level):
            target = self._find_nearest_enemy(entity, ai, pos)
            if target:
                ai.target_entity_id = target.id
                ai.state = AIState.PURSUING
                self._set_pathfinding_target(entity, target)
                # Post aggro event to start combat
                self._post_aggro_event(entity.id, target.id)
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
                # Save target position
                target_pos_comp = target.get_component(PositionComponent)
                if target_pos_comp:
                    ai.last_known_target_pos = (target_pos_comp.x, target_pos_comp.y, target_pos_comp.z)
                # Post aggro event to start combat
                self._post_aggro_event(entity.id, target.id)
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
        if self.npc_manager and self.lod_system.should_do_perception(lod_level):
            target = self._find_nearest_enemy(entity, ai, pos)
            if target:
                ai.target_entity_id = target.id
                ai.behavior = AIBehavior.HOSTILE
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
        """
        if not self.npc_manager:
            return None

        faction = entity.get_component(FactionComponent)
        if not faction:
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

                    if dist <= ai.aggro_radius:
                        # Check hostility
                        if faction.hostile_to_players or self._is_enemy_faction(faction, "player"):
                            if dist < nearest_dist:
                                nearest_dist = dist
                                # Find original player data to create entity
                                for player in self.npc_manager.get_players():
                                    if player.get("uuid") == player_id:
                                        nearest = self._create_player_entity(player)
                                        break
        else:
            # Fallback: check all players (O(n))
            for player in self.npc_manager.get_players():
                player_pos = player.get("position", {})
                px, py = player_pos.get("x", 0), player_pos.get("y", 0)
                dist = pos.distance_to(px, py)

                if dist <= ai.aggro_radius:
                    # Check hostility
                    if faction.hostile_to_players or self._is_enemy_faction(faction, "player"):
                        if dist < nearest_dist:
                            nearest_dist = dist
                            # Create temporary entity for player
                            nearest = self._create_player_entity(player)

        return nearest

    def _is_enemy_faction(self, faction: FactionComponent, target_faction: str) -> bool:
        """Проверяет, враждебна ли фракция."""
        if target_faction in faction.disposition_overrides:
            return faction.disposition_overrides[target_faction] < 0
        # TODO: Проверить глобальные отношения фракций
        return False

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
        if self.npc_manager:
            for player in self.npc_manager.get_players():
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
        if self.npc_manager:
            self.npc_manager.event_manager.post("npc_aggro_player", {
                "npc_id": npc_id,
                "player_id": target_id
            })
            logger.debug(f"NPC {npc_id[:8]} aggro on {target_id[:8]}")

    def on_entity_removed(self, entity: Entity) -> None:
        """Called when entity is removed from the system."""
        # Clean up LOD tracking
        self.lod_system.remove_entity(entity.id)
        self._think_accumulators.pop(entity.id, None)

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

        # Поворачиваем в направлении движения
        if pathfinding.velocity.length() > 0.1:
            pos.rotation = math.degrees(math.atan2(pathfinding.velocity.y, pathfinding.velocity.x))

        # Проверяем застревание
        if pathfinding.velocity.length() < 0.1:
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


# =============================================================================
# Combat AI System — боевые решения
# =============================================================================

class CombatAISystem(System):
    """
    Система боевого AI. Обрабатывает атаки NPC.
    """

    required_components = [AIComponent, CombatComponent, PositionComponent]
    priority = 30  # После pathfinding

    def __init__(self, npc_manager: 'NPCManager' = None):
        super().__init__()
        self.npc_manager = npc_manager

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
        if not ai.target_entity_id or not self.npc_manager:
            return

        # Сбрасываем кулдаун
        combat.attack_timer = combat.attack_cooldown

        # Отправляем событие атаки
        self.npc_manager.event_manager.post("npc_attack", {
            "attacker_id": entity.id,
            "target_id": ai.target_entity_id,
            "attack_bonus": combat.attack_bonus,
            "damage_dice": combat.damage_dice,
            "damage_bonus": combat.damage_bonus,
            "damage_type": combat.damage_type,
            "position": {"x": pos.x, "y": pos.y, "z": pos.z}
        })

        logger.debug(f"NPC {entity.id[:8]} attacks {ai.target_entity_id[:8]}")
