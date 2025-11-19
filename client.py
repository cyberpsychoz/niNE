import asyncio
import json
import struct
import sys
import uuid
from pathlib import Path

from panda3d.core import loadPrcFileData
# Отключаем аудио-библиотеку, чтобы избежать некритичных ошибок на некоторых системах
loadPrcFileData("", "audio-library-name null")

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import CardMaker, NodePath, LColor, TextNode

from nine.core.ui import UIManager

# Устанавливаем кодировку по умолчанию для всего текста в UTF-8
TextNode.setDefaultEncoding(TextNode.EUtf8)

# Конфигурация
HOST = "localhost"
PORT = 9009

class GameClient(ShowBase):
    def __init__(self):
        self.asyncio_loop = asyncio.get_event_loop()
        ShowBase.__init__(self)

        # Состояние игры
        self.player_id = -1
        self.is_connected = False
        self.character_name = "Player"
        self.client_uuid = self._get_or_create_uuid()
        self.player_model = None
        self.other_players = {}
        self.writer = None
        self.is_ingame_menu_open = False
        self.is_chat_open = False
        self.temp_password = None # Временно храним пароль для отправки
        
        # --- UI ---
        callbacks = {
            "connect": self.open_login_menu,
            "settings": self.open_settings_menu,
            "exit": self.exit_game,
            "save_settings": self.save_settings,
            "close_settings": self.close_settings_menu,
            "resume": self.toggle_ingame_menu,
            "disconnect": self.disconnect,
            "attempt_login": self.attempt_login,
            "close_login_menu": self.close_login_menu,
            "send_chat_message": self.send_chat_message,
            "close_chat_input": self.close_chat_input,
        }
        self.ui = UIManager(self, callbacks)
        self.ui.create_main_menu()

        self.setup_scene()

        # --- Управление ---
        self.keyMap = {"w": False, "a": False, "s": False, "d": False}
        self.accept("w", self.update_key_map, ["w", True])
        self.accept("w-up", self.update_key_map, ["w", False])
        self.accept("a", self.update_key_map, ["a", True])
        self.accept("a-up", self.update_key_map, ["a", False])
        self.accept("s", self.update_key_map, ["s", True])
        self.accept("s-up", self.update_key_map, ["s", False])
        self.accept("d", self.update_key_map, ["d", True])
        self.accept("d-up", self.update_key_map, ["d", False])
        self.accept("escape", self.handle_escape)
        self.accept("y", self.toggle_chat_input)

        # --- Задачи ---
        self.taskMgr.add(self.poll_asyncio, "asyncio-poll")
        self.taskMgr.add(self.update_movement, "update-movement-task")

    def _get_or_create_uuid(self) -> str:
        """
        Получает уникальный идентификатор клиента из файла или создает новый.
        """
        uuid_file = Path(".client_uuid")
        if uuid_file.exists():
            try:
                client_uuid = uuid_file.read_text().strip()
                uuid.UUID(client_uuid)
                print(f"Найден существующий UUID клиента: {client_uuid}")
                return client_uuid
            except (ValueError, IndexError):
                print("Найден невалидный UUID. Будет создан новый.")
        
        client_uuid = str(uuid.uuid4())
        try:
            uuid_file.write_text(client_uuid)
            print(f"Создан и сохранен новый UUID клиента: {client_uuid}")
        except IOError as e:
            print(f"Не удалось сохранить UUID клиента: {e}")

        return client_uuid

    def setup_scene(self):
        self.disableMouse()
        cm = CardMaker("ground")
        cm.setFrame(-50, 50, -50, 50)
        ground = self.render.attachNewNode(cm.generate())
        ground.setP(-90)
        ground.setPos(0, 0, -1)

    def update_key_map(self, key, state):
        self.keyMap[key] = state

    def update_movement(self, task):
        if not self.is_connected or not self.player_model or self.is_ingame_menu_open or self.is_chat_open:
            return Task.cont

        dt = globalClock.getDt()
        move_speed = 10.0
        pos = self.player_model.getPos()
        moved = False

        if self.keyMap["w"]: pos.y += move_speed * dt; moved = True
        if self.keyMap["s"]: pos.y -= move_speed * dt; moved = True
        if self.keyMap["a"]: pos.x -= move_speed * dt; moved = True
        if self.keyMap["d"]: pos.x += move_speed * dt; moved = True

        if moved:
            self.player_model.setPos(pos)
            self.asyncio_loop.create_task(
                self.send_message(self.writer, {"type": "move", "pos": [pos.x, pos.y, pos.z]})
            )
        return Task.cont

    # --- UI Callbacks ---
    def open_login_menu(self):
        self.ui.destroy_main_menu()
        self.ui.create_login_menu(default_ip=HOST, default_name=self.character_name)

    def close_login_menu(self):
        self.ui.destroy_login_menu()
        self.ui.create_main_menu()

    def attempt_login(self):
        credentials = self.ui.get_login_credentials()
        host = credentials.get("ip")
        name = credentials.get("name")
        password = credentials.get("password")

        if not all([host, name, password]):
            print("Все поля (IP, Имя, Пароль) должны быть заполнены.")
            # TODO: Показать ошибку в UI
            return
            
        self.character_name = name
        self.temp_password = password # Сохраняем для отправки после подключения
        
        self.ui.destroy_login_menu()
        self.asyncio_loop.create_task(self.connect_and_read(host))

    def open_settings_menu(self):
        self.ui.destroy_main_menu()
        self.ui.create_settings_menu(self.character_name)
    
    # ... (остальные методы без изменений)

    def on_successful_connection(self):
        auth_data = {
            "type": "auth",
            "name": self.character_name,
            "uuid": self.client_uuid,
            "password": self.temp_password # Добавляем пароль
        }
        self.temp_password = None # Очищаем пароль после использования
        
        self.asyncio_loop.create_task(
            self.send_message(self.writer, auth_data)
        )
		
    # ...

        elif msg_type == "auth_failed":
            reason = data.get("reason", "Неизвестная ошибка")
            print(f"Ошибка аутентификации: {reason}")
            # Закрываем соединение. Блок finally в connect_and_read
            # должен будет снова показать главное меню.
            # Для лучшего UX, мы можем сразу показать меню логина.
            self.is_connected = False # Инициируем закрытие
            # Дальнейшая очистка произойдет в finally
            self.ui.destroy_ingame_menu() # на случай если было открыто
            self.open_login_menu() # Показываем меню логина снова
            # TODO: Показать 'reason' в UI
			
	# ... (остальные методы без изменений)
		
		
		

    async def connect_and_read(self, host: str):
        reader, self.writer = None, None
        
        # --- SSL-контекст для клиента ---
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        try:
            # Указываем, что мы доверяем нашему самоподписанному сертификату
            ssl_context.load_verify_locations('certs/cert.pem')
            print("SSL-контекст клиента успешно создан.")
        except FileNotFoundError:
            print("="*50)
            print("КРИТИЧЕСКАЯ ОШИБКА: Файл сертификата 'certs/cert.pem' не найден.")
            print("Клиент не может проверить подлинность сервера.")
            print("="*50)
            self.ui.create_main_menu()
            return
            
        try:
            # При использовании самоподписанного сертификата 'localhost' должен быть и в host,
            # и в server_hostname
            reader, self.writer = await asyncio.open_connection(
                host, PORT, ssl=ssl_context, server_hostname=host
            )
            self.is_connected = True
            print("Успешно установлено TLS-соединение с сервером.")
            self.on_successful_connection() # Отправляем auth данные
            await self.read_messages(reader)
        except ConnectionRefusedError:
            print("В соединении отказано. Сервер запущен?")
            self.ui.create_main_menu()
        except ssl.SSLCertVerificationError:
            print("="*50)
            print("ОШИБКА ПРОВЕРКИ SSL СЕРТИФИКАТА!")
            print(f"Клиент не доверяет сертификату, предоставленному сервером '{host}'.")
            print("Убедитесь, что на клиенте и сервере используются одинаковые сертификаты.")
            print("="*50)
            self.ui.create_main_menu()
        except Exception as e:
            print(f"Ошибка подключения: {e}")
        finally:
            self.is_connected = False
            if self.writer:
                self.writer.close()
                if not self.asyncio_loop.is_closed():
                    await self.writer.wait_closed()
            
            self.ui.clear_chat_lines()
            print("Соединение с сервером закрыто.")
            if self.player_model: self.player_model.removeNode()
            for p in self.other_players.values(): p.removeNode()
            self.other_players.clear()
            self.player_id = -1
            self.ui.create_main_menu()

    async def read_messages(self, reader: asyncio.StreamReader):
        while self.is_connected:
            try:
                header = await reader.readexactly(4)
                msg_len = struct.unpack("!I", header)[0]
                payload = await reader.readexactly(msg_len)
                data = json.loads(payload.decode("utf-8"))
                self.handle_network_data(data)
            except (asyncio.IncompleteReadError, ConnectionResetError):
                self.is_connected = False
            except Exception as e:
                print(f"Ошибка при чтении сообщения: {e}")
                self.is_connected = False

if __name__ == "__main__":

    try:

        import panda3d

    except ImportError:

        print("Ошибка: Panda3D не установлен. Пожалуйста, установите его:")

        print("pip install panda3d")

        sys.exit(1)



    app = GameClient()

    try:

        app.run()

    except SystemExit:

        pass

    finally:

        if app.asyncio_loop.is_running():

            app.asyncio_loop.stop()
