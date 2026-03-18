# Gameplay Gap Analysis — что есть, чего не хватает

## Текущие системы (30,000+ строк плагинов)

### Полностью реализованные
| Система | Строк | Состояние |
|---------|-------|-----------|
| Chat | 2110 | RP-чат с радиусом, /me, /it, /ooc, /looc, 20+ admin команд |
| Inventory | 7544 | Предметы, стаки, use/drop, persistence в БД (новое) |
| Equipment | (часть inventory) | 12 слотов, надевание/снятие, бонусы статов |
| Combat | 5839 | Пошаговый D&D 5e, инициатива, action economy |
| NPC AI | 3211 | LOD-система, wander, patrol, faction hostility |
| Living NPC | 496 | Потребности (hunger/energy), personality, memories, расписания |
| Spells | 1819 | 35 заклинаний, слоты, концентрация |
| Conditions | 1165 | D&D 5e состояния (stunned, poisoned, etc.) |
| D&D Characters | 3361 | 6 рас, 12 классов, 8-step character creation |
| Quests | 1341 | Журнал квестов, objectives, rewards |
| DM Panel | 1688 | Админка для DM (управление боем, NPC, аудио) |
| Rest | 683 | Короткий/длинный отдых, hit dice |
| Stats | 569 | HP, AC, attributes, level |
| Lighting | 121 | Динамическое освещение от сервера |
| Skybox | 156 | Небо, день/ночь |
| PostFX | 217 | Пост-обработка (bloom, etc.) |
| World Config | 92 | Настройки мира от сервера |

### Частично реализованные (есть фундамент)
| Система | Что есть | Что не доделано |
|---------|----------|----------------|
| Needs (NPC) | hunger, energy в NeedsComponent | Только для NPC, не для игроков |
| Trading | TRADEABLE флаг в Item, n_bucks валюта, merchant NPC template | Нет UI торговли, нет NPC магазинов |
| Death | is_dead в HealthComponent, death анимация | Нет respawn, нет loot drop |
| Loot/Drop | item_pickup/item_drop события, on_pickup() в Item | Нет drop при смерти, нет loot tables |
| Dialogue | NPC interact event, context menu | Нет диалоговых деревьев, нет NPC реплик |

---

## Архитектура: Unified Pawn System

Игроки и NPC наследуют общую ECS-архитектуру через `PawnComponent`:

```
PawnComponent(pawn_type=PLAYER/NPC)
  Общие компоненты:
    TransformComponent    — позиция, rotation, velocity
    HealthComponent       — HP, is_dead
    CombatStatsComponent  — AC, атака, damage
    ModelComponent        — модель, анимация, tint
    PhysicsComponent      — FULL/SIMPLE/NONE
    FactionComponent      — фракция, враждебность

  Только NPC:
    AIComponent           — state, behavior, LOD
    NeedsComponent        — hunger, energy, safety
    PathfindingComponent  — waypoints, steering
    PersonalityComponent  — traits
    ScheduleComponent     — daily routines
    MemoryComponent       — memories of events

  Только Player:
    CharacterController   — input → movement (не ECS, отдельный класс)
```

Ресурсные ноды, crafting stations, мировые объекты — это тоже ECS entities
с `PawnType.OBJECT` или отдельным компонентом. NPC могут взаимодействовать
с ними через AI (голодный NPC идёт к еде, кузнец идёт к наковальне).

---

## Чего не хватает для Rimworld-подобного геймплея

### Tier 1 — Критически важно

**1. Crafting System** `nine/plugins/crafting/`
- Рецепты (input items → output item)
- Crafting stations (workbench, forge, alchemy table)
- Прогресс крафтинга (время)
- Интеграция с inventory (расход материалов)
- Пример: 2x Wood + 1x Iron → Wooden Shield
- NPC тоже должны уметь крафтить (кузнец NPC создаёт оружие)

**2. Resource Gathering** `nine/plugins/gathering/`
- Ресурсные ноды на карте (деревья, камни, руда, травы)
- Добыча с анимацией и таймером
- Респавн ресурсов
- Tool requirements (кирка для руды, топор для дерева)
- Drop table при сборе (1-3 Wood, chance of special item)
- NPC тоже собирают ресурсы (фермер собирает еду, шахтёр — руду)

**3. Building/Construction** `nine/plugins/building/`
- Размещение объектов в мире (ghost preview → build)
- Blueprint system (стоимость ресурсов)
- Разрушение построек
- Collision для построенных объектов
- Примеры: стена, дверь, факел, верстак

### Tier 2 — Важно для полноты

**4. Trading/Economy** `nine/plugins/trading/`
- NPC магазины с UI
- Buy/sell с ценами
- Торговля между игроками
- Динамические цены (спрос/предложение)
- Merchant NPC уже есть в шаблонах

**5. Loot System** `nine/plugins/loot/`
- Loot tables для NPC (при смерти)
- Loot tables для ресурсных нодов
- Rarity system (common → legendary)
- Мировые контейнеры (сундуки)
- Ground items (подбор)

**6. Death & Respawn**
- Экран смерти
- Respawn points
- Потеря предметов / XP при смерти (настраиваемо)
- Corpse с loot (для NPC)

**7. Weather System** `nine/plugins/weather/`
- Дождь, снег, туман, гроза
- Влияние на геймплей (скорость, видимость)
- Серверная синхронизация
- Визуальные эффекты (particles)

### Tier 3 — Nice to have

**8. Party/Group System**
- Создание группы, приглашение
- Shared XP
- Party chat
- Group UI (HP bars)

**9. Dialogue System** (расширение NPC)
- Деревья диалогов (JSON/YAML)
- NPC реплики с выбором ответа
- Условия (faction, quest progress, stats)
- Rewards/consequences

**10. Map/Minimap**
- 2D миникарта в HUD
- Markers (NPC, quest objectives, party members)
- Fog of war

**11. Skills/Professions**
- Crafting leveling (кузнец, алхимик, etc.)
- Gathering leveling
- Бонусы от уровня профессии
- XP за действия

---

## DM Toolkit — инструменты мастера

### Текущее состояние
DM Panel (`nine/plugins/dm_panel/`) — базовая веб-панель + chat-команды для управления.
Не хватает удобного in-game управления через контекстное меню.

### Что нужно: Context Menu (C) для NPC

DM/Admin должен мочь кликнуть на NPC (или нажать C рядом с ним) и получить контекстное меню со ВСЕМИ инструментами:

#### Управление NPC
- **Переместить** — drag & drop или teleport к указанной точке
- **Повернуть** — изменить facing direction
- **Удалить** — убрать NPC с карты
- **Клонировать** — создать копию этого NPC рядом

#### Боевые действия
- **Начать бой** — от лица этого NPC (инициирует encounter)
- **Атаковать цель** — выбрать цель для атаки
- **Установить инициативу** — ручной ввод числа
- **Добавить в текущий бой** — если бой уже идёт

#### Здоровье и состояния
- **Изменить HP** — ползунок или ввод (+/- или абсолютное значение)
- **Полный хил** — восстановить HP до максимума
- **Убить** — мгновенно установить HP = 0, триггерить death
- **Воскресить** — восстановить из мёртвого состояния
- **Добавить состояние** — выбор из списка D&D conditions
- **Убрать состояние** — снять конкретное condition

#### Roleplay
- **Говорить от лица NPC** — текст появится в чате от имени этого NPC
- **Действие (/me)** — эмоция/действие от имени NPC
- **Шёпот игроку** — приватное сообщение конкретному игроку от NPC

#### Информация
- **Инспект** — показать все характеристики NPC (HP, AC, faction, inventory, etc.)
- **Статистика** — damage dealt, damage taken, kills
- **Позиция** — координаты x/y/z

#### Создание NPC (быстрое)
- **Spawn menu** — выбор из шаблонов (guard, goblin, merchant, skeleton, etc.)
- **Spawn рядом с собой** — быстрый спавн без координат
- **Spawn по клику** — кликнуть на карту = спавн в этой точке
- **Кастомный NPC** — ввести имя, HP, AC, faction, модель

### Реализация

Серверная часть (`sv_dm_tools.py`):
```python
# События для DM инструментов
"dm_npc_move"         → {entity_id, x, y, z}
"dm_npc_set_hp"       → {entity_id, hp}  или  {entity_id, delta}
"dm_npc_kill"         → {entity_id}
"dm_npc_resurrect"    → {entity_id}
"dm_npc_speak"        → {entity_id, message, chat_type}
"dm_npc_attack"       → {entity_id, target_id}
"dm_npc_add_condition" → {entity_id, condition_id}
"dm_npc_remove"       → {entity_id}
"dm_npc_clone"        → {entity_id}
"dm_spawn_npc"        → {template, x, y, z, custom_data}
"dm_start_combat_as"  → {entity_id}  (NPC инициирует бой)
```

Клиентская часть (`cl_dm_context_menu.js`):
- Привязка к клавише C или правому клику
- Raycast для определения NPC под курсором
- Выбранный NPC подсвечивается (outline или glow)
- Радиальное или вертикальное контекстное меню
- Горячие клавиши для частых действий (H = heal, K = kill, M = move)

---

## Рекомендации по порядку реализации

### Фаза 1: Survival Loop (самое важное)
1. **Resource Gathering** → даёт ресурсы
2. **Crafting** → даёт применение ресурсам
3. **Loot System** → даёт reward за combat

Это создаёт core loop: **gather → craft → equip → fight → loot → repeat**

### Фаза 2: World Systems
4. **Building** → даёт цель для ресурсов
5. **Trading** → даёт экономику
6. **Weather** → даёт атмосферу

### Фаза 3: DM & Social
7. **DM Context Menu** → мастер может нормально вести сессию
8. **Dialogue** → NPC становятся интересными
9. **Party System** → мультиплеер становится полезным
10. **Map** → навигация
11. **Professions** → долгосрочная прогрессия

---

## Что уже есть и можно переиспользовать

- **Entity/Item система** — новые ресурсы = новые Entity subclasses
- **NPC templates** — merchant уже есть, добавить trader AI
- **Needs система** — hunger/energy уже в компонентах, включить для игроков
- **Event система** — все плагины общаются через события
- **ECS** — crafting stations и ресурсные ноды = ECS entities с PawnType.OBJECT
- **CEF UI** — любой UI через HTML/CSS/JS
- **Context Menu** — уже есть базовое (inspect, interact), расширить для DM

---

## Проделанная работа (эта сессия)

### Asset Pipeline
- Извлечение BSA (Morrowind + Oblivion)
- NIF парсер v4.0.0.2 с prescan (pipeline/nif_parser.py)
- Сборка персонажа Oblivion через Blender + niftools (5 NIF → 1 модель)
- Патчи niftools для Blender 5.0 (use_auto_smooth, shadow_method, Action.fcurves, armature matmul)
- Документация пайплайна (docs/OBLIVION_ASSET_PIPELINE.md)

### Core Engine → main branch
- Хирургическое разделение D&D контента от движка
- client.py, game_server.py, webview_api.py — убран D&D код
- Force push в main с новой архитектурой

### Inventory Persistence
- Item.to_dict()/from_dict() сериализация
- DB миграция (inventory column)
- Save/load на join/leave в sv_inventory.py и sv_equipment.py
- Удалён _cl_inventory_legacy.py (661 строк мёртвого кода)

### Chat Refactoring
- sv_broadcast.py (1677L) → sv_broadcast.py (714L) + sv_commands.py (1040L)
- Выделены command handlers в отдельный класс

### Bug Fixes
- world.py: loader → self.base.loader
