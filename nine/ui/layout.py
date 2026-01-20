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

from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DirectEntry, DGG
from direct.interval.IntervalGlobal import (
    LerpPosInterval, LerpColorScaleInterval, LerpScaleInterval,
    Sequence, Parallel, Func, Wait
)
from panda3d.core import NodePath, TextNode, TransparencyAttrib

from .ui_config import ui
from .bg1_button import BG1Button, BG1ButtonSmall


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


# Предустановленные стили для D&D тематики (используют UIConfig)
DEFAULT_STYLES = StyleSheet()

# Кнопки
DEFAULT_STYLES.define("btn-primary", {
    "frameColor": ui.colors.btn_accent_normal,
    "text_fg": ui.colors.text_primary,
    "text_scale": ui.font.label,
    "frameSize": (-0.15, 0.15, -0.04, 0.045),
})

DEFAULT_STYLES.define("btn-secondary", {
    "frameColor": ui.colors.btn_normal,
    "text_fg": ui.colors.text_primary,
    "text_scale": ui.font.body,
    "frameSize": (-0.12, 0.12, -0.035, 0.04),
})

DEFAULT_STYLES.define("btn-danger", {
    "frameColor": ui.colors.error,
    "text_fg": ui.colors.text_primary,
    "text_scale": ui.font.label,
    "frameSize": (-0.15, 0.15, -0.04, 0.045),
})

# Панели
DEFAULT_STYLES.define("panel", {
    "frameColor": ui.colors.bg_medium,
})

DEFAULT_STYLES.define("panel-dark", {
    "frameColor": ui.colors.bg_dark,
})

DEFAULT_STYLES.define("panel-transparent", {
    "frameColor": ui.colors.bg_overlay,
})

# Тексты
DEFAULT_STYLES.define("title", {
    "text_fg": ui.colors.gold,
    "text_scale": ui.font.title,
    "frameColor": (0, 0, 0, 0),
})

DEFAULT_STYLES.define("subtitle", {
    "text_fg": ui.colors.text_secondary,
    "text_scale": ui.font.subtitle,
    "frameColor": (0, 0, 0, 0),
})

DEFAULT_STYLES.define("text", {
    "text_fg": ui.colors.text_primary,
    "text_scale": ui.font.body,
    "frameColor": (0, 0, 0, 0),
})

DEFAULT_STYLES.define("text-muted", {
    "text_fg": ui.colors.text_hint,
    "text_scale": ui.font.small,
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


# =============================================================================
# Declarative UI Builder
# =============================================================================

class UIBuilder:
    """
    Declarative UI builder for creating layouts.

    Usage:
        builder = UIBuilder(parent=base.aspect2d)

        panel = builder.panel(
            width=ui.panel.settings_width,
            height=ui.panel.settings_height,
            bg=ui.colors.bg_medium
        )

        with panel:
            panel.label("НАСТРОЙКИ", style="title")
            panel.spacer(ui.spacing.md)

            with panel.row(spacing=ui.spacing.sm, justify="center") as tabs:
                tabs.button("Общие", small=True)
                tabs.button("Звук", small=True)

            panel.spacer(ui.spacing.lg)

            with panel.column(spacing=ui.spacing.sm) as content:
                with content.row(justify="space-between"):
                    content.label("Громкость:")
                    content.label("80%")

            panel.spacer(ui.spacing.lg)

            with panel.row(spacing=ui.spacing.md, justify="center"):
                panel.button("Назад", small=True)
                panel.button("Сохранить", small=True)

        panel.build()
    """

    def __init__(self, parent=None):
        self.parent = parent
        self._root = None

    def panel(
        self,
        width: float = None,
        height: float = None,
        bg: Tuple = None,
        padding: float = None,
        pos: Tuple = (0, 0, 0)
    ) -> "PanelBuilder":
        """Create a panel builder."""
        return PanelBuilder(
            parent=self.parent,
            width=width or ui.panel.settings_width,
            height=height,
            bg=bg or ui.colors.bg_medium,
            padding=padding or ui.spacing.panel_padding,
            pos=pos
        )


class PanelBuilder:
    """Builder for creating panel layouts."""

    def __init__(
        self,
        parent=None,
        width: float = 1.0,
        height: float = None,
        bg: Tuple = None,
        padding: float = None,
        pos: Tuple = (0, 0, 0)
    ):
        self.parent = parent
        self.width = width
        self.height = height
        self.bg = bg or ui.colors.bg_medium
        self.padding = padding or ui.spacing.panel_padding
        self.pos = pos

        self._children: List[dict] = []
        self._gui_elements: List = []
        self._frame = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def label(
        self,
        text: str,
        style: str = "body",
        align: int = TextNode.ACenter,
        color: Tuple = None
    ) -> "PanelBuilder":
        """Add a label."""
        self._children.append({
            "type": "label",
            "text": text,
            "style": style,
            "align": align,
            "color": color
        })
        return self

    def button(
        self,
        text: str,
        command: Callable = None,
        small: bool = False,
        accent: bool = False
    ) -> "PanelBuilder":
        """Add a BG1 button."""
        self._children.append({
            "type": "button",
            "text": text,
            "command": command,
            "small": small,
            "accent": accent
        })
        return self

    def entry(
        self,
        initial_text: str = "",
        width: float = 0.5,
        obscured: bool = False,
        name: str = None
    ) -> "PanelBuilder":
        """Add a text entry field."""
        self._children.append({
            "type": "entry",
            "initial_text": initial_text,
            "width": width,
            "obscured": obscured,
            "name": name
        })
        return self

    def spacer(self, height: float = None) -> "PanelBuilder":
        """Add vertical space."""
        self._children.append({
            "type": "spacer",
            "height": height or ui.spacing.md
        })
        return self

    def row(
        self,
        spacing: float = None,
        justify: str = "center"
    ) -> "RowBuilder":
        """Add a horizontal row container."""
        row = RowBuilder(
            spacing=spacing or ui.spacing.sm,
            justify=justify
        )
        self._children.append({
            "type": "row",
            "builder": row
        })
        return row

    def column(
        self,
        spacing: float = None,
        align: str = "center"
    ) -> "ColumnBuilder":
        """Add a vertical column container."""
        col = ColumnBuilder(
            spacing=spacing or ui.spacing.sm,
            align=align
        )
        self._children.append({
            "type": "column",
            "builder": col
        })
        return col

    def build(self) -> DirectFrame:
        """Build the panel and all children."""
        # Calculate height if not specified
        if self.height is None:
            self.height = self._calculate_height()

        half_w = self.width / 2
        half_h = self.height / 2

        # Create main frame
        self._frame = DirectFrame(
            parent=self.parent,
            frameSize=(-half_w, half_w, -half_h, half_h),
            frameColor=self.bg,
            pos=self.pos
        )
        self._frame.setTransparency(TransparencyAttrib.M_alpha)

        # Layout children from top to bottom
        current_y = half_h - self.padding

        for child in self._children:
            current_y = self._build_child(child, current_y)

        return self._frame

    def _calculate_height(self) -> float:
        """Calculate panel height from children."""
        height = self.padding * 2  # Top and bottom padding

        for child in self._children:
            if child["type"] == "label":
                scale = self._get_style_scale(child["style"])
                height += scale * 1.8
            elif child["type"] == "button":
                if child["small"]:
                    height += ui.button.small_scale * ui.button.small_height * 2.5
                else:
                    height += ui.button.scale * ui.button.height * 2.5
            elif child["type"] == "entry":
                height += ui.font.entry * 3
            elif child["type"] == "spacer":
                height += child["height"]
            elif child["type"] == "row":
                height += child["builder"]._calculate_height()
            elif child["type"] == "column":
                height += child["builder"]._calculate_height()

        return height

    def _get_style_scale(self, style: str) -> float:
        """Get font scale for a style."""
        scales = {
            "title": ui.font.title,
            "subtitle": ui.font.subtitle,
            "heading": ui.font.heading,
            "label": ui.font.label,
            "body": ui.font.body,
            "small": ui.font.small,
        }
        return scales.get(style, ui.font.body)

    def _build_child(self, child: dict, y: float) -> float:
        """Build a single child element. Returns new y position."""
        child_type = child["type"]

        if child_type == "label":
            scale = self._get_style_scale(child["style"])
            color = child["color"] or self._get_style_color(child["style"])

            elem = DirectLabel(
                parent=self._frame,
                text=child["text"],
                text_scale=scale,
                text_fg=color,
                text_align=child["align"],
                frameColor=(0, 0, 0, 0),
                pos=(0, 0, y - scale * 0.5)
            )
            self._gui_elements.append(elem)
            return y - scale * 1.8

        elif child_type == "button":
            ButtonClass = BG1ButtonSmall if child["small"] else BG1Button
            btn_scale = ui.button.small_scale if child["small"] else ui.button.scale
            btn_height = ui.button.small_height if child["small"] else ui.button.height

            elem = ButtonClass.create(
                parent=self._frame,
                text=child["text"],
                command=child["command"],
                pos=(0, 0, y - btn_scale * btn_height)
            )
            self._gui_elements.append(elem)
            return y - btn_scale * btn_height * 2.5

        elif child_type == "entry":
            entry_width = child["width"] / ui.font.entry

            elem = DirectEntry(
                parent=self._frame,
                scale=ui.font.entry,
                pos=(-child["width"] / 2, 0, y - ui.font.entry),
                initialText=child["initial_text"],
                width=entry_width,
                numLines=1,
                obscured=child["obscured"],
                frameColor=ui.colors.entry_bg,
                text_fg=ui.colors.text_primary,
            )
            self._gui_elements.append(elem)

            if child["name"]:
                setattr(self, f"entry_{child['name']}", elem)

            return y - ui.font.entry * 3

        elif child_type == "spacer":
            return y - child["height"]

        elif child_type == "row":
            row_height = child["builder"]._calculate_height()
            child["builder"]._build(self._frame, y - row_height / 2, self.width - self.padding * 2)
            self._gui_elements.extend(child["builder"]._gui_elements)
            return y - row_height

        elif child_type == "column":
            col_height = child["builder"]._calculate_height()
            child["builder"]._build(self._frame, y, self.width - self.padding * 2)
            self._gui_elements.extend(child["builder"]._gui_elements)
            return y - col_height

        return y

    def _get_style_color(self, style: str) -> Tuple:
        """Get text color for a style."""
        colors = {
            "title": ui.colors.gold,
            "subtitle": ui.colors.text_secondary,
            "heading": ui.colors.text_primary,
            "label": ui.colors.text_secondary,
            "body": ui.colors.text_primary,
            "small": ui.colors.text_hint,
        }
        return colors.get(style, ui.colors.text_primary)

    def destroy(self):
        """Destroy all elements."""
        for elem in self._gui_elements:
            if hasattr(elem, 'destroy'):
                elem.destroy()
        if self._frame:
            self._frame.destroy()
        self._gui_elements.clear()

    def get_frame(self) -> DirectFrame:
        """Get the main frame."""
        return self._frame


class RowBuilder:
    """Builder for horizontal row layouts."""

    def __init__(self, spacing: float = None, justify: str = "center"):
        self.spacing = spacing or ui.spacing.sm
        self.justify = justify
        self._children: List[dict] = []
        self._gui_elements: List = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def label(self, text: str, style: str = "body", color: Tuple = None) -> "RowBuilder":
        self._children.append({
            "type": "label",
            "text": text,
            "style": style,
            "color": color
        })
        return self

    def button(self, text: str, command: Callable = None, small: bool = False) -> "RowBuilder":
        self._children.append({
            "type": "button",
            "text": text,
            "command": command,
            "small": small
        })
        return self

    def spacer(self, width: float = None) -> "RowBuilder":
        self._children.append({
            "type": "spacer",
            "width": width or ui.spacing.md
        })
        return self

    def _calculate_height(self) -> float:
        """Calculate row height from children."""
        max_height = ui.spacing.md

        for child in self._children:
            if child["type"] == "label":
                scale = self._get_style_scale(child["style"])
                max_height = max(max_height, scale * 1.5)
            elif child["type"] == "button":
                if child["small"]:
                    max_height = max(max_height, ui.button.small_scale * ui.button.small_height * 2.2)
                else:
                    max_height = max(max_height, ui.button.scale * ui.button.height * 2.2)

        return max_height

    def _get_style_scale(self, style: str) -> float:
        scales = {
            "title": ui.font.title,
            "subtitle": ui.font.subtitle,
            "heading": ui.font.heading,
            "label": ui.font.label,
            "body": ui.font.body,
            "small": ui.font.small,
        }
        return scales.get(style, ui.font.body)

    def _build(self, parent, y: float, available_width: float):
        """Build the row."""
        # Calculate total width of children
        total_width = 0
        widths = []

        for child in self._children:
            if child["type"] == "label":
                w = len(child["text"]) * self._get_style_scale(child["style"]) * 0.5
                widths.append(w)
            elif child["type"] == "button":
                if child["small"]:
                    w = ui.button.small_scale * ui.button.small_width * 2
                else:
                    w = ui.button.scale * ui.button.width * 2
                widths.append(w)
            elif child["type"] == "spacer":
                widths.append(child["width"])
            else:
                widths.append(0.1)
            total_width += widths[-1]

        total_width += self.spacing * (len(self._children) - 1)

        # Starting X based on justify
        if self.justify == "center":
            x = -total_width / 2
        elif self.justify == "start":
            x = -available_width / 2
        elif self.justify == "end":
            x = available_width / 2 - total_width
        elif self.justify == "space-between" and len(self._children) > 1:
            x = -available_width / 2
            self.spacing = (available_width - total_width + self.spacing * (len(self._children) - 1)) / (len(self._children) - 1)
        else:
            x = -total_width / 2

        # Build children
        for i, child in enumerate(self._children):
            if child["type"] == "label":
                scale = self._get_style_scale(child["style"])
                color = child.get("color") or ui.colors.text_primary

                elem = DirectLabel(
                    parent=parent,
                    text=child["text"],
                    text_scale=scale,
                    text_fg=color,
                    text_align=TextNode.ALeft,
                    frameColor=(0, 0, 0, 0),
                    pos=(x, 0, y)
                )
                self._gui_elements.append(elem)

            elif child["type"] == "button":
                ButtonClass = BG1ButtonSmall if child["small"] else BG1Button

                elem = ButtonClass.create(
                    parent=parent,
                    text=child["text"],
                    command=child["command"],
                    pos=(x + widths[i] / 2, 0, y)
                )
                self._gui_elements.append(elem)

            x += widths[i] + self.spacing


class ColumnBuilder:
    """Builder for vertical column layouts."""

    def __init__(self, spacing: float = None, align: str = "center"):
        self.spacing = spacing or ui.spacing.sm
        self.align = align
        self._children: List[dict] = []
        self._gui_elements: List = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def label(self, text: str, style: str = "body", color: Tuple = None) -> "ColumnBuilder":
        self._children.append({
            "type": "label",
            "text": text,
            "style": style,
            "color": color
        })
        return self

    def button(self, text: str, command: Callable = None, small: bool = False) -> "ColumnBuilder":
        self._children.append({
            "type": "button",
            "text": text,
            "command": command,
            "small": small
        })
        return self

    def row(self, spacing: float = None, justify: str = "center") -> RowBuilder:
        row = RowBuilder(spacing=spacing, justify=justify)
        self._children.append({
            "type": "row",
            "builder": row
        })
        return row

    def spacer(self, height: float = None) -> "ColumnBuilder":
        self._children.append({
            "type": "spacer",
            "height": height or ui.spacing.sm
        })
        return self

    def _calculate_height(self) -> float:
        height = 0
        for child in self._children:
            if child["type"] == "label":
                scale = self._get_style_scale(child["style"])
                height += scale * 1.5
            elif child["type"] == "button":
                if child["small"]:
                    height += ui.button.small_scale * ui.button.small_height * 2.2
                else:
                    height += ui.button.scale * ui.button.height * 2.2
            elif child["type"] == "spacer":
                height += child["height"]
            elif child["type"] == "row":
                height += child["builder"]._calculate_height()
            height += self.spacing
        return height

    def _get_style_scale(self, style: str) -> float:
        scales = {
            "title": ui.font.title,
            "subtitle": ui.font.subtitle,
            "heading": ui.font.heading,
            "label": ui.font.label,
            "body": ui.font.body,
            "small": ui.font.small,
        }
        return scales.get(style, ui.font.body)

    def _build(self, parent, y: float, available_width: float):
        """Build the column."""
        current_y = y

        for child in self._children:
            if child["type"] == "label":
                scale = self._get_style_scale(child["style"])
                color = child.get("color") or ui.colors.text_primary

                elem = DirectLabel(
                    parent=parent,
                    text=child["text"],
                    text_scale=scale,
                    text_fg=color,
                    text_align=TextNode.ACenter if self.align == "center" else TextNode.ALeft,
                    frameColor=(0, 0, 0, 0),
                    pos=(0, 0, current_y - scale * 0.5)
                )
                self._gui_elements.append(elem)
                current_y -= scale * 1.5

            elif child["type"] == "button":
                ButtonClass = BG1ButtonSmall if child["small"] else BG1Button
                btn_scale = ui.button.small_scale if child["small"] else ui.button.scale
                btn_height = ui.button.small_height if child["small"] else ui.button.height

                elem = ButtonClass.create(
                    parent=parent,
                    text=child["text"],
                    command=child["command"],
                    pos=(0, 0, current_y - btn_scale * btn_height)
                )
                self._gui_elements.append(elem)
                current_y -= btn_scale * btn_height * 2.2

            elif child["type"] == "spacer":
                current_y -= child["height"]

            elif child["type"] == "row":
                row_height = child["builder"]._calculate_height()
                child["builder"]._build(parent, current_y - row_height / 2, available_width)
                self._gui_elements.extend(child["builder"]._gui_elements)
                current_y -= row_height

            current_y -= self.spacing
