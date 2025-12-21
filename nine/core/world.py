"""
Server-side game world management.
"""

import time
from itertools import cycle
from math import sin, cos, radians

from panda3d.bullet import BulletRigidBodyNode, BulletPlaneShape
from panda3d.core import Vec3, LVector3

from nine.core.database import DatabaseManager
from nine.core.character_controller import CharacterController


class Player:
    """Represents a player on the server side."""

    def __init__(self, client_id, name, actor, physics_world):
        self.client_id = client_id
        self.name = name
        self.actor = actor
        self.last_move_time = 0
        self.is_dev_client = False

        # Input state from client
        self.keys = {"w": False, "a": False, "s": False, "d": False, "space": False, "shift": False}
        self.camera_yaw = 0.0  # Camera direction for calculating movement

        self.character_controller = CharacterController(self.actor, physics_world)

    def update(self, dt):
        """Updates the player's character controller."""
        if self.is_dev_client:
            return None

        # Calculate movement vector from keys and camera direction
        move_vector = self._calculate_move_vector()
        is_running = self.keys.get("shift", False)
        do_jump = self.keys.get("space", False)

        result = self.character_controller.update(dt, move_vector, is_running, do_jump)
        if result:
            self.last_move_time = time.time()
        return result

    def _calculate_move_vector(self):
        """Convert WASD + camera yaw to world-space movement vector."""
        input_x = 0
        input_y = 0
        if self.keys.get("w"): input_y += 1
        if self.keys.get("s"): input_y -= 1
        if self.keys.get("a"): input_x -= 1
        if self.keys.get("d"): input_x += 1

        if input_x == 0 and input_y == 0:
            return LVector3(0, 0, 0)

        # Calculate forward and right vectors from camera yaw
        yaw_rad = radians(self.camera_yaw)
        forward = LVector3(-sin(yaw_rad), -cos(yaw_rad), 0)
        right = LVector3(-cos(yaw_rad), sin(yaw_rad), 0)

        move = forward * input_y + right * input_x
        move.normalize()
        return move

    def get_state(self):
        """Gets the player's state for broadcasting."""
        pos = self.character_controller.character_np.getPos()
        rot = self.actor.getHpr()

        anim_state = self.character_controller.get_anim_state()
        speed_ratio = 0.0
        if self.character_controller.is_moving:
            max_speed = self.character_controller.run_speed
            speed_ratio = self.character_controller.current_speed / max_speed

        return {
            "pos": [pos.x, pos.y, pos.z],
            "rot": [rot.x, rot.y, rot.z],
            "name": self.name,
            "anim_state": anim_state,
            "speed_ratio": speed_ratio
        }


class GameWorld:
    """Manages the server-side game state, including all players and physics."""

    def __init__(self, physics_world, render_node):
        self.physics_world = physics_world
        self.render = render_node
        self.players = {}
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
        """Handle input from regular clients (server-authoritative movement)."""
        if client_id in self.players:
            player = self.players[client_id]
            player.camera_yaw = input_data.pop("camera_yaw", player.camera_yaw)
            player.keys = input_data

    def handle_move(self, client_id, move_data):
        """Handle movement from dev clients (client-authoritative movement)."""
        if client_id in self.players:
            player = self.players[client_id]
            player.is_dev_client = True

            pos = move_data.get("pos")
            rot = move_data.get("rot")

            if pos:
                player.character_controller.set_position(pos)
            if rot:
                player.character_controller.set_rotation(rot)

            # Update state for animation broadcast
            player.character_controller.is_moving = move_data.get("is_moving", False)
            player.character_controller.is_running = move_data.get("is_running", False)

    def remove_player(self, client_id):
        if client_id in self.players:
            player = self.players.pop(client_id)
            player.character_controller.cleanup()
            player.actor.removeNode()
            self.db.shutdown()
            print(f"Removed player {client_id}")
            return player.client_id
        return None

    def add_player(self, client_id, name):
        """Creates a player entity in the world."""
        actor = self.render.attachNewNode(name)

        player = Player(client_id, name, actor, self.physics_world)

        spawn_pos = next(self.spawn_points)
        player.character_controller.character_np.setPos(Vec3(*spawn_pos))

        self.players[client_id] = player

        print(f"Added player {name} ({client_id}) to the world.")
        return player
