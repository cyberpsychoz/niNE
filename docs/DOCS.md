# Документация по проекту niNE

Этот документ представляет технический обзор архитектуры проекта niNE, его ключевых компонентов и потоков данных.

---

## Ключевая архитектура

Проект использует гибридную архитектуру, сочетающую **Panda3D** для 3D-рендеринга и его менеджер задач с **asyncio** из Python для современной, высокопроизводительной сетевой части.

-   **Менеджер задач Panda3D** используется для основного игрового цикла (`game_loop` на сервере, `update_movement_task` на клиенте), симуляции физики и других покадровых обновлений.
-   **Asyncio** используется для всей сетевой коммуникации, что позволяет серверу эффективно обрабатывать множество одновременных клиентов и обеспечивает неблокирующие сетевые вызовы на стороне клиента.
-   Обе системы интегрированы через специальную задачу (`poll_asyncio`), которая выполняет одну итерацию цикла событий asyncio в рамках игрового цикла Panda3D.

---

## Клиент-серверное взаимодействие

Взаимодействие осуществляется по собственному, зашифрованному с помощью SSL, протоколу на основе JSON.

-   **Транспорт:** Все общение происходит по одному TCP-сокету, защищенному с помощью SSL/TLS. Сервер использует самоподписанный сертификат (`certs/cert.pem` и `certs/key.pem`), который клиент должен иметь для проверки соединения.
-   **Протокол сообщений:** Сообщения отправляются в виде JSON-строк. Для обработки кадрирования сообщений (т.е. чтобы знать, где заканчивается одно сообщение и начинается другое), перед каждой JSON-полезной нагрузкой добавляется 4-байтовый заголовок, содержащий длину этой нагрузки в виде беззнакового целого числа.
-   **Централизованная логика:** Основная логика для отправки и получения этих сообщений с префиксом длины централизована в модуле `nine.core.network`, который используется всеми клиентами.

---

## Сервер (`GameServer`)

**Файл:** `nine/server/game_server.py`

Сервер является авторитетным источником истины для игрового мира. Он управляет состоянием игры, физикой и всеми взаимодействиями с клиентами.

-   **Обязанности:**
    -   Принятие и управление клиентскими подключениями.
    -   Обработка входящих сообщений (аутентификация, ввод и т.д.).
    -   Выполнение основного игрового цикла (`game_loop`) с фиксированной частотой (`tick_rate`).
    -   Симуляция физического мира (`BulletWorld`).
    -   Рассылка состояния мира всем клиентам.
-   **Аутентификация:**
    -   **`auth`:** Стандартная аутентификация для обычных клиентов. Сервер предотвращает вход нескольких клиентов под одним и тем же именем.
    -   **`dev_auth`:** Специальный путь аутентификации для клиентов разработки. Если в `server_config.json` установлено `allow_dev_client: true`, сервер обходит проверку на уникальность имени, позволяя подключаться нескольким dev-клиентам для тестирования.

---

## Клиенты

### 1. Основной игровой клиент (`client.py`)

Это основной клиент, с которым взаимодействует пользователь.

-   **Класс:** `GameClient`
-   **Функциональность:**
    -   Предоставляет полный пользовательский интерфейс (главное меню, экран входа, настройки и т.д.), управляемый `UIManager`.
    -   В стандартном режиме действует как "глупый" клиент: он захватывает необработанный ввод с клавиатуры (`w`, `a`, `s`, `d`) и отправляет его на сервер через сообщение `input`. Затем сервер симулирует движение и отправляет новую позицию обратно в широковещательном сообщении `world_state`.
    -   **Режим разработки:** Может быть запущен в режиме разработки с помощью флага `--dev`. В этом режиме он ведет себя аналогично `DevGameClient`.

### 2. Клиент для разработки (`dev_client.py`)

Это отдельный, упрощенный клиент для быстрой разработки и тестирования.

-   **Класс:** `DevGameClient`
-   **Функциональность:**
    -   Не имеет главного меню; он автоматически подключается к указанному хосту/порту при запуске.
    -   Всегда использует `dev_auth`.
    -   Использует **предсказание на стороне клиента (client-side prediction)**. Он самостоятельно рассчитывает свое движение на основе ввода игрока каждый кадр и отправляет итоговую позицию на сервер через сообщение `move`. Это обеспечивает более плавный игровой процесс для локального игрока, но делает клиента авторитетным в отношении его собственной позиции. Сервер просто принимает эту позицию и рассылает ее другим клиентам.

---

## Система плагинов (`PluginManager`)

**Файл:** `nine/core/plugins.py`

Проект обладает мощной, событийно-ориентированной системой плагинов, которая позволяет модульно и независимо разрабатывать новый функционал.

-   **Обнаружение:** `PluginManager` автоматически находит и загружает Python-файлы и пакеты из каталога `nine/plugins/`.
-   **Фильтрация:** Каждый класс плагина может иметь атрибут `plugin_type`, который может быть `'client'`, `'server'` или `'common'`. Менеджер загрузит только те плагины, которые соответствуют текущему окружению (например, он не будет загружать плагин типа `'client'` на сервере).
-   **Слабая связанность:** Плагины не ссылаются напрямую на основное приложение или другие компоненты. Вместо этого они общаются с помощью `EventManager`.
    -   **Подписка:** Плагин может `subscribe` на события (например, на тип сетевого сообщения, такой как `"chat_broadcast"`, или на событие UI, такое как `"escape_key_pressed"`).
    -   **Публикация:** Плагин может `post` собственные события, чтобы инициировать действия в основных системах или других плагинах (например, опубликовать `"client_send_chat_message"`, чтобы клиент отправил сетевой пакет).
-   **Пример:** Плагин `chat_ui.py` слушает сетевое событие `"chat_broadcast"` для отображения сообщений и публикует событие `"client_send_chat_message"`, когда пользователь вводит текст.

---

## Система UI

### UI Backend Selection

Проект поддерживает несколько UI бэкендов, настраиваемых через `config.json`:

```json
{
  "ui_backend": "playwright"  // Рекомендуемый
}
```

| Backend | Статус | Описание |
|---------|--------|----------|
| `playwright` | **Рекомендуемый** | Chromium-based HTML/CSS UI через Playwright |
| `directgui` | Fallback | Нативный Panda3D DirectGUI |

### Playwright UI (Рекомендуемый)

**Файлы:**
- `nine/ui/playwright_manager.py` — Offscreen Chromium рендеринг на текстуру
- `nine/ui/webview_api.py` — Python API для JavaScript вызовов
- `nine/ui/web/` — HTML/CSS/JS assets

**Архитектура:**
```
┌─────────────────────────────────┐
│  Playwright (offscreen browser)  │ ← HTML/CSS UI
│  → Screenshot → Panda3D Texture │
└─────────────────────────────────┘
         ↓ (overlay on)
┌─────────────────────────────────┐
│   Panda3D Window                │ ← 3D rendering
└─────────────────────────────────┘
```

**Структура web/:**
```
nine/ui/web/
├── index.html              # Root HTML
├── css/
│   ├── theme.css          # BG1-style тема
│   ├── main.css           # Layout
│   ├── components.css     # UI компоненты
│   └── animations.css     # Анимации
├── js/
│   ├── api.js             # Python API wrapper
│   ├── router.js          # SPA router
│   └── components/        # JS компоненты
└── templates/             # HTML templates
```

**JavaScript → Python:**
```javascript
await PythonAPI.getApi().exit_game()
await PythonAPI.getApi().attempt_login(ip, name, password)
await PythonAPI.getApi().send_chat_message(msg)
```

**Python → JavaScript:**
```python
ui_manager.send_to_js("navigate", {"screen": "main-menu"})
ui_manager.send_to_js("chat_message", {"sender": "Bob", "text": "Hello"})
```

### DirectGUI Fallback

При `"ui_backend": "directgui"` используется старая система:

**Файлы:**
- `nine/ui/manager.py` — UIManager с состояниями
- `nine/ui/base_component.py` — BaseUIComponent базовый класс
- `nine/ui/blocks_v2.py` — Декларативный layout (CSS-like)

**Игровые состояния (GameState):**
```python
class GameState(Enum):
    MENU = auto()        # Главное меню, логин, настройки
    CONNECTING = auto()  # Процесс подключения
    IN_GAME = auto()     # В игре
```

#### DnD Plugin UI (nine/plugins/dnd/)

| Файл | Назначение |
|------|------------|
| `cl_character_select_ui.py` | Выбор персонажа |
| `cl_character_create_ui.py` | Создание персонажа |

#### Combat Plugin UI (nine/plugins/combat/)

| Файл | Назначение |
|------|------------|
| `cl_combat_ui.py` | Главный UI боя |
| `cl_action_bar.py` | Панель действий (атака, заклинания) |
| `cl_initiative_display.py` | Отображение инициативы |
| `cl_spectator_mode.py` | Режим наблюдателя |
| `cl_target_selector.py` | Выбор цели |

---

## Конфигурация

Проект использует четкое разделение между конфигурацией клиента и сервера.

-   **`config.json`:** Содержит настройки на стороне клиента, такие как никнейм, разрешение и чувствительность камеры. Его читают только клиенты.
-   **`server_config.json`:** Содержит настройки на стороне сервера, такие как хост, порт, частота тиков и флаг `allow_dev_client`. **Этот файл никогда не должен читаться клиентом.** Это разделение было ключевой частью недавнего архитектурного рефакторинга.

---

## Физическая система

### Bullet Physics

Проект использует **Bullet Physics** через интеграцию Panda3D (`panda3d.bullet`) для симуляции физики на сервере.

**Файлы:**
- `nine/core/character_controller.py` — контроллер персонажа
- `nine/core/world.py` — игровой мир и коллизия карты
- `nine/server/game_server.py` — физический мир и игровой цикл

### Физика персонажа

Персонажи используют `BulletCharacterControllerNode` — специализированный контроллер для игровых персонажей:

```python
# Создание капсулы коллизии
shape = BulletCapsuleShape(radius=0.4, height=1.8 - 0.8, up=ZUp)
character_node = BulletCharacterControllerNode(shape, step_height=0.4, name='Player')

# Настройка гравитации и прыжка
character_node.setGravity(50.0)
character_node.setFallSpeed(100.0)
character_node.setMaxJumpHeight(2.0)
character_node.setJumpSpeed(12.0)
```

**Важные особенности:**
- `BulletCharacterControllerNode` имеет **собственную гравитацию**, независимую от `BulletWorld.setGravity()`
- Маска коллизии должна быть установлена: `character_np.setCollideMask(BitMask32.allOn())`
- Движение задаётся через `setLinearMovement(velocity, is_local=False)` — параметр `is_local` должен быть `False` для мировых координат

### Коллизия карты

Геометрия карты автоматически преобразуется в коллизионный меш:

```python
mesh = BulletTriangleMesh()
for geom_node_path in map_model.findAllMatches("**/+GeomNode"):
    geom_node = geom_node_path.node()
    for i in range(geom_node.getNumGeoms()):
        geom = geom_node.getGeom(i)
        mesh.addGeom(geom, True, transform)

shape = BulletTriangleMeshShape(mesh, dynamic=False)
map_body = BulletRigidBodyNode('MapCollision')
map_body.addShape(shape)
map_np.setCollideMask(BitMask32.allOn())
```

### Игровой цикл и delta time

**Критически важно для headless-режима сервера:**

В headless-режиме (без окна) `globalClock.getDt()` может возвращать некорректные значения (~0) после первого кадра. Решение:

```python
from panda3d.core import ClockObject
globalClock = ClockObject.getGlobalClock()

def game_loop(self, task):
    dt = globalClock.getDt()

    # Исправление для headless-режима
    if dt < 0.001:
        dt = 1.0 / self.tick_rate

    # Ограничение максимального dt (защита от "взрывов" физики)
    if dt > 0.1:
        dt = 0.1

    # Симуляция физики с substeps
    self.physics_world.doPhysics(dt, maxSubSteps=10, fixedTimeStep=1.0/60.0)
```

### Порядок обновления

1. Обработка сетевых сообщений
2. Обновление состояния игроков (`world.update(dt)`)
3. Симуляция физики (`physics_world.doPhysics(dt)`)
4. Рассылка состояния мира клиентам

---

## Боевая система (Combat)

**Плагин:** `nine.combat` (`nine/plugins/combat/`)

Пошаговая боевая система в стиле D&D 5e / Baldur's Gate 3.

### Архитектура

```
combat/
├── sh_plugin.py           # Общий плагин (регистрация)
├── sh_dice.py             # Система бросков кубов
├── sh_action_economy.py   # Экономика действий D&D
├── sv_plugin.py           # Серверный модуль
├── sv_combat_manager.py   # Менеджер боёв
├── sv_turn_manager.py     # Управление ходами
├── cl_combat_ui.py        # Главный UI боя
├── cl_initiative_display.py  # Панель инициативы (слева)
├── cl_action_bar.py       # Панель действий (внизу)
├── cl_target_selector.py  # Выбор целей курсором
└── cl_spectator_mode.py   # Режим наблюдателя
```

### Ключевые компоненты

- **CombatManager** - управляет боевыми сессиями, участниками
- **TurnManager** - валидация и выполнение действий
- **DiceRoller** - парсинг и бросок кубов (`2d6+3`, `d20`)

### Боевой цикл

1. DM начинает бой командой `/startcombat [radius]`
2. Сервер собирает участников, бросает инициативу
3. Отправляет `combat_started` всем клиентам
4. По очереди ходов отправляет `combat_turn_start`
5. Игрок выбирает действие, клиент отправляет `combat_action`
6. Сервер валидирует, выполняет, отправляет `combat_action_result`
7. Бой заканчивается победой/поражением/командой DM

---

## Система NPC

**Плагин:** `nine.npc` (`nine/plugins/npc/`)

ECS-based система NPC с AI и интеграцией в боевую систему.

### Архитектура

```
npc/
├── sh_plugin.py        # Общий плагин
├── sh_components.py    # ECS компоненты (Position, AI, Combat, Faction...)
├── sv_plugin.py        # Серверный модуль
├── sv_npc_manager.py   # Менеджер NPC (спавн, деспавн, синхронизация)
├── sv_npc_ai.py        # AI системы (патруль, агрессия, преследование)
└── cl_npc_renderer.py  # Клиентский рендерер (модели, имена, HP)
```

### Компоненты NPC

- **PositionComponent** - позиция в мире (x, y, z, rotation)
- **ModelComponent** - 3D модель и анимации
- **AIComponent** - поведение AI (IDLE, PATROL, HOSTILE, PURSUING)
- **CombatComponent** - боевые характеристики (HP, AC, атака)
- **FactionComponent** - фракция (враждебность к игрокам)
- **NPCInfoComponent** - имя, тип, описание

### AI состояния

- **IDLE** - стоит на месте
- **PATROL** - патрулирует между точками
- **HOSTILE** - агрессивен, ищет цели
- **PURSUING** - преследует цель
- **ATTACKING** - атакует (в бою)

### Спавн NPC

```
/spawn goblin 10 5 0        # Спавн гоблина в точке (10, 5, 0)
/spawn orc                   # Спавн орка в позиции DM
/despawn abc123              # Удалить NPC по ID
```

---

## Аудио система

**Файлы:**
- `nine/core/audio_manager.py` - AudioManager
- `nine/plugins/dnd/audio/` - интеграция с игровыми событиями

### AudioManager

Управляет всеми звуками в игре:

```python
audio = AudioManager(base)

# Фоновая музыка
audio.play_bgm("combat", crossfade=1.5)  # С плавным переходом
audio.stop_bgm()

# Ambient звуки
audio.set_ambient("forest_day")
audio.stop_ambient()

# Звуковые эффекты
audio.play_sfx("sword_hit", volume=0.8, pitch_variance=0.1)

# Шаги
audio.play_footstep("stone", is_running=True, has_chain_armor=False)
```

### Плейлисты

- **BGM:** adventure, combat, tavern, town, dungeon
- **Ambient:** forest_day, forest_night, dungeon, town
- **SFX:** sword_attack, sword_hit, sword_blocked, sword_unsheath

### Интеграция с событиями

AudioIntegration автоматически реагирует на:
- `combat_started` / `combat_ended` - переключение на боевую музыку
- `combat_action_result` - звуки атак
- `player_jump` / `player_land` - звуки прыжка/приземления