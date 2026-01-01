# nine/ui/settings_menu.py
"""
Меню настроек.
Минималистичный тёмный дизайн.
"""

from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectEntry, DirectLabel,
    DirectOptionMenu, DGG, DirectSlider
)
from panda3d.core import TextNode, WindowProperties, TransparencyAttrib

from .base_component import BaseUIComponent
from .theme import NineTheme
from nine.core.config import config


class SettingsMenu(BaseUIComponent):
    """Меню настроек."""

    def __init__(self, ui_manager, client):
        super().__init__(ui_manager)
        self.client = client
        self._setup()

    def _setup(self):
        """Создает элементы меню настроек."""
        # Полупрозрачный тёмный фон
        bg = self._add_element('background', DirectFrame(
            parent=self.base.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=NineTheme.BG_DARK,
        ))
        bg.setTransparency(TransparencyAttrib.M_alpha)

        # Центральная панель
        panel_width = 2
        panel_height = 1
        panel = self._add_element('panel', DirectFrame(
            parent=self.base.aspect2d,
            frameSize=(-panel_width/2, panel_width/2, -panel_height/2, panel_height/2),
            frameColor=NineTheme.BG_MEDIUM,
            pos=(0, 0, 0),
            sortOrder=10
        ))
        panel.setTransparency(TransparencyAttrib.M_alpha)

        # Заголовок (центрирован)
        self._add_element('title', DirectLabel(
            parent=panel,
            text="НАСТРОЙКИ",
            scale=NineTheme.TITLE_SCALE,
            pos=(0, 0, panel_height/2 - 0.10),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        ))

        # Поля настроек
        label_x = -panel_width/2 + 0.08
        value_x = 0.05
        row_height = 0.12

        # Никнейм
        row_y = 0.18
        self._add_element('nickname_label', DirectLabel(
            parent=panel,
            text="Никнейм:",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        ))
        self._add_element('nickname_entry', DirectEntry(
            parent=panel,
            scale=NineTheme.ENTRY_SCALE,
            pos=(value_x, 0, row_y),
            initialText=config.get("nickname"),
            numLines=1,
            width=12,
            text_align=TextNode.ALeft,
            frameColor=NineTheme.ENTRY_BG,
            text_fg=NineTheme.TEXT_PRIMARY,
            cursorKeys=True,
        ))

        # Разрешение
        row_y -= row_height
        self._add_element('resolution_label', DirectLabel(
            parent=panel,
            text="Разрешение:",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        ))

        available_resolutions = config.get("available_resolutions")
        current_resolution = config.get("resolution")

        self._add_element('resolution_option_menu', DirectOptionMenu(
            parent=panel,
            text=current_resolution,
            scale=NineTheme.ENTRY_SCALE,
            pos=(value_x, 0, row_y),
            items=available_resolutions,
            initialitem=available_resolutions.index(current_resolution) if current_resolution in available_resolutions else 0,
            highlightColor=NineTheme.BTN_HOVER,
            frameColor=NineTheme.ENTRY_BG,
            text_fg=NineTheme.TEXT_PRIMARY,
            popupMarker_frameColor=NineTheme.BTN_NORMAL,
            sortOrder=11,
            command=self._on_resolution_selected
        ))

        # Чувствительность камеры
        row_y -= row_height
        self._add_element('sensitivity_label', DirectLabel(
            parent=panel,
            text="Чувствительность камеры:",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        ))

        initial_sensitivity = config.get("camera_sensitivity", 1.0)

        self.sensitivity_slider = self._add_element('sensitivity_slider', DirectSlider(
            parent=panel,
            range=(0.1, 3.0),
            value=initial_sensitivity,
            scale=0.35,
            pos=(value_x + 0.15, 0, row_y),
            thumb_frameColor=NineTheme.BTN_HOVER,
            frameColor=NineTheme.BG_LIGHT,
            command=self._on_sensitivity_changed
        ))

        self.sensitivity_value_label = self._add_element('sensitivity_value_label', DirectLabel(
            parent=panel,
            text=f"{initial_sensitivity:.2f}",
            scale=NineTheme.LABEL_SCALE,
            pos=(panel_width/2 - 0.1, 0, row_y),
            text_align=TextNode.ARight,
            text_fg=NineTheme.TEXT_PRIMARY,
            frameColor=(0, 0, 0, 0),
        ))

        # Кнопки
        btn_y = -panel_height/2 + 0.12
        btn_spacing = 0.30

        # Кнопка "Сохранить" (акцентная)
        save_btn = self._add_element('save_button', DirectButton(
            parent=panel,
            text="Сохранить",
            scale=NineTheme.BUTTON_SCALE,
            pos=(-btn_spacing/2 - 0.2, 0, btn_y),
            command=self._on_save_click,
            frameColor=NineTheme.accent_button_colors(),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            pressEffect=True,
            relief=DGG.FLAT,
            frameSize=(-3.5, 3.5, -0.8, 1.1),
        ))

        # Кнопка "Назад"
        back_btn = self._add_element('back_button', DirectButton(
            parent=panel,
            text="Назад",
            scale=NineTheme.BUTTON_SCALE,
            pos=(btn_spacing/2, 0, btn_y),
            command=self._on_back_click,
            frameColor=NineTheme.button_colors(),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            pressEffect=True,
            relief=DGG.FLAT,
            frameSize=(-3.5, 3.5, -0.8, 1.1),
        ))

        self.hide()

    def _on_sensitivity_changed(self):
        """Callback при изменении слайдера чувствительности."""
        new_sensitivity = self.sensitivity_slider.getValue()
        self.sensitivity_value_label['text'] = f"{new_sensitivity:.2f}"
        if self.client and self.client.camera_controller:
            self.client.camera_controller.sensitivity_multiplier = new_sensitivity

    def _on_resolution_selected(self, selection):
        """Callback при выборе разрешения."""
        pass

    def _on_save_click(self):
        """Сохраняет настройки."""
        new_nickname = self._elements['nickname_entry'].get()
        selected_resolution = self._elements['resolution_option_menu'].get()
        new_sensitivity = self.sensitivity_slider.getValue()

        # Обновляем конфиг
        config.set("nickname", new_nickname)
        config.set("resolution", selected_resolution)
        config.set("camera_sensitivity", new_sensitivity)

        # Применяем никнейм
        self.client.character_name = new_nickname

        # Применяем разрешение
        width, height = map(int, selected_resolution.split('x'))
        props = WindowProperties()
        props.setSize(width, height)
        self.client.win.requestProperties(props)

        self.ui_manager.hide_settings_menu()
        self.ui_manager.show_main_menu()

    def _on_back_click(self):
        """Возврат без сохранения."""
        self.ui_manager.hide_settings_menu()
        self.ui_manager.show_main_menu()
