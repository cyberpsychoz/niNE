import asyncio
import ssl
import sys
import argparse
import json

from nine.core.network import send_message, read_messages


def handle_incoming_message(data: dict):
    print(f"Received: {data}")


async def user_input(writer: asyncio.StreamWriter):
    while True:
        message = await asyncio.to_thread(sys.stdin.readline)
        message = message.strip()
        if message:
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
    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    try:
        ssl_context.load_verify_locations('certs/cert.pem')
    except FileNotFoundError:
        print("CRITICAL ERROR: Certificate file 'certs/cert.pem' not found.")
        return

    reader, writer = None, None
    try:
        reader, writer = await asyncio.open_connection(
            host, port, ssl=ssl_context, server_hostname=host if host != "localhost" else None
        )
        print(f"Connected to {host}:{port}")

        auth_data = {"type": "dev_auth", "name": name}
        await send_message(writer, auth_data)

        read_task = asyncio.create_task(read_messages(reader, handle_incoming_message))
        input_task = asyncio.create_task(user_input(writer))

        await asyncio.gather(read_task, input_task)

    except Exception as e:
        print(f"Failed to connect: {e}")
    finally:
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
    except KeyboardInterrupt:
        print("Client stopped.")
