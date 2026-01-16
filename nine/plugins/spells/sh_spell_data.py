"""
Dataclasses для системы заклинаний.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class SpellSchool(Enum):
    """Школы магии D&D."""
    ABJURATION = "abjuration"
    CONJURATION = "conjuration"
    DIVINATION = "divination"
    ENCHANTMENT = "enchantment"
    EVOCATION = "evocation"
    ILLUSION = "illusion"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"


class SpellComponent(Enum):
    """Компоненты заклинания."""
    VERBAL = "V"
    SOMATIC = "S"
    MATERIAL = "M"


class SpellTargetType(Enum):
    """Типы целей заклинания."""
    SELF = "self"
    TOUCH = "touch"
    SINGLE = "single"
    MULTIPLE = "multiple"
    AREA_CONE = "cone"
    AREA_CUBE = "cube"
    AREA_CYLINDER = "cylinder"
    AREA_LINE = "line"
    AREA_SPHERE = "sphere"


class SpellDurationType(Enum):
    """Типы длительности."""
    INSTANTANEOUS = "instantaneous"
    CONCENTRATION = "concentration"
    TIMED = "timed"


class DamageType(Enum):
    """Типы урона."""
    ACID = "acid"
    BLUDGEONING = "bludgeoning"
    COLD = "cold"
    FIRE = "fire"
    FORCE = "force"
    LIGHTNING = "lightning"
    NECROTIC = "necrotic"
    PIERCING = "piercing"
    POISON = "poison"
    PSYCHIC = "psychic"
    RADIANT = "radiant"
    SLASHING = "slashing"
    THUNDER = "thunder"


@dataclass
class SpellEffect:
    """Эффект заклинания."""
    effect_type: str  # damage, heal, buff, debuff, summon, utility
    damage_type: Optional[str] = None
    dice_count: int = 0
    dice_size: int = 0
    modifier: int = 0
    condition: Optional[str] = None  # Применяемое условие
    duration_rounds: int = 0
    save_ability: Optional[str] = None  # STR, DEX, CON, INT, WIS, CHA
    save_dc_type: str = "spell"  # spell или фиксированное число

    def roll_damage(self) -> int:
        """Бросает урон/хил."""
        import random
        total = 0
        for _ in range(self.dice_count):
            total += random.randint(1, self.dice_size)
        return total + self.modifier


@dataclass
class Spell:
    """Заклинание D&D 5e."""
    id: str
    name: str
    level: int  # 0 = cantrip
    school: str
    casting_time: str  # "1 action", "1 bonus action", "1 reaction", etc.
    range_ft: int  # 0 = self, -1 = touch
    components: List[str] = field(default_factory=list)  # ["V", "S", "M"]
    material: Optional[str] = None  # Описание материального компонента
    duration: str  # "Instantaneous", "Concentration, up to 1 minute", etc.
    concentration: bool = False
    ritual: bool = False
    description: str = ""
    higher_levels: Optional[str] = None  # Описание каста на высоком уровне

    # Целеуказание
    target_type: str = "single"
    area_size: int = 0  # Размер области в футах

    # Эффекты
    effects: List[Dict[str, Any]] = field(default_factory=list)

    # Классы, которые могут изучить
    classes: List[str] = field(default_factory=list)

    @property
    def is_cantrip(self) -> bool:
        return self.level == 0

    def get_slot_level_label(self) -> str:
        """Возвращает метку уровня слота."""
        if self.level == 0:
            return "Cantrip"
        return f"Level {self.level}"

    def get_range_label(self) -> str:
        """Возвращает текстовое описание дальности."""
        if self.range_ft == 0:
            return "Self"
        elif self.range_ft == -1:
            return "Touch"
        else:
            return f"{self.range_ft} ft."

    def get_components_label(self) -> str:
        """Возвращает строку компонентов."""
        result = ", ".join(self.components)
        if self.material:
            result += f" ({self.material})"
        return result


@dataclass
class SpellSlots:
    """Слоты заклинаний персонажа."""
    # Текущие слоты (могут быть потрачены)
    current: Dict[int, int] = field(default_factory=dict)  # level -> count
    # Максимальные слоты
    maximum: Dict[int, int] = field(default_factory=dict)  # level -> count

    def use_slot(self, level: int) -> bool:
        """Тратит слот указанного уровня. Возвращает успех."""
        if level not in self.current or self.current[level] <= 0:
            return False
        self.current[level] -= 1
        return True

    def restore_slot(self, level: int, count: int = 1) -> None:
        """Восстанавливает слоты."""
        if level in self.maximum:
            self.current[level] = min(
                self.current.get(level, 0) + count,
                self.maximum[level]
            )

    def restore_all(self) -> None:
        """Полностью восстанавливает все слоты."""
        self.current = self.maximum.copy()

    def has_slot(self, level: int) -> bool:
        """Проверяет наличие слота указанного уровня."""
        return self.current.get(level, 0) > 0

    def get_available_levels(self) -> List[int]:
        """Возвращает список уровней с доступными слотами."""
        return [lvl for lvl, count in self.current.items() if count > 0]


@dataclass
class CharacterSpellcasting:
    """Данные заклинательства персонажа."""
    # Основная способность для заклинаний
    spellcasting_ability: str = "INT"  # INT, WIS, CHA

    # Изученные заклинания (для Wizard, Bard и т.д.)
    spells_known: List[str] = field(default_factory=list)  # spell_ids

    # Подготовленные заклинания (для Wizard, Cleric и т.д.)
    spells_prepared: List[str] = field(default_factory=list)  # spell_ids

    # Слоты заклинаний
    spell_slots: SpellSlots = field(default_factory=SpellSlots)

    # Текущая концентрация
    concentrating_on: Optional[str] = None  # spell_id
    concentration_target: Optional[str] = None  # entity_id цели
    concentration_rounds_left: int = 0

    def can_cast(self, spell: Spell, at_level: Optional[int] = None) -> bool:
        """Проверяет, может ли персонаж скастовать заклинание."""
        # Cantrip'ы всегда можно кастовать
        if spell.is_cantrip:
            return True

        # Определяем уровень слота
        cast_level = at_level if at_level is not None else spell.level

        # Проверяем, что есть слот нужного уровня или выше
        for slot_level in range(cast_level, 10):
            if self.spell_slots.has_slot(slot_level):
                return True

        return False

    def start_concentration(self, spell_id: str, target_id: Optional[str], rounds: int):
        """Начинает концентрацию на заклинании."""
        # Если уже концентрируемся - прерываем предыдущее
        self.concentrating_on = spell_id
        self.concentration_target = target_id
        self.concentration_rounds_left = rounds

    def break_concentration(self):
        """Прерывает текущую концентрацию."""
        self.concentrating_on = None
        self.concentration_target = None
        self.concentration_rounds_left = 0

    def tick_concentration(self) -> bool:
        """Уменьшает счётчик концентрации. Возвращает True если закончилась."""
        if self.concentration_rounds_left > 0:
            self.concentration_rounds_left -= 1
            if self.concentration_rounds_left <= 0:
                spell_id = self.concentrating_on
                self.break_concentration()
                return True
        return False
