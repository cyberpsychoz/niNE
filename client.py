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
from nine.ui.manager import UIManager

loadPrcFileData("", "audio-library-name null")


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
        except (FileNotFoundError, json.JSONDecodeError):
            self.camera_sensitivity = 1.0

        self.player_id = -1
        self.is_connected = False
        self.is_server = False  # Plugins check this
        self.character_name = name
        self.client_uuid = client_uuid if client_uuid else self._get_or_create_uuid()

        self.player_actor = None
        self.player_actor_model = None  # Actual Actor for animations
        self.other_players = {}

        self.writer = None
        self.in_game_menu_active = False
        self.camera_controller = None

        # --- UI Setup ---
        callbacks = {
            "connect": self.open_login_menu, "exit": self.exit_game,
            "attempt_login": self.attempt_login, "close_login_menu": self.close_login_menu,
            "settings": self.show_settings_menu,
        }
        self.ui = UIManager(self, callbacks)
        self.event_manager.subscribe("client_send_chat_message", self.send_chat_packet)

        # --- Final Initializations ---
        self.plugin_manager.load_plugins()
        self.setup_visual_scene()
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

    def setup_visual_scene(self):
        """Set up the visual environment with ground and reference objects."""
        from panda3d.core import AmbientLight, DirectionalLight, CardMaker

        # Lighting
        ambient = AmbientLight("ambient")
        ambient.setColor((0.4, 0.4, 0.45, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

        sun = DirectionalLight("sun")
        sun.setColor((0.9, 0.85, 0.8, 1))
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(45, -45, 0)
        self.render.setLight(sun_np)

        # Ground plane - green grass-like color
        cm = CardMaker("ground")
        cm.setFrame(-100, 100, -100, 100)
        ground = self.render.attachNewNode(cm.generate())
        ground.setP(-90)
        ground.setPos(0, 0, 0)
        ground.setColor(0.3, 0.5, 0.25, 1)  # Grass green

        # Grid lines on ground for orientation
        from panda3d.core import LineSegs
        lines = LineSegs()
        lines.setThickness(1.5)
        lines.setColor(0.25, 0.4, 0.2, 1)  # Darker green
        for i in range(-10, 11):
            pos = i * 5
            lines.moveTo(pos, -50, 0.01)
            lines.drawTo(pos, 50, 0.01)
            lines.moveTo(-50, pos, 0.01)
            lines.drawTo(50, pos, 0.01)
        self.render.attachNewNode(lines.create())

        # Reference cubes at cardinal directions
        self._create_reference_cube(0, 10, "North", (0.2, 0.4, 0.8, 1))   # Blue - North (+Y)
        self._create_reference_cube(0, -10, "South", (0.8, 0.3, 0.2, 1))  # Red - South (-Y)
        self._create_reference_cube(10, 0, "East", (0.2, 0.7, 0.3, 1))    # Green - East (+X)
        self._create_reference_cube(-10, 0, "West", (0.7, 0.6, 0.2, 1))   # Yellow - West (-X)

        # Some obstacles for reference
        self._create_box(5, 5, 1.0, (0.6, 0.6, 0.6, 1))
        self._create_box(-5, 8, 0.5, (0.5, 0.5, 0.55, 1))
        self._create_box(8, -3, 1.5, (0.55, 0.5, 0.5, 1))
        self._create_box(-7, -6, 0.8, (0.5, 0.55, 0.5, 1))

    def _create_reference_cube(self, x, y, label, color):
        """Create a colored cube with label for orientation."""
        from panda3d.core import CardMaker
        from direct.gui.OnscreenText import OnscreenText

        # Simple cube using 6 cards
        size = 1.0
        cube = self.render.attachNewNode(f"cube_{label}")
        cube.setPos(x, y, size / 2)

        cm = CardMaker("face")
        cm.setFrame(-size/2, size/2, -size/2, size/2)

        # Create 6 faces
        faces = [
            ((0, 0, size/2), (0, 0, 0)),      # Top
            ((0, 0, -size/2), (180, 0, 0)),   # Bottom
            ((0, size/2, 0), (-90, 0, 0)),    # Front
            ((0, -size/2, 0), (90, 0, 0)),    # Back
            ((size/2, 0, 0), (0, 90, 0)),     # Right
            ((-size/2, 0, 0), (0, -90, 0)),   # Left
        ]

        for pos, hpr in faces:
            face = cube.attachNewNode(cm.generate())
            face.setPos(*pos)
            face.setHpr(*hpr)
            face.setColor(*color)

    def _create_box(self, x, y, height, color):
        """Create a simple box obstacle."""
        from panda3d.core import CardMaker

        size = 1.5
        box = self.render.attachNewNode(f"box_{x}_{y}")
        box.setPos(x, y, height / 2)

        cm = CardMaker("face")
        cm.setFrame(-size/2, size/2, -height/2, height/2)

        # Front and back
        for z_mult in [1, -1]:
            face = box.attachNewNode(cm.generate())
            face.setPos(0, size/2 * z_mult, 0)
            face.setHpr(0 if z_mult == 1 else 180, 0, 0)
            face.setColor(*color)

        # Left and right
        for x_mult in [1, -1]:
            face = box.attachNewNode(cm.generate())
            face.setPos(size/2 * x_mult, 0, 0)
            face.setHpr(90 * x_mult, 0, 0)
            face.setColor(*color)

        # Top
        cm2 = CardMaker("top")
        cm2.setFrame(-size/2, size/2, -size/2, size/2)
        top = box.attachNewNode(cm2.generate())
        top.setPos(0, 0, height/2)
        top.setP(-90)
        top.setColor(*[c * 1.1 for c in color[:3]] + [1])

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
            if self.dev_mode:
                self.input_task = self.taskMgr.add(self.update_movement_task, "update-movement-task")
            else:
                self.input_task = self.taskMgr.add(self.send_input_task, "send-input-task")

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
        """Client-side prediction movement task for dev mode."""
        if not self.is_connected or not self.player_actor or self.in_game_menu_active:
            return Task.cont

        if not self.camera_controller:
            return Task.cont

        from math import atan2, degrees

        dt = globalClock.getDt()

        # Initialize dev mode state
        if not hasattr(self, '_dev_state'):
            self._dev_state = {
                'current_speed': 0.0,
                'move_direction': LVector3(0, 1, 0),
                'current_heading': 0.0,
                'current_anim_rate': 1.0,
            }

        # Movement parameters
        walk_speed = 5.0
        run_speed = 10.0
        acceleration = 30.0
        deceleration = 40.0
        rotation_speed = 10.0  # How fast character turns

        # Build input from WASD
        input_x = 0
        input_y = 0
        if self.keyMap["w"]: input_y += 1
        if self.keyMap["s"]: input_y -= 1
        if self.keyMap["a"]: input_x -= 1
        if self.keyMap["d"]: input_x += 1

        is_running = self.keyMap.get("shift", False)
        has_input = input_x != 0 or input_y != 0

        # Calculate world-space movement vector from camera
        if has_input:
            move_vector = self.camera_controller.get_movement_vector(input_x, input_y)
            self._dev_state['move_direction'] = move_vector

        # Calculate speed
        if has_input:
            target_speed = run_speed if is_running else walk_speed
            self._dev_state['current_speed'] = min(
                self._dev_state['current_speed'] + acceleration * dt,
                target_speed
            )
        else:
            self._dev_state['current_speed'] = max(
                self._dev_state['current_speed'] - deceleration * dt,
                0.0
            )

        is_moving = self._dev_state['current_speed'] > 0.1

        if is_moving:
            # Select animation (use actor model, not wrapper)
            target_anim = "run_forward" if is_running else "walk_forward"
            if self.player_actor_model.getCurrentAnim() != target_anim:
                self.player_actor_model.loop(target_anim)

            # Sync animation speed (only update if changed significantly to avoid jitter)
            speed_ratio = self._dev_state['current_speed'] / run_speed
            target_anim_rate = 0.5 + (speed_ratio * 0.5)
            if abs(target_anim_rate - self._dev_state['current_anim_rate']) > 0.05:
                self._dev_state['current_anim_rate'] = target_anim_rate
                self.player_actor_model.setPlayRate(target_anim_rate, target_anim)

            # Move player
            move_dir = self._dev_state['move_direction']
            velocity = move_dir * self._dev_state['current_speed'] * dt
            self.player_actor.setPos(self.player_actor.getPos() + velocity)

            # Smooth rotation towards movement direction
            # Add 180 because model faces -Y by default
            target_heading = degrees(atan2(-move_dir.x, move_dir.y)) + 180
            current_heading = self._dev_state['current_heading']
            new_heading = self._lerp_angle(current_heading, target_heading, rotation_speed * dt)
            self._dev_state['current_heading'] = new_heading
            self.player_actor.setH(new_heading)
        else:
            if self.player_actor_model.getCurrentAnim() != "idle":
                self.player_actor_model.loop("idle")
                self._dev_state['current_anim_rate'] = 1.0

        # Send movement data to server
        pos = self.player_actor.getPos()
        rot = self.player_actor.getHpr()

        move_data = {
            "type": "move",
            "pos": [pos.x, pos.y, pos.z],
            "rot": [rot.x, rot.y, rot.z],
            "is_moving": is_moving,
            "is_running": is_running
        }
        self.asyncio_loop.create_task(send_message(self.writer, move_data))

        return Task.cont

    def attempt_login(self):
        credentials = self.ui.get_login_credentials()
        ip_str = credentials.get("ip", "localhost:9009")
        self.character_name = credentials.get("name", "Player")

        if not ip_str or not self.character_name:
            self.logger.warning("IP and Name fields must be filled.")
            return

        try:
            host, port_str = ip_str.split(":")
            port = int(port_str)
        except ValueError:
            self.logger.warning(f"Invalid address format: {ip_str}. Expected 'host:port'.")
            return

        self.ui.hide_login_menu()
        self.asyncio_loop.create_task(self.connect_and_read(host, port))

    def on_successful_connection(self):
        if self.dev_mode:
            auth_data = {"type": "dev_auth", "name": self.character_name, "uuid": self.client_uuid}
        else:
            auth_data = {"type": "auth", "name": self.character_name}
        self.asyncio_loop.create_task(send_message(self.writer, auth_data))

    def load_actor(self, player_id, color, is_local_player=False):
        # Model contains embedded animations: idle, walk_forward, walk_backward, run_forward, strafe_left, strafe_right
        actor = Actor("nine/assets/models/player.bam")
        actor.set_scale(0.3)
        actor.setColor(color)

        # Create wrapper node for positioning to avoid root motion jitter
        # We move the wrapper, actor stays at origin relative to it
        wrapper = self.render.attachNewNode(f"player_{player_id}")
        actor.reparentTo(wrapper)

        # Start with idle animation
        actor.loop("idle")

        if is_local_player:
            self.player_actor = wrapper
            self.player_actor_model = actor  # Keep reference to actual actor for animations
        else:
            self.other_players[player_id] = wrapper
            # Store actor reference on wrapper for animation access
            wrapper.setPythonTag("actor", actor)
        return wrapper

    def handle_network_data(self, data: dict):
        msg_type = data.get("type")

        if msg_type == "welcome":
            if not self.dev_mode: self.ui.hide_main_menu()
            self.player_id = data["id"]
            self.load_actor(self.player_id, LColor(0.5, 0.8, 0.5, 1), is_local_player=True)
            self.player_actor.setPos(*data["pos"])
            self.camera_controller = CameraController(self, self.camera, self.win, self.player_actor, self.camera_sensitivity)
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

        elif msg_type == "world_state":
            for p_id_str, p_info in data.get("players", {}).items():
                p_id = int(p_id_str)
                wrapper = self.player_actor if p_id == self.player_id else self.other_players.get(p_id)
                if not wrapper:
                    wrapper = self.load_actor(p_id, LColor(0.8, 0.8, 0.8, 1))

                # Get the actual actor model for animations
                if p_id == self.player_id:
                    actor_model = self.player_actor_model
                else:
                    actor_model = wrapper.getPythonTag("actor")

                # Server-authoritative clients get position/rotation from server.
                # Dev mode clients only update other players, not themselves.
                is_other_player = p_id != self.player_id
                if not self.dev_mode or is_other_player:
                    wrapper.setPos(*p_info["pos"])
                    wrapper.setHpr(*p_info["rot"])
                # Update animations (dev mode handles own player's animations locally)
                if (not self.dev_mode or is_other_player) and actor_model:
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
        else:
            self.event_manager.post(msg_type, data)

    def cleanup_game_state(self):
        self.logger.info("Connection closed. Cleaning up game state.")
        self.disable_game_input()

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

        if self.camera_controller:
            self.camera_controller.destroy()
            self.camera_controller = None

        self.player_id = -1
        self.is_connected = False
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

    def send_chat_packet(self, message: str):
        if message.strip():
            self.asyncio_loop.create_task(send_message(self.writer, {"type": "chat_message", "message": message}))

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

