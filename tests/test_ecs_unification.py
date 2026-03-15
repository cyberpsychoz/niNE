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


# =============================================================================
# Component merge tests
# =============================================================================

def test_all_components_from_core():
    from nine.core.components import (
        TransformComponent, VelocityComponent, PhysicsComponent, PhysicsTier,
        PawnComponent, PawnType, ModelComponent, HealthComponent,
        CombatStatsComponent, CombatSessionComponent, TargetableComponent,
        FactionComponent, AIComponent, AIBehavior, AIState,
        AIControllerComponent,
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

def test_transform_vec3_compat():
    from nine.core.components import TransformComponent
    t = TransformComponent(x=1.0, y=2.0, z=3.0)
    pos = t.get_pos()
    assert pos.x == 1.0 and pos.y == 2.0 and pos.z == 3.0

def test_relationships_methods():
    from nine.core.components import RelationshipsComponent
    rc = RelationshipsComponent()
    rc.modify_disposition("player1", 30)
    assert rc.get_disposition("player1") == 80.0
    assert not rc.is_hostile_to("player1")
    rel = rc.get_relationship("player1")
    assert rel.relationship_level == "friend"

def test_combat_session_methods():
    from nine.core.components import CombatSessionComponent
    cs = CombatSessionComponent()
    assert cs.consume_action()
    assert not cs.consume_action()  # already consumed
    cs.reset_turn_resources()
    assert cs.has_action
    cs.add_condition("poisoned", duration=3)
    assert cs.has_condition("poisoned")
    cs.tick_conditions()
    assert cs.condition_durations["poisoned"] == 2



# =============================================================================
# Integration tests
# =============================================================================

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

def test_shim_aliases_resolve_to_core():
    """PositionComponent and CombatComponent aliases work through shim."""
    from nine.plugins.npc.sh_components import PositionComponent, CombatComponent
    from nine.core.components import TransformComponent, CombatStatsComponent
    assert PositionComponent is TransformComponent
    assert CombatComponent is CombatStatsComponent

    # entity.get_component(PositionComponent) == get_component(TransformComponent)
    from nine.core.ecs import ECSWorld
    world = ECSWorld()
    e = world.create_entity("alias-test")
    e.add_component(TransformComponent(x=1, y=2, z=3))
    world.flush()
    # Query via alias returns same component
    assert e.get_component(PositionComponent).x == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS {name}")
            except Exception as ex:
                print(f"  FAIL {name}: {ex}")
    print("Done.")
