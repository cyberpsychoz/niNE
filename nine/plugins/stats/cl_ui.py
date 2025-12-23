"""
Клиентский UI для отображения характеристик.
Показывает горизонтальные прогресс-бары здоровья и голода справа сверху.
"""

from direct.gui.DirectGui import DirectFrame, DirectWaitBar
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode

from nine.core.plugins import PluginModule


class StatsBar:
    """Горизонтальный прогресс-бар характеристики."""

    def __init__(self, parent, position, bar_color, label, max_value=100):
        self.max_value = max_value
        self.current_value = max_value
        self.bar_color = bar_color

        # Ширина и высота бара
        self.bar_width = 0.25
        self.bar_height = 0.025

        # Контейнер для бара и текста
        self.container = DirectFrame(
            parent=parent,
            frameSize=(0, self.bar_width + 0.1, -self.bar_height, self.bar_height),
            frameColor=(0, 0, 0, 0),
            pos=position,
        )

        # Подпись слева
        self.label = OnscreenText(
            text=label,
            parent=self.container,
            scale=0.035,
            pos=(-0.01, -0.01),
            fg=(1, 1, 1, 0.9),
            align=TextNode.ARight,
            mayChange=False,
        )

        # Фон полоски (тёмный)
        self.bg = DirectFrame(
            parent=self.container,
            frameSize=(0, self.bar_width, -self.bar_height / 2, self.bar_height / 2),
            frameColor=(0.15, 0.15, 0.15, 0.85),
            pos=(0, 0, 0),
        )

        # Заполненная часть
        self.fill = DirectFrame(
            parent=self.bg,
            frameSize=(0.002, self.bar_width - 0.002, -self.bar_height / 2 + 0.002, self.bar_height / 2 - 0.002),
            frameColor=bar_color,
            pos=(0, 0, 0),
        )

        # Значение справа от бара
        self.value_text = OnscreenText(
            text=f"{int(max_value)}",
            parent=self.container,
            scale=0.03,
            pos=(self.bar_width + 0.02, -0.008),
            fg=(1, 1, 1, 0.9),
            align=TextNode.ALeft,
            mayChange=True,
        )

    def set_value(self, value, max_value=None):
        """Обновить значение полоски."""
        if max_value is not None:
            self.max_value = max_value

        self.current_value = max(0, min(value, self.max_value))

        # Обновляем ширину заполнения
        ratio = self.current_value / self.max_value if self.max_value > 0 else 0
        fill_width = (self.bar_width - 0.004) * ratio

        if fill_width > 0.001:
            self.fill["frameSize"] = (0.002, 0.002 + fill_width, -self.bar_height / 2 + 0.002, self.bar_height / 2 - 0.002)
            self.fill.show()
        else:
            self.fill.hide()

        # Меняем цвет при низком значении
        if ratio < 0.25:
            # Критический уровень - красноватый оттенок
            self.fill["frameColor"] = (0.9, 0.2, 0.2, 1)
        elif ratio < 0.5:
            # Низкий уровень - желтоватый
            self.fill["frameColor"] = (0.9, 0.7, 0.2, 1)
        else:
            # Нормальный уровень - исходный цвет
            self.fill["frameColor"] = self.bar_color

        # Обновляем текст
        self.value_text.setText(f"{int(self.current_value)}")

    def destroy(self):
        """Очистка ресурсов."""
        self.container.destroy()


class StatsUIModule(PluginModule):
    """Клиентский модуль UI характеристик."""

    def on_load(self):
        self.stats_frame = None
        self.health_bar = None
        self.hunger_bar = None
        self._visible = False

        # Подписки
        # stats_update - сетевое сообщение от сервера
        self.event_manager.subscribe("stats_update", self.on_stats_updated)
        self.event_manager.subscribe("game_started", self.show_stats)
        self.event_manager.subscribe("game_ended", self.hide_stats)
        self.event_manager.subscribe("client_connected", self.on_connected)
        self.event_manager.subscribe("client_disconnected", self.on_disconnected)

        self.logger.info("UI характеристик загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("stats_update", self.on_stats_updated)
        self.event_manager.unsubscribe("game_started", self.show_stats)
        self.event_manager.unsubscribe("game_ended", self.hide_stats)
        self.event_manager.unsubscribe("client_connected", self.on_connected)
        self.event_manager.unsubscribe("client_disconnected", self.on_disconnected)

        self.destroy_ui()
        self.logger.info("UI характеристик выгружен")

    def on_connected(self, data=None):
        """Клиент подключился - создаём UI."""
        self.create_ui()
        self.show_stats()

    def on_disconnected(self, data=None):
        """Клиент отключился - скрываем UI."""
        self.hide_stats()

    def create_ui(self):
        """Создаёт UI элементы."""
        if self.stats_frame:
            return

        # Контейнер справа сверху
        self.stats_frame = DirectFrame(
            frameSize=(-0.4, 0, -0.15, 0.05),
            frameColor=(0, 0, 0, 0),
            pos=(1.25, 0, 0.85),
            parent=self.app.aspect2d,
        )

        # Полоска здоровья (красная) - сверху
        self.health_bar = StatsBar(
            parent=self.stats_frame,
            position=(-0.32, 0, 0),
            bar_color=(0.8, 0.25, 0.25, 1),
            label="HP",
            max_value=100,
        )

        # Полоска голода (оранжевая) - ниже
        self.hunger_bar = StatsBar(
            parent=self.stats_frame,
            position=(-0.32, 0, -0.05),
            bar_color=(0.9, 0.6, 0.2, 1),
            label="Еда",
            max_value=100,
        )

        self.stats_frame.hide()

    def destroy_ui(self):
        """Уничтожает UI элементы."""
        if self.health_bar:
            self.health_bar.destroy()
            self.health_bar = None

        if self.hunger_bar:
            self.hunger_bar.destroy()
            self.hunger_bar = None

        if self.stats_frame:
            self.stats_frame.destroy()
            self.stats_frame = None

    def show_stats(self, data=None):
        """Показать полоски."""
        if not self.stats_frame:
            self.create_ui()
        self.stats_frame.show()
        self._visible = True

    def hide_stats(self, data=None):
        """Скрыть полоски."""
        if self.stats_frame:
            self.stats_frame.hide()
        self._visible = False

    def on_stats_updated(self, data: dict):
        """Обновление характеристик от сервера."""
        if not self._visible:
            self.show_stats()

        health = data.get("health", 100)
        max_health = data.get("max_health", 100)
        hunger = data.get("hunger", 100)
        max_hunger = data.get("max_hunger", 100)

        if self.health_bar:
            self.health_bar.set_value(health, max_health)

        if self.hunger_bar:
            self.hunger_bar.set_value(hunger, max_hunger)
