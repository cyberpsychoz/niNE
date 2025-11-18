import asyncio
import json
import struct
import sys
from pathlib import Path

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import CardMaker, NodePath, LColor

from nine.core.ui import UIManager

# Конфигурация
HOST = "localhost"
PORT = 9009

class GameClient(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.player_model = None
        self.is_connected = False
        self.character_name = "Player"

        # --- UI ---
        callbacks = {
            "connect": self.start_connection,
            "settings": self.open_settings_menu,
            "exit": self.exit_game,
            "save_settings": self.save_settings,
            "close_settings": self.close_settings_menu,
        }
        self.ui = UIManager(callbacks)
        self.ui.create_main_menu()

        self.setup_scene()

        # Интеграция asyncio с менеджером задач Panda3D
        self.taskMgr.add(self.poll_asyncio, "asyncio-poll")

    def setup_scene(self):
        """Настраивает базовое освещение и положение камеры."""
        self.disableMouse()
        self.camera.setPos(0, -20, 5)
        self.camera.lookAt(0, 0, 0)

    # --- UI Callbacks ---
    def start_connection(self):
        """Начинает процесс подключения к серверу."""
        print("Нажата кнопка 'Подключиться'...")
        self.ui.destroy_main_menu()
        # В будущем здесь может быть экран загрузки
        asyncio.create_task(self.connect_and_read())

    def open_settings_menu(self):
        """Открывает меню настроек."""
        self.ui.destroy_main_menu()
        self.ui.create_settings_menu(self.character_name)

    def save_settings(self):
        """Сохраняет имя персонажа и закрывает меню настроек."""
        self.character_name = self.ui.get_character_name()
        print(f"Имя персонажа изменено на: {self.character_name}")
        self.close_settings_menu()

    def close_settings_menu(self):
        """Закрывает меню настроек и возвращается в главное меню."""
        self.ui.destroy_settings_menu()
        self.ui.create_main_menu()

    def exit_game(self):
        """Выходит из игры."""
        self.userExit()

    # --- Game Logic ---
    def on_successful_connection(self):
        """Вызывается после успешного подключения к серверу."""
        # Теперь, когда мы подключены, загружаем игровой мир/модели
        self.load_player_model()

    def load_player_model(self):
        """
        Пытается загрузить модель игрока. Если не удается,
        создает белый прямоугольник в качестве запасного варианта.
        """
        if self.player_model:
            self.player_model.removeNode()

        model_path = Path("assets/models/player.glb")
        try:
            print(f"Загрузка модели: {model_path}")
            self.player_model = self.loader.loadModel(model_path)
            self.player_model.reparentTo(self.render)
            print("Модель игрока успешно загружена.")
        except Exception as e:
            print(f"Не удалось загрузить модель игрока: {e}")
            print("Создание запасной модели (белый прямоугольник)...")
            
            cm = CardMaker("fallback-player")
            cm.setFrame(-0.5, 0.5, -1, 1)
            
            self.player_model = self.render.attachNewNode(cm.generate())
            self.player_model.setColor(LColor(1, 1, 1, 1))
            print("Запасная модель создана.")

        self.player_model.setPos(0, 0, 0)

    # --- Networking ---
    async def poll_asyncio(self, task):
        """Задача Panda3D для работы цикла событий asyncio."""
        await asyncio.sleep(0)
        return Task.cont

    async def connect_and_read(self):
        """Подключается к серверу и запускает чтение сообщений."""
        print(f"Подключение к {HOST}:{PORT}...")
        try:
            reader, writer = await asyncio.open_connection(HOST, PORT)
            self.is_connected = True
            print("Успешно подключено к серверу.")
            
            self.on_successful_connection()
            
            await self.read_messages(reader)

        except ConnectionRefusedError:
            print("В соединении отказано. Сервер запущен?")
            self.ui.create_main_menu() # Возвращаемся в меню, если не удалось подключиться
        except Exception as e:
            print(f"Ошибка подключения: {e}")
        finally:
            self.is_connected = False
            print("Соединение с сервером закрыто.")

    async def read_messages(self, reader: asyncio.StreamReader):
        """Читает и обрабатывает сообщения от сервера."""
        while self.is_connected:
            try:
                header = await reader.readexactly(4)
                msg_len = struct.unpack("!I", header)[0]
                payload = await reader.readexactly(msg_len)
                data = json.loads(payload.decode("utf-8"))
                print(f"[Ответ сервера]: {data}")
            except (asyncio.IncompleteReadError, ConnectionResetError):
                self.is_connected = False
            except Exception as e:
                print(f"Ошибка при чтении сообщения: {e}")
                self.is_connected = False
        
        print("Соединение с сервером разорвано.")
        if self.player_model:
            self.player_model.hide()
        self.ui.create_main_menu()


if __name__ == "__main__":
    try:
        import panda3d
    except ImportError:
        print("Ошибка: Panda3D не установлен. Пожалуйста, установите его:")
        print("pip install panda3d")
        sys.exit(1)

    app = GameClient()
    app.run()