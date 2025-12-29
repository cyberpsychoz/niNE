"""
Server-side character controller using Panda3D collision system.

Features:
- Source-like movement with acceleration and friction
- Panda3D CollisionHandlerPusher for wall sliding
- Ray-based ground detection with proper gravity
- Smooth rotation towards movement direction
"""

import logging
import time
from math import atan2, degrees

from panda3d.core import (
    LVector3, NodePath, BitMask32, Vec3, Point3,
    CollisionSphere, CollisionNode, CollisionRay,
    CollisionHandlerPusher, CollisionHandlerQueue,
    CollisionTraverser
)

# Use the server's logger
logger = logging.getLogger("nine.server.game_server")


class CharacterController:
    """
    Character controller with Source engine-like physics.

    Uses Panda3D collision system for:
    - Wall collision with sliding (CollisionHandlerPusher)
    - Ray-based ground detection
    """

    # Collision masks
    WALL_MASK = BitMask32.bit(1)    # Walls/obstacles
    FLOOR_MASK = BitMask32.bit(2)   # Floors/ground

    def __init__(self, actor_nodepath: NodePath, render, cTrav: CollisionTraverser):
        self.actor = actor_nodepath
        self.render = render
        self.cTrav = cTrav

        # === Movement parameters ===
        # ПОЛЬЗОВАТЕЛЬСКИЕ ЗНАЧЕНИЯ - НЕ МЕНЯТЬ!
        self.walk_speed = 0.025    # Walking speed (units/sec)
        self.run_speed = 0.05      # Running speed (2x walk)
        self.rotation_speed = 10.0 # Rotation multiplier

        # Physics parameters
        self.gravity = 25.0        # Gravity acceleration
        self.jump_speed = 10.0     # Initial jump velocity
        self.max_fall_speed = 40.0 # Terminal velocity

        # Source-like movement parameters
        self.ground_accel = 10.0   # Ground acceleration
        self.air_accel = 2.0       # Air acceleration (limited air control)
        self.friction = 6.0        # Ground friction for smooth stopping
        self.stop_speed = 0.01     # Speed threshold for full friction

        # State
        self.velocity = LVector3(0, 0, 0)  # Full velocity vector (x, y = horizontal, z = vertical)
        self.is_moving = False
        self.is_running = False
        self.move_direction = LVector3(0, 1, 0)
        self.current_heading = 0.0
        self.is_on_ground = False
        self.is_jumping = False  # True while ascending from jump

        # Logging
        self._last_log_time = 0
        self._spawn_time = time.time()
        self._last_pos = None

        # === Panda3D Collision Setup ===
        self._setup_collision()

        logger.info(f"[CharacterController] === PANDA3D COLLISION SYSTEM ===")
        logger.info(f"[CharacterController] Walk Speed: {self.walk_speed}")
        logger.info(f"[CharacterController] Run Speed: {self.run_speed}")
        logger.info(f"[CharacterController] Gravity: {self.gravity}")
        logger.info(f"[CharacterController] Jump Speed: {self.jump_speed}")
        logger.info(f"[CharacterController] ========================================\n")

    def _setup_collision(self):
        """Setup collision geometry for the character."""
        # Character collision sphere (for wall collision)
        # Two spheres - one at body level, one at head level for better wall detection
        self.collision_node = CollisionNode('player_collision')
        # Body sphere
        self.collision_node.addSolid(CollisionSphere(0, 0, 0.5, 0.4))
        # Head sphere
        self.collision_node.addSolid(CollisionSphere(0, 0, 1.3, 0.3))

        # From mask: collide with walls
        self.collision_node.setFromCollideMask(self.WALL_MASK)
        self.collision_node.setIntoCollideMask(BitMask32.allOff())

        self.collision_np = self.actor.attachNewNode(self.collision_node)

        # Ground detection ray
        self.ground_ray = CollisionRay()
        self.ground_ray.setOrigin(0, 0, 0.5)  # Start from above feet
        self.ground_ray.setDirection(0, 0, -1)  # Point downward

        self.ground_ray_node = CollisionNode('player_ground_ray')
        self.ground_ray_node.addSolid(self.ground_ray)
        self.ground_ray_node.setFromCollideMask(self.FLOOR_MASK)
        self.ground_ray_node.setIntoCollideMask(BitMask32.allOff())

        self.ground_ray_np = self.actor.attachNewNode(self.ground_ray_node)

        # Collision handlers
        # Pusher for wall sliding
        self.pusher = CollisionHandlerPusher()
        self.pusher.addCollider(self.collision_np, self.actor)
        self.pusher.setHorizontal(True)  # Only push horizontally

        # Queue for ground detection
        self.ground_queue = CollisionHandlerQueue()

        # Register with traverser
        self.cTrav.addCollider(self.collision_np, self.pusher)
        self.cTrav.addCollider(self.ground_ray_np, self.ground_queue)

    def jump(self):
        """Initiate jump if on ground."""
        if self.is_on_ground:
            self.velocity.z = self.jump_speed
            self.is_on_ground = False
            self.is_jumping = True  # Prevent ground detection while ascending
            logger.info(f"[Player] Jump! velocity.z={self.velocity.z}")

    def get_anim_state(self):
        """Returns animation name based on movement state."""
        if not self.is_on_ground:
            return "idle"  # Could add jump/fall animations
        if not self.is_moving:
            return "idle"
        return "run_forward" if self.is_running else "walk_forward"

    def _lerp_angle(self, current, target, factor):
        """Smoothly interpolate between angles, handling wraparound."""
        diff = (target - current + 180) % 360 - 180
        return current + diff * factor

    def _apply_friction(self, dt, factor=1.0):
        """Apply Source-like friction to horizontal velocity."""
        speed = LVector3(self.velocity.x, self.velocity.y, 0).length()
        if speed < 0.001:  # Very low threshold for slow speeds
            self.velocity.x = 0
            self.velocity.y = 0
            return

        # Source friction formula
        control = max(speed, self.stop_speed)
        drop = control * self.friction * dt * factor
        new_speed = max(speed - drop, 0)

        if speed > 0:
            scale = new_speed / speed
            self.velocity.x *= scale
            self.velocity.y *= scale

    def _accelerate(self, wish_dir, wish_speed, accel, dt):
        """Apply Source-like acceleration."""
        # Current speed in wish direction
        current_speed = self.velocity.x * wish_dir.x + self.velocity.y * wish_dir.y

        # How much speed to add
        add_speed = wish_speed - current_speed
        if add_speed <= 0:
            return

        # Acceleration amount
        accel_speed = min(accel * wish_speed * dt, add_speed)

        self.velocity.x += accel_speed * wish_dir.x
        self.velocity.y += accel_speed * wish_dir.y

    def _check_ground(self):
        """Check if character is on ground using ray cast results."""
        # Clear jumping flag when starting to fall
        if self.is_jumping and self.velocity.z <= 0:
            self.is_jumping = False

        # Don't check ground while actively jumping upward
        if self.is_jumping:
            self.is_on_ground = False
            return

        if self.ground_queue.getNumEntries() == 0:
            self.is_on_ground = False
            return

        self.ground_queue.sortEntries()
        entry = self.ground_queue.getEntry(0)

        # Get the surface point in global coordinates
        surface_point = entry.getSurfacePoint(self.render)
        current_z = self.actor.getZ()

        # Distance from actor origin to ground
        ground_distance = current_z - surface_point.z

        # Ground check threshold
        step_height = 0.5
        snap_threshold = 0.05  # Only snap if difference > this (prevents trembling)

        if ground_distance <= step_height and ground_distance >= -0.1:
            # On or slightly above ground
            if self.velocity.z <= 0:
                # Landing or standing
                self.is_on_ground = True
                # Only snap if difference is significant (prevents trembling)
                if abs(ground_distance) > snap_threshold:
                    self.actor.setZ(surface_point.z)
                self.velocity.z = 0
            else:
                # Moving up - don't snap
                self.is_on_ground = False
        elif ground_distance < -0.1:
            # Below ground surface - push up
            self.is_on_ground = True
            self.actor.setZ(surface_point.z)
            self.velocity.z = 0
        else:
            # In the air
            self.is_on_ground = False

    def update(self, dt, move_vector, is_running=False, do_jump=False, cTrav=None):
        """
        Updates character position with Source-like physics.

        Args:
            dt: Delta time
            move_vector: World-space movement direction (normalized or zero)
            is_running: Whether shift is held
            do_jump: Whether to jump
            cTrav: Not used (uses self.cTrav)

        Returns:
            Tuple of (position, rotation)
        """
        # Check ground first (uses results from previous frame's traversal)
        self._check_ground()

        # Jump
        if do_jump and self.is_on_ground:
            self.jump()

        self.is_running = is_running

        # Input handling
        has_input = move_vector.length_squared() > 0.01
        if has_input:
            self.move_direction = LVector3(move_vector)
            self.move_direction.normalize()
        self.is_moving = has_input

        # Movement physics
        if self.is_on_ground:
            # Ground movement
            if has_input:
                # Apply friction while accelerating (for control)
                self._apply_friction(dt, 0.3)
                wish_speed = self.run_speed if is_running else self.walk_speed
                self._accelerate(self.move_direction, wish_speed, self.ground_accel, dt)
            else:
                # Full friction when stopping
                self._apply_friction(dt, 1.0)
        else:
            # Air movement - limited air control
            if has_input:
                wish_speed = self.run_speed if is_running else self.walk_speed
                self._accelerate(self.move_direction, wish_speed, self.air_accel, dt)

            # Apply gravity
            self.velocity.z -= self.gravity * dt
            if self.velocity.z < -self.max_fall_speed:
                self.velocity.z = -self.max_fall_speed

        # Apply velocity to position using setFluidPos for proper collision detection
        # setFluidPos() slides the object testing collisions, setPos() teleports!
        new_pos = self.actor.getPos()
        new_pos.x += self.velocity.x * dt
        new_pos.y += self.velocity.y * dt
        new_pos.z += self.velocity.z * dt
        self.actor.setFluidPos(new_pos)

        # Rotation towards movement direction
        horiz_speed = LVector3(self.velocity.x, self.velocity.y, 0).length()
        if self.is_moving and horiz_speed > 0.005:  # Very low threshold for slow speeds
            target_heading = degrees(atan2(-self.velocity.x, self.velocity.y)) + 180
            self.current_heading = self._lerp_angle(
                self.current_heading, target_heading, self.rotation_speed * dt
            )
            self.actor.setH(self.current_heading)

        # Logging
        now = time.time()
        pos = self.actor.getPos()

        if now - self._last_log_time >= 1.0:
            logger.info(f"[Player] pos=({pos.x:.2f}, {pos.y:.2f}, {pos.z:.2f}) "
                       f"onGround={self.is_on_ground} vel=({horiz_speed:.2f}, {self.velocity.z:.2f})")
            self._last_log_time = now

        # Detect physics explosions
        if self._last_pos is not None:
            delta = (pos - self._last_pos).length()
            if delta > 10.0:
                logger.warning(f"[Movement] EXPLOSION! Delta={delta:.2f}")
        self._last_pos = LVector3(pos)

        return self.actor.getPos(), self.actor.getHpr()

    def set_position(self, pos):
        """Directly set position (for spawning/teleport)."""
        actor_pos = LVector3(*pos) if isinstance(pos, (list, tuple)) else pos
        self.actor.setPos(actor_pos)
        self.velocity = LVector3(0, 0, 0)

    def set_rotation(self, hpr):
        """Set character rotation."""
        self.actor.setHpr(LVector3(*hpr))
        self.current_heading = hpr[0]

    def get_velocity(self):
        """Get current velocity."""
        return LVector3(self.velocity)

    def cleanup(self):
        """Remove collision nodes and cleanup."""
        if hasattr(self, 'collision_np') and self.collision_np:
            self.cTrav.removeCollider(self.collision_np)
            self.collision_np.removeNode()
        if hasattr(self, 'ground_ray_np') and self.ground_ray_np:
            self.cTrav.removeCollider(self.ground_ray_np)
            self.ground_ray_np.removeNode()
        if hasattr(self, 'actor') and self.actor:
            self.actor.removeNode()
            self.actor = None
