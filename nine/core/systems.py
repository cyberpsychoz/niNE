"""
ECS Systems for niNE.

Systems process entities with specific components and contain the game logic.
Each system operates on entities that have the required components.

Usage:
    world = ECSWorld()
    world.add_system(PhysicsSystem(render, cTrav))
    world.add_system(InputSystem())
    world.add_system(AISystem())
    world.add_system(AnimationSystem())
    world.add_system(NetworkSyncSystem())

    # In game loop
    world.update(dt)
"""

from __future__ import annotations

import logging
from math import atan2, degrees, radians, sin, cos
from typing import List, Dict, Optional, Any, TYPE_CHECKING

from panda3d.core import (
    LVector3, NodePath, BitMask32, Point3,
    CollisionSphere, CollisionNode, CollisionRay,
    CollisionHandlerPusher, CollisionHandlerQueue,
    CollisionTraverser
)

from nine.core.ecs import System, Entity, ECSWorld
from nine.core.components import (
    TransformComponent,
    VelocityComponent,
    ModelComponent,
    PawnComponent,
    PhysicsComponent,
    PhysicsTier,
    HealthComponent,
    InputComponent,
    AIControllerComponent,
    PathfindingComponent,
    NetworkSyncComponent,
    WorldBoundsComponent,
    PawnType,
    AIBehavior,
    AIState,
)

if TYPE_CHECKING:
    from nine.core.pathfinder import GridPathfinder

logger = logging.getLogger(__name__)


# =============================================================================
# Collision Masks
# =============================================================================

WALL_MASK = BitMask32.bit(1)
FLOOR_MASK = BitMask32.bit(2)


# =============================================================================
# Physics System
# =============================================================================

class PhysicsSystem(System):
    """
    Handles physics simulation for all Pawns with PhysicsComponent.

    Responsible for:
    - Movement based on velocity
    - Gravity
    - Ground detection
    - Wall collision
    """

    required_components = [PawnComponent, TransformComponent, PhysicsComponent, VelocityComponent]
    priority = 10  # Run early

    def __init__(self, render: NodePath, cTrav: CollisionTraverser):
        super().__init__()
        self.render = render
        self.cTrav = cTrav

        # Track physics data per entity (FULL tier only)
        self._physics_data: Dict[str, PhysicsEntityData] = {}

        # World bounds (cached from WorldBoundsComponent)
        self._world_bounds: Optional[WorldBoundsComponent] = None

        # Ground height cache for SIMPLE tier NPC
        self._ground_z_cache: Dict[str, float] = {}  # entity_id -> cached ground z
        self._ground_ray_budget: int = 10  # Max ray casts per frame for SIMPLE tier
        self._ground_ray_queue: List[str] = []  # Round-robin queue of entity IDs

    def on_entity_added(self, entity: Entity) -> None:
        """Setup collision for new entity."""
        if entity.id in self._physics_data:
            return

        physics = entity.get_component(PhysicsComponent)
        if not physics or not physics.has_collision:
            return

        # Only FULL tier gets Panda3D collision nodes
        if physics.tier == PhysicsTier.FULL:
            data = PhysicsEntityData()
            data.setup_collision(entity.id, self.render, self.cTrav, physics)
            self._physics_data[entity.id] = data
            logger.debug(f"[PhysicsSystem] Setup FULL collision for entity {entity.id[:8]}")
        elif physics.tier == PhysicsTier.SIMPLE:
            # SIMPLE tier: add to ground ray round-robin queue
            self._ground_ray_queue.append(entity.id)
            logger.debug(f"[PhysicsSystem] Setup SIMPLE physics for entity {entity.id[:8]}")

    def on_entity_removed(self, entity: Entity) -> None:
        """Cleanup collision for removed entity."""
        if entity.id in self._physics_data:
            self._physics_data[entity.id].cleanup(self.cTrav)
            del self._physics_data[entity.id]
            logger.debug(f"[PhysicsSystem] Cleaned up collision for entity {entity.id[:8]}")
        # Clean up SIMPLE tier data
        self._ground_z_cache.pop(entity.id, None)
        if entity.id in self._ground_ray_queue:
            self._ground_ray_queue.remove(entity.id)

    def update(self, dt: float, entities: List[Entity]) -> None:
        """Update physics for all entities, branching by PhysicsTier."""
        # Cache world bounds on first frame
        if self._world_bounds is None and self._world:
            for e in self._world.get_entities_with_components(WorldBoundsComponent):
                self._world_bounds = e.get_component(WorldBoundsComponent)
                break

        for entity in entities:
            physics = entity.get_component(PhysicsComponent)
            if not physics:
                continue

            if physics.tier == PhysicsTier.NONE:
                continue
            elif physics.tier == PhysicsTier.SIMPLE:
                self._update_simple_physics(entity, dt)
            else:
                # FULL tier — original collision-based physics
                self._update_entity_physics(entity, dt)

    def _update_entity_physics(self, entity: Entity, dt: float) -> None:
        """Update physics for a single entity."""
        transform = entity.get_component(TransformComponent)
        velocity = entity.get_component(VelocityComponent)
        physics = entity.get_component(PhysicsComponent)

        if not all([transform, velocity, physics]):
            return

        data = self._physics_data.get(entity.id)

        # Check ground (uses results from previous frame's traversal)
        if data:
            self._check_ground(entity, data, physics, velocity)

        # Apply gravity if not on ground
        if not physics.is_on_ground:
            velocity.vz -= physics.gravity * dt
            if velocity.vz < -physics.max_fall_speed:
                velocity.vz = -physics.max_fall_speed
        elif velocity.vz < 0:
            velocity.vz = 0

        # Apply friction on ground
        if physics.is_on_ground and not physics.is_running:
            self._apply_friction(velocity, physics, dt)

        # Update position from velocity
        new_x = transform.x + velocity.vx * dt
        new_y = transform.y + velocity.vy * dt
        new_z = transform.z + velocity.vz * dt

        # Update actor position if we have collision data
        if data and data.actor_np:
            data.actor_np.setFluidPos(new_x, new_y, new_z)
            actual_pos = data.actor_np.getPos()
            transform.x = actual_pos.x
            transform.y = actual_pos.y
            transform.z = actual_pos.z
        else:
            transform.x = new_x
            transform.y = new_y
            transform.z = new_z

        # Update rotation
        horiz_speed = velocity.speed_horizontal()
        if horiz_speed > 0.1:
            target_heading = degrees(atan2(-velocity.vx, velocity.vy)) + 180
            current_heading = transform.rotation
            diff = (target_heading - current_heading + 180) % 360 - 180
            transform.rotation = current_heading + diff * physics.rotation_speed * dt

            if data and data.actor_np:
                data.actor_np.setH(transform.rotation)

    def _update_simple_physics(self, entity: Entity, dt: float) -> None:
        """
        SIMPLE tier physics for NPC.
        Applies velocity to position, clamps to world bounds, snaps to cached ground Z.
        No Panda3D collision nodes — much cheaper than FULL tier.
        """
        transform = entity.get_component(TransformComponent)
        velocity = entity.get_component(VelocityComponent)
        physics = entity.get_component(PhysicsComponent)

        if not all([transform, velocity, physics]):
            return

        # Apply velocity to position
        if abs(velocity.vx) > 0.001 or abs(velocity.vy) > 0.001:
            transform.x += velocity.vx * dt
            transform.y += velocity.vy * dt

            # Update rotation to face movement direction
            horiz_speed = velocity.speed_horizontal()
            if horiz_speed > 0.05:
                target_heading = degrees(atan2(-velocity.vx, velocity.vy)) + 180
                current_heading = transform.rotation
                diff = (target_heading - current_heading + 180) % 360 - 180
                transform.rotation = current_heading + diff * min(physics.rotation_speed * dt, 1.0)

        # Apply friction (NPC slow down when AI stops commanding movement)
        speed = velocity.speed_horizontal()
        if speed > 0.001:
            # Simple linear decay — NPC decelerate smoothly
            decay = min(physics.friction * dt, 1.0)
            velocity.vx *= max(0, 1.0 - decay)
            velocity.vy *= max(0, 1.0 - decay)
        else:
            velocity.vx = 0
            velocity.vy = 0

        # Snap to cached ground Z (updated periodically via round-robin ray casts)
        cached_z = self._ground_z_cache.get(entity.id)
        if cached_z is not None:
            transform.z = cached_z
        # If no cached ground, keep current Z (NPC won't fall through void)

        # World bounds clamping
        self._clamp_to_world_bounds(transform, entity)

        # Sync interpolation velocity on TransformComponent
        transform.velocity_x = velocity.vx
        transform.velocity_y = velocity.vy

    def _clamp_to_world_bounds(self, transform: TransformComponent, entity: Entity) -> None:
        """Clamp entity position to world boundaries. Kill plane teleports to origin."""
        wb = self._world_bounds
        if not wb:
            return

        transform.x = max(wb.min_x, min(wb.max_x, transform.x))
        transform.y = max(wb.min_y, min(wb.max_y, transform.y))

        # Kill plane — teleport back to origin if below min_z
        if transform.z < wb.min_z:
            logger.warning(f"[PhysicsSystem] Entity {entity.id[:8]} fell below kill plane, resetting")
            transform.x = 0
            transform.y = 0
            transform.z = 1.0

    def _check_ground(self, entity: Entity, data: 'PhysicsEntityData',
                      physics: PhysicsComponent, velocity: VelocityComponent) -> None:
        """Check if entity is on ground using ray cast."""
        if physics.is_jumping and velocity.vz > 0:
            physics.is_on_ground = False
            return

        if physics.is_jumping and velocity.vz <= 0:
            physics.is_jumping = False

        if not data.ground_queue:
            return

        num_entries = data.ground_queue.getNumEntries()
        if num_entries == 0:
            physics.is_on_ground = False
            return

        data.ground_queue.sortEntries()
        entry = data.ground_queue.getEntry(0)
        surface_point = entry.getSurfacePoint(self.render)

        current_z = data.actor_np.getZ() if data.actor_np else 0
        ground_distance = current_z - surface_point.z

        step_height = 0.5
        snap_threshold = 0.05

        if ground_distance <= step_height and ground_distance >= -0.1:
            if velocity.vz <= 0 and not physics.is_jumping:
                physics.is_on_ground = True
                if abs(ground_distance) > snap_threshold and data.actor_np:
                    data.actor_np.setZ(surface_point.z)
                velocity.vz = 0
            else:
                physics.is_on_ground = False
        elif ground_distance < -0.1:
            physics.is_on_ground = True
            if data.actor_np:
                data.actor_np.setZ(surface_point.z)
            velocity.vz = 0
        else:
            physics.is_on_ground = False

    def _apply_friction(self, velocity: VelocityComponent, physics: PhysicsComponent, dt: float) -> None:
        """Apply friction to slow down horizontal movement."""
        speed = velocity.speed_horizontal()
        if speed < 0.001:
            velocity.vx = 0
            velocity.vy = 0
            return

        stop_speed = 0.01
        control = max(speed, stop_speed)
        drop = control * physics.friction * dt
        new_speed = max(speed - drop, 0)

        if speed > 0:
            scale = new_speed / speed
            velocity.vx *= scale
            velocity.vy *= scale

    def jump(self, entity: Entity) -> bool:
        """Make entity jump if on ground."""
        physics = entity.get_component(PhysicsComponent)
        velocity = entity.get_component(VelocityComponent)

        if not physics or not velocity:
            return False

        if physics.is_on_ground:
            velocity.vz = physics.jump_speed
            physics.is_on_ground = False
            physics.is_jumping = True
            return True

        return False


class PhysicsEntityData:
    """Collision data for a single entity."""

    def __init__(self):
        self.actor_np: Optional[NodePath] = None
        self.collision_np: Optional[NodePath] = None
        self.ground_ray_np: Optional[NodePath] = None
        self.pusher: Optional[CollisionHandlerPusher] = None
        self.ground_queue: Optional[CollisionHandlerQueue] = None

    def setup_collision(self, entity_id: str, render: NodePath,
                       cTrav: CollisionTraverser, physics: PhysicsComponent) -> None:
        """Setup Panda3D collision nodes."""
        # Create actor node
        self.actor_np = render.attachNewNode(f"pawn_{entity_id[:8]}")

        # Character collision sphere
        collision_node = CollisionNode(f"collision_{entity_id[:8]}")
        collision_node.addSolid(CollisionSphere(0, 0, 0.5, physics.collision_radius))
        collision_node.addSolid(CollisionSphere(0, 0, 1.3, physics.collision_radius * 0.75))
        collision_node.setFromCollideMask(WALL_MASK)
        collision_node.setIntoCollideMask(BitMask32.allOff())
        self.collision_np = self.actor_np.attachNewNode(collision_node)

        # Ground detection ray
        ground_ray = CollisionRay()
        ground_ray.setOrigin(0, 0, 0.5)
        ground_ray.setDirection(0, 0, -1)

        ground_ray_node = CollisionNode(f"ground_ray_{entity_id[:8]}")
        ground_ray_node.addSolid(ground_ray)
        ground_ray_node.setFromCollideMask(FLOOR_MASK)
        ground_ray_node.setIntoCollideMask(BitMask32.allOff())
        self.ground_ray_np = self.actor_np.attachNewNode(ground_ray_node)

        # Collision handlers
        self.pusher = CollisionHandlerPusher()
        self.pusher.addCollider(self.collision_np, self.actor_np)
        self.pusher.setHorizontal(True)

        self.ground_queue = CollisionHandlerQueue()

        # Register with traverser
        cTrav.addCollider(self.collision_np, self.pusher)
        cTrav.addCollider(self.ground_ray_np, self.ground_queue)

    def cleanup(self, cTrav: CollisionTraverser) -> None:
        """Remove collision nodes."""
        if self.collision_np:
            cTrav.removeCollider(self.collision_np)
            self.collision_np.removeNode()
        if self.ground_ray_np:
            cTrav.removeCollider(self.ground_ray_np)
            self.ground_ray_np.removeNode()
        if self.actor_np:
            self.actor_np.removeNode()


# =============================================================================
# Input System
# =============================================================================

class InputSystem(System):
    """
    Processes input for player-controlled Pawns.

    Converts input state (keys, camera direction) into velocity.
    """

    required_components = [PawnComponent, InputComponent, VelocityComponent, PhysicsComponent]
    priority = 5  # Run before physics

    def update(self, dt: float, entities: List[Entity]) -> None:
        """Process input for all player entities."""
        for entity in entities:
            pawn = entity.get_component(PawnComponent)
            if pawn.pawn_type != PawnType.PLAYER:
                continue

            self._process_player_input(entity, dt)

    def _process_player_input(self, entity: Entity, dt: float) -> None:
        """Convert player input to velocity."""
        input_comp = entity.get_component(InputComponent)
        velocity = entity.get_component(VelocityComponent)
        physics = entity.get_component(PhysicsComponent)

        if not all([input_comp, velocity, physics]):
            return

        keys = input_comp.keys

        # Calculate input vector
        input_x = 0
        input_y = 0
        if keys.get("w"):
            input_y += 1
        if keys.get("s"):
            input_y -= 1
        if keys.get("a"):
            input_x -= 1
        if keys.get("d"):
            input_x += 1

        if input_x == 0 and input_y == 0:
            physics.is_running = False
            return

        # Convert to world-space movement based on camera yaw
        yaw_rad = radians(input_comp.camera_yaw)
        forward = LVector3(-sin(yaw_rad), cos(yaw_rad), 0)
        right = LVector3(cos(yaw_rad), sin(yaw_rad), 0)

        move_dir = forward * input_y + right * input_x
        move_dir.normalize()

        # Set running state
        physics.is_running = keys.get("shift", False)

        # Determine speed
        wish_speed = physics.run_speed if physics.is_running else physics.walk_speed

        # Acceleration
        accel = physics.ground_accel if physics.is_on_ground else physics.air_accel

        # Current speed in wish direction
        current_speed = velocity.vx * move_dir.x + velocity.vy * move_dir.y
        add_speed = wish_speed - current_speed

        if add_speed > 0:
            accel_speed = min(accel * wish_speed * dt, add_speed)
            velocity.vx += accel_speed * move_dir.x
            velocity.vy += accel_speed * move_dir.y


# =============================================================================
# AI System
# =============================================================================

class AISystem(System):
    """
    Processes AI behavior for NPC Pawns.

    Handles different behaviors (patrol, hostile, idle) and state transitions.
    """

    required_components = [PawnComponent, AIControllerComponent, TransformComponent, VelocityComponent]
    priority = 5

    def __init__(self, pathfinder: Optional['GridPathfinder'] = None):
        super().__init__()
        self.pathfinder = pathfinder
        self._players_cache: List[Dict] = []

    def set_players_cache(self, players: List[Dict]) -> None:
        """Update the cache of player positions for targeting."""
        self._players_cache = players

    def update(self, dt: float, entities: List[Entity]) -> None:
        """Update AI for all NPC entities."""
        for entity in entities:
            pawn = entity.get_component(PawnComponent)
            if pawn.pawn_type == PawnType.PLAYER:
                continue

            self._update_ai(entity, dt)

    def _update_ai(self, entity: Entity, dt: float) -> None:
        """Update AI state and behavior for a single entity."""
        ai = entity.get_component(AIControllerComponent)
        transform = entity.get_component(TransformComponent)
        velocity = entity.get_component(VelocityComponent)

        if not all([ai, transform, velocity]):
            return

        # Update think timer
        ai.think_timer += dt
        if ai.think_timer < ai.think_interval:
            return
        ai.think_timer = 0

        # Handle behavior based on type
        if ai.behavior == AIBehavior.IDLE:
            self._behavior_idle(entity, ai, transform, velocity)
        elif ai.behavior == AIBehavior.PATROL:
            self._behavior_patrol(entity, ai, transform, velocity, dt)
        elif ai.behavior == AIBehavior.HOSTILE:
            self._behavior_hostile(entity, ai, transform, velocity)
        elif ai.behavior == AIBehavior.WANDER:
            self._behavior_wander(entity, ai, transform, velocity, dt)

    def _behavior_idle(self, entity: Entity, ai: AIControllerComponent,
                       transform: TransformComponent, velocity: VelocityComponent) -> None:
        """Idle behavior - just stand around."""
        ai.state = AIState.IDLE
        velocity.vx = 0
        velocity.vy = 0

    def _behavior_patrol(self, entity: Entity, ai: AIControllerComponent,
                         transform: TransformComponent, velocity: VelocityComponent,
                         dt: float) -> None:
        """Patrol between points."""
        if not ai.patrol_points:
            self._behavior_idle(entity, ai, transform, velocity)
            return

        target = ai.patrol_points[ai.current_patrol_index]
        dist = transform.distance_to(target[0], target[1])

        if dist < 0.5:
            # Reached waypoint, wait then move to next
            ai.patrol_timer += ai.think_interval
            if ai.patrol_timer >= ai.patrol_wait_time:
                ai.patrol_timer = 0
                ai.current_patrol_index = (ai.current_patrol_index + 1) % len(ai.patrol_points)
            ai.state = AIState.IDLE
            velocity.vx = 0
            velocity.vy = 0
        else:
            # Move towards target
            ai.state = AIState.MOVING
            dx = target[0] - transform.x
            dy = target[1] - transform.y
            length = (dx * dx + dy * dy) ** 0.5
            if length > 0:
                velocity.vx = (dx / length) * ai.move_speed
                velocity.vy = (dy / length) * ai.move_speed

    def _behavior_hostile(self, entity: Entity, ai: AIControllerComponent,
                          transform: TransformComponent, velocity: VelocityComponent) -> None:
        """Hostile behavior - attack players in range."""
        # Find nearest player
        nearest_player = None
        nearest_dist = float('inf')

        for player in self._players_cache:
            pos = player.get("position", {})
            px = pos.get("x", 0)
            py = pos.get("y", 0)
            dist = transform.distance_to(px, py)

            if dist < ai.aggro_radius and dist < nearest_dist:
                nearest_dist = dist
                nearest_player = player

        if nearest_player:
            pos = nearest_player.get("position", {})
            px = pos.get("x", 0)
            py = pos.get("y", 0)

            if nearest_dist <= ai.attack_range:
                # In attack range
                ai.state = AIState.ATTACKING
                ai.target_entity_id = nearest_player.get("uuid")
                velocity.vx = 0
                velocity.vy = 0
            else:
                # Pursue
                ai.state = AIState.PURSUING
                ai.target_entity_id = nearest_player.get("uuid")
                ai.last_known_target_pos = (px, py, 0)

                dx = px - transform.x
                dy = py - transform.y
                length = (dx * dx + dy * dy) ** 0.5
                if length > 0:
                    velocity.vx = (dx / length) * ai.move_speed
                    velocity.vy = (dy / length) * ai.move_speed
        else:
            # No target - idle
            ai.state = AIState.IDLE
            ai.target_entity_id = None
            velocity.vx = 0
            velocity.vy = 0

    def _behavior_wander(self, entity: Entity, ai: AIControllerComponent,
                         transform: TransformComponent, velocity: VelocityComponent,
                         dt: float) -> None:
        """Wander randomly within radius."""
        import random

        if ai.wander_center is None:
            ai.wander_center = (transform.x, transform.y, transform.z)

        ai.wander_timer += ai.think_interval
        if ai.wander_timer >= ai.wander_interval or ai.last_known_target_pos is None:
            ai.wander_timer = 0
            # Pick new random point
            angle = random.uniform(0, 360)
            dist = random.uniform(0, ai.wander_radius)
            rad = radians(angle)
            ai.last_known_target_pos = (
                ai.wander_center[0] + cos(rad) * dist,
                ai.wander_center[1] + sin(rad) * dist,
                transform.z
            )

        target = ai.last_known_target_pos
        dist = transform.distance_to(target[0], target[1])

        if dist < 0.5:
            ai.state = AIState.IDLE
            velocity.vx = 0
            velocity.vy = 0
        else:
            ai.state = AIState.MOVING
            dx = target[0] - transform.x
            dy = target[1] - transform.y
            length = (dx * dx + dy * dy) ** 0.5
            if length > 0:
                velocity.vx = (dx / length) * ai.move_speed
                velocity.vy = (dy / length) * ai.move_speed


# =============================================================================
# Animation System
# =============================================================================

class AnimationSystem(System):
    """
    Determines animation state based on movement and physics.
    """

    required_components = [PawnComponent, ModelComponent, VelocityComponent, PhysicsComponent]
    priority = 50  # Run after movement

    def update(self, dt: float, entities: List[Entity]) -> None:
        """Update animation state for all entities."""
        for entity in entities:
            self._update_animation(entity)

    def _update_animation(self, entity: Entity) -> None:
        """Determine animation based on state."""
        model = entity.get_component(ModelComponent)
        velocity = entity.get_component(VelocityComponent)
        physics = entity.get_component(PhysicsComponent)

        if not all([model, velocity, physics]):
            return

        health = entity.get_component(HealthComponent)
        if health and health.is_dead:
            model.animation = "death"
            return

        horiz_speed = velocity.speed_horizontal()

        if not physics.is_on_ground:
            if velocity.vz > 0:
                model.animation = "jump"
            else:
                model.animation = "fall"
        elif horiz_speed < 0.1:
            model.animation = "idle"
        elif physics.is_running:
            model.animation = "run_forward"
        else:
            model.animation = "walk_forward"


# =============================================================================
# Network Sync System
# =============================================================================

class NetworkSyncSystem(System):
    """
    Prepares entity data for network synchronization.

    Generates world_state data for broadcasting to clients.
    """

    required_components = [PawnComponent, TransformComponent]
    priority = 100  # Run last

    def update(self, dt: float, entities: List[Entity]) -> None:
        """Update network sync data (stores previous positions)."""
        for entity in entities:
            sync = entity.get_component(NetworkSyncComponent)
            if not sync:
                continue

            transform = entity.get_component(TransformComponent)
            if transform:
                sync.prev_x = transform.x
                sync.prev_y = transform.y
                sync.prev_z = transform.z
                sync.prev_rotation = transform.rotation

    def get_world_state(self, world: ECSWorld) -> Dict[str, Any]:
        """
        Generate world state for network broadcast.

        Returns:
            {
                "pawns": [...],  # All pawns (players + NPCs)
                "objects": [...]  # World objects (future)
            }
        """
        pawns = []

        for entity in world.get_entities_with_components(PawnComponent, TransformComponent):
            pawn_data = self._serialize_pawn(entity)
            if pawn_data:
                pawns.append(pawn_data)

        return {
            "pawns": pawns,
            "objects": []  # TODO: Add world objects
        }

    def _serialize_pawn(self, entity: Entity) -> Optional[Dict[str, Any]]:
        """Serialize a pawn entity for network transmission."""
        pawn = entity.get_component(PawnComponent)
        transform = entity.get_component(TransformComponent)

        if not pawn or not transform:
            return None

        data = {
            "entity_id": entity.id,
            "pawn_type": pawn.pawn_type.name.lower(),
            "display_name": pawn.display_name,
            "transform": {
                "x": transform.x,
                "y": transform.y,
                "z": transform.z,
                "rotation": transform.rotation
            }
        }

        # Add owner_id for players
        if pawn.owner_id is not None:
            data["owner_id"] = pawn.owner_id

        # Add template for NPCs
        if pawn.template_id:
            data["template_id"] = pawn.template_id

        # Add velocity
        velocity = entity.get_component(VelocityComponent)
        if velocity:
            data["velocity"] = {
                "x": velocity.vx,
                "y": velocity.vy,
                "z": velocity.vz
            }

        # Add model
        model = entity.get_component(ModelComponent)
        if model:
            data["model"] = model.model_path
            data["animation"] = model.animation

        # Add health
        health = entity.get_component(HealthComponent)
        if health:
            data["hp_current"] = health.hp_current
            data["hp_max"] = health.hp_max
            data["is_dead"] = health.is_dead

        # Add AI state for NPCs
        ai = entity.get_component(AIControllerComponent)
        if ai:
            data["ai_state"] = ai.state.name

        return data


# =============================================================================
# System Registry
# =============================================================================

SYSTEM_REGISTRY: Dict[str, type] = {
    "PhysicsSystem": PhysicsSystem,
    "InputSystem": InputSystem,
    "AISystem": AISystem,
    "AnimationSystem": AnimationSystem,
    "NetworkSyncSystem": NetworkSyncSystem,
}
