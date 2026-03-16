"""
Общие константы для системы характеристик.
Доступны и на сервере, и на клиенте.
"""

# Здоровье
DEFAULT_HEALTH = 100
MAX_HEALTH = 100
MIN_HEALTH = 0

# Голод
DEFAULT_HUNGER = 100
MAX_HUNGER = 100
MIN_HUNGER = 0
HUNGER_DECAY_RATE = 0.5  # Единиц голода в секунду
HUNGER_DAMAGE_THRESHOLD = 10  # При каком голоде начинается урон
HUNGER_DAMAGE_RATE = 1  # Урон в секунду при голоде

# Типы урона и их модификаторы
DAMAGE_TYPES = {
    "physical": 1.0,
    "fire": 1.2,
    "ice": 0.8,
    "poison": 0.5,
    "fall": 1.5,
    "hunger": 0.3,  # Урон от голода
}

# Статусы для UI
HEALTH_STATUS = {
    "critical": (0, 25),
    "low": (25, 50),
    "medium": (50, 75),
    "high": (75, 100),
}

HUNGER_STATUS = {
    "starving": (0, 25),
    "hungry": (25, 50),
    "satisfied": (50, 75),
    "full": (75, 100),
}
