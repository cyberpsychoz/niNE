# nine/ui/ui_config.py
"""
Unified UI Configuration System.

Centralizes all UI sizing, spacing, and layout parameters.
Change UI_SCALE to resize the entire interface proportionally.

Usage:
    from nine.ui.ui_config import ui

    # Get scaled values
    title_scale = ui.font.title        # 0.16 at scale 1.0
    button_height = ui.button.height   # 0.12 at scale 1.0
    panel_padding = ui.spacing.panel   # 0.04 at scale 1.0
"""

from dataclasses import dataclass
from typing import Tuple


# =============================================================================
# Global Scale Multiplier
# =============================================================================
# Change this to resize ALL UI elements proportionally
# 1.0 = default size, 1.5 = 50% larger, 0.75 = 25% smaller
UI_SCALE = 0.8


# =============================================================================
# Color Definitions (RGBA tuples)
# =============================================================================
@dataclass(frozen=True)
class UIColors:
    """UI color palette - Baldur's Gate 1 warm brown style."""

    # Backgrounds
    bg_dark: Tuple[float, ...] = (0.08, 0.06, 0.04, 1.0)
    bg_medium: Tuple[float, ...] = (0.15, 0.11, 0.08, 0.95)
    bg_light: Tuple[float, ...] = (0.22, 0.16, 0.12, 1.0)
    bg_overlay: Tuple[float, ...] = (0.05, 0.03, 0.02, 0.8)

    # Text
    text_primary: Tuple[float, ...] = (0.95, 0.88, 0.70, 1.0)
    text_secondary: Tuple[float, ...] = (0.75, 0.65, 0.50, 1.0)
    text_hint: Tuple[float, ...] = (0.55, 0.48, 0.38, 1.0)
    text_highlight: Tuple[float, ...] = (1.0, 0.92, 0.65, 1.0)

    # Buttons
    btn_normal: Tuple[float, ...] = (0.25, 0.18, 0.12, 1.0)
    btn_hover: Tuple[float, ...] = (0.35, 0.26, 0.18, 1.0)
    btn_click: Tuple[float, ...] = (0.18, 0.12, 0.08, 1.0)

    # Accent buttons
    btn_accent_normal: Tuple[float, ...] = (0.45, 0.30, 0.15, 1.0)
    btn_accent_hover: Tuple[float, ...] = (0.55, 0.38, 0.20, 1.0)
    btn_accent_click: Tuple[float, ...] = (0.35, 0.22, 0.10, 1.0)

    # Entry fields
    entry_bg: Tuple[float, ...] = (0.10, 0.07, 0.05, 1.0)

    # Special
    gold: Tuple[float, ...] = (0.9, 0.8, 0.5, 1.0)
    error: Tuple[float, ...] = (0.9, 0.3, 0.3, 1.0)
    success: Tuple[float, ...] = (0.3, 0.9, 0.3, 1.0)


# =============================================================================
# Scaled Value Classes
# =============================================================================
class ScaledValue:
    """A value that scales with UI_SCALE."""

    def __init__(self, base_value: float):
        self._base = base_value

    @property
    def value(self) -> float:
        return self._base * UI_SCALE

    def __float__(self) -> float:
        return self.value

    def __mul__(self, other) -> float:
        return self.value * other

    def __rmul__(self, other) -> float:
        return other * self.value

    def __add__(self, other) -> float:
        return self.value + other

    def __radd__(self, other) -> float:
        return other + self.value

    def __sub__(self, other) -> float:
        return self.value - other

    def __neg__(self) -> float:
        return -self.value

    def __repr__(self) -> str:
        return f"{self.value:.3f}"


def scaled(base: float) -> ScaledValue:
    """Create a scaled value."""
    return ScaledValue(base)


# =============================================================================
# Font Sizes
# =============================================================================
@dataclass
class FontConfig:
    """Font size configuration."""

    # Base sizes (will be multiplied by UI_SCALE)
    _title: float = 0.16
    _subtitle: float = 0.10
    _heading: float = 0.08
    _label: float = 0.07
    _body: float = 0.06
    _small: float = 0.05
    _tiny: float = 0.04

    # Entry field text
    _entry: float = 0.07

    @property
    def title(self) -> float:
        return self._title * UI_SCALE

    @property
    def subtitle(self) -> float:
        return self._subtitle * UI_SCALE

    @property
    def heading(self) -> float:
        return self._heading * UI_SCALE

    @property
    def label(self) -> float:
        return self._label * UI_SCALE

    @property
    def body(self) -> float:
        return self._body * UI_SCALE

    @property
    def small(self) -> float:
        return self._small * UI_SCALE

    @property
    def tiny(self) -> float:
        return self._tiny * UI_SCALE

    @property
    def entry(self) -> float:
        return self._entry * UI_SCALE


# =============================================================================
# Spacing & Padding
# =============================================================================
@dataclass
class SpacingConfig:
    """Spacing and padding configuration."""

    # Base values
    _xs: float = 0.01    # Extra small
    _sm: float = 0.02    # Small
    _md: float = 0.04    # Medium
    _lg: float = 0.06    # Large
    _xl: float = 0.10    # Extra large

    # Specific use cases
    _button_gap: float = 0.04      # Gap between buttons
    _row_height: float = 0.08      # Height of a row in lists/settings
    _panel_padding: float = 0.05   # Padding inside panels
    _section_gap: float = 0.08     # Gap between sections

    @property
    def xs(self) -> float:
        return self._xs * UI_SCALE

    @property
    def sm(self) -> float:
        return self._sm * UI_SCALE

    @property
    def md(self) -> float:
        return self._md * UI_SCALE

    @property
    def lg(self) -> float:
        return self._lg * UI_SCALE

    @property
    def xl(self) -> float:
        return self._xl * UI_SCALE

    @property
    def button_gap(self) -> float:
        return self._button_gap * UI_SCALE

    @property
    def row_height(self) -> float:
        return self._row_height * UI_SCALE

    @property
    def panel_padding(self) -> float:
        return self._panel_padding * UI_SCALE

    @property
    def section_gap(self) -> float:
        return self._section_gap * UI_SCALE


# =============================================================================
# Button Configuration
# =============================================================================
@dataclass
class ButtonConfig:
    """Button size configuration."""

    # BG1 Button (main style)
    _scale: float = 0.09           # DirectButton scale
    _width: float = 6.2            # Frame width (in button units)
    _height: float = 1.2           # Frame height (in button units)
    _text_offset_y: float = -0.3   # Vertical text offset for centering

    # Small button variant
    _small_scale: float = 0.07
    _small_width: float = 5.17
    _small_height: float = 1.0

    # Large button variant
    _large_scale: float = 0.11
    _large_width: float = 6.2
    _large_height: float = 1.2

    # Menu button (text-only style)
    _menu_scale: float = 0.10

    # Button spacing in rows
    _spacing: float = 0.30

    @property
    def scale(self) -> float:
        return self._scale * UI_SCALE

    @property
    def width(self) -> float:
        return self._width  # Not scaled - it's relative to button scale

    @property
    def height(self) -> float:
        return self._height  # Not scaled

    @property
    def text_offset_y(self) -> float:
        return self._text_offset_y  # Not scaled

    @property
    def small_scale(self) -> float:
        return self._small_scale * UI_SCALE

    @property
    def small_width(self) -> float:
        return self._small_width

    @property
    def small_height(self) -> float:
        return self._small_height

    @property
    def large_scale(self) -> float:
        return self._large_scale * UI_SCALE

    @property
    def menu_scale(self) -> float:
        return self._menu_scale * UI_SCALE

    @property
    def spacing(self) -> float:
        return self._spacing * UI_SCALE


# =============================================================================
# Panel Configuration
# =============================================================================
@dataclass
class PanelConfig:
    """Panel and window size configuration."""

    # Login menu panel
    _login_width: float = 1.4
    _login_height: float = 1.2

    # Settings menu panel
    _settings_width: float = 2.2
    _settings_height: float = 1.6

    # In-game menu panel
    _ingame_width: float = 1.0
    _ingame_height: float = 0.9

    # Character sheet
    _charsheet_width: float = 2.0
    _charsheet_height: float = 1.5

    @property
    def login_width(self) -> float:
        return self._login_width * UI_SCALE

    @property
    def login_height(self) -> float:
        return self._login_height * UI_SCALE

    @property
    def settings_width(self) -> float:
        return self._settings_width * UI_SCALE

    @property
    def settings_height(self) -> float:
        return self._settings_height * UI_SCALE

    @property
    def ingame_width(self) -> float:
        return self._ingame_width * UI_SCALE

    @property
    def ingame_height(self) -> float:
        return self._ingame_height * UI_SCALE

    @property
    def charsheet_width(self) -> float:
        return self._charsheet_width * UI_SCALE

    @property
    def charsheet_height(self) -> float:
        return self._charsheet_height * UI_SCALE


# =============================================================================
# HUD Configuration
# =============================================================================
@dataclass
class HUDConfig:
    """HUD element configuration."""

    # Health bar
    _hp_bar_width: float = 0.35
    _hp_bar_height: float = 0.03

    # Text sizes
    _name_scale: float = 0.06
    _stat_scale: float = 0.05
    _value_scale: float = 0.055

    # Position (from edge)
    _margin_x: float = 0.15
    _margin_y: float = 0.12

    @property
    def hp_bar_width(self) -> float:
        return self._hp_bar_width * UI_SCALE

    @property
    def hp_bar_height(self) -> float:
        return self._hp_bar_height * UI_SCALE

    @property
    def name_scale(self) -> float:
        return self._name_scale * UI_SCALE

    @property
    def stat_scale(self) -> float:
        return self._stat_scale * UI_SCALE

    @property
    def value_scale(self) -> float:
        return self._value_scale * UI_SCALE

    @property
    def margin_x(self) -> float:
        return self._margin_x * UI_SCALE

    @property
    def margin_y(self) -> float:
        return self._margin_y * UI_SCALE


# =============================================================================
# Main UI Config Class
# =============================================================================
class UIConfig:
    """
    Main UI configuration container.

    Access all UI parameters through this class:
        ui.font.title
        ui.spacing.md
        ui.button.scale
        ui.panel.login_width
        ui.colors.text_primary
    """

    def __init__(self):
        self.font = FontConfig()
        self.spacing = SpacingConfig()
        self.button = ButtonConfig()
        self.panel = PanelConfig()
        self.hud = HUDConfig()
        self.colors = UIColors()

    @property
    def scale(self) -> float:
        """Current global UI scale."""
        return UI_SCALE

    @staticmethod
    def set_scale(new_scale: float):
        """
        Set the global UI scale.

        Args:
            new_scale: Scale multiplier (1.0 = default, 1.5 = 50% larger)
        """
        global UI_SCALE
        UI_SCALE = max(0.5, min(2.0, new_scale))  # Clamp between 0.5 and 2.0

    # Convenience methods for common color tuples
    def button_colors(self) -> tuple:
        """Returns (normal, hover, click, disabled) colors for buttons."""
        return (
            self.colors.btn_normal,
            self.colors.btn_hover,
            self.colors.btn_click,
            self.colors.btn_normal,
        )

    def accent_button_colors(self) -> tuple:
        """Returns (normal, hover, click, disabled) colors for accent buttons."""
        return (
            self.colors.btn_accent_normal,
            self.colors.btn_accent_hover,
            self.colors.btn_accent_click,
            self.colors.btn_accent_normal,
        )


# =============================================================================
# Global Instance
# =============================================================================
# Use this instance throughout the codebase
ui = UIConfig()


# =============================================================================
# Helper Functions
# =============================================================================
def get_ui_scale() -> float:
    """Get current UI scale."""
    return UI_SCALE


def set_ui_scale(scale: float):
    """Set UI scale (0.5 to 2.0)."""
    ui.set_scale(scale)
