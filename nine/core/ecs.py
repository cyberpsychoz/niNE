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
from typing import Dict, List, Type, TypeVar, Optional, Set, Iterator, Any
import logging

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

            logger.debug(f"Entity {entity.id[:8]}... added to ECS world")

        self._pending_addition.clear()

    def _process_pending_removals(self) -> None:
        """Обрабатывает очередь на удаление."""
        for entity_id in self._pending_removal:
            entity = self._entities.pop(entity_id, None)
            if entity:
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
