"""
Dataclasses для системы квестов.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class QuestStatus(Enum):
    """Статус квеста."""
    AVAILABLE = "available"  # Доступен для принятия
    ACTIVE = "active"  # В процессе выполнения
    COMPLETED = "completed"  # Выполнен, но награда не получена
    TURNED_IN = "turned_in"  # Сдан, награда получена
    FAILED = "failed"  # Провален


class ObjectiveType(Enum):
    """Типы целей квеста."""
    KILL = "kill"  # Убить N существ определённого типа
    COLLECT = "collect"  # Собрать N предметов
    TALK = "talk"  # Поговорить с NPC
    REACH_LOCATION = "reach_location"  # Достичь точки
    INTERACT = "interact"  # Взаимодействовать с объектом
    ESCORT = "escort"  # Сопроводить NPC
    DEFEND = "defend"  # Защитить точку/NPC
    CUSTOM = "custom"  # Кастомная цель (проверяется через события)


@dataclass
class QuestObjective:
    """Цель квеста."""
    id: str
    type: str  # ObjectiveType value
    description: str
    description_ru: str

    # Параметры в зависимости от типа
    target_id: str = ""  # ID цели (monster_type, item_id, npc_id, location_id)
    target_count: int = 1  # Требуемое количество

    # Опциональные параметры
    location: Optional[List[float]] = None  # [x, y, z] для reach_location
    radius: float = 5.0  # Радиус для reach_location
    hidden: bool = False  # Скрытая цель (не показывается до выполнения)
    optional: bool = False  # Опциональная цель

    # Прогресс (заполняется при загрузке состояния игрока)
    current_count: int = 0

    @property
    def is_complete(self) -> bool:
        return self.current_count >= self.target_count

    @property
    def progress_text(self) -> str:
        if self.type == "talk" or self.type == "reach_location":
            return "Complete" if self.is_complete else "Incomplete"
        return f"{self.current_count}/{self.target_count}"


@dataclass
class QuestReward:
    """Награда за квест."""
    experience: int = 0
    gold: int = 0
    items: List[Dict[str, Any]] = field(default_factory=list)  # [{"id": "item_id", "count": 1}]
    reputation: Dict[str, int] = field(default_factory=dict)  # {"faction_id": amount}


@dataclass
class Quest:
    """Определение квеста."""
    id: str
    name: str
    name_ru: str
    description: str
    description_ru: str

    # Мета
    level_requirement: int = 1
    repeatable: bool = False
    chain_id: Optional[str] = None  # ID цепочки квестов
    chain_order: int = 0  # Порядок в цепочке

    # NPC
    giver_npc_id: str = ""  # NPC, который даёт квест
    turn_in_npc_id: str = ""  # NPC, которому сдаётся квест (если пусто - тому же)

    # Цели
    objectives: List[QuestObjective] = field(default_factory=list)

    # Награды
    rewards: QuestReward = field(default_factory=QuestReward)

    # Требования
    prerequisites: List[str] = field(default_factory=list)  # Список ID квестов-пререквизитов
    required_class: Optional[str] = None  # Только для определённого класса
    required_faction: Optional[str] = None  # Только для определённой фракции

    # Диалоги
    dialog_accept: str = ""  # Текст при принятии
    dialog_progress: str = ""  # Текст при незавершённом квесте
    dialog_complete: str = ""  # Текст при завершении

    def get_objective(self, objective_id: str) -> Optional[QuestObjective]:
        """Возвращает цель по ID."""
        for obj in self.objectives:
            if obj.id == objective_id:
                return obj
        return None

    @property
    def all_objectives_complete(self) -> bool:
        """Проверяет, выполнены ли все обязательные цели."""
        for obj in self.objectives:
            if not obj.optional and not obj.is_complete:
                return False
        return True


@dataclass
class PlayerQuestState:
    """Состояние квеста у игрока."""
    quest_id: str
    status: str  # QuestStatus value
    objectives_progress: Dict[str, int] = field(default_factory=dict)  # objective_id -> count
    accepted_at: Optional[str] = None  # ISO timestamp
    completed_at: Optional[str] = None  # ISO timestamp

    def get_progress(self, objective_id: str) -> int:
        """Возвращает прогресс цели."""
        return self.objectives_progress.get(objective_id, 0)

    def set_progress(self, objective_id: str, count: int):
        """Устанавливает прогресс цели."""
        self.objectives_progress[objective_id] = count

    def increment_progress(self, objective_id: str, amount: int = 1) -> int:
        """Увеличивает прогресс цели. Возвращает новое значение."""
        current = self.objectives_progress.get(objective_id, 0)
        new_value = current + amount
        self.objectives_progress[objective_id] = new_value
        return new_value
