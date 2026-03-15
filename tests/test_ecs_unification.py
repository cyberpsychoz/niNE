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
