"""
Клиентский модуль журнала квестов.

Открывается по клавише J.
"""

from typing import Dict, List, Optional

from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectLabel,
    DirectScrolledFrame, DGG
)
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode

from nine.core.plugins import PluginModule


class QuestLogClientModule(PluginModule, DirectObject):
    """
    Клиентский модуль журнала квестов.
    """

    def on_load(self):
        # UI элементы
        self._main_frame: Optional[DirectFrame] = None
        self._is_visible = False

        # Данные квестов
        self._quests: List[dict] = []
        self._selected_quest: Optional[dict] = None
        self._current_filter: str = "active"

        # Биндим клавишу J
        self.accept("j", self.toggle_quest_log)

        # Подписки на события
        self.event_manager.subscribe("quest_list", self._on_quest_list)
        self.event_manager.subscribe("quest_accepted", self._on_quest_accepted)
        self.event_manager.subscribe("quest_completed", self._on_quest_completed)
        self.event_manager.subscribe("quest_objective_progress", self._on_objective_progress)
        self.event_manager.subscribe("quest_ready_to_turn_in", self._on_ready_to_turn_in)
        self.event_manager.subscribe("game_state_changed", self._on_game_state_changed)

        self.logger.info("Quest Log клиентский модуль загружен (J)")

    def on_unload(self):
        self.ignore_all()
        self.event_manager.unsubscribe("quest_list", self._on_quest_list)
        self.event_manager.unsubscribe("quest_accepted", self._on_quest_accepted)
        self.event_manager.unsubscribe("quest_completed", self._on_quest_completed)
        self.event_manager.unsubscribe("quest_objective_progress", self._on_objective_progress)
        self.event_manager.unsubscribe("quest_ready_to_turn_in", self._on_ready_to_turn_in)
        self.event_manager.unsubscribe("game_state_changed", self._on_game_state_changed)

        if self._main_frame:
            self._main_frame.destroy()
            self._main_frame = None

        self.logger.info("Quest Log клиентский модуль выгружен")

    # =========================================================================
    # Toggle & Visibility
    # =========================================================================

    def toggle_quest_log(self):
        """Переключает видимость журнала квестов."""
        if self._is_visible:
            self.hide_quest_log()
        else:
            self.show_quest_log()

    def show_quest_log(self):
        """Показывает журнал квестов."""
        if self._is_visible:
            return

        if not self._main_frame:
            self._create_ui()

        # Запрашиваем список квестов
        self.event_manager.post("quest_list_request", {
            "filter": self._current_filter,
        })

        self._main_frame.show()
        self._is_visible = True

    def hide_quest_log(self):
        """Скрывает журнал квестов."""
        if not self._is_visible:
            return

        if self._main_frame:
            self._main_frame.hide()

        self._is_visible = False

    # =========================================================================
    # UI Creation
    # =========================================================================

    def _create_ui(self):
        """Создаёт UI журнала квестов."""
        # Основной фрейм
        self._main_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.15, 0.95),
            frameSize=(-0.7, 0.7, -0.6, 0.6),
            pos=(0, 0, 0),
        )

        # Заголовок
        DirectLabel(
            parent=self._main_frame,
            text="Quest Log",
            text_scale=0.055,
            text_fg=(0.9, 0.8, 0.5, 1),
            text_align=TextNode.ACenter,
            pos=(0, 0, 0.52),
            frameColor=(0, 0, 0, 0),
        )

        # Кнопка закрытия
        DirectButton(
            parent=self._main_frame,
            text="X",
            text_scale=0.05,
            text_fg=(1, 0.3, 0.3, 1),
            frameColor=(0.3, 0.1, 0.1, 0.8),
            frameSize=(-0.04, 0.04, -0.03, 0.04),
            pos=(0.63, 0, 0.53),
            command=self.hide_quest_log,
        )

        # Фильтры
        self._create_filters()

        # Список квестов (левая часть)
        self._create_quest_list()

        # Детали квеста (правая часть)
        self._create_quest_details()

        self._main_frame.hide()

    def _create_filters(self):
        """Создаёт кнопки фильтров."""
        filter_frame = DirectFrame(
            parent=self._main_frame,
            frameColor=(0, 0, 0, 0),
            frameSize=(-0.65, 0.65, -0.04, 0.04),
            pos=(0, 0, 0.44),
        )

        filters = [
            ("Active", "active", -0.5),
            ("Available", "available", -0.25),
            ("Completed", "completed", 0.05),
            ("All", "all", 0.3),
        ]

        self._filter_buttons: Dict[str, DirectButton] = {}
        for text, filter_id, x_pos in filters:
            btn = DirectButton(
                parent=filter_frame,
                text=text,
                text_scale=0.032,
                text_fg=(0.9, 0.9, 0.9, 1),
                frameColor=(0.25, 0.25, 0.3, 0.9),
                frameSize=(-0.1, 0.1, -0.03, 0.035),
                pos=(x_pos, 0, 0),
                command=self._set_filter,
                extraArgs=[filter_id],
            )
            self._filter_buttons[filter_id] = btn

        self._update_filter_buttons()

    def _create_quest_list(self):
        """Создаёт список квестов."""
        self._quest_list_frame = DirectScrolledFrame(
            parent=self._main_frame,
            frameColor=(0.12, 0.12, 0.17, 0.9),
            frameSize=(-0.35, 0.0, -0.55, 0.35),
            canvasSize=(-0.33, -0.02, -2.0, 0.0),
            scrollBarWidth=0.025,
            pos=(-0.33, 0, 0),
            autoHideScrollBars=True,
        )

        self._quest_buttons: List[DirectButton] = []

    def _create_quest_details(self):
        """Создаёт панель деталей квеста."""
        details_frame = DirectFrame(
            parent=self._main_frame,
            frameColor=(0.12, 0.12, 0.17, 0.9),
            frameSize=(-0.35, 0.35, -0.55, 0.35),
            pos=(0.35, 0, 0),
        )

        # Название
        self._detail_name = DirectLabel(
            parent=details_frame,
            text="Select a quest",
            text_scale=0.04,
            text_fg=(0.9, 0.8, 0.5, 1),
            text_align=TextNode.ALeft,
            pos=(-0.32, 0, 0.28),
            frameColor=(0, 0, 0, 0),
        )

        # Статус
        self._detail_status = DirectLabel(
            parent=details_frame,
            text="",
            text_scale=0.028,
            text_fg=(0.6, 0.8, 0.6, 1),
            text_align=TextNode.ALeft,
            pos=(-0.32, 0, 0.22),
            frameColor=(0, 0, 0, 0),
        )

        # Описание
        self._detail_desc = DirectLabel(
            parent=details_frame,
            text="",
            text_scale=0.025,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            text_wordwrap=26,
            pos=(-0.32, 0, 0.15),
            frameColor=(0, 0, 0, 0),
        )

        # Заголовок целей
        self._objectives_label = DirectLabel(
            parent=details_frame,
            text="",
            text_scale=0.03,
            text_fg=(0.7, 0.7, 0.9, 1),
            text_align=TextNode.ALeft,
            pos=(-0.32, 0, 0.0),
            frameColor=(0, 0, 0, 0),
        )

        # Список целей
        self._objectives_frame = DirectScrolledFrame(
            parent=details_frame,
            frameColor=(0.08, 0.08, 0.1, 0.8),
            frameSize=(-0.32, 0.32, -0.25, 0.0),
            canvasSize=(-0.30, 0.28, -1.0, 0.0),
            scrollBarWidth=0.02,
            pos=(0, 0, -0.08),
            autoHideScrollBars=True,
        )

        self._objective_labels: List[DirectLabel] = []

        # Заголовок наград
        self._rewards_label = DirectLabel(
            parent=details_frame,
            text="",
            text_scale=0.03,
            text_fg=(0.9, 0.7, 0.3, 1),
            text_align=TextNode.ALeft,
            pos=(-0.32, 0, -0.38),
            frameColor=(0, 0, 0, 0),
        )

        # Награды
        self._rewards_text = DirectLabel(
            parent=details_frame,
            text="",
            text_scale=0.025,
            text_fg=(0.8, 0.8, 0.6, 1),
            text_align=TextNode.ALeft,
            pos=(-0.32, 0, -0.44),
            frameColor=(0, 0, 0, 0),
        )

        # Кнопка действия (abandon/turn in)
        self._action_button = DirectButton(
            parent=details_frame,
            text="",
            text_scale=0.035,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.3, 0.3, 0.5, 0.9),
            frameSize=(-0.12, 0.12, -0.035, 0.04),
            pos=(0, 0, -0.5),
            state=DGG.DISABLED,
        )
        self._action_button.hide()

    # =========================================================================
    # UI Updates
    # =========================================================================

    def _refresh_quest_list(self):
        """Обновляет список квестов."""
        # Очищаем старые кнопки
        for btn in self._quest_buttons:
            btn.destroy()
        self._quest_buttons.clear()

        canvas = self._quest_list_frame.getCanvas()
        y_pos = -0.04

        for quest in self._quests:
            quest_id = quest.get("id", "")
            name = quest.get("name_ru", quest.get("name", quest_id))
            status = quest.get("status", "active")

            # Определяем цвет по статусу
            if status == "active":
                color = (0.9, 0.9, 0.6, 1)
            elif status == "completed":
                color = (0.5, 0.9, 0.5, 1)
            elif status == "available":
                color = (0.6, 0.6, 0.9, 1)
            else:
                color = (0.6, 0.6, 0.6, 1)

            # Индикатор статуса
            prefix = ""
            if status == "completed":
                prefix = "[!] "
            elif status == "active":
                prefix = "* "

            btn = DirectButton(
                parent=canvas,
                text=f"{prefix}{name}",
                text_scale=0.028,
                text_fg=color,
                text_align=TextNode.ALeft,
                frameColor=(0.15, 0.15, 0.2, 0.8),
                frameSize=(-0.01, 0.28, -0.025, 0.03),
                pos=(-0.31, 0, y_pos),
                command=self._select_quest,
                extraArgs=[quest],
            )
            self._quest_buttons.append(btn)
            y_pos -= 0.06

        # Обновляем размер canvas
        canvas_height = max(2.0, abs(y_pos) + 0.1)
        self._quest_list_frame["canvasSize"] = (-0.33, -0.02, -canvas_height, 0.0)

    def _update_filter_buttons(self):
        """Обновляет визуал кнопок фильтра."""
        for filter_id, btn in self._filter_buttons.items():
            if filter_id == self._current_filter:
                btn["frameColor"] = (0.3, 0.5, 0.3, 0.9)
            else:
                btn["frameColor"] = (0.25, 0.25, 0.3, 0.9)

    def _update_quest_details(self, quest: dict):
        """Обновляет панель деталей квеста."""
        self._selected_quest = quest

        # Название
        name = quest.get("name_ru", quest.get("name", ""))
        self._detail_name["text"] = name

        # Статус
        status = quest.get("status", "active")
        status_text = {
            "active": "In Progress",
            "completed": "Ready to Turn In",
            "available": "Available",
            "turned_in": "Completed",
        }.get(status, status)
        self._detail_status["text"] = f"Status: {status_text}"

        if status == "completed":
            self._detail_status["text_fg"] = (0.5, 1.0, 0.5, 1)
        elif status == "active":
            self._detail_status["text_fg"] = (0.9, 0.9, 0.5, 1)
        else:
            self._detail_status["text_fg"] = (0.6, 0.8, 0.6, 1)

        # Описание
        desc = quest.get("description_ru", quest.get("description", ""))
        self._detail_desc["text"] = desc

        # Цели
        objectives = quest.get("objectives", [])
        self._objectives_label["text"] = "Objectives:" if objectives else ""

        # Очищаем старые метки целей
        for label in self._objective_labels:
            label.destroy()
        self._objective_labels.clear()

        canvas = self._objectives_frame.getCanvas()
        y_pos = -0.03

        for obj in objectives:
            obj_desc = obj.get("description_ru", obj.get("description", ""))
            current = obj.get("current_count", 0)
            target = obj.get("target_count", 1)
            optional = obj.get("optional", False)

            # Определяем прогресс
            if current >= target:
                progress = "[DONE]"
                color = (0.5, 1.0, 0.5, 1)
            else:
                progress = f"[{current}/{target}]"
                color = (0.8, 0.8, 0.8, 1)

            text = f"{progress} {obj_desc}"
            if optional:
                text += " (optional)"

            label = DirectLabel(
                parent=canvas,
                text=text,
                text_scale=0.023,
                text_fg=color,
                text_align=TextNode.ALeft,
                text_wordwrap=24,
                pos=(-0.28, 0, y_pos),
                frameColor=(0, 0, 0, 0),
            )
            self._objective_labels.append(label)
            y_pos -= 0.05

        # Обновляем размер canvas
        obj_height = max(1.0, abs(y_pos) + 0.1)
        self._objectives_frame["canvasSize"] = (-0.30, 0.28, -obj_height, 0.0)

        # Награды
        rewards = quest.get("rewards", {})
        if rewards:
            self._rewards_label["text"] = "Rewards:"
            reward_parts = []
            if rewards.get("experience"):
                reward_parts.append(f"{rewards['experience']} XP")
            if rewards.get("gold"):
                reward_parts.append(f"{rewards['gold']} Gold")
            if rewards.get("items"):
                for item in rewards["items"]:
                    reward_parts.append(f"{item.get('count', 1)}x {item.get('id', 'item')}")
            self._rewards_text["text"] = ", ".join(reward_parts)
        else:
            self._rewards_label["text"] = ""
            self._rewards_text["text"] = ""

        # Кнопка действия
        if status == "active":
            self._action_button["text"] = "Abandon Quest"
            self._action_button["frameColor"] = (0.5, 0.3, 0.3, 0.9)
            self._action_button["command"] = self._abandon_quest
            self._action_button["state"] = DGG.NORMAL
            self._action_button.show()
        else:
            self._action_button.hide()

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _set_filter(self, filter_id: str):
        """Устанавливает фильтр."""
        self._current_filter = filter_id
        self._update_filter_buttons()

        # Запрашиваем квесты с новым фильтром
        self.event_manager.post("quest_list_request", {
            "filter": filter_id,
        })

    def _select_quest(self, quest: dict):
        """Выбирает квест."""
        self._update_quest_details(quest)

    def _abandon_quest(self):
        """Отказывается от выбранного квеста."""
        if not self._selected_quest:
            return

        quest_id = self._selected_quest.get("id")
        self.event_manager.post("quest_abandon", {"quest_id": quest_id})

        # Обновляем список
        self.event_manager.post("quest_list_request", {
            "filter": self._current_filter,
        })

    def _on_quest_list(self, data: dict):
        """Получен список квестов."""
        self._quests = data.get("quests", [])
        self._refresh_quest_list()

        # Если был выбран квест - обновляем его
        if self._selected_quest:
            quest_id = self._selected_quest.get("id")
            for quest in self._quests:
                if quest.get("id") == quest_id:
                    self._update_quest_details(quest)
                    break

    def _on_quest_accepted(self, data: dict):
        """Квест принят."""
        if self._is_visible:
            self.event_manager.post("quest_list_request", {
                "filter": self._current_filter,
            })

    def _on_quest_completed(self, data: dict):
        """Квест завершён."""
        if self._is_visible:
            self.event_manager.post("quest_list_request", {
                "filter": self._current_filter,
            })

    def _on_objective_progress(self, data: dict):
        """Обновление прогресса цели."""
        if self._is_visible:
            # Обновляем данные в кеше
            quest_id = data.get("quest_id")
            obj_id = data.get("objective_id")
            current = data.get("current")

            for quest in self._quests:
                if quest.get("id") == quest_id:
                    for obj in quest.get("objectives", []):
                        if obj.get("id") == obj_id:
                            obj["current_count"] = current
                            break
                    break

            # Обновляем детали если это выбранный квест
            if self._selected_quest and self._selected_quest.get("id") == quest_id:
                self._update_quest_details(self._selected_quest)

    def _on_ready_to_turn_in(self, data: dict):
        """Квест готов к сдаче."""
        if self._is_visible:
            self.event_manager.post("quest_list_request", {
                "filter": self._current_filter,
            })

    def _on_game_state_changed(self, data: dict):
        """Изменение состояния игры."""
        state = data.get("state", "")
        if state == "disconnected" and self._is_visible:
            self.hide_quest_log()
            self._quests.clear()
