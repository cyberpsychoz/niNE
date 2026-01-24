import argparse
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
from panda3d.core import (
    CardMaker,
    LColor,
    loadPrcFileData,
    NodePath,
    LVector3,
)

from nine.core.camera_controller import CameraController
from nine.core.events import EventManager
from nine.core.plugins import PluginManager
from nine.core.network import send_message, read_messages
from nine.core.scene_optimizer import SceneOptimizer, LODSettings
from nine.ui.manager import UIManager
from nine.ui.loading_screen import LoadingScreen

# Audio enabled - using OpenAL (default)
# loadPrcFileData("", "audio-library-name null")  # Uncomment to disable audio


class GameClient(ShowBase):
    def __init__(self, dev_mode=False, name="Player", client_uuid=None):
        # --- Standard setup (logging, asyncio, ShowBase) ---
        log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler("client.log", mode='w')
        file_handler.setFormatter(log_formatter)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)

        try:
            self.asyncio_loop = asyncio.get_running_loop()
        except RuntimeError:
            self.asyncio_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.asyncio_loop)

        ShowBase.__init__(self)
        self.disableMouse()

        # --- Core Systems ---
        self.event_manager = EventManager()
        self.plugin_manager = PluginManager(self, self.event_manager)

        # --- Config and State ---
        self.dev_mode = dev_mode
        try:
            with open("config.json") as f:
                config = json.load(f)
            self.camera_sensitivity = config.get("camera_sensitivity", 1.0)
            self.third_person_camera = config.get("third_person_camera", True)
            self.invert_mouse_x = config.get("invert_mouse_x", False)
            self.invert_mouse_y = config.get("invert_mouse_y", False)
            self.fov = config.get("fov", 70)
        except (FileNotFoundError, json.JSONDecodeError):
            self.camera_sensitivity = 1.0
            self.third_person_camera = True
            self.invert_mouse_x = False
            self.invert_mouse_y = False
            self.fov = 70

        self.player_id = -1
        self.is_connected = False
        self.is_server = False  # Plugins check this
        self.character_name = name
        self.client_uuid = client_uuid if client_uuid else self._get_or_create_uuid()

        self.player_actor = None
        self.player_actor_model = None  # Actual Actor for animations
        self.other_players = {}  # {id: wrapper_node}
        self.other_players_state = {}  # {id: {target_pos, target_rot, vel, last_update}}

        self.writer = None
        self.in_game_menu_active = False
        self.camera_controller = None

        # D&D character data
        self.account_uuid = None
        self.password = ""  # Stored for auth
        self.current_character = None  # Currently selected character data

        # --- UI Setup ---
        callbacks = {
            "connect": self.open_login_menu, "exit": self.exit_game,
            "attempt_login": self.attempt_login, "close_login_menu": self.close_login_menu,
            "settings": self.show_settings_menu,
        }
        self.ui = UIManager(self, callbacks)
        self.loading_screen = LoadingScreen(self.ui)
        self.loading_screen.hide()  # Скрыт по умолчанию
        self.event_manager.subscribe("client_send_chat_message", self.send_chat_packet)
        self.event_manager.subscribe("client_item_use", self.send_item_use_packet)
        self.event_manager.subscribe("client_item_drop", self.send_item_drop_packet)

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
        self.plugin_manager.load_plugins()
        self.map_model = None
        self.logger.info("Client initialized.")

        # --- Input Handling ---
        self.keyMap = {"w": False, "a": False, "s": False, "d": False, "space": False, "shift": False}
        self.accept("w", self.update_key_map, ["w", True])
        self.accept("w-up", self.update_key_map, ["w", False])
        self.accept("a", self.update_key_map, ["a", True])
        self.accept("a-up", self.update_key_map, ["a", False])
        self.accept("s", self.update_key_map, ["s", True])
        self.accept("s-up", self.update_key_map, ["s", False])
        self.accept("d", self.update_key_map, ["d", True])
        self.accept("d-up", self.update_key_map, ["d", False])
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

    def _get_or_create_uuid(self) -> str:
        uuid_file = Path(".client_uuid")
        if uuid_file.exists():
            try:
                return str(uuid.UUID(uuid_file.read_text().strip()))
            except (ValueError, IndexError):
                pass
        client_uuid = str(uuid.uuid4())
        uuid_file.write_text(client_uuid)
        return client_uuid

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
            # Fallback: simple ground plane
            cm = CardMaker("ground")
            cm.setFrame(-100, 100, -100, 100)
            self.map_model = self.render.attachNewNode(cm.generate())
            self.map_model.setP(-90)
            self.map_model.setColor(0.2, 0.25, 0.2, 1)

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
        # Блокируем ввод движения когда чат открыт
        if self.is_chat_active():
            return
        self.keyMap[key] = state

    def disable_game_input(self):
        if self.camera_controller:
            self.camera_controller.stop()
        if self.input_task:
            self.taskMgr.remove(self.input_task)
            self.input_task = None
        for key in self.keyMap: self.keyMap[key] = False

    def enable_game_input(self):
        if self.camera_controller:
            self.camera_controller.start()
        if not self.input_task:
            # Always use server-authoritative movement (send input state to server)
            # Dev mode only affects connection behavior, not movement model
            self.input_task = self.taskMgr.add(self.send_input_task, "send-input-task")
        # Start interpolation task for other players
        if not self.taskMgr.hasTaskNamed("interpolate-players"):
            self.taskMgr.add(self.interpolate_other_players_task, "interpolate-players")

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
        """Client-side prediction movement task for dev mode with Source-like physics."""
        if not self.is_connected or not self.player_actor or self.in_game_menu_active:
            return Task.cont

        if not self.camera_controller:
            return Task.cont

        from math import atan2, degrees

        dt = globalClock.getDt()

        # Initialize dev mode state with velocity-based physics
        if not hasattr(self, '_dev_state'):
            self._dev_state = {
                'velocity': LVector3(0, 0, 0),
                'current_heading': 0.0,
                'current_anim_rate': 1.0,
                'send_timer': 0.0,  # Rate limit network sends
            }

        # === Movement parameters (same as server) ===
        walk_speed = 1.25
        run_speed = 2.5
        ground_accel = 8.0
        friction = 6.0
        stop_speed = 0.5
        rotation_speed = 12.0

        # Build input from WASD
        input_x = 0
        input_y = 0
        if self.keyMap["w"]: input_y += 1
        if self.keyMap["s"]: input_y -= 1
        if self.keyMap["a"]: input_x -= 1
        if self.keyMap["d"]: input_x += 1

        is_running = self.keyMap.get("shift", False)
        has_input = input_x != 0 or input_y != 0

        velocity = self._dev_state['velocity']
        wish_speed = run_speed if is_running else walk_speed

        # Apply friction
        speed = velocity.length()
        if speed > 0.01:
            if not has_input:
                # Full friction when not moving
                control = max(speed, stop_speed)
                drop = control * friction * dt
                new_speed = max(speed - drop, 0)
                velocity *= (new_speed / speed) if speed > 0 else 0
            else:
                # Reduced friction when moving
                control = max(speed, stop_speed)
                drop = control * friction * dt * 0.3
                new_speed = max(speed - drop, 0)
                velocity *= (new_speed / speed) if speed > 0 else 0

        # Accelerate towards input direction
        if has_input:
            move_dir = self.camera_controller.get_movement_vector(input_x, input_y)
            move_dir.normalize()

            # Source-like acceleration
            current_speed = velocity.dot(move_dir)
            add_speed = wish_speed - current_speed
            if add_speed > 0:
                accel_speed = min(ground_accel * wish_speed * dt, add_speed)
                velocity += move_dir * accel_speed

        self._dev_state['velocity'] = velocity

        # Check if moving
        speed = velocity.length()
        is_moving = speed > 0.1

        # Update animation
        if is_moving:
            target_anim = "run_forward" if is_running else "walk_forward"
            if self.player_actor_model.getCurrentAnim() != target_anim:
                self.player_actor_model.loop(target_anim)

            speed_ratio = min(speed / run_speed, 1.0)
            target_anim_rate = 0.5 + (speed_ratio * 0.5)
            if abs(target_anim_rate - self._dev_state['current_anim_rate']) > 0.05:
                self._dev_state['current_anim_rate'] = target_anim_rate
                self.player_actor_model.setPlayRate(target_anim_rate, target_anim)

            # Move player
            self.player_actor.setPos(self.player_actor.getPos() + velocity * dt)

            # Smooth rotation towards velocity direction
            vel_dir = LVector3(velocity)
            vel_dir.normalize()
            target_heading = degrees(atan2(-vel_dir.x, vel_dir.y)) + 180
            current_heading = self._dev_state['current_heading']
            new_heading = self._lerp_angle(current_heading, target_heading, rotation_speed * dt)
            self._dev_state['current_heading'] = new_heading
            self.player_actor.setH(new_heading)
        else:
            if self.player_actor_model.getCurrentAnim() != "idle":
                self.player_actor_model.loop("idle")
                self._dev_state['current_anim_rate'] = 1.0

        # Rate limit network sends (20 times per second max)
        self._dev_state['send_timer'] += dt
        if self._dev_state['send_timer'] >= 0.05:
            self._dev_state['send_timer'] = 0.0

            pos = self.player_actor.getPos()
            rot = self.player_actor.getHpr()

            move_data = {
                "type": "move",
                "pos": [pos.x, pos.y, pos.z],
                "rot": [rot.x, rot.y, rot.z],
                "vel": [velocity.x, velocity.y, velocity.z],
                "is_moving": is_moving,
                "is_running": is_running
            }
            self.asyncio_loop.create_task(send_message(self.writer, move_data))

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
        self.loading_screen.set_title("ПОДКЛЮЧЕНИЕ")
        self.loading_screen.set_status("Подключение к серверу...")
        self.loading_screen.set_progress(0.1)
        self.loading_screen.show()
        self.asyncio_loop.create_task(self.connect_and_read(host, port))

    def on_successful_connection(self):
        # Обновляем экран загрузки
        self.loading_screen.set_status("Авторизация...")
        self.loading_screen.set_progress(0.3)

        if self.dev_mode:
            auth_data = {"type": "dev_auth", "name": self.character_name, "uuid": self.client_uuid}
        else:
            # D&D auth with password
            auth_data = {
                "type": "auth",
                "name": self.character_name,
                "password": self.password
            }
        self.asyncio_loop.create_task(send_message(self.writer, auth_data))
        # Clear password from memory after sending
        self.password = ""

    def load_actor(self, player_id, color, is_local_player=False):
        # Model contains embedded animations: idle, walk_forward, walk_backward, run_forward, strafe_left, strafe_right
        actor = Actor("nine/assets/models/base.bam")
        actor.set_scale(0.3)
        actor.setColor(color)

        # Create wrapper node for positioning to avoid root motion jitter
        # We move the wrapper, actor stays at origin relative to it
        wrapper = self.render.attachNewNode(f"player_{player_id}")
        actor.reparentTo(wrapper)

        # Fix root motion: lock actor position relative to wrapper
        # Animation may move the actor, we reset it every frame
        actor.setPos(0, 0, 0)

        # Start with idle animation
        actor.loop("idle")

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

    def handle_network_data(self, data: dict):
        msg_type = data.get("type")

        # ===== D&D Auth & Character Messages =====
        if msg_type == "auth_success":
            # Авторизация успешна, сохраняем account_uuid и запрашиваем список персонажей
            self.account_uuid = data.get("account_uuid")
            self.logger.info(f"Auth success, account: {self.account_uuid}")
            # Запрашиваем список персонажей
            self.send_message({"type": "character_list_request"})

        elif msg_type == "auth_failed":
            # Авторизация не удалась
            reason = data.get("reason", "Unknown error")
            self.logger.warning(f"Auth failed: {reason}")
            # Возвращаемся в меню
            self.disconnect()
            # TODO: Показать сообщение об ошибке

        elif msg_type == "character_list":
            # Получен список персонажей - показываем UI выбора
            characters = data.get("characters", [])
            max_characters = data.get("max_characters", 2)
            self.logger.info(f"Character list received: {len(characters)} characters")
            self.ui.show_character_select(characters, max_characters, self)

        elif msg_type == "character_created":
            # Персонаж успешно создан - обновляем список
            character = data.get("character")
            self.logger.info(f"Character created: {character.get('character_name')}")
            # Запрашиваем обновлённый список
            self.send_message({"type": "character_list_request"})
            # Скрываем экран создания, показываем выбор
            self.ui.hide_character_create()

        elif msg_type == "character_create_failed":
            # Создание персонажа не удалось
            reason = data.get("reason", "Unknown error")
            self.logger.warning(f"Character create failed: {reason}")
            # TODO: Показать сообщение об ошибке в UI создания

        elif msg_type == "character_deleted":
            # Персонаж удалён - запрашиваем обновлённый список
            char_uuid = data.get("character_uuid")
            self.logger.info(f"Character deleted: {char_uuid}")
            self.send_message({"type": "character_list_request"})

        elif msg_type == "welcome":
            # Скрываем экран загрузки
            self.loading_screen.set_progress(1.0)
            self.loading_screen.hide()

            # Переходим в игровое состояние (скрывает меню и уведомляет плагины)
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
            self.load_actor(self.player_id, LColor(0.5, 0.8, 0.5, 1), is_local_player=True)
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
            self.loading_screen.set_title("ЗАГРУЗКА МИРА")
            self.loading_screen.set_status("Загрузка карты...")
            self.loading_screen.set_progress(0.5)

            # Загружаем карту
            map_config = data.get("map", {})
            map_model = map_config.get("model", "nine/assets/models/maps/map.bam")
            self._load_map(map_model)

            self.loading_screen.set_status("Настройка освещения...")
            self.loading_screen.set_progress(0.7)

            # Передаём плагинам для обработки освещения и скайбокса
            self.event_manager.post("world_config", data)
            self.logger.info("World config received and applied")

            self.loading_screen.set_status("Ожидание персонажа...")
            self.loading_screen.set_progress(0.9)

        elif msg_type == "inventory_update":
            # Передаём плагину инвентаря
            self.event_manager.post("inventory_update", data)

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
                    # Server-authoritative mode: directly set own position
                    # (applies to both normal and dev clients now)
                    wrapper.setPos(*pos)
                    wrapper.setHpr(*rot)

                # Update animations from server state
                if actor_model:
                    anim_state = p_info.get("anim_state", "idle")
                    speed_ratio = p_info.get("speed_ratio", 0.0)

                    current_anim = actor_model.getCurrentAnim()
                    if current_anim != anim_state:
                        actor_model.loop(anim_state)

                    # Sync animation speed with movement speed
                    if anim_state != "idle" and speed_ratio > 0:
                        anim_rate = 0.3 + (speed_ratio * 0.7)
                        actor_model.setPlayRate(anim_rate, anim_state)
                    else:
                        actor_model.setPlayRate(1.0, anim_state)

            # Post world_state_received event for NPC renderer and other plugins
            self.event_manager.post("world_state_received", data)
        else:
            self.event_manager.post(msg_type, data)

    def cleanup_game_state(self):
        self.logger.info("Connection closed. Cleaning up game state.")
        self.disable_game_input()
        self.loading_screen.hide()

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

        # Уведомляем плагины об отключении ПЕРЕД уничтожением UI
        self.event_manager.post("client_disconnected", {})

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
        # Проверяем реальное состояние чата (устанавливается плагином)
        if hasattr(self, 'chat_window') and self.chat_window:
            return self.chat_window.is_open()
        return False

    def handle_escape(self):
        if self.is_chat_active():
            self.event_manager.post("escape_key_pressed")
            return
        if self.in_game_menu_active:
            self.ui.hide_in_game_menu()
            self.in_game_menu_active = False
            self.enable_game_input()
        else:
            self.ui.show_in_game_menu(self)
            self.in_game_menu_active = True
            self.disable_game_input()

    def send_message(self, data: dict):
        """Отправляет сообщение на сервер."""
        if self.is_connected and self.writer:
            self.asyncio_loop.create_task(send_message(self.writer, data))

    def disconnect(self):
        """Отключается от сервера и возвращается в меню."""
        self.disconnect_from_server()

    def send_chat_packet(self, message: str):
        if message.strip():
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

    def open_login_menu(self): self.ui.show_login_menu(default_ip="localhost:9009", default_name=self.character_name)
    def close_login_menu(self): self.ui.hide_login_menu(); self.ui.show_main_menu()
    def show_settings_menu(self): self.ui.show_settings_menu(self)


if __name__ == "__main__":
    if "panda3d" not in sys.modules:
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
    try:
        app.run()
    except (SystemExit, KeyboardInterrupt):
        logging.info("Exiting application.")
    finally:
        if hasattr(app, 'asyncio_loop') and app.asyncio_loop.is_running():
            app.asyncio_loop.stop()

