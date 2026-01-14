"""
AI системы для NPC.

Обрабатывают поведение NPC: патрулирование, преследование, атаки и т.д.
"""

from __future__ import annotations

import random
import math
from typing import List, Optional, Dict, TYPE_CHECKING
from panda3d.core import Vec3
import logging

from nine.core.ecs import System, Entity, ECSWorld
from nine.core.pathfinder import GridPathfinder, SteeringBehaviors

from nine.plugins.npc.sh_components import (
    PositionComponent,
    AIComponent,
    PathfindingComponent,
    CombatComponent,
    FactionComponent,
    NPCInfoComponent,
    AIBehavior,
    AIState,
)

if TYPE_CHECKING:
    from nine.plugins.npc.sv_npc_manager import NPCManager

logger = logging.getLogger(__name__)


# =============================================================================
# AI System — основная логика поведения
# =============================================================================

class AISystem(System):
    """
    Главная AI система. Обновляет состояние и принимает решения.
    """

    required_components = [PositionComponent, AIComponent]
    priority = 10  # Выполняется рано

    def __init__(self, npc_manager: 'NPCManager' = None):
        super().__init__()
        self.npc_manager = npc_manager
        self._think_accumulators: Dict[str, float] = {}

    def update(self, dt: float, entities: List[Entity]) -> None:
        for entity in entities:
            ai = entity.get_component(AIComponent)
            pos = entity.get_component(PositionComponent)

            # Мёртвые NPC не думают
            combat = entity.get_component(CombatComponent)
            if combat and combat.is_dead:
                ai.state = AIState.DEAD
                continue

            # Throttle AI thinking
            entity_id = entity.id
            if entity_id not in self._think_accumulators:
                self._think_accumulators[entity_id] = random.uniform(0, ai.think_interval)

            self._think_accumulators[entity_id] += dt
            if self._think_accumulators[entity_id] < ai.think_interval:
                continue
            self._think_accumulators[entity_id] = 0.0

            # Обновляем AI в зависимости от поведения
            if ai.behavior == AIBehavior.IDLE:
                self._update_idle(entity, ai, pos, dt)
            elif ai.behavior == AIBehavior.PATROL:
                self._update_patrol(entity, ai, pos, dt)
            elif ai.behavior == AIBehavior.HOSTILE:
                self._update_hostile(entity, ai, pos, dt)
            elif ai.behavior == AIBehavior.WANDER:
                self._update_wander(entity, ai, pos, dt)
            elif ai.behavior == AIBehavior.FOLLOW:
                self._update_follow(entity, ai, pos, dt)

    def _update_idle(self, entity: Entity, ai: AIComponent, pos: PositionComponent, dt: float):
        """Idle — стоит на месте, но может реагировать на врагов."""
        ai.state = AIState.IDLE

        # Проверяем наличие врагов
        if self.npc_manager:
            target = self._find_nearest_enemy(entity, ai, pos)
            if target:
                ai.target_entity_id = target.id
                ai.behavior = AIBehavior.HOSTILE
                ai.state = AIState.PURSUING

    def _update_patrol(self, entity: Entity, ai: AIComponent, pos: PositionComponent, dt: float):
        """Patrol — ходит по точкам патруля."""
        if not ai.patrol_points:
            ai.state = AIState.IDLE
            return

        # Проверяем врагов
        if self.npc_manager:
            target = self._find_nearest_enemy(entity, ai, pos)
            if target:
                ai.target_entity_id = target.id
                ai.state = AIState.PURSUING
                self._set_pathfinding_target(entity, target)
                return

        current_point = ai.patrol_points[ai.current_patrol_index]

        # Если достигли точки — ждём
        distance = pos.distance_to(current_point[0], current_point[1])
        if distance < 1.0:
            ai.patrol_timer += ai.think_interval
            ai.state = AIState.IDLE

            if ai.patrol_timer >= ai.patrol_wait_time:
                # Переходим к следующей точке
                ai.patrol_timer = 0.0
                ai.current_patrol_index = (ai.current_patrol_index + 1) % len(ai.patrol_points)
                next_point = ai.patrol_points[ai.current_patrol_index]
                self._set_pathfinding_target_pos(entity, Vec3(*next_point))
        else:
            ai.state = AIState.MOVING
            self._set_pathfinding_target_pos(entity, Vec3(*current_point))

    def _update_hostile(self, entity: Entity, ai: AIComponent, pos: PositionComponent, dt: float):
        """Hostile — атакует врагов."""
        # Если нет цели — ищем
        if not ai.target_entity_id:
            target = self._find_nearest_enemy(entity, ai, pos)
            if target:
                ai.target_entity_id = target.id
            else:
                # Нет врагов — возвращаемся к idle или patrol
                ai.state = AIState.IDLE
                return

        # Получаем цель
        target = self._get_target_entity(ai.target_entity_id)
        if not target:
            ai.target_entity_id = None
            ai.state = AIState.IDLE
            return

        target_pos = target.get_component(PositionComponent)
        if not target_pos:
            ai.target_entity_id = None
            return

        distance = pos.distance_to(target_pos.x, target_pos.y)

        # Проверяем leash radius
        if ai.last_known_target_pos:
            origin = ai.last_known_target_pos
            dist_from_origin = pos.distance_to(origin[0], origin[1])
            if dist_from_origin > ai.leash_radius:
                # Слишком далеко — возвращаемся
                ai.target_entity_id = None
                ai.state = AIState.IDLE
                self._set_pathfinding_target_pos(entity, Vec3(*origin))
                return
        else:
            ai.last_known_target_pos = (pos.x, pos.y, pos.z)

        # В радиусе атаки?
        if distance <= ai.attack_range:
            ai.state = AIState.ATTACKING
            # Атака обрабатывается в CombatAISystem
        else:
            ai.state = AIState.PURSUING
            self._set_pathfinding_target(entity, target)

    def _update_wander(self, entity: Entity, ai: AIComponent, pos: PositionComponent, dt: float):
        """Wander — случайное блуждание."""
        if ai.wander_center is None:
            ai.wander_center = (pos.x, pos.y, pos.z)

        # Проверяем врагов
        if self.npc_manager:
            target = self._find_nearest_enemy(entity, ai, pos)
            if target:
                ai.target_entity_id = target.id
                ai.behavior = AIBehavior.HOSTILE
                return

        ai.wander_timer += ai.think_interval
        if ai.wander_timer >= ai.wander_interval:
            ai.wander_timer = 0.0
            # Выбираем случайную точку
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, ai.wander_radius)
            new_x = ai.wander_center[0] + math.cos(angle) * distance
            new_y = ai.wander_center[1] + math.sin(angle) * distance
            self._set_pathfinding_target_pos(entity, Vec3(new_x, new_y, pos.z))
            ai.state = AIState.MOVING

    def _update_follow(self, entity: Entity, ai: AIComponent, pos: PositionComponent, dt: float):
        """Follow — следует за целью."""
        if not ai.target_entity_id:
            ai.state = AIState.IDLE
            return

        target = self._get_target_entity(ai.target_entity_id)
        if not target:
            ai.target_entity_id = None
            ai.state = AIState.IDLE
            return

        target_pos = target.get_component(PositionComponent)
        if not target_pos:
            return

        distance = pos.distance_to(target_pos.x, target_pos.y)

        # Держим дистанцию
        if distance > 3.0:
            ai.state = AIState.MOVING
            self._set_pathfinding_target(entity, target)
        else:
            ai.state = AIState.IDLE

    # =========================================================================
    # Вспомогательные методы
    # =========================================================================

    def _find_nearest_enemy(self, entity: Entity, ai: AIComponent, pos: PositionComponent) -> Optional[Entity]:
        """Находит ближайшего врага в радиусе агрессии."""
        if not self.npc_manager:
            return None

        faction = entity.get_component(FactionComponent)
        if not faction:
            return None

        nearest = None
        nearest_dist = float('inf')

        # Проверяем игроков
        for player in self.npc_manager.get_players():
            player_pos = player.get("position", {})
            px, py = player_pos.get("x", 0), player_pos.get("y", 0)
            dist = pos.distance_to(px, py)

            if dist <= ai.aggro_radius:
                # Проверяем враждебность
                if faction.hostile_to_players or self._is_enemy_faction(faction, "player"):
                    if dist < nearest_dist:
                        nearest_dist = dist
                        # Создаём временную entity для игрока
                        nearest = self._create_player_entity(player)

        return nearest

    def _is_enemy_faction(self, faction: FactionComponent, target_faction: str) -> bool:
        """Проверяет, враждебна ли фракция."""
        if target_faction in faction.disposition_overrides:
            return faction.disposition_overrides[target_faction] < 0
        # TODO: Проверить глобальные отношения фракций
        return False

    def _get_target_entity(self, entity_id: str) -> Optional[Entity]:
        """Получает entity цели."""
        if not self._world:
            return None
        return self._world.get_entity(entity_id)

    def _set_pathfinding_target(self, entity: Entity, target: Entity) -> None:
        """Устанавливает цель pathfinding на другую entity."""
        pathfinding = entity.get_component(PathfindingComponent)
        target_pos = target.get_component(PositionComponent)

        if pathfinding and target_pos:
            pathfinding.target_position = Vec3(target_pos.x, target_pos.y, target_pos.z)
            pathfinding.needs_repath = True

    def _set_pathfinding_target_pos(self, entity: Entity, target: Vec3) -> None:
        """Устанавливает цель pathfinding на позицию."""
        pathfinding = entity.get_component(PathfindingComponent)
        if pathfinding:
            pathfinding.target_position = target
            pathfinding.needs_repath = True

    def _create_player_entity(self, player_data: dict) -> Entity:
        """Создаёт временную entity для игрока (для targeting)."""
        entity = Entity(player_data.get("uuid", "player"))
        pos = player_data.get("position", {})
        entity.add_component(PositionComponent(
            x=pos.get("x", 0),
            y=pos.get("y", 0),
            z=pos.get("z", 0)
        ))
        return entity


# =============================================================================
# Pathfinding System — движение NPC
# =============================================================================

class PathfindingSystem(System):
    """
    Система навигации. Вычисляет пути и двигает NPC.
    """

    required_components = [PositionComponent, PathfindingComponent]
    priority = 20  # После AI

    def __init__(self, pathfinder: GridPathfinder = None):
        super().__init__()
        self.pathfinder = pathfinder

    def update(self, dt: float, entities: List[Entity]) -> None:
        for entity in entities:
            pos = entity.get_component(PositionComponent)
            pathfinding = entity.get_component(PathfindingComponent)
            ai = entity.get_component(AIComponent)

            # Пропускаем мёртвых
            combat = entity.get_component(CombatComponent)
            if combat and combat.is_dead:
                continue

            # Нужно пересчитать путь?
            if pathfinding.needs_repath and pathfinding.target_position:
                self._calculate_path(entity, pos, pathfinding)

            # Двигаемся по пути
            if pathfinding.current_path:
                self._follow_path(entity, pos, pathfinding, ai, dt)

    def _calculate_path(self, entity: Entity, pos: PositionComponent, pathfinding: PathfindingComponent):
        """Вычисляет путь к цели."""
        pathfinding.needs_repath = False

        if not self.pathfinder:
            # Без pathfinder — идём напрямую
            pathfinding.current_path = [pathfinding.target_position]
            pathfinding.current_waypoint_index = 0
            return

        start = (pos.x, pos.y, pos.z)
        end = (pathfinding.target_position.x, pathfinding.target_position.y, pathfinding.target_position.z)

        result = self.pathfinder.find_path(start, end)
        if result.found:
            pathfinding.current_path = result.path
            pathfinding.current_waypoint_index = 0
            pathfinding.is_stuck = False
        else:
            pathfinding.current_path = []
            logger.debug(f"No path found for entity {entity.id[:8]}")

    def _follow_path(self, entity: Entity, pos: PositionComponent, pathfinding: PathfindingComponent, ai: Optional[AIComponent], dt: float):
        """Следует по пути."""
        if pathfinding.current_waypoint_index >= len(pathfinding.current_path):
            pathfinding.current_path = []
            return

        target = pathfinding.current_path[pathfinding.current_waypoint_index]
        current_pos = Vec3(pos.x, pos.y, pos.z)

        # Вычисляем steering force
        move_speed = ai.move_speed if ai else pathfinding.max_speed

        steering, new_index = SteeringBehaviors.follow_path(
            current_pos,
            pathfinding.velocity,
            pathfinding.current_path,
            pathfinding.current_waypoint_index,
            move_speed,
            pathfinding.max_force,
            pathfinding.waypoint_radius
        )

        pathfinding.current_waypoint_index = new_index

        # Обновляем velocity
        pathfinding.velocity = pathfinding.velocity + steering * dt
        if pathfinding.velocity.length() > move_speed:
            pathfinding.velocity.normalize()
            pathfinding.velocity *= move_speed

        # Обновляем позицию
        new_pos = current_pos + pathfinding.velocity * dt
        pos.x = new_pos.x
        pos.y = new_pos.y
        # Z обновляется отдельно (из heightmap или collision)

        pos.velocity_x = pathfinding.velocity.x
        pos.velocity_y = pathfinding.velocity.y

        # Поворачиваем в направлении движения
        if pathfinding.velocity.length() > 0.1:
            pos.rotation = math.degrees(math.atan2(pathfinding.velocity.y, pathfinding.velocity.x))

        # Проверяем застревание
        if pathfinding.velocity.length() < 0.1:
            pathfinding.stuck_timer += dt
            if pathfinding.stuck_timer > pathfinding.stuck_threshold:
                pathfinding.is_stuck = True
                pathfinding.needs_repath = True
                pathfinding.stuck_timer = 0.0
        else:
            pathfinding.stuck_timer = 0.0

        # Достигли конца пути?
        if pathfinding.current_waypoint_index >= len(pathfinding.current_path):
            pathfinding.current_path = []
            pathfinding.velocity = Vec3(0, 0, 0)
            pos.velocity_x = 0
            pos.velocity_y = 0


# =============================================================================
# Combat AI System — боевые решения
# =============================================================================

class CombatAISystem(System):
    """
    Система боевого AI. Обрабатывает атаки NPC.
    """

    required_components = [AIComponent, CombatComponent, PositionComponent]
    priority = 30  # После pathfinding

    def __init__(self, npc_manager: 'NPCManager' = None):
        super().__init__()
        self.npc_manager = npc_manager

    def update(self, dt: float, entities: List[Entity]) -> None:
        for entity in entities:
            ai = entity.get_component(AIComponent)
            combat = entity.get_component(CombatComponent)
            pos = entity.get_component(PositionComponent)

            if combat.is_dead:
                continue

            # Обновляем кулдаун атаки
            if combat.attack_timer > 0:
                combat.attack_timer -= dt

            # Атакуем если в состоянии атаки
            if ai.state == AIState.ATTACKING and combat.attack_timer <= 0:
                self._perform_attack(entity, ai, combat, pos)

    def _perform_attack(self, entity: Entity, ai: AIComponent, combat: CombatComponent, pos: PositionComponent):
        """Выполняет атаку."""
        if not ai.target_entity_id or not self.npc_manager:
            return

        # Сбрасываем кулдаун
        combat.attack_timer = combat.attack_cooldown

        # Отправляем событие атаки
        self.npc_manager.event_manager.post("npc_attack", {
            "attacker_id": entity.id,
            "target_id": ai.target_entity_id,
            "attack_bonus": combat.attack_bonus,
            "damage_dice": combat.damage_dice,
            "damage_bonus": combat.damage_bonus,
            "damage_type": combat.damage_type,
            "position": {"x": pos.x, "y": pos.y, "z": pos.z}
        })

        logger.debug(f"NPC {entity.id[:8]} attacks {ai.target_entity_id[:8]}")
