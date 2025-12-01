import asyncio
import json
import struct

async def send_message(writer: asyncio.StreamWriter, data: dict):
    if not writer or writer.is_closing():
        return
    payload = json.dumps(data).encode("utf-8")
    header = struct.pack("!I", len(payload))
    writer.write(header + payload)
    await writer.drain()

async def read_messages(reader: asyncio.StreamReader, message_handler):
    while True:
        try:
            header = await reader.readexactly(4)
            if not header:
                break
            msg_len = struct.unpack("!I", header)[0]
            payload = await reader.readexactly(msg_len)
            if not payload:
                break
            data = json.loads(payload.decode("utf-8"))
            message_handler(data)
        except (asyncio.IncompleteReadError, ConnectionResetError):
            print("Connection lost.")
            break
        except Exception as e:
            print(f"Error reading message: {e}")
            break