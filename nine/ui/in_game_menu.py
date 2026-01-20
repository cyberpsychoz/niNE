# nine/ui/in_game_menu.py
"""
Игровое меню паузы.
Использует блочную систему layout.
"""

from direct.gui.DirectGui import DirectFrame
from panda3d.core import TransparencyAttrib

from .base_component import BaseUIComponent
from .blocks import Block
from .ui_config import ui


class InGameMenu(BaseUIComponent):
    """Меню паузы с автоматическим layout."""

    def __init__(self, ui_manager, client):
        super().__init__(ui_manager)
        self.client = client
        self._block = None
        self._setup()

    def _setup(self):
        """Создает элементы меню."""
        # Затемняющий оверлей
        self._overlay = DirectFrame(
            parent=self.base.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=ui.colors.bg_overlay,
        )
        self._overlay.setTransparency(TransparencyAttrib.M_alpha)
        self._add_element('overlay', self._overlay)

        # Создаём блок меню
        self._block = Block(
            parent=self.base.aspect2d,
            width=0.8,
            padding=ui.spacing.panel_padding,
            bg_color=ui.colors.bg_medium,
            pos=(0, 0, 0)
        )

        # Заголовок по центру
        self._block.label("ПАУЗА", style="title", align="center")
        self._block.spacer(ui.spacing.lg)

        # Кнопки - каждая в отдельном row по центру
        row1 = self._block.row(justify="center")
        row1.button("Продолжить", command=self._on_continue_click, small=True)

        self._block.spacer(ui.spacing.sm)

        row2 = self._block.row(justify="center")
        row2.button("Настройки", command=self._on_settings_click, small=True)

        self._block.spacer(ui.spacing.sm)

        row3 = self._block.row(justify="center")
        row3.button("Отключиться", command=self._on_disconnect_click, small=True)

        self._block.spacer(ui.spacing.md)

        # Строим
        frame = self._block.build()
        self._add_element('panel', frame)

        self.hide()

    def show(self):
        """Показывает меню."""
        self._play_open_sound()
        self._overlay.show()
        self._block.show()

    def hide(self):
        """Скрывает меню."""
        self._overlay.hide()
        if self._block:
            self._block.hide()

    def destroy(self):
        """Уничтожает меню."""
        if self._block:
            self._block.destroy()
            self._block = None
        super().destroy()

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
