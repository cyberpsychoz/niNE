import asyncio
import logging
import json
import ssl
import struct
import sys
import uuid
import argparse # Added for command line argument parsing
from pathlib import Path

from panda3d.core import loadPrcFileData

loadPrcFileData("", "audio-library-name null")

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import CardMaker, NodePath, LColor

from nine.core.events import EventManager
from nine.core.plugins import PluginManager
from nine.ui.manager import UIManager


class GameClient(ShowBase):
    def __init__(self, name: str, client_uuid: str): # Added name and client_uuid as arguments
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
        
        self.event_manager = EventManager()
        self.plugin_manager = PluginManager(self, self.event_manager)

        # Load server config
        with open("server_config.json") as f:
            config = json.load(f)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 9009)

        self.player_id = -1
        self.is_connected = False
        self.character_name = name # Use name from argument
        self.client_uuid = client_uuid # Use uuid from argument
        self.player_model = None
        self.other_players = {}
        self.writer = None
        self.temp_password = None
        self.in_game_menu_active = False # New attribute to track in-game menu state

        callbacks = {
            "connect": self.open_login_menu,
            "exit": self.exit_game,
            "attempt_login": self.attempt_login,
            "close_login_menu": self.close_login_menu,
            "settings": self.show_settings_menu, # ADDED THIS LINE
        }
        self.ui = UIManager(self, callbacks)
        
        self.event_manager.subscribe("client_send_chat_message", self.send_chat_packet)
        self.plugin_manager.load_plugins()

        # Connect directly without showing main menu
        self.setup_scene()
        self.logger.info(f"Dev Client {self.character_name} ({self.client_uuid}) launched. Connecting to {self.host}:{self.port}")
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
        self.update_movement_task = self.taskMgr.add(self.update_movement, "update-movement-task")

    def _get_or_create_uuid(self) -> str:
        # For dev clients, always generate a new UUID or use the one provided by argument
        return str(uuid.uuid4())

    def setup_scene(self):
        self.disableMouse()
        cm = CardMaker("ground")
        cm.setFrame(-50, 50, -50, 50)
        ground = self.render.attachNewNode(cm.generate())
        ground.setP(-90)
        ground.setPos(0, 0, -1)

    def update_key_map(self, key, state):
        self.keyMap[key] = state

    def is_chat_active(self) -> bool:
        """Helper method to find the chat plugin and check its status."""
        for plugin in self.plugin_manager.plugins:
            if plugin.name == "Chat UI" and hasattr(plugin, 'is_active'):
                return plugin.is_active()
        return False

    def disable_game_input(self):
        """Disables game-related input and tasks when a menu is active."""
        for key in self.keyMap:
            self.keyMap[key] = False # Clear any held keys
        if self.update_movement_task:
            self.taskMgr.remove(self.update_movement_task)
            self.update_movement_task = None

    def enable_game_input(self):
        """Enables game-related input and tasks when a menu is closed."""
        if not self.update_movement_task:
            self.update_movement_task = self.taskMgr.add(self.update_movement, "update-movement-task")

    def update_movement(self, task):
        if not self.is_connected or not self.player_model or self.is_chat_active() or self.in_game_menu_active:
            return Task.cont

        dt = globalClock.getDt()
        move_speed = 10.0
        pos = self.player_model.getPos()
        moved = False

        if self.keyMap["w"]: pos.y += move_speed * dt; moved = True
        if self.keyMap["s"]: pos.y -= move_speed * dt; moved = True
        if self.keyMap["a"]: pos.x -= move_speed * dt; moved = True
        if self.keyMap["d"]: pos.x += move_speed * dt; moved = True

        if moved:
            self.player_model.setPos(pos)
            self.asyncio_loop.create_task(
                self.send_message(self.writer, {"type": "move", "pos": [pos.x, pos.y, pos.z]})
            )
        return Task.cont

    def open_login_menu(self):
        # Not used in dev client, connect directly
        pass 

    def close_login_menu(self):
        # Not used in dev client
        pass

    def show_settings_menu(self):
        """Displays the settings menu."""
        self.ui.show_settings_menu(self) # Assuming show_settings_menu takes client instance

    def attempt_login(self):
        # Not used in dev client, connect directly
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
                self.enable_game_input() # Re-enable game input/tasks
            else:
                self.ui.show_in_game_menu(self) # Pass self (GameClient instance) for disconnect
                self.in_game_menu_active = True
                self.disable_game_input() # Disable game input/tasks
            
    def send_chat_packet(self, message: str):
        if not message.strip():
            return
        message_data = {"type": "chat_message", "message": message}
        self.asyncio_loop.create_task(self.send_message(self.writer, message_data))


    def on_successful_connection(self):
        auth_data = {
            "type": "dev_auth", # Changed from "auth"
            "name": self.character_name,
            "uuid": self.client_uuid, 
            # No password needed for dev_auth
        }
        self.temp_password = None
        self.asyncio_loop.create_task(self.send_message(self.writer, auth_data))

    def load_player_model(self, is_local_player=False) -> NodePath:
        model = self.loader.loadModel("nine/assets/models/player.egg")
        if not model:
            cm = CardMaker("fallback-player")
            cm.setFrame(-0.5, 0.5, -0.5, 0.5)
            model = NodePath(cm.generate())
            model.setZ(0.5)
        
        model.setColor(LColor(0.5, 0.8, 0.5, 1) if is_local_player else LColor(0.8, 0.8, 0.8, 1))
        model.set_scale(0.3)
        
        if is_local_player:
            self.camera.reparentTo(model)
            self.camera.setPos(0, -20, 8)
            self.camera.lookAt(model)
            
        model.reparentTo(self.render)
        return model

    def handle_network_data(self, data: dict):
        msg_type = data.get("type")

        if msg_type == "welcome":
            # self.ui.hide_main_menu() # No main menu to hide for dev client
            self.player_id = data["id"]
            self.player_model = self.load_player_model(is_local_player=True)
            self.player_model.setPos(*data["pos"])
            for p_id_str, p_info in data.get("players", {}).items():
                p_id = int(p_id_str)
                if p_id != self.player_id:
                    p_node = self.load_player_model()
                    p_node.setPos(*p_info["pos"])
                    self.other_players[p_id] = p_node

        elif msg_type == "auth_failed":
            self.logger.error(f"Ошибка аутентификации: {data.get('reason', 'Неизвестная ошибка')}")
            self.is_connected = False
            # self.ui.show_main_menu() # No main menu for dev client
            # self.ui.hide_login_menu() # No login menu for dev client
            self.exit_game() # Exit if dev auth fails

        elif msg_type == "chat_broadcast":
            self.event_manager.post("network_chat_broadcast", {
                "sender": data.get("from_name", "Unknown"), 
                "message": data.get("message", "")
            })

        elif msg_type == "player_joined":
            p_id = data["id"]
            if p_id != self.player_id:
                p_info = data["player_info"]
                p_node = self.load_player_model()
                p_node.setPos(*p_info["pos"])
                self.other_players[p_id] = p_node

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
            # self.close_login_menu() # No login menu for dev client
            self.exit_game() # Exit if cert not found
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
            self.exit_game() # Exit on connection error
        finally:
            self.is_connected = False
            if self.writer:
                self.writer.close()
                if not self.asyncio_loop.is_closed():
                    try:
                        pass # Removed await self.writer.wait_closed()
                    except (AttributeError, TypeError, ValueError):
                        pass

            if reader:
                reader.feed_eof()
            self.asyncio_loop.call_soon_threadsafe(self.cleanup_game_state)

    def disconnect_from_server(self):
        """Initiates disconnection from the server."""
        if self.is_connected:
            self.logger.info("Отключение от сервера и очистка состояния игры.")
            self.is_connected = False
            if self.writer:
                self.writer.close()
            # The cleanup_game_state will be called via the finally block in connect_and_read
            # and lead back to the main menu.
            if self.in_game_menu_active:
                self.ui.hide_in_game_menu()
                self.in_game_menu_active = False
                self.enable_game_input()

    def cleanup_game_state(self):
        """Очищает состояние игры после отключения."""
        self.logger.info("Соединение с сервером закрыто.")
        if self.player_model:
            self.player_model.removeNode()
            self.player_model = None
        for p in self.other_players.values():
            p.removeNode()
        self.other_players.clear()
        self.player_id = -1
        self.ui.destroy_all()
        # self.ui.show_main_menu() # No main menu for dev client
        self.exit_game() # Exit after cleanup

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
    
    # Generate UUID if not provided
    client_uuid = args.uuid if args.uuid else str(uuid.uuid4())
    app = GameClient(args.name, client_uuid)
    try:
        app.run()
    except SystemExit:
        logging.info("Выход из приложения.")
    finally:
        if hasattr(app, 'asyncio_loop') and app.asyncio_loop.is_running():
            app.asyncio_loop.stop()