"""
Server-side character controller with Source-like physics.

Features:
- Velocity-based movement with inertia
- Ground friction for smooth deceleration
- Air control for limited movement while jumping
- Smooth rotation towards movement direction
"""

import logging
import time
from math import atan2, degrees

from panda3d.bullet import BulletCharacterControllerNode, BulletCapsuleShape, BulletRigidBodyNode, ZUp
from panda3d.core import LVector3, NodePath, BitMask32

# Use the server's logger
logger = logging.getLogger("nine.server.game_server")


class CharacterController:
    """
    Character controller with Source engine-like physics.

    Movement feels smooth with gradual acceleration and friction-based stopping.
    """

    def __init__(self, actor_nodepath: NodePath, physics_world):
        self.actor = actor_nodepath
        self.physics_world = physics_world

        # === Movement parameters ===
        # Speeds (units per second)
        self.walk_speed = 5.0      # Normal walking speed
        self.run_speed = 10.0      # Running speed (with shift)

        # Acceleration
        self.ground_accel = 8.0    # How fast we accelerate on ground
        self.air_accel = 2.0       # Air control (much lower)

        # Friction (Source-like friction model)
        self.friction = 6.0        # Ground friction coefficient
        self.stop_speed = 0.5      # Below this, apply full friction

        # Rotation
        self.rotation_speed = 12.0  # Degrees per second multiplier

        # === State ===
        self.velocity = LVector3(0, 0, 0)  # Current velocity vector
        self.is_moving = False
        self.is_running = False
        self.move_direction = LVector3(0, 1, 0)
        self.current_heading = 0.0

        # Logging state
        self._last_log_time = 0
        self._spawn_time = time.time()
        self._last_pos = None

        self.reference_node = self.actor.getParent()

        # TEST: Use RigidBody instead of CharacterController to test gravity
        height = 1.8
        radius = 0.4
        shape = BulletCapsuleShape(radius, height - 2 * radius, ZUp)

        # Use CharacterController (more stable for characters)
        self.use_rigid_body = False

        if self.use_rigid_body:
            self.character_node = BulletRigidBodyNode(f'Player_{self.actor.getName()}')
            self.character_node.addShape(shape)
            self.character_node.setMass(80.0)  # 80 kg
            self.character_node.setAngularFactor(LVector3(0, 0, 0))  # Prevent tilting
            self.character_node.setDeactivationEnabled(False)  # Never sleep!
            self.character_np = self.reference_node.attachNewNode(self.character_node)
            self.character_np.setCollideMask(BitMask32.allOn())
            self.physics_world.attachRigidBody(self.character_node)
        else:
            self.character_node = BulletCharacterControllerNode(
                shape, 0.4, f'Player_{self.actor.getName()}'
            )
            self.character_np = self.reference_node.attachNewNode(self.character_node)
            self.character_np.setCollideMask(BitMask32.allOn())
            self.physics_world.attachCharacter(self.character_node)
            self.character_node.setGravity(50.0)
            self.character_node.setFallSpeed(100.0)
            self.character_node.setMaxJumpHeight(2.0)
            self.character_node.setJumpSpeed(12.0)

        # Reparent actor to physics node
        self.actor.reparentTo(self.character_np)
        self.actor.setPos(0, 0, -height/2)

    def jump(self):
        if self.use_rigid_body:
            # For rigid body, apply impulse
            # TODO: Need ground check
            self.character_node.applyCentralImpulse(LVector3(0, 0, 500))
        else:
            if self.character_node.isOnGround():
                self.character_node.doJump()

    def get_anim_state(self):
        """Returns animation name based on movement state."""
        if not self.is_moving:
            return "idle"
        return "run_forward" if self.is_running else "walk_forward"

    def _lerp_angle(self, current, target, factor):
        """Smoothly interpolate between angles, handling wraparound."""
        diff = (target - current + 180) % 360 - 180
        return current + diff * factor

    def _apply_friction(self, dt):
        """
        Apply Source-like friction to velocity.

        Friction is proportional to speed, but has a minimum threshold
        (stop_speed) to ensure characters actually stop.
        """
        speed = self.velocity.length()
        if speed < 0.01:
            self.velocity = LVector3(0, 0, 0)
            return

        # Control calculation - higher of speed or stop_speed
        control = max(speed, self.stop_speed)

        # Calculate friction drop
        drop = control * self.friction * dt

        # Scale velocity by remaining speed
        new_speed = max(speed - drop, 0)
        if speed > 0:
            self.velocity *= (new_speed / speed)

    def _accelerate(self, wish_dir, wish_speed, accel, dt):
        """
        Source-like acceleration.

        Projects current velocity onto wish direction and accelerates
        only if we're below wish_speed in that direction.
        """
        # Current speed in desired direction
        current_speed = self.velocity.dot(wish_dir)

        # How much we need to add
        add_speed = wish_speed - current_speed
        if add_speed <= 0:
            return

        # Acceleration amount
        accel_speed = accel * wish_speed * dt
        if accel_speed > add_speed:
            accel_speed = add_speed

        # Add to velocity
        self.velocity += wish_dir * accel_speed

    def update(self, dt, move_vector, is_running=False, do_jump=False):
        """
        Updates character position with Source-like physics.

        Args:
            dt: Delta time
            move_vector: World-space movement direction (normalized or zero)
            is_running: Whether shift is held
            do_jump: Whether to jump

        Returns:
            Tuple of (position, rotation)
        """
        if do_jump:
            self.jump()

        self.is_running = is_running


        # Movement
        has_input = move_vector.length_squared() > 0.01

        if has_input:
            self.move_direction = LVector3(move_vector)
            self.move_direction.normalize()
            wish_speed = self.run_speed if is_running else self.walk_speed
            speed = LVector3(self.move_direction * wish_speed)
        else:
            speed = LVector3(0, 0, 0)

        self.is_moving = has_input

        if self.use_rigid_body:
            # For rigid body: set horizontal velocity, preserve vertical (gravity)
            current_vel = self.character_node.getLinearVelocity()
            target_vel = LVector3(speed.x, speed.y, current_vel.z)
            self.character_node.setLinearVelocity(target_vel)
        else:
            # CharacterController uses setLinearMovement
            # Second parameter is is_local - False for world space movement
            if has_input:
                self.character_node.setLinearMovement(speed, False)
            else:
                self.character_node.setLinearMovement(LVector3(0, 0, 0), False)

        # Log position - more frequently in first 5 seconds
        now = time.time()
        pos = self.character_np.getPos()

        # Detect sudden position changes (explosion detection)
        if self._last_pos is not None:
            delta = (pos - self._last_pos).length()
            if delta > 10.0:  # More than 10 units in one frame = something wrong
                logger.warning(f"[Player] EXPLOSION! Delta={delta:.2f} from ({self._last_pos.x:.2f}, {self._last_pos.y:.2f}, {self._last_pos.z:.2f}) to ({pos.x:.2f}, {pos.y:.2f}, {pos.z:.2f})")
        self._last_pos = LVector3(pos)

        log_interval = 0.1 if (now - self._spawn_time) < 5.0 else 1.0
        if now - self._last_log_time >= log_interval:
            if self.use_rigid_body:
                vel = self.character_node.getLinearVelocity()
                logger.info(f"[Player] pos=({pos.x:.2f}, {pos.y:.2f}, {pos.z:.2f}) vel=({vel.x:.2f}, {vel.y:.2f}, {vel.z:.2f}) moving={self.is_moving}")
            else:
                on_ground = self.character_node.isOnGround()
                logger.info(f"[Player] pos=({pos.x:.2f}, {pos.y:.2f}, {pos.z:.2f}) onGround={on_ground} moving={self.is_moving}")
            self._last_log_time = now

        # Smooth rotation towards movement direction (if moving)
        if self.is_moving and speed.length() > 0.1:
            target_heading = degrees(atan2(-self.move_direction.x, self.move_direction.y)) + 180
            self.current_heading = self._lerp_angle(
                self.current_heading, target_heading, self.rotation_speed * dt
            )
            self.actor.setH(self.current_heading)

        return self.character_np.getPos(), self.actor.getHpr()

    def set_position(self, pos):
        """Directly set position (for dev clients)."""
        actor_pos = LVector3(*pos)
        physics_offset = self.actor.getPos()
        physics_pos = actor_pos - physics_offset
        self.character_np.setPos(physics_pos)

    def set_rotation(self, hpr):
        """Set character rotation."""
        self.actor.setHpr(LVector3(*hpr))
        self.current_heading = hpr[0]

    def set_velocity(self, vel):
        """Set velocity directly (for network sync)."""
        self.velocity = LVector3(*vel) if isinstance(vel, (list, tuple)) else vel

    def get_velocity(self):
        """Get current velocity."""
        return self.velocity

    def cleanup(self):
        if hasattr(self, 'character_node') and self.character_node:
            self.physics_world.remove(self.character_node)
            self.character_node = None
        if hasattr(self, 'actor') and self.actor:
            self.actor.removeNode()
            self.actor = None
