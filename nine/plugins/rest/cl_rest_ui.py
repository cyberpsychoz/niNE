"""
Клиентский модуль UI отдыха.

Показывает диалог отдыха с возможностью тратить Hit Dice.
"""

from typing import Optional

from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectLabel, DGG
)
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode

from nine.core.plugins import PluginModule


class RestUIClientModule(PluginModule, DirectObject):
    """
    Клиентский модуль UI отдыха.
    """

    def on_load(self):
        # UI элементы
        self._rest_frame: Optional[DirectFrame] = None
        self._is_visible = False
        self._rest_type: str = "short"

        # Данные персонажа
        self._hp_current: int = 0
        self._hp_max: int = 1
        self._hit_dice_current: int = 1
        self._hit_dice_max: int = 1

        # Подписки на события
        self.event_manager.subscribe("show_rest_dialog", self._on_show_rest_dialog)
        self.event_manager.subscribe("rest_result", self._on_rest_result)
        self.event_manager.subscribe("hit_die_result", self._on_hit_die_result)
        self.event_manager.subscribe("character_sheet", self._on_character_update)
        self.event_manager.subscribe("game_state_changed", self._on_game_state_changed)

        self.logger.info("Rest UI клиентский модуль загружен")

    def on_unload(self):
        self.ignore_all()
        self.event_manager.unsubscribe("show_rest_dialog", self._on_show_rest_dialog)
        self.event_manager.unsubscribe("rest_result", self._on_rest_result)
        self.event_manager.unsubscribe("hit_die_result", self._on_hit_die_result)
        self.event_manager.unsubscribe("character_sheet", self._on_character_update)
        self.event_manager.unsubscribe("game_state_changed", self._on_game_state_changed)

        if self._rest_frame:
            self._rest_frame.destroy()
            self._rest_frame = None

        self.logger.info("Rest UI клиентский модуль выгружен")

    # =========================================================================
    # UI
    # =========================================================================

    def _create_ui(self):
        """Создаёт UI диалога отдыха."""
        self._rest_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.15, 0.95),
            frameSize=(-0.4, 0.4, -0.35, 0.35),
            pos=(0, 0, 0),
        )

        # Заголовок
        self._title_label = DirectLabel(
            parent=self._rest_frame,
            text="Rest",
            text_scale=0.05,
            text_fg=(0.9, 0.8, 0.5, 1),
            text_align=TextNode.ACenter,
            pos=(0, 0, 0.28),
            frameColor=(0, 0, 0, 0),
        )

        # Кнопка закрытия
        DirectButton(
            parent=self._rest_frame,
            text="X",
            text_scale=0.04,
            text_fg=(1, 0.3, 0.3, 1),
            frameColor=(0.3, 0.1, 0.1, 0.8),
            frameSize=(-0.03, 0.03, -0.025, 0.035),
            pos=(0.35, 0, 0.3),
            command=self.hide_rest_dialog,
        )

        # HP статус
        self._hp_label = DirectLabel(
            parent=self._rest_frame,
            text="HP: 0/0",
            text_scale=0.035,
            text_fg=(0.8, 0.4, 0.4, 1),
            text_align=TextNode.ACenter,
            pos=(0, 0, 0.18),
            frameColor=(0, 0, 0, 0),
        )

        # Hit Dice статус
        self._hit_dice_label = DirectLabel(
            parent=self._rest_frame,
            text="Hit Dice: 0/0",
            text_scale=0.035,
            text_fg=(0.6, 0.6, 0.9, 1),
            text_align=TextNode.ACenter,
            pos=(0, 0, 0.1),
            frameColor=(0, 0, 0, 0),
        )

        # Описание
        self._description_label = DirectLabel(
            parent=self._rest_frame,
            text="",
            text_scale=0.028,
            text_fg=(0.7, 0.7, 0.7, 1),
            text_align=TextNode.ACenter,
            text_wordwrap=28,
            pos=(0, 0, 0.0),
            frameColor=(0, 0, 0, 0),
        )

        # Кнопка Spend Hit Die (только для Short Rest)
        self._spend_die_button = DirectButton(
            parent=self._rest_frame,
            text="Spend Hit Die",
            text_scale=0.035,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.3, 0.3, 0.6, 0.9),
            frameSize=(-0.15, 0.15, -0.035, 0.04),
            pos=(0, 0, -0.1),
            command=self._on_spend_hit_die_click,
        )

        # Кнопка завершения отдыха
        self._finish_button = DirectButton(
            parent=self._rest_frame,
            text="Finish Rest",
            text_scale=0.035,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.5, 0.3, 0.9),
            frameSize=(-0.12, 0.12, -0.035, 0.04),
            pos=(0, 0, -0.2),
            command=self._on_finish_rest,
        )

        # Сообщение результата
        self._result_label = DirectLabel(
            parent=self._rest_frame,
            text="",
            text_scale=0.03,
            text_fg=(0.5, 1.0, 0.5, 1),
            text_align=TextNode.ACenter,
            pos=(0, 0, -0.28),
            frameColor=(0, 0, 0, 0),
        )

        self._rest_frame.hide()

    def _update_ui(self):
        """Обновляет UI."""
        self._hp_label["text"] = f"HP: {self._hp_current}/{self._hp_max}"

        # Цвет HP в зависимости от здоровья
        hp_ratio = self._hp_current / max(1, self._hp_max)
        if hp_ratio >= 0.7:
            self._hp_label["text_fg"] = (0.4, 0.9, 0.4, 1)
        elif hp_ratio >= 0.3:
            self._hp_label["text_fg"] = (0.9, 0.9, 0.4, 1)
        else:
            self._hp_label["text_fg"] = (0.9, 0.4, 0.4, 1)

        self._hit_dice_label["text"] = f"Hit Dice: {self._hit_dice_current}/{self._hit_dice_max}"

        # Обновляем кнопку Spend Hit Die
        if self._rest_type == "short" and self._hit_dice_current > 0 and self._hp_current < self._hp_max:
            self._spend_die_button["state"] = DGG.NORMAL
            self._spend_die_button["frameColor"] = (0.3, 0.3, 0.6, 0.9)
            self._spend_die_button.show()
        elif self._rest_type == "short":
            self._spend_die_button["state"] = DGG.DISABLED
            self._spend_die_button["frameColor"] = (0.3, 0.3, 0.3, 0.5)
            self._spend_die_button.show()
        else:
            self._spend_die_button.hide()

        # Описание в зависимости от типа отдыха
        if self._rest_type == "short":
            self._title_label["text"] = "Short Rest"
            self._description_label["text"] = (
                "During a short rest (1 hour), you can spend Hit Dice\n"
                "to heal. Each Hit Die heals 1dX + CON modifier HP."
            )
        else:
            self._title_label["text"] = "Long Rest"
            self._description_label["text"] = (
                "A long rest (8 hours) restores all HP,\n"
                "half your Hit Dice (minimum 1),\n"
                "and all spell slots."
            )

    # =========================================================================
    # Visibility
    # =========================================================================

    def show_rest_dialog(self, rest_type: str = "short"):
        """Показывает диалог отдыха."""
        if self._is_visible:
            return

        if not self._rest_frame:
            self._create_ui()

        self._rest_type = rest_type
        self._result_label["text"] = ""
        self._update_ui()

        self._rest_frame.show()
        self._is_visible = True

    def hide_rest_dialog(self):
        """Скрывает диалог отдыха."""
        if not self._is_visible:
            return

        if self._rest_frame:
            self._rest_frame.hide()

        self._is_visible = False

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _on_show_rest_dialog(self, data: dict):
        """Запрос на показ диалога отдыха."""
        rest_type = data.get("rest_type", "short")
        self.show_rest_dialog(rest_type)

    def _on_spend_hit_die_click(self):
        """Клик по кнопке Spend Hit Die."""
        self.event_manager.post("spend_hit_die", {"count": 1})

    def _on_finish_rest(self):
        """Клик по кнопке Finish Rest."""
        self.event_manager.post("rest_request", {"rest_type": self._rest_type})

    def _on_rest_result(self, data: dict):
        """Результат отдыха от сервера."""
        if not data.get("success"):
            self._result_label["text"] = f"Error: {data.get('error', 'Unknown')}"
            self._result_label["text_fg"] = (1.0, 0.4, 0.4, 1)
            return

        rest_type = data.get("rest_type", "short")

        if rest_type == "long":
            hp_restored = data.get("hp_restored", 0)
            self._result_label["text"] = f"Restored {hp_restored} HP. Fully rested!"
            self._result_label["text_fg"] = (0.5, 1.0, 0.5, 1)
        else:
            self._result_label["text"] = "Short rest complete."
            self._result_label["text_fg"] = (0.5, 1.0, 0.5, 1)

        # Обновляем локальные данные
        self._hp_current = data.get("hp_new", self._hp_current)
        self._hp_max = data.get("hp_max", self._hp_max)
        self._hit_dice_current = data.get("hit_dice_remaining", self._hit_dice_current)
        self._hit_dice_max = data.get("hit_dice_max", self._hit_dice_max)

        self._update_ui()

    def _on_hit_die_result(self, data: dict):
        """Результат траты Hit Die."""
        if not data.get("success"):
            self._result_label["text"] = data.get("message", "Cannot spend hit die")
            self._result_label["text_fg"] = (1.0, 0.7, 0.4, 1)
            return

        healing = data.get("healing", 0)
        self._result_label["text"] = f"Healed {healing} HP!"
        self._result_label["text_fg"] = (0.5, 1.0, 0.5, 1)

        # Обновляем локальные данные
        self._hp_current = data.get("hp_new", self._hp_current)
        self._hp_max = data.get("hp_max", self._hp_max)
        self._hit_dice_current = data.get("hit_dice_remaining", self._hit_dice_current)
        self._hit_dice_max = data.get("hit_dice_max", self._hit_dice_max)

        self._update_ui()

    def _on_character_update(self, data: dict):
        """Обновление данных персонажа."""
        char_data = data.get("character", {})

        self._hp_current = char_data.get("hp_current", self._hp_current)
        self._hp_max = char_data.get("hp_max", self._hp_max)
        self._hit_dice_current = char_data.get("hit_dice_current", self._hit_dice_current)
        self._hit_dice_max = char_data.get("hit_dice_max", self._hit_dice_max)

        if self._is_visible:
            self._update_ui()

    def _on_game_state_changed(self, data: dict):
        """Изменение состояния игры."""
        state = data.get("state", "")
        if state == "disconnected" and self._is_visible:
            self.hide_rest_dialog()
