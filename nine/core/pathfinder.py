"""
Pathfinding система для niNE.

Предоставляет алгоритмы поиска пути для NPC:
- Grid-based A* (простой, для начала)
- NavMesh (продвинутый, на будущее)

Пример использования:
    # Создание pathfinder
    pathfinder = GridPathfinder(cell_size=1.0)

    # Загрузка карты проходимости
    pathfinder.build_from_collision(collision_polygons)

    # Поиск пути
    path = pathfinder.find_path(start=(0, 0, 0), end=(10, 5, 0))
    if path:
        for point in path:
            print(f"Move to {point}")
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set, Dict, Callable
from panda3d.core import Vec3, Point3
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Типы данных
# =============================================================================

@dataclass
class PathNode:
    """Узел пути для A* алгоритма."""
    x: int
    y: int
    g_cost: float = 0.0  # Стоимость от старта
    h_cost: float = 0.0  # Эвристика до цели
    parent: Optional['PathNode'] = None

    @property
    def f_cost(self) -> float:
        """Полная стоимость (g + h)."""
        return self.g_cost + self.h_cost

    def __lt__(self, other: 'PathNode') -> bool:
        return self.f_cost < other.f_cost

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PathNode):
            return False
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))


@dataclass
class PathResult:
    """Результат поиска пути."""
    found: bool
    path: List[Vec3] = field(default_factory=list)
    cost: float = 0.0
    nodes_explored: int = 0


# =============================================================================
# Grid-based Pathfinder
# =============================================================================

class GridPathfinder:
    """
    Pathfinder на основе сетки с алгоритмом A*.

    Простой и надёжный pathfinder для начала.
    Карта представляется как 2D сетка проходимых/непроходимых клеток.
    """

    # Направления движения (8 направлений)
    DIRECTIONS = [
        (0, 1),   # Вверх
        (0, -1),  # Вниз
        (1, 0),   # Вправо
        (-1, 0),  # Влево
        (1, 1),   # Вверх-вправо
        (-1, 1),  # Вверх-влево
        (1, -1),  # Вниз-вправо
        (-1, -1), # Вниз-влево
    ]

    # Стоимость движения
    STRAIGHT_COST = 1.0
    DIAGONAL_COST = 1.414  # sqrt(2)

    def __init__(
        self,
        cell_size: float = 1.0,
        width: int = 100,
        height: int = 100,
        origin_x: float = 0.0,
        origin_y: float = 0.0
    ):
        """
        Инициализирует pathfinder.

        Args:
            cell_size: Размер ячейки сетки в мировых единицах
            width: Ширина сетки в ячейках
            height: Высота сетки в ячейках
            origin_x: X координата начала сетки
            origin_y: Y координата начала сетки
        """
        self.cell_size = cell_size
        self.width = width
        self.height = height
        self.origin_x = origin_x
        self.origin_y = origin_y

        # Сетка: True = проходимо, False = стена
        self._grid: List[List[bool]] = [
            [True for _ in range(width)] for _ in range(height)
        ]

        # Высота поверхности (для 3D координат)
        self._height_map: List[List[float]] = [
            [0.0 for _ in range(width)] for _ in range(height)
        ]

        # Динамические препятствия (например, другие NPC)
        self._dynamic_obstacles: Set[Tuple[int, int]] = set()

        logger.info(f"GridPathfinder initialized: {width}x{height}, cell_size={cell_size}")

    # =========================================================================
    # Построение карты
    # =========================================================================

    def build_from_bounds(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        default_walkable: bool = True
    ) -> None:
        """
        Создаёт сетку по границам мира.

        Args:
            min_x, min_y: Минимальные координаты
            max_x, max_y: Максимальные координаты
            default_walkable: Проходимы ли клетки по умолчанию
        """
        self.origin_x = min_x
        self.origin_y = min_y
        self.width = int(math.ceil((max_x - min_x) / self.cell_size))
        self.height = int(math.ceil((max_y - min_y) / self.cell_size))

        self._grid = [
            [default_walkable for _ in range(self.width)]
            for _ in range(self.height)
        ]
        self._height_map = [
            [0.0 for _ in range(self.width)]
            for _ in range(self.height)
        ]

        logger.info(f"Grid rebuilt: {self.width}x{self.height} from bounds")

    def set_walkable(self, world_x: float, world_y: float, walkable: bool) -> None:
        """
        Устанавливает проходимость клетки по мировым координатам.

        Args:
            world_x, world_y: Мировые координаты
            walkable: Проходима ли клетка
        """
        grid_x, grid_y = self.world_to_grid(world_x, world_y)
        if self._in_bounds(grid_x, grid_y):
            self._grid[grid_y][grid_x] = walkable

    def set_walkable_rect(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        walkable: bool
    ) -> None:
        """
        Устанавливает проходимость прямоугольной области.

        Args:
            min_x, min_y, max_x, max_y: Границы области
            walkable: Проходима ли область
        """
        grid_min_x, grid_min_y = self.world_to_grid(min_x, min_y)
        grid_max_x, grid_max_y = self.world_to_grid(max_x, max_y)

        for y in range(max(0, grid_min_y), min(self.height, grid_max_y + 1)):
            for x in range(max(0, grid_min_x), min(self.width, grid_max_x + 1)):
                self._grid[y][x] = walkable

    def set_height(self, world_x: float, world_y: float, height: float) -> None:
        """
        Устанавливает высоту поверхности в точке.

        Args:
            world_x, world_y: Мировые координаты
            height: Высота поверхности (Z)
        """
        grid_x, grid_y = self.world_to_grid(world_x, world_y)
        if self._in_bounds(grid_x, grid_y):
            self._height_map[grid_y][grid_x] = height

    def build_from_collision_polygons(
        self,
        floor_polygons: List,
        wall_polygons: List,
        world_bounds: Tuple[float, float, float, float]
    ) -> None:
        """
        Строит карту проходимости из collision полигонов.

        Args:
            floor_polygons: Полигоны пола
            wall_polygons: Полигоны стен
            world_bounds: (min_x, min_y, max_x, max_y)
        """
        min_x, min_y, max_x, max_y = world_bounds
        self.build_from_bounds(min_x, min_y, max_x, max_y, default_walkable=False)

        # Отмечаем пол как проходимый
        for polygon in floor_polygons:
            # Получаем вершины полигона
            vertices = self._get_polygon_vertices(polygon)
            if vertices:
                self._fill_polygon(vertices, walkable=True)

        # Отмечаем стены как непроходимые
        for polygon in wall_polygons:
            vertices = self._get_polygon_vertices(polygon)
            if vertices:
                self._fill_polygon(vertices, walkable=False)

        walkable_count = sum(
            1 for row in self._grid for cell in row if cell
        )
        logger.info(f"Pathfinder map built: {walkable_count} walkable cells")

    def _get_polygon_vertices(self, polygon) -> List[Tuple[float, float]]:
        """Извлекает вершины из collision polygon."""
        try:
            # Panda3D CollisionPolygon
            if hasattr(polygon, 'get_num_points'):
                return [
                    (polygon.get_point(i).x, polygon.get_point(i).y)
                    for i in range(polygon.get_num_points())
                ]
        except Exception as e:
            logger.warning(f"Failed to get polygon vertices: {e}")
        return []

    def _fill_polygon(self, vertices: List[Tuple[float, float]], walkable: bool) -> None:
        """Заполняет полигон на сетке."""
        if len(vertices) < 3:
            return

        # Находим bounding box
        min_x = min(v[0] for v in vertices)
        max_x = max(v[0] for v in vertices)
        min_y = min(v[1] for v in vertices)
        max_y = max(v[1] for v in vertices)

        grid_min_x, grid_min_y = self.world_to_grid(min_x, min_y)
        grid_max_x, grid_max_y = self.world_to_grid(max_x, max_y)

        # Проверяем каждую клетку
        for gy in range(max(0, grid_min_y), min(self.height, grid_max_y + 1)):
            for gx in range(max(0, grid_min_x), min(self.width, grid_max_x + 1)):
                wx, wy = self.grid_to_world(gx, gy)
                if self._point_in_polygon(wx, wy, vertices):
                    self._grid[gy][gx] = walkable

    def _point_in_polygon(self, x: float, y: float, vertices: List[Tuple[float, float]]) -> bool:
        """Проверяет, находится ли точка внутри полигона (ray casting)."""
        n = len(vertices)
        inside = False
        j = n - 1

        for i in range(n):
            xi, yi = vertices[i]
            xj, yj = vertices[j]

            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside

    # =========================================================================
    # Динамические препятствия
    # =========================================================================

    def add_dynamic_obstacle(self, world_x: float, world_y: float) -> None:
        """Добавляет динамическое препятствие (например, другой NPC)."""
        grid_x, grid_y = self.world_to_grid(world_x, world_y)
        self._dynamic_obstacles.add((grid_x, grid_y))

    def remove_dynamic_obstacle(self, world_x: float, world_y: float) -> None:
        """Удаляет динамическое препятствие."""
        grid_x, grid_y = self.world_to_grid(world_x, world_y)
        self._dynamic_obstacles.discard((grid_x, grid_y))

    def clear_dynamic_obstacles(self) -> None:
        """Очищает все динамические препятствия."""
        self._dynamic_obstacles.clear()

    # =========================================================================
    # Поиск пути
    # =========================================================================

    def find_path(
        self,
        start: Tuple[float, float, float],
        end: Tuple[float, float, float],
        max_iterations: int = 10000
    ) -> PathResult:
        """
        Находит путь между двумя точками с помощью A*.

        Args:
            start: Начальная позиция (x, y, z)
            end: Конечная позиция (x, y, z)
            max_iterations: Максимум итераций (защита от зацикливания)

        Returns:
            PathResult с путём или пустым списком
        """
        # Конвертируем в координаты сетки
        start_x, start_y = self.world_to_grid(start[0], start[1])
        end_x, end_y = self.world_to_grid(end[0], end[1])

        # Проверяем границы и проходимость
        if not self._in_bounds(start_x, start_y):
            logger.warning(f"Start position out of bounds: {start}")
            return PathResult(found=False)

        if not self._in_bounds(end_x, end_y):
            logger.warning(f"End position out of bounds: {end}")
            return PathResult(found=False)

        if not self._is_walkable(end_x, end_y):
            # Пробуем найти ближайшую проходимую клетку к цели
            end_x, end_y = self._find_nearest_walkable(end_x, end_y)
            if end_x is None:
                logger.warning(f"No walkable cell near end: {end}")
                return PathResult(found=False)

        if not self._is_walkable(start_x, start_y):
            start_x, start_y = self._find_nearest_walkable(start_x, start_y)
            if start_x is None:
                logger.warning(f"No walkable cell near start: {start}")
                return PathResult(found=False)

        # A* алгоритм
        start_node = PathNode(start_x, start_y)
        end_node = PathNode(end_x, end_y)

        open_set: List[PathNode] = [start_node]
        closed_set: Set[Tuple[int, int]] = set()
        open_dict: Dict[Tuple[int, int], PathNode] = {(start_x, start_y): start_node}

        iterations = 0

        while open_set and iterations < max_iterations:
            iterations += 1

            # Берём узел с минимальной f_cost
            current = heapq.heappop(open_set)
            current_pos = (current.x, current.y)

            # Удаляем из open_dict
            open_dict.pop(current_pos, None)

            # Проверяем достижение цели
            if current.x == end_node.x and current.y == end_node.y:
                path = self._reconstruct_path(current)
                return PathResult(
                    found=True,
                    path=path,
                    cost=current.g_cost,
                    nodes_explored=iterations
                )

            closed_set.add(current_pos)

            # Проверяем соседей
            for dx, dy in self.DIRECTIONS:
                neighbor_x = current.x + dx
                neighbor_y = current.y + dy
                neighbor_pos = (neighbor_x, neighbor_y)

                # Пропускаем если вне границ, непроходимо или уже обработано
                if not self._in_bounds(neighbor_x, neighbor_y):
                    continue
                if not self._is_walkable(neighbor_x, neighbor_y):
                    continue
                if neighbor_pos in closed_set:
                    continue

                # Проверяем диагональное движение (не должно срезать углы)
                if dx != 0 and dy != 0:
                    if not self._is_walkable(current.x + dx, current.y):
                        continue
                    if not self._is_walkable(current.x, current.y + dy):
                        continue

                # Вычисляем стоимость
                move_cost = self.DIAGONAL_COST if (dx != 0 and dy != 0) else self.STRAIGHT_COST
                new_g_cost = current.g_cost + move_cost

                # Проверяем, есть ли узел в open_set
                existing = open_dict.get(neighbor_pos)
                if existing:
                    if new_g_cost < existing.g_cost:
                        # Обновляем путь
                        existing.g_cost = new_g_cost
                        existing.parent = current
                        # Перестраиваем heap
                        heapq.heapify(open_set)
                else:
                    # Создаём новый узел
                    neighbor = PathNode(
                        x=neighbor_x,
                        y=neighbor_y,
                        g_cost=new_g_cost,
                        h_cost=self._heuristic(neighbor_x, neighbor_y, end_x, end_y),
                        parent=current
                    )
                    heapq.heappush(open_set, neighbor)
                    open_dict[neighbor_pos] = neighbor

        logger.warning(f"Path not found after {iterations} iterations")
        return PathResult(found=False, nodes_explored=iterations)

    def _heuristic(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Эвристика расстояния (Diagonal distance)."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        return self.STRAIGHT_COST * (dx + dy) + (self.DIAGONAL_COST - 2 * self.STRAIGHT_COST) * min(dx, dy)

    def _reconstruct_path(self, end_node: PathNode) -> List[Vec3]:
        """Восстанавливает путь от конца к началу."""
        path = []
        current = end_node

        while current:
            world_x, world_y = self.grid_to_world(current.x, current.y)
            height = self._height_map[current.y][current.x] if self._in_bounds(current.x, current.y) else 0.0
            path.append(Vec3(world_x, world_y, height))
            current = current.parent

        path.reverse()
        return path

    def _find_nearest_walkable(self, grid_x: int, grid_y: int, max_radius: int = 10) -> Tuple[Optional[int], Optional[int]]:
        """Находит ближайшую проходимую клетку."""
        for radius in range(1, max_radius + 1):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) == radius or abs(dy) == radius:
                        nx, ny = grid_x + dx, grid_y + dy
                        if self._in_bounds(nx, ny) and self._is_walkable(nx, ny):
                            return nx, ny
        return None, None

    # =========================================================================
    # Вспомогательные методы
    # =========================================================================

    def world_to_grid(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Конвертирует мировые координаты в координаты сетки."""
        grid_x = int((world_x - self.origin_x) / self.cell_size)
        grid_y = int((world_y - self.origin_y) / self.cell_size)
        return grid_x, grid_y

    def grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """Конвертирует координаты сетки в мировые координаты (центр клетки)."""
        world_x = self.origin_x + (grid_x + 0.5) * self.cell_size
        world_y = self.origin_y + (grid_y + 0.5) * self.cell_size
        return world_x, world_y

    def _in_bounds(self, grid_x: int, grid_y: int) -> bool:
        """Проверяет, находится ли клетка в границах сетки."""
        return 0 <= grid_x < self.width and 0 <= grid_y < self.height

    def _is_walkable(self, grid_x: int, grid_y: int) -> bool:
        """Проверяет проходимость клетки (включая динамические препятствия)."""
        if not self._in_bounds(grid_x, grid_y):
            return False
        if (grid_x, grid_y) in self._dynamic_obstacles:
            return False
        return self._grid[grid_y][grid_x]

    def is_walkable_world(self, world_x: float, world_y: float) -> bool:
        """Проверяет проходимость по мировым координатам."""
        grid_x, grid_y = self.world_to_grid(world_x, world_y)
        return self._is_walkable(grid_x, grid_y)

    def get_height_at(self, world_x: float, world_y: float) -> float:
        """Получает высоту поверхности по мировым координатам."""
        grid_x, grid_y = self.world_to_grid(world_x, world_y)
        if self._in_bounds(grid_x, grid_y):
            return self._height_map[grid_y][grid_x]
        return 0.0

    # =========================================================================
    # Отладка
    # =========================================================================

    def get_debug_info(self) -> Dict:
        """Возвращает отладочную информацию."""
        walkable = sum(1 for row in self._grid for cell in row if cell)
        total = self.width * self.height
        return {
            "width": self.width,
            "height": self.height,
            "cell_size": self.cell_size,
            "origin": (self.origin_x, self.origin_y),
            "walkable_cells": walkable,
            "total_cells": total,
            "walkable_percent": (walkable / total * 100) if total > 0 else 0,
            "dynamic_obstacles": len(self._dynamic_obstacles)
        }


# =============================================================================
# Path Smoother
# =============================================================================

class PathSmoother:
    """Сглаживание пути для более естественного движения."""

    @staticmethod
    def smooth_path(
        path: List[Vec3],
        pathfinder: GridPathfinder,
        iterations: int = 2
    ) -> List[Vec3]:
        """
        Сглаживает путь, удаляя лишние точки.

        Args:
            path: Исходный путь
            pathfinder: Pathfinder для проверки проходимости
            iterations: Количество итераций сглаживания

        Returns:
            Сглаженный путь
        """
        if len(path) <= 2:
            return path

        result = path.copy()

        for _ in range(iterations):
            i = 0
            while i < len(result) - 2:
                # Проверяем, можно ли пройти напрямую от i к i+2
                if PathSmoother._has_line_of_sight(result[i], result[i + 2], pathfinder):
                    result.pop(i + 1)
                else:
                    i += 1

        return result

    @staticmethod
    def _has_line_of_sight(start: Vec3, end: Vec3, pathfinder: GridPathfinder) -> bool:
        """Проверяет прямую видимость между двумя точками."""
        dx = end.x - start.x
        dy = end.y - start.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < pathfinder.cell_size:
            return True

        steps = int(distance / (pathfinder.cell_size * 0.5))
        if steps == 0:
            return True

        for i in range(steps + 1):
            t = i / steps
            x = start.x + dx * t
            y = start.y + dy * t
            if not pathfinder.is_walkable_world(x, y):
                return False

        return True


# =============================================================================
# Steering Behaviors (для плавного движения)
# =============================================================================

class SteeringBehaviors:
    """Поведения рулевого управления для плавного следования по пути."""

    @staticmethod
    def seek(
        current_pos: Vec3,
        target_pos: Vec3,
        current_velocity: Vec3,
        max_speed: float,
        max_force: float
    ) -> Vec3:
        """
        Вычисляет силу для движения к цели.

        Args:
            current_pos: Текущая позиция
            target_pos: Целевая позиция
            current_velocity: Текущая скорость
            max_speed: Максимальная скорость
            max_force: Максимальная сила

        Returns:
            Вектор силы
        """
        desired = target_pos - current_pos
        desired_length = desired.length()

        if desired_length > 0:
            desired.normalize()
            desired *= max_speed

        steering = desired - current_velocity
        if steering.length() > max_force:
            steering.normalize()
            steering *= max_force

        return steering

    @staticmethod
    def arrive(
        current_pos: Vec3,
        target_pos: Vec3,
        current_velocity: Vec3,
        max_speed: float,
        max_force: float,
        slow_radius: float = 2.0
    ) -> Vec3:
        """
        Вычисляет силу для плавной остановки у цели.

        Args:
            current_pos: Текущая позиция
            target_pos: Целевая позиция
            current_velocity: Текущая скорость
            max_speed: Максимальная скорость
            max_force: Максимальная сила
            slow_radius: Радиус замедления

        Returns:
            Вектор силы
        """
        desired = target_pos - current_pos
        distance = desired.length()

        if distance > 0:
            desired.normalize()

            # Замедляемся при приближении
            if distance < slow_radius:
                desired *= max_speed * (distance / slow_radius)
            else:
                desired *= max_speed

        steering = desired - current_velocity
        if steering.length() > max_force:
            steering.normalize()
            steering *= max_force

        return steering

    @staticmethod
    def follow_path(
        current_pos: Vec3,
        current_velocity: Vec3,
        path: List[Vec3],
        current_waypoint_index: int,
        max_speed: float,
        max_force: float,
        waypoint_radius: float = 0.5
    ) -> Tuple[Vec3, int]:
        """
        Следует по пути с waypoints.

        Args:
            current_pos: Текущая позиция
            current_velocity: Текущая скорость
            path: Список точек пути
            current_waypoint_index: Индекс текущей точки
            max_speed: Максимальная скорость
            max_force: Максимальная сила
            waypoint_radius: Радиус достижения точки

        Returns:
            Tuple (сила, новый индекс)
        """
        if not path or current_waypoint_index >= len(path):
            return Vec3(0, 0, 0), current_waypoint_index

        target = path[current_waypoint_index]
        distance = (target - current_pos).length()

        # Переходим к следующей точке если достигли текущей
        if distance < waypoint_radius and current_waypoint_index < len(path) - 1:
            current_waypoint_index += 1
            target = path[current_waypoint_index]

        # Используем arrive для последней точки, seek для остальных
        if current_waypoint_index == len(path) - 1:
            steering = SteeringBehaviors.arrive(
                current_pos, target, current_velocity, max_speed, max_force
            )
        else:
            steering = SteeringBehaviors.seek(
                current_pos, target, current_velocity, max_speed, max_force
            )

        return steering, current_waypoint_index
