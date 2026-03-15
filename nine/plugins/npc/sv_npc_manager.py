"""
Server NPC Manager.

Manages NPC lifecycle: spawn, despawn, update, synchronization.

Optimizations (v0.1.0):
- Spatial partitioning for O(k) neighbor queries
- Async pathfinding to prevent tick blocking
- AI LOD system for distance-based throttling
- Entity pooling for reduced GC pressure

This module now supports the unified ECS architecture, allowing NPCs to be
managed alongside players in a shared ECS world. It can either use its own
ECS world (legacy mode) or share the GameWorld's ECS world (unified mode).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from dataclasses import asdict
import logging

from nine.core.ecs import ECSWorld, Entity, EntityPool, PooledECSWorld, create_entity_from_template
from nine.core.pathfinder import GridPathfinder
from nine.core.spatial import SpatialHash
from nine.core.pathfinder_async import AsyncPathfinder, PathPriority, PathResult
from nine.core.plugins import PluginContext

# Legacy NPC components (for backward compatibility)
from nine.plugins.npc.sh_components import (
    PositionComponent,
    ModelComponent,
    AIComponent,
    PathfindingComponent,
    CombatComponent,
    FactionComponent,
    DialogueComponent,
    InteractionComponent,
    InventoryComponent,
    NPCInfoComponent,
    COMPONENT_REGISTRY,
    AIBehavior,
    AIState,
)

# New unified components (optional import for unified mode)
try:
    from nine.core.components import (
        TransformComponent as UnifiedTransformComponent,
        VelocityComponent as UnifiedVelocityComponent,
        PawnComponent,
        PhysicsComponent as UnifiedPhysicsComponent,
        PhysicsTier,
        HealthComponent as UnifiedHealthComponent,
        AIControllerComponent,
        ModelComponent as UnifiedModelComponent,
        NetworkSyncComponent,
        PawnType,
        AIBehavior as UnifiedAIBehavior,
        AIState as UnifiedAIState,
    )
    UNIFIED_COMPONENTS_AVAILABLE = True
except ImportError:
    UNIFIED_COMPONENTS_AVAILABLE = False

from nine.plugins.npc.sv_npc_ai import AISystem, PathfindingSystem, CombatAISystem, AILODSystem

if TYPE_CHECKING:
    from nine.core.events import EventManager

logger = logging.getLogger(__name__)


class NPCManager:
    """
    Server NPC Manager.

    Responsibilities:
    - Load NPC templates from JSON
    - Spawn/despawn NPCs
    - Update ECS world
    - Synchronize with clients

    Optimizations:
    - Spatial partitioning for fast neighbor queries
    - Async pathfinding on worker threads
    - AI LOD for distance-based throttling
    - Entity pooling for reduced memory pressure

    Supports two modes:
    - Legacy mode: Uses its own ECS world (default)
    - Unified mode: Uses shared ECS world from GameWorld
    """

    # Configuration
    SPATIAL_CELL_SIZE = 15.0        # Spatial hash cell size
    ASYNC_PATHFINDER_WORKERS = 2    # Number of pathfinding threads
    ENTITY_POOL_SIZE = 100          # Initial entity pool size
    ENTITY_POOL_MAX = 500           # Maximum entity pool size

    def __init__(self, context: PluginContext):
        self.context = context
        self.app = context.app
        self.logger = context.logger
        self.event_manager = context.event_manager

        # Flag for unified ECS mode
        self._unified_mode = False
        self._shared_ecs_world: Optional[ECSWorld] = None

        # Optimization systems (initialized in on_load)
        self.spatial_hash: Optional[SpatialHash] = None
        self.async_pathfinder: Optional[AsyncPathfinder] = None
        self.ai_lod_system: Optional[AILODSystem] = None
        self.entity_pool: Optional[EntityPool] = None

        # Position cache for spatial updates
        self._npc_positions: Dict[str, Tuple[float, float]] = {}

    def on_load(self):
        """Initialize when plugin loads."""
        # Initialize optimization systems
        self._init_optimization_systems()

        # ECS world for NPCs (create own if not using shared)
        # Use PooledECSWorld for automatic entity pooling
        self._own_ecs_world = PooledECSWorld(pool=self.entity_pool)

        # Default to using own world
        self.ecs_world = self._own_ecs_world

        # Pathfinder (created after map loads)
        self.pathfinder: Optional[GridPathfinder] = None

        # NPC templates
        self.npc_templates: Dict[str, Dict] = {}

        # Mapping entity_id -> network data
        self._npc_network_data: Dict[str, Dict] = {}

        # Player cache for AI targeting
        self._players_cache: List[Dict] = []

        # Initialize ECS systems
        self._init_systems()

        # Load templates
        self._load_templates()

        # Event subscriptions
        self.event_manager.subscribe("world_loaded", self._on_world_loaded)
        self.event_manager.subscribe("player_update", self._on_player_update)
        self.event_manager.subscribe("dm_npc_spawn", self._on_dm_spawn)
        self.event_manager.subscribe("dm_npc_despawn", self._on_dm_despawn)
        self.event_manager.subscribe("npc_interact_request", self._on_interact_request)
        self.event_manager.subscribe("npc_attack", self._on_npc_attack)

        self.logger.info("NPC Manager loaded (with optimization systems)")

    def _init_optimization_systems(self):
        """Initialize performance optimization systems."""
        # Spatial hash for fast neighbor queries
        self.spatial_hash = SpatialHash(cell_size=self.SPATIAL_CELL_SIZE)
        self.logger.debug(f"Spatial hash initialized (cell_size={self.SPATIAL_CELL_SIZE})")

        # AI LOD system for distance-based throttling
        self.ai_lod_system = AILODSystem()
        self.logger.debug("AI LOD system initialized")

        # Entity pool for reduced GC pressure
        self.entity_pool = EntityPool(
            initial_size=self.ENTITY_POOL_SIZE,
            max_size=self.ENTITY_POOL_MAX
        )
        self.logger.debug(f"Entity pool initialized (size={self.ENTITY_POOL_SIZE})")

    def set_shared_ecs_world(self, ecs_world: ECSWorld) -> None:
        """
        Set a shared ECS world for unified mode.

        When called, NPCs will be created in the shared world alongside players.
        This enables unified physics, rendering, and network sync.

        Args:
            ecs_world: The shared ECS world (typically from GameWorld)
        """
        self._shared_ecs_world = ecs_world
        self._unified_mode = True
        self.ecs_world = ecs_world

        # Migrate systems to shared world
        self._init_systems()

        self.logger.info("NPC Manager switched to unified ECS mode")

    @property
    def is_unified_mode(self) -> bool:
        """Check if using unified ECS mode."""
        return self._unified_mode

    def on_unload(self):
        """Cleanup when plugin unloads."""
        self.event_manager.unsubscribe("world_loaded", self._on_world_loaded)
        self.event_manager.unsubscribe("player_update", self._on_player_update)
        self.event_manager.unsubscribe("dm_npc_spawn", self._on_dm_spawn)
        self.event_manager.unsubscribe("dm_npc_despawn", self._on_dm_despawn)
        self.event_manager.unsubscribe("npc_interact_request", self._on_interact_request)
        self.event_manager.unsubscribe("npc_attack", self._on_npc_attack)

        # Stop async pathfinder
        if self.async_pathfinder:
            self.async_pathfinder.stop()
            self.logger.debug("Async pathfinder stopped")

        # Clear spatial hash
        if self.spatial_hash:
            self.spatial_hash.clear()

        # Clear ECS world
        self.ecs_world.clear()

        self.logger.info("NPC Manager unloaded")

    def _init_systems(self):
        """Initialize ECS systems with optimization support."""
        # AI system with LOD and spatial hash
        # Pass event_manager directly to decouple from NPCManager
        ai_system = AISystem(
            npc_manager=self,  # Kept for backward compatibility
            lod_system=self.ai_lod_system,
            spatial_hash=self.spatial_hash,
            event_manager=self.event_manager
        )
        self.ecs_world.add_system(ai_system)
        self._ai_system = ai_system  # Keep reference for stats

        # Pathfinding system (pathfinder added later)
        pathfinding_system = PathfindingSystem(pathfinder=None)
        self.ecs_world.add_system(pathfinding_system)
        self._pathfinding_system = pathfinding_system

        # Combat AI system
        combat_system = CombatAISystem(
            npc_manager=self,  # Kept for backward compatibility
            event_manager=self.event_manager
        )
        self.ecs_world.add_system(combat_system)

        self.logger.debug("NPC ECS systems initialized (with LOD + spatial hash)")

    def _load_templates(self):
        """Загружает шаблоны NPC из JSON файлов."""
        templates_path = Path(__file__).parent / "data" / "npc_templates.json"

        if templates_path.exists():
            try:
                with open(templates_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.npc_templates = data.get("templates", {})
                    self.logger.info(f"Loaded {len(self.npc_templates)} NPC templates")
            except Exception as e:
                self.logger.error(f"Failed to load NPC templates: {e}")
        else:
            # Создаём дефолтные шаблоны
            self._create_default_templates()

    def _create_default_templates(self):
        """Создаёт дефолтные шаблоны NPC."""
        self.npc_templates = {
            "guard": {
                "display_name": "Стражник",
                "model": "human_male",
                "components": {
                    "AIComponent": {
                        "behavior": "PATROL",
                        "aggro_radius": 8.0,
                        "attack_range": 2.0,
                        "move_speed": 0.6
                    },
                    "CombatComponent": {
                        "hp_max": 22,
                        "hp_current": 22,
                        "armor_class": 16,
                        "attack_bonus": 3,
                        "damage_dice": "1d8",
                        "damage_bonus": 1
                    },
                    "FactionComponent": {
                        "faction_id": "guards",
                        "hostile_to_players": False
                    },
                    "InteractionComponent": {
                        "interaction_prompt": "Поговорить"
                    }
                },
                "living": {
                    "has_needs": True,
                    "has_personality": True,
                    "personality": {
                        "traits": ["brave", "loyal"],
                        "courage": 0.8,
                        "aggression": 0.4
                    },
                    "has_schedule": True,
                    "schedule": [
                        {"hour_start": 6, "hour_end": 22, "activity": "patrolling"},
                        {"hour_start": 22, "hour_end": 6, "activity": "sleeping",
                         "location": [0, -5, 0]}
                    ]
                },
                "tags": ["humanoid", "guard"]
            },
            "goblin": {
                "display_name": "Гоблин",
                "model": "goblin",
                "components": {
                    "AIComponent": {
                        "behavior": "WANDER",
                        "aggro_radius": 5.0,
                        "attack_range": 1.5,
                        "move_speed": 0.7,
                        "wander_radius": 6.0,
                        "wander_interval": 4.0
                    },
                    "CombatComponent": {
                        "hp_max": 7,
                        "hp_current": 7,
                        "armor_class": 15,
                        "attack_bonus": 4,
                        "damage_dice": "1d6",
                        "damage_bonus": 2,
                        "cr": 0.25
                    },
                    "FactionComponent": {
                        "faction_id": "monsters",
                        "hostile_to_players": True
                    },
                    "InventoryComponent": {
                        "loot_table_id": "goblin_loot",
                        "gold": 5
                    }
                },
                "living": {
                    "has_needs": True,
                    "has_personality": True,
                    "personality": {
                        "traits": ["cowardly", "greedy"],
                        "courage": 0.2,
                        "aggression": 0.6,
                        "greed": 0.8
                    }
                },
                "tags": ["humanoid", "monster", "goblinoid"]
            },
            "merchant": {
                "display_name": "Торговец",
                "model": "human_male",
                "components": {
                    "AIComponent": {
                        "behavior": "IDLE",
                        "move_speed": 0.5
                    },
                    "CombatComponent": {
                        "hp_max": 10,
                        "hp_current": 10,
                        "armor_class": 10
                    },
                    "FactionComponent": {
                        "faction_id": "neutral"
                    },
                    "DialogueComponent": {
                        "dialogue_id": "merchant_default",
                        "greeting_text": "Добро пожаловать! Желаете взглянуть на товары?"
                    },
                    "InteractionComponent": {
                        "interaction_prompt": "Торговать"
                    },
                    "InventoryComponent": {
                        "is_merchant": True,
                        "gold": 100
                    }
                },
                "living": {
                    "has_needs": True,
                    "has_personality": True,
                    "personality": {
                        "traits": ["honest", "patient"],
                        "kindness": 0.7,
                        "greed": 0.6
                    },
                    "has_schedule": True,
                    "schedule": [
                        {"hour_start": 8, "hour_end": 20, "activity": "trading"},
                        {"hour_start": 20, "hour_end": 8, "activity": "sleeping",
                         "location": [0, -5, 0]}
                    ]
                },
                "tags": ["humanoid", "merchant", "npc"]
            },
            "skeleton": {
                "display_name": "Скелет",
                "model": "skeleton",
                "components": {
                    "AIComponent": {
                        "behavior": "NEUTRAL",
                        "aggro_radius": 4.0,
                        "attack_range": 1.5,
                        "move_speed": 0.6
                    },
                    "CombatComponent": {
                        "hp_max": 13,
                        "hp_current": 13,
                        "armor_class": 13,
                        "attack_bonus": 4,
                        "damage_dice": "1d6",
                        "damage_bonus": 2,
                        "cr": 0.25
                    },
                    "FactionComponent": {
                        "faction_id": "undead",
                        "hostile_to_players": True
                    }
                },
                "tags": ["undead", "monster"]
            }
        }

        # Сохраняем в файл
        templates_path = Path(__file__).parent / "data" / "npc_templates.json"
        templates_path.parent.mkdir(parents=True, exist_ok=True)

        with open(templates_path, 'w', encoding='utf-8') as f:
            json.dump({"templates": self.npc_templates}, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Created {len(self.npc_templates)} default NPC templates")

    # =========================================================================
    # Публичные методы
    # =========================================================================

    def _get_ground_height(self, x: float, y: float, z_start: float = 100.0) -> float:
        """Find ground height at (x, y) using a collision ray cast."""
        from panda3d.core import (
            CollisionRay, CollisionNode, CollisionHandlerQueue,
            CollisionTraverser, BitMask32
        )

        world = getattr(self.app, 'world', None)
        if not world or not hasattr(world, 'render'):
            return 0.0

        ray = CollisionRay()
        ray.setOrigin(x, y, z_start)
        ray.setDirection(0, 0, -1)

        ray_node = CollisionNode('npc_ground_probe')
        ray_node.addSolid(ray)
        ray_node.setFromCollideMask(BitMask32.bit(2))  # FLOOR_MASK
        ray_node.setIntoCollideMask(BitMask32.allOff())

        ray_np = world.render.attachNewNode(ray_node)
        queue = CollisionHandlerQueue()

        trav = CollisionTraverser()
        trav.addCollider(ray_np, queue)
        trav.traverse(world.render)

        ray_np.removeNode()

        if queue.getNumEntries() > 0:
            queue.sortEntries()
            entry = queue.getEntry(0)
            surface_point = entry.getSurfacePoint(world.render)
            return surface_point.z

        return 0.0  # Fallback

    def spawn_npc(
        self,
        template_id: str,
        x: float,
        y: float,
        z: float,
        rotation: float = 0.0,
        entity_id: Optional[str] = None,
        overrides: Optional[Dict] = None
    ) -> Optional[Entity]:
        """
        Спавнит NPC по шаблону.

        Args:
            template_id: ID шаблона
            x, y, z: Позиция спавна
            rotation: Поворот
            entity_id: Опциональный ID entity
            overrides: Переопределения компонентов

        Returns:
            Созданная entity или None
        """
        # Snap NPC to ground level via ray cast
        ground_z = self._get_ground_height(x, y, z + 50.0)
        if ground_z != 0.0 or z <= 1.0:
            self.logger.info(f"[NPC Spawn] Adjusted z: {z:.1f} -> {ground_z:.1f} (ground level)")
            z = ground_z

        template = self.npc_templates.get(template_id)
        if not template:
            self.logger.warning(f"Unknown NPC template: {template_id}")
            return None

        # Создаём entity
        entity = self.ecs_world.create_entity(entity_id)

        # In unified mode, add unified components for integration with player system
        if self._unified_mode and UNIFIED_COMPONENTS_AVAILABLE:
            self._add_unified_components(entity, template, x, y, z, rotation, overrides)
        else:
            self._add_legacy_components(entity, template, x, y, z, rotation, overrides)

        # Добавляем теги
        for tag in template.get("tags", []):
            entity.add_tag(tag)
        entity.add_tag("npc")
        entity.add_tag("pawn")  # Mark as pawn for unified queries

        # Save network data
        self._update_network_data(entity)

        # Add to spatial hash
        if self.spatial_hash:
            self.spatial_hash.update_entity(entity.id, x, y)
            self._npc_positions[entity.id] = (x, y)

        self.logger.info(f"Spawned NPC '{template_id}' at ({x:.1f}, {y:.1f}, {z:.1f}) [unified={self._unified_mode}]")

        # Apply personality trait modifiers to AI parameters
        living_data = template.get("living", {})
        personality_data = living_data.get("personality", {})
        if personality_data:
            self._apply_trait_modifiers(entity, personality_data)

        # Post spawn event (npc_id for living systems, entity_id for legacy)
        self.event_manager.post("npc_spawned", {
            "entity_id": entity.id,
            "npc_id": entity.id,
            "template_id": template_id,
            "template_data": template,
            "position": {"x": x, "y": y, "z": z, "rotation": rotation}
        })

        return entity

    def _add_legacy_components(
        self,
        entity: Entity,
        template: Dict,
        x: float, y: float, z: float,
        rotation: float,
        overrides: Optional[Dict]
    ) -> None:
        """Add legacy NPC components to entity."""
        # Добавляем NPCInfo
        entity.add_component(NPCInfoComponent(
            template_id=template.get("template_id", ""),
            display_name=template.get("display_name", "NPC"),
            tags=template.get("tags", [])
        ))

        # Добавляем позицию
        entity.add_component(PositionComponent(x=x, y=y, z=z, rotation=rotation))

        # Добавляем модель
        entity.add_component(ModelComponent(model_path=template.get("model", "")))

        # Добавляем компоненты из шаблона
        for comp_name, comp_data in template.get("components", {}).items():
            if comp_name in COMPONENT_REGISTRY:
                # Применяем overrides если есть
                final_data = comp_data.copy()
                if overrides and comp_name in overrides:
                    final_data.update(overrides[comp_name])

                # Конвертируем enum строки
                if comp_name == "AIComponent" and "behavior" in final_data:
                    final_data["behavior"] = AIBehavior[final_data["behavior"]]

                comp_class = COMPONENT_REGISTRY[comp_name]
                try:
                    component = comp_class(**final_data)
                    entity.add_component(component)
                except Exception as e:
                    self.logger.error(f"Failed to create component {comp_name}: {e}")

        # Добавляем Pathfinding если есть AI
        if entity.has_component(AIComponent):
            entity.add_component(PathfindingComponent())

    def _add_unified_components(
        self,
        entity: Entity,
        template: Dict,
        x: float, y: float, z: float,
        rotation: float,
        overrides: Optional[Dict]
    ) -> None:
        """Add unified Pawn components to entity for shared ECS mode."""
        # Core Pawn component
        entity.add_component(PawnComponent(
            pawn_type=PawnType.NPC,
            display_name=template.get("display_name", "NPC"),
            template_id=template.get("template_id", ""),
            tags=template.get("tags", [])
        ))

        # Transform
        entity.add_component(UnifiedTransformComponent(x=x, y=y, z=z, rotation=rotation))

        # Velocity
        entity.add_component(UnifiedVelocityComponent())

        # Model
        entity.add_component(UnifiedModelComponent(
            model_path=template.get("model", ""),
            animation="idle"
        ))

        # Network sync
        entity.add_component(NetworkSyncComponent(needs_full_sync=True))

        # Parse template components
        components_data = template.get("components", {})

        # Physics (SIMPLE tier for NPC — no Panda3D collision nodes, world bounds only)
        ai_data = components_data.get("AIComponent", {})
        entity.add_component(UnifiedPhysicsComponent(
            tier=PhysicsTier.SIMPLE,
            walk_speed=ai_data.get("move_speed", 0.6),
            run_speed=ai_data.get("move_speed", 0.6) * 1.5,
            has_collision=False,  # SIMPLE tier doesn't use Panda3D collision
        ))

        # Health from CombatComponent
        combat_data = components_data.get("CombatComponent", {})
        if combat_data:
            entity.add_component(UnifiedHealthComponent(
                hp_current=combat_data.get("hp_current", combat_data.get("hp_max", 10)),
                hp_max=combat_data.get("hp_max", 10),
                armor_class=combat_data.get("armor_class", 10)
            ))

        # AI Controller
        if ai_data:
            behavior_str = ai_data.get("behavior", "IDLE")
            try:
                behavior = UnifiedAIBehavior[behavior_str]
            except KeyError:
                behavior = UnifiedAIBehavior.IDLE

            entity.add_component(AIControllerComponent(
                behavior=behavior,
                state=UnifiedAIState.IDLE,
                aggro_radius=ai_data.get("aggro_radius", 10.0),
                attack_range=ai_data.get("attack_range", 2.0),
                move_speed=ai_data.get("move_speed", 0.6)
            ))

        # Also add legacy components for backward compatibility with NPC systems
        self._add_legacy_components(entity, template, x, y, z, rotation, overrides)

    def _apply_trait_modifiers(self, entity: Entity, personality_data: dict):
        """Modify AI parameters based on personality traits."""
        ai = entity.get_component(AIComponent)
        if not ai:
            return
        traits = [t.lower() for t in personality_data.get("traits", [])]

        if "brave" in traits:
            ai.aggro_radius *= 1.3
        if "cowardly" in traits:
            ai.aggro_radius *= 0.5
            ai.leash_radius *= 0.5
        if "lazy" in traits:
            ai.move_speed *= 0.7
            ai.patrol_wait_time *= 2.0
        if "patient" in traits:
            ai.patrol_wait_time *= 1.5
        if "curious" in traits:
            ai.wander_radius *= 1.5

        if traits:
            self.logger.debug(f"Applied trait modifiers {traits} to {entity.id[:8]}")

    def despawn_npc(self, entity_id: str) -> bool:
        """
        Remove NPC.

        Args:
            entity_id: Entity ID

        Returns:
            True if removed
        """
        entity = self.ecs_world.get_entity(entity_id)
        if not entity:
            return False

        # Remove from spatial hash
        if self.spatial_hash:
            self.spatial_hash.remove_entity(entity_id)
        self._npc_positions.pop(entity_id, None)

        # Remove from ECS world
        self.ecs_world.remove_entity(entity_id)
        self._npc_network_data.pop(entity_id, None)

        # Cancel any pending path requests
        if self.async_pathfinder:
            self.async_pathfinder.cancel_request(entity_id)

        self.event_manager.post("npc_despawned", {"entity_id": entity_id, "npc_id": entity_id})
        self.logger.info(f"Despawned NPC {entity_id[:8]}")

        return True

    def update(self, dt: float):
        """
        Update NPC world.

        Called from game_server every tick.

        Args:
            dt: Time since last update
        """
        # Update player positions in spatial hash (for AI enemy detection)
        self._update_player_spatial_positions()

        # Update AI system with current player positions
        # This decouples AISystem from NPCManager dependency
        if hasattr(self, '_ai_system'):
            self._ai_system.set_player_positions(self._players_cache)

        # Poll async pathfinding results
        if self.async_pathfinder:
            self._process_pathfinding_results()

        # Update ECS world (AI, pathfinding, combat)
        self.ecs_world.update(dt)

        # Update spatial hash and network data for all NPCs
        for entity in self.ecs_world.get_entities_with_tag("npc"):
            pos = entity.get_component(PositionComponent)
            if pos:
                # Update spatial hash
                if self.spatial_hash:
                    self.spatial_hash.update_entity(entity.id, pos.x, pos.y)
                    self._npc_positions[entity.id] = (pos.x, pos.y)

            # Update network data
            self._update_network_data(entity)

    def _update_player_spatial_positions(self):
        """Update player positions in spatial hash for AI enemy detection."""
        if not self.spatial_hash:
            return

        for player in self._players_cache:
            player_uuid = player.get("uuid", "")
            if not player_uuid:
                continue

            player_pos = player.get("position", {})
            px = player_pos.get("x", 0)
            py = player_pos.get("y", 0)

            self.spatial_hash.update_entity(player_uuid, px, py)

    def _process_pathfinding_results(self):
        """Process completed async pathfinding requests."""
        if not self.async_pathfinder:
            return

        results = self.async_pathfinder.poll_results(max_results=20)

        for result in results:
            entity = self.ecs_world.get_entity(result.entity_id)
            if not entity:
                continue

            pathfinding = entity.get_component(PathfindingComponent)
            if not pathfinding:
                continue

            if result.found:
                pathfinding.current_path = result.path
                pathfinding.current_waypoint_index = 0
                pathfinding.is_stuck = False
            else:
                pathfinding.current_path = []
                self.logger.debug(f"Async path not found for {result.entity_id[:8]}")

    def get_npc_states(self) -> List[Dict]:
        """
        Возвращает состояния всех NPC для синхронизации.

        Returns:
            Список данных NPC (in legacy format for backward compatibility)
        """
        states = list(self._npc_network_data.values())
        if states:
            self.logger.debug(f"[NPC_MANAGER] get_npc_states returning {len(states)} NPCs: {[s.get('entity_id', '')[:8] for s in states]}")
        return states

    def get_npc_pawn_states(self) -> List[Dict]:
        """
        Get NPC states in unified pawn format.

        Returns:
            List of NPC data in unified format (matches player pawn format)
        """
        pawns = []
        for entity in self.ecs_world.get_entities_with_tag("npc"):
            pawn_data = self._serialize_npc_as_pawn(entity)
            if pawn_data:
                pawns.append(pawn_data)
        return pawns

    def _serialize_npc_as_pawn(self, entity: Entity) -> Optional[Dict]:
        """Serialize NPC entity in unified pawn format."""
        # Try unified components first
        if self._unified_mode and UNIFIED_COMPONENTS_AVAILABLE:
            pawn = entity.get_component(PawnComponent)
            transform = entity.get_component(UnifiedTransformComponent)

            if pawn and transform:
                data = {
                    "entity_id": entity.id,
                    "pawn_type": "npc",
                    "display_name": pawn.display_name,
                    "template_id": pawn.template_id,
                    "transform": {
                        "x": transform.x,
                        "y": transform.y,
                        "z": transform.z,
                        "rotation": transform.rotation
                    }
                }

                # Velocity
                velocity = entity.get_component(UnifiedVelocityComponent)
                if velocity:
                    data["velocity"] = {
                        "x": velocity.vx,
                        "y": velocity.vy,
                        "z": velocity.vz
                    }

                # Model
                model = entity.get_component(UnifiedModelComponent)
                if model:
                    data["model"] = model.model_path
                    data["animation"] = model.animation

                # Health
                health = entity.get_component(UnifiedHealthComponent)
                if health:
                    data["hp_current"] = health.hp_current
                    data["hp_max"] = health.hp_max
                    data["is_dead"] = health.is_dead

                # AI state
                ai = entity.get_component(AIControllerComponent)
                if ai:
                    data["ai_state"] = ai.state.name

                return data

        # Fallback to legacy components
        pos = entity.get_component(PositionComponent)
        info = entity.get_component(NPCInfoComponent)
        model = entity.get_component(ModelComponent)
        combat = entity.get_component(CombatComponent)
        ai = entity.get_component(AIComponent)

        if not pos:
            return None

        return {
            "entity_id": entity.id,
            "pawn_type": "npc",
            "display_name": info.display_name if info else "NPC",
            "template_id": info.template_id if info else "",
            "transform": {
                "x": pos.x,
                "y": pos.y,
                "z": pos.z,
                "rotation": pos.rotation
            },
            "velocity": {
                "x": pos.velocity_x,
                "y": pos.velocity_y,
                "z": 0
            },
            "model": model.model_path if model else "",
            "animation": model.current_animation if model else "idle",
            "hp_current": combat.hp_current if combat else 0,
            "hp_max": combat.hp_max if combat else 0,
            "is_dead": combat.is_dead if combat else False,
            "ai_state": ai.state.name if ai else "IDLE"
        }

    def get_players(self) -> List[Dict]:
        """Возвращает кэш данных игроков для AI."""
        return self._players_cache

    def get_npc_entity(self, entity_id: str) -> Optional[Entity]:
        """Получает NPC entity по ID."""
        return self.ecs_world.get_entity(entity_id)

    def get_npcs_in_radius(self, x: float, y: float, radius: float) -> List[Entity]:
        """
        Get NPCs within radius of a point.

        Uses spatial hash for O(k) complexity when available.
        """
        result = []

        if self.spatial_hash:
            # Use spatial hash for fast query
            nearby_ids = self.spatial_hash.get_nearby_entities(x, y, radius)

            for entity_id in nearby_ids:
                entity = self.ecs_world.get_entity(entity_id)
                if entity and entity.has_tag("npc"):
                    # Verify distance (spatial hash is approximate)
                    pos = entity.get_component(PositionComponent)
                    if pos and pos.distance_to(x, y) <= radius:
                        result.append(entity)
        else:
            # Fallback: iterate all (O(n))
            for entity in self.ecs_world.get_entities_with_tag("npc"):
                pos = entity.get_component(PositionComponent)
                if pos and pos.distance_to(x, y) <= radius:
                    result.append(entity)

        return result

    def get_optimization_stats(self) -> Dict:
        """
        Get statistics for all optimization systems.

        Returns:
            Dict with stats from spatial hash, LOD, pathfinding, pool
        """
        stats = {
            "npc_count": len(list(self.ecs_world.get_entities_with_tag("npc"))),
        }

        if self.spatial_hash:
            stats["spatial"] = self.spatial_hash.get_stats()

        if self.ai_lod_system:
            stats["lod"] = self.ai_lod_system.get_stats()

        if self.async_pathfinder:
            stats["pathfinding"] = self.async_pathfinder.get_stats()

        if self.entity_pool:
            stats["pool"] = self.entity_pool.get_stats()

        return stats

    def request_async_path(
        self,
        entity_id: str,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        priority: PathPriority = PathPriority.PATROL
    ) -> int:
        """
        Request an async path calculation.

        Args:
            entity_id: Entity requesting the path
            start: Start position (x, y, z)
            goal: Goal position (x, y, z)
            priority: Path priority

        Returns:
            Request ID or -1 if async pathfinder not available
        """
        if not self.async_pathfinder:
            return -1

        from panda3d.core import Vec3
        return self.async_pathfinder.request_path(
            entity_id=entity_id,
            start=Vec3(*start),
            goal=Vec3(*goal),
            priority=priority
        )

    # =========================================================================
    # Обработчики событий
    # =========================================================================

    def _on_world_loaded(self, data: dict):
        """Handle world load event."""
        # Initialize synchronous pathfinder
        world_bounds = data.get("bounds", (-50, -50, 50, 50))
        self.pathfinder = GridPathfinder(
            cell_size=1.0,
            width=int((world_bounds[2] - world_bounds[0]) / 1.0),
            height=int((world_bounds[3] - world_bounds[1]) / 1.0),
            origin_x=world_bounds[0],
            origin_y=world_bounds[1]
        )

        # Update pathfinder in system
        if self._pathfinding_system:
            self._pathfinding_system.pathfinder = self.pathfinder

        self.logger.info("Sync pathfinder initialized for NPC")

        # Initialize async pathfinder (uses sync pathfinder for actual calculations)
        self.async_pathfinder = AsyncPathfinder(
            pathfinder=self.pathfinder,
            num_workers=self.ASYNC_PATHFINDER_WORKERS
        )
        self.async_pathfinder.start()
        self.logger.info(f"Async pathfinder started ({self.ASYNC_PATHFINDER_WORKERS} workers)")

        # Spawn test NPCs (can be removed in production)
        self._spawn_test_npcs()

    def _spawn_test_npcs(self):
        """Spawn test NPCs for alpha demonstration."""
        # Merchant (IDLE with occasional wander at shop area)
        self.spawn_npc("merchant", x=5.0, y=0.0, z=0.0)

        # Patrol guard #1 (4-point patrol route)
        guard = self.spawn_npc("guard", x=10.0, y=5.0, z=0.0)
        if guard:
            ai = guard.get_component(AIComponent)
            if ai:
                ai.patrol_points = [
                    (10.0, 5.0, 0.0),
                    (15.0, 5.0, 0.0),
                    (15.0, 10.0, 0.0),
                    (10.0, 10.0, 0.0)
                ]

        # Patrol guard #2 (different route, opposite side)
        guard2 = self.spawn_npc("guard", x=-10.0, y=5.0, z=0.0)
        if guard2:
            ai2 = guard2.get_component(AIComponent)
            if ai2:
                ai2.patrol_points = [
                    (-10.0, 5.0, 0.0),
                    (-10.0, 10.0, 0.0),
                    (-5.0, 10.0, 0.0),
                    (-5.0, 5.0, 0.0)
                ]

    def _on_player_update(self, data: dict):
        """Обновляет кэш данных игроков."""
        players = data.get("players", [])
        self._players_cache = players

    def _on_dm_spawn(self, data: dict):
        """Обрабатывает команду DM на спавн NPC."""
        self.logger.info(f"[NPC_MANAGER] Получено событие dm_npc_spawn: {data}")

        template_id = data.get("template_id")
        pos = data.get("position", {})
        if isinstance(pos, (list, tuple)):
            x = pos[0] if len(pos) > 0 else 0
            y = pos[1] if len(pos) > 1 else 0
            z = pos[2] if len(pos) > 2 else 0
            rotation = 0
        else:
            x = pos.get("x", 0)
            y = pos.get("y", 0)
            z = pos.get("z", 0)
            rotation = pos.get("rotation", 0)

        self.logger.info(f"[NPC_MANAGER] Спавним NPC: template={template_id}, pos=({x}, {y}, {z})")

        entity = self.spawn_npc(template_id, x, y, z, rotation)
        if entity:
            self.logger.info(f"[NPC_MANAGER] NPC создан: entity_id={entity.id}")
            # Отправляем подтверждение DM
            self.event_manager.post("dm_npc_spawn_result", {
                "success": True,
                "entity_id": entity.id,
                "template_id": template_id
            })
        else:
            self.logger.error(f"[NPC_MANAGER] Не удалось создать NPC: template={template_id}")

    def _on_dm_despawn(self, data: dict):
        """Обрабатывает команду DM на деспавн NPC."""
        entity_id = data.get("entity_id")
        success = self.despawn_npc(entity_id)
        self.event_manager.post("dm_npc_despawn_result", {
            "success": success,
            "entity_id": entity_id
        })

    def _on_interact_request(self, data: dict):
        """Обрабатывает запрос на взаимодействие с NPC."""
        entity_id = data.get("npc_id")
        player_id = data.get("player_id")
        interaction_type = data.get("interaction")

        entity = self.ecs_world.get_entity(entity_id)
        if not entity:
            return

        interaction = entity.get_component(InteractionComponent)
        if not interaction or not interaction.is_interactable:
            return

        # Обрабатываем разные типы взаимодействия
        if interaction_type == "talk":
            dialogue = entity.get_component(DialogueComponent)
            if dialogue:
                self.event_manager.post("npc_dialogue_start", {
                    "npc_id": entity_id,
                    "player_id": player_id,
                    "dialogue_id": dialogue.dialogue_id
                })

        elif interaction_type == "trade":
            inventory = entity.get_component(InventoryComponent)
            if inventory and inventory.is_merchant:
                self.event_manager.post("npc_trade_open", {
                    "npc_id": entity_id,
                    "player_id": player_id,
                    "inventory": inventory.items,
                    "gold": inventory.gold
                })

    def _on_npc_attack(self, data: dict):
        """Обрабатывает атаку NPC (для расчёта урона)."""
        # TODO: Интеграция с боевой системой D&D
        attacker_id = data.get("attacker_id")
        target_id = data.get("target_id")

        self.logger.debug(f"NPC attack: {attacker_id[:8]} -> {target_id[:8]}")

        # Отправляем событие для синхронизации с клиентами
        self.event_manager.post("npc_combat_action", {
            "npc_id": attacker_id,
            "action": "attack",
            "target_id": target_id,
            "damage_dice": data.get("damage_dice"),
            "damage_bonus": data.get("damage_bonus")
        })

    # =========================================================================
    # Вспомогательные методы
    # =========================================================================

    def _update_network_data(self, entity: Entity):
        """Обновляет данные NPC для сетевой синхронизации."""
        pos = entity.get_component(PositionComponent)
        model = entity.get_component(ModelComponent)
        info = entity.get_component(NPCInfoComponent)
        combat = entity.get_component(CombatComponent)
        ai = entity.get_component(AIComponent)

        faction = entity.get_component(FactionComponent)
        interaction = entity.get_component(InteractionComponent)
        inventory = entity.get_component(InventoryComponent)

        data = {
            "entity_id": entity.id,
            "template_id": info.template_id if info else "",
            "display_name": info.display_name if info else "NPC",
            "position": {
                "x": pos.x if pos else 0,
                "y": pos.y if pos else 0,
                "z": pos.z if pos else 0,
                "rotation": pos.rotation if pos else 0
            },
            "velocity": {
                "x": pos.velocity_x if pos else 0,
                "y": pos.velocity_y if pos else 0
            },
            "model": model.model_path if model else "",
            "animation": model.current_animation if model else "idle",
            "hp_current": combat.hp_current if combat else 0,
            "hp_max": combat.hp_max if combat else 0,
            "is_dead": combat.is_dead if combat else False,
            "ai_state": ai.state.name if ai else "IDLE",
            "interactions": [it.name.lower() for it in interaction.interactions] if interaction else ["talk"],
            "hostile": faction.hostile_to_players if faction else False,
            "is_merchant": inventory.is_merchant if inventory else False,
        }

        self._npc_network_data[entity.id] = data
        self.logger.debug(f"[NPC_MANAGER] Updated network data for {entity.id[:8]}: pos=({data['position']['x']:.1f}, {data['position']['y']:.1f}), name={data['display_name']}")
