"""
Автоматизированный набор тестов с визуальными отчётами.

Запускает сервер, клиент, выполняет действия, делает скриншоты.
Генерирует HTML отчёт со всеми скриншотами и логами.

Запуск:
    python -m tests.automated_test_suite

Что тестирует:
1. UI экраны (Login, Character Select, Settings)
2. NPC спавн и отображение
3. Боевая система
4. Движение и камера

Результат:
    test_report_TIMESTAMP/ - папка с отчётом
        - report.html - визуальный отчёт
        - screenshots/ - все скриншоты
        - logs/ - копии логов
"""

import asyncio
import json
import logging
import os
import ssl
import struct
import sys
import time
from datetime import datetime
from pathlib import Path

# Добавляем корень проекта
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from direct.showbase.ShowBase import ShowBase
from panda3d.core import loadPrcFileData, WindowProperties, Filename

# Настройки для headless режима (без окна)
loadPrcFileData("", "window-type offscreen")
loadPrcFileData("", "audio-library-name null")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AutoTest")


class AutomatedTestClient(ShowBase):
    """Автоматизированный тестовый клиент."""

    def __init__(self, output_dir: Path):
        logger.info("=== AUTOMATED TEST SUITE ===")
        ShowBase.__init__(self)

        self.output_dir = output_dir
        self.screenshots_dir = output_dir / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)

        self.screenshot_counter = 0
        self.test_results = []

        # Подключение
        self.writer = None
        self.reader = None
        self.player_id = -1

        # Атрибуты для совместимости с UI
        self.camera_controller = None
        self.character_name = "AutoTest"
        self.is_connected = False

        # Импорты
        from nine.core.events import EventManager
        from nine.core.plugins import PluginManager
        from nine.ui.manager import UIManager

        self.event_manager = EventManager()
        self.plugin_manager = PluginManager(self, self.event_manager)

        # UI
        callbacks = {
            "connect": lambda: None,
            "exit": lambda: None,
            "attempt_login": lambda: None,
            "close_login_menu": lambda: None,
            "settings": lambda: None,
        }
        self.ui = UIManager(self, callbacks)

        # Загружаем плагины
        self.plugin_manager.load_plugins()

        # Asyncio - создаём новый loop если нужно
        try:
            self.asyncio_loop = asyncio.get_running_loop()
        except RuntimeError:
            self.asyncio_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.asyncio_loop)

        self.taskMgr.add(self.poll_asyncio, "asyncio-poll")

        logger.info("Test client initialized")

    def poll_asyncio(self, task):
        """Обрабатывает asyncio события."""
        self.asyncio_loop.stop()
        self.asyncio_loop.run_forever()
        return task.cont

    def take_screenshot(self, name: str, description: str = ""):
        """Делает скриншот и сохраняет в отчёт."""
        self.screenshot_counter += 1
        filename = f"{self.screenshot_counter:03d}_{name}.png"
        filepath = self.screenshots_dir / filename

        # Panda3D screenshot
        self.screenshot(namePrefix=str(filepath.with_suffix('')), defaultFilename=0)

        # Ждём сохранения
        time.sleep(0.5)

        result = {
            "step": self.screenshot_counter,
            "name": name,
            "description": description,
            "screenshot": f"screenshots/{filename}",
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        logger.info(f"Screenshot: {name}")

        return result

    async def connect_to_server(self):
        """Подключается к серверу."""
        logger.info("Connecting to localhost:9009...")

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try:
            self.reader, self.writer = await asyncio.open_connection(
                'localhost', 9009, ssl=ssl_context
            )
            logger.info("Connected")

            # Dev auth
            await self.send_message({
                "type": "dev_auth",
                "name": "AutoTest"
            })

            self.asyncio_loop.create_task(self.read_messages())

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.test_results.append({
                "step": 0,
                "name": "CONNECTION_FAILED",
                "description": str(e),
                "screenshot": None,
                "timestamp": datetime.now().isoformat()
            })

    async def send_message(self, data: dict):
        if not self.writer:
            return
        payload = json.dumps(data).encode("utf-8")
        header = struct.pack("!I", len(payload))
        self.writer.write(header + payload)
        await self.writer.drain()

    async def read_messages(self):
        while True:
            try:
                header = await self.reader.readexactly(4)
                length = struct.unpack("!I", header)[0]
                payload = await self.reader.readexactly(length)
                data = json.loads(payload.decode("utf-8"))
                self.handle_message(data)
            except Exception as e:
                logger.error(f"Read error: {e}")
                break

    def handle_message(self, data: dict):
        msg_type = data.get("type")

        if msg_type == "auth_success":
            self.player_id = data.get("player_id", -1)
            logger.info(f"Auth success: player_id={self.player_id}")

        elif msg_type == "world_state":
            pawns = data.get("pawns", [])
            logger.info(f"World state: {len(pawns)} pawns")
            for pawn in pawns:
                if not pawn.get("is_player"):
                    logger.info(f"  NPC: {pawn.get('display_name')} model={pawn.get('model')} pos={pawn.get('position')}")

    async def run_test_sequence(self):
        """Выполняет последовательность тестов."""
        logger.info("\n=== Starting Test Sequence ===\n")

        try:
            await self._run_tests()
        except Exception as e:
            logger.error(f"Test sequence failed: {e}", exc_info=True)
            self.test_results.append({
                "step": 999,
                "name": "ERROR",
                "description": f"Test sequence crashed: {str(e)}",
                "screenshot": None,
                "timestamp": datetime.now().isoformat()
            })
        finally:
            # Всегда генерируем отчёт
            self.generate_report()
            await asyncio.sleep(1)
            sys.exit(0)

    async def _run_tests(self):
        """Внутренний метод с тестами."""

        # Test 1: Main Menu
        logger.info("Test 1: Main Menu")
        self.ui.show_main_menu()
        await asyncio.sleep(1)
        self.take_screenshot("01_main_menu", "Главное меню при запуске")

        # Test 2: Login Menu
        logger.info("Test 2: Login Menu")
        self.ui.show_login_menu("localhost:9009", "AutoTest")
        await asyncio.sleep(1)
        self.take_screenshot("02_login_menu", "Меню входа - проверка кнопок и полей")

        # Test 3: Connect to server
        logger.info("Test 3: Connecting to server")
        await self.connect_to_server()
        await asyncio.sleep(2)

        # Test 4: Settings Menu
        logger.info("Test 4: Settings Menu")
        self.ui.hide_login_menu()
        self.ui.show_settings_menu(self)
        await asyncio.sleep(1)
        self.take_screenshot("03_settings_menu", "Настройки - проверка поля имени")

        # Test 5: Load map and spawn NPC
        logger.info("Test 5: Loading game world")
        self.ui.hide_all()

        # Load map
        try:
            from nine.core.character_controller import CharacterController
            self.map_model = self.loader.loadModel("nine/assets/models/maps/map.bam")
            self.map_model.reparentTo(self.render)
            logger.info("Map loaded")
        except Exception as e:
            logger.error(f"Map load failed: {e}")

        await asyncio.sleep(1)
        self.take_screenshot("04_game_world", "Игровой мир загружен")

        # Test 6: Spawn goblin
        logger.info("Test 6: Spawning goblin")
        await self.send_message({
            "type": "chat_message",
            "message": "/spawnnpc goblin 0 5 0"
        })
        await asyncio.sleep(2)
        self.take_screenshot("05_goblin_spawned", "Гоблин заспавнен - проверка цвета и модели")

        # Test 7: Camera angle 1
        logger.info("Test 7: Different camera angles")
        self.camera.setPos(10, -10, 5)
        self.camera.lookAt(0, 5, 0)
        await asyncio.sleep(0.5)
        self.take_screenshot("06_camera_angle_1", "Вид на NPC с угла")

        # Test 8: Camera angle 2
        self.camera.setPos(-10, -10, 5)
        self.camera.lookAt(0, 5, 0)
        await asyncio.sleep(0.5)
        self.take_screenshot("07_camera_angle_2", "Вид на NPC с другого угла")

        # Test 9: Start combat
        logger.info("Test 9: Starting combat")
        await self.send_message({
            "type": "chat_message",
            "message": "/startcombat"
        })
        await asyncio.sleep(2)
        self.take_screenshot("08_combat_started", "Боевая система - проверка UI")

        logger.info("\n=== Test Sequence Complete ===\n")

    def generate_report(self):
        """Генерирует HTML отчёт."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>niNE Automated Test Report</title>
    <style>
        body {{
            font-family: 'Courier New', monospace;
            background: #1a1a1a;
            color: #00ff00;
            padding: 20px;
        }}
        h1 {{
            color: #00ff00;
            border-bottom: 2px solid #00ff00;
        }}
        .test-step {{
            background: #2a2a2a;
            border: 1px solid #00ff00;
            margin: 20px 0;
            padding: 15px;
        }}
        .screenshot {{
            max-width: 100%;
            border: 2px solid #00ff00;
            margin-top: 10px;
        }}
        .timestamp {{
            color: #888;
            font-size: 0.9em;
        }}
        .description {{
            color: #0ff;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <h1>niNE Automated Test Report</h1>
    <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <h2>Test Results ({len(self.test_results)} steps)</h2>
"""

        for result in self.test_results:
            html += f"""
    <div class="test-step">
        <h3>Step {result['step']}: {result['name']}</h3>
        <p class="description">{result['description']}</p>
        <p class="timestamp">{result['timestamp']}</p>
"""
            if result['screenshot']:
                html += f"""
        <img src="{result['screenshot']}" alt="{result['name']}" class="screenshot">
"""
            html += """
    </div>
"""

        html += """
</body>
</html>
"""

        report_path = self.output_dir / "report.html"
        report_path.write_text(html, encoding='utf-8')
        logger.info(f"Report generated: {report_path}")


def main():
    """Главная функция."""
    # Создаём директорию для отчёта
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"test_report_{timestamp}")
    output_dir.mkdir(exist_ok=True)

    logger.info(f"Output directory: {output_dir}")

    # Запускаем клиент
    app = AutomatedTestClient(output_dir)

    # Запускаем тесты
    app.asyncio_loop.create_task(app.run_test_sequence())

    # Запускаем Panda3D (блокирует до завершения)
    app.run()


if __name__ == "__main__":
    logger.info("Starting automated test suite")
    logger.info("Make sure server is running: python -m nine.server.game_server")

    main()
