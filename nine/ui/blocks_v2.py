# nine/ui/blocks_v2.py
"""
Improved Block Layout System for Panda3D DirectGUI - Version 2.

Based on best practices from:
- DirectGui-layout-system (Epihaius)
- LUI Framework (tobspr)
- Panda3D community examples

Key improvements:
- CSS-like margin/padding for all elements
- Min/Max size constraints
- Better size caching
- Sizer-based architecture
- Responsive without text scaling
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
    """Size of an element with min/max constraints."""
    width: float = 0.0
    height: float = 0.0
    min_width: float = 0.0
    max_width: float = float('inf')
    min_height: float = 0.0
    max_height: float = float('inf')

    def constrain(self):
        """Apply min/max constraints."""
        self.width = max(self.min_width, min(self.max_width, self.width))
        self.height = max(self.min_height, min(self.max_height, self.height))


@dataclass
class Margin:
    """CSS-like margin (outside element)."""
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0
    left: float = 0.0

    @classmethod
    def all(cls, value: float):
        """Create uniform margin."""
        return cls(value, value, value, value)

    @classmethod
    def symmetric(cls, vertical: float, horizontal: float):
        """Create symmetric margin."""
        return cls(vertical, horizontal, vertical, horizontal)


@dataclass
class Padding:
    """CSS-like padding (inside element)."""
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0
    left: float = 0.0

    @classmethod
    def all(cls, value: float):
        """Create uniform padding."""
        return cls(value, value, value, value)

    @classmethod
    def symmetric(cls, vertical: float, horizontal: float):
        """Create symmetric padding."""
        return cls(vertical, horizontal, vertical, horizontal)


class BaseElement:
    """Base class for all layout elements with margin support."""

    def __init__(self):
        self.margin = Margin()
        self._cached_size = None
        self._dirty = True

    def get_size(self) -> ElementSize:
        """Returns the size this element needs (including margin)."""
        if not self._dirty and self._cached_size:
            return self._cached_size

        size = self._calculate_size()
        # Add margin to size
        size.width += self.margin.left + self.margin.right
        size.height += self.margin.top + self.margin.bottom
        size.constrain()

        self._cached_size = size
        self._dirty = False
        return size

    def _calculate_size(self) -> ElementSize:
        """Override in subclasses to calculate actual size."""
        raise NotImplementedError

    def build(self, parent, x: float, y: float, available_width: float) -> Any:
        """Build the element. x, y are OUTER coordinates (including margin)."""
        raise NotImplementedError

    def invalidate(self):
        """Mark size cache as dirty."""
        self._dirty = True


class LabelElement(BaseElement):
    """A text label element with improved sizing."""

    # More accurate character width multipliers
    CHAR_WIDTH_LATIN = 0.45
    CHAR_WIDTH_CYRILLIC = 0.5

    def __init__(self, text: str, style: str = "body", color: Tuple = None, align: str = "left"):
        super().__init__()
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

    def _calculate_size(self) -> ElementSize:
        # More accurate width estimation using Panda3D's text measurement
        # Fallback to heuristic if TextNode not available
        try:
            # Use actual text measurement
            from panda3d.core import TextNode as TN
            tn = TN("")
            tn.setText(self.text)
            bounds = tn.getCardActual()
            width = (bounds[1] - bounds[0]) * self._scale
        except:
            # Fallback heuristic
            width = len(self.text) * self._scale * self.CHAR_WIDTH_CYRILLIC

        height = self._scale * 1.4

        return ElementSize(
            width=width,
            height=height,
            min_width=0,
            min_height=height
        )

    def build(self, parent, x: float, y: float, available_width: float):
        size = self.get_size()

        # Apply margin offset
        inner_x = x + self.margin.left
        inner_y = y - self.margin.top

        # Determine X position based on alignment
        if self.align == "center":
            pos_x = inner_x + available_width / 2
            text_align = TextNode.ACenter
        elif self.align == "right":
            pos_x = inner_x + available_width
            text_align = TextNode.ARight
        else:
            pos_x = inner_x
            text_align = TextNode.ALeft

        # Y is top edge, text baseline should be slightly below
        content_height = size.height - self.margin.top - self.margin.bottom
        pos_y = inner_y - content_height / 2

        return DirectLabel(
            parent=parent,
            text=self.text,
            text_scale=self._scale,
            text_fg=self._get_color(),
            text_align=text_align,
            frameColor=(0, 0, 0, 0),
            pos=(pos_x, 0, pos_y),
        )


class ButtonElement(BaseElement):
    """Button with automatic sizing and min/max constraints."""

    def __init__(self, text: str, command: Callable = None, small: bool = True,
                 min_width: float = None, max_width: float = None):
        super().__init__()
        self.text = text
        self.command = command
        self.small = small
        self._min_width = min_width or (0.25 if small else 0.35)
        self._max_width = max_width or 1.0

    def _calculate_size(self) -> ElementSize:
        # Calculate based on text
        scale = 0.05 if self.small else 0.06
        text_width = len(self.text) * scale * 0.6  # Conservative estimate
        padding = 0.15  # Generous padding

        width = text_width + padding
        height = 0.08 if self.small else 0.10

        return ElementSize(
            width=width,
            height=height,
            min_width=self._min_width,
            max_width=self._max_width,
            min_height=height
        )

    def build(self, parent, x: float, y: float, available_width: float):
        from .bg1_button import BG1Button, BG1ButtonSmall

        size = self.get_size()
        ButtonClass = BG1ButtonSmall if self.small else BG1Button

        # Apply margin
        inner_x = x + self.margin.left
        inner_y = y - self.margin.top

        # Center button
        content_width = size.width - self.margin.left - self.margin.right
        content_height = size.height - self.margin.top - self.margin.bottom

        center_x = inner_x + content_width / 2
        center_y = inner_y - content_height / 2

        return ButtonClass.create(
            parent=parent,
            text=self.text,
            command=self.command,
            pos=(center_x, 0, center_y)
        )


class EntryElement(BaseElement):
    """Text entry with better sizing control."""

    ENTRY_SCALE = 0.045

    def __init__(self, name: str = None, initial: str = "", width: int = 12,
                 obscured: bool = False, focus: bool = False,
                 max_width: float = None):
        super().__init__()
        self.name = name
        self.initial = initial
        self.char_width = width
        self.obscured = obscured
        self.focus = focus
        self._max_width = max_width or 1.0
        self._entry = None

    def _calculate_size(self) -> ElementSize:
        # Calculate width based on character count
        width = self.char_width * self.ENTRY_SCALE * 0.6 * ui.scale
        height = self.ENTRY_SCALE * 2.2

        return ElementSize(
            width=width,
            height=height,
            max_width=self._max_width,
            min_height=height
        )

    def build(self, parent, x: float, y: float, available_width: float):
        size = self.get_size()

        # Apply margin
        inner_x = x + self.margin.left
        inner_y = y - self.margin.top

        content_height = size.height - self.margin.top - self.margin.bottom
        pos_y = inner_y - content_height / 2

        self._entry = DirectEntry(
            parent=parent,
            scale=self.ENTRY_SCALE,
            pos=(inner_x, 0, pos_y),
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
        return self.initial


class SliderElement(BaseElement):
    """Slider with proper spacing."""

    SLIDER_SCALE = 0.22
    SLIDER_WIDTH = 0.40
    VALUE_LABEL_WIDTH = 0.12

    def __init__(self, name: str = None, min_val: float = 0, max_val: float = 100,
                 initial: float = 50, command: Callable = None,
                 show_value: bool = True, value_format: str = "{:.0f}"):
        super().__init__()
        self.name = name
        self.min_val = min_val
        self.max_val = max_val
        self.initial = initial
        self.command = command
        self.show_value = show_value
        self.value_format = value_format
        self._slider = None
        self._value_label = None

    def _calculate_size(self) -> ElementSize:
        width = self.SLIDER_WIDTH
        if self.show_value:
            width += self.VALUE_LABEL_WIDTH + 0.02
        height = ui.font.label * 1.8

        return ElementSize(
            width=width,
            height=height,
            min_height=height
        )

    def build(self, parent, x: float, y: float, available_width: float):
        size = self.get_size()

        # Apply margin
        inner_x = x + self.margin.left
        inner_y = y - self.margin.top

        content_height = size.height - self.margin.top - self.margin.bottom
        center_y = inner_y - content_height / 2

        def on_change():
            if self._value_label and self._slider:
                val = self._slider.getValue()
                self._value_label['text'] = self.value_format.format(val)
            if self.command:
                self.command()

        slider_center_x = inner_x + self.SLIDER_WIDTH / 2
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
            label_x = inner_x + self.SLIDER_WIDTH + 0.02
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


class DropdownElement(BaseElement):
    """Dropdown with better sizing."""

    DROPDOWN_SCALE = 0.055
    DROPDOWN_WIDTH = 0.65

    def __init__(self, name: str = None, items: List[str] = None,
                 initial: str = None, command: Callable = None):
        super().__init__()
        self.name = name
        self.items = items or []
        self.initial = initial or (items[0] if items else "")
        self.command = command
        self._menu = None

    def _calculate_size(self) -> ElementSize:
        return ElementSize(
            width=self.DROPDOWN_WIDTH,
            height=self.DROPDOWN_SCALE * 2.2,
            min_height=self.DROPDOWN_SCALE * 2.2
        )

    def build(self, parent, x: float, y: float, available_width: float):
        size = self.get_size()

        # Apply margin
        inner_x = x + self.margin.left
        inner_y = y - self.margin.top

        content_height = size.height - self.margin.top - self.margin.bottom
        pos_y = inner_y - content_height / 2

        initial_idx = 0
        if self.initial in self.items:
            initial_idx = self.items.index(self.initial)

        self._menu = DirectOptionMenu(
            parent=parent,
            text=self.initial,
            scale=self.DROPDOWN_SCALE,
            pos=(inner_x, 0, pos_y),
            items=self.items,
            initialitem=initial_idx,
            highlightColor=ui.colors.btn_hover,
            frameColor=ui.colors.entry_bg,
            text_fg=ui.colors.text_primary,
            popupMarker_frameColor=ui.colors.btn_normal,
            # No command - prevents misclick apply
        )
        return self._menu

    def get_value(self) -> str:
        if self._menu:
            return self._menu.get()
        return self.initial


class CheckboxElement(BaseElement):
    """Checkbox element."""

    def __init__(self, name: str = None, initial: bool = False, command: Callable = None):
        super().__init__()
        self.name = name
        self.initial = initial
        self.command = command
        self._checkbox = None

    def _calculate_size(self) -> ElementSize:
        return ElementSize(
            width=0.10,
            height=0.08,
            min_width=0.10,
            min_height=0.08
        )

    def build(self, parent, x: float, y: float, available_width: float):
        size = self.get_size()

        # Apply margin
        inner_x = x + self.margin.left
        inner_y = y - self.margin.top

        content_height = size.height - self.margin.top - self.margin.bottom
        pos_y = inner_y - content_height / 2

        self._checkbox = DirectCheckButton(
            parent=parent,
            pos=(inner_x, 0, pos_y),
            scale=0.05,
            indicatorValue=self.initial,
            frameColor=ui.colors.entry_bg,
            command=self.command
        )
        return self._checkbox

    def get_value(self) -> bool:
        if self._checkbox:
            return bool(self._checkbox['indicatorValue'])
        return self.initial


class SpacerElement(BaseElement):
    """Vertical spacer."""

    def __init__(self, height: float = None):
        super().__init__()
        self._height = height or ui.spacing.md

    def _calculate_size(self) -> ElementSize:
        return ElementSize(width=0, height=self._height)

    def build(self, parent, x: float, y: float, available_width: float):
        return None


class HSpacerElement(BaseElement):
    """Horizontal spacer."""

    def __init__(self, width: float = None):
        super().__init__()
        self._width = width or ui.spacing.md

    def _calculate_size(self) -> ElementSize:
        return ElementSize(width=self._width, height=0)

    def build(self, parent, x: float, y: float, available_width: float):
        return None


class Row:
    """
    Horizontal row container with margin support.
    """

    def __init__(self, gap: float = None, justify: str = "start", parent_block=None):
        self.gap = gap if gap is not None else ui.spacing.sm
        self.justify = Justify(justify) if isinstance(justify, str) else justify
        self.elements: List[BaseElement] = []
        self._built_elements: List = []
        self.parent_block = parent_block  # Reference to parent Block for named elements

    def label(self, text: str, style: str = "label", color: Tuple = None, margin: Margin = None) -> "Row":
        """Add a label to the row."""
        elem = LabelElement(text, style, color, align="left")
        if margin:
            elem.margin = margin
        self.elements.append(elem)
        return self

    def button(self, text: str, command: Callable = None, small: bool = True,
               margin: Margin = None) -> "Row":
        """Add a button to the row."""
        elem = ButtonElement(text, command, small)
        if margin:
            elem.margin = margin
        self.elements.append(elem)
        return self

    def entry(self, name: str = None, initial: str = "", width: int = 12,
              obscured: bool = False, focus: bool = False, margin: Margin = None,
              max_width: float = None) -> "Row":
        """Add a text entry to the row."""
        elem = EntryElement(name, initial, width, obscured, focus, max_width=max_width)
        if margin:
            elem.margin = margin
        self.elements.append(elem)
        # Register named element in parent Block
        if name and self.parent_block:
            self.parent_block._named_elements[name] = elem
        return self

    def slider(self, name: str = None, min_val: float = 0, max_val: float = 100,
               initial: float = 50, command: Callable = None,
               show_value: bool = True, value_format: str = "{:.0f}",
               margin: Margin = None) -> "Row":
        """Add a slider to the row."""
        elem = SliderElement(name, min_val, max_val, initial, command, show_value, value_format)
        if margin:
            elem.margin = margin
        self.elements.append(elem)
        # Register named element in parent Block
        if name and self.parent_block:
            self.parent_block._named_elements[name] = elem
        return self

    def checkbox(self, name: str = None, initial: bool = False,
                 command: Callable = None, margin: Margin = None) -> "Row":
        """Add a checkbox to the row."""
        elem = CheckboxElement(name, initial, command)
        if margin:
            elem.margin = margin
        self.elements.append(elem)
        # Register named element in parent Block
        if name and self.parent_block:
            self.parent_block._named_elements[name] = elem
        return self

    def dropdown(self, name: str = None, items: List[str] = None,
                 initial: str = None, command: Callable = None,
                 margin: Margin = None) -> "Row":
        """Add a dropdown to the row."""
        elem = DropdownElement(name, items, initial, command)
        if margin:
            elem.margin = margin
        self.elements.append(elem)
        # Register named element in parent Block
        if name and self.parent_block:
            self.parent_block._named_elements[name] = elem
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
        """Build all elements in the row."""
        if not self.elements:
            return []

        self._built_elements = []
        sizes = [elem.get_size() for elem in self.elements]
        content_width = sum(s.width for s in sizes)
        row_height = max((s.height for s in sizes), default=ui.spacing.sm)

        # Calculate starting X and gap based on justify mode
        MIN_GAP = 0.05  # Minimum gap to prevent elements from touching

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
            extra_space = available_width - content_width
            gap = max(MIN_GAP, extra_space / (len(self.elements) - 1))
        else:  # START
            current_x = x
            gap = self.gap

        # Build each element
        for elem, size in zip(self.elements, sizes):
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

    def __init__(self, parent, width: float = 1.0, padding: float = 0.04,
                 bg_color: Tuple = None, pos: Tuple = (0, 0, 0)):
        self.parent = parent
        self.width = width
        self.padding = padding
        self.bg_color = bg_color or (0, 0, 0, 0)
        self.pos = pos

        self.elements: List = []  # Can be Row or BaseElement
        self._built_elements: List = []
        self._named_elements: dict = {}  # Track named elements (entry, dropdown, etc.)

    def row(self, gap: float = None, justify: str = "start") -> Row:
        """Add a row to the block."""
        r = Row(gap, justify, parent_block=self)
        self.elements.append(r)
        return r

    def label(self, text: str, style: str = "body", align: str = "left") -> "Block":
        """Add a standalone label."""
        elem = LabelElement(text, style, align=align)
        self.elements.append(elem)
        return self

    def spacer(self, height: float = None) -> "Block":
        """Add vertical space."""
        self.elements.append(SpacerElement(height))
        return self

    def build(self, height: float = None):
        """Build all elements in the block."""
        # Create background frame if needed
        if self.bg_color != (0, 0, 0, 0):
            hw = self.width / 2
            hh = (height / 2) if height else 0.5

            bg_frame = DirectFrame(
                parent=self.parent,
                frameSize=(-hw, hw, -hh, hh),
                frameColor=self.bg_color,
                pos=self.pos
            )
            bg_frame.setTransparency(TransparencyAttrib.M_alpha)
            self._built_elements.append(bg_frame)

        # Calculate available width (accounting for padding)
        available_width = self.width - (self.padding * 2)

        # Starting Y position (top of block)
        current_y = self.pos[2]

        # Starting X position (left edge + padding)
        start_x = self.pos[0] - self.width / 2 + self.padding

        # Build each element
        for elem in self.elements:
            if isinstance(elem, Row):
                size = elem.get_size()
                result = elem.build(self.parent, start_x, current_y, available_width)
                self._built_elements.extend(result)
                current_y -= size.height
            else:
                # Standalone element
                size = elem.get_size()
                result = elem.build(self.parent, start_x, current_y, available_width)
                if result:
                    self._built_elements.append(result)
                current_y -= size.height

    def get_element(self, name: str):
        """Get a named element from the block."""
        for elem in self.elements:
            if isinstance(elem, Row):
                result = elem.get_element(name)
                if result:
                    return result
            elif hasattr(elem, 'name') and elem.name == name:
                return elem
        return None

    def hide(self):
        """Hide all built elements."""
        for elem in self._built_elements:
            if hasattr(elem, 'hide'):
                elem.hide()

    def show(self):
        """Show all built elements."""
        for elem in self._built_elements:
            if hasattr(elem, 'show'):
                elem.show()

    def get(self, name: str):
        """Get value of a named element."""
        elem = self._named_elements.get(name)
        if elem and hasattr(elem, 'get_value'):
            return elem.get_value()
        return None

    def get_element(self, name: str):
        """Get a named element object."""
        return self._named_elements.get(name)

    def destroy(self):
        """Destroy all built elements."""
        for elem in self._built_elements:
            if hasattr(elem, 'destroy'):
                elem.destroy()
        self._built_elements.clear()


# Preset window flags
WINDOW_FLAGS_MENU = (
    DGG.NORMAL
)

WINDOW_FLAGS_RESIZABLE = (
    DGG.NORMAL
)

# Preset sizes
SIZE_BUTTON_LARGE = 50
SIZE_BUTTON_MEDIUM = 40
SIZE_BUTTON_SMALL = 30

# Spacing presets
SPACING_SECTION = 2
SPACING_ELEMENT = 1
