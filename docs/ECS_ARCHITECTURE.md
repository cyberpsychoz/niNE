# Unified ECS Architecture

**Последнее обновление:** 2026-03-15 (ECS Unification Phase 1-3)

## Overview

niNE uses a Unified Entity-Component-System (ECS) architecture where **players and NPCs share the same `PooledECSWorld`**. This provides:

- **Unified Physics** - All pawns use the same PhysicsSystem (FULL tier for players, SIMPLE tier for NPC)
- **World Boundaries** - `WorldBoundsComponent` with kill plane prevents entities escaping to infinity
- **Single Component Set** - All components defined in `nine/core/components.py`
- **ECS Player Queries** - AISystem finds players via `PawnComponent(pawn_type=PLAYER)` — no NPCManager coupling
- **Code Reuse** - Same systems process both players and NPCs
- **Entity Pooling** - `PooledECSWorld` reduces GC pressure for 300+ NPC
- **flush()** - `ECSWorld.flush()` makes entities queryable immediately after creation

---

## Architecture Diagram

```
                    +-----------------------+
                    |      GameServer       |
                    +----------+------------+
                               |
              +----------------+----------------+
              |                                 |
    +---------v---------+           +-----------v-----------+
    |     GameWorld     |           |     NPCManager        |
    |  (Player entities)|           |   (NPC entities)      |
    +--------+----------+           +-----------+-----------+
             |                                  |
             |     +------------------+         |
             +---->|   ECSWorld       |<--------+
                   | (shared)         |
                   +--------+---------+
                            |
            +---------------+---------------+
            |               |               |
    +-------v------+ +------v------+ +------v-------+
    | PhysicsSystem| | AISystem    | |NetworkSync   |
    +--------------+ +-------------+ +--------------+
```

---

## Core Files

| File | Description |
|------|-------------|
| `nine/core/ecs.py` | ECS core: Entity, Component, ECSWorld, PooledECSWorld, EntityPool, `flush()` |
| `nine/core/components.py` | **ALL** unified components (players + NPC + living world + combat) |
| `nine/core/systems.py` | Systems: PhysicsSystem (FULL/SIMPLE tiers), InputSystem, AnimationSystem, NetworkSyncSystem |
| `nine/core/world.py` | GameWorld with PooledECSWorld, PhysicsSystem, WorldBoundsComponent |
| `nine/core/spatial.py` | SpatialHash for O(k) neighbor queries (tracks both players and NPC) |
| `nine/plugins/npc/sh_components.py` | **Re-export shim** — imports from core, provides legacy aliases |
| `nine/plugins/npc/sv_npc_manager.py` | NPC manager with unified mode (shared ECS world) |
| `nine/plugins/npc/sv_npc_ai.py` | AISystem — queries players from ECS, writes VelocityComponent |

---

## Components (`nine/core/components.py`)

### Key Enums

| Enum | Values | Used by |
|------|--------|---------|
| `PawnType` | PLAYER, NPC, CREATURE | PawnComponent |
| `AIBehavior` | IDLE, NEUTRAL, PATROL, HOSTILE, FOLLOW, FLEE, SCHEDULE, WANDER | AIComponent |
| `AIState` | IDLE, MOVING, ATTACKING, PURSUING, FLEEING, INTERACTING, DEAD, IN_COMBAT | AIComponent |
| `PhysicsTier` | FULL, SIMPLE, NONE | PhysicsComponent |
| `InteractionType` | TALK, TRADE, ATTACK, LOOT | InteractionComponent |
| `PersonalityTrait` | BRAVE, KIND, COWARDLY, GREEDY... (string values) | PersonalityComponent |
| `Activity` | IDLE, SLEEPING, EATING, WORKING... (string values) | ScheduleComponent |
| `MemoryType` | PLAYER_HELPED, PLAYER_ATTACKED... (string values) | MemoryComponent |

### Component Categories

**Transform & Movement:**
- `TransformComponent` — x, y, z, rotation + velocity_x/y/z for interpolation + `get_pos()`/`set_pos()` Vec3 compat
- `VelocityComponent` — vx, vy, vz + `speed_horizontal()`, `speed()`

**Identity & Physics:**
- `PawnComponent` — pawn_type, display_name, owner_id, template_id
- `PhysicsComponent` — **tier** (FULL/SIMPLE/NONE), walk_speed (0.8), run_speed (1.6), collision, gravity
- `FactionComponent` — faction_id, hostile_to_players, disposition_overrides

**Health & Combat:**
- `HealthComponent` — hp_current/max, armor_class, temp_hp, `take_damage()`/`heal()`
- `CombatStatsComponent` — attack_bonus, damage_dice, saves, CR (also aliased as `CombatComponent`)
- `CombatSessionComponent` — turn-based state: initiative, action economy, conditions, concentration
- `TargetableComponent` — target selection state

**AI & Pathfinding:**
- `AIComponent` — behavior, state, aggro/leash/attack radius, patrol, wander, LOD level
- `PathfindingComponent` — Vec3-based path, steering (velocity, max_speed, max_force)
- `AIControllerComponent` — DEPRECATED (kept for backward compat)

**NPC Info:**
- `NPCInfoComponent` — template_id, display_name, title, is_unique, is_essential
- `InteractionComponent` — interaction types (enum list), prompt, radius
- `DialogueComponent` — dialogue_id, flags, greeting, partner tracking

**Living World (with full methods):**
- `NeedsComponent` — hunger, energy, social, safety + `update()`, `eat()`, `sleep()`, `most_urgent_need`
- `PersonalityComponent` — traits, chattiness, aggression + `has_trait()`, `get_reaction_modifier()`
- `ScheduleComponent` — typed ScheduleEntry list + `get_activity_for_hour()`, `add_entry()`
- `RelationshipsComponent` — per-entity disposition/trust + `modify_disposition()`, `is_hostile_to()`
- `MemoryComponent` — memories list + `add_memory()`, `get_memories_about()`, `decay_memories()`

**World:**
- `WorldBoundsComponent` — min/max x/y/z, kill plane at min_z
- `WorldObjectComponent` — static/pickup/interactive objects

**Network:**
- `NetworkSyncComponent` — sync flags, interpolation data

### Physics Tiers

| Tier | Entities | What it does | Cost |
|------|----------|-------------|------|
| FULL | Players, boss NPC | Panda3D CollisionSphere + Pusher + ground ray | ~0.2ms/entity |
| SIMPLE | Regular NPC | Velocity → position, friction, world bounds clamp, periodic ground ray | ~0.005ms/entity |
| NONE | Sleeping/distant NPC | Skipped entirely | 0 |

@dataclass
class HealthComponent(Component):
    """Health and death state"""
    hp_current: int = 10
    hp_max: int = 10
    is_dead: bool = False
```

### Control Components

```python
@dataclass
class InputComponent(Component):
    """Player input state"""
    keys: Dict[str, bool] = field(default_factory=dict)
    camera_yaw: float = 0.0

@dataclass
class AIControllerComponent(Component):
    """AI behavior for NPCs"""
    behavior: str = "IDLE"         # AIBehavior value
    state: str = "IDLE"            # AIState value
    target_entity_id: Optional[str] = None
    aggro_radius: float = 10.0
    attack_range: float = 1.5
    move_speed: float = 1.5
```

### Rendering & Network

```python
@dataclass
class ModelComponent(Component):
    """Visual representation"""
    model_path: str = "human_male"
    animation: str = "idle"
    scale: float = 1.0

@dataclass
class NetworkSyncComponent(Component):
    """Network synchronization flags"""
    sync_position: bool = True
    sync_animation: bool = True
    is_dirty: bool = False
    last_sync_time: float = 0.0
```

---

## Systems (`nine/core/systems.py`)

### PhysicsSystem

Handles physics for all pawns with `PhysicsComponent`.

```python
class PhysicsSystem:
    def update(self, world: ECSWorld, dt: float):
        for entity in world.query(PawnComponent, TransformComponent, PhysicsComponent):
            physics = entity.get_component(PhysicsComponent)
            transform = entity.get_component(TransformComponent)
            velocity = entity.get_component(VelocityComponent)

            if velocity:
                # Apply velocity
                transform.x += velocity.vx * dt
                transform.y += velocity.vy * dt
                transform.z += velocity.vz * dt

            # Collision checks, gravity, etc.
```

### AISystem

Processes AI behaviors for NPCs.

```python
class AISystem:
    def update(self, world: ECSWorld, dt: float):
        for entity in world.query(PawnComponent, AIControllerComponent, TransformComponent):
            ai = entity.get_component(AIControllerComponent)

            if ai.behavior == "HOSTILE":
                self._process_hostile_ai(entity, world, dt)
            elif ai.behavior == "PATROL":
                self._process_patrol_ai(entity, world, dt)
            # etc.
```

### AnimationSystem

Determines animation state based on velocity and actions.

```python
class AnimationSystem:
    def update(self, world: ECSWorld, dt: float):
        for entity in world.query(PawnComponent, ModelComponent, VelocityComponent):
            model = entity.get_component(ModelComponent)
            velocity = entity.get_component(VelocityComponent)

            speed = (velocity.vx**2 + velocity.vy**2) ** 0.5
            if speed < 0.1:
                model.animation = "idle"
            elif speed < 2.0:
                model.animation = "walk_forward"
            else:
                model.animation = "run_forward"
```

### NetworkSyncSystem

Generates unified world_state for network broadcast.

```python
class NetworkSyncSystem:
    def get_world_state(self, world: ECSWorld) -> dict:
        pawns = []
        for entity in world.query(PawnComponent, TransformComponent):
            pawns.append(self._serialize_pawn(entity))
        return {"pawns": pawns}

    def _serialize_pawn(self, entity: Entity) -> dict:
        pawn = entity.get_component(PawnComponent)
        transform = entity.get_component(TransformComponent)
        return {
            "entity_id": entity.id,
            "pawn_type": pawn.pawn_type,
            "display_name": pawn.display_name,
            "transform": {
                "x": transform.x, "y": transform.y, "z": transform.z,
                "rotation": transform.rotation
            },
            # ... other fields
        }
```

---

## ECS World (`nine/core/ecs.py`)

### Creating Entities

```python
from nine.core.ecs import ECSWorld
from nine.core.components import TransformComponent, PawnComponent

world = ECSWorld()

# Create entity
entity = world.create_entity("player_1")

# Add components
entity.add_component(TransformComponent(x=10, y=20, z=1))
entity.add_component(PawnComponent(pawn_type="player", display_name="Hero"))

# Add tags
entity.add_tag("pawn")
entity.add_tag("player")
```

### Querying Entities

```python
# Query by components
for entity in world.query(PawnComponent, TransformComponent):
    pawn = entity.get_component(PawnComponent)
    transform = entity.get_component(TransformComponent)
    print(f"{pawn.display_name} at ({transform.x}, {transform.y})")

# Query by tag
for entity in world.get_entities_with_tag("npc"):
    print(entity.id)

# Get by ID
entity = world.get_entity("player_1")
```

### Removing Entities

```python
world.remove_entity("player_1")

# Process pending removals
world.update(0.016)
```

---

## Integration

### GameWorld (Players)

```python
# nine/core/world.py
class GameWorld:
    def __init__(self):
        self.ecs_world = ECSWorld()

    def add_player(self, client_id, name, position):
        player = Player(client_id, name, position)
        player.entity = self._create_player_entity(client_id, name, position)
        return player

    def _create_player_entity(self, client_id, name, position):
        entity = self.ecs_world.create_entity(f"player_{client_id}")
        entity.add_component(PawnComponent(pawn_type="player", display_name=name, owner_id=client_id))
        entity.add_component(TransformComponent(x=position[0], y=position[1], z=position[2]))
        entity.add_component(PhysicsComponent(has_collision=True))
        entity.add_component(HealthComponent(hp_current=100, hp_max=100))
        entity.add_tag("pawn")
        entity.add_tag("player")
        return entity

    def get_ecs_world(self) -> ECSWorld:
        return self.ecs_world
```

### NPCManager (NPCs)

```python
# nine/plugins/npc/sv_npc_manager.py
class NPCManager:
    def __init__(self):
        self.ecs_world = ECSWorld()  # Own world (legacy mode)
        self._unified_mode = False
        self._shared_ecs_world = None

    def set_shared_ecs_world(self, ecs_world: ECSWorld):
        """Enable unified mode with shared ECS world"""
        self._shared_ecs_world = ecs_world
        self._unified_mode = True

    @property
    def ecs_world(self) -> ECSWorld:
        if self._unified_mode and self._shared_ecs_world:
            return self._shared_ecs_world
        return self._own_ecs_world
```

### GameServer (Unified Mode)

```python
# nine/server/game_server.py
class GameServer:
    def _setup_unified_ecs(self):
        """Share ECS world between GameWorld and NPCManager"""
        if self.world and self.npc_manager:
            ecs_world = self.world.get_ecs_world()
            self.npc_manager.set_shared_ecs_world(ecs_world)

    def _get_unified_world_state(self):
        """Build unified world state with all pawns"""
        world_state = {
            "pawns": [],
            "players": [],  # Legacy format
            "npcs": []      # Legacy format
        }

        # Add player pawns
        for player in self.world.players.values():
            pawn_state = self._serialize_player_as_pawn(player)
            world_state["pawns"].append(pawn_state)
            world_state["players"].append(self._serialize_player_legacy(player))

        # Add NPC pawns
        if self.npc_manager:
            for npc_state in self.npc_manager.get_npc_pawn_states():
                world_state["pawns"].append(npc_state)
            world_state["npcs"] = self.npc_manager.get_npc_states()

        return world_state
```

---

## Network Format

### Unified Format (New)

```python
world_state = {
    "pawns": [
        {
            "entity_id": "player_1",
            "pawn_type": "player",
            "owner_id": 1,
            "display_name": "Hero",
            "transform": {"x": 10, "y": 20, "z": 1, "rotation": 45},
            "velocity": {"x": 0.5, "y": 0, "z": 0},
            "model": "human_male",
            "animation": "walk_forward",
            "hp_current": 100,
            "hp_max": 100
        },
        {
            "entity_id": "npc_goblin_1",
            "pawn_type": "npc",
            "display_name": "Goblin",
            "transform": {"x": 15, "y": 25, "z": 1, "rotation": 180},
            "velocity": {"x": 0, "y": 0, "z": 0},
            "model": "goblin",
            "animation": "idle",
            "hp_current": 7,
            "hp_max": 7,
            "ai_state": "IDLE"
        }
    ],
    # Legacy format for backward compatibility
    "players": [...],
    "npcs": [...]
}
```

### Legacy Format

```python
world_state = {
    "players": [
        {
            "client_id": 1,
            "name": "Hero",
            "position": {"x": 10, "y": 20, "z": 1, "rotation": 45},
            "velocity": {"x": 0.5, "y": 0, "z": 0},
            "animation": "walk_forward"
        }
    ],
    "npcs": [
        {
            "entity_id": "goblin_1",
            "display_name": "Goblin",
            "position": {"x": 15, "y": 25, "z": 1, "rotation": 180},
            "model": "goblin",
            "animation": "idle",
            "ai_state": "IDLE",
            "hp_current": 7,
            "hp_max": 7
        }
    ]
}
```

---

## Migration Guide

### From Separate Systems to Unified ECS

1. **Enable unified mode** in GameServer:
   ```python
   self.use_unified_world_state = True
   self._setup_unified_ecs()
   ```

2. **Update client** to read `pawns[]` array:
   ```python
   for pawn in world_state.get("pawns", []):
       if pawn["pawn_type"] == "player":
           self.render_player(pawn)
       else:
           self.render_npc(pawn)
   ```

3. **Backward compatibility**: Legacy `players[]` and `npcs[]` are still included.

---

## Related Documentation

- [NPC System](NPC_SYSTEM.md) - NPC-specific documentation
- [Plugins](PLUGINS.md) - Plugin system with ECS integration examples
- [Event API](EVENT_API.md) - Event reference including world_state_received

---

**Version**: 1.0.0
**Date**: 2026-01-22
