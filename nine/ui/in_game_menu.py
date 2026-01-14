# nine/ui/in_game_menu.py
"""
Игровое меню паузы.
Компактное меню в центре экрана.
"""

from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DGG
from panda3d.core import TransparencyAttrib, TextNode

from .base_component import BaseUIComponent
from .theme import NineTheme


class InGameMenu(BaseUIComponent):
    """Меню паузы."""

    def __init__(self, ui_manager, client):
        super().__init__(ui_manager)
        self.client = client
        self._setup()

    def _setup(self):
        """Создает элементы меню."""
        # Полупрозрачный оверлей
        overlay = self._add_element('overlay', DirectFrame(
            parent=self.base.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=NineTheme.BG_OVERLAY,
        ))
        overlay.setTransparency(TransparencyAttrib.M_alpha)

        # Компактная панель (увеличена для длинных кнопок)
        panel_width = 0.6
        panel_height = 0.6
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
            text="ПАУЗА",
            scale=NineTheme.TITLE_SCALE,
            pos=(0, 0, panel_height/2 - 0.10),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        ))

        # Кнопки
        buttons_data = [
            ("Продолжить", self._on_continue_click),
            ("Настройки", self._on_settings_click),
            ("Отключиться", self._on_disconnect_click),
        ]

        button_start_y = 0.12
        button_spacing = 0.14

        for i, (text, command) in enumerate(buttons_data):
            y_pos = button_start_y - i * button_spacing

            btn = self._add_element(f'button_{i}', DirectButton(
                parent=panel,
                text=text,
                scale=NineTheme.BUTTON_SCALE,
                pos=(0, 0, y_pos),
                command=command,
                frameColor=NineTheme.button_colors(),
                text_fg=NineTheme.TEXT_PRIMARY,
                text_align=TextNode.ACenter,
                pressEffect=True,
                relief=DGG.FLAT,
                frameSize=(-3.8, 3.8, -0.8, 1.1),
            ))

        self.hide()

    def _on_continue_click(self):
        """Продолжить игру."""
        self.ui_manager.hide_in_game_menu()
        self.client.in_game_menu_active = False
        self.client.enable_game_input()

    def _on_settings_click(self):
        """Открыть настройки."""
        self.ui_manager.hide_in_game_menu()
        self.ui_manager.show_settings_menu(self.client, from_in_game=True)

    def _on_disconnect_click(self):
        """Отключиться от сервера."""
        self.client.disconnect_from_server()
