# nine/ui/login_menu.py
"""
Меню входа/подключения.
Использует блочную систему layout.
"""

from direct.gui.DirectGui import DirectFrame
from panda3d.core import TransparencyAttrib

from .base_component import BaseUIComponent
from .blocks import Block
from .bg1_button import BG1Button
from .ui_config import ui


class LoginMenu(BaseUIComponent):
    """Меню входа на сервер."""

    def __init__(self, ui_manager, default_ip: str, default_name: str):
        super().__init__(ui_manager)
        self._default_ip = default_ip
        self._default_name = default_name
        self._block = None
        self._create_window()

    def _create_window(self):
        """Создает элементы меню входа."""
        # Тёмный фон
        bg = DirectFrame(
            parent=self.base.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=ui.colors.bg_dark,
        )
        bg.setTransparency(TransparencyAttrib.M_alpha)
        self._add_element('background', bg)

        # Блок формы входа
        self._block = Block(
            parent=self.base.aspect2d,
            width=1.2,
            padding=ui.spacing.panel_padding,
            bg_color=ui.colors.bg_medium,
            pos=(0, 0, 0)
        )

        # Заголовок
        self._block.label("ПОДКЛЮЧЕНИЕ", style="title", align="center")
        self._block.spacer(ui.spacing.lg)

        # IP сервера
        self._block.label("IP Сервера:", style="label")
        self._block.spacer(ui.spacing.xs)
        row_ip = self._block.row()
        row_ip.entry(name="ip", initial=self._default_ip, width=20, focus=True)

        self._block.spacer(ui.spacing.md)

        # Имя персонажа
        self._block.label("Имя персонажа:", style="label")
        self._block.spacer(ui.spacing.xs)
        row_name = self._block.row()
        row_name.entry(name="name", initial=self._default_name, width=20)

        self._block.spacer(ui.spacing.md)

        # Пароль
        self._block.label("Пароль:", style="label")
        self._block.spacer(ui.spacing.xs)
        row_pass = self._block.row()
        row_pass.entry(name="password", initial="", width=20, obscured=True)

        self._block.spacer(ui.spacing.lg)

        # Строим блок сначала (без кнопок)
        frame = self._block.build()
        self._add_element('panel', frame)

        # Кнопки - создаём напрямую через BG1Button для правильного позиционирования
        login_btn = BG1Button.create(
            parent=frame,
            text="Войти",
            command=self.ui_manager.callbacks.get("attempt_login"),
            pos=(-0.15, 0, -0.35),
            scale=0.045,
            width=2.5,
            height=1.0,
        )
        self._add_element('login_btn', login_btn)

        back_btn = BG1Button.create(
            parent=frame,
            text="Назад",
            command=self.ui_manager.callbacks.get("close_login_menu"),
            pos=(0.15, 0, -0.35),
            scale=0.045,
            width=2.5,
            height=1.0,
        )
        self._add_element('back_btn', back_btn)

        self._play_open_sound()

    def destroy(self):
        """Уничтожает меню."""
        if self._block:
            self._block.destroy()
            self._block = None
        super().destroy()

    def get_credentials(self) -> dict:
        """Возвращает словарь с данными для входа."""
        return {
            "ip": self._block.get("ip") if self._block else "",
            "name": self._block.get("name") if self._block else "",
            "password": self._block.get("password") if self._block else ""
        }
