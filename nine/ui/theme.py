"""
UI Theme constants and helper functions.
Defines colors, scales, and styling for all UI components.
"""


class NineTheme:
    """Константы темы UI для niNE."""

    # Путь к шрифту (Exo 2 - технологичный/футуристический, с кириллицей)
    FONT_PATH = "nine/assets/fonts/Exo2.ttf"
    FONT_PIXELS_PER_UNIT = 60  # Выше для чёткости

    # Цвета фона (RGBA)
    BG_DARK = (0.05, 0.05, 0.08, 1.0)
    BG_MEDIUM = (0.1, 0.1, 0.15, 0.95)
    BG_LIGHT = (0.15, 0.15, 0.2, 1.0)
    BG_OVERLAY = (0.0, 0.0, 0.0, 0.7)

    # Цвета текста
    TEXT_PRIMARY = (0.9, 0.9, 0.95, 1.0)
    TEXT_SECONDARY = (0.6, 0.6, 0.7, 1.0)
    TEXT_HINT = (0.4, 0.4, 0.5, 1.0)
    TEXT_HIGHLIGHT = (0.3, 0.8, 1.0, 1.0)  # Синий акцент

    # Цвета кнопок
    BTN_NORMAL = (0.2, 0.2, 0.3, 1.0)
    BTN_HOVER = (0.3, 0.3, 0.4, 1.0)
    BTN_CLICK = (0.15, 0.15, 0.25, 1.0)

    # Цвет акцентных кнопок
    BTN_ACCENT_NORMAL = (0.2, 0.5, 0.8, 1.0)
    BTN_ACCENT_HOVER = (0.3, 0.6, 0.9, 1.0)
    BTN_ACCENT_CLICK = (0.15, 0.4, 0.7, 1.0)

    # Фон полей ввода
    ENTRY_BG = (0.08, 0.08, 0.12, 1.0)

    # Размеры шрифтов/элементов
    TITLE_SCALE = 0.08
    LABEL_SCALE = 0.04
    ENTRY_SCALE = 0.045
    BUTTON_SCALE = 0.05
    MENU_ITEM_SCALE = 0.06
    SMALL_SCALE = 0.03

    @staticmethod
    def button_colors():
        """Возвращает кортеж цветов для обычной кнопки (normal, hover, click, disabled)."""
        return (
            NineTheme.BTN_NORMAL,
            NineTheme.BTN_HOVER,
            NineTheme.BTN_CLICK,
            NineTheme.BTN_NORMAL
        )

    @staticmethod
    def accent_button_colors():
        """Возвращает кортеж цветов для акцентной кнопки (normal, hover, click, disabled)."""
        return (
            NineTheme.BTN_ACCENT_NORMAL,
            NineTheme.BTN_ACCENT_HOVER,
            NineTheme.BTN_ACCENT_CLICK,
            NineTheme.BTN_ACCENT_NORMAL
        )