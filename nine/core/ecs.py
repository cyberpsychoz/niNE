"""
Entity-Component-System (ECS) фреймворк для niNE.

Предоставляет базовую архитектуру для создания игровых сущностей
с компонентным подходом. Используется для NPC, предметов и других
игровых объектов.

Пример использования:
    # Создание менеджера
    world = ECSWorld()

    # Регистрация систем
    world.add_system(AISystem())
    world.add_system(PathfindingSystem())

    # Создание сущности
    npc = world.create_entity()
    npc.add_component(PositionComponent(x=10, y=5, z=1))
    npc.add_component(AIComponent(behavior="patrol"))

    # Обновление всех систем
    world.update(dt)
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Type, TypeVar, Optional, Set, Iterator, Any, Callable
import logging
import threading

logger = logging.getLogger(__name__)


# =============================================================================
# Базовые классы
# =============================================================================

@dataclass
class Component:
    """
    Базовый класс для всех компонентов.

    Компонент — это чистые данные без логики.
    Наследуйте от этого класса для создания новых типов компонентов.

    Пример:
        @dataclass
        class PositionComponent(Component):
            x: float = 0.0
            y: float = 0.0
            z: float = 0.0
    """
    pass


# TypeVar для типизации компонентов
C = TypeVar('C', bound=Component)


class Entity:
    """
    Сущность — контейнер для компонентов.

    Entity сам по себе не содержит логики, только идентификатор
    и набор компонентов. Вся логика обрабатывается системами.
    """

    def __init__(self, entity_id: Optional[str] = None):
        self.id: str = entity_id or str(uuid.uuid4())
        self._components: Dict[Type[Component], Component] = {}
        self._world: Optional[ECSWorld] = None
        self.tags: Set[str] = set()
        self.active: bool = True

    def add_component(self, component: Component) -> 'Entity':
        """
        Добавляет компонент к сущности.

        Args:
            component: Экземпляр компонента

        Returns:
            Self для цепочки вызовов
        """
        component_type = type(component)
        self._components[component_type] = component

        # Уведомляем мир об изменении компонентов
        if self._world:
            self._world._on_component_added(self, component_type)

        return self

    def remove_component(self, component_type: Type[C]) -> Optional[C]:
        """
        Удаляет компонент из сущности.

        Args:
            component_type: Тип компонента для удаления

        Returns:
            Удалённый компонент или None
        """
        component = self._components.pop(component_type, None)

        if component and self._world:
            self._world._on_component_removed(self, component_type)

        return component

    def get_component(self, component_type: Type[C]) -> Optional[C]:
        """
        Получает компонент по типу.

        Args:
            component_type: Тип компонента

        Returns:
            Компонент или None если не найден
        """
        return self._components.get(component_type)

    def has_component(self, component_type: Type[Component]) -> bool:
        """Проверяет наличие компонента."""
        return component_type in self._components

    def has_components(self, *component_types: Type[Component]) -> bool:
        """Проверяет наличие всех указанных компонентов."""
        return all(ct in self._components for ct in component_types)

    def get_components(self) -> Dict[Type[Component], Component]:
        """Возвращает все компоненты сущности."""
        return self._components.copy()

    def add_tag(self, tag: str) -> 'Entity':
        """Добавляет тег к сущности."""
        self.tags.add(tag)
        return self

    def remove_tag(self, tag: str) -> 'Entity':
        """Удаляет тег из сущности."""
        self.tags.discard(tag)
        return self

    def has_tag(self, tag: str) -> bool:
        """Проверяет наличие тега."""
        return tag in self.tags

    def __repr__(self) -> str:
        components = ", ".join(c.__class__.__name__ for c in self._components.values())
        return f"Entity(id={self.id[:8]}..., components=[{components}])"


class System(ABC):
    """
    Базовый класс для систем.

    Система содержит логику обработки сущностей с определёнными компонентами.
    Каждая система определяет, какие компоненты ей нужны через required_components.

    Пример:
        class MovementSystem(System):
            required_components = [PositionComponent, VelocityComponent]

            def update(self, dt: float, entities: List[Entity]):
                for entity in entities:
                    pos = entity.get_component(PositionComponent)
                    vel = entity.get_component(VelocityComponent)
                    pos.x += vel.x * dt
                    pos.y += vel.y * dt
    """

    # Компоненты, необходимые для работы системы
    required_components: List[Type[Component]] = []

    # Приоритет выполнения (меньше = раньше)
    priority: int = 0

    # Включена ли система
    enabled: bool = True

    def __init__(self):
        self._world: Optional[ECSWorld] = None

    @abstractmethod
    def update(self, dt: float, entities: List[Entity]) -> None:
        """
        Обновляет все подходящие сущности.

        Args:
            dt: Время с прошлого обновления (секунды)
            entities: Список сущностей с нужными компонентами
        """
        pass

    def on_entity_added(self, entity: Entity) -> None:
        """Вызывается когда сущность добавляется в систему."""
        pass

    def on_entity_removed(self, entity: Entity) -> None:
        """Вызывается когда сущность удаляется из системы."""
        pass

    def on_system_added(self, world: 'ECSWorld') -> None:
        """Вызывается при добавлении системы в мир."""
        pass

    def on_system_removed(self) -> None:
        """Вызывается при удалении системы из мира."""
        pass


# =============================================================================
# ECS World — менеджер сущностей и систем
# =============================================================================

class ECSWorld:
    """
    Мир ECS — управляет сущностями и системами.

    Основной класс для работы с ECS архитектурой.
    Отвечает за создание/удаление сущностей и выполнение систем.
    """

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._systems: List[System] = []
        self._entities_by_tag: Dict[str, Set[str]] = {}

        # Кэш сущностей по компонентам для быстрого поиска
        self._component_cache: Dict[Type[Component], Set[str]] = {}

        # Очередь на удаление (удаляем в конце update)
        self._pending_removal: Set[str] = set()

        # Очередь на добавление
        self._pending_addition: List[Entity] = []

    # =========================================================================
    # Управление сущностями
    # =========================================================================

    def create_entity(self, entity_id: Optional[str] = None) -> Entity:
        """
        Создаёт новую сущность.

        Args:
            entity_id: Опциональный ID (генерируется если не указан)

        Returns:
            Новая сущность
        """
        entity = Entity(entity_id)
        entity._world = self
        self._pending_addition.append(entity)
        return entity

    def add_entity(self, entity: Entity) -> Entity:
        """
        Добавляет существующую сущность в мир.

        Args:
            entity: Сущность для добавления

        Returns:
            Добавленная сущность
        """
        entity._world = self
        self._pending_addition.append(entity)
        return entity

    def remove_entity(self, entity_id: str) -> None:
        """
        Помечает сущность на удаление (удалится в конце update).

        Args:
            entity_id: ID сущности для удаления
        """
        self._pending_removal.add(entity_id)

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """
        Получает сущность по ID.

        Args:
            entity_id: ID сущности

        Returns:
            Сущность или None
        """
        return self._entities.get(entity_id)

    def get_entities_with_components(self, *component_types: Type[Component]) -> Iterator[Entity]:
        """
        Возвращает все сущности с указанными компонентами.

        Args:
            component_types: Типы компонентов

        Yields:
            Сущности с этими компонентами
        """
        if not component_types:
            return

        # Находим пересечение сущностей с каждым компонентом
        first_type = component_types[0]
        entity_ids = self._component_cache.get(first_type, set()).copy()

        for comp_type in component_types[1:]:
            entity_ids &= self._component_cache.get(comp_type, set())

        for entity_id in entity_ids:
            entity = self._entities.get(entity_id)
            if entity and entity.active and entity_id not in self._pending_removal:
                yield entity

    def query(self, *component_types: Type[Component]) -> Iterator[Entity]:
        """
        Alias for get_entities_with_components.
        Provides a shorter, more convenient API for querying entities.

        Args:
            component_types: Types of components to query

        Yields:
            Entities with all specified components

        Example:
            for entity in world.query(PawnComponent, TransformComponent):
                pawn = entity.get_component(PawnComponent)
                transform = entity.get_component(TransformComponent)
        """
        return self.get_entities_with_components(*component_types)

    def get_entities_with_tag(self, tag: str) -> Iterator[Entity]:
        """
        Возвращает все сущности с указанным тегом.

        Args:
            tag: Тег для поиска

        Yields:
            Сущности с этим тегом
        """
        entity_ids = self._entities_by_tag.get(tag, set())
        for entity_id in entity_ids:
            entity = self._entities.get(entity_id)
            if entity and entity.active and entity_id not in self._pending_removal:
                yield entity

    def get_all_entities(self) -> Iterator[Entity]:
        """Возвращает все активные сущности."""
        for entity_id, entity in self._entities.items():
            if entity.active and entity_id not in self._pending_removal:
                yield entity

    def entity_count(self) -> int:
        """Возвращает количество сущностей."""
        return len(self._entities)

    # =========================================================================
    # Управление системами
    # =========================================================================

    def add_system(self, system: System) -> None:
        """
        Добавляет систему в мир.

        Args:
            system: Система для добавления
        """
        system._world = self
        self._systems.append(system)
        self._systems.sort(key=lambda s: s.priority)
        system.on_system_added(self)
        logger.debug(f"System {system.__class__.__name__} added to ECS world")

    def remove_system(self, system_type: Type[System]) -> Optional[System]:
        """
        Удаляет систему из мира.

        Args:
            system_type: Тип системы для удаления

        Returns:
            Удалённая система или None
        """
        for i, system in enumerate(self._systems):
            if isinstance(system, system_type):
                removed = self._systems.pop(i)
                removed.on_system_removed()
                removed._world = None
                return removed
        return None

    def get_system(self, system_type: Type[System]) -> Optional[System]:
        """
        Получает систему по типу.

        Args:
            system_type: Тип системы

        Returns:
            Система или None
        """
        for system in self._systems:
            if isinstance(system, system_type):
                return system
        return None

    # =========================================================================
    # Обновление мира
    # =========================================================================

    def update(self, dt: float) -> None:
        """
        Обновляет все системы.

        Args:
            dt: Время с прошлого обновления (секунды)
        """
        # Добавляем ожидающие сущности
        self._process_pending_additions()

        # Обновляем системы
        for system in self._systems:
            if not system.enabled:
                continue

            # Получаем сущности для системы
            if system.required_components:
                entities = list(self.get_entities_with_components(*system.required_components))
            else:
                entities = list(self.get_all_entities())

            if entities:
                system.update(dt, entities)

        # Удаляем помеченные сущности
        self._process_pending_removals()

    def _process_pending_additions(self) -> None:
        """Обрабатывает очередь на добавление."""
        for entity in self._pending_addition:
            self._entities[entity.id] = entity

            # Обновляем кэш компонентов
            for comp_type in entity._components:
                if comp_type not in self._component_cache:
                    self._component_cache[comp_type] = set()
                self._component_cache[comp_type].add(entity.id)

            # Обновляем индекс тегов
            for tag in entity.tags:
                if tag not in self._entities_by_tag:
                    self._entities_by_tag[tag] = set()
                self._entities_by_tag[tag].add(entity.id)

            # Notify systems about new entity
            for system in self._systems:
                if system.enabled and system.required_components:
                    if entity.has_components(*system.required_components):
                        system.on_entity_added(entity)

            logger.debug(f"Entity {entity.id[:8]}... added to ECS world")

        self._pending_addition.clear()

    def _process_pending_removals(self) -> None:
        """Обрабатывает очередь на удаление."""
        for entity_id in self._pending_removal:
            entity = self._entities.pop(entity_id, None)
            if entity:
                # Notify systems about entity removal
                for system in self._systems:
                    if system.enabled and system.required_components:
                        if entity.has_components(*system.required_components):
                            system.on_entity_removed(entity)

                # Очищаем кэш компонентов
                for comp_type in entity._components:
                    if comp_type in self._component_cache:
                        self._component_cache[comp_type].discard(entity_id)

                # Очищаем индекс тегов
                for tag in entity.tags:
                    if tag in self._entities_by_tag:
                        self._entities_by_tag[tag].discard(entity_id)

                entity._world = None
                logger.debug(f"Entity {entity_id[:8]}... removed from ECS world")

        self._pending_removal.clear()

    def flush(self) -> None:
        """Process pending additions immediately. Safe to call multiple times."""
        self._process_pending_additions()

    def _on_component_added(self, entity: Entity, component_type: Type[Component]) -> None:
        """Вызывается при добавлении компонента к сущности."""
        if entity.id in self._entities:
            if component_type not in self._component_cache:
                self._component_cache[component_type] = set()
            self._component_cache[component_type].add(entity.id)

    def _on_component_removed(self, entity: Entity, component_type: Type[Component]) -> None:
        """Вызывается при удалении компонента из сущности."""
        if component_type in self._component_cache:
            self._component_cache[component_type].discard(entity.id)

    def clear(self) -> None:
        """Очищает мир от всех сущностей."""
        for entity in self._entities.values():
            entity._world = None

        self._entities.clear()
        self._component_cache.clear()
        self._entities_by_tag.clear()
        self._pending_removal.clear()
        self._pending_addition.clear()

        logger.info("ECS world cleared")


# =============================================================================
# Entity Pool - Object reuse for reduced GC pressure
# =============================================================================

class EntityPool:
    """
    Object pool for Entity instances.

    Reduces garbage collection pressure by reusing Entity objects
    instead of creating/destroying them. Essential for scaling to
    300+ NPCs with frequent spawn/despawn.

    Thread Safety:
        This pool is thread-safe for acquire/release operations.

    Usage:
        pool = EntityPool(initial_size=50)

        # Acquire entity from pool
        entity = pool.acquire("npc_123")
        entity.add_component(PositionComponent(x=10, y=5))

        # Return to pool when done
        pool.release(entity)  # Components are cleared automatically
    """

    def __init__(
        self,
        initial_size: int = 50,
        max_size: int = 500,
        auto_grow: bool = True
    ):
        """
        Initialize entity pool.

        Args:
            initial_size: Number of entities to pre-allocate
            max_size: Maximum pool size (prevents unbounded growth)
            auto_grow: If True, create new entities when pool is empty
        """
        self._pool: List[Entity] = []
        self._active: Dict[str, Entity] = {}  # entity_id -> Entity
        self._max_size = max_size
        self._auto_grow = auto_grow
        self._lock = threading.Lock()

        # Statistics
        self._stats = {
            "acquires": 0,
            "releases": 0,
            "creates": 0,
            "reuses": 0,
            "peak_active": 0,
        }

        # Pre-allocate entities
        for _ in range(initial_size):
            self._pool.append(Entity())
            self._stats["creates"] += 1

        logger.debug(f"EntityPool initialized with {initial_size} entities")

    def acquire(self, entity_id: Optional[str] = None) -> Entity:
        """
        Get an entity from the pool.

        If the pool is empty and auto_grow is True, creates a new entity.
        If auto_grow is False and pool is empty, raises RuntimeError.

        Args:
            entity_id: Optional ID for the entity. If None, generates UUID.

        Returns:
            A clean Entity ready for use

        Raises:
            RuntimeError: If pool is empty and auto_grow is False
        """
        with self._lock:
            self._stats["acquires"] += 1

            # Try to get from pool
            if self._pool:
                entity = self._pool.pop()
                self._stats["reuses"] += 1
            elif self._auto_grow:
                entity = Entity()
                self._stats["creates"] += 1
            else:
                raise RuntimeError("Entity pool exhausted")

            # Reset entity with new ID
            entity.id = entity_id or str(uuid.uuid4())
            entity._components.clear()
            entity.tags.clear()
            entity.active = True
            entity._world = None

            # Track active entity
            self._active[entity.id] = entity

            # Update peak
            if len(self._active) > self._stats["peak_active"]:
                self._stats["peak_active"] = len(self._active)

            return entity

    def release(self, entity: Entity) -> bool:
        """
        Return an entity to the pool.

        The entity's components and tags are cleared automatically.
        If the pool is at max capacity, the entity is discarded.

        Args:
            entity: The entity to release

        Returns:
            True if returned to pool, False if discarded
        """
        with self._lock:
            self._stats["releases"] += 1

            # Remove from active tracking
            self._active.pop(entity.id, None)

            # Clear entity state
            self._clear_entity(entity)

            # Return to pool if under capacity
            if len(self._pool) < self._max_size:
                self._pool.append(entity)
                return True
            else:
                # Pool is full, let GC handle it
                return False

    def release_by_id(self, entity_id: str) -> bool:
        """
        Release entity by ID.

        Args:
            entity_id: ID of entity to release

        Returns:
            True if found and released, False otherwise
        """
        with self._lock:
            entity = self._active.get(entity_id)
            if entity:
                # Use internal release (already holding lock)
                self._stats["releases"] += 1
                self._active.pop(entity_id, None)
                self._clear_entity(entity)
                if len(self._pool) < self._max_size:
                    self._pool.append(entity)
                return True
            return False

    def _clear_entity(self, entity: Entity) -> None:
        """Reset entity to clean state for reuse."""
        entity._components.clear()
        entity.tags.clear()
        entity.active = False
        entity._world = None

    def get_active(self, entity_id: str) -> Optional[Entity]:
        """
        Get an active entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity if active, None otherwise
        """
        return self._active.get(entity_id)

    def is_active(self, entity_id: str) -> bool:
        """Check if entity is currently active (acquired from pool)."""
        return entity_id in self._active

    def prewarm(self, count: int) -> int:
        """
        Pre-allocate additional entities.

        Useful before expected high activity (e.g., dungeon start).

        Args:
            count: Number of entities to pre-allocate

        Returns:
            Number of entities actually created
        """
        created = 0
        with self._lock:
            space = self._max_size - len(self._pool) - len(self._active)
            to_create = min(count, space)

            for _ in range(to_create):
                self._pool.append(Entity())
                self._stats["creates"] += 1
                created += 1

        if created > 0:
            logger.debug(f"EntityPool prewarmed with {created} entities")

        return created

    def shrink(self, target_size: Optional[int] = None) -> int:
        """
        Shrink pool to target size, releasing excess entities.

        Args:
            target_size: Target pool size. If None, uses initial_size.

        Returns:
            Number of entities removed
        """
        if target_size is None:
            target_size = 50

        removed = 0
        with self._lock:
            while len(self._pool) > target_size:
                self._pool.pop()
                removed += 1

        if removed > 0:
            logger.debug(f"EntityPool shrunk by {removed} entities")

        return removed

    def clear(self) -> None:
        """Clear all entities (active and pooled)."""
        with self._lock:
            for entity in self._active.values():
                self._clear_entity(entity)
            self._active.clear()
            self._pool.clear()

        logger.debug("EntityPool cleared")

    # =========================================================================
    # Statistics
    # =========================================================================

    @property
    def pool_size(self) -> int:
        """Number of entities available in pool."""
        return len(self._pool)

    @property
    def active_count(self) -> int:
        """Number of entities currently in use."""
        return len(self._active)

    @property
    def total_count(self) -> int:
        """Total entities (pooled + active)."""
        return len(self._pool) + len(self._active)

    def get_stats(self) -> Dict:
        """
        Get pool statistics.

        Returns:
            Dict with stats (acquires, releases, reuse rate, etc.)
        """
        with self._lock:
            total_acquires = self._stats["acquires"]
            reuses = self._stats["reuses"]

            return {
                **self._stats,
                "pool_size": len(self._pool),
                "active_count": len(self._active),
                "max_size": self._max_size,
                "reuse_rate": reuses / total_acquires if total_acquires > 0 else 0.0,
            }

    def reset_stats(self) -> None:
        """Reset statistics counters (keeps pool state)."""
        with self._lock:
            self._stats = {
                "acquires": 0,
                "releases": 0,
                "creates": 0,
                "reuses": 0,
                "peak_active": len(self._active),
            }


class PooledECSWorld(ECSWorld):
    """
    ECSWorld that uses EntityPool for entity management.

    Drop-in replacement for ECSWorld with automatic entity pooling.
    """

    def __init__(self, pool: Optional[EntityPool] = None):
        """
        Initialize pooled ECS world.

        Args:
            pool: Optional EntityPool to use. If None, creates default pool.
        """
        super().__init__()
        self._pool = pool or EntityPool(initial_size=100, max_size=500)

    def create_entity(self, entity_id: Optional[str] = None) -> Entity:
        """
        Create an entity from the pool.

        Args:
            entity_id: Optional ID (generates UUID if not provided)

        Returns:
            New entity from pool
        """
        entity = self._pool.acquire(entity_id)
        entity._world = self
        self._pending_addition.append(entity)
        return entity

    def _process_pending_removals(self) -> None:
        """Process removals and return entities to pool."""
        for entity_id in self._pending_removal:
            entity = self._entities.pop(entity_id, None)
            if entity:
                # Notify systems
                for system in self._systems:
                    if system.enabled and system.required_components:
                        if entity.has_components(*system.required_components):
                            system.on_entity_removed(entity)

                # Clear caches
                for comp_type in list(entity._components.keys()):
                    if comp_type in self._component_cache:
                        self._component_cache[comp_type].discard(entity_id)

                for tag in list(entity.tags):
                    if tag in self._entities_by_tag:
                        self._entities_by_tag[tag].discard(entity_id)

                # Return to pool
                self._pool.release(entity)

                logger.debug(f"Entity {entity_id[:8]}... returned to pool")

        self._pending_removal.clear()

    def clear(self) -> None:
        """Clear world and return all entities to pool."""
        for entity_id in list(self._entities.keys()):
            entity = self._entities[entity_id]
            self._pool.release(entity)

        self._entities.clear()
        self._component_cache.clear()
        self._entities_by_tag.clear()
        self._pending_removal.clear()
        self._pending_addition.clear()

        logger.info("PooledECSWorld cleared")

    def get_pool_stats(self) -> Dict:
        """Get entity pool statistics."""
        return self._pool.get_stats()


# =============================================================================
# Вспомогательные функции
# =============================================================================

def create_entity_from_template(
    world: ECSWorld,
    template: Dict[str, Any],
    component_registry: Dict[str, Type[Component]]
) -> Entity:
    """
    Создаёт сущность из шаблона (например, из JSON).

    Args:
        world: ECS мир
        template: Шаблон сущности {"components": {"PositionComponent": {"x": 10}}, "tags": ["npc"]}
        component_registry: Реестр компонентов {"PositionComponent": PositionComponent}

    Returns:
        Созданная сущность
    """
    entity = world.create_entity(template.get("id"))

    # Добавляем компоненты
    for comp_name, comp_data in template.get("components", {}).items():
        if comp_name in component_registry:
            comp_class = component_registry[comp_name]
            component = comp_class(**comp_data)
            entity.add_component(component)
        else:
            logger.warning(f"Unknown component type: {comp_name}")

    # Добавляем теги
    for tag in template.get("tags", []):
        entity.add_tag(tag)

    return entity
