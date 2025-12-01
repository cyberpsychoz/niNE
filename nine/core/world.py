import time
from itertools import cycle

from panda3d.bullet import BulletRigidBodyNode, BulletPlaneShape
from panda3d.core import Vec3, LColor

from nine.core.database import DatabaseManager
from nine.core.character_controller import CharacterController


class Player:
    """Represents a player on the server side."""
    def __init__(self, client_id, name, actor, physics_world):
        self.client_id = client_id
        self.name = name
        self.actor = actor  # This is a server-side NodePath
        self.input_state = {"w": False, "a": False, "s": False, "d": False, "space": False}
        self.last_move_time = 0

        # On the server, the character controller manages the physics node
        self.character_controller = CharacterController(self.actor, physics_world)
    
    def update(self, dt):
        """Updates the player's character controller."""
        # Reset is_moving at the start of the tick for dev clients
        # For regular clients, this is set by the controller. For dev clients, by handle_move.
        self.character_controller.is_moving = False
        
        result = self.character_controller.update(dt, self.input_state)
        if result:
            self.last_move_time = time.time()
        return result

    def get_state(self):
        """Gets the player's state for broadcasting."""
        # The character_controller holds the physics NodePath, which has the position
        pos = self.character_controller.character_np.getPos()
        # The actor itself holds the rotation
        rot = self.actor.getHpr()

        anim_state = "idle"
        if self.character_controller.is_moving:
            anim_state = "walk"

        return {
            "pos": [pos.x, pos.y, pos.z],
            "rot": [rot.x, rot.y, rot.z],
            "name": self.name,
            "anim_state": anim_state
        }


class GameWorld:
    """
    Manages the server-side game state, including all players and physics.
    """
    def __init__(self, physics_world, render_node):
        self.physics_world = physics_world
        self.render = render_node  # The server's top-level render node
        self.players = {}  # Maps client_id to Player object
        self.db = DatabaseManager()

        self.spawn_points = cycle([
            [0, 0, 1], [5, 5, 1], [-5, 5, 1], [5, -5, 1], [-5, -5, 1]
        ])

        self._setup_scene()

    def _setup_scene(self):
        """Sets up the static physical world."""
        ground_shape = BulletPlaneShape(Vec3(0, 0, 1), 0)
        ground_body_node = BulletRigidBodyNode('Ground')
        ground_body_node.addShape(ground_shape)
        ground_np = self.render.attachNewNode(ground_body_node)
        ground_np.setPos(0, 0, -0.5)
        self.physics_world.attachRigidBody(ground_body_node)
    
    def get_world_state(self):
        """Gathers the state of all players for broadcasting."""
        player_states = {}
        for client_id, player in self.players.items():
            player_states[client_id] = player.get_state()
        return {"type": "world_state", "players": player_states}

    def update(self, dt):
        """The main update tick for the world."""
        for player in self.players.values():
            player.update(dt)

    def handle_input(self, client_id, input_data):
        if client_id in self.players:
            self.players[client_id].input_state = input_data

    def handle_move(self, client_id, move_data):
        """Directly sets the position and rotation for a player (used for dev clients)."""
        if client_id in self.players:
            player = self.players[client_id]
            pos = move_data.get("pos")
            rot = move_data.get("rot")
            if pos:
                player.character_controller.character_np.setPos(Vec3(*pos))
                # We should still mark them as moving so the anim broadcasts correctly
                player.character_controller.is_moving = True
            if rot:
                player.actor.setHpr(Vec3(*rot))

    def remove_player(self, client_id):
        if client_id in self.players:
            player = self.players.pop(client_id)
            player.character_controller.cleanup()
            player.actor.removeNode()
            self.db.shutdown() # Should be handled better
            print(f"Removed player {client_id}")
            return player.client_id
        return None

    def add_player(self, client_id, name):
        """
        Creates a player entity in the world.
        For now, we create a dummy actor on the server.
        It doesn't need to be visible, it's just a NodePath for transform.
        """
        from direct.actor.Actor import Actor
        # The server doesn't need to load the full model, just a node
        actor = self.render.attachNewNode(name)
        
        player = Player(client_id, name, actor, self.physics_world)
        
        spawn_pos = next(self.spawn_points)
        player.character_controller.character_np.setPos(Vec3(*spawn_pos))

        self.players[client_id] = player
        
        print(f"Added player {name} ({client_id}) to the world.")
        return player