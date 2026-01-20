"""
Серверный модуль управления заклинаниями.

Обрабатывает:
- Каст заклинаний
- Подготовку заклинаний
- Восстановление слотов
- Концентрацию
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Any

from nine.core.plugins import PluginModule
from nine.plugins.spells.sh_spell_slots import (
    get_spell_slots_for_class,
    get_spellcasting_ability,
    calculate_spell_save_dc,
    calculate_spell_attack_bonus,
    get_max_spell_level,
)


class SpellManagerServerModule(PluginModule):
    """
    Серверный модуль управления заклинаниями.
    """

    def on_load(self):
        # Данные заклинаний
        self._spells_data: Dict[str, dict] = {}

        # Кеш данных заклинательства игроков
        # client_id -> CharacterSpellcasting data
        self._player_spellcasting: Dict[int, dict] = {}

        # Загружаем данные заклинаний
        self._load_spells_data()

        # Подписки на события
        self.event_manager.subscribe("spellcasting_request", self._on_spellcasting_request)
        self.event_manager.subscribe("cast_spell_request", self._on_cast_spell_request)
        self.event_manager.subscribe("prepare_spell_request", self._on_prepare_spell_request)
        self.event_manager.subscribe("unprepare_spell_request", self._on_unprepare_spell_request)

        # Интеграция с персонажами
        self.event_manager.subscribe("player_authenticated", self._on_player_authenticated)
        self.event_manager.subscribe("player_left", self._on_player_left)

        # Интеграция с отдыхом
        self.event_manager.subscribe("short_rest_completed", self._on_short_rest)
        self.event_manager.subscribe("long_rest_completed", self._on_long_rest)

        # Интеграция с боем (концентрация)
        self.event_manager.subscribe("combat_damage_taken", self._on_damage_taken)
        self.event_manager.subscribe("combat_turn_end", self._on_turn_end)

        self.logger.info("Spell Manager серверный модуль загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("spellcasting_request", self._on_spellcasting_request)
        self.event_manager.unsubscribe("cast_spell_request", self._on_cast_spell_request)
        self.event_manager.unsubscribe("prepare_spell_request", self._on_prepare_spell_request)
        self.event_manager.unsubscribe("unprepare_spell_request", self._on_unprepare_spell_request)
        self.event_manager.unsubscribe("player_authenticated", self._on_player_authenticated)
        self.event_manager.unsubscribe("player_left", self._on_player_left)
        self.event_manager.unsubscribe("short_rest_completed", self._on_short_rest)
        self.event_manager.unsubscribe("long_rest_completed", self._on_long_rest)
        self.event_manager.unsubscribe("combat_damage_taken", self._on_damage_taken)
        self.event_manager.unsubscribe("combat_turn_end", self._on_turn_end)

        self.logger.info("Spell Manager серверный модуль выгружен")

    # =========================================================================
    # Data Loading
    # =========================================================================

    def _load_spells_data(self):
        """Загружает данные заклинаний из JSON."""
        spells_path = Path(__file__).parent / "data" / "spells.json"

        try:
            with open(spells_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for spell in data.get("spells", []):
                self._spells_data[spell["id"]] = spell

            self.logger.info(f"Загружено {len(self._spells_data)} заклинаний")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки заклинаний: {e}")

    # =========================================================================
    # Player Management
    # =========================================================================

    def _on_player_authenticated(self, data: dict):
        """Игрок авторизовался - инициализируем данные заклинательства."""
        client_id = data.get("client_id", -1)
        character_data = data.get("character_data", {})

        if client_id < 0:
            return

        char_class = character_data.get("class", "").lower()
        char_level = character_data.get("level", 1)

        # Получаем способность для заклинаний
        ability = get_spellcasting_ability(char_class) or "INT"

        # Получаем слоты по классу и уровню
        slots = get_spell_slots_for_class(char_class, char_level)

        # Загружаем сохранённые данные из character_data или создаём новые
        spellcasting = character_data.get("spellcasting", {})

        self._player_spellcasting[client_id] = {
            "ability": ability,
            "spells_known": spellcasting.get("spells_known", self._get_default_spells(char_class)),
            "spells_prepared": spellcasting.get("spells_prepared", []),
            "spell_slots_current": spellcasting.get("spell_slots_current", slots.copy()),
            "spell_slots_max": slots.copy(),
            "concentrating_on": spellcasting.get("concentrating_on"),
            "concentration_target": spellcasting.get("concentration_target"),
            "concentration_rounds_left": spellcasting.get("concentration_rounds_left", 0),
        }

        self.logger.info(f"Инициализированы данные заклинательства для клиента {client_id}")

    def _on_player_left(self, data: dict):
        """Игрок вышел - сохраняем данные."""
        client_id = data.get("client_id", -1)
        if client_id in self._player_spellcasting:
            # Данные должны быть сохранены в character_data
            del self._player_spellcasting[client_id]

    def _get_default_spells(self, char_class: str) -> List[str]:
        """Возвращает стартовый набор заклинаний для класса."""
        defaults = {
            "wizard": ["fire_bolt", "ray_of_frost", "light", "mage_hand", "magic_missile", "shield"],
            "sorcerer": ["fire_bolt", "light", "magic_missile", "shield"],
            "warlock": ["eldritch_blast", "mage_hand"],
            "cleric": ["sacred_flame", "light", "cure_wounds", "healing_word", "bless"],
            "druid": ["light", "cure_wounds", "thunderwave"],
            "bard": ["light", "mage_hand", "cure_wounds", "healing_word"],
            "paladin": ["cure_wounds", "bless"],
            "ranger": ["cure_wounds"],
        }
        return defaults.get(char_class.lower(), [])

    # =========================================================================
    # Spellcasting Data
    # =========================================================================

    def _on_spellcasting_request(self, data: dict):
        """Запрос данных заклинательства."""
        client_id = data.get("client_id", -1)

        spellcasting = self._player_spellcasting.get(client_id)
        if not spellcasting:
            return

        self._send_spellcasting_update(client_id)

    def _send_spellcasting_update(self, client_id: int):
        """Отправляет обновление данных заклинательства клиенту."""
        spellcasting = self._player_spellcasting.get(client_id)
        if not spellcasting:
            return

        self._send_to_client(client_id, {
            "type": "spellcasting_update",
            "spells_known": spellcasting["spells_known"],
            "spells_prepared": spellcasting["spells_prepared"],
            "spell_slots_current": spellcasting["spell_slots_current"],
            "spell_slots_max": spellcasting["spell_slots_max"],
            "ability": spellcasting["ability"],
            "concentrating_on": spellcasting["concentrating_on"],
        })

    # =========================================================================
    # Spell Casting
    # =========================================================================

    def _on_cast_spell_request(self, data: dict):
        """Запрос на каст заклинания."""
        client_id = data.get("client_id", -1)
        spell_id = data.get("spell_id", "")
        slot_level = data.get("slot_level", 0)
        target_id = data.get("target_id")

        spellcasting = self._player_spellcasting.get(client_id)
        if not spellcasting:
            self._send_cast_result(client_id, False, spell_id, "No spellcasting data")
            return

        spell = self._spells_data.get(spell_id)
        if not spell:
            self._send_cast_result(client_id, False, spell_id, "Unknown spell")
            return

        spell_level = spell.get("level", 0)

        # Проверка на cantrip
        if spell_level == 0:
            # Cantrip - всегда можно кастовать
            self._execute_spell(client_id, spell, target_id, 0)
            return

        # Проверка знания заклинания
        if spell_id not in spellcasting["spells_known"]:
            self._send_cast_result(client_id, False, spell_id, "Spell not known")
            return

        # Проверка подготовки (для классов, которым это нужно)
        # Для простоты пока пропускаем эту проверку

        # Определяем уровень слота (минимум - уровень заклинания)
        cast_level = max(slot_level, spell_level)

        # Ищем доступный слот
        available_slot = None
        for lvl in range(cast_level, 10):
            if spellcasting["spell_slots_current"].get(lvl, 0) > 0:
                available_slot = lvl
                break

        if available_slot is None:
            self._send_cast_result(client_id, False, spell_id, "No spell slots available")
            return

        # Тратим слот
        spellcasting["spell_slots_current"][available_slot] -= 1

        # Выполняем заклинание
        self._execute_spell(client_id, spell, target_id, available_slot)

    def _execute_spell(self, client_id: int, spell: dict, target_id: Optional[str], slot_level: int):
        """Выполняет заклинание."""
        spell_id = spell["id"]
        spell_level = spell.get("level", 0)

        # Обработка концентрации
        if spell.get("concentration"):
            spellcasting = self._player_spellcasting.get(client_id)
            if spellcasting:
                # Прерываем предыдущую концентрацию
                if spellcasting["concentrating_on"]:
                    self._break_concentration(client_id)

                # Начинаем новую
                duration_str = spell.get("duration", "")
                rounds = self._parse_duration_to_rounds(duration_str)
                spellcasting["concentrating_on"] = spell_id
                spellcasting["concentration_target"] = target_id
                spellcasting["concentration_rounds_left"] = rounds

        # Применяем эффекты
        effects = spell.get("effects", [])
        total_damage = 0
        total_healing = 0

        for effect in effects:
            effect_type = effect.get("effect_type", "")

            if effect_type == "damage":
                dice_count = effect.get("dice_count", 0)
                dice_size = effect.get("dice_size", 0)
                modifier = effect.get("modifier", 0)

                # Уапгрейд урона при касте на высоком уровне
                if slot_level > spell_level and spell.get("higher_levels"):
                    dice_count += (slot_level - spell_level)

                damage = self._roll_dice(dice_count, dice_size) + modifier
                total_damage += damage

            elif effect_type == "heal":
                dice_count = effect.get("dice_count", 0)
                dice_size = effect.get("dice_size", 0)
                modifier = effect.get("modifier", 0)

                if slot_level > spell_level and spell.get("higher_levels"):
                    dice_count += (slot_level - spell_level)

                healing = self._roll_dice(dice_count, dice_size) + modifier
                total_healing += healing

            elif effect_type == "debuff":
                condition = effect.get("condition", "")
                if condition and target_id:
                    # Применяем условие (интеграция с conditions системой)
                    self.event_manager.post("apply_condition", {
                        "target_id": target_id,
                        "condition": condition,
                        "source_id": str(client_id),
                        "duration_rounds": effect.get("duration_rounds", 0),
                    })

            elif effect_type == "buff":
                condition = effect.get("condition", "")
                if condition:
                    buff_target = target_id or str(client_id)
                    self.event_manager.post("apply_buff", {
                        "target_id": buff_target,
                        "buff": condition,
                        "source_id": str(client_id),
                        "duration_rounds": effect.get("duration_rounds", 0),
                    })

        # Публикуем событие о касте
        self.event_manager.post("spell_cast", {
            "caster_id": client_id,
            "spell_id": spell_id,
            "spell_name": spell.get("name", spell_id),
            "slot_level": slot_level,
            "target_id": target_id,
            "damage": total_damage,
            "healing": total_healing,
        })

        # Применяем урон/хил к цели
        if total_damage > 0 and target_id:
            self.event_manager.post("deal_damage", {
                "source_id": str(client_id),
                "target_id": target_id,
                "damage": total_damage,
                "damage_type": effects[0].get("damage_type", "magical") if effects else "magical",
            })

        if total_healing > 0:
            heal_target = target_id or str(client_id)
            self.event_manager.post("apply_healing", {
                "source_id": str(client_id),
                "target_id": heal_target,
                "healing": total_healing,
            })

        # Отправляем результат
        spellcasting = self._player_spellcasting.get(client_id, {})
        self._send_to_client(client_id, {
            "type": "spell_cast_result",
            "success": True,
            "spell_id": spell_id,
            "slot_level": slot_level,
            "damage": total_damage,
            "healing": total_healing,
            "spell_slots_current": spellcasting.get("spell_slots_current", {}),
        })

        # Логируем
        self.logger.info(
            f"Client {client_id} cast {spell_id} "
            f"(slot {slot_level}, dmg={total_damage}, heal={total_healing})"
        )

    def _send_cast_result(self, client_id: int, success: bool, spell_id: str, message: str = ""):
        """Отправляет результат каста."""
        self._send_to_client(client_id, {
            "type": "spell_cast_result",
            "success": success,
            "spell_id": spell_id,
            "message": message,
        })

    # =========================================================================
    # Spell Preparation
    # =========================================================================

    def _on_prepare_spell_request(self, data: dict):
        """Запрос на подготовку заклинания."""
        client_id = data.get("client_id", -1)
        spell_id = data.get("spell_id", "")

        spellcasting = self._player_spellcasting.get(client_id)
        if not spellcasting:
            return

        if spell_id not in spellcasting["spells_known"]:
            return

        if spell_id not in spellcasting["spells_prepared"]:
            spellcasting["spells_prepared"].append(spell_id)
            self._send_spellcasting_update(client_id)

    def _on_unprepare_spell_request(self, data: dict):
        """Запрос на снятие подготовки заклинания."""
        client_id = data.get("client_id", -1)
        spell_id = data.get("spell_id", "")

        spellcasting = self._player_spellcasting.get(client_id)
        if not spellcasting:
            return

        if spell_id in spellcasting["spells_prepared"]:
            spellcasting["spells_prepared"].remove(spell_id)
            self._send_spellcasting_update(client_id)

    # =========================================================================
    # Rest Integration
    # =========================================================================

    def _on_short_rest(self, data: dict):
        """Короткий отдых - восстановление для Warlock."""
        client_id = data.get("client_id", -1)

        spellcasting = self._player_spellcasting.get(client_id)
        if not spellcasting:
            return

        # Получаем данные персонажа
        char_class = self._get_player_class(client_id)
        if char_class == "warlock":
            # Warlock восстанавливает все слоты на коротком отдыхе
            spellcasting["spell_slots_current"] = spellcasting["spell_slots_max"].copy()
            self._send_spellcasting_update(client_id)
            self.logger.info(f"Warlock {client_id} восстановил слоты на коротком отдыхе")

    def _on_long_rest(self, data: dict):
        """Длинный отдых - полное восстановление слотов."""
        client_id = data.get("client_id", -1)

        spellcasting = self._player_spellcasting.get(client_id)
        if not spellcasting:
            return

        # Восстанавливаем все слоты
        spellcasting["spell_slots_current"] = spellcasting["spell_slots_max"].copy()

        # Прерываем концентрацию
        spellcasting["concentrating_on"] = None
        spellcasting["concentration_target"] = None
        spellcasting["concentration_rounds_left"] = 0

        self._send_spellcasting_update(client_id)
        self.logger.info(f"Client {client_id} восстановил все слоты на длинном отдыхе")

    # =========================================================================
    # Concentration
    # =========================================================================

    def _on_damage_taken(self, data: dict):
        """Игрок получил урон - проверка концентрации."""
        target_id = data.get("target_id")
        damage = data.get("damage", 0)

        # Конвертируем target_id в client_id если нужно
        try:
            client_id = int(target_id)
        except (ValueError, TypeError):
            return

        spellcasting = self._player_spellcasting.get(client_id)
        if not spellcasting or not spellcasting["concentrating_on"]:
            return

        # DC = 10 или половина урона, что больше
        dc = max(10, damage // 2)

        # Бросок CON saving throw
        con_modifier = self._get_ability_modifier(client_id, "CON")
        roll = random.randint(1, 20) + con_modifier

        if roll < dc:
            # Концентрация потеряна
            self._break_concentration(client_id)
            self._send_to_client(client_id, {
                "type": "concentration_broken",
                "spell_id": spellcasting.get("concentrating_on"),
                "reason": f"Failed concentration check (rolled {roll} vs DC {dc})",
            })
        else:
            self._send_to_client(client_id, {
                "type": "concentration_maintained",
                "spell_id": spellcasting["concentrating_on"],
                "roll": roll,
                "dc": dc,
            })

    def _on_turn_end(self, data: dict):
        """Конец хода - уменьшаем счётчик концентрации."""
        entity_id = data.get("entity_id")

        try:
            client_id = int(entity_id)
        except (ValueError, TypeError):
            return

        spellcasting = self._player_spellcasting.get(client_id)
        if not spellcasting or not spellcasting["concentrating_on"]:
            return

        spellcasting["concentration_rounds_left"] -= 1

        if spellcasting["concentration_rounds_left"] <= 0:
            spell_id = spellcasting["concentrating_on"]
            self._break_concentration(client_id)
            self._send_to_client(client_id, {
                "type": "concentration_ended",
                "spell_id": spell_id,
                "reason": "Duration expired",
            })

    def _break_concentration(self, client_id: int):
        """Прерывает концентрацию."""
        spellcasting = self._player_spellcasting.get(client_id)
        if not spellcasting:
            return

        spell_id = spellcasting["concentrating_on"]
        target_id = spellcasting["concentration_target"]

        spellcasting["concentrating_on"] = None
        spellcasting["concentration_target"] = None
        spellcasting["concentration_rounds_left"] = 0

        # Снимаем эффекты заклинания
        if spell_id and target_id:
            self.event_manager.post("remove_spell_effect", {
                "spell_id": spell_id,
                "target_id": target_id,
                "caster_id": client_id,
            })

        self._send_spellcasting_update(client_id)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _roll_dice(self, count: int, size: int) -> int:
        """Бросает кубики."""
        if count <= 0 or size <= 0:
            return 0
        return sum(random.randint(1, size) for _ in range(count))

    def _parse_duration_to_rounds(self, duration: str) -> int:
        """Парсит строку длительности в раунды (1 раунд = 6 секунд)."""
        duration = duration.lower()

        if "1 minute" in duration:
            return 10
        elif "10 minute" in duration:
            return 100
        elif "1 hour" in duration:
            return 600
        elif "8 hour" in duration:
            return 4800
        elif "24 hour" in duration:
            return 14400
        elif "1 round" in duration:
            return 1

        return 10  # По умолчанию 1 минута

    def _get_player_class(self, client_id: int) -> str:
        """Получает класс игрока."""
        if hasattr(self.app, 'authenticated_clients'):
            auth_data = self.app.authenticated_clients.get(client_id, {})
            char_data = auth_data.get("character_data", {})
            return char_data.get("class", "").lower()
        return ""

    def _get_ability_modifier(self, client_id: int, ability: str) -> int:
        """Получает модификатор способности игрока."""
        if hasattr(self.app, 'authenticated_clients'):
            auth_data = self.app.authenticated_clients.get(client_id, {})
            char_data = auth_data.get("character_data", {})
            abilities = char_data.get("abilities", {})
            score = abilities.get(ability.lower(), 10)
            return (score - 10) // 2
        return 0

    def _send_to_client(self, client_id: int, message: dict):
        """Отправляет сообщение клиенту."""
        if hasattr(self.app, 'send_to_client'):
            self.app.send_to_client(client_id, message)
        else:
            self.event_manager.post(f"send_to_client_{client_id}", message)

    # =========================================================================
    # Public API
    # =========================================================================

    def get_spell_data(self, spell_id: str) -> Optional[dict]:
        """Возвращает данные заклинания."""
        return self._spells_data.get(spell_id)

    def get_player_spell_slots(self, client_id: int) -> Dict[int, int]:
        """Возвращает текущие слоты игрока."""
        spellcasting = self._player_spellcasting.get(client_id, {})
        return spellcasting.get("spell_slots_current", {})

    def restore_spell_slot(self, client_id: int, level: int):
        """Восстанавливает слот заклинания."""
        spellcasting = self._player_spellcasting.get(client_id)
        if not spellcasting:
            return

        max_slots = spellcasting["spell_slots_max"].get(level, 0)
        current = spellcasting["spell_slots_current"].get(level, 0)

        if current < max_slots:
            spellcasting["spell_slots_current"][level] = current + 1
            self._send_spellcasting_update(client_id)
