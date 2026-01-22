# Unified ECS Architecture

## Overview

niNE uses a Unified Entity-Component-System (ECS) architecture where **players and NPCs share the same ECS world**. This provides:

- **Unified Physics** - All pawns (players + NPCs) use the same physics system
- **Consistent Collisions** - NPCs collide with walls and players
- **Single Network Format** - One `pawns[]` array instead of separate `players[]` and `npcs[]`
- **Code Reuse** - Same systems process both players and NPCs
- **Simpler Queries** - Query all pawns with `ecs_world.query(PawnComponent, ...)`

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
| `nine/core/ecs.py` | ECS core: Entity, Component, ECSWorld |
| `nine/core/components.py` | Unified components for all entities |
| `nine/core/systems.py` | Systems: Physics, AI, Animation, NetworkSync |
| `nine/core/world.py` | GameWorld with ECS integration for players |
| `nine/plugins/npc/sv_npc_manager.py` | NPC manager with unified mode |

---

## Components (`nine/core/components.py`)

### Enums

```python
class PawnType(Enum):
    PLAYER = "player"
    NPC = "npc"
    CREATURE = "creature"

class AIBehavior(Enum):
    IDLE = "IDLE"
    PATROL = "PATROL"
    WANDER = "WANDER"
    HOSTILE = "HOSTILE"
    FRIENDLY = "FRIENDLY"
    COWARDLY = "COWARDLY"

class AIState(Enum):
    IDLE = "IDLE"
    PATROL = "PATROL"
    ALERT = "ALERT"
    CHASE = "CHASE"
    ATTACK = "ATTACK"
    FLEE = "FLEE"
    DEAD = "DEAD"
```

### Transform & Movement

```python
@dataclass
class TransformComponent(Component):
    """Position and rotation in world space"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0

@dataclass
class VelocityComponent(Component):
    """Movement velocity"""
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
```

### Pawn Components

```python
@dataclass
class PawnComponent(Component):
    """Base component for all creatures (players, NPCs)"""
    pawn_type: str = "npc"         # PawnType value
    display_name: str = ""
    owner_id: Optional[int] = None  # client_id for players

@dataclass
class PhysicsComponent(Component):
    """Physics properties"""
    has_collision: bool = True
    walk_speed: float = 1.5
    run_speed: float = 3.0
    is_on_ground: bool = False
    is_running: bool = False

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
