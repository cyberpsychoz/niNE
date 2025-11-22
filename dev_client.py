import asyncio
import logging
import json
import ssl
import struct
import sys
import uuid
import argparse
from pathlib import Path

from panda3d.core import loadPrcFileData, WindowProperties, LVector3, LPoint3

loadPrcFileData("", "audio-library-name null")
loadPrcFileData("", "cursor-hidden 0")
loadPrcFileData("", "mouse-mode absolute")

from direct.actor.Actor import Actor
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import CardMaker, NodePath, LColor

from nine.core.camera_controller import CameraController
from nine.core.events import EventManager
from nine.core.plugins import PluginManager
from nine.ui.manager import UIManager


class GameClient(ShowBase):
    def __init__(self, name: str, client_uuid: str):
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

        with open("server_config.json") as f:
            config = json.load(f)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 9009)

        self.player_id = -1
        self.is_connected = False
        self.character_name = name
        self.client_uuid = client_uuid
        self.player_actor = None
        self.camera_controller = None
        self.other_players = {}
        self.writer = None
        self.temp_password = None
        self.in_game_menu_active = False

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

        self.setup_scene()
        self.logger.info(
            f"Dev Client {self.character_name} ({self.client_uuid}) launched. Connecting to {self.host}:{self.port}")
        self.asyncio_loop.create_task(self.connect_and_read(self.host))

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
        self.update_movement_task = None

    def _get_or_create_uuid(self) -> str:
        return str(uuid.uuid4())

    def setup_scene(self):
        cm = CardMaker("ground")
        cm.setFrame(-50, 50, -50, 50)
        ground = self.render.attachNewNode(cm.generate())
        ground.setP(-90)
        ground.setPos(0, 0, -1)

    def setup_mouse_control(self, active):
        if self.camera_controller:
            if active:
                self.camera_controller.start()
            else:
                self.camera_controller.stop()

    def update_key_map(self, key, state):
        self.keyMap[key] = state

    def is_chat_active(self) -> bool:
        for plugin in self.plugin_manager.plugins:
            if plugin.name == "Chat UI" and hasattr(plugin, 'is_active'):
                return plugin.is_active()
        return False

    def disable_game_input(self):
        self.setup_mouse_control(False)
        for key in self.keyMap:
            self.keyMap[key] = False
        if self.update_movement_task:
            self.taskMgr.remove(self.update_movement_task)
            self.update_movement_task = None

    def enable_game_input(self):
        self.setup_mouse_control(True)
        if not self.update_movement_task:
            self.update_movement_task = self.taskMgr.add(self.update_movement, "update-movement-task")

    def update_movement(self, task):
        if not self.is_connected or not self.player_actor or not self.camera_controller or self.is_chat_active() or self.in_game_menu_active:
            return Task.cont

        dt = globalClock.getDt()
        move_speed = 10.0

        move_vec = LVector3(0, 0, 0)
        if self.keyMap["w"]: move_vec.y += 1
        if self.keyMap["s"]: move_vec.y -= 1
        if self.keyMap["a"]: move_vec.x -= 1
        if self.keyMap["d"]: move_vec.x += 1

        moved = move_vec.length_squared() > 0
        if moved:
            if self.player_actor.getCurrentAnim() != "walk":
                self.player_actor.loop("walk")

            move_vec.normalize()

            camera_pivot = self.camera_controller.get_camera_pivot()
            world_move_vec = self.render.getRelativeVector(camera_pivot, move_vec)
            world_move_vec.z = 0
            world_move_vec.normalize()

            self.player_actor.setPos(self.player_actor.getPos() + world_move_vec * move_speed * dt)
            self.player_actor.lookAt(self.player_actor.getPos() + world_move_vec)

            pos = self.player_actor.getPos()
            rot = self.player_actor.getHpr()
            self.asyncio_loop.create_task(
                self.send_message(self.writer, {"type": "move", "pos": [pos.x, pos.y, pos.z], "rot": [rot.x, rot.y, rot.z]})
            )
        else:
            if self.player_actor.getCurrentAnim() != "idle":
                self.player_actor.loop("idle")

        return Task.cont

    def open_login_menu(self):
        pass

    def close_login_menu(self):
        pass

    def show_settings_menu(self):
        self.ui.show_settings_menu(self)

    def attempt_login(self):
        pass

    def exit_game(self):
        self.plugin_manager.unload_plugins()
        if self.writer:
            self.writer.close()
        self.userExit()

    def handle_escape(self):
        if self.is_chat_active():
            self.event_manager.post("escape_key_pressed")
        else:
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
            "type": "dev_auth",
            "name": self.character_name,
            "uuid": self.client_uuid,
        }
        self.temp_password = None
        self.asyncio_loop.create_task(self.send_message(self.writer, auth_data))

    def load_actor(self, is_local_player=False) -> NodePath:
        anims = {
            "walk": "nine/assets/models/player.egg",
            "idle": "nine/assets/models/player.egg"
        }
        actor = Actor("nine/assets/models/player.egg", anims)

        if not actor or actor.isEmpty():
            cm = CardMaker("fallback-player")
            cm.setFrame(-0.5, 0.5, -0.5, 0.5)
            actor = NodePath(cm.generate())
            actor.setZ(0.5)

        actor.setColor(LColor(0.5, 0.8, 0.5, 1) if is_local_player else LColor(0.8, 0.8, 0.8, 1))
        actor.set_scale(0.3)
        actor.reparentTo(self.render)
        return actor

    def handle_network_data(self, data: dict):
        msg_type = data.get("type")

        if msg_type == "welcome":
            self.player_id = data["id"]
            self.player_actor = self.load_actor(is_local_player=True)
            self.player_actor.setPos(*data["pos"])

            self.camera_controller = CameraController(self, self.camera, self.win, self.player_actor, self.camera_sensitivity)
            self.enable_game_input()

            for p_id_str, p_info in data.get("players", {}).items():
                p_id = int(p_id_str)
                if p_id != self.player_id:
                    p_node = self.load_actor()
                    p_node.setPos(*p_info["pos"])
                    self.other_players[p_id] = p_node

        elif msg_type == "auth_failed":
            self.logger.error(f"Ошибка аутентификации: {data.get('reason', 'Неизвестная ошибка')}")
            self.is_connected = False
            self.disable_game_input()
            self.exit_game()

        elif msg_type == "chat_broadcast":
            self.event_manager.post("network_chat_broadcast", {
                "sender": data.get("from_name", "Unknown"),
                "message": data.get("message", "")
            })

        elif msg_type == "player_joined":
            p_id = data["id"]
            if p_id != self.player_id:
                p_info = data["player_info"]
                p_node = self.load_actor()
                p_node.setPos(*p_info["pos"])
                self.other_players[p_id] = p_node

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

        elif msg_type == "player_left":
            p_id = data["id"]
            if p_id in self.other_players:
                self.other_players[p_id].removeNode()
                del self.other_players[p_id]

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
            self.logger.critical("КРИТИЧЕСКАЯ ОШИБКА: Файл сертификата 'certs/cert.pem' не найден.")
            self.exit_game()
            return

        reader = None
        try:
            reader, self.writer = await asyncio.open_connection(
                host, self.port, ssl=ssl_context, server_hostname=host if host != "localhost" else None
            )
            self.is_connected = True
            self.logger.info("Успешно установлено TLS-соединение с сервером.")
            self.on_successful_connection()
            await self.read_messages(reader)
        except Exception as e:
            self.logger.error(f"Ошибка подключения: {e}")
            self.exit_game()
        finally:
            self.is_connected = False
            if self.writer:
                self.writer.close()
            if reader:
                reader.feed_eof()
            self.asyncio_loop.call_soon_threadsafe(self.cleanup_game_state)

    def disconnect_from_server(self):
        if self.is_connected:
            self.logger.info("Отключение от сервера и очистка состояния игры.")
            self.is_connected = False
            if self.writer:
                self.writer.close()
            if self.in_game_menu_active:
                self.ui.hide_in_game_menu()
                self.in_game_menu_active = False
                self.enable_game_input()

    def cleanup_game_state(self):
        self.logger.info("Соединение с сервером закрыто.")
        self.disable_game_input()
        if self.player_actor:
            self.player_actor.cleanup()
            self.player_actor.removeNode()
            self.player_actor = None
        if self.camera_controller:
            self.camera_controller.stop()
            self.camera_controller = None
        for p in self.other_players.values():
            p.cleanup()
            p.removeNode()
        self.other_players.clear()
        self.player_id = -1
        self.ui.destroy_all()
        self.exit_game()

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
                self.logger.warning("Потеряно соединение с сервером.")
                self.is_connected = False
            except Exception as e:
                self.logger.error(f"Ошибка при чтении сообщения: {e}")
                self.is_connected = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Development client for the game.")
    parser.add_argument("--name", type=str, default="DevPlayer", help="Player name for the dev client.")
    parser.add_argument("--uuid", type=str, default=None, help="Optional: specific UUID for the dev client.")
    args = parser.parse_args()

    if "panda3d" not in sys.modules:
        try:
            import panda3d
        except ImportError:
            logging.basicConfig(level=logging.CRITICAL)
            logging.critical("Ошибка: Panda3D не установлен. Пожалуйста, установите его: pip install panda3d")
            sys.exit(1)

    client_uuid = args.uuid if args.uuid else str(uuid.uuid4())
    app = GameClient(args.name, client_uuid)
    try:
        app.run()
    except SystemExit:
        logging.info("Выход из приложения.")
    finally:
        if hasattr(app, 'asyncio_loop') and app.asyncio_loop.is_running():
            app.asyncio_loop.stop()