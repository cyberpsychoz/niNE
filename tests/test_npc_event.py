"""
Тест событий NPC спавна - проверяет event flow.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nine.core.events import EventManager

def test_event_subscription():
    """Тест подписки на события dm_npc_spawn."""
    print("=== Тест подписки на dm_npc_spawn ===")

    em = EventManager()

    spawn_received = []

    def on_dm_spawn(data):
        print(f"  [EVENT] dm_npc_spawn получен: {data}")
        spawn_received.append(data)

    # Подписываемся как NPC Manager
    em.subscribe("dm_npc_spawn", on_dm_spawn)
    print("  Подписка на dm_npc_spawn выполнена")

    # Симулируем отправку как chat handler
    test_data = {
        "template_id": "goblin",
        "position": {"x": 10.0, "y": 10.0, "z": 1.0},
        "spawner_id": 1
    }

    em.post("dm_npc_spawn", test_data)
    print("  Событие dm_npc_spawn отправлено")

    if spawn_received:
        print(f"  [OK] Событие получено: {spawn_received[0]}")
        return True
    else:
        print("  [FAIL] Событие не получено!")
        return False


def test_npc_manager_event_handling():
    """Тест обработки событий NPC Manager."""
    print("\n=== Тест NPC Manager event handling ===")

    try:
        from nine.core.events import EventManager
        from nine.core.ecs import ECSWorld

        # Создаём mock context
        class MockApp:
            def __init__(self):
                self.plugin_manager = None

        class MockContext:
            def __init__(self, em):
                self.event_manager = em
                self.plugin_path = "nine/plugins/npc"
                self.app = MockApp()
                import logging
                self.logger = logging.getLogger("test_npc")

            def get_logger(self, name):
                import logging
                return logging.getLogger(name)

        em = EventManager()
        ctx = MockContext(em)

        # Импортируем NPCManager
        from nine.plugins.npc.sv_npc_manager import NPCManager

        # Создаём NPC Manager
        npc_manager = NPCManager(ctx)
        npc_manager.on_load()

        print("  NPCManager создан и загружен")

        # Проверяем, что подписка есть
        print(f"  Подписчики dm_npc_spawn: {len(em._listeners.get('dm_npc_spawn', []))}")

        # Отправляем событие спавна
        spawn_data = {
            "template_id": "goblin",
            "position": {"x": 5.0, "y": 5.0, "z": 1.0}
        }

        print(f"  Отправляем dm_npc_spawn: {spawn_data}")
        em.post("dm_npc_spawn", spawn_data)

        # Обрабатываем pending additions в ECS
        npc_manager.ecs_world._process_pending_additions()

        # Проверяем результат
        npc_states = npc_manager.get_npc_states()
        print(f"  NPC states после спавна: {len(npc_states)}")

        if npc_states:
            print(f"  [OK] NPC заспавнен: {npc_states[0]}")
            return True
        else:
            print("  [FAIL] NPC не заспавнен")
            return False

    except Exception as e:
        print(f"  [FAIL] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  ТЕСТ EVENT FLOW NPC")
    print("="*50 + "\n")

    r1 = test_event_subscription()
    r2 = test_npc_manager_event_handling()

    print("\n" + "="*50)
    print("  РЕЗУЛЬТАТЫ")
    print("="*50)
    print(f"  Event subscription: {'OK' if r1 else 'FAIL'}")
    print(f"  NPC Manager handling: {'OK' if r2 else 'FAIL'}")
    print("="*50 + "\n")
