# nine/ui/login_menu.py
from .base_component import BaseUIComponent
from direct.gui.DirectGui import DirectFrame, DirectEntry, DirectLabel, DirectButton, DGG
from panda3d.core import LColor, TextNode

class LoginMenu(BaseUIComponent):
    def __init__(self, ui_manager, default_ip: str, default_name: str):
        super().__init__(ui_manager)
        
        self.button_color = (LColor(0.1, 0.1, 0.1, 0.8), LColor(0.2, 0.2, 0.2, 0.8), LColor(0.3, 0.3, 0.3, 0.8), LColor(0.1, 0.1, 0.1, 0.5))

        self._create_window(default_ip, default_name)

    def _create_window(self, default_ip, default_name):
        """Создает элементы меню входа."""
        frame = self._add_element('root', DirectFrame(
            parent=self.base.aspect2d, 
            frameColor=(0, 0, 0, 0.7), 
            frameSize=(-0.7, 0.7, -0.5, 0.5)
        ))
        
        # Поле для IP
        self._add_element('ip_entry', DirectEntry(
            parent=frame, scale=0.06, pos=(-0.6, 0, 0.35), initialText=default_ip,
            numLines=1, focus=1, text_align=TextNode.ALeft, width=20
        ))
        self._add_element('ip_label', DirectLabel(
            parent=frame, text="IP Сервера:", pos=(-0.6, 0, 0.42), scale=0.05, text_align=TextNode.ALeft
        ))
        
        # Поле для имени
        self._add_element('name_entry', DirectEntry(
            parent=frame, scale=0.06, pos=(-0.6, 0, 0.15), initialText=default_name,
            numLines=1, text_align=TextNode.ALeft, width=20
        ))
        self._add_element('name_label', DirectLabel(
            parent=frame, text="Имя персонажа:", pos=(-0.6, 0, 0.22), scale=0.05, text_align=TextNode.ALeft
        ))

        # Поле для пароля
        self._add_element('password_entry', DirectEntry(
            parent=frame, scale=0.06, pos=(-0.6, 0, -0.05), initialText="",
            numLines=1, text_align=TextNode.ALeft, width=20, obscured=True
        ))
        self._add_element('password_label', DirectLabel(
            parent=frame, text="Пароль:", pos=(-0.6, 0, 0.02), scale=0.05, text_align=TextNode.ALeft
        ))

        # Кнопки
        self._add_element('login_button', DirectButton(
            parent=frame, text="Войти / Регистрация", scale=0.07, pos=(0, 0, -0.3), 
            command=self.ui_manager.callbacks.get("attempt_login"), frameColor=self.button_color
        ))
        self._add_element('back_button', DirectButton(
            parent=frame, text="Назад", scale=0.07, pos=(0, 0, -0.4), 
            command=self.ui_manager.callbacks.get("close_login_menu"), frameColor=self.button_color
        ))
        
    def get_credentials(self) -> dict:
        """Возвращает словарь с данными для входа."""
        return {
            "ip": self._elements['ip_entry'].get() if 'ip_entry' in self._elements else "",
            "name": self._elements['name_entry'].get() if 'name_entry' in self._elements else "",
            "password": self._elements['password_entry'].get() if 'password_entry' in self._elements else ""
        }
