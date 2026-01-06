# Документация по системе плагинов niNE

## Содержание

1. [Введение](#введение)
2. [Архитектура системы](#архитектура-системы)
3. [Структура плагина](#структура-плагина)
4. [Создание плагина](#создание-плагина)
5. [Event API](#event-api)
6. [Типы модулей](#типы-модулей)
7. [Жизненный цикл плагина](#жизненный-цикл-плагина)
8. [Зависимости и порядок загрузки](#зависимости-и-порядок-загрузки)
9. [Примеры](#примеры)
10. [Справочник API](#справочник-api)

---

## Введение

**niNE Plugin System** — модульная система расширения функционала игры, вдохновленная архитектурой **Garry's Mod Helix**. Система поддерживает:

- ✅ Разделение на клиентский и серверный код
- ✅ Систему событий для взаимодействия между компонентами
- ✅ Автоматическую загрузку и управление зависимостями
- ✅ Горячую перезагрузку плагинов без перезапуска сервера
- ✅ Изолированный контекст выполнения для каждого плагина

---

## Архитектура системы

### Основные компоненты

```
┌─────────────────────────────────────────────┐
│         GameServer / GameClient             │
├─────────────────────────────────────────────┤
│  ┌────────────────┐  ┌──────────────────┐  │
│  │ PluginManager  │  │  EventManager    │  │
│  └────────┬───────┘  └────────┬─────────┘  │
│           │                   │             │
│  ┌────────▼───────────────────▼──────────┐  │
│  │         Plugin Modules                │  │
│  │  ┌─────────┐  ┌─────────┐            │  │
│  │  │ Shared  │  │ Client/ │            │  │
│  │  │ Modules │  │ Server  │            │  │
│  │  └─────────┘  └─────────┘            │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### PluginManager

Главный менеджер плагинов, который:
- Обнаруживает плагины в папках `nine/plugins/` и `plugins/`
- Загружает метаданные из `sh_plugin.py`
- Сортирует плагины по зависимостям и `load_order`
- Создает контекст для каждого плагина
- Загружает модули и вызывает хуки жизненного цикла

### EventManager

Система событий для асинхронного взаимодействия:
- Подписка на события: `event_manager.subscribe(event_type, callback)`
- Отправка событий: `event_manager.post(event_type, data)`
- Отписка от событий: `event_manager.unsubscribe(event_type, callback)`

### PluginContext

Контекст выполнения, передаваемый в каждый модуль плагина:

```python
@dataclass
class PluginContext:
    app: Any                      # GameClient или GameServer
    event_manager: EventManager   # Менеджер событий
    plugin_info: PluginInfo       # Метаданные плагина
    plugin_path: Path             # Путь к папке плагина
    is_server: bool               # True для серверных модулей
    shared_data: Dict[str, Any]   # Общие данные между модулями плагина
    logger: logging.Logger        # Логгер плагина
```

---

## Структура плагина

### Минимальная структура

```
plugins/my_plugin/
    sh_plugin.py          # ОБЯЗАТЕЛЬНЫЙ - Точка входа и метаданные
```

### Полная структура

```
plugins/my_plugin/
    sh_plugin.py          # Метаданные плагина
    sh_config.py          # Общая конфигурация (опционально)
    sh_utils.py           # Общие утилиты (опционально)

    cl_ui.py              # Клиентский UI модуль
    cl_renderer.py        # Клиентский рендеринг

    sv_logic.py           # Серверная логика
    sv_database.py        # Серверная БД

    entities/             # Папка с Entity классами (для inventory)
        base.py
        item_1.py
```

### Именование файлов

| Префикс | Описание | Загружается где |
|---------|----------|-----------------|
| `sh_*`  | **Sh**ared (общие) модули | И на клиенте, и на сервере |
| `cl_*`  | **Cl**ient (клиентские) модули | Только на клиенте |
| `sv_*`  | **S**er**v**er (серверные) модули | Только на сервере |

---

## Создание плагина

### Шаг 1: Создайте папку плагина

```bash
mkdir plugins/my_plugin
cd plugins/my_plugin
```

### Шаг 2: Создайте sh_plugin.py

```python
"""
My Plugin - Описание плагина
"""
from nine.core.plugins import PluginInfo

# ОБЯЗАТЕЛЬНАЯ переменная PLUGIN_INFO
PLUGIN_INFO = PluginInfo(
    unique_id="my.plugin",              # Уникальный ID (формат: author.name)
    name="My Plugin",                   # Человекочитаемое имя
    description="Описание плагина",     # Описание функционала
    author="YourName",                  # Автор
    version="1.0.0",                    # Версия
    dependencies=[],                    # Список зависимостей (unique_id других плагинов)
    load_order=50,                      # Порядок загрузки (10-100)
    enabled=True,                       # Включен ли плагин
)

# ОПЦИОНАЛЬНАЯ функция on_plugin_load
def on_plugin_load(context):
    """
    Вызывается после загрузки всех модулей плагина.

    Args:
        context (PluginContext): Контекст выполнения плагина
    """
    context.logger.info(f"{PLUGIN_INFO.name} загружен!")
```

### Шаг 3: Создайте модули (опционально)

#### Серверный модуль (sv_logic.py)

```python
from nine.core.plugins import PluginModule

class MyServerModule(PluginModule):
    """Серверная логика плагина"""

    def on_load(self):
        """Вызывается при загрузке модуля"""
        self.logger.info("Серверный модуль загружен")

        # Подписываемся на события
        self.event_manager.subscribe("player_joined", self.on_player_join)

    def on_unload(self):
        """Вызывается при выгрузке модуля"""
        # Отписываемся от событий
        self.event_manager.unsubscribe("player_joined", self.on_player_join)

    def on_player_join(self, data: dict):
        """Обработчик события player_joined"""
        player_id = data.get("id")
        self.logger.info(f"Игрок {player_id} присоединился")

        # Отправляем событие другим плагинам
        self.event_manager.post("my_custom_event", {"player": player_id})
```

#### Клиентский модуль (cl_ui.py)

```python
from nine.core.plugins import PluginModule
from direct.gui.DirectGui import DirectFrame, DirectLabel

class MyUIModule(PluginModule):
    """Клиентский UI модуль"""

    def on_load(self):
        """Вызывается при загрузке модуля"""
        self.ui_frame = None

        # Подписываемся на события
        self.event_manager.subscribe("game_state_changed", self.on_game_state_changed)

        # Создаем UI
        self.create_ui()

    def on_unload(self):
        """Вызывается при выгрузке модуля"""
        if self.ui_frame:
            self.ui_frame.destroy()
        self.event_manager.unsubscribe("game_state_changed", self.on_game_state_changed)

    def create_ui(self):
        """Создание UI элементов"""
        self.ui_frame = DirectFrame(
            frameColor=(0, 0, 0, 0.5),
            frameSize=(-0.5, 0.5, -0.3, 0.3),
            pos=(0, 0, 0)
        )

        DirectLabel(
            text="My Plugin UI",
            parent=self.ui_frame,
            scale=0.07,
            pos=(0, 0, 0)
        )

        self.ui_frame.hide()

    def on_game_state_changed(self, data: dict):
        """Обработчик смены состояния игры"""
        state = data.get("state")
        if state == "IN_GAME":
            self.ui_frame.show()
        else:
            self.ui_frame.hide()
```

---

## Event API

### Система событий

События — главный способ взаимодействия между плагинами и ядром игры.

### Подписка на событие

```python
def on_load(self):
    self.event_manager.subscribe("event_name", self.callback_method)

def callback_method(self, data: dict):
    """Обработчик события"""
    print(f"Получено событие: {data}")
```

### Отправка события

```python
# Отправить событие
self.event_manager.post("my_event", {
    "key": "value",
    "player_id": 123
})
```

### Отписка от события

```python
def on_unload(self):
    self.event_manager.unsubscribe("event_name", self.callback_method)
```

### Стандартные события

#### События жизненного цикла

| Событие | Когда вызывается | Данные |
|---------|------------------|--------|
| `app_start` | Приложение запущено | `{}` |
| `app_tick` | Каждый тик приложения | `{"dt": float}` |
| `app_stop` | Приложение останавливается | `{}` |
| `game_state_changed` | Смена состояния игры | `{"state": str}` |

#### События подключения

| Событие | Когда вызывается | Данные |
|---------|------------------|--------|
| `client_connected` | Клиент подключился к серверу | `{}` |
| `client_disconnected` | Клиент отключился | `{}` |
| `player_joined` | Игрок присоединился (сервер) | `{"id": int, "name": str, "pos": list}` |
| `player_left` | Игрок покинул сервер | `{"id": int}` |

#### События игрока

| Событие | Когда вызывается | Данные |
|---------|------------------|--------|
| `player_damage` | Игрок получил урон | `{"uuid": str, "damage": float}` |
| `player_heal` | Игрок исцелен | `{"uuid": str, "amount": float}` |
| `player_death` | Игрок умер | `{"uuid": str}` |
| `player_feed` | Восстановление голода | `{"uuid": str, "amount": float}` |

#### События чата

| Событие | Когда вызывается | Данные |
|---------|------------------|--------|
| `chat_message_received` | Сервер получил сообщение | `{"client_id": int, "message": str, "player_name": str}` |
| `chat_broadcast` | Клиент получил сообщение | `{"type": str, "sender": str, "message": str, "color": tuple}` |
| `client_send_chat_message` | Клиент отправляет сообщение | `str` (само сообщение) |

#### События инвентаря

| Событие | Когда вызывается | Данные |
|---------|------------------|--------|
| `give_item` | Выдать предмет игроку | `{"uuid": str, "class_id": str, "count": int}` |
| `item_pickup` | Подбор предмета | `{"uuid": str, "entity_id": int}` |
| `item_drop` | Выброс предмета | `{"uuid": str, "slot": int, "count": int}` |
| `item_use` | Использование предмета | `{"uuid": str, "slot": int}` |
| `inventory_update` | Обновление инвентаря | `{"inventory": list, "max_slots": int}` |
| `inventory_full` | Инвентарь переполнен | `{"uuid": str}` |

#### События мира

| Событие | Когда вызывается | Данные |
|---------|------------------|--------|
| `world_config` | Конфигурация мира получена | `{"map": dict, "lighting": dict, "skybox": dict}` |
| `world_config_send_to_client` | Отправить конфиг клиенту | `{"client_id": int}` |

#### События характеристик

| Событие | Когда вызывается | Данные |
|---------|------------------|--------|
| `stats_update` | Обновление характеристик | `{"health": float, "hunger": float}` |
| `stats_request` | Клиент запросил обновление | `{}` |

### Создание собственных событий

Вы можете создавать и использовать свои события:

```python
# Отправка пользовательского события
self.event_manager.post("my_plugin.custom_event", {
    "custom_data": "value"
})

# Подписка на пользовательское событие
self.event_manager.subscribe("my_plugin.custom_event", self.my_handler)
```

**Рекомендация по именованию**: Используйте формат `plugin_id.event_name` для избежания конфликтов.

---

## Типы модулей

### Shared модули (sh_*.py)

Загружаются **везде** (и на клиенте, и на сервере).

**Используйте для**:
- Общих констант
- Общих утилит
- Конфигурации
- Классов данных

**Пример (sh_config.py)**:

```python
# Общая конфигурация для клиента и сервера
MAX_HEALTH = 100
DEFAULT_SPAWN = (0, 0, 5)
GAME_NAME = "My RPG"
```

**Условная логика**:

```python
from nine.core.plugins import PluginModule

class SharedModule(PluginModule):
    def on_load(self):
        if self.context.is_server:
            # Серверная логика
            print("Загружено на сервере")
        else:
            # Клиентская логика
            print("Загружено на клиенте")
```

### Client модули (cl_*.py)

Загружаются **только на клиенте**.

**Используйте для**:
- UI компонентов (DirectGUI)
- Рендеринга (Panda3D визуализация)
- Клиентских эффектов (частицы, звуки)
- Обработки ввода

**Доступ к Panda3D**:

```python
class MyClientModule(PluginModule):
    def on_load(self):
        # Доступ к ShowBase
        self.app.render          # Сцена рендеринга
        self.app.camera          # Камера
        self.app.taskMgr         # Менеджер задач
        self.app.loader          # Загрузчик ресурсов

        # Создание задачи
        self.app.taskMgr.add(self.update_task, "my-update-task")

    def update_task(self, task):
        # Обновление каждый кадр
        return task.cont
```

### Server модули (sv_*.py)

Загружаются **только на сервере**.

**Используйте для**:
- Игровой логики
- Обработки данных игроков
- Физики и коллизий
- Сохранения/загрузки данных

**Доступ к серверу**:

```python
class MyServerModule(PluginModule):
    def on_load(self):
        # Доступ к серверу
        self.app.world           # GameWorld (физика, игроки)
        self.app.clients         # Подключенные клиенты

        # Отправка данных клиентам
        self.event_manager.post("my_data_send_to_client", {
            "data": {...},
            "recipients": [client_id]  # или None для всех
        })
```

---

## Жизненный цикл плагина

### Порядок вызовов

```
1. Обнаружение плагинов (сканирование папок)
   ↓
2. Загрузка PLUGIN_INFO из sh_plugin.py
   ↓
3. Проверка enabled=True
   ↓
4. Топологическая сортировка (dependencies + load_order)
   ↓
5. Для каждого плагина:
   ├─ Создание PluginContext
   ├─ Загрузка sh_*.py файлов
   ├─ Загрузка cl_*.py или sv_*.py
   ├─ Поиск классов PluginModule
   ├─ Инстанцирование модулей
   ├─ Вызов module.on_load() для каждого модуля
   └─ Вызов on_plugin_load(context) из sh_plugin.py
   ↓
6. Плагины работают...
   ↓
7. Выгрузка (при остановке или reload):
   ├─ Вызов module.on_unload() для каждого модуля
   └─ Очистка ресурсов
```

### Хуки жизненного цикла

#### 1. `on_plugin_load(context)` - в sh_plugin.py

Вызывается **один раз** после загрузки всех модулей плагина.

```python
def on_plugin_load(context):
    """
    Args:
        context (PluginContext): Контекст плагина
    """
    context.logger.info("Плагин загружен!")

    # Инициализация общих данных
    context.shared_data["initialized"] = True
```

#### 2. `module.on_load()` - в каждом модуле

Вызывается при загрузке конкретного модуля.

```python
class MyModule(PluginModule):
    def on_load(self):
        """Инициализация модуля"""
        self.logger.info("Модуль загружен")

        # Подписка на события
        self.event_manager.subscribe("event_name", self.handler)

        # Доступ к shared_data
        self.context.shared_data["module_data"] = {}
```

#### 3. `module.on_unload()` - в каждом модуле

Вызывается при выгрузке модуля (остановка или reload).

```python
class MyModule(PluginModule):
    def on_unload(self):
        """Очистка ресурсов"""
        # Отписка от событий
        self.event_manager.unsubscribe("event_name", self.handler)

        # Удаление UI
        if hasattr(self, 'ui_frame'):
            self.ui_frame.destroy()
```

### Shared Data между модулями

Все модули одного плагина имеют доступ к общему словарю `context.shared_data`:

```python
# В sv_logic.py
class ServerModule(PluginModule):
    def on_load(self):
        self.context.shared_data["player_data"] = {}

# В cl_ui.py
class ClientModule(PluginModule):
    def on_load(self):
        # Доступ к данным серверного модуля
        data = self.context.shared_data.get("player_data")
```

---

## Зависимости и порядок загрузки

### Зависимости (dependencies)

Если ваш плагин требует другой плагин, укажите его в `dependencies`:

```python
PLUGIN_INFO = PluginInfo(
    unique_id="my.advanced_plugin",
    dependencies=["nine.inventory", "nine.stats"],  # Требуются эти плагины
    # ...
)
```

**Поведение**:
- Если зависимость не найдена или отключена, плагин **НЕ загрузится**
- Зависимости загружаются **раньше** текущего плагина
- Система автоматически разрешает цепочки зависимостей

### Порядок загрузки (load_order)

Число от **10 до 100**, определяющее порядок загрузки. Меньше = раньше.

**Рекомендуемые диапазоны**:

| Диапазон | Тип плагина |
|----------|-------------|
| 10-20 | Ядро (world config, базовые системы) |
| 20-30 | Визуальные системы (lighting, skybox) |
| 30-40 | Игровые системы (stats, physics) |
| 40-50 | Высокоуровневая логика (inventory, quests) |
| 50-60 | UI и взаимодействие (chat, menus) |
| 60-100 | Пользовательские плагины |

**Примеры из встроенных плагинов**:

```python
# nine.world_config - загружается первым
load_order=10

# nine.lighting, nine.skybox - зависят от world_config
load_order=20

# nine.stats - игровые системы
load_order=30

# nine.inventory - высокоуровневая логика
load_order=35

# nine.chat - UI и взаимодействие
load_order=40
```

### Алгоритм сортировки

1. Группировка по `load_order` (меньше = раньше)
2. Внутри группы — топологическая сортировка по `dependencies`
3. Обнаружение циклических зависимостей (ошибка загрузки)

---

## Примеры

### Пример 1: Простой плагин уведомлений

**Задача**: Показывать уведомление при входе игрока.

**plugins/notification/sh_plugin.py**:

```python
from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="notification.system",
    name="Notification System",
    description="Показывает уведомления при событиях",
    author="YourName",
    version="1.0.0",
    dependencies=[],
    load_order=50,
    enabled=True,
)
```

**plugins/notification/sv_notify.py**:

```python
from nine.core.plugins import PluginModule

class NotificationServerModule(PluginModule):
    def on_load(self):
        self.event_manager.subscribe("player_joined", self.on_player_join)

    def on_unload(self):
        self.event_manager.unsubscribe("player_joined", self.on_player_join)

    def on_player_join(self, data: dict):
        player_name = data.get("name", "Unknown")

        # Отправляем уведомление всем клиентам
        self.event_manager.post("chat_send_to_clients", {
            "data": {
                "type": "system",
                "message": f"Игрок {player_name} присоединился!",
                "color": (0.5, 1.0, 0.5, 1.0)
            },
            "recipients": None  # Всем
        })
```

### Пример 2: Плагин времени суток

**Задача**: Циклическая смена времени суток с изменением освещения.

**plugins/daycycle/sh_plugin.py**:

```python
from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="daycycle.system",
    name="Day Cycle System",
    description="Система смены дня и ночи",
    author="YourName",
    version="1.0.0",
    dependencies=["nine.lighting"],  # Зависит от освещения
    load_order=25,
    enabled=True,
)
```

**plugins/daycycle/sh_config.py**:

```python
# Длительность дня в секундах
DAY_LENGTH = 600  # 10 минут

# Цвета освещения
DAY_COLOR = (0.9, 0.85, 0.8, 1)
NIGHT_COLOR = (0.2, 0.2, 0.3, 1)
```

**plugins/daycycle/sv_daycycle.py**:

```python
from nine.core.plugins import PluginModule
import time

class DayCycleServerModule(PluginModule):
    def on_load(self):
        self.start_time = time.time()
        self.event_manager.subscribe("app_tick", self.on_tick)

    def on_unload(self):
        self.event_manager.unsubscribe("app_tick", self.on_tick)

    def on_tick(self, data: dict):
        from .sh_config import DAY_LENGTH

        elapsed = time.time() - self.start_time
        day_progress = (elapsed % DAY_LENGTH) / DAY_LENGTH  # 0.0 - 1.0

        # Отправляем обновление времени клиентам каждые 5 секунд
        if int(elapsed) % 5 == 0:
            self.event_manager.post("daycycle_update", {
                "progress": day_progress,
                "is_day": day_progress < 0.5
            })
```

**plugins/daycycle/cl_lighting.py**:

```python
from nine.core.plugins import PluginModule
from panda3d.core import DirectionalLight

class DayCycleLightingModule(PluginModule):
    def on_load(self):
        self.sun_light = None
        self.event_manager.subscribe("daycycle_update", self.on_daycycle_update)

        # Создаем солнце
        self.create_sun()

    def on_unload(self):
        self.event_manager.unsubscribe("daycycle_update", self.on_daycycle_update)
        if self.sun_light:
            self.app.render.clearLight(self.sun_light)

    def create_sun(self):
        from .sh_config import DAY_COLOR

        sun = DirectionalLight("daycycle_sun")
        sun.setColor(DAY_COLOR)
        self.sun_light = self.app.render.attachNewNode(sun)
        self.sun_light.setHpr(45, -45, 0)
        self.app.render.setLight(self.sun_light)

    def on_daycycle_update(self, data: dict):
        from .sh_config import DAY_COLOR, NIGHT_COLOR

        progress = data.get("progress", 0.0)

        # Интерполяция цвета
        if progress < 0.5:
            # День -> Закат
            t = progress * 2
            color = self.lerp_color(DAY_COLOR, NIGHT_COLOR, t)
        else:
            # Ночь -> Рассвет
            t = (progress - 0.5) * 2
            color = self.lerp_color(NIGHT_COLOR, DAY_COLOR, t)

        # Обновляем цвет солнца
        if self.sun_light:
            light = self.sun_light.node()
            light.setColor(color)

    def lerp_color(self, c1, c2, t):
        """Линейная интерполяция цвета"""
        return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(4))
```

### Пример 3: Плагин квестов

**Задача**: Система квестов с серверной логикой и клиентским UI.

**plugins/quests/sh_plugin.py**:

```python
from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="quests.system",
    name="Quest System",
    description="Система заданий и квестов",
    author="YourName",
    version="1.0.0",
    dependencies=["nine.inventory"],  # Награды в инвентарь
    load_order=45,
    enabled=True,
)
```

**plugins/quests/sv_quests.py**:

```python
from nine.core.plugins import PluginModule
from typing import Dict, List

class QuestServerModule(PluginModule):
    def on_load(self):
        # Данные квестов игроков: {player_uuid: [quest_ids]}
        self.player_quests: Dict[str, List[str]] = {}

        self.event_manager.subscribe("player_joined", self.on_player_join)
        self.event_manager.subscribe("quest_start", self.on_quest_start)
        self.event_manager.subscribe("quest_complete", self.on_quest_complete)

    def on_unload(self):
        self.event_manager.unsubscribe("player_joined", self.on_player_join)
        self.event_manager.unsubscribe("quest_start", self.on_quest_start)
        self.event_manager.unsubscribe("quest_complete", self.on_quest_complete)

    def on_player_join(self, data: dict):
        player_uuid = str(data.get("id"))
        self.player_quests[player_uuid] = []

        # Отправляем список квестов
        self._send_quest_list(player_uuid)

    def on_quest_start(self, data: dict):
        player_uuid = data.get("uuid")
        quest_id = data.get("quest_id")

        if quest_id not in self.player_quests.get(player_uuid, []):
            self.player_quests[player_uuid].append(quest_id)
            self._send_quest_list(player_uuid)

            self.logger.info(f"Игрок {player_uuid} начал квест {quest_id}")

    def on_quest_complete(self, data: dict):
        player_uuid = data.get("uuid")
        quest_id = data.get("quest_id")

        if quest_id in self.player_quests.get(player_uuid, []):
            self.player_quests[player_uuid].remove(quest_id)

            # Выдаем награду
            self.event_manager.post("give_item", {
                "uuid": player_uuid,
                "class_id": "n_bucks",
                "count": 100
            })

            self._send_quest_list(player_uuid)
            self.logger.info(f"Игрок {player_uuid} завершил квест {quest_id}")

    def _send_quest_list(self, player_uuid: str):
        """Отправка списка квестов клиенту"""
        self.event_manager.post("quests_send_to_client", {
            "client_id": int(player_uuid),
            "data": {
                "quests": self.player_quests.get(player_uuid, [])
            }
        })
```

**plugins/quests/cl_ui.py**:

```python
from nine.core.plugins import PluginModule
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel

class QuestUIModule(PluginModule):
    def on_load(self):
        self.quests = []
        self.ui_frame = None

        self.event_manager.subscribe("quests_update", self.on_quests_update)
        self.event_manager.subscribe("game_state_changed", self.on_game_state_changed)

        # Клавиша Q для открытия
        self.app.accept("q", self.toggle_ui)

        self.create_ui()

    def on_unload(self):
        if self.ui_frame:
            self.ui_frame.destroy()
        self.event_manager.unsubscribe("quests_update", self.on_quests_update)
        self.event_manager.unsubscribe("game_state_changed", self.on_game_state_changed)

    def create_ui(self):
        """Создание UI квестов"""
        self.ui_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.1, 0.9),
            frameSize=(-0.6, 0.6, -0.8, 0.8),
            pos=(0, 0, 0)
        )

        # Заголовок
        DirectLabel(
            text="Квесты",
            parent=self.ui_frame,
            scale=0.1,
            pos=(0, 0, 0.7),
            text_fg=(1, 1, 1, 1)
        )

        self.ui_frame.hide()

    def toggle_ui(self):
        """Переключение видимости UI"""
        if self.ui_frame.isHidden():
            self.ui_frame.show()
        else:
            self.ui_frame.hide()

    def on_quests_update(self, data: dict):
        """Обновление списка квестов"""
        self.quests = data.get("quests", [])
        # TODO: Обновить UI список

    def on_game_state_changed(self, data: dict):
        """Скрывать UI в меню"""
        if data.get("state") != "IN_GAME":
            self.ui_frame.hide()
```

---

## Справочник API

### PluginInfo

Метаданные плагина (датакласс).

```python
@dataclass
class PluginInfo:
    unique_id: str          # Уникальный ID (формат: author.name)
    name: str               # Человекочитаемое имя
    description: str = ""   # Описание
    author: str = ""        # Автор
    version: str = "1.0.0"  # Версия
    dependencies: List[str] = field(default_factory=list)  # Зависимости
    load_order: int = 50    # Порядок загрузки (10-100)
    enabled: bool = True    # Включен ли плагин
```

### PluginContext

Контекст выполнения плагина.

```python
@dataclass
class PluginContext:
    app: Any                      # GameClient или GameServer
    event_manager: EventManager   # Менеджер событий
    plugin_info: PluginInfo       # Метаданные плагина
    plugin_path: Path             # Путь к папке плагина
    is_server: bool               # True для серверных модулей
    shared_data: Dict[str, Any]   # Общие данные между модулями
    logger: logging.Logger        # Логгер плагина
```

**Свойства**:
- `context.app` - Доступ к GameClient или GameServer
- `context.event_manager` - Система событий
- `context.plugin_info` - Метаданные плагина
- `context.plugin_path` - Path объект папки плагина
- `context.is_server` - True на сервере, False на клиенте
- `context.shared_data` - Словарь для обмена данными между модулями
- `context.logger` - Логгер с префиксом плагина

### PluginModule

Базовый класс для модулей плагина.

```python
class PluginModule:
    def __init__(self, context: PluginContext):
        self.context = context
        self.app = context.app
        self.event_manager = context.event_manager
        self.logger = context.logger
        self.plugin_path = context.plugin_path

    def on_load(self):
        """Вызывается при загрузке модуля"""
        pass

    def on_unload(self):
        """Вызывается при выгрузке модуля"""
        pass
```

**Наследуйте и переопределяйте**:

```python
class MyModule(PluginModule):
    def on_load(self):
        # Ваша логика загрузки
        pass

    def on_unload(self):
        # Ваша логика выгрузки
        pass
```

### EventManager

Менеджер событий.

**Методы**:

```python
# Подписка на событие
event_manager.subscribe(event_type: str, listener: Callable)

# Отправка события
event_manager.post(event_type: str, data: Any)

# Отписка от события
event_manager.unsubscribe(event_type: str, listener: Callable)
```

### PluginManager

Менеджер плагинов (используется ядром).

**Методы**:

```python
# Загрузка всех плагинов
plugin_manager.load_plugins(plugin_dirs=['nine/plugins', 'plugins'])

# Выгрузка всех плагинов
plugin_manager.unload_plugins()

# Перезагрузка конкретного плагина
plugin_manager.reload_plugin(unique_id: str)

# Получение загруженного плагина
plugin_manager.get_plugin(unique_id: str) -> Optional[dict]
```

---

## Лучшие практики

### 1. Используйте префиксы событий

```python
# ✅ Хорошо
self.event_manager.post("my_plugin.custom_event", data)

# ❌ Плохо (может конфликтовать)
self.event_manager.post("custom_event", data)
```

### 2. Всегда отписывайтесь в on_unload

```python
class MyModule(PluginModule):
    def on_load(self):
        self.event_manager.subscribe("event", self.handler)

    def on_unload(self):
        # ✅ Обязательно отписаться!
        self.event_manager.unsubscribe("event", self.handler)
```

### 3. Очищайте ресурсы UI

```python
def on_unload(self):
    if hasattr(self, 'ui_frame') and self.ui_frame:
        self.ui_frame.destroy()  # ✅ Удаляем UI
```

### 4. Используйте logger вместо print

```python
# ✅ Хорошо
self.logger.info("Событие обработано")
self.logger.error("Ошибка!")

# ❌ Плохо
print("Событие обработано")
```

### 5. Проверяйте наличие данных

```python
def on_event(self, data: dict):
    # ✅ Безопасно
    player_id = data.get("player_id")
    if player_id is None:
        self.logger.warning("player_id не найден в событии")
        return

    # ❌ Небезопасно (может вызвать KeyError)
    player_id = data["player_id"]
```

### 6. Используйте shared_data для общих данных

```python
# В одном модуле
self.context.shared_data["config"] = {...}

# В другом модуле того же плагина
config = self.context.shared_data.get("config", {})
```

### 7. Документируйте события

```python
def on_load(self):
    """
    Подписывается на события:
    - player_joined: Обрабатывает вход игрока
    - item_use: Обрабатывает использование предмета

    Отправляет события:
    - my_plugin.data_updated: Когда данные обновлены
    """
    pass
```

---

## Отладка плагинов

### Включение логирования

По умолчанию каждый плагин имеет свой логгер:

```python
self.logger.debug("Отладочное сообщение")
self.logger.info("Информация")
self.logger.warning("Предупреждение")
self.logger.error("Ошибка")
```

### Горячая перезагрузка

```python
# В консоли сервера
plugin_manager.reload_plugin("my.plugin")
```

### Частые ошибки

#### 1. Плагин не загружается

**Причины**:
- Отсутствует `sh_plugin.py`
- Нет переменной `PLUGIN_INFO`
- `enabled=False`
- Отсутствует зависимость
- Ошибка в коде плагина

**Решение**: Проверьте логи сервера/клиента.

#### 2. События не работают

**Причины**:
- Не подписались на событие в `on_load()`
- Неправильное имя события
- Отписались слишком рано

**Решение**: Добавьте логирование в обработчик:

```python
def on_event(self, data: dict):
    self.logger.info(f"Получено событие: {data}")
```

#### 3. UI не отображается

**Причины**:
- UI создан, но скрыт (`hide()`)
- Неправильная позиция или размер
- UI создан на сервере вместо клиента

**Решение**: Убедитесь, что UI модуль в `cl_*.py` файле.

---

## FAQ

### Q: Как добавить новый тип предмета?

**A**: Создайте класс в папке `nine/plugins/inventory/entities/`:

```python
# nine/plugins/inventory/entities/my_item.py
from .base import Item

class MyItem(Item):
    CLASS_ID = "my_item"
    NAME = "Мой предмет"
    DESCRIPTION = "Описание предмета"
    CATEGORY = "misc"
    MAX_STACK = 10

    def on_use(self, player_uuid: str) -> bool:
        # Логика использования
        return True  # True = предмет потреблен
```

Плагин inventory автоматически загрузит его.

### Q: Как создать команду для чата?

**A**: Добавьте обработчик в плагин chat или создайте свой:

```python
class MyChatModule(PluginModule):
    def on_load(self):
        self.event_manager.subscribe("chat_message_received", self.on_chat)

    def on_chat(self, data: dict):
        message = data.get("message", "")

        if message.startswith("/mycommand"):
            # Обработка команды
            player_id = data.get("client_id")
            self.logger.info(f"Команда от {player_id}")
```

### Q: Как отправить данные с сервера клиенту?

**A**: Используйте специальные события:

```python
# Сервер
self.event_manager.post("my_data_send_to_client", {
    "client_id": player_id,  # или None для всех
    "data": {"key": "value"}
})

# Нужно зарегистрировать обработчик в GameServer
```

Или используйте существующие события (chat_send_to_clients, stats_send_to_client и т.д.).

### Q: Можно ли использовать базу данных?

**A**: Да! В серверном модуле:

```python
import sqlite3

class MyDBModule(PluginModule):
    def on_load(self):
        db_path = self.plugin_path / "data.db"
        self.conn = sqlite3.connect(str(db_path))
        self.cursor = self.conn.cursor()

        # Создание таблиц
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                uuid TEXT PRIMARY KEY,
                data TEXT
            )
        """)
        self.conn.commit()

    def on_unload(self):
        self.conn.close()
```

### Q: Как добавить задачу, выполняющуюся каждый кадр?

**A**: В клиентском модуле:

```python
class MyClientModule(PluginModule):
    def on_load(self):
        self.app.taskMgr.add(self.update_task, "my-task")

    def on_unload(self):
        self.app.taskMgr.remove("my-task")

    def update_task(self, task):
        # Ваша логика
        return task.cont  # Продолжить выполнение
```

---

## Дополнительные ресурсы

- [Документация Panda3D](https://docs.panda3d.org/)
- [DirectGUI Reference](https://docs.panda3d.org/1.10/python/programming/gui/directgui/index)
- [Примеры встроенных плагинов](../nine/plugins/)

---

**Версия документации**: 1.0.0
**Дата обновления**: 2026-01-06
