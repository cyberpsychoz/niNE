"""
Серверный менеджер NPC.

Управляет жизненным циклом NPC: спавн, деспавн, обновление, синхронизация.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import asdict
import logging

from nine.core.ecs import ECSWorld, Entity, create_entity_from_template
from nine.core.pathfinder import GridPathfinder
from nine.core.plugins import PluginModule, PluginContext

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
    NPCInfoComponent,
    COMPONENT_REGISTRY,
    AIBehavior,
    AIState,
)
from .sv_npc_ai import AISystem, PathfindingSystem, CombatAISystem

if TYPE_CHECKING:
    from nine.core.events import EventManager

logger = logging.getLogger(__name__)


class NPCManager(PluginModule):
    """
    Серверный плагин управления NPC.

    Обязанности:
    - Загрузка шаблонов NPC из JSON
    - Спавн/деспавн NPC
    - Обновление ECS мира
    - Синхронизация с клиентами
    """

    plugin_type = 'server'

    def __init__(self, context: PluginContext):
        super().__init__(context)

    def on_load(self):
        """Инициализация при загрузке плагина."""
        # ECS мир для NPC
        self.ecs_world = ECSWorld()

        # Pathfinder (создаётся после загрузки карты)
        self.pathfinder: Optional[GridPathfinder] = None

        # Шаблоны NPC
        self.npc_templates: Dict[str, Dict] = {}

        # Маппинг entity_id -> данные для сети
        self._npc_network_data: Dict[str, Dict] = {}

        # Ссылка на игроков (для AI targeting)
        self._players_cache: List[Dict] = []

        # Инициализируем системы
        self._init_systems()

        # Загружаем шаблоны
        self._load_templates()

        # Подписки на события
        self.event_manager.subscribe("world_loaded", self._on_world_loaded)
        self.event_manager.subscribe("player_update", self._on_player_update)
        self.event_manager.subscribe("dm_npc_spawn", self._on_dm_spawn)
        self.event_manager.subscribe("dm_npc_despawn", self._on_dm_despawn)
        self.event_manager.subscribe("npc_interact_request", self._on_interact_request)
        self.event_manager.subscribe("npc_attack", self._on_npc_attack)

        self.logger.info("NPC Manager loaded")

    def on_unload(self):
        """Очистка при выгрузке плагина."""
        self.event_manager.unsubscribe("world_loaded", self._on_world_loaded)
        self.event_manager.unsubscribe("player_update", self._on_player_update)
        self.event_manager.unsubscribe("dm_npc_spawn", self._on_dm_spawn)
        self.event_manager.unsubscribe("dm_npc_despawn", self._on_dm_despawn)
        self.event_manager.unsubscribe("npc_interact_request", self._on_interact_request)
        self.event_manager.unsubscribe("npc_attack", self._on_npc_attack)

        self.ecs_world.clear()
        self.logger.info("NPC Manager unloaded")

    def _init_systems(self):
        """Инициализирует ECS системы."""
        # AI система
        ai_system = AISystem(npc_manager=self)
        self.ecs_world.add_system(ai_system)

        # Pathfinding система (pathfinder добавится позже)
        pathfinding_system = PathfindingSystem(pathfinder=None)
        self.ecs_world.add_system(pathfinding_system)

        # Combat AI система
        combat_system = CombatAISystem(npc_manager=self)
        self.ecs_world.add_system(combat_system)

        self.logger.debug("NPC systems initialized")

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
                        "move_speed": 1.2
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
                "tags": ["humanoid", "guard"]
            },
            "goblin": {
                "display_name": "Гоблин",
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
                    },
                    "InventoryComponent": {
                        "loot_table_id": "goblin_loot",
                        "gold": 5
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
                        "move_speed": 1.0
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
                "tags": ["humanoid", "merchant", "npc"]
            },
            "skeleton": {
                "display_name": "Скелет",
                "model": "skeleton",
                "components": {
                    "AIComponent": {
                        "behavior": "HOSTILE",
                        "aggro_radius": 10.0,
                        "attack_range": 1.5,
                        "move_speed": 1.2
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
        template = self.npc_templates.get(template_id)
        if not template:
            self.logger.warning(f"Unknown NPC template: {template_id}")
            return None

        # Создаём entity
        entity = self.ecs_world.create_entity(entity_id)

        # Добавляем NPCInfo
        entity.add_component(NPCInfoComponent(
            template_id=template_id,
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

        # Добавляем теги
        for tag in template.get("tags", []):
            entity.add_tag(tag)
        entity.add_tag("npc")

        # Сохраняем данные для сети
        self._update_network_data(entity)

        self.logger.info(f"Spawned NPC '{template_id}' at ({x:.1f}, {y:.1f}, {z:.1f})")

        # Отправляем событие спавна
        self.event_manager.post("npc_spawned", {
            "entity_id": entity.id,
            "template_id": template_id,
            "position": {"x": x, "y": y, "z": z, "rotation": rotation}
        })

        return entity

    def despawn_npc(self, entity_id: str) -> bool:
        """
        Удаляет NPC.

        Args:
            entity_id: ID entity

        Returns:
            True если удалено
        """
        entity = self.ecs_world.get_entity(entity_id)
        if not entity:
            return False

        self.ecs_world.remove_entity(entity_id)
        self._npc_network_data.pop(entity_id, None)

        self.event_manager.post("npc_despawned", {"entity_id": entity_id})
        self.logger.info(f"Despawned NPC {entity_id[:8]}")

        return True

    def update(self, dt: float):
        """
        Обновляет NPC мир.

        Вызывается из game_server каждый тик.

        Args:
            dt: Время с прошлого обновления
        """
        self.ecs_world.update(dt)

        # Обновляем сетевые данные для изменённых NPC
        for entity in self.ecs_world.get_entities_with_tag("npc"):
            self._update_network_data(entity)

    def get_npc_states(self) -> List[Dict]:
        """
        Возвращает состояния всех NPC для синхронизации.

        Returns:
            Список данных NPC
        """
        return list(self._npc_network_data.values())

    def get_players(self) -> List[Dict]:
        """Возвращает кэш данных игроков для AI."""
        return self._players_cache

    def get_npc_entity(self, entity_id: str) -> Optional[Entity]:
        """Получает NPC entity по ID."""
        return self.ecs_world.get_entity(entity_id)

    def get_npcs_in_radius(self, x: float, y: float, radius: float) -> List[Entity]:
        """Возвращает NPC в радиусе от точки."""
        result = []
        for entity in self.ecs_world.get_entities_with_tag("npc"):
            pos = entity.get_component(PositionComponent)
            if pos and pos.distance_to(x, y) <= radius:
                result.append(entity)
        return result

    # =========================================================================
    # Обработчики событий
    # =========================================================================

    def _on_world_loaded(self, data: dict):
        """Обрабатывает загрузку мира."""
        # Инициализируем pathfinder
        world_bounds = data.get("bounds", (-50, -50, 50, 50))
        self.pathfinder = GridPathfinder(
            cell_size=1.0,
            width=int((world_bounds[2] - world_bounds[0]) / 1.0),
            height=int((world_bounds[3] - world_bounds[1]) / 1.0),
            origin_x=world_bounds[0],
            origin_y=world_bounds[1]
        )

        # Обновляем pathfinder в системе
        pathfinding_system = self.ecs_world.get_system(PathfindingSystem)
        if pathfinding_system:
            pathfinding_system.pathfinder = self.pathfinder

        self.logger.info("Pathfinder initialized for NPC")

        # Спавним тестовых NPC (можно убрать в продакшене)
        self._spawn_test_npcs()

    def _spawn_test_npcs(self):
        """Спавнит тестовых NPC."""
        # Торговец
        self.spawn_npc("merchant", x=5.0, y=0.0, z=1.0)

        # Патрульный страж
        guard = self.spawn_npc("guard", x=10.0, y=5.0, z=1.0)
        if guard:
            ai = guard.get_component(AIComponent)
            if ai:
                ai.patrol_points = [
                    (10.0, 5.0, 1.0),
                    (15.0, 5.0, 1.0),
                    (15.0, 10.0, 1.0),
                    (10.0, 10.0, 1.0)
                ]

        # Гоблин враг
        self.spawn_npc("goblin", x=-5.0, y=-5.0, z=1.0)

    def _on_player_update(self, data: dict):
        """Обновляет кэш данных игроков."""
        players = data.get("players", [])
        self._players_cache = players

    def _on_dm_spawn(self, data: dict):
        """Обрабатывает команду DM на спавн NPC."""
        template_id = data.get("template_id")
        pos = data.get("position", {})
        x = pos.get("x", 0)
        y = pos.get("y", 0)
        z = pos.get("z", 1)
        rotation = pos.get("rotation", 0)

        entity = self.spawn_npc(template_id, x, y, z, rotation)
        if entity:
            # Отправляем подтверждение DM
            self.event_manager.post("dm_npc_spawn_result", {
                "success": True,
                "entity_id": entity.id,
                "template_id": template_id
            })

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
            "ai_state": ai.state.name if ai else "IDLE"
        }

        self._npc_network_data[entity.id] = data
