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
from panda3d.core import (CardMaker, LColor, LVector3, NodePath,
                          WindowProperties, loadPrcFileData, Vec3)

from nine.core.camera_controller import CameraController
from nine.core.events import EventManager
from nine.core.plugins import PluginManager
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
        self.accept("w", self.update_key_map, ["w", True])
        self.accept("w-up", self.update_key_map, ["w", False])
        self.accept("a", self.update_key_map, ["a", True])
        self.accept("a-up", self.update_key_map, ["a", False])
        self.accept("s", self.update_key_map, ["s", True])
        self.accept("s-up", self.update_key_map, ["s", False])
        self.accept("d", self.update_key_map, ["d", True])
        self.accept("d-up", self.update_key_map, ["d", False])
        self.accept("escape", self.handle_escape)

        self.taskMgr.add(self.poll_asyncio, "asyncio-poll")
        self.game_update_task = None

    def _get_or_create_uuid(self) -> str:
        uuid_file = Path(".client_uuid")
        if uuid_file.exists():
            try:
                client_uuid = uuid_file.read_text().strip()
                return str(client_uuid)
            except (ValueError, IndexError):
                pass
        client_uuid = str(uuid.uuid4())
        uuid_file.write_text(client_uuid)
        return client_uuid

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
        return False

    def disable_game_input(self):
        if self.camera_controller:
            self.camera_controller.stop()

        for key in self.keyMap:
            self.keyMap[key] = False
        if self.game_update_task:
            self.taskMgr.remove(self.game_update_task)
            self.game_update_task = None

    def enable_game_input(self):
        if self.camera_controller:
            self.camera_controller.start()
            
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

        if self.in_game_menu_active:
            self.ui.hide_in_game_menu()
            self.in_game_menu_active = False
            self.enable_game_input()
        else:
            self.ui.show_in_game_menu(self)
            self.in_game_menu_active = True
            self.disable_game_input()
            
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


if __name__ == "__main__":
    if "panda3d" not in sys.modules:
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
