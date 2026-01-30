# nine/ui/theme.py
"""
UI Theme - Backwards compatible wrapper around UIConfig.

For new code, use `from nine.ui.ui_config import ui` directly.
This module provides NineTheme for compatibility with existing code.
"""

from .ui_config import ui, UI_SCALE


class NineTheme:
    """
    Theme constants for niNE UI (Baldur's Gate 1 style).

    This class wraps UIConfig for backwards compatibility.
    New code should use `ui` from ui_config directly.
    """

    # Font path
    FONT_PATH = "nine/assets/fonts/PressStart2P.ttf"
    FONT_PIXELS_PER_UNIT = 96  # Higher resolution for crisp pixel font rendering
    FONT_USE_NEAREST = True    # Use nearest-neighbor filtering for pixel fonts

    # ==========================================================================
    # Colors (direct references to UIConfig)
    # ==========================================================================

    @property
    def BG_DARK(self):
        return ui.colors.bg_dark

    @property
    def BG_MEDIUM(self):
        return ui.colors.bg_medium

    @property
    def BG_LIGHT(self):
        return ui.colors.bg_light

    @property
    def BG_OVERLAY(self):
        return ui.colors.bg_overlay

    @property
    def TEXT_PRIMARY(self):
        return ui.colors.text_primary

    @property
    def TEXT_SECONDARY(self):
        return ui.colors.text_secondary

    @property
    def TEXT_HINT(self):
        return ui.colors.text_hint

    @property
    def TEXT_HIGHLIGHT(self):
        return ui.colors.text_highlight

    @property
    def BTN_NORMAL(self):
        return ui.colors.btn_normal

    @property
    def BTN_HOVER(self):
        return ui.colors.btn_hover

    @property
    def BTN_CLICK(self):
        return ui.colors.btn_click

    @property
    def BTN_ACCENT_NORMAL(self):
        return ui.colors.btn_accent_normal

    @property
    def BTN_ACCENT_HOVER(self):
        return ui.colors.btn_accent_hover

    @property
    def BTN_ACCENT_CLICK(self):
        return ui.colors.btn_accent_click

    @property
    def ENTRY_BG(self):
        return ui.colors.entry_bg

    # ==========================================================================
    # Font Scales (using UIConfig with scaling)
    # ==========================================================================

    @property
    def TITLE_SCALE(self):
        return ui.font.title

    @property
    def LABEL_SCALE(self):
        return ui.font.label

    @property
    def ENTRY_SCALE(self):
        return ui.font.entry

    @property
    def BUTTON_SCALE(self):
        return ui.button.scale

    @property
    def MENU_ITEM_SCALE(self):
        return ui.button.menu_scale

    @property
    def SMALL_SCALE(self):
        return ui.font.small

    # ==========================================================================
    # Static color tuples for backwards compatibility
    # ==========================================================================

    @staticmethod
    def button_colors():
        """Returns (normal, hover, click, disabled) colors for buttons."""
        return ui.button_colors()

    @staticmethod
    def accent_button_colors():
        """Returns (normal, hover, click, disabled) colors for accent buttons."""
        return ui.accent_button_colors()


# Create a singleton instance for attribute access
_theme_instance = NineTheme()


# Make class attributes work as both class and instance attributes
class NineThemeMeta(type):
    """Metaclass to allow NineTheme.ATTR syntax."""

    def __getattr__(cls, name):
        return getattr(_theme_instance, name)


class NineTheme(metaclass=NineThemeMeta):
    """
    Theme constants for niNE UI (Baldur's Gate 1 style).

    Access colors and scales as class attributes:
        NineTheme.BG_DARK
        NineTheme.TITLE_SCALE
        NineTheme.button_colors()
    """

    FONT_PATH = "nine/assets/fonts/PressStart2P.ttf"
    FONT_PIXELS_PER_UNIT = 96
    FONT_USE_NEAREST = True

    # Static color values for direct access
    BG_DARK = ui.colors.bg_dark
    BG_MEDIUM = ui.colors.bg_medium
    BG_LIGHT = ui.colors.bg_light
    BG_OVERLAY = ui.colors.bg_overlay

    TEXT_PRIMARY = ui.colors.text_primary
    TEXT_SECONDARY = ui.colors.text_secondary
    TEXT_HINT = ui.colors.text_hint
    TEXT_HIGHLIGHT = ui.colors.text_highlight

    BTN_NORMAL = ui.colors.btn_normal
    BTN_HOVER = ui.colors.btn_hover
    BTN_CLICK = ui.colors.btn_click

    BTN_ACCENT_NORMAL = ui.colors.btn_accent_normal
    BTN_ACCENT_HOVER = ui.colors.btn_accent_hover
    BTN_ACCENT_CLICK = ui.colors.btn_accent_click

    ENTRY_BG = ui.colors.entry_bg

    # Dynamic scales (these are properties that read from UIConfig)
    @staticmethod
    def get_title_scale():
        return ui.font.title

    @staticmethod
    def get_label_scale():
        return ui.font.label

    @staticmethod
    def get_entry_scale():
        return ui.font.entry

    @staticmethod
    def get_button_scale():
        return ui.button.scale

    @staticmethod
    def get_menu_item_scale():
        return ui.button.menu_scale

    @staticmethod
    def get_small_scale():
        return ui.font.small

    # For backwards compatibility - these will be evaluated at import time
    # To get dynamic values, use the get_* methods or ui.* directly
    TITLE_SCALE = ui.font.title
    LABEL_SCALE = ui.font.label
    ENTRY_SCALE = ui.font.entry
    BUTTON_SCALE = ui.button.scale
    MENU_ITEM_SCALE = ui.button.menu_scale
    SMALL_SCALE = ui.font.small

    @staticmethod
    def button_colors():
        """Returns (normal, hover, click, disabled) colors for buttons."""
        return ui.button_colors()

    @staticmethod
    def accent_button_colors():
        """Returns (normal, hover, click, disabled) colors for accent buttons."""
        return ui.accent_button_colors()
