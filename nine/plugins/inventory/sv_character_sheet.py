"""
Серверный модуль листа персонажа.

Управляет данными персонажа:
- Описание персонажа (редактируемое игроком)
- Базовые характеристики (STR, DEX, CON, INT, WIS, CHA)
- Производные статы (HP, AC, скорость и т.д.)
- Синхронизация с клиентом
"""

from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from nine.core.plugins import PluginModule


@dataclass
class CharacterDescription:
    """Описание персонажа, видимое другим игрокам."""
    # Внешность (всегда видна)
    appearance: str = ""
    # Возраст
    age: str = ""
    # Рост и телосложение
    build: str = ""
    # Особые приметы
    features: str = ""
    # Манера поведения
    demeanor: str = ""


@dataclass
class CharacterStats:
    """Характеристики персонажа D&D 5e."""
    # Базовые характеристики (8-20 обычно)
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    # Уровень и опыт
    level: int = 1
    experience: int = 0

    # Здоровье
    max_hp: int = 10
    current_hp: int = 10
    temp_hp: int = 0

    # Скорость (в футах)
    base_speed: int = 30

    # Владения
    proficiencies: List[str] = field(default_factory=list)
    # Языки
    languages: List[str] = field(default_factory=lambda: ["Common"])

    def get_modifier(self, stat: str) -> int:
        """Получить модификатор характеристики."""
        value = getattr(self, stat, 10)
        return (value - 10) // 2

    def get_proficiency_bonus(self) -> int:
        """Получить бонус мастерства по уровню."""
        return (self.level - 1) // 4 + 2

    def to_dict(self) -> dict:
        """Сериализация в словарь."""
        return {
            "strength": self.strength,
            "dexterity": self.dexterity,
            "constitution": self.constitution,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "charisma": self.charisma,
            "level": self.level,
            "experience": self.experience,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "temp_hp": self.temp_hp,
            "base_speed": self.base_speed,
            "proficiencies": self.proficiencies,
            "languages": self.languages,
            # Модификаторы
            "str_mod": self.get_modifier("strength"),
            "dex_mod": self.get_modifier("dexterity"),
            "con_mod": self.get_modifier("constitution"),
            "int_mod": self.get_modifier("intelligence"),
            "wis_mod": self.get_modifier("wisdom"),
            "cha_mod": self.get_modifier("charisma"),
            "proficiency_bonus": self.get_proficiency_bonus(),
        }


@dataclass
class CharacterSheet:
    """Полный лист персонажа."""
    # Имя персонажа (игровое, не Steam)
    name: str = "Незнакомец"
    # Раса
    race: str = "Human"
    # Класс
    character_class: str = "Commoner"
    # Предыстория
    background: str = ""

    # Описание
    description: CharacterDescription = field(default_factory=CharacterDescription)

    # Характеристики
    stats: CharacterStats = field(default_factory=CharacterStats)

    # Бонусы от экипировки (добавляются сервером)
    equipment_bonuses: Dict[str, int] = field(default_factory=dict)

    def get_effective_stat(self, stat: str) -> int:
        """Получить эффективное значение характеристики с учётом бонусов."""
        base = getattr(self.stats, stat, 10)
        bonus = self.equipment_bonuses.get(stat, 0)
        return base + bonus

    def get_effective_speed(self) -> int:
        """Получить эффективную скорость с учётом бонусов."""
        return self.stats.base_speed + self.equipment_bonuses.get("speed", 0)

    def to_dict(self) -> dict:
        """Сериализация в словарь."""
        return {
            "name": self.name,
            "race": self.race,
            "class": self.character_class,
            "background": self.background,
            "description": {
                "appearance": self.description.appearance,
                "age": self.description.age,
                "build": self.description.build,
                "features": self.description.features,
                "demeanor": self.description.demeanor,
            },
            "stats": self.stats.to_dict(),
            "equipment_bonuses": self.equipment_bonuses,
        }


class CharacterSheetServerModule(PluginModule):
    """
    Серверный модуль управления листами персонажей.

    Хранит и синхронизирует данные персонажей между сервером и клиентами.
    """

    def on_load(self):
        # {player_uuid: CharacterSheet}
        self.characters: Dict[str, CharacterSheet] = {}

        # Подписки на события
        self.event_manager.subscribe("player_joined", self.on_player_join)
        self.event_manager.subscribe("player_left", self.on_player_leave)
        self.event_manager.subscribe("character_update_description", self.on_update_description)
        self.event_manager.subscribe("character_update_name", self.on_update_name)
        self.event_manager.subscribe("request_character_sheet", self.on_request_character)
        self.event_manager.subscribe("request_other_character", self.on_request_other_character)
        self.event_manager.subscribe("equipment_stats_updated", self.on_equipment_stats_updated)

        self.logger.info("Серверный модуль листа персонажа загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("player_joined", self.on_player_join)
        self.event_manager.unsubscribe("player_left", self.on_player_leave)
        self.event_manager.unsubscribe("character_update_description", self.on_update_description)
        self.event_manager.unsubscribe("character_update_name", self.on_update_name)
        self.event_manager.unsubscribe("request_character_sheet", self.on_request_character)
        self.event_manager.unsubscribe("request_other_character", self.on_request_other_character)
        self.event_manager.unsubscribe("equipment_stats_updated", self.on_equipment_stats_updated)

        self.logger.info("Серверный модуль листа персонажа выгружен")

    # =========================================================================
    # Event handlers
    # =========================================================================

    def on_player_join(self, data: dict):
        """Игрок присоединился — загружаем лист персонажа."""
        player_uuid = data.get("uuid")
        player_name = data.get("name", "Игрок")

        if not player_uuid:
            return

        # TODO: Загрузить из БД
        # Пока создаём новый лист с именем из Steam
        self.characters[player_uuid] = CharacterSheet(name=player_name)

        self.logger.debug(f"Лист персонажа {player_uuid} загружен")

        # Отправляем клиенту его лист
        self._send_character_sheet(player_uuid)

    def on_player_leave(self, data: dict):
        """Игрок вышел — сохраняем данные."""
        player_uuid = data.get("uuid")
        if not player_uuid:
            return

        # TODO: Сохранить в БД
        if player_uuid in self.characters:
            del self.characters[player_uuid]

    def on_update_description(self, data: dict):
        """
        Игрок обновил описание персонажа.

        data: {
            uuid: str,
            field: str,  # "appearance", "age", "build", "features", "demeanor"
            value: str,
        }
        """
        player_uuid = data.get("uuid")
        field_name = data.get("field")
        value = data.get("value", "")

        if not player_uuid or not field_name:
            return

        if player_uuid not in self.characters:
            return

        character = self.characters[player_uuid]

        # Проверяем допустимые поля
        allowed_fields = ["appearance", "age", "build", "features", "demeanor"]
        if field_name not in allowed_fields:
            return

        # Ограничиваем длину
        max_length = 500
        value = value[:max_length]

        # Обновляем
        setattr(character.description, field_name, value)

        self.logger.debug(f"Игрок {player_uuid} обновил {field_name}")

        # Отправляем подтверждение
        self._send_character_sheet(player_uuid)

    def on_update_name(self, data: dict):
        """
        Игрок изменил игровое имя персонажа.

        data: {
            uuid: str,
            name: str,
        }
        """
        player_uuid = data.get("uuid")
        new_name = data.get("name", "").strip()

        if not player_uuid or not new_name:
            return

        if player_uuid not in self.characters:
            return

        # Ограничиваем длину
        new_name = new_name[:50]

        character = self.characters[player_uuid]
        old_name = character.name
        character.name = new_name

        self.logger.debug(f"Игрок {player_uuid} сменил имя: {old_name} -> {new_name}")

        # Отправляем обновление
        self._send_character_sheet(player_uuid)

        # Уведомляем систему знакомств об изменении имени
        self.event_manager.post("character_name_changed", {
            "uuid": player_uuid,
            "old_name": old_name,
            "new_name": new_name,
        })

    def on_request_character(self, data: dict):
        """Запрос собственного листа персонажа."""
        player_uuid = data.get("uuid")
        if player_uuid:
            self._send_character_sheet(player_uuid)

    def on_request_other_character(self, data: dict):
        """
        Запрос информации о другом персонаже.

        Возвращает только публичную информацию (описание).

        data: {
            uuid: str,           # Кто запрашивает
            target_uuid: str,    # О ком запрашивает
        }
        """
        requester_uuid = data.get("uuid")
        target_uuid = data.get("target_uuid")

        if not requester_uuid or not target_uuid:
            return

        if target_uuid not in self.characters:
            return

        target = self.characters[target_uuid]

        # Формируем публичную информацию
        public_info = {
            "uuid": target_uuid,
            "description": {
                "appearance": target.description.appearance,
                "age": target.description.age,
                "build": target.description.build,
                "features": target.description.features,
                "demeanor": target.description.demeanor,
            },
            "race": target.race,
            # Имя НЕ отправляем — это решает система знакомств
        }

        # Отправляем запрашивающему
        self.event_manager.post("character_info_send_to_client", {
            "client_id": requester_uuid,
            "data": {
                "type": "other_character_info",
                "character": public_info,
            }
        })

    def on_equipment_stats_updated(self, data: dict):
        """Обновились бонусы от экипировки."""
        player_uuid = data.get("uuid")
        bonuses = data.get("bonuses", {})

        if not player_uuid:
            return

        if player_uuid not in self.characters:
            return

        character = self.characters[player_uuid]
        character.equipment_bonuses = bonuses

        # Пересчитываем HP если изменилось CON
        con_bonus = bonuses.get("constitution", 0)
        if con_bonus != 0:
            old_con_mod = character.stats.get_modifier("constitution")
            new_con_mod = (character.stats.constitution + con_bonus - 10) // 2
            hp_diff = (new_con_mod - old_con_mod) * character.stats.level

            character.stats.max_hp += hp_diff
            character.stats.current_hp = min(
                character.stats.current_hp,
                character.stats.max_hp
            )

        # Отправляем обновлённый лист
        self._send_character_sheet(player_uuid)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _send_character_sheet(self, player_uuid: str):
        """Отправить полный лист персонажа клиенту."""
        if player_uuid not in self.characters:
            return

        character = self.characters[player_uuid]

        self.event_manager.post("character_sheet_send_to_client", {
            "client_id": player_uuid,
            "data": {
                "type": "character_sheet",
                "character": character.to_dict(),
            }
        })

    # =========================================================================
    # Public API
    # =========================================================================

    def get_character(self, player_uuid: str) -> Optional[CharacterSheet]:
        """Получить лист персонажа."""
        return self.characters.get(player_uuid)

    def get_character_name(self, player_uuid: str) -> str:
        """Получить имя персонажа."""
        character = self.characters.get(player_uuid)
        if character:
            return character.name
        return "Незнакомец"

    def get_character_description(self, player_uuid: str) -> Optional[CharacterDescription]:
        """Получить описание персонажа."""
        character = self.characters.get(player_uuid)
        if character:
            return character.description
        return None

    def get_stats(self, player_uuid: str) -> Dict[str, Any]:
        """Получить статы персонажа для проверок."""
        character = self.characters.get(player_uuid)
        if not character:
            return {"level": 1}

        stats = character.stats

        return {
            "level": stats.level,
            "strength": character.get_effective_stat("strength"),
            "dexterity": character.get_effective_stat("dexterity"),
            "constitution": character.get_effective_stat("constitution"),
            "intelligence": character.get_effective_stat("intelligence"),
            "wisdom": character.get_effective_stat("wisdom"),
            "charisma": character.get_effective_stat("charisma"),
            "proficiencies": stats.proficiencies,
            "class": character.character_class,
        }

    def damage_character(self, player_uuid: str, amount: int) -> bool:
        """
        Нанести урон персонажу.

        Returns:
            True если персонаж упал в 0 HP
        """
        character = self.characters.get(player_uuid)
        if not character:
            return False

        # Сначала снимаем временные HP
        if character.stats.temp_hp > 0:
            if amount <= character.stats.temp_hp:
                character.stats.temp_hp -= amount
                amount = 0
            else:
                amount -= character.stats.temp_hp
                character.stats.temp_hp = 0

        # Затем основные HP
        character.stats.current_hp -= amount
        is_down = character.stats.current_hp <= 0

        if is_down:
            character.stats.current_hp = 0

        # Отправляем обновление
        self._send_character_sheet(player_uuid)

        # Событие об изменении HP
        self.event_manager.post("character_hp_changed", {
            "uuid": player_uuid,
            "current_hp": character.stats.current_hp,
            "max_hp": character.stats.max_hp,
            "is_down": is_down,
        })

        return is_down

    def heal_character(self, player_uuid: str, amount: int):
        """Исцелить персонажа."""
        character = self.characters.get(player_uuid)
        if not character:
            return

        character.stats.current_hp = min(
            character.stats.current_hp + amount,
            character.stats.max_hp
        )

        self._send_character_sheet(player_uuid)

        self.event_manager.post("character_hp_changed", {
            "uuid": player_uuid,
            "current_hp": character.stats.current_hp,
            "max_hp": character.stats.max_hp,
            "is_down": False,
        })

    def add_temp_hp(self, player_uuid: str, amount: int):
        """Добавить временные HP."""
        character = self.characters.get(player_uuid)
        if not character:
            return

        # Временные HP не суммируются, берём максимум
        character.stats.temp_hp = max(character.stats.temp_hp, amount)

        self._send_character_sheet(player_uuid)
