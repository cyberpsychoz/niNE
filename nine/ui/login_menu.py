# nine/ui/login_menu.py
"""
Меню входа/подключения.
Минималистичный тёмный дизайн.
"""

from direct.gui.DirectGui import DirectFrame, DirectEntry, DirectLabel, DirectButton, DGG
from panda3d.core import TextNode, TransparencyAttrib

from .base_component import BaseUIComponent
from .theme import NineTheme


class LoginMenu(BaseUIComponent):
    """Меню входа на сервер."""

    def __init__(self, ui_manager, default_ip: str, default_name: str):
        super().__init__(ui_manager)
        self._create_window(default_ip, default_name)

    def _create_window(self, default_ip, default_name):
        """Создает элементы меню входа."""
        # Полупрозрачный тёмный фон
        bg = self._add_element('background', DirectFrame(
            parent=self.base.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=NineTheme.BG_DARK,
        ))
        bg.setTransparency(TransparencyAttrib.M_alpha)

        # Центральная панель
        panel_width = 1.0
        panel_height = 1.0
        panel = self._add_element('panel', DirectFrame(
            parent=self.base.aspect2d,
            frameSize=(-panel_width/2, panel_width/2, -panel_height/2, panel_height/2),
            frameColor=NineTheme.BG_MEDIUM,
            pos=(0, 0, 0),
        ))
        panel.setTransparency(TransparencyAttrib.M_alpha)

        # Заголовок (центрирован)
        self._add_element('title', DirectLabel(
            parent=panel,
            text="ПОДКЛЮЧЕНИЕ",
            scale=NineTheme.TITLE_SCALE,
            pos=(0, 0, panel_height/2 - 0.10),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        ))

        # Поля ввода
        field_x = -panel_width/2 + 0.1
        field_width = (panel_width - 0.16) / NineTheme.ENTRY_SCALE

        # IP Сервера
        self._add_element('ip_label', DirectLabel(
            parent=panel,
            text="IP Сервера:",
            scale=NineTheme.LABEL_SCALE,
            pos=(field_x, 0, 0.2),
            text_fg=NineTheme.TEXT_SECONDARY,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
        ))
        self._add_element('ip_entry', DirectEntry(
            parent=panel,
            scale=NineTheme.ENTRY_SCALE,
            pos=(field_x, 0, 0.10),
            initialText=default_ip,
            numLines=1,
            focus=1,
            text_align=TextNode.ALeft,
            width=field_width,
            frameColor=NineTheme.ENTRY_BG,
            text_fg=NineTheme.TEXT_PRIMARY,
            cursorKeys=True,
        ))

        # Имя персонажа
        self._add_element('name_label', DirectLabel(
            parent=panel,
            text="Имя персонажа:",
            scale=NineTheme.LABEL_SCALE,
            pos=(field_x, 0, 0.02),
            text_fg=NineTheme.TEXT_SECONDARY,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
        ))
        self._add_element('name_entry', DirectEntry(
            parent=panel,
            scale=NineTheme.ENTRY_SCALE,
            pos=(field_x, 0, -0.07),
            initialText=default_name,
            numLines=1,
            text_align=TextNode.ALeft,
            width=field_width,
            frameColor=NineTheme.ENTRY_BG,
            text_fg=NineTheme.TEXT_PRIMARY,
            cursorKeys=True,
        ))

        # Пароль
        self._add_element('password_label', DirectLabel(
            parent=panel,
            text="Пароль:",
            scale=NineTheme.LABEL_SCALE,
            pos=(field_x, 0, -0.15),
            text_fg=NineTheme.TEXT_SECONDARY,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
        ))
        self._add_element('password_entry', DirectEntry(
            parent=panel,
            scale=NineTheme.ENTRY_SCALE,
            pos=(field_x, 0, -0.24),
            initialText="",
            numLines=1,
            text_align=TextNode.ALeft,
            width=field_width,
            obscured=True,
            frameColor=NineTheme.ENTRY_BG,
            text_fg=NineTheme.TEXT_PRIMARY,
            cursorKeys=True,
        ))

        # Кнопки
        btn_y = -panel_height/2 + 0.12
        btn_spacing = 0.28

        # Кнопка "Войти" (акцентная)
        login_btn = self._add_element('login_button', DirectButton(
            parent=panel,
            text="Войти",
            scale=NineTheme.BUTTON_SCALE,
            pos=(-btn_spacing/2 - 0.08, 0, btn_y),
            command=self.ui_manager.callbacks.get("attempt_login"),
            frameColor=NineTheme.accent_button_colors(),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            pressEffect=True,
            relief=DGG.FLAT,
            frameSize=(-2.5, 2.5, -0.8, 1.1),
        ))

        # Кнопка "Назад"
        back_btn = self._add_element('back_button', DirectButton(
            parent=panel,
            text="Назад",
            scale=NineTheme.BUTTON_SCALE,
            pos=(btn_spacing/2, 0, btn_y),
            command=self.ui_manager.callbacks.get("close_login_menu"),
            frameColor=NineTheme.button_colors(),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            pressEffect=True,
            relief=DGG.FLAT,
            frameSize=(-2.5, 2.5, -0.8, 1.1),
        ))

    def get_credentials(self) -> dict:
        """Возвращает словарь с данными для входа."""
        return {
            "ip": self._elements['ip_entry'].get() if 'ip_entry' in self._elements else "",
            "name": self._elements['name_entry'].get() if 'name_entry' in self._elements else "",
            "password": self._elements['password_entry'].get() if 'password_entry' in self._elements else ""
        }
