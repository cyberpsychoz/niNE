"""
Клиентский UI выбора персонажа D&D.
Отображает список персонажей аккаунта с возможностью выбора, удаления или создания нового.
"""

from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton,
    DirectScrolledFrame, DGG
)
from panda3d.core import TextNode, TransparencyAttrib

from nine.ui.base_component import BaseUIComponent
from nine.ui.theme import NineTheme
from nine.ui.ui_config import ui
from nine.ui.bg1_button import BG1Button, BG1ButtonSmall


# Локализация рас и классов
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


class CharacterSelectUI(BaseUIComponent):
    """UI экран выбора персонажа."""

    def __init__(self, ui_manager, characters_data: list, max_characters: int, client):
        super().__init__(ui_manager)
        self.characters = characters_data or []
        self.max_characters = max_characters
        self.client = client
        self._character_cards = []

        self._create_ui()

    def _create_ui(self):
        """Создаёт UI элементы."""
        # Тёмный фон на весь экран
        self._add_element('background', DirectFrame(
            parent=self.base.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=NineTheme.BG_DARK,
        ))

        # Основная панель
        panel_width = 1.6
        panel_height = 1.5
        panel = self._add_element('panel', DirectFrame(
            parent=self.base.aspect2d,
            frameSize=(-panel_width/2, panel_width/2, -panel_height/2, panel_height/2),
            frameColor=NineTheme.BG_MEDIUM,
            pos=(0, 0, 0),
        ))
        panel.setTransparency(TransparencyAttrib.M_alpha)

        # Заголовок
        self._add_element('title', DirectLabel(
            parent=panel,
            text="ВЫБОР ПЕРСОНАЖА",
            scale=NineTheme.TITLE_SCALE,
            pos=(0, 0, panel_height/2 - 0.1),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        ))

        # Подзаголовок с количеством персонажей
        self._add_element('subtitle', DirectLabel(
            parent=panel,
            text=f"Персонажей: {len(self.characters)}/{self.max_characters}",
            scale=NineTheme.SMALL_SCALE,
            pos=(0, 0, panel_height/2 - 0.18),
            text_fg=NineTheme.TEXT_SECONDARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        ))

        # Область прокрутки для карточек персонажей
        scroll_height = 0.9
        scroll_frame = self._add_element('scroll_frame', DirectScrolledFrame(
            parent=panel,
            frameSize=(-panel_width/2 + 0.1, panel_width/2 - 0.1, -scroll_height/2, scroll_height/2),
            canvasSize=(-panel_width/2 + 0.15, panel_width/2 - 0.15, -0.5, 0.5),
            frameColor=(0.08, 0.08, 0.12, 0.5),
            pos=(0, 0, 0.05),
            scrollBarWidth=0.03,
            verticalScroll_frameColor=NineTheme.BTN_NORMAL,
            verticalScroll_thumb_frameColor=NineTheme.BTN_ACCENT_NORMAL,
            horizontalScroll_frameColor=(0, 0, 0, 0),
            horizontalScroll_incButton_frameColor=(0, 0, 0, 0),
            horizontalScroll_decButton_frameColor=(0, 0, 0, 0),
            horizontalScroll_thumb_frameColor=(0, 0, 0, 0),
        ))

        # Создаём карточки персонажей
        self._create_character_cards(scroll_frame.getCanvas())

        # Кнопка "Создать персонажа" (если не достигнут лимит)
        if len(self.characters) < self.max_characters:
            self._add_element('create_btn', BG1Button.create(
                parent=panel,
                text="Создать персонажа",
                command=self._on_create_character,
                pos=(0, 0, -panel_height/2 + 0.15),
            ))

        # Кнопка "Выход" (отключение)
        self._add_element('logout_btn', BG1ButtonSmall.create(
            parent=panel,
            text="Выход",
            command=self._on_logout,
            pos=(-panel_width/2 + 0.18, 0, -panel_height/2 + 0.08),
        ))

    def _create_character_cards(self, canvas):
        """Создаёт карточки для каждого персонажа."""
        card_height = 0.22
        card_width = 1.3
        spacing = 0.05
        start_y = 0.4

        # Очищаем старые карточки
        for card in self._character_cards:
            if hasattr(card, 'destroy'):
                card.destroy()
        self._character_cards.clear()

        # Рассчитываем размер канваса
        total_height = len(self.characters) * (card_height + spacing) + 0.1
        canvas_min = -max(total_height, 0.5)

        # Обновляем размер канваса
        scroll_frame = self._elements.get('scroll_frame')
        if scroll_frame:
            scroll_frame['canvasSize'] = (-0.65, 0.65, canvas_min, 0.45)

        if not self.characters:
            # Показываем сообщение "Нет персонажей"
            empty_label = DirectLabel(
                parent=canvas,
                text="У вас пока нет персонажей.\nСоздайте своего первого героя!",
                scale=NineTheme.LABEL_SCALE,
                pos=(0, 0, 0.1),
                text_fg=NineTheme.TEXT_SECONDARY,
                text_align=TextNode.ACenter,
                frameColor=(0, 0, 0, 0),
            )
            self._character_cards.append(empty_label)
            return

        for i, char in enumerate(self.characters):
            y_pos = start_y - i * (card_height + spacing)

            # Карточка персонажа
            card = DirectFrame(
                parent=canvas,
                frameSize=(-card_width/2, card_width/2, -card_height/2, card_height/2),
                frameColor=NineTheme.BG_LIGHT,
                pos=(0, 0, y_pos),
            )
            card.setTransparency(TransparencyAttrib.M_alpha)
            self._character_cards.append(card)

            # Имя персонажа
            char_name = char.get('character_name', 'Безымянный')
            DirectLabel(
                parent=card,
                text=char_name,
                scale=NineTheme.LABEL_SCALE * 1.2,
                pos=(-card_width/2 + 0.08, 0, card_height/2 - 0.05),
                text_fg=NineTheme.TEXT_HIGHLIGHT,
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
            )

            # Раса, класс, уровень
            race = char.get('race', 'human')
            char_class = char.get('class', 'fighter')
            level = char.get('level', 1)
            hp_current = char.get('hp_current', 10)
            hp_max = char.get('hp_max', 10)
            last_played = char.get('last_played', '')

            race_ru = RACE_NAMES_RU.get(race, race.title())
            class_ru = CLASS_NAMES_RU.get(char_class, char_class.title())

            info_text = f"{race_ru} • {class_ru} • Ур. {level}"
            DirectLabel(
                parent=card,
                text=info_text,
                scale=NineTheme.SMALL_SCALE,
                pos=(-card_width/2 + 0.08, 0, card_height/2 - 0.11),
                text_fg=NineTheme.TEXT_SECONDARY,
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
            )

            # HP и последний вход
            hp_color = (0.3, 0.8, 0.3, 1) if hp_current == hp_max else (0.8, 0.6, 0.2, 1)
            if hp_current < hp_max * 0.3:
                hp_color = (0.8, 0.2, 0.2, 1)

            DirectLabel(
                parent=card,
                text=f"HP: {hp_current}/{hp_max}",
                scale=NineTheme.SMALL_SCALE * 0.9,
                pos=(-card_width/2 + 0.08, 0, -card_height/2 + 0.05),
                text_fg=hp_color,
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
            )

            # Форматируем дату последнего входа
            last_played_str = ""
            if last_played:
                try:
                    from datetime import datetime
                    if isinstance(last_played, str):
                        dt = datetime.fromisoformat(last_played.replace('Z', '+00:00'))
                        last_played_str = dt.strftime("%d.%m.%Y %H:%M")
                except Exception:
                    last_played_str = ""

            if last_played_str:
                DirectLabel(
                    parent=card,
                    text=f"Последняя игра: {last_played_str}",
                    scale=NineTheme.SMALL_SCALE * 0.8,
                    pos=(card_width/2 - 0.35, 0, -card_height/2 + 0.05),
                    text_fg=NineTheme.TEXT_HINT,
                    text_align=TextNode.ARight,
                    frameColor=(0, 0, 0, 0),
                )

            # Кнопка "Играть" в стиле BG1
            char_uuid = char.get('uuid')
            play_btn = BG1ButtonSmall.create(
                parent=card,
                text="Играть",
                command=lambda uuid=char_uuid: self._on_select_character(uuid),
                pos=(card_width/2 - 0.20, 0, 0),
            )
            self._character_cards.append(play_btn)

            # Кнопка "Удалить" (красный X) - иконка в углу карточки
            delete_btn = DirectButton(
                parent=card,
                text="X",
                scale=0.035,  # Маленький масштаб
                pos=(card_width/2 - 0.04, 0, card_height/2 - 0.04),
                command=lambda uuid=char_uuid, name=char_name: self._on_delete_character(uuid, name),
                frameColor=(0.5, 0.12, 0.12, 0.85),
                text_fg=(1, 0.9, 0.9, 1),
                text_align=TextNode.ACenter,
                pressEffect=True,
                relief=DGG.FLAT,
                frameSize=(-1.0, 1.0, -1.0, 1.0),  # Квадратный
            )
            delete_btn.setTransparency(TransparencyAttrib.M_alpha)
            # Эффект при наведении
            delete_btn.bind(DGG.ENTER, lambda e, b=delete_btn: b.setColor(0.7, 0.2, 0.2, 1))
            delete_btn.bind(DGG.EXIT, lambda e, b=delete_btn: b.setColor(1, 1, 1, 1))
            self._character_cards.append(delete_btn)

    def update_characters(self, characters_data: list, max_characters: int):
        """Обновляет список персонажей."""
        self.characters = characters_data or []
        self.max_characters = max_characters

        # Обновляем подзаголовок
        if 'subtitle' in self._elements:
            self._elements['subtitle']['text'] = f"Персонажей: {len(self.characters)}/{self.max_characters}"

        # Пересоздаём карточки
        scroll_frame = self._elements.get('scroll_frame')
        if scroll_frame:
            self._create_character_cards(scroll_frame.getCanvas())

        # Обновляем видимость кнопки создания
        if len(self.characters) >= self.max_characters:
            if 'create_btn' in self._elements:
                self._elements['create_btn'].hide()
        else:
            if 'create_btn' in self._elements:
                self._elements['create_btn'].show()

    def _on_select_character(self, character_uuid: str):
        """Обработчик выбора персонажа."""
        if self.client and character_uuid:
            self.client.send_message({
                "type": "character_select",
                "character_uuid": character_uuid
            })

    def _on_create_character(self):
        """Обработчик создания персонажа."""
        self.ui_manager.show_character_create(self.client)

    def _on_delete_character(self, character_uuid: str, character_name: str):
        """Обработчик удаления персонажа."""
        # TODO: Добавить диалог подтверждения
        if self.client and character_uuid:
            self.client.send_message({
                "type": "character_delete",
                "character_uuid": character_uuid
            })

    def _on_logout(self):
        """Обработчик выхода (отключение от сервера)."""
        if self.client:
            self.client.disconnect()

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
