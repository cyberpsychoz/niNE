"""
Серверный модуль листа персонажа.

Управляет данными персонажа:
- Полный лист D&D персонажа
- Характеристики, навыки, спасброски
- Классовые и расовые особенности
- Заклинания и слоты
- Синхронизация с клиентом
"""

from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from nine.core.plugins import PluginModule

# Импортируем D&D константы
try:
    from nine.plugins.dnd.sh_constants import (
        SKILLS, CLASSES, RACES, BACKGROUNDS, FEATURES, ABILITIES,
        calculate_modifier, calculate_proficiency_bonus
    )
except ImportError:
    # Fallback если модуль не загружен
    SKILLS = {}
    CLASSES = {}
    RACES = {}
    BACKGROUNDS = {}
    FEATURES = {}
    ABILITIES = {}
    def calculate_modifier(x): return (x - 10) // 2
    def calculate_proficiency_bonus(lvl): return 2 + (lvl - 1) // 4


@dataclass
class CharacterDescription:
    """Описание персонажа, видимое другим игрокам."""
    appearance: str = ""
    age: str = ""
    build: str = ""
    features: str = ""
    demeanor: str = ""


class CharacterSheetServerModule(PluginModule):
    """
    Серверный модуль управления листами персонажей.
    Загружает полные данные из БД и синхронизирует с клиентами.
    """

    def on_load(self):
        # {player_uuid: full_character_data}
        self.characters: Dict[str, dict] = {}

        # Кэш активных условий {player_uuid: [condition_ids]}
        self.active_conditions: Dict[str, List[str]] = {}

        # Подписки на события
        self.event_manager.subscribe("player_joined", self.on_player_join)
        self.event_manager.subscribe("player_left", self.on_player_leave)
        self.event_manager.subscribe("character_selected", self.on_character_selected)
        self.event_manager.subscribe("character_update_description", self.on_update_description)
        self.event_manager.subscribe("character_update_name", self.on_update_name)
        self.event_manager.subscribe("request_character_sheet", self.on_request_character)
        self.event_manager.subscribe("request_other_character", self.on_request_other_character)
        self.event_manager.subscribe("equipment_stats_updated", self.on_equipment_stats_updated)
        self.event_manager.subscribe("condition_applied", self.on_condition_applied)
        self.event_manager.subscribe("condition_removed", self.on_condition_removed)

        self.logger.info("Серверный модуль листа персонажа загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("player_joined", self.on_player_join)
        self.event_manager.unsubscribe("player_left", self.on_player_leave)
        self.event_manager.unsubscribe("character_selected", self.on_character_selected)
        self.event_manager.unsubscribe("character_update_description", self.on_update_description)
        self.event_manager.unsubscribe("character_update_name", self.on_update_name)
        self.event_manager.unsubscribe("request_character_sheet", self.on_request_character)
        self.event_manager.unsubscribe("request_other_character", self.on_request_other_character)
        self.event_manager.unsubscribe("equipment_stats_updated", self.on_equipment_stats_updated)
        self.event_manager.unsubscribe("condition_applied", self.on_condition_applied)
        self.event_manager.unsubscribe("condition_removed", self.on_condition_removed)

        self.logger.info("Серверный модуль листа персонажа выгружен")

    # =========================================================================
    # Event handlers
    # =========================================================================

    def on_player_join(self, data: dict):
        """Игрок присоединился."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return
        self.active_conditions[player_uuid] = []

    def on_character_selected(self, data: dict):
        """Игрок выбрал персонажа — загружаем полный лист из БД."""
        player_uuid = data.get("uuid")
        char_uuid = data.get("character_uuid")

        if not player_uuid or not char_uuid:
            return

        # Загружаем из БД
        if hasattr(self.app, 'db') and self.app.db:
            char_data = self.app.db.get_character(char_uuid)
            if char_data:
                self.characters[player_uuid] = self._build_full_character(char_data)
                self._send_character_sheet(player_uuid)
                self.logger.debug(f"Лист персонажа {char_uuid} загружен для {player_uuid}")
                return

        # Fallback — создаём базовый лист
        player_name = data.get("name", "Игрок")
        self.characters[player_uuid] = self._create_default_character(player_name)
        self._send_character_sheet(player_uuid)

    def on_player_leave(self, data: dict):
        """Игрок вышел — сохраняем и очищаем."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        if player_uuid in self.characters:
            del self.characters[player_uuid]
        if player_uuid in self.active_conditions:
            del self.active_conditions[player_uuid]

    def on_update_description(self, data: dict):
        """Обновление описания персонажа."""
        player_uuid = data.get("uuid")
        field_name = data.get("field")
        value = data.get("value", "")

        if not player_uuid or not field_name:
            return
        if player_uuid not in self.characters:
            return

        # Разрешённые поля - старые + новое "text"
        allowed_fields = ["appearance", "age", "build", "features", "demeanor", "text"]
        if field_name not in allowed_fields:
            return

        # Для "text" разрешаем больше символов (2000)
        max_length = 2000 if field_name == "text" else 500
        value = value[:max_length]

        if "description" not in self.characters[player_uuid]:
            self.characters[player_uuid]["description"] = {}

        self.characters[player_uuid]["description"][field_name] = value

        # Сохраняем в БД если есть
        if hasattr(self.app, 'db') and self.app.db:
            char_uuid = self.characters[player_uuid].get("uuid")
            if char_uuid:
                try:
                    # Сериализуем описание в JSON для хранения
                    import json
                    desc_json = json.dumps(self.characters[player_uuid]["description"])
                    self.app.db.update_character(char_uuid, {"description": desc_json})
                except Exception as e:
                    self.logger.warning(f"Не удалось сохранить описание: {e}")

        self._send_character_sheet(player_uuid)

    def on_update_name(self, data: dict):
        """Изменение имени персонажа."""
        player_uuid = data.get("uuid")
        new_name = data.get("name", "").strip()

        if not player_uuid or not new_name:
            return
        if player_uuid not in self.characters:
            return

        new_name = new_name[:50]
        old_name = self.characters[player_uuid].get("name", "")
        self.characters[player_uuid]["name"] = new_name

        self._send_character_sheet(player_uuid)

        self.event_manager.post("character_name_changed", {
            "uuid": player_uuid,
            "old_name": old_name,
            "new_name": new_name,
        })

    def on_request_character(self, data: dict):
        """Запрос листа персонажа."""
        player_uuid = data.get("uuid")
        if player_uuid:
            self._send_character_sheet(player_uuid)

    def on_request_other_character(self, data: dict):
        """Запрос информации о другом персонаже (только публичная)."""
        requester_uuid = data.get("uuid")
        target_uuid = data.get("target_uuid")

        if not requester_uuid or not target_uuid:
            return
        if target_uuid not in self.characters:
            return

        target = self.characters[target_uuid]
        public_info = {
            "uuid": target_uuid,
            "description": target.get("description", {}),
            "race": target.get("race", "human"),
        }

        # Используем dnd_send_to_client для отправки клиенту
        self.event_manager.post("dnd_send_to_client", {
            "client_id": requester_uuid,
            "data": {"type": "other_character_info", "character": public_info}
        })

    def on_equipment_stats_updated(self, data: dict):
        """Обновились бонусы от экипировки."""
        player_uuid = data.get("uuid")
        bonuses = data.get("bonuses", {})

        if not player_uuid or player_uuid not in self.characters:
            return

        self.characters[player_uuid]["equipment_bonuses"] = bonuses
        self._recalculate_derived_stats(player_uuid)
        self._send_character_sheet(player_uuid)

    def on_condition_applied(self, data: dict):
        """Применено условие (condition)."""
        player_uuid = data.get("entity_id")
        condition_id = data.get("condition_id")

        if not player_uuid or not condition_id:
            return
        if player_uuid not in self.active_conditions:
            self.active_conditions[player_uuid] = []

        if condition_id not in self.active_conditions[player_uuid]:
            self.active_conditions[player_uuid].append(condition_id)
            self._send_character_sheet(player_uuid)

    def on_condition_removed(self, data: dict):
        """Снято условие (condition)."""
        player_uuid = data.get("entity_id")
        condition_id = data.get("condition_id")

        if not player_uuid or not condition_id:
            return
        if player_uuid in self.active_conditions:
            if condition_id in self.active_conditions[player_uuid]:
                self.active_conditions[player_uuid].remove(condition_id)
                self._send_character_sheet(player_uuid)

    # =========================================================================
    # Character Building
    # =========================================================================

    def _build_full_character(self, db_data: dict) -> dict:
        """Строит полный лист персонажа из данных БД."""
        char_class = db_data.get("class", "fighter")
        race = db_data.get("race", "human")
        background = db_data.get("background", "")
        level = db_data.get("level", 1)

        # Базовые характеристики
        strength = db_data.get("strength", 10)
        dexterity = db_data.get("dexterity", 10)
        constitution = db_data.get("constitution", 10)
        intelligence = db_data.get("intelligence", 10)
        wisdom = db_data.get("wisdom", 10)
        charisma = db_data.get("charisma", 10)

        # Модификаторы
        str_mod = calculate_modifier(strength)
        dex_mod = calculate_modifier(dexterity)
        con_mod = calculate_modifier(constitution)
        int_mod = calculate_modifier(intelligence)
        wis_mod = calculate_modifier(wisdom)
        cha_mod = calculate_modifier(charisma)

        prof_bonus = calculate_proficiency_bonus(level)

        # Данные класса
        class_data = CLASSES.get(char_class, {})
        race_data = RACES.get(race, {})
        background_data = BACKGROUNDS.get(background, {})

        # Спасброски (saving throws)
        saving_throws = self._build_saving_throws(
            class_data.get("saving_throws", []),
            {
                "strength": str_mod, "dexterity": dex_mod, "constitution": con_mod,
                "intelligence": int_mod, "wisdom": wis_mod, "charisma": cha_mod
            },
            prof_bonus
        )

        # Навыки (skills)
        skill_proficiencies = db_data.get("skills", {})
        if isinstance(skill_proficiencies, str):
            import json
            try:
                skill_proficiencies = json.loads(skill_proficiencies)
            except:
                skill_proficiencies = {}

        skills = self._build_skills(
            skill_proficiencies,
            {
                "strength": str_mod, "dexterity": dex_mod, "constitution": con_mod,
                "intelligence": int_mod, "wisdom": wis_mod, "charisma": cha_mod
            },
            prof_bonus
        )

        # Особенности (features)
        features = self._build_features(race, char_class, background, level, db_data.get("class_features", []))

        # Заклинания
        spells_known = db_data.get("spells_known", [])
        spells_prepared = db_data.get("spells_prepared", [])
        spell_slots_current = db_data.get("spell_slots_current", {})
        spell_slots_max = db_data.get("spell_slots_max", {})

        # Hit Dice
        hit_die = class_data.get("hit_die", 8)
        hit_dice_current = db_data.get("hit_dice_current", level)
        hit_dice_max = db_data.get("hit_dice_max", level)

        # Владения (proficiencies)
        proficiencies = self._build_proficiencies(class_data, race_data, background_data, db_data.get("proficiencies", {}))

        return {
            "uuid": db_data.get("uuid", ""),
            "name": db_data.get("character_name", "Незнакомец"),
            "race": race,
            "race_name": race_data.get("name", race),
            "class": char_class,
            "class_name": class_data.get("name", char_class),
            "background": background,
            "background_name": background_data.get("name", background) if background else "",
            "level": level,
            "experience": db_data.get("experience", 0),
            "xp_to_next": self._xp_for_level(level + 1),

            # Характеристики
            "abilities": {
                "strength": {"value": strength, "modifier": str_mod},
                "dexterity": {"value": dexterity, "modifier": dex_mod},
                "constitution": {"value": constitution, "modifier": con_mod},
                "intelligence": {"value": intelligence, "modifier": int_mod},
                "wisdom": {"value": wisdom, "modifier": wis_mod},
                "charisma": {"value": charisma, "modifier": cha_mod},
            },

            # Боевые статы
            "hp_current": db_data.get("hp_current", 10),
            "hp_max": db_data.get("hp_max", 10),
            "hp_temp": 0,
            "armor_class": db_data.get("armor_class", 10 + dex_mod),
            "initiative": dex_mod,
            "speed": race_data.get("speed", 30),
            "proficiency_bonus": prof_bonus,

            # Hit Dice
            "hit_die": f"d{hit_die}",
            "hit_dice_current": hit_dice_current,
            "hit_dice_max": hit_dice_max,

            # Спасброски и навыки
            "saving_throws": saving_throws,
            "skills": skills,

            # Особенности
            "features": features,

            # Владения
            "proficiencies": proficiencies,

            # Заклинания
            "spellcasting": {
                "ability": class_data.get("spellcasting_ability", ""),
                "spell_save_dc": 8 + prof_bonus + self._get_spellcasting_mod(class_data, {
                    "intelligence": int_mod, "wisdom": wis_mod, "charisma": cha_mod
                }),
                "spell_attack": prof_bonus + self._get_spellcasting_mod(class_data, {
                    "intelligence": int_mod, "wisdom": wis_mod, "charisma": cha_mod
                }),
                "spells_known": spells_known,
                "spells_prepared": spells_prepared,
                "spell_slots_current": spell_slots_current,
                "spell_slots_max": spell_slots_max,
            } if class_data.get("spellcaster") else None,

            # Описание - загружаем из БД если есть
            "description": self._load_description(db_data.get("description", {})),

            # Бонусы экипировки
            "equipment_bonuses": {},

            # Для совместимости со старым кодом
            "stats": {
                "strength": strength,
                "dexterity": dexterity,
                "constitution": constitution,
                "intelligence": intelligence,
                "wisdom": wisdom,
                "charisma": charisma,
                "str_mod": str_mod,
                "dex_mod": dex_mod,
                "con_mod": con_mod,
                "int_mod": int_mod,
                "wis_mod": wis_mod,
                "cha_mod": cha_mod,
                "level": level,
                "experience": db_data.get("experience", 0),
                "max_hp": db_data.get("hp_max", 10),
                "current_hp": db_data.get("hp_current", 10),
                "temp_hp": 0,
                "base_speed": race_data.get("speed", 30),
                "proficiency_bonus": prof_bonus,
                "proficiencies": proficiencies.get("all", []),
                "languages": proficiencies.get("languages", ["Common"]),
            },
        }

    def _create_default_character(self, name: str) -> dict:
        """Создаёт базовый лист персонажа."""
        return self._build_full_character({
            "character_name": name,
            "race": "human",
            "class": "fighter",
            "level": 1,
            "strength": 10,
            "dexterity": 10,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10,
            "hp_current": 10,
            "hp_max": 10,
        })

    def _build_saving_throws(self, proficient_saves: List[str], mods: dict, prof_bonus: int) -> dict:
        """Строит словарь спасбросков."""
        saves = {}
        for ability in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
            is_prof = ability in proficient_saves
            mod = mods.get(ability, 0)
            total = mod + (prof_bonus if is_prof else 0)
            saves[ability] = {
                "modifier": total,
                "proficient": is_prof,
            }
        return saves

    def _build_skills(self, skill_proficiencies: dict, mods: dict, prof_bonus: int) -> dict:
        """Строит словарь навыков."""
        skills = {}
        for skill_name, skill_data in SKILLS.items():
            ability = skill_data.get("ability", "dexterity")
            is_prof = skill_proficiencies.get(skill_name, False)
            is_expertise = skill_proficiencies.get(f"{skill_name}_expertise", False)

            mod = mods.get(ability, 0)
            bonus = 0
            if is_expertise:
                bonus = prof_bonus * 2
            elif is_prof:
                bonus = prof_bonus

            total = mod + bonus

            skills[skill_name] = {
                "name_ru": skill_data.get("name", skill_name),
                "ability": ability,
                "modifier": total,
                "proficient": is_prof,
                "expertise": is_expertise,
            }
        return skills

    def _build_features(self, race: str, char_class: str, background: str, level: int, custom_features: list) -> List[dict]:
        """Собирает список всех особенностей персонажа."""
        features = []

        # Расовые особенности
        race_data = RACES.get(race, {})
        for feature_id in race_data.get("features", []):
            feature_info = FEATURES.get(feature_id, {"name": feature_id, "description": ""})
            features.append({
                "id": feature_id,
                "name": feature_info.get("name", feature_id),
                "description": feature_info.get("description", ""),
                "source": f"Раса: {race_data.get('name', race)}",
                "type": "racial",
            })

        # Классовые особенности 1 уровня
        class_data = CLASSES.get(char_class, {})
        for feature_id in class_data.get("features_1", []):
            feature_info = FEATURES.get(feature_id, {"name": feature_id, "description": ""})
            features.append({
                "id": feature_id,
                "name": feature_info.get("name", feature_id),
                "description": feature_info.get("description", ""),
                "source": f"Класс: {class_data.get('name', char_class)}",
                "type": "class",
            })

        # Особенность предыстории
        if background:
            bg_data = BACKGROUNDS.get(background, {})
            feature_id = bg_data.get("feature", "")
            if feature_id:
                feature_info = FEATURES.get(feature_id, {"name": feature_id, "description": ""})
                features.append({
                    "id": feature_id,
                    "name": feature_info.get("name", feature_id),
                    "description": feature_info.get("description", ""),
                    "source": f"Предыстория: {bg_data.get('name', background)}",
                    "type": "background",
                })

        # Кастомные особенности из БД
        for feat in custom_features:
            if isinstance(feat, str):
                feature_info = FEATURES.get(feat, {"name": feat, "description": ""})
                features.append({
                    "id": feat,
                    "name": feature_info.get("name", feat),
                    "description": feature_info.get("description", ""),
                    "source": "Дополнительно",
                    "type": "custom",
                })
            elif isinstance(feat, dict):
                features.append(feat)

        return features

    def _build_proficiencies(self, class_data: dict, race_data: dict, background_data: dict, custom_prof: dict) -> dict:
        """Собирает все владения персонажа."""
        armor = list(class_data.get("armor_proficiencies", []))
        weapons = list(class_data.get("weapon_proficiencies", []))
        tools = list(background_data.get("tool_proficiencies", []))
        languages = ["Common"]

        # Языки из расы
        # Языки из предыстории
        num_languages = background_data.get("languages", 0)

        # Кастомные владения
        if isinstance(custom_prof, dict):
            armor.extend(custom_prof.get("armor", []))
            weapons.extend(custom_prof.get("weapons", []))
            tools.extend(custom_prof.get("tools", []))
            languages.extend(custom_prof.get("languages", []))

        return {
            "armor": list(set(armor)),
            "weapons": list(set(weapons)),
            "tools": list(set(tools)),
            "languages": list(set(languages)),
            "all": list(set(armor + weapons + tools)),
        }

    def _get_spellcasting_mod(self, class_data: dict, mods: dict) -> int:
        """Возвращает модификатор для заклинаний."""
        ability = class_data.get("spellcasting_ability", "")
        return mods.get(ability, 0)

    def _load_description(self, db_description) -> dict:
        """Загружает описание из данных БД."""
        default_desc = {
            "appearance": "",
            "age": "",
            "build": "",
            "features": "",
            "demeanor": "",
            "text": "",
        }

        if not db_description:
            return default_desc

        # Если это строка JSON - парсим
        if isinstance(db_description, str):
            try:
                import json
                db_description = json.loads(db_description)
            except:
                return default_desc

        # Если это словарь - используем его
        if isinstance(db_description, dict):
            for key in default_desc:
                if key in db_description:
                    default_desc[key] = db_description[key]

        return default_desc

    def _xp_for_level(self, level: int) -> int:
        """Возвращает необходимый XP для уровня."""
        xp_table = {
            1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500,
            6: 14000, 7: 23000, 8: 34000, 9: 48000, 10: 64000,
            11: 85000, 12: 100000, 13: 120000, 14: 140000, 15: 165000,
            16: 195000, 17: 225000, 18: 265000, 19: 305000, 20: 355000,
        }
        return xp_table.get(level, 355000)

    def _recalculate_derived_stats(self, player_uuid: str):
        """Пересчитывает производные характеристики."""
        if player_uuid not in self.characters:
            return

        char = self.characters[player_uuid]
        bonuses = char.get("equipment_bonuses", {})

        # Пересчёт AC, HP и т.д. с учётом бонусов экипировки
        # TODO: Реализовать полный пересчёт

    # =========================================================================
    # Sending data
    # =========================================================================

    def _send_character_sheet(self, player_uuid: str):
        """Отправляет полный лист персонажа клиенту."""
        if player_uuid not in self.characters:
            return

        char = self.characters[player_uuid]

        # Добавляем активные условия
        char["conditions"] = self.active_conditions.get(player_uuid, [])

        # Используем dnd_send_to_client для отправки клиенту
        self.event_manager.post("dnd_send_to_client", {
            "client_id": player_uuid,
            "data": {
                "type": "character_sheet",
                "character": char,
            }
        })

    # =========================================================================
    # Public API
    # =========================================================================

    def get_character(self, player_uuid: str) -> Optional[dict]:
        """Получить лист персонажа."""
        return self.characters.get(player_uuid)

    def get_character_name(self, player_uuid: str) -> str:
        """Получить имя персонажа."""
        char = self.characters.get(player_uuid)
        return char.get("name", "Незнакомец") if char else "Незнакомец"

    def get_stats(self, player_uuid: str) -> Dict[str, Any]:
        """Получить статы персонажа для проверок."""
        char = self.characters.get(player_uuid)
        if not char:
            return {"level": 1}
        return char.get("stats", {"level": 1})

    def damage_character(self, player_uuid: str, amount: int) -> bool:
        """Нанести урон персонажу. Returns True если персонаж упал в 0 HP."""
        char = self.characters.get(player_uuid)
        if not char:
            return False

        # Сначала временные HP
        temp_hp = char.get("hp_temp", 0)
        if temp_hp > 0:
            if amount <= temp_hp:
                char["hp_temp"] = temp_hp - amount
                amount = 0
            else:
                amount -= temp_hp
                char["hp_temp"] = 0

        # Основные HP
        char["hp_current"] = max(0, char.get("hp_current", 0) - amount)
        char["stats"]["current_hp"] = char["hp_current"]

        is_down = char["hp_current"] <= 0

        self._send_character_sheet(player_uuid)

        self.event_manager.post("character_hp_changed", {
            "uuid": player_uuid,
            "current_hp": char["hp_current"],
            "max_hp": char.get("hp_max", 10),
            "is_down": is_down,
        })

        return is_down

    def heal_character(self, player_uuid: str, amount: int):
        """Исцелить персонажа."""
        char = self.characters.get(player_uuid)
        if not char:
            return

        max_hp = char.get("hp_max", 10)
        char["hp_current"] = min(char.get("hp_current", 0) + amount, max_hp)
        char["stats"]["current_hp"] = char["hp_current"]

        self._send_character_sheet(player_uuid)

        self.event_manager.post("character_hp_changed", {
            "uuid": player_uuid,
            "current_hp": char["hp_current"],
            "max_hp": max_hp,
            "is_down": False,
        })

    def add_temp_hp(self, player_uuid: str, amount: int):
        """Добавить временные HP."""
        char = self.characters.get(player_uuid)
        if not char:
            return

        char["hp_temp"] = max(char.get("hp_temp", 0), amount)
        char["stats"]["temp_hp"] = char["hp_temp"]

        self._send_character_sheet(player_uuid)
