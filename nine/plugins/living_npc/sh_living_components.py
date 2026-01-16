"""
ECS компоненты для Living World NPC.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class PersonalityTrait(Enum):
    """Личностные черты NPC."""
    # Положительные
    BRAVE = "brave"
    KIND = "kind"
    HONEST = "honest"
    LOYAL = "loyal"
    WISE = "wise"
    PATIENT = "patient"
    GENEROUS = "generous"
    HUMBLE = "humble"

    # Отрицательные
    COWARDLY = "cowardly"
    CRUEL = "cruel"
    DECEITFUL = "deceitful"
    TREACHEROUS = "treacherous"
    FOOLISH = "foolish"
    IMPATIENT = "impatient"
    GREEDY = "greedy"
    ARROGANT = "arrogant"

    # Нейтральные
    CURIOUS = "curious"
    CAUTIOUS = "cautious"
    AMBITIOUS = "ambitious"
    PRAGMATIC = "pragmatic"


class Activity(Enum):
    """Активности NPC."""
    IDLE = "idle"
    SLEEPING = "sleeping"
    EATING = "eating"
    WORKING = "working"
    PATROLLING = "patrolling"
    SOCIALIZING = "socializing"
    TRADING = "trading"
    PRAYING = "praying"
    TRAINING = "training"
    CRAFTING = "crafting"
    WANDERING = "wandering"


class MemoryType(Enum):
    """Типы воспоминаний."""
    PLAYER_HELPED = "player_helped"
    PLAYER_ATTACKED = "player_attacked"
    PLAYER_GAVE_ITEM = "player_gave_item"
    PLAYER_INSULTED = "player_insulted"
    PLAYER_COMPLIMENTED = "player_complimented"
    WITNESSED_CRIME = "witnessed_crime"
    WITNESSED_HEROIC_ACT = "witnessed_heroic_act"
    RECEIVED_GIFT = "received_gift"
    WAS_ROBBED = "was_robbed"
    CONVERSATION = "conversation"


@dataclass
class NeedsComponent:
    """
    Компонент потребностей NPC.
    Значения от 0 (критически низко) до 100 (полностью удовлетворено).
    """
    hunger: float = 100.0      # Сытость (падает со временем)
    energy: float = 100.0      # Энергия (падает при активности)
    social: float = 50.0       # Социальность (падает в одиночестве)
    safety: float = 80.0       # Чувство безопасности
    comfort: float = 70.0      # Комфорт

    # Скорости изменения (за игровой час)
    hunger_decay: float = 2.0
    energy_decay: float = 1.5
    social_decay: float = 0.5

    def update(self, delta_hours: float, is_active: bool = True):
        """Обновляет потребности за прошедшее время."""
        # Голод падает всегда
        self.hunger = max(0, self.hunger - self.hunger_decay * delta_hours)

        # Энергия падает при активности, восстанавливается во сне
        if is_active:
            self.energy = max(0, self.energy - self.energy_decay * delta_hours)

        # Социальность медленно падает
        self.social = max(0, self.social - self.social_decay * delta_hours)

    def eat(self, amount: float = 30.0):
        """NPC поел."""
        self.hunger = min(100, self.hunger + amount)

    def sleep(self, hours: float):
        """NPC поспал."""
        self.energy = min(100, self.energy + hours * 12.5)

    def socialize(self, quality: float = 1.0):
        """NPC пообщался."""
        self.social = min(100, self.social + 10 * quality)

    @property
    def most_urgent_need(self) -> str:
        """Возвращает самую срочную потребность."""
        needs = {
            "hunger": self.hunger,
            "energy": self.energy,
            "social": self.social,
            "safety": self.safety,
        }
        return min(needs, key=needs.get)

    @property
    def is_critical(self) -> bool:
        """Есть ли критически низкая потребность."""
        return min(self.hunger, self.energy, self.safety) < 20


@dataclass
class PersonalityComponent:
    """Компонент личности NPC."""
    traits: List[str] = field(default_factory=list)  # PersonalityTrait values

    # Числовые характеристики (0.0 - 1.0)
    chattiness: float = 0.5       # Насколько разговорчив
    aggression: float = 0.3       # Склонность к агрессии
    curiosity: float = 0.5        # Любопытство
    greed: float = 0.3            # Жадность
    kindness: float = 0.5         # Доброта
    courage: float = 0.5          # Храбрость

    def has_trait(self, trait: str) -> bool:
        """Проверяет наличие черты."""
        return trait.lower() in [t.lower() for t in self.traits]

    def get_reaction_modifier(self, event_type: str) -> float:
        """Возвращает модификатор реакции на событие."""
        modifiers = {
            "threat": self.courage - 0.5,  # Храбрые не боятся
            "gift": self.kindness,  # Добрые ценят подарки больше
            "insult": -self.aggression,  # Агрессивные реагируют хуже
            "trade": self.greed - 0.5,  # Жадные торгуются жёстче
        }
        return modifiers.get(event_type, 0.0)


@dataclass
class RelationshipData:
    """Данные об отношении к сущности."""
    entity_id: str
    disposition: float = 50.0  # -100 (враг) до 100 (друг)
    trust: float = 50.0        # 0 (не доверяет) до 100 (полное доверие)
    familiarity: float = 0.0   # 0 (незнакомец) до 100 (хорошо знает)
    last_interaction: Optional[str] = None  # ISO timestamp

    @property
    def relationship_level(self) -> str:
        """Возвращает уровень отношений."""
        if self.disposition >= 80:
            return "friend"
        elif self.disposition >= 60:
            return "friendly"
        elif self.disposition >= 40:
            return "neutral"
        elif self.disposition >= 20:
            return "unfriendly"
        else:
            return "hostile"


@dataclass
class RelationshipsComponent:
    """Компонент отношений NPC."""
    # entity_id -> RelationshipData
    relationships: Dict[str, RelationshipData] = field(default_factory=dict)

    # Базовое отношение к незнакомцам
    default_disposition: float = 50.0
    default_trust: float = 30.0

    def get_relationship(self, entity_id: str) -> RelationshipData:
        """Получает или создаёт данные об отношении."""
        if entity_id not in self.relationships:
            self.relationships[entity_id] = RelationshipData(
                entity_id=entity_id,
                disposition=self.default_disposition,
                trust=self.default_trust,
            )
        return self.relationships[entity_id]

    def modify_disposition(self, entity_id: str, amount: float):
        """Изменяет отношение к сущности."""
        rel = self.get_relationship(entity_id)
        rel.disposition = max(-100, min(100, rel.disposition + amount))
        rel.familiarity = min(100, rel.familiarity + abs(amount) * 0.1)

    def modify_trust(self, entity_id: str, amount: float):
        """Изменяет доверие к сущности."""
        rel = self.get_relationship(entity_id)
        rel.trust = max(0, min(100, rel.trust + amount))

    def get_disposition(self, entity_id: str) -> float:
        """Возвращает отношение к сущности."""
        return self.get_relationship(entity_id).disposition

    def is_hostile_to(self, entity_id: str) -> bool:
        """Проверяет, враждебен ли NPC к сущности."""
        return self.get_disposition(entity_id) < 20


@dataclass
class Memory:
    """Единичное воспоминание."""
    memory_type: str  # MemoryType value
    entity_id: str    # Кто участвовал
    details: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5  # 0-1, влияет на забывание
    timestamp: str = ""      # ISO timestamp
    location: Optional[List[float]] = None  # Где произошло


@dataclass
class MemoryComponent:
    """Компонент памяти NPC."""
    memories: List[Memory] = field(default_factory=list)
    max_memories: int = 50  # Максимальное количество воспоминаний

    # Порог важности для забывания
    forget_threshold: float = 0.2

    def add_memory(self, memory: Memory):
        """Добавляет воспоминание."""
        self.memories.append(memory)

        # Если превышен лимит - забываем наименее важные
        if len(self.memories) > self.max_memories:
            self._forget_least_important()

    def _forget_least_important(self):
        """Удаляет наименее важные воспоминания."""
        # Сортируем по важности
        self.memories.sort(key=lambda m: m.importance, reverse=True)
        # Оставляем только max_memories
        self.memories = self.memories[:self.max_memories]

    def get_memories_about(self, entity_id: str) -> List[Memory]:
        """Возвращает воспоминания о сущности."""
        return [m for m in self.memories if m.entity_id == entity_id]

    def get_memories_of_type(self, memory_type: str) -> List[Memory]:
        """Возвращает воспоминания определённого типа."""
        return [m for m in self.memories if m.memory_type == memory_type]

    def has_memory_of(self, entity_id: str, memory_type: str) -> bool:
        """Проверяет, есть ли воспоминание."""
        for m in self.memories:
            if m.entity_id == entity_id and m.memory_type == memory_type:
                return True
        return False

    def decay_memories(self, amount: float = 0.01):
        """Уменьшает важность воспоминаний (забывание со временем)."""
        for memory in self.memories:
            memory.importance = max(0, memory.importance - amount)

        # Удаляем полностью забытые
        self.memories = [m for m in self.memories if m.importance > self.forget_threshold]


@dataclass
class ScheduleEntry:
    """Запись в расписании."""
    hour_start: int     # Час начала (0-23)
    hour_end: int       # Час окончания (0-23)
    activity: str       # Activity value
    location: Optional[List[float]] = None  # Куда идти
    location_id: Optional[str] = None  # ID локации (альтернатива координатам)
    priority: int = 1   # Приоритет (выше = важнее)


@dataclass
class ScheduleComponent:
    """Компонент расписания NPC."""
    entries: List[ScheduleEntry] = field(default_factory=list)
    current_activity: str = "idle"
    deviation_chance: float = 0.1  # Шанс отклониться от расписания

    def get_activity_for_hour(self, hour: int) -> Optional[ScheduleEntry]:
        """Возвращает запланированную активность для часа."""
        best_entry = None
        best_priority = -1

        for entry in self.entries:
            # Проверяем, попадает ли час в диапазон
            if entry.hour_start <= entry.hour_end:
                # Обычный диапазон (например, 9-17)
                in_range = entry.hour_start <= hour < entry.hour_end
            else:
                # Диапазон через полночь (например, 22-6)
                in_range = hour >= entry.hour_start or hour < entry.hour_end

            if in_range and entry.priority > best_priority:
                best_entry = entry
                best_priority = entry.priority

        return best_entry

    def add_entry(self, entry: ScheduleEntry):
        """Добавляет запись в расписание."""
        self.entries.append(entry)
        # Сортируем по времени начала
        self.entries.sort(key=lambda e: e.hour_start)
