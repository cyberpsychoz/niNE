# nine/core/ui.py
from direct.gui.DirectGui import (
    DirectFrame,
    DirectButton,
    DirectEntry,
    DGG
)
from panda3d.core import LColor, TextNode

class UIManager:
    """
    Управляет всеми элементами пользовательского интерфейса (DirectGUI).
    """
    def __init__(self, callbacks: dict):
        self.callbacks = callbacks
        self.main_menu_frame = None
        self.settings_frame = None
        self.character_name_entry = None

        # Стили
        self.font = DGG.getDefaultFont()
        self.button_color = (LColor(0.1, 0.1, 0.1, 0.8), LColor(0.2, 0.2, 0.2, 0.8), LColor(0.3, 0.3, 0.3, 0.8), LColor(0.1, 0.1, 0.1, 0.5))

    def create_main_menu(self):
        """Создает главное меню."""
        if self.main_menu_frame:
            self.destroy_main_menu()

        self.main_menu_frame = DirectFrame(frameColor=(0, 0, 0, 0.5), frameSize=(-0.7, 0.7, -0.7, 0.7))

        buttons = [
            ("Подключиться", self.callbacks.get("connect"), -0.1),
            ("Настройки", self.callbacks.get("settings"), -0.3),
            ("Выход", self.callbacks.get("exit"), -0.5)
        ]
        
        # Кнопка "Создать сервер" временно отключена
        # buttons.insert(0, ("Создать сервер", self.callbacks.get("start_server"), 0.1))

        for text, command, z in buttons:
            DirectButton(
                parent=self.main_menu_frame,
                text=text,
                scale=0.07,
                pos=(0, 0, z),
                command=command,
                frameColor=self.button_color,
                text_fg=(1,1,1,1),
                pressEffect=True,
                relief=DGG.FLAT
            )

    def destroy_main_menu(self):
        """Уничтожает главное меню."""
        if self.main_menu_frame:
            self.main_menu_frame.destroy()
            self.main_menu_frame = None

    def create_settings_menu(self, current_name: str):
        """Создает меню настроек."""
        if self.settings_frame:
            self.destroy_settings_menu()

        self.settings_frame = DirectFrame(frameColor=(0, 0, 0, 0.7), frameSize=(-0.8, 0.8, -0.6, 0.6))

        # Поле для ввода имени
        self.character_name_entry = DirectEntry(
            parent=self.settings_frame,
            text="Имя персонажа",
            scale=0.06,
            pos=(-0.7, 0, 0.2),
            initialText=current_name,
            numLines=1,
            focus=1,
            text_align=TextNode.ALeft
        )

        # Кнопка Сохранить
        DirectButton(
            parent=self.settings_frame,
            text="Сохранить",
            scale=0.07,
            pos=(-0.2, 0, -0.4),
            command=self.callbacks.get("save_settings"),
            frameColor=self.button_color,
            text_fg=(1,1,1,1),
            pressEffect=True,
            relief=DGG.FLAT
        )

        # Кнопка Назад
        DirectButton(
            parent=self.settings_frame,
            text="Назад",
            scale=0.07,
            pos=(0.2, 0, -0.4),
            command=self.callbacks.get("close_settings"),
            frameColor=self.button_color,
            text_fg=(1,1,1,1),
            pressEffect=True,
            relief=DGG.FLAT
        )

    def get_character_name(self) -> str:
        """Возвращает имя персонажа из поля ввода."""
        if self.character_name_entry:
            return self.character_name_entry.get()
        return ""

    def destroy_settings_menu(self):
        """Уничтожает меню настроек."""
        if self.settings_frame:
            self.settings_frame.destroy()
            self.settings_frame = None
            self.character_name_entry = None
