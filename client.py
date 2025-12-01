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
        self.keyMap = {"w": False, "a": False, "s": False, "d": False, "space": False}
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
        cm = CardMaker("ground")
        cm.setFrame(-50, 50, -50, 50)
        ground_visual = self.render.attachNewNode(cm.generate())
        ground_visual.setP(-90)
        ground_visual.setPos(0, 0, 0)

    def update_key_map(self, key, state):
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
        if self.is_connected:
            input_message = {"type": "input", "state": self.keyMap}
            self.asyncio_loop.create_task(send_message(self.writer, input_message))
        return Task.cont

    def update_movement_task(self, task):
        """Client-side prediction movement task for dev mode."""
        if not self.is_connected or not self.player_actor or self.in_game_menu_active:
            return Task.cont

        dt = globalClock.getDt()
        move_speed = 10.0
        move_vec = LVector3(0, 0, 0)
        if self.keyMap["w"]: move_vec.y += 1
        if self.keyMap["s"]: move_vec.y -= 1
        if self.keyMap["a"]: move_vec.x -= 1
        if self.keyMap["d"]: move_vec.x += 1

        if move_vec.length_squared() > 0:
            if self.player_actor.getCurrentAnim() != "walk":
                self.player_actor.loop("walk")

            move_vec.normalize()
            if self.camera_controller:
                camera_pivot = self.camera_controller.get_camera_pivot()
                world_move_vec = self.render.getRelativeVector(camera_pivot, move_vec)
                world_move_vec.z = 0
                world_move_vec.normalize()

                self.player_actor.setPos(self.player_actor.getPos() + world_move_vec * move_speed * dt)
                self.player_actor.lookAt(self.player_actor.getPos() + world_move_vec)

                pos = self.player_actor.getPos()
                rot = self.player_actor.getHpr()
                self.asyncio_loop.create_task(
                    send_message(self.writer, {"type": "move", "pos": [pos.x, pos.y, pos.z], "rot": [rot.x, rot.y, rot.z]}))
        else:
            if self.player_actor.getCurrentAnim() != "idle":
                self.player_actor.loop("idle")

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
        anims = {"walk": "nine/assets/models/player.egg", "idle": "nine/assets/models/player.egg"}
        actor = Actor("nine/assets/models/player.egg", anims)
        actor.set_scale(0.3)
        actor.setColor(color)
        actor.reparentTo(self.render)

        if is_local_player:
            self.player_actor = actor
        else:
            self.other_players[player_id] = actor
        return actor

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
                actor = self.other_players.pop(p_id)
                actor.cleanup()
                actor.removeNode()

        elif msg_type == "world_state":
            for p_id_str, p_info in data.get("players", {}).items():
                p_id = int(p_id_str)
                actor_to_update = self.player_actor if p_id == self.player_id else self.other_players.get(p_id)
                if not actor_to_update:
                    actor_to_update = self.load_actor(p_id, LColor(0.8, 0.8, 0.8, 1))

                # Server-authoritative clients should not do client-side prediction,
                # so we only apply server state if we are not in dev mode.
                # In dev mode, we only update other players.
                if not self.dev_mode or (self.dev_mode and p_id != self.player_id):
                    actor_to_update.setPos(*p_info["pos"])

                actor_to_update.setHpr(*p_info["rot"])
                anim_state = p_info.get("anim_state", "idle")
                if actor_to_update.getCurrentAnim() != anim_state:
                    actor_to_update.loop(anim_state)
        else:
            self.event_manager.post(msg_type, data)

    def cleanup_game_state(self):
        self.logger.info("Connection closed. Cleaning up game state.")
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
        self.asyncio_loop.call_soon_threadsafe(self.cleanup_.game_state)

    async def poll_asyncio(self, task):
        self.asyncio_loop.stop()
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
            reader, self.writer = await asyncio.open_connection(host, port, ssl=ssl_context)
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
        return False  # Simplified

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
    def close_login_menu(self): self.ui.hide_login_.menu(); self.ui.show_main_menu()
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