# nine/ui/main_menu.py
"""
Главное меню в стиле Source Engine.
Текстовые кнопки слева внизу, анимированный/статичный фон.
Поддержка: PNG, JPG, JPEG, GIF (анимированные).
"""

import os
import random

from direct.gui.DirectGui import DirectButton, DirectLabel, DGG, OnscreenImage
from direct.showbase.DirectObject import DirectObject
from direct.task import Task
from panda3d.core import (
    TransparencyAttrib, Texture, PNMImage,
    CardMaker, NodePath
)

from .base_component import BaseUIComponent
from .theme import NineTheme

# Опциональный импорт PIL для GIF
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# Глобальный кэш для фоновых изображений
# Ключ: путь к файлу, Значение: данные текстуры
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
                    frame = gif.convert('RGBA')

                    # Создаём PNMImage из PIL Image
                    width, height = frame.size
                    pnm = PNMImage(width, height, 4)

                    pixels = frame.load()
                    for y in range(height):
                        for x in range(width):
                            r, g, b, a = pixels[x, y]
                            pnm.setXelA(x, y, r/255.0, g/255.0, b/255.0, a/255.0)

                    # Создаём текстуру из PNMImage
                    tex = Texture(f"gif_frame_{frame_index}")
                    tex.load(pnm)
                    tex.setMagfilter(Texture.FT_linear)
                    tex.setMinfilter(Texture.FT_linear)
                    self.frames.append(tex)

                    # Длительность кадра (в секундах)
                    duration = gif.info.get('duration', 100) / 1000.0
                    if duration <= 0:
                        duration = 0.1
                    self.frame_durations.append(duration)

                    frame_index += 1
                except EOFError:
                    break

            gif.close()

            # Сохраняем в кэш
            if self.frames:
                cache_gif(self.gif_path, self.frames, self.frame_durations)

        except Exception as e:
            print(f"[MainMenu] Ошибка загрузки GIF: {e}")

    def _create_card(self):
        """Создаёт карточку для отображения текстуры."""
        if not self.frames:
            return

        cm = CardMaker("gif_background")
        cm.setFrameFullscreenQuad()

        self.node = NodePath(cm.generate())
        self.node.reparentTo(self.base.render2d)
        self.node.setTransparency(TransparencyAttrib.M_alpha)

        # Устанавливаем первый кадр
        self.texture = self.frames[0]
        self.node.setTexture(self.texture)

        # Запускаем анимацию если больше 1 кадра
        if len(self.frames) > 1:
            self._task = self.base.taskMgr.add(self._animate_task, "gif_animate")

    def _animate_task(self, task):
        """Задача анимации GIF."""
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
        # НЕ очищаем frames - они кэшируются для повторного использования
        self.frames = []
        self.frame_durations = []


class MainMenu(BaseUIComponent, DirectObject):
    """Главное меню игры в стиле Source Engine."""

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

        self._scan_backgrounds()
        self._create_window()

    def _scan_backgrounds(self):
        """Сканирует папку backgrounds на наличие файлов."""
        all_formats = self.STATIC_FORMATS + self.ANIMATED_FORMATS

        if os.path.exists(self.BACKGROUNDS_PATH):
            for file in os.listdir(self.BACKGROUNDS_PATH):
                if file.lower().endswith(all_formats):
                    # Используем / для Panda3D (работает на всех ОС)
                    self._bg_files.append(f"{self.BACKGROUNDS_PATH}/{file}")

        # Fallback
        if not self._bg_files:
            if os.path.exists(self.FALLBACK_BG):
                self._bg_files.append(self.FALLBACK_BG)

        # Перемешиваем для случайного выбора
        if self._bg_files:
            random.shuffle(self._bg_files)

    def _create_background(self):
        """Создаёт фоновое изображение (статичное или анимированное) с кэшированием."""
        if not self._bg_files:
            return

        bg_path = self._bg_files[0]
        is_gif = bg_path.lower().endswith('.gif')

        if is_gif and HAS_PIL:
            # Анимированный GIF
            self._animated_bg = AnimatedBackground(self.base, bg_path)
            self._is_animated = True

            if self._animated_bg.get_node():
                self._update_bg_scale(self._animated_bg.get_node(),
                                      self._animated_bg.get_texture())
        else:
            # Статичное изображение с кэшированием
            cached_tex = get_cached_static(bg_path)

            if cached_tex:
                # Используем кэшированную текстуру
                cm = CardMaker("static_background")
                cm.setFrameFullscreenQuad()
                bg = NodePath(cm.generate())
                bg.reparentTo(self.base.render2d)
                bg.setTexture(cached_tex)
                bg.setTransparency(TransparencyAttrib.M_alpha)
                self._add_element('background', bg)
            else:
                # Загружаем и кэшируем
                bg = self._add_element('background', OnscreenImage(
                    parent=self.base.render2d,
                    image=bg_path,
                    pos=(0, 0, 0),
                    scale=(1, 1, 1),
                ))
                bg.setTransparency(TransparencyAttrib.M_alpha)
                # Кэшируем текстуру
                tex = bg.getTexture()
                if tex:
                    cache_static(bg_path, tex)

            self._update_bg_scale(self._elements['background'])
            self._is_animated = False

    def _create_window(self):
        """Создает элементы главного меню."""
        # Фоновое изображение
        self._create_background()
        self.accept('window-event', self._on_window_event)

        # Затемнение снизу для читаемости текста (градиент)
        gradient_path = "nine/assets/materials/menu_gradient.png"
        if os.path.exists(gradient_path):
            gradient = self._add_element('gradient', OnscreenImage(
                parent=self.base.render2d,
                image=gradient_path,
                pos=(0, 0, -0.5),
                scale=(2, 1, 0.5),
                color=(0, 0, 0, 0.7),
            ))
            gradient.setTransparency(TransparencyAttrib.M_alpha)

        # Логотип/название игры - слева вверху
        self._add_element('title', DirectLabel(
            parent=self.base.a2dTopLeft,
            text="D&D gamemode",
            scale=0.12,
            pos=(0.15, 0, -0.12),
            text_fg=(1, 1, 1, 0.95),
            text_shadow=(0, 0, 0, 0.8),
            text_shadowOffset=(0.03, 0.03),
            text_align=0,  # Left
            frameColor=(0, 0, 0, 0),
        ))

        # Контейнер для кнопок - слева внизу
        menu_x = 0.08
        menu_y = 0.40
        item_spacing = 0.10

        buttons_data = [
            ("ИГРАТЬ", self.ui_manager.callbacks.get("connect")),
            ("НАСТРОЙКИ", self.ui_manager.callbacks.get("settings")),
            ("ВЫХОД", self.ui_manager.callbacks.get("exit")),
        ]

        for i, (text, command) in enumerate(buttons_data):
            y_pos = menu_y - i * item_spacing

            # Используем новый метод создания кнопок с звуками
            self._create_menu_button(
                name=f'menu_item_{i}',
                text=text,
                command=command,
                parent=self.base.a2dBottomLeft,
                pos=(menu_x, 0, y_pos),
            )

        # Версия - слева внизу
        self._add_element('version', DirectLabel(
            parent=self.base.a2dBottomLeft,
            text="v0.1.0-alpha",
            scale=NineTheme.SMALL_SCALE,
            pos=(0.08, 0, 0.05),
            text_fg=NineTheme.TEXT_HINT,
            text_align=0,
            frameColor=(0, 0, 0, 0),
        ))

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

        win_w, win_h = win_props.getXSize(), win_props.getYSize()
        if win_w == 0 or win_h == 0:
            return

        try:
            # Получаем текстуру
            if texture is None:
                texture = bg_node.get_texture()

            if texture:
                img_w = texture.get_x_size()
                img_h = texture.get_y_size()

                if img_w > 0 and img_h > 0:
                    img_aspect = img_w / img_h
                    win_aspect = win_w / win_h

                    # Cover - заполняем весь экран, обрезая лишнее
                    if win_aspect > img_aspect:
                        scale_x = win_aspect / img_aspect
                        scale_z = 1
                    else:
                        scale_x = 1
                        scale_z = img_aspect / win_aspect

                    bg_node.set_scale(scale_x, 1, scale_z)
        except Exception:
            pass

    def show(self):
        """Показывает главное меню."""
        # Показываем все элементы
        for element in self._elements.values():
            if hasattr(element, 'show'):
                element.show()

        # Показываем и возобновляем анимированный фон
        if self._animated_bg:
            node = self._animated_bg.get_node()
            if node:
                node.show()
            # Возобновляем анимацию если была остановлена
            if self._animated_bg.frames and len(self._animated_bg.frames) > 1:
                if not self._animated_bg._task:
                    self._animated_bg._task = self.base.taskMgr.add(
                        self._animated_bg._animate_task, "gif_animate"
                    )

    def hide(self):
        """Скрывает главное меню (без уничтожения)."""
        # Скрываем все элементы
        for element in self._elements.values():
            if hasattr(element, 'hide'):
                element.hide()

        # Скрываем и останавливаем анимированный фон (экономия CPU)
        if self._animated_bg:
            node = self._animated_bg.get_node()
            if node:
                node.hide()
            # Останавливаем задачу анимации
            if self._animated_bg._task:
                self.base.taskMgr.remove(self._animated_bg._task)
                self._animated_bg._task = None

    def next_background(self):
        """Переключает на следующий фон."""
        if len(self._bg_files) <= 1:
            return

        # Уничтожаем текущий фон
        if self._animated_bg:
            self._animated_bg.destroy()
            self._animated_bg = None
        if 'background' in self._elements:
            self._elements['background'].destroy()
            del self._elements['background']

        # Переключаемся на следующий
        self._bg_files.append(self._bg_files.pop(0))
        self._create_background()

    def destroy(self):
        """Уничтожает меню."""
        self.ignoreAll()
        if self._animated_bg:
            self._animated_bg.destroy()
            self._animated_bg = None
        super().destroy()
