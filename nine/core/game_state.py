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
    - CHARACTER_SELECT: Выбор персонажа (D&D)
    - CHARACTER_CREATE: Создание персонажа (D&D)
    - IN_GAME: Игровой процесс
    """
    MENU = auto()
    CONNECTING = auto()
    CHARACTER_SELECT = auto()
    CHARACTER_CREATE = auto()
    IN_GAME = auto()