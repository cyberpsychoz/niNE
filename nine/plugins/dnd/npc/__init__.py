"""
NPC система для D&D режима niNE.

Модуль предоставляет ECS-based систему NPC с поддержкой:
- Различных типов NPC (торговцы, квестодатели, враги и т.д.)
- AI поведения (patrol, idle, hostile, follow)
- Pathfinding для навигации
- Диалоговой системы
- Боевых характеристик

Структура модуля:
- sh_components.py - Компоненты NPC (Position, AI, Combat и т.д.)
- sv_npc_manager.py - Серверный менеджер NPC
- sv_npc_ai.py - AI системы
- cl_npc_renderer.py - Клиентская отрисовка
- cl_npc_interaction.py - UI взаимодействия
"""

from .sh_components import (
    PositionComponent,
    ModelComponent,
    AIComponent,
    PathfindingComponent,
    CombatComponent,
    FactionComponent,
    DialogueComponent,
    InteractionComponent,
    InventoryComponent,
)

__all__ = [
    'PositionComponent',
    'ModelComponent',
    'AIComponent',
    'PathfindingComponent',
    'CombatComponent',
    'FactionComponent',
    'DialogueComponent',
    'InteractionComponent',
    'InventoryComponent',
]
