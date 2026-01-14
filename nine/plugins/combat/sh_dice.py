"""
D&D 5e Dice Rolling System.
Система бросков кубов для D&D 5e.

Поддерживает:
- Стандартную нотацию (2d6+3, 1d20, 4d6-1)
- Преимущество/помеху для d20
- Критические попадания (удвоение кубов урона)
- Автоматическое определение крита (20) и промаха (1)
"""

import random
import re
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class DiceRoll:
    """Результат броска кубов."""
    dice_notation: str           # Исходная нотация (например, "2d6+3")
    rolls: List[int]             # Результаты отдельных кубов
    modifier: int                # Статический модификатор
    total: int                   # Итоговый результат
    is_critical: bool = False    # Натуральная 20 на d20
    is_fumble: bool = False      # Натуральная 1 на d20
    advantage: bool = False      # Бросок с преимуществом
    disadvantage: bool = False   # Бросок с помехой
    dropped_rolls: List[int] = field(default_factory=list)  # Отброшенные кубы

    def __str__(self) -> str:
        """Строковое представление броска."""
        rolls_str = ", ".join(str(r) for r in self.rolls)
        if self.dropped_rolls:
            dropped_str = ", ".join(str(r) for r in self.dropped_rolls)
            rolls_str += f" (отброшено: {dropped_str})"

        result = f"{self.dice_notation}: [{rolls_str}]"
        if self.modifier > 0:
            result += f" + {self.modifier}"
        elif self.modifier < 0:
            result += f" - {abs(self.modifier)}"
        result += f" = {self.total}"

        if self.is_critical:
            result += " [КРИТ!]"
        elif self.is_fumble:
            result += " [ПРОМАХ!]"

        return result


class DiceRoller:
    """
    Утилита для бросков кубов D&D 5e.

    Примеры использования:
        roll = DiceRoller.roll("2d6+3")
        attack, roll = DiceRoller.roll_attack(5, advantage=True)
        damage = DiceRoller.roll_damage("1d8+3", critical=True)
    """

    # Паттерн для парсинга нотации кубов: [число]d[грани][+/-модификатор]
    DICE_PATTERN = re.compile(r'^(\d*)d(\d+)([+-]\d+)?$')

    @classmethod
    def roll(cls, notation: str, advantage: bool = False,
             disadvantage: bool = False) -> DiceRoll:
        """
        Бросает кубы по D&D нотации.

        Args:
            notation: Нотация кубов (например, "2d6+3", "1d20", "4d6")
            advantage: Бросить дважды и взять лучший (только для 1d20)
            disadvantage: Бросить дважды и взять худший (только для 1d20)

        Returns:
            DiceRoll с результатами броска

        Raises:
            ValueError: Если нотация некорректна
        """
        # Убираем пробелы и приводим к нижнему регистру
        notation = notation.replace(" ", "").lower()

        match = cls.DICE_PATTERN.match(notation)
        if not match:
            raise ValueError(f"Некорректная нотация кубов: {notation}")

        # Парсим компоненты
        num_dice = int(match.group(1)) if match.group(1) else 1
        die_sides = int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0

        if die_sides < 1:
            raise ValueError(f"Количество граней должно быть >= 1: {die_sides}")
        if num_dice < 1:
            raise ValueError(f"Количество кубов должно быть >= 1: {num_dice}")

        rolls = []
        dropped_rolls = []
        is_critical = False
        is_fumble = False

        # Особая обработка преимущества/помехи для d20
        if die_sides == 20 and num_dice == 1 and (advantage or disadvantage):
            roll1 = random.randint(1, 20)
            roll2 = random.randint(1, 20)

            if advantage:
                if roll1 >= roll2:
                    rolls = [roll1]
                    dropped_rolls = [roll2]
                else:
                    rolls = [roll2]
                    dropped_rolls = [roll1]
            else:  # disadvantage
                if roll1 <= roll2:
                    rolls = [roll1]
                    dropped_rolls = [roll2]
                else:
                    rolls = [roll2]
                    dropped_rolls = [roll1]

            # Проверяем крит/промах по выбранному кубу
            is_critical = rolls[0] == 20
            is_fumble = rolls[0] == 1
        else:
            # Обычный бросок
            rolls = [random.randint(1, die_sides) for _ in range(num_dice)]

            # Крит/промах только для одиночного d20
            if die_sides == 20 and num_dice == 1:
                is_critical = rolls[0] == 20
                is_fumble = rolls[0] == 1

        total = sum(rolls) + modifier

        return DiceRoll(
            dice_notation=notation,
            rolls=rolls,
            modifier=modifier,
            total=total,
            is_critical=is_critical,
            is_fumble=is_fumble,
            advantage=advantage,
            disadvantage=disadvantage,
            dropped_rolls=dropped_rolls
        )

    @classmethod
    def roll_initiative(cls, dex_modifier: int) -> Tuple[int, DiceRoll]:
        """
        Бросает инициативу (d20 + DEX модификатор).

        Args:
            dex_modifier: Модификатор ловкости

        Returns:
            Tuple[итоговая инициатива, DiceRoll]
        """
        notation = f"1d20+{dex_modifier}" if dex_modifier >= 0 else f"1d20{dex_modifier}"
        roll = cls.roll(notation)
        return roll.total, roll

    @classmethod
    def roll_attack(cls, attack_bonus: int, advantage: bool = False,
                    disadvantage: bool = False) -> Tuple[int, DiceRoll]:
        """
        Бросает атаку (d20 + бонус атаки).

        Args:
            attack_bonus: Бонус атаки
            advantage: Преимущество
            disadvantage: Помеха

        Returns:
            Tuple[итоговый бросок атаки, DiceRoll]

        Note:
            Если есть и преимущество, и помеха - они взаимоуничтожаются
        """
        # Преимущество и помеха отменяют друг друга
        if advantage and disadvantage:
            advantage = False
            disadvantage = False

        roll = cls.roll("1d20", advantage=advantage, disadvantage=disadvantage)
        total = roll.total + attack_bonus

        # Создаём новый DiceRoll с учётом бонуса атаки
        return total, DiceRoll(
            dice_notation=f"1d20+{attack_bonus}" if attack_bonus >= 0 else f"1d20{attack_bonus}",
            rolls=roll.rolls,
            modifier=attack_bonus,
            total=total,
            is_critical=roll.is_critical,
            is_fumble=roll.is_fumble,
            advantage=advantage,
            disadvantage=disadvantage,
            dropped_rolls=roll.dropped_rolls
        )

    @classmethod
    def roll_damage(cls, damage_dice: str, critical: bool = False) -> DiceRoll:
        """
        Бросает урон. При критическом попадании удваивает кубы.

        Args:
            damage_dice: Нотация урона (например, "2d6+3")
            critical: Критическое попадание (удваивает кубы)

        Returns:
            DiceRoll с результатом урона
        """
        if critical:
            # Парсим и удваиваем количество кубов
            match = cls.DICE_PATTERN.match(damage_dice.replace(" ", "").lower())
            if match:
                num_dice = int(match.group(1)) if match.group(1) else 1
                die_sides = match.group(2)
                modifier = match.group(3) or ""
                # Удваиваем кубы, модификатор остаётся
                doubled_notation = f"{num_dice * 2}d{die_sides}{modifier}"
                return cls.roll(doubled_notation)

        return cls.roll(damage_dice)

    @classmethod
    def roll_saving_throw(cls, save_modifier: int, advantage: bool = False,
                          disadvantage: bool = False) -> Tuple[int, DiceRoll]:
        """
        Бросает спасбросок (d20 + модификатор).

        Args:
            save_modifier: Модификатор спасброска
            advantage: Преимущество
            disadvantage: Помеха

        Returns:
            Tuple[итоговый результат, DiceRoll]
        """
        return cls.roll_attack(save_modifier, advantage, disadvantage)

    @classmethod
    def roll_ability_check(cls, ability_modifier: int, proficiency: int = 0,
                           advantage: bool = False,
                           disadvantage: bool = False) -> Tuple[int, DiceRoll]:
        """
        Бросает проверку характеристики (d20 + модификатор + владение).

        Args:
            ability_modifier: Модификатор характеристики
            proficiency: Бонус владения (0 если нет владения)
            advantage: Преимущество
            disadvantage: Помеха

        Returns:
            Tuple[итоговый результат, DiceRoll]
        """
        total_bonus = ability_modifier + proficiency
        return cls.roll_attack(total_bonus, advantage, disadvantage)

    @classmethod
    def roll_4d6_drop_lowest(cls) -> Tuple[int, DiceRoll]:
        """
        Бросает 4d6 и отбрасывает наименьший — стандартный метод генерации характеристик.

        Returns:
            Tuple[сумма трёх лучших, DiceRoll]
        """
        rolls = [random.randint(1, 6) for _ in range(4)]
        sorted_rolls = sorted(rolls, reverse=True)

        kept = sorted_rolls[:3]
        dropped = sorted_rolls[3:]

        total = sum(kept)

        return total, DiceRoll(
            dice_notation="4d6 drop lowest",
            rolls=kept,
            modifier=0,
            total=total,
            dropped_rolls=dropped
        )

    @classmethod
    def roll_percentile(cls) -> Tuple[int, DiceRoll]:
        """
        Бросает процентный куб (d100).

        Returns:
            Tuple[результат 1-100, DiceRoll]
        """
        roll = cls.roll("1d100")
        return roll.total, roll

    @classmethod
    def roll_hit_die(cls, hit_die: str, con_modifier: int) -> DiceRoll:
        """
        Бросает кость хитов для восстановления HP.

        Args:
            hit_die: Кость хитов класса (например, "1d10")
            con_modifier: Модификатор телосложения

        Returns:
            DiceRoll (минимум 1 HP восстановлено)
        """
        notation = f"{hit_die}+{con_modifier}" if con_modifier >= 0 else f"{hit_die}{con_modifier}"
        roll = cls.roll(notation)

        # Минимум 1 HP при броске кости хитов
        if roll.total < 1:
            roll.total = 1

        return roll
