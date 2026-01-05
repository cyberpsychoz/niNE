"""
Game state enumeration.
Defines possible game states for UI state machine.
"""

from enum import Enum, auto


class GameState(Enum):
    """
    Перечисление состояний игры.

    - MENU: Главное меню (логин, настройки)
    - CONNECTING: Подключение к серверу
    - IN_GAME: Игровой процесс
    """
    MENU = auto()
    CONNECTING = auto()
    IN_GAME = auto()
