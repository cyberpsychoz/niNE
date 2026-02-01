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
from nine.core.components import TransformComponent, PawnComponent, PawnType
from nine.plugins.npc.sh_components import (
    AIComponent, AIBehavior, AIState,
    PositionComponent, CombatComponent
)
from nine.plugins.npc.sv_npc_ai import AISystem

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
    ai_system = AISystem()  # AISystem не требует world и event_manager в конструкторе

    # === Сценарий 1: Нейтральный гоблин вдалеке от игрока ===
    logger.info("\n--- Scenario 1: Neutral Goblin (Far from Player) ---")

    goblin = world.create_entity()
    goblin.add_component(PositionComponent(x=10.0, y=10.0, z=0.0))
    goblin.add_component(PawnComponent(
        pawn_type=PawnType.NPC,
        display_name="Goblin"
    ))
    goblin.add_component(AIComponent(
        state=AIState.IDLE,
        behavior=AIBehavior.NEUTRAL,
        aggro_radius=5.0,
    ))
    goblin.add_component(CombatComponent(
        hp_max=7,
        hp_current=7,
        armor_class=15,
        attack_bonus=4,
    ))

    player = world.create_entity()
    player.add_component(PositionComponent(x=0.0, y=0.0, z=0.0))
    player.add_component(PawnComponent(
        pawn_type=PawnType.PLAYER,
        display_name="Player",
        owner_id=1
    ))

    # Симулируем 10 тиков
    logger.info("Player at (0,0), Goblin at (10,10), distance ~14 > aggro_radius=5")
    for tick in range(10):
        # Получаем entities для AI системы
        entities = list(world.get_entities_with_components(PositionComponent, AIComponent))
        ai_system.update(0.1, entities)

        ai = goblin.get_component(AIComponent)
        logger.info(f"Tick {tick}: Goblin state={ai.state.name}")

        if tick == 5:
            # На 5-м тике игрок приближается
            player_pos = player.get_component(PositionComponent)
            player_pos.x = 8.0
            player_pos.y = 8.0
            logger.info("Player moved to (8,8), distance ~2.8 < aggro_radius=5")

        await asyncio.sleep(0.05)

    # === Сценарий 2: Провокация - игрок атакует нейтрального NPC ===
    logger.info("\n--- Scenario 2: Provocation (Player Attacks Neutral NPC) ---")

    skeleton = world.create_entity()
    skeleton.add_component(PositionComponent(x=5.0, y=5.0, z=0.0))
    skeleton.add_component(PawnComponent(
        pawn_type=PawnType.NPC,
        display_name="Skeleton"
    ))
    skeleton.add_component(AIComponent(
        state=AIState.IDLE,
        behavior=AIBehavior.NEUTRAL,
        aggro_radius=4.0,
    ))
    skeleton.add_component(CombatComponent(
        hp_max=13,
        hp_current=13,
        armor_class=13,
        attack_bonus=4,
    ))

    logger.info("Skeleton at (5,5), Player at (8,8), distance ~4.2 > aggro_radius=4")
    for tick in range(5):
        entities = list(world.get_entities_with_components(PositionComponent, AIComponent))
        ai_system.update(0.1, entities)
        ai = skeleton.get_component(AIComponent)
        logger.info(f"Tick {tick}: Skeleton state={ai.state.name}")
        await asyncio.sleep(0.05)

    # Игрок атакует скелета (симулируем провокацию)
    logger.info("Player attacks Skeleton! Changing behavior to HOSTILE")
    ai = skeleton.get_component(AIComponent)
    ai.behavior = AIBehavior.HOSTILE  # Провокация = становится враждебным

    for tick in range(5):
        entities = list(world.get_entities_with_components(PositionComponent, AIComponent))
        ai_system.update(0.1, entities)
        ai = skeleton.get_component(AIComponent)
        logger.info(f"Tick {tick}: Skeleton state={ai.state.name} (now hostile)")
        await asyncio.sleep(0.05)

    # === Сценарий 3: Wandering NPC ===
    logger.info("\n--- Scenario 3: Wandering NPC ---")

    merchant = world.create_entity()
    merchant.add_component(PositionComponent(x=15.0, y=15.0, z=0.0))
    merchant.add_component(PawnComponent(
        pawn_type=PawnType.NPC,
        display_name="Merchant"
    ))
    merchant.add_component(AIComponent(
        state=AIState.IDLE,
        behavior=AIBehavior.WANDER,
        move_speed=1.0,
        wander_radius=5.0,
        wander_center=(15.0, 15.0, 0.0),
    ))
    merchant.add_component(CombatComponent(
        hp_max=10,
        hp_current=10,
    ))

    for tick in range(10):
        entities = list(world.get_entities_with_components(PositionComponent, AIComponent))
        ai_system.update(0.1, entities)
        pos = merchant.get_component(PositionComponent)
        ai = merchant.get_component(AIComponent)
        logger.info(f"Tick {tick}: Merchant pos=({pos.x:.1f},{pos.y:.1f}), state={ai.state.name}")
        await asyncio.sleep(0.05)

    logger.info("\n=== NPC BEHAVIOR SIMULATION END ===")

    # Итоги
    logger.info("\n--- Event Summary ---")
    for event_name, data in event_manager.events:
        logger.info(f"{event_name}: {data}")


if __name__ == "__main__":
    asyncio.run(simulate_npc_behavior())
