# nine/ui/base_component.py
"""
Base UI Component with sound support.

Все UI компоненты наследуются от BaseUIComponent,
который предоставляет:
- Управление элементами DirectGUI
- Автоматическую очистку при destroy()
- Звуковую систему UI (hover, click)
- Хелперы для создания кнопок с звуками
"""

from panda3d.core import NodePath
from direct.gui.DirectGui import DirectButton, DGG

from .theme import NineTheme
from .bg1_button import BG1Button, BG1ButtonSmall, BG1Panel
from nine.core.config import config


class BaseUIComponent:
    """
    Базовый класс для всех компонентов пользовательского интерфейса.
    Предоставляет общие методы для управления элементами DirectGUI.
    """

    def __init__(self, ui_manager):
        self.ui_manager = ui_manager
        self.base = ui_manager.base
        self._elements = {}

        # Кешируем AudioManager для быстрого доступа
        self._audio = getattr(self.base, 'audio_manager', None)

    @property
    def _ui_sounds_enabled(self) -> bool:
        """Проверяет включены ли звуки UI из конфига."""
        return config.get("ui_sounds_enabled", True)

    # =========================================================================
    # Управление элементами
    # =========================================================================

    def show(self):
        """Показывает корневой элемент компонента."""
        if 'root' in self._elements:
            self._elements['root'].show()

    def hide(self):
        """Скрывает корневой элемент компонента."""
        if 'root' in self._elements:
            self._elements['root'].hide()

    def destroy(self):
        """Уничтожает все элементы DirectGUI, управляемые этим компонентом."""
        for name, element in list(self._elements.items()):
            if hasattr(element, 'destroy') and callable(element.destroy):
                element.destroy()
            elif isinstance(element, NodePath):
                element.removeNode()
        self._elements.clear()

    def _add_element(self, name, element):
        """Отслеживает элемент для автоматического уничтожения."""
        self._elements[name] = element
        return element

    # =========================================================================
    # Звуки UI
    # =========================================================================

    def _play_hover_sound(self):
        """Воспроизводит звук наведения."""
        if self._ui_sounds_enabled and self._audio:
            self._audio.play_ui_hover()

    def _play_click_sound(self):
        """Воспроизводит звук клика."""
        if self._ui_sounds_enabled and self._audio:
            self._audio.play_ui_click()

    def _play_confirm_sound(self):
        """Воспроизводит звук подтверждения."""
        if self._ui_sounds_enabled and self._audio:
            self._audio.play_ui_confirm()

    def _play_cancel_sound(self):
        """Воспроизводит звук отмены."""
        if self._ui_sounds_enabled and self._audio:
            self._audio.play_ui_cancel()

    def _play_open_sound(self):
        """Воспроизводит звук открытия."""
        if self._ui_sounds_enabled and self._audio:
            self._audio.play_ui_open()

    def _play_close_sound(self):
        """Воспроизводит звук закрытия."""
        if self._ui_sounds_enabled and self._audio:
            self._audio.play_ui_close()

    def _play_error_sound(self):
        """Воспроизводит звук ошибки."""
        if self._ui_sounds_enabled and self._audio:
            self._audio.play_ui_error()

    def _play_success_sound(self):
        """Воспроизводит звук успеха."""
        if self._ui_sounds_enabled and self._audio:
            self._audio.play_ui_success()

    # =========================================================================
    # Создание кнопок с звуками
    # =========================================================================

    def _create_button(self, name: str, text: str, command=None,
                       parent=None, pos=(0, 0, 0), scale=None,
                       accent: bool = False, text_align=None,
                       hover_sound: bool = True, click_sound: bool = True,
                       **kwargs) -> DirectButton:
        """
        Создает кнопку с автоматическими звуками и стилизацией.

        Args:
            name: Уникальное имя элемента
            text: Текст кнопки
            command: Функция при нажатии
            parent: Родительский узел
            pos: Позиция (x, y, z)
            scale: Масштаб
            accent: True для акцентной кнопки (оранжевой)
            text_align: Выравнивание текста (0=left, 1=right, 2=center)
            hover_sound: Воспроизводить звук при наведении
            click_sound: Воспроизводить звук при клике
            **kwargs: Дополнительные параметры DirectButton

        Returns:
            DirectButton объект
        """
        if parent is None:
            parent = self.base.aspect2d

        if scale is None:
            scale = NineTheme.BUTTON_SCALE

        # Выбираем цвета
        if accent:
            colors = NineTheme.accent_button_colors()
            text_fg = NineTheme.TEXT_PRIMARY
        else:
            colors = NineTheme.button_colors()
            text_fg = NineTheme.TEXT_PRIMARY

        # Обёртка команды для звука клика
        def command_with_sound():
            if click_sound:
                self._play_click_sound()
            if command:
                command()

        # Создаём кнопку
        btn = DirectButton(
            parent=parent,
            text=text,
            text_font=self.ui_manager.font,
            scale=scale,
            pos=pos,
            command=command_with_sound,
            text_fg=text_fg,
            frameColor=colors[0],  # normal
            **kwargs
        )

        # Привязываем события hover
        if hover_sound:
            btn.bind(DGG.ENTER, self._on_btn_enter_with_sound, [btn, colors])
        else:
            btn.bind(DGG.ENTER, self._on_btn_enter, [btn, colors])
        btn.bind(DGG.EXIT, self._on_btn_exit, [btn, colors])

        # Сохраняем для очистки
        self._add_element(name, btn)

        return btn

    def _create_menu_button(self, name: str, text: str, command=None,
                            parent=None, pos=(0, 0, 0),
                            hover_sound: bool = True, click_sound: bool = True,
                            **kwargs) -> DirectButton:
        """
        Создает текстовую кнопку меню в стиле Source Engine.

        Args:
            name: Уникальное имя элемента
            text: Текст кнопки
            command: Функция при нажатии
            parent: Родительский узел
            pos: Позиция (x, y, z)
            hover_sound: Воспроизводить звук при наведении
            click_sound: Воспроизводить звук при клике
            **kwargs: Дополнительные параметры DirectButton

        Returns:
            DirectButton объект
        """
        if parent is None:
            parent = self.base.aspect2d

        # Обёртка команды для звука клика
        def command_with_sound():
            if click_sound:
                self._play_click_sound()
            if command:
                command()

        btn = DirectButton(
            parent=parent,
            text=text,
            text_font=self.ui_manager.font,
            scale=NineTheme.MENU_ITEM_SCALE,
            pos=pos,
            command=command_with_sound,
            text_align=0,  # Left align
            text_fg=NineTheme.TEXT_SECONDARY,
            text_shadow=(0, 0, 0, 0.9),
            text_shadowOffset=(0.04, 0.04),
            frameColor=(0, 0, 0, 0),
            relief=None,
            pressEffect=False,
            **kwargs
        )

        # Привязываем события hover
        if hover_sound:
            btn.bind(DGG.ENTER, self._on_menu_btn_enter_with_sound, [btn])
        else:
            btn.bind(DGG.ENTER, self._on_menu_btn_enter, [btn])
        btn.bind(DGG.EXIT, self._on_menu_btn_exit, [btn])

        self._add_element(name, btn)
        return btn

    # =========================================================================
    # Обработчики событий кнопок
    # =========================================================================

    def _on_btn_enter_with_sound(self, btn, colors, event):
        """Hover с звуком для обычной кнопки."""
        self._play_hover_sound()
        btn['frameColor'] = colors[1]  # hover color

    def _on_btn_enter(self, btn, colors, event):
        """Hover без звука для обычной кнопки."""
        btn['frameColor'] = colors[1]  # hover color

    def _on_btn_exit(self, btn, colors, event):
        """Exit hover для обычной кнопки."""
        btn['frameColor'] = colors[0]  # normal color

    def _on_menu_btn_enter_with_sound(self, btn, event):
        """Hover с звуком для кнопки меню."""
        self._play_hover_sound()
        btn['text_fg'] = NineTheme.TEXT_HIGHLIGHT

    def _on_menu_btn_enter(self, btn, event):
        """Hover без звука для кнопки меню."""
        btn['text_fg'] = NineTheme.TEXT_HIGHLIGHT

    def _on_menu_btn_exit(self, btn, event):
        """Exit hover для кнопки меню."""
        btn['text_fg'] = NineTheme.TEXT_SECONDARY

    # =========================================================================
    # BG1 Style кнопки
    # =========================================================================

    def _create_bg1_button(self, name: str, text: str, command=None,
                           parent=None, pos=(0, 0, 0), small: bool = False,
                           click_sound: bool = True) -> DirectButton:
        """
        Создает кнопку в стиле Baldur's Gate 1.

        Args:
            name: Уникальное имя элемента
            text: Текст кнопки
            command: Функция при нажатии
            parent: Родительский узел
            pos: Позиция (x, y, z)
            small: Использовать маленькую кнопку
            click_sound: Воспроизводить звук при клике

        Returns:
            DirectButton объект
        """
        if parent is None:
            parent = self.base.aspect2d

        # Обёртка команды для звука клика
        def command_with_sound():
            if click_sound:
                self._play_click_sound()
            if command:
                command()

        # Создаём кнопку через BG1Button
        ButtonClass = BG1ButtonSmall if small else BG1Button
        btn = ButtonClass.create(
            parent=parent,
            text=text,
            command=command_with_sound,
            pos=pos,
            font=self.ui_manager.font,
            sound_callback=self._play_hover_sound if self._ui_sounds_enabled else None,
        )

        self._add_element(name, btn)
        return btn
