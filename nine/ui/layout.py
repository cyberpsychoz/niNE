"""
GUI Layout Helper Library.

Предоставляет CSS-подобную систему для создания интерфейсов:
- Layout managers (vstack, hstack, grid)
- Анимации и переходы
- Стилизация компонентов
- Responsive позиционирование

Использование:
    from nine.ui.layout import VStack, HStack, Grid, UIAnimator, Padding, Spacing

    # Вертикальный стек
    vstack = VStack(parent=frame, spacing=0.05, padding=Padding(0.02))
    vstack.add(label1)
    vstack.add(label2)
    vstack.add(button)

    # Горизонтальный стек
    hstack = HStack(parent=frame, spacing=0.03, align="center")
    hstack.add(icon)
    hstack.add(text)

    # Сетка
    grid = Grid(parent=frame, cols=3, rows=2, spacing=0.02)
    grid.add(item1, row=0, col=0)
    grid.add(item2, row=0, col=1)

    # Анимации
    UIAnimator.fade_in(element, duration=0.3)
    UIAnimator.slide_in(element, from_x=-0.5, duration=0.4)
"""

from typing import List, Optional, Tuple, Union, Callable
from dataclasses import dataclass
from enum import Enum

from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DGG
from direct.interval.IntervalGlobal import (
    LerpPosInterval, LerpColorScaleInterval, LerpScaleInterval,
    Sequence, Parallel, Func, Wait
)
from panda3d.core import NodePath


class Align(Enum):
    """Выравнивание элементов."""
    START = "start"      # Слева / сверху
    CENTER = "center"    # По центру
    END = "end"          # Справа / снизу
    STRETCH = "stretch"  # Растянуть


@dataclass
class Padding:
    """Отступы от краёв контейнера."""
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0
    left: float = 0.0

    @classmethod
    def all(cls, value: float) -> "Padding":
        """Одинаковые отступы со всех сторон."""
        return cls(value, value, value, value)

    @classmethod
    def symmetric(cls, vertical: float = 0.0, horizontal: float = 0.0) -> "Padding":
        """Симметричные отступы."""
        return cls(vertical, horizontal, vertical, horizontal)


@dataclass
class Spacing:
    """Расстояние между элементами."""
    x: float = 0.0
    y: float = 0.0

    @classmethod
    def uniform(cls, value: float) -> "Spacing":
        """Одинаковое расстояние по обеим осям."""
        return cls(value, value)


class LayoutContainer:
    """Базовый класс для layout контейнеров."""

    def __init__(
        self,
        parent: Optional[NodePath] = None,
        pos: Tuple[float, float, float] = (0, 0, 0),
        size: Optional[Tuple[float, float]] = None,
        padding: Optional[Padding] = None,
        frame_color: Tuple[float, float, float, float] = (0, 0, 0, 0),
    ):
        self.parent = parent
        self.padding = padding or Padding()
        self.elements: List[NodePath] = []

        # Создаём контейнерный фрейм
        frame_size = None
        if size:
            frame_size = (-size[0]/2, size[0]/2, -size[1]/2, size[1]/2)

        self.frame = DirectFrame(
            parent=parent,
            pos=pos,
            frameSize=frame_size,
            frameColor=frame_color,
        )

    def add(self, element: NodePath, **kwargs):
        """Добавляет элемент в контейнер."""
        element.reparentTo(self.frame)
        self.elements.append(element)
        self._update_layout()

    def remove(self, element: NodePath):
        """Удаляет элемент из контейнера."""
        if element in self.elements:
            self.elements.remove(element)
            element.detachNode()
            self._update_layout()

    def clear(self):
        """Очищает все элементы."""
        for element in self.elements:
            element.destroy() if hasattr(element, 'destroy') else element.removeNode()
        self.elements.clear()

    def _update_layout(self):
        """Обновляет позиции элементов. Переопределяется в подклассах."""
        raise NotImplementedError

    def destroy(self):
        """Уничтожает контейнер."""
        self.clear()
        self.frame.destroy()


class VStack(LayoutContainer):
    """
    Вертикальный стек элементов.

    Пример:
        vstack = VStack(parent=frame, spacing=0.05, align=Align.CENTER)
        vstack.add(title_label)
        vstack.add(description_label)
        vstack.add(button)
    """

    def __init__(
        self,
        parent: Optional[NodePath] = None,
        pos: Tuple[float, float, float] = (0, 0, 0),
        spacing: float = 0.05,
        align: Align = Align.CENTER,
        padding: Optional[Padding] = None,
        **kwargs
    ):
        super().__init__(parent, pos, padding=padding, **kwargs)
        self.spacing = spacing
        self.align = align

    def _update_layout(self):
        """Располагает элементы вертикально сверху вниз."""
        if not self.elements:
            return

        y = -self.padding.top
        for element in self.elements:
            # Получаем размер элемента
            bounds = self._get_element_bounds(element)
            height = bounds[3] - bounds[2] if bounds else 0.05

            # Позиционируем
            x = 0
            if self.align == Align.START:
                x = self.padding.left
            elif self.align == Align.END:
                x = -self.padding.right
            # CENTER и STRETCH остаются на x=0

            element.setPos(x, 0, y - height/2)
            y -= height + self.spacing

    def _get_element_bounds(self, element: NodePath) -> Optional[Tuple]:
        """Получает границы элемента."""
        try:
            if hasattr(element, 'getBounds'):
                return element.getBounds()
            elif hasattr(element, '__getitem__') and 'frameSize' in dir(element):
                fs = element['frameSize']
                if fs:
                    return fs
        except:
            pass
        return None


class HStack(LayoutContainer):
    """
    Горизонтальный стек элементов.

    Пример:
        hstack = HStack(parent=frame, spacing=0.03, align=Align.CENTER)
        hstack.add(icon)
        hstack.add(label)
        hstack.add(value)
    """

    def __init__(
        self,
        parent: Optional[NodePath] = None,
        pos: Tuple[float, float, float] = (0, 0, 0),
        spacing: float = 0.03,
        align: Align = Align.CENTER,
        padding: Optional[Padding] = None,
        **kwargs
    ):
        super().__init__(parent, pos, padding=padding, **kwargs)
        self.spacing = spacing
        self.align = align

    def _update_layout(self):
        """Располагает элементы горизонтально слева направо."""
        if not self.elements:
            return

        # Сначала вычисляем общую ширину
        total_width = 0
        widths = []
        for element in self.elements:
            bounds = self._get_element_bounds(element)
            width = bounds[1] - bounds[0] if bounds else 0.1
            widths.append(width)
            total_width += width

        total_width += self.spacing * (len(self.elements) - 1)

        # Начальная позиция X
        x = -total_width / 2 + self.padding.left

        for i, element in enumerate(self.elements):
            y = 0
            if self.align == Align.START:
                y = -self.padding.top
            elif self.align == Align.END:
                y = self.padding.bottom

            element.setPos(x + widths[i]/2, 0, y)
            x += widths[i] + self.spacing

    def _get_element_bounds(self, element: NodePath) -> Optional[Tuple]:
        """Получает границы элемента."""
        try:
            if hasattr(element, 'getBounds'):
                return element.getBounds()
            elif hasattr(element, '__getitem__'):
                fs = element.get('frameSize') if hasattr(element, 'get') else None
                if fs:
                    return fs
        except:
            pass
        return None


class Grid(LayoutContainer):
    """
    Сетка элементов.

    Пример:
        grid = Grid(parent=frame, cols=3, rows=2, spacing=Spacing.uniform(0.02))
        grid.add(item, row=0, col=0)
        grid.add(item, row=0, col=1)
    """

    def __init__(
        self,
        parent: Optional[NodePath] = None,
        pos: Tuple[float, float, float] = (0, 0, 0),
        cols: int = 3,
        rows: int = 3,
        cell_width: float = 0.15,
        cell_height: float = 0.15,
        spacing: Optional[Spacing] = None,
        padding: Optional[Padding] = None,
        **kwargs
    ):
        super().__init__(parent, pos, padding=padding, **kwargs)
        self.cols = cols
        self.rows = rows
        self.cell_width = cell_width
        self.cell_height = cell_height
        self.spacing = spacing or Spacing()

        # Grid хранит элементы по позициям
        self.grid_elements: dict = {}  # (row, col) -> element

    def add(self, element: NodePath, row: int = 0, col: int = 0, **kwargs):
        """Добавляет элемент в ячейку сетки."""
        if row >= self.rows or col >= self.cols:
            raise ValueError(f"Position ({row}, {col}) out of grid bounds ({self.rows}x{self.cols})")

        element.reparentTo(self.frame)
        self.grid_elements[(row, col)] = element
        self.elements.append(element)
        self._position_element(element, row, col)

    def _position_element(self, element: NodePath, row: int, col: int):
        """Позиционирует элемент в ячейке."""
        # Вычисляем позицию ячейки
        total_width = self.cols * self.cell_width + (self.cols - 1) * self.spacing.x
        total_height = self.rows * self.cell_height + (self.rows - 1) * self.spacing.y

        x = -total_width/2 + col * (self.cell_width + self.spacing.x) + self.cell_width/2
        y = total_height/2 - row * (self.cell_height + self.spacing.y) - self.cell_height/2

        x += self.padding.left - self.padding.right
        y += self.padding.bottom - self.padding.top

        element.setPos(x, 0, y)

    def _update_layout(self):
        """Обновляет все позиции."""
        for (row, col), element in self.grid_elements.items():
            self._position_element(element, row, col)

    def get(self, row: int, col: int) -> Optional[NodePath]:
        """Получает элемент из ячейки."""
        return self.grid_elements.get((row, col))


class UIAnimator:
    """
    Утилиты для анимации UI элементов.

    Использование:
        UIAnimator.fade_in(panel, duration=0.3)
        UIAnimator.slide_in(menu, from_x=-1.0, duration=0.5)
        UIAnimator.pulse(button, scale=1.1, duration=0.2)
    """

    @staticmethod
    def fade_in(
        element: NodePath,
        duration: float = 0.3,
        start_alpha: float = 0.0,
        end_alpha: float = 1.0,
        on_complete: Optional[Callable] = None
    ):
        """Плавное появление элемента."""
        element.setColorScale(1, 1, 1, start_alpha)
        interval = LerpColorScaleInterval(
            element,
            duration,
            (1, 1, 1, end_alpha),
            (1, 1, 1, start_alpha),
        )
        if on_complete:
            seq = Sequence(interval, Func(on_complete))
            seq.start()
        else:
            interval.start()
        return interval

    @staticmethod
    def fade_out(
        element: NodePath,
        duration: float = 0.3,
        on_complete: Optional[Callable] = None
    ):
        """Плавное исчезновение элемента."""
        interval = LerpColorScaleInterval(
            element,
            duration,
            (1, 1, 1, 0),
            element.getColorScale(),
        )
        if on_complete:
            seq = Sequence(interval, Func(on_complete))
            seq.start()
        else:
            interval.start()
        return interval

    @staticmethod
    def slide_in(
        element: NodePath,
        duration: float = 0.4,
        from_x: Optional[float] = None,
        from_y: Optional[float] = None,
        from_z: Optional[float] = None,
        on_complete: Optional[Callable] = None
    ):
        """Выезжание элемента из-за края."""
        target_pos = element.getPos()
        start_pos = list(target_pos)

        if from_x is not None:
            start_pos[0] = from_x
        if from_y is not None:
            start_pos[1] = from_y
        if from_z is not None:
            start_pos[2] = from_z

        element.setPos(*start_pos)
        interval = LerpPosInterval(
            element,
            duration,
            target_pos,
            blendType='easeOut',
        )
        if on_complete:
            seq = Sequence(interval, Func(on_complete))
            seq.start()
        else:
            interval.start()
        return interval

    @staticmethod
    def slide_out(
        element: NodePath,
        duration: float = 0.4,
        to_x: Optional[float] = None,
        to_y: Optional[float] = None,
        to_z: Optional[float] = None,
        on_complete: Optional[Callable] = None
    ):
        """Уезжание элемента за край."""
        start_pos = element.getPos()
        target_pos = list(start_pos)

        if to_x is not None:
            target_pos[0] = to_x
        if to_y is not None:
            target_pos[1] = to_y
        if to_z is not None:
            target_pos[2] = to_z

        interval = LerpPosInterval(
            element,
            duration,
            tuple(target_pos),
            blendType='easeIn',
        )
        if on_complete:
            seq = Sequence(interval, Func(on_complete))
            seq.start()
        else:
            interval.start()
        return interval

    @staticmethod
    def scale_pop(
        element: NodePath,
        duration: float = 0.2,
        target_scale: float = 1.1,
        on_complete: Optional[Callable] = None
    ):
        """Эффект 'выскакивания' с увеличением и возвратом."""
        original_scale = element.getScale()
        seq = Sequence(
            LerpScaleInterval(element, duration/2, target_scale, blendType='easeOut'),
            LerpScaleInterval(element, duration/2, original_scale, blendType='easeIn'),
        )
        if on_complete:
            seq.append(Func(on_complete))
        seq.start()
        return seq

    @staticmethod
    def pulse(
        element: NodePath,
        duration: float = 0.5,
        min_scale: float = 0.95,
        max_scale: float = 1.05,
        loops: int = -1
    ):
        """Пульсирующая анимация (бесконечная по умолчанию)."""
        seq = Sequence(
            LerpScaleInterval(element, duration/2, max_scale, blendType='easeInOut'),
            LerpScaleInterval(element, duration/2, min_scale, blendType='easeInOut'),
        )
        seq.loop()
        return seq

    @staticmethod
    def shake(
        element: NodePath,
        duration: float = 0.3,
        intensity: float = 0.02,
        on_complete: Optional[Callable] = None
    ):
        """Эффект тряски (для ошибок)."""
        original_pos = element.getPos()
        x, y, z = original_pos

        seq = Sequence(
            LerpPosInterval(element, duration/6, (x + intensity, y, z)),
            LerpPosInterval(element, duration/6, (x - intensity, y, z)),
            LerpPosInterval(element, duration/6, (x + intensity/2, y, z)),
            LerpPosInterval(element, duration/6, (x - intensity/2, y, z)),
            LerpPosInterval(element, duration/6, original_pos),
        )
        if on_complete:
            seq.append(Func(on_complete))
        seq.start()
        return seq

    @staticmethod
    def sequence(*animations, on_complete: Optional[Callable] = None):
        """Запускает анимации последовательно."""
        seq = Sequence(*animations)
        if on_complete:
            seq.append(Func(on_complete))
        seq.start()
        return seq

    @staticmethod
    def parallel(*animations, on_complete: Optional[Callable] = None):
        """Запускает анимации параллельно."""
        par = Parallel(*animations)
        if on_complete:
            seq = Sequence(par, Func(on_complete))
            seq.start()
            return seq
        par.start()
        return par


class StyleSheet:
    """
    CSS-подобные стили для UI элементов.

    Использование:
        styles = StyleSheet()
        styles.define("button", {
            "frameColor": (0.2, 0.3, 0.4, 1),
            "text_fg": (1, 1, 1, 1),
            "text_scale": 0.04,
        })
        styles.define("button:hover", {
            "frameColor": (0.3, 0.4, 0.5, 1),
        })

        button = styles.create_button("button", text="Click me")
    """

    def __init__(self):
        self.styles: dict = {}

    def define(self, name: str, properties: dict):
        """Определяет стиль."""
        self.styles[name] = properties

    def get(self, name: str) -> dict:
        """Получает стиль по имени."""
        return self.styles.get(name, {})

    def apply(self, element, style_name: str):
        """Применяет стиль к элементу."""
        style = self.get(style_name)
        for key, value in style.items():
            if hasattr(element, '__setitem__'):
                try:
                    element[key] = value
                except:
                    pass

    def merge(self, *style_names: str) -> dict:
        """Объединяет несколько стилей."""
        result = {}
        for name in style_names:
            result.update(self.get(name))
        return result

    def create_button(self, style_name: str, **kwargs) -> DirectButton:
        """Создаёт кнопку с заданным стилем."""
        style = self.get(style_name)
        merged = {**style, **kwargs}
        return DirectButton(**merged)

    def create_label(self, style_name: str, **kwargs) -> DirectLabel:
        """Создаёт метку с заданным стилем."""
        style = self.get(style_name)
        merged = {**style, **kwargs}
        return DirectLabel(**merged)

    def create_frame(self, style_name: str, **kwargs) -> DirectFrame:
        """Создаёт фрейм с заданным стилем."""
        style = self.get(style_name)
        merged = {**style, **kwargs}
        return DirectFrame(**merged)


# Предустановленные стили для D&D тематики
DEFAULT_STYLES = StyleSheet()

# Кнопки
DEFAULT_STYLES.define("btn-primary", {
    "frameColor": (0.2, 0.5, 0.3, 1),
    "text_fg": (1, 1, 1, 1),
    "text_scale": 0.04,
    "frameSize": (-0.15, 0.15, -0.04, 0.045),
})

DEFAULT_STYLES.define("btn-secondary", {
    "frameColor": (0.3, 0.3, 0.4, 1),
    "text_fg": (0.9, 0.9, 0.9, 1),
    "text_scale": 0.035,
    "frameSize": (-0.12, 0.12, -0.035, 0.04),
})

DEFAULT_STYLES.define("btn-danger", {
    "frameColor": (0.5, 0.2, 0.2, 1),
    "text_fg": (1, 1, 1, 1),
    "text_scale": 0.04,
    "frameSize": (-0.15, 0.15, -0.04, 0.045),
})

# Панели
DEFAULT_STYLES.define("panel", {
    "frameColor": (0.1, 0.1, 0.15, 0.95),
})

DEFAULT_STYLES.define("panel-dark", {
    "frameColor": (0.05, 0.05, 0.08, 0.98),
})

DEFAULT_STYLES.define("panel-transparent", {
    "frameColor": (0, 0, 0, 0.5),
})

# Тексты
DEFAULT_STYLES.define("title", {
    "text_fg": (0.9, 0.8, 0.5, 1),
    "text_scale": 0.06,
    "frameColor": (0, 0, 0, 0),
})

DEFAULT_STYLES.define("subtitle", {
    "text_fg": (0.7, 0.7, 0.8, 1),
    "text_scale": 0.04,
    "frameColor": (0, 0, 0, 0),
})

DEFAULT_STYLES.define("text", {
    "text_fg": (0.8, 0.8, 0.8, 1),
    "text_scale": 0.03,
    "frameColor": (0, 0, 0, 0),
})

DEFAULT_STYLES.define("text-muted", {
    "text_fg": (0.5, 0.5, 0.5, 1),
    "text_scale": 0.025,
    "frameColor": (0, 0, 0, 0),
})


def responsive_pos(
    base_x: float,
    base_y: float,
    anchor_x: str = "center",
    anchor_y: str = "center"
) -> Tuple[float, float, float]:
    """
    Вычисляет позицию с учётом привязки к краям экрана.

    anchor_x: "left", "center", "right"
    anchor_y: "top", "center", "bottom"

    Пример:
        pos = responsive_pos(-0.1, 0.9, anchor_x="right", anchor_y="top")
    """
    # В Panda3D aspect2d координаты от -1 до 1 по высоте
    # и от -aspect до aspect по ширине

    try:
        from direct.showbase.ShowBase import ShowBase
        aspect = base.getAspectRatio() if base else 1.33
    except:
        aspect = 1.33

    x = base_x
    y = base_y

    if anchor_x == "left":
        x = -aspect + base_x
    elif anchor_x == "right":
        x = aspect + base_x

    if anchor_y == "top":
        y = 1.0 + base_y if base_y < 0 else 1.0 - base_y
    elif anchor_y == "bottom":
        y = -1.0 + base_y if base_y > 0 else -1.0 - base_y

    return (x, 0, y)
