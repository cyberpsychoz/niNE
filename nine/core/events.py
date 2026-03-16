from collections import defaultdict
from typing import Callable, Any, Dict, List
<<<<<<< HEAD
=======
import logging

logger = logging.getLogger(__name__)

>>>>>>> main-core-engine

class EventManager:
    """Простой менеджер событий для слабой связи компонентов."""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, listener: Callable):
        """Подписывает слушателя на тип события."""
        if listener not in self._listeners[event_type]:
            self._listeners[event_type].append(listener)
<<<<<<< HEAD
=======
            logger.debug(f"[EventManager] Subscribed to '{event_type}': {listener.__qualname__}")
>>>>>>> main-core-engine

    def unsubscribe(self, event_type: str, listener: Callable):
        """Отписывает слушателя от типа события."""
        if listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)

    def post(self, event_type: str, data: Any = None):
        """Отправляет событие всем подписанным слушателям."""
<<<<<<< HEAD
        for listener in self._listeners[event_type]:
            try:
                listener(data)
            except Exception as e:
                print(f"Ошибка в обработчике события '{event_type}': {e}")
=======
        listeners = self._listeners[event_type]
        if event_type.startswith("dm_") or event_type == "npc_spawn":
            # Debug logging for NPC-related events
            logger.info(f"[EventManager] Posting '{event_type}' to {len(listeners)} listeners: {data}")
        for listener in listeners:
            try:
                if event_type.startswith("dm_") or event_type == "npc_spawn":
                    logger.info(f"[EventManager] Calling {listener.__qualname__}")
                listener(data)
            except Exception as e:
                logger.error(f"Error in event handler '{event_type}': {e}", exc_info=True)
>>>>>>> main-core-engine

