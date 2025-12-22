"""
Server-side character controller.

Simple movement model:
- Character rotates smoothly to face movement direction
- Only uses forward animations (idle, walk_forward, run_forward)
- Movement direction is provided as a world-space vector from client
"""

from math import atan2, degrees

from panda3d.bullet import BulletCharacterControllerNode, BulletCapsuleShape
from panda3d.core import LVector3, NodePath


class CharacterController:
    def __init__(self, actor_nodepath: NodePath, physics_world):
        self.actor = actor_nodepath
        self.physics_world = physics_world

        # Movement parameters
        self.walk_speed = 5.0
        self.run_speed = 10.0
        self.acceleration = 30.0
        self.deceleration = 40.0
        self.current_speed = 0.0
        self.rotation_speed = 10.0  # How fast character turns

        # State
        self.is_moving = False
        self.is_running = False
        self.move_direction = LVector3(0, 1, 0)  # World-space movement direction
        self.current_heading = 0.0  # Current facing direction

        self.reference_node = self.actor.getParent()

        # Physics capsule
        height = 1.8
        radius = 0.4
        shape = BulletCapsuleShape(radius, height - 2 * radius, 2)
        self.character_node = BulletCharacterControllerNode(
            shape, 0.4, f'Player_{self.actor.getName()}'
        )
        self.character_np = self.reference_node.attachNewNode(self.character_node)
        self.physics_world.attachCharacter(self.character_node)

        # Reparent actor to physics node
        # Offset actor so feet are at the bottom of the capsule
        # When capsule stands on ground (z=0), its center is at z=height/2
        # Actor origin (feet) should be at z=0, so offset = -height/2
        self.actor.reparentTo(self.character_np)
        self.actor.setPos(0, 0, -height/2)

    def jump(self):
        if self.character_node.isOnGround():
            self.character_node.doJump()

    def get_anim_state(self):
        """Returns animation name: idle, walk_forward, or run_forward."""
        if not self.is_moving:
            return "idle"
        return "run_forward" if self.is_running else "walk_forward"

    def _lerp_angle(self, current, target, factor):
        """Smoothly interpolate between angles, handling wraparound."""
        diff = (target - current + 180) % 360 - 180
        return current + diff * factor

    def update(self, dt, move_vector, is_running=False, do_jump=False):
        """
        Updates character position based on movement vector.

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
        has_input = move_vector.length_squared() > 0.01

        # Store movement direction for rotation
        if has_input:
            self.move_direction = LVector3(move_vector)
            self.move_direction.normalize()

        # Calculate target speed
        if has_input:
            target_speed = self.run_speed if is_running else self.walk_speed
            self.current_speed = min(
                self.current_speed + self.acceleration * dt,
                target_speed
            )
        else:
            self.current_speed = max(
                self.current_speed - self.deceleration * dt,
                0.0
            )

        self.is_moving = self.current_speed > 0.1

        if self.is_moving:
            # Apply movement
            velocity = self.move_direction * self.current_speed
            self.character_node.setLinearMovement(velocity, True)

            # Smooth rotation towards movement direction
            # Add 180 because model faces -Y by default
            target_heading = degrees(atan2(-self.move_direction.x, self.move_direction.y)) + 180
            self.current_heading = self._lerp_angle(
                self.current_heading, target_heading, self.rotation_speed * dt
            )
            self.actor.setH(self.current_heading)
        else:
            self.character_node.setLinearMovement(LVector3(0, 0, 0), True)

        return self.character_np.getPos(), self.actor.getHpr()

    def set_position(self, pos):
        """Directly set position (for dev clients).

        The pos argument is the actor's visual position. We need to compute
        the physics node position by reversing the actor offset.
        """
        actor_pos = LVector3(*pos)
        # Reverse the actor offset (actor is at -height/2 + radius relative to physics node)
        # So physics node should be at actor_pos - offset = actor_pos + (height/2 - radius)
        physics_offset = self.actor.getPos()  # This is the local offset from physics node
        physics_pos = actor_pos - physics_offset
        self.character_np.setPos(physics_pos)

    def set_rotation(self, hpr):
        """Set character rotation."""
        self.actor.setHpr(LVector3(*hpr))

    def cleanup(self):
        if hasattr(self, 'character_node') and self.character_node:
            self.physics_world.remove(self.character_node)
            self.character_node = None
        if hasattr(self, 'actor') and self.actor:
            self.actor.removeNode()
            self.actor = None
