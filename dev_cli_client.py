import asyncio
<<<<<<< HEAD
import json
import ssl
import struct
import sys
import argparse

async def send_message(writer: asyncio.StreamWriter, data: dict):
    if not writer or writer.is_closing(): return
    payload = json.dumps(data).encode("utf-8")
    header = struct.pack("!I", len(payload))
    writer.write(header + payload)
    await writer.drain()

async def read_messages(reader: asyncio.StreamReader):
    while True:
        try:
            header = await reader.readexactly(4)
            if not header: break
            msg_len = struct.unpack("!I", header)[0]
            payload = await reader.readexactly(msg_len)
            if not payload: break
            data = json.loads(payload.decode("utf-8"))
            print(f"Received: {data}")
        except (asyncio.IncompleteReadError, ConnectionResetError):
            print("Connection lost.")
            break
        except Exception as e:
            print(f"Error reading message: {e}")
            break
=======
import ssl
import sys
import argparse
import json

from nine.core.network import send_message, read_messages


def handle_incoming_message(data: dict):
    print(f"Received: {data}")

>>>>>>> main-core-engine

async def user_input(writer: asyncio.StreamWriter):
    while True:
        message = await asyncio.to_thread(sys.stdin.readline)
        message = message.strip()
        if message:
<<<<<<< HEAD
            await send_message(writer, {"type": "chat_message", "message": message})

async def main(name: str):
    with open("server_config.json") as f:
        config = json.load(f)

    host = config.get("host", "localhost")
    port = config.get("port", 9009)

=======
            # Allow sending raw JSON for debugging
            if message.startswith('{') and message.endswith('}'):
                try:
                    data = json.loads(message)
                    await send_message(writer, data)
                except json.JSONDecodeError:
                    print("Invalid JSON. Sending as a chat message.")
                    await send_message(writer, {"type": "chat_message", "message": message})
            else:
                await send_message(writer, {"type": "chat_message", "message": message})


async def main(name: str, host: str, port: int):
>>>>>>> main-core-engine
    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    try:
        ssl_context.load_verify_locations('certs/cert.pem')
    except FileNotFoundError:
        print("CRITICAL ERROR: Certificate file 'certs/cert.pem' not found.")
        return

<<<<<<< HEAD
=======
    reader, writer = None, None
>>>>>>> main-core-engine
    try:
        reader, writer = await asyncio.open_connection(
            host, port, ssl=ssl_context, server_hostname=host if host != "localhost" else None
        )
        print(f"Connected to {host}:{port}")

<<<<<<< HEAD
        auth_data = {
            "type": "dev_auth",
            "name": name,
        }
        await send_message(writer, auth_data)

        # Run reader and user input tasks concurrently
        read_task = asyncio.create_task(read_messages(reader))
=======
        auth_data = {"type": "dev_auth", "name": name}
        await send_message(writer, auth_data)

        read_task = asyncio.create_task(read_messages(reader, handle_incoming_message))
>>>>>>> main-core-engine
        input_task = asyncio.create_task(user_input(writer))

        await asyncio.gather(read_task, input_task)

    except Exception as e:
        print(f"Failed to connect: {e}")
    finally:
<<<<<<< HEAD
        if 'writer' in locals() and writer:
            writer.close()
            await writer.wait_closed()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="DevPlayer", help="Player name to use for authentication.")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.name))
=======
        if writer:
            writer.close()
            await writer.wait_closed()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Development CLI client.")
    parser.add_argument("--name", default="DevCliPlayer", help="Player name to use.")
    parser.add_argument("--host", default="localhost", help="Server host.")
    parser.add_argument("--port", type=int, default=9009, help="Server port.")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.name, args.host, args.port))
>>>>>>> main-core-engine
    except KeyboardInterrupt:
        print("Client stopped.")
