# COMBAT SYSTEM INTEGRATION FIX REPORT
## Дата исправления: 2026-02-01

---

## ✅ ИСПРАВЛЕННЫЕ ПРОБЛЕМЫ

### COMBAT BUG: Игнорирование экипированного оружия — **ИСПРАВЛЕН**
**Severity:** CRITICAL
**Location:** `nine/plugins/combat/sv_turn_manager.py:_get_player_combat_data()`

**Проблема:**
Боевая система НЕ использовала экипированное оружие игрока. Все расчёты атаки и урона были хардкодированы.

**Код (до исправления):**
```python
def _get_player_combat_data(self, client_id: int) -> Optional[dict]:
    char = self.app.db.get_character(char_uuid)
    if char:
        str_mod = (char.get("strength", 10) - 10) // 2
        prof = char.get("proficiency_bonus", 2)

        return {
            "attack_bonus": str_mod + prof,  # ❌ ВСЕГДА STR
            "damage_dice": "1d8+" + str(str_mod),  # ❌ ВСЕГДА 1d8
        }
```

**Проблемы:**
1. ❌ Attack bonus ВСЕГДА использовал STR (не учитывал finesse/ranged weapons)
2. ❌ Damage dice ВСЕГДА был "1d8" (не использовал weapon.DAMAGE_DICE)
3. ❌ НЕ проверял class proficiency с оружием
4. ❌ НЕ учитывал weapon range (melee 5ft, reach 10ft, ranged 80+ft)
5. ❌ НЕ поддерживал unarmed strike

**Влияние:**
- Игрок с DEX 18 + rapier (finesse) использовал STR вместо DEX → неправильный бонус атаки
- Ranger с shortbow (1d6 ranged) наносил 1d8 урона вместо 1d6
- Wizard без martial proficiency получал proficiency bonus с longsword
- Все атаки имели дальность 5 футов (action.range_feet), даже с shortbow
- Невозможно атаковать безоружным (unarmed strike)

**Решение (с интеграцией экипировки):**
```python
def _get_player_combat_data(self, client_id: int) -> Optional[dict]:
    """
    Получает боевые данные игрока с учетом экипированного оружия.

    Учитывает:
    - Экипированное оружие в main_hand
    - Свойства оружия (finesse, ranged, reach)
    - Класс игрока и proficiency с оружием
    - Дальность оружия
    """
    # Получаем персонажа
    char = self.app.db.get_character(char_uuid)

    # Вычисляем модификаторы
    str_mod = (char.get("strength", 10) - 10) // 2
    dex_mod = (char.get("dexterity", 10) - 10) // 2
    prof = char.get("proficiency_bonus", 2)

    # Получаем экипированное оружие через EquipmentServerModule
    equipment_module = self.equipment_module
    weapon = equipment_module.get_main_weapon(client_id)

    if weapon:
        # ✅ Используем weapon.get_attack_modifier() для правильного модификатора
        ability_mod = weapon.get_attack_modifier(str_mod, dex_mod)

        # ✅ Проверяем proficiency с оружием
        player_proficiencies = char.get("proficiencies", [])
        has_proficiency = weapon.required_proficiency in player_proficiencies

        # ✅ Бонус атаки = ability modifier + proficiency (если есть)
        attack_bonus = ability_mod + (prof if has_proficiency else 0)

        # ✅ Используем weapon.DAMAGE_DICE
        damage_dice = weapon.DAMAGE_DICE
        if ability_mod != 0:
            sign = "+" if ability_mod > 0 else ""
            damage_dice += f"{sign}{ability_mod}"

        # ✅ Определяем weapon_range
        weapon_range = 5.0  # По умолчанию melee 5 футов
        if weapon.REACH:
            weapon_range = 10.0  # Reach weapons 10 футов
        elif weapon.is_ranged:
            weapon_range = weapon.RANGE.normal
        elif weapon.THROWN:
            weapon_range = weapon.RANGE.normal

        return {
            "attack_bonus": attack_bonus,
            "damage_dice": damage_dice,
            "weapon_range": weapon_range,
            "is_ranged": weapon.is_ranged,
            "has_proficiency": has_proficiency,
        }

    # ✅ Без оружия - unarmed strike
    else:
        damage = 1 + str_mod
        damage_dice = "1" if damage <= 1 else f"1+{damage - 1}"

        return {
            "attack_bonus": str_mod + prof,
            "damage_dice": damage_dice,
            "weapon_range": 5.0,
            "is_ranged": False,
            "has_proficiency": True,
        }
```

**Изменения в `_check_range()`:**
```python
def _check_range(self, actor_id: str, target_id: str, action) -> dict:
    """
    Проверяет, находится ли цель в пределах дальности.

    Для атак использует дальность экипированного оружия.
    Для других действий использует action.range_feet.
    """
    distance = self._calculate_distance(actor_pos, target_pos)
    required_range = action.range_feet

    # ✅ Для атаки используем дальность оружия
    if action.id == "attack":
        player_data = self._get_player_combat_data(client_id)
        if player_data and "weapon_range" in player_data:
            required_range = player_data["weapon_range"]

    return {
        "in_range": distance <= required_range,
        "distance": distance,
        "required_range": required_range,
    }
```

**Добавлено свойство для доступа к EquipmentServerModule:**
```python
@property
def equipment_module(self):
    """Ленивое получение equipment module."""
    if not hasattr(self, '_equipment_module'):
        self._equipment_module = None
    if self._equipment_module is None:
        if hasattr(self.app, 'plugin_manager'):
            inventory_plugin = self.app.plugin_manager.get_plugin("nine.inventory")
            if inventory_plugin:
                for module in inventory_plugin.modules:
                    if hasattr(module, 'get_main_weapon'):
                        self._equipment_module = module
                        break
    return self._equipment_module
```

**Обновлён `_get_npc_combat_data()`:**
```python
def _get_npc_combat_data(self, entity_id: str) -> Optional[dict]:
    """Получает боевые данные NPC."""
    combat = entity.get_component(CombatComponent)
    if combat:
        # ✅ Добавлен weapon_range для NPC (по умолчанию 5.0)
        weapon_range = 5.0
        if hasattr(combat, 'weapon_range'):
            weapon_range = combat.weapon_range

        return {
            "attack_bonus": combat.attack_bonus,
            "damage_dice": f"{combat.damage_dice}+{combat.damage_bonus}",
            "weapon_range": weapon_range,
        }
```

---

## 📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ

### Integration Tests (test_combat_weapon_integration.py):
```
Tests Run: 6
✓ Passed: 6
✗ Failed: 0
```

| Тест | Статус | Проверка |
|------|--------|----------|
| Melee Weapon STR Modifier | ✅ PASS | Longsword использует STR (+3) + Prof (+2) = +5 |
| Finesse Weapon DEX Modifier | ✅ PASS | Rapier использует DEX (+4) вместо STR (+0) |
| Ranged Weapon DEX Only | ✅ PASS | Shortbow использует DEX (+3), range 80 футов |
| Reach Weapon 10 feet | ✅ PASS | Glaive имеет range 10.0 вместо 5.0 |
| No Proficiency | ✅ PASS | Wizard с longsword не получает proficiency bonus |
| Unarmed Strike | ✅ PASS | Monk без оружия наносит 1+STR урона |

### Comprehensive Tests (test_combat_system.py):
```
Tests Run: 10
✓ Passed: 10
✗ Failed: 0
```

---

## 🎯 ЧТО РАБОТАЕТ СЕЙЧАС

### ✅ Melee Weapons (STR)
- **Longsword (1d8 slashing, martial):**
  - Fighter STR 16 (+3), Prof +2
  - Attack bonus: +5 (STR+Prof)
  - Damage: 1d8+3
  - Range: 5 feet

### ✅ Finesse Weapons (best of STR/DEX)
- **Rapier (1d8 piercing, finesse, martial):**
  - Rogue STR 10 (+0), DEX 18 (+4), Prof +2
  - Attack bonus: +6 (DEX+Prof, uses DEX instead of STR!)
  - Damage: 1d8+4
  - Range: 5 feet

### ✅ Ranged Weapons (DEX)
- **Shortbow (1d6 piercing, ranged 80/160, simple):**
  - Ranger STR 14 (+2), DEX 16 (+3), Prof +2
  - Attack bonus: +5 (DEX+Prof, ignores STR!)
  - Damage: 1d6+3
  - Range: 80 feet (normal), 160 feet (disadvantage)

### ✅ Reach Weapons (10 feet)
- **Glaive (1d10 slashing, reach, two-handed, martial):**
  - Fighter STR 16 (+3), Prof +2
  - Attack bonus: +5 (STR+Prof)
  - Damage: 1d10+3
  - Range: 10 feet (instead of 5!)

### ✅ Class Proficiency
- **Fighter + Longsword:** +5 (STR+3 + Prof+2) ✓
- **Wizard + Longsword:** +1 (STR+1 only, no Prof) ✓
- **Rogue + Rapier:** +6 (DEX+4 + Prof+2, has simple weapons & finesse proficiency) ✓

### ✅ Unarmed Strike
- **Monk без оружия:**
  - STR 14 (+2), Prof +2
  - Attack bonus: +4 (STR+Prof)
  - Damage: 1+2 = 3 (1 base + STR modifier)
  - Range: 5 feet

---

## 🔧 ТЕХНИЧЕСКИЕ ДЕТАЛИ

### weapon.get_attack_modifier() логика:
```python
def get_attack_modifier(self, str_mod: int, dex_mod: int) -> int:
    """Определяет модификатор атаки."""
    if self.is_ranged:
        # Дальнобойное всегда использует DEX
        return dex_mod
    elif self.FINESSE:
        # Фехтовальное — лучший из STR/DEX
        return max(str_mod, dex_mod)
    elif self.THROWN:
        # Метательное — STR (или DEX если finesse)
        return str_mod
    else:
        # Обычное рукопашное — STR
        return str_mod
```

### Weapon Range определение:
```python
weapon_range = 5.0  # По умолчанию melee 5 футов

if weapon.REACH:
    weapon_range = 10.0  # Reach weapons (pike, glaive, whip)
elif weapon.is_ranged:
    weapon_range = weapon.RANGE.normal  # Shortbow 80, Longbow 150
elif weapon.THROWN:
    weapon_range = weapon.RANGE.normal  # Handaxe 20, Javelin 30
```

### Proficiency проверка:
```python
player_proficiencies = char.get("proficiencies", [])
# ["simple_weapons", "martial_weapons", "light_armor", ...]

weapon_proficiency = weapon.required_proficiency
# "martial_weapons" for longsword, rapier, glaive
# "simple_weapons" for shortbow, dagger, club

has_proficiency = weapon_proficiency in player_proficiencies
attack_bonus = ability_mod + (prof if has_proficiency else 0)
```

---

## 📝 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### Пример 1: Fighter с Longsword
```python
# Character: Fighter Level 1
# STR 16 (+3), DEX 12 (+1), Prof +2
# Proficiencies: simple_weapons, martial_weapons

# Equipped: Longsword (1d8, martial, not finesse)

combat_data = turn_manager._get_player_combat_data(client_id)
# {
#     "attack_bonus": 5,  # STR(+3) + Prof(+2)
#     "damage_dice": "1d8+3",
#     "weapon_range": 5.0,
#     "is_ranged": False,
#     "has_proficiency": True,
# }
```

### Пример 2: Rogue с Rapier (Finesse)
```python
# Character: Rogue Level 1
# STR 10 (+0), DEX 18 (+4), Prof +2
# Proficiencies: simple_weapons, martial_weapons (rapier)

# Equipped: Rapier (1d8, finesse, martial)

combat_data = turn_manager._get_player_combat_data(client_id)
# {
#     "attack_bonus": 6,  # max(STR+0, DEX+4) + Prof(+2) = DEX(+4) + Prof(+2)
#     "damage_dice": "1d8+4",
#     "weapon_range": 5.0,
#     "is_ranged": False,
#     "has_proficiency": True,
# }
```

### Пример 3: Ranger с Shortbow
```python
# Character: Ranger Level 1
# STR 14 (+2), DEX 16 (+3), Prof +2
# Proficiencies: simple_weapons, martial_weapons

# Equipped: Shortbow (1d6, ranged 80/160, simple)

combat_data = turn_manager._get_player_combat_data(client_id)
# {
#     "attack_bonus": 5,  # DEX(+3) + Prof(+2), ignores STR!
#     "damage_dice": "1d6+3",
#     "weapon_range": 80.0,  # weapon.RANGE.normal
#     "is_ranged": True,
#     "has_proficiency": True,
# }
```

### Пример 4: Wizard без Proficiency
```python
# Character: Wizard Level 1
# STR 12 (+1), DEX 14 (+2), Prof +2
# Proficiencies: simple_weapons (NO martial_weapons!)

# Equipped: Longsword (1d8, martial)

combat_data = turn_manager._get_player_combat_data(client_id)
# {
#     "attack_bonus": 1,  # STR(+1) only, no Prof bonus!
#     "damage_dice": "1d8+1",
#     "weapon_range": 5.0,
#     "is_ranged": False,
#     "has_proficiency": False,  # ❌ No martial_weapons proficiency
# }
```

### Пример 5: Unarmed Strike
```python
# Character: Monk Level 1
# STR 14 (+2), DEX 16 (+3), Prof +2
# No weapon equipped

combat_data = turn_manager._get_player_combat_data(client_id)
# {
#     "attack_bonus": 4,  # STR(+2) + Prof(+2)
#     "damage_dice": "1+2",  # 1 base damage + STR(+2)
#     "weapon_range": 5.0,
#     "is_ranged": False,
#     "has_proficiency": True,  # Everyone can punch
# }
```

---

## 🎉 ЗАКЛЮЧЕНИЕ

**Боевая система успешно интегрирована с системой экипировки:**
- ✅ Attack bonus зависит от типа оружия (STR/DEX/finesse)
- ✅ Damage dice берётся из weapon.DAMAGE_DICE
- ✅ Range проверяется по weapon.RANGE (melee 5, reach 10, ranged 80-150)
- ✅ Class proficiency влияет на attack bonus
- ✅ Unarmed strike работает без экипированного оружия
- ✅ 6/6 интеграционных тестов проходят
- ✅ 10/10 комплексных тестов проходят

**Система готова для:**
- Полноценного turn-based combat с учётом экипировки
- Различных классов персонажей (Fighter, Rogue, Ranger, Wizard)
- Всех типов оружия D&D 5e (melee, finesse, ranged, reach, thrown)
- Проверки proficiency с оружием
- Расчёта дальности атаки

---

**Автор:** Claude Sonnet 4.5
**Дата:** 2026-02-01
**Коммит:** (следующий коммит после документации)
