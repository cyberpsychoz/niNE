import asyncio
import time
from itertools import cycle

from nine.core.app import Application
from nine.core.network import NetworkManager, MessageReceivedEvent, ClientConnectedEvent, ClientDisconnectedEvent
from nine.core.plugins import PluginManager
from nine.core.world import World
from nine.core.database import DatabaseManager

# Конфигурация
HOST = "localhost"
PORT = 9009
TICK_RATE = 20

class ServerApp(Application):
    def __init__(self):
        super().__init__(is_server=True)
        self.network = NetworkManager(self.event_manager)
        self.db = DatabaseManager()
        self.plugin_manager = PluginManager(self, self.event_manager)

        # {client_id: {'name': str, 'pos': [x, y, z], 'uuid': str}}
        self.players = {}
        # {client_id: 'player_uuid'} - для обратного поиска UUID при отключении
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
        # Событие network_client_connected уже разослано через EventManager,
        # плагины могут подписаться на него напрямую.

    def on_client_disconnected(self, event: ClientDisconnectedEvent):
        client_id = event.client_id
        player_uuid = self.client_id_to_uuid.get(client_id)
        
        if player_uuid and client_id in self.players:
            player_info = self.players[client_id]
            player_name = player_info.get("name", "Unknown")
            
            self.db.set_player_attribute(player_uuid, "pos", player_info["pos"])
            self.db.set_player_attribute(player_uuid, "name", player_name)
            print(f"Данные для игрока '{player_name}' ({player_uuid}) сохранены.")
            
            del self.players[client_id]
            del self.client_id_to_uuid[client_id]
            
            leave_data = {"type": "player_left", "id": client_id}
            self.asyncio_loop.create_task(self.network.broadcast(leave_data))
            print(f"Игрок {player_name} ({client_id}) отключился.")
        
        # Событие network_client_disconnected уже разослано,
        # плагины могут подписаться на него напрямую.

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
                # --- Игрок существует, проверяем пароль ---
                if self.db.verify_player_password_by_name(player_name, password):
                    print(f"Игрок '{player_name}' успешно аутентифицирован.")
                    # Обновляем UUID, если он изменился (вход с другой машины)
                    if player_data['uuid'] != client_uuid:
                        self.db.update_player_uuid(player_name, client_uuid)
                    
                    # Используем каноничный UUID из базы
                    player_uuid = player_data['uuid']
                else:
                    print(f"Неудачная попытка входа для '{player_name}': неверный пароль.")
                    self.asyncio_loop.create_task(self.network.send_message(
                        client_id, {"type": "auth_failed", "reason": "Неверное имя пользователя или пароль."}
                    ))
                    return
            else:
                # --- Новый игрок, регистрируем ---
                if self.db.create_player(client_uuid, player_name, password):
                    print(f"Новый игрок '{player_name}' зарегистрирован с UUID {client_uuid}.")
                    player_uuid = client_uuid # Используем UUID, с которым создали
                else:
                    # Это может случиться в редком случае гонки, когда два клиента
                    # одновременно пытаются зарегистрировать одно и то же имя.
                    print(f"Неудачная попытка регистрации для '{player_name}': имя уже может быть занято.")
                    self.asyncio_loop.create_task(self.network.send_message(
                        client_id, {"type": "auth_failed", "reason": "Не удалось зарегистрировать пользователя. Возможно, имя занято."}
                    ))
                    return

            # --- Логика после успешной аутентификации / регистрации ---
            
            # Проверяем, не подключен ли уже игрок с таким UUID
            old_client_id = next((cid for cid, p_info in self.players.items() if p_info.get('uuid') == player_uuid), None)
            if old_client_id is not None:
                print(f"Игрок {player_name} ({player_uuid}) переподключается. Старый ID: {old_client_id}, новый ID: {client_id}.")
                old_writer = self.network.clients.get(old_client_id)
                if old_writer:
                    old_writer.close()
                if old_client_id in self.players: del self.players[old_client_id]
                if old_client_id in self.client_id_to_uuid: del self.client_id_to_uuid[old_client_id]

            db_attributes = self.db.get_player_all_attributes(player_uuid)
            spawn_pos = db_attributes.get("pos", next(self.spawn_points))

            self.players[client_id] = {"name": player_name, "pos": spawn_pos, "uuid": player_uuid}
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

        elif client_id in self.players:
            if msg_type == "move":
                self.players[client_id]["pos"] = data.get("pos", self.players[client_id]["pos"])
            elif msg_type == "chat_message":
                message = data.get("message", "")
                if message:
                    sender_name = self.players.get(client_id, {}).get('name', f'Player {client_id}')
                    broadcast_data = {
                        "type": "chat_broadcast",
                        "from_name": sender_name,
                        "message": message
                    }
                    self.asyncio_loop.create_task(self.network.broadcast(broadcast_data))
            else:
                event_name = f"server_on_{msg_type}"
                event_data = {
                    "client_id": client_id,
                    "player_uuid": self.client_id_to_uuid.get(client_id),
                    "data": data
                }
                self.event_manager.post(event_name, event_data)

    async def broadcast_world_state(self):
        while self.running:
            await asyncio.sleep(1 / TICK_RATE)
            if not self.players:
                continue
            
            state_data = {"type": "world_state", "players": self.players}
            await self.network.broadcast(state_data)

    async def auto_save_world(self):
        auto_save_interval = 300  # 5 минут
        while self.running:
            await asyncio.sleep(auto_save_interval)
            
            if not self.players:
                continue

            print(f"[{time.strftime('%H:%M:%S')}] Начало автосохранения мира...")
            saved_count = 0
            for client_id, player_info in self.players.items():
                player_uuid = player_info.get("uuid")
                if player_uuid:
                    try:
                        self.db.set_player_attribute(player_uuid, "pos", player_info["pos"])
                        self.db.set_player_attribute(player_uuid, "name", player_info.get("name"))
                        saved_count += 1
                    except Exception as e:
                        print(f"Ошибка при автосохранении игрока {player_uuid}: {e}")
            
            if saved_count > 0:
                print(f"[{time.strftime('%H:%M:%S')}] Автосохранение завершено. Сохранено {saved_count} игроков.")


    async def main_loop(self):
        self.running = True
        self.event_manager.post("app_start")
        self.plugin_manager.load_plugins()
        self.asyncio_loop.create_task(self.broadcast_world_state())
        self.asyncio_loop.create_task(self.auto_save_world())

        last_tick_time = time.time()
        tick_interval = 1.0 / TICK_RATE

        try:
            while self.running:
                now = time.time()
                delta_time = now - last_tick_time
                
                if delta_time >= tick_interval:
                    # Отправляем событие тика, на которое могут подписаться плагины
                    self.event_manager.post('app_tick', {'delta_time': delta_time})
                    last_tick_time = now

                # Небольшая пауза, чтобы не загружать CPU на 100%
                await asyncio.sleep(0.01)

        except KeyboardInterrupt:
            print("Сервер завершает работу...")
        finally:
            self.stop()

    def stop(self):
        if self.running:
            # Сохраняем данные всех оставшихся игроков при остановке сервера
            for client_id, player_info in self.players.items():
                player_uuid = player_info.get("uuid")
                if player_uuid:
                    self.db.set_player_attribute(player_uuid, "pos", player_info["pos"])
                    self.db.set_player_attribute(player_uuid, "name", player_info.get("name"))
            
            self.plugin_manager.unload_plugins()
            super().stop()
            # Останавливаем управляемый процесс Redis
            self.db.shutdown()


async def main():
    server_app = ServerApp()
    server_app.asyncio_loop = asyncio.get_running_loop()
    server_task = asyncio.create_task(server_app.network.start_server(HOST, PORT))
    main_loop_task = asyncio.create_task(server_app.main_loop())
    await asyncio.gather(server_task, main_loop_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Завершение работы.")

