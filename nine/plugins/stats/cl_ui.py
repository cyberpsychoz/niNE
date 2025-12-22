"""
Клиентский UI для отображения характеристик.
Показывает полоски здоровья и голода слева на экране.
"""

from direct.gui.DirectGui import DirectFrame, DirectLabel
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode

from nine.core.plugins import PluginModule


class StatsBar:
    """Вертикальная полоска характеристики."""

    def __init__(self, parent, position, color, label, max_value=100):
        self.max_value = max_value
        self.current_value = max_value

        # Фон полоски
        self.bg = DirectFrame(
            parent=parent,
            frameSize=(-0.015, 0.015, 0, 0.3),
            frameColor=(0.1, 0.1, 0.1, 0.8),
            pos=position,
        )

        # Заполненная часть
        self.fill = DirectFrame(
            parent=self.bg,
            frameSize=(-0.012, 0.012, 0, 0.294),
            frameColor=color,
            pos=(0, 0, 0.003),
        )

        # Подпись
        self.label = OnscreenText(
            text=label,
            parent=parent,
            scale=0.03,
            pos=(position[0], position[2] - 0.04),
            fg=(1, 1, 1, 0.9),
            align=TextNode.ACenter,
            mayChange=True,
        )

        # Значение
        self.value_text = OnscreenText(
            text=f"{max_value}",
            parent=parent,
            scale=0.025,
            pos=(position[0], position[2] + 0.31),
            fg=(1, 1, 1, 0.9),
            align=TextNode.ACenter,
            mayChange=True,
        )

    def set_value(self, value, max_value=None):
        """Обновить значение полоски."""
        if max_value is not None:
            self.max_value = max_value

        self.current_value = max(0, min(value, self.max_value))

        # Обновляем высоту заполнения
        ratio = self.current_value / self.max_value if self.max_value > 0 else 0
        fill_height = 0.294 * ratio
        self.fill["frameSize"] = (-0.012, 0.012, 0, fill_height)

        # Обновляем цвет в зависимости от значения
        if ratio < 0.25:
            # Мигающий эффект при критическом значении
            pass  # TODO: добавить мигание

        # Обновляем текст
        self.value_text.setText(f"{int(self.current_value)}")

    def destroy(self):
        """Очистка ресурсов."""
        self.bg.destroy()
        self.label.destroy()
        self.value_text.destroy()


class StatsUIModule(PluginModule):
    """Клиентский модуль UI характеристик."""

    def on_load(self):
        self.stats_frame = None
        self.health_bar = None
        self.hunger_bar = None
        self._visible = False

        # Подписки
        self.event_manager.subscribe("stats_updated", self.on_stats_updated)
        self.event_manager.subscribe("game_started", self.show_stats)
        self.event_manager.subscribe("game_ended", self.hide_stats)
        self.event_manager.subscribe("client_connected", self.on_connected)
        self.event_manager.subscribe("client_disconnected", self.on_disconnected)

        self.logger.info("UI характеристик загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("stats_updated", self.on_stats_updated)
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

        # Контейнер слева внизу
        self.stats_frame = DirectFrame(
            frameSize=(-0.15, 0.15, -0.05, 0.4),
            frameColor=(0, 0, 0, 0),
            pos=(-1.15, 0, -0.5),
            parent=self.app.aspect2d,
        )

        # Полоска здоровья (красная)
        self.health_bar = StatsBar(
            parent=self.stats_frame,
            position=(-0.05, 0, 0),
            color=(0.8, 0.2, 0.2, 1),
            label="HP",
            max_value=100,
        )

        # Полоска голода (оранжевая)
        self.hunger_bar = StatsBar(
            parent=self.stats_frame,
            position=(0.05, 0, 0),
            color=(0.9, 0.6, 0.2, 1),
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
