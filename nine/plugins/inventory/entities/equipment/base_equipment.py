"""
Базовый класс Equipment для экипируемых предметов.

Наследует от Item и добавляет:
- Слот экипировки
- Бонусы к характеристикам
- Требования для экипировки
- Прочность
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from nine.plugins.inventory.entities.base import Item
from .sh_equipment_slots import EquipmentSlot, get_slot_name


@dataclass
class StatBonus:
    """Бонус к характеристике от экипировки."""
    strength: int = 0
    dexterity: int = 0
    constitution: int = 0
    intelligence: int = 0
    wisdom: int = 0
    charisma: int = 0

    # Производные статы
    armor_class: int = 0
    attack_bonus: int = 0
    damage_bonus: int = 0
    spell_dc: int = 0
    speed: int = 0          # В футах
    initiative: int = 0

    # Сопротивления
    damage_resistance: List[str] = field(default_factory=list)
    condition_immunity: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Сериализация в словарь."""
        return {
            "str": self.strength,
            "dex": self.dexterity,
            "con": self.constitution,
            "int": self.intelligence,
            "wis": self.wisdom,
            "cha": self.charisma,
            "ac": self.armor_class,
            "attack": self.attack_bonus,
            "damage": self.damage_bonus,
            "spell_dc": self.spell_dc,
            "speed": self.speed,
            "initiative": self.initiative,
            "resistances": self.damage_resistance,
            "immunities": self.condition_immunity,
        }


@dataclass
class EquipmentRequirements:
    """Требования для экипировки предмета."""
    min_level: int = 0
    min_strength: int = 0
    min_dexterity: int = 0
    min_intelligence: int = 0
    min_wisdom: int = 0
    min_charisma: int = 0
    required_class: Optional[str] = None    # Например, "wizard"
    required_proficiency: Optional[str] = None  # Например, "heavy_armor"

    def check(self, player_stats: dict) -> tuple[bool, str]:
        """
        Проверяет, соответствует ли игрок требованиям.

        Returns:
            (True, "") если соответствует
            (False, "причина") если не соответствует
        """
        level = player_stats.get("level", 1)
        if level < self.min_level:
            return False, f"Требуется уровень {self.min_level}"

        stats_map = {
            "strength": self.min_strength,
            "dexterity": self.min_dexterity,
            "intelligence": self.min_intelligence,
            "wisdom": self.min_wisdom,
            "charisma": self.min_charisma,
        }

        stat_names_ru = {
            "strength": "Сила",
            "dexterity": "Ловкость",
            "intelligence": "Интеллект",
            "wisdom": "Мудрость",
            "charisma": "Харизма",
        }

        for stat, min_val in stats_map.items():
            if min_val > 0:
                current = player_stats.get(stat, 10)
                if current < min_val:
                    return False, f"Требуется {stat_names_ru[stat]} {min_val}"

        if self.required_class:
            player_class = player_stats.get("class", "")
            if player_class.lower() != self.required_class.lower():
                return False, f"Требуется класс: {self.required_class}"

        if self.required_proficiency:
            proficiencies = player_stats.get("proficiencies", [])
            if self.required_proficiency not in proficiencies:
                return False, f"Требуется владение: {self.required_proficiency}"

        return True, ""


class Equipment(Item):
    """
    Базовый класс для экипируемых предметов.

    Наследует от Item и добавляет:
    - Слот экипировки (EQUIPMENT_SLOT)
    - Бонусы к статам (STAT_BONUS)
    - Требования для экипировки (REQUIREMENTS)
    - Прочность (DURABILITY_MAX)

    Пример:
    ```python
    class ChainMail(Equipment):
        CLASS_ID = "chainmail"
        NAME = "Кольчуга"
        EQUIPMENT_SLOT = EquipmentSlot.CHEST
        STAT_BONUS = StatBonus(armor_class=16)
        REQUIREMENTS = EquipmentRequirements(min_strength=13)
    ```
    """

    CLASS_ID = "base_equipment"
    NAME = "Equipment"
    CATEGORY = "equipment"
    MAX_STACK = 1  # Экипировка не стакается

    # Слот по умолчанию (переопределить в наследниках)
    EQUIPMENT_SLOT: Optional[EquipmentSlot] = None

    # Тип предмета (для проверки слотов)
    EQUIPMENT_TYPE: str = "misc"  # armor, weapon, shield, ring, amulet, etc.

    # Бонусы к статам
    STAT_BONUS: StatBonus = StatBonus()

    # Требования для экипировки
    REQUIREMENTS: EquipmentRequirements = EquipmentRequirements()

    # Прочность (0 = неразрушимый)
    DURABILITY_MAX: int = 0

    # D&D свойства
    MAGICAL: bool = False           # Магический предмет
    ATTUNEMENT: bool = False        # Требует настройки (attunement)
    CURSED: bool = False            # Проклятый предмет

    def __init__(self, unique_id: Optional[str] = None):
        super().__init__(unique_id)

        # Текущая прочность
        if self.DURABILITY_MAX > 0:
            self.data["durability"] = self.DURABILITY_MAX

        # Состояние настройки (attunement)
        self.data["attuned_to"] = None

    # =========================================================================
    # Свойства
    # =========================================================================

    @property
    def durability(self) -> int:
        """Текущая прочность предмета."""
        if self.DURABILITY_MAX == 0:
            return -1  # Неразрушимый
        return self.data.get("durability", self.DURABILITY_MAX)

    @durability.setter
    def durability(self, value: int):
        if self.DURABILITY_MAX > 0:
            self.data["durability"] = max(0, min(value, self.DURABILITY_MAX))

    @property
    def is_broken(self) -> bool:
        """Сломан ли предмет."""
        if self.DURABILITY_MAX == 0:
            return False
        return self.durability <= 0

    @property
    def attuned_to(self) -> Optional[str]:
        """UUID игрока, к которому настроен предмет."""
        return self.data.get("attuned_to")

    @attuned_to.setter
    def attuned_to(self, player_uuid: Optional[str]):
        self.data["attuned_to"] = player_uuid

    # =========================================================================
    # Методы экипировки
    # =========================================================================

    def can_equip(self, player_uuid: str, player_stats: dict) -> tuple[bool, str]:
        """
        Проверяет, может ли игрок экипировать этот предмет.

        Args:
            player_uuid: UUID игрока
            player_stats: Статы игрока (level, strength, class, proficiencies, etc.)

        Returns:
            (True, "") если можно экипировать
            (False, "причина") если нельзя
        """
        # Проверяем, не сломан ли предмет
        if self.is_broken:
            return False, "Предмет сломан"

        # Проверяем требования
        can_use, reason = self.REQUIREMENTS.check(player_stats)
        if not can_use:
            return False, reason

        # Проверяем настройку (attunement)
        if self.ATTUNEMENT:
            if self.attuned_to and self.attuned_to != player_uuid:
                return False, "Предмет настроен на другого игрока"

        return True, ""

    def on_equip(self, player_uuid: str, slot: str) -> bool:
        """
        Вызывается при экипировке предмета.

        Args:
            player_uuid: UUID игрока
            slot: Слот экипировки

        Returns:
            True если экипировка успешна
        """
        # Проверяем правильный слот
        if self.EQUIPMENT_SLOT and slot != self.EQUIPMENT_SLOT.value:
            return False

        # Если требуется attunement, настраиваем
        if self.ATTUNEMENT and not self.attuned_to:
            self.attuned_to = player_uuid

        # Отправляем событие о применении бонусов
        self._apply_stat_bonuses(player_uuid, add=True)

        return True

    def on_unequip(self, player_uuid: str) -> bool:
        """
        Вызывается при снятии экипировки.

        Args:
            player_uuid: UUID игрока

        Returns:
            True если снятие успешно
        """
        # Проклятые предметы нельзя снять обычным способом
        if self.CURSED:
            return False

        # Убираем бонусы
        self._apply_stat_bonuses(player_uuid, add=False)

        return True

    def _apply_stat_bonuses(self, player_uuid: str, add: bool = True):
        """Применяет или убирает бонусы от экипировки."""
        multiplier = 1 if add else -1
        bonus = self.STAT_BONUS

        # Основные характеристики
        stat_changes = []

        if bonus.strength != 0:
            stat_changes.append(("strength", bonus.strength * multiplier))
        if bonus.dexterity != 0:
            stat_changes.append(("dexterity", bonus.dexterity * multiplier))
        if bonus.constitution != 0:
            stat_changes.append(("constitution", bonus.constitution * multiplier))
        if bonus.intelligence != 0:
            stat_changes.append(("intelligence", bonus.intelligence * multiplier))
        if bonus.wisdom != 0:
            stat_changes.append(("wisdom", bonus.wisdom * multiplier))
        if bonus.charisma != 0:
            stat_changes.append(("charisma", bonus.charisma * multiplier))

        # Производные статы
        if bonus.armor_class != 0:
            stat_changes.append(("armor_class", bonus.armor_class * multiplier))
        if bonus.attack_bonus != 0:
            stat_changes.append(("attack_bonus", bonus.attack_bonus * multiplier))
        if bonus.damage_bonus != 0:
            stat_changes.append(("damage_bonus", bonus.damage_bonus * multiplier))
        if bonus.speed != 0:
            stat_changes.append(("speed", bonus.speed * multiplier))
        if bonus.initiative != 0:
            stat_changes.append(("initiative", bonus.initiative * multiplier))

        # Отправляем события для каждого изменения
        for stat, change in stat_changes:
            self.post_event("player_stat_changed", {
                "uuid": player_uuid,
                "stat": stat,
                "change": change,
                "source": self.CLASS_ID,
            })

    # =========================================================================
    # Прочность
    # =========================================================================

    def damage_durability(self, amount: int = 1) -> bool:
        """
        Уменьшает прочность предмета.

        Args:
            amount: Количество прочности для снятия

        Returns:
            True если предмет сломался
        """
        if self.DURABILITY_MAX == 0:
            return False  # Неразрушимый

        self.durability -= amount

        if self.is_broken:
            self.post_event("item_broken", {
                "item_id": self.CLASS_ID,
                "unique_id": self.unique_id,
            })
            return True

        return False

    def repair(self, amount: Optional[int] = None):
        """
        Восстанавливает прочность предмета.

        Args:
            amount: Количество прочности для восстановления (None = полное)
        """
        if self.DURABILITY_MAX == 0:
            return

        if amount is None:
            self.durability = self.DURABILITY_MAX
        else:
            self.durability += amount

    # =========================================================================
    # Отображение
    # =========================================================================

    def get_slot_name(self, lang: str = "ru") -> str:
        """Получить название слота экипировки."""
        if self.EQUIPMENT_SLOT:
            return get_slot_name(self.EQUIPMENT_SLOT, lang)
        return "—"

    def get_tooltip(self) -> str:
        """Расширенный tooltip для экипировки."""
        lines = [self.NAME]

        if self.DESCRIPTION:
            lines.append(self.DESCRIPTION)

        lines.append("")

        # Слот
        slot_name = self.get_slot_name()
        lines.append(f"Слот: {slot_name}")

        # Бонусы
        bonus = self.STAT_BONUS
        if bonus.armor_class != 0:
            lines.append(f"AC: {'+' if bonus.armor_class > 0 else ''}{bonus.armor_class}")
        if bonus.attack_bonus != 0:
            lines.append(f"Атака: {'+' if bonus.attack_bonus > 0 else ''}{bonus.attack_bonus}")
        if bonus.damage_bonus != 0:
            lines.append(f"Урон: {'+' if bonus.damage_bonus > 0 else ''}{bonus.damage_bonus}")

        # Характеристики
        stat_bonuses = []
        if bonus.strength != 0:
            stat_bonuses.append(f"СИЛ {'+' if bonus.strength > 0 else ''}{bonus.strength}")
        if bonus.dexterity != 0:
            stat_bonuses.append(f"ЛОВ {'+' if bonus.dexterity > 0 else ''}{bonus.dexterity}")
        if bonus.constitution != 0:
            stat_bonuses.append(f"ТЕЛ {'+' if bonus.constitution > 0 else ''}{bonus.constitution}")
        if bonus.intelligence != 0:
            stat_bonuses.append(f"ИНТ {'+' if bonus.intelligence > 0 else ''}{bonus.intelligence}")
        if bonus.wisdom != 0:
            stat_bonuses.append(f"МДР {'+' if bonus.wisdom > 0 else ''}{bonus.wisdom}")
        if bonus.charisma != 0:
            stat_bonuses.append(f"ХАР {'+' if bonus.charisma > 0 else ''}{bonus.charisma}")

        if stat_bonuses:
            lines.append(", ".join(stat_bonuses))

        # Прочность
        if self.DURABILITY_MAX > 0:
            lines.append(f"Прочность: {self.durability}/{self.DURABILITY_MAX}")

        # Требования
        req = self.REQUIREMENTS
        requirements = []
        if req.min_level > 0:
            requirements.append(f"Уровень {req.min_level}")
        if req.min_strength > 0:
            requirements.append(f"Сила {req.min_strength}")
        if req.required_proficiency:
            requirements.append(f"Владение: {req.required_proficiency}")

        if requirements:
            lines.append("")
            lines.append(f"Требуется: {', '.join(requirements)}")

        # Особые свойства
        if self.MAGICAL:
            lines.append("[Магический]")
        if self.ATTUNEMENT:
            lines.append("[Требует настройки]")
        if self.CURSED:
            lines.append("[Проклятый]")

        return "\n".join(lines)

    @classmethod
    def get_info(cls) -> dict:
        """Расширенная информация о классе экипировки."""
        info = super().get_info()
        info.update({
            "equipment_slot": cls.EQUIPMENT_SLOT.value if cls.EQUIPMENT_SLOT else None,
            "equipment_type": cls.EQUIPMENT_TYPE,
            "stat_bonus": cls.STAT_BONUS.to_dict() if cls.STAT_BONUS else {},
            "durability_max": cls.DURABILITY_MAX,
            "magical": cls.MAGICAL,
            "attunement": cls.ATTUNEMENT,
        })
        return info
