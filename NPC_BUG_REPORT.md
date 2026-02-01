# NPC AI BUG TESTING REPORT
## Дата: 2026-02-01

### КРИТИЧЕСКИЕ БАГИ НАЙДЕНЫ

#### БАГ #1: ECS Entity Pending Addition не обрабатывается
**Severity:** CRITICAL  
**Location:** `nine/core/ecs.py`

**Описание:**  
Entities созданные через `world.create_entity()` добавляются в `_pending_addition` очередь и не доступны для `get_entities_with_components()` до вызова `world.update()` или `_process_pending_additions()`.

**Воспроизведение:**
```python
world = ECSWorld()
npc = world.create_entity()
npc.add_component(PositionComponent())

# БАГ: entities = 0!
entities = list(world.get_entities_with_components(PositionComponent))
```

**Исправление:**
Вызывать `world._process_pending_additions()` перед query OR документировать это поведение.

---

#### БАГ #2: AISystem требует жесткую связь с NPCManager
**Severity:** HIGH  
**Location:** `nine/plugins/npc/sv_npc_ai.py:382-383`

**Описание:**  
AISystem не может работать без NPCManager - это делает систему не unit-testable и нарушает принципы декаплинга.

**Код:**
```python
def _update_player_cache(self) -> None:
    if not self.npc_manager:
        return  # <-- ранний возврат, player cache остается пустым
```

**Влияние:**
- NPC не видят игроков
- Невозможно unit-тестировать AI систему
- Нарушение Single Responsibility Principle

**Решение:**
Инжектить список игроков через параметры OR сделать player detection опциональным.

---

#### БАГ #3: FactionComponent обязателен для вражеской детекции
**Severity:** MEDIUM  
**Location:** `nine/plugins/npc/sv_npc_ai.py:_find_nearest_enemy`

**Описание:**  
Метод `_find_nearest_enemy()` требует FactionComponent, иначе возвращает None. Это не документировано.

**Код:**
```python
faction = entity.get_component(FactionComponent)
if not faction:
    return None  # <-- Без FactionComponent враг не детектится
```

**Решение:**
- Документировать requirement
- OR сделать FactionComponent опциональным с дефолтным поведением

---

### ПОТЕНЦИАЛЬНЫЕ БАГИ

#### Граничный случай: aggro_radius == distance
**Status:** Requires Investigation  
Тесты показывают что NPC может не детектить игрока на ТОЧНОМ расстоянии aggro_radius (edge case с float comparison).

#### Memory Leak при create/destroy циклах
**Status:** Minor  
901 новых объектов после 100 create/destroy циклов. Возможно нормально, но требует профилирования.

---

### УСПЕШНО РАБОТАЕТ

✓ NEUTRAL NPC не атакуют первым  
✓ Zero distance handling (без division by zero)  
✓ Negative aggro radius корректно обрабатывается  
✓ WANDER AI не зацикливается  
✓ State transition не спамит  
✓ Leash radius enforcement работает

---

### РЕКОМЕНДАЦИИ

1. **Немедленно:** Исправить ECS pending additions - это критическая архитектурная проблема
2. **High Priority:** Декаплить AISystem от NPCManager для unit-testability
3. **Medium:** Документировать FactionComponent requirement
4. **Low:** Профилировать memory usage

---

### ЗАКЛЮЧЕНИЕ

Найдено **3 архитектурных бага** которые делают систему трудной для тестирования и поддержки. Основная проблема - tight coupling и недостаток документации.

Рекомендуется рефакторинг для улучшения testability перед добавлением новых AI features.
