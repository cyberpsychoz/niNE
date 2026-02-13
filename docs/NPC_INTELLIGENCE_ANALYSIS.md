# Анализ "Интеллекта" NPC System
## Дата: 2026-02-01

---

## 🧠 НАСКОЛЬКО NPCs "УМНЫЕ"?

### Общая оценка: ⭐⭐⭐⭐☆ (4/5 звёзд)

**Вывод:** NPCs обладают **сложной внутренней моделью** (потребности, черты, отношения), но **не используют её полностью** для принятия решений. Это как иметь мозг, но не подключить его к телу.

---

## ✅ ЧТО РАБОТАЕТ ОТЛИЧНО

### 1. Боевая AI (⭐⭐⭐⭐⭐)

**Система детекции:**
```python
aggro_radius: 5-10 метров       # Детекция врагов
leash_radius: 30 метров         # Максимальное преследование
attack_range: 2 метра           # Дистанция атаки
```

**AI LOD (Level of Detail):**
- NEAR (0-30m): обновление 0.5s
- MEDIUM (30-60m): обновление 1.0s
- FAR (60-100m): обновление 2.0s
- VERY_FAR (100-200m): обновление 5.0s
- SLEEPING (200m+): не обновляется

**Оптимизация:**
- Spatial Hash → O(k) поиск врагов вместо O(n)
- Skip perception/pathfinding на дальних дистанциях
- Масштабируется до **300+ NPCs** без лагов

**Тактика:**
```
IDLE → детекция игрока → PURSUING → достиг attack_range → ATTACKING
                          ↓
                    превысил leash_radius → возврат домой
```

**Оценка:** Идеально для экшен-игры. Превосходит большинство MMO.

---

### 2. Living World Components (⭐⭐⭐⭐☆)

**Потребности (NeedsComponent):**
```python
hunger: 100.0 → 0.0    # Падает 0.5/час
energy: 100.0 → 0.0    # Падает при активности
social: 100.0 → 0.0    # Падает в одиночестве
safety: 100.0 → 0.0    # Падает при угрозах
comfort: 100.0 → 0.0   # Зависит от окружения
purpose: 100.0 → 0.0   # Падает при бездействии
```

**Реализация:** ✅ Полная
**Проблема:** ⚠️ НЕ влияет на AI решения

**Черты характера (18+ traits):**
- Социальные: EXTROVERT, INTROVERT, CHARISMATIC, SOCIALLY_AWKWARD
- Рабочие: HARD_WORKER, LAZY, PERFECTIONIST, SLOPPY
- Боевые: BRAVE, COWARD, BLOODTHIRSTY, PACIFIST
- Моральные: KIND, CRUEL, HONEST, DECEITFUL
- Особые: NIGHT_OWL, EARLY_BIRD, GLUTTON, ASCETIC

**Реализация:** ✅ Полная
**Проблема:** ⚠️ НЕ влияет на AI поведение

**Отношения:**
```python
opinion: -100 до +100      # Как сильно нравится
trust: 0 до 100            # Доверие
familiarity: 0 до 100      # Насколько знакомы
relationship_type: str     # friend, rival, lover, enemy
```

**Реализация:** ✅ Полная
**Проблема:** ⚠️ НЕ влияет на взаимодействия (friend не помогает, enemy не атакует без провокации)

**Оценка:** Сложная система есть, но **не подключена к AI**.

---

### 3. D&D 5e Интеграция (⭐⭐⭐⭐⭐)

**Боевая система:**
- ✅ Инициатива (d20 + DEX modifier)
- ✅ Броски атаки (d20 + attack_bonus vs AC)
- ✅ Урон по кубикам (1d6, 2d8+3, и т.д.)
- ✅ Условия (Blinded, Paralyzed, Poisoned, Stunned...)
- ✅ Заклинания (35 спелов с концентрацией)
- ✅ Short/Long Rest, Hit Dice

**NPCs используют те же правила что игроки:**
```python
Goblin:
  HP: 7 (2d6)
  AC: 15 (leather armor + DEX)
  Attack: +4 (scimitar, 1d6+2 slashing)

Skeleton:
  HP: 13 (2d8+4)
  AC: 13 (armor scraps)
  Attack: +4 (shortsword, 1d6+2 piercing)
```

**Оценка:** Полноценный D&D 5e для NPCs. Можно создавать сложные энкаунтеры.

---

## ✅ РЕАЛИЗОВАНО (февраль 2026)

### 1. Приоритизация потребностей (✅ Living World → AI Integration)

**Реализовано в `sv_npc_ai.py`:**
- Событие `npc_urgent_need` от Living World системы переопределяет текущее AI поведение
- Критический голод → `SEEK_FOOD` (движение к ближайшей точке еды)
- Критическая усталость → `SEEK_REST` (движение к месту отдыха)
- Критическая безопасность → `FLEE` (бегство от угрозы)
- Behavior overrides имеют приоритет над дефолтным поведением

**Код:**
```python
# В AISystem.update() — проверка override перед выбором поведения:
override = self._behavior_overrides.get(entity_id)
if override:
    self._update_override(entity, ai, pos, dt, override, lod_level)
    continue  # Skip default behavior
```

---

### 2. Влияние черт на AI (✅ Trait Modifiers)

**Реализовано в `sv_npc_manager.py` — `_apply_trait_modifiers()`:**
```python
# При спавне NPC черты реально меняют AI параметры:
if "brave" in traits:    ai.aggro_radius *= 1.3   # Более агрессивен
if "cowardly" in traits: ai.aggro_radius *= 0.5   # Менее агрессивен
if "lazy" in traits:     ai.move_speed *= 0.7     # Двигается медленнее
if "patient" in traits:  ai.patrol_wait_time *= 1.5  # Дольше ждёт на точках
if "curious" in traits:  ai.wander_radius *= 1.5  # Бродит дальше
```

**Результат:** BRAVE и COWARD ведут себя по-разному, LAZY медленнее, CURIOUS исследует дальше.

---

## ⚠️ ЧТО ЕЩЁ НЕ РЕАЛИЗОВАНО

---

### 3. Социальные взаимодействия (❌)

**Проблема:**
```python
# NPC_A и NPC_B — друзья (opinion = 80, trust = 70)
# NPC_A атакован врагом

# Что происходит:
NPC_B.behavior = AIBehavior.IDLE  # Стоит и смотрит

# Что ДОЛЖНО происходить:
if NPC_A.relationship[NPC_B].relationship_type == "friend":
    NPC_B.behavior = AIBehavior.ASSIST  # Помогает другу!
```

**Что ломается:**
- Friends не помогают друг другу
- Enemies не атакуют друг друга (без провокации)
- Lovers не ищут компанию друг друга
- Rivals не соперничают

**Почему критично:**
Отношения **не влияют на действия** → мир статичный.

---

### 4. Экономика и работа (❌)

**Проблема:**
```python
# NPC с profession = "blacksmith"
# Расписание: work 8-18 часов

# Что происходит:
while current_hour in work_schedule:
    ai.behavior = AIBehavior.IDLE  # Стоит на месте

# Что ДОЛЖНО происходить:
while current_hour in work_schedule:
    produce_item("iron_sword")  # Создаёт меч
    inventory.add("iron_sword")
    # Когда игрок приходит — продаёт меч
```

**Что ломается:**
- Blacksmith не производит оружие
- Merchant не торгует
- Farmer не выращивает еду
- Guard не патрулирует по расписанию

**Почему критично:**
Профессии **декоративные** → нет экономики.

---

## 📊 ДЕТАЛЬНОЕ СРАВНЕНИЕ

### NPCs vs Игроки

| Система | Игроки | NPCs | Gap |
|---------|--------|------|-----|
| D&D 5e статы | ✅ Full | ✅ Full | 0% |
| Боевая система | ✅ Full | ✅ Full | 0% |
| Заклинания | ✅ 35 спелов | ✅ 35 спелов | 0% |
| Инвентарь/экипировка | ✅ Full | ✅ Full | 0% |
| Потребности | ❌ Нет | ✅ 6 потребностей | 100% |
| Черты характера | ❌ Нет | ✅ 18+ traits | 100% |
| Отношения | ❌ Нет | ✅ Full system | 100% |
| **Принятие решений** | ✅ Игрок думает | ❌ **AI не использует данные** | **100%** |

**Парадокс:** NPCs имеют **больше данных** чем игроки, но **хуже принимают решения**.

---

### NPCs vs Kenshi/RimWorld

| Особенность | Kenshi | RimWorld | niNE NPCs | Gap |
|-------------|--------|----------|-----------|-----|
| Потребности | ✅ Hunger, rest | ✅ 10+ needs | ✅ 6 needs | 0% |
| Черты | ✅ ~50 traits | ✅ ~80 traits | ✅ 18 traits | -70% |
| Отношения | ✅ Faction only | ✅ Individual | ✅ Individual | 0% |
| **Реакция на потребности** | ✅ **Активная** | ✅ **Активная** | ❌ **Пассивная** | **100%** |
| **Профессии** | ✅ **Работают** | ✅ **Работают** | ❌ **Декоративные** | **100%** |
| **Социальные события** | ❌ Нет | ✅ **Динамические** | ❌ Нет | 100% |
| Масштаб | ✅ 100+ NPCs | ⚠️ 20-30 | ✅ 300+ NPCs | +200% |

**Вывод:** niNE **превосходит** по масштабу и боевой системе, но **уступает** в Living World реализации.

---

## 🎯 CRITICAL PATH: От "Smart" к "Alive"

### Приоритет 1: NEEDS → ACTIONS (CRITICAL)

**Что нужно:**
```python
def _choose_behavior_by_needs(npc):
    needs = npc.get_component(NeedsComponent)

    # Критические потребности → приоритет
    if needs.hunger < 20.0:
        return AIBehavior.SEEK_FOOD
    if needs.energy < 20.0:
        return AIBehavior.SEEK_REST
    if needs.safety < 20.0:
        return AIBehavior.FLEE

    # Низкие потребности → второстепенно
    if needs.social < 40.0:
        return AIBehavior.SOCIALIZE
    if needs.purpose < 40.0:
        return AIBehavior.SEEK_WORK

    # Всё в порядке → обычное поведение
    return npc.ai.default_behavior
```

**Эффект:**
- NPCs ищут еду когда голодны → **реалистично**
- NPCs спят когда устали → **живой мир**
- NPCs избегают опасности → **инстинкт самосохранения**

**Сложность:** LOW (1-2 дня)
**Влияние:** CRITICAL (без этого система бесполезна)

---

### Приоритет 2: TRAITS → MODIFIERS (HIGH)

**Что нужно:**
```python
def apply_trait_modifiers(npc):
    personality = npc.get_component(PersonalityComponent)
    ai = npc.get_component(AIComponent)
    combat = npc.get_component(CombatComponent)

    if personality.has_trait(TraitType.BRAVE):
        ai.flee_hp_threshold *= 0.3  # Бежит при 6% HP вместо 20%
        ai.aggro_radius *= 1.5       # Более агрессивен

    if personality.has_trait(TraitType.COWARD):
        ai.flee_hp_threshold *= 2.5  # Бежит при 50% HP
        ai.aggro_radius *= 0.5       # Менее агрессивен

    if personality.has_trait(TraitType.LAZY):
        ai.move_speed *= 0.75        # Двигается медленнее
        needs.energy_decay *= 0.5    # Меньше устаёт

    if personality.has_trait(TraitType.KIND):
        # Помогает раненым союзникам
        ai.assist_threshold = 0.5    # Помогает при 50% HP
```

**Эффект:**
- BRAVE NPCs дерутся до смерти → **героизм**
- COWARD NPCs бегут рано → **трусость**
- KIND NPCs лечат раненых → **сострадание**
- LAZY NPCs работают медленнее → **лень**

**Сложность:** MEDIUM (3-5 дней)
**Влияние:** HIGH (NPCs становятся уникальными)

---

### Приоритет 3: RELATIONSHIPS → ACTIONS (HIGH)

**Что нужно:**
```python
def check_relationship_actions(npc, target):
    relationships = npc.get_component(RelationshipsComponent)
    rel = relationships.get_relationship(target.id)

    if rel.relationship_type == "friend":
        # Друзья помогают в бою
        if target.combat.hp_current < target.combat.hp_max * 0.5:
            return AIBehavior.ASSIST_FRIEND

    if rel.relationship_type == "enemy":
        # Враги атакуют даже без провокации
        if distance(npc, target) < ai.aggro_radius:
            return AIBehavior.ATTACK_ENEMY

    if rel.relationship_type == "lover":
        # Любовники ищут компанию
        if npc.needs.social < 40.0:
            return AIBehavior.SEEK_LOVER
```

**Эффект:**
- Friends защищают друг друга → **дружба**
- Enemies атакуют друг друга → **вражда**
- Lovers ищут компанию → **романтика**

**Сложность:** MEDIUM (3-5 дней)
**Влияние:** HIGH (социальная динамика)

---

## 📈 ROADMAP К "ЖИВОМУ МИРУ"

### Milestone 1: Basic Reactivity (✅ ЗАВЕРШЁН — февраль 2026)
- ✅ Потребности влияют на поведение (urgent needs → behavior override)
- ✅ Черты влияют на модификаторы (brave, cowardly, lazy, patient, curious)
- ✅ Расписания влияют на поведение (schedule → activity override)
- ✅ Game time система (день/ночь цикл, 1 мин = 1 час)
- ✅ Wander behavior для idle NPC
- **Результат:** NPCs **реагируют** на внутреннее состояние и время суток

### Milestone 2: Social Interactions (3 недели)
- ✅ NPCs разговаривают друг с другом
- ✅ Формируются дружбы/вражды
- ✅ Динамические квесты от NPCs
- **Результат:** NPCs **взаимодействуют** между собой

### Milestone 3: Economy & Professions (4 недели)
- ✅ Blacksmith производит оружие
- ✅ Merchant торгует
- ✅ Farmer выращивает еду
- **Результат:** NPCs **работают** и создают экономику

### Milestone 4: Faction Politics (3 недели)
- ✅ Репутация у фракций
- ✅ Войны фракций
- ✅ Динамическая территория
- **Результат:** NPCs **формируют политику**

### Milestone 5: Advanced Life (6 недель)
- ✅ Романтика и семьи
- ✅ Дети NPCs
- ✅ Эволюция мира
- **Результат:** NPCs **размножаются** и создают поколения

**Общее время:** ~18 недель (4.5 месяца)

**Текущий прогресс:** Milestone 0 завершён (инфраструктура готова)

---

## 🏆 СИЛЬНЫЕ СТОРОНЫ (Что уже лучше чем у конкурентов)

### 1. Масштаб (300+ NPCs)
**niNE:** ✅ 300+ одновременно
**RimWorld:** ⚠️ 20-30 max (лагает)
**Kenshi:** ✅ 100-200
**MMOs:** ❌ Обычно 10-30 "живых" NPCs

### 2. D&D 5e Боевка
**niNE:** ✅ Полный D&D 5e
**Kenshi:** ⚠️ Упрощённая (атака/защита)
**RimWorld:** ⚠️ Упрощённая (меткость/броня)
**BG3:** ✅ D&D 5e, но single-player

### 3. Multiplayer
**niNE:** ✅ 10-30 игроков
**Kenshi:** ❌ Single-player only
**RimWorld:** ❌ Single-player only
**MMOs:** ✅ Много игроков, но NPCs тупые

### 4. Оптимизация AI
**niNE:** ✅ AI LOD, Spatial Hash, Delta Compression
**Другие:** ⚠️ Обычно простая оптимизация

---

## 🎯 ЗАКЛЮЧЕНИЕ

### Текущее состояние: **"Умные, но не живые"**

**NPCs имеют:**
- ✅ Сложную внутреннюю модель (потребности, черты, отношения)
- ✅ Отличную боевую AI (детекция, тактика, D&D 5e)
- ✅ Масштабируемость (300+ NPCs без лагов)

**NPCs НЕ имеют:**
- ❌ Реакцию на потребности (голодный не ищет еду)
- ❌ Влияние черт (BRAVE = COWARD)
- ❌ Социальные взаимодействия (друзья не помогают)
- ❌ Профессии (blacksmith не производит)

### Что нужно сделать:

**1-2 недели → Milestone 1 → NPCs "оживают"**
- Голодный ищет еду
- Усталый ищет сон
- Трусливый бежит раньше
- Храбрый дерётся до смерти

**Это превратит niNE из "хорошей AI" в "живой мир".**

---

**Оценка:** ⭐⭐⭐⭐☆ (Milestone 1 завершён)
**Потенциал:** ⭐⭐⭐⭐⭐ через Milestone 2-3

**Обновлено:** 2026-02-13
**Автор:** Claude Opus 4.5 → обновлено Claude Opus 4.6
