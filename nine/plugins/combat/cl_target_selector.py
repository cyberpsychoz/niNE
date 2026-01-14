"""
Target Selector - клиентский модуль выбора целей.
Переключение между режимом камеры и курсора (клавиша C).
"""

from typing import Optional
from panda3d.core import (
    CollisionTraverser, CollisionNode, CollisionRay,
    CollisionHandlerQueue, GeomNode, WindowProperties,
    Point3, Vec3, BitMask32
)
from direct.gui.OnscreenText import OnscreenText

from nine.core.plugins import PluginModule


class TargetSelector(PluginModule):
    """
    Система выбора целей с переключением режима курсора.
    - Клавиша C: переключение между режимом камеры и курсора
    - В режиме курсора: клик по сущности выбирает её как цель
    """

    def on_load(self):
        self.logger.info("Target Selector loaded")

        # Состояние
        self.cursor_mode = False           # Режим курсора активен
        self.is_in_combat = False          # Находимся в бою
        self.hovered_entity_id = None      # ID сущности под курсором
        self.selected_entity_id = None     # Выбранная цель

        # Подсветка
        self.highlight_node = None
        self.target_indicator = None

        # UI элементы
        self.cursor_mode_hint = None

        # Настройка picking
        self._setup_picker()

        # Подписки на события
        self.base.accept("c", self._toggle_cursor_mode)
        self.base.accept("mouse1", self._on_left_click)
        self.base.accept("mouse3", self._on_right_click)

        self.event_manager.subscribe("combat_started", self._on_combat_started)
        self.event_manager.subscribe("combat_ended", self._on_combat_ended)
        self.event_manager.subscribe("combat_turn_start", self._on_turn_start)

    def on_unload(self):
        self.base.ignore("c")
        self.base.ignore("mouse1")
        self.base.ignore("mouse3")

        self.event_manager.unsubscribe("combat_started", self._on_combat_started)
        self.event_manager.unsubscribe("combat_ended", self._on_combat_ended)
        self.event_manager.unsubscribe("combat_turn_start", self._on_turn_start)

        if self.cursor_mode:
            self._disable_cursor_mode()

        self._cleanup_ui()

        self.logger.info("Target Selector unloaded")

    def _setup_picker(self):
        """Настраивает систему raycasting для выбора объектов."""
        self.picker_traverser = CollisionTraverser("targetPicker")
        self.picker_handler = CollisionHandlerQueue()

        # Создаём луч от камеры
        self.picker_node = CollisionNode("mouseRay")
        self.picker_node.setFromCollideMask(GeomNode.getDefaultCollideMask())
        self.picker_node.setIntoCollideMask(BitMask32.allOff())

        self.picker_ray = CollisionRay()
        self.picker_node.addSolid(self.picker_ray)

        self.picker_np = self.base.camera.attachNewNode(self.picker_node)
        self.picker_traverser.addCollider(self.picker_np, self.picker_handler)

    # =========================================================================
    # Переключение режима
    # =========================================================================

    def _toggle_cursor_mode(self):
        """Переключает между режимом камеры и курсора."""
        # Не переключаем если открыт чат или меню
        if hasattr(self.base, 'is_chat_active') and self.base.is_chat_active():
            return
        if hasattr(self.base, 'in_game_menu_active') and self.base.in_game_menu_active:
            return

        if self.cursor_mode:
            self._disable_cursor_mode()
        else:
            self._enable_cursor_mode()

    def _enable_cursor_mode(self):
        """Включает режим курсора."""
        self.cursor_mode = True

        # Останавливаем камеру
        if hasattr(self.base, 'camera_controller') and self.base.camera_controller:
            self.base.camera_controller.stop()
        else:
            # Показываем курсор вручную
            props = WindowProperties()
            props.setCursorHidden(False)
            props.setMouseMode(WindowProperties.M_absolute)
            self.base.win.requestProperties(props)

        # Запускаем задачу обновления наведения
        self.base.taskMgr.add(self._update_hover_task, "target-hover-task")

        # Показываем подсказку
        self._show_cursor_mode_hint()

        self.logger.debug("Cursor mode enabled")

    def _disable_cursor_mode(self):
        """Выключает режим курсора."""
        self.cursor_mode = False

        # Возобновляем камеру
        if hasattr(self.base, 'camera_controller') and self.base.camera_controller:
            self.base.camera_controller.start()
        else:
            # Скрываем курсор вручную
            props = WindowProperties()
            props.setCursorHidden(True)
            props.setMouseMode(WindowProperties.M_relative)
            self.base.win.requestProperties(props)

        # Останавливаем задачу
        self.base.taskMgr.remove("target-hover-task")

        # Убираем подсветку
        self._clear_hover()

        # Скрываем подсказку
        self._hide_cursor_mode_hint()

        self.logger.debug("Cursor mode disabled")

    # =========================================================================
    # Обновление наведения
    # =========================================================================

    def _update_hover_task(self, task):
        """Обновляет сущность под курсором."""
        if not self.cursor_mode:
            return task.done

        # Проверяем наличие мыши в окне
        if not self.base.mouseWatcherNode.hasMouse():
            return task.cont

        # Получаем позицию мыши
        mouse_pos = self.base.mouseWatcherNode.getMouse()

        # Устанавливаем луч от камеры через позицию мыши
        self.picker_ray.setFromLens(
            self.base.camNode,
            mouse_pos.getX(),
            mouse_pos.getY()
        )

        # Выполняем raycast
        self.picker_traverser.traverse(self.base.render)

        # Обрабатываем результаты
        if self.picker_handler.getNumEntries() > 0:
            self.picker_handler.sortEntries()
            entry = self.picker_handler.getEntry(0)

            # Получаем узел, в который попали
            into_node = entry.getIntoNodePath()
            entity_id = self._extract_entity_id(into_node)

            if entity_id and entity_id != self.hovered_entity_id:
                self._set_hover(entity_id)
        else:
            self._clear_hover()

        return task.cont

    def _extract_entity_id(self, node_path) -> Optional[str]:
        """Извлекает ID сущности из узла."""
        # Ищем среди родителей узел с тегом entity_id
        current = node_path
        while current and current != self.base.render:
            # Проверяем python tag
            if current.hasPythonTag("entity_id"):
                return current.getPythonTag("entity_id")

            # Проверяем имя узла (npc_XXX или player_XXX)
            name = current.getName()
            if name.startswith("npc_"):
                return name[4:]  # Убираем префикс "npc_"
            if name.startswith("player_"):
                return name[7:]  # Убираем префикс "player_"

            current = current.getParent()

        return None

    def _set_hover(self, entity_id: str):
        """Устанавливает подсветку на сущность."""
        # Убираем предыдущую подсветку
        self._clear_hover()

        self.hovered_entity_id = entity_id

        # Применяем подсветку
        self._apply_highlight(entity_id)

        self.logger.debug(f"Hovering over: {entity_id}")

    def _clear_hover(self):
        """Убирает подсветку."""
        if self.hovered_entity_id:
            self._remove_highlight(self.hovered_entity_id)
            self.hovered_entity_id = None

    def _apply_highlight(self, entity_id: str):
        """Применяет визуальную подсветку к сущности."""
        # Ищем узел сущности
        node = self._find_entity_node(entity_id)
        if node:
            # Сохраняем оригинальный цвет и применяем подсветку
            if not node.hasColorScale():
                node.setColorScale(1.2, 1.2, 0.8, 1.0)  # Жёлтоватая подсветка

    def _remove_highlight(self, entity_id: str):
        """Убирает подсветку с сущности."""
        node = self._find_entity_node(entity_id)
        if node:
            node.clearColorScale()

    def _find_entity_node(self, entity_id: str):
        """Находит узел сущности по ID."""
        # Ищем NPC
        npc_node = self.base.render.find(f"**/npc_{entity_id}")
        if not npc_node.isEmpty():
            return npc_node

        # Ищем игрока
        player_node = self.base.render.find(f"**/player_{entity_id}")
        if not player_node.isEmpty():
            return player_node

        return None

    # =========================================================================
    # Обработка кликов
    # =========================================================================

    def _on_left_click(self):
        """Обрабатывает левый клик мыши."""
        if not self.cursor_mode:
            return

        if self.hovered_entity_id:
            self._select_target(self.hovered_entity_id)

    def _on_right_click(self):
        """Обрабатывает правый клик мыши (контекстное меню)."""
        if not self.cursor_mode:
            return

        if self.hovered_entity_id:
            # TODO: показать контекстное меню с действиями
            self._show_context_menu(self.hovered_entity_id)

    def _select_target(self, entity_id: str):
        """Выбирает сущность как цель."""
        # Убираем выделение с предыдущей цели
        if self.selected_entity_id:
            self._remove_selection_indicator(self.selected_entity_id)

        self.selected_entity_id = entity_id

        # Показываем индикатор выбора
        self._show_selection_indicator(entity_id)

        # Оповещаем систему
        self.event_manager.post("target_selected", {
            "target_id": entity_id,
        })

        self.logger.info(f"Target selected: {entity_id}")

    def _show_selection_indicator(self, entity_id: str):
        """Показывает индикатор выбранной цели."""
        node = self._find_entity_node(entity_id)
        if node:
            # Красная обводка для выбранной цели
            node.setColorScale(1.0, 0.5, 0.5, 1.0)

    def _remove_selection_indicator(self, entity_id: str):
        """Убирает индикатор выбора."""
        node = self._find_entity_node(entity_id)
        if node:
            node.clearColorScale()

    def _show_context_menu(self, entity_id: str):
        """Показывает контекстное меню для сущности."""
        # TODO: реализовать контекстное меню с действиями
        # Атака, Осмотреть, Поговорить и т.д.
        self.logger.debug(f"Context menu for: {entity_id}")

    # =========================================================================
    # UI
    # =========================================================================

    def _show_cursor_mode_hint(self):
        """Показывает подсказку о режиме курсора."""
        if not self.cursor_mode_hint:
            self.cursor_mode_hint = OnscreenText(
                text="[C] Режим выбора цели",
                pos=(0, 0.9),
                scale=0.05,
                fg=(1, 1, 0.5, 0.8),
                shadow=(0, 0, 0, 0.5),
                mayChange=True
            )

    def _hide_cursor_mode_hint(self):
        """Скрывает подсказку."""
        if self.cursor_mode_hint:
            self.cursor_mode_hint.destroy()
            self.cursor_mode_hint = None

    def _cleanup_ui(self):
        """Очищает все UI элементы."""
        self._hide_cursor_mode_hint()
        if self.selected_entity_id:
            self._remove_selection_indicator(self.selected_entity_id)

    # =========================================================================
    # Обработчики событий боя
    # =========================================================================

    def _on_combat_started(self, data: dict):
        """Обрабатывает начало боя."""
        self.is_in_combat = True

        # Автоматически включаем режим курсора при входе в бой
        if not self.cursor_mode:
            self._enable_cursor_mode()

    def _on_combat_ended(self, data: dict):
        """Обрабатывает окончание боя."""
        self.is_in_combat = False

        # Очищаем выбор
        if self.selected_entity_id:
            self._remove_selection_indicator(self.selected_entity_id)
            self.selected_entity_id = None

        # Возвращаем режим камеры
        if self.cursor_mode:
            self._disable_cursor_mode()

    def _on_turn_start(self, data: dict):
        """Обрабатывает начало хода."""
        # Если это наш ход, убедимся что курсор активен
        is_my_turn = data.get("is_player", False)
        if is_my_turn and not self.cursor_mode:
            self._enable_cursor_mode()

    # =========================================================================
    # Публичные методы
    # =========================================================================

    def get_selected_target(self) -> Optional[str]:
        """Возвращает ID выбранной цели."""
        return self.selected_entity_id

    def clear_selection(self):
        """Очищает выбор цели."""
        if self.selected_entity_id:
            self._remove_selection_indicator(self.selected_entity_id)
            self.selected_entity_id = None

    def is_cursor_mode_active(self) -> bool:
        """Возвращает True если режим курсора активен."""
        return self.cursor_mode
