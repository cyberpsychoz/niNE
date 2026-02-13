# Справочник Event API

## Содержание

1. [Введение](#введение)
2. [Как использовать события](#как-использовать-события)
3. [События жизненного цикла](#события-жизненного-цикла)
4. [События подключения](#события-подключения)
5. [События игрока](#события-игрока)
6. [События чата](#события-чата)
7. [События инвентаря](#события-инвентаря)
8. [События характеристик](#события-характеристик)
9. [События мира](#события-мира)
10. [События боевой системы](#события-боевой-системы)
11. [События NPC](#события-npc)
12. [События аудио](#события-аудио)
13. [Серверные события отправки](#серверные-события-отправки)
14. [Создание собственных событий](#создание-собственных-событий)

---

## Введение

**EventManager** — центральная система событий в niNE. Все плагины и компоненты взаимодействуют через события, обеспечивая слабую связь и модульность.

### Преимущества

- ✅ Слабая связь между компонентами
- ✅ Легко добавлять новый функционал
- ✅ Плагины не знают друг о друге напрямую
- ✅ Асинхронная обработка

---

## Как использовать события

### Подписка на событие

```python
from nine.core.plugins import PluginModule

class MyModule(PluginModule):
    def on_load(self):
        # Подписываемся на событие
        self.event_manager.subscribe("event_name", self.my_handler)

    def my_handler(self, data: dict):
        """Обработчик события"""
        print(f"Получено событие: {data}")

    def on_unload(self):
        # ОБЯЗАТЕЛЬНО отписываемся при выгрузке!
        self.event_manager.unsubscribe("event_name", self.my_handler)
```

### Отправка события

```python
# Отправка события
self.event_manager.post("event_name", {
    "key": "value",
    "player_id": 123
})
```

### Типы данных

- Данные события могут быть:
  - `dict` - словарь (чаще всего)
  - `str` - строка
  - `int` - число
  - Любой другой тип

---

## События жизненного цикла

### app_start

Приложение запущено (клиент или сервер).

**Когда вызывается**: После инициализации приложения, до загрузки плагинов.

**Данные**: `{}`

**Где слушать**: Любой модуль

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("app_start", self.on_app_start)

def on_app_start(self, data: dict):
    self.logger.info("Приложение запущено!")
```

---

### app_tick

Каждый тик приложения (обновление кадра).

**Когда вызывается**: Каждый кадр (60 FPS на клиенте, 20 TPS на сервере).

**Данные**:
```python
{
    "dt": float  # Время с последнего тика (delta time)
}
```

**Где слушать**: Любой модуль

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("app_tick", self.on_tick)
    self.timer = 0.0

def on_tick(self, data: dict):
    dt = data.get("dt", 0.0)
    self.timer += dt
    if self.timer >= 1.0:  # Каждую секунду
        self.logger.info("Прошла секунда")
        self.timer = 0.0
```

**⚠️ Внимание**: Это событие вызывается ОЧЕНЬ часто. Избегайте тяжелых операций!

---

### app_stop

Приложение останавливается.

**Когда вызывается**: Перед выключением приложения.

**Данные**: `{}`

**Где слушать**: Любой модуль

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("app_stop", self.on_app_stop)

def on_app_stop(self, data: dict):
    # Сохраняем данные перед выключением
    self.save_data()
```

---

### game_state_changed

Смена состояния игры на клиенте.

**Когда вызывается**: При переходе между состояниями (MENU, CONNECTING, IN_GAME).

**Данные**:
```python
{
    "state": str  # "MENU" | "CONNECTING" | "IN_GAME"
}
```

**Где слушать**: Клиентские модули (cl_*.py)

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("game_state_changed", self.on_state_change)

def on_state_change(self, data: dict):
    state = data.get("state")
    if state == "IN_GAME":
        self.ui_frame.show()
    else:
        self.ui_frame.hide()
```

---

## События подключения

### client_connected

Клиент подключился к серверу.

**Когда вызывается**: После установки соединения с сервером.

**Данные**: `{}`

**Где слушать**: Клиентские модули

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("client_connected", self.on_connected)

def on_connected(self, data: dict):
    self.logger.info("Подключение к серверу установлено!")
```

---

### client_disconnected

Клиент отключился от сервера.

**Когда вызывается**: После разрыва соединения.

**Данные**: `{}`

**Где слушать**: Клиентские модули

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("client_disconnected", self.on_disconnected)

def on_disconnected(self, data: dict):
    self.logger.info("Соединение с сервером разорвано")
    # Очищаем кеш, скрываем UI
    self.clear_cache()
```

---

### player_joined

Игрок присоединился к серверу (серверное событие).

**Когда вызывается**: После успешной аутентификации игрока на сервере.

**Данные**:
```python
{
    "id": int,         # ID игрока (клиента)
    "name": str,       # Имя игрока
    "pos": [x, y, z],  # Позиция спавна
    "uuid": str        # UUID игрока (строка)
}
```

**Где слушать**: Серверные модули (sv_*.py)

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("player_joined", self.on_player_join)
    self.player_data = {}

def on_player_join(self, data: dict):
    player_id = data.get("id")
    player_name = data.get("name")

    # Инициализация данных игрока
    self.player_data[player_id] = {
        "name": player_name,
        "joined_at": time.time()
    }

    self.logger.info(f"Игрок {player_name} присоединился!")
```

---

### player_left

Игрок покинул сервер (серверное событие).

**Когда вызывается**: После отключения игрока.

**Данные**:
```python
{
    "id": int  # ID игрока
}
```

**Где слушать**: Серверные модули

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("player_left", self.on_player_leave)

def on_player_leave(self, data: dict):
    player_id = data.get("id")

    # Очищаем данные игрока
    if player_id in self.player_data:
        del self.player_data[player_id]

    self.logger.info(f"Игрок {player_id} покинул сервер")
```

---

## События игрока

### player_damage

Игрок получил урон.

**Когда вызывается**: При получении урона.

**Данные**:
```python
{
    "uuid": str,      # UUID игрока
    "damage": float,  # Количество урона
    "source": str     # Источник урона (опционально)
}
```

**Где слушать**: Серверные модули

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("player_damage", self.on_damage)

def on_damage(self, data: dict):
    player_uuid = data.get("uuid")
    damage = data.get("damage", 0.0)
    source = data.get("source", "unknown")

    self.logger.info(f"Игрок {player_uuid} получил {damage} урона от {source}")
```

---

### player_heal

Игрок исцелен.

**Когда вызывается**: При восстановлении здоровья.

**Данные**:
```python
{
    "uuid": str,      # UUID игрока
    "amount": float   # Количество восстановленного здоровья
}
```

**Где слушать**: Серверные модули

**Пример**:
```python
self.event_manager.post("player_heal", {
    "uuid": player_uuid,
    "amount": 25.0
})
```

---

### player_death

Игрок умер.

**Когда вызывается**: Когда здоровье игрока <= 0.

**Данные**:
```python
{
    "uuid": str  # UUID игрока
}
```

**Где слушать**: Серверные модули

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("player_death", self.on_death)

def on_death(self, data: dict):
    player_uuid = data.get("uuid")
    # Респавн игрока, обнуление статов и т.д.
    self.respawn_player(player_uuid)
```

---

### player_feed / player_restore_hunger

Восстановление голода игрока.

**Когда вызывается**: При потреблении еды.

**Данные**:
```python
{
    "uuid": str,      # UUID игрока
    "amount": float   # Количество восстановленного голода
}
```

**Где слушать**: Серверные модули

**Пример**:
```python
# Отправка события
self.event_manager.post("player_feed", {
    "uuid": player_uuid,
    "amount": 30.0
})
```

---

## События чата

### chat_message_received

Сервер получил сообщение от клиента.

**Когда вызывается**: Когда клиент отправляет сообщение в чат.

**Данные**:
```python
{
    "client_id": int,    # ID клиента
    "message": str,      # Текст сообщения
    "player_name": str   # Имя игрока
}
```

**Где слушать**: Серверные модули

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("chat_message_received", self.on_chat)

def on_chat(self, data: dict):
    client_id = data.get("client_id")
    message = data.get("message", "")
    player_name = data.get("player_name", "Unknown")

    # Обработка команд
    if message.startswith("/"):
        self.handle_command(client_id, message)
    else:
        # Обычное сообщение
        self.broadcast_message(client_id, player_name, message)
```

---

### chat_broadcast

Клиент получил сообщение для отображения в чате.

**Когда вызывается**: Когда сервер отправляет сообщение клиенту.

**Данные**:
```python
{
    "type": str,        # Тип сообщения: "IC", "EMOTE", "IT", "LOOC", "OOC", "SYSTEM"
    "sender": str,      # Имя отправителя
    "message": str,     # Текст сообщения
    "color": tuple,     # Цвет (R, G, B, A)
    "distance": float   # Расстояние до отправителя (опционально)
}
```

**Где слушать**: Клиентские модули

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("chat_broadcast", self.on_chat_message)

def on_chat_message(self, data: dict):
    msg_type = data.get("type")
    sender = data.get("sender")
    message = data.get("message")
    color = data.get("color", (1, 1, 1, 1))

    # Добавляем в UI чата
    self.chat_ui.add_message(sender, message, color, msg_type)
```

---

### client_send_chat_message

Клиент отправляет сообщение на сервер.

**Когда вызывается**: Когда UI чата отправляет сообщение.

**Данные**: `str` (само сообщение)

**Где слушать**: GameClient (уже обрабатывается)

**Пример отправки**:
```python
# В клиентском модуле
def send_message(self, message: str):
    self.event_manager.post("client_send_chat_message", message)
```

---

## События инвентаря

### give_item

Выдать предмет игроку.

**Когда вызывается**: Через команду `/give` или программно.

**Данные**:
```python
{
    "uuid": str,          # UUID игрока
    "class_id": str,      # ID класса предмета (например, "health_potion")
    "count": int,         # Количество (по умолчанию 1)
    "extra_data": dict    # Дополнительные данные (опционально)
}
```

**Где слушать**: Серверные модули (обычно плагин inventory)

**Пример**:
```python
# Выдать предмет
self.event_manager.post("give_item", {
    "uuid": player_uuid,
    "class_id": "health_potion",
    "count": 5
})
```

---

### item_pickup

Подбор предмета из мира.

**Когда вызывается**: Когда игрок поднимает предмет.

**Данные**:
```python
{
    "uuid": str,       # UUID игрока
    "entity_id": int   # ID сущности предмета в мире
}
```

**Где слушать**: Серверные модули

---

### item_drop

Выброс предмета из инвентаря.

**Когда вызывается**: Когда игрок выбрасывает предмет.

**Данные**:
```python
{
    "uuid": str,   # UUID игрока
    "slot": int,   # Номер слота инвентаря
    "count": int   # Количество для выброса
}
```

**Где слушать**: Серверные модули

**Пример (клиентская отправка)**:
```python
# В клиентском модуле
self.event_manager.post("client_item_drop", {
    "slot": slot_index,
    "count": drop_count
})
```

---

### item_use

Использование предмета.

**Когда вызывается**: Когда игрок использует предмет (ПКМ, двойной клик).

**Данные**:
```python
{
    "uuid": str,  # UUID игрока
    "slot": int   # Номер слота инвентаря
}
```

**Где слушать**: Серверные модули

**Пример (клиентская отправка)**:
```python
# В клиентском модуле
self.event_manager.post("client_item_use", {
    "slot": slot_index
})
```

---

### inventory_update

Обновление инвентаря на клиенте.

**Когда вызывается**: Когда сервер отправляет обновленный инвентарь.

**Данные**:
```python
{
    "inventory": list,    # Список предметов (сериализованные Entity)
    "max_slots": int      # Максимальное количество слотов
}
```

**Где слушать**: Клиентские модули

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("inventory_update", self.on_inventory_update)

def on_inventory_update(self, data: dict):
    self.items = data.get("inventory", [])
    self.max_slots = data.get("max_slots", 20)
    self.refresh_ui()
```

---

### inventory_full

Инвентарь переполнен.

**Когда вызывается**: Когда попытка добавить предмет не удалась (нет места).

**Данные**:
```python
{
    "uuid": str  # UUID игрока
}
```

**Где слушать**: Серверные модули

---

## События характеристик

### stats_update

Обновление характеристик игрока на клиенте.

**Когда вызывается**: Когда сервер отправляет обновленные характеристики.

**Данные**:
```python
{
    "health": float,  # Текущее здоровье
    "hunger": float   # Текущий голод
}
```

**Где слушать**: Клиентские модули

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("stats_update", self.on_stats_update)

def on_stats_update(self, data: dict):
    health = data.get("health", 100.0)
    hunger = data.get("hunger", 100.0)

    # Обновляем UI
    self.health_bar.set_value(health)
    self.hunger_bar.set_value(hunger)
```

---

### stats_request

Клиент запросил обновление характеристик.

**Когда вызывается**: Когда клиенту нужны актуальные статы.

**Данные**: `{}`

**Где слушать**: Серверные модули

---

## События мира

### world_config

Конфигурация мира получена клиентом.

**Когда вызывается**: При подключении или обновлении конфигурации мира.

**Данные**:
```python
{
    "map": {
        "model": str  # Путь к модели карты
    },
    "lighting": {
        "ambient": {"color": [R,G,B,A], "enabled": bool},
        "sun": {"color": [R,G,B,A], "direction": [H,P,R], "enabled": bool},
        "fill": {"color": [R,G,B,A], "direction": [H,P,R], "enabled": bool},
        "rim": {"color": [R,G,B,A], "direction": [H,P,R], "enabled": bool}
    },
    "skybox": {
        "texture": str,
        "radius": float,
        "segments": int,
        "rings": int,
        "uv_scale": {"v_offset": float, "v_scale": float}
    },
    "fog": {
        "enabled": bool
    }
}
```

**Где слушать**: Клиентские модули (lighting, skybox и др.)

**Пример**:
```python
def on_load(self):
    self.event_manager.subscribe("world_config", self.on_world_config)

def on_world_config(self, data: dict):
    lighting = data.get("lighting", {})
    ambient = lighting.get("ambient", {})

    if ambient.get("enabled", False):
        self.setup_ambient_light(ambient["color"])
```

---

### world_config_send_to_client

Запрос отправить конфиг мира клиенту.

**Когда вызывается**: Когда нужно отправить конфиг клиенту.

**Данные**:
```python
{
    "client_id": int  # ID клиента (или None для всех)
}
```

**Где слушать**: GameServer (уже обрабатывается)

---

## События боевой системы

### combat_started

Бой начался.

**Когда вызывается**: Когда DM или система начинает бой.

**Данные**:
```python
{
    "combat_id": str,          # Уникальный ID боя
    "participants": [          # Список участников
        {
            "entity_id": str,
            "name": str,
            "is_player": bool,
            "initiative": int,
            "hp_current": int,
            "hp_max": int,
            "is_dead": bool
        }
    ],
    "turn_order": list,        # Порядок ходов (entity_id)
    "round": int               # Номер раунда (начинается с 1)
}
```

**Где слушать**: Клиентские модули (combat UI)

---

### combat_ended

Бой закончился.

**Когда вызывается**: Когда бой завершён (победа, поражение, отмена DM).

**Данные**:
```python
{
    "combat_id": str,
    "reason": str  # "VICTORY" | "DEFEAT" | "DM_ENDED" | "TIMEOUT"
}
```

**Где слушать**: Клиентские и серверные модули

---

### combat_turn_start

Начало хода участника.

**Когда вызывается**: В начале хода каждого участника боя.

**Данные**:
```python
{
    "combat_id": str,
    "entity_id": str,      # ID сущности, чей ход
    "is_player": bool,     # Это ваш ход?
    "round": int,          # Номер раунда
    "resources": {         # Ресурсы хода (для игрока)
        "movement": float,       # Оставшееся движение (фт)
        "has_action": bool,      # Есть действие
        "has_bonus_action": bool,
        "has_reaction": bool
    }
}
```

**Где слушать**: Клиентские модули

---

### combat_action_result

Результат боевого действия.

**Когда вызывается**: После выполнения любого действия в бою.

**Данные**:
```python
{
    "combat_id": str,
    "actor_id": str,       # Кто совершил действие
    "target_id": str,      # Цель (может быть None)
    "action_id": str,      # Тип действия: "attack", "dash", "dodge", etc.
    "result": {
        "success": bool,
        "action": str,
        # Для атаки:
        "attack_roll": int,
        "attack_total": int,
        "target_ac": int,
        "hit": bool,
        "is_critical": bool,
        "is_fumble": bool,
        "damage": int,
        "target_hp_current": int,
        "target_hp_max": int,
        "target_is_dead": bool,
        # Для ошибок:
        "error": str
    }
}
```

**Где слушать**: Клиентские модули

---

### combat_round_start

Начало нового раунда.

**Когда вызывается**: Когда начинается новый раунд боя.

**Данные**:
```python
{
    "combat_id": str,
    "round": int
}
```

**Где слушать**: Клиентские модули

---

## События NPC

### world_state_received

Получено состояние мира с данными игроков и NPC.

**Когда вызывается**: При получении world_state от сервера.

**Данные** (Unified Format - новый):
```python
{
    "pawns": [  # Унифицированный список всех существ (игроки + NPC)
        {
            "entity_id": str,      # "player_1" или "npc_goblin_123"
            "pawn_type": str,      # "player" | "npc" | "creature"
            "owner_id": int,       # client_id для игроков, None для NPC
            "display_name": str,
            "transform": {"x": float, "y": float, "z": float, "rotation": float},
            "velocity": {"x": float, "y": float, "z": float},
            "model": str,
            "animation": str,
            "hp_current": int,
            "hp_max": int,
            "ai_state": str        # Только для NPC: "IDLE" | "PATROL" | "HOSTILE"
        }
    ],
    # Legacy format (для обратной совместимости):
    "players": [...],
    "npcs": [...]
}
```

**Данные** (Legacy Format):
```python
{
    "npcs": [
        {
            "entity_id": str,
            "display_name": str,
            "position": {"x": float, "y": float, "z": float, "rotation": float},
            "velocity": {"x": float, "y": float},
            "model": str,
            "animation": str,
            "ai_state": str,  # "IDLE" | "PATROL" | "HOSTILE" | "PURSUING" | "ATTACKING"
            "hp_current": int,
            "hp_max": int,
            "is_dead": bool
        }
    ]
}
```

**Где слушать**: Клиентские модули (NPC renderer, Pawn renderer)

---

### npc_aggro_player

NPC обнаружил и агрится на игрока.

**Когда вызывается**: Когда враждебный NPC обнаруживает игрока в радиусе агро.

**Данные**:
```python
{
    "npc_id": str,      # Entity ID NPC
    "player_id": str    # Client ID игрока (как строка)
}
```

**Где слушать**: Серверные модули (CombatManager автоматически подписан)

**Результат**: CombatManager автоматически начинает бой между NPC и игроком.

---

### npc_interact_request

Запрос на взаимодействие с NPC.

**Когда вызывается**: Когда игрок хочет взаимодействовать с NPC (клик).

**Данные**:
```python
{
    "client_id": int,
    "entity_id": str,
    "interaction_type": str  # "talk" | "trade" | "quest"
}
```

**Где слушать**: Серверные модули

---

### npc_attack

NPC атакует цель.

**Когда вызывается**: Когда NPC совершает атаку по цели.

**Данные**:
```python
{
    "attacker_id": str,     # Entity ID NPC
    "target_id": str,       # Entity ID цели
    "attack_roll": int,     # Бросок атаки (d20)
    "attack_total": int,    # Итоговый бросок (d20 + мод)
    "damage": int,          # Урон (если попал)
    "hit": bool,            # Попадание?
    "is_critical": bool     # Крит?
}
```

**Где слушать**: Серверные модули

---

### dm_npc_spawn

DM команда спавна NPC.

**Когда вызывается**: Команда `/spawn`.

**Данные**:
```python
{
    "client_id": int,
    "template_id": str,
    "x": float,
    "y": float,
    "z": float,
    "name": str  # Опционально
}
```

**Где слушать**: Серверные модули (NPC Manager)

---

### dm_npc_despawn

DM команда удаления NPC.

**Когда вызывается**: Команда `/despawn`.

**Данные**:
```python
{
    "client_id": int,
    "entity_id": str
}
```

**Где слушать**: Серверные модули

---

### npc_spawned

NPC был создан в мире.

**Когда вызывается**: При спавне NPC через NPCManager.

**Данные**:
```python
{
    "entity_id": str,       # Entity ID
    "npc_id": str,          # То же что entity_id (для совместимости с living_npc)
    "template_id": str,     # ID шаблона ("guard", "goblin", etc.)
    "template_data": dict,  # Полные данные шаблона (включая living)
    "position": {"x": float, "y": float, "z": float, "rotation": float}
}
```

**Где слушать**: Серверные модули (Living World systems)

---

### npc_despawned

NPC был удалён из мира.

**Когда вызывается**: При удалении NPC.

**Данные**:
```python
{
    "entity_id": str,  # Entity ID
    "npc_id": str      # То же что entity_id
}
```

---

### npc_urgent_need

NPC испытывает критическую потребность.

**Когда вызывается**: Когда потребность NPC падает ниже критического уровня (< 20).

**Данные**:
```python
{
    "entity_id": str,   # Entity ID NPC
    "need": str,        # "hunger" | "energy" | "safety"
    "value": float,     # Текущее значение потребности
    "action": str       # "SEEK_FOOD" | "SEEK_REST" | "FLEE"
}
```

**Где слушать**: `sv_npc_ai.py` (AISystem) — создаёт behavior override

---

### npc_activity_changed

Активность NPC изменилась по расписанию.

**Когда вызывается**: Когда игровой час сменяется и NPC получает новую активность по расписанию.

**Данные**:
```python
{
    "entity_id": str,     # Entity ID NPC
    "activity": str,      # "patrolling" | "sleeping" | "eating" | "socializing"
    "location": list      # [x, y, z] — опционально, целевая позиция
}
```

**Где слушать**: `sv_npc_ai.py` (AISystem) — создаёт behavior override

---

## События игрового времени

### game_tick

Тик игрового времени.

**Когда вызывается**: Каждый серверный тик.

**Данные**:
```python
{
    "delta_hours": float  # Сколько игровых часов прошло за этот тик
}
```

**Где слушать**: Living World systems (обновление потребностей)

---

### game_hour_changed

Сменился игровой час.

**Когда вызывается**: Когда игровой час увеличивается на 1.

**Данные**:
```python
{
    "hour": int  # Текущий игровой час (0-23)
}
```

**Где слушать**: Living World systems (обновление расписаний), любые модули зависящие от времени суток

**Заметка**: Game time: 1 реальная минута = 1 игровой час (полный цикл день/ночь = 24 минуты). Стартовое время: 8:00 утра.

---

## События аудио

### dm_audio_command

DM команда управления аудио.

**Когда вызывается**: Команды `/music`, `/ambient`, `/sfx`.

**Данные**:
```python
{
    "command": str,    # "music" | "ambient" | "sfx"
    "value": str,      # Название плейлиста/звука
    "volume": float    # Опционально
}
```

**Где слушать**: Клиентские аудио модули

---

### player_jump

Игрок прыгнул.

**Когда вызывается**: При прыжке игрока.

**Данные**:
```python
{
    "surface": str,          # "dirt" | "stone" | "wood" | "water"
    "has_chain_armor": bool  # Есть ли тяжёлая броня
}
```

**Где слушать**: Клиентские аудио модули

---

### player_land

Игрок приземлился.

**Когда вызывается**: При приземлении после прыжка/падения.

**Данные**:
```python
{
    "surface": str,
    "has_chain_armor": bool
}
```

**Где слушать**: Клиентские аудио модули

---

## Серверные события отправки

Эти события используются плагинами для отправки данных клиентам через сервер.

### chat_send_to_clients

Отправить сообщение в чат клиентам.

**Данные**:
```python
{
    "data": {
        "type": str,
        "sender": str,
        "message": str,
        "color": tuple
    },
    "recipients": list | None  # Список ID клиентов или None для всех
}
```

**Пример**:
```python
self.event_manager.post("chat_send_to_clients", {
    "data": {
        "type": "system",
        "sender": "Сервер",
        "message": "Приветствую!",
        "color": (1, 1, 0, 1)
    },
    "recipients": None  # Всем
})
```

---

### stats_send_to_client

Отправить характеристики клиенту.

**Данные**:
```python
{
    "client_id": int,
    "data": {
        "health": float,
        "hunger": float
    }
}
```

**Пример**:
```python
self.event_manager.post("stats_send_to_client", {
    "client_id": player_id,
    "data": {
        "health": 75.0,
        "hunger": 50.0
    }
})
```

---

### inventory_send_to_client

Отправить инвентарь клиенту.

**Данные**:
```python
{
    "client_id": int,
    "data": {
        "inventory": list,
        "max_slots": int
    }
}
```

**Пример**:
```python
self.event_manager.post("inventory_send_to_client", {
    "client_id": player_id,
    "data": {
        "inventory": serialized_items,
        "max_slots": 20
    }
})
```

---

### system_message_to_client

Отправить системное сообщение клиенту.

**Данные**:
```python
{
    "client_id": int | None,  # None для всех
    "data": {
        "message": str
    }
}
```

**Пример**:
```python
self.event_manager.post("system_message_to_client", {
    "client_id": None,  # Всем
    "data": {
        "message": "Сервер перезагружается через 5 минут"
    }
})
```

---

## Создание собственных событий

### Соглашения по именованию

Используйте формат `plugin_id.event_name` для избежания конфликтов:

```python
# ✅ Хорошо
self.event_manager.post("my_plugin.player_spawned", data)
self.event_manager.post("quests.quest_completed", data)
self.event_manager.post("economy.transaction", data)

# ❌ Плохо (может конфликтовать)
self.event_manager.post("spawned", data)
self.event_manager.post("completed", data)
```

### Пример создания события

**Серверный модуль (отправитель)**:
```python
class EconomyServerModule(PluginModule):
    def give_money(self, player_uuid: str, amount: int):
        # ... логика выдачи денег ...

        # Отправляем событие
        self.event_manager.post("economy.money_received", {
            "uuid": player_uuid,
            "amount": amount,
            "balance": new_balance
        })
```

**Другой модуль (слушатель)**:
```python
class AchievementsModule(PluginModule):
    def on_load(self):
        # Подписываемся на событие экономики
        self.event_manager.subscribe("economy.money_received", self.on_money_received)

    def on_money_received(self, data: dict):
        player_uuid = data.get("uuid")
        balance = data.get("balance", 0)

        # Проверяем ачивку "Миллионер"
        if balance >= 1000000:
            self.unlock_achievement(player_uuid, "millionaire")
```

---

## Лучшие практики

### 1. Всегда отписывайтесь в on_unload

```python
class MyModule(PluginModule):
    def on_load(self):
        self.event_manager.subscribe("event", self.handler)

    def on_unload(self):
        # ✅ ОБЯЗАТЕЛЬНО!
        self.event_manager.unsubscribe("event", self.handler)
```

### 2. Проверяйте наличие данных

```python
def on_event(self, data: dict):
    # ✅ Безопасно
    player_id = data.get("player_id")
    if player_id is None:
        self.logger.warning("player_id отсутствует в событии")
        return

    # ❌ Небезопасно (может вызвать KeyError)
    player_id = data["player_id"]
```

### 3. Документируйте свои события

```python
class MyPlugin(PluginModule):
    """
    События, которые отправляет плагин:
    - my_plugin.data_updated: Когда данные обновлены
      Данные: {"uuid": str, "value": int}

    События, на которые подписывается:
    - player_joined: Инициализация данных игрока
    - player_left: Очистка данных
    """
    pass
```

### 4. Используйте типизацию

```python
from typing import Dict, Any

def on_event(self, data: Dict[str, Any]):
    """
    Обработчик события с типизацией.

    Args:
        data: Словарь с данными события
            - player_id (int): ID игрока
            - value (float): Значение
    """
    pass
```

### 5. Избегайте тяжелых операций в app_tick

```python
def on_load(self):
    # ❌ Плохо - вызывается каждый кадр
    self.event_manager.subscribe("app_tick", self.heavy_operation)

    # ✅ Хорошо - используйте таймер
    self.timer = 0.0
    self.event_manager.subscribe("app_tick", self.tick_with_timer)

def tick_with_timer(self, data: dict):
    dt = data.get("dt", 0.0)
    self.timer += dt

    if self.timer >= 1.0:  # Раз в секунду
        self.heavy_operation()
        self.timer = 0.0
```

---

## Диаграммы потоков событий

### Поток чата

```
Пользователь вводит сообщение
    ↓
ChatUI отправляет "client_send_chat_message"
    ↓
GameClient.send_chat_packet() отправляет пакет на сервер
    ↓
GameServer получает пакет
    ↓
GameServer отправляет "chat_message_received"
    ↓
ChatBroadcastModule обрабатывает сообщение
    ↓
ChatBroadcastModule отправляет "chat_send_to_clients"
    ↓
GameServer отправляет пакет клиентам
    ↓
GameClient получает пакет
    ↓
GameClient отправляет "chat_broadcast"
    ↓
ChatUIModule отображает сообщение
```

### Поток инвентаря

```
Игрок нажимает "Использовать предмет"
    ↓
InventoryUI отправляет "client_item_use"
    ↓
GameClient.send_item_use_packet() отправляет пакет
    ↓
GameServer получает пакет
    ↓
GameServer отправляет "item_use"
    ↓
InventoryServerModule обрабатывает использование
    ↓
Предмет.on_use() выполняется
    ↓
InventoryServerModule отправляет "inventory_send_to_client"
    ↓
GameServer отправляет обновленный инвентарь
    ↓
GameClient получает пакет
    ↓
GameClient отправляет "inventory_update"
    ↓
InventoryClientModule обновляет UI
```

---

## FAQ

### Q: Как узнать, какие события доступны?

**A**: Смотрите этот справочник или изучите исходный код встроенных плагинов в `nine/plugins/`.

### Q: Можно ли отправлять события с клиента на сервер?

**A**: Напрямую нет. Используйте специальные события (например, `client_send_chat_message`), которые GameClient преобразует в сетевые пакеты.

### Q: Что делать если событие не срабатывает?

**A**: Проверьте:
1. Правильно ли имя события?
2. Подписались ли вы в `on_load()`?
3. Не отписались ли вы слишком рано?
4. Добавьте логирование в обработчик для отладки.

### Q: Можно ли подписаться на событие несколько раз?

**A**: Да, но обработчик будет вызван несколько раз. Обычно это ошибка.

---

**Версия документа**: 1.2.0
**Дата обновления**: 2026-01-22
