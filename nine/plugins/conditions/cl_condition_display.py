"""
Клиентский модуль отображения состояний.

Показывает иконки активных состояний над персонажами и в UI.
"""

from typing import Dict, List, Optional

from direct.gui.DirectGui import DirectFrame, DirectLabel, DGG
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode

from nine.core.plugins import PluginModule


class ConditionDisplayClientModule(PluginModule, DirectObject):
    """
    Клиентский модуль отображения состояний.
    """

    def on_load(self):
        # UI элементы
        self._condition_frame: Optional[DirectFrame] = None
        self._condition_icons: Dict[str, DirectLabel] = {}

        # Кеш состояний сущностей
        # entity_id -> list of condition data
        self._entity_conditions: Dict[str, List[dict]] = {}

        # ID локального игрока
        self._local_player_id: Optional[str] = None

        # Only create DirectGUI when not using web UI
        if not self.app.ui_is_web:
            self._create_ui()

        # Подписки на события (always — forwarding handles web UI)
        self.event_manager.subscribe("conditions_update", self._on_conditions_update)
        self.event_manager.subscribe("character_selected", self._on_character_selected)
        self.event_manager.subscribe("game_state_changed", self._on_game_state_changed)

        self.logger.info("Condition Display клиентский модуль загружен")

    def on_unload(self):
        self.ignore_all()
        self.event_manager.unsubscribe("conditions_update", self._on_conditions_update)
        self.event_manager.unsubscribe("character_selected", self._on_character_selected)
        self.event_manager.unsubscribe("game_state_changed", self._on_game_state_changed)

        if self._condition_frame:
            self._condition_frame.destroy()
            self._condition_frame = None

        self.logger.info("Condition Display клиентский модуль выгружен")

    # =========================================================================
    # UI Creation
    # =========================================================================

    def _create_ui(self):
        """Создаёт UI для отображения состояний."""
        # Фрейм для иконок состояний (в верхней левой части экрана)
        self._condition_frame = DirectFrame(
            frameColor=(0, 0, 0, 0),
            frameSize=(-0.5, 0.5, -0.1, 0.1),
            pos=(-0.9, 0, 0.85),
        )

        # Заголовок
        self._conditions_label = DirectLabel(
            parent=self._condition_frame,
            text="",
            text_scale=0.03,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            pos=(-0.48, 0, 0.06),
            frameColor=(0, 0, 0, 0),
        )

    def _update_condition_display(self):
        """Обновляет отображение состояний локального игрока."""
        # Очищаем старые иконки
        for label in self._condition_icons.values():
            label.destroy()
        self._condition_icons.clear()

        if not self._local_player_id:
            self._conditions_label["text"] = ""
            return

        conditions = self._entity_conditions.get(self._local_player_id, [])

        if not conditions:
            self._conditions_label["text"] = ""
            return

        self._conditions_label["text"] = "Conditions:"

        x_pos = -0.45
        for i, cond in enumerate(conditions):
            cond_id = cond.get("id", "")
            name = cond.get("name_ru", cond.get("name", cond_id))
            color = cond.get("color", (0.7, 0.7, 0.7, 1))
            duration = cond.get("duration", -1)

            # Текст с длительностью
            if duration > 0:
                text = f"{name} ({duration})"
            else:
                text = name

            label = DirectLabel(
                parent=self._condition_frame,
                text=text,
                text_scale=0.025,
                text_fg=color,
                text_align=TextNode.ALeft,
                frameColor=(0.1, 0.1, 0.15, 0.8),
                frameSize=(-0.01, 0.18, -0.015, 0.025),
                pos=(x_pos, 0, 0.02),
            )

            self._condition_icons[cond_id] = label
            x_pos += 0.2

            # Ограничиваем количество видимых иконок
            if i >= 4:
                break

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _on_conditions_update(self, data: dict):
        """Обновление состояний от сервера."""
        entity_id = data.get("entity_id", "")
        conditions = data.get("conditions", [])

        self._entity_conditions[entity_id] = conditions

        if self.app.ui_is_web:
            return  # Web UI handles display via GameHUD

        # Обновляем UI если это локальный игрок
        if entity_id == self._local_player_id:
            self._update_condition_display()

    def _on_character_selected(self, data: dict):
        """Выбран персонаж."""
        char_uuid = data.get("character_uuid", "")
        self._local_player_id = char_uuid

        # Запрашиваем состояния
        self.event_manager.post("conditions_request", {
            "entity_id": char_uuid,
        })

        if not self.app.ui_is_web:
            self._update_condition_display()

    def _on_game_state_changed(self, data: dict):
        """Изменение состояния игры."""
        state = data.get("state", "")

        if self.app.ui_is_web:
            if state == "disconnected":
                self._entity_conditions.clear()
                self._local_player_id = None
            return

        if state == "playing":
            if self._condition_frame:
                self._condition_frame.show()
        elif state == "disconnected":
            if self._condition_frame:
                self._condition_frame.hide()
            self._entity_conditions.clear()
            self._local_player_id = None

    # =========================================================================
    # Public API
    # =========================================================================

    def get_conditions(self, entity_id: str) -> List[dict]:
        """Возвращает список состояний сущности."""
        return self._entity_conditions.get(entity_id, [])

    def has_condition(self, entity_id: str, condition_id: str) -> bool:
        """Проверяет наличие состояния у сущности."""
        conditions = self._entity_conditions.get(entity_id, [])
        for cond in conditions:
            if cond.get("id") == condition_id:
                return True
        return False
