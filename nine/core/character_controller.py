from panda3d.core import LVector3, LPoint3
from direct.actor.Actor import Actor
import math

class CharacterController:
    def __init__(self, actor: Actor, camera_pivot_node):
        self.actor = actor
        self.camera_pivot = camera_pivot_node
        self.move_speed = 10.0
        
    def update(self, dt, key_map) -> LVector3:
        """
        Updates the character's position and animation based on input.
        Returns the new position if moved, otherwise None.
        """
        move_vec = LVector3(0, 0, 0)
        if key_map.get("w"): move_vec.y += 1
        if key_map.get("s"): move_vec.y -= 1
        if key_map.get("a"): move_vec.x -= 1
        if key_map.get("d"): move_vec.x += 1

        if move_vec.length_squared() > 0:
            move_vec.normalize()
            
            # Get the world-space movement vector relative to the camera
            world_move_vec = self.actor.getParent().getRelativeVector(self.camera_pivot, move_vec)
            world_move_vec.z = 0
            world_move_vec.normalize()

            # Move the player
            new_pos = self.actor.getPos() + world_move_vec * self.move_speed * dt
            self.actor.setPos(new_pos)

            # Rotate the player to face the direction of movement
            self.actor.lookAt(self.actor.getPos() + world_move_vec)
            
            return new_pos
        else:
            return None

    def cleanup(self):
        if self.actor:
            self.actor.cleanup()
            self.actor.removeNode()
            self.actor = None
