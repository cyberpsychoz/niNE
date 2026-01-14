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
    AI поведение NPC.
    """
    behavior: AIBehavior = AIBehavior.IDLE
    state: AIState = AIState.IDLE

    # Параметры агрессии
    aggro_radius: float = 10.0     # Радиус обнаружения врагов
    leash_radius: float = 30.0     # Максимальное расстояние преследования
    attack_range: float = 2.0      # Дистанция атаки

    # Патрулирование
    patrol_points: List[tuple] = field(default_factory=list)  # [(x, y, z), ...]
    current_patrol_index: int = 0
    patrol_wait_time: float = 2.0  # Время ожидания на точке
    patrol_timer: float = 0.0

    # Преследование
    target_entity_id: Optional[str] = None  # ID цели (игрок/NPC)
    last_known_target_pos: Optional[tuple] = None

    # Wander (случайное блуждание)
    wander_radius: float = 5.0
    wander_center: Optional[tuple] = None
    wander_timer: float = 0.0
    wander_interval: float = 5.0   # Интервал выбора новой точки

    # Общие параметры
    move_speed: float = 1.5        # Скорость движения
    think_interval: float = 0.5    # Интервал обновления AI


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
    max_speed: float = 1.5
    max_force: float = 5.0


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
    "FactionComponent": FactionComponent,
    "DialogueComponent": DialogueComponent,
    "InteractionComponent": InteractionComponent,
    "InventoryComponent": InventoryComponent,
    "ScheduleComponent": ScheduleComponent,
    "NPCInfoComponent": NPCInfoComponent,
}
