"""
Клиентский модуль книги заклинаний.

Открывается по клавише K.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectLabel,
    DirectScrolledFrame, DGG
)
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode

from nine.core.plugins import PluginModule


class SpellbookClientModule(PluginModule, DirectObject):
    """
    Клиентский модуль книги заклинаний.
    """

    def on_load(self):
        # UI элементы
        self._main_frame: Optional[DirectFrame] = None
        self._is_visible = False

        # Данные заклинаний
        self._spells_data: Dict[str, dict] = {}
        self._known_spells: List[str] = []
        self._prepared_spells: List[str] = []
        self._spell_slots: Dict[int, int] = {}
        self._spell_slots_max: Dict[int, int] = {}
        self._spellcasting_ability: str = "INT"

        # UI состояние
        self._selected_spell: Optional[str] = None
        self._current_filter: str = "all"  # all, cantrips, prepared

        # Загружаем данные заклинаний
        self._load_spells_data()

        # Биндим клавишу K
        self.accept("k", self.toggle_spellbook)

        # Подписки на события
        self.event_manager.subscribe("character_sheet", self._on_character_update)
        self.event_manager.subscribe("spellcasting_update", self._on_spellcasting_update)
        self.event_manager.subscribe("spell_cast_result", self._on_spell_cast_result)
        self.event_manager.subscribe("game_state_changed", self._on_game_state_changed)

        self.logger.info("Spellbook клиентский модуль загружен (K)")

    def on_unload(self):
        self.ignore_all()
        self.event_manager.unsubscribe("character_sheet", self._on_character_update)
        self.event_manager.unsubscribe("spellcasting_update", self._on_spellcasting_update)
        self.event_manager.unsubscribe("spell_cast_result", self._on_spell_cast_result)
        self.event_manager.unsubscribe("game_state_changed", self._on_game_state_changed)

        if self._main_frame:
            self._main_frame.destroy()
            self._main_frame = None

        self.logger.info("Spellbook клиентский модуль выгружен")

    # =========================================================================
    # Data Loading
    # =========================================================================

    def _load_spells_data(self):
        """Загружает данные заклинаний из JSON."""
        spells_path = Path(__file__).parent / "data" / "spells.json"

        try:
            with open(spells_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for spell in data.get("spells", []):
                self._spells_data[spell["id"]] = spell

            self.logger.info(f"Загружено {len(self._spells_data)} заклинаний")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки заклинаний: {e}")

    # =========================================================================
    # Toggle & Visibility
    # =========================================================================

    def toggle_spellbook(self):
        """Переключает видимость книги заклинаний."""
        if self._is_visible:
            self.hide_spellbook()
        else:
            self.show_spellbook()

    def show_spellbook(self):
        """Показывает книгу заклинаний."""
        if self._is_visible:
            return

        if not self._main_frame:
            self._create_ui()

        # Запрашиваем актуальные данные
        self.event_manager.post("spellcasting_request", {})

        self._main_frame.show()
        self._is_visible = True
        self._refresh_spell_list()

    def hide_spellbook(self):
        """Скрывает книгу заклинаний."""
        if not self._is_visible:
            return

        if self._main_frame:
            self._main_frame.hide()

        self._is_visible = False

    # =========================================================================
    # UI Creation
    # =========================================================================

    def _create_ui(self):
        """Создаёт UI книги заклинаний."""
        # Основной фрейм
        self._main_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.15, 0.95),
            frameSize=(-0.8, 0.8, -0.7, 0.7),
            pos=(0, 0, 0),
        )

        # Заголовок
        DirectLabel(
            parent=self._main_frame,
            text="Spellbook",
            text_scale=0.06,
            text_fg=(0.9, 0.8, 0.5, 1),
            text_align=TextNode.ACenter,
            pos=(0, 0, 0.62),
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
            pos=(0.73, 0, 0.63),
            command=self.hide_spellbook,
        )

        # Слоты заклинаний (верхняя панель)
        self._create_slots_panel()

        # Фильтры
        self._create_filters()

        # Список заклинаний (левая часть)
        self._create_spell_list()

        # Детали заклинания (правая часть)
        self._create_spell_details()

        self._main_frame.hide()

    def _create_slots_panel(self):
        """Создаёт панель слотов заклинаний."""
        slots_frame = DirectFrame(
            parent=self._main_frame,
            frameColor=(0.15, 0.15, 0.2, 0.9),
            frameSize=(-0.75, 0.75, -0.06, 0.06),
            pos=(0, 0, 0.52),
        )

        DirectLabel(
            parent=slots_frame,
            text="Spell Slots:",
            text_scale=0.035,
            text_fg=(0.7, 0.7, 0.7, 1),
            text_align=TextNode.ALeft,
            pos=(-0.72, 0, 0.01),
            frameColor=(0, 0, 0, 0),
        )

        # Контейнер для слотов
        self._slots_labels: Dict[int, DirectLabel] = {}
        x_start = -0.45
        for level in range(1, 10):
            label = DirectLabel(
                parent=slots_frame,
                text=f"L{level}: 0/0",
                text_scale=0.03,
                text_fg=(0.6, 0.6, 0.8, 1),
                text_align=TextNode.ACenter,
                pos=(x_start + (level - 1) * 0.14, 0, 0.01),
                frameColor=(0, 0, 0, 0),
            )
            self._slots_labels[level] = label

    def _create_filters(self):
        """Создаёт кнопки фильтров."""
        filter_frame = DirectFrame(
            parent=self._main_frame,
            frameColor=(0, 0, 0, 0),
            frameSize=(-0.75, 0.75, -0.04, 0.04),
            pos=(0, 0, 0.42),
        )

        filters = [
            ("All", "all", -0.55),
            ("Cantrips", "cantrips", -0.35),
            ("Prepared", "prepared", -0.1),
        ]

        self._filter_buttons: Dict[str, DirectButton] = {}
        for text, filter_id, x_pos in filters:
            btn = DirectButton(
                parent=filter_frame,
                text=text,
                text_scale=0.035,
                text_fg=(0.9, 0.9, 0.9, 1),
                frameColor=(0.25, 0.25, 0.3, 0.9),
                frameSize=(-0.1, 0.1, -0.03, 0.035),
                pos=(x_pos, 0, 0),
                command=self._set_filter,
                extraArgs=[filter_id],
            )
            self._filter_buttons[filter_id] = btn

        self._update_filter_buttons()

    def _create_spell_list(self):
        """Создаёт прокручиваемый список заклинаний."""
        self._spell_list_frame = DirectScrolledFrame(
            parent=self._main_frame,
            frameColor=(0.12, 0.12, 0.17, 0.9),
            frameSize=(-0.4, 0.03, -0.65, 0.35),
            canvasSize=(-0.38, 0.0, -2.0, 0.0),
            scrollBarWidth=0.03,
            pos=(-0.38, 0, 0),
            autoHideScrollBars=True,
        )

        self._spell_buttons: List[DirectButton] = []

    def _create_spell_details(self):
        """Создаёт панель деталей заклинания."""
        details_frame = DirectFrame(
            parent=self._main_frame,
            frameColor=(0.12, 0.12, 0.17, 0.9),
            frameSize=(-0.38, 0.38, -0.65, 0.35),
            pos=(0.4, 0, 0),
        )

        # Название
        self._detail_name = DirectLabel(
            parent=details_frame,
            text="Select a spell",
            text_scale=0.045,
            text_fg=(0.9, 0.8, 0.5, 1),
            text_align=TextNode.ALeft,
            pos=(-0.35, 0, 0.28),
            frameColor=(0, 0, 0, 0),
        )

        # Уровень и школа
        self._detail_level = DirectLabel(
            parent=details_frame,
            text="",
            text_scale=0.03,
            text_fg=(0.6, 0.8, 0.6, 1),
            text_align=TextNode.ALeft,
            pos=(-0.35, 0, 0.2),
            frameColor=(0, 0, 0, 0),
        )

        # Время каста
        self._detail_casting = DirectLabel(
            parent=details_frame,
            text="",
            text_scale=0.028,
            text_fg=(0.7, 0.7, 0.7, 1),
            text_align=TextNode.ALeft,
            pos=(-0.35, 0, 0.14),
            frameColor=(0, 0, 0, 0),
        )

        # Дальность
        self._detail_range = DirectLabel(
            parent=details_frame,
            text="",
            text_scale=0.028,
            text_fg=(0.7, 0.7, 0.7, 1),
            text_align=TextNode.ALeft,
            pos=(-0.35, 0, 0.1),
            frameColor=(0, 0, 0, 0),
        )

        # Компоненты
        self._detail_components = DirectLabel(
            parent=details_frame,
            text="",
            text_scale=0.028,
            text_fg=(0.7, 0.7, 0.7, 1),
            text_align=TextNode.ALeft,
            pos=(-0.35, 0, 0.06),
            frameColor=(0, 0, 0, 0),
        )

        # Длительность
        self._detail_duration = DirectLabel(
            parent=details_frame,
            text="",
            text_scale=0.028,
            text_fg=(0.7, 0.7, 0.7, 1),
            text_align=TextNode.ALeft,
            pos=(-0.35, 0, 0.02),
            frameColor=(0, 0, 0, 0),
        )

        # Описание (прокручиваемое)
        self._detail_desc_frame = DirectScrolledFrame(
            parent=details_frame,
            frameColor=(0.08, 0.08, 0.1, 0.8),
            frameSize=(-0.35, 0.33, -0.35, 0.0),
            canvasSize=(-0.33, 0.28, -1.0, 0.0),
            scrollBarWidth=0.02,
            pos=(0, 0, -0.08),
            autoHideScrollBars=True,
        )

        self._detail_description = DirectLabel(
            parent=self._detail_desc_frame.getCanvas(),
            text="",
            text_scale=0.025,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            text_wordwrap=24,
            pos=(-0.31, 0, -0.03),
            frameColor=(0, 0, 0, 0),
        )

        # Кнопка каста
        self._cast_button = DirectButton(
            parent=details_frame,
            text="Cast Spell",
            text_scale=0.04,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.5, 0.3, 0.9),
            frameSize=(-0.15, 0.15, -0.04, 0.045),
            pos=(0, 0, -0.55),
            command=self._on_cast_click,
            state=DGG.DISABLED,
        )

        # Кнопка подготовки
        self._prepare_button = DirectButton(
            parent=details_frame,
            text="Prepare",
            text_scale=0.035,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.3, 0.3, 0.5, 0.9),
            frameSize=(-0.1, 0.1, -0.035, 0.04),
            pos=(-0.2, 0, -0.55),
            command=self._on_prepare_click,
            state=DGG.DISABLED,
        )

    # =========================================================================
    # UI Updates
    # =========================================================================

    def _refresh_spell_list(self):
        """Обновляет список заклинаний."""
        # Очищаем старые кнопки
        for btn in self._spell_buttons:
            btn.destroy()
        self._spell_buttons.clear()

        # Фильтруем заклинания
        filtered_spells = self._get_filtered_spells()

        # Сортируем по уровню, затем по имени
        filtered_spells.sort(key=lambda s: (s.get("level", 0), s.get("name", "")))

        # Создаём кнопки
        canvas = self._spell_list_frame.getCanvas()
        y_pos = -0.04

        for spell in filtered_spells:
            spell_id = spell["id"]
            level = spell.get("level", 0)
            name = spell.get("name", spell_id)

            # Определяем цвет по уровню
            if level == 0:
                color = (0.5, 0.7, 0.5, 1)  # Cantrip - зелёный
            elif level <= 3:
                color = (0.6, 0.6, 0.9, 1)  # 1-3 - синий
            elif level <= 6:
                color = (0.8, 0.6, 0.8, 1)  # 4-6 - фиолетовый
            else:
                color = (0.9, 0.7, 0.4, 1)  # 7-9 - оранжевый

            # Индикатор подготовки
            prefix = ""
            if spell_id in self._prepared_spells:
                prefix = "* "
            elif level == 0:
                prefix = ""

            btn = DirectButton(
                parent=canvas,
                text=f"{prefix}[{level}] {name}",
                text_scale=0.03,
                text_fg=color,
                text_align=TextNode.ALeft,
                frameColor=(0.15, 0.15, 0.2, 0.8),
                frameSize=(-0.01, 0.35, -0.025, 0.03),
                pos=(-0.36, 0, y_pos),
                command=self._select_spell,
                extraArgs=[spell_id],
            )
            self._spell_buttons.append(btn)
            y_pos -= 0.06

        # Обновляем размер canvas
        canvas_height = max(2.0, abs(y_pos) + 0.1)
        self._spell_list_frame["canvasSize"] = (-0.38, 0.0, -canvas_height, 0.0)

    def _get_filtered_spells(self) -> List[dict]:
        """Возвращает отфильтрованные заклинания."""
        result = []

        for spell_id, spell in self._spells_data.items():
            # Проверяем, знает ли персонаж это заклинание
            if spell_id not in self._known_spells:
                continue

            level = spell.get("level", 0)

            if self._current_filter == "cantrips" and level != 0:
                continue
            elif self._current_filter == "prepared":
                if level > 0 and spell_id not in self._prepared_spells:
                    continue

            result.append(spell)

        return result

    def _update_filter_buttons(self):
        """Обновляет визуал кнопок фильтра."""
        for filter_id, btn in self._filter_buttons.items():
            if filter_id == self._current_filter:
                btn["frameColor"] = (0.3, 0.5, 0.3, 0.9)
            else:
                btn["frameColor"] = (0.25, 0.25, 0.3, 0.9)

    def _update_slots_display(self):
        """Обновляет отображение слотов."""
        for level, label in self._slots_labels.items():
            current = self._spell_slots.get(level, 0)
            maximum = self._spell_slots_max.get(level, 0)

            if maximum > 0:
                if current > 0:
                    color = (0.5, 0.8, 0.5, 1)  # Зелёный
                else:
                    color = (0.8, 0.4, 0.4, 1)  # Красный
                label["text"] = f"L{level}: {current}/{maximum}"
            else:
                color = (0.4, 0.4, 0.4, 1)  # Серый
                label["text"] = f"L{level}: -"

            label["text_fg"] = color

    def _update_spell_details(self, spell_id: str):
        """Обновляет панель деталей заклинания."""
        spell = self._spells_data.get(spell_id)
        if not spell:
            return

        # Название
        name = spell.get("name", spell_id)
        name_ru = spell.get("name_ru", "")
        if name_ru:
            self._detail_name["text"] = f"{name}\n({name_ru})"
        else:
            self._detail_name["text"] = name

        # Уровень и школа
        level = spell.get("level", 0)
        school = spell.get("school", "unknown").capitalize()
        if level == 0:
            level_text = f"Cantrip - {school}"
        else:
            level_text = f"Level {level} {school}"
        if spell.get("ritual"):
            level_text += " (Ritual)"
        if spell.get("concentration"):
            level_text += " [Concentration]"
        self._detail_level["text"] = level_text

        # Время каста
        self._detail_casting["text"] = f"Casting Time: {spell.get('casting_time', 'Unknown')}"

        # Дальность
        range_ft = spell.get("range_ft", 0)
        if range_ft == 0:
            range_text = "Self"
        elif range_ft == -1:
            range_text = "Touch"
        else:
            range_text = f"{range_ft} ft."
        self._detail_range["text"] = f"Range: {range_text}"

        # Компоненты
        components = spell.get("components", [])
        comp_text = ", ".join(components)
        if spell.get("material"):
            comp_text += f" ({spell['material']})"
        self._detail_components["text"] = f"Components: {comp_text}"

        # Длительность
        self._detail_duration["text"] = f"Duration: {spell.get('duration', 'Unknown')}"

        # Описание
        desc = spell.get("description", "")
        higher = spell.get("higher_levels", "")
        if higher:
            desc += f"\n\nAt Higher Levels: {higher}"
        self._detail_description["text"] = desc

        # Обновляем размер canvas описания
        lines = len(desc) // 40 + desc.count("\n") + 3
        desc_height = max(1.0, lines * 0.035)
        self._detail_desc_frame["canvasSize"] = (-0.33, 0.28, -desc_height, 0.0)

        # Кнопки
        self._update_action_buttons(spell)

    def _update_action_buttons(self, spell: dict):
        """Обновляет состояние кнопок действий."""
        spell_id = spell["id"]
        level = spell.get("level", 0)

        # Кнопка каста
        can_cast = False
        if level == 0:
            # Cantrip всегда можно кастовать
            can_cast = True
        else:
            # Проверяем наличие слота
            for slot_level in range(level, 10):
                if self._spell_slots.get(slot_level, 0) > 0:
                    can_cast = True
                    break

        if can_cast:
            self._cast_button["state"] = DGG.NORMAL
            self._cast_button["frameColor"] = (0.2, 0.5, 0.3, 0.9)
        else:
            self._cast_button["state"] = DGG.DISABLED
            self._cast_button["frameColor"] = (0.3, 0.3, 0.3, 0.5)

        # Кнопка подготовки (только для не-cantrip)
        if level > 0:
            self._prepare_button.show()
            if spell_id in self._prepared_spells:
                self._prepare_button["text"] = "Unprepare"
                self._prepare_button["frameColor"] = (0.5, 0.3, 0.3, 0.9)
            else:
                self._prepare_button["text"] = "Prepare"
                self._prepare_button["frameColor"] = (0.3, 0.3, 0.5, 0.9)
            self._prepare_button["state"] = DGG.NORMAL
        else:
            self._prepare_button.hide()

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _set_filter(self, filter_id: str):
        """Устанавливает фильтр."""
        self._current_filter = filter_id
        self._update_filter_buttons()
        self._refresh_spell_list()

    def _select_spell(self, spell_id: str):
        """Выбирает заклинание."""
        self._selected_spell = spell_id
        self._update_spell_details(spell_id)

    def _on_cast_click(self):
        """Обработчик клика по кнопке каста."""
        if not self._selected_spell:
            return

        spell = self._spells_data.get(self._selected_spell)
        if not spell:
            return

        # Отправляем запрос на каст
        self.event_manager.post("cast_spell_request", {
            "spell_id": self._selected_spell,
            "slot_level": spell.get("level", 0),  # Можно добавить выбор слота
        })

    def _on_prepare_click(self):
        """Обработчик клика по кнопке подготовки."""
        if not self._selected_spell:
            return

        spell = self._spells_data.get(self._selected_spell)
        if not spell or spell.get("level", 0) == 0:
            return

        if self._selected_spell in self._prepared_spells:
            # Убираем из подготовленных
            self.event_manager.post("unprepare_spell_request", {
                "spell_id": self._selected_spell,
            })
        else:
            # Добавляем в подготовленные
            self.event_manager.post("prepare_spell_request", {
                "spell_id": self._selected_spell,
            })

    def _on_character_update(self, data: dict):
        """Обновление данных персонажа."""
        char_data = data.get("character", {})

        # Обновляем класс для определения известных заклинаний
        char_class = char_data.get("class", "").lower()

        # Получаем данные заклинательства
        spellcasting = char_data.get("spellcasting", {})

        self._known_spells = spellcasting.get("spells_known", [])
        self._prepared_spells = spellcasting.get("spells_prepared", [])
        self._spell_slots = spellcasting.get("spell_slots_current", {})
        self._spell_slots_max = spellcasting.get("spell_slots_max", {})
        self._spellcasting_ability = spellcasting.get("ability", "INT")

        # Конвертируем ключи слотов в int
        self._spell_slots = {int(k): v for k, v in self._spell_slots.items()}
        self._spell_slots_max = {int(k): v for k, v in self._spell_slots_max.items()}

        if self._is_visible:
            self._update_slots_display()
            self._refresh_spell_list()

    def _on_spellcasting_update(self, data: dict):
        """Обновление данных заклинательства."""
        self._known_spells = data.get("spells_known", self._known_spells)
        self._prepared_spells = data.get("spells_prepared", self._prepared_spells)
        self._spell_slots = data.get("spell_slots_current", self._spell_slots)
        self._spell_slots_max = data.get("spell_slots_max", self._spell_slots_max)

        # Конвертируем ключи
        self._spell_slots = {int(k): v for k, v in self._spell_slots.items()}
        self._spell_slots_max = {int(k): v for k, v in self._spell_slots_max.items()}

        if self._is_visible:
            self._update_slots_display()
            self._refresh_spell_list()
            if self._selected_spell:
                self._update_spell_details(self._selected_spell)

    def _on_spell_cast_result(self, data: dict):
        """Результат каста заклинания."""
        success = data.get("success", False)
        spell_id = data.get("spell_id", "")
        message = data.get("message", "")

        if success:
            self.logger.info(f"Spell cast: {spell_id}")
            # Обновляем слоты
            if "spell_slots_current" in data:
                self._spell_slots = {int(k): v for k, v in data["spell_slots_current"].items()}
                if self._is_visible:
                    self._update_slots_display()
                    if self._selected_spell:
                        self._update_action_buttons(self._spells_data.get(self._selected_spell, {}))
        else:
            self.logger.warning(f"Spell cast failed: {message}")

    def _on_game_state_changed(self, data: dict):
        """Обработчик изменения состояния игры."""
        state = data.get("state", "")
        if state == "disconnected" and self._is_visible:
            self.hide_spellbook()
