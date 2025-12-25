"""
Server-side game world management.
"""

import json
import logging
import time
from itertools import cycle
from math import sin, cos, radians

logger = logging.getLogger("nine.server.game_server")

from panda3d.bullet import (
    BulletRigidBodyNode,
    BulletPlaneShape,
    BulletTriangleMesh,
    BulletTriangleMeshShape,
)
from panda3d.core import Vec3, LVector3, Geom, GeomNode

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
        # Forward = direction from camera to player = (-sin(yaw), cos(yaw))
        # Right = 90° clockwise from forward = (cos(yaw), sin(yaw))
        yaw_rad = radians(self.camera_yaw)
        forward = LVector3(-sin(yaw_rad), cos(yaw_rad), 0)
        right = LVector3(cos(yaw_rad), sin(yaw_rad), 0)

        move = forward * input_y + right * input_x
        move.normalize()
        return move

    def get_state(self):
        """Gets the player's state for broadcasting."""
        # Get actor position in world coordinates (not physics node position)
        # This ensures client receives the visual position, not physics capsule center
        pos = self.actor.getPos(self.character_controller.reference_node)
        rot = self.actor.getHpr()
        vel = self.character_controller.get_velocity()

        anim_state = self.character_controller.get_anim_state()
        speed_ratio = 0.0
        speed = vel.length()
        if speed > 0.1:
            max_speed = self.character_controller.run_speed
            speed_ratio = min(speed / max_speed, 1.0)

        return {
            "pos": [pos.x, pos.y, pos.z],
            "rot": [rot.x, rot.y, rot.z],
            "vel": [vel.x, vel.y, vel.z],
            "name": self.name,
            "anim_state": anim_state,
            "speed_ratio": speed_ratio
        }


class GameWorld:
    """Manages the server-side game state, including all players and physics."""

    def __init__(self, physics_world, render_node, world_config: dict = None):
        self.physics_world = physics_world
        self.render = render_node
        self.players = {}
        self.db = DatabaseManager()
        self.world_config = world_config or self._load_world_config()

        # Spawn points - above map geometry (map floor is around Z=3-5)
        self.spawn_points = cycle([
            [0, 0, 10], [5, 5, 10], [-5, 5, 10], [5, -5, 10], [-5, -5, 10]
        ])

        self._setup_scene()

    def _load_world_config(self) -> dict:
        """Загружает конфигурацию мира из server_config.json."""
        try:
            with open("server_config.json") as f:
                config = json.load(f)
            return config.get("world", {})
        except Exception:
            return {}

    def _setup_scene(self):
        """Sets up the static physical world with map collision."""
        self.ground_body = None
        self.ground_np = None

        # DEBUG: Use simple test floor to verify physics works
        use_test_floor = False

        if use_test_floor:
            from panda3d.bullet import BulletBoxShape
            from panda3d.core import BitMask32
            ground_shape = BulletBoxShape(Vec3(50, 50, 0.5))
            self.ground_body = BulletRigidBodyNode('TestFloor')
            self.ground_body.addShape(ground_shape)
            self.ground_body.setMass(0)
            self.ground_np = self.render.attachNewNode(self.ground_body)
            self.ground_np.setPos(0, 0, -0.5)
            self.ground_np.setCollideMask(BitMask32.allOn())
            self.physics_world.attachRigidBody(self.ground_body)
            logger.info("[World] Using TEST FLOOR at z=0 with collision mask")
            return

        # Try to load map with collision first
        map_config = self.world_config.get("map", {})
        map_model_path = map_config.get("model")
        map_loaded = False

        if map_model_path:
            map_loaded = self._load_map_collision(map_model_path)

        # Fallback ground plane only if map loading failed
        if not map_loaded:
            from panda3d.core import BitMask32
            logger.info("[World] Using fallback ground plane at z=-100")
            ground_shape = BulletPlaneShape(Vec3(0, 0, 1), -100)
            self.ground_body = BulletRigidBodyNode('Ground')
            self.ground_body.addShape(ground_shape)
            self.ground_np = self.render.attachNewNode(self.ground_body)
            self.ground_np.setCollideMask(BitMask32.allOn())
            self.physics_world.attachRigidBody(self.ground_body)

    def _load_map_collision(self, model_path: str) -> bool:
        """Loads map model and creates collision mesh from its geometry."""
        try:
            # Load model (server-side, no rendering)
            map_model = loader.loadModel(model_path)
            if not map_model:
                logger.error(f"[World] Failed to load map model: {model_path}")
                return False

            # Create triangle mesh from all geometry in the model
            mesh = BulletTriangleMesh()
            geom_count = 0

            for geom_node_path in map_model.findAllMatches("**/+GeomNode"):
                geom_node = geom_node_path.node()
                transform = geom_node_path.getTransform(map_model)

                for i in range(geom_node.getNumGeoms()):
                    geom = geom_node.getGeom(i)
                    mesh.addGeom(geom, True, transform)
                    geom_count += 1

            if geom_count == 0:
                logger.error(f"[World] No geometry found in map: {model_path}")
                return False

            # Create collision shape and rigid body
            from panda3d.core import BitMask32
            shape = BulletTriangleMeshShape(mesh, dynamic=False)
            map_body = BulletRigidBodyNode('MapCollision')
            map_body.addShape(shape)
            map_body.setMass(0)  # Static object

            map_np = self.render.attachNewNode(map_body)
            map_np.setCollideMask(BitMask32.allOn())  # Enable collision detection
            self.physics_world.attachRigidBody(map_body)

            logger.info(f"[World] Map collision loaded: {model_path} ({geom_count} geoms)")
            return True

        except Exception as e:
            logger.error(f"[World] Error loading map collision: {e}")
            return False

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
            logger.info(f"[World] Removed player (client_id={client_id})")
            return player.client_id
        return None

    def add_player(self, client_id, name):
        """Creates a player entity in the world."""
        actor = self.render.attachNewNode(name)

        player = Player(client_id, name, actor, self.physics_world)

        # Set spawn position
        spawn_pos = next(self.spawn_points)
        logger.info(f"[World] Spawning player '{name}' at {spawn_pos}")
        player.character_controller.set_position(spawn_pos)
        # Verify position was set
        actual_pos = player.character_controller.character_np.getPos()
        logger.info(f"[World] Actual position after spawn: ({actual_pos.x:.2f}, {actual_pos.y:.2f}, {actual_pos.z:.2f})")

        self.players[client_id] = player

        logger.info(f"[World] Added player '{name}' (client_id={client_id})")
        return player
