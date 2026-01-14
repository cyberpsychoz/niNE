"""
Клиентский UI создания персонажа D&D.
7-шаговый мастер создания персонажа.
"""

import importlib.util
from pathlib import Path
from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton,
    DirectEntry, DirectOptionMenu, DirectScrolledFrame,
    DGG
)
from panda3d.core import TextNode, TransparencyAttrib

from nine.ui.base_component import BaseUIComponent
from nine.ui.theme import NineTheme


def _load_constants():
    """Загружает константы из sh_constants.py в той же папке."""
    constants_path = Path(__file__).parent / "sh_constants.py"
    spec = importlib.util.spec_from_file_location("dnd_constants", constants_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_constants = _load_constants()
RACES = _constants.RACES
CLASSES = _constants.CLASSES
BACKGROUNDS = _constants.BACKGROUNDS
SKILLS = _constants.SKILLS
STAT_GENERATION = _constants.STAT_GENERATION
FEATURES = _constants.FEATURES
get_feature_info = _constants.get_feature_info


# Локализация
RACE_NAMES_RU = {
    "human": "Человек",
    "elf": "Эльф",
    "dwarf": "Дварф",
    "halfling": "Полурослик",
    "orc": "Орк",
    "half_orc": "Полуорк",
    "tiefling": "Тифлинг",
}

CLASS_NAMES_RU = {
    "fighter": "Воин",
    "wizard": "Волшебник",
    "rogue": "Плут",
    "cleric": "Жрец",
    "ranger": "Следопыт",
    "paladin": "Паладин",
    "barbarian": "Варвар",
    "bard": "Бард",
    "druid": "Друид",
    "monk": "Монах",
    "sorcerer": "Чародей",
    "warlock": "Колдун",
}

BACKGROUND_NAMES_RU = {
    "acolyte": "Послушник",
    "criminal": "Преступник",
    "folk_hero": "Народный герой",
    "noble": "Дворянин",
    "sage": "Мудрец",
    "soldier": "Солдат",
    "entertainer": "Артист",
    "hermit": "Отшельник",
    "outlander": "Чужеземец",
    "guild_artisan": "Гильдейский ремесленник",
}

SKILL_NAMES_RU = {
    "acrobatics": "Акробатика",
    "animal_handling": "Уход за животными",
    "arcana": "Магия",
    "athletics": "Атлетика",
    "deception": "Обман",
    "history": "История",
    "insight": "Проницательность",
    "intimidation": "Запугивание",
    "investigation": "Расследование",
    "medicine": "Медицина",
    "nature": "Природа",
    "perception": "Внимательность",
    "performance": "Выступление",
    "persuasion": "Убеждение",
    "religion": "Религия",
    "sleight_of_hand": "Ловкость рук",
    "stealth": "Скрытность",
    "survival": "Выживание",
}

STAT_NAMES_RU = {
    "strength": "Сила",
    "dexterity": "Ловкость",
    "constitution": "Телосложение",
    "intelligence": "Интеллект",
    "wisdom": "Мудрость",
    "charisma": "Харизма",
}


class CharacterCreateUI(BaseUIComponent):
    """
    UI мастер создания персонажа D&D.
    7 шагов:
    1. Имя и пол
    2. Раса
    3. Класс
    4. Характеристики
    5. Навыки
    6. Предыстория
    7. Подтверждение
    """

    def __init__(self, ui_manager, client):
        super().__init__(ui_manager)
        self.client = client

        # Текущий шаг (1-7)
        self.current_step = 1
        self.total_steps = 7

        # Данные персонажа
        self.character_data = {
            "character_name": "",
            "gender": "male",
            "race": "human",
            "class": "fighter",
            "background": "",
            "strength": 10,
            "dexterity": 10,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10,
            "skills": {},
        }

        # Тултип для отображения описаний способностей
        self._tooltip_frame = None

        self._create_base_ui()
        self._show_step(1)

    def _create_base_ui(self):
        """Создаёт базовые элементы UI."""
        # Тёмный фон
        self._add_element('background', DirectFrame(
            parent=self.base.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=NineTheme.BG_DARK,
        ))

        # Основная панель
        self.panel_width = 1.4
        self.panel_height = 1.4
        panel = self._add_element('panel', DirectFrame(
            parent=self.base.aspect2d,
            frameSize=(-self.panel_width/2, self.panel_width/2, -self.panel_height/2, self.panel_height/2),
            frameColor=NineTheme.BG_MEDIUM,
            pos=(0, 0, 0),
        ))
        panel.setTransparency(TransparencyAttrib.M_alpha)

        # Заголовок
        self._add_element('title', DirectLabel(
            parent=panel,
            text="СОЗДАНИЕ ПЕРСОНАЖА",
            scale=NineTheme.TITLE_SCALE,
            pos=(0, 0, self.panel_height/2 - 0.1),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        ))

        # Индикатор шагов
        self._add_element('step_indicator', DirectLabel(
            parent=panel,
            text=f"Шаг {self.current_step} из {self.total_steps}",
            scale=NineTheme.SMALL_SCALE,
            pos=(0, 0, self.panel_height/2 - 0.17),
            text_fg=NineTheme.TEXT_SECONDARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        ))

        # Контейнер для содержимого шага
        self.content_frame = self._add_element('content', DirectFrame(
            parent=panel,
            frameSize=(-self.panel_width/2 + 0.1, self.panel_width/2 - 0.1, -0.4, 0.4),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0),
        ))

        # Кнопки навигации
        btn_y = -self.panel_height/2 + 0.12

        self._add_element('back_btn', DirectButton(
            parent=panel,
            text="Назад",
            scale=NineTheme.BUTTON_SCALE,
            pos=(-0.35, 0, btn_y),
            command=self._prev_step,
            frameColor=NineTheme.button_colors(),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            pressEffect=True,
            relief=DGG.FLAT,
            frameSize=(-3.5, 3.5, -0.8, 1.1),
        ))

        self._add_element('next_btn', DirectButton(
            parent=panel,
            text="Далее",
            scale=NineTheme.BUTTON_SCALE,
            pos=(0.35, 0, btn_y),
            command=self._next_step,
            frameColor=NineTheme.accent_button_colors(),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            pressEffect=True,
            relief=DGG.FLAT,
            frameSize=(-3.5, 3.5, -0.8, 1.1),
        ))

        # Кнопка отмены
        self._add_element('cancel_btn', DirectButton(
            parent=panel,
            text="Отмена",
            scale=NineTheme.SMALL_SCALE,
            pos=(-self.panel_width/2 + 0.15, 0, self.panel_height/2 - 0.08),
            command=self._cancel,
            frameColor=NineTheme.button_colors(),
            text_fg=NineTheme.TEXT_SECONDARY,
            text_align=TextNode.ACenter,
            pressEffect=True,
            relief=DGG.FLAT,
            frameSize=(-3, 3, -0.8, 1.1),
        ))

    def _clear_content(self):
        """Очищает содержимое текущего шага."""
        self._hide_feature_tooltip()
        for child in self.content_frame.getChildren():
            child.removeNode()

    def _show_step(self, step: int):
        """Показывает указанный шаг."""
        self.current_step = step
        self._clear_content()

        # Обновляем индикатор
        if 'step_indicator' in self._elements:
            self._elements['step_indicator']['text'] = f"Шаг {step} из {self.total_steps}"

        # Обновляем текст кнопки "Далее"
        if step == self.total_steps:
            self._elements['next_btn']['text'] = "Создать"
        else:
            self._elements['next_btn']['text'] = "Далее"

        # Показываем/скрываем кнопку "Назад"
        if step == 1:
            self._elements['back_btn'].hide()
        else:
            self._elements['back_btn'].show()

        # Отображаем содержимое шага
        step_methods = {
            1: self._show_step_name,
            2: self._show_step_race,
            3: self._show_step_class,
            4: self._show_step_stats,
            5: self._show_step_skills,
            6: self._show_step_background,
            7: self._show_step_confirm,
        }
        step_methods[step]()

    def _show_feature_tooltip(self, feature_id: str, pos_x: float = 0, pos_y: float = -0.35):
        """Показывает тултип с описанием способности."""
        self._hide_feature_tooltip()

        feat_info = get_feature_info(feature_id)
        name = feat_info["name"]
        description = feat_info["description"]

        # Создаём фрейм тултипа
        tooltip_width = 0.55
        tooltip_height = 0.25

        self._tooltip_frame = DirectFrame(
            parent=self.content_frame,
            frameSize=(-tooltip_width, tooltip_width, -tooltip_height, tooltip_height),
            frameColor=(0.1, 0.1, 0.15, 0.95),
            pos=(pos_x, 0, pos_y),
        )
        self._tooltip_frame.setTransparency(TransparencyAttrib.M_alpha)

        # Заголовок способности
        DirectLabel(
            parent=self._tooltip_frame,
            text=name,
            scale=NineTheme.SMALL_SCALE * 1.1,
            pos=(0, 0, tooltip_height - 0.05),
            text_fg=NineTheme.TEXT_HIGHLIGHT,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        # Описание способности
        DirectLabel(
            parent=self._tooltip_frame,
            text=description,
            scale=NineTheme.SMALL_SCALE * 0.75,
            pos=(0, 0, 0),
            text_fg=NineTheme.TEXT_SECONDARY,
            text_align=TextNode.ACenter,
            text_wordwrap=25,
            frameColor=(0, 0, 0, 0),
        )

        # Кнопка закрытия
        DirectButton(
            parent=self._tooltip_frame,
            text="X",
            scale=NineTheme.SMALL_SCALE * 0.8,
            pos=(tooltip_width - 0.05, 0, tooltip_height - 0.05),
            command=self._hide_feature_tooltip,
            frameColor=(0.6, 0.15, 0.15, 0.9),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ACenter,
            pressEffect=True,
            relief=DGG.FLAT,
            frameSize=(-1, 1, -0.9, 1.1),
        )

    def _hide_feature_tooltip(self):
        """Скрывает тултип."""
        if self._tooltip_frame:
            self._tooltip_frame.destroy()
            self._tooltip_frame = None

    def _show_step_name(self):
        """Шаг 1: Имя и пол."""
        DirectLabel(
            parent=self.content_frame,
            text="Введите имя персонажа:",
            scale=NineTheme.LABEL_SCALE,
            pos=(0, 0, 0.3),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        self.name_entry = DirectEntry(
            parent=self.content_frame,
            scale=NineTheme.ENTRY_SCALE,
            pos=(-0.4, 0, 0.18),
            initialText=self.character_data["character_name"],
            numLines=1,
            focus=1,
            width=18,
            frameColor=NineTheme.ENTRY_BG,
            text_fg=NineTheme.TEXT_PRIMARY,
            cursorKeys=True,
        )

        DirectLabel(
            parent=self.content_frame,
            text="Выберите пол:",
            scale=NineTheme.LABEL_SCALE,
            pos=(0, 0, 0.02),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        # Кнопки выбора пола
        self.gender_buttons = {}

        male_color = NineTheme.accent_button_colors() if self.character_data["gender"] == "male" else NineTheme.button_colors()
        female_color = NineTheme.accent_button_colors() if self.character_data["gender"] == "female" else NineTheme.button_colors()

        self.gender_buttons["male"] = DirectButton(
            parent=self.content_frame,
            text="Мужской",
            scale=NineTheme.BUTTON_SCALE,
            pos=(-0.22, 0, -0.1),
            command=lambda: self._select_gender("male"),
            frameColor=male_color,
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            pressEffect=True,
            relief=DGG.FLAT,
            frameSize=(-3.5, 3.5, -0.8, 1.1),
        )

        self.gender_buttons["female"] = DirectButton(
            parent=self.content_frame,
            text="Женский",
            scale=NineTheme.BUTTON_SCALE,
            pos=(0.22, 0, -0.1),
            command=lambda: self._select_gender("female"),
            frameColor=female_color,
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            pressEffect=True,
            relief=DGG.FLAT,
            frameSize=(-3.5, 3.5, -0.8, 1.1),
        )

    def _select_gender(self, gender: str):
        """Выбор пола."""
        self.character_data["gender"] = gender
        for g, btn in self.gender_buttons.items():
            if g == gender:
                btn['frameColor'] = NineTheme.accent_button_colors()
            else:
                btn['frameColor'] = NineTheme.button_colors()

    def _show_step_race(self):
        """Шаг 2: Выбор расы."""
        DirectLabel(
            parent=self.content_frame,
            text="Выберите расу:",
            scale=NineTheme.LABEL_SCALE,
            pos=(0, 0, 0.36),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        self.race_buttons = {}
        races = list(RACES.keys())
        cols = 3
        start_x = -0.38
        start_y = 0.26
        spacing_x = 0.30
        spacing_y = 0.13

        for i, race in enumerate(races):
            row = i // cols
            col = i % cols
            x = start_x + col * spacing_x
            y = start_y - row * spacing_y

            is_selected = self.character_data["race"] == race
            color = NineTheme.accent_button_colors() if is_selected else NineTheme.button_colors()

            race_data = RACES.get(race, {})
            race_name_ru = race_data.get("name", RACE_NAMES_RU.get(race, race.title()))
            self.race_buttons[race] = DirectButton(
                parent=self.content_frame,
                text=race_name_ru,
                scale=NineTheme.BUTTON_SCALE * 0.85,
                pos=(x, 0, y),
                command=lambda r=race: self._select_race(r),
                frameColor=color,
                text_fg=NineTheme.TEXT_PRIMARY,
                text_align=TextNode.ACenter,
                pressEffect=True,
                relief=DGG.FLAT,
                frameSize=(-3.5, 3.5, -0.9, 1.2),
            )

        # Описание выбранной расы
        self.race_desc_label = DirectLabel(
            parent=self.content_frame,
            text=self._get_race_description(self.character_data["race"]),
            scale=NineTheme.SMALL_SCALE * 0.85,
            pos=(0, 0, -0.08),
            text_fg=NineTheme.TEXT_SECONDARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        # Кликабельные кнопки способностей
        self._race_feature_btns = []
        self._update_race_feature_buttons(self.character_data["race"])

    def _truncate_text(self, text: str, max_len: int = 14) -> str:
        """Обрезает текст до максимальной длины."""
        if len(text) > max_len:
            return text[:max_len-2] + ".."
        return text

    def _update_race_feature_buttons(self, race: str):
        """Обновляет кнопки способностей для выбранной расы."""
        # Удаляем старые кнопки
        for btn in self._race_feature_btns:
            btn.destroy()
        self._race_feature_btns.clear()
        self._hide_feature_tooltip()

        race_data = RACES.get(race, {})
        features = race_data.get("features", [])

        if not features:
            return

        # Подсказка
        hint = DirectLabel(
            parent=self.content_frame,
            text="Способности (клик):",
            scale=NineTheme.SMALL_SCALE * 0.7,
            pos=(0, 0, -0.32),
            text_fg=NineTheme.TEXT_HINT,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )
        self._race_feature_btns.append(hint)

        # Создаём кнопки способностей в ряд по центру
        num_features = len(features)
        btn_width = 0.28
        total_width = num_features * btn_width
        start_x = -total_width / 2 + btn_width / 2
        y = -0.38

        for i, feat_id in enumerate(features):
            feat_info = get_feature_info(feat_id)
            x = start_x + i * btn_width
            display_name = self._truncate_text(feat_info["name"], 12)

            btn = DirectButton(
                parent=self.content_frame,
                text=display_name,
                scale=NineTheme.SMALL_SCALE * 0.7,
                pos=(x, 0, y),
                command=lambda fid=feat_id: self._show_feature_tooltip(fid, pos_y=-0.05),
                frameColor=(0.18, 0.18, 0.25, 0.95),
                text_fg=NineTheme.TEXT_HIGHLIGHT,
                text_align=TextNode.ACenter,
                pressEffect=True,
                relief=DGG.FLAT,
                frameSize=(-5, 5, -1.1, 1.4),
            )
            self._race_feature_btns.append(btn)

    def _get_race_description(self, race: str) -> str:
        """Возвращает описание расы с бонусами и способностями."""
        race_data = RACES.get(race, {})

        # Бонусы характеристик
        bonuses = race_data.get("ability_bonuses", {})
        bonus_strs = []
        for stat, value in bonuses.items():
            stat_ru = STAT_NAMES_RU.get(stat, stat)
            bonus_strs.append(f"+{value} {stat_ru}")
        bonus_text = ", ".join(bonus_strs) if bonus_strs else "Нет бонусов"

        # Особенности расы
        features = race_data.get("features", [])
        feature_names = []
        for feat_id in features:
            feat_info = get_feature_info(feat_id)
            feature_names.append(feat_info["name"])
        features_text = ", ".join(feature_names) if feature_names else ""

        # Скорость
        speed = race_data.get("speed", 30)

        result = f"Бонусы: {bonus_text}\nСкорость: {speed} фт."
        if features_text:
            result += f"\nСпособности: {features_text}"
        return result

    def _select_race(self, race: str):
        """Выбор расы."""
        self.character_data["race"] = race
        for r, btn in self.race_buttons.items():
            if r == race:
                btn['frameColor'] = NineTheme.accent_button_colors()
            else:
                btn['frameColor'] = NineTheme.button_colors()
        if hasattr(self, 'race_desc_label'):
            self.race_desc_label['text'] = self._get_race_description(race)
        # Обновляем кнопки способностей
        if hasattr(self, '_race_feature_btns'):
            self._update_race_feature_buttons(race)

    def _show_step_class(self):
        """Шаг 3: Выбор класса."""
        DirectLabel(
            parent=self.content_frame,
            text="Выберите класс:",
            scale=NineTheme.LABEL_SCALE,
            pos=(0, 0, 0.36),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        self.class_buttons = {}
        classes = list(CLASSES.keys())
        cols = 4
        start_x = -0.45
        start_y = 0.26
        spacing_x = 0.26
        spacing_y = 0.11

        for i, cls in enumerate(classes):
            row = i // cols
            col = i % cols
            x = start_x + col * spacing_x
            y = start_y - row * spacing_y

            is_selected = self.character_data["class"] == cls
            color = NineTheme.accent_button_colors() if is_selected else NineTheme.button_colors()

            cls_data = CLASSES.get(cls, {})
            cls_name_ru = cls_data.get("name", CLASS_NAMES_RU.get(cls, cls.title()))
            self.class_buttons[cls] = DirectButton(
                parent=self.content_frame,
                text=cls_name_ru,
                scale=NineTheme.BUTTON_SCALE * 0.7,
                pos=(x, 0, y),
                command=lambda c=cls: self._select_class(c),
                frameColor=color,
                text_fg=NineTheme.TEXT_PRIMARY,
                text_align=TextNode.ACenter,
                pressEffect=True,
                relief=DGG.FLAT,
                frameSize=(-3.8, 3.8, -0.9, 1.2),
            )

        # Описание класса
        self.class_desc_label = DirectLabel(
            parent=self.content_frame,
            text=self._get_class_description(self.character_data["class"]),
            scale=NineTheme.SMALL_SCALE * 0.85,
            pos=(0, 0, -0.15),
            text_fg=NineTheme.TEXT_SECONDARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        # Кликабельные кнопки способностей класса
        self._class_feature_btns = []
        self._update_class_feature_buttons(self.character_data["class"])

    def _update_class_feature_buttons(self, cls: str):
        """Обновляет кнопки способностей для выбранного класса."""
        # Удаляем старые кнопки
        for btn in self._class_feature_btns:
            btn.destroy()
        self._class_feature_btns.clear()
        self._hide_feature_tooltip()

        class_data = CLASSES.get(cls, {})
        features = class_data.get("features_1", [])

        if not features:
            return

        # Подсказка
        hint = DirectLabel(
            parent=self.content_frame,
            text="Способности 1 ур. (клик):",
            scale=NineTheme.SMALL_SCALE * 0.7,
            pos=(0, 0, -0.38),
            text_fg=NineTheme.TEXT_HINT,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )
        self._class_feature_btns.append(hint)

        # Создаём кнопки способностей в ряд по центру
        num_features = len(features)
        btn_width = 0.32
        total_width = num_features * btn_width
        start_x = -total_width / 2 + btn_width / 2
        y = -0.44

        for i, feat_id in enumerate(features):
            feat_info = get_feature_info(feat_id)
            x = start_x + i * btn_width
            display_name = self._truncate_text(feat_info["name"], 14)

            btn = DirectButton(
                parent=self.content_frame,
                text=display_name,
                scale=NineTheme.SMALL_SCALE * 0.7,
                pos=(x, 0, y),
                command=lambda fid=feat_id: self._show_feature_tooltip(fid, pos_y=-0.1),
                frameColor=(0.18, 0.18, 0.25, 0.95),
                text_fg=NineTheme.TEXT_HIGHLIGHT,
                text_align=TextNode.ACenter,
                pressEffect=True,
                relief=DGG.FLAT,
                frameSize=(-5.5, 5.5, -1.1, 1.4),
            )
            self._class_feature_btns.append(btn)

    def _get_class_description(self, cls: str) -> str:
        """Возвращает описание класса."""
        class_data = CLASSES.get(cls, {})
        hit_die = class_data.get("hit_die", 8)

        # Основные характеристики
        primary_stats = class_data.get("primary_stats", [])
        primary_ru = ", ".join(STAT_NAMES_RU.get(s, s) for s in primary_stats)

        # Способности 1 уровня
        features_1 = class_data.get("features_1", [])
        feature_names = []
        for feat_id in features_1:
            feat_info = get_feature_info(feat_id)
            feature_names.append(feat_info["name"])
        features_text = ", ".join(feature_names) if feature_names else ""

        result = f"Кость хитов: d{hit_die} | Основная хар.: {primary_ru}"
        if features_text:
            result += f"\nСпособности 1 ур.: {features_text}"
        return result

    def _select_class(self, cls: str):
        """Выбор класса."""
        self.character_data["class"] = cls
        for c, btn in self.class_buttons.items():
            if c == cls:
                btn['frameColor'] = NineTheme.accent_button_colors()
            else:
                btn['frameColor'] = NineTheme.button_colors()
        if hasattr(self, 'class_desc_label'):
            self.class_desc_label['text'] = self._get_class_description(cls)
        # Обновляем кнопки способностей
        if hasattr(self, '_class_feature_btns'):
            self._update_class_feature_buttons(cls)

    def _show_step_stats(self):
        """Шаг 4: Характеристики с кнопками +/-."""
        DirectLabel(
            parent=self.content_frame,
            text="Распределите характеристики:",
            scale=NineTheme.LABEL_SCALE,
            pos=(0, 0, 0.35),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        # Оставшиеся очки (point buy: 27 очков)
        self.stat_points = 27
        self._recalculate_points()

        self.points_label = DirectLabel(
            parent=self.content_frame,
            text=f"Очков: {self.stat_points}",
            scale=NineTheme.SMALL_SCALE,
            pos=(0, 0, 0.27),
            text_fg=NineTheme.TEXT_HIGHLIGHT,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        stats = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
        self.stat_labels = {}
        self.stat_buttons = {}

        start_y = 0.15
        spacing = 0.09

        for i, stat in enumerate(stats):
            y = start_y - i * spacing

            # Название характеристики
            DirectLabel(
                parent=self.content_frame,
                text=f"{STAT_NAMES_RU.get(stat, stat)}:",
                scale=NineTheme.SMALL_SCALE,
                pos=(-0.4, 0, y),
                text_fg=NineTheme.TEXT_PRIMARY,
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
            )

            # Кнопка минус
            DirectButton(
                parent=self.content_frame,
                text="-",
                scale=NineTheme.SMALL_SCALE,
                pos=(0.1, 0, y),
                command=lambda s=stat: self._change_stat(s, -1),
                frameColor=NineTheme.button_colors(),
                text_fg=NineTheme.TEXT_PRIMARY,
                text_align=TextNode.ACenter,
                pressEffect=True,
                relief=DGG.FLAT,
                frameSize=(-1.2, 1.2, -1, 1.2),
            )

            # Значение
            self.stat_labels[stat] = DirectLabel(
                parent=self.content_frame,
                text=str(self.character_data[stat]),
                scale=NineTheme.SMALL_SCALE * 1.2,
                pos=(0.22, 0, y),
                text_fg=NineTheme.TEXT_HIGHLIGHT,
                text_align=TextNode.ACenter,
                frameColor=(0, 0, 0, 0),
            )

            # Кнопка плюс
            DirectButton(
                parent=self.content_frame,
                text="+",
                scale=NineTheme.SMALL_SCALE,
                pos=(0.34, 0, y),
                command=lambda s=stat: self._change_stat(s, 1),
                frameColor=NineTheme.accent_button_colors(),
                text_fg=NineTheme.TEXT_PRIMARY,
                text_align=TextNode.ACenter,
                pressEffect=True,
                relief=DGG.FLAT,
                frameSize=(-1.2, 1.2, -1, 1.2),
            )

    def _get_point_cost(self, value: int) -> int:
        """Возвращает стоимость значения характеристики (point buy)."""
        # 8=0, 9=1, 10=2, 11=3, 12=4, 13=5, 14=7, 15=9
        costs = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
        return costs.get(value, 0)

    def _recalculate_points(self):
        """Пересчитывает оставшиеся очки."""
        total_spent = 0
        for stat in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
            total_spent += self._get_point_cost(self.character_data[stat])
        self.stat_points = 27 - total_spent

    def _change_stat(self, stat: str, delta: int):
        """Изменяет характеристику на delta."""
        current = self.character_data[stat]
        new_value = current + delta

        # Ограничения: 8-15
        if new_value < 8 or new_value > 15:
            return

        # Проверяем очки
        old_cost = self._get_point_cost(current)
        new_cost = self._get_point_cost(new_value)
        cost_diff = new_cost - old_cost

        if cost_diff > self.stat_points:
            return  # Не хватает очков

        self.character_data[stat] = new_value
        self._recalculate_points()

        # Обновляем UI
        if stat in self.stat_labels:
            self.stat_labels[stat]['text'] = str(new_value)
        if hasattr(self, 'points_label'):
            self.points_label['text'] = f"Очков: {self.stat_points}"

    def _get_skill_modifier(self, skill: str) -> int:
        """Вычисляет модификатор навыка на основе связанной характеристики."""
        skill_data = SKILLS.get(skill, {})
        ability = skill_data.get("ability", "strength")
        stat_value = self.character_data.get(ability, 10)
        return (stat_value - 10) // 2

    def _show_step_skills(self):
        """Шаг 5: Выбор навыков."""
        DirectLabel(
            parent=self.content_frame,
            text="Выберите 2 навыка:",
            scale=NineTheme.LABEL_SCALE,
            pos=(0, 0, 0.35),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        # Подсказка о выбранных
        selected_count = len(self.character_data.get("skills", {}))
        self.skills_count_label = DirectLabel(
            parent=self.content_frame,
            text=f"Выбрано: {selected_count}/2",
            scale=NineTheme.SMALL_SCALE * 0.8,
            pos=(0, 0, 0.27),
            text_fg=NineTheme.TEXT_SECONDARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        # Создаём прокручиваемую область для навыков
        scroll = DirectScrolledFrame(
            parent=self.content_frame,
            frameSize=(-0.55, 0.55, -0.4, 0.22),
            canvasSize=(-0.5, 0.5, -0.9, 0.25),
            frameColor=(0.08, 0.08, 0.12, 0.5),
            pos=(0, 0, -0.08),
            scrollBarWidth=0.03,
            verticalScroll_frameColor=NineTheme.BTN_NORMAL,
            verticalScroll_thumb_frameColor=NineTheme.BTN_ACCENT_NORMAL,
        )

        canvas = scroll.getCanvas()
        self.skill_buttons = {}
        skills = list(SKILLS.keys())
        start_y = 0.2
        spacing = 0.1

        selected_skills = list(self.character_data.get("skills", {}).keys())

        for i, skill in enumerate(skills):
            y = start_y - i * spacing
            is_selected = skill in selected_skills
            color = NineTheme.accent_button_colors() if is_selected else NineTheme.button_colors()

            # Получаем русское название и модификатор
            skill_data = SKILLS.get(skill, {})
            skill_name_ru = skill_data.get("name", skill)
            modifier = self._get_skill_modifier(skill)
            modifier_str = f"+{modifier}" if modifier >= 0 else str(modifier)

            btn_text = f"{skill_name_ru} ({modifier_str})"

            self.skill_buttons[skill] = DirectButton(
                parent=canvas,
                text=btn_text,
                scale=NineTheme.SMALL_SCALE * 0.9,
                pos=(0, 0, y),
                command=lambda s=skill: self._toggle_skill(s),
                frameColor=color,
                text_fg=NineTheme.TEXT_PRIMARY,
                text_align=TextNode.ACenter,
                pressEffect=True,
                relief=DGG.FLAT,
                frameSize=(-7, 7, -1.1, 1.4),
            )

    def _toggle_skill(self, skill: str):
        """Переключает выбор навыка."""
        skills = self.character_data.get("skills", {})
        if skill in skills:
            del skills[skill]
        else:
            if len(skills) >= 2:
                # Уже выбрано 2 навыка - заменяем первый
                first = list(skills.keys())[0]
                del skills[first]
                if first in self.skill_buttons:
                    self.skill_buttons[first]['frameColor'] = NineTheme.button_colors()
            skills[skill] = True

        self.character_data["skills"] = skills

        # Обновляем цвет кнопки
        if skill in self.skill_buttons:
            if skill in skills:
                self.skill_buttons[skill]['frameColor'] = NineTheme.accent_button_colors()
            else:
                self.skill_buttons[skill]['frameColor'] = NineTheme.button_colors()

        # Обновляем счётчик
        if hasattr(self, 'skills_count_label'):
            self.skills_count_label['text'] = f"Выбрано: {len(skills)}/2"

    def _show_step_background(self):
        """Шаг 6: Выбор предыстории."""
        DirectLabel(
            parent=self.content_frame,
            text="Выберите предысторию:",
            scale=NineTheme.LABEL_SCALE,
            pos=(0, 0, 0.35),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        # Создаём прокручиваемую область
        scroll = DirectScrolledFrame(
            parent=self.content_frame,
            frameSize=(-0.55, 0.55, -0.35, 0.25),
            canvasSize=(-0.5, 0.5, -0.7, 0.3),
            frameColor=(0.08, 0.08, 0.12, 0.5),
            pos=(0, 0, -0.05),
            scrollBarWidth=0.03,
            verticalScroll_frameColor=NineTheme.BTN_NORMAL,
            verticalScroll_thumb_frameColor=NineTheme.BTN_ACCENT_NORMAL,
        )

        canvas = scroll.getCanvas()
        self.bg_buttons = {}
        backgrounds = list(BACKGROUNDS.keys())
        start_y = 0.25
        spacing = 0.1

        for i, bg in enumerate(backgrounds):
            y = start_y - i * spacing

            is_selected = self.character_data["background"] == bg
            color = NineTheme.accent_button_colors() if is_selected else NineTheme.button_colors()

            # Получаем бонусы
            bg_data = BACKGROUNDS.get(bg, {})
            bg_name_ru = bg_data.get("name", BACKGROUND_NAMES_RU.get(bg, bg.title()))
            skills = bg_data.get("skill_proficiencies", [])
            skills_str = ", ".join(SKILL_NAMES_RU.get(s.lower().replace(" ", "_"), s) for s in skills)
            btn_text = f"{bg_name_ru} ({skills_str})"

            self.bg_buttons[bg] = DirectButton(
                parent=canvas,
                text=btn_text,
                scale=NineTheme.SMALL_SCALE,
                pos=(0, 0, y),
                command=lambda b=bg: self._select_background(b),
                frameColor=color,
                text_fg=NineTheme.TEXT_PRIMARY,
                text_align=TextNode.ACenter,
                pressEffect=True,
                relief=DGG.FLAT,
                frameSize=(-12, 12, -1, 1.5),
            )

        # Описание выбранной предыстории
        self.bg_desc_label = DirectLabel(
            parent=self.content_frame,
            text=self._get_background_description(self.character_data["background"]),
            scale=NineTheme.SMALL_SCALE * 0.9,
            pos=(0, 0, -0.45),
            text_fg=NineTheme.TEXT_SECONDARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

    def _get_background_description(self, bg: str) -> str:
        """Возвращает описание предыстории."""
        bg_data = BACKGROUNDS.get(bg, {})
        desc = bg_data.get("description", "")
        gold = bg_data.get("gold", 0)
        return f"{desc}\nСтартовое золото: {gold}"

    def _select_background(self, bg: str):
        """Выбор предыстории."""
        self.character_data["background"] = bg
        for b, btn in self.bg_buttons.items():
            if b == bg:
                btn['frameColor'] = NineTheme.accent_button_colors()
            else:
                btn['frameColor'] = NineTheme.button_colors()
        if hasattr(self, 'bg_desc_label'):
            self.bg_desc_label['text'] = self._get_background_description(bg)

    def _show_step_confirm(self):
        """Шаг 7: Подтверждение."""
        DirectLabel(
            parent=self.content_frame,
            text="Подтвердите создание:",
            scale=NineTheme.LABEL_SCALE,
            pos=(0, 0, 0.35),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        # Сводка персонажа
        name = self.character_data.get("character_name", "Безымянный")
        gender = "М" if self.character_data["gender"] == "male" else "Ж"
        race_key = self.character_data["race"]
        race_data = RACES.get(race_key, {})
        race = race_data.get("name", RACE_NAMES_RU.get(race_key, race_key))
        cls_key = self.character_data["class"]
        cls_data = CLASSES.get(cls_key, {})
        cls = cls_data.get("name", CLASS_NAMES_RU.get(cls_key, cls_key))
        bg_key = self.character_data["background"]
        bg_data = BACKGROUNDS.get(bg_key, {})
        bg = bg_data.get("name", BACKGROUND_NAMES_RU.get(bg_key, bg_key)) if bg_key else "Не выбрана"

        # Получаем выбранные навыки
        selected_skills = list(self.character_data.get("skills", {}).keys())
        skills_ru = []
        for skill in selected_skills:
            skill_data = SKILLS.get(skill, {})
            skill_name = skill_data.get("name", skill)
            modifier = self._get_skill_modifier(skill)
            modifier_str = f"+{modifier}" if modifier >= 0 else str(modifier)
            skills_ru.append(f"{skill_name} ({modifier_str})")
        skills_text = ", ".join(skills_ru) if skills_ru else "Не выбраны"

        # Вычисляем модификаторы характеристик
        str_mod = (self.character_data['strength'] - 10) // 2
        dex_mod = (self.character_data['dexterity'] - 10) // 2
        con_mod = (self.character_data['constitution'] - 10) // 2
        int_mod = (self.character_data['intelligence'] - 10) // 2
        wis_mod = (self.character_data['wisdom'] - 10) // 2
        cha_mod = (self.character_data['charisma'] - 10) // 2

        def fmt_mod(m):
            return f"+{m}" if m >= 0 else str(m)

        summary = f"""{name} ({gender})
{race} {cls}
Предыстория: {bg}

СИЛ: {self.character_data['strength']} ({fmt_mod(str_mod)})  ЛОВ: {self.character_data['dexterity']} ({fmt_mod(dex_mod)})  ТЕЛ: {self.character_data['constitution']} ({fmt_mod(con_mod)})
ИНТ: {self.character_data['intelligence']} ({fmt_mod(int_mod)})  МДР: {self.character_data['wisdom']} ({fmt_mod(wis_mod)})  ХАР: {self.character_data['charisma']} ({fmt_mod(cha_mod)})

Навыки: {skills_text}"""

        DirectLabel(
            parent=self.content_frame,
            text=summary.strip(),
            scale=NineTheme.SMALL_SCALE * 0.9,
            pos=(0, 0, 0.05),
            text_fg=NineTheme.TEXT_SECONDARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

    def _next_step(self):
        """Переход к следующему шагу или создание персонажа."""
        # Сохраняем данные текущего шага
        if self.current_step == 1:
            if hasattr(self, 'name_entry'):
                name = self.name_entry.get().strip()
                if len(name) < 2:
                    return  # Имя слишком короткое
                self.character_data["character_name"] = name

        if self.current_step < self.total_steps:
            self._show_step(self.current_step + 1)
        else:
            # Создаём персонажа
            self._create_character()

    def _prev_step(self):
        """Возврат к предыдущему шагу."""
        if self.current_step > 1:
            self._show_step(self.current_step - 1)

    def _create_character(self):
        """Отправляет запрос на создание персонажа."""
        if self.client:
            self.client.send_message({
                "type": "character_create",
                **self.character_data
            })

    def _cancel(self):
        """Отмена создания персонажа."""
        self.ui_manager.hide_character_create()

    def show(self):
        """Показывает UI."""
        if 'background' in self._elements:
            self._elements['background'].show()
        if 'panel' in self._elements:
            self._elements['panel'].show()

    def hide(self):
        """Скрывает UI."""
        if 'background' in self._elements:
            self._elements['background'].hide()
        if 'panel' in self._elements:
            self._elements['panel'].hide()
