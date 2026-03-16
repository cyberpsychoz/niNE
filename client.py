<<<<<<< HEAD
=======
import argparse
>>>>>>> main-core-engine
import asyncio
import json
import logging
import ssl
import struct
import sys
import uuid
from pathlib import Path

from direct.actor.Actor import Actor
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
<<<<<<< HEAD
from panda3d.core import (CardMaker, LColor, LVector3, NodePath,
                          WindowProperties, loadPrcFileData, Vec3)
=======
from panda3d.core import (
    CardMaker,
    ClockObject,
    LColor,
    loadPrcFileData,
    NodePath,
    LVector3,
)

globalClock = ClockObject.getGlobalClock()
>>>>>>> main-core-engine

from nine.core.camera_controller import CameraController
from nine.core.events import EventManager
from nine.core.plugins import PluginManager
<<<<<<< HEAD
from nine.ui.manager import UIManager

loadPrcFileData("", "audio-library-name null")


HOST = "localhost"
PORT = 9009


class GameClient(ShowBase):
    def __init__(self):
        log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler("client.log", mode='w')
        file_handler.setFormatter(log_formatter)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)

        try:
            self.asyncio_loop = asyncio.get_event_loop()
        except RuntimeError:
            self.asyncio_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.asyncio_loop)

        ShowBase.__init__(self)

        self.disableMouse()

        self.event_manager = EventManager()
        self.plugin_manager = PluginManager(self, self.event_manager)

        try:
            with open("config.json") as f:
                config = json.load(f)
            self.camera_sensitivity = config.get("camera_sensitivity", 1.0)
        except (FileNotFoundError, json.JSONDecodeError):
            self.camera_sensitivity = 1.0

        self.player_id = -1
        self.is_connected = False
        self.character_name = "Player"
        self.client_uuid = self._get_or_create_uuid()

        self.player_actor = None
        self.other_players = {}

        self.writer = None
        self.temp_password = None
        self.in_game_menu_active = False

        self.camera_controller = None

        callbacks = {
            "connect": self.open_login_menu,
            "exit": self.exit_game,
            "attempt_login": self.attempt_login,
            "close_login_menu": self.close_login_menu,
            "settings": self.show_settings_menu,
        }
        self.ui = UIManager(self, callbacks)

        self.event_manager.subscribe("client_send_chat_message", self.send_chat_packet)
        self.plugin_manager.load_plugins()

        self.ui.show_main_menu()
        self.setup_scene()
        self.logger.info("Клиент запущен.")

        self.keyMap = {"w": False, "a": False, "s": False, "d": False}
=======
from nine.core.network import send_message, read_messages
from nine.core.scene_optimizer import SceneOptimizer, LODSettings

# Audio enabled - using OpenAL (default)
# loadPrcFileData("", "audio-library-name null")  # Uncomment to disable audio


class GameClient(ShowBase):
    def __init__(self, dev_mode=False, name="Player", client_uuid=None):
        # --- Standard setup (logging, asyncio, ShowBase) ---
        log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Логирование в файл
        file_handler = logging.FileHandler("client.log", mode='w')
        file_handler.setFormatter(log_formatter)

        # Логирование в консоль
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)

        # Configure root logger so ALL module logs go to file and console
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        self.logger = logging.getLogger(__name__)

        try:
            self.asyncio_loop = asyncio.get_running_loop()
        except RuntimeError:
            self.asyncio_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.asyncio_loop)

        # Apply saved resolution BEFORE creating the window
        try:
            with open("config.json") as f:
                _cfg = json.load(f)
            res = _cfg.get("resolution", "")
            if "x" in res:
                w, h = res.split("x")
                loadPrcFileData("", f"win-size {w} {h}")
        except Exception:
            pass

        ShowBase.__init__(self)
        self.disableMouse()

        # --- Core Systems ---
        self.event_manager = EventManager()
        self.plugin_manager = PluginManager(self, self.event_manager)

        # --- Config and State ---
        self.dev_mode = dev_mode
        try:
            with open("config.json") as f:
                self.user_config = json.load(f)
            self.camera_sensitivity = self.user_config.get("camera_sensitivity", 1.0)
            self.third_person_camera = self.user_config.get("third_person_camera", True)
            self.invert_mouse_x = self.user_config.get("invert_mouse_x", False)
            self.invert_mouse_y = self.user_config.get("invert_mouse_y", False)
            self.fov = self.user_config.get("fov", 70)
        except (FileNotFoundError, json.JSONDecodeError):
            self.user_config = {}
            self.camera_sensitivity = 1.0
            self.third_person_camera = True
            self.invert_mouse_x = False
            self.invert_mouse_y = False
            self.fov = 70

        self.player_id = -1
        self.is_connected = False
        self.is_server = False  # Plugins check this

        # Buffer for events that arrive before plugins are loaded.
        # Server sends world_config, character_sheet, etc. BEFORE welcome,
        # but plugins load in the welcome handler. Buffer these and replay.
        self._pre_plugin_event_buffer = []
        self.character_name = name
        self.client_uuid = client_uuid if client_uuid else self._get_or_create_uuid()

        self.player_actor = None
        self.player_actor_model = None  # Actual Actor for animations
        self.other_players = {}  # {id: wrapper_node}
        self.other_players_state = {}  # {id: {target_pos, target_rot, vel, last_update}}

        self.writer = None
        self.in_game_menu_active = False
        self.camera_controller = None

        self.password = ""  # Stored for auth
        self.current_character = None  # Currently selected character data

        # --- UI Setup ---
        callbacks = {
            "connect": self.open_login_menu, "exit": self.exit_game,
            "attempt_login": self.attempt_login, "close_login_menu": self.close_login_menu,
            "settings": self.show_settings_menu,
        }

        # Choose UI backend from config
        ui_backend = self.user_config.get("ui_backend", "directgui")
        self.logger.info(f"Using UI backend: {ui_backend}")

        if ui_backend == "imgui":
            try:
                from nine.ui.imgui_manager import ImGuiManager
                self.ui = ImGuiManager(self, callbacks)
                self.ui.create_overlay()
                self.loading_screen = None  # ImGui has integrated loading screen
                self.logger.info("ImGui UI initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize ImGui UI: {e}")
                self.logger.info("Falling back to DirectGUI")
                from nine.ui.manager import UIManager
                from nine.ui.loading_screen import LoadingScreen
                self.ui = UIManager(self, callbacks)
                self.loading_screen = LoadingScreen(self.ui)
                self.loading_screen.hide()
        elif ui_backend == "cef":
            try:
                from nine.ui.cef_manager import CEFUIManager
                self.ui = CEFUIManager(self, callbacks)
                self.ui.create_overlay()
                self.ui.show_main_menu()
                self.loading_screen = None  # CEF has integrated loading screen
                self.logger.info("CEF UI initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize CEF UI: {e}")
                self.logger.info("Falling back to DirectGUI")
                from nine.ui.manager import UIManager
                from nine.ui.loading_screen import LoadingScreen
                self.ui = UIManager(self, callbacks)
                self.loading_screen = LoadingScreen(self.ui)
                self.loading_screen.hide()
        elif ui_backend == "webview":
            try:
                from nine.ui.webview_manager import WebViewUIManager
                self.ui = WebViewUIManager(self, callbacks)
                self.ui.create_overlay()
                self.ui.show_main_menu()
                self.loading_screen = None
                self.logger.info("WebView UI initialized successfully (browser mode)")
            except Exception as e:
                self.logger.error(f"Failed to initialize WebView UI: {e}")
                self.logger.info("Falling back to DirectGUI")
                from nine.ui.manager import UIManager
                from nine.ui.loading_screen import LoadingScreen
                self.ui = UIManager(self, callbacks)
                self.loading_screen = LoadingScreen(self.ui)
                self.loading_screen.hide()
        elif ui_backend == "playwright":
            try:
                from nine.ui.playwright_manager import PlaywrightUIManager
                self.ui = PlaywrightUIManager(self, callbacks)
                self.ui.create_overlay()
                self.ui.show_main_menu()
                self.loading_screen = None
                self.logger.info("Playwright UI initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Playwright UI: {e}")
                self.logger.info("Falling back to DirectGUI")
                from nine.ui.manager import UIManager
                from nine.ui.loading_screen import LoadingScreen
                self.ui = UIManager(self, callbacks)
                self.loading_screen = LoadingScreen(self.ui)
                self.loading_screen.hide()
        else:
            from nine.ui.manager import UIManager
            from nine.ui.loading_screen import LoadingScreen
            self.ui = UIManager(self, callbacks)
            self.loading_screen = LoadingScreen(self.ui)
            self.loading_screen.hide()  # Скрыт по умолчанию
        # Flag for plugins to check — skip DirectGUI creation when web UI is active
        self.ui_is_web = ui_backend in ("cef", "playwright", "webview")

        self.event_manager.subscribe("client_send_chat_message", self.send_chat_packet)
        self.event_manager.subscribe("client_item_use", self.send_item_use_packet)
        self.event_manager.subscribe("client_item_drop", self.send_item_drop_packet)
        self.event_manager.subscribe("client_equip_item", self.send_equip_item_packet)
        self.event_manager.subscribe("client_unequip_item", self.send_unequip_item_packet)
        self.event_manager.subscribe("send_to_server", self._handle_send_to_server)

        # --- Scene Optimizer ---
        self.scene_optimizer = SceneOptimizer(
            self,
            LODSettings(
                high_distance=50.0,
                medium_distance=150.0,
                low_distance=300.0,
                cull_distance=400.0
            )
        )

        # --- Final Initializations ---
        self.map_model = None
        self.logger.info("Client initialized.")

        # --- Input Handling ---
        self.keyMap = {"w": False, "a": False, "s": False, "d": False, "space": False, "shift": False}
>>>>>>> main-core-engine
        self.accept("w", self.update_key_map, ["w", True])
        self.accept("w-up", self.update_key_map, ["w", False])
        self.accept("a", self.update_key_map, ["a", True])
        self.accept("a-up", self.update_key_map, ["a", False])
        self.accept("s", self.update_key_map, ["s", True])
        self.accept("s-up", self.update_key_map, ["s", False])
        self.accept("d", self.update_key_map, ["d", True])
        self.accept("d-up", self.update_key_map, ["d", False])
<<<<<<< HEAD
        self.accept("escape", self.handle_escape)

        self.taskMgr.add(self.poll_asyncio, "asyncio-poll")
        self.game_update_task = None
=======
        self.accept("space", self.update_key_map, ["space", True])
        self.accept("space-up", self.update_key_map, ["space", False])
        self.accept("shift", self.update_key_map, ["shift", True])
        self.accept("shift-up", self.update_key_map, ["shift", False])
        # Handle WASD when Shift is held (Panda3D generates "shift-w" instead of "w")
        self.accept("shift-w", self.update_key_map, ["w", True])
        self.accept("shift-w-up", self.update_key_map, ["w", False])
        self.accept("shift-a", self.update_key_map, ["a", True])
        self.accept("shift-a-up", self.update_key_map, ["a", False])
        self.accept("shift-s", self.update_key_map, ["s", True])
        self.accept("shift-s-up", self.update_key_map, ["s", False])
        self.accept("shift-d", self.update_key_map, ["d", True])
        self.accept("shift-d-up", self.update_key_map, ["d", False])
        self.accept("shift-space", self.update_key_map, ["space", True])
        self.accept("shift-space-up", self.update_key_map, ["space", False])
        self.accept("escape", self.handle_escape)

        # --- Panda3D Tasks & Dev Mode ---
        self.taskMgr.add(self.poll_asyncio, "asyncio-poll")
        self.input_task = None

        if self.dev_mode:
            self.logger.info(f"Dev Client '{self.character_name}' ({self.client_uuid}) launched.")
            self.asyncio_loop.create_task(self.connect_and_read("localhost", 9009))
        else:
            self.ui.show_main_menu()
>>>>>>> main-core-engine

    def _get_or_create_uuid(self) -> str:
        uuid_file = Path(".client_uuid")
        if uuid_file.exists():
            try:
<<<<<<< HEAD
                client_uuid = uuid_file.read_text().strip()
                return str(client_uuid)
=======
                return str(uuid.UUID(uuid_file.read_text().strip()))
>>>>>>> main-core-engine
            except (ValueError, IndexError):
                pass
        client_uuid = str(uuid.uuid4())
        uuid_file.write_text(client_uuid)
        return client_uuid

<<<<<<< HEAD
    def setup_scene(self):
        cm = CardMaker("ground")
        cm.setFrame(-50, 50, -50, 50)
        ground = self.render.attachNewNode(cm.generate())
        ground.setP(-90)
        ground.setPos(0, 0, -1)

    def update_key_map(self, key, state):
        self.keyMap[key] = state

    def is_chat_active(self) -> bool:
        for plugin in self.plugin_manager.plugins:
            if plugin.name == "Chat UI" and hasattr(plugin, 'is_active'):
                return plugin.is_active()
=======
    def _load_map(self, model_path: str):
        """Загружает модель карты и применяет оптимизации."""
        from panda3d.core import CardMaker, BitMask32, CollisionNode, CollisionPolygon, Point3
        from panda3d.core import GeomNode, GeomVertexReader
        from nine.core.character_controller import CharacterController

        # Удаляем старую карту если есть
        if self.map_model:
            self.map_model.removeNode()
            self.map_model = None

        try:
            self.map_model = self.loader.loadModel(model_path)
            self.map_model.reparentTo(self.render)
            self.map_model.setPos(0, 0, 0)
            self.logger.info(f"Map loaded: {model_path}")

            # Настраиваем коллизии для камеры
            self._setup_map_collision()

            # Оптимизация карты для повышения производительности
            if self.scene_optimizer:
                opt_stats = self.scene_optimizer.optimize_map(self.map_model, aggressive=True)
                self.logger.info(
                    f"Map optimized: {opt_stats.get('geoms_before', 0)} -> "
                    f"{opt_stats.get('geoms_after', 0)} geoms "
                    f"({opt_stats.get('reduction_percent', 0):.1f}% reduction)"
                )

                # Включаем distance culling для больших карт
                self.scene_optimizer.setup_distance_culling(
                    self.camera,
                    self.map_model,
                    cull_distance=400.0,
                    update_interval=0.15
                )

        except Exception as e:
            self.logger.error(f"Failed to load map {model_path}: {e}")
            # Fallback: procedural test level
            self._generate_test_level()

    def _generate_test_level(self):
        """Generates a visual test level matching the server's _create_test_map() layout.

        The server creates collision boxes at specific positions — this renders
        visible cubes at the exact same positions so visuals match collision.
        """
        from panda3d.core import CardMaker, LColor

        self.logger.info("Generating procedural test level...")

        # Root node for the entire test level
        self.map_model = self.render.attachNewNode("test_level")

        # --- Ground platform (large flat plane) ---
        cm = CardMaker("ground")
        cm.setFrame(-50, 50, -50, 50)
        ground = self.map_model.attachNewNode(cm.generate())
        ground.setP(-90)
        ground.setPos(0, 0, 0)
        ground.setColor(0.3, 0.35, 0.25, 1)

        # --- Blocks matching server _create_test_map() ---
        # Format: (name, (cx, cy, bottom_z), (width, depth, height), color)
        # Position is center-bottom, same as server's _create_collision_box.
        test_blocks = [
            ("block_red",   (5, 0, 0),    (2, 2, 2),      LColor(0.7, 0.3, 0.3, 1)),
            ("block_green", (-5, 3, 0),   (1.5, 1.5, 3),  LColor(0.3, 0.6, 0.3, 1)),
            ("block_blue",  (0, 8, 0),    (3, 1, 1.5),    LColor(0.3, 0.3, 0.7, 1)),
            ("wall_north",  (0, 15, 0),   (20, 0.5, 3),   LColor(0.5, 0.5, 0.5, 1)),
            ("wall_south",  (0, -15, 0),  (20, 0.5, 3),   LColor(0.5, 0.5, 0.5, 1)),
            ("wall_east",   (15, 0, 0),   (0.5, 15, 3),   LColor(0.5, 0.5, 0.5, 1)),
            ("wall_west",   (-15, 0, 0),  (0.5, 15, 3),   LColor(0.5, 0.5, 0.5, 1)),
            ("step_1",      (8, -5, 0),   (2, 2, 0.3),    LColor(0.6, 0.5, 0.4, 1)),
            ("step_2",      (8, -8, 0),   (2, 2, 0.6),    LColor(0.6, 0.5, 0.4, 1)),
            ("step_3",      (8, -11, 0),  (2, 2, 1.0),    LColor(0.6, 0.5, 0.4, 1)),
        ]

        # rgbCube is centered at origin: extends (-0.5,-0.5,-0.5) to (0.5,0.5,0.5).
        # To match server box (center-bottom, width/depth/height):
        #   scale = (width, depth, height)
        #   pos   = (cx, cy, bottom_z + height/2)
        for name, pos, size, color in test_blocks:
            try:
                cube = self.loader.loadModel("models/misc/rgbCube")
                if not cube:
                    continue
            except Exception:
                continue

            cube.reparentTo(self.map_model)
            cube.setScale(size[0], size[1], size[2])
            cube.setPos(pos[0], pos[1], pos[2] + size[2] / 2)
            cube.setColor(color)

        self.logger.info(f"Test level generated: ground + {len(test_blocks)} blocks (matching server collision)")

    def _setup_map_collision(self):
        """Настраивает коллизии карты для камеры."""
        from panda3d.core import BitMask32, CollisionNode, CollisionPolygon, Point3
        from panda3d.core import GeomNode, GeomVertexReader, Geom
        from nine.core.character_controller import CharacterController

        if not self.map_model:
            return

        # Находим все GeomNode в модели
        geom_nodes = self.map_model.findAllMatches("**/+GeomNode")
        total_polys = 0

        for i in range(geom_nodes.getNumPaths()):
            geom_np = geom_nodes.getPath(i)
            geom_node = geom_np.node()

            # Создаём узел коллизий для этой геометрии
            coll_node = CollisionNode(f"map_coll_{i}")
            coll_node.setIntoCollideMask(CharacterController.WALL_MASK)
            coll_node.setFromCollideMask(BitMask32.allOff())

            poly_count = 0

            # Проходим по всем Geom в GeomNode
            for j in range(geom_node.getNumGeoms()):
                geom = geom_node.getGeom(j)
                vdata = geom.getVertexData()
                vertex_reader = GeomVertexReader(vdata, "vertex")

                # Проходим по примитивам
                for k in range(geom.getNumPrimitives()):
                    prim = geom.getPrimitive(k)
                    prim = prim.decompose()  # Разбиваем на треугольники

                    # Читаем треугольники
                    for p in range(prim.getNumPrimitives()):
                        start = prim.getPrimitiveStart(p)
                        end = prim.getPrimitiveEnd(p)

                        if end - start >= 3:
                            vertices = []
                            for v_idx in range(start, min(start + 3, end)):
                                vert_index = prim.getVertex(v_idx)
                                vertex_reader.setRow(vert_index)
                                v = vertex_reader.getData3()
                                # Применяем трансформацию узла
                                world_v = geom_np.getTransform(self.render).getMat().xformPoint(Point3(v))
                                vertices.append(world_v)

                            if len(vertices) == 3:
                                # Проверяем что полигон вертикальный (стена)
                                v0, v1, v2 = vertices
                                edge1 = v1 - v0
                                edge2 = v2 - v0
                                normal = edge1.cross(edge2)
                                normal.normalize()

                                # Если нормаль почти горизонтальная - это стена
                                if abs(normal.z) < 0.7:
                                    try:
                                        poly = CollisionPolygon(
                                            Point3(v0), Point3(v1), Point3(v2)
                                        )
                                        coll_node.addSolid(poly)
                                        poly_count += 1
                                    except Exception:
                                        pass  # Невалидный полигон

            if poly_count > 0:
                coll_np = self.render.attachNewNode(coll_node)
                total_polys += poly_count

        self.logger.info(f"Map collision setup: {total_polys} wall polygons for camera")

    def update_key_map(self, key, state):
        # Block key-down when chat or a panel is open, allow key-up to prevent stuck keys
        if state and (self.is_chat_active() or self._is_panel_open()):
            return
        self.keyMap[key] = state

    def _is_panel_open(self):
        """Check if any UI panel is open (character sheet, etc.)."""
        ui = getattr(self, 'ui', None)
        if ui and hasattr(ui, '_panel_open'):
            return ui._panel_open is not None
>>>>>>> main-core-engine
        return False

    def disable_game_input(self):
        if self.camera_controller:
            self.camera_controller.stop()
<<<<<<< HEAD

        for key in self.keyMap:
            self.keyMap[key] = False
        if self.game_update_task:
            self.taskMgr.remove(self.game_update_task)
            self.game_update_task = None
=======
        if self.input_task:
            self.taskMgr.remove(self.input_task)
            self.input_task = None
        self.taskMgr.remove("update-movement")
        for key in self.keyMap: self.keyMap[key] = False
>>>>>>> main-core-engine

    def enable_game_input(self):
        if self.camera_controller:
            self.camera_controller.start()
<<<<<<< HEAD
            
        if not self.game_update_task:
            self.game_update_task = self.taskMgr.add(self.game_update, "game-update-task")

    def game_update(self, task):
        if not self.is_connected or not self.player_actor or not self.camera_controller:
            return Task.cont

        dt = globalClock.getDt()

        move_vec = LVector3(0, 0, 0)
        if self.keyMap.get("w"): move_vec.y += 1
        if self.keyMap.get("s"): move_vec.y -= 1
        if self.keyMap.get("a"): move_vec.x -= 1
        if self.keyMap.get("d"): move_vec.x += 1

        is_moving = move_vec.length_squared() > 0
        if is_moving:
            if self.player_actor.getCurrentAnim() != "walk":
                self.player_actor.loop("walk")
            
            move_vec.normalize()
            
            camera_pivot = self.camera_controller.get_camera_pivot()
            world_move_vec = self.render.getRelativeVector(camera_pivot, move_vec)
            world_move_vec.z = 0
            world_move_vec.normalize()

            new_pos = self.player_actor.getPos() + world_move_vec * 10 * dt
            self.player_actor.setPos(new_pos)
            self.player_actor.lookAt(self.player_actor.getPos() + world_move_vec)

            new_rot = self.player_actor.getHpr()
            self.asyncio_loop.create_task(
                self.send_message(self.writer, {"type": "move", "pos": [new_pos.x, new_pos.y, new_pos.z], "rot": [new_rot.x, new_rot.y, new_rot.z]})
            )
        else:
            if self.player_actor.getCurrentAnim() != "idle":
                self.player_actor.loop("idle")

        return Task.cont

    def open_login_menu(self):
        self.ui.show_login_menu(default_ip=HOST, default_name=self.character_name)

    def close_login_menu(self):
        self.ui.hide_login_menu()
        self.ui.show_main_menu()

    def show_settings_menu(self):
        self.ui.show_settings_menu(self)

    def attempt_login(self):
        credentials = self.ui.get_login_credentials()
        if not credentials["ip"] or not credentials["name"] or not credentials["password"]:
            self.logger.warning("Все поля должны быть заполнены.")
            return
        self.character_name = credentials["name"]
        self.temp_password = credentials["password"]
        self.ui.hide_login_menu()
        self.asyncio_loop.create_task(self.connect_and_read(credentials["ip"]))

    def exit_game(self):
        self.plugin_manager.unload_plugins()
        if self.writer:
            self.writer.close()
        self.userExit()

    def handle_escape(self):
        if self.is_chat_active():
            self.event_manager.post("escape_key_pressed")
            return

=======
        if not self.input_task:
            # Always use server-authoritative movement (send input state to server)
            # Dev mode only affects connection behavior, not movement model
            self.input_task = self.taskMgr.add(self.send_input_task, "send-input-task")
        # Start interpolation tasks
        if not self.taskMgr.hasTaskNamed("interpolate-players"):
            self.taskMgr.add(self.interpolate_other_players_task, "interpolate-players")
        if not self.taskMgr.hasTaskNamed("interpolate-local-player"):
            self._local_player_target = None
            self.taskMgr.add(self._interpolate_local_player_task, "interpolate-local-player")
        # Start client-side animation prediction
        if not self.taskMgr.hasTaskNamed("update-movement"):
            self.taskMgr.add(self.update_movement_task, "update-movement")

    def send_input_task(self, task):
        """Periodically sends the current input state to the server (server-authoritative)."""
        if self.is_connected and self.camera_controller:
            state = dict(self.keyMap)
            state["camera_yaw"] = self.camera_controller.yaw
            input_message = {"type": "input", "state": state}
            self.asyncio_loop.create_task(send_message(self.writer, input_message))
        return Task.cont

    def _lerp_angle(self, current, target, factor):
        """Smoothly interpolate between angles, handling wraparound."""
        # Normalize angles to -180 to 180
        diff = (target - current + 180) % 360 - 180
        return current + diff * factor

    def update_movement_task(self, task):
        """Client-side animation prediction — reads local input to animate immediately."""
        if not self.is_connected or not self.player_actor or self.in_game_menu_active:
            return Task.cont

        if not self.camera_controller or not self.player_actor_model:
            return Task.cont

        # Initialize prediction state
        if not hasattr(self, '_dev_state'):
            self._dev_state = {
                'current_anim_rate': 1.0,
            }

        # Read local input to determine animation (no position changes)
        has_input = (self.keyMap["w"] or self.keyMap["s"] or
                     self.keyMap["a"] or self.keyMap["d"])
        is_running = self.keyMap.get("shift", False)

        # Determine target animation from local input
        if has_input:
            target_anim = "run_forward" if is_running else "walk_forward"
        else:
            target_anim = "idle"

        # Track logical animation state to avoid redundant transitions
        # (resolved names may be identical when model has limited animations)
        last_state = getattr(self.player_actor_model, '_last_anim_state', None)
        if target_anim != last_state:
            self.player_actor_model._last_anim_state = target_anim
            self._safe_loop(self.player_actor_model, target_anim)
            self._dev_state['current_anim_rate'] = 1.0

        # Adjust animation playback rate for movement
        if has_input:
            target_rate = 0.8 if is_running else 0.6
            if abs(target_rate - self._dev_state['current_anim_rate']) > 0.05:
                self._dev_state['current_anim_rate'] = target_rate
                resolved = self._resolve_anim(self.player_actor_model, target_anim)
                if resolved:
                    self.player_actor_model.setPlayRate(target_rate, resolved)

        return Task.cont

    def interpolate_other_players_task(self, task):
        """Smoothly interpolate other players' positions for smooth movement."""
        import time
        dt = globalClock.getDt()

        for p_id, state in list(self.other_players_state.items()):
            wrapper = self.other_players.get(p_id)
            if not wrapper:
                continue

            current_pos = wrapper.getPos()
            target_pos = state.get('target_pos', current_pos)
            vel = state.get('vel', LVector3(0, 0, 0))

            # Interpolation with velocity prediction
            # Move towards target + predicted position based on velocity
            time_since_update = time.time() - state.get('last_update', time.time())
            predicted_pos = LVector3(target_pos) + vel * min(time_since_update, 0.1)

            # Smooth interpolation (lerp factor based on distance)
            diff = predicted_pos - current_pos
            dist = diff.length()

            if dist < 0.01:
                # Close enough, snap
                new_pos = predicted_pos
            elif dist > 5.0:
                # Too far, teleport (probably spawned/respawned)
                new_pos = predicted_pos
            else:
                # Smooth interpolation - faster when further away
                lerp_speed = min(15.0, 5.0 + dist * 3.0)
                new_pos = current_pos + diff * min(lerp_speed * dt, 1.0)

            wrapper.setPos(new_pos)

            # Smooth rotation
            current_rot = wrapper.getH()
            target_rot = state.get('target_rot', [current_rot, 0, 0])[0]
            new_rot = self._lerp_angle(current_rot, target_rot, 10.0 * dt)
            wrapper.setH(new_rot)

        return Task.cont

    def _interpolate_local_player_task(self, task):
        """Smoothly interpolate the local player's position from server updates."""
        import time
        dt = globalClock.getDt()
        state = getattr(self, '_local_player_target', None)
        if not state or not self.player_actor:
            return Task.cont

        current_pos = self.player_actor.getPos()
        target_pos = state['target_pos']
        vel = state.get('vel', LVector3(0, 0, 0))

        # Predict position based on velocity and time since last update
        time_since = time.time() - state.get('last_update', time.time())
        predicted_pos = LVector3(target_pos) + vel * min(time_since, 0.1)

        diff = predicted_pos - current_pos
        dist = diff.length()

        if dist < 0.01:
            new_pos = predicted_pos
        elif dist > 5.0:
            new_pos = predicted_pos  # Teleport if too far
        else:
            lerp_speed = min(20.0, 8.0 + dist * 5.0)
            new_pos = current_pos + diff * min(lerp_speed * dt, 1.0)

        self.player_actor.setPos(new_pos)

        # Smooth rotation
        current_rot = self.player_actor.getH()
        target_rot = state.get('target_rot', [current_rot, 0, 0])[0]
        new_rot = self._lerp_angle(current_rot, target_rot, 15.0 * dt)
        self.player_actor.setH(new_rot)

        return Task.cont

    def attempt_login(self):
        credentials = self.ui.get_login_credentials()
        ip_str = credentials.get("ip", "localhost:9009")
        self.character_name = credentials.get("name", "Player")
        self.password = credentials.get("password", "")

        if not ip_str or not self.character_name:
            self.logger.warning("IP and Name fields must be filled.")
            return

        if not self.password:
            self.logger.warning("Password field must be filled.")
            return

        try:
            host, port_str = ip_str.split(":")
            port = int(port_str)
        except ValueError:
            self.logger.warning(f"Invalid address format: {ip_str}. Expected 'host:port'.")
            return

        self.ui.hide_login_menu()
        # Показываем экран загрузки
        if self.loading_screen:
            self.loading_screen.set_title("ПОДКЛЮЧЕНИЕ")
            self.loading_screen.set_status("Подключение к серверу...")
            self.loading_screen.set_progress(0.1)
            self.loading_screen.show()
        else:
            self.ui.show_loading_screen("Подключение к серверу...")
        self.asyncio_loop.create_task(self.connect_and_read(host, port))

    def on_successful_connection(self):
        # Обновляем экран загрузки
        if self.loading_screen:
            self.loading_screen.set_status("Авторизация...")
            self.loading_screen.set_progress(0.3)
        else:
            self.ui.update_loading_progress(0.3, "Авторизация...")

        if self.dev_mode:
            auth_data = {"type": "dev_auth", "name": self.character_name, "uuid": self.client_uuid}
        else:
            auth_data = {
                "type": "auth",
                "name": self.character_name,
                "password": self.password
            }
        self.asyncio_loop.create_task(send_message(self.writer, auth_data))
        self.password = ""

    def _build_anim_map(self, actor):
        """Build a mapping from expected animation names to actual ones in the model."""
        anim_names = actor.getAnimNames()
        anim_set = set(anim_names)
        self.logger.info(f"Available animations: {sorted(anim_names)}")

        # Known aliases: expected_name -> possible actual names in model
        aliases = {
            "idle": ["idle"],
            "walk_forward": ["walk_forward"],
            "walk_backward": ["walk_backward"],
            "run_forward": ["run_forward"],
            "strafe_left": ["strafe_left", "left_strafe"],
            "strafe_right": ["strafe_right", "right_strafe"],
        }

        anim_map = {}
        fallback = anim_names[0] if anim_names else None

        for expected_name, candidates in aliases.items():
            matched = False
            for candidate in candidates:
                if candidate in anim_set:
                    anim_map[expected_name] = candidate
                    matched = True
                    break
            if not matched:
                anim_map[expected_name] = fallback
                if fallback:
                    self.logger.warning(f"Animation '{expected_name}' not found, using fallback '{fallback}'")

        return anim_map

    def _resolve_anim(self, actor, anim_name):
        """Resolve a logical animation name to the actual one in the model."""
        anim_map = getattr(actor, '_anim_map', None)
        return anim_map.get(anim_name, anim_name) if anim_map else anim_name

    def _safe_loop(self, actor, anim_name):
        """Loop an animation using the anim map, falling back if needed."""
        resolved = self._resolve_anim(actor, anim_name)
        if resolved:
            actor.loop(resolved)

    def load_actor(self, player_id, color, is_local_player=False):
        # Model contains embedded animations: idle, walk_forward, walk_backward, run_forward, strafe_left, strafe_right
        model_paths = [
            "nine/assets/models/base.bam",
            "nine/assets/models/player2.bam",
        ]
        actor = None
        for model_path in model_paths:
            try:
                actor = Actor(model_path)
                self.logger.info(f"Loaded actor model: {model_path}")
                break
            except Exception as e:
                self.logger.warning(f"Failed to load {model_path}: {e}")
        if actor is None:
            raise RuntimeError("Could not load any player model")
        actor.set_scale(0.3)
        actor.setColorScale(color)

        # Build animation name map and store on actor for later use
        actor._anim_map = self._build_anim_map(actor)

        # Create wrapper node for positioning to avoid root motion jitter
        # We move the wrapper, actor stays at origin relative to it
        wrapper = self.render.attachNewNode(f"player_{player_id}")
        actor.reparentTo(wrapper)

        # Fix root motion: lock actor position relative to wrapper
        # Animation may move the actor, we reset it every frame
        actor.setPos(0, 0, 0)

        # Start with idle animation
        self._safe_loop(actor, "idle")

        if is_local_player:
            self.player_actor = wrapper
            self.player_actor_model = actor  # Keep reference to actual actor for animations
            # Start task to fix root motion jitter for local player
            if not self.taskMgr.hasTaskNamed("fix-root-motion"):
                self.taskMgr.add(self._fix_root_motion_task, "fix-root-motion", sort=-10)
        else:
            self.other_players[player_id] = wrapper
            # Store actor reference on wrapper for animation access
            wrapper.setPythonTag("actor", actor)
        return wrapper

    def _fix_root_motion_task(self, task):
        """Fix root motion jitter by resetting actor position every frame."""
        if self.player_actor_model:
            # Keep actor at origin relative to wrapper - animations shouldn't move it
            self.player_actor_model.setPos(0, 0, 0)

        # Also fix other players
        for wrapper in self.other_players.values():
            actor = wrapper.getPythonTag("actor")
            if actor:
                actor.setPos(0, 0, 0)

        return Task.cont

    def update_player_model_visibility(self):
        """
        Обновляет видимость модели игрока в зависимости от режима камеры.
        В first-person режиме модель скрыта, в third-person — видима.
        """
        if not self.player_actor_model:
            return

        if self.camera_controller and not self.camera_controller.third_person:
            # First-person: скрываем модель
            self.player_actor_model.hide()
        else:
            # Third-person: показываем модель
            self.player_actor_model.show()

    def _post_or_buffer_event(self, event_name, event_data):
        """Post event if plugins loaded, otherwise buffer for replay after welcome."""
        if self.plugin_manager.loaded_plugins:
            self.event_manager.post(event_name, event_data)
        else:
            self._pre_plugin_event_buffer.append((event_name, event_data))
            self.logger.debug(f"Buffered event '{event_name}' (plugins not loaded yet)")

    def handle_network_data(self, data: dict):
        msg_type = data.get("type")

        if msg_type == "auth_success":
            self.logger.info("Auth success")
            # Server will send welcome message next

        elif msg_type == "auth_failed":
            reason = data.get("reason", "Unknown error")
            self.logger.warning(f"Auth failed: {reason}")
            self.disconnect()

        elif msg_type == "welcome":
            # Load plugins on first connection
            if not self.plugin_manager.loaded_plugins:
                self.plugin_manager.load_plugins()

            # Replay buffered events (world_config, character_sheet, etc.
            # arrive BEFORE welcome due to server message ordering)
            if self._pre_plugin_event_buffer:
                self.logger.info(f"Replaying {len(self._pre_plugin_event_buffer)} buffered events after plugin load")
                for event_name, event_data in self._pre_plugin_event_buffer:
                    self.logger.info(f"  Replaying: {event_name}")
                    self.event_manager.post(event_name, event_data)
                self._pre_plugin_event_buffer.clear()

            # Скрываем экран загрузки
            if self.loading_screen:
                self.loading_screen.set_progress(1.0)
                self.loading_screen.hide()
            else:
                self.ui.hide_loading_screen()

            # Enter game state (hides menus and notifies plugins)
            self.current_character = data.get("character_data")
            self.ui.enter_game(self.current_character)
            self.player_id = data["id"]

            # Очищаем старого актёра если есть (предотвращаем двойной спавн)
            if self.player_actor:
                if self.player_actor_model:
                    self.player_actor_model.cleanup()
                    self.player_actor_model = None
                self.player_actor.removeNode()
                self.player_actor = None

            # Загружаем актёра (TODO: использовать модель из character_data)
            try:
                self.load_actor(self.player_id, LColor(0.5, 0.8, 0.5, 1), is_local_player=True)
            except Exception as e:
                self.logger.error(f"Failed to load player actor: {e}")
            if self.player_actor:
                self.player_actor.setPos(*data["pos"])
            self.camera_controller = CameraController(
                self, self.camera, self.win, self.player_actor,
                sensitivity=self.camera_sensitivity,
                third_person=self.third_person_camera,
                invert_x=self.invert_mouse_x,
                invert_y=self.invert_mouse_y,
                fov=self.fov
            )
            self.update_player_model_visibility()
            self.enable_game_input()

            for p_id, p_info in data.get("players", {}).items():
                p_id = int(p_id)
                if p_id != self.player_id:
                    self.load_actor(p_id, LColor(0.8, 0.8, 0.8, 1)).setPos(*p_info["pos"])

        elif msg_type == "player_joined":
            p_id = data["id"]
            if p_id != self.player_id:
                p_info = data["player_info"]
                self.load_actor(p_id, LColor(0.8, 0.8, 0.8, 1)).setPos(*p_info["pos"])

        elif msg_type == "player_left":
            p_id = data["id"]
            if p_id in self.other_players:
                wrapper = self.other_players.pop(p_id)
                actor = wrapper.getPythonTag("actor")
                if actor:
                    actor.cleanup()
                wrapper.removeNode()
            # Clean up interpolation state
            if p_id in self.other_players_state:
                del self.other_players_state[p_id]

        elif msg_type == "world_config":
            # Обновляем экран загрузки
            if self.loading_screen:
                self.loading_screen.set_title("ЗАГРУЗКА МИРА")
                self.loading_screen.set_status("Загрузка карты...")
                self.loading_screen.set_progress(0.5)
            else:
                self.ui.show_loading_screen("Загрузка карты...")
                self.ui.update_loading_progress(0.5)

            # Загружаем карту
            map_config = data.get("map", {})
            map_model = map_config.get("model", "nine/assets/models/maps/map.bam")
            self._load_map(map_model)

            if self.loading_screen:
                self.loading_screen.set_status("Настройка освещения...")
                self.loading_screen.set_progress(0.7)
            else:
                self.ui.update_loading_progress(0.7, "Настройка освещения...")

            # Передаём плагинам для обработки освещения и скайбокса
            self._post_or_buffer_event("world_config", data)
            self.logger.info("World config received and applied")

            # Скрываем экран загрузки - мир готов
            if self.loading_screen:
                self.loading_screen.set_progress(1.0)
                self.loading_screen.hide()
            else:
                self.ui.hide_loading_screen()

        elif msg_type == "inventory_update":
            # Передаём плагину инвентаря
            self._post_or_buffer_event("inventory_update", data)

        elif msg_type == "equipment_update":
            # Передаём обновление экипировки
            self._post_or_buffer_event("equipment_update", data)

        elif msg_type == "world_state":
            import time
            for p_id_str, p_info in data.get("players", {}).items():
                p_id = int(p_id_str)
                is_other_player = p_id != self.player_id

                wrapper = self.player_actor if p_id == self.player_id else self.other_players.get(p_id)
                if not wrapper:
                    wrapper = self.load_actor(p_id, LColor(0.8, 0.8, 0.8, 1))

                # Get the actual actor model for animations
                if p_id == self.player_id:
                    actor_model = self.player_actor_model
                else:
                    actor_model = wrapper.getPythonTag("actor")

                pos = p_info["pos"]
                rot = p_info["rot"]
                vel = p_info.get("vel", [0, 0, 0])

                if is_other_player:
                    # Store target state for interpolation (other players)
                    self.other_players_state[p_id] = {
                        'target_pos': LVector3(*pos),
                        'target_rot': rot,
                        'vel': LVector3(*vel),
                        'last_update': time.time(),
                    }
                else:
                    # Store target for smooth interpolation (same as other players)
                    self._local_player_target = {
                        'target_pos': LVector3(*pos),
                        'target_rot': rot,
                        'vel': LVector3(*vel),
                        'last_update': time.time(),
                    }

                # Update animations from server state
                # Skip animation for local player — client-side prediction handles it
                if actor_model and is_other_player:
                    anim_state = p_info.get("anim_state", "idle")
                    speed_ratio = p_info.get("speed_ratio", 0.0)

                    # Track logical animation state (resolved names may be identical
                    # when model has limited animations — comparing getCurrentAnim()
                    # would never detect transitions)
                    last_state = getattr(actor_model, '_last_anim_state', None)
                    if anim_state != last_state:
                        actor_model._last_anim_state = anim_state
                        resolved_anim = self._resolve_anim(actor_model, anim_state)
                        if resolved_anim:
                            actor_model.loop(resolved_anim)

                    # Sync animation speed with movement speed
                    resolved_anim = self._resolve_anim(actor_model, anim_state)
                    if resolved_anim and anim_state != "idle" and speed_ratio > 0:
                        anim_rate = 0.3 + (speed_ratio * 0.7)
                        actor_model.setPlayRate(anim_rate, resolved_anim)
                    elif resolved_anim:
                        actor_model.setPlayRate(1.0, resolved_anim)

            # Post world_state_received event for NPC renderer and other plugins
            self._post_or_buffer_event("world_state_received", data)

        elif msg_type == "kicked":
            reason = data.get("reason", "You have been kicked")
            self.logger.warning(f"Kicked from server: {reason}")
            self.disconnect()

        elif msg_type == "noclip_toggled":
            enabled = data.get("enabled", False)
            self.logger.info(f"Noclip {'enabled' if enabled else 'disabled'}")
            cc = getattr(self, 'character_controller', None)
            if cc:
                if enabled:
                    cc.enable_noclip()
                else:
                    cc.disable_noclip()
            # Hide/show player model in noclip
            if self.player_actor_model:
                if enabled:
                    self.player_actor_model.hide()
                else:
                    self.player_actor_model.show()
            self._post_or_buffer_event("noclip_toggled", data)

        else:
            self._post_or_buffer_event(msg_type, data)

    def cleanup_game_state(self):
        self.logger.info("Connection closed. Cleaning up game state.")
        self.disable_game_input()
        if self.loading_screen:
            self.loading_screen.hide()
        else:
            self.ui.hide_loading_screen()

        # Stop interpolation task
        if self.taskMgr.hasTaskNamed("interpolate-players"):
            self.taskMgr.remove("interpolate-players")
        # Stop root motion fix task
        if self.taskMgr.hasTaskNamed("fix-root-motion"):
            self.taskMgr.remove("fix-root-motion")

        if self.player_actor:
            if self.player_actor_model:
                self.player_actor_model.cleanup()
                self.player_actor_model = None
            self.player_actor.removeNode()
            self.player_actor = None
        for wrapper in self.other_players.values():
            actor = wrapper.getPythonTag("actor")
            if actor:
                actor.cleanup()
            wrapper.removeNode()
        self.other_players.clear()
        self.other_players_state.clear()

        if self.camera_controller:
            self.camera_controller.destroy()
            self.camera_controller = None

        # Cleanup scene optimizer culling
        if self.scene_optimizer:
            self.scene_optimizer.cleanup()

        self.player_id = -1
        self.is_connected = False
        self._pre_plugin_event_buffer.clear()

        # Уведомляем плагины об отключении ПЕРЕД уничтожением UI
        self.event_manager.post("client_disconnected", {})

        # Unload plugins on disconnect
        self.plugin_manager.unload_plugins()

        self.ui.destroy_all()
        if not self.dev_mode:
            self.ui.show_main_menu()
        else:
            self.exit_game() # Exit dev client on disconnect

    def disconnect_from_server(self):
        if self.writer:
            self.writer.close()
            self.writer = None
        self.is_connected = False
        self.asyncio_loop.call_soon_threadsafe(self.cleanup_game_state)

    def poll_asyncio(self, task):
        self.asyncio_loop.call_soon(self.asyncio_loop.stop)
        self.asyncio_loop.run_forever()
        return Task.cont

    async def connect_and_read(self, host: str, port: int):
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        try:
            ssl_context.load_verify_locations('certs/cert.pem')
        except FileNotFoundError:
            self.logger.critical("CRITICAL ERROR: 'certs/cert.pem' not found.")
            if not self.dev_mode: self.close_login_menu()
            return

        try:
            reader, self.writer = await asyncio.open_connection(
                host, port, ssl=ssl_context, server_hostname=host
            )
            self.is_connected = True
            self.logger.info(f"Connection to {host}:{port} successful.")
            self.on_successful_connection()
            await read_messages(reader, self.handle_network_data)
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            # Скрываем экран загрузки при ошибке
            if self.loading_screen:
                self.loading_screen.hide()
            self.ui.show_main_menu()
        finally:
            self.is_connected = False
            if self.writer: self.writer.close()
            self.asyncio_loop.call_soon_threadsafe(self.cleanup_game_state)

    def exit_game(self):
        self.plugin_manager.unload_plugins()
        if self.writer: self.writer.close()
        self.userExit()

    def is_chat_active(self) -> bool:
        # Web UI sets this flag via webview_api.set_chat_active()
        if getattr(self, '_web_chat_active', False):
            return True
        # DirectGUI fallback
        if hasattr(self, 'chat_window') and self.chat_window:
            return self.chat_window.is_open()
        return False

    def handle_escape(self):
        from nine.core.game_state import GameState
        if self.ui.game_state != GameState.IN_GAME:
            return
        if self.is_chat_active():
            self.event_manager.post("escape_key_pressed")
            return
        # Close any open panel first
        if hasattr(self.ui, '_close_active_panel') and self.ui._close_active_panel():
            return
>>>>>>> main-core-engine
        if self.in_game_menu_active:
            self.ui.hide_in_game_menu()
            self.in_game_menu_active = False
            self.enable_game_input()
        else:
            self.ui.show_in_game_menu(self)
            self.in_game_menu_active = True
            self.disable_game_input()
<<<<<<< HEAD
            
    def send_chat_packet(self, message: str):
        if not message.strip():
            return
        message_data = {"type": "chat_message", "message": message}
        self.asyncio_loop.create_task(self.send_message(self.writer, message_data))

    def on_successful_connection(self):
        auth_data = {
            "type": "auth", 
            "name": self.character_name,
            "uuid": self.client_uuid, 
            "password": self.temp_password
        }
        self.temp_password = None
        self.asyncio_loop.create_task(self.send_message(self.writer, auth_data))

    def load_actor(self, player_id, color):
        anims = {
            "walk": "nine/assets/models/player.egg",
            "idle": "nine/assets/models/player.egg"
        }
        actor = Actor("nine/assets/models/player.egg", anims)
        actor.set_scale(0.3)
        actor.setColor(color)
        actor.reparentTo(self.render)
        return actor

    def handle_network_data(self, data: dict):
        msg_type = data.get("type")

        if msg_type == "welcome":
            self.ui.hide_main_menu()
            self.player_id = data["id"]
            
            self.player_actor = self.load_actor(self.player_id, LColor(0.5, 0.8, 0.5, 1))
            self.player_actor.setPos(*data["pos"])
            
            self.camera_controller = CameraController(self, self.camera, self.win, self.player_actor, self.camera_sensitivity)
            self.enable_game_input()
            
            for p_id_str, p_info in data.get("players", {}).items():
                p_id = int(p_id_str)
                if p_id != self.player_id:
                    other_actor = self.load_actor(p_id, LColor(0.8, 0.8, 0.8, 1))
                    other_actor.setPos(*p_info["pos"])
                    self.other_players[p_id] = other_actor

        elif msg_type == "auth_failed":
            self.logger.error(f"Authentication failed: {data.get('reason', 'Unknown error')}")
            self.is_connected = False
            self.ui.show_main_menu()
            self.ui.hide_login_menu()
            self.disable_game_input()

        elif msg_type == "player_joined":
            p_id = data["id"]
            if p_id != self.player_id:
                p_info = data["player_info"]
                other_actor = self.load_actor(p_id, LColor(0.8, 0.8, 0.8, 1))
                other_actor.setPos(*p_info["pos"])
                self.other_players[p_id] = other_actor

        elif msg_type == "player_left":
            p_id = data["id"]
            if p_id in self.other_players:
                actor = self.other_players.pop(p_id)
                actor.cleanup()
                actor.removeNode()

        elif msg_type == "world_state":
            for p_id_str, p_info in data.get("players", {}).items():
                p_id = int(p_id_str)
                if p_id in self.other_players:
                    actor = self.other_players[p_id]
                    actor.setPos(*p_info["pos"])
                    actor.setHpr(*p_info["rot"])
                    anim_state = p_info.get("anim_state", "idle")
                    if actor.getCurrentAnim() != anim_state:
                        actor.loop(anim_state)
        else:
            self.event_manager.post(msg_type, data)

    async def poll_asyncio(self, task):
        self.asyncio_loop.stop()
        self.asyncio_loop.run_forever()
        return Task.cont

    async def send_message(self, writer: asyncio.StreamWriter, data: dict):
        if not writer or writer.is_closing(): return
        payload = json.dumps(data).encode("utf-8")
        header = struct.pack("!I", len(payload))
        writer.write(header + payload)
        await writer.drain()

    async def connect_and_read(self, host: str):
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        try:
            ssl_context.load_verify_locations('certs/cert.pem')
        except FileNotFoundError:
            self.logger.critical("CRITICAL ERROR: Certificate file 'certs/cert.pem' not found.")
            self.close_login_menu()
            return
            
        reader = None
        try:
            reader, self.writer = await asyncio.open_connection(
                host, PORT, ssl=ssl_context, server_hostname=host if host != "localhost" else None
            )
            self.is_connected = True
            self.logger.info("Successfully established TLS connection with the server.")
            self.on_successful_connection()
            await self.read_messages(reader)
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
        finally:
            self.is_connected = False
            if self.writer:
                self.writer.close()
                if not self.asyncio_loop.is_closed():
                    try: pass
                    except: pass
            if reader:
                reader.feed_eof()
            self.asyncio_loop.call_soon_threadsafe(self.cleanup_game_state)

    def disconnect_from_server(self):
        if self.is_connected:
            self.logger.info("Disconnecting from server and cleaning up game state.")
            self.is_connected = False
            if self.writer:
                self.writer.close()
            if self.in_game_menu_active:
                self.ui.hide_in_game_menu()
                self.in_game_menu_active = False
                self.enable_game_input()

    def cleanup_game_state(self):
        self.logger.info("Connection closed.")
        self.disable_game_input()

        if self.player_actor:
            self.player_actor.cleanup()
            self.player_actor.removeNode()
            self.player_actor = None
        
        for actor in self.other_players.values():
            actor.cleanup()
            actor.removeNode()
        self.other_players.clear()

        if self.camera_controller:
            self.camera_controller.destroy()
            self.camera_controller = None
            
        self.player_id = -1
        self.ui.destroy_all()
        self.ui.show_main_menu()

    async def read_messages(self, reader: asyncio.StreamReader):
        while self.is_connected:
            try:
                header = await reader.readexactly(4)
                if not header: break
                msg_len = struct.unpack("!I", header)[0]
                payload = await reader.readexactly(msg_len)
                if not payload: break
                data = json.loads(payload.decode("utf-8"))
                self.asyncio_loop.call_soon_threadsafe(self.handle_network_data, data)
            except (asyncio.IncompleteReadError, ConnectionResetError):
                self.logger.warning("Lost connection to the server.")
                self.is_connected = False
            except Exception as e:
                self.logger.error(f"Error reading message: {e}")
                self.is_connected = False
=======

    def send_message(self, data: dict):
        """Отправляет сообщение на сервер."""
        if self.is_connected and self.writer:
            self.asyncio_loop.create_task(send_message(self.writer, data))

    def disconnect(self):
        """Отключается от сервера и возвращается в меню."""
        self.disconnect_from_server()

    def send_chat_packet(self, message):
        # Accept both str and dict (for backwards compatibility)
        if isinstance(message, dict):
            message = message.get("message", "")
        if message and message.strip():
            self.asyncio_loop.create_task(send_message(self.writer, {"type": "chat_message", "message": message}))

    def send_item_use_packet(self, data: dict):
        """Отправляет запрос на использование предмета."""
        if self.is_connected and self.player_id >= 0:
            packet = {
                "type": "item_use",
                "slot": data.get("slot", 0),
            }
            self.asyncio_loop.create_task(send_message(self.writer, packet))

    def send_item_drop_packet(self, data: dict):
        """Отправляет запрос на выбрасывание предмета."""
        if self.is_connected and self.player_id >= 0:
            packet = {
                "type": "item_drop",
                "slot": data.get("slot", 0),
                "count": data.get("count", 1),
            }
            self.asyncio_loop.create_task(send_message(self.writer, packet))

    def send_equip_item_packet(self, data: dict):
        """Отправляет запрос на экипировку предмета."""
        if self.is_connected and self.player_id >= 0:
            packet = {
                "type": "equip_item",
                "inventory_slot": data.get("inventory_slot", 0),
            }
            eq_slot = data.get("equipment_slot")
            if eq_slot:
                packet["equipment_slot"] = eq_slot
            self.asyncio_loop.create_task(send_message(self.writer, packet))

    def send_unequip_item_packet(self, data: dict):
        """Отправляет запрос на снятие экипировки."""
        if self.is_connected and self.player_id >= 0:
            packet = {
                "type": "unequip_item",
                "equipment_slot": data.get("equipment_slot", ""),
            }
            self.asyncio_loop.create_task(send_message(self.writer, packet))

    def _handle_send_to_server(self, event_data: dict):
        """Отправляет локальное событие на сервер как сетевой пакет."""
        if not self.writer or not self.is_connected:
            return

        message = {"type": event_data.get("type")}
        for key, value in event_data.items():
            if key != "type":
                message[key] = value

        self.asyncio_loop.create_task(send_message(self.writer, message))

    def open_login_menu(self): self.ui.show_login_menu(default_ip="localhost:9009", default_name=self.user_config.get("nickname", self.character_name))
    def close_login_menu(self): self.ui.hide_login_menu(); self.ui.show_main_menu()
    def show_settings_menu(self): self.ui.show_settings_menu(self)
>>>>>>> main-core-engine


if __name__ == "__main__":
    if "panda3d" not in sys.modules:
<<<<<<< HEAD
        try:
            import panda3d
        except ImportError:
            logging.basicConfig(level=logging.CRITICAL)
            logging.critical("Panda3D not found. Please install it: pip install panda3d")
            sys.exit(1)

    app = GameClient()
    try:
        app.run()
    except SystemExit:
        logging.info("Exiting application.")
    finally:
        if hasattr(app, 'asyncio_loop') and app.asyncio_loop.is_running():
            app.asyncio_loop.stop()
=======
        logging.basicConfig(level=logging.CRITICAL)
        logging.critical("Fatal Error: Panda3D is not installed. Please run 'pip install panda3d'.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="nine game client.")
    parser.add_argument("--dev", action="store_true", help="Enable development mode.")
    parser.add_argument("--name", type=str, default="DevPlayer", help="Player name (dev mode).")
    parser.add_argument("--uuid", type=str, default=None, help="Player UUID (dev mode).")
    args = parser.parse_args()

    app = GameClient(
        dev_mode=args.dev,
        name=args.name,
        client_uuid=args.uuid
    )

    # Custom exception hook to log uncaught exceptions
    def exception_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        app.logger.error("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = exception_hook

    try:
        app.run()
    except (SystemExit, KeyboardInterrupt):
        logging.info("Exiting application.")
    except Exception as e:
        app.logger.exception("Fatal error during execution:")
        raise
    finally:
        if hasattr(app, 'asyncio_loop') and app.asyncio_loop.is_running():
            app.asyncio_loop.stop()

>>>>>>> main-core-engine
