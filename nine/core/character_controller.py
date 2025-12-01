from panda3d.bullet import BulletCharacterControllerNode, BulletCapsuleShape
from panda3d.core import LVector3, NodePath

class CharacterController:
    """
    Server-side character controller. Manages the physics and movement
    of a single character based on input state.
    """
    def __init__(self, actor_nodepath: NodePath, physics_world):
        self.actor = actor_nodepath
        self.physics_world = physics_world
        self.move_speed = 10.0
        
        # Movement is processed relative to the main render node, making it world-relative.
        # A future improvement would be to use a client-provided orientation vector.
        self.reference_node = self.actor.getParent()

        height = 1.8
        radius = 0.4
        shape = BulletCapsuleShape(radius, height - 2 * radius, 2)
        # The character node needs a unique name.
        self.character_node = BulletCharacterControllerNode(shape, 0.4, f'Player_{self.actor.getName()}')
        self.character_np = self.reference_node.attachNewNode(self.character_node)
        self.physics_world.attachCharacter(self.character_node)
        
        # Reparent the actor nodepath to the physics controller nodepath
        self.actor.reparentTo(self.character_np)
        self.actor.setPos(0, 0, -height/2 + radius) # Center the model

        self.is_moving = False

    def jump(self):
        if self.character_node.isOnGround():
            self.character_node.doJump()
        
    def update(self, dt, input_map):
        """
        Updates the character's position based on the current input state.
        The input_map is a dictionary like {'w': True, 'a': False, ...}.
        Returns the new position and rotation if moved, otherwise None.
        """
        speed = LVector3(0, 0, 0)

        if input_map.get("w"): speed.y = 1
        if input_map.get("s"): speed.y = -1
        if input_map.get("a"): speed.x = -1
        if input_map.get("d"): speed.x = 1
        if input_map.get("space"): self.jump()
        
        self.is_moving = speed.length_squared() > 0

        if self.is_moving:
            speed.normalize()
            speed *= self.move_speed
            
            # This is now a world-relative move vector
            world_move_vec = self.reference_node.getRelativeVector(self.reference_node, speed)
            
            self.character_node.setLinearMovement(world_move_vec, True)
            
            # Make the actor face the direction of movement.
            # We must convert the world-space move vector to the actor's local coordinate space.
            local_move_vec = self.actor.getParent().getRelativeVector(self.reference_node, world_move_vec)
            self.actor.lookAt(self.actor.getPos() + local_move_vec)
        else:
            self.character_node.setLinearMovement(LVector3(0, 0, 0), True)

        # The physics simulation will move the character_np
        new_pos = self.character_np.getPos()
        new_rot = self.actor.getHpr()
        
        return new_pos, new_rot

    def cleanup(self):
        if hasattr(self, 'character_node') and self.character_node:
            self.physics_world.remove(self.character_node)
            self.character_node = None
        if hasattr(self, 'actor') and self.actor:
            self.actor.removeNode()
            self.actor = None