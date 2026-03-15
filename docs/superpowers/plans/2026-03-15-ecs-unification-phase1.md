# ECS Unification Phase 1 — Unified World & Components

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge two parallel ECS worlds and two component sets into one shared `PooledECSWorld` with a single canonical set of components.

**Architecture:** `GameWorld` upgrades to `PooledECSWorld`. All components defined in `nine/core/components.py` — copied as-is from their source files (NPC, living_npc), only adding `Component` inheritance where missing. `npc/sh_components.py` and `living_npc/sh_living_components.py` become thin re-export shims. Existing `_setup_unified_ecs()` in game_server.py already wires the shared world.

**Tech Stack:** Python 3.12, Panda3D 1.10, dataclasses, ECS pattern

**Spec:** `docs/superpowers/specs/2026-03-15-ecs-unification-design.md`

**Key design decisions (from spec review):**
- Components are copied **as-is** from source — no field renaming, no method removal
- `NeedsComponent`, `PersonalityComponent` get `(Component)` base added — only change
- NPC `ScheduleComponent` (living_npc version) replaces simple NPC version
- NPC `ModelComponent` fields (`current_animation`, `tint_r/g/b`) merge into core
- NPC `PathfindingComponent` (Vec3-based) replaces core tuple-based version
- NPC `DialogueComponent` (richer, with `dialogue_flags`) replaces core version
- `InteractionComponent` from NPC replaces core `InteractableComponent`
- `InventoryComponent` from NPC replaces core version (same fields + more)
- `game_server.py::_setup_unified_ecs()` already exists — no duplication needed

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `nine/core/ecs.py` | Add `flush()` public method |
| Modify | `nine/core/components.py` | Merge ALL components (copy as-is from NPC/living_npc) |
| Replace | `nine/plugins/npc/sh_components.py` | Re-export shim |
| Replace | `nine/plugins/living_npc/sh_living_components.py` | Re-export shim |
| Modify | `nine/core/world.py:238` | Change `ECSWorld()` to `PooledECSWorld()` |
| Verify | `nine/server/game_server.py:372-396` | Already has `_setup_unified_ecs()` — no changes |
| Verify | `nine/plugins/npc/sv_npc_manager.py` | Imports via shim — verify works |
| Verify | `nine/plugins/npc/sv_npc_ai.py` | Imports via shim — verify works |
| Verify | `nine/plugins/npc/cl_npc_renderer.py` | Imports via shim — verify works |
| Verify | `nine/plugins/combat/sv_combat_manager.py` | Imports via shim — verify works |
| Verify | `nine/plugins/combat/sv_turn_manager.py` | Imports via shim — verify works |
| Verify | `nine/plugins/living_npc/sv_living_systems.py` | Imports via shim — verify works |
| Create | `tests/test_ecs_unification.py` | All Phase 1 tests |

---

## Task 1: Add flush() to ECSWorld

**Files:**
- Modify: `nine/core/ecs.py` (after `update()` method, ~line 443)
- Create: `tests/test_ecs_unification.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_ecs_unification.py`:
```python
"""Tests for ECS unification (Phase 1)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nine.core.ecs import ECSWorld, PooledECSWorld, Component
from dataclasses import dataclass

@dataclass
class _Dummy(Component):
    value: int = 0

def test_flush_makes_entity_queryable():
    world = ECSWorld()
    e = world.create_entity("t1")
    e.add_component(_Dummy(42))
    assert len(list(world.get_entities_with_components(_Dummy))) == 0
    world.flush()
    r = list(world.get_entities_with_components(_Dummy))
    assert len(r) == 1 and r[0].get_component(_Dummy).value == 42

def test_flush_pooled():
    world = PooledECSWorld()
    e = world.create_entity("t2")
    e.add_component(_Dummy(99))
    world.flush()
    assert len(list(world.get_entities_with_components(_Dummy))) == 1

def test_flush_idempotent():
    world = ECSWorld()
    world.create_entity("t3").add_component(_Dummy())
    world.flush()
    world.flush()
    assert len(list(world.get_entities_with_components(_Dummy))) == 1

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS {name}")
            except Exception as ex:
                print(f"  FAIL {name}: {ex}")
    print("Done.")
```

- [ ] **Step 2: Run — expect fail**

`cd /home/mrv/Homework/PROJECTS/niNE && python tests/test_ecs_unification.py`
Expected: `AttributeError: 'ECSWorld' object has no attribute 'flush'`

- [ ] **Step 3: Add flush() to ECSWorld**

In `nine/core/ecs.py`, add after `_process_pending_removals()`:
```python
def flush(self) -> None:
    """Process pending additions immediately. Safe to call multiple times."""
    self._process_pending_additions()
```

- [ ] **Step 4: Run — expect pass**

- [ ] **Step 5: Commit**
```bash
git add nine/core/ecs.py tests/test_ecs_unification.py
git commit -m "feat(ecs): add flush() for immediate entity visibility (Bug #1)"
```

---

## Task 2: Merge components into core/components.py

This is the critical task. **Copy component definitions as-is** from their source files into `core/components.py`. The only changes allowed:
- Add `(Component)` inheritance where missing
- Add `current_animation` alias field to `ModelComponent`
- Adopt NPC `PathfindingComponent` (Vec3-based) over core tuple-based
- Adopt NPC `DialogueComponent` (richer) over core version
- Adopt NPC `InteractionComponent` over core `InteractableComponent`

**Files:**
- Modify: `nine/core/components.py`

- [ ] **Step 1: Add NPC enums to core/components.py**

After existing enums (~line 57), add the NPC-specific enums **copied from `npc/sh_components.py`**:

```python
class PhysicsTier(Enum):
    """Physics simulation detail level."""
    FULL = auto()
    SIMPLE = auto()
    NONE = auto()

class InteractionType(Enum):
    """Types of NPC interaction."""
    TALK = auto()
    TRADE = auto()
    ATTACK = auto()
    LOOT = auto()
```

Extend existing `AIBehavior` with NPC values:
```python
class AIBehavior(Enum):
    IDLE = auto()
    PATROL = auto()
    HOSTILE = auto()
    FOLLOW = auto()
    FLEE = auto()
    WANDER = auto()
    NEUTRAL = auto()     # from NPC
    SCHEDULE = auto()    # from NPC
```

Extend existing `AIState`:
```python
class AIState(Enum):
    IDLE = auto()
    MOVING = auto()
    ATTACKING = auto()
    PURSUING = auto()
    FLEEING = auto()
    INTERACTING = auto()
    DEAD = auto()
    IN_COMBAT = auto()   # from NPC
```

Add living_npc enums (**copied as-is, string values preserved**):
```python
class PersonalityTrait(Enum):
    BRAVE = "brave"
    KIND = "kind"
    HONEST = "honest"
    LOYAL = "loyal"
    WISE = "wise"
    PATIENT = "patient"
    GENEROUS = "generous"
    HUMBLE = "humble"
    COWARDLY = "cowardly"
    CRUEL = "cruel"
    DECEITFUL = "deceitful"
    TREACHEROUS = "treacherous"
    FOOLISH = "foolish"
    IMPATIENT = "impatient"
    GREEDY = "greedy"
    ARROGANT = "arrogant"
    CURIOUS = "curious"
    CAUTIOUS = "cautious"
    AMBITIOUS = "ambitious"
    PRAGMATIC = "pragmatic"

class Activity(Enum):
    IDLE = "idle"
    SLEEPING = "sleeping"
    EATING = "eating"
    WORKING = "working"
    PATROLLING = "patrolling"
    SOCIALIZING = "socializing"
    TRADING = "trading"
    PRAYING = "praying"
    TRAINING = "training"
    CRAFTING = "crafting"
    WANDERING = "wandering"

class MemoryType(Enum):
    PLAYER_HELPED = "player_helped"
    PLAYER_ATTACKED = "player_attacked"
    PLAYER_GAVE_ITEM = "player_gave_item"
    PLAYER_INSULTED = "player_insulted"
    PLAYER_COMPLIMENTED = "player_complimented"
    WITNESSED_CRIME = "witnessed_crime"
    WITNESSED_HEROIC_ACT = "witnessed_heroic_act"
    RECEIVED_GIFT = "received_gift"
    WAS_ROBBED = "was_robbed"
    CONVERSATION = "conversation"
```

- [ ] **Step 2: Update TransformComponent with velocity fields and Vec3 compat**

Replace existing `TransformComponent`:
```python
@dataclass
class TransformComponent(Component):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0
    # Velocity fields for client interpolation (from NPC PositionComponent)
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    velocity_z: float = 0.0

    def get_pos(self):
        from panda3d.core import Vec3
        return Vec3(self.x, self.y, self.z)

    def set_pos(self, pos) -> None:
        if hasattr(pos, 'x'):
            self.x, self.y, self.z = pos.x, pos.y, pos.z
        else:
            self.x, self.y, self.z = pos[0], pos[1], pos[2]

    def distance_to(self, other_x: float, other_y: float) -> float:
        dx = self.x - other_x
        dy = self.y - other_y
        return (dx * dx + dy * dy) ** 0.5

    def distance_to_3d(self, other_x: float, other_y: float, other_z: float) -> float:
        dx = self.x - other_x
        dy = self.y - other_y
        dz = self.z - other_z
        return (dx * dx + dy * dy + dz * dz) ** 0.5
```

- [ ] **Step 3: Update ModelComponent with NPC fields**

Replace existing `ModelComponent`:
```python
@dataclass
class ModelComponent(Component):
    model_path: str = ""
    scale: float = 1.0
    animation: str = "idle"
    current_animation: str = "idle"  # NPC alias (same as animation)
    animation_speed: float = 1.0
    visible: bool = True
    tint_r: float = 1.0
    tint_g: float = 1.0
    tint_b: float = 1.0
```

- [ ] **Step 4: Add `tier` to PhysicsComponent**

Add `tier: 'PhysicsTier' = None` as first field (with lazy default to avoid forward ref):
```python
@dataclass
class PhysicsComponent(Component):
    tier: PhysicsTier = PhysicsTier.FULL
    # ... keep ALL existing fields unchanged ...
```

- [ ] **Step 5: Add AIComponent (copy from NPC as-is)**

Add after `AIControllerComponent` (keep old one, add deprecation comment):

```python
# AIControllerComponent is DEPRECATED — use AIComponent instead
```

Copy `AIComponent` from `npc/sh_components.py:101-137` exactly as-is, including `lod_level`, `spawn_position`.

- [ ] **Step 6: Replace PathfindingComponent with NPC Vec3 version**

Replace the tuple-based `PathfindingComponent` with the NPC version from `npc/sh_components.py:140-170` (uses `Vec3`, has steering fields).

- [ ] **Step 7: Copy CombatSessionComponent and TargetableComponent**

Copy from `npc/sh_components.py:209-331` exactly as-is (already inherit `Component`).

- [ ] **Step 8: Replace DialogueComponent with NPC version**

Replace existing `DialogueComponent` with the richer NPC version from `npc/sh_components.py:350-366` (has `dialogue_flags`, `is_in_dialogue`, etc.).

- [ ] **Step 9: Replace InteractableComponent with NPC InteractionComponent**

Remove `InteractableComponent`. Add NPC `InteractionComponent` from `npc/sh_components.py:370-387` (uses `InteractionType` enum, has `interactions` list).

- [ ] **Step 10: Replace InventoryComponent with NPC version**

Replace with NPC version from `npc/sh_components.py:390-409` (same fields, ensure `buy_modifier`, `sell_modifier`, `looted` present).

- [ ] **Step 11: Add NPCInfoComponent (copy from NPC)**

Copy from `npc/sh_components.py:432-446` as-is.

- [ ] **Step 12: Add living_npc components (copy as-is, add Component inheritance)**

Copy **every** class from `living_npc/sh_living_components.py` as-is, only changing:
- `class NeedsComponent:` → `class NeedsComponent(Component):`
- `class PersonalityComponent:` → `class PersonalityComponent(Component):`
- `class RelationshipsComponent:` → `class RelationshipsComponent(Component):`
- `class MemoryComponent:` → `class MemoryComponent(Component):`
- `class ScheduleComponent:` → `class ScheduleComponent(Component):`

Keep ALL methods (`update()`, `eat()`, `sleep()`, `has_trait()`, `get_reaction_modifier()`, `add_memory()`, `_forget_least_important()`, `get_memories_about()`, `decay_memories()`, `get_activity_for_hour()`, `add_entry()`, etc.)

Keep ALL fields with original names, types, and defaults.

Also copy supporting dataclasses:
- `RelationshipData` (with `disposition: float`, `trust: float`, `familiarity: float`, `last_interaction`, `relationship_level` property)
- `Memory` (with `entity_id: str`, `location: Optional[List[float]]`, `timestamp: str`)
- `ScheduleEntry` (with `location_id: Optional[str]`, `location: Optional[List[float]]`)

- [ ] **Step 13: Add WorldBoundsComponent**

```python
@dataclass
class WorldBoundsComponent(Component):
    min_x: float = -500.0
    max_x: float = 500.0
    min_y: float = -500.0
    max_y: float = 500.0
    min_z: float = -10.0
    max_z: float = 200.0
```

- [ ] **Step 14: Update COMPONENT_REGISTRY**

Merge both registries. Include legacy aliases:
```python
COMPONENT_REGISTRY: Dict[str, type] = {
    # Transform
    "TransformComponent": TransformComponent,
    "PositionComponent": TransformComponent,  # NPC legacy alias
    "VelocityComponent": VelocityComponent,
    # Visual
    "ModelComponent": ModelComponent,
    # Identity
    "PawnComponent": PawnComponent,
    "FactionComponent": FactionComponent,
    # Physics
    "PhysicsComponent": PhysicsComponent,
    # Health & Combat
    "HealthComponent": HealthComponent,
    "CombatStatsComponent": CombatStatsComponent,
    "CombatComponent": CombatStatsComponent,  # NPC legacy alias
    "CombatSessionComponent": CombatSessionComponent,
    "TargetableComponent": TargetableComponent,
    # AI
    "AIComponent": AIComponent,
    "AIControllerComponent": AIControllerComponent,  # deprecated
    # Pathfinding
    "PathfindingComponent": PathfindingComponent,
    # Input
    "InputComponent": InputComponent,
    # NPC
    "NPCInfoComponent": NPCInfoComponent,
    "InteractionComponent": InteractionComponent,
    "InteractableComponent": InteractionComponent,  # core legacy alias
    "DialogueComponent": DialogueComponent,
    "InventoryComponent": InventoryComponent,
    # Living World
    "NeedsComponent": NeedsComponent,
    "PersonalityComponent": PersonalityComponent,
    "ScheduleComponent": ScheduleComponent,
    "RelationshipsComponent": RelationshipsComponent,
    "MemoryComponent": MemoryComponent,
    # World
    "WorldObjectComponent": WorldObjectComponent,
    "WorldBoundsComponent": WorldBoundsComponent,
    # Network
    "NetworkSyncComponent": NetworkSyncComponent,
}
```

- [ ] **Step 15: Commit**
```bash
git add nine/core/components.py
git commit -m "feat(components): merge NPC + living_npc components into core (as-is copy)"
```

---

## Task 3: Write component merge tests

**Files:**
- Modify: `tests/test_ecs_unification.py`

- [ ] **Step 1: Add import tests**

Append to test file:
```python
def test_all_components_from_core():
    from nine.core.components import (
        TransformComponent, VelocityComponent, PhysicsComponent, PhysicsTier,
        PawnComponent, PawnType, ModelComponent, HealthComponent,
        CombatStatsComponent, CombatSessionComponent, TargetableComponent,
        FactionComponent, AIComponent, AIBehavior, AIState,
        AIControllerComponent,  # deprecated but still importable
        PathfindingComponent, InputComponent, NetworkSyncComponent,
        NPCInfoComponent, InteractionComponent, InteractionType,
        DialogueComponent, InventoryComponent,
        NeedsComponent, PersonalityComponent, ScheduleComponent, ScheduleEntry,
        RelationshipsComponent, RelationshipData, MemoryComponent, Memory,
        PersonalityTrait, Activity, MemoryType,
        WorldBoundsComponent, COMPONENT_REGISTRY,
    )
    from nine.core.ecs import Component
    for cls in [NeedsComponent, PersonalityComponent, RelationshipsComponent,
                MemoryComponent, ScheduleComponent]:
        assert issubclass(cls, Component), f"{cls.__name__} must inherit Component"

def test_needs_component_methods():
    from nine.core.components import NeedsComponent
    n = NeedsComponent()
    n.update(1.0, is_active=True)
    assert n.hunger < 100
    n.eat(50)
    assert n.hunger > 95
    assert n.most_urgent_need in ("hunger", "energy", "social", "safety")

def test_personality_methods():
    from nine.core.components import PersonalityComponent
    p = PersonalityComponent(traits=["brave", "kind"])
    assert p.has_trait("BRAVE")
    mod = p.get_reaction_modifier("threat")
    assert isinstance(mod, float)

def test_memory_component_methods():
    from nine.core.components import MemoryComponent, Memory
    mc = MemoryComponent()
    mc.add_memory(Memory(memory_type="test", entity_id="e1", importance=0.8))
    assert mc.has_memory_of("e1", "test")
    assert len(mc.get_memories_about("e1")) == 1

def test_schedule_methods():
    from nine.core.components import ScheduleComponent, ScheduleEntry
    sc = ScheduleComponent()
    sc.add_entry(ScheduleEntry(hour_start=8, hour_end=17, activity="working", priority=1))
    result = sc.get_activity_for_hour(10)
    assert result is not None and result.activity == "working"

def test_model_has_current_animation():
    from nine.core.components import ModelComponent
    m = ModelComponent(tint_r=0.5)
    assert hasattr(m, 'current_animation')
    assert hasattr(m, 'tint_r') and m.tint_r == 0.5

def test_registry_legacy_aliases():
    from nine.core.components import COMPONENT_REGISTRY, TransformComponent, CombatStatsComponent
    assert COMPONENT_REGISTRY["PositionComponent"] is TransformComponent
    assert COMPONENT_REGISTRY["CombatComponent"] is CombatStatsComponent

def test_personality_trait_string_values():
    from nine.core.components import PersonalityTrait
    assert PersonalityTrait.BRAVE.value == "brave"
    assert PersonalityTrait.GREEDY.value == "greedy"
```

- [ ] **Step 2: Run all tests**

`python tests/test_ecs_unification.py`
Expected: All pass.

- [ ] **Step 3: Commit**
```bash
git add tests/test_ecs_unification.py
git commit -m "test(components): add merge verification tests for all components"
```

---

## Task 4: Create re-export shims

**Files:**
- Replace: `nine/plugins/npc/sh_components.py`
- Replace: `nine/plugins/living_npc/sh_living_components.py`

- [ ] **Step 1: Replace npc/sh_components.py**

```python
"""
NPC Components — backward compatibility shim.
All components now defined in nine.core.components.
"""
# Re-export everything NPC code expects
from nine.core.components import (
    # Enums
    AIBehavior, AIState, InteractionType, PhysicsTier,
    PawnType, PersonalityTrait, Activity, MemoryType,
    # Components (canonical names)
    TransformComponent, VelocityComponent, ModelComponent,
    AIComponent, PathfindingComponent, FactionComponent,
    CombatStatsComponent, CombatSessionComponent, TargetableComponent,
    HealthComponent, PhysicsComponent, NPCInfoComponent,
    InteractionComponent, DialogueComponent, InventoryComponent,
    NeedsComponent, PersonalityComponent, ScheduleComponent, ScheduleEntry,
    RelationshipsComponent, RelationshipData, MemoryComponent, Memory,
    NetworkSyncComponent, WorldBoundsComponent,
    COMPONENT_REGISTRY,
)

# Legacy aliases — NPC code uses these names
PositionComponent = TransformComponent
CombatComponent = CombatStatsComponent
```

- [ ] **Step 2: Replace living_npc/sh_living_components.py**

```python
"""
Living NPC Components — backward compatibility shim.
All components now defined in nine.core.components.
"""
from nine.core.components import (
    NeedsComponent, PersonalityComponent,
    ScheduleComponent, ScheduleEntry,
    RelationshipsComponent, RelationshipData,
    MemoryComponent, Memory,
    PersonalityTrait, Activity, MemoryType,
)
```

- [ ] **Step 3: Test imports through shims**

```bash
python -c "
from nine.plugins.npc.sh_components import (
    PositionComponent, CombatComponent, AIComponent, ModelComponent,
    FactionComponent, InteractionType, COMPONENT_REGISTRY, AIBehavior
)
print('NPC shim OK:', PositionComponent.__name__, '==', 'TransformComponent')

from nine.plugins.living_npc.sh_living_components import (
    NeedsComponent, PersonalityComponent, ScheduleComponent, Memory
)
print('Living NPC shim OK')
"
```

- [ ] **Step 4: Commit**
```bash
git add nine/plugins/npc/sh_components.py nine/plugins/living_npc/sh_living_components.py
git commit -m "refactor: replace NPC component files with re-export shims from core"
```

---

## Task 5: Upgrade GameWorld to PooledECSWorld

**Files:**
- Modify: `nine/core/world.py` (import + line 238)

- [ ] **Step 1: Change import**

In `nine/core/world.py`, update import:
```python
from nine.core.ecs import ECSWorld, Entity, PooledECSWorld
```

- [ ] **Step 2: Change constructor**

Line ~238, change:
```python
self.ecs_world = PooledECSWorld()
```

- [ ] **Step 3: Commit**
```bash
git add nine/core/world.py
git commit -m "feat(world): upgrade GameWorld to PooledECSWorld"
```

---

## Task 6: Verify all plugins work through shims

No code changes expected — the re-export shims should handle everything. Run import smoke tests.

- [ ] **Step 1: Test each plugin module imports**

```bash
python -c "from nine.plugins.npc.sv_npc_manager import NPCManager; print('sv_npc_manager OK')"
python -c "from nine.plugins.npc.sv_npc_ai import AISystem; print('sv_npc_ai OK')"
python -c "from nine.plugins.npc.cl_npc_renderer import NPCRenderer; print('cl_npc_renderer OK')"
python -c "from nine.plugins.combat.sv_combat_manager import CombatManager; print('sv_combat_manager OK')"
python -c "from nine.plugins.combat.sv_turn_manager import TurnManager; print('sv_turn_manager OK')"
python -c "from nine.plugins.living_npc.sv_living_systems import *; print('sv_living_systems OK')"
```

- [ ] **Step 2: Fix any import errors found**

If any module fails, check what name it imports and ensure the shim re-exports it.

- [ ] **Step 3: Commit only if fixes were needed**

```bash
git add -u
git commit -m "fix: resolve import issues from component unification"
```

---

## Task 7: Integration test — shared world

- [ ] **Step 1: Add integration test**

Append to `tests/test_ecs_unification.py`:
```python
def test_shared_world_coexistence():
    from nine.core.ecs import PooledECSWorld
    from nine.core.components import (
        TransformComponent, PawnComponent, PawnType,
        AIComponent, AIBehavior, FactionComponent,
        InputComponent, PhysicsComponent, VelocityComponent,
    )
    world = PooledECSWorld()

    player = world.create_entity("player-1")
    player.add_component(PawnComponent(pawn_type=PawnType.PLAYER, display_name="Hero"))
    player.add_component(TransformComponent(x=0, y=0, z=1))
    player.add_component(InputComponent())
    player.add_component(PhysicsComponent())
    player.add_component(VelocityComponent())

    npc = world.create_entity("npc-guard")
    npc.add_component(PawnComponent(pawn_type=PawnType.NPC, display_name="Guard"))
    npc.add_component(TransformComponent(x=5, y=5, z=1))
    npc.add_component(AIComponent(behavior=AIBehavior.PATROL))
    npc.add_component(FactionComponent(faction_id="guards"))
    npc.add_component(VelocityComponent())

    world.flush()

    all_pawns = list(world.get_entities_with_components(PawnComponent, TransformComponent))
    assert len(all_pawns) == 2

    npcs = [e for e in all_pawns if e.get_component(PawnComponent).pawn_type == PawnType.NPC]
    assert len(npcs) == 1 and npcs[0].get_component(AIComponent).behavior == AIBehavior.PATROL

    players = [e for e in all_pawns if e.get_component(PawnComponent).pawn_type == PawnType.PLAYER]
    assert len(players) == 1 and players[0].get_component(InputComponent) is not None
```

- [ ] **Step 2: Run full test suite**

`python tests/test_ecs_unification.py`

- [ ] **Step 3: Test server starts**

```bash
timeout 15 python -m nine.server.game_server 2>&1 | grep -iE "ECS|unified|NPC|ERROR" | head -20
```

Expected: "Unified ECS mode enabled" in logs, no errors.

- [ ] **Step 4: Final commit**
```bash
git add tests/test_ecs_unification.py
git commit -m "test(ecs): integration test for unified ECS world"
```

---

## Summary

**7 tasks, ~10 commits.** After completion:
- One `PooledECSWorld` shared by GameWorld and NPCManager
- All components in `core/components.py` (copied as-is, no functionality lost)
- Shims provide backward compatibility for all existing imports
- `flush()` solves Bug #1
- All living_npc component methods preserved
- All NPC field names preserved (no `current_animation` vs `animation` breakage)
- Legacy aliases (`PositionComponent`, `CombatComponent`) work through shims

**Next:** Phase 2 plan (unified physics with PhysicsTier).
