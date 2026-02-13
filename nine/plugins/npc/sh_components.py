"""
Компоненты NPC для ECS системы.

Все компоненты — это чистые данные (dataclass).
Логика обрабатывается в системах (sv_npc_ai.py и др.)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum, auto
from panda3d.core import Vec3

from nine.core.ecs import Component


# =============================================================================
# Перечисления
# =============================================================================

class AIBehavior(Enum):
    """Типы AI поведения."""
    IDLE = auto()       # Стоит на месте
    NEUTRAL = auto()    # Нейтральный, не атакует первым
    PATROL = auto()     # Патрулирует по точкам
    HOSTILE = auto()    # Враждебный, атакует
    FOLLOW = auto()     # Следует за целью
    FLEE = auto()       # Убегает
    SCHEDULE = auto()   # По расписанию
    WANDER = auto()     # Случайное блуждание


class AIState(Enum):
    """Состояния AI."""
    IDLE = auto()           # Ничего не делает
    MOVING = auto()         # Двигается к цели
    ATTACKING = auto()      # Атакует
    PURSUING = auto()       # Преследует цель
    FLEEING = auto()        # Убегает
    INTERACTING = auto()    # Взаимодействует (диалог)
    DEAD = auto()           # Мёртв


class InteractionType(Enum):
    """Типы взаимодействия с NPC."""
    TALK = auto()       # Диалог
    TRADE = auto()      # Торговля
    ATTACK = auto()     # Атака
    LOOT = auto()       # Сбор лута


# =============================================================================
# Базовые компоненты
# =============================================================================

@dataclass
class PositionComponent(Component):
    """
    Позиция и ориентация NPC в мире.
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0  # Поворот по Z (градусы)

    # Скорость (для интерполяции на клиенте)
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    velocity_z: float = 0.0

    def get_pos(self) -> Vec3:
        """Возвращает позицию как Vec3."""
        return Vec3(self.x, self.y, self.z)

    def set_pos(self, pos: Vec3) -> None:
        """Устанавливает позицию из Vec3."""
        self.x = pos.x
        self.y = pos.y
        self.z = pos.z

    def distance_to(self, other_x: float, other_y: float) -> float:
        """Вычисляет расстояние до точки (2D)."""
        dx = self.x - other_x
        dy = self.y - other_y
        return (dx * dx + dy * dy) ** 0.5


@dataclass
class ModelComponent(Component):
    """
    Визуальная модель NPC.
    """
    model_path: str = ""           # Путь к .bam модели
    scale: float = 1.0             # Масштаб модели
    current_animation: str = "idle"  # Текущая анимация
    animation_speed: float = 1.0   # Скорость анимации
    tint_r: float = 1.0            # Цвет (для выделения)
    tint_g: float = 1.0
    tint_b: float = 1.0
    visible: bool = True           # Видимость


@dataclass
class AIComponent(Component):
    """
    AI behavior for NPC.
    """
    behavior: AIBehavior = AIBehavior.IDLE
    state: AIState = AIState.IDLE

    # Aggression parameters
    aggro_radius: float = 10.0     # Enemy detection radius
    leash_radius: float = 30.0     # Maximum pursuit distance
    attack_range: float = 2.0      # Attack distance

    # Patrolling
    patrol_points: List[tuple] = field(default_factory=list)  # [(x, y, z), ...]
    current_patrol_index: int = 0
    patrol_wait_time: float = 2.0  # Wait time at each point
    patrol_timer: float = 0.0

    # Pursuit
    target_entity_id: Optional[str] = None  # Target ID (player/NPC)
    last_known_target_pos: Optional[tuple] = None

    # Wander (random wandering)
    wander_radius: float = 5.0
    wander_center: Optional[tuple] = None
    wander_timer: float = 0.0
    wander_interval: float = 5.0   # Interval for choosing new point

    # General parameters
    move_speed: float = 0.6        # Movement speed
    think_interval: float = 0.5    # AI update interval

    # LOD (Level of Detail) - set by AISystem
    lod_level: int = 0             # 0=NEAR, 1=MEDIUM, 2=FAR, 3=VERY_FAR, 4=SLEEPING


@dataclass
class PathfindingComponent(Component):
    """
    Навигация NPC.
    """
    # Текущий путь
    current_path: List[Vec3] = field(default_factory=list)
    current_waypoint_index: int = 0

    # Цель
    target_position: Optional[Vec3] = None
    needs_repath: bool = False

    # Параметры движения
    waypoint_radius: float = 0.5   # Радиус достижения точки
    repath_interval: float = 1.0   # Интервал перерасчёта пути
    repath_timer: float = 0.0

    # Состояние
    is_stuck: bool = False
    stuck_timer: float = 0.0
    stuck_threshold: float = 3.0   # Время до признания "застрял"

    # Steering
    velocity: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    max_speed: float = 0.6
    max_force: float = 2.0  # Gentle steering for smooth turns


@dataclass
class CombatComponent(Component):
    """
    Боевые характеристики NPC (D&D стиль).
    """
    # Здоровье
    hp_current: int = 10
    hp_max: int = 10

    # Защита
    armor_class: int = 10

    # Атака
    attack_bonus: int = 0          # Бонус к броску атаки
    damage_dice: str = "1d6"       # Кости урона
    damage_bonus: int = 0          # Бонус к урону
    damage_type: str = "slashing"  # Тип урона

    # Боевые параметры
    attack_cooldown: float = 2.0   # Кулдаун атаки (сек)
    attack_timer: float = 0.0

    # Спасброски
    save_str: int = 0
    save_dex: int = 0
    save_con: int = 0
    save_int: int = 0
    save_wis: int = 0
    save_cha: int = 0

    # Challenge Rating (для наград)
    cr: float = 0.25

    # Состояние
    is_dead: bool = False
    death_time: float = 0.0
    corpse_despawn_time: float = 60.0  # Время до исчезновения трупа


@dataclass
class CombatSessionComponent(Component):
    """
    Компонент участия в пошаговом бою.
    Добавляется сущностям при входе в бой, удаляется при выходе.
    """
    # Идентификация боя
    combat_id: str = ""                      # UUID боевой сессии

    # Инициатива
    initiative: int = 0                       # Результат броска инициативы
    initiative_modifier: int = 0              # Модификатор (обычно DEX)
    turn_order_position: int = 0              # Позиция в очереди ходов

    # Экономика действий (сбрасывается в начале хода)
    movement_remaining: float = 30.0          # Оставшееся движение в футах
    movement_speed: float = 30.0              # Базовая скорость
    has_action: bool = True                   # Есть действие
    has_bonus_action: bool = True             # Есть бонусное действие
    has_reaction: bool = True                 # Есть реакция

    # Состояние хода
    is_current_turn: bool = False             # Сейчас ход этой сущности
    is_incapacitated: bool = False            # Не может действовать
    has_used_movement: bool = False           # Использовал движение

    # Боевые состояния (conditions)
    conditions: List[str] = field(default_factory=list)  # ["poisoned", "prone"]
    condition_durations: Dict[str, int] = field(default_factory=dict)  # {"stunned": 2}
    condition_sources: Dict[str, str] = field(default_factory=dict)  # {"charmed": "entity_id"}

    # Концентрация (для заклинаний)
    concentrating_on: Optional[str] = None    # ID заклинания
    concentration_target: Optional[str] = None  # Цель концентрации

    # Подготовленное действие
    readied_action: Optional[str] = None      # ID действия
    readied_trigger: str = ""                 # Описание триггера

    # Текущая цель
    selected_target_id: Optional[str] = None  # Выбранная цель

    def reset_turn_resources(self):
        """Сбрасывает ресурсы в начале хода."""
        self.movement_remaining = self.movement_speed
        self.has_action = True
        self.has_bonus_action = True
        self.has_reaction = True  # Реакция восстанавливается в начале хода
        self.has_used_movement = False
        self.readied_action = None
        self.readied_trigger = ""

    def consume_action(self) -> bool:
        """Использует действие, возвращает успех."""
        if self.has_action and not self.is_incapacitated:
            self.has_action = False
            return True
        return False

    def consume_bonus_action(self) -> bool:
        """Использует бонусное действие, возвращает успех."""
        if self.has_bonus_action and not self.is_incapacitated:
            self.has_bonus_action = False
            return True
        return False

    def consume_reaction(self) -> bool:
        """Использует реакцию, возвращает успех."""
        if self.has_reaction and not self.is_incapacitated:
            self.has_reaction = False
            return True
        return False

    def consume_movement(self, feet: float) -> bool:
        """Использует движение, возвращает успех."""
        if self.movement_remaining >= feet and not self.is_incapacitated:
            self.movement_remaining -= feet
            self.has_used_movement = True
            return True
        return False

    def add_condition(self, condition_id: str, duration: int = -1, source: str = ""):
        """Добавляет состояние."""
        if condition_id not in self.conditions:
            self.conditions.append(condition_id)
        if duration > 0:
            self.condition_durations[condition_id] = duration
        if source:
            self.condition_sources[condition_id] = source

    def remove_condition(self, condition_id: str):
        """Удаляет состояние."""
        if condition_id in self.conditions:
            self.conditions.remove(condition_id)
        self.condition_durations.pop(condition_id, None)
        self.condition_sources.pop(condition_id, None)

    def has_condition(self, condition_id: str) -> bool:
        """Проверяет наличие состояния."""
        return condition_id in self.conditions

    def tick_conditions(self):
        """Уменьшает длительность состояний в конце хода."""
        expired = []
        for cond, duration in list(self.condition_durations.items()):
            if duration > 0:
                self.condition_durations[cond] = duration - 1
                if self.condition_durations[cond] <= 0:
                    expired.append(cond)

        for cond in expired:
            self.remove_condition(cond)


@dataclass
class TargetableComponent(Component):
    """
    Компонент, делающий сущность доступной для выбора как цели.
    """
    is_targetable: bool = True               # Можно выбрать как цель
    target_priority: int = 0                  # Приоритет для AI (выше = важнее)
    highlight_color: tuple = (1.0, 0.0, 0.0, 0.5)  # Цвет подсветки (RGBA)
    is_highlighted: bool = False              # Сейчас подсвечен
    is_selected: bool = False                 # Сейчас выбран как цель


@dataclass
class FactionComponent(Component):
    """
    Принадлежность к фракции и отношения.
    """
    faction_id: str = "neutral"    # ID фракции

    # Переопределения отношений для конкретного NPC
    # {"faction_id": relation_value}
    disposition_overrides: Dict[str, int] = field(default_factory=dict)

    # Враждебность к игрокам по умолчанию
    hostile_to_players: bool = False


@dataclass
class DialogueComponent(Component):
    """
    Диалоговая система NPC.
    """
    dialogue_id: str = ""          # ID дерева диалога
    current_node_id: str = "start"  # Текущий узел диалога

    # Состояние диалога
    is_in_dialogue: bool = False
    dialogue_partner_id: Optional[str] = None  # ID игрока в диалоге

    # Условия (для проверки в диалогах)
    dialogue_flags: Dict[str, Any] = field(default_factory=dict)

    # Голосовые реплики (опционально)
    greeting_text: str = ""        # Текст при приближении
    greeting_radius: float = 3.0   # Радиус приветствия


@dataclass
class InteractionComponent(Component):
    """
    Типы взаимодействия с NPC.
    """
    # Доступные взаимодействия
    interactions: List[InteractionType] = field(
        default_factory=lambda: [InteractionType.TALK]
    )

    # Радиус взаимодействия
    interaction_radius: float = 2.0

    # Подсказка при наведении
    interaction_prompt: str = "Поговорить"

    # Состояние
    is_interactable: bool = True


@dataclass
class InventoryComponent(Component):
    """
    Инвентарь NPC (для торговцев и лута).
    """
    # Предметы
    items: List[Dict[str, Any]] = field(default_factory=list)

    # Золото
    gold: int = 0

    # Таблица лута (ID таблицы)
    loot_table_id: Optional[str] = None

    # Торговля
    is_merchant: bool = False
    buy_modifier: float = 1.0      # Множитель цены покупки (у NPC)
    sell_modifier: float = 0.5     # Множитель цены продажи (NPC)

    # Уже заглуленный?
    looted: bool = False


@dataclass
class ScheduleComponent(Component):
    """
    Расписание активности NPC (day/night cycle).
    """
    # Расписание: {"06:00": {"action": "move", "target": (x, y, z)}, ...}
    schedule: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Текущая активность
    current_activity: str = "idle"
    activity_target: Optional[tuple] = None

    # Время последней проверки
    last_check_time: str = ""


# =============================================================================
# Компонент-идентификатор NPC
# =============================================================================

@dataclass
class NPCInfoComponent(Component):
    """
    Идентификационная информация NPC.
    """
    template_id: str = ""          # ID шаблона NPC
    display_name: str = "NPC"      # Отображаемое имя
    title: str = ""                # Титул (например, "Торговец")

    # Уникальность
    is_unique: bool = False        # Уникальный NPC (не респавнится)
    is_essential: bool = False     # Не может умереть

    # Теги для поиска
    tags: List[str] = field(default_factory=list)


# =============================================================================
# Реестр компонентов для загрузки из JSON
# =============================================================================

COMPONENT_REGISTRY: Dict[str, type] = {
    "PositionComponent": PositionComponent,
    "ModelComponent": ModelComponent,
    "AIComponent": AIComponent,
    "PathfindingComponent": PathfindingComponent,
    "CombatComponent": CombatComponent,
    "CombatSessionComponent": CombatSessionComponent,
    "TargetableComponent": TargetableComponent,
    "FactionComponent": FactionComponent,
    "DialogueComponent": DialogueComponent,
    "InteractionComponent": InteractionComponent,
    "InventoryComponent": InventoryComponent,
    "ScheduleComponent": ScheduleComponent,
    "NPCInfoComponent": NPCInfoComponent,
}
