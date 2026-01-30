"""
Симуляция NPC для проверки иммерсивности поведения.

Запуск:
    python -m tests.test_npc_simulation

Проверяет:
- Поведение NPC в состояниях IDLE, WANDERING, PURSUING, ATTACKING
- Корректность переходов между состояниями
- Логику агрессии и провокации
- Взаимодействие с игроком на разных дистанциях
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nine.core.ecs import ECSWorld
from nine.core.components import Transform, Pawn, AIComponent, CombatComponent
from nine.plugins.npc.sv_npc_ai import NPCAISystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NPC_SIMULATION")


class MockEventManager:
    """Мок EventManager для симуляции."""

    def __init__(self):
        self.events = []

    def post(self, event_name: str, data: dict):
        self.events.append((event_name, data))
        logger.debug(f"Event: {event_name} - {data}")


async def simulate_npc_behavior():
    """Симулирует поведение нескольких NPC в разных сценариях."""
    logger.info("=== NPC BEHAVIOR SIMULATION START ===")

    # Создаём мир и систему AI
    world = ECSWorld()
    event_manager = MockEventManager()
    ai_system = NPCAISystem(world, event_manager)

    # === Сценарий 1: Нейтральный гоблин вдалеке от игрока ===
    logger.info("\n--- Scenario 1: Neutral Goblin (Far from Player) ---")

    goblin = world.create_entity()
    goblin.add_component(Transform(position=(10, 10, 0)))
    goblin.add_component(Pawn(name="Goblin", hp=7, max_hp=7))
    goblin.add_component(AIComponent(
        state="IDLE",
        behavior="NEUTRAL",
        aggro_radius=5.0,
    ))
    goblin.add_component(CombatComponent(
        hp_max=7,
        hp_current=7,
        armor_class=15,
        attack_bonus=4,
    ))

    player = world.create_entity()
    player.add_component(Transform(position=(0, 0, 0)))
    player.add_component(Pawn(name="Player", hp=20, max_hp=20, is_player=True))

    # Симулируем 10 тиков
    logger.info("Player at (0,0), Goblin at (10,10), distance ~14 > aggro_radius=5")
    for tick in range(10):
        ai_system.update(0.1)
        ai = goblin.get_component(AIComponent)
        logger.info(f"Tick {tick}: Goblin state={ai.state}")

        if tick == 5:
            # На 5-м тике игрок приближается
            player_transform = player.get_component(Transform)
            player_transform.position = (8, 8, 0)
            logger.info("Player moved to (8,8), distance ~2.8 < aggro_radius=5")

        await asyncio.sleep(0.05)

    # === Сценарий 2: Провокация - игрок атакует нейтрального NPC ===
    logger.info("\n--- Scenario 2: Provocation (Player Attacks Neutral NPC) ---")

    skeleton = world.create_entity()
    skeleton.add_component(Transform(position=(5, 5, 0)))
    skeleton.add_component(Pawn(name="Skeleton", hp=13, max_hp=13))
    skeleton.add_component(AIComponent(
        state="IDLE",
        behavior="NEUTRAL",
        aggro_radius=4.0,
        was_provoked=False,
    ))
    skeleton.add_component(CombatComponent(
        hp_max=13,
        hp_current=13,
        armor_class=13,
        attack_bonus=4,
    ))

    logger.info("Skeleton at (5,5), Player at (8,8), distance ~4.2 > aggro_radius=4")
    for tick in range(5):
        ai_system.update(0.1)
        ai = skeleton.get_component(AIComponent)
        logger.info(f"Tick {tick}: Skeleton state={ai.state}")
        await asyncio.sleep(0.05)

    # Игрок атакует скелета
    logger.info("Player attacks Skeleton! Setting was_provoked=True")
    ai = skeleton.get_component(AIComponent)
    ai.was_provoked = True

    for tick in range(5):
        ai_system.update(0.1)
        ai = skeleton.get_component(AIComponent)
        logger.info(f"Tick {tick}: Skeleton state={ai.state} (provoked)")
        await asyncio.sleep(0.05)

    # === Сценарий 3: Wandering NPC ===
    logger.info("\n--- Scenario 3: Wandering NPC ---")

    merchant = world.create_entity()
    merchant.add_component(Transform(position=(15, 15, 0)))
    merchant.add_component(Pawn(name="Merchant", hp=10, max_hp=10))
    merchant.add_component(AIComponent(
        state="WANDERING",
        behavior="IDLE",
        move_speed=1.0,
    ))

    for tick in range(10):
        ai_system.update(0.1)
        transform = merchant.get_component(Transform)
        ai = merchant.get_component(AIComponent)
        logger.info(f"Tick {tick}: Merchant pos={transform.position}, state={ai.state}")
        await asyncio.sleep(0.05)

    logger.info("\n=== NPC BEHAVIOR SIMULATION END ===")

    # Итоги
    logger.info("\n--- Event Summary ---")
    for event_name, data in event_manager.events:
        logger.info(f"{event_name}: {data}")


if __name__ == "__main__":
    asyncio.run(simulate_npc_behavior())
