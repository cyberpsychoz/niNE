# niNE Architecture Fixes - Январь 2026

## Обнаруженные проблемы и план исправления

### КРИТИЧЕСКИЕ (требуют немедленного исправления)

#### 1. Дублирование audio плагина
**Проблема:** Два идентичных audio плагина с разными ID:
- `nine/plugins/dnd/audio/` (unique_id: `nine.dnd.audio`)
- `nine/plugins/dnd_audio/` (unique_id: `nine.dnd_audio`)

**Анализ:**
- `dnd/audio/` - использует `doMethodLater` для автозапуска музыки
- `dnd_audio/` - использует event system (`game_state_changed`) - более современный подход

**Решение:**
- ✓ Удалить `nine/plugins/dnd_audio/` (старая версия)
- ✓ Оставить `nine/plugins/dnd/audio/` как основной плагин
- ✓ При необходимости портировать улучшения из dnd_audio в dnd/audio

**Файлы для удаления:**
```
nine/plugins/dnd_audio/
├── sh_plugin.py
├── cl_audio_integration.py
├── cl_footsteps.py
└── __init__.py
```

---

#### 2. Неправильная передача base в NPCRenderer
**Проблема:** В `nine/plugins/npc/cl_npc_renderer.py:299` передаётся `self.app` вместо правильного объекта.

**Текущий код:**
```python
renderer = NPCRenderer(
    entity_id,
    npc_data,
    self.app.render,
    self.app  # ОШИБКА! NPCRenderer ожидает ShowBase, но получает базовый объект
)
```

**Анализ:**
- Класс `NPCRenderer` (строка 30) принимает `base: ShowBase`
- Использует `self.base.loader` (строка 107) - правильно для вспомогательного класса
- НО ему передаётся `self.app` из NPCClientModule, который может не быть ShowBase

**Решение:**
```python
# Вариант 1: Передавать правильный объект
renderer = NPCRenderer(
    entity_id,
    npc_data,
    self.app.render,
    self.app  # self.app в PluginModule УЖЕ является ShowBase
)
```

Проблема скорее концептуальная - нужно проверить что `self.app` действительно ShowBase.

---

### ВАЖНЫЕ (рекомендуется исправить)

#### 3. Две разные Entity системы
**Проблема:** Сосуществуют две несовместимые системы:
- `nine/core/entity.py` - старая компонентная система (для предметов, мира)
- `nine/core/ecs.py` - новая ECS система (для NPC, pawns)

**Решение:**
- ✓ Создать документацию `docs/ENTITY_SYSTEMS.md` с описанием разделения
- ✓ Добавить комментарии в оба файла о назначении
- [ ] В будущем: мигрировать на единую ECS систему

**Разделение ответственности:**
| Система | Назначение | Примеры |
|---------|-----------|---------|
| entity.py | Статичные игровые объекты | Предметы, инвентарь, world entities |
| ecs.py | Динамические сущности с системами | NPC, Pawns, AI, Physics |

---

### НИЗКИЙ ПРИОРИТЕТ

#### 4. Тестовые файлы в корне проекта
**Проблема:** 8 тестовых файлов в корне вместо `tests/`

**Файлы:**
- test_blocks.py
- test_blocks_visual.py
- test_button_texture.py
- test_npc_event.py
- test_npc_spawn.py
- test_pathfinding.py
- test_ui.py
- test_ui_auto.py

**Решение:**
- ✓ Создать `tests/` директорию
- ✓ Переместить все test_*.py файлы туда
- ✓ Добавить `tests/__init__.py`
- ✓ Обновить .gitignore если нужно

---

## План выполнения

### Фаза 1: Критические исправления (сегодня)
1. ✓ Удалить `nine/plugins/dnd_audio/`
2. ✓ Проверить и исправить NPCRenderer если нужно
3. ✓ Запустить тесты для проверки работоспособности

### Фаза 2: Улучшения архитектуры (на неделе)
4. ✓ Создать документацию Entity систем
5. ✓ Переместить тестовые файлы
6. ✓ Обновить BACKLOG.md

### Фаза 3: Дополнительные находки
7. ✓ Добавить pre-commit hook для проверки архитектуры
8. ✓ Создать CI проверку с architecture_check.py

---

## Дополнительные рекомендации

### Улучшение plugin системы
- Добавить проверку на дубликаты unique_id при загрузке
- Логировать предупреждение если два плагина с похожими именами

### Улучшение NPCRenderer
- Рассмотреть рефакторинг в PluginModule вместо вспомогательного класса
- Или использовать зависимость через PluginContext

### Code style
- Добавить type hints везде где их нет
- Использовать dataclasses для data transfer objects
- Добавить docstrings ко всем публичным методам

---

## Checklist выполнения

- [ ] Удалить dnd_audio плагин
- [ ] Проверить NPCRenderer
- [ ] Создать docs/ENTITY_SYSTEMS.md
- [ ] Переместить тесты в tests/
- [ ] Обновить BACKLOG.md
- [ ] Запустить architecture_check.py
- [ ] Проверить что всё работает (запустить сервер + клиент)
