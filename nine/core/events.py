from collections import defaultdict
from typing import Callable, Any, Dict, List

class EventManager:
    """Простой менеджер событий для слабой связи компонентов."""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, listener: Callable):
        """Подписывает слушателя на тип события."""
        if listener not in self._listeners[event_type]:
            self._listeners[event_type].append(listener)

    def unsubscribe(self, event_type: str, listener: Callable):
        """Отписывает слушателя от типа события."""
        if listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)

    def post(self, event_type: str, data: Any = None):
        """Отправляет событие всем подписанным слушателям."""
        for listener in self._listeners[event_type]:
            try:
                listener(data)
            except Exception as e:
                print(f"Ошибка в обработчике события '{event_type}': {e}")

