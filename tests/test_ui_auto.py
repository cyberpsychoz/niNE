"""
Автоматический тест UI с созданием скриншота.
"""

from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectButton, DirectLabel, DGG, OnscreenImage
from panda3d.core import TransparencyAttrib, TextNode, loadPrcFileData
from direct.task import Task


class UITestAuto(ShowBase):
    def __init__(self):
        # Настройки окна
        loadPrcFileData("", "window-title niNE UI Test")
        loadPrcFileData("", "win-size 1280 720")

        ShowBase.__init__(self)

        # Загружаем шрифт
        try:
            self.font = self.loader.loadFont("nine/assets/fonts/Orbitron-VariableFont_wght.ttf")
            self.font.setPixelsPerUnit(60)
        except:
            self.font = DGG.getDefaultFont()

        self.setup_ui()

        # Создаём скриншот через 2 секунды и закрываем
        self.taskMgr.doMethodLater(2.0, self.take_screenshot_and_exit, "screenshot_task")

    def setup_ui(self):
        """Настраивает UI элементы"""
        # Простой фон
        bg = DirectLabel(
            parent=self.render2d,
            frameColor=(0.1, 0.1, 0.15, 1),
            frameSize=(-2, 2, -1, 1),
        )

        # Заголовок
        DirectLabel(
            parent=self.aspect2d,
            text="DUNGEONS & DRAGONS",
            scale=0.09,
            pos=(0, 0, 0.7),
            text_font=self.font,
            text_fg=(0.9, 0.8, 0.5, 1),
            text_shadow=(0, 0, 0, 1),
            text_shadowOffset=(0.003, 0.003),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )

        # Версия 1: Текущая из main_menu.py
        self.create_button(
            text="ИГРАТЬ",
            pos=(0, 0, 0.3),
            label_text="Текущая версия (frameSize: -3.0, 3.0, -0.8, 0.8)",
            label_pos=(0, 0, 0.45)
        )

        # Версия 2: С RAISED рамкой
        btn2 = DirectButton(
            parent=self.aspect2d,
            text="НАСТРОЙКИ",
            text_font=self.font,
            scale=0.06,
            pos=(0, 0, 0.0),
            text_align=TextNode.ACenter,
            text_fg=(0.9, 0.85, 0.7, 1),
            text_shadow=(0, 0, 0, 0.9),
            text_shadowOffset=(0.003, 0.003),
            frameSize=(-3.5, 3.5, -0.65, 0.65),
            frameColor=(0.15, 0.12, 0.10, 0.9),
            relief=DGG.RAISED,
            borderWidth=(0.01, 0.01),
        )
        DirectLabel(
            parent=self.aspect2d,
            text="RAISED стиль (с рамкой)",
            scale=0.03,
            pos=(0, 0, 0.15),
            text_fg=(0.7, 0.7, 0.7, 1),
            frameColor=(0, 0, 0, 0),
        )

        # Версия 3: С более узкой кнопкой
        btn3 = DirectButton(
            parent=self.aspect2d,
            text="ВЫХОД",
            text_font=self.font,
            scale=0.06,
            pos=(0, 0, -0.3),
            text_align=TextNode.ACenter,
            text_fg=(0.9, 0.85, 0.7, 1),
            text_shadow=(0, 0, 0, 0.9),
            text_shadowOffset=(0.003, 0.003),
            frameSize=(-2.5, 2.5, -0.6, 0.6),
            frameColor=(0.15, 0.12, 0.10, 0.9),
            relief=DGG.RAISED,
            borderWidth=(0.015, 0.015),
        )
        DirectLabel(
            parent=self.aspect2d,
            text="Узкая версия (frameSize: -2.5, 2.5, -0.6, 0.6)",
            scale=0.03,
            pos=(0, 0, -0.45),
            text_fg=(0.7, 0.7, 0.7, 1),
            frameColor=(0, 0, 0, 0),
        )

    def create_button(self, text, pos, label_text="", label_pos=(0, 0, 0)):
        """Создаёт кнопку с подписью"""
        btn_width = 3.0
        btn_height = 0.8

        btn = DirectButton(
            parent=self.aspect2d,
            text=text,
            text_font=self.font,
            scale=0.06,
            pos=pos,
            text_align=TextNode.ACenter,
            text_fg=(0.9, 0.85, 0.7, 1),
            text_shadow=(0, 0, 0, 0.9),
            text_shadowOffset=(0.003, 0.003),
            frameSize=(-btn_width, btn_width, -btn_height, btn_height),
            frameColor=(0.15, 0.12, 0.10, 0.9),
            relief=DGG.FLAT,
        )

        if label_text:
            DirectLabel(
                parent=self.aspect2d,
                text=label_text,
                scale=0.03,
                pos=label_pos,
                text_fg=(0.7, 0.7, 0.7, 1),
                frameColor=(0, 0, 0, 0),
            )

    def take_screenshot_and_exit(self, task):
        """Делает скриншот и закрывает приложение"""
        print("Creating screenshot...")
        self.screenshot(namePrefix="ui_test_", defaultFilename=0)
        print("Screenshot saved as ui_test_*.png")
        print("Closing...")
        self.taskMgr.doMethodLater(0.5, lambda t: self.userExit(), "exit_task")
        return Task.done


if __name__ == "__main__":
    app = UITestAuto()
    app.run()
