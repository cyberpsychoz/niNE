"""
Тест pathfinding системы.
"""
import sys
sys.path.insert(0, '.')

from nine.core.pathfinder import GridPathfinder, PathSmoother
from panda3d.core import Vec3

def test_pathfinder():
    print("\n" + "="*60)
    print("  ТЕСТ PATHFINDING")
    print("="*60 + "\n")

    # Создаём pathfinder
    print("[1] Создаём GridPathfinder...")
    pf = GridPathfinder(
        cell_size=1.0,
        width=50,
        height=50,
        origin_x=-25,
        origin_y=-25
    )
    print(f"    Grid: {pf.width}x{pf.height}, cell_size={pf.cell_size}")
    print(f"    Origin: ({pf.origin_x}, {pf.origin_y})")

    # Добавляем стену
    print("\n[2] Добавляем стену (x=0, y=-10..10)...")
    for y in range(-10, 11):
        pf.set_walkable(0, y, False)

    # Тест поиска пути
    print("\n[3] Ищем путь от (-5, 0, 0) до (5, 0, 0)...")
    result = pf.find_path((-5, 0, 0), (5, 0, 0))

    if result.found:
        print(f"    [OK] Путь найден!")
        print(f"    Длина: {len(result.path)} точек")
        print(f"    Стоимость: {result.cost:.2f}")
        print(f"    Узлов исследовано: {result.nodes_explored}")

        # Показываем путь
        print("\n    Маршрут:")
        for i, point in enumerate(result.path[:10]):  # Первые 10 точек
            print(f"      {i}: ({point.x:.1f}, {point.y:.1f})")
        if len(result.path) > 10:
            print(f"      ... ещё {len(result.path) - 10} точек")
    else:
        print("    [FAIL] Путь не найден!")

    # Тест прямого пути (без стены)
    print("\n[4] Ищем прямой путь от (-5, 5, 0) до (5, 5, 0) (без стены)...")
    result2 = pf.find_path((-5, 5, 0), (5, 5, 0))

    if result2.found:
        print(f"    [OK] Путь найден! Длина: {len(result2.path)} точек")
    else:
        print("    [FAIL] Путь не найден!")

    # Тест сглаживания
    if result.found and len(result.path) > 2:
        print("\n[5] Сглаживаем путь...")
        smoothed = PathSmoother.smooth_path(result.path, pf)
        print(f"    До: {len(result.path)} точек")
        print(f"    После: {len(smoothed)} точек")

    # Debug info
    print("\n[6] Debug info:")
    info = pf.get_debug_info()
    for key, value in info.items():
        print(f"    {key}: {value}")

    print("\n" + "="*60)
    print("  PATHFINDING ТЕСТ ЗАВЕРШЁН")
    print("="*60 + "\n")


def test_ai_behavior():
    """Тест AI поведений."""
    print("\n" + "="*60)
    print("  ТЕСТ AI BEHAVIORS")
    print("="*60 + "\n")

    try:
        from nine.plugins.npc.sh_components import AIBehavior, AIState

        print("[1] AI Behaviors:")
        for b in AIBehavior:
            print(f"    - {b.name}")

        print("\n[2] AI States:")
        for s in AIState:
            print(f"    - {s.name}")

        print("\n    [OK] AI компоненты загружены")

    except Exception as e:
        print(f"    [FAIL] Ошибка: {e}")


if __name__ == "__main__":
    test_pathfinder()
    test_ai_behavior()
