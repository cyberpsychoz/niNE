import asyncio
import json
import logging
import ssl
import struct
import time
from collections import deque
from itertools import cycle

from direct.showbase.ShowBase import ShowBase
from panda3d.core import loadPrcFileData, Vec3
from panda3d.bullet import BulletWorld

from nine.core.world import GameWorld

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

        # Load config
        with open("server_config.json") as f:
            config = json.load(f)

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

        # Setup Physics and World
        self.physics_world = BulletWorld()
        self.physics_world.setGravity(Vec3(0, 0, -9.81))
        self.world = GameWorld(self.physics_world, self.render)

        # Setup game loop
        self.taskMgr.add(self.game_loop, "game_loop")
        self.taskMgr.add(self.poll_asyncio, "asyncio-poll")

        self.logger.info("Game Server initialized.")

    def poll_asyncio(self, task):
        self.asyncio_loop.call_soon(self.asyncio_loop.stop)
        self.asyncio_loop.run_forever()
        return task.cont

    def game_loop(self, task):
        dt = globalClock.getDt()
        
        # 1. Process network messages
        while self.message_queue:
            client_id, data = self.message_queue.popleft()
            self.process_message(client_id, data)

        # 2. Update game world
        self.physics_world.doPhysics(dt)
        self.world.update(dt)

        # 3. Broadcast new state
        world_state = self.world.get_world_state()
        if world_state["players"]:
             self.asyncio_loop.call_soon_threadsafe(
                self.broadcast, world_state
             )
        
        return task.cont
        
    def process_message(self, client_id, data):
        msg_type = data.get("type")

        if msg_type == "auth":
            self.handle_auth(client_id, data)
        elif msg_type == "dev_auth":
            self.handle_dev_auth(client_id, data)
        elif msg_type == "input":
             self.world.handle_input(client_id, data.get("state", {}))
        elif msg_type == "move": # Dev clients send their own position
            if self.allow_dev_client:
                self.world.handle_move(client_id, data)
        elif msg_type == "chat_message":
            player = self.world.players.get(client_id)
            if player:
                broadcast_data = {
                    "type": "chat_broadcast",
                    "from_name": player.name,
                    "message": data.get("message", "")
                }
                self.asyncio_loop.call_soon_threadsafe(self.broadcast, broadcast_data)
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

        other_players_state = {pid: p.get_state() for pid, p in self.world.players.items() if pid != client_id}
        welcome_data = {
            "type": "welcome",
            "id": client_id,
            "pos": player.get_state()["pos"],
            "players": other_players_state
        }
        self.send_to_client(client_id, welcome_data)

        join_data = {"type": "player_joined", "id": client_id, "player_info": player.get_state()}
        self.broadcast(join_data, exclude_ids=[client_id])

    def handle_auth(self, client_id, data):
        player_name = data.get("name")
        
        if not player_name:
            self.logger.warning(f"Client {client_id} sent auth request with no name. Disconnecting.")
            writer = self.clients.get(client_id)
            if writer:
                self.asyncio_loop.call_soon_threadsafe(writer.close)
            return

        for p in self.world.players.values():
            if p.name == player_name:
                self.logger.warning(f"Player '{player_name}' is already logged in. Disconnecting new client {client_id}.")
                writer = self.clients.get(client_id)
                if writer:
                    self.asyncio_loop.call_soon_threadsafe(writer.close)
                return

        player = self.world.add_player(client_id, player_name)
        self.logger.info(f"Player '{player_name}' (Client #{client_id}) authenticated.")

        # Prepare welcome message
        other_players_state = {pid: p.get_state() for pid, p in self.world.players.items() if pid != client_id}
        welcome_data = {
            "type": "welcome",
            "id": client_id,
            "pos": player.get_state()["pos"],
            "players": other_players_state
        }
        self.send_to_client(client_id, welcome_data)

        # Inform other players
        join_data = {"type": "player_joined", "id": client_id, "player_info": player.get_state()}
        self.broadcast(join_data, exclude_ids=[client_id])

    def handle_disconnect(self, client_id):
        self.logger.info(f"Client #{client_id} processing disconnection.")
        if client_id in self.clients:
            del self.clients[client_id]
        
        player_id = self.world.remove_player(client_id)
        if player_id is not None:
            leave_data = {"type": "player_left", "id": player_id}
            self.broadcast(leave_data)

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

    def broadcast(self, data, exclude_ids=None):
        if exclude_ids is None:
            exclude_ids = []
        
        payload = json.dumps(data).encode("utf-8")
        header = struct.pack("!I", len(payload))
        
        for client_id, writer in self.clients.items():
            if client_id not in exclude_ids:
                try:
                    writer.write(header + payload)
                except Exception as e:
                    self.logger.error(f"Error broadcasting to client {client_id}: {e}")

    def send_to_client(self, client_id, data):
        writer = self.clients.get(client_id)
        if writer:
            payload = json.dumps(data).encode("utf-8")
            header = struct.pack("!I", len(payload))
            try:
                writer.write(header + payload)
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