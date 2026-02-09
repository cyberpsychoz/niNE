"""
Initiative Display - панель очерёдности ходов.
Отображается слева экрана во время боя.
"""

from typing import Dict, List, Optional
from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectWaitBar
)
from panda3d.core import TextNode

from nine.core.plugins import PluginModule


class InitiativeDisplay(PluginModule):
    """
    Отображает порядок инициативы в бою.
    - Вертикальный список участников слева экрана
    - Имя, HP-бар, число инициативы
    - Подсветка текущего хода
    """

    def on_load(self):
        self.logger.info("Initiative Display loaded")

        # Состояние
        self.is_visible = False
        self.participants_data: List[dict] = []
        self.turn_order: List[str] = []
        self.current_turn_entity: Optional[str] = None

        # UI элементы
        self.container = None
        self.participant_frames: Dict[str, DirectFrame] = {}

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

        self.logger.info("Initiative Display unloaded")

    # =========================================================================
    # Создание UI
    # =========================================================================

    def _create_ui(self):
        """Создаёт UI панели инициативы."""
        if self.container:
            return

        # Главный контейнер (слева экрана)
        self.container = DirectFrame(
            frameColor=(0.1, 0.1, 0.15, 0.85),
            frameSize=(-0.28, 0.28, -0.9, 0.9),
            pos=(-1.05, 0, 0),
            sortOrder=10
        )

        # Заголовок
        self.title_label = DirectLabel(
            parent=self.container,
            text="Очерёдность",
            text_scale=0.05,
            text_fg=(0.9, 0.8, 0.3, 1),
            text_align=TextNode.ACenter,
            pos=(0, 0, 0.82),
            frameColor=(0, 0, 0, 0)
        )

        # Номер раунда
        self.round_label = DirectLabel(
            parent=self.container,
            text="Раунд 1",
            text_scale=0.04,
            text_fg=(0.7, 0.7, 0.7, 1),
            text_align=TextNode.ACenter,
            pos=(0, 0, 0.74),
            frameColor=(0, 0, 0, 0)
        )

        self.is_visible = True

    def _destroy_ui(self):
        """Уничтожает UI."""
        if self.container:
            self.container.destroy()
            self.container = None
        self.participant_frames.clear()
        self.is_visible = False

    def _create_participant_frame(self, entity_id: str, data: dict, y_pos: float):
        """Создаёт фрейм для одного участника."""
        is_player = data.get("is_player", False)
        is_dead = data.get("is_dead", False)

        # Определяем цвет фона
        if is_dead:
            bg_color = (0.2, 0.2, 0.2, 0.6)
        elif is_player:
            bg_color = (0.15, 0.2, 0.15, 0.8)
        else:
            bg_color = (0.2, 0.15, 0.15, 0.8)

        frame = DirectFrame(
            parent=self.container,
            frameColor=bg_color,
            frameSize=(-0.25, 0.25, -0.07, 0.07),
            pos=(0, 0, y_pos)
        )

        # Число инициативы (слева)
        init_label = DirectLabel(
            parent=frame,
            text=str(data.get("initiative", 0)),
            text_scale=0.045,
            text_fg=(0.9, 0.8, 0.3, 1),
            text_align=TextNode.ACenter,
            pos=(-0.2, 0, 0.02),
            frameColor=(0, 0, 0, 0)
        )

        # Имя (центр)
        name = data.get("name", "???")
        if len(name) > 12:
            name = name[:11] + "..."

        name_label = DirectLabel(
            parent=frame,
            text=name,
            text_scale=0.04,
            text_fg=(1, 1, 1, 1) if not is_dead else (0.5, 0.5, 0.5, 1),
            text_align=TextNode.ALeft,
            pos=(-0.12, 0, 0.02),
            frameColor=(0, 0, 0, 0)
        )

        # HP бар
        hp_current = data.get("hp_current", 0)
        hp_max = max(data.get("hp_max", 1), 1)
        hp_ratio = hp_current / hp_max

        # Цвет HP бара
        if hp_ratio > 0.5:
            hp_color = (0.2, 0.7, 0.2, 1)
        elif hp_ratio > 0.25:
            hp_color = (0.8, 0.6, 0.1, 1)
        else:
            hp_color = (0.8, 0.2, 0.2, 1)

        if is_dead:
            hp_color = (0.3, 0.3, 0.3, 1)

        hp_bar = DirectWaitBar(
            parent=frame,
            range=100,
            value=hp_ratio * 100,
            barColor=hp_color,
            frameColor=(0.15, 0.15, 0.15, 1),
            frameSize=(-0.18, 0.18, -0.015, 0.015),
            pos=(0.02, 0, -0.04)
        )

        # HP текст
        hp_text = DirectLabel(
            parent=frame,
            text=f"{hp_current}/{hp_max}" if not is_dead else "X",
            text_scale=0.025,
            text_fg=(0.9, 0.9, 0.9, 1),
            text_align=TextNode.ACenter,
            pos=(0.02, 0, -0.04),
            frameColor=(0, 0, 0, 0)
        )

        # Сохраняем компоненты для обновления
        frame.setPythonTag("components", {
            "init_label": init_label,
            "name_label": name_label,
            "hp_bar": hp_bar,
            "hp_text": hp_text,
            "is_player": is_player,
        })

        self.participant_frames[entity_id] = frame

    def _update_participants_list(self):
        """Обновляет список участников."""
        # Удаляем старые фреймы
        for frame in self.participant_frames.values():
            frame.destroy()
        self.participant_frames.clear()

        # Создаём новые в порядке инициативы
        y_pos = 0.65  # Начальная позиция (под заголовком)
        spacing = 0.16  # Расстояние между фреймами

        for entity_id in self.turn_order:
            # Находим данные участника
            participant_data = None
            for p in self.participants_data:
                if p.get("entity_id") == entity_id:
                    participant_data = p
                    break

            if participant_data:
                self._create_participant_frame(entity_id, participant_data, y_pos)
                y_pos -= spacing

    def _highlight_current_turn(self, entity_id: str):
        """Подсвечивает участника, чей сейчас ход."""
        for eid, frame in self.participant_frames.items():
            components = frame.getPythonTag("components")
            is_player = components.get("is_player", False)

            if eid == entity_id:
                # Текущий ход - яркая зелёная подсветка
                frame["frameColor"] = (0.2, 0.5, 0.2, 0.95)
            else:
                # Обычный цвет
                if is_player:
                    frame["frameColor"] = (0.15, 0.2, 0.15, 0.8)
                else:
                    frame["frameColor"] = (0.2, 0.15, 0.15, 0.8)

        self.current_turn_entity = entity_id

    def _update_participant_hp(self, entity_id: str, hp_current: int, hp_max: int, is_dead: bool):
        """Обновляет HP участника."""
        frame = self.participant_frames.get(entity_id)
        if not frame:
            return

        components = frame.getPythonTag("components")
        hp_bar = components.get("hp_bar")
        hp_text = components.get("hp_text")
        name_label = components.get("name_label")

        if hp_bar:
            hp_ratio = hp_current / max(hp_max, 1)

            # Цвет HP бара
            if is_dead:
                hp_color = (0.3, 0.3, 0.3, 1)
            elif hp_ratio > 0.5:
                hp_color = (0.2, 0.7, 0.2, 1)
            elif hp_ratio > 0.25:
                hp_color = (0.8, 0.6, 0.1, 1)
            else:
                hp_color = (0.8, 0.2, 0.2, 1)

            hp_bar["value"] = hp_ratio * 100
            hp_bar["barColor"] = hp_color

        if hp_text:
            hp_text["text"] = f"{hp_current}/{hp_max}" if not is_dead else "X"

        if name_label and is_dead:
            name_label["text_fg"] = (0.5, 0.5, 0.5, 1)

        if is_dead:
            frame["frameColor"] = (0.2, 0.2, 0.2, 0.6)

    # =========================================================================
    # Обработчики событий
    # =========================================================================

    def _on_combat_started(self, data: dict):
        """Обрабатывает начало боя."""
        self.participants_data = data.get("participants", [])
        self.turn_order = data.get("turn_order", [])

        if self.app.ui_is_web:
            return  # Web UI handles display via GameHUD

        self._create_ui()
        self._update_participants_list()

        self.round_label["text"] = f"Раунд {data.get('round', 1)}"

    def _on_combat_ended(self, data: dict):
        """Обрабатывает окончание боя."""
        self.participants_data = []
        self.turn_order = []
        self.current_turn_entity = None
        if self.app.ui_is_web:
            return
        self._destroy_ui()

    def _on_turn_start(self, data: dict):
        """Обрабатывает начало нового хода."""
        if self.app.ui_is_web:
            return
        entity_id = data.get("entity_id")
        round_num = data.get("round", 1)

        if entity_id:
            self._highlight_current_turn(entity_id)

        if self.round_label:
            self.round_label["text"] = f"Раунд {round_num}"

    def _on_action_result(self, data: dict):
        """Обрабатывает результат действия (обновление HP)."""
        if self.app.ui_is_web:
            return
        result = data.get("result", {})

        target_id = data.get("target_id")
        if target_id and "target_hp_current" in result:
            self._update_participant_hp(
                target_id,
                result.get("target_hp_current", 0),
                result.get("target_hp_max", 1),
                result.get("target_is_dead", False)
            )

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
