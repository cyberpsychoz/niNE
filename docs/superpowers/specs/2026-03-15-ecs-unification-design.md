# ECS Unification & Physics — Architecture Redesign

**Date:** 2026-03-15
**Branch:** `dnd-gamemode-v0.1.0-alpha`
**Status:** Reviewed

---

## Problem Statement

niNE has two parallel ECS worlds, two component sets, two physics approaches, and scattered plugin organization. This causes:

1. NPC walk through walls (no collision)
2. NPC float in air (no gravity)
3. Players and NPC cannot interact physically
4. Duplicated code across `core/components.py` and `npc/sh_components.py`
5. Two separate game loops that don't share state
6. No world boundaries — entities wander to infinity
7. Movement speed doesn't match animation playback rate

---

## Current Architecture (Problems)

### Dual ECS Worlds

```
GameWorld.ecs_world (ECSWorld)          NPCManager.ecs_world (PooledECSWorld)
├── TransformComponent                  ├── PositionComponent        ← duplicate
├── VelocityComponent                   ├── AIComponent
├── PhysicsComponent                    ├── CombatComponent          ← overlaps HealthComponent
├── HealthComponent                     ├── CombatSessionComponent
├── InputComponent                      ├── TargetableComponent
├── PawnComponent                       ├── FactionComponent
├── ModelComponent                      ├── PathfindingComponent (Vec3-based)
├── NetworkSyncComponent                ├── ModelComponent           ← duplicate (has tint fields)
├── AIControllerComponent               ├── NPCInfoComponent
├── CombatStatsComponent                ├── InteractionComponent
├── PathfindingComponent (tuple-based)  ├── DialogueComponent
└── InteractableComponent               └── ScheduleComponent
```

**Result:** NPC are invisible to PhysicsSystem. Players are invisible to NPC AISystem. No shared spatial queries.

### Dual Physics

| Entity | Physics approach | Collision | Gravity | Ground detection |
|--------|-----------------|-----------|---------|-----------------|
| Player | `CharacterController` (legacy, non-ECS) | CollisionSphere + Pusher | Yes (25 m/s²) | Ray cast |
| NPC | Arithmetic (`pos.x += speed * dt`) | None | None | None |

### Scattered Plugins

```
nine/plugins/
├── npc/              ← NPC core (manager, AI, renderer, components)
├── living_npc/       ← NPC needs/personality (separate plugin, uses own components)
├── dnd/npc/          ← NPC dialogue data (inside dnd plugin)
├── dnd/audio/        ← Audio (inside dnd plugin, should be standalone)
├── combat/           ← Combat system (references both component sets)
└── ...
```

### living_npc Component Issues

`living_npc/sh_living_components.py` defines:
- `NeedsComponent`, `PersonalityComponent` — **do NOT inherit from `Component`** (plain `@dataclass`)
- `ScheduleComponent` — conflicts with `npc/sh_components.py::ScheduleComponent` (different structure)
- `RelationshipsComponent`, `MemoryComponent` — not mentioned in current docs
- Supporting types: `PersonalityTrait`, `Activity`, `MemoryType` enums, `RelationshipData`, `Memory`, `ScheduleEntry` dataclasses

---

## Target Architecture

### Single ECS World

One `PooledECSWorld` shared by all systems. All entities (players, NPC, world objects) live in the same world.

`GameWorld` upgraded from `ECSWorld` to `PooledECSWorld` (explicit Phase 1 step).

```
nine/core/ecs.py          ← ECSWorld, Entity, System, EntityPool (Bug #1 fix)
nine/core/components.py   ← ALL unified components (merge of both sets)
nine/core/systems.py      ← ALL core systems (physics, input, animation, network)
```

### Unified Component Set

#### Core components (in `core/components.py`):

**Transform & Physics:**
- `TransformComponent` — position + rotation (replaces NPC `PositionComponent`; add `get_pos()`/`set_pos()` convenience methods for Vec3 compat)
- `VelocityComponent` — velocity vector (NPC `PositionComponent.velocity_x/y/z` migrates here)
- `PhysicsComponent` — collision, gravity, movement speeds + `tier: PhysicsTier` (NEW)
- `WorldBoundsComponent` — world limits and kill plane

**Identity & Visuals:**
- `PawnComponent` — entity identity (player/NPC/creature), display name, owner
- `FactionComponent` — **kept as separate component** (has `faction_id`, `hostile_to_players`, `disposition_overrides` — too rich for a single field)
- `ModelComponent` — model path, animation, scale + `tint_r/g/b` (merged from NPC version)
- `NetworkSyncComponent` — sync flags

**Input:**
- `InputComponent` — player key states

**Health & Combat:**
- `HealthComponent` — HP, death state, armor class, temp HP
- `CombatStatsComponent` — attack bonus, damage dice, damage type
- `CombatSessionComponent` — turn-based combat state (initiative, action economy, conditions, concentration) — **kept from NPC as-is**
- `TargetableComponent` — target selection state — **kept from NPC as-is**

**AI:**
- `AIComponent` — replaces core `AIControllerComponent` (more complete: has `lod_level`, `spawn_position`, NPC-specific fields). Core `AIBehavior` enum replaced by NPC version (includes `NEUTRAL`, `SCHEDULE`).
- `PathfindingComponent` — adopt NPC version with `Vec3` types (core version's `tuple` callers updated). Includes steering fields (`velocity: Vec3`, `max_speed`, `max_force`).

**NPC-specific:**
- `NPCInfoComponent` — template, spawn data
- `InteractionComponent` — interaction types and prompts (replaces core `InteractableComponent`)
- `DialogueComponent` — dialogue tree reference

**Living world (from `living_npc/`, fixed to inherit `Component`):**
- `NeedsComponent(Component)` — hunger, rest, social needs
- `PersonalityComponent(Component)` — personality traits with modifiers
- `ScheduleComponent(Component)` — adopt living_npc version (typed `ScheduleEntry` with hour ranges and priority; NPC simple `Dict` version deprecated)
- `RelationshipsComponent(Component)` — NPC relationships
- `MemoryComponent(Component)` — NPC memories
- Supporting types: `PersonalityTrait`, `Activity`, `MemoryType`, `RelationshipData`, `Memory`, `ScheduleEntry`

#### Removed (deduplicated):
- `npc/sh_components.py::PositionComponent` → `TransformComponent` + `VelocityComponent`
- `npc/sh_components.py::ModelComponent` → core `ModelComponent` (with tint fields added)
- `core/components.py::AIControllerComponent` → NPC `AIComponent`
- `core/components.py::InteractableComponent` → NPC `InteractionComponent`
- `core/components.py::PathfindingComponent` (tuple version) → NPC `PathfindingComponent` (Vec3 version)
- NPC `CombatComponent` → split into `HealthComponent` + `CombatStatsComponent` (CR field → `CombatStatsComponent`)

#### COMPONENT_REGISTRY

Unified registry in `core/components.py` combining both current registries. Used by `create_entity_from_template()` for JSON-based NPC spawning.

### Physics Tiers

Not all entities need full Panda3D collision. Three tiers:

| Tier | Entities | Collision | Gravity | Ground detection | Cost |
|------|----------|-----------|---------|-----------------|------|
| FULL | Players, boss NPC | CollisionSphere + Pusher | Full simulation | Ray cast every frame | ~0.2ms/entity |
| SIMPLE | Regular NPC | World boundary clamp only | Snap to cached ground_z | Periodic ray (1/second), dynamically added/removed from traverser | ~0.005ms/entity (amortized) |
| NONE | Distant NPC (LOD SLEEPING) | Skip entirely | None | None | 0 |

**SIMPLE tier implementation detail:** Ground rays are NOT persistent colliders. Instead, a per-frame budget of N ray casts is distributed across SIMPLE entities round-robin (e.g., 10 rays/frame at 60fps = all 300 NPC sampled within 0.5s). Rays are added to traverser, fired, result cached, ray removed — no persistent traverser overhead.

### World Boundaries

```python
@dataclass
class WorldBoundsComponent(Component):
    """Attached to a single 'world' entity. Systems read it."""
    min_x: float = -500.0
    max_x: float = 500.0
    min_y: float = -500.0
    max_y: float = 500.0
    min_z: float = -10.0    # Kill plane
    max_z: float = 200.0
```

PhysicsSystem clamps positions. Entities below `min_z` get teleported to nearest spawn point.

### Movement Speed & Animation Sync

Current problem: `walk_speed=1.5`, `run_speed=3.0` units/sec makes entities fly across the map because world units are in meters and animation root motion doesn't match.

Solution:
- Reduce default speeds: `walk_speed=0.8`, `run_speed=1.6`
- `AnimationSystem` sets `play_rate = actual_speed / anim_reference_speed` so animation speed matches movement
- Configurable per-entity via `PhysicsComponent.walk_speed`

### Player Migration Path

**Phase 1:** Player keeps `CharacterController` but shares the same `PooledECSWorld` as NPC. `CharacterController` writes directly to `TransformComponent` (no double-sync).

**Phase 4 (future):** `CharacterController` logic moves into `PhysicsSystem` (FULL tier). Player becomes a pure ECS entity with `InputComponent` + `PhysicsComponent(tier=FULL)`. `CharacterController` removed.

### Camera

Keep current camera system. Improvements deferred (separate task):
- Smooth follow with damping
- Collision with environment (camera doesn't clip through walls)
- Better third-person orbit

### Plugin Consolidation

```
BEFORE:                          AFTER:
plugins/npc/                     plugins/npc/          ← all NPC (AI, living, renderer)
plugins/living_npc/              (merged into npc/)
plugins/dnd/npc/                 plugins/dnd/          ← D&D rules only
plugins/dnd/audio/               plugins/audio/        ← standalone audio plugin
```

- Move `living_npc/*` into `npc/` (same plugin, living world is NPC behavior)
- Move `dnd/audio/` to top-level `plugins/audio/` (audio isn't D&D-specific)
- Move `dnd/npc/data/dialogues/` into `npc/data/dialogues/`

---

## Implementation Phases

### Phase 1: Unified ECS World + Components

**Goal:** One world, one component set. No behavior changes yet.

1. Upgrade `GameWorld.ecs_world` from `ECSWorld` to `PooledECSWorld`
2. Merge ALL component definitions into `core/components.py` (full inventory above)
3. Fix `NeedsComponent`, `PersonalityComponent` to inherit from `Component`
4. Resolve `ScheduleComponent` conflict: adopt living_npc version, update NPC callers
5. Unify `COMPONENT_REGISTRY` in `core/components.py`
6. Create migration aliases in `npc/sh_components.py` (re-exports from core for backward compat)
7. `GameWorld` calls `NPCManager.set_shared_ecs_world(self.ecs_world)` at startup
8. All entity creation uses the shared world
9. Fix ECS Bug #1: add public `flush()` method that calls `_process_pending_additions()`. `create_entity()` behavior unchanged (batching preserved). Callers that need immediate visibility call `flush()`.
10. Update all plugin imports
11. Update NPC AI imports: `AIBehavior` enum now includes `NEUTRAL`, `SCHEDULE`; core `systems.py::AISystem` updated to handle them

**Rollback strategy:** Feature flag `UNIFIED_ECS = True` in `config.json`. When `False`, NPCManager creates its own world (current behavior). Flag checked in `game_server.py` when wiring worlds.

**Risk:** High — touches ~20 files. Migration aliases reduce breakage.
**Validation:** Server starts, NPC spawn, player moves, combat works, living NPC behaviors unchanged.

### Phase 2: Unified Physics

**Goal:** NPC get collision and gravity. Players still use CharacterController.

1. Add `PhysicsTier` enum and `tier` field to `PhysicsComponent`
2. `PhysicsSystem` handles FULL tier (existing code) and SIMPLE tier (round-robin ground ray + boundary clamp)
3. NPC entities get `PhysicsComponent(tier=SIMPLE)` + `VelocityComponent`
4. NPC AI writes to `VelocityComponent` instead of directly changing position
5. Add `WorldBoundsComponent` and boundary clamping in PhysicsSystem
6. Add kill plane (teleport to spawn if z < min_z)
7. Reduce movement speeds (`walk_speed=0.8`, `run_speed=1.6`)
8. `AnimationSystem` play_rate sync with actual movement speed

**Risk:** Medium — NPC movement will feel different. Needs tuning.
**Validation:** NPC don't walk through walls. NPC don't fall below map. NPC stop at world edges. Animation matches movement speed.

### Phase 3: AI + Combat Integration

**Goal:** AISystem sees players through ECS. Combat uses ECS entities directly.

1. `AISystem` queries players from shared ECS world via `PawnComponent(pawn_type=PLAYER)` — no more `NPCManager.get_players()`
2. Fix Bug #2: AISystem decoupled from NPCManager (player positions from ECS query)
3. Fix Bug #3: `FactionComponent` with default `faction_id="neutral"` for entities without it
4. `CombatManager` reads/writes `HealthComponent` + `CombatStatsComponent` on ECS entities directly (eliminate `CombatParticipant` copy where possible)
5. `SpatialHash` tracks all entities (players + NPC)
6. Plugin consolidation (merge living_npc → npc, extract audio → plugins/audio)

**Risk:** Medium — combat flow changes significantly.
**Validation:** Combat deals damage reflected in ECS. AI detects players. Living NPC still work.

### Phase 4: Full Player ECS Migration (Future)

**Goal:** Remove `CharacterController`, players are pure ECS entities.

1. Port `CharacterController` logic into `PhysicsSystem` (FULL tier)
2. `InputSystem` processes `InputComponent` → writes `VelocityComponent`
3. Remove `Player` wrapper class
4. Remove `CharacterController`
5. Remove `UNIFIED_ECS` feature flag

**Risk:** High — changes player movement feel.
**Validation:** Player movement identical to before.

---

## Files Changed Per Phase

### Phase 1 (~20 files)
- `nine/core/ecs.py` — add `flush()` method
- `nine/core/components.py` — merge all components + unified COMPONENT_REGISTRY
- `nine/plugins/npc/sh_components.py` — re-export aliases from core
- `nine/plugins/living_npc/sh_living_components.py` — re-export aliases from core
- `nine/core/world.py` — upgrade to PooledECSWorld, wire shared world
- `nine/plugins/npc/sv_npc_manager.py` — use shared world, update imports
- `nine/plugins/npc/sv_npc_ai.py` — import from core, handle new AIBehavior values
- `nine/plugins/npc/cl_npc_renderer.py` — import from core
- `nine/plugins/combat/sv_combat_manager.py` — import from core
- `nine/plugins/combat/sv_turn_manager.py` — import from core
- `nine/plugins/living_npc/sv_living_systems.py` — import from core
- `nine/plugins/conditions/*.py` — import from core
- `nine/server/game_server.py` — wire shared world, feature flag
- `nine/core/systems.py` — update AISystem for new enum values
- `nine/core/config.py` — add UNIFIED_ECS flag

### Phase 2 (~8 files)
- `nine/core/components.py` — PhysicsTier enum, WorldBoundsComponent
- `nine/core/systems.py` — PhysicsSystem SIMPLE tier, boundary clamping, AnimationSystem speed sync
- `nine/plugins/npc/sv_npc_ai.py` — write VelocityComponent not PositionComponent
- `nine/plugins/npc/sv_npc_manager.py` — add PhysicsComponent(tier=SIMPLE) to NPC
- `nine/core/world.py` — create world bounds entity, reduce default speeds
- `nine/core/character_controller.py` — reduce speeds to match

### Phase 3 (~12 files)
- `nine/plugins/npc/sv_npc_ai.py` — query players from ECS
- `nine/plugins/combat/sv_combat_manager.py` — use ECS entities directly
- `nine/plugins/combat/sv_turn_manager.py` — read/write HealthComponent
- `nine/core/spatial.py` — track all entities
- `nine/plugins/npc/` — absorb living_npc files
- `nine/plugins/audio/` — extracted from dnd/audio
- `nine/plugins/living_npc/` — delete (moved to npc/)
- `nine/plugins/dnd/audio/` — delete (moved to plugins/audio/)

---

## Success Criteria

1. **One ECS world** — `GameWorld.ecs_world` is the only `PooledECSWorld`
2. **One component set** — all components in `core/components.py`, no duplicates
3. **NPC have collision** — don't walk through walls
4. **NPC have gravity** — stay on ground
5. **World has boundaries** — nothing escapes to infinity
6. **Animation matches movement** — walk looks like walking, not skating
7. **AI sees players** — through ECS queries, not NPCManager coupling
8. **Combat uses ECS** — damage applied to HealthComponent directly
9. **Plugin tree is clean** — no scattered duplicates
10. **300+ NPC at 60 tick/s** — SIMPLE physics tier keeps it fast
11. **Existing features don't break** — combat, chat, inventory, UI all work
12. **Feature flag rollback** — can disable unified ECS if critical issues found

---

## Out of Scope

- Camera improvements (separate task, tracked)
- Bullet physics migration (Panda3D collision is sufficient)
- Netcode rewrite
- Client-side prediction
- New content (maps, quests, spells)
