"""
Тест NPC спавна - проверяет работу ECS и event системы.
Запуск: python test_npc_spawn.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nine.core.events import EventManager
from nine.core.ecs import ECSWorld

def test_ecs_basic():
    """Тест базового ECS."""
    print("=== Тест ECS ===")

    try:
        world = ECSWorld()
        print(f"  ECSWorld создан: {world}")

        # Создаём entity
        entity = world.create_entity("test_entity_1")
        print(f"  Entity создана: {entity.id}")

        # Добавляем тег
        entity.add_tag("npc")
        print(f"  Тег 'npc' добавлен")

        # Проверяем получение entities с тегом
        npcs = world.get_entities_with_tag("npc")
        print(f"  Entities с тегом 'npc': {len(npcs)}")

        print("  [OK] ECS базовый тест пройден\n")
        return True

    except Exception as e:
        print(f"  [FAIL] ECS ошибка: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_event_manager():
    """Тест Event Manager."""
    print("=== Тест Event Manager ===")

    try:
        em = EventManager()
        print(f"  EventManager создан: {em}")

        received_events = []

        def handler(data):
            received_events.append(data)
            print(f"    Handler получил: {data}")

        # Подписываемся
        em.subscribe("test_event", handler)
        print("  Подписка на 'test_event' выполнена")

        # Постим событие
        em.post("test_event", {"message": "Hello!"})
        print("  Событие 'test_event' отправлено")

        # Проверяем
        if len(received_events) == 1 and received_events[0]["message"] == "Hello!":
            print("  [OK] Event Manager тест пройден\n")
            return True
        else:
            print(f"  [FAIL] События не получены: {received_events}\n")
            return False

    except Exception as e:
        print(f"  [FAIL] Event Manager ошибка: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_npc_components():
    """Тест NPC компонентов."""
    print("=== Тест NPC компонентов ===")

    try:
        from nine.plugins.npc.sh_components import (
            PositionComponent, ModelComponent, NPCInfoComponent,
            AIComponent, AIBehavior, CombatComponent
        )

        print("  Компоненты импортированы")

        # Создаём компоненты
        pos = PositionComponent(x=10, y=20, z=1)
        print(f"  PositionComponent: ({pos.x}, {pos.y}, {pos.z})")

        model = ModelComponent(model_path="human_male")
        print(f"  ModelComponent: {model.model_path}")

        info = NPCInfoComponent(template_id="goblin", display_name="Гоблин")
        print(f"  NPCInfoComponent: {info.display_name}")

        ai = AIComponent(behavior=AIBehavior.HOSTILE)
        print(f"  AIComponent: {ai.behavior}")

        combat = CombatComponent(hp_max=10, hp_current=10, armor_class=12)
        print(f"  CombatComponent: HP {combat.hp_current}/{combat.hp_max}")

        print("  [OK] NPC компоненты тест пройден\n")
        return True

    except Exception as e:
        print(f"  [FAIL] NPC компоненты ошибка: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_npc_manager_import():
    """Тест импорта NPC Manager."""
    print("=== Тест импорта NPC Manager ===")

    try:
        from nine.plugins.npc.sv_npc_manager import NPCManager
        print("  NPCManager импортирован")
        print("  [OK] Импорт NPC Manager успешен\n")
        return True

    except Exception as e:
        print(f"  [FAIL] Импорт NPC Manager ошибка: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_full_spawn_flow():
    """Тест полного flow спавна NPC."""
    print("=== Тест полного flow спавна ===")

    try:
        from nine.core.events import EventManager
        from nine.plugins.npc.sh_components import (
            PositionComponent, ModelComponent, NPCInfoComponent,
            AIComponent, AIBehavior, CombatComponent, FactionComponent
        )
        from nine.core.ecs import ECSWorld

        # Создаём мир
        ecs_world = ECSWorld()
        event_manager = EventManager()

        print("  ECS World и EventManager созданы")

        # Симулируем то, что делает NPC Manager
        npc_templates = {
            "goblin": {
                "display_name": "Гоблин",
                "model": "goblin",
                "components": {
                    "AIComponent": {
                        "behavior": "HOSTILE",
                        "aggro_radius": 12.0,
                    },
                    "CombatComponent": {
                        "hp_max": 7,
                        "hp_current": 7,
                        "armor_class": 15,
                    },
                },
                "tags": ["humanoid", "monster"]
            }
        }

        template = npc_templates["goblin"]
        print(f"  Шаблон 'goblin' найден: {template['display_name']}")

        # Создаём entity
        entity = ecs_world.create_entity()
        print(f"  Entity создана: {entity.id}")

        # Добавляем компоненты
        entity.add_component(PositionComponent(x=10, y=10, z=1))
        entity.add_component(ModelComponent(model_path=template["model"]))
        entity.add_component(NPCInfoComponent(
            template_id="goblin",
            display_name=template["display_name"]
        ))
        entity.add_component(AIComponent(behavior=AIBehavior.HOSTILE))
        entity.add_component(CombatComponent(hp_max=7, hp_current=7, armor_class=15))

        entity.add_tag("npc")
        entity.add_tag("monster")

        print(f"  Компоненты добавлены к entity")

        # Проверяем
        pos = entity.get_component(PositionComponent)
        info = entity.get_component(NPCInfoComponent)

        print(f"  Позиция: ({pos.x}, {pos.y}, {pos.z})")
        print(f"  Имя: {info.display_name}")

        # Получаем NPC
        npcs = ecs_world.get_entities_with_tag("npc")
        print(f"  NPCs в мире: {len(npcs)}")

        if len(npcs) == 1:
            print("  [OK] Полный flow спавна пройден\n")
            return True
        else:
            print(f"  [FAIL] Неверное количество NPC\n")
            return False

    except Exception as e:
        print(f"  [FAIL] Flow спавна ошибка: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  ТЕСТ NPC СИСТЕМЫ")
    print("="*50 + "\n")

    results = []

    results.append(("ECS Basic", test_ecs_basic()))
    results.append(("Event Manager", test_event_manager()))
    results.append(("NPC Components", test_npc_components()))
    results.append(("NPC Manager Import", test_npc_manager_import()))
    results.append(("Full Spawn Flow", test_full_spawn_flow()))

    print("="*50)
    print("  РЕЗУЛЬТАТЫ")
    print("="*50)

    passed = 0
    failed = 0
    for name, result in results:
        status = "OK" if result else "FAIL"
        print(f"  {name}: [{status}]")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n  Пройдено: {passed}/{len(results)}")
    print(f"  Провалено: {failed}/{len(results)}")
    print("="*50 + "\n")
