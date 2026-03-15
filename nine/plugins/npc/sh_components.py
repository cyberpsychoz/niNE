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
