"""
Server-side game world management.

Uses Panda3D collision system (no Bullet physics).
Supports loading maps from config or generating test map.

This module now uses a unified ECS architecture where both players and NPCs
are managed as Pawn entities with shared components and systems.
"""

import json
import logging
import os
import time
from itertools import cycle
from math import sin, cos, radians
from typing import Dict, Optional, List, Any

from panda3d.core import (
    Vec3, LVector3, Geom, GeomNode, GeomTriangles, GeomVertexData,
    GeomVertexFormat, GeomVertexReader, BitMask32,
    CollisionNode, CollisionPlane, CollisionBox, CollisionPolygon,
    CollisionTraverser, Plane, Point3
)

logger = logging.getLogger("nine.server.game_server")

from nine.core.database import DatabaseManager
from nine.core.character_controller import CharacterController
from nine.core.ecs import ECSWorld, Entity
from nine.core.components import (
    TransformComponent,
    VelocityComponent,
    ModelComponent,
    PawnComponent,
    PhysicsComponent,
    HealthComponent,
    InputComponent,
    NetworkSyncComponent,
    PawnType,
)
from nine.core.systems import (
    PhysicsSystem,
    InputSystem,
    AnimationSystem,
    NetworkSyncSystem,
)


class Player:
    """
    Represents a player on the server side.

    This is a wrapper class that bridges the legacy API with the new ECS system.
    Internally, player data is stored in ECS components.
    """

    def __init__(self, client_id: int, name: str, actor, render, cTrav,
                 entity: Optional[Entity] = None):
        self.client_id = client_id
        self.name = name
        self.actor = actor
        self.last_move_time = 0
        self.is_dev_client = False
        self.cTrav = cTrav

        # ECS entity reference (set when using unified ECS)
        self.entity = entity

        # Input state from client (legacy - will be moved to InputComponent)
        self.keys = {"w": False, "a": False, "s": False, "d": False, "space": False, "shift": False}
        self.camera_yaw = 0.0  # Camera direction for calculating movement

        # Character controller (legacy physics - used when ECS physics not enabled)
        self.character_controller = CharacterController(self.actor, render, cTrav)

    def update(self, dt: float):
        """Updates the player's character controller."""
        if self.is_dev_client:
            return None

        # If using ECS entity, sync input to component
        if self.entity:
            input_comp = self.entity.get_component(InputComponent)
            if input_comp:
                input_comp.keys = self.keys.copy()
                input_comp.camera_yaw = self.camera_yaw

        # Calculate movement vector from keys and camera direction
        move_vector = self._calculate_move_vector()
        is_running = self.keys.get("shift", False)
        do_jump = self.keys.get("space", False)

        # Debug: Log jump attempts
        if do_jump:
            logger.info(f"[Player '{self.name}'] Jump button pressed! keys={self.keys}")

        result = self.character_controller.update(dt, move_vector, is_running, do_jump)
        if result:
            self.last_move_time = time.time()

        # Sync position back to ECS entity
        if self.entity and result:
            transform = self.entity.get_component(TransformComponent)
            velocity = self.entity.get_component(VelocityComponent)
            physics = self.entity.get_component(PhysicsComponent)

            if transform:
                pos = self.actor.getPos()
                rot = self.actor.getHpr()
                transform.x = pos.x
                transform.y = pos.y
                transform.z = pos.z
                transform.rotation = rot.x

            if velocity:
                vel = self.character_controller.get_velocity()
                velocity.vx = vel.x
                velocity.vy = vel.y
                velocity.vz = vel.z

            if physics:
                physics.is_on_ground = self.character_controller.is_on_ground
                physics.is_jumping = self.character_controller.is_jumping
                physics.is_running = self.character_controller.is_running

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

    def get_state(self) -> Dict[str, Any]:
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

    def get_entity_id(self) -> Optional[str]:
        """Get the ECS entity ID for this player."""
        return self.entity.id if self.entity else None


class GameWorld:
    """
    Manages the server-side game state using Panda3D collision system.

    Now uses a unified ECS architecture for managing both players and NPCs
    through the Pawn system.
    """

    def __init__(self, render_node, world_config: dict = None):
        self.render = render_node
        self.players: Dict[int, Player] = {}
        self.db = DatabaseManager()
        self.world_config = world_config or self._load_world_config()

        # Create collision traverser for Panda3D collision system
        self.cTrav = CollisionTraverser('world_traverser')
        # Enable previous transform mode for fast-moving objects (prevents tunneling)
        self.cTrav.setRespectPrevTransform(True)

        # =========================================================================
        # Unified ECS World
        # =========================================================================
        self.ecs_world = ECSWorld()

        # Network sync system (used to generate world_state)
        self.network_sync_system = NetworkSyncSystem()
        self.ecs_world.add_system(self.network_sync_system)

        # Animation system
        self.ecs_world.add_system(AnimationSystem())

        # Player entity ID mapping: client_id -> entity_id
        self._player_entity_map: Dict[int, str] = {}

        # DEBUG: Визуализация коллизий (раскомментируйте для отладки на КЛИЕНТЕ)
        # Показывает collision geometry красными линиями
        # ВАЖНО: НЕ используйте на сервере без графики!
        # self.cTrav.showCollisions(self.render)

        # Spawn points - high above floor for testing fall physics (floor at z=0)
        self.spawn_points = cycle([
            [8, -3, 15], [10, 5, 15], [5, 0, 15], [15, -5, 15], [3, 3, 15]
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
        Loads map and creates collision geometry from all GeomNodes.
        Automatically creates precise collision polygons from mesh geometry.
        Floor is a single infinite plane at z=0.
        """
        try:
            # Load model for collision extraction
            map_model = loader.loadModel(model_path)
            if not map_model:
                logger.error(f"[World] Failed to load map model: {model_path}")
                self._create_fallback_ground()
                return

            logger.info(f"[World] Loaded map: {model_path}")
            logger.info(f"[World] Creating collision from geometry...")

            # Find all GeomNodes in the model (recursive search)
            geom_nodes = map_model.findAllMatches("**/+GeomNode")

            if geom_nodes.isEmpty():
                logger.warning(f"[World] No GeomNodes found in {model_path}! Using fallback.")
                self._create_fallback_ground()
                return

            logger.info(f"[World] Found {geom_nodes.getNumPaths()} GeomNode(s)")

            # Create collision geometry from each GeomNode
            for i in range(geom_nodes.getNumPaths()):
                geom_node_path = geom_nodes.getPath(i)
                node_name = geom_node_path.getName()

                logger.info(f"[World] Processing GeomNode: {node_name}")

                # Create collision from geometry (auto-separates floors and walls by normal)
                self._create_collision_from_geom(
                    geom_node_path,
                    None,  # Mask is now determined automatically by normal direction
                    f"map_{node_name}"
                )

            # Clean up the model
            map_model.removeNode()

            # Create single ground plane at z=0
            self._create_fallback_ground()

            logger.info(f"[World] Map collision loaded successfully")

        except Exception as e:
            logger.error(f"[World] Error loading map collision: {e}")
            import traceback
            traceback.print_exc()
            self._create_fallback_ground()

    def _create_collision_from_geom(self, geom_node_path, _mask, name):
        # Note: _mask parameter is unused, kept for API compatibility
        """
        Creates collision geometry from a GeomNode.
        Uses CollisionPolygon for accurate per-triangle collision.

        IMPORTANT: Separates polygons by normal direction:
        - Horizontal polygons (floors) get FLOOR_MASK for ground detection
        - Vertical polygons (walls) get WALL_MASK for wall collision
        """
        try:
            geom_node = geom_node_path.node()
            transform = geom_node_path.getNetTransform()

            # Two separate collision nodes: one for walls, one for floors
            wall_node = CollisionNode(f"{name}_walls")
            wall_node.setIntoCollideMask(CharacterController.WALL_MASK)
            wall_node.setFromCollideMask(BitMask32.allOff())

            floor_node = CollisionNode(f"{name}_floors")
            floor_node.setIntoCollideMask(CharacterController.FLOOR_MASK)
            floor_node.setFromCollideMask(BitMask32.allOff())

            wall_count = 0
            floor_up_count = 0    # Floors facing UP (walkable)
            floor_down_count = 0  # Floors facing DOWN (ceilings - need to flip)
            total_triangles = 0

            # Threshold for floor detection: abs(normal.z) > 0.5 means mostly horizontal
            FLOOR_NORMAL_THRESHOLD = 0.5

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
                    logger.warning(f"[World] Geom {i} has < 3 vertices, skipping")
                    continue

                logger.debug(f"[World] Geom {i}: {len(vertices)} vertices")

                # Process primitives (triangles)
                for j in range(geom.getNumPrimitives()):
                    prim = geom.getPrimitive(j)
                    prim = prim.decompose()  # Convert to triangles

                    for k in range(prim.getNumPrimitives()):
                        start = prim.getPrimitiveStart(k)
                        end = prim.getPrimitiveEnd(k)
                        total_triangles += 1

                        if end - start >= 3:
                            # Get triangle vertices
                            idx0 = prim.getVertex(start)
                            idx1 = prim.getVertex(start + 1)
                            idx2 = prim.getVertex(start + 2)

                            if idx0 < len(vertices) and idx1 < len(vertices) and idx2 < len(vertices):
                                v0 = vertices[idx0]
                                v1 = vertices[idx1]
                                v2 = vertices[idx2]

                                # Calculate triangle normal
                                edge1 = LVector3(v1.x - v0.x, v1.y - v0.y, v1.z - v0.z)
                                edge2 = LVector3(v2.x - v0.x, v2.y - v0.y, v2.z - v0.z)
                                normal = edge1.cross(edge2)

                                if normal.length() < 0.0001:
                                    # Degenerate triangle (zero area)
                                    continue

                                normal.normalize()

                                # Determine if floor or wall based on normal direction
                                # CollisionPolygon is ONE-SIDED! Front face determined by vertex winding.
                                # A downward ray only detects polygons whose front faces UP.

                                try:
                                    if normal.z > FLOOR_NORMAL_THRESHOLD:
                                        # Floor facing UP - ray from above will hit front face
                                        poly = CollisionPolygon(
                                            Point3(v0), Point3(v1), Point3(v2)
                                        )
                                        floor_node.addSolid(poly)
                                        floor_up_count += 1

                                    elif normal.z < -FLOOR_NORMAL_THRESHOLD:
                                        # Floor facing DOWN (ceiling) - flip vertex order!
                                        # This makes the CollisionPolygon face UP so ray can detect it
                                        poly = CollisionPolygon(
                                            Point3(v0), Point3(v2), Point3(v1)  # Reversed v1/v2
                                        )
                                        floor_node.addSolid(poly)
                                        floor_down_count += 1

                                    else:
                                        # Wall polygon (mostly vertical)
                                        poly = CollisionPolygon(
                                            Point3(v0), Point3(v1), Point3(v2)
                                        )
                                        wall_node.addSolid(poly)
                                        wall_count += 1

                                except Exception as e:
                                    # Skip degenerate triangles
                                    logger.debug(f"[World] Skipped degenerate triangle: {e}")

            # Attach nodes to scene if they have polygons
            floor_total = floor_up_count + floor_down_count

            if wall_count > 0:
                wall_np = self.render.attachNewNode(wall_node)
                logger.info(f"[World] {name}_walls: {wall_count} wall polygons (WALL_MASK)")

            if floor_total > 0:
                floor_np = self.render.attachNewNode(floor_node)
                logger.info(f"[World] {name}_floors: {floor_total} floor polygons (FLOOR_MASK)")
                logger.info(f"[World]   - {floor_up_count} facing UP (original)")
                logger.info(f"[World]   - {floor_down_count} facing DOWN (flipped to face UP)")

            if wall_count == 0 and floor_total == 0:
                logger.warning(f"[World] {name}: No valid collision polygons created!")
            else:
                logger.info(f"[World] Total: {wall_count + floor_total}/{total_triangles} polygons")

        except Exception as e:
            logger.error(f"[World] Failed to create collision for {name}: {e}")
            import traceback
            traceback.print_exc()

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

    def get_world_state(self) -> Dict[str, Any]:
        """
        Gathers the state of all players for broadcasting.

        Returns both legacy format (players dict) and new unified format (pawns list).
        """
        # Legacy format for backward compatibility
        player_states = {}
        for client_id, player in self.players.items():
            player_states[client_id] = player.get_state()

        return {
            "type": "world_state",
            "players": player_states,
            # Unified ECS format will be added by game_server when merging with NPCs
        }

    def get_unified_world_state(self) -> Dict[str, Any]:
        """
        Get world state in the new unified format with pawns.

        Returns:
            {
                "type": "world_state",
                "pawns": [...],  # All pawns (players + NPCs)
                "players": {...}  # Legacy format for backward compatibility
            }
        """
        # Get legacy player states
        player_states = {}
        for client_id, player in self.players.items():
            player_states[client_id] = player.get_state()

        # Get unified pawn states from ECS
        pawns = []
        for entity in self.ecs_world.query(PawnComponent, TransformComponent):
            pawn_data = self._serialize_pawn_entity(entity)
            if pawn_data:
                pawns.append(pawn_data)

        return {
            "type": "world_state",
            "players": player_states,
            "pawns": pawns,
        }

    def _serialize_pawn_entity(self, entity: Entity) -> Optional[Dict[str, Any]]:
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

        return data

    def update(self, dt: float) -> None:
        """The main update tick for the world."""
        # DEBUG: Store tick ID for debugging
        if not hasattr(self, '_tick_id'):
            self._tick_id = 0
        self._tick_id += 1

        if self._tick_id % 10 == 0 or self._tick_id < 20:  # Log first 20 ticks and every 10th
            logger.info(f"[World TICK #{self._tick_id}] Updating {len(self.players)} players")

        # Update all players (legacy character controller)
        for player in self.players.values():
            player.update(dt)

        # Update ECS world (systems like Animation, NetworkSync)
        self.ecs_world.update(dt)

        # Run collision detection
        self.cTrav.traverse(self.render)

    def handle_input(self, client_id, input_data):
        """Handle input from regular clients (server-authoritative movement)."""
        if client_id in self.players:
            player = self.players[client_id]
            player.camera_yaw = input_data.pop("camera_yaw", player.camera_yaw)

            # Debug: Log when space is pressed
            if input_data.get("space", False):
                logger.info(f"[World] Received SPACE input for '{player.name}': {input_data}")

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

    def remove_player(self, client_id: int) -> Optional[int]:
        """Remove a player from the world."""
        if client_id in self.players:
            player = self.players.pop(client_id)
            player.character_controller.cleanup()
            player.actor.removeNode()

            # Remove ECS entity
            if client_id in self._player_entity_map:
                entity_id = self._player_entity_map.pop(client_id)
                self.ecs_world.remove_entity(entity_id)
                logger.debug(f"[World] Removed ECS entity {entity_id[:8]} for player")

            self.db.shutdown()
            logger.info(f"[World] Removed player (client_id={client_id})")
            return player.client_id
        return None

    def add_player(self, client_id: int, name: str) -> Player:
        """
        Creates a player entity in the world.

        Creates both a legacy Player wrapper and an ECS Entity for the player.
        """
        actor = self.render.attachNewNode(name)

        # Create ECS entity for the player
        entity = self._create_player_entity(client_id, name)

        # Create legacy Player wrapper with entity reference
        player = Player(client_id, name, actor, self.render, self.cTrav, entity=entity)

        # Set spawn position
        spawn_pos = next(self.spawn_points)
        logger.info(f"[World] Spawning player '{name}' at {spawn_pos}")
        player.character_controller.set_position(spawn_pos)

        # Sync spawn position to ECS entity
        transform = entity.get_component(TransformComponent)
        if transform:
            transform.x = spawn_pos[0]
            transform.y = spawn_pos[1]
            transform.z = spawn_pos[2]

        # Verify position was set
        actual_pos = player.actor.getPos()
        logger.info(f"[World] Actual position after spawn: ({actual_pos.x:.2f}, {actual_pos.y:.2f}, {actual_pos.z:.2f})")

        # Store mappings
        self.players[client_id] = player
        self._player_entity_map[client_id] = entity.id

        logger.info(f"[World] Added player '{name}' (client_id={client_id}, entity_id={entity.id[:8]})")
        return player

    def _create_player_entity(self, client_id: int, name: str) -> Entity:
        """Create an ECS entity for a player with all required components."""
        entity = self.ecs_world.create_entity()

        # Core pawn component
        entity.add_component(PawnComponent(
            pawn_type=PawnType.PLAYER,
            display_name=name,
            owner_id=client_id,
            tags=["player"]
        ))

        # Transform (position/rotation)
        entity.add_component(TransformComponent())

        # Velocity
        entity.add_component(VelocityComponent())

        # Physics properties
        entity.add_component(PhysicsComponent(
            walk_speed=1.5,
            run_speed=3.0
        ))

        # Health
        entity.add_component(HealthComponent(
            hp_current=100,
            hp_max=100,
            armor_class=10
        ))

        # Input state
        entity.add_component(InputComponent())

        # Model
        entity.add_component(ModelComponent(
            model_path="human_male",
            animation="idle"
        ))

        # Network sync
        entity.add_component(NetworkSyncComponent(needs_full_sync=True))

        # Add player tag
        entity.add_tag("player")
        entity.add_tag("pawn")

        return entity

    # =========================================================================
    # ECS Helper Methods
    # =========================================================================

    def get_ecs_world(self) -> ECSWorld:
        """Get the unified ECS world instance."""
        return self.ecs_world

    def get_player_entity(self, client_id: int) -> Optional[Entity]:
        """Get the ECS entity for a player by client_id."""
        entity_id = self._player_entity_map.get(client_id)
        if entity_id:
            return self.ecs_world.get_entity(entity_id)
        return None

    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by its ID."""
        return self.ecs_world.get_entity(entity_id)

    def get_pawns_in_radius(self, x: float, y: float, radius: float) -> List[Entity]:
        """Get all pawn entities within a radius of a point."""
        result = []
        for entity in self.ecs_world.query(PawnComponent, TransformComponent):
            transform = entity.get_component(TransformComponent)
            if transform and transform.distance_to(x, y) <= radius:
                result.append(entity)
        return result
