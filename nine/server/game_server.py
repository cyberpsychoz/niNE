import asyncio
import ipaddress
import json
import logging
import os
import ssl
import struct
import subprocess
import time
from collections import deque
from itertools import cycle

from direct.showbase.ShowBase import ShowBase
from panda3d.core import loadPrcFileData, Vec3, ClockObject

# Global clock for delta time
globalClock = ClockObject.getGlobalClock()

from nine.core.world import GameWorld
from nine.core.events import EventManager
from nine.core.plugins import PluginManager
from nine.core.database import DatabaseManager

# Load server-specific PRC file data
loadPrcFileData("", """
    window-type none
    audio-library-name null
    threading-model None
""")

class GameServer(ShowBase):
    def __init__(self):
        super().__init__()

        # Setup logging
        log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler("server.log", mode='w')
        file_handler.setFormatter(log_formatter)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)

        # Load config (create default if not exists)
        config = self._load_or_create_config()

        # Ensure SSL certificates exist
        if not self._ensure_certificates():
            raise SystemExit("SSL certificates required to start server.")

        self.host = config.get("host", "localhost")
        self.port = config.get("port", 9009)
        self.tick_rate = config.get("tick_rate", 30)
        self.allow_dev_client = config.get("allow_dev_client", False)

        # Init asyncio loop
        self.asyncio_loop = asyncio.get_event_loop()

        # Networking state
        self.clients = {}  # map client_id to writer
        self.client_id_counter = 0
        self.message_queue = deque()

        # Setup World (uses Panda3D collision system, no Bullet)
        self.world = GameWorld(self.render)

        # Database for accounts and characters
        self.db = DatabaseManager("nine.db")

        # Event system and plugins
        self.is_server = True  # Plugins check this flag
        self.event_manager = EventManager()
        self.plugin_manager = PluginManager(self, self.event_manager)

        # Subscribe to chat events from plugins
        self.event_manager.subscribe("chat_send_to_clients", self.handle_chat_send)
        # Subscribe to stats events from plugins
        self.event_manager.subscribe("stats_send_to_client", self.handle_stats_send)
        # Subscribe to world config events from plugins
        self.event_manager.subscribe("world_config_send_to_client", self.handle_world_config_send)
        # Subscribe to inventory events from plugins
        self.event_manager.subscribe("inventory_send_to_client", self.handle_inventory_send)
        # Subscribe to system messages
        self.event_manager.subscribe("system_message_to_client", self.handle_system_message)

        # Subscribe to D&D character events
        self.event_manager.subscribe("dnd_send_to_client", self.handle_dnd_send)
        self.event_manager.subscribe("dnd_character_selected", self.handle_character_selected)

        # Load plugins
        self.plugin_manager.load_plugins()

        # Setup game loop
        self.taskMgr.add(self.game_loop, "game_loop")
        self.taskMgr.add(self.poll_asyncio, "asyncio-poll")

        self.logger.info("Game Server initialized.")

    def _load_or_create_config(self) -> dict:
        """Load server config from file, or create default if not exists."""
        config_path = "server_config.json"

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Invalid config file, recreating: {e}")

        # Create default config
        default_config = {
            "host": "localhost",
            "port": 9009,
            "tick_rate": 30,
            "allow_dev_client": False,
            "world": {
                "map": {"model": "nine/assets/models/maps/map.bam"},
                "lighting": {
                    "ambient": {"color": [0.15, 0.1, 0.2, 1.0], "enabled": True},
                    "sun": {"color": [1.2, 0.7, 0.6, 1.0], "direction": [45, -30, 0], "enabled": True},
                    "fill": {"color": [0.2, 0.25, 0.4, 1.0], "direction": [150, -30, 0], "enabled": True},
                    "rim": {"color": [0.4, 0.2, 0.1, 1.0], "direction": [-120, -10, 0], "enabled": False}
                },
                "skybox": {
                    "texture": "nine/assets/materials/textures/sky.png",
                    "radius": 1000,
                    "segments": 64,
                    "rings": 32,
                    "uv_scale": {"v_offset": 0.15, "v_scale": 0.9}
                },
                "fog": {"enabled": False}
            }
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)

        self.logger.info(f"Created default config: {config_path}")
        return default_config

    def _ensure_certificates(self) -> bool:
        """Check for SSL certificates, offer to generate if missing. Returns True if certs exist."""
        cert_path = "certs/cert.pem"
        key_path = "certs/key.pem"

        if os.path.exists(cert_path) and os.path.exists(key_path):
            return True

        print("\n" + "=" * 50)
        print("SSL сертификаты не найдены!")
        print("=" * 50)
        print(f"Ожидаемые пути:")
        print(f"  - {cert_path}")
        print(f"  - {key_path}")
        print()

        while True:
            response = input("Сгенерировать самоподписанные сертификаты для разработки? [Y/n]: ").strip().lower()
            if response in ("", "y", "yes", "д", "да"):
                return self._generate_certificates()
            elif response in ("n", "no", "н", "нет"):
                print("Сервер не может запуститься без SSL сертификатов.")
                return False
            else:
                print("Пожалуйста, введите 'y' или 'n'")

    def _generate_certificates(self) -> bool:
        """Generate self-signed SSL certificates for development using Python."""
        certs_dir = "certs"
        cert_path = os.path.join(certs_dir, "cert.pem")
        key_path = os.path.join(certs_dir, "key.pem")

        # Create certs directory
        os.makedirs(certs_dir, exist_ok=True)

        print("Генерация SSL сертификатов...")

        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.backends import default_backend
            import datetime

            # Generate RSA key
            key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )

            # Generate self-signed certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ])

            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.datetime.utcnow())
                .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
                .add_extension(
                    x509.SubjectAlternativeName([
                        x509.DNSName("localhost"),
                        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    ]),
                    critical=False,
                )
                .sign(key, hashes.SHA256(), default_backend())
            )

            # Write private key
            with open(key_path, "wb") as f:
                f.write(key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            # Write certificate
            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))

            print(f"Сертификаты успешно созданы в папке '{certs_dir}/'")
            self.logger.info("Self-signed certificates generated successfully.")
            return True

        except ImportError:
            print("Ошибка: библиотека 'cryptography' не установлена!")
            print("Установите её командой: pip install cryptography")
            self.logger.error("cryptography library not installed.")
            return False
        except Exception as e:
            print(f"Ошибка при генерации сертификатов: {e}")
            self.logger.error(f"Certificate generation error: {e}")
            return False

    def poll_asyncio(self, task):
        self.asyncio_loop.call_soon(self.asyncio_loop.stop)
        self.asyncio_loop.run_forever()
        return task.cont

    def game_loop(self, task):
        # CRITICAL FIX: Limit tick rate to prevent multiple ticks per millisecond
        if not hasattr(self, '_last_tick_time'):
            self._last_tick_time = globalClock.getRealTime()
            self._tick_id = 0

        # Calculate time since last tick
        current_time = globalClock.getRealTime()
        time_since_last_tick = current_time - self._last_tick_time
        target_tick_interval = 1.0 / self.tick_rate

        # Skip this frame if not enough time has passed
        if time_since_last_tick < target_tick_interval:
            return task.cont

        # Update last tick time
        self._last_tick_time = current_time
        self._tick_id += 1

        # Use fixed dt based on tick_rate for consistent physics
        dt = target_tick_interval

        # 1. Process network messages
        while self.message_queue:
            client_id, data = self.message_queue.popleft()
            self.process_message(client_id, data)

        # 2. Update game world (includes collision traversal)
        if self._tick_id % 10 == 0 or self._tick_id < 20:  # Log first 20 and every 10th
            self.logger.info(f"[GameServer TICK #{self._tick_id}] world.update(dt={dt:.4f})")
        self.world.update(dt)

        # 3. Broadcast new state
        world_state = self.world.get_world_state()
        if world_state["players"]:
            asyncio.run_coroutine_threadsafe(
                self.broadcast(world_state), self.asyncio_loop
            )

        return task.cont
        
    def process_message(self, client_id, data):
        msg_type = data.get("type")

        if msg_type == "auth":
            self.handle_auth(client_id, data)
        elif msg_type == "dev_auth":
            self.handle_dev_auth(client_id, data)
        # D&D Character messages
        elif msg_type == "character_list_request":
            self.event_manager.post("dnd_character_list_request", {"client_id": client_id})
        elif msg_type == "character_select":
            self.event_manager.post("dnd_character_select", {
                "client_id": client_id,
                "character_uuid": data.get("character_uuid")
            })
        elif msg_type == "character_create":
            self.event_manager.post("dnd_character_create", {
                "client_id": client_id,
                **{k: v for k, v in data.items() if k != "type"}
            })
        elif msg_type == "character_delete":
            self.event_manager.post("dnd_character_delete", {
                "client_id": client_id,
                "character_uuid": data.get("character_uuid")
            })
        elif msg_type == "input":
             self.world.handle_input(client_id, data.get("state", {}))
        elif msg_type == "move":  # Dev clients send their own position
            if self.allow_dev_client:
                self.world.handle_move(client_id, data)
        elif msg_type == "chat_message":
            player = self.world.players.get(client_id)
            if player:
                # Send to plugin for processing
                player_pos = player.get_state()["pos"]
                self.event_manager.post("chat_message_received", {
                    "client_id": client_id,
                    "player_name": player.name,
                    "message": data.get("message", ""),
                    "player_pos": player_pos
                })
        elif msg_type == "item_use":
            # Отправляем событие плагину инвентаря
            self.event_manager.post("item_use", {
                "uuid": client_id,
                "slot": data.get("slot", 0),
            })
        elif msg_type == "item_drop":
            # Получаем позицию игрока для спавна предмета
            player = self.world.players.get(client_id)
            position = None
            if player:
                pos = player.get_state()["pos"]
                # Спавним перед игроком
                position = (pos[0], pos[1] + 1, pos[2])

            self.event_manager.post("item_drop", {
                "uuid": client_id,
                "slot": data.get("slot", 0),
                "count": data.get("count", 1),
                "position": position,
            })
        elif data.get("type") == "internal_disconnect":
            self.handle_disconnect(client_id)

    def handle_dev_auth(self, client_id, data):
        if not self.allow_dev_client:
            self.logger.warning(f"Client {client_id} attempted dev_auth, but it is disabled. Disconnecting.")
            writer = self.clients.get(client_id)
            if writer:
                self.asyncio_loop.call_soon_threadsafe(writer.close)
            return
        
        player_name = data.get("name", f"DevPlayer_{client_id}")
        
        # Dev clients can have duplicate names, just log a warning.
        for p in self.world.players.values():
            if p.name == player_name:
                self.logger.warning(f"Player '{player_name}' is already logged in. Allowing duplicate for dev client.")
                break

        player = self.world.add_player(client_id, player_name)
        self.logger.info(f"Dev player '{player_name}' (Client #{client_id}) authenticated.")

        # Notify plugins about player join
        self.event_manager.post("player_joined", {"uuid": client_id, "name": player_name})

        other_players_state = {pid: p.get_state() for pid, p in self.world.players.items() if pid != client_id}
        welcome_data = {
            "type": "welcome",
            "id": client_id,
            "pos": player.get_state()["pos"],
            "players": other_players_state
        }
        asyncio.run_coroutine_threadsafe(self.send_to_client(client_id, welcome_data), self.asyncio_loop)

        join_data = {"type": "player_joined", "id": client_id, "player_info": player.get_state()}
        asyncio.run_coroutine_threadsafe(self.broadcast(join_data, exclude_ids=[client_id]), self.asyncio_loop)

    def handle_auth(self, client_id, data):
        """
        D&D авторизация с проверкой пароля.
        Если аккаунт существует - проверяем пароль.
        Если не существует - создаём новый.
        После успеха отправляем auth_success и ждём character_select.
        """
        import uuid as uuid_module

        account_name = data.get("name", "").strip()
        password = data.get("password", "")

        if not account_name:
            self.logger.warning(f"Client {client_id} sent auth request with no name. Disconnecting.")
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, {"type": "auth_failed", "reason": "No account name provided"}),
                self.asyncio_loop
            )
            return

        if not password:
            self.logger.warning(f"Client {client_id} sent auth request with no password.")
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, {"type": "auth_failed", "reason": "No password provided"}),
                self.asyncio_loop
            )
            return

        # Проверяем существует ли аккаунт
        existing_account = self.db.get_player_by_name(account_name)

        if existing_account:
            # Аккаунт существует - проверяем пароль
            if not self.db.verify_player_password_by_name(account_name, password):
                self.logger.warning(f"Wrong password for account '{account_name}' from client {client_id}")
                asyncio.run_coroutine_threadsafe(
                    self.send_to_client(client_id, {"type": "auth_failed", "reason": "wrong_password"}),
                    self.asyncio_loop
                )
                return

            account_uuid = existing_account["uuid"]
            self.logger.info(f"Account '{account_name}' authenticated (Client #{client_id})")
        else:
            # Аккаунт не существует - создаём новый
            account_uuid = str(uuid_module.uuid4())
            success = self.db.create_player(account_uuid, account_name, password)
            if not success:
                self.logger.error(f"Failed to create account '{account_name}'")
                asyncio.run_coroutine_threadsafe(
                    self.send_to_client(client_id, {"type": "auth_failed", "reason": "Failed to create account"}),
                    self.asyncio_loop
                )
                return

            self.logger.info(f"New account '{account_name}' created (Client #{client_id})")

        # Уведомляем D&D плагин об успешной авторизации
        self.event_manager.post("dnd_auth_success", {
            "client_id": client_id,
            "account_uuid": account_uuid,
            "account_name": account_name
        })

        # Отправляем auth_success клиенту
        asyncio.run_coroutine_threadsafe(
            self.send_to_client(client_id, {
                "type": "auth_success",
                "account_uuid": account_uuid,
                "account_name": account_name
            }),
            self.asyncio_loop
        )

    def handle_chat_send(self, event_data: dict):
        """
        Handles chat_send_to_clients event from chat plugin.
        event_data = {
            "data": broadcast_data,
            "recipients": list of client_ids or None for all
        }
        """
        broadcast_data = event_data.get("data", {})
        recipients = event_data.get("recipients")

        if recipients is None:
            # Send to all clients
            asyncio.run_coroutine_threadsafe(
                self.broadcast(broadcast_data), self.asyncio_loop
            )
        else:
            # Send only to specific clients
            asyncio.run_coroutine_threadsafe(
                self.send_to_clients(broadcast_data, recipients), self.asyncio_loop
            )

    def handle_stats_send(self, event_data: dict):
        """
        Handles stats_send_to_client event from stats plugin.
        event_data = {
            "client_id": client_id,
            "data": stats_data
        }
        """
        client_id = event_data.get("client_id")
        stats_data = event_data.get("data", {})

        if client_id is not None:
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, stats_data), self.asyncio_loop
            )

    def handle_world_config_send(self, event_data: dict):
        """
        Handles world_config_send_to_client event from world_config plugin.
        event_data = {
            "client_id": client_id,
            "data": world_config_data
        }
        """
        client_id = event_data.get("client_id")
        config_data = event_data.get("data", {})

        if client_id is not None:
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, config_data), self.asyncio_loop
            )

    def handle_inventory_send(self, event_data: dict):
        """
        Handles inventory_send_to_client event from inventory plugin.
        event_data = {
            "client_id": client_id,
            "data": inventory_data
        }
        """
        client_id = event_data.get("client_id")
        inventory_data = event_data.get("data", {})

        if client_id is not None:
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, inventory_data), self.asyncio_loop
            )

    def handle_system_message(self, event_data: dict):
        """
        Отправляет системное сообщение клиенту через чат.
        event_data = {
            "client_id": client_id,
            "message": str
        }
        """
        client_id = event_data.get("client_id")
        message = event_data.get("message", "")

        if client_id is not None and message:
            chat_data = {
                "type": "chat_broadcast",
                "chat_type": "system",
                "from_name": "Система",
                "message": message,
            }
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, chat_data), self.asyncio_loop
            )

    def handle_dnd_send(self, event_data: dict):
        """
        Отправляет D&D сообщение конкретному клиенту.
        event_data = {
            "client_id": client_id,
            "data": message_data
        }
        """
        client_id = event_data.get("client_id")
        message_data = event_data.get("data", {})

        if client_id is not None:
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, message_data), self.asyncio_loop
            )

    def handle_character_selected(self, event_data: dict):
        """
        Обработчик выбора персонажа - создаёт игрока в мире.
        event_data = {
            "client_id": client_id,
            "character": character_data dict
        }
        """
        client_id = event_data.get("client_id")
        character = event_data.get("character", {})

        if client_id is None or not character:
            return

        character_name = character.get("character_name", f"Player_{client_id}")
        character_uuid = character.get("uuid")

        # Проверяем что имя не занято другим игроком
        for pid, p in self.world.players.items():
            if p.name == character_name and pid != client_id:
                self.logger.warning(f"Character name '{character_name}' already in use by another player")
                asyncio.run_coroutine_threadsafe(
                    self.send_to_client(client_id, {
                        "type": "error",
                        "message": "Character already in use by another player"
                    }),
                    self.asyncio_loop
                )
                return

        # Получаем позицию персонажа из БД или используем стартовую
        pos_x = character.get("pos_x", 8.0)
        pos_y = character.get("pos_y", -3.0)
        pos_z = character.get("pos_z", 1.0)

        # Создаём игрока в мире
        player = self.world.add_player(client_id, character_name)
        if player:
            # Устанавливаем позицию из сохранения
            player.set_position(Vec3(pos_x, pos_y, pos_z))

        self.logger.info(f"Character '{character_name}' (Client #{client_id}) entered the game world")

        # Уведомляем плагины о входе игрока
        self.event_manager.post("player_joined", {
            "uuid": client_id,
            "name": character_name,
            "character_uuid": character_uuid,
            "character_data": character
        })

        # Отправляем welcome сообщение с данными персонажа
        other_players_state = {
            pid: p.get_state()
            for pid, p in self.world.players.items()
            if pid != client_id
        }

        welcome_data = {
            "type": "welcome",
            "id": client_id,
            "pos": [pos_x, pos_y, pos_z],
            "players": other_players_state,
            "character_data": character
        }
        asyncio.run_coroutine_threadsafe(
            self.send_to_client(client_id, welcome_data), self.asyncio_loop
        )

        # Уведомляем других игроков о входе
        join_data = {
            "type": "player_joined",
            "id": client_id,
            "player_info": player.get_state() if player else {"name": character_name}
        }
        asyncio.run_coroutine_threadsafe(
            self.broadcast(join_data, exclude_ids=[client_id]), self.asyncio_loop
        )

    async def send_to_clients(self, data, client_ids):
        """Sends a message to specific clients."""
        payload = json.dumps(data).encode("utf-8")
        header = struct.pack("!I", len(payload))

        for client_id in client_ids:
            writer = self.clients.get(client_id)
            if writer and not writer.is_closing():
                try:
                    writer.write(header + payload)
                    await writer.drain()
                except Exception as e:
                    self.logger.error(f"Error sending to client {client_id}: {e}")

    def handle_disconnect(self, client_id):
        self.logger.info(f"Client #{client_id} processing disconnection.")
        if client_id in self.clients:
            del self.clients[client_id]

        # Notify plugins about player leave before removing
        self.event_manager.post("player_left", {"uuid": client_id})

        player_id = self.world.remove_player(client_id)
        if player_id is not None:
            leave_data = {"type": "player_left", "id": player_id}
            asyncio.run_coroutine_threadsafe(self.broadcast(leave_data), self.asyncio_loop)

    async def handle_connection(self, reader, writer):
        self.client_id_counter += 1
        client_id = self.client_id_counter
        self.clients[client_id] = writer
        addr = writer.get_extra_info('peername')
        self.logger.info(f"Client #{client_id} connected from {addr}.")
        
        try:
            while True:
                header = await reader.readexactly(4)
                msg_len = struct.unpack("!I", header)[0]
                payload = await reader.readexactly(msg_len)
                data = json.loads(payload.decode("utf-8"))
                # Add to a queue to be processed in the main thread
                self.message_queue.append((client_id, data))
        except (asyncio.IncompleteReadError, ConnectionResetError, struct.error):
            # Pass to main thread to handle cleanup
            self.message_queue.append((client_id, {"type": "internal_disconnect"}))
        finally:
            # Final cleanup in case the connection is force-closed
             if client_id in self.clients:
                self.message_queue.append((client_id, {"type": "internal_disconnect"}))

    async def broadcast(self, data, exclude_ids=None):
        if exclude_ids is None:
            exclude_ids = []
        
        payload = json.dumps(data).encode("utf-8")
        header = struct.pack("!I", len(payload))
        
        for client_id, writer in self.clients.items():
            if client_id not in exclude_ids:
                if writer.is_closing():
                    continue
                try:
                    writer.write(header + payload)
                    await writer.drain()
                except Exception as e:
                    self.logger.error(f"Error broadcasting to client {client_id}: {e}")

    async def send_to_client(self, client_id, data):
        writer = self.clients.get(client_id)
        if writer and not writer.is_closing():
            payload = json.dumps(data).encode("utf-8")
            header = struct.pack("!I", len(payload))
            try:
                writer.write(header + payload)
                await writer.drain()
            except Exception as e:
                self.logger.error(f"Error sending to client {client_id}: {e}")

    async def start_server_async(self):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        try:
            ssl_context.load_cert_chain('certs/cert.pem', 'certs/key.pem')
            self.logger.info("SSL context loaded.")
        except FileNotFoundError:
            self.logger.critical("Certificate files not found! Server will not start.")
            self.userExit()
            return
            
        server = await asyncio.start_server(
            self.handle_connection, self.host, self.port, ssl=ssl_context
        )
        
        addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
        self.logger.info(f'Serving on {addrs}')

        # This will run until the server is closed
        await server.serve_forever()

    def run(self):
        # Start the asyncio server coroutine
        self.asyncio_loop.create_task(self.start_server_async())
        # This will start Panda3D's internal loop
        super().run()
        self.logger.info("Server has shut down.")