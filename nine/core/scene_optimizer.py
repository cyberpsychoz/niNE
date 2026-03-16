"""
Scene Optimizer - оптимизация рендеринга для больших карт.

Реализует:
- Flatten (объединение геометрии для уменьшения draw calls)
- Distance Culling (скрытие далеких объектов)
- LOD (Level of Detail) - разная детализация на разных дистанциях
- Frustum Culling оптимизации
- Spatial Partitioning для больших миров
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto

from panda3d.core import (
    NodePath, LODNode, FadeLODNode,
    Point3, Vec3, LPoint3f,
    BitMask32, BoundingSphere,
    RenderState, ColorAttrib, TransparencyAttrib,
    PStatClient,
)

logger = logging.getLogger(__name__)


class CullMode(Enum):
    """Режимы отсечения."""
    NONE = auto()           # Без отсечения
    DISTANCE = auto()       # По дистанции
    FRUSTUM = auto()        # По фрустуму камеры (Panda3D по умолчанию)
    HYBRID = auto()         # Комбинированный


@dataclass
class CullZone:
    """Зона отсечения для группы объектов."""
    name: str
    center: Point3
    radius: float
    objects: List[NodePath] = field(default_factory=list)
    is_visible: bool = True
    last_distance: float = 0.0


@dataclass
class LODSettings:
    """Настройки LOD."""
    high_distance: float = 50.0      # До этой дистанции - высокая детализация
    medium_distance: float = 150.0   # До этой дистанции - средняя
    low_distance: float = 300.0      # До этой - низкая
    cull_distance: float = 500.0     # Дальше - скрываем


class SceneOptimizer:
    """
    Оптимизатор сцены для больших карт.

    Использование:
        optimizer = SceneOptimizer(base)
        optimizer.optimize_map(map_node)
        optimizer.setup_distance_culling(camera_node, render)
    """

    def __init__(self, base, lod_settings: Optional[LODSettings] = None):
        """
        Args:
            base: ShowBase instance
            lod_settings: Настройки LOD (опционально)
        """
        self.base = base
        self.lod = lod_settings or LODSettings()

        # Зоны для spatial partitioning
        self._zones: Dict[str, CullZone] = {}

        # Отслеживаемые объекты для distance culling
        self._tracked_objects: Dict[int, NodePath] = {}
        self._hidden_objects: Set[int] = set()

        # Камера для расчёта дистанций
        self._camera: Optional[NodePath] = None

        # Статистика
        self._stats = {
            "total_objects": 0,
            "visible_objects": 0,
            "culled_objects": 0,
            "draw_calls_saved": 0,
        }

        # Задача обновления culling
        self._cull_task = None
        self._cull_interval = 0.1  # Обновлять каждые 100мс

        logger.info("SceneOptimizer initialized")

    # =========================================================================
    # Flatten (объединение геометрии)
    # =========================================================================

    def optimize_map(self, map_node: NodePath, aggressive: bool = True) -> dict:
        """
        Оптимизирует карту объединением геометрии.

        Args:
            map_node: Корневой узел карты
            aggressive: True для максимальной оптимизации (flattenStrong)

        Returns:
            Статистика оптимизации
        """
        if not map_node:
            return {"error": "No map node provided"}

        # Считаем до оптимизации
        geoms_before = self._count_geoms(map_node)
        nodes_before = self._count_nodes(map_node)

        logger.info(f"[Optimizer] Before: {nodes_before} nodes, {geoms_before} geoms")

        # Применяем оптимизации
        if aggressive:
            # flattenStrong объединяет всю геометрию в минимум draw calls
            # НО: убивает возможность скрывать отдельные объекты
            # Поэтому делаем это умнее - по группам
            self._flatten_by_groups(map_node)
        else:
            # flattenMedium - более мягкая оптимизация
            map_node.flattenMedium()

        # Считаем после оптимизации
        geoms_after = self._count_geoms(map_node)
        nodes_after = self._count_nodes(map_node)

        stats = {
            "nodes_before": nodes_before,
            "nodes_after": nodes_after,
            "nodes_reduced": nodes_before - nodes_after,
            "geoms_before": geoms_before,
            "geoms_after": geoms_after,
            "geoms_reduced": geoms_before - geoms_after,
            "reduction_percent": (1 - geoms_after / max(geoms_before, 1)) * 100,
        }

        logger.info(
            f"[Optimizer] After: {nodes_after} nodes, {geoms_after} geoms "
            f"(reduced {stats['reduction_percent']:.1f}%)"
        )

        return stats

    def _flatten_by_groups(self, map_node: NodePath):
        """
        Объединяет геометрию по группам для сохранения возможности culling.

        Стратегия:
        - Объекты с одинаковым материалом/текстурой объединяем
        - Сохраняем крупные структуры отдельно для culling
        """
        # Находим все дочерние узлы первого уровня (обычно это группы объектов)
        children = map_node.getChildren()

        if children.getNumPaths() == 0:
            # Если нет дочерних - flatten всё
            map_node.flattenStrong()
            return

        # Для каждой группы делаем отдельный flatten
        for child in children:
            # Пропускаем узлы освещения и камер
            if child.getName().lower() in ('lights', 'cameras', 'collision'):
                continue

            # Flatten группу
            child.flattenStrong()

        logger.info(f"[Optimizer] Flattened {children.getNumPaths()} groups")

    def _count_geoms(self, node: NodePath) -> int:
        """Считает количество Geom в узле."""
        count = 0
        for geom_node in node.findAllMatches("**/+GeomNode"):
            gn = geom_node.node()
            count += gn.getNumGeoms()
        return count

    def _count_nodes(self, node: NodePath) -> int:
        """Считает количество узлов."""
        return len(node.findAllMatches("**"))

    # =========================================================================
    # Distance Culling
    # =========================================================================

    def setup_distance_culling(
        self,
        camera: NodePath,
        scene_root: NodePath,
        cull_distance: Optional[float] = None,
        update_interval: float = 0.1
    ):
        """
        Настраивает систему distance culling.

        Args:
            camera: Узел камеры
            scene_root: Корень сцены для отслеживания
            cull_distance: Дистанция отсечения (если не задана - из LODSettings)
            update_interval: Интервал обновления в секундах
        """
        self._camera = camera
        self._cull_interval = update_interval

        if cull_distance:
            self.lod.cull_distance = cull_distance

        # Собираем все объекты для отслеживания
        self._collect_cullable_objects(scene_root)

        # Запускаем задачу обновления
        if self._cull_task:
            self.base.taskMgr.remove(self._cull_task)

        self._cull_task = self.base.taskMgr.doMethodLater(
            self._cull_interval,
            self._update_culling_task,
            "distance-culling-update"
        )

        logger.info(
            f"[Optimizer] Distance culling enabled: "
            f"{len(self._tracked_objects)} objects, "
            f"cull at {self.lod.cull_distance}m"
        )

    def _collect_cullable_objects(self, root: NodePath, min_size: float = 1.0):
        """
        Собирает объекты для culling.

        Args:
            root: Корневой узел
            min_size: Минимальный размер объекта для отслеживания
        """
        self._tracked_objects.clear()
        self._hidden_objects.clear()

        # Ищем все узлы с геометрией
        for node in root.findAllMatches("**/+GeomNode"):
            # Пропускаем слишком мелкие объекты
            bounds = node.getBounds()
            if bounds.isEmpty():
                continue

            # Сохраняем для отслеживания
            obj_id = id(node)
            self._tracked_objects[obj_id] = node

        self._stats["total_objects"] = len(self._tracked_objects)

    def _update_culling_task(self, task):
        """Задача обновления distance culling."""
        if not self._camera:
            return task.again

        camera_pos = self._camera.getPos(self.base.render)
        cull_dist_sq = self.lod.cull_distance ** 2

        visible_count = 0
        culled_count = 0

        for obj_id, node in self._tracked_objects.items():
            if node.isEmpty():
                continue

            # Расстояние до объекта
            obj_pos = node.getPos(self.base.render)
            dist_sq = (obj_pos - camera_pos).lengthSquared()

            should_be_visible = dist_sq < cull_dist_sq
            is_currently_hidden = obj_id in self._hidden_objects

            if should_be_visible and is_currently_hidden:
                # Показываем
                node.show()
                self._hidden_objects.discard(obj_id)
                visible_count += 1
            elif not should_be_visible and not is_currently_hidden:
                # Скрываем
                node.hide()
                self._hidden_objects.add(obj_id)
                culled_count += 1
            elif should_be_visible:
                visible_count += 1
            else:
                culled_count += 1

        self._stats["visible_objects"] = visible_count
        self._stats["culled_objects"] = culled_count

        return task.again

    def set_cull_distance(self, distance: float):
        """Устанавливает дистанцию отсечения."""
        self.lod.cull_distance = distance
        logger.info(f"[Optimizer] Cull distance set to {distance}m")

    # =========================================================================
    # LOD (Level of Detail)
    # =========================================================================

    def create_lod_node(
        self,
        name: str,
        high_model: NodePath,
        medium_model: Optional[NodePath] = None,
        low_model: Optional[NodePath] = None
    ) -> NodePath:
        """
        Создает LOD узел с разными уровнями детализации.

        Args:
            name: Имя узла
            high_model: Модель высокой детализации
            medium_model: Модель средней детализации (опционально)
            low_model: Модель низкой детализации (опционально)

        Returns:
            NodePath с LOD узлом
        """
        lod_node = LODNode(name)
        lod_np = NodePath(lod_node)

        # Добавляем уровни детализации
        # Формат: addSwitch(far_distance, near_distance)

        if high_model:
            high_model.reparentTo(lod_np)
            lod_node.addSwitch(self.lod.high_distance, 0)

        if medium_model:
            medium_model.reparentTo(lod_np)
            lod_node.addSwitch(self.lod.medium_distance, self.lod.high_distance)
        elif high_model:
            # Если нет medium - используем high дольше
            pass

        if low_model:
            low_model.reparentTo(lod_np)
            lod_node.addSwitch(self.lod.low_distance, self.lod.medium_distance)

        return lod_np

    def create_fade_lod_node(
        self,
        name: str,
        models: List[Tuple[NodePath, float]],
        fade_time: float = 0.5
    ) -> NodePath:
        """
        Создает LOD с плавным переходом между уровнями.

        Args:
            name: Имя узла
            models: Список кортежей (модель, дистанция)
            fade_time: Время перехода

        Returns:
            NodePath с FadeLOD узлом
        """
        lod_node = FadeLODNode(name)
        lod_node.setFadeTime(fade_time)
        lod_np = NodePath(lod_node)

        prev_dist = 0
        for model, distance in sorted(models, key=lambda x: x[1]):
            model.reparentTo(lod_np)
            lod_node.addSwitch(distance, prev_dist)
            prev_dist = distance

        return lod_np

    # =========================================================================
    # Spatial Partitioning (Zones)
    # =========================================================================

    def create_zone(self, name: str, center: Point3, radius: float) -> CullZone:
        """
        Создает зону для пространственного разделения.

        Args:
            name: Имя зоны
            center: Центр зоны
            radius: Радиус зоны

        Returns:
            Созданная зона
        """
        zone = CullZone(name=name, center=center, radius=radius)
        self._zones[name] = zone
        return zone

    def add_to_zone(self, zone_name: str, node: NodePath):
        """Добавляет объект в зону."""
        if zone_name in self._zones:
            self._zones[zone_name].objects.append(node)

    def update_zone_visibility(self, camera_pos: Point3):
        """
        Обновляет видимость зон на основе позиции камеры.

        Args:
            camera_pos: Позиция камеры
        """
        for zone in self._zones.values():
            # Дистанция до центра зоны
            dist = (zone.center - camera_pos).length()
            zone.last_distance = dist

            # Зона видима если камера в пределах радиуса + буфер
            should_be_visible = dist < (zone.radius + self.lod.cull_distance)

            if should_be_visible != zone.is_visible:
                zone.is_visible = should_be_visible
                for obj in zone.objects:
                    if should_be_visible:
                        obj.show()
                    else:
                        obj.hide()

    # =========================================================================
    # Статистика и отладка
    # =========================================================================

    def get_stats(self) -> dict:
        """Возвращает статистику оптимизации."""
        return self._stats.copy()

    def enable_pstats(self):
        """Включает PStats для профилирования."""
        PStatClient.connect()
        logger.info("[Optimizer] PStats enabled")

    def cleanup(self):
        """Очистка ресурсов."""
        if self._cull_task:
            self.base.taskMgr.remove(self._cull_task)
            self._cull_task = None

        self._tracked_objects.clear()
        self._hidden_objects.clear()
        self._zones.clear()

        logger.info("[Optimizer] Cleaned up")


# Глобальный оптимизатор (опционально)
_optimizer: Optional[SceneOptimizer] = None


def get_optimizer(base=None) -> Optional[SceneOptimizer]:
    """Возвращает глобальный оптимизатор."""
    global _optimizer
    if _optimizer is None and base:
        _optimizer = SceneOptimizer(base)
    return _optimizer
