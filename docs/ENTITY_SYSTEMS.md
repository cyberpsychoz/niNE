# Системы Entity в niNE

**Последнее обновление:** 2026-01-30

---

## Обзор

Проект niNE использует **две различные системы Entity** для разных целей:

1. **`nine/core/entity.py`** - Компонентная система для статичных игровых объектов
2. **`nine/core/ecs.py`** - Entity Component System для динамических сущностей

Обе системы сосуществуют намеренно и решают разные задачи.

---

## 1. entity.py - Компонентная система

### Назначение
Используется для **статичных игровых объектов** с постоянными свойствами:
- Предметы (Items)
- Инвентарь (Inventory)
- Статичные мировые объекты (World entities)
- Сохранённые данные

### Архитектура

```python
from nine.core.entity import Entity, ENTITY_REGISTRY

# Создание entity
entity = Entity(unique_id="item_sword_123")
entity.add_component("physics", {
    "position": {"x": 10, "y": 20, "z": 0},
    "rotation": 0
})
entity.add_component("item", {
    "name": "Iron Sword",
    "weight": 3.5,
    "value": 100
})

# Регистрация в глобальном реестре
ENTITY_REGISTRY[entity.unique_id] = entity
```

### Особенности

| Аспект | Реализация |
|--------|-----------|
| **Компоненты** | Словари (dict) с произвольной структурой |
| **Хранение** | Глобальный `ENTITY_REGISTRY` |
| **Сериализация** | `to_dict()` / `from_dict()` для сохранения/загрузки |
| **Позиция** | Компонент "physics" с координатами x, y, z |
| **Обновление** | Нет автоматического update loop |
| **Type safety** | Нет (используются словари) |

### Когда использовать

✓ **Используйте entity.py для:**
- Предметов в инвентаре
- Статичных объектов на карте (сундуки, двери, алтари)
- Данных для сохранения в БД
- Объектов, которые не требуют постоянного обновления

❌ **НЕ используйте для:**
- NPC с AI
- Игроков
- Объектов требующих физику/анимацию
- Систем требующих регулярного update

### Пример использования

```python
# Создание предмета
from nine.core.entity import Entity

sword = Entity(unique_id="item_001")
sword.add_component("item", {
    "name": "Longsword",
    "type": "weapon",
    "damage": "1d8",
    "properties": ["versatile"]
})

# Сохранение в БД
sword_data = sword.to_dict()
db.save_item(sword_data)

# Загрузка из БД
loaded_data = db.load_item("item_001")
sword = Entity.from_dict(loaded_data)
```

---

## 2. ecs.py - Entity Component System

### Назначение
Используется для **динамических сущностей** с поведением и системами обновления:
- NPC с AI
- Pawns (игроки и NPC в едином представлении)
- Физические объекты
- Анимированные сущности

### Архитектура

```python
from nine.core.ecs import ECSWorld, Entity
from nine.core.components import Transform, Pawn, AIComponent
from nine.core.systems import AISystem, PhysicsSystem

# Создание ECS мира
world = ECSWorld()
world.add_system(AISystem(world))
world.add_system(PhysicsSystem(world))

# Создание NPC
npc = world.create_entity()
npc.add_component(Transform(position=(10, 20, 0), rotation=0))
npc.add_component(Pawn(name="Goblin", hp=10, max_hp=10))
npc.add_component(AIComponent(state="IDLE", target=None))

# Обновление каждый кадр
world.update(dt=0.016)
```

### Особенности

| Аспект | Реализация |
|--------|-----------|
| **Компоненты** | Типизированные классы (dataclasses) |
| **Хранение** | `ECSWorld` - изолированный контейнер |
| **Обновление** | Системы (Systems) автоматически обновляют entities |
| **Query** | `world.get_entities_with_components(Transform, Pawn)` |
| **Type safety** | Полная (type hints + dataclasses) |
| **Производительность** | Оптимизировано для 300+ entities |

### Системы (Systems)

ECS включает встроенные системы обновления:

```python
# nine/core/systems.py
- PhysicsSystem      # Обновление позиций, коллизий
- AISystem           # Обновление AI состояний, pathfinding
- AnimationSystem    # Проигрывание анимаций
- NetworkSyncSystem  # Синхронизация по сети
```

Каждая система автоматически обрабатывает entities с нужными компонентами:

```python
class AISystem:
    def update(self, dt: float):
        # Автоматически находит все entities с AI
        for entity in self.world.get_entities_with_components(AIComponent, Transform):
            ai = entity.get_component(AIComponent)
            transform = entity.get_component(Transform)
            # Обновляем AI...
```

### Когда использовать

✓ **Используйте ecs.py для:**
- NPC с AI поведением
- Игроков (Pawns)
- Врагов в бою
- Объектов с физикой/анимацией
- Любых сущностей требующих регулярного update

❌ **НЕ используйте для:**
- Предметов в инвентаре
- Статичных объектов без поведения
- Данных для сохранения (используйте entity.py)

### Пример использования

```python
# Создание NPC врага
from nine.core.ecs import ECSWorld
from nine.core.components import Transform, Pawn, AIComponent

world = ECSWorld()

goblin = world.create_entity()
goblin.add_component(Transform(position=(15, 20, 0)))
goblin.add_component(Pawn(
    name="Goblin Scout",
    hp=7,
    max_hp=7,
    ac=13,
    speed=30
))
goblin.add_component(AIComponent(
    state="IDLE",
    behavior="hostile",
    aggro_range=10.0
))

# Системы автоматически обновят NPC
world.update(dt=0.016)
```

---

## Сравнение систем

| Критерий | entity.py | ecs.py |
|----------|-----------|--------|
| **Цель** | Статичные данные | Динамические сущности |
| **Компоненты** | Dict-based | Class-based (typed) |
| **Обновление** | Ручное | Автоматическое (systems) |
| **Производительность** | Нет требований | Оптимизировано для масштаба |
| **Сериализация** | Встроенная (to_dict) | Через NetworkSyncSystem |
| **Type safety** | Нет | Полная |
| **Примеры** | Items, Inventory | NPC, Pawns, AI |

---

## Интеграция систем

### Преобразование между системами

Иногда нужно преобразовать entity в ecs entity (например, когда предмет "оживает"):

```python
# entity.py -> ecs.py
from nine.core.entity import Entity as StaticEntity
from nine.core.ecs import ECSWorld

# Статичный предмет
item = StaticEntity(unique_id="chest_001")
item.add_component("physics", {"position": {"x": 10, "y": 20, "z": 0}})

# Преобразование в dynamic entity (например, миmic!)
world = ECSWorld()
mimic = world.create_entity()
mimic.add_component(Transform(
    position=(
        item.get_component("physics")["position"]["x"],
        item.get_component("physics")["position"]["y"],
        item.get_component("physics")["position"]["z"]
    )
))
mimic.add_component(Pawn(name="Mimic", hp=30, max_hp=30))
mimic.add_component(AIComponent(state="HIDDEN", behavior="ambush"))
```

### Лучшие практики

1. **Разделяйте ответственность:**
   - Инвентарь игрока → `entity.py`
   - Сам игрок (pawn) → `ecs.py`

2. **Не смешивайте реестры:**
   - Не добавляйте ECS entities в `ENTITY_REGISTRY`
   - Не пытайтесь использовать `to_dict()` на ECS entities напрямую

3. **Сохранение данных:**
   - ECS entities → преобразовать в dict через NetworkSyncSystem
   - Static entities → использовать `to_dict()` напрямую

---

## Будущее развитие

### Потенциальные улучшения

1. **Унификация API** (не объединение!):
   - Общий интерфейс `EntityLike` для обеих систем
   - Единый паттерн query/iteration

2. **Гибридные entities:**
   - Entities которые могут быть как статичными так и динамическими
   - Автоматическое преобразование при необходимости

3. **Улучшенная сериализация:**
   - Единый формат для обеих систем
   - Автоматическое определение типа при загрузке

### НЕ планируется

❌ Полное объединение систем - они решают разные задачи
❌ Миграция всех entities на ECS - избыточно для статичных объектов
❌ Удаление entity.py - необходима для инвентаря/предметов

---

## Диагностика проблем

### "Entity не обновляется"

✓ **Решение:** Убедитесь что используете ECS entity, а не static entity

```python
# НЕПРАВИЛЬНО - static entity не обновляется автоматически
npc = Entity(unique_id="npc_001")

# ПРАВИЛЬНО - ECS entity обновляется через systems
npc = world.create_entity()
```

### "Не могу найти entity по ID"

✓ **Решение:** Проверьте правильный реестр

```python
# Static entities
entity = ENTITY_REGISTRY.get(unique_id)

# ECS entities
for entity in world.get_entities_with_components(Pawn):
    if entity.get_component(Pawn).name == "Goblin":
        ...
```

### "Entity не сохраняется"

✓ **Решение:** Используйте правильный метод

```python
# Static entity
data = entity.to_dict()

# ECS entity
from nine.core.systems import NetworkSyncSystem
sync = NetworkSyncSystem(world)
data = sync.get_world_state()
```

---

## Заключение

Две системы Entity - это **преднамеренное архитектурное решение**, а не техдолг:

- **entity.py** - простая, гибкая система для данных
- **ecs.py** - мощная, производительная система для поведения

Используйте правильную систему для правильной задачи!

---

## См. также

- `docs/PLUGINS.md` - Документация plugin системы
- `docs/EVENT_API.md` - Документация event системы
- `nine/core/components.py` - Все доступные компоненты ECS
- `nine/core/systems.py` - Все системы ECS
