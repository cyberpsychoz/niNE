"""
Клиентский UI для отображения характеристик персонажа (D&D).
Показывает портрет, HP bar, AC, уровень в стиле Baldur's Gate.
"""

from direct.gui.DirectGui import DirectFrame, DirectLabel
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (
    CardMaker,
    NodePath,
    TextNode,
    Texture,
    TransparencyAttrib,
)

from nine.core.game_state import GameState
from nine.core.plugins import PluginModule
from nine.ui.ui_config import ui

# Путь к UI текстурам
UI_PATH = "nine/assets/materials/textures/ui"


class DNDHealthBar:
    """HP бар в стиле BG1 с красной заливкой."""

    def __init__(self, parent, position, width=0.25, height=0.03):
        self.width = width
        self.height = height
        self.current_hp = 100
        self.max_hp = 100
        self.temp_hp = 0

        # Загружаем текстуры
        self.empty_tex = self._load_texture(f"{UI_PATH}/bars/EmptyBar.png")
        self.red_tex = self._load_texture(f"{UI_PATH}/bars/RedBar.png")
        self.blue_tex = self._load_texture(f"{UI_PATH}/bars/BlueBar.png")  # для temp HP

        # Контейнер
        self.container = NodePath("hp_bar_container")
        self.container.reparentTo(parent)
        self.container.setPos(*position)

        # Фон (пустой бар)
        self.bg_node = self._create_card("bg", self.empty_tex, self.width, self.height)
        self.bg_node.reparentTo(self.container)

        # Заполнение (красный HP)
        self.fill_node = self._create_card("fill", self.red_tex, self.width, self.height)
        self.fill_node.reparentTo(self.container)
        self.fill_node.setPos(0, 0, 0.001)

        # Temp HP (синий поверх)
        self.temp_node = self._create_card("temp", self.blue_tex, self.width, self.height)
        self.temp_node.reparentTo(self.container)
        self.temp_node.setPos(0, 0, 0.002)
        self.temp_node.hide()

    def _load_texture(self, path):
        """Загружает текстуру."""
        tex = Texture()
        tex.read(path)
        tex.setMagfilter(Texture.FT_linear)
        tex.setMinfilter(Texture.FT_linear)
        return tex

    def _create_card(self, name, texture, width, height):
        """Создаёт текстурированную карточку (центрированную)."""
        cm = CardMaker(name)
        cm.setFrame(-width / 2, width / 2, -height / 2, height / 2)  # Центрировано
        node = NodePath(cm.generate())
        node.setTexture(texture)
        node.setTransparency(TransparencyAttrib.M_alpha)
        return node

    def set_hp(self, current, maximum, temp=0):
        """Обновляет HP."""
        self.current_hp = max(0, current)
        self.max_hp = max(1, maximum)
        self.temp_hp = max(0, temp)

        # Основной HP (красный)
        hp_ratio = self.current_hp / self.max_hp
        self._update_bar(self.fill_node, self.red_tex, hp_ratio)

        # Temp HP (синий)
        if self.temp_hp > 0:
            total_hp = self.current_hp + self.temp_hp
            temp_ratio = min(1.0, total_hp / self.max_hp)
            self._update_bar(self.temp_node, self.blue_tex, temp_ratio)
            self.temp_node.show()
        else:
            self.temp_node.hide()

    def _update_bar(self, node, texture, ratio):
        """Обновляет ширину бара (центрированный относительно фона)."""
        if ratio <= 0.001:
            node.hide()
            return

        node.show()
        fill_width = self.width * ratio

        # Пересоздаём карточку с новой шириной (выровнено по центру фона)
        cm = CardMaker(node.getName())
        # Центрируем заполнение относительно полной ширины
        cm.setFrame(-self.width / 2, -self.width / 2 + fill_width, -self.height / 2, self.height / 2)
        cm.setUvRange((0, 0), (ratio, 1))

        # Заменяем геометрию
        node.node().removeAllGeoms()
        node.attachNewNode(cm.generate())
        node.setTexture(texture)
        node.setTransparency(TransparencyAttrib.M_alpha)

    def destroy(self):
        """Очистка."""
        self.container.removeNode()


class StatsUIModule(PluginModule):
    """Клиентский модуль UI характеристик D&D."""

    def on_load(self):
        self.hud_frame = None
        self.hp_bar = None
        self.hp_text = None
        self.ac_text = None
        self.level_text = None
        self.name_text = None

        self._visible = False
        self._cached_character = None

        # Подписки на D&D события
        self.event_manager.subscribe("character_sheet", self.on_character_update)
        self.event_manager.subscribe("game_state_changed", self.on_game_state_changed)

        self.logger.info("D&D HUD загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("character_sheet", self.on_character_update)
        self.event_manager.unsubscribe("game_state_changed", self.on_game_state_changed)
        self.destroy_ui()
        self.logger.info("D&D HUD выгружен")

    def on_game_state_changed(self, data: dict):
        """Обработка смены состояния игры."""
        new_state = data.get("new_state")

        if new_state == GameState.MENU:
            self.hide_hud()
            self.destroy_ui()
            self._cached_character = None
        elif new_state == GameState.IN_GAME:
            if self._cached_character:
                self._apply_character_data(self._cached_character)

    def create_ui(self):
        """Создаёт HUD элементы в стиле BG1 (размеры из UIConfig)."""
        if self.hud_frame:
            return

        # Контейнер справа снизу
        self.hud_frame = DirectFrame(
            frameSize=(-0.5, 0.5, -0.22, 0.22),
            frameColor=(0, 0, 0, 0),
            pos=(1.1, 0, -0.70),  # Правая сторона
            parent=self.app.aspect2d,
        )

        # Имя персонажа (размеры из UIConfig)
        self.name_text = OnscreenText(
            text="",
            parent=self.hud_frame,
            scale=ui.hud.name_scale,
            pos=(0, 0.14),
            fg=ui.colors.gold,
            align=TextNode.ACenter,
            mayChange=True,
        )

        # HP бар (по центру, размеры из UIConfig)
        self.hp_bar = DNDHealthBar(
            parent=self.hud_frame,
            position=(0, 0, 0.06),
            width=ui.hud.hp_bar_width,
            height=ui.hud.hp_bar_height,
        )

        # HP текст (под баром)
        self.hp_text = OnscreenText(
            text="HP: 0/0",
            parent=self.hud_frame,
            scale=ui.hud.stat_scale,
            pos=(0, 0.005),
            fg=(1, 1, 1, 0.95),
            align=TextNode.ACenter,
            mayChange=True,
        )

        # AC (слева)
        self.ac_text = OnscreenText(
            text="AC: 10",
            parent=self.hud_frame,
            scale=ui.hud.value_scale,
            pos=(-0.18, -0.08),
            fg=ui.colors.gold,
            align=TextNode.ACenter,
            mayChange=True,
        )

        # Уровень (справа)
        self.level_text = OnscreenText(
            text="Lv 1",
            parent=self.hud_frame,
            scale=ui.hud.value_scale,
            pos=(0.18, -0.08),
            fg=ui.colors.gold,
            align=TextNode.ACenter,
            mayChange=True,
        )

        self.hud_frame.hide()

    def destroy_ui(self):
        """Уничтожает UI элементы."""
        if self.hp_bar:
            self.hp_bar.destroy()
            self.hp_bar = None

        if self.hud_frame:
            self.hud_frame.destroy()
            self.hud_frame = None

        self.hp_text = None
        self.ac_text = None
        self.level_text = None
        self.name_text = None
        self._visible = False

    def show_hud(self):
        """Показать HUD."""
        if not self.hud_frame:
            self.create_ui()
        self.hud_frame.show()
        self._visible = True

    def hide_hud(self):
        """Скрыть HUD."""
        if self.hud_frame:
            self.hud_frame.hide()
        self._visible = False

    def on_character_update(self, data: dict):
        """Обновление данных персонажа от сервера."""
        character = data.get("character", {})
        self._cached_character = character

        # Если в меню - только кешируем
        if hasattr(self.app, 'ui') and hasattr(self.app.ui, 'game_state'):
            if self.app.ui.game_state == GameState.MENU:
                return

        self._apply_character_data(character)

    def _apply_character_data(self, character: dict):
        """Применяет данные персонажа к HUD."""
        if not self._visible:
            self.show_hud()

        # Имя
        name = character.get("name", "Unknown")
        if self.name_text:
            self.name_text.setText(name)

        # HP
        stats = character.get("stats", {})
        current_hp = stats.get("current_hp", 10)
        max_hp = stats.get("max_hp", 10)
        temp_hp = stats.get("temp_hp", 0)

        if self.hp_bar:
            self.hp_bar.set_hp(current_hp, max_hp, temp_hp)

        if self.hp_text:
            hp_display = f"HP: {current_hp}/{max_hp}"
            if temp_hp > 0:
                hp_display += f" (+{temp_hp})"
            self.hp_text.setText(hp_display)

        # AC
        ac = stats.get("armor_class", 10)
        if self.ac_text:
            self.ac_text.setText(f"AC: {ac}")

        # Уровень
        level = stats.get("level", 1)
        if self.level_text:
            self.level_text.setText(f"Lv {level}")
