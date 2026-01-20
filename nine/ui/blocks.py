# nine/ui/blocks.py
"""
HTML-like Block Layout System for Panda3D DirectGUI.

Provides automatic layout without manual positioning.
Elements stack vertically, rows distribute horizontally.

Key concepts:
- y coordinate is always the TOP edge of the element
- Elements position themselves so their visual top aligns with y
- Row handles horizontal distribution, Block handles vertical stacking
"""

from typing import List, Optional, Callable, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton, DirectEntry,
    DirectSlider, DirectCheckButton, DirectOptionMenu, DGG
)
from panda3d.core import TextNode, TransparencyAttrib

from .ui_config import ui


class Justify(Enum):
    """Horizontal alignment for rows."""
    START = "start"
    CENTER = "center"
    END = "end"
    SPACE_BETWEEN = "space-between"


@dataclass
class ElementSize:
    """Size of an element."""
    width: float = 0.0
    height: float = 0.0


class BaseElement:
    """Base class for all layout elements."""

    def get_size(self) -> ElementSize:
        """Returns the size this element needs."""
        raise NotImplementedError

    def build(self, parent, x: float, y: float, available_width: float) -> Any:
        """
        Build the element.

        Args:
            parent: Parent node
            x: Left edge X coordinate
            y: TOP edge Y coordinate (element grows downward)
            available_width: Width available for this element
        """
        raise NotImplementedError


class LabelElement(BaseElement):
    """A text label element."""

    def __init__(self, text: str, style: str = "body", color: Tuple = None, align: str = "left"):
        self.text = text
        self.style = style
        self.color = color
        self.align = align
        self._scale = self._get_scale()

    def _get_scale(self) -> float:
        scales = {
            "title": ui.font.title,
            "subtitle": ui.font.subtitle,
            "heading": ui.font.heading,
            "label": ui.font.label,
            "body": ui.font.body,
            "small": ui.font.small,
        }
        return scales.get(self.style, ui.font.body)

    def _get_color(self) -> Tuple:
        if self.color:
            return self.color
        colors = {
            "title": ui.colors.gold,
            "subtitle": ui.colors.text_secondary,
            "heading": ui.colors.text_primary,
            "label": ui.colors.text_secondary,
            "body": ui.colors.text_primary,
            "small": ui.colors.text_hint,
        }
        return colors.get(self.style, ui.colors.text_primary)

    def get_size(self) -> ElementSize:
        # Более консервативная оценка ширины (0.6 для кириллицы)
        width = len(self.text) * self._scale * 0.6
        height = self._scale * 1.4
        return ElementSize(width, height)

    def build(self, parent, x: float, y: float, available_width: float):
        size = self.get_size()

        # Determine X position based on alignment
        if self.align == "center":
            pos_x = x + available_width / 2
            text_align = TextNode.ACenter
        elif self.align == "right":
            pos_x = x + available_width
            text_align = TextNode.ARight
        else:
            pos_x = x
            text_align = TextNode.ALeft

        # Y is top edge, text baseline should be slightly below
        pos_y = y - size.height / 2

        return DirectLabel(
            parent=parent,
            text=self.text,
            text_scale=self._scale,
            text_fg=self._get_color(),
            text_align=text_align,
            frameColor=(0, 0, 0, 0),
            pos=(pos_x, 0, pos_y)
        )


class ButtonElement(BaseElement):
    """A button element using BG1Button."""

    # Фиксированные размеры кнопок
    SMALL_WIDTH = 0.30
    SMALL_HEIGHT = 0.08
    NORMAL_WIDTH = 0.45
    NORMAL_HEIGHT = 0.10

    def __init__(self, text: str, command: Callable = None, small: bool = True):
        self.text = text
        self.command = command
        self.small = small

    def get_size(self) -> ElementSize:
        if self.small:
            return ElementSize(self.SMALL_WIDTH, self.SMALL_HEIGHT)
        return ElementSize(self.NORMAL_WIDTH, self.NORMAL_HEIGHT)

    def build(self, parent, x: float, y: float, available_width: float):
        from .bg1_button import BG1Button, BG1ButtonSmall

        size = self.get_size()
        ButtonClass = BG1ButtonSmall if self.small else BG1Button

        # Центр кнопки
        center_x = x + size.width / 2
        center_y = y - size.height / 2

        return ButtonClass.create(
            parent=parent,
            text=self.text,
            command=self.command,
            pos=(center_x, 0, center_y)
        )


class EntryElement(BaseElement):
    """A text entry field."""

    ENTRY_SCALE = 0.05  # Фиксированный масштаб

    def __init__(self, name: str = None, initial: str = "", width: int = 12,
                 obscured: bool = False, focus: bool = False):
        self.name = name
        self.initial = initial
        self.char_width = width
        self.obscured = obscured
        self.focus = focus
        self._entry = None

    def get_size(self) -> ElementSize:
        # Entry width: scale * char_width * ~0.6 (font width factor)
        width = self.char_width * self.ENTRY_SCALE * 0.6
        height = self.ENTRY_SCALE * 2.2
        return ElementSize(width, height)

    def build(self, parent, x: float, y: float, available_width: float):
        size = self.get_size()
        pos_y = y - size.height / 2

        self._entry = DirectEntry(
            parent=parent,
            scale=self.ENTRY_SCALE,
            pos=(x, 0, pos_y),
            initialText=self.initial,
            numLines=1,
            width=self.char_width,
            obscured=self.obscured,
            focus=1 if self.focus else 0,
            text_align=TextNode.ALeft,
            frameColor=ui.colors.entry_bg,
            text_fg=ui.colors.text_primary,
            cursorKeys=True,
        )
        return self._entry

    def get_value(self) -> str:
        if self._entry:
            return self._entry.get()
        return ""


class SliderElement(BaseElement):
    """A slider with optional value display."""

    # Slider визуальные размеры
    SLIDER_SCALE = 0.22
    SLIDER_WIDTH = 0.40  # Ширина слайдера (scale * ~1.8)
    VALUE_LABEL_WIDTH = 0.12  # Ширина метки значения

    def __init__(self, name: str = None, min_val: float = 0, max_val: float = 100,
                 initial: float = 50, command: Callable = None,
                 show_value: bool = True, value_format: str = "{:.0f}"):
        self.name = name
        self.min_val = min_val
        self.max_val = max_val
        self.initial = initial
        self.command = command
        self.show_value = show_value
        self.value_format = value_format
        self._slider = None
        self._value_label = None

    def get_size(self) -> ElementSize:
        # Реальная ширина слайдера + отступ + метка значения
        width = self.SLIDER_WIDTH
        if self.show_value:
            width += self.VALUE_LABEL_WIDTH + 0.02
        height = ui.font.label * 1.8
        return ElementSize(width, height)

    def build(self, parent, x: float, y: float, available_width: float):
        size = self.get_size()
        center_y = y - size.height / 2

        def on_change():
            if self._value_label and self._slider:
                val = self._slider.getValue()
                self._value_label['text'] = self.value_format.format(val)
            if self.command:
                self.command()

        # Слайдер центрируется в своей области
        slider_center_x = x + self.SLIDER_WIDTH / 2
        self._slider = DirectSlider(
            parent=parent,
            range=(self.min_val, self.max_val),
            value=self.initial,
            scale=self.SLIDER_SCALE,
            pos=(slider_center_x, 0, center_y),
            thumb_frameColor=ui.colors.btn_hover,
            frameColor=ui.colors.bg_light,
            command=on_change
        )

        if self.show_value:
            # Метка значения справа от слайдера
            label_x = x + self.SLIDER_WIDTH + 0.02
            self._value_label = DirectLabel(
                parent=parent,
                text=self.value_format.format(self.initial),
                text_scale=ui.font.small,
                text_fg=ui.colors.text_primary,
                frameColor=(0, 0, 0, 0),
                pos=(label_x, 0, center_y),
                text_align=TextNode.ALeft,
            )

        return self._slider

    def get_value(self) -> float:
        if self._slider:
            return self._slider.getValue()
        return self.initial


class CheckboxElement(BaseElement):
    """A checkbox element."""

    CHECKBOX_SCALE = 0.05  # Фиксированный масштаб чекбокса
    CHECKBOX_SIZE = 0.10   # Визуальный размер

    def __init__(self, name: str = None, initial: bool = False, command: Callable = None):
        self.name = name
        self.initial = initial
        self.command = command
        self._checkbox = None

    def get_size(self) -> ElementSize:
        return ElementSize(self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)

    def build(self, parent, x: float, y: float, available_width: float):
        size = self.get_size()
        center_y = y - size.height / 2
        center_x = x + size.width / 2

        self._checkbox = DirectCheckButton(
            parent=parent,
            scale=self.CHECKBOX_SCALE,
            pos=(center_x, 0, center_y),
            text="",
            indicatorValue=self.initial,
            boxImage=None,
            boxImageColor=ui.colors.btn_normal,
            boxImageScale=1.5,
            boxRelief=DGG.FLAT,
            frameColor=(0, 0, 0, 0),
            command=self.command
        )
        return self._checkbox

    def get_value(self) -> bool:
        if self._checkbox:
            return bool(self._checkbox['indicatorValue'])
        return self.initial


class DropdownElement(BaseElement):
    """A dropdown/select menu."""

    DROPDOWN_SCALE = 0.05
    DROPDOWN_WIDTH = 0.35

    def __init__(self, name: str = None, items: List[str] = None,
                 initial: str = None, command: Callable = None):
        self.name = name
        self.items = items or []
        self.initial = initial or (items[0] if items else "")
        self.command = command
        self._menu = None

    def get_size(self) -> ElementSize:
        return ElementSize(self.DROPDOWN_WIDTH, self.DROPDOWN_SCALE * 2.2)

    def build(self, parent, x: float, y: float, available_width: float):
        size = self.get_size()
        pos_y = y - size.height / 2

        initial_idx = 0
        if self.initial in self.items:
            initial_idx = self.items.index(self.initial)

        self._menu = DirectOptionMenu(
            parent=parent,
            text=self.initial,
            scale=self.DROPDOWN_SCALE,
            pos=(x, 0, pos_y),
            items=self.items,
            initialitem=initial_idx,
            highlightColor=ui.colors.btn_hover,
            frameColor=ui.colors.entry_bg,
            text_fg=ui.colors.text_primary,
            popupMarker_frameColor=ui.colors.btn_normal,
            command=self.command,
        )
        return self._menu

    def get_value(self) -> str:
        if self._menu:
            return self._menu.get()
        return self.initial


class SpacerElement(BaseElement):
    """Empty vertical space."""

    def __init__(self, height: float = None):
        self.height = height or ui.spacing.md

    def get_size(self) -> ElementSize:
        return ElementSize(0, self.height)

    def build(self, parent, x: float, y: float, available_width: float):
        return None


class HSpacerElement(BaseElement):
    """Empty horizontal space (for rows)."""

    def __init__(self, width: float = None):
        self.width = width or ui.spacing.md

    def get_size(self) -> ElementSize:
        return ElementSize(self.width, 0)

    def build(self, parent, x: float, y: float, available_width: float):
        return None


class Row:
    """
    Horizontal row container.
    Elements are placed side by side with configurable spacing and alignment.
    """

    def __init__(self, gap: float = None, justify: str = "start"):
        self.gap = gap if gap is not None else ui.spacing.sm
        self.justify = Justify(justify) if isinstance(justify, str) else justify
        self.elements: List[BaseElement] = []
        self._built_elements: List = []

    def label(self, text: str, style: str = "label", color: Tuple = None) -> "Row":
        """Add a label to the row."""
        self.elements.append(LabelElement(text, style, color, align="left"))
        return self

    def button(self, text: str, command: Callable = None, small: bool = True) -> "Row":
        """Add a button to the row."""
        self.elements.append(ButtonElement(text, command, small))
        return self

    def entry(self, name: str = None, initial: str = "", width: int = 12,
              obscured: bool = False, focus: bool = False) -> "Row":
        """Add a text entry to the row."""
        self.elements.append(EntryElement(name, initial, width, obscured, focus))
        return self

    def slider(self, name: str = None, min_val: float = 0, max_val: float = 100,
               initial: float = 50, command: Callable = None,
               show_value: bool = True, value_format: str = "{:.0f}") -> "Row":
        """Add a slider to the row."""
        self.elements.append(SliderElement(name, min_val, max_val, initial,
                                           command, show_value, value_format))
        return self

    def checkbox(self, name: str = None, initial: bool = False,
                 command: Callable = None) -> "Row":
        """Add a checkbox to the row."""
        self.elements.append(CheckboxElement(name, initial, command))
        return self

    def dropdown(self, name: str = None, items: List[str] = None,
                 initial: str = None, command: Callable = None) -> "Row":
        """Add a dropdown to the row."""
        self.elements.append(DropdownElement(name, items, initial, command))
        return self

    def spacer(self, width: float = None) -> "Row":
        """Add horizontal space."""
        self.elements.append(HSpacerElement(width))
        return self

    def get_size(self) -> ElementSize:
        """Calculate total size of the row."""
        if not self.elements:
            return ElementSize(0, ui.spacing.sm)

        total_width = 0
        max_height = 0

        for elem in self.elements:
            size = elem.get_size()
            total_width += size.width
            max_height = max(max_height, size.height)

        # Add gaps between elements
        if len(self.elements) > 1:
            total_width += self.gap * (len(self.elements) - 1)

        return ElementSize(total_width, max_height)

    def build(self, parent, x: float, y: float, available_width: float) -> List:
        """
        Build all elements in the row.

        Args:
            parent: Parent node
            x: Left edge of row
            y: TOP edge of row
            available_width: Total width available
        """
        if not self.elements:
            return []

        self._built_elements = []
        sizes = [elem.get_size() for elem in self.elements]
        content_width = sum(s.width for s in sizes)
        row_height = max((s.height for s in sizes), default=ui.spacing.sm)

        # Calculate starting X and gap based on justify mode
        if self.justify == Justify.CENTER:
            total_with_gaps = content_width + self.gap * max(0, len(self.elements) - 1)
            current_x = x + (available_width - total_with_gaps) / 2
            gap = self.gap
        elif self.justify == Justify.END:
            total_with_gaps = content_width + self.gap * max(0, len(self.elements) - 1)
            current_x = x + available_width - total_with_gaps
            gap = self.gap
        elif self.justify == Justify.SPACE_BETWEEN and len(self.elements) > 1:
            current_x = x
            # Ensure gap is non-negative (min gap = 0.02)
            extra_space = available_width - content_width
            gap = max(0.02, extra_space / (len(self.elements) - 1))
        else:  # START
            current_x = x
            gap = self.gap

        # Build each element
        for elem, size in zip(self.elements, sizes):
            # All elements get the same y (top of row) - they handle their own vertical centering
            result = elem.build(parent, current_x, y, size.width)
            if result:
                self._built_elements.append(result)

            current_x += size.width + gap

        return self._built_elements

    def get_element(self, name: str):
        """Get a named element from this row."""
        for elem in self.elements:
            if hasattr(elem, 'name') and elem.name == name:
                return elem
        return None


class Block:
    """
    Main block container - like a div in HTML.
    Elements stack vertically from top to bottom.
    """

    def __init__(self, parent=None, width: float = 1.0, padding: float = None,
                 bg_color: Tuple = None, pos: Tuple = (0, 0, 0)):
        self.parent = parent
        self.width = width
        self.padding = padding if padding is not None else ui.spacing.panel_padding
        self.bg_color = bg_color or ui.colors.bg_medium
        self.pos = pos

        self.elements: List = []  # BaseElement or Row
        self._frame: DirectFrame = None
        self._built_elements: List = []
        self._named_elements: Dict[str, Any] = {}

    def label(self, text: str, style: str = "body", color: Tuple = None,
              align: str = "left") -> "Block":
        """Add a text label."""
        self.elements.append(LabelElement(text, style, color, align))
        return self

    def button(self, text: str, command: Callable = None, small: bool = True) -> "Block":
        """Add a button."""
        self.elements.append(ButtonElement(text, command, small))
        return self

    def entry(self, name: str = None, initial: str = "", width: int = 12,
              obscured: bool = False, focus: bool = False) -> "Block":
        """Add a text entry field."""
        elem = EntryElement(name, initial, width, obscured, focus)
        self.elements.append(elem)
        if name:
            self._named_elements[name] = elem
        return self

    def slider(self, name: str = None, min_val: float = 0, max_val: float = 100,
               initial: float = 50, command: Callable = None,
               show_value: bool = True, value_format: str = "{:.0f}") -> "Block":
        """Add a slider."""
        elem = SliderElement(name, min_val, max_val, initial, command, show_value, value_format)
        self.elements.append(elem)
        if name:
            self._named_elements[name] = elem
        return self

    def checkbox(self, name: str = None, initial: bool = False,
                 command: Callable = None) -> "Block":
        """Add a checkbox."""
        elem = CheckboxElement(name, initial, command)
        self.elements.append(elem)
        if name:
            self._named_elements[name] = elem
        return self

    def dropdown(self, name: str = None, items: List[str] = None,
                 initial: str = None, command: Callable = None) -> "Block":
        """Add a dropdown menu."""
        elem = DropdownElement(name, items, initial, command)
        self.elements.append(elem)
        if name:
            self._named_elements[name] = elem
        return self

    def spacer(self, height: float = None) -> "Block":
        """Add vertical space."""
        self.elements.append(SpacerElement(height))
        return self

    def row(self, gap: float = None, justify: str = "start") -> Row:
        """
        Add a horizontal row container.
        Returns the Row for adding elements.
        """
        row = Row(gap, justify)
        self.elements.append(row)
        return row

    def get_content_height(self) -> float:
        """Calculate total height of all content."""
        total = 0
        for elem in self.elements:
            size = elem.get_size()
            total += size.height
        return total

    def build(self, height: float = None) -> DirectFrame:
        """
        Build the block and all children.

        Args:
            height: Fixed height. If None, calculated from content.

        Returns:
            The main DirectFrame
        """
        # Calculate dimensions
        content_height = self.get_content_height()
        actual_height = height if height else (content_height + self.padding * 2)

        half_w = self.width / 2
        half_h = actual_height / 2

        # Create main frame
        self._frame = DirectFrame(
            parent=self.parent,
            frameSize=(-half_w, half_w, -half_h, half_h),
            frameColor=self.bg_color,
            pos=self.pos
        )
        self._frame.setTransparency(TransparencyAttrib.M_alpha)

        # Content area
        inner_width = self.width - self.padding * 2
        start_x = -half_w + self.padding
        current_y = half_h - self.padding  # Start from top

        self._built_elements = []

        for elem in self.elements:
            size = elem.get_size()

            if isinstance(elem, Row):
                # Row gets the full inner width
                results = elem.build(self._frame, start_x, current_y, inner_width)
                self._built_elements.extend(results)

                # Register named elements from row
                for e in elem.elements:
                    if hasattr(e, 'name') and e.name:
                        self._named_elements[e.name] = e
            else:
                # Regular element
                result = elem.build(self._frame, start_x, current_y, inner_width)
                if result:
                    self._built_elements.append(result)

            # Move down by element height
            current_y -= size.height

        return self._frame

    def get(self, name: str):
        """Get value of a named element."""
        elem = self._named_elements.get(name)
        if elem and hasattr(elem, 'get_value'):
            return elem.get_value()
        return None

    def get_element(self, name: str):
        """Get a named element object."""
        return self._named_elements.get(name)

    def get_frame(self) -> DirectFrame:
        """Get the main DirectFrame."""
        return self._frame

    def show(self):
        """Show the block."""
        if self._frame:
            self._frame.show()

    def hide(self):
        """Hide the block."""
        if self._frame:
            self._frame.hide()

    def destroy(self):
        """Destroy the block and all children."""
        for elem in self._built_elements:
            if hasattr(elem, 'destroy'):
                elem.destroy()
        if self._frame:
            self._frame.destroy()
        self._built_elements.clear()
        self._named_elements.clear()
        self._frame = None
