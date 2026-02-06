"""
ImGui UI Helpers - utilities for consistent, auto-scaling UI.

Provides functions for proper sizing, centering, and styling.
"""

import imgui


class UIHelpers:
    """Helper functions for ImGui UI."""

    @staticmethod
    def get_window_center():
        """Get center position of current window."""
        width = imgui.get_window_width()
        height = imgui.get_window_height()
        return width / 2, height / 2

    @staticmethod
    def get_content_width():
        """Get available content width."""
        return imgui.get_content_region_available_width()

    @staticmethod
    def center_text(text):
        """Center text horizontally."""
        text_width = imgui.calc_text_size(text)[0]
        window_width = imgui.get_window_width()
        imgui.set_cursor_pos_x((window_width - text_width) / 2)
        imgui.text(text)

    @staticmethod
    def centered_button(label, width_percent=0.8, height=40):
        """
        Create centered button with percentage width.

        Args:
            label: Button text
            width_percent: Width as percentage of available space (0.0-1.0)
            height: Button height in pixels

        Returns:
            True if clicked
        """
        available_width = imgui.get_content_region_available_width()
        button_width = available_width * width_percent

        # Calculate text size to ensure it fits
        text_width = imgui.calc_text_size(label)[0]
        if text_width + 20 > button_width:  # 20px padding
            button_width = text_width + 20

        # Center the button
        imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + (available_width - button_width) / 2)

        return imgui.button(label, button_width, height)

    @staticmethod
    def full_width_button(label, height=40):
        """Create button that fills available width."""
        width = imgui.get_content_region_available_width()
        return imgui.button(label, width, height)

    @staticmethod
    def labeled_input(label, value, max_length=256, width_percent=1.0):
        """
        Create labeled input field with proper sizing.

        Args:
            label: Label text
            value: Current value
            max_length: Max input length
            width_percent: Width as percentage of available space

        Returns:
            (changed, new_value)
        """
        imgui.text(label)

        available_width = imgui.get_content_region_available_width()
        input_width = available_width * width_percent

        imgui.push_item_width(input_width)
        changed, new_value = imgui.input_text(f"##{label}", value, max_length)
        imgui.pop_item_width()

        return changed, new_value

    @staticmethod
    def labeled_input_password(label, value, max_length=256, width_percent=1.0):
        """Create labeled password input field."""
        imgui.text(label)

        available_width = imgui.get_content_region_available_width()
        input_width = available_width * width_percent

        imgui.push_item_width(input_width)
        changed, new_value = imgui.input_text(
            f"##{label}", value, max_length,
            imgui.INPUT_TEXT_PASSWORD
        )
        imgui.pop_item_width()

        return changed, new_value

    @staticmethod
    def labeled_slider_int(label, value, min_val, max_val, width_percent=0.7):
        """Create labeled integer slider."""
        # Split into label and slider columns
        imgui.columns(2, f"##{label}_cols", False)
        imgui.set_column_width(0, imgui.get_window_width() * 0.3)

        imgui.text(label)
        imgui.next_column()

        available_width = imgui.get_content_region_available_width()
        imgui.push_item_width(available_width * width_percent)
        changed, new_value = imgui.slider_int(f"##{label}_slider", value, min_val, max_val)
        imgui.pop_item_width()

        imgui.columns(1)

        return changed, new_value

    @staticmethod
    def labeled_checkbox(label, value):
        """Create labeled checkbox."""
        changed, new_value = imgui.checkbox(label, value)
        return changed, new_value

    @staticmethod
    def spacing(multiplier=1):
        """Add spacing (multiplier of default spacing)."""
        for _ in range(multiplier):
            imgui.spacing()

    @staticmethod
    def separator():
        """Add separator line."""
        imgui.spacing()
        imgui.separator()
        imgui.spacing()

    @staticmethod
    def section_header(text):
        """Create section header text."""
        imgui.spacing()
        imgui.text(text)
        imgui.separator()
        imgui.spacing()

    @staticmethod
    def centered_window(title, width_percent=0.4, height_percent=0.5, flags=0):
        """
        Begin centered window with percentage size.

        Args:
            title: Window title
            width_percent: Width as percentage of screen (0.0-1.0)
            height_percent: Height as percentage of screen (0.0-1.0)
            flags: ImGui window flags

        Returns:
            True if window is visible
        """
        io = imgui.get_io()
        display_width = io.display_size[0]
        display_height = io.display_size[1]

        window_width = display_width * width_percent
        window_height = display_height * height_percent

        window_x = (display_width - window_width) / 2
        window_y = (display_height - window_height) / 2

        imgui.set_next_window_position(window_x, window_y, imgui.ONCE)
        imgui.set_next_window_size(window_width, window_height, imgui.ONCE)

        return imgui.begin(title, True, flags)

    @staticmethod
    def two_column_layout(left_width_percent=0.3):
        """
        Setup two-column layout.

        Args:
            left_width_percent: Width of left column as percentage
        """
        imgui.columns(2, "two_columns", False)
        window_width = imgui.get_window_width()
        imgui.set_column_width(0, window_width * left_width_percent)

    @staticmethod
    def end_columns():
        """End column layout."""
        imgui.columns(1)


# Preset window flags
WINDOW_FLAGS_MENU = (
    imgui.WINDOW_NO_COLLAPSE |
    imgui.WINDOW_NO_RESIZE |
    imgui.WINDOW_NO_MOVE
)

WINDOW_FLAGS_RESIZABLE = (
    imgui.WINDOW_NO_COLLAPSE
)

# Preset sizes
SIZE_BUTTON_LARGE = 50
SIZE_BUTTON_MEDIUM = 40
SIZE_BUTTON_SMALL = 30

# Spacing presets
SPACING_SECTION = 2
SPACING_ELEMENT = 1
