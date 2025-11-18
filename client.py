import asyncio
import json
import struct
import sys

# Конфигурация
HOST = "localhost"
PORT = 9009

async def send_message(writer: asyncio.StreamWriter, data: dict):
    """Отправляет JSON сообщение на сервер."""
    payload = json.dumps(data).encode("utf-8")
    header = struct.pack("!I", len(payload))
    writer.write(header + payload)
    await writer.drain()

async def read_messages(reader: asyncio.StreamReader):
    """Читает и выводит сообщения от сервера."""
    try:
        while True:
            header = await reader.readexactly(4)
            msg_len = struct.unpack("!I", header)[0]
            payload = await reader.readexactly(msg_len)
            data = json.loads(payload.decode("utf-8"))
            print(f"\n[Ответ сервера]: {data}\n> ", end="")
    except (asyncio.IncompleteReadError, ConnectionResetError):
        print("Соединение с сервером разорвано.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

async def handle_user_input(writer: asyncio.StreamWriter):
    """Читает ввод пользователя и отправляет на сервер."""
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        message = line.strip()
        if message:
            if message.lower() == "/quit":
                break
            await send_message(writer, {"type": "chat_message", "message": message})
    writer.close()


async def main():
    """Основная функция для подключения к серверу."""
    print(f"Подключение к {HOST}:{PORT}...")
    try:
        reader, writer = await asyncio.open_connection(HOST, PORT)
    except ConnectionRefusedError:
        print("В соединении отказано. Сервер запущен?")
        return

    print("Подключено! Вводите сообщения и нажимайте Enter. Для выхода введите /quit.")
    print("> ", end="")
    sys.stdout.flush()

    read_task = asyncio.create_task(read_messages(reader))
    input_task = asyncio.create_task(handle_user_input(writer))

    await input_task
    read_task.cancel()
    
    print("Соединение закрыто.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nКлиент отключен.")
