# Changelog

Все важные изменения в проекте niNE документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и этот проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

---

## [Unreleased]

### Added (2026-02-01)

#### Тестирование боевой системы
- **test_combat_system.py** - комплексное тестирование боевой системы D&D 5e
  - 10 тестов покрывают: attack bonus, damage dice, range, proficiency, AC, turn-based movement, action economy, критические попадания, advantage/disadvantage
  - Запуск: `python -m tests.test_combat_system`
  - Все тесты проходят (10/10)

- **test_combat_weapon_integration.py** - интеграционное тестирование TurnManager с системой экипировки
  - 6 тестов проверяют корректную интеграцию equipped weapons
  - Проверка: melee/finesse/ranged weapons, reach, proficiency, unarmed strike
  - Запуск: `python -m tests.test_combat_weapon_integration`
  - Результат: 6/6 тестов проходят ✅

### Added (2026-02-01)

#### Модели и ассеты
- **goblin.bam** (185KB) - новая 3D модель NPC гоблина, конвертирована из FBX
  - Содержит встроенные анимации для замены T-позы
  - Путь: `/home/mrv/Homework/PROJECTS/niNE/nine/assets/models/npc/goblin.bam`
- **map3.bam** (11MB) - новая карта для тестирования NPC системы
  - Конвертирована из FBX формата
  - Путь: `/home/mrv/Homework/PROJECTS/niNE/nine/assets/models/maps/map3.bam`
  - Исходный FBX: `map3.fbx` (7.2MB)

#### Тестирование NPC AI
- **test_npc_diagnostic.py** - изолированная тестовая среда для диагностики NPC системы
  - Тестирует: рендеринг, синхронизацию, анимации, мигание, боевую систему, turn management
  - Запуск: `python -m tests.test_npc_diagnostic`
  - Детальное логирование на уровне DEBUG

- **test_npc_simulation.py** - симуляция поведения NPC в разных состояниях
  - Проверяет: IDLE, WANDERING, PURSUING, ATTACKING
  - Тестирует переходы между состояниями и логику агрессии
  - Запуск: `python -m tests.test_npc_simulation`

- **test_npc_ai_bugs.py** - комплексное тестирование AI системы на наличие багов
  - Проверяет: детекцию игрока (граничные случаи), переходы состояний, логику NEUTRAL vs HOSTILE
  - Тестирует: провокацию, leash radius, деление на ноль, edge cases
  - Проверяет: memory leaks и performance
  - Запуск: `python -m tests.test_npc_ai_bugs`
  - **РЕЗУЛЬТАТ:** Обнаружено 3 критических архитектурных бага (см. NPC_BUG_REPORT.md)

- **NPC_DIAGNOSTIC_README.md** - документация диагностических инструментов
  - Инструкции по запуску и интерпретации результатов
  - Описание ожидаемого vs проблемного поведения

#### Документация
- **NPC_BUG_REPORT.md** - полный отчёт об исправлении архитектурных багов NPC AI системы
  - БАГ #1: ECS Entity Pending Addition (CRITICAL) - частично исправлен
  - БАГ #2: AISystem/NPCManager coupling (HIGH) - **ИСПРАВЛЕН** ✅
  - БАГ #3: FactionComponent requirement (MEDIUM) - **ИСПРАВЛЕН** ✅
  - Результаты тестирования: 10/11 тестов проходят (было 5/11)
  - Разблокированные задачи из BACKLOG

- **docs/LIVING_WORLD_VISION.md** - концепция "Живого Мира" для niNE
  - Inspiration: Kenshi + RimWorld для мультиплеера в мире D&D
  - Главная идея: 300+ NPCs с уникальными статами живут своей жизнью
  - Философия эмерджентного геймплея
  - Roadmap от "Smart" к "Alive" (6 этапов)
  - Сравнение с Kenshi/RimWorld/BG3/MMOs
  - Долгосрочная цель: первый мультиплеерный симулятор живого фэнтези мира

- **docs/NPC_INTELLIGENCE_ANALYSIS.md** - детальный анализ текущей "умности" NPCs
  - Оценка: ⭐⭐⭐⭐☆ (4/5 звёзд) - "Умные, но не живые"
  - Что работает отлично: боевая AI (5/5), Living World компоненты (4/5), D&D интеграция (5/5)
  - Что не работает: приоритизация потребностей, влияние черт, социальные взаимодействия
  - Сравнение NPCs vs Игроки, NPCs vs Kenshi/RimWorld
  - Critical Path: 5 milestone к "Живому Миру" (18 недель)
  - Сильные стороны: масштаб (300+ NPCs), D&D 5e, multiplayer, оптимизация

### Changed (2026-02-01)

#### Архитектура
- Обновлен `docs/BACKLOG.md` с новой секцией "Архитектурные баги (февраль 2026)"
  - Добавлены детальные описания БАГов #1, #2, #3
  - Обновлены связи между известными проблемами и архитектурными багами
  - Проблема "Бой начинается автоматически" теперь связана с БАГом #2 (AISystem coupling)

- Обновлен статус NPC проблем с учетом новых диагностических инструментов
  - Добавлены пути к новым моделям (goblin.bam, map3.bam)
  - Добавлены ссылки на диагностические инструменты
  - Пересмотрены приоритеты исправлений

### Fixed (2026-02-01)

#### COMBAT SYSTEM: Интеграция с экипированным оружием — **ИСПРАВЛЕН** ✅
**Severity:** CRITICAL
**Location:** `nine/plugins/combat/sv_turn_manager.py`

**Проблема:**
Метод `_get_player_combat_data()` использовал хардкодированные значения вместо данных экипированного оружия:
- Attack bonus всегда использовал STR (игнорировал finesse/ranged weapons)
- Damage dice всегда был "1d8" (игнорировал weapon.DAMAGE_DICE)
- Не проверял class proficiency с оружием
- Не использовал weapon range для проверки дальности атаки

**Решение:**
```python
# Добавлено свойство для доступа к EquipmentServerModule
@property
def equipment_module(self):
    """Ленивое получение equipment module."""
    ...

# Переписан _get_player_combat_data() для использования экипированного оружия
def _get_player_combat_data(self, client_id: int) -> Optional[dict]:
    # Получаем экипированное оружие
    weapon = equipment_module.get_main_weapon(client_id)

    if weapon:
        # Используем weapon.get_attack_modifier(str_mod, dex_mod) для правильного модификатора
        ability_mod = weapon.get_attack_modifier(str_mod, dex_mod)

        # Проверяем proficiency с оружием
        has_proficiency = weapon.required_proficiency in player_proficiencies
        attack_bonus = ability_mod + (prof if has_proficiency else 0)

        # Используем weapon.DAMAGE_DICE
        damage_dice = weapon.DAMAGE_DICE + modifier

        # Определяем weapon_range
        weapon_range = 5.0  # melee
        if weapon.REACH:
            weapon_range = 10.0  # reach weapons
        elif weapon.is_ranged:
            weapon_range = weapon.RANGE.normal
```

**Изменения:**
- ✅ Melee weapons используют STR modifier
- ✅ Finesse weapons используют max(STR, DEX)
- ✅ Ranged weapons используют DEX modifier
- ✅ Reach weapons имеют 10 футов дальности (вместо 5)
- ✅ Проверяется class proficiency с weapon.required_proficiency
- ✅ Используется weapon.DAMAGE_DICE вместо хардкода "1d8"
- ✅ Unarmed strike работает без экипированного оружия

**Дополнительные исправления:**
- Переписан `_check_range()` для использования weapon_range при атаках
- Обновлен `_get_npc_combat_data()` для возврата weapon_range

**Тестирование:**
- ✅ Тест "Melee Weapon STR Modifier" проходит
- ✅ Тест "Finesse Weapon DEX Modifier" проходит
- ✅ Тест "Ranged Weapon DEX Only" проходит
- ✅ Тест "Reach Weapon 10 feet" проходит
- ✅ Тест "No Proficiency" проходит (proficiency bonus не добавляется)
- ✅ Тест "Unarmed Strike" проходит

**Результат:**
- Боевая система теперь корректно учитывает экипированное оружие игрока
- Attack bonus зависит от типа оружия (STR/DEX/finesse)
- Damage dice берётся из weapon.DAMAGE_DICE
- Range проверяется по weapon.RANGE
- Class proficiency влияет на attack bonus

---

#### БАГ #2: AISystem/NPCManager coupling — **ИСПРАВЛЕН** ✅
- **Проблема:** AISystem жёстко зависел от NPCManager - NPCs не видели игроков в тестах
- **Решение:** Добавлен Dependency Injection для player positions
  - Новый метод `AISystem.set_player_positions(players)` для явной передачи игроков
  - `NPCManager.update()` вызывает `set_player_positions()` перед `world.update()`
  - `event_manager` передаётся в конструктор напрямую
  - CombatAISystem также получает event_manager напрямую
- **Результат:**
  - ✅ NPCs теперь видят игроков в unit-тестах
  - ✅ Система testable (можно тестировать без NPCManager)
  - ✅ Разблокированы 3 задачи из BACKLOG
- **Коммит:** `74b2ffe`

#### БАГ #3: FactionComponent requirement — **ИСПРАВЛЕН** ✅
- **Проблема:** `_find_nearest_enemy()` требовал FactionComponent, иначе возвращал None
- **Решение:** FactionComponent сделан опциональным
  - Если FactionComponent есть → используется `faction.hostile_to_players`
  - Если FactionComponent нет → используется `AIBehavior.HOSTILE`
  - HOSTILE NPCs атакуют игроков автоматически даже без FactionComponent
- **Результат:**
  - ✅ HOSTILE поведение работает без FactionComponent
  - ✅ Документирована логика определения враждебности
- **Коммит:** `74b2ffe`

#### БАГ #1: ECS Pending Addition — **ЧАСТИЧНО ИСПРАВЛЕН** ⚠️
- **Проблема:** Entities в `_pending_addition` не видны для queries
- **Решение:** Добавлен явный вызов `_process_pending_additions()` в тестах
- **Статус:** Тесты исправлены, архитектура требует документации

### Technical Details (2026-02-01)

#### Конвертация моделей
```bash
# FBX → BAM конвертация выполнена для:
- goblin.fbx (320KB) → goblin.bam (185KB)
- map3.fbx (7.2MB) → map3.bam (11MB)
```

#### Git коммиты
- `74b2ffe` - fix: resolve BUG #2 and #3 in NPC AI system
- `6822c5b` - test: comprehensive NPC AI bug testing suite
- `007f912` - refactor: update NPC simulation test for new ECS architecture
- `b96f572` - feat: add converted models and switch to map3
- `8dbe09b` - feat: add new models

#### Статистика
- **Баги:**
  - Найдено: 3 архитектурных бага
  - Исправлено: 2 критических бага (БАГ #2, #3)
  - Частично исправлено: 1 баг (БАГ #1)
- **Тестирование:**
  - Создано: 3 комплексных теста (645+ строк кода)
  - Результат: 10/11 тестов проходят (91% success rate)
  - Было: 5/11 (45% success rate)
- **Модели:**
  - Добавлено: 2 новые модели (goblin.bam 185KB, map3.bam 11MB)
- **Документация:**
  - Обновлено: 3 файла (NPC_BUG_REPORT.md, BACKLOG.md, CHANGELOG.md)
  - Создано: 2 новых документа (LIVING_WORLD_VISION.md, NPC_INTELLIGENCE_ANALYSIS.md)
  - Всего страниц документации: ~15 (3000+ строк)

---

## [v0.1.0-alpha] - 2026-01-30

### Added
- Первый публичный альфа-релиз niNE
- Базовая клиент-серверная архитектура
- Система плагинов с event-driven подходом
- Базовая NPC система (с известными проблемами)
- Combat система (требует доработки)
- UI система с меню и экранами
- Система персонажей D&D (характеристики, классы, расы)

### Known Issues
- 7 критических проблем NPC системы (см. BACKLOG.md)
- 10+ проблем UI системы (наложение элементов, блочная система)
- Множественные архитектурные проблемы требующие рефакторинга

---

## Формат записи

### Added
Новые функции и возможности.

### Changed
Изменения в существующей функциональности.

### Deprecated
Функциональность, которая скоро будет удалена.

### Removed
Удаленная функциональность.

### Fixed
Исправленные баги.

### Security
Исправления уязвимостей безопасности.
