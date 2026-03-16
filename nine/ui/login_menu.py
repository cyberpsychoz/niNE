# nine/ui/login_menu.py
"""
Меню входа/подключения.
Полностью переписано с использованием blocks_v2.
"""

from direct.gui.DirectGui import DirectFrame
from panda3d.core import TransparencyAttrib

from .base_component import BaseUIComponent
from .blocks_v2 import Block
from .ui_config import ui


class LoginMenu(BaseUIComponent):
    """Меню входа на сервер - чистый blocks_v2 дизайн."""

    def __init__(self, ui_manager, default_ip: str, default_name: str):
        super().__init__(ui_manager)
        self._default_ip = default_ip
        self._default_name = default_name
        self._block = None
        self._create_window()

    def _create_window(self):
        """Создает элементы меню входа."""
        # Тёмный фон на весь экран
        bg = DirectFrame(
            parent=self.base.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=ui.colors.bg_dark,
        )
        bg.setTransparency(TransparencyAttrib.M_alpha)
        self._add_element('background', bg)

        # Основной блок формы
        self._block = Block(
            parent=self.base.aspect2d,
            width=1.0,  # Компактнее
            padding=0.08,
            bg_color=ui.colors.bg_medium,
            pos=(0, 0, 0)
        )

        # Заголовок
        self._block.label("ПОДКЛЮЧЕНИЕ К СЕРВЕРУ", style="title", align="center")
        self._block.spacer(ui.spacing.lg)

        # IP сервера
        self._block.label("IP Адрес:", style="label")
        self._block.spacer(ui.spacing.xs)
        row_ip = self._block.row(justify="center")
        row_ip.entry(
            name="ip",
            initial=self._default_ip,
            width=24,
            max_width=0.8,
            focus=True
        )
        self._block.spacer(ui.spacing.md)

        # Имя персонажа
        self._block.label("Имя персонажа:", style="label")
        self._block.spacer(ui.spacing.xs)
        row_name = self._block.row(justify="center")
        row_name.entry(
            name="name",
            initial=self._default_name,
            width=24,
            max_width=0.8
        )
        self._block.spacer(ui.spacing.md)

        # Пароль
        self._block.label("Пароль:", style="label")
        self._block.spacer(ui.spacing.xs)
        row_pass = self._block.row(justify="center")
        row_pass.entry(
            name="password",
            initial="",
            width=24,
            max_width=0.8,
            obscured=True
        )
        self._block.spacer(ui.spacing.xl)

        # Кнопки в одной строке
        btn_row = self._block.row(justify="center", gap=0.08)
        btn_row.button(
            "ВОЙТИ",
            command=self._on_login_click,
            small=False
        )
        btn_row.button(
            "НАЗАД",
            command=self._on_back_click,
            small=False
        )

        # Строим весь блок
        frame = self._block.build()
        self._add_element('panel', frame)

        self._play_open_sound()

    def _on_login_click(self):
        """Обработчик кнопки Войти."""
        callback = self.ui_manager.callbacks.get("attempt_login")
        if callback:
            callback()

    def _on_back_click(self):
        """Обработчик кнопки Назад."""
        callback = self.ui_manager.callbacks.get("close_login_menu")
        if callback:
            callback()

    def get_credentials(self) -> dict:
        """Возвращает словарь с данными для входа."""
        if not self._block:
            return {"ip": "", "name": "", "password": ""}

        return {
            "ip": self._block.get("ip") or "",
            "name": self._block.get("name") or "",
            "password": self._block.get("password") or ""
        }

    def destroy(self):
        """Уничтожает меню."""
        if self._block:
            self._block.destroy()
            self._block = None
        super().destroy()
