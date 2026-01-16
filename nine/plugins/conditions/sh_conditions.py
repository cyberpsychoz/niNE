"""
Определения состояний D&D 5e.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set
from enum import Enum


class ConditionType(Enum):
    """Типы состояний D&D 5e."""
    BLINDED = "blinded"
    CHARMED = "charmed"
    DEAFENED = "deafened"
    FRIGHTENED = "frightened"
    GRAPPLED = "grappled"
    INCAPACITATED = "incapacitated"
    INVISIBLE = "invisible"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    POISONED = "poisoned"
    PRONE = "prone"
    RESTRAINED = "restrained"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"
    # Дополнительные состояния
    EXHAUSTION = "exhaustion"
    HASTED = "hasted"
    BLESSED = "blessed"
    CONCENTRATION = "concentration"


@dataclass
class ConditionEffect:
    """Эффекты, накладываемые состоянием."""
    # Модификаторы к броскам
    attack_advantage: bool = False
    attack_disadvantage: bool = False
    attacks_against_advantage: bool = False
    attacks_against_disadvantage: bool = False

    # Автопровалы спасбросков
    auto_fail_str_saves: bool = False
    auto_fail_dex_saves: bool = False

    # Advantage/Disadvantage на спасброски
    str_save_advantage: bool = False
    str_save_disadvantage: bool = False
    dex_save_advantage: bool = False
    dex_save_disadvantage: bool = False
    con_save_advantage: bool = False
    con_save_disadvantage: bool = False

    # Блокировка действий
    cannot_move: bool = False
    cannot_take_actions: bool = False
    cannot_take_reactions: bool = False
    cannot_speak: bool = False

    # Скорость
    speed_zero: bool = False
    speed_halved: bool = False
    speed_multiplier: float = 1.0

    # AC модификаторы
    ac_bonus: int = 0

    # Урон
    damage_resistance: List[str] = field(default_factory=list)
    damage_vulnerability: List[str] = field(default_factory=list)
    damage_immunity: List[str] = field(default_factory=list)

    # Специальные эффекты
    auto_crit_within_5ft: bool = False  # Атаки в пределах 5 футов автокрит
    drops_held_items: bool = False
    falls_prone: bool = False

    # Проверки способностей
    ability_check_disadvantage: List[str] = field(default_factory=list)  # ["STR", "DEX", ...]


@dataclass
class Condition:
    """Определение состояния D&D 5e."""
    id: str
    name: str
    name_ru: str
    description: str
    description_ru: str
    icon: str  # Имя иконки для UI
    color: tuple  # RGBA цвет для отображения
    effects: ConditionEffect
    # Состояния, которые это состояние включает
    includes: List[str] = field(default_factory=list)


# =============================================================================
# Определения всех стандартных состояний D&D 5e
# =============================================================================

CONDITIONS: Dict[str, Condition] = {
    "blinded": Condition(
        id="blinded",
        name="Blinded",
        name_ru="Ослеплён",
        description="A blinded creature can't see and automatically fails any ability check that requires sight. Attack rolls against the creature have advantage, and the creature's attack rolls have disadvantage.",
        description_ru="Ослеплённое существо не видит и автоматически проваливает проверки, требующие зрения. Броски атаки по нему совершаются с преимуществом, а его броски атаки — с помехой.",
        icon="blind",
        color=(0.3, 0.3, 0.3, 1),
        effects=ConditionEffect(
            attack_disadvantage=True,
            attacks_against_advantage=True,
            ability_check_disadvantage=["perception_sight"],
        ),
    ),

    "charmed": Condition(
        id="charmed",
        name="Charmed",
        name_ru="Очарован",
        description="A charmed creature can't attack the charmer or target the charmer with harmful abilities or magical effects. The charmer has advantage on any ability check to interact socially with the creature.",
        description_ru="Очарованное существо не может атаковать очаровавшего или делать его целью вредоносных способностей. Очаровавший совершает проверки харизмы для социального взаимодействия с существом с преимуществом.",
        icon="heart",
        color=(1.0, 0.5, 0.8, 1),
        effects=ConditionEffect(),  # Особый эффект - не может атаковать источник
    ),

    "deafened": Condition(
        id="deafened",
        name="Deafened",
        name_ru="Оглушён",
        description="A deafened creature can't hear and automatically fails any ability check that requires hearing.",
        description_ru="Оглушённое существо не слышит и автоматически проваливает проверки, требующие слуха.",
        icon="deaf",
        color=(0.5, 0.5, 0.6, 1),
        effects=ConditionEffect(
            ability_check_disadvantage=["perception_hearing"],
        ),
    ),

    "frightened": Condition(
        id="frightened",
        name="Frightened",
        name_ru="Испуган",
        description="A frightened creature has disadvantage on ability checks and attack rolls while the source of its fear is within line of sight. The creature can't willingly move closer to the source of its fear.",
        description_ru="Испуганное существо совершает проверки характеристик и броски атаки с помехой, пока видит источник страха. Существо не может добровольно приближаться к источнику страха.",
        icon="fear",
        color=(0.6, 0.3, 0.6, 1),
        effects=ConditionEffect(
            attack_disadvantage=True,
            ability_check_disadvantage=["all"],
        ),
    ),

    "grappled": Condition(
        id="grappled",
        name="Grappled",
        name_ru="Схвачен",
        description="A grappled creature's speed becomes 0, and it can't benefit from any bonus to its speed. The condition ends if the grappler is incapacitated or if an effect removes the grappled creature from the reach of the grappler.",
        description_ru="Скорость схваченного существа становится 0, и оно не получает бонусов к скорости. Состояние заканчивается, если схвативший недееспособен или эффект убирает схваченного из досягаемости.",
        icon="grab",
        color=(0.7, 0.5, 0.3, 1),
        effects=ConditionEffect(
            speed_zero=True,
        ),
    ),

    "incapacitated": Condition(
        id="incapacitated",
        name="Incapacitated",
        name_ru="Недееспособен",
        description="An incapacitated creature can't take actions or reactions.",
        description_ru="Недееспособное существо не может совершать действия и реакции.",
        icon="dizzy",
        color=(0.5, 0.5, 0.5, 1),
        effects=ConditionEffect(
            cannot_take_actions=True,
            cannot_take_reactions=True,
        ),
    ),

    "invisible": Condition(
        id="invisible",
        name="Invisible",
        name_ru="Невидим",
        description="An invisible creature is impossible to see without the aid of magic or a special sense. For the purpose of hiding, the creature is heavily obscured. The creature's location can be detected by any noise it makes or any tracks it leaves. Attack rolls against the creature have disadvantage, and the creature's attack rolls have advantage.",
        description_ru="Невидимое существо невозможно увидеть без магии или особых чувств. Для целей укрытия существо сильно заслонено. Броски атаки по существу совершаются с помехой, а его броски атаки — с преимуществом.",
        icon="invisible",
        color=(0.7, 0.9, 1.0, 0.5),
        effects=ConditionEffect(
            attack_advantage=True,
            attacks_against_disadvantage=True,
        ),
    ),

    "paralyzed": Condition(
        id="paralyzed",
        name="Paralyzed",
        name_ru="Парализован",
        description="A paralyzed creature is incapacitated and can't move or speak. The creature automatically fails Strength and Dexterity saving throws. Attack rolls against the creature have advantage. Any attack that hits the creature is a critical hit if the attacker is within 5 feet.",
        description_ru="Парализованное существо недееспособно, не может двигаться или говорить. Автоматически проваливает спасброски Силы и Ловкости. Броски атаки по нему с преимуществом. Попадание в пределах 5 футов — критическое.",
        icon="paralysis",
        color=(0.8, 0.8, 0.2, 1),
        effects=ConditionEffect(
            cannot_take_actions=True,
            cannot_take_reactions=True,
            cannot_move=True,
            cannot_speak=True,
            auto_fail_str_saves=True,
            auto_fail_dex_saves=True,
            attacks_against_advantage=True,
            auto_crit_within_5ft=True,
        ),
        includes=["incapacitated"],
    ),

    "petrified": Condition(
        id="petrified",
        name="Petrified",
        name_ru="Окаменел",
        description="A petrified creature is transformed into a solid inanimate substance. It is incapacitated, can't move or speak, and is unaware of its surroundings. Attack rolls against the creature have advantage. The creature automatically fails Strength and Dexterity saving throws. The creature has resistance to all damage and is immune to poison and disease.",
        description_ru="Окаменевшее существо превращено в неживую субстанцию. Оно недееспособно, не может двигаться, говорить и не осознаёт окружение. Имеет сопротивление всему урону и иммунитет к яду и болезням.",
        icon="stone",
        color=(0.5, 0.5, 0.5, 1),
        effects=ConditionEffect(
            cannot_take_actions=True,
            cannot_take_reactions=True,
            cannot_move=True,
            cannot_speak=True,
            auto_fail_str_saves=True,
            auto_fail_dex_saves=True,
            attacks_against_advantage=True,
            damage_resistance=["all"],
            damage_immunity=["poison"],
        ),
        includes=["incapacitated"],
    ),

    "poisoned": Condition(
        id="poisoned",
        name="Poisoned",
        name_ru="Отравлен",
        description="A poisoned creature has disadvantage on attack rolls and ability checks.",
        description_ru="Отравленное существо совершает броски атаки и проверки характеристик с помехой.",
        icon="poison",
        color=(0.3, 0.8, 0.3, 1),
        effects=ConditionEffect(
            attack_disadvantage=True,
            ability_check_disadvantage=["all"],
        ),
    ),

    "prone": Condition(
        id="prone",
        name="Prone",
        name_ru="Лежит ничком",
        description="A prone creature's only movement option is to crawl. The creature has disadvantage on attack rolls. An attack roll against the creature has advantage if the attacker is within 5 feet, otherwise disadvantage.",
        description_ru="Лежащее существо может только ползти. Совершает броски атаки с помехой. Атака по нему с преимуществом в пределах 5 футов, иначе с помехой.",
        icon="prone",
        color=(0.6, 0.4, 0.2, 1),
        effects=ConditionEffect(
            attack_disadvantage=True,
            speed_halved=True,
            # Особый эффект: advantage/disadvantage зависит от дистанции
        ),
    ),

    "restrained": Condition(
        id="restrained",
        name="Restrained",
        name_ru="Опутан",
        description="A restrained creature's speed becomes 0. Attack rolls against the creature have advantage, and the creature's attack rolls have disadvantage. The creature has disadvantage on Dexterity saving throws.",
        description_ru="Скорость опутанного существа становится 0. Броски атаки по нему с преимуществом, его броски атаки с помехой. Спасброски Ловкости с помехой.",
        icon="chain",
        color=(0.4, 0.4, 0.5, 1),
        effects=ConditionEffect(
            speed_zero=True,
            attack_disadvantage=True,
            attacks_against_advantage=True,
            dex_save_disadvantage=True,
        ),
    ),

    "stunned": Condition(
        id="stunned",
        name="Stunned",
        name_ru="Оглушён",
        description="A stunned creature is incapacitated, can't move, and can speak only falteringly. The creature automatically fails Strength and Dexterity saving throws. Attack rolls against the creature have advantage.",
        description_ru="Оглушённое существо недееспособно, не может двигаться и говорит с трудом. Автоматически проваливает спасброски Силы и Ловкости. Броски атаки по нему с преимуществом.",
        icon="stun",
        color=(1.0, 1.0, 0.3, 1),
        effects=ConditionEffect(
            cannot_take_actions=True,
            cannot_take_reactions=True,
            cannot_move=True,
            auto_fail_str_saves=True,
            auto_fail_dex_saves=True,
            attacks_against_advantage=True,
        ),
        includes=["incapacitated"],
    ),

    "unconscious": Condition(
        id="unconscious",
        name="Unconscious",
        name_ru="Без сознания",
        description="An unconscious creature is incapacitated, can't move or speak, and is unaware of its surroundings. The creature drops whatever it's holding and falls prone. The creature automatically fails Strength and Dexterity saving throws. Attack rolls against the creature have advantage. Any attack that hits the creature is a critical hit if the attacker is within 5 feet.",
        description_ru="Существо без сознания недееспособно, не может двигаться или говорить, не осознаёт окружение. Роняет всё, что держит, и падает ничком. Автопровал спасбросков Силы и Ловкости. Атаки по нему с преимуществом, попадание в пределах 5 футов — критическое.",
        icon="sleep",
        color=(0.2, 0.2, 0.4, 1),
        effects=ConditionEffect(
            cannot_take_actions=True,
            cannot_take_reactions=True,
            cannot_move=True,
            cannot_speak=True,
            auto_fail_str_saves=True,
            auto_fail_dex_saves=True,
            attacks_against_advantage=True,
            auto_crit_within_5ft=True,
            drops_held_items=True,
            falls_prone=True,
        ),
        includes=["incapacitated", "prone"],
    ),

    # Дополнительные состояния (buffs)
    "hasted": Condition(
        id="hasted",
        name="Hasted",
        name_ru="Ускорен",
        description="The creature's speed is doubled, it gains a +2 bonus to AC, it has advantage on Dexterity saving throws, and it gains an additional action on each of its turns.",
        description_ru="Скорость существа удвоена, +2 к AC, преимущество на спасброски Ловкости, дополнительное действие каждый ход.",
        icon="haste",
        color=(0.3, 0.8, 1.0, 1),
        effects=ConditionEffect(
            speed_multiplier=2.0,
            ac_bonus=2,
            dex_save_advantage=True,
        ),
    ),

    "blessed": Condition(
        id="blessed",
        name="Blessed",
        name_ru="Благословлён",
        description="Whenever the target makes an attack roll or a saving throw, it can roll a d4 and add the number rolled.",
        description_ru="При броске атаки или спасброска цель может добавить результат броска d4.",
        icon="bless",
        color=(1.0, 0.9, 0.5, 1),
        effects=ConditionEffect(),  # +1d4, обрабатывается отдельно
    ),
}


def get_condition(condition_id: str) -> Optional[Condition]:
    """Возвращает определение состояния по ID."""
    return CONDITIONS.get(condition_id.lower())


def get_all_conditions() -> List[Condition]:
    """Возвращает список всех состояний."""
    return list(CONDITIONS.values())


def get_combined_effects(condition_ids: List[str]) -> ConditionEffect:
    """
    Объединяет эффекты нескольких состояний.
    Используется для расчёта итоговых модификаторов.
    """
    combined = ConditionEffect()

    for cond_id in condition_ids:
        condition = get_condition(cond_id)
        if not condition:
            continue

        effects = condition.effects

        # Объединяем boolean эффекты (любой True = True)
        combined.attack_advantage = combined.attack_advantage or effects.attack_advantage
        combined.attack_disadvantage = combined.attack_disadvantage or effects.attack_disadvantage
        combined.attacks_against_advantage = combined.attacks_against_advantage or effects.attacks_against_advantage
        combined.attacks_against_disadvantage = combined.attacks_against_disadvantage or effects.attacks_against_disadvantage

        combined.auto_fail_str_saves = combined.auto_fail_str_saves or effects.auto_fail_str_saves
        combined.auto_fail_dex_saves = combined.auto_fail_dex_saves or effects.auto_fail_dex_saves

        combined.str_save_advantage = combined.str_save_advantage or effects.str_save_advantage
        combined.str_save_disadvantage = combined.str_save_disadvantage or effects.str_save_disadvantage
        combined.dex_save_advantage = combined.dex_save_advantage or effects.dex_save_advantage
        combined.dex_save_disadvantage = combined.dex_save_disadvantage or effects.dex_save_disadvantage
        combined.con_save_advantage = combined.con_save_advantage or effects.con_save_advantage
        combined.con_save_disadvantage = combined.con_save_disadvantage or effects.con_save_disadvantage

        combined.cannot_move = combined.cannot_move or effects.cannot_move
        combined.cannot_take_actions = combined.cannot_take_actions or effects.cannot_take_actions
        combined.cannot_take_reactions = combined.cannot_take_reactions or effects.cannot_take_reactions
        combined.cannot_speak = combined.cannot_speak or effects.cannot_speak

        combined.speed_zero = combined.speed_zero or effects.speed_zero
        combined.speed_halved = combined.speed_halved or effects.speed_halved

        # AC бонусы складываются
        combined.ac_bonus += effects.ac_bonus

        # Speed multiplier - берём наибольший
        if effects.speed_multiplier > combined.speed_multiplier:
            combined.speed_multiplier = effects.speed_multiplier

        # Списки объединяются
        combined.damage_resistance.extend(effects.damage_resistance)
        combined.damage_vulnerability.extend(effects.damage_vulnerability)
        combined.damage_immunity.extend(effects.damage_immunity)
        combined.ability_check_disadvantage.extend(effects.ability_check_disadvantage)

        combined.auto_crit_within_5ft = combined.auto_crit_within_5ft or effects.auto_crit_within_5ft
        combined.drops_held_items = combined.drops_held_items or effects.drops_held_items
        combined.falls_prone = combined.falls_prone or effects.falls_prone

    return combined
