"""
Тест текстур кнопок - проверка альфа канала и отображения.
Автоматически делает скриншот и закрывается.
"""
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectButton, DirectFrame, DGG, DirectLabel
from panda3d.core import (
    TransparencyAttrib, Texture, PNMImage,
    TextNode, loadPrcFileData
)
from direct.task import Task
import os

loadPrcFileData("", "window-title Button Texture Test")
loadPrcFileData("", "win-size 800 600")


class ButtonTest(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.setBackgroundColor(0.2, 0.3, 0.4)  # Синий фон для проверки альфы

        tex_path = "nine/assets/materials/textures/ui/buttons/buttons.png"

        if not os.path.exists(tex_path):
            print(f"ERROR: Texture not found: {tex_path}")
            return

        main_tex = self.loader.loadTexture(tex_path)
        print(f"Texture size: {main_tex.getXSize()}x{main_tex.getYSize()}")
        print(f"Texture format: {main_tex.getFormat()}")

        # Показываем полную текстуру
        self._show_full_texture(main_tex)

        # Тесты
        self._test_color_button()
        self._test_full_texture_button(main_tex)
        self._test_extracted_texture_button(main_tex)
        self._test_frame_with_texture(main_tex)

        # Автоскриншот через 2 секунды
        self.taskMgr.doMethodLater(2.0, self._auto_screenshot, "auto_screenshot")

    def _show_full_texture(self, tex):
        frame = DirectFrame(
            parent=self.aspect2d,
            frameSize=(-0.35, 0.35, -0.1, 0.1),
            pos=(-0.9, 0, 0.8),
            frameTexture=tex,
        )
        frame.setTransparency(TransparencyAttrib.M_alpha)
        DirectLabel(parent=self.aspect2d, text="Full texture:", pos=(-0.9, 0, 0.95),
                    scale=0.04, text_fg=(1,1,1,1), frameColor=(0,0,0,0))

    def _test_color_button(self):
        btn = DirectButton(
            parent=self.aspect2d, text="Color", pos=(-0.5, 0, 0.4),
            scale=0.07, frameSize=(-2.5, 2.5, -0.7, 0.7),
            frameColor=(0.3, 0.2, 0.1, 0.9), text_fg=(1, 0.9, 0.7, 1), relief=DGG.FLAT,
        )
        btn.setTransparency(TransparencyAttrib.M_alpha)
        DirectLabel(parent=self.aspect2d, text="1. Color", pos=(-0.5, 0, 0.55),
                    scale=0.035, text_fg=(1,1,0,1), frameColor=(0,0,0,0))

    def _test_full_texture_button(self, tex):
        btn = DirectButton(
            parent=self.aspect2d, text="FullTex", pos=(0.5, 0, 0.4),
            scale=0.07, frameSize=(-2.5, 2.5, -0.7, 0.7),
            frameTexture=tex, text_fg=(1, 0.9, 0.7, 1), relief=DGG.FLAT,
        )
        btn.setTransparency(TransparencyAttrib.M_alpha)
        DirectLabel(parent=self.aspect2d, text="2. Full tex", pos=(0.5, 0, 0.55),
                    scale=0.035, text_fg=(1,1,0,1), frameColor=(0,0,0,0))

    def _test_extracted_texture_button(self, main_tex):
        # Средний столбец (x=40), средний ряд (y=11) = normal
        # Текстура 128x32: 3 столбца по ~40px, 3 ряда по ~11px
        extracted = self._extract_region(main_tex, 40, 11, 40, 11)
        if extracted:
            btn = DirectButton(
                parent=self.aspect2d, text="Extract", pos=(-0.5, 0, 0.0),
                scale=0.07, frameSize=(-2.5, 2.5, -0.7, 0.7),
                frameTexture=extracted, text_fg=(1, 0.9, 0.7, 1), relief=DGG.FLAT,
            )
            btn.setTransparency(TransparencyAttrib.M_alpha)
        DirectLabel(parent=self.aspect2d, text="3. Extracted 40x11", pos=(-0.5, 0, 0.15),
                    scale=0.035, text_fg=(1,1,0,1), frameColor=(0,0,0,0))

    def _test_frame_with_texture(self, main_tex):
        # Тест с DirectFrame (не кнопка)
        extracted = self._extract_region(main_tex, 40, 11, 40, 11)
        if extracted:
            frame = DirectFrame(
                parent=self.aspect2d,
                frameSize=(-0.2, 0.2, -0.06, 0.06),
                pos=(0.5, 0, 0.0),
                frameTexture=extracted,
            )
            frame.setTransparency(TransparencyAttrib.M_alpha)
        DirectLabel(parent=self.aspect2d, text="4. Frame", pos=(0.5, 0, 0.15),
                    scale=0.035, text_fg=(1,1,0,1), frameColor=(0,0,0,0))

    def _extract_region(self, main_tex, x, y, w, h):
        try:
            pnm = PNMImage()
            main_tex.store(pnm)
            print(f"Source: {pnm.getXSize()}x{pnm.getYSize()}, channels={pnm.getNumChannels()}, alpha={pnm.hasAlpha()}")

            # Создаём RGBA изображение
            region_pnm = PNMImage(w, h, 4)
            region_pnm.addAlpha()
            region_pnm.copySubImage(pnm, 0, 0, x, y, w, h)
            print(f"Region: {region_pnm.getXSize()}x{region_pnm.getYSize()}, channels={region_pnm.getNumChannels()}, alpha={region_pnm.hasAlpha()}")

            region_tex = Texture()
            region_tex.load(region_pnm)
            region_tex.setMagfilter(Texture.FT_linear)
            region_tex.setMinfilter(Texture.FT_linear)
            region_tex.setWrapU(Texture.WM_clamp)
            region_tex.setWrapV(Texture.WM_clamp)
            print(f"Texture format: {region_tex.getFormat()}")
            return region_tex
        except Exception as e:
            print(f"Extract error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _auto_screenshot(self, task):
        filename = "button_test.png"
        self.screenshot(namePrefix="button_test_", defaultFilename=False)
        print(f"Screenshot saved")
        self.taskMgr.doMethodLater(0.5, lambda t: self.userExit(), "exit")
        return Task.done


if __name__ == "__main__":
    app = ButtonTest()
    app.run()
