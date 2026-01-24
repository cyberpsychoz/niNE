"""
Loading Screen - экран загрузки с прогрессом и статусом.
"""

from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectWaitBar, DGG
from panda3d.core import TextNode, TransparencyAttrib

from .base_component import BaseUIComponent
from .theme import NineTheme
from .ui_config import ui


class LoadingScreen(BaseUIComponent):
    """
    Экран загрузки с индикатором прогресса.

    Использование:
        loading = LoadingScreen(ui_manager)
        loading.show()
        loading.set_status("Загрузка карты...")
        loading.set_progress(0.5)  # 50%
        loading.hide()
    """

    def __init__(self, ui_manager, title: str = "ЗАГРУЗКА"):
        super().__init__(ui_manager)
        self.title_text = title
        self._create_ui()

    def _create_ui(self):
        """Создаёт UI элементы."""
        # Тёмный фон на весь экран
        self._add_element('background', DirectFrame(
            parent=self.base.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=(0.02, 0.02, 0.03, 1.0),
        ))

        # Центральная панель
        panel_width = 1.0
        panel_height = 0.4
        panel = self._add_element('panel', DirectFrame(
            parent=self.base.aspect2d,
            frameSize=(-panel_width/2, panel_width/2, -panel_height/2, panel_height/2),
            frameColor=(0.08, 0.06, 0.04, 0.95),
            pos=(0, 0, 0),
        ))
        panel.setTransparency(TransparencyAttrib.M_alpha)

        # Заголовок
        self._add_element('title', DirectLabel(
            parent=panel,
            text=self.title_text,
            scale=ui.font.subtitle,
            pos=(0, 0, 0.1),
            text_fg=NineTheme.TEXT_HIGHLIGHT,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        ))

        # Статус текст
        self._add_element('status', DirectLabel(
            parent=panel,
            text="",
            scale=ui.font.small,
            pos=(0, 0, 0.02),
            text_fg=NineTheme.TEXT_SECONDARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        ))

        # Прогресс бар
        bar_width = 0.7
        bar_height = 0.03
        self._add_element('progress_bar', DirectWaitBar(
            parent=panel,
            range=100,
            value=0,
            pos=(0, 0, -0.08),
            frameSize=(-bar_width/2, bar_width/2, -bar_height/2, bar_height/2),
            frameColor=NineTheme.BG_DARK,
            barColor=(0.6, 0.45, 0.2, 1.0),  # Золотистый
            relief=DGG.FLAT,
        ))

        # Подсказка внизу
        self._add_element('hint', DirectLabel(
            parent=panel,
            text="",
            scale=ui.font.tiny,
            pos=(0, 0, -0.15),
            text_fg=NineTheme.TEXT_HINT,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        ))

    def set_title(self, title: str):
        """Устанавливает заголовок."""
        if 'title' in self._elements:
            self._elements['title']['text'] = title

    def set_status(self, status: str):
        """Устанавливает текст статуса."""
        if 'status' in self._elements:
            self._elements['status']['text'] = status

    def set_progress(self, progress: float):
        """
        Устанавливает прогресс (0.0 - 1.0).

        Args:
            progress: Значение от 0.0 до 1.0
        """
        if 'progress_bar' in self._elements:
            self._elements['progress_bar']['value'] = int(progress * 100)

    def set_hint(self, hint: str):
        """Устанавливает текст подсказки."""
        if 'hint' in self._elements:
            self._elements['hint']['text'] = hint

    def show(self):
        """Показывает экран загрузки."""
        for element in self._elements.values():
            element.show()

    def hide(self):
        """Скрывает экран загрузки."""
        for element in self._elements.values():
            element.hide()


class ConnectionScreen(LoadingScreen):
    """Экран подключения к серверу."""

    def __init__(self, ui_manager):
        super().__init__(ui_manager, title="ПОДКЛЮЧЕНИЕ")
        self.set_hint("Подключение к серверу...")
        self._dots = 0
        self._animate_task = None

    def show(self):
        super().show()
        # Запускаем анимацию точек
        self._animate_task = self.base.taskMgr.doMethodLater(
            0.5, self._animate_dots, "loading-dots"
        )

    def hide(self):
        super().hide()
        if self._animate_task:
            self.base.taskMgr.remove("loading-dots")
            self._animate_task = None

    def _animate_dots(self, task):
        """Анимация точек в статусе."""
        self._dots = (self._dots + 1) % 4
        dots = "." * self._dots
        current = self._elements.get('status')
        if current:
            base_text = current['text'].rstrip('.')
            if not base_text:
                base_text = "Подключение"
            self._elements['status']['text'] = base_text + dots
        return task.again


class MapLoadingScreen(LoadingScreen):
    """Экран загрузки карты."""

    def __init__(self, ui_manager):
        super().__init__(ui_manager, title="ЗАГРУЗКА МИРА")
        self.set_hint("Подготовка игрового мира...")

    def set_map_name(self, name: str):
        """Устанавливает название карты."""
        self.set_status(f"Карта: {name}")
