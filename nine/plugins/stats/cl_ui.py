"""
Клиентский UI для отображения характеристик.
Показывает горизонтальные прогресс-бары здоровья и голода справа сверху.
"""

import os

from direct.gui.DirectGui import DirectFrame
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (
    CardMaker,
    NodePath,
    TextNode,
    Texture,
    TransparencyAttrib,
    Vec2,
)

from nine.core.game_state import GameState
from nine.core.plugins import PluginModule

# Путь к текстурам
TEXTURES_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "materials", "textures")


class TexturedStatsBar:
    """Горизонтальный прогресс-бар с текстурами."""

    def __init__(self, parent, position, fill_texture_path, empty_texture_path, label, max_value=100, uv_row=0, total_rows=4):
        """
        Args:
            parent: Родительский узел
            position: Позиция (x, y, z)
            fill_texture_path: Путь к текстуре заполненного бара
            empty_texture_path: Путь к текстуре пустого бара
            label: Подпись слева
            max_value: Максимальное значение
            uv_row: Номер ряда в текстуре (0 = верхний)
            total_rows: Общее количество рядов в текстуре
        """
        self.max_value = max_value
        self.current_value = max_value
        self.uv_row = uv_row
        self.total_rows = total_rows

        # Размеры бара в экранных координатах
        self.bar_width = 0.3
        self.bar_height = 0.04

        # Рассчитываем UV координаты для нужного ряда
        # UV: V=0 внизу, V=1 вверху. Для верхнего ряда (row=0): v_top=1.0, v_bottom=0.75
        row_height = 1.0 / total_rows
        self.v_top = 1.0 - (uv_row * row_height)
        self.v_bottom = self.v_top - row_height

        # Контейнер
        self.container = DirectFrame(
            parent=parent,
            frameSize=(0, self.bar_width + 0.12, -self.bar_height, self.bar_height),
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

        # Загружаем текстуры
        self.empty_texture = self._load_texture(empty_texture_path)
        self.fill_texture = self._load_texture(fill_texture_path)

        # Создаём фоновый бар (пустой)
        self.bg_node = self._create_textured_card(
            "bg_bar", self.empty_texture, self.bar_width, self.bar_height
        )
        self.bg_node.reparentTo(self.container)
        self.bg_node.setPos(0, 0, 0)

        # Создаём заполненный бар
        self.fill_node = self._create_textured_card(
            "fill_bar", self.fill_texture, self.bar_width, self.bar_height
        )
        self.fill_node.reparentTo(self.container)
        self.fill_node.setPos(0, 0, 0.001)  # Чуть впереди фона

        # Значение справа
        self.value_text = OnscreenText(
            text=f"{int(max_value)}",
            parent=self.container,
            scale=0.03,
            pos=(self.bar_width + 0.02, -0.008),
            fg=(1, 1, 1, 0.9),
            align=TextNode.ALeft,
            mayChange=True,
        )

    def _load_texture(self, path):
        """Загрузка текстуры с настройками."""
        tex = Texture()
        tex.read(path)
        tex.setMagfilter(Texture.FT_nearest)  # Пиксельный стиль
        tex.setMinfilter(Texture.FT_nearest)
        tex.setWrapU(Texture.WM_clamp)
        tex.setWrapV(Texture.WM_clamp)
        return tex

    def _create_textured_card(self, name, texture, width, height):
        """Создаёт карточку с текстурой и нужными UV координатами."""
        cm = CardMaker(name)
        # Геометрия карточки
        cm.setFrame(0, width, -height / 2, height / 2)
        # UV координаты: используем только нужный ряд текстуры
        cm.setUvRange(Vec2(0, self.v_bottom), Vec2(1, self.v_top))

        node = NodePath(cm.generate())
        node.setTexture(texture)
        node.setTransparency(TransparencyAttrib.M_alpha)
        return node

    def set_value(self, value, max_value=None):
        """Обновить значение полоски."""
        if max_value is not None:
            self.max_value = max_value

        self.current_value = max(0, min(value, self.max_value))
        ratio = self.current_value / self.max_value if self.max_value > 0 else 0

        if ratio > 0.001:
            self.fill_node.show()
            self._update_fill_width(ratio)
        else:
            self.fill_node.hide()

        # Обновляем текст
        self.value_text.setText(f"{int(self.current_value)}")

    def _update_fill_width(self, ratio):
        """Перегенерирует карточку заполнения с нужной шириной."""
        # Удаляем старую карточку
        if self.fill_node:
            self.fill_node.removeNode()

        # Новая ширина
        fill_width = self.bar_width * ratio

        # Создаём новую карточку с обрезанным UV
        cm = CardMaker("fill_bar")
        cm.setFrame(0, fill_width, -self.bar_height / 2, self.bar_height / 2)
        # UV: показываем только часть текстуры соответствующую ratio
        cm.setUvRange(Vec2(0, self.v_bottom), Vec2(ratio, self.v_top))

        self.fill_node = NodePath(cm.generate())
        self.fill_node.setTexture(self.fill_texture)
        self.fill_node.setTransparency(TransparencyAttrib.M_alpha)
        self.fill_node.reparentTo(self.container)
        self.fill_node.setPos(0, 0, 0.001)

    def destroy(self):
        """Очистка ресурсов."""
        if self.bg_node:
            self.bg_node.removeNode()
        if self.fill_node:
            self.fill_node.removeNode()
        self.container.destroy()


class StatsUIModule(PluginModule):
    """Клиентский модуль UI характеристик."""

    def on_load(self):
        self.stats_frame = None
        self.health_bar = None
        self.hunger_bar = None
        self._visible = False

        # Подписки
        self.event_manager.subscribe("stats_update", self.on_stats_updated)
        self.event_manager.subscribe("game_started", self.show_stats)
        self.event_manager.subscribe("game_ended", self.hide_stats)
        self.event_manager.subscribe("client_connected", self.on_connected)
        self.event_manager.subscribe("client_disconnected", self.on_disconnected)
        self.event_manager.subscribe("game_state_changed", self.on_game_state_changed)

        self.logger.info("UI характеристик загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("stats_update", self.on_stats_updated)
        self.event_manager.unsubscribe("game_started", self.show_stats)
        self.event_manager.unsubscribe("game_ended", self.hide_stats)
        self.event_manager.unsubscribe("client_connected", self.on_connected)
        self.event_manager.unsubscribe("client_disconnected", self.on_disconnected)
        self.event_manager.unsubscribe("game_state_changed", self.on_game_state_changed)

        self.destroy_ui()
        self.logger.info("UI характеристик выгружен")

    def on_game_state_changed(self, data: dict):
        """Обработка смены состояния игры."""
        new_state = data.get("new_state")

        if new_state == GameState.MENU:
            # Скрываем и уничтожаем UI в меню
            self.hide_stats()
            self.destroy_ui()
        elif new_state == GameState.IN_GAME:
            # UI создастся при получении stats_update от сервера
            pass

    def on_connected(self, data=None):
        """Клиент подключился - создаём UI."""
        self.create_ui()
        self.show_stats()

    def on_disconnected(self, data=None):
        """Клиент отключился - уничтожаем UI."""
        self.hide_stats()
        self.destroy_ui()

    def create_ui(self):
        """Создаёт UI элементы."""
        if self.stats_frame:
            return

        # Пути к текстурам
        health_tex = os.path.join(TEXTURES_PATH, "health_bar.png")
        food_tex = os.path.join(TEXTURES_PATH, "food_bar.png")
        empty_tex = os.path.join(TEXTURES_PATH, "empty_bar.png")

        # Контейнер справа сверху
        self.stats_frame = DirectFrame(
            frameSize=(-0.5, 0, -0.2, 0.1),
            frameColor=(0, 0, 0, 0),
            pos=(1.3, 0, 0.85),
            parent=self.app.aspect2d,
        )

        # Полоска здоровья - сверху
        self.health_bar = TexturedStatsBar(
            parent=self.stats_frame,
            position=(-0.38, 0, 0),
            fill_texture_path=health_tex,
            empty_texture_path=empty_tex,
            label="HP",
            max_value=100,
            uv_row=0,  # Верхний ряд текстуры
            total_rows=4,
        )

        # Полоска еды - ниже
        self.hunger_bar = TexturedStatsBar(
            parent=self.stats_frame,
            position=(-0.38, 0, -0.06),
            fill_texture_path=food_tex,
            empty_texture_path=empty_tex,
            label="Еда",
            max_value=100,
            uv_row=0,  # Верхний ряд текстуры
            total_rows=4,
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

        self._visible = False

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
        # Не показываем если мы в меню
        if self.app.ui.game_state == GameState.MENU:
            return

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
