import asyncio
import json
import logging
import time
import uuid
from itertools import cycle

from nine.core.app import Application
from nine.core.database import DatabaseManager
from nine.core.network import (ClientConnectedEvent, ClientDisconnectedEvent,
                               MessageReceivedEvent, NetworkManager)
from nine.core.plugins import PluginManager


class ServerApp(Application):
    def __init__(self):
        super().__init__(is_server=True)

        log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler("server.log", mode='w')
        file_handler.setFormatter(log_formatter)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        
        with open("server_config.json") as f:
            config = json.load(f)

        self.host = config.get("host", "localhost")
        self.port = config.get("port", 9009)
        self.tick_rate = config.get("tick_rate", 20)
        self.allow_dev_client = config.get("allow_dev_client", False)

        self.network = NetworkManager(self.event_manager)
        self.db = DatabaseManager()
        self.plugin_manager = PluginManager(self, self.event_manager)

        self.players = {}
        self.client_id_to_uuid = {}
        
        self.spawn_points = cycle([
            [0, 0, 0], [5, 5, 0], [-5, 5, 0], [5, -5, 0], [-5, -5, 0]
        ])

        self.event_manager.subscribe("server_broadcast", self._broadcast_handler)
        self.event_manager.subscribe("network_client_connected", self.on_client_connected)
        self.event_manager.subscribe("network_client_disconnected", self.on_client_disconnected)
        self.event_manager.subscribe("network_message_received", self.on_message_received)

    def _broadcast_handler(self, event_data: dict):
        self.asyncio_loop.create_task(
            self.network.broadcast(event_data.get("data", {}), event_data.get("exclude_ids", []))
        )

    def on_client_connected(self, event: ClientConnectedEvent):
        print(f"Клиент {event.client_id} ожидает аутентификации...")

    def on_client_disconnected(self, event: ClientDisconnectedEvent):
        client_id = event.client_id
        player_uuid = self.client_id_to_uuid.get(client_id)
        
        if player_uuid and client_id in self.players:
            player_info = self.players[client_id]
            player_name = player_info.get("name", "Unknown")
            
            is_dev_client = player_info.get("is_dev", False)

            if not is_dev_client:
                self.db.set_player_attribute(player_uuid, "pos", player_info["pos"])
                self.db.set_player_attribute(player_uuid, "name", player_name)
                print(f"Данные для игрока '{player_name}' ({player_uuid}) сохранены.")
            
            del self.players[client_id]
            del self.client_id_to_uuid[client_id]
            
            leave_data = {"type": "player_left", "id": client_id}
            self.asyncio_loop.create_task(self.network.broadcast(leave_data))
            print(f"Игрок {player_name} ({client_id}) отключился.")

    def on_message_received(self, event: MessageReceivedEvent):
        client_id = event.client_id
        data = event.data
        msg_type = data.get("type")

        if msg_type == "auth":
            player_name = data.get("name")
            client_uuid = data.get("uuid")
            password = data.get("password")

            if not all([client_uuid, player_name, password]):
                self.asyncio_loop.create_task(self.network.send_message(
                    client_id, {"type": "auth_failed", "reason": "Все поля должны быть заполнены."}
                ))
                return

            player_data = self.db.get_player_by_name(player_name)

            if player_data:
                if self.db.verify_player_password_by_name(player_name, password):
                    player_uuid = player_data['uuid']
                else:
                    self.asyncio_loop.create_task(self.network.send_message(
                        client_id, {"type": "auth_failed", "reason": "Неверное имя пользователя или пароль."}
                    ))
                    return
            else:
                if self.db.create_player(client_uuid, player_name, password):
                    player_uuid = client_uuid
                else:
                    self.asyncio_loop.create_task(self.network.send_message(
                        client_id, {"type": "auth_failed", "reason": "Не удалось зарегистрировать пользователя."}
                    ))
                    return

            old_client_id = next((cid for cid, p_info in self.players.items() if p_info.get('uuid') == player_uuid), None)
            if old_client_id is not None:
                old_writer = self.network.clients.get(old_client_id)
                if old_writer:
                    old_writer.close()
                if old_client_id in self.players: del self.players[old_client_id]
                if old_client_id in self.client_id_to_uuid: del self.client_id_to_uuid[old_client_id]

            db_attributes = self.db.get_player_all_attributes(player_uuid)
            spawn_pos = db_attributes.get("pos", next(self.spawn_points))

            self.players[client_id] = {"name": player_name, "pos": spawn_pos, "uuid": player_uuid, "rot": (0, 0, 0), "anim_state": "idle", "last_move_time": time.time()}
            self.client_id_to_uuid[client_id] = player_uuid

            welcome_data = {
                "type": "welcome",
                "id": client_id,
                "pos": spawn_pos,
                "players": {cid: p_info for cid, p_info in self.players.items() if cid != client_id}
            }
            self.asyncio_loop.create_task(self.network.send_message(client_id, welcome_data))

            join_data = {"type": "player_joined", "id": client_id, "player_info": self.players[client_id]}
            self.asyncio_loop.create_task(self.network.broadcast(join_data, exclude_ids=[client_id]))

        elif msg_type == "dev_auth" and self.allow_dev_client:
            player_name = data.get("name", f"DevPlayer{client_id}")
            player_uuid = str(uuid.uuid4())

            spawn_pos = next(self.spawn_points)
            self.players[client_id] = {"name": player_name, "pos": spawn_pos, "uuid": player_uuid, "is_dev": True, "rot": (0, 0, 0), "anim_state": "idle", "last_move_time": time.time()}
            self.client_id_to_uuid[client_id] = player_uuid

            welcome_data = {
                "type": "welcome",
                "id": client_id,
                "pos": spawn_pos,
                "players": {cid: p_info for cid, p_info in self.players.items() if cid != client_id},
            }
            self.asyncio_loop.create_task(self.network.send_message(client_id, welcome_data))

            join_data = {"type": "player_joined", "id": client_id, "player_info": self.players[client_id]}
            self.asyncio_loop.create_task(self.network.broadcast(join_data, exclude_ids=[client_id]))

        elif client_id in self.players:
            if msg_type == "move":
                self.players[client_id]["pos"] = data.get("pos", (0,0,0))
                self.players[client_id]["rot"] = data.get("rot", (0,0,0))
                self.players[client_id]["anim_state"] = "walk"
                self.players[client_id]["last_move_time"] = time.time()
            else:
                event_name = f"server_on_{msg_type}"
                event_data = {
                    "client_id": client_id,
                    "player_uuid": self.client_id_to_uuid.get(client_id),
                    "data": data
                }
                self.event_manager.post(event_name, event_data)

    async def check_idle_players(self):
        while self.running:
            now = time.time()
            for player_info in self.players.values():
                if player_info.get("anim_state") == "walk" and now - player_info.get("last_move_time", 0) > 0.2:
                    player_info["anim_state"] = "idle"
            await asyncio.sleep(1)

    async def broadcast_world_state(self):
        while self.running:
            await asyncio.sleep(1 / self.tick_rate)
            if not self.players:
                continue
            
            state_data = {"type": "world_state", "players": self.players}
            await self.network.broadcast(state_data)

    async def auto_save_world(self):
        auto_save_interval = 300
        while self.running:
            await asyncio.sleep(auto_save_interval)
            
            if not self.players:
                continue

            print(f"[{time.strftime('%H:%M:%S')}] Начало автосохранения мира...")
            saved_count = 0
            for client_id, player_info in self.players.items():
                if not player_info.get("is_dev", False):
                    player_uuid = player_info.get("uuid")
                    try:
                        self.db.set_player_attribute(player_uuid, "pos", player_info["pos"])
                        self.db.set_player_attribute(player_uuid, "name", player_info.get("name"))
                        saved_count += 1
                    except Exception as e:
                        print(f"Error autosaving player {player_uuid}: {e}")
            
            if saved_count > 0:
                print(f"[{time.strftime('%H:%M:%S')}] Автосохранение завершено. Сохранено {saved_count} игроков.")

    async def main_loop(self):
        self.running = True
        self.event_manager.post("app_start")
        self.plugin_manager.load_plugins()
        self.asyncio_loop.create_task(self.broadcast_world_state())
        self.asyncio_loop.create_task(self.auto_save_world())
        self.asyncio_loop.create_task(self.check_idle_players())

        last_tick_time = time.time()
        tick_interval = 1.0 / self.tick_rate

        try:
            while self.running:
                now = time.time()
                delta_time = now - last_tick_time
                
                if delta_time >= tick_interval:
                    self.event_manager.post('app_tick', {'delta_time': delta_time})
                    last_tick_time = now

                await asyncio.sleep(0.01)

        except KeyboardInterrupt:
            print("Сервер завершает работу...")
        finally:
            self.stop()

    def stop(self):
        if self.running:
            for client_id, player_info in self.players.items():
                if not player_info.get("is_dev", False):
                    player_uuid = player_info.get("uuid")
                    self.db.set_player_attribute(player_uuid, "pos", player_info["pos"])
                    self.db.set_player_attribute(player_uuid, "name", player_info.get("name"))
            
            self.plugin_manager.unload_plugins()
            super().stop()
            self.db.shutdown()

async def main():
    server_app = ServerApp()
    server_app.asyncio_loop = asyncio.get_running_loop()
    server_task = asyncio.create_task(server_app.network.start_server(server_app.host, server_app.port))
    main_loop_task = asyncio.create_task(server_app.main_loop())
    await asyncio.gather(server_task, main_loop_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Завершение работы.")
