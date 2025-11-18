from typing import Dict
from .events import EventManager

class Entity:
    """
    Базовый класс для любого объекта в игровом мире.
    В полноценной реализации это будет часть ECS.
    """
    def __init__(self, entity_id: int):
        self.id = entity_id
        self.position = (0, 0, 0)

    def __repr__(self):
        return f"<Entity {self.id}>"


class World:
    """
    Управляет состоянием всех сущностей в игровом мире.
    """

    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager
        self.entities: Dict[int, Entity] = {}
        self._next_entity_id = 1
        
        self.event_manager.subscribe("app_tick", self.update)

    def create_entity(self) -> Entity:
        """Создает новую сущность и добавляет ее в мир."""
        entity_id = self._next_entity_id
        self._next_entity_id += 1
        
        entity = Entity(entity_id)
        self.entities[entity_id] = entity
        
        self.event_manager.post("entity_created", entity)
        print(f"Создана сущность {entity.id}")
        return entity

    def destroy_entity(self, entity_id: int):
        """Удаляет сущность из мира."""
        if entity_id in self.entities:
            entity = self.entities.pop(entity_id)
            self.event_manager.post("entity_destroyed", entity)
            print(f"Удалена сущность {entity.id}")

    def get_entity(self, entity_id: int) -> Entity:
        """Возвращает сущность по ее ID."""
        return self.entities.get(entity_id)

    def update(self, dt: float):
        """
        Основной цикл обновления мира.
        """
        pass

