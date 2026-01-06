# Туториал: Создание первого плагина для niNE

## Введение

В этом туториале мы создадим простой плагин **"Welcome System"**, который будет:
- Приветствовать игроков при входе
- Показывать приветственное сообщение на экране
- Подсчитывать количество подключений

Этот туториал покажет основы работы с системой плагинов niNE.

---

## Что мы будем изучать

1. ✅ Структура плагина
2. ✅ Создание метаданных (sh_plugin.py)
3. ✅ Серверный модуль (обработка событий)
4. ✅ Клиентский модуль (UI)
5. ✅ Взаимодействие через EventManager
6. ✅ Тестирование плагина

**Время выполнения**: ~20 минут

---

## Шаг 1: Создание структуры плагина

### 1.1 Создайте папку плагина

```bash
cd D:\Projects\niNE
mkdir plugins\welcome
cd plugins\welcome
```

### 1.2 Создайте файлы

Создайте три файла:
- `sh_plugin.py` - метаданные плагина
- `sv_welcome.py` - серверная логика
- `cl_ui.py` - клиентский UI

```
plugins/welcome/
    sh_plugin.py
    sv_welcome.py
    cl_ui.py
```

---

## Шаг 2: Настройка метаданных (sh_plugin.py)

Откройте `sh_plugin.py` и добавьте:

```python
"""
Welcome System Plugin
Приветствует игроков при входе на сервер
"""
from nine.core.plugins import PluginInfo

# ОБЯЗАТЕЛЬНАЯ переменная - метаданные плагина
PLUGIN_INFO = PluginInfo(
    unique_id="welcome.system",          # Уникальный ID плагина
    name="Welcome System",               # Отображаемое имя
    description="Система приветствия игроков",
    author="YourName",                   # Ваше имя
    version="1.0.0",                     # Версия плагина
    dependencies=[],                     # Нет зависимостей
    load_order=50,                       # Стандартный порядок загрузки
    enabled=True,                        # Плагин включен
)

def on_plugin_load(context):
    """
    Вызывается после загрузки всех модулей плагина.
    Используется для инициализации общих данных.
    """
    context.logger.info(f"✅ {PLUGIN_INFO.name} v{PLUGIN_INFO.version} загружен!")

    # Инициализируем счетчик подключений в shared_data
    context.shared_data["total_connections"] = 0
```

**Что здесь происходит?**
- `PLUGIN_INFO` - обязательная переменная с метаданными
- `on_plugin_load()` - опциональная функция, вызывается после загрузки
- `context.shared_data` - общий словарь для всех модулей плагина

---

## Шаг 3: Серверная логика (sv_welcome.py)

Откройте `sv_welcome.py` и добавьте:

```python
"""
Серверный модуль системы приветствия.
Обрабатывает события подключения игроков.
"""
from nine.core.plugins import PluginModule

class WelcomeServerModule(PluginModule):
    """
    Серверный модуль обрабатывает подключения игроков
    и отправляет приветственные сообщения.
    """

    def on_load(self):
        """
        Вызывается при загрузке модуля.
        Здесь мы подписываемся на события.
        """
        self.logger.info("🔧 Серверный модуль Welcome загружен")

        # Подписываемся на событие "player_joined"
        self.event_manager.subscribe("player_joined", self.on_player_joined)

    def on_unload(self):
        """
        Вызывается при выгрузке модуля.
        Обязательно отписываемся от событий!
        """
        self.event_manager.unsubscribe("player_joined", self.on_player_joined)
        self.logger.info("🔧 Серверный модуль Welcome выгружен")

    def on_player_joined(self, data: dict):
        """
        Обработчик события player_joined.

        Args:
            data (dict): Данные события
                - id: ID игрока
                - name: Имя игрока
                - pos: Позиция спавна
        """
        player_id = data.get("id")
        player_name = data.get("name", "Unknown")

        # Увеличиваем счетчик подключений
        self.context.shared_data["total_connections"] += 1
        total = self.context.shared_data["total_connections"]

        self.logger.info(f"👤 Игрок {player_name} (ID: {player_id}) присоединился!")
        self.logger.info(f"📊 Всего подключений: {total}")

        # Формируем приветственное сообщение
        welcome_message = f"Добро пожаловать, {player_name}! Вы {total}-й посетитель сервера."

        # Отправляем сообщение в чат ВСЕМ игрокам
        self.event_manager.post("chat_send_to_clients", {
            "data": {
                "type": "system",
                "sender": "Система",
                "message": welcome_message,
                "color": (0.3, 1.0, 0.3, 1.0)  # Зеленый цвет
            },
            "recipients": None  # None = всем клиентам
        })

        # Отправляем персональное приветствие только новому игроку
        self.event_manager.post("welcome_send_to_client", {
            "client_id": player_id,
            "data": {
                "message": f"Привет, {player_name}!",
                "connection_number": total
            }
        })
```

**Что здесь происходит?**
1. Создаем класс `WelcomeServerModule`, наследующий `PluginModule`
2. В `on_load()` подписываемся на событие `player_joined`
3. В `on_player_joined()` обрабатываем подключение:
   - Увеличиваем счетчик
   - Логируем информацию
   - Отправляем сообщение в чат всем игрокам
   - Отправляем персональное приветствие новому игроку

---

## Шаг 4: Клиентский UI (cl_ui.py)

Откройте `cl_ui.py` и добавьте:

```python
"""
Клиентский модуль системы приветствия.
Отображает приветственное сообщение на экране.
"""
from nine.core.plugins import PluginModule
from direct.gui.DirectGui import DirectFrame, DirectLabel

class WelcomeUIModule(PluginModule):
    """
    Клиентский модуль отображает UI приветствия.
    """

    def on_load(self):
        """
        Инициализация клиентского модуля.
        Создаем UI и подписываемся на события.
        """
        self.logger.info("🎨 Клиентский UI модуль Welcome загружен")

        # Подписываемся на событие от сервера
        self.event_manager.subscribe("welcome_update", self.on_welcome_received)

        # Создаем UI элементы
        self.create_welcome_ui()

    def on_unload(self):
        """
        Очистка ресурсов при выгрузке.
        """
        # Удаляем UI
        if hasattr(self, 'welcome_frame') and self.welcome_frame:
            self.welcome_frame.destroy()

        # Удаляем задачу скрытия если есть
        if self.app.taskMgr.hasTaskNamed("hide-welcome"):
            self.app.taskMgr.remove("hide-welcome")

        # Отписываемся от событий
        self.event_manager.unsubscribe("welcome_update", self.on_welcome_received)

        self.logger.info("🎨 Клиентский UI модуль Welcome выгружен")

    def create_welcome_ui(self):
        """
        Создание UI элементов приветствия.
        """
        # Создаем фрейм (контейнер)
        self.welcome_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.1, 0.8),  # Темный полупрозрачный фон
            frameSize=(-0.8, 0.8, -0.2, 0.2),  # Ширина и высота
            pos=(0, 0, 0.5),  # Позиция (центр верхней части экрана)
        )

        # Создаем текстовую метку внутри фрейма
        self.welcome_label = DirectLabel(
            text="",  # Изначально пусто
            parent=self.welcome_frame,  # Родитель - наш фрейм
            scale=0.08,  # Размер текста
            pos=(0, 0, 0.05),  # Позиция относительно фрейма
            text_fg=(1, 1, 0.5, 1),  # Цвет текста (желтоватый)
            text_shadow=(0, 0, 0, 1),  # Тень текста (черная)
            text_shadowOffset=(0.05, 0.05),  # Смещение тени
        )

        # Метка с номером подключения
        self.connection_label = DirectLabel(
            text="",
            parent=self.welcome_frame,
            scale=0.06,
            pos=(0, 0, -0.05),
            text_fg=(0.8, 0.8, 0.8, 1),
            text_shadow=(0, 0, 0, 1),
            text_shadowOffset=(0.05, 0.05),
        )

        # Скрываем UI по умолчанию
        self.welcome_frame.hide()

    def on_welcome_received(self, data: dict):
        """
        Обработчик события welcome_update от сервера.

        Args:
            data (dict): Данные приветствия
                - message: Приветственное сообщение
                - connection_number: Номер подключения
        """
        message = data.get("message", "Добро пожаловать!")
        connection_number = data.get("connection_number", 0)

        self.logger.info(f"📨 Получено приветствие: {message}")

        # Обновляем текст
        self.welcome_label["text"] = message
        self.connection_label["text"] = f"Подключение #{connection_number}"

        # Показываем UI
        self.welcome_frame.show()

        # Скрываем через 5 секунд
        self.app.taskMgr.doMethodLater(
            5.0,  # Через 5 секунд
            self.hide_welcome_ui,  # Вызвать эту функцию
            "hide-welcome"  # Имя задачи
        )

    def hide_welcome_ui(self, task=None):
        """
        Скрывает UI приветствия.
        """
        if self.welcome_frame:
            self.welcome_frame.hide()
            self.logger.info("👋 Приветствие скрыто")

        return task.done if task else None
```

**Что здесь происходит?**
1. Создаем класс `WelcomeUIModule` для клиентского UI
2. В `create_welcome_ui()` создаем DirectGUI элементы:
   - `DirectFrame` - контейнер с фоном
   - `DirectLabel` - текстовые метки
3. В `on_welcome_received()` обрабатываем данные от сервера:
   - Обновляем текст
   - Показываем UI
   - Планируем скрытие через 5 секунд

---

## Шаг 5: Регистрация серверного события

Чтобы сервер мог отправлять событие `welcome_send_to_client`, нам нужно зарегистрировать обработчик.

Откройте `nine/server/game_server.py` и найдите `__init__`. Добавьте подписку:

```python
# В методе __init__ после других подписок
self.event_manager.subscribe("welcome_send_to_client", self.handle_welcome_send)
```

Затем добавьте метод обработчик:

```python
async def handle_welcome_send(self, data: dict):
    """Отправка приветствия клиенту"""
    client_id = data.get("client_id")
    welcome_data = data.get("data", {})

    message = {
        "type": "welcome_update",
        **welcome_data
    }

    if client_id is not None and client_id in self.clients:
        writer = self.clients[client_id]["writer"]
        await send_message(writer, message)
    else:
        # Отправить всем клиентам
        for client_id, client_info in self.clients.items():
            writer = client_info["writer"]
            await send_message(writer, message)
```

---

## Шаг 6: Тестирование плагина

### 6.1 Запустите сервер

```bash
cd D:\Projects\niNE
python server.py
```

Вы должны увидеть в логах:

```
✅ Welcome System v1.0.0 загружен!
🔧 Серверный модуль Welcome загружен
```

### 6.2 Запустите клиент

```bash
python client.py
```

После подключения вы должны увидеть:
1. В логах сервера:
   ```
   👤 Игрок YourName (ID: 123) присоединился!
   📊 Всего подключений: 1
   ```

2. В чате (на клиенте):
   ```
   [Система] Добро пожаловать, YourName! Вы 1-й посетитель сервера.
   ```

3. На экране (вверху по центру):
   ```
   ┌────────────────────────────────────────┐
   │      Привет, YourName!                 │
   │      Подключение #1                    │
   └────────────────────────────────────────┘
   ```

Через 5 секунд приветствие исчезнет.

### 6.3 Подключите второго клиента

Запустите еще один клиент. Вы должны увидеть:
- Второй клиент видит "Подключение #2"
- Первый клиент видит сообщение в чате о втором игроке

---

## Шаг 7: Расширение функционала (опционально)

### 7.1 Добавьте конфигурацию

Создайте `sh_config.py`:

```python
"""
Конфигурация плагина Welcome
"""

# Цвет приветственного сообщения (RGBA)
WELCOME_COLOR = (0.3, 1.0, 0.3, 1.0)

# Время отображения приветствия (секунды)
WELCOME_DISPLAY_TIME = 5.0

# Шаблон сообщения
MESSAGE_TEMPLATE = "Добро пожаловать, {player_name}! Вы {number}-й посетитель."
```

Затем используйте в `sv_welcome.py`:

```python
from .sh_config import WELCOME_COLOR, MESSAGE_TEMPLATE

# В on_player_joined:
welcome_message = MESSAGE_TEMPLATE.format(
    player_name=player_name,
    number=total
)
```

### 7.2 Добавьте звук приветствия

В `cl_ui.py`:

```python
def on_welcome_received(self, data: dict):
    # ... существующий код ...

    # Воспроизводим звук (если есть файл)
    sound_path = self.plugin_path / "welcome.ogg"
    if sound_path.exists():
        sound = self.app.loader.loadSfx(str(sound_path))
        sound.play()
```

### 7.3 Сохраните статистику в файл

В `sv_welcome.py`:

```python
import json

def on_load(self):
    # ... существующий код ...

    # Загружаем статистику
    self.load_stats()

def load_stats(self):
    """Загрузка статистики из файла"""
    stats_file = self.plugin_path / "stats.json"
    if stats_file.exists():
        with open(stats_file, 'r') as f:
            stats = json.load(f)
            self.context.shared_data["total_connections"] = stats.get("total", 0)

def save_stats(self):
    """Сохранение статистики"""
    stats_file = self.plugin_path / "stats.json"
    stats = {
        "total": self.context.shared_data.get("total_connections", 0)
    }
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)

def on_player_joined(self, data: dict):
    # ... существующий код ...

    # Сохраняем после каждого подключения
    self.save_stats()
```

---

## Что вы изучили

✅ **Структуру плагина** - как организовать файлы
✅ **Метаданные (PLUGIN_INFO)** - как описать плагин
✅ **Серверные модули** - обработка событий на сервере
✅ **Клиентские модули** - создание UI с DirectGUI
✅ **EventManager** - подписка и отправка событий
✅ **Shared Data** - обмен данными между модулями
✅ **Жизненный цикл** - on_load() и on_unload()

---

## Следующие шаги

Теперь, когда вы знаете основы, попробуйте:

1. **Создать плагин статистики** - отслеживание убийств, смертей, времени игры
2. **Создать плагин достижений** - система ачивок
3. **Создать плагин магазина** - покупка предметов за игровую валюту
4. **Создать плагин телепортации** - команды `/tp` и `/home`

Изучите встроенные плагины в `nine/plugins/` для вдохновения!

---

## Полезные ресурсы

- [Полная документация по плагинам](PLUGINS.md)
- [Справочник Event API](EVENT_API.md)
- [Документация Panda3D](https://docs.panda3d.org/)
- [DirectGUI Reference](https://docs.panda3d.org/1.10/python/programming/gui/directgui/index)

---

## Устранение проблем

### Плагин не загружается

**Проверьте**:
1. Есть ли файл `sh_plugin.py`?
2. Есть ли переменная `PLUGIN_INFO`?
3. `enabled=True`?
4. Нет ли ошибок в логах?

### События не работают

**Проверьте**:
1. Подписались ли вы на событие в `on_load()`?
2. Правильно ли имя события?
3. Есть ли обработчик на другой стороне (клиент/сервер)?

### UI не отображается

**Проверьте**:
1. UI файл назван `cl_*.py`? (не `sv_*`!)
2. Вызвали ли вы `.show()` на фрейме?
3. Правильная ли позиция и размер?

---

**Поздравляем! Вы создали свой первый плагин для niNE!** 🎉
