import asyncio
import json
import struct
from typing import NamedTuple, Optional

from .events import EventManager


class ClientConnectedEvent(NamedTuple):
    client_id: int
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter


class ClientDisconnectedEvent(NamedTuple):
    client_id: int


class MessageReceivedEvent(NamedTuple):
    client_id: int
    data: dict


class NetworkManager:
    """
    Управляет сетевым взаимодействием (клиент/сервер) на базе asyncio.
    """

    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager
        self.clients: dict[int, asyncio.StreamWriter] = {}
        self._next_client_id = 1
        self._server_task: Optional[asyncio.Task] = None

    async def start_server(self, host: str, port: int):
        """Запускает TCP сервер."""
        server = await asyncio.start_server(self._handle_connection, host, port)
        addr = server.sockets[0].getsockname()
        print(f"Сервер запущен на {addr}")
        self.event_manager.post("network_server_started", addr)

        async with server:
            await server.serve_forever()

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Обрабатывает новое клиентское подключение."""
        client_id = self._next_client_id
        self._next_client_id += 1
        self.clients[client_id] = writer

        addr = writer.get_extra_info("peername")
        print(f"Новое подключение от {addr}, назначен ID {client_id}")

        self.event_manager.post("network_client_connected", ClientConnectedEvent(client_id, reader, writer))

        try:
            while True:
                header = await reader.readexactly(4)
                msg_len = struct.unpack("!I", header)[0]

                payload = await reader.readexactly(msg_len)
                data = json.loads(payload.decode("utf-8"))

                self.event_manager.post("network_message_received", MessageReceivedEvent(client_id, data))

        except (asyncio.IncompleteReadError, ConnectionResetError):
            print(f"Клиент {client_id} ({addr}) отключился.")
        except Exception as e:
            print(f"Ошибка клиента {client_id}: {e}")
        finally:
            del self.clients[client_id]
            writer.close()
            await writer.wait_closed()
            self.event_manager.post("network_client_disconnected", ClientDisconnectedEvent(client_id))

    async def send_message(self, client_id: int, data: dict):
        """Отправляет сообщение определенному клиенту."""
        writer = self.clients.get(client_id)
        if writer:
            payload = json.dumps(data).encode("utf-8")
            header = struct.pack("!I", len(payload))
            
            writer.write(header + payload)
            await writer.drain()

    async def broadcast(self, data: dict, exclude_ids: Optional[list[int]] = None):
        """Рассылает сообщение всем клиентам, с возможностью исключений."""
        if exclude_ids is None:
            exclude_ids = []
        
        tasks = [
            self.send_message(client_id, data)
            for client_id in self.clients
            if client_id not in exclude_ids
        ]
        await asyncio.gather(*tasks)

