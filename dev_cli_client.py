import asyncio
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

async def user_input(writer: asyncio.StreamWriter):
    while True:
        message = await asyncio.to_thread(sys.stdin.readline)
        message = message.strip()
        if message:
            await send_message(writer, {"type": "chat_message", "message": message})

async def main(name: str):
    with open("server_config.json") as f:
        config = json.load(f)

    host = config.get("host", "localhost")
    port = config.get("port", 9009)

    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    try:
        ssl_context.load_verify_locations('certs/cert.pem')
    except FileNotFoundError:
        print("CRITICAL ERROR: Certificate file 'certs/cert.pem' not found.")
        return

    try:
        reader, writer = await asyncio.open_connection(
            host, port, ssl=ssl_context, server_hostname=host if host != "localhost" else None
        )
        print(f"Connected to {host}:{port}")

        auth_data = {
            "type": "dev_auth",
            "name": name,
        }
        await send_message(writer, auth_data)

        # Run reader and user input tasks concurrently
        read_task = asyncio.create_task(read_messages(reader))
        input_task = asyncio.create_task(user_input(writer))

        await asyncio.gather(read_task, input_task)

    except Exception as e:
        print(f"Failed to connect: {e}")
    finally:
        if 'writer' in locals() and writer:
            writer.close()
            await writer.wait_closed()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="DevPlayer", help="Player name to use for authentication.")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.name))
    except KeyboardInterrupt:
        print("Client stopped.")
