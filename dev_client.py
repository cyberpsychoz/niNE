import argparse
import asyncio
import json
import logging
import ssl
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
loadPrcFileData("", "cursor-hidden 0")
loadPrcFileData("", "mouse-mode absolute")


class DevGameClient(ShowBase):
    def __init__(self, name="DevPlayer", client_uuid=None, host="localhost", port=9009):
        # --- Standard setup (logging, asyncio, ShowBase) ---
        log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # Use a different log file for the dev client
        file_handler = logging.FileHandler("dev_client.log", mode='w')
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
        self.dev_mode = True  # Always in dev mode
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
        self.client_uuid = client_uuid if client_uuid else str(uuid.uuid4())

        self.player_actor = None
        self.other_players = {}

        self.writer = None
        self.in_game_menu_active = False
        self.camera_controller = None

        # --- UI Setup (Minimal) ---
        # No main menu, connect automatically.
        # UIManager is still needed for in-game menus, chat, etc.
        callbacks = {"exit": self.exit_game}
        self.ui = UIManager(self, callbacks)
        self.event_manager.subscribe("client_send_chat_message", self.send_chat_packet)

        # --- Final Initializations ---
        self.plugin_manager.load_plugins()
        self.setup_visual_scene()
        self.logger.info("Dev Client initialized.")

        # --- Input Handling ---
        self.keyMap = {"w": False, "a": False, "s": False, "d": False}
        self.accept("w", self.update_key_map, ["w", True])
        self.accept("w-up", self.update_key_map, ["w", False])
        self.accept("a", self.update_key_map, ["a", True])
        self.accept("a-up", self.update_key_map, ["a", False])
        self.accept("s", self.update_key_map, ["s", True])
        self.accept("s-up", self.update_key_map, ["s", False])
        self.accept("d", self.update_key_map, ["d", True])
        self.accept("d-up", self.update_key_map, ["d", False])
        self.accept("escape", self.handle_escape)

        # --- Panda3D Tasks & Auto-connect ---
        self.taskMgr.add(self.poll_asyncio, "asyncio-poll")
        self.input_task = None

        self.logger.info(f"Dev Client '{self.character_name}' ({self.client_uuid}) launched.")
        self.asyncio_loop.create_task(self.connect_and_read(host, port))

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
            # Dev client uses client-side prediction
            self.input_task = self.taskMgr.add(self.update_movement_task, "update-movement-task")

    def update_movement_task(self, task):
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

    def on_successful_connection(self):
        # Dev client always uses dev_auth
        auth_data = {"type": "dev_auth", "name": self.character_name, "uuid": self.client_uuid}
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
                
                # In dev mode, we only update other players as we are authoritative over our own position
                if p_id != self.player_id:
                    actor_to_update.setPos(*p_info["pos"])

                actor_to_update.setHpr(*p_info["rot"])
                anim_state = p_info.get("anim_state", "idle")
                if actor_to_update.getCurrentAnim() != anim_state:
                    actor_to_update.loop(anim_state)
        else:
            self.event_manager.post(msg_type, data)

    def cleanup_game_state(self):
        self.logger.info("Connection closed. Exiting dev client.")
        self.exit_game()

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
            self.logger.critical("CRITICAL ERROR: 'certs/cert.pem' not found. Exiting.")
            self.exit_game()
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
        # We need to check if these systems were initialized before trying to destroy them
        if hasattr(self, 'plugin_manager'):
            self.plugin_manager.unload_plugins()
        if self.writer:
            self.writer.close()
        # This will stop the asyncio loop and Panda3D
        self.userExit()

    def handle_escape(self):
        # Simplified for dev client: just exit
        self.exit_game()

    def send_chat_packet(self, message: str):
        if message.strip():
            self.asyncio_loop.create_task(send_message(self.writer, {"type": "chat_message", "message": message}))


if __name__ == "__main__":
    if "panda3d" not in sys.modules:
        logging.basicConfig(level=logging.CRITICAL)
        logging.critical("Fatal Error: Panda3D is not installed. Please run 'pip install panda3d'.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="nine development client.")
    parser.add_argument("--name", type=str, default="DevPlayer", help="Player name for the client.")
    parser.add_argument("--uuid", type=str, default=None, help="Optional: specific UUID for the client.")
    parser.add_argument("--host", type=str, default="localhost", help="Server host to connect to.")
    parser.add_argument("--port", type=int, default=9009, help="Server port to connect to.")
    args = parser.parse_args()

    app = DevGameClient(
        name=args.name,
        client_uuid=args.uuid,
        host=args.host,
        port=args.port
    )
    try:
        app.run()
    except (SystemExit, KeyboardInterrupt):
        logging.info("Exiting Dev Client application.")
    finally:
        if hasattr(app, 'asyncio_loop') and app.asyncio_loop.is_running():
            app.asyncio_loop.stop()
