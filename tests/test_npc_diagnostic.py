"""
Диагностический скрипт для тестирования NPC.

Создаёт изолированную среду для проверки:
- Рендеринга NPC
- Применения цветов
- Анимаций
- Синхронизации позиций
- Боевой системы

Запуск:
    python -m tests.test_npc_diagnostic

Требования:
    - Запущенный сервер на localhost:9009
"""

import asyncio
import json
import logging
import ssl
import struct
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from direct.showbase.ShowBase import ShowBase
from panda3d.core import loadPrcFileData, Vec3, TextNode
from direct.actor.Actor import Actor
from direct.gui.OnscreenText import OnscreenText

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG для полного вывода
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("npc_diagnostic.log", mode='w')
    ]
)
logger = logging.getLogger("NPC_DIAGNOSTIC")


class NPCDiagnosticClient(ShowBase):
    """Специальный клиент для диагностики NPC."""

    def __init__(self):
        logger.info("=== NPC DIAGNOSTIC CLIENT ===")
        ShowBase.__init__(self)
        self.disableMouse()

        # Networking
        self.writer = None
        self.reader = None
        self.player_id = -1

        # NPC tracking
        self.npcs = {}  # {entity_id: NPC data}
        self.npc_nodes = {}  # {entity_id: NodePath}

        # Камера
        self.camera.setPos(0, -20, 10)
        self.camera.lookAt(0, 0, 0)

        # Инструкции на экране
        self.instructions = OnscreenText(
            text="NPC Diagnostic Mode\nPress '1' to spawn goblin\nPress '2' to start combat\nPress 'ESC' to exit",
            pos=(-1.3, 0.9),
            scale=0.05,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft
        )

        # Debug info
        self.debug_text = OnscreenText(
            text="",
            pos=(-1.3, 0.7),
            scale=0.04,
            fg=(0.8, 1, 0.8, 1),
            align=TextNode.ALeft
        )

        # Bindings
        self.accept("1", self.spawn_goblin)
        self.accept("2", self.start_combat)
        self.accept("escape", sys.exit)

        # Подключение к серверу
        self.asyncio_loop = asyncio.get_event_loop()
        self.taskMgr.add(self.poll_asyncio, "asyncio-poll")
        self.asyncio_loop.create_task(self.connect_to_server())

    def poll_asyncio(self, task):
        """Обрабатывает asyncio события в Panda3D event loop."""
        self.asyncio_loop.stop()
        self.asyncio_loop.run_forever()
        return task.cont

    async def connect_to_server(self):
        """Подключается к серверу как dev клиент."""
        logger.info("Connecting to localhost:9009...")

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try:
            self.reader, self.writer = await asyncio.open_connection(
                'localhost', 9009, ssl=ssl_context
            )
            logger.info("Connected to server")

            # Отправляем dev_auth
            await self.send_message({
                "type": "dev_auth",
                "name": "NPCDiagnostic"
            })

            # Запускаем цикл чтения
            self.asyncio_loop.create_task(self.read_messages())

        except Exception as e:
            logger.error(f"Failed to connect: {e}")

    async def send_message(self, data: dict):
        """Отправляет сообщение на сервер."""
        if not self.writer:
            return

        payload = json.dumps(data).encode("utf-8")
        header = struct.pack("!I", len(payload))
        self.writer.write(header + payload)
        await self.writer.drain()
        logger.debug(f"SENT: {data}")

    async def read_messages(self):
        """Читает сообщения от сервера."""
        while True:
            try:
                header = await self.reader.readexactly(4)
                length = struct.unpack("!I", header)[0]
                payload = await self.reader.readexactly(length)
                data = json.loads(payload.decode("utf-8"))

                logger.debug(f"RECV: {data}")
                self.handle_message(data)

            except Exception as e:
                logger.error(f"Connection lost: {e}")
                break

    def handle_message(self, data: dict):
        """Обрабатывает сообщения от сервера."""
        msg_type = data.get("type")

        if msg_type == "auth_success":
            self.player_id = data.get("player_id", -1)
            logger.info(f"Auth success, player_id={self.player_id}")
            self.update_debug_text()

        elif msg_type == "world_state":
            self.handle_world_state(data)

        elif msg_type == "combat_started":
            logger.info(f"Combat started: {data}")

    def handle_world_state(self, data: dict):
        """Обрабатывает world_state с NPC."""
        pawns = data.get("pawns", [])

        for pawn in pawns:
            entity_id = pawn.get("entity_id")
            if not entity_id:
                continue

            # Пропускаем игрока
            if pawn.get("is_player", False):
                continue

            # Это NPC
            if entity_id not in self.npcs:
                # Новый NPC
                logger.info(f"\n=== NEW NPC SPAWNED ===")
                logger.info(f"Entity ID: {entity_id}")
                logger.info(f"Display name: {pawn.get('display_name', 'Unknown')}")
                logger.info(f"Model: {pawn.get('model', 'N/A')}")
                logger.info(f"Position: {pawn.get('position', {})}")
                logger.info(f"HP: {pawn.get('hp_current')}/{pawn.get('hp_max')}")
                logger.info(f"AI State: {pawn.get('ai_state', 'N/A')}")
                logger.info(f"Full data: {json.dumps(pawn, indent=2)}")

                self.create_npc_visual(entity_id, pawn)

            # Обновляем данные
            self.npcs[entity_id] = pawn
            self.update_npc_position(entity_id, pawn)

        self.update_debug_text()

    def create_npc_visual(self, entity_id: str, data: dict):
        """Создаёт визуальное представление NPC."""
        logger.info(f"Creating visual for NPC {entity_id}")

        # Позиция
        pos_data = data.get("position", {})
        position = Vec3(
            pos_data.get("x", 0),
            pos_data.get("y", 0),
            pos_data.get("z", 0)
        )

        # Корневой узел
        node = self.render.attachNewNode(f"npc_{entity_id[:8]}")
        node.setPos(position)

        # Модель
        model_path = data.get("model", "")
        logger.info(f"Model path from server: '{model_path}'")

        try:
            model_file = "nine/assets/models/base.bam"
            actor = Actor(model_file)
            actor.reparentTo(node)
            actor.setScale(0.3)

            # Применяем цвет
            color_map = {
                "goblin": (0.4, 0.6, 0.3, 1),    # Зелёный
                "skeleton": (0.9, 0.9, 0.8, 1),  # Белый
                "bandit": (0.6, 0.4, 0.3, 1),    # Коричневый
                "wolf": (0.5, 0.5, 0.5, 1),      # Серый
            }

            npc_type = model_path if model_path else "default"
            logger.info(f"NPC type for color mapping: '{npc_type}'")

            if npc_type in color_map:
                color = color_map[npc_type]
                actor.setColor(*color)
                logger.info(f"Applied color: {color}")
            else:
                actor.setColor(0.7, 0.7, 0.7, 1)
                logger.info("Applied default gray color")

            logger.info("NPC visual created successfully")

        except Exception as e:
            logger.error(f"Failed to create NPC visual: {e}", exc_info=True)
            # Fallback sphere
            sphere = self.loader.loadModel("models/misc/sphere")
            sphere.reparentTo(node)
            sphere.setScale(0.5)
            sphere.setColor(1, 0, 0, 1)  # Красная сфера = ошибка

        # Имя над головой
        name_tag = OnscreenText(
            text=data.get("display_name", "NPC"),
            pos=(0, 2),
            scale=0.3,
            fg=(1, 1, 0, 1),
            align=TextNode.ACenter,
            mayChange=True
        )
        name_tag.reparentTo(node)

        self.npc_nodes[entity_id] = node

    def update_npc_position(self, entity_id: str, data: dict):
        """Обновляет позицию NPC."""
        if entity_id not in self.npc_nodes:
            return

        pos_data = data.get("position", {})
        position = Vec3(
            pos_data.get("x", 0),
            pos_data.get("y", 0),
            pos_data.get("z", 0)
        )

        self.npc_nodes[entity_id].setPos(position)

    def update_debug_text(self):
        """Обновляет debug информацию на экране."""
        lines = [
            f"Player ID: {self.player_id}",
            f"NPCs count: {len(self.npcs)}",
            ""
        ]

        for entity_id, data in self.npcs.items():
            lines.append(f"{data.get('display_name', 'NPC')}: {data.get('ai_state', 'N/A')}")

        self.debug_text.setText("\n".join(lines))

    def spawn_goblin(self):
        """Спавнит гоблина через чат команду."""
        logger.info("Spawning goblin...")
        self.asyncio_loop.create_task(self.send_message({
            "type": "chat_message",
            "message": "/spawnnpc goblin 0 3 0"
        }))

    def start_combat(self):
        """Начинает бой."""
        logger.info("Starting combat...")
        self.asyncio_loop.create_task(self.send_message({
            "type": "chat_message",
            "message": "/startcombat"
        }))


if __name__ == "__main__":
    logger.info("Starting NPC Diagnostic Client")
    logger.info("Make sure server is running on localhost:9009")

    app = NPCDiagnosticClient()
    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
