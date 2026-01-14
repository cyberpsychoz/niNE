"""
Action Bar - панель действий в бою.
Отображается внизу экрана во время боя.
"""

from typing import Dict, Optional, Callable
from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectLabel, DirectWaitBar
)
from panda3d.core import TextNode

from nine.core.plugins import PluginModule
from nine.plugins.combat.sh_action_economy import COMBAT_ACTIONS, ActionCost


class ActionBar(PluginModule):
    """
    Панель действий для пошагового боя.
    - Кнопки основных действий (Атака, Рывок, Отход, Уклонение, Помощь, Конец хода)
    - Индикаторы ресурсов (Движение, Действие, Бонус, Реакция)
    - Активна только в ваш ход
    """

    def on_load(self):
        self.logger.info("Action Bar loaded")

        # Состояние
        self.is_visible = False
        self.is_my_turn = False
        self.is_enabled = False

        # Ресурсы хода
        self.movement_remaining = 30.0
        self.movement_speed = 30.0
        self.has_action = True
        self.has_bonus_action = True
        self.has_reaction = True

        # UI элементы
        self.container = None
        self.action_buttons: Dict[str, DirectButton] = {}
        self.resource_indicators: Dict[str, DirectFrame] = {}

        # Подписки
        self.event_manager.subscribe("combat_started", self._on_combat_started)
        self.event_manager.subscribe("combat_ended", self._on_combat_ended)
        self.event_manager.subscribe("combat_turn_start", self._on_turn_start)
        self.event_manager.subscribe("combat_action_result", self._on_action_result)

    def on_unload(self):
        self.event_manager.unsubscribe("combat_started", self._on_combat_started)
        self.event_manager.unsubscribe("combat_ended", self._on_combat_ended)
        self.event_manager.unsubscribe("combat_turn_start", self._on_turn_start)
        self.event_manager.unsubscribe("combat_action_result", self._on_action_result)

        self._destroy_ui()

        self.logger.info("Action Bar unloaded")

    # =========================================================================
    # Создание UI
    # =========================================================================

    def _create_ui(self):
        """Создаёт UI панели действий."""
        if self.container:
            return

        # Главный контейнер (внизу экрана по центру)
        self.container = DirectFrame(
            frameColor=(0.1, 0.1, 0.15, 0.9),
            frameSize=(-0.7, 0.7, -0.12, 0.12),
            pos=(0, 0, -0.82),
            sortOrder=10
        )

        # Создаём кнопки действий
        self._create_action_buttons()

        # Создаём индикаторы ресурсов
        self._create_resource_indicators()

        self.is_visible = True

    def _destroy_ui(self):
        """Уничтожает UI."""
        if self.container:
            self.container.destroy()
            self.container = None
        self.action_buttons.clear()
        self.resource_indicators.clear()
        self.is_visible = False

    def _create_action_buttons(self):
        """Создаёт кнопки действий."""
        # Основные действия для отображения
        actions = [
            ("attack", "1"),
            ("dash", "2"),
            ("disengage", "3"),
            ("dodge", "4"),
            ("help", "5"),
            ("end_turn", "E"),
        ]

        x_start = -0.55
        x_spacing = 0.18
        y_pos = 0.03

        for i, (action_id, hotkey) in enumerate(actions):
            action = COMBAT_ACTIONS.get(action_id)
            if not action:
                continue

            x_pos = x_start + i * x_spacing

            # Кнопка действия
            btn = DirectButton(
                parent=self.container,
                text=action.name_ru,
                text_scale=0.035,
                text_fg=(1, 1, 1, 1),
                frameColor=(0.25, 0.25, 0.3, 1),
                frameSize=(-0.075, 0.075, -0.035, 0.035),
                pos=(x_pos, 0, y_pos),
                relief=1,
                command=self._on_action_click,
                extraArgs=[action_id]
            )

            # Горячая клавиша
            hotkey_label = DirectLabel(
                parent=btn,
                text=f"[{hotkey}]",
                text_scale=0.025,
                text_fg=(0.7, 0.7, 0.5, 1),
                pos=(0, 0, -0.055),
                frameColor=(0, 0, 0, 0)
            )

            self.action_buttons[action_id] = btn

            # Привязываем горячую клавишу
            self.base.accept(hotkey.lower(), self._on_action_click, [action_id])

    def _create_resource_indicators(self):
        """Создаёт индикаторы ресурсов."""
        # Контейнер для ресурсов (вверху панели)
        resources_frame = DirectFrame(
            parent=self.container,
            frameColor=(0, 0, 0, 0),
            pos=(0.45, 0, 0.03)
        )

        # Движение
        self.movement_bar = DirectWaitBar(
            parent=resources_frame,
            range=100,
            value=100,
            barColor=(0.3, 0.6, 0.9, 1),
            frameColor=(0.15, 0.15, 0.15, 1),
            frameSize=(-0.12, 0.12, -0.015, 0.015),
            pos=(0, 0, 0.04)
        )

        self.movement_label = DirectLabel(
            parent=resources_frame,
            text="30 фт",
            text_scale=0.03,
            text_fg=(0.8, 0.8, 0.8, 1),
            pos=(0, 0, 0.04),
            frameColor=(0, 0, 0, 0)
        )

        move_title = DirectLabel(
            parent=resources_frame,
            text="Движение",
            text_scale=0.025,
            text_fg=(0.6, 0.6, 0.6, 1),
            pos=(0, 0, 0.07),
            frameColor=(0, 0, 0, 0)
        )

        # Индикаторы действий (Д, Б, Р)
        action_types = [
            ("action", "Д", "Действие", -0.08),
            ("bonus", "Б", "Бонусное", 0.0),
            ("reaction", "Р", "Реакция", 0.08),
        ]

        for res_id, letter, tooltip, x_offset in action_types:
            indicator = DirectFrame(
                parent=resources_frame,
                frameColor=(0.2, 0.5, 0.2, 1),  # Зелёный = доступно
                frameSize=(-0.025, 0.025, -0.025, 0.025),
                pos=(x_offset, 0, -0.04)
            )

            letter_label = DirectLabel(
                parent=indicator,
                text=letter,
                text_scale=0.03,
                text_fg=(1, 1, 1, 1),
                pos=(0, 0, -0.005),
                frameColor=(0, 0, 0, 0)
            )

            self.resource_indicators[res_id] = indicator

    # =========================================================================
    # Обновление UI
    # =========================================================================

    def _update_resources(self, resources: dict):
        """Обновляет отображение ресурсов."""
        self.movement_remaining = resources.get("movement", 30.0)
        self.has_action = resources.get("has_action", True)
        self.has_bonus_action = resources.get("has_bonus_action", True)
        self.has_reaction = resources.get("has_reaction", True)

        # Обновляем бар движения
        if self.movement_bar and self.movement_label:
            ratio = self.movement_remaining / max(self.movement_speed, 1)
            self.movement_bar["value"] = ratio * 100
            self.movement_label["text"] = f"{int(self.movement_remaining)} фт"

        # Обновляем индикаторы
        self._update_indicator("action", self.has_action)
        self._update_indicator("bonus", self.has_bonus_action)
        self._update_indicator("reaction", self.has_reaction)

        # Обновляем доступность кнопок
        self._update_button_states()

    def _update_indicator(self, res_id: str, is_available: bool):
        """Обновляет цвет индикатора."""
        indicator = self.resource_indicators.get(res_id)
        if indicator:
            if is_available:
                indicator["frameColor"] = (0.2, 0.5, 0.2, 1)  # Зелёный
            else:
                indicator["frameColor"] = (0.4, 0.4, 0.4, 0.5)  # Серый

    def _update_button_states(self):
        """Обновляет состояние кнопок на основе ресурсов."""
        for action_id, btn in self.action_buttons.items():
            action = COMBAT_ACTIONS.get(action_id)
            if not action:
                continue

            # Проверяем можно ли использовать действие
            can_use = self._can_use_action(action)

            if can_use and self.is_my_turn:
                btn["state"] = 1  # Normal
                btn["frameColor"] = (0.25, 0.25, 0.3, 1)
                btn["text_fg"] = (1, 1, 1, 1)
            else:
                btn["state"] = 0  # Disabled
                btn["frameColor"] = (0.2, 0.2, 0.2, 0.5)
                btn["text_fg"] = (0.5, 0.5, 0.5, 1)

    def _can_use_action(self, action) -> bool:
        """Проверяет, можно ли использовать действие."""
        if action.cost == ActionCost.NONE:
            return True
        if action.cost == ActionCost.ACTION:
            return self.has_action
        if action.cost == ActionCost.BONUS:
            return self.has_bonus_action
        if action.cost == ActionCost.REACTION:
            return self.has_reaction
        return True

    def _set_enabled(self, enabled: bool):
        """Включает/выключает панель."""
        self.is_enabled = enabled
        self.is_my_turn = enabled

        if self.container:
            if enabled:
                self.container["frameColor"] = (0.12, 0.15, 0.12, 0.95)
            else:
                self.container["frameColor"] = (0.1, 0.1, 0.15, 0.7)

        self._update_button_states()

    # =========================================================================
    # Обработка действий
    # =========================================================================

    def _on_action_click(self, action_id: str):
        """Обрабатывает клик по кнопке действия."""
        if not self.is_my_turn:
            return

        action = COMBAT_ACTIONS.get(action_id)
        if not action:
            return

        if not self._can_use_action(action):
            self._show_message("Недостаточно ресурсов")
            return

        # Для действий с целью - проверяем выбрана ли цель
        target_id = None
        if action.target_type.name not in ("NONE", "SELF"):
            target_id = self._get_selected_target()
            if not target_id:
                self._show_message("Выберите цель")
                return

        # Отправляем запрос на сервер
        self._send_action_request(action_id, target_id)

    def _get_selected_target(self) -> Optional[str]:
        """Получает выбранную цель из target selector."""
        # Ищем target selector среди модулей
        if hasattr(self.app, 'plugin_manager'):
            combat_plugin = self.app.plugin_manager.get_plugin("nine.combat")
            if combat_plugin:
                for module in combat_plugin.modules:
                    if hasattr(module, 'get_selected_target'):
                        return module.get_selected_target()
        return None

    def _send_action_request(self, action_id: str, target_id: Optional[str] = None):
        """Отправляет запрос действия на сервер."""
        self.event_manager.post("send_to_server", {
            "type": "combat_action",
            "action_id": action_id,
            "target_id": target_id,
        })

    def _show_message(self, message: str):
        """Показывает сообщение игроку."""
        self.event_manager.post("show_notification", {
            "message": message,
            "duration": 2.0,
        })

    # =========================================================================
    # Обработчики событий
    # =========================================================================

    def _on_combat_started(self, data: dict):
        """Обрабатывает начало боя."""
        self._create_ui()

    def _on_combat_ended(self, data: dict):
        """Обрабатывает окончание боя."""
        self._destroy_ui()

        # Отвязываем горячие клавиши
        for hotkey in ["1", "2", "3", "4", "5", "e"]:
            self.base.ignore(hotkey)

    def _on_turn_start(self, data: dict):
        """Обрабатывает начало хода."""
        is_my_turn = data.get("is_player", False)
        resources = data.get("resources", {})

        self.movement_speed = resources.get("movement", 30.0)
        self._update_resources(resources)
        self._set_enabled(is_my_turn)

    def _on_action_result(self, data: dict):
        """Обрабатывает результат действия."""
        # Обновляем ресурсы после действия
        result = data.get("result", {})

        if result.get("success"):
            action_id = data.get("action_id")
            action = COMBAT_ACTIONS.get(action_id)

            if action:
                # Локально обновляем ресурсы
                if action.cost == ActionCost.ACTION:
                    self.has_action = False
                elif action.cost == ActionCost.BONUS:
                    self.has_bonus_action = False
                elif action.cost == ActionCost.REACTION:
                    self.has_reaction = False

            # Обновляем движение если был Dash
            if action_id == "dash" and "new_movement" in result:
                self.movement_remaining = result["new_movement"]

            self._update_resources({
                "movement": self.movement_remaining,
                "has_action": self.has_action,
                "has_bonus_action": self.has_bonus_action,
                "has_reaction": self.has_reaction,
            })

    # =========================================================================
    # Публичные методы
    # =========================================================================

    def show(self):
        """Показывает панель."""
        if self.container:
            self.container.show()
            self.is_visible = True

    def hide(self):
        """Скрывает панель."""
        if self.container:
            self.container.hide()
            self.is_visible = False
