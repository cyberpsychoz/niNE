# NPC System Documentation

## Overview

The NPC system in niNE uses a **Unified ECS Architecture** where players and NPCs share the same Entity-Component-System. This provides:
- Unified physics and collision for all pawns (players + NPCs)
- Consistent network synchronization format
- Shared rendering pipeline
- Flexible, data-driven approach to NPC behavior, combat, and interaction

## Architecture

### Core ECS (Shared by Players & NPCs)
```
nine/core/
├── ecs.py              # ECS core: Entity, Component, ECSWorld
├── components.py       # Unified components (Transform, Pawn, Physics, AI, etc.)
├── systems.py          # Systems: Physics, AI, Animation, NetworkSync
└── world.py            # GameWorld with ECS integration
```

### NPC Plugin
```
nine/plugins/npc/
├── sh_plugin.py        # Plugin metadata
├── sh_components.py    # Legacy NPC components (backward compatibility)
├── sv_plugin.py        # Server module entry point
├── sv_npc_manager.py   # NPC manager with unified mode support
├── sv_npc_ai.py        # AI systems (behavior, pathfinding, combat)
├── cl_npc_renderer.py  # Client-side NPC rendering
└── __init__.py         # Package exports
```

## Key Components

### Unified Components (`nine/core/components.py`)

These components are shared between players and NPCs in the unified ECS:

| Component | Description |
|-----------|-------------|
| `TransformComponent` | x, y, z coordinates and rotation |
| `VelocityComponent` | Movement velocity (vx, vy, vz) |
| `PawnComponent` | Pawn type (player/npc/creature), display name, owner_id |
| `PhysicsComponent` | Collision, walk/run speed, ground state |
| `HealthComponent` | HP current/max, is_dead flag |
| `ModelComponent` | Model path, animation state, scale |
| `InputComponent` | Player input state (keys, camera_yaw) |
| `AIControllerComponent` | AI behavior/state, aggro radius, target |
| `NetworkSyncComponent` | Sync flags, dirty state, last sync time |

### Legacy NPC Components (`sh_components.py`)

For backward compatibility, the NPC plugin still supports:

| Component | Description |
|-----------|-------------|
| `PositionComponent` | x, y, z coordinates and rotation |
| `ModelComponent` | Model path and animation state |
| `NPCInfoComponent` | Template ID, display name, unique ID |
| `AIComponent` | Behavior type, state, aggro radius, movement speed |
| `CombatComponent` | HP, AC, attack bonus, damage dice (D&D stats) |
| `FactionComponent` | Faction ID, hostile flags |
| `DialogueComponent` | Dialogue tree ID, greeting text |
| `InteractionComponent` | Interaction prompts, interaction state |
| `InventoryComponent` | Loot table, gold drops |
| `PathfindingComponent` | Current path, target position |

### AI Behaviors (`AIBehavior` enum)

- `IDLE` - Stands still, doesn't move
- `PATROL` - Follows patrol points
- `WANDER` - Random movement in area
- `HOSTILE` - Attacks players on sight
- `FOLLOW` - Follows a target entity
- `FLEE` - Flees from threats
- `SCHEDULE` - Follows a daily schedule

### AI States (`AIState` enum)

- `IDLE` - Resting
- `MOVING` - Moving to a destination
- `ATTACKING` - In attack range, attacking target
- `PURSUING` - Chasing a target
- `FLEEING` - Running away
- `INTERACTING` - Interacting with player/object
- `DEAD` - NPC is dead

### Combat Integration

When a HOSTILE NPC detects a player within `aggro_radius`:

1. AISystem calls `_find_nearest_enemy()` to find players in range
2. If found, sets `ai.target_entity_id` to player's client_id
3. Posts `npc_aggro_player` event to trigger combat:
   ```python
   event_manager.post("npc_aggro_player", {
       "npc_id": entity.id,
       "player_id": target.id  # client_id as string
   })
   ```
4. CombatManager receives event and starts combat session
5. Initiative is rolled for all participants
6. Turn-based combat begins

## Event Flow

### Spawning NPC via Chat Command

```
1. Player types /spawnnpc goblin
2. ChatBroadcastModule parses command
3. ChatBroadcastModule._handle_spawnnpc() posts event:
   event_manager.post("dm_npc_spawn", {
       "template_id": "goblin",
       "position": {"x": 10.0, "y": 10.0, "z": 1.0},
       "spawner_id": client_id
   })
4. NPCManager._on_dm_spawn() receives event
5. NPCManager.spawn_npc() creates entity:
   - Creates ECS entity
   - Adds components from template
   - Adds tags ("npc", etc.)
6. NPCManager.get_npc_states() returns NPC data
7. GameServer broadcasts world_state to clients
8. Client renders NPC from world_state
```

### World State Sync

#### Unified Format (New)

```python
# Server tick (game_server.py) with unified ECS
def tick(task):
    # Update systems (Physics, AI, Animation)
    if self.npc_manager:
        self.npc_manager.update(dt)

    # Build unified world state
    world_state = {
        "pawns": [  # Players AND NPCs in one array
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
                "model": "goblin",
                "animation": "idle",
                "hp_current": 7,
                "hp_max": 7,
                "ai_state": "IDLE"
            }
        ],
        # Legacy format also included for backward compatibility
        "players": [...],
        "npcs": [...]
    }

    self.broadcast_world_state(world_state)
```

#### Legacy Format (Backward Compatible)

```python
# Old format still supported
world_state = {
    "players": [...],
    "npcs": self.npc_manager.get_npc_states() if self.npc_manager else []
}
```

## NPC Templates

Templates are defined in `sv_npc_manager.py`:

```python
"goblin": {
    "display_name": "Goblin",
    "model": "goblin",
    "components": {
        "AIComponent": {
            "behavior": "HOSTILE",
            "aggro_radius": 12.0,
            "attack_range": 1.5,
            "move_speed": 1.5
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
        }
    },
    "tags": ["humanoid", "monster", "goblinoid"]
}
```

## Chat Commands

| Command | Description | Role |
|---------|-------------|------|
| `/spawnnpc <template> [x y z]` | Spawn NPC at position | admin |
| `/listnpcs` | List active NPCs | admin |
| `/removenpc <entity_id>` | Remove NPC | admin |
| `/startcombat [radius]` | Start combat with NPCs in radius | admin |
| `/endcombat` | End current combat | admin |

## Debugging

### Enable Debug Logging

The EventManager logs NPC-related events (dm_* events) at INFO level:
```
[EventManager] Posting 'dm_npc_spawn' to 1 listeners: {...}
[EventManager] Calling NPCManager._on_dm_spawn
```

### Check NPC Manager Loading

In server.log, look for:
```
NPC Manager loaded
NPC Server Module loaded
```

### Verify Event Subscriptions

The NPCManager subscribes to these events on load:
- `world_loaded`
- `player_update`
- `dm_npc_spawn`
- `dm_npc_despawn`
- `npc_interact_request`
- `npc_attack`

### Common Issues

1. **NPC doesn't spawn**
   - Check server.log for `[SPAWNNPC]` and `[NPC_MANAGER]` logs
   - Verify template exists in npc_templates
   - Check EventManager is shared between plugins

2. **NPC spawns but doesn't appear on client**
   - Verify `world_state_received` event is posted in `client.py`
   - Check client NPC renderer is receiving data via event subscription
   - Verify model path exists (or placeholder will be used)

3. **NPC doesn't move or react to player**
   - Verify `world_loaded` event is posted by GameServer
   - Check pathfinder is initialized (requires `world_loaded` event)
   - Verify `player_update` event is posted with player positions
   - Check AISystem has access to players cache via `get_players()`

4. **Combat doesn't start when NPC sees player**
   - Verify NPC has `hostile_to_players=True` in FactionComponent
   - Check `npc_aggro_player` event is posted by AISystem
   - Verify CombatManager is subscribed to `npc_aggro_player`
   - Check CombatManager can find NPC and player data via `app.npc_manager` and `app.world`

5. **Combat starts but with 0 participants**
   - CombatManager couldn't find NPC data - check `app.npc_manager` reference
   - CombatManager couldn't find player data - check `app.world.players` dict
   - Player might not have entered the game world yet

## ECS Implementation

### Core ECS (`nine/core/ecs.py`)

```python
world = ECSWorld()

# Create entity
entity = world.create_entity("unique_id")

# Add component
entity.add_component(TransformComponent(x=10, y=10, z=1))

# Add tag
entity.add_tag("npc")

# Get entities with tag (returns generator)
npcs = world.get_entities_with_tag("npc")
for npc in npcs:
    print(npc.id)

# Query entities with multiple components
for entity in world.query(PawnComponent, TransformComponent, PhysicsComponent):
    pawn = entity.get_component(PawnComponent)
    transform = entity.get_component(TransformComponent)
    # Process entity...

# Get entity by ID
entity = world.get_entity("unique_id")

# Update world (processes pending additions/removals)
world.update(dt)
```

### Systems (`nine/core/systems.py`)

| System | Description |
|--------|-------------|
| `PhysicsSystem` | Handles physics simulation, collision, gravity for all pawns |
| `InputSystem` | Processes player input into velocity |
| `AISystem` | NPC AI behaviors (idle, patrol, hostile, wander, cowardly) |
| `AnimationSystem` | Determines animation state based on velocity and actions |
| `NetworkSyncSystem` | Generates unified world_state for network broadcast |

```python
# Example: Using systems
physics = PhysicsSystem()
ai = AISystem()
network = NetworkSyncSystem()

# Update in game loop
physics.update(ecs_world, dt)
ai.update(ecs_world, dt)

# Get network state
world_state = network.get_world_state(ecs_world)
```

### Entity

```python
# Get component
pos = entity.get_component(PositionComponent)

# Check tag
if entity.has_tag("npc"):
    ...

# Remove entity
world.remove_entity(entity.id)
```

## Integration Points

### Game Server (Unified Mode)

```python
# game_server.py - unified ECS integration
class GameServer:
    def __init__(self):
        self.npc_manager = None
        self.use_unified_world_state = True  # Enable unified format

    def _setup_unified_ecs(self):
        """Share ECS world between GameWorld and NPCManager"""
        if self.world and self.npc_manager:
            ecs_world = self.world.get_ecs_world()
            self.npc_manager.set_shared_ecs_world(ecs_world)

    def tick(self, task):
        # Update NPC AI
        if self.npc_manager:
            self.npc_manager.update(dt)

        # Build world state (unified or legacy)
        if self.use_unified_world_state:
            world_state = self._get_unified_world_state()
        else:
            world_state = self._get_legacy_world_state()

        self.broadcast_world_state(world_state)
```

### GameWorld (Player ECS)

```python
# world.py - players as ECS entities
class GameWorld:
    def __init__(self):
        self.ecs_world = ECSWorld()

    def add_player(self, client_id, name, position):
        player = Player(client_id, name, position)
        player.entity = self._create_player_entity(client_id, name, position)
        return player

    def _create_player_entity(self, client_id, name, position):
        entity = self.ecs_world.create_entity(f"player_{client_id}")
        entity.add_component(PawnComponent(pawn_type="player", display_name=name))
        entity.add_component(TransformComponent(x=position[0], y=position[1], z=position[2]))
        entity.add_component(PhysicsComponent(has_collision=True))
        entity.add_component(HealthComponent(hp_current=100, hp_max=100))
        entity.add_tag("pawn")
        entity.add_tag("player")
        return entity
```

### NPC Manager (Unified Mode)

```python
# sv_npc_manager.py - shared ECS support
class NPCManager:
    def set_shared_ecs_world(self, ecs_world):
        """Enable unified mode with shared ECS world"""
        self._shared_ecs_world = ecs_world
        self._unified_mode = True

    def spawn_npc(self, template_id, position):
        entity = self.ecs_world.create_entity(f"npc_{uuid}")
        if self._unified_mode:
            self._add_unified_components(entity, template)
        else:
            self._add_legacy_components(entity, template)
```

### Combat System

The combat plugin can query all pawns:
```python
# Query NPCs in radius
npc_plugin = plugin_manager.get_plugin("nine.npc")
if npc_plugin:
    npcs_in_range = npc_plugin.get_npcs_in_radius(player_pos, 30.0)

# Or query via shared ECS
ecs_world = game_world.get_ecs_world()
for entity in ecs_world.query(PawnComponent, TransformComponent):
    # Check distance, pawn_type, etc.
    pass
```

## Adding New NPC Templates

1. Add template to `_load_templates()` in `sv_npc_manager.py`
2. Define all required components
3. Add appropriate tags
4. Optionally add model to assets

```python
"skeleton": {
    "display_name": "Skeleton",
    "model": "skeleton",  # nine/assets/models/npcs/skeleton.bam
    "components": {
        "AIComponent": {"behavior": "HOSTILE", ...},
        "CombatComponent": {"hp_max": 13, "armor_class": 13, ...},
        "FactionComponent": {"faction_id": "undead", "hostile_to_players": True}
    },
    "tags": ["undead", "monster"]
}
```

## Unified ECS Mode

### Enabling Unified Mode

The unified ECS mode is enabled automatically when `GameServer._setup_unified_ecs()` is called. This shares the ECS world between `GameWorld` (players) and `NPCManager` (NPCs).

### Benefits of Unified Mode

1. **Shared Physics** - Players and NPCs use the same physics system
2. **Consistent Collisions** - NPCs collide with walls and players
3. **Unified Network Format** - Single `pawns[]` array instead of separate `players[]` and `npcs[]`
4. **Simpler Queries** - Query all pawns with `ecs_world.query(PawnComponent, ...)`
5. **Code Reuse** - Same systems process both players and NPCs

### Migration from Legacy Mode

The system maintains backward compatibility:

```python
# Legacy format still works
world_state = {
    "players": [...],  # Legacy player format
    "npcs": [...]      # Legacy NPC format
}

# Unified format (new)
world_state = {
    "pawns": [...],    # All pawns (players + NPCs)
    "players": [...],  # Also included for compatibility
    "npcs": [...]      # Also included for compatibility
}
```

Clients can use either `pawns[]` (new) or `players[]`/`npcs[]` (legacy) depending on their implementation.
