"""
Entity Component System (ECS) базовые классы.

Вдохновлено Helix Garry's Mod framework.
Позволяет создавать модульные игровые сущности с компонентами.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, TYPE_CHECKING
from abc import ABC, abstractmethod
import uuid as uuid_lib

if TYPE_CHECKING:
    from panda3d.core import NodePath


# =============================================================================
# КОМПОНЕНТЫ
# =============================================================================

class Component(ABC):
    """
    Базовый класс компонента.
    Компоненты добавляют функциональность к Entity.
    """

    def __init__(self):
        self.entity: Optional['Entity'] = None

    def on_attach(self, entity: 'Entity'):
        """Вызывается при присоединении к entity."""
        self.entity = entity

    def on_detach(self):
        """Вызывается при отсоединении от entity."""
        self.entity = None

    def on_spawn(self):
        """Вызывается когда entity появляется в мире."""
        pass

    def on_remove(self):
        """Вызывается когда entity удаляется из мира."""
        pass

    def update(self, dt: float):
        """Вызывается каждый тик (если нужно)."""
        pass


# =============================================================================
# ENTITY
# =============================================================================

@dataclass
class EntityData:
    """Сериализуемые данные entity."""
    entity_class: str = ""          # Класс entity (например "health_potion")
    unique_id: str = ""             # UUID конкретного экземпляра
    data: Dict[str, Any] = field(default_factory=dict)


class Entity(ABC):
    """
    Базовый класс для всех игровых сущностей.

    Наследники должны определить:
    - CLASS_ID: уникальный идентификатор класса
    - NAME: отображаемое имя
    - DESCRIPTION: описание

    Опционально:
    - MODEL: путь к модели (по умолчанию жёлтый куб)
    - ICON: путь к иконке
    - MAX_STACK: максимальный размер стека
    - CATEGORY: категория (item, weapon, prop, npc)
    """

    # Метаданные класса (переопределяются в наследниках)
    CLASS_ID: str = "base_entity"
    NAME: str = "Entity"
    DESCRIPTION: str = ""
    MODEL: str = ""  # Пустая строка = жёлтый куб
    ICON: str = ""
    MAX_STACK: int = 1
    CATEGORY: str = "misc"
    WEIGHT: float = 0.0
    DROPPABLE: bool = True
    TRADEABLE: bool = True

    def __init__(self, unique_id: Optional[str] = None):
        self.unique_id = unique_id or str(uuid_lib.uuid4())
        self.components: Dict[str, Component] = {}
        self.data: Dict[str, Any] = {}  # Произвольные данные
        self.count: int = 1  # Количество в стеке

        # Runtime state (не сериализуется)
        self._spawned: bool = False
        self._node: Optional['NodePath'] = None
        self._owner_uuid: Optional[str] = None  # UUID владельца (игрока)

    # -------------------------------------------------------------------------
    # Жизненный цикл
    # -------------------------------------------------------------------------

    def on_spawn(self, world, position=None):
        """
        Вызывается когда entity появляется в мире.
        Можно переопределить для кастомной логики.
        """
        self._spawned = True
        for comp in self.components.values():
            comp.on_spawn()

    def on_remove(self):
        """
        Вызывается когда entity удаляется из мира.
        """
        for comp in self.components.values():
            comp.on_remove()
        self._spawned = False

        if self._node:
            self._node.removeNode()
            self._node = None

    def on_pickup(self, player_uuid: str) -> bool:
        """
        Вызывается когда игрок подбирает entity.
        Вернуть False чтобы отменить подбор.
        """
        self._owner_uuid = player_uuid
        return True

    def on_drop(self, player_uuid: str, position=None) -> bool:
        """
        Вызывается когда игрок выбрасывает entity.
        Вернуть False чтобы отменить.
        """
        if not self.DROPPABLE:
            return False
        self._owner_uuid = None
        return True

    def on_use(self, player_uuid: str) -> bool:
        """
        Вызывается когда игрок использует entity.
        Вернуть True если предмет был потреблён.
        """
        return False

    def on_equip(self, player_uuid: str, slot: str) -> bool:
        """
        Вызывается когда игрок экипирует entity.
        """
        return True

    def on_unequip(self, player_uuid: str) -> bool:
        """
        Вызывается когда игрок снимает entity.
        """
        return True

    def update(self, dt: float):
        """Обновление каждый тик (для активных entity)."""
        for comp in self.components.values():
            comp.update(dt)

    # -------------------------------------------------------------------------
    # Компоненты
    # -------------------------------------------------------------------------

    def add_component(self, name: str, component: Component) -> 'Entity':
        """Добавить компонент к entity."""
        self.components[name] = component
        component.on_attach(self)
        if self._spawned:
            component.on_spawn()
        return self

    def get_component(self, name: str) -> Optional[Component]:
        """Получить компонент по имени."""
        return self.components.get(name)

    def has_component(self, name: str) -> bool:
        """Проверить наличие компонента."""
        return name in self.components

    def remove_component(self, name: str) -> Optional[Component]:
        """Удалить компонент."""
        comp = self.components.pop(name, None)
        if comp:
            comp.on_detach()
        return comp

    # -------------------------------------------------------------------------
    # Сериализация
    # -------------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Сериализация для сохранения/передачи."""
        return {
            "class_id": self.CLASS_ID,
            "unique_id": self.unique_id,
            "count": self.count,
            "data": self.data.copy(),
            "owner_uuid": self._owner_uuid,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Entity':
        """Создание из словаря."""
        entity = cls(unique_id=data.get("unique_id"))
        entity.count = data.get("count", 1)
        entity.data = data.get("data", {})
        entity._owner_uuid = data.get("owner_uuid")
        return entity

    # -------------------------------------------------------------------------
    # Визуализация
    # -------------------------------------------------------------------------

    def create_model(self, render_node: 'NodePath') -> 'NodePath':
        """
        Создаёт 3D модель entity в мире.
        По умолчанию создаёт жёлтый куб.
        """
        from panda3d.core import CardMaker, Vec4

        if self.MODEL:
            # Загрузить кастомную модель
            from direct.actor.Actor import Actor
            try:
                self._node = render_node.attachNewNode(f"entity_{self.unique_id}")
                model = loader.loadModel(self.MODEL)
                model.reparentTo(self._node)
            except Exception:
                # Fallback на куб
                self._node = self._create_default_cube(render_node)
        else:
            # Жёлтый куб по умолчанию
            self._node = self._create_default_cube(render_node)

        return self._node

    def _create_default_cube(self, render_node: 'NodePath') -> 'NodePath':
        """Создаёт жёлтый куб как дефолтную модель."""
        from panda3d.core import GeomNode, Geom, GeomVertexFormat, GeomVertexData
        from panda3d.core import GeomVertexWriter, GeomTriangles, Vec4

        # Создаём простой куб
        node = render_node.attachNewNode(f"entity_{self.unique_id}")

        # Используем встроенную модель box
        try:
            cube = loader.loadModel("models/box")
            cube.reparentTo(node)
            cube.setScale(0.3)
            cube.setColor(Vec4(1.0, 0.9, 0.2, 1.0))  # Жёлтый
        except Exception:
            # Если нет box, создадим примитив
            from panda3d.core import CardMaker
            cm = CardMaker("cube_face")
            cm.setFrame(-0.15, 0.15, -0.15, 0.15)
            for i, (h, p) in enumerate([(0, 0), (90, 0), (180, 0), (270, 0), (0, 90), (0, -90)]):
                face = node.attachNewNode(cm.generate())
                face.setH(h)
                face.setP(p)
                if p == 90:
                    face.setZ(0.15)
                elif p == -90:
                    face.setZ(-0.15)
                else:
                    face.setY(0.15)
            node.setColor(Vec4(1.0, 0.9, 0.2, 1.0))

        return node

    # -------------------------------------------------------------------------
    # Утилиты
    # -------------------------------------------------------------------------

    def can_stack_with(self, other: 'Entity') -> bool:
        """Можно ли объединить с другим entity в стек."""
        return (
            self.CLASS_ID == other.CLASS_ID and
            self.count + other.count <= self.MAX_STACK and
            self.data == other.data  # Одинаковые доп. данные
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.CLASS_ID}:{self.unique_id[:8]}>"


# =============================================================================
# ENTITY REGISTRY
# =============================================================================

class EntityRegistry:
    """
    Реестр классов Entity.
    Позволяет регистрировать и создавать entity по CLASS_ID.
    """

    def __init__(self):
        self._classes: Dict[str, type] = {}

    def register(self, entity_class: type):
        """Регистрирует класс entity."""
        if not hasattr(entity_class, 'CLASS_ID'):
            raise ValueError(f"{entity_class} must have CLASS_ID attribute")
        self._classes[entity_class.CLASS_ID] = entity_class
        return entity_class

    def create(self, class_id: str, unique_id: Optional[str] = None, **kwargs) -> Optional[Entity]:
        """Создаёт экземпляр entity по CLASS_ID."""
        entity_class = self._classes.get(class_id)
        if not entity_class:
            return None
        return entity_class(unique_id=unique_id, **kwargs)

    def get_class(self, class_id: str) -> Optional[type]:
        """Получить класс по ID."""
        return self._classes.get(class_id)

    def get_all_classes(self) -> Dict[str, type]:
        """Получить все зарегистрированные классы."""
        return self._classes.copy()

    def is_registered(self, class_id: str) -> bool:
        """Проверить регистрацию."""
        return class_id in self._classes


# Глобальный реестр
ENTITY_REGISTRY = EntityRegistry()


def register_entity(cls):
    """Декоратор для регистрации entity класса."""
    ENTITY_REGISTRY.register(cls)
    return cls


# =============================================================================
# ENTITY MANAGER
# =============================================================================

class EntityManager:
    """
    Менеджер entity в мире.
    Управляет созданием, обновлением и удалением entity.
    """

    def __init__(self, world, event_manager):
        self.world = world
        self.event_manager = event_manager
        self.entities: Dict[str, Entity] = {}  # unique_id -> Entity
        self.world_entities: List[str] = []  # Entity в мире (spawned)

    def spawn(self, entity: Entity, position=None) -> Entity:
        """Спавнит entity в мире."""
        self.entities[entity.unique_id] = entity
        self.world_entities.append(entity.unique_id)
        entity.on_spawn(self.world, position)

        if position and entity._node:
            entity._node.setPos(*position)

        self.event_manager.post("entity_spawned", {
            "entity": entity,
            "class_id": entity.CLASS_ID,
            "unique_id": entity.unique_id,
            "position": position,
        })

        return entity

    def remove(self, unique_id: str) -> Optional[Entity]:
        """Удаляет entity из мира."""
        entity = self.entities.pop(unique_id, None)
        if entity:
            if unique_id in self.world_entities:
                self.world_entities.remove(unique_id)
            entity.on_remove()

            self.event_manager.post("entity_removed", {
                "class_id": entity.CLASS_ID,
                "unique_id": unique_id,
            })

        return entity

    def get(self, unique_id: str) -> Optional[Entity]:
        """Получить entity по ID."""
        return self.entities.get(unique_id)

    def get_by_class(self, class_id: str) -> List[Entity]:
        """Получить все entity определённого класса."""
        return [e for e in self.entities.values() if e.CLASS_ID == class_id]

    def get_in_radius(self, position, radius: float) -> List[Entity]:
        """Получить entity в радиусе от позиции."""
        from math import sqrt
        result = []
        for uid in self.world_entities:
            entity = self.entities.get(uid)
            if entity and entity._node:
                pos = entity._node.getPos()
                dist = sqrt(
                    (pos.x - position[0])**2 +
                    (pos.y - position[1])**2 +
                    (pos.z - position[2])**2
                )
                if dist <= radius:
                    result.append(entity)
        return result

    def update(self, dt: float):
        """Обновить все spawned entity."""
        for uid in self.world_entities:
            entity = self.entities.get(uid)
            if entity:
                entity.update(dt)

    def create_and_spawn(
        self,
        class_id: str,
        position=None,
        unique_id: Optional[str] = None,
        **kwargs
    ) -> Optional[Entity]:
        """Создать и сразу заспавнить entity."""
        entity = ENTITY_REGISTRY.create(class_id, unique_id=unique_id, **kwargs)
        if entity:
            return self.spawn(entity, position)
        return None
