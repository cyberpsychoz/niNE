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
from panda3d.core import (CardMaker, LColor, WindowProperties, loadPrcFileData, Vec3, NodePath)

# Client does not need its own character controller anymore
# from nine.core.character_controller import CharacterController
from nine.core.camera_controller import CameraController
from nine.core.events import EventManager
from nine.core.plugins import PluginManager
from nine.ui.manager import UIManager

loadPrcFileData("", "audio-library-name null")


HOST = "localhost"
PORT = 9009


class GameClient(ShowBase):
    def __init__(self):
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
        try:
            with open("config.json") as f:
                config = json.load(f)
            self.camera_sensitivity = config.get("camera_sensitivity", 1.0)
        except (FileNotFoundError, json.JSONDecodeError):
            self.camera_sensitivity = 1.0

        self.player_id = -1
        self.is_connected = False
        self.is_server = False  # Plugins check this
        self.character_name = "Player"
        self.client_uuid = self._get_or_create_uuid()

        self.player_actor = None  # This is the player's own actor
        self.other_players = {}  # Maps player_id -> Actor

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
        self.ui.show_main_menu()
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

        # --- Panda3D Tasks ---
        self.taskMgr.add(self.poll_asyncio, "asyncio-poll")
        self.input_task = None

    def _get_or_create_uuid(self) -> str:
        # (Unchanged from original)
        uuid_file = Path(".client_uuid")
        if uuid_file.exists():
            try:
                client_uuid = uuid_file.read_text().strip()
                return str(uuid.UUID(client_uuid)) # Validate UUID
            except (ValueError, IndexError):
                pass
        client_uuid = str(uuid.uuid4())
        uuid_file.write_text(client_uuid)
        return client_uuid

    def setup_visual_scene(self):
        """Sets up a simple visual ground. Physics is handled by the server."""
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
            self.input_task = self.taskMgr.add(self.send_input_task, "send-input-task")

    def send_input_task(self, task):
        """Periodically sends the current input state to the server."""
        if self.is_connected:
            # Future improvement: send only on change
            input_message = {"type": "input", "state": self.keyMap}
            self.asyncio_loop.create_task(self.send_message(self.writer, input_message))
        return Task.cont

    def attempt_login(self):
        credentials = self.ui.get_login_credentials()
        if not credentials["ip"] or not credentials["name"]:
            self.logger.warning("IP and Name fields must be filled.")
            return
        self.character_name = credentials["name"]
        self.ui.hide_login_menu()
        self.asyncio_loop.create_task(self.connect_and_read(credentials["ip"]))

    def on_successful_connection(self):
        """Send authentication request to the server."""
        auth_data = {"type": "auth", "name": self.character_name}
        self.asyncio_loop.create_task(self.send_message(self.writer, auth_data))

    def load_actor(self, player_id, color, is_local_player=False):
        """Loads a visual actor for a player."""
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
            self.ui.hide_main_menu()
            self.player_id = data["id"]
            
            # Create the local player actor and camera
            self.load_actor(self.player_id, LColor(0.5, 0.8, 0.5, 1), is_local_player=True)
            self.player_actor.setPos(*data["pos"])
            self.camera_controller = CameraController(self, self.camera, self.win, self.player_actor, self.camera_sensitivity)
            self.enable_game_input()
            
            # Create actors for players already on the server
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
                actor = None
                if p_id == self.player_id:
                    actor = self.player_actor
                elif p_id in self.other_players:
                    actor = self.other_players[p_id]
                else:
                    # Player is new to us, create them
                    actor = self.load_actor(p_id, LColor(0.8, 0.8, 0.8, 1))

                if actor:
                    # Smooth movement can be added here later (e.g., lerp)
                    actor.setPos(*p_info["pos"])
                    actor.setHpr(*p_info["rot"])
                    anim_state = p_info.get("anim_state", "idle")
                    if actor.getCurrentAnim() != anim_state:
                        actor.loop(anim_state)
        else:
            # Pass other messages to plugins
            self.event_manager.post(msg_type, data)

    def cleanup_game_state(self):
        """Resets the client to its initial state, ready for a new connection."""
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
        self.ui.show_main_menu()

    # --- Boilerplate networking, UI, and app lifecycle methods (mostly unchanged) ---

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
            self.logger.critical("CRITICAL ERROR: 'certs/cert.pem' not found.")
            self.close_login_menu()
            return
            
        try:
            reader, self.writer = await asyncio.open_connection(host, PORT, ssl=ssl_context)
            self.is_connected = True
            self.logger.info("Connection to server successful.")
            self.on_successful_connection()
            await self.read_messages(reader)
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
        finally:
            self.is_connected = False
            if self.writer: self.writer.close()
            self.asyncio_loop.call_soon_threadsafe(self.cleanup_game_state)

    async def read_messages(self, reader: asyncio.StreamReader):
        while self.is_connected:
            try:
                header = await reader.readexactly(4)
                msg_len = struct.unpack("!I", header)[0]
                payload = await reader.readexactly(msg_len)
                data = json.loads(payload.decode("utf-8"))
                self.asyncio_loop.call_soon_threadsafe(self.handle_network_data, data)
            except (asyncio.IncompleteReadError, ConnectionResetError, struct.error):
                self.logger.warning("Lost connection to the server.")
                self.is_connected = False
            except Exception as e:
                self.logger.error(f"Error reading message: {e}")
                self.is_connected = False

    def exit_game(self):
        self.plugin_manager.unload_plugins()
        if self.writer: self.writer.close()
        self.userExit()

    def is_chat_active(self) -> bool:
        """A fallback method in case the chat plugin is not loaded."""
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
            self.asyncio_loop.create_task(self.send_message(self.writer, {"type": "chat_message", "message": message}))

    def open_login_menu(self): self.ui.show_login_menu(default_ip=HOST, default_name=self.character_name)
    def close_login_menu(self): self.ui.hide_login_menu(); self.ui.show_main_menu()
    def show_settings_menu(self): self.ui.show_settings_menu(self)


if __name__ == "__main__":
    app = GameClient()
    try:
        app.run()
    except (SystemExit, KeyboardInterrupt):
        logging.info("Exiting application.")
    finally:
        if hasattr(app, 'asyncio_loop') and app.asyncio_loop.is_running():
            app.asyncio_loop.stop()