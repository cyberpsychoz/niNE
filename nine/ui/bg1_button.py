"""
Кнопка в стиле Baldur's Gate 1.
Используется как базовый класс для всех кнопок в UI.
Также предоставляет текстуры для панелей (правый столбец).
"""

import os
from direct.gui.DirectGui import DirectButton, DirectFrame, DGG
from panda3d.core import TransparencyAttrib, TextNode, Texture, PNMImage

from .ui_config import ui


class BG1Panel:
    """Текстура для панелей/плашек из правого столбца buttons.png."""

    _panel_texture = None

    @classmethod
    def get_texture(cls):
        """Возвращает текстуру панели (загружает при первом вызове)."""
        if cls._panel_texture is not None:
            return cls._panel_texture

        texture_path = "nine/assets/materials/textures/ui/buttons/buttons.png"
        if not os.path.exists(texture_path):
            return None

        try:
            pnm = PNMImage()
            pnm.read(texture_path)

            # Правый столбец: x=128, ширина ~38px, нормальное состояние y=18
            panel_x = 128
            panel_y = 18
            panel_width = 38
            panel_height = 12

            region_pnm = PNMImage(panel_width, panel_height, 4)
            region_pnm.addAlpha()
            region_pnm.copySubImage(pnm, 0, 0, panel_x, panel_y, panel_width, panel_height)

            cls._panel_texture = Texture()
            cls._panel_texture.load(region_pnm)
            cls._panel_texture.setMagfilter(Texture.FT_linear)
            cls._panel_texture.setMinfilter(Texture.FT_linear)
            cls._panel_texture.setWrapU(Texture.WM_clamp)
            cls._panel_texture.setWrapV(Texture.WM_clamp)
            return cls._panel_texture
        except Exception as e:
            print(f"[BG1Panel] Failed to load texture: {e}")
            return None

    @classmethod
    def create(cls, parent, pos=(0, 0, 0), size=(0.3, 0.08)):
        """
        Создаёт панель/плашку в стиле BG1.

        Args:
            parent: Родительский узел
            pos: Позиция (x, y, z)
            size: (ширина, высота)

        Returns:
            DirectFrame
        """
        width, height = size
        tex = cls.get_texture()

        frame = DirectFrame(
            parent=parent,
            frameSize=(-width/2, width/2, -height/2, height/2),
            pos=pos,
            frameTexture=tex if tex else None,
            frameColor=(0.25, 0.18, 0.12, 0.95) if not tex else (1, 1, 1, 1),
        )
        frame.setTransparency(TransparencyAttrib.M_alpha)
        return frame


class BG1Button:
    """
    Фабрика для создания кнопок в стиле BG1.

    Использование:
        btn = BG1Button.create(
            parent=self.aspect2d,
            text="ИГРАТЬ",
            command=self.on_play,
            pos=(0, 0, 0.3),
        )
    """

    # Путь к текстуре кнопок
    TEXTURE_PATH = "nine/assets/materials/textures/ui/buttons/buttons.png"

    # Кэш текстур (загружаем один раз)
    _textures_cache = None
    _loader = None

    @classmethod
    def init(cls, loader):
        """Инициализация - загружает текстуры. Вызвать один раз при старте."""
        cls._loader = loader
        cls._load_textures()

    @classmethod
    def _load_textures(cls):
        """Загружает и нарезает текстуры кнопок."""
        if cls._textures_cache is not None:
            return

        if not os.path.exists(cls.TEXTURE_PATH):
            print(f"[BG1Button] Texture not found: {cls.TEXTURE_PATH}")
            return

        if cls._loader is None:
            print("[BG1Button] Loader not initialized!")
            return

        try:
            # Загружаем текстуру
            main_tex = cls._loader.loadTexture(cls.TEXTURE_PATH)
            if not main_tex:
                return

            tex_width = main_tex.getXSize()
            tex_height = main_tex.getYSize()
            print(f"[BG1Button] Texture loaded: {tex_width}x{tex_height}")

            # Текстура 176x48:
            # - Левый столбец (x=2-64): 62px - основной дизайн кнопки
            # - 3 ряда состояний (12px каждый):
            #   y=2: disabled, y=18: normal, y=34: hover
            # Aspect ratio: 62/12 ≈ 5.17:1

            button_width = 62   # Ширина кнопки
            button_height = 12  # Высота состояния
            column_x = 2        # Начало левого столбца

            # Координаты рядов
            row_disabled_y = 2
            row_normal_y = 18
            row_hover_y = 34

            # Загружаем PNMImage напрямую (чтобы получить реальный размер)
            pnm = PNMImage()
            pnm.read(cls.TEXTURE_PATH)
            actual_width = pnm.getXSize()
            actual_height = pnm.getYSize()
            print(f"[BG1Button] Actual PNM size: {actual_width}x{actual_height}")

            def extract_region(x, y, w, h):
                """Вырезает регион текстуры с сохранением альфа-канала."""
                # Создаём изображение с альфа-каналом
                region_pnm = PNMImage(w, h, 4)
                region_pnm.addAlpha()

                # Копируем регион из исходного изображения
                region_pnm.copySubImage(pnm, 0, 0, x, y, w, h)

                region_tex = Texture()
                region_tex.load(region_pnm)
                region_tex.setMagfilter(Texture.FT_linear)
                region_tex.setMinfilter(Texture.FT_linear)
                region_tex.setWrapU(Texture.WM_clamp)
                region_tex.setWrapV(Texture.WM_clamp)
                return region_tex

            # Вырезаем из СРЕДНЕГО столбца:
            disabled_tex = extract_region(column_x, row_disabled_y, button_width, button_height)
            normal_tex = extract_region(column_x, row_normal_y, button_width, button_height)
            hover_tex = extract_region(column_x, row_hover_y, button_width, button_height)

            # Формат для DirectButton: (ready, press, rollover, disabled)
            # ready=normal, press=hover (нажатие), rollover=hover, disabled=disabled
            cls._textures_cache = (normal_tex, hover_tex, hover_tex, disabled_tex)

            print(f"[BG1Button] Textures extracted: {button_width}x{button_height} each from middle column")

        except Exception as e:
            print(f"[BG1Button] Failed to load textures: {e}")
            cls._textures_cache = None

    @classmethod
    def create(cls, parent, text, command=None, pos=(0, 0, 0),
               scale=None, width=None, height=None, font=None,
               text_fg=(0.9, 0.85, 0.7, 1), sound_callback=None):
        """
        Создаёт кнопку в стиле BG1.

        Args:
            parent: Родительский узел (aspect2d, render2d, etc.)
            text: Текст кнопки
            command: Функция при нажатии
            pos: Позиция (x, y, z)
            scale: Масштаб кнопки (None = из UIConfig)
            width: Ширина в текстовых единицах (None = из UIConfig)
            height: Высота в текстовых единицах (None = из UIConfig)
            font: Шрифт текста (опционально)
            text_fg: Цвет текста
            sound_callback: Функция для воспроизведения звука hover

        Returns:
            DirectButton
        """
        # Используем значения из UIConfig если не указаны
        if scale is None:
            scale = ui.button.scale
        if width is None:
            width = ui.button.width
        if height is None:
            height = ui.button.height

        # Безопасная обёртка команды
        def safe_command():
            if command and callable(command):
                command()

        btn_params = {
            'parent': parent,
            'text': text,
            'text_scale': 1.0,
            'scale': scale,
            'pos': pos,
            'command': safe_command,
            'text_align': TextNode.ACenter,
            'text_pos': (0, ui.button.text_offset_y),  # Центрируем текст вертикально
            'text_fg': text_fg,
            'text_shadow': (0, 0, 0, 0.9),
            'text_shadowOffset': (0.003, 0.003),
            'frameSize': (-width, width, -height, height),
            'rolloverSound': None,
            'clickSound': None,
        }

        if font:
            btn_params['text_font'] = font

        # Применяем текстуры если загружены
        if cls._textures_cache:
            btn_params['frameTexture'] = cls._textures_cache
            btn_params['relief'] = DGG.FLAT
        else:
            # Fallback на цветной фон
            btn_params['frameColor'] = (0.2, 0.16, 0.12, 0.95)
            btn_params['relief'] = DGG.RAISED
            btn_params['borderWidth'] = (0.02, 0.02)

        btn = DirectButton(**btn_params)
        btn.setTransparency(TransparencyAttrib.M_alpha)

        # Hover эффекты
        original_text_fg = text_fg
        bright_text_fg = (1, 0.95, 0.8, 1)

        def on_enter(event):
            if sound_callback:
                try:
                    sound_callback()
                except:
                    pass
            btn['text_fg'] = bright_text_fg
            if not cls._textures_cache:
                btn['frameColor'] = (0.28, 0.22, 0.16, 0.98)

        def on_exit(event):
            btn['text_fg'] = original_text_fg
            if not cls._textures_cache:
                btn['frameColor'] = (0.2, 0.16, 0.12, 0.95)

        btn.bind(DGG.ENTER, on_enter)
        btn.bind(DGG.EXIT, on_exit)

        return btn


class BG1ButtonSmall(BG1Button):
    """Маленькая кнопка в стиле BG1 (для диалогов, подтверждений)."""

    @classmethod
    def create(cls, parent, text, command=None, pos=(0, 0, 0), font=None, sound_callback=None):
        # Uses small button config from UIConfig
        return super().create(
            parent=parent,
            text=text,
            command=command,
            pos=pos,
            scale=ui.button.small_scale,
            width=ui.button.small_width,
            height=ui.button.small_height,
            font=font,
            sound_callback=sound_callback,
        )


class BG1ButtonLarge(BG1Button):
    """Большая кнопка в стиле BG1 (для главного меню)."""

    @classmethod
    def create(cls, parent, text, command=None, pos=(0, 0, 0), font=None, sound_callback=None):
        # Uses large button config from UIConfig
        return super().create(
            parent=parent,
            text=text,
            command=command,
            pos=pos,
            scale=ui.button.large_scale,
            width=ui.button.width,
            height=ui.button.height,
            font=font,
            sound_callback=sound_callback,
        )
