"""
D&D 5e Action Economy System.
Система экономики действий для D&D 5e.

Каждый ход персонаж может использовать:
- Движение (равное скорости)
- 1 Действие
- 1 Бонусное действие (если есть способность)
- 1 Реакция (можно использовать вне своего хода)
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, List, Dict


class ActionType(Enum):
    """Тип действия в экономике действий D&D."""
    ACTION = auto()           # Стандартное действие
    BONUS_ACTION = auto()     # Бонусное действие
    REACTION = auto()         # Реакция
    FREE = auto()             # Свободное действие
    MOVEMENT = auto()         # Перемещение


class ActionCost(Enum):
    """Стоимость действия."""
    NONE = 0                  # Бесплатно
    ACTION = 1                # Требует действие
    BONUS = 2                 # Требует бонусное действие
    REACTION = 3              # Требует реакцию
    MOVEMENT = 4              # Требует перемещение


class TargetType(Enum):
    """Тип цели для действия."""
    NONE = auto()             # Не требует цели
    SELF = auto()             # На себя
    SINGLE_ENEMY = auto()     # Один враг
    SINGLE_ALLY = auto()      # Один союзник
    SINGLE_ANY = auto()       # Любое существо
    AREA = auto()             # Область
    POINT = auto()            # Точка на земле


@dataclass
class CombatAction:
    """Определение боевого действия D&D."""
    id: str                              # Уникальный ID
    name: str                            # Английское название
    name_ru: str                         # Русское название
    description: str                     # Описание
    description_ru: str                  # Русское описание

    action_type: ActionType              # Тип (действие/бонус/реакция)
    cost: ActionCost                     # Стоимость

    # Требования
    target_type: TargetType = TargetType.NONE
    range_feet: float = 5.0              # Дальность в футах (5 = рукопашная)
    requires_weapon: bool = False        # Требует оружие
    requires_spell_slot: bool = False    # Требует слот заклинания
    requires_concentration: bool = False # Требует концентрацию

    # Эффекты
    attack_roll: bool = False            # Требует бросок атаки
    damage_dice: str = ""                # Кубы урона (например, "1d8+3")
    saving_throw: Optional[str] = None   # Спасбросок (DEX, WIS, etc.)
    saving_throw_dc: int = 0             # DC спасброска

    # Дополнительные эффекты
    conditions_applied: List[str] = field(default_factory=list)  # Применяемые состояния
    conditions_removed: List[str] = field(default_factory=list)  # Снимаемые состояния

    # UI
    icon: str = ""                       # Иконка для UI
    hotkey: str = ""                     # Горячая клавиша

    def can_use(self, has_action: bool, has_bonus: bool, has_reaction: bool) -> bool:
        """Проверяет, можно ли использовать действие."""
        if self.cost == ActionCost.NONE:
            return True
        if self.cost == ActionCost.ACTION:
            return has_action
        if self.cost == ActionCost.BONUS:
            return has_bonus
        if self.cost == ActionCost.REACTION:
            return has_reaction
        return True


# =============================================================================
# Стандартные действия D&D 5e
# =============================================================================

COMBAT_ACTIONS: Dict[str, CombatAction] = {
    # =========================================================================
    # ОСНОВНЫЕ ДЕЙСТВИЯ (Action)
    # =========================================================================

    "attack": CombatAction(
        id="attack",
        name="Attack",
        name_ru="Атака",
        description="Make a melee or ranged attack against a target",
        description_ru="Совершите рукопашную или дальнобойную атаку по цели",
        action_type=ActionType.ACTION,
        cost=ActionCost.ACTION,
        target_type=TargetType.SINGLE_ENEMY,
        range_feet=5.0,  # По умолчанию рукопашная, оружие может менять
        requires_weapon=True,
        attack_roll=True,
        hotkey="1",
    ),

    "dash": CombatAction(
        id="dash",
        name="Dash",
        name_ru="Рывок",
        description="Double your movement speed this turn",
        description_ru="Удвойте свою скорость передвижения на этот ход",
        action_type=ActionType.ACTION,
        cost=ActionCost.ACTION,
        target_type=TargetType.SELF,
        hotkey="2",
    ),

    "disengage": CombatAction(
        id="disengage",
        name="Disengage",
        name_ru="Отход",
        description="Your movement doesn't provoke opportunity attacks this turn",
        description_ru="Ваше передвижение не провоцирует атаки возможности на этот ход",
        action_type=ActionType.ACTION,
        cost=ActionCost.ACTION,
        target_type=TargetType.SELF,
        hotkey="3",
    ),

    "dodge": CombatAction(
        id="dodge",
        name="Dodge",
        name_ru="Уклонение",
        description="Attacks against you have disadvantage until your next turn",
        description_ru="Атаки по вам совершаются с помехой до начала вашего следующего хода",
        action_type=ActionType.ACTION,
        cost=ActionCost.ACTION,
        target_type=TargetType.SELF,
        conditions_applied=["dodging"],
        hotkey="4",
    ),

    "help": CombatAction(
        id="help",
        name="Help",
        name_ru="Помощь",
        description="Give an ally advantage on their next ability check or attack roll",
        description_ru="Дайте союзнику преимущество на следующую проверку или бросок атаки",
        action_type=ActionType.ACTION,
        cost=ActionCost.ACTION,
        target_type=TargetType.SINGLE_ALLY,
        range_feet=5.0,
        hotkey="5",
    ),

    "hide": CombatAction(
        id="hide",
        name="Hide",
        name_ru="Прятки",
        description="Attempt to hide from enemies (Stealth check vs Perception)",
        description_ru="Попытайтесь спрятаться от врагов (проверка Скрытности против Восприятия)",
        action_type=ActionType.ACTION,
        cost=ActionCost.ACTION,
        target_type=TargetType.SELF,
        conditions_applied=["hidden"],
    ),

    "ready": CombatAction(
        id="ready",
        name="Ready",
        name_ru="Подготовка",
        description="Prepare an action to use when a trigger occurs (uses reaction)",
        description_ru="Подготовьте действие для использования при наступлении триггера (использует реакцию)",
        action_type=ActionType.ACTION,
        cost=ActionCost.ACTION,
        target_type=TargetType.SELF,
        conditions_applied=["readied"],
    ),

    "search": CombatAction(
        id="search",
        name="Search",
        name_ru="Поиск",
        description="Make a Perception or Investigation check to find something",
        description_ru="Совершите проверку Восприятия или Анализа для поиска чего-либо",
        action_type=ActionType.ACTION,
        cost=ActionCost.ACTION,
        target_type=TargetType.SELF,
    ),

    "use_object": CombatAction(
        id="use_object",
        name="Use Object",
        name_ru="Использовать предмет",
        description="Interact with an object that requires an action",
        description_ru="Взаимодействуйте с предметом, требующим действия",
        action_type=ActionType.ACTION,
        cost=ActionCost.ACTION,
        target_type=TargetType.NONE,
    ),

    # =========================================================================
    # РЕАКЦИИ (Reaction)
    # =========================================================================

    "opportunity_attack": CombatAction(
        id="opportunity_attack",
        name="Opportunity Attack",
        name_ru="Атака возможности",
        description="Make a melee attack when an enemy leaves your reach",
        description_ru="Совершите рукопашную атаку, когда враг покидает вашу зону досягаемости",
        action_type=ActionType.REACTION,
        cost=ActionCost.REACTION,
        target_type=TargetType.SINGLE_ENEMY,
        range_feet=5.0,
        requires_weapon=True,
        attack_roll=True,
    ),

    # =========================================================================
    # БЕСПЛАТНЫЕ ДЕЙСТВИЯ (Free)
    # =========================================================================

    "end_turn": CombatAction(
        id="end_turn",
        name="End Turn",
        name_ru="Закончить ход",
        description="End your turn and pass to the next combatant",
        description_ru="Завершите свой ход и передайте ход следующему участнику",
        action_type=ActionType.FREE,
        cost=ActionCost.NONE,
        target_type=TargetType.SELF,
        hotkey="E",
    ),

    "drop_item": CombatAction(
        id="drop_item",
        name="Drop Item",
        name_ru="Бросить предмет",
        description="Drop an item you're holding (free action)",
        description_ru="Бросьте предмет, который держите (свободное действие)",
        action_type=ActionType.FREE,
        cost=ActionCost.NONE,
        target_type=TargetType.SELF,
    ),
}


# =============================================================================
# Условия (Conditions)
# =============================================================================

@dataclass
class Condition:
    """Состояние (condition) в D&D."""
    id: str
    name: str
    name_ru: str
    description: str
    description_ru: str
    duration_rounds: int = -1  # -1 = бесконечно (до снятия)
    ends_on_save: bool = False  # Снимается при успешном спасброске


CONDITIONS: Dict[str, Condition] = {
    "blinded": Condition(
        id="blinded",
        name="Blinded",
        name_ru="Ослеплён",
        description="Can't see, auto-fail sight checks, attacks have disadvantage, attacks against have advantage",
        description_ru="Не видит, провал проверок зрения, атаки с помехой, атаки против с преимуществом",
    ),
    "charmed": Condition(
        id="charmed",
        name="Charmed",
        name_ru="Очарован",
        description="Can't attack charmer, charmer has advantage on social checks",
        description_ru="Не может атаковать очаровавшего, очаровавший имеет преимущество на социальные проверки",
    ),
    "deafened": Condition(
        id="deafened",
        name="Deafened",
        name_ru="Оглушён",
        description="Can't hear, auto-fail hearing checks",
        description_ru="Не слышит, провал проверок слуха",
    ),
    "frightened": Condition(
        id="frightened",
        name="Frightened",
        name_ru="Испуган",
        description="Disadvantage on checks/attacks while source visible, can't move closer to source",
        description_ru="Помеха на проверки и атаки пока источник виден, не может приближаться к источнику",
    ),
    "grappled": Condition(
        id="grappled",
        name="Grappled",
        name_ru="Схвачен",
        description="Speed is 0, ends when grappler incapacitated or moved out of reach",
        description_ru="Скорость 0, заканчивается когда схвативший недееспособен или вышел из досягаемости",
    ),
    "incapacitated": Condition(
        id="incapacitated",
        name="Incapacitated",
        name_ru="Недееспособен",
        description="Can't take actions or reactions",
        description_ru="Не может совершать действия или реакции",
    ),
    "invisible": Condition(
        id="invisible",
        name="Invisible",
        name_ru="Невидимый",
        description="Can't be seen without magic, attacks have advantage, attacks against have disadvantage",
        description_ru="Не виден без магии, атаки с преимуществом, атаки против с помехой",
    ),
    "paralyzed": Condition(
        id="paralyzed",
        name="Paralyzed",
        name_ru="Парализован",
        description="Incapacitated, can't move or speak, auto-fail STR/DEX saves, attacks have advantage, melee crits",
        description_ru="Недееспособен, не может двигаться или говорить, провал спасбросков СИЛ/ЛОВ, атаки по нему с преимуществом, критические попадания в ближнем бою",
    ),
    "petrified": Condition(
        id="petrified",
        name="Petrified",
        name_ru="Окаменевший",
        description="Transformed to stone, incapacitated, unaware, resistance to all damage",
        description_ru="Превращён в камень, недееспособен, не осознаёт окружение, сопротивление всему урону",
    ),
    "poisoned": Condition(
        id="poisoned",
        name="Poisoned",
        name_ru="Отравлен",
        description="Disadvantage on attack rolls and ability checks",
        description_ru="Помеха на броски атаки и проверки характеристик",
    ),
    "prone": Condition(
        id="prone",
        name="Prone",
        name_ru="Лежит",
        description="Can only crawl, disadvantage on attacks, melee attacks have advantage, ranged disadvantage",
        description_ru="Может только ползти, помеха на атаки, рукопашные атаки по нему с преимуществом, дальнобойные с помехой",
    ),
    "restrained": Condition(
        id="restrained",
        name="Restrained",
        name_ru="Опутан",
        description="Speed is 0, attacks have disadvantage, attacks against have advantage, DEX saves disadvantage",
        description_ru="Скорость 0, атаки с помехой, атаки против с преимуществом, спасброски ЛОВ с помехой",
    ),
    "stunned": Condition(
        id="stunned",
        name="Stunned",
        name_ru="Оглушён",
        description="Incapacitated, can't move, speak falteringly, auto-fail STR/DEX saves, attacks have advantage",
        description_ru="Недееспособен, не может двигаться, говорит с трудом, провал спасбросков СИЛ/ЛОВ, атаки против с преимуществом",
    ),
    "unconscious": Condition(
        id="unconscious",
        name="Unconscious",
        name_ru="Без сознания",
        description="Incapacitated, drops items, falls prone, auto-fail STR/DEX saves, attacks have advantage, melee crits",
        description_ru="Недееспособен, роняет предметы, падает, провал СИЛ/ЛОВ спасбросков, атаки с преимуществом, рукопашные криты",
    ),

    # Временные состояния от действий
    "dodging": Condition(
        id="dodging",
        name="Dodging",
        name_ru="Уклоняется",
        description="Attacks against have disadvantage, DEX saves have advantage",
        description_ru="Атаки против с помехой, спасброски ЛОВ с преимуществом",
        duration_rounds=1,
    ),
    "hidden": Condition(
        id="hidden",
        name="Hidden",
        name_ru="Скрыт",
        description="Can't be seen, attacks have advantage",
        description_ru="Не виден, атаки с преимуществом",
    ),
    "readied": Condition(
        id="readied",
        name="Readied",
        name_ru="Подготовлен",
        description="Has a readied action waiting for trigger",
        description_ru="Имеет подготовленное действие, ожидающее триггера",
        duration_rounds=1,
    ),
    "concentrating": Condition(
        id="concentrating",
        name="Concentrating",
        name_ru="Концентрация",
        description="Maintaining concentration on a spell",
        description_ru="Поддерживает концентрацию на заклинании",
    ),
}


# =============================================================================
# Утилиты
# =============================================================================

def get_action(action_id: str) -> Optional[CombatAction]:
    """Получает действие по ID."""
    return COMBAT_ACTIONS.get(action_id)


def get_condition(condition_id: str) -> Optional[Condition]:
    """Получает состояние по ID."""
    return CONDITIONS.get(condition_id)


def get_available_actions(has_action: bool, has_bonus: bool, has_reaction: bool,
                          in_melee_range: bool = False) -> List[CombatAction]:
    """
    Возвращает список доступных действий на основе экономики действий.

    Args:
        has_action: Есть ли неиспользованное действие
        has_bonus: Есть ли неиспользованное бонусное действие
        has_reaction: Есть ли неиспользованная реакция
        in_melee_range: Есть ли враги в зоне рукопашной атаки

    Returns:
        Список доступных действий
    """
    available = []

    for action in COMBAT_ACTIONS.values():
        if action.can_use(has_action, has_bonus, has_reaction):
            # Атака возможности доступна только вне своего хода
            if action.id == "opportunity_attack":
                continue
            available.append(action)

    return available
