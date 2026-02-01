"""
Комплексное тестирование системы NPC AI на наличие багов.

Проверяет:
- Детекцию игрока (граничные случаи)
- Переходы между состояниями
- Логику агрессии NEUTRAL vs HOSTILE
- Провокацию и leash radius
- Деление на ноль и edge cases
- Memory leaks и performance
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nine.core.ecs import ECSWorld
from nine.core.components import PawnComponent, PawnType, FactionComponent
from nine.plugins.npc.sh_components import (
    AIComponent, AIBehavior, AIState,
    PositionComponent, CombatComponent
)
from nine.plugins.npc.sv_npc_ai import AISystem

logging.basicConfig(
    level=logging.DEBUG,  # DEBUG mode for bug hunting
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NPC_AI_BUGS")
logger.setLevel(logging.DEBUG)


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.warnings = []

    def fail(self, error: str):
        self.passed = False
        self.error = error

    def succeed(self):
        self.passed = True

    def warn(self, warning: str):
        self.warnings.append(warning)


class MockNPCManager:
    """Mock NPCManager для тестов."""
    def __init__(self):
        self.players = []
        self.event_manager = self  # Mock event manager

    def post(self, event_name: str, data: dict):
        """Mock event post."""
        pass

    def get_players(self):
        """Возвращает список игроков."""
        return self.players

    def add_player(self, player_entity):
        """Добавляет игрока в список."""
        pos = player_entity.get_component(PositionComponent)
        pawn = player_entity.get_component(PawnComponent)
        self.players.append({
            "uuid": player_entity.id,
            "position": {"x": pos.x, "y": pos.y, "z": pos.z},
            "name": pawn.display_name
        })

    def update_player_position(self, player_entity):
        """Обновляет позицию игрока."""
        pos = player_entity.get_component(PositionComponent)
        for p in self.players:
            if p["uuid"] == player_entity.id:
                p["position"] = {"x": pos.x, "y": pos.y, "z": pos.z}
                break


class NPCAITester:
    def __init__(self):
        self.world = ECSWorld()
        self.npc_manager = MockNPCManager()
        # Use new decoupled API - pass event_manager directly
        self.ai_system = AISystem(event_manager=self.npc_manager)
        self.results = []
        self.bug_count = 0

    def reset(self):
        """Сбрасывает состояние между тестами."""
        self.world.clear()
        self.npc_manager.players.clear()

    def create_npc(self, x: float, y: float, behavior: AIBehavior, aggro_radius: float = 5.0, hostile: bool = True):
        """Создает NPC с заданными параметрами."""
        npc = self.world.create_entity()
        npc.add_component(PositionComponent(x=x, y=y, z=0.0))
        npc.add_component(PawnComponent(pawn_type=PawnType.NPC, display_name="TestNPC"))
        npc.add_component(AIComponent(
            behavior=behavior,
            state=AIState.IDLE,
            aggro_radius=aggro_radius,
            leash_radius=30.0,
            attack_range=2.0,
        ))
        npc.add_component(CombatComponent(hp_max=10, hp_current=10, armor_class=10))

        # Добавляем FactionComponent (требуется для _find_nearest_enemy)
        npc.add_component(FactionComponent(
            faction_id="monster" if hostile else "neutral",
            hostile_to_players=hostile
        ))

        return npc

    def create_player(self, x: float, y: float):
        """Создает игрока."""
        player = self.world.create_entity()
        player.add_component(PositionComponent(x=x, y=y, z=0.0))
        player.add_component(PawnComponent(
            pawn_type=PawnType.PLAYER,
            display_name="TestPlayer",
            owner_id=1
        ))
        # Регистрируем игрока в mock manager
        self.npc_manager.add_player(player)
        return player

    def update_player_position(self, player):
        """Обновляет позицию игрока в npc_manager."""
        self.npc_manager.update_player_position(player)

    def update_ai(self, ticks: int = 1):
        """Обновляет AI систему N раз."""
        for _ in range(ticks):
            # КРИТИЧНО: process pending additions before querying entities!
            self.world._process_pending_additions()

            # Update AI with current player positions (new decoupled API)
            self.ai_system.set_player_positions(self.npc_manager.players)

            entities = list(self.world.get_entities_with_components(PositionComponent, AIComponent))
            self.ai_system.update(0.1, entities)

    async def test_aggro_detection_exact_distance(self):
        """BUG TEST: NPC на ТОЧНО aggro_radius - срабатывает ли детекция?"""
        result = TestResult("Aggro Detection at Exact Distance")

        try:
            npc = self.create_npc(0, 0, AIBehavior.HOSTILE, aggro_radius=5.0)
            player = self.create_player(5.0, 0.0)  # Ровно 5.0 units

            self.update_ai(5)

            ai = npc.get_component(AIComponent)

            # На границе aggro_radius NPC должен агриться
            if ai.state == AIState.IDLE:
                result.fail("NPC не агрится на игрока на точном расстоянии aggro_radius (граничный случай)")
                self.bug_count += 1
            else:
                result.succeed()

        except Exception as e:
            result.fail(f"Exception: {e}")
            self.bug_count += 1

        self.results.append(result)
        return result

    async def test_neutral_no_aggro(self):
        """BUG TEST: NEUTRAL NPC не должен атаковать первым."""
        result = TestResult("Neutral NPC No Auto-Aggro")

        try:
            npc = self.create_npc(0, 0, AIBehavior.NEUTRAL, aggro_radius=5.0, hostile=False)
            player = self.create_player(2.0, 0.0)  # Близко (2 units < 5)

            self.update_ai(10)

            ai = npc.get_component(AIComponent)

            if ai.state == AIState.PURSUING or ai.state == AIState.ATTACKING:
                result.fail("NEUTRAL NPC атакует игрока без провокации - нарушение логики")
                self.bug_count += 1
            else:
                result.succeed()

        except Exception as e:
            result.fail(f"Exception: {e}")
            self.bug_count += 1

        self.results.append(result)
        return result

    async def test_hostile_aggro(self):
        """BUG TEST: HOSTILE NPC должен агриться в пределах aggro_radius."""
        result = TestResult("Hostile NPC Auto-Aggro")

        try:
            npc = self.create_npc(0, 0, AIBehavior.HOSTILE, aggro_radius=5.0)
            player = self.create_player(3.0, 0.0)  # Близко (3 < 5)

            # DEBUG: проверяем что игрок зарегистрирован
            logger.debug(f"Players in manager: {len(self.npc_manager.players)}")
            logger.debug(f"Player positions: {self.ai_system._player_positions}")

            self.update_ai(10)

            ai = npc.get_component(AIComponent)

            # DEBUG: проверяем LOD и player_positions после update
            logger.debug(f"LOD level: {ai.lod_level}")
            logger.debug(f"Player positions after update: {self.ai_system._player_positions}")

            if ai.state == AIState.IDLE:
                result.fail("HOSTILE NPC не агрится на игрока в пределах aggro_radius")
                result.warn(f"State: {ai.state.name}, target: {ai.target_entity_id}, LOD: {ai.lod_level}")
                self.bug_count += 1
            else:
                result.succeed()

        except Exception as e:
            result.fail(f"Exception: {e}")
            self.bug_count += 1

        self.results.append(result)
        return result

    async def test_leash_radius(self):
        """BUG TEST: NPC должен отступать если игрок вышел за leash_radius."""
        result = TestResult("Leash Radius Enforcement")

        try:
            npc = self.create_npc(0, 0, AIBehavior.HOSTILE, aggro_radius=5.0)
            npc.get_component(AIComponent).leash_radius = 10.0

            player = self.create_player(3.0, 0.0)

            # NPC агрится
            self.update_ai(5)
            ai = npc.get_component(AIComponent)
            initial_state = ai.state

            # Игрок убегает за leash radius
            player.get_component(PositionComponent).x = 50.0
            self.update_player_position(player)

            self.update_ai(5)

            if ai.state == AIState.PURSUING:
                result.fail("NPC не отступает когда игрок за leash_radius (потенциальный kiting exploit)")
                result.warn(f"Initial: {initial_state.name}, After leash: {ai.state.name}")
                self.bug_count += 1
            else:
                result.succeed()

        except Exception as e:
            result.fail(f"Exception: {e}")
            self.bug_count += 1

        self.results.append(result)
        return result

    async def test_zero_distance(self):
        """BUG TEST: Игрок на той же позиции что NPC - деление на ноль?"""
        result = TestResult("Zero Distance Handling (Division by Zero)")

        try:
            npc = self.create_npc(0, 0, AIBehavior.HOSTILE)
            player = self.create_player(0.0, 0.0)  # Та же позиция!

            # Не должно быть exception
            self.update_ai(5)

            result.succeed()

        except ZeroDivisionError as e:
            result.fail(f"CRITICAL: Division by zero при distance=0: {e}")
            self.bug_count += 1
        except Exception as e:
            result.fail(f"Exception: {e}")
            self.bug_count += 1

        self.results.append(result)
        return result

    async def test_negative_aggro_radius(self):
        """BUG TEST: Отрицательный aggro_radius - undefined behavior?"""
        result = TestResult("Negative Aggro Radius")

        try:
            npc = self.create_npc(0, 0, AIBehavior.HOSTILE, aggro_radius=-5.0)
            player = self.create_player(2.0, 0.0)

            self.update_ai(5)

            ai = npc.get_component(AIComponent)

            # С отрицательным radius не должно быть агро
            if ai.state != AIState.IDLE:
                result.warn("NPC с negative aggro_radius агрится (undefined behavior)")

            result.succeed()

        except Exception as e:
            result.fail(f"Exception: {e}")
            self.bug_count += 1

        self.results.append(result)
        return result

    async def test_wander_infinite_loop(self):
        """BUG TEST: WANDER NPC не зацикливается?"""
        result = TestResult("Wander Infinite Loop Check")

        try:
            npc = self.create_npc(0, 0, AIBehavior.WANDER)

            start_time = time.time()
            self.update_ai(100)  # 100 тиков
            elapsed = time.time() - start_time

            # 100 тиков должно занять < 1 секунды
            if elapsed > 1.0:
                result.fail(f"WANDER AI слишком медленный: {elapsed:.2f}s для 100 тиков (возможно infinite loop)")
                self.bug_count += 1
            else:
                result.succeed()

        except Exception as e:
            result.fail(f"Exception: {e}")
            self.bug_count += 1

        self.results.append(result)
        return result

    async def test_multiple_players(self):
        """BUG TEST: Несколько игроков - выбирает ли NPC ближайшего?"""
        result = TestResult("Multiple Players Target Selection")

        try:
            # Clear state from previous tests
            self.reset()

            npc = self.create_npc(0, 0, AIBehavior.HOSTILE, aggro_radius=10.0)

            player1 = self.create_player(8.0, 0.0)  # Дальше
            player2 = self.create_player(3.0, 0.0)  # Ближе

            self.update_ai(10)

            ai = npc.get_component(AIComponent)

            # NPC должен таргетить ближайшего (player2)
            if ai.target_entity_id == player1.id:
                result.fail("NPC таргетит дальнего игрока вместо ближайшего")
                self.bug_count += 1
            elif ai.target_entity_id == player2.id:
                result.succeed()
            else:
                result.warn("NPC не выбрал ни одного таргета")

        except Exception as e:
            result.fail(f"Exception: {e}")
            self.bug_count += 1

        self.results.append(result)
        return result

    async def test_state_transition_spam(self):
        """BUG TEST: NPC не спамит переходами между состояниями?"""
        result = TestResult("State Transition Spam Check")

        try:
            npc = self.create_npc(0, 0, AIBehavior.HOSTILE, aggro_radius=5.0)
            player = self.create_player(4.9, 0.0)  # На границе

            states = []
            for _ in range(20):
                self.update_ai(1)
                ai = npc.get_component(AIComponent)
                states.append(ai.state)

            # Подсчитываем переключения состояния
            transitions = sum(1 for i in range(1, len(states)) if states[i] != states[i-1])

            if transitions > 10:  # Больше 10 переключений за 20 тиков
                result.fail(f"State transition spam: {transitions} переключений за 20 тиков")
                result.warn(f"States: {[s.name for s in states[:10]]}...")
                self.bug_count += 1
            else:
                result.succeed()

        except Exception as e:
            result.fail(f"Exception: {e}")
            self.bug_count += 1

        self.results.append(result)
        return result

    async def test_dead_npc_updates(self):
        """BUG TEST: Мертвый NPC продолжает обновляться?"""
        result = TestResult("Dead NPC Updates")

        try:
            npc = self.create_npc(0, 0, AIBehavior.HOSTILE)
            player = self.create_player(2.0, 0.0)

            # "Убиваем" NPC
            combat = npc.get_component(CombatComponent)
            combat.hp_current = 0

            ai = npc.get_component(AIComponent)
            ai.state = AIState.DEAD

            initial_state = ai.state
            self.update_ai(10)

            # Мертвый NPC не должен менять состояние
            if ai.state != AIState.DEAD:
                result.fail(f"Мертвый NPC изменил состояние с DEAD на {ai.state.name}")
                self.bug_count += 1
            else:
                result.succeed()

        except Exception as e:
            result.fail(f"Exception: {e}")
            self.bug_count += 1

        self.results.append(result)
        return result

    async def test_memory_leak(self):
        """BUG TEST: Memory leak при создании/удалении NPC?"""
        result = TestResult("Memory Leak Check")

        try:
            import gc
            import sys

            gc.collect()
            initial_objects = len(gc.get_objects())

            # Создаем и удаляем 100 NPC
            npcs_to_remove = []
            for i in range(100):
                npc = self.create_npc(i, i, AIBehavior.HOSTILE)
                self.update_ai(1)
                npcs_to_remove.append(npc)

            # Правильно удаляем NPC через ECS API
            for npc in npcs_to_remove:
                self.world.remove_entity(npc.id)

            # Process pending removals
            self.world._process_pending_removals()

            gc.collect()
            final_objects = len(gc.get_objects())

            leak = final_objects - initial_objects

            if leak > 500:  # Допускаем небольшой рост
                result.fail(f"Potential memory leak: {leak} новых объектов после 100 create/destroy циклов")
                self.bug_count += 1
            else:
                result.succeed()
                result.warn(f"Object count delta: {leak}")

        except Exception as e:
            result.fail(f"Exception: {e}")
            self.bug_count += 1

        self.results.append(result)
        return result

    def print_report(self):
        """Выводит финальный отчет."""
        print("\n" + "="*70)
        print("NPC AI BUG TESTING REPORT")
        print("="*70)

        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        print(f"\nTests Run: {len(self.results)}")
        print(f"✓ Passed: {passed}")
        print(f"✗ Failed: {failed}")
        print(f"🐛 Bugs Found: {self.bug_count}")

        print("\n" + "-"*70)
        print("TEST RESULTS:")
        print("-"*70)

        for r in self.results:
            status = "✓ PASS" if r.passed else "✗ FAIL"
            print(f"\n{status} | {r.name}")

            if r.error:
                print(f"  Error: {r.error}")

            for warning in r.warnings:
                print(f"  ⚠ Warning: {warning}")

        print("\n" + "="*70)

        if self.bug_count == 0:
            print("✓ NO BUGS FOUND - AI система работает корректно!")
        else:
            print(f"⚠ FOUND {self.bug_count} POTENTIAL BUGS - требуется исправление")

        print("="*70 + "\n")


async def main():
    logger.info("Запуск комплексного тестирования NPC AI системы...")

    tester = NPCAITester()

    # Запускаем все тесты
    await tester.test_aggro_detection_exact_distance()
    await tester.test_neutral_no_aggro()
    await tester.test_hostile_aggro()
    await tester.test_leash_radius()
    await tester.test_zero_distance()
    await tester.test_negative_aggro_radius()
    await tester.test_wander_infinite_loop()
    await tester.test_multiple_players()
    await tester.test_state_transition_spam()
    await tester.test_dead_npc_updates()
    await tester.test_memory_leak()

    # Выводим отчет
    tester.print_report()

    return tester.bug_count


if __name__ == "__main__":
    bug_count = asyncio.run(main())
    sys.exit(0 if bug_count == 0 else 1)
