"""
Server-side game world management.

Uses Panda3D collision system (no Bullet physics).
Supports loading maps from config or generating test map.
"""

import json
import logging
import os
import time
from itertools import cycle
from math import sin, cos, radians

from panda3d.core import (
    Vec3, LVector3, Geom, GeomNode, GeomTriangles, GeomVertexData,
    GeomVertexFormat, GeomVertexReader, BitMask32,
    CollisionNode, CollisionPlane, CollisionBox, CollisionPolygon,
    CollisionTraverser, Plane, Point3
)

logger = logging.getLogger("nine.server.game_server")

from nine.core.database import DatabaseManager
from nine.core.character_controller import CharacterController


class Player:
    """Represents a player on the server side."""

    def __init__(self, client_id, name, actor, render, cTrav):
        self.client_id = client_id
        self.name = name
        self.actor = actor
        self.last_move_time = 0
        self.is_dev_client = False
        self.cTrav = cTrav

        # Input state from client
        self.keys = {"w": False, "a": False, "s": False, "d": False, "space": False, "shift": False}
        self.camera_yaw = 0.0  # Camera direction for calculating movement

        self.character_controller = CharacterController(self.actor, render, cTrav)

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

        # Clear jump after processing (one-shot)
        self.keys["space"] = False

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
        forward = LVector3(-sin(yaw_rad), cos(yaw_rad), 0)
        right = LVector3(cos(yaw_rad), sin(yaw_rad), 0)

        move = forward * input_y + right * input_x
        move.normalize()
        return move

    def get_state(self):
        """Gets the player's state for broadcasting."""
        pos = self.actor.getPos()
        rot = self.actor.getHpr()
        vel = self.character_controller.get_velocity()

        anim_state = self.character_controller.get_anim_state()
        speed_ratio = 0.0
        horiz_speed = LVector3(vel.x, vel.y, 0).length()
        if horiz_speed > 0.1:
            max_speed = self.character_controller.run_speed
            speed_ratio = min(horiz_speed / max_speed, 1.0)

        return {
            "pos": [pos.x, pos.y, pos.z],
            "rot": [rot.x, rot.y, rot.z],
            "vel": [vel.x, vel.y, vel.z],
            "name": self.name,
            "anim_state": anim_state,
            "speed_ratio": speed_ratio
        }


class GameWorld:
    """Manages the server-side game state using Panda3D collision system."""

    def __init__(self, render_node, world_config: dict = None):
        self.render = render_node
        self.players = {}
        self.db = DatabaseManager()
        self.world_config = world_config or self._load_world_config()

        # Create collision traverser for Panda3D collision system
        self.cTrav = CollisionTraverser('world_traverser')
        # Enable previous transform mode for fast-moving objects (prevents tunneling)
        self.cTrav.setRespectPrevTransform(True)
        # Enable verbose debugging (optional)
        # self.cTrav.showCollisions(self.render)

        # Spawn points - high above floor for testing fall physics (floor at z=0)
        self.spawn_points = cycle([
            [8, -3, 10], [10, 5, 10], [5, 0, 10], [15, -5, 10], [3, 3, 10]
        ])

        self._setup_scene()

    def _load_world_config(self) -> dict:
        """Loads world config from server_config.json."""
        try:
            with open("server_config.json") as f:
                config = json.load(f)
            return config.get("world", {})
        except Exception:
            return {}

    def _setup_scene(self):
        """Sets up the physical world with Panda3D collision system."""
        logger.info("[World] Setting up Panda3D collision system")

        # Get map path from config
        map_path = self.world_config.get("map", {}).get("model", "test")

        # Check if should use test map
        if map_path == "test" or not os.path.exists(map_path):
            if map_path != "test":
                logger.warning(f"[World] Map not found: {map_path}, using test map")
            self._create_test_map()
        else:
            self._load_map_collision(map_path)

    def _load_map_collision(self, model_path: str):
        """
        Loads map and creates wall collision boxes.
        Floor is a single infinite plane at z=0.
        """
        from panda3d.core import CollisionBox

        try:
            # Load model for collision extraction
            map_model = loader.loadModel(model_path)
            if not map_model:
                logger.error(f"[World] Failed to load map model: {model_path}")
                self._create_fallback_ground()
                return

            logger.info(f"[World] Loaded map: {model_path}")

            wall_count = 0

            # Process each PandaNode (parent of GeomNode) for transforms
            for panda_node in map_model.getChildren():
                node_name = panda_node.getName()

                # Only process Cube.* objects as walls
                if not node_name.startswith("Cube"):
                    continue

                # Skip distant objects (skybox decorations)
                pos = panda_node.getPos()
                if abs(pos.x) > 80 or abs(pos.y) > 80:
                    continue

                scale = panda_node.getScale()
                world_pos = panda_node.getPos()

                # Create wall as collision box
                half_x = abs(scale.x) * 0.5
                half_y = abs(scale.y) * 0.5
                half_z = abs(scale.z)

                # Minimum size
                if half_x < 0.1: half_x = 0.5
                if half_y < 0.1: half_y = 0.5
                if half_z < 0.1: half_z = 1.0

                box = CollisionBox(
                    Point3(-half_x, -half_y, 0),
                    Point3(half_x, half_y, half_z * 2)
                )
                wall_node = CollisionNode(f'wall_{wall_count}')
                wall_node.addSolid(box)
                wall_node.setIntoCollideMask(CharacterController.WALL_MASK)
                wall_node.setFromCollideMask(BitMask32.allOff())

                wall_np = self.render.attachNewNode(wall_node)
                wall_np.setPos(world_pos)
                wall_np.setHpr(panda_node.getHpr())
                wall_count += 1

            logger.info(f"[World] Created {wall_count} wall collision boxes")

            # Clean up the model
            map_model.removeNode()

            # Create single ground plane at z=0
            self._create_fallback_ground()

        except Exception as e:
            logger.error(f"[World] Error loading map collision: {e}")
            import traceback
            traceback.print_exc()
            self._create_fallback_ground()

    def _create_collision_from_geom(self, geom_node_path, mask, name):
        """
        Creates collision geometry from a GeomNode.
        Uses CollisionPolygon for accurate collision.
        """
        try:
            geom_node = geom_node_path.node()
            transform = geom_node_path.getNetTransform()

            collision_node = CollisionNode(name)
            collision_node.setIntoCollideMask(mask)
            collision_node.setFromCollideMask(BitMask32.allOff())

            poly_count = 0

            for i in range(geom_node.getNumGeoms()):
                geom = geom_node.getGeom(i)
                vdata = geom.getVertexData()
                vertex_reader = GeomVertexReader(vdata, 'vertex')

                # Read all vertices
                vertices = []
                while not vertex_reader.isAtEnd():
                    v = vertex_reader.getData3f()
                    # Transform vertex to world space
                    world_v = transform.getMat().xformPoint(Point3(v))
                    vertices.append(world_v)

                if len(vertices) < 3:
                    continue

                # Process primitives
                for j in range(geom.getNumPrimitives()):
                    prim = geom.getPrimitive(j)
                    prim = prim.decompose()  # Convert to triangles

                    for k in range(prim.getNumPrimitives()):
                        start = prim.getPrimitiveStart(k)
                        end = prim.getPrimitiveEnd(k)

                        if end - start >= 3:
                            # Get triangle vertices
                            idx0 = prim.getVertex(start)
                            idx1 = prim.getVertex(start + 1)
                            idx2 = prim.getVertex(start + 2)

                            if idx0 < len(vertices) and idx1 < len(vertices) and idx2 < len(vertices):
                                v0 = vertices[idx0]
                                v1 = vertices[idx1]
                                v2 = vertices[idx2]

                                # Create collision polygon (triangle)
                                try:
                                    poly = CollisionPolygon(
                                        Point3(v0),
                                        Point3(v1),
                                        Point3(v2)
                                    )
                                    collision_node.addSolid(poly)
                                    poly_count += 1
                                except Exception:
                                    # Skip degenerate triangles
                                    pass

            if poly_count > 0:
                collision_np = self.render.attachNewNode(collision_node)
                logger.debug(f"[World] Created {name} with {poly_count} collision polygons")

        except Exception as e:
            logger.warning(f"[World] Failed to create collision for {name}: {e}")

    def _create_fallback_ground(self):
        """Creates main ground plane at z=0."""
        ground_plane = CollisionPlane(Plane(Vec3(0, 0, 1), Point3(0, 0, 0)))
        ground_node = CollisionNode('ground_plane')
        ground_node.addSolid(ground_plane)
        ground_node.setIntoCollideMask(CharacterController.FLOOR_MASK)
        ground_node.setFromCollideMask(BitMask32.allOff())

        self.ground_np = self.render.attachNewNode(ground_node)
        logger.info("[World] Created ground plane at z=0")

    def _create_test_map(self):
        """
        Creates a simple test map for physics testing.
        - White platform (floor) at z=0
        - Several colored blocks as obstacles
        """
        logger.info("[World] === CREATING TEST MAP ===")

        # 1. Create ground plane at z=0
        self._create_fallback_ground()

        # 2. Create test blocks with wall collision
        # Format: (name, position, size)
        test_blocks = [
            # Central area blocks
            ("block_red", (5, 0, 0), (2, 2, 2)),      # Red block
            ("block_green", (-5, 3, 0), (1.5, 1.5, 3)),  # Green tall block
            ("block_blue", (0, 8, 0), (3, 1, 1.5)),   # Blue wide block

            # Perimeter walls
            ("wall_north", (0, 15, 0), (20, 0.5, 3)),  # North wall
            ("wall_south", (0, -15, 0), (20, 0.5, 3)), # South wall
            ("wall_east", (15, 0, 0), (0.5, 15, 3)),   # East wall
            ("wall_west", (-15, 0, 0), (0.5, 15, 3)),  # West wall

            # Ramp/step test
            ("step_1", (8, -5, 0), (2, 2, 0.3)),      # Low step
            ("step_2", (8, -8, 0), (2, 2, 0.6)),      # Medium step
            ("step_3", (8, -11, 0), (2, 2, 1.0)),     # High step
        ]

        for name, pos, size in test_blocks:
            self._create_collision_box(name, pos, size)

        # Update spawn points for test map (center, above ground)
        self.spawn_points = cycle([
            [0, 0, 5],      # Center, high for fall test
            [3, 3, 2],      # Near center
            [-3, -3, 2],    # Opposite corner
        ])

        logger.info(f"[World] Test map created with {len(test_blocks)} collision objects")
        logger.info("[World] === TEST MAP READY ===")

    def _create_collision_box(self, name: str, pos: tuple, size: tuple):
        """
        Creates a collision box at the specified position.

        Args:
            name: Unique name for the collision node
            pos: (x, y, z) position of box center bottom
            size: (width, depth, height) of the box
        """
        half_x = size[0] / 2
        half_y = size[1] / 2
        height = size[2]

        # CollisionBox takes two corners: min and max
        box = CollisionBox(
            Point3(-half_x, -half_y, 0),
            Point3(half_x, half_y, height)
        )

        col_node = CollisionNode(name)
        col_node.addSolid(box)
        col_node.setIntoCollideMask(CharacterController.WALL_MASK)
        col_node.setFromCollideMask(BitMask32.allOff())

        col_np = self.render.attachNewNode(col_node)
        col_np.setPos(pos[0], pos[1], pos[2])

        logger.debug(f"[World] Created collision box '{name}' at {pos} size {size}")

    def get_world_state(self):
        """Gathers the state of all players for broadcasting."""
        player_states = {}
        for client_id, player in self.players.items():
            player_states[client_id] = player.get_state()
        return {"type": "world_state", "players": player_states}

    def update(self, dt):
        """The main update tick for the world."""
        # Update all players
        for player in self.players.values():
            player.update(dt)

        # Run collision detection
        self.cTrav.traverse(self.render)

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

        player = Player(client_id, name, actor, self.render, self.cTrav)

        # Set spawn position
        spawn_pos = next(self.spawn_points)
        logger.info(f"[World] Spawning player '{name}' at {spawn_pos}")
        player.character_controller.set_position(spawn_pos)

        # Verify position was set
        actual_pos = player.actor.getPos()
        logger.info(f"[World] Actual position after spawn: ({actual_pos.x:.2f}, {actual_pos.y:.2f}, {actual_pos.z:.2f})")

        self.players[client_id] = player

        logger.info(f"[World] Added player '{name}' (client_id={client_id})")
        return player
