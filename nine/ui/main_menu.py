# nine/ui/main_menu.py
"""
Главное меню в стиле Baldur's Gate.
Центрированные кнопки с текстурами, случайные фоны.
"""

import os
import random

from direct.gui.DirectGui import DirectButton, DirectLabel, DirectFrame, DGG, OnscreenImage
from direct.showbase.DirectObject import DirectObject
from direct.task import Task
from panda3d.core import (
    TransparencyAttrib, Texture, PNMImage,
    CardMaker, NodePath, TextNode, Vec4
)

from .base_component import BaseUIComponent
from .theme import NineTheme
from .bg1_button import BG1Button
from .ui_config import ui

# Опциональный импорт PIL для GIF
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# Глобальный кэш для фоновых изображений
_background_cache = {
    'gif': {},      # {path: {'frames': [Texture, ...], 'durations': [float, ...]}}
    'static': {},   # {path: Texture}
}


def get_cached_gif(path):
    """Возвращает кэшированные данные GIF или None."""
    return _background_cache['gif'].get(path)


def cache_gif(path, frames, durations):
    """Сохраняет GIF в кэш."""
    _background_cache['gif'][path] = {
        'frames': frames,
        'durations': durations
    }


def get_cached_static(path):
    """Возвращает кэшированную статическую текстуру или None."""
    return _background_cache['static'].get(path)


def cache_static(path, texture):
    """Сохраняет статическую текстуру в кэш."""
    _background_cache['static'][path] = texture


class AnimatedBackground:
    """Класс для анимированного GIF-фона."""

    def __init__(self, base, gif_path):
        self.base = base
        self.gif_path = gif_path
        self.frames = []
        self.frame_durations = []
        self.current_frame = 0
        self.texture = None
        self.card = None
        self.node = None
        self._task = None
        self._time_accumulator = 0

        self._load_gif()
        self._create_card()

    def _load_gif(self):
        """Загружает кадры GIF через PIL (с кэшированием)."""
        if not HAS_PIL:
            return

        # Проверяем кэш
        cached = get_cached_gif(self.gif_path)
        if cached:
            self.frames = cached['frames']
            self.frame_durations = cached['durations']
            return

        try:
            gif = Image.open(self.gif_path)

            # Извлекаем все кадры
            frame_index = 0
            while True:
                try:
                    gif.seek(frame_index)

                    # Конвертируем в RGBA
                    frame_rgba = gif.convert('RGBA')
                    width, height = frame_rgba.size

                    # Создаём Panda3D текстуру
                    tex = Texture()
                    tex.setup2dTexture(width, height, Texture.T_unsigned_byte, Texture.F_rgba)

                    # Копируем данные
                    img_data = frame_rgba.tobytes()
                    tex.setRamImage(img_data)

                    self.frames.append(tex)

                    # Длительность кадра (по умолчанию 0.1 сек)
                    duration = gif.info.get('duration', 100) / 1000.0
                    self.frame_durations.append(duration)

                    frame_index += 1
                except EOFError:
                    break

            # Кэшируем
            if self.frames:
                cache_gif(self.gif_path, self.frames, self.frame_durations)

        except Exception as e:
            print(f"Failed to load GIF {self.gif_path}: {e}")

    def _create_card(self):
        """Создаёт карточку для отображения текстуры."""
        if not self.frames:
            return

        cm = CardMaker('menu_bg_card')
        cm.setFrame(-1, 1, -1, 1)
        self.node = NodePath(cm.generate())
        self.node.reparentTo(self.base.render2d)
        self.node.setTransparency(TransparencyAttrib.M_alpha)

        # Устанавливаем первый кадр
        self.texture = self.frames[0]
        self.node.setTexture(self.texture)

        # Запускаем анимацию если больше 1 кадра
        if len(self.frames) > 1:
            from panda3d.core import ClockObject
            global globalClock
            globalClock = ClockObject.getGlobalClock()
            self._task = self.base.taskMgr.add(self._animate_task, "gif_animate")

    def _animate_task(self, task):
        """Задача анимации GIF."""
        from panda3d.core import ClockObject
        globalClock = ClockObject.getGlobalClock()

        dt = globalClock.getDt()
        self._time_accumulator += dt

        # Проверяем нужно ли переключить кадр
        current_duration = self.frame_durations[self.current_frame]

        if self._time_accumulator >= current_duration:
            self._time_accumulator -= current_duration
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.node.setTexture(self.frames[self.current_frame])

        return Task.cont

    def get_node(self):
        """Возвращает NodePath для масштабирования."""
        return self.node

    def get_texture(self):
        """Возвращает текущую текстуру."""
        if self.frames:
            return self.frames[self.current_frame]
        return None

    def destroy(self):
        """Уничтожает анимированный фон (текстуры остаются в кэше)."""
        if self._task:
            self.base.taskMgr.remove(self._task)
            self._task = None
        if self.node:
            self.node.removeNode()
            self.node = None
        self.frames = []
        self.frame_durations = []


class MainMenu(BaseUIComponent, DirectObject):
    """Главное меню игры в стиле Baldur's Gate."""

    # Папка с фоновыми изображениями
    BACKGROUNDS_PATH = "nine/assets/materials/textures/backgrounds"
    FALLBACK_BG = "nine/assets/materials/main_menu.png"

    # Поддерживаемые форматы
    STATIC_FORMATS = ('.png', '.jpg', '.jpeg', '.bmp', '.tga')
    ANIMATED_FORMATS = ('.gif',)

    def __init__(self, ui_manager):
        BaseUIComponent.__init__(self, ui_manager)
        DirectObject.__init__(self)

        self._bg_files = []
        self._current_bg = None
        self._animated_bg = None
        self._is_animated = False

        # Инициализируем BG1Button с loader
        BG1Button.init(self.base.loader)

        self._scan_backgrounds()
        self._create_window()

    def _scan_backgrounds(self):
        """Сканирует папку backgrounds на наличие файлов."""
        all_formats = self.STATIC_FORMATS + self.ANIMATED_FORMATS

        if os.path.exists(self.BACKGROUNDS_PATH):
            for file in os.listdir(self.BACKGROUNDS_PATH):
                if file.lower().endswith(all_formats):
                    self._bg_files.append(f"{self.BACKGROUNDS_PATH}/{file}")

        # Fallback
        if not self._bg_files:
            if os.path.exists(self.FALLBACK_BG):
                self._bg_files.append(self.FALLBACK_BG)

        # Перемешиваем для случайного выбора
        if self._bg_files:
            random.shuffle(self._bg_files)

    def _create_background(self):
        """Создаёт фоновое изображение (статичное или анимированное)."""
        if not self._bg_files:
            return

        bg_path = self._bg_files[0]
        is_gif = bg_path.lower().endswith('.gif')

        if is_gif and HAS_PIL:
            # Анимированный GIF
            self._animated_bg = AnimatedBackground(self.base, bg_path)
            node = self._animated_bg.get_node()
            tex = self._animated_bg.get_texture()
            if node and tex:
                self._update_bg_scale(node, tex)
            self._is_animated = True
        else:
            # Статичное изображение
            try:
                bg = self._add_element('background', OnscreenImage(
                    parent=self.base.render2d,
                    image=bg_path,
                    pos=(0, 0, 0),
                    scale=(1, 1, 1),
                ))
                if bg and not bg.isEmpty():
                    bg.setTransparency(TransparencyAttrib.M_alpha)
                    self._update_bg_scale(bg)
                else:
                    # Fallback - создаём цветной фон
                    del self._elements['background']
                    self._create_fallback_background()
            except (AssertionError, Exception) as e:
                print(f"[MainMenu] Failed to load background: {e}")
                self._create_fallback_background()
            self._is_animated = False

    def _create_fallback_background(self):
        """Создаёт простой цветной фон если изображение не загрузилось."""
        bg = self._add_element('background', DirectFrame(
            parent=self.base.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=ui.colors.bg_dark,
        ))
        bg.setTransparency(TransparencyAttrib.M_alpha)

    def _create_window(self):
        """Создает элементы главного меню в стиле BG1."""
        # Фоновое изображение
        self._create_background()
        self.accept('window-event', self._on_window_event)

        # Затемнение для контраста
        gradient_path = "nine/assets/materials/menu_gradient.png"
        if os.path.exists(gradient_path):
            gradient = self._add_element('gradient', OnscreenImage(
                parent=self.base.render2d,
                image=gradient_path,
                pos=(0, 0, 0),
                scale=(2, 1, 1),
                color=(0, 0, 0, 0.5),
            ))
            gradient.setTransparency(TransparencyAttrib.M_alpha)

        # Заголовок - центр, вверху
        title_y = 0.55 + ui.font.title
        self._add_element('title', DirectLabel(
            parent=self.base.aspect2d,
            text="DUNGEONS & DRAGONS",
            scale=ui.font.title,
            pos=(0, 0, title_y),
            text_fg=ui.colors.gold,
            text_shadow=(0, 0, 0, 1),
            text_shadowOffset=(0.003, 0.003),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        ))

        # Подзаголовок
        subtitle_y = title_y - ui.font.title - ui.spacing.sm
        self._add_element('subtitle', DirectLabel(
            parent=self.base.aspect2d,
            text="niNE Game Mode",
            scale=ui.font.heading,
            pos=(0, 0, subtitle_y),
            text_fg=ui.colors.text_secondary,
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.002, 0.002),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        ))

        # Кнопки - центр экрана
        buttons_data = [
            ("ИГРАТЬ", "connect"),
            ("НАСТРОЙКИ", "settings"),
            ("ВЫХОД", "exit"),
        ]

        # Первая кнопка ниже подзаголовка
        button_y_start = subtitle_y - ui.spacing.xl - ui.button.scale * ui.button.height
        button_spacing = ui.button.spacing

        for i, (text, callback_name) in enumerate(buttons_data):
            y_pos = button_y_start - i * button_spacing
            callback = self.ui_manager.callbacks.get(callback_name)
            self._create_bg1_button(
                name=f'menu_btn_{i}',
                text=text,
                command=callback,
                pos=(0, 0, y_pos),
            )

        # Версия - справа внизу
        self._add_element('version', DirectLabel(
            parent=self.base.a2dBottomRight,
            text="v0.1.0-alpha (dnd-gamemode)",
            scale=ui.font.small,
            pos=(-ui.spacing.lg, 0, ui.spacing.sm),
            text_fg=ui.colors.text_hint,
            text_align=TextNode.ARight,
            frameColor=(0, 0, 0, 0),
        ))

        # Запускаем музыку главного меню
        self._start_menu_music()

    def _create_bg1_button(self, name: str, text: str, command=None, pos=(0, 0, 0)):
        """Создаёт кнопку в стиле BG1 используя базовый класс BG1Button."""
        # Обёртка команды с звуком
        def command_with_sound():
            try:
                if hasattr(self, '_play_click_sound'):
                    self._play_click_sound()
            except:
                pass
            if command and callable(command):
                command()

        # Создаём кнопку через BG1Button
        btn = BG1Button.create(
            parent=self.base.aspect2d,
            text=text,
            command=command_with_sound,
            pos=pos,
            font=self.ui_manager.font,
            sound_callback=lambda: self._play_hover_sound() if hasattr(self, '_play_hover_sound') else None,
        )

        self._add_element(name, btn)
        return btn

    def _on_window_event(self, window):
        """Пересчитывает фон при изменении размера окна."""
        if self._is_animated and self._animated_bg:
            node = self._animated_bg.get_node()
            tex = self._animated_bg.get_texture()
            if node and tex:
                self._update_bg_scale(node, tex)
        elif 'background' in self._elements:
            self._update_bg_scale(self._elements['background'])

    def _update_bg_scale(self, bg_node, texture=None):
        """Масштабирует фон для заполнения окна (cover)."""
        if not bg_node or not self.base.win:
            return

        win_props = self.base.win.getProperties()
        if not win_props.hasSize():
            return

        win_width = win_props.getXSize()
        win_height = win_props.getYSize()

        if win_width == 0 or win_height == 0:
            return

        # Получаем текстуру
        if texture is None:
            texture = bg_node.getTexture()

        if not texture:
            return

        img_width = texture.getXSize()
        img_height = texture.getYSize()

        if img_width == 0 or img_height == 0:
            return

        # Соотношения сторон
        win_aspect = win_width / win_height
        img_aspect = img_width / img_height

        # Cover: масштабируем чтобы полностью заполнить окно
        if win_aspect > img_aspect:
            scale_x = win_aspect / img_aspect
            scale_y = 1.0
        else:
            scale_x = 1.0
            scale_y = img_aspect / win_aspect

        bg_node.setScale(scale_x, 1, scale_y)

    def _start_menu_music(self):
        """Запускает музыку главного меню."""
        try:
            if hasattr(self.base, 'audio_manager') and self.base.audio_manager:
                self.base.audio_manager.play_bgm("menu", crossfade=1.0)
            else:
                from nine.core.audio_manager import AudioManager
                self.base.audio_manager = AudioManager(self.base)
                self.base.audio_manager.play_bgm("menu", crossfade=0)
        except Exception as e:
            print(f"[MainMenu] Failed to start menu music: {e}")

    def _stop_menu_music(self, fadeout: float = 1.0):
        """Останавливает музыку главного меню."""
        try:
            if hasattr(self.base, 'audio_manager') and self.base.audio_manager:
                self.base.audio_manager.stop_bgm(fadeout=fadeout)
        except Exception:
            pass

    def show(self):
        """Показывает главное меню."""
        for element in self._elements.values():
            if hasattr(element, 'show'):
                element.show()

        if self._animated_bg:
            node = self._animated_bg.get_node()
            if node:
                node.show()
            if self._animated_bg.frames and len(self._animated_bg.frames) > 1:
                if not self._animated_bg._task:
                    self._animated_bg._task = self.base.taskMgr.add(
                        self._animated_bg._animate_task, "gif_animate"
                    )

        self._start_menu_music()

    def hide(self):
        """Скрывает главное меню."""
        for element in self._elements.values():
            if hasattr(element, 'hide'):
                element.hide()

        if self._animated_bg:
            node = self._animated_bg.get_node()
            if node:
                node.hide()
            if self._animated_bg._task:
                self.base.taskMgr.remove(self._animated_bg._task)
                self._animated_bg._task = None

        self._stop_menu_music(fadeout=0.5)

    def next_background(self):
        """Переключает на следующий фон."""
        if len(self._bg_files) <= 1:
            return

        if self._animated_bg:
            self._animated_bg.destroy()
            self._animated_bg = None
        if 'background' in self._elements:
            self._elements['background'].destroy()
            del self._elements['background']

        self._bg_files.append(self._bg_files.pop(0))
        self._create_background()

    def destroy(self):
        """Уничтожает меню."""
        self.ignoreAll()
        self._stop_menu_music(fadeout=0.3)
        if self._animated_bg:
            self._animated_bg.destroy()
            self._animated_bg = None
        super().destroy()
