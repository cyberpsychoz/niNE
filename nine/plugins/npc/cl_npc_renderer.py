"""
Клиентский рендерер NPC.

Отображает NPC в игровом мире на основе данных от сервера.
"""

from __future__ import annotations

from typing import Dict, Optional, TYPE_CHECKING
from panda3d.core import Vec3, TextNode, NodePath
from direct.actor.Actor import Actor
from direct.gui.OnscreenText import OnscreenText
import logging

from nine.core.plugins import PluginModule, PluginContext

if TYPE_CHECKING:
    from direct.showbase.ShowBase import ShowBase

logger = logging.getLogger(__name__)


class NPCRenderer:
    """
    Рендерит одного NPC на клиенте.

    Управляет Actor, именем над головой и интерполяцией движения.
    """

    def __init__(self, entity_id: str, data: dict, render: NodePath, base: 'ShowBase'):
        self.entity_id = entity_id
        self.base = base
        self._data = data

        # Позиция
        self.position = Vec3(
            data.get("position", {}).get("x", 0),
            data.get("position", {}).get("y", 0),
            data.get("position", {}).get("z", 0)
        )
        self.target_position = self.position
        self.rotation = data.get("position", {}).get("rotation", 0)

        # Скорость для интерполяции
        self.velocity = Vec3(
            data.get("velocity", {}).get("x", 0),
            data.get("velocity", {}).get("y", 0),
            0
        )

        # Модель
        self.model_path = data.get("model", "")
        self.actor: Optional[Actor] = None
        self.node: Optional[NodePath] = None

        # Имя над головой
        self.name_tag: Optional[OnscreenText] = None
        self.display_name = data.get("display_name", "NPC")

        # Состояние
        self.is_dead = data.get("is_dead", False)
        self.current_animation = "idle"
        self.ai_state = data.get("ai_state", "IDLE")

        # HP для отображения
        self.hp_current = data.get("hp_current", 0)
        self.hp_max = data.get("hp_max", 0)

        # Animation name map (populated in _create_visual)
        self._anim_map = {}

        # Создаём визуальное представление
        self._create_visual(render)

    def _create_visual(self, render: NodePath):
        """Создаёт визуальное представление NPC."""
        # Создаём корневой узел
        self.node = render.attachNewNode(f"npc_{self.entity_id[:8]}")
        self.node.setPos(self.position)
        self.node.setH(self.rotation)

        # Пытаемся загрузить модель (с fallback)
        model_loaded = False
        model_files = [
            "nine/assets/models/base.bam",
            "nine/assets/models/player2.bam",
        ]
        for model_file in model_files:
            try:
                self.actor = Actor(model_file)
                logger.debug(f"Loaded NPC model: {model_file}")
                break
            except Exception as e:
                logger.debug(f"Failed to load NPC model {model_file}: {e}")
                self.actor = None
                continue

        if self.actor:
            try:
                self.actor.reparentTo(self.node)
                self.actor.setScale(0.3)

                # Build animation name map (same as player actors)
                anim_names = self.actor.getAnimNames()
                fallback = anim_names[0] if anim_names else None
                self._anim_map = {}
                for name in ("idle", "walk_forward", "run_forward"):
                    self._anim_map[name] = name if name in anim_names else fallback

                # Start idle animation
                idle_anim = self._anim_map.get("idle")
                if idle_anim:
                    self.actor.loop(idle_anim)

                # Применяем цвет в зависимости от типа NPC
                color_map = {
                    "goblin": (0.4, 0.6, 0.3, 1),
                    "skeleton": (0.9, 0.9, 0.8, 1),
                    "bandit": (0.6, 0.4, 0.3, 1),
                    "wolf": (0.5, 0.5, 0.5, 1),
                }
                npc_type = self.model_path if self.model_path else "default"
                if npc_type in color_map:
                    self.actor.setColorScale(color_map[npc_type])
                else:
                    self.actor.setColorScale(0.7, 0.7, 0.7, 1)

                model_loaded = True
            except Exception as e:
                logger.warning(f"Failed to setup NPC model: {e}")

        # Если модель не загрузилась — создаём placeholder
        if not model_loaded:
            self._create_placeholder()

        # Создаём имя над головой
        self._create_name_tag()

    def _create_placeholder(self):
        """Создаёт placeholder модель (простой куб)."""
        try:
            # Используем встроенную модель Panda3D
            placeholder = self.base.loader.loadModel("models/misc/sphere")
            if placeholder:
                placeholder.reparentTo(self.node)
                placeholder.setScale(0.5, 0.5, 1.0)
                placeholder.setPos(0, 0, 0.5)

                # Красный цвет для врагов, синий для нейтральных
                if self.ai_state in ["ATTACKING", "PURSUING"]:
                    placeholder.setColor(1, 0.2, 0.2, 1)
                else:
                    placeholder.setColor(0.2, 0.5, 1, 1)
        except Exception as e:
            logger.warning(f"Failed to create placeholder: {e}")

    def _create_name_tag(self):
        """Создаёт текст с именем над NPC."""
        try:
            # Определяем цвет по AI состоянию
            if self.is_dead:
                color = (0.5, 0.5, 0.5, 0.7)
            elif self.ai_state in ["ATTACKING", "PURSUING"]:
                color = (1, 0.3, 0.3, 1)
            else:
                color = (0.3, 1, 0.3, 1)

            # HP строка
            hp_str = f" [{self.hp_current}/{self.hp_max}]" if self.hp_max > 0 else ""

            # Создаём 3D текст
            text_node = TextNode(f"npc_name_{self.entity_id[:8]}")
            text_node.setText(f"{self.display_name}{hp_str}")
            text_node.setAlign(TextNode.ACenter)
            text_node.setTextColor(*color)

            self.name_tag = self.node.attachNewNode(text_node)
            self.name_tag.setScale(0.3)
            self.name_tag.setPos(0, 0, 2.2)  # Над головой
            self.name_tag.setBillboardPointEye()  # Всегда смотрит на камеру
        except Exception as e:
            logger.warning(f"Failed to create name tag: {e}")

    def update(self, dt: float, data: dict):
        """Обновляет NPC на основе данных от сервера."""
        self._data = data

        # Обновляем целевую позицию
        new_pos = Vec3(
            data.get("position", {}).get("x", self.position.x),
            data.get("position", {}).get("y", self.position.y),
            data.get("position", {}).get("z", self.position.z)
        )
        self.target_position = new_pos
        self.rotation = data.get("position", {}).get("rotation", self.rotation)

        # Обновляем скорость
        self.velocity = Vec3(
            data.get("velocity", {}).get("x", 0),
            data.get("velocity", {}).get("y", 0),
            0
        )

        # Интерполяция позиции
        self._interpolate_position(dt)

        # Обновляем состояние
        self.ai_state = data.get("ai_state", "IDLE")
        self.is_dead = data.get("is_dead", False)
        self.hp_current = data.get("hp_current", self.hp_current)
        self.hp_max = data.get("hp_max", self.hp_max)

        # Обновляем анимацию
        new_anim = data.get("animation", "idle")
        if new_anim != self.current_animation:
            self._play_animation(new_anim)

        # Обновляем имя (цвет/HP)
        self._update_name_tag()

    def _interpolate_position(self, dt: float):
        """Интерполирует позицию для плавного движения."""
        # Простая линейная интерполяция к целевой позиции
        diff = self.target_position - self.position
        distance = diff.length()

        if distance > 0.01:
            # Скорость интерполяции
            speed = max(distance * 5, 2.0)  # Минимум 2 units/sec
            move_amount = min(speed * dt, distance)

            direction = diff / distance
            self.position += direction * move_amount

        if self.node:
            self.node.setPos(self.position)
            self.node.setH(self.rotation)

    def _play_animation(self, anim_name: str):
        """Проигрывает анимацию."""
        self.current_animation = anim_name
        if self.actor:
            try:
                # Resolve animation name via map (handles model mismatch)
                anim_map = getattr(self, '_anim_map', {})
                resolved = anim_map.get(anim_name, anim_name)
                if resolved:
                    self.actor.loop(resolved)
            except Exception as e:
                logger.debug(f"NPC animation error for '{anim_name}': {e}")

    def _update_name_tag(self):
        """Обновляет текст имени."""
        if self.name_tag:
            # Определяем цвет
            if self.is_dead:
                color = (0.5, 0.5, 0.5, 0.7)
            elif self.ai_state in ["ATTACKING", "PURSUING"]:
                color = (1, 0.3, 0.3, 1)
            else:
                color = (0.3, 1, 0.3, 1)

            hp_str = f" [{self.hp_current}/{self.hp_max}]" if self.hp_max > 0 else ""
            text_node = self.name_tag.node()
            text_node.setText(f"{self.display_name}{hp_str}")
            text_node.setTextColor(*color)

    def destroy(self):
        """Удаляет визуальное представление."""
        if self.actor:
            self.actor.cleanup()
            self.actor = None

        if self.name_tag:
            self.name_tag.removeNode()
            self.name_tag = None

        if self.node:
            self.node.removeNode()
            self.node = None


class NPCClientModule(PluginModule):
    """
    Клиентский модуль рендеринга NPC.

    Получает данные NPC от сервера и отображает их в игровом мире.
    """

    # How many seconds an NPC can be absent from world_state before removal.
    # Server uses delta compression — only sends NPCs whose state changed.
    STALE_TIMEOUT = 5.0

    def __init__(self, context: PluginContext):
        super().__init__(context)
        self._renderers: Dict[str, NPCRenderer] = {}
        self._last_seen: Dict[str, float] = {}  # entity_id -> timestamp

    def on_load(self):
        """Инициализация модуля."""
        # Подписываемся на world_state с NPC данными
        self.event_manager.subscribe("world_state_received", self._on_world_state)

        # Добавляем задачу обновления
        self.app.taskMgr.add(self._update_task, "npc_renderer_update")

        self.logger.info("NPC Client Module loaded")

    def on_unload(self):
        """Очистка модуля."""
        self.event_manager.unsubscribe("world_state_received", self._on_world_state)
        self.app.taskMgr.remove("npc_renderer_update")

        # Удаляем все рендереры
        for renderer in self._renderers.values():
            renderer.destroy()
        self._renderers.clear()
        self._last_seen.clear()

        self.logger.info("NPC Client Module unloaded")

    def _on_world_state(self, data: dict):
        """Обрабатывает world_state с NPC данными."""
        import time
        now = time.time()
        npcs = data.get("npcs", [])

        # Обновляем существующих NPC и создаём новых
        for npc_data in npcs:
            entity_id = npc_data.get("entity_id")
            if not entity_id:
                continue

            self._last_seen[entity_id] = now

            if entity_id in self._renderers:
                # Обновляем существующего
                self._renderers[entity_id].update(0, npc_data)
            else:
                # Создаём нового
                self.logger.info(f"[NPC_RENDERER] Creating NPC: {entity_id[:8]}, name={npc_data.get('display_name')}")
                renderer = NPCRenderer(
                    entity_id,
                    npc_data,
                    self.app.render,
                    self.app
                )
                self._renderers[entity_id] = renderer

        # Remove NPCs that haven't been seen for STALE_TIMEOUT seconds
        to_remove = []
        for entity_id in self._renderers:
            if now - self._last_seen.get(entity_id, 0) > self.STALE_TIMEOUT:
                to_remove.append(entity_id)

        for entity_id in to_remove:
            self.logger.info(f"[NPC_RENDERER] Removing stale NPC: {entity_id[:8]}")
            self._renderers[entity_id].destroy()
            del self._renderers[entity_id]
            self._last_seen.pop(entity_id, None)

    def _update_task(self, task):
        """Задача обновления интерполяции."""
        dt = globalClock.getDt()

        for renderer in self._renderers.values():
            renderer._interpolate_position(dt)

        return task.cont


from panda3d.core import ClockObject
globalClock = ClockObject.getGlobalClock()
