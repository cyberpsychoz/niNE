"""
Тестовый файл для проверки UI элементов.
Запуск: python test_ui.py
"""

from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectButton, DirectLabel, DGG, OnscreenImage
from panda3d.core import TransparencyAttrib, TextNode, loadPrcFileData

# Настройки окна
loadPrcFileData("", "window-title niNE UI Test")
loadPrcFileData("", "win-size 1280 720")
loadPrcFileData("", "framebuffer-multisample 1")
loadPrcFileData("", "multisamples 2")


class UITest(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # Загружаем шрифт
        try:
            self.font = self.loader.loadFont("nine/assets/fonts/Orbitron-VariableFont_wght.ttf")
            self.font.setPixelsPerUnit(60)
            self.font.setMinfilter(1)
            self.font.setMagfilter(1)
        except:
            self.font = DGG.getDefaultFont()

        # Фон
        bg = OnscreenImage(
            parent=self.render2d,
            image="nine/assets/materials/textures/backgrounds/bg1.jpg",
            pos=(0, 0, 0),
            scale=(2, 1, 1),
        )
        bg.setTransparency(TransparencyAttrib.M_alpha)

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

        # Тестовые кнопки с разными параметрами
        self._test_button_1()
        self._test_button_2()
        self._test_button_3()

        # Инструкция
        DirectLabel(
            parent=self.aspect2d,
            text="Нажмите F9 для скриншота",
            scale=0.04,
            pos=(0, 0, -0.8),
            text_fg=(1, 1, 1, 0.7),
            frameColor=(0, 0, 0, 0),
        )

        self.accept("f9", self.screenshot, ["test_ui_screenshot.png"])
        print("Тест UI запущен. Нажмите F9 для скриншота.")

    def _test_button_1(self):
        """Кнопка с текущими параметрами из main_menu.py"""
        btn_width = 3.0
        btn_height = 0.8

        btn = DirectButton(
            parent=self.aspect2d,
            text="ИГРАТЬ (текущая версия)",
            text_font=self.font,
            scale=0.06,
            pos=(0, 0, 0.3),
            command=lambda: print("Button 1 clicked"),
            text_align=TextNode.ACenter,
            text_fg=(0.9, 0.85, 0.7, 1),
            text_shadow=(0, 0, 0, 0.9),
            text_shadowOffset=(0.003, 0.003),
            frameSize=(-btn_width, btn_width, -btn_height, btn_height),
            frameColor=(0.15, 0.12, 0.10, 0.9),
            relief=DGG.FLAT,
            rolloverSound=None,
            clickSound=None,
        )
        btn.setTransparency(TransparencyAttrib.M_alpha)

        def on_enter(event):
            btn['text_fg'] = (1, 0.95, 0.8, 1)
            btn['frameColor'] = (0.25, 0.20, 0.15, 0.95)

        def on_exit(event):
            btn['text_fg'] = (0.9, 0.85, 0.7, 1)
            btn['frameColor'] = (0.15, 0.12, 0.10, 0.9)

        btn.bind(DGG.ENTER, on_enter)
        btn.bind(DGG.EXIT, on_exit)

    def _test_button_2(self):
        """Кнопка с RAISED стилем (рамка)"""
        btn = DirectButton(
            parent=self.aspect2d,
            text="НАСТРОЙКИ (RAISED)",
            text_font=self.font,
            scale=0.06,
            pos=(0, 0, 0.0),
            command=lambda: print("Button 2 clicked"),
            text_align=TextNode.ACenter,
            text_fg=(0.9, 0.85, 0.7, 1),
            text_shadow=(0, 0, 0, 0.9),
            text_shadowOffset=(0.003, 0.003),
            frameSize=(-3.5, 3.5, -0.65, 0.65),
            frameColor=(0.15, 0.12, 0.10, 0.9),
            relief=DGG.RAISED,
            borderWidth=(0.01, 0.01),
            rolloverSound=None,
            clickSound=None,
        )
        btn.setTransparency(TransparencyAttrib.M_alpha)

    def _test_button_3(self):
        """Кнопка с SUNKEN стилем (вдавленная рамка)"""
        btn = DirectButton(
            parent=self.aspect2d,
            text="ВЫХОД (SUNKEN)",
            text_font=self.font,
            scale=0.06,
            pos=(0, 0, -0.3),
            command=lambda: print("Button 3 clicked"),
            text_align=TextNode.ACenter,
            text_fg=(0.9, 0.85, 0.7, 1),
            text_shadow=(0, 0, 0, 0.9),
            text_shadowOffset=(0.003, 0.003),
            frameSize=(-3.5, 3.5, -0.65, 0.65),
            frameColor=(0.15, 0.12, 0.10, 0.9),
            relief=DGG.SUNKEN,
            borderWidth=(0.01, 0.01),
            rolloverSound=None,
            clickSound=None,
        )
        btn.setTransparency(TransparencyAttrib.M_alpha)


if __name__ == "__main__":
    app = UITest()
    app.run()
