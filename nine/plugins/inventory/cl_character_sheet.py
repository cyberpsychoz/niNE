"""
Клиентский модуль листа персонажа.

Главный UI с вкладками:
- Инвентарь (с drag & drop)
- Экипировка (слоты на манекене)
- Описание (редактируемое)
- Статы (характеристики + спасброски)
- Навыки (18 навыков D&D)
- Способности (расовые/классовые/предыстории)
- Заклинания (для магов)

Открывается на клавишу I.
"""

from typing import Dict, List, Optional, Callable
from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectLabel, DirectEntry,
    DirectScrolledFrame, DGG
)
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode

from nine.core.plugins import PluginModule
from nine.core.game_state import GameState
from nine.ui.bg1_button import BG1Button, BG1ButtonSmall

from nine.plugins.inventory.entities.equipment.sh_equipment_slots import EquipmentSlot, SLOT_INFO


class CharacterSheetClientModule(PluginModule, DirectObject):
    """
    Клиентский модуль листа персонажа.

    Объединяет инвентарь, экипировку, описание, статы, навыки,
    способности и заклинания в одном UI.
    """

    # Цвета редкости
    RARITY_COLORS = {
        "common": (0.9, 0.9, 0.9, 1),
        "uncommon": (0.3, 0.9, 0.3, 1),
        "rare": (0.3, 0.5, 0.9, 1),
        "very_rare": (0.7, 0.3, 0.9, 1),
        "legendary": (0.9, 0.7, 0.2, 1),
        "artifact": (0.9, 0.3, 0.3, 1),
    }

    # Названия навыков на русском
    SKILL_NAMES = {
        "Athletics": "Атлетика",
        "Acrobatics": "Акробатика",
        "Sleight of Hand": "Ловкость рук",
        "Stealth": "Скрытность",
        "Arcana": "Магия",
        "History": "История",
        "Investigation": "Анализ",
        "Nature": "Природа",
        "Religion": "Религия",
        "Animal Handling": "Уход за животными",
        "Insight": "Проницательность",
        "Medicine": "Медицина",
        "Perception": "Внимательность",
        "Survival": "Выживание",
        "Deception": "Обман",
        "Intimidation": "Запугивание",
        "Performance": "Выступление",
        "Persuasion": "Убеждение",
    }

    # Названия характеристик на русском
    ABILITY_NAMES = {
        "strength": "СИЛ",
        "dexterity": "ЛОВ",
        "constitution": "ТЕЛ",
        "intelligence": "ИНТ",
        "wisdom": "МДР",
        "charisma": "ХАР",
    }

    ABILITY_FULL_NAMES = {
        "strength": "Сила",
        "dexterity": "Ловкость",
        "constitution": "Телосложение",
        "intelligence": "Интеллект",
        "wisdom": "Мудрость",
        "charisma": "Харизма",
    }

    def __init__(self, context):
        PluginModule.__init__(self, context)
        DirectObject.__init__(self)

    def on_load(self):
        # Состояние UI
        self.is_open = False
        self.current_tab = "inventory"

        # Данные
        self.inventory_items: List[dict] = []
        self.equipment_slots: Dict[str, Optional[dict]] = {}
        self.character_data: dict = {}
        self.max_slots = 20

        # Данные квестов
        self.quests_data: List[dict] = []

        # Drag & drop
        self.dragging_item: Optional[dict] = None
        self.dragging_from: Optional[str] = None
        self.drag_frame: Optional[DirectFrame] = None

        # UI элементы
        self.main_frame: Optional[DirectFrame] = None
        self.tab_buttons: Dict[str, DirectButton] = {}
        self.content_frame: Optional[DirectFrame] = None

        # Tooltip
        self.tooltip_frame: Optional[DirectFrame] = None

        # Подписки
        self.event_manager.subscribe("inventory_update", self.on_inventory_update)
        self.event_manager.subscribe("equipment_update", self.on_equipment_update)
        self.event_manager.subscribe("character_sheet", self.on_character_sheet_update)
        self.event_manager.subscribe("game_state_changed", self._on_game_state_changed)
        self.event_manager.subscribe("close_other_ui", self._on_close_other_ui)
        self.event_manager.subscribe("open_character_sheet_tab", self._on_open_to_tab)
        self.event_manager.subscribe("quest_list", self._on_quest_list_update)

        # Клавиши
        self.accept("i", self.toggle_character_sheet)
        self.accept("escape", self.on_escape)

        self.logger.info("Клиентский модуль листа персонажа загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("inventory_update", self.on_inventory_update)
        self.event_manager.unsubscribe("equipment_update", self.on_equipment_update)
        self.event_manager.unsubscribe("character_sheet", self.on_character_sheet_update)
        self.event_manager.unsubscribe("game_state_changed", self._on_game_state_changed)
        self.event_manager.unsubscribe("close_other_ui", self._on_close_other_ui)
        self.event_manager.unsubscribe("open_character_sheet_tab", self._on_open_to_tab)
        self.event_manager.unsubscribe("quest_list", self._on_quest_list_update)
        self.ignoreAll()
        self._destroy_ui()
        self.logger.info("Клиентский модуль листа персонажа выгружен")

    def _on_close_other_ui(self, data: dict):
        """Закрывает окно если оно не исключено."""
        exclude = data.get("exclude", "")
        if exclude != "character_sheet" and self.is_open:
            self.close_character_sheet()

    def _on_open_to_tab(self, data: dict):
        """Открывает лист персонажа на определённую вкладку."""
        tab = data.get("tab", "inventory")
        if not self.is_open:
            self.open_character_sheet(tab=tab)
        else:
            # Если уже открыт, переключаем на нужную вкладку
            if tab != self.current_tab:
                self._switch_tab(tab)

    def _on_quest_list_update(self, data: dict):
        """Обновление списка квестов."""
        self.quests_data = data.get("quests", [])
        if self.is_open and self.current_tab == "quests":
            self._refresh_content()

    def _on_game_state_changed(self, data: dict):
        """Закрываем UI при смене состояния."""
        new_state = data.get("new_state")
        if new_state != GameState.IN_GAME and self.is_open:
            self.close_character_sheet()

    # =========================================================================
    # Data handlers
    # =========================================================================

    def on_inventory_update(self, data: dict):
        """Обновление инвентаря от сервера."""
        self.inventory_items = data.get("inventory", [])
        self.max_slots = data.get("max_slots", 20)

        if self.is_open and self.current_tab == "inventory":
            self._refresh_content()

    def on_equipment_update(self, data: dict):
        """Обновление экипировки от сервера."""
        self.equipment_slots = data.get("slots", {})

        if self.is_open and self.current_tab == "equipment":
            self._refresh_content()

    def on_character_sheet_update(self, data: dict):
        """Обновление данных персонажа от сервера."""
        self.character_data = data.get("character", {})

        if self.is_open:
            # Обновляем текущую вкладку если она зависит от данных персонажа
            if self.current_tab in ("description", "stats", "skills", "abilities", "spells", "quests"):
                self._refresh_content()

    # =========================================================================
    # UI Control
    # =========================================================================

    def toggle_character_sheet(self):
        """Открывает/закрывает лист персонажа."""
        if not self.is_open:
            if hasattr(self.app, 'is_chat_active') and self.app.is_chat_active():
                return

        if self.is_open:
            self.close_character_sheet()
        else:
            self.open_character_sheet()

    def open_character_sheet(self, tab: str = None):
        """Открывает лист персонажа на указанную вкладку."""
        if self.is_open:
            return

        if hasattr(self.app, 'is_chat_active') and self.app.is_chat_active():
            return

        # Закрываем другие окна
        self.event_manager.post("close_other_ui", {"exclude": "character_sheet"})

        # Устанавливаем вкладку если указана
        if tab is not None:
            self.current_tab = tab

        self.is_open = True

        # Приостанавливаем управление камерой (камера остаётся прикреплённой)
        if hasattr(self.app, 'camera_controller') and self.app.camera_controller:
            self.app.camera_controller.pause()

        self._create_ui()
        self.logger.debug(f"Лист персонажа открыт (вкладка: {self.current_tab})")

    def close_character_sheet(self):
        """Закрывает лист персонажа."""
        if not self.is_open:
            return

        self.is_open = False
        self._destroy_ui()

        # Возобновляем управление камерой
        if hasattr(self.app, 'camera_controller') and self.app.camera_controller:
            self.app.camera_controller.resume()

        self.logger.debug("Лист персонажа закрыт")

    def on_escape(self):
        """Escape закрывает UI."""
        if self.is_open:
            self.close_character_sheet()

    # =========================================================================
    # Main UI Creation
    # =========================================================================

    def _create_ui(self):
        """Создаёт основной UI (увеличен x1.5)."""
        # Главный фрейм (увеличенный для новых вкладок)
        self.main_frame = DirectFrame(
            frameColor=(0.08, 0.08, 0.12, 0.98),
            frameSize=(-1.1, 1.1, -0.85, 0.75),
            pos=(0, 0, 0),
            parent=self.app.aspect2d,
        )

        # Заголовок
        name = self.character_data.get("name", "Персонаж")
        char_class = self.character_data.get("class", "")
        race = self.character_data.get("race", "")
        level = self.character_data.get("stats", {}).get("level", 1)

        title = f"{name}"
        if race and char_class:
            title += f" — {race} {char_class} {level} ур."

        DirectLabel(
            text=title,
            text_scale=0.07,
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.65),
            parent=self.main_frame,
        )

        # Кнопка закрытия
        DirectButton(
            text="X",
            text_scale=0.06,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.6, 0.2, 0.2, 1),
            frameSize=(-0.04, 0.04, -0.035, 0.04),
            pos=(1.02, 0, 0.67),
            parent=self.main_frame,
            command=self.close_character_sheet,
        )

        # Вкладки
        self._create_tabs()

        # Область контента
        self.content_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.14, 1),
            frameSize=(-1.05, 1.05, -0.78, 0.48),
            pos=(0, 0, 0),
            parent=self.main_frame,
        )

        # Загружаем контент текущей вкладки
        self._refresh_content()

        # Клик по фрейму не закрывает UI
        self.accept("mouse1", self._on_mouse_click)

    def _create_tabs(self):
        """Создаёт панель вкладок (увеличены)."""
        tabs = [
            ("inventory", "Инвентарь"),
            ("equipment", "Экипировка"),
            ("description", "Описание"),
            ("stats", "Статы"),
            ("skills", "Навыки"),
            ("abilities", "Способности"),
            ("quests", "Квесты"),
            ("spells", "Заклинания"),
        ]

        tab_width = 0.24
        start_x = -0.88

        for i, (tab_id, tab_name) in enumerate(tabs):
            x = start_x + i * (tab_width + 0.01)

            is_active = tab_id == self.current_tab
            color = (0.3, 0.4, 0.5, 1) if is_active else (0.2, 0.2, 0.25, 1)

            btn = DirectButton(
                text=tab_name,
                text_scale=0.04,
                text_fg=(1, 1, 1, 1),
                frameColor=color,
                frameSize=(-tab_width/2, tab_width/2, -0.035, 0.04),
                pos=(x, 0, 0.54),
                parent=self.main_frame,
                command=self._switch_tab,
                extraArgs=[tab_id],
            )

            self.tab_buttons[tab_id] = btn

    def _switch_tab(self, tab_id: str):
        """Переключает вкладку."""
        if tab_id == self.current_tab:
            return

        self.current_tab = tab_id

        # Обновляем цвета кнопок
        for tid, btn in self.tab_buttons.items():
            is_active = tid == self.current_tab
            color = (0.3, 0.4, 0.5, 1) if is_active else (0.2, 0.2, 0.25, 1)
            btn["frameColor"] = color

        # Обновляем контент
        self._refresh_content()

    def _refresh_content(self):
        """Обновляет содержимое текущей вкладки."""
        # Очищаем контент
        if self.content_frame:
            for child in self.content_frame.getChildren():
                child.removeNode()

        self._hide_tooltip()

        # Загружаем контент в зависимости от вкладки
        if self.current_tab == "inventory":
            self._create_inventory_content()
        elif self.current_tab == "equipment":
            self._create_equipment_content()
        elif self.current_tab == "description":
            self._create_description_content()
        elif self.current_tab == "stats":
            self._create_stats_content()
        elif self.current_tab == "skills":
            self._create_skills_content()
        elif self.current_tab == "abilities":
            self._create_abilities_content()
        elif self.current_tab == "quests":
            self._create_quests_content()
        elif self.current_tab == "spells":
            self._create_spells_content()

    # =========================================================================
    # Inventory Tab
    # =========================================================================

    def _create_inventory_content(self):
        """Создаёт содержимое вкладки инвентаря."""
        # Сетка слотов 5x4
        cols = 5
        rows = 4
        slot_size = 0.12
        padding = 0.02
        start_x = -0.5
        start_y = 0.32

        for row in range(rows):
            for col in range(cols):
                slot_index = row * cols + col
                x = start_x + col * (slot_size + padding)
                y = start_y - row * (slot_size + padding)

                self._create_inventory_slot(slot_index, x, y, slot_size)

    def _create_inventory_slot(self, index: int, x: float, y: float, size: float):
        """Создаёт один слот инвентаря."""
        has_item = index < len(self.inventory_items)
        item = self.inventory_items[index] if has_item else None

        # Цвет слота
        if has_item:
            rarity = item.get("rarity", "common")
            border_color = self.RARITY_COLORS.get(rarity, (0.3, 0.3, 0.35, 1))
            bg_color = (0.2, 0.25, 0.2, 1)
        else:
            border_color = (0.25, 0.25, 0.3, 1)
            bg_color = (0.15, 0.15, 0.18, 0.5)

        # Фрейм слота
        slot_frame = DirectFrame(
            frameColor=border_color,
            frameSize=(-size/2, size/2, -size/2, size/2),
            pos=(x, 0, y),
            parent=self.content_frame,
        )

        # Внутренний фон
        inner = DirectButton(
            frameColor=bg_color,
            frameSize=(-size/2 + 0.005, size/2 - 0.005, -size/2 + 0.005, size/2 - 0.005),
            pos=(0, 0, 0),
            parent=slot_frame,
            command=self._on_inventory_slot_click,
            extraArgs=[index],
        )

        # События
        inner.bind(DGG.ENTER, self._on_inventory_hover, [index])
        inner.bind(DGG.EXIT, self._on_slot_unhover)
        inner.bind(DGG.B3PRESS, self._on_inventory_right_click, [index])

        if has_item:
            # Название
            name = item.get("name", "???")
            if len(name) > 8:
                name = name[:7] + ".."

            DirectLabel(
                text=name,
                text_scale=0.025,
                text_fg=(1, 1, 1, 1),
                frameColor=(0, 0, 0, 0),
                pos=(0, 0, 0),
                parent=slot_frame,
            )

            # Количество
            count = item.get("count", 1)
            if count > 1:
                DirectLabel(
                    text=str(count),
                    text_scale=0.022,
                    text_fg=(1, 1, 0.7, 1),
                    text_align=TextNode.ARight,
                    frameColor=(0, 0, 0, 0),
                    pos=(size/2 - 0.01, 0, -size/2 + 0.015),
                    parent=slot_frame,
                )

    def _on_inventory_slot_click(self, index: int):
        """Клик по слоту инвентаря."""
        self._hide_tooltip()

        if index < len(self.inventory_items):
            item = self.inventory_items[index]
            category = item.get("category", "misc")

            # Если это экипировка, экипируем
            if category in ("armor", "weapon", "accessory", "equipment"):
                self.event_manager.post("client_equip_item", {
                    "inventory_slot": index,
                })

    def _on_inventory_hover(self, index: int, event):
        """Наведение на слот инвентаря."""
        if index < len(self.inventory_items):
            item = self.inventory_items[index]
            self._show_tooltip(item)

    def _on_inventory_right_click(self, index: int, event):
        """ПКМ по слоту инвентаря."""
        if index < len(self.inventory_items):
            # TODO: Контекстное меню
            pass

    # =========================================================================
    # Equipment Tab
    # =========================================================================

    def _create_equipment_content(self):
        """Создаёт содержимое вкладки экипировки."""
        slot_positions = {
            EquipmentSlot.HEAD.value: (0, 0.32),
            EquipmentSlot.CHEST.value: (0, 0.16),
            EquipmentSlot.AMULET.value: (-0.18, 0.16),
            EquipmentSlot.CLOAK.value: (0.18, 0.16),
            EquipmentSlot.HANDS.value: (0, 0.0),
            EquipmentSlot.RING_1.value: (-0.18, 0.0),
            EquipmentSlot.RING_2.value: (0.18, 0.0),
            EquipmentSlot.OFF_HAND.value: (-0.18, -0.16),
            EquipmentSlot.BELT.value: (0, -0.16),
            EquipmentSlot.MAIN_HAND.value: (0.18, -0.16),
            EquipmentSlot.LEGS.value: (0, -0.32),
            EquipmentSlot.FEET.value: (0, -0.48),
        }

        slot_size = 0.12

        for slot_value, (x, y) in slot_positions.items():
            self._create_equipment_slot(slot_value, x, y, slot_size)

        # Информация о персонаже справа
        self._create_equipment_stats()

    def _create_equipment_slot(self, slot_value: str, x: float, y: float, size: float):
        """Создаёт слот экипировки."""
        item = self.equipment_slots.get(slot_value)
        slot_enum = None
        for s in EquipmentSlot:
            if s.value == slot_value:
                slot_enum = s
                break

        slot_info = SLOT_INFO.get(slot_enum, {}) if slot_enum else {}
        slot_name = slot_info.get("name_ru", slot_value)

        # Цвета
        if item:
            rarity = item.get("rarity", "common")
            border_color = self.RARITY_COLORS.get(rarity, (0.3, 0.5, 0.3, 1))
            bg_color = (0.2, 0.3, 0.25, 1)
        else:
            border_color = (0.25, 0.25, 0.3, 1)
            bg_color = (0.12, 0.12, 0.15, 0.8)

        # Фрейм
        slot_frame = DirectFrame(
            frameColor=border_color,
            frameSize=(-size/2, size/2, -size/2, size/2),
            pos=(x, 0, y),
            parent=self.content_frame,
        )

        # Внутренний фон
        inner = DirectButton(
            frameColor=bg_color,
            frameSize=(-size/2 + 0.005, size/2 - 0.005, -size/2 + 0.005, size/2 - 0.005),
            pos=(0, 0, 0),
            parent=slot_frame,
            command=self._on_equipment_slot_click,
            extraArgs=[slot_value],
        )

        # События
        inner.bind(DGG.ENTER, self._on_equipment_hover, [slot_value])
        inner.bind(DGG.EXIT, self._on_slot_unhover)
        inner.bind(DGG.B3PRESS, self._on_equipment_right_click, [slot_value])

        if item:
            # Название предмета
            name = item.get("name", "???")
            if len(name) > 8:
                name = name[:7] + ".."

            DirectLabel(
                text=name,
                text_scale=0.022,
                text_fg=(1, 1, 1, 1),
                frameColor=(0, 0, 0, 0),
                pos=(0, 0, 0),
                parent=slot_frame,
            )
        else:
            # Название слота
            DirectLabel(
                text=slot_name,
                text_scale=0.018,
                text_fg=(0.5, 0.5, 0.5, 1),
                frameColor=(0, 0, 0, 0),
                pos=(0, 0, 0),
                parent=slot_frame,
            )

    def _create_equipment_stats(self):
        """Создаёт панель статов справа от манекена."""
        stats = self.character_data.get("stats", {})

        # Панель справа
        panel_x = 0.5

        DirectLabel(
            text="Боевые статы",
            text_scale=0.035,
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            pos=(panel_x, 0, 0.32),
            parent=self.content_frame,
        )

        # AC
        ac = stats.get("armor_class", 10)
        DirectLabel(
            text=f"КД: {ac}",
            text_scale=0.03,
            text_fg=(0.7, 0.9, 0.7, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(panel_x - 0.12, 0, 0.22),
            parent=self.content_frame,
        )

        # HP
        hp = stats.get("current_hp", 10)
        max_hp = stats.get("max_hp", 10)
        temp_hp = stats.get("temp_hp", 0)
        hp_text = f"HP: {hp}/{max_hp}"
        if temp_hp > 0:
            hp_text += f" (+{temp_hp})"
        DirectLabel(
            text=hp_text,
            text_scale=0.03,
            text_fg=(0.9, 0.4, 0.4, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(panel_x - 0.12, 0, 0.14),
            parent=self.content_frame,
        )

        # Скорость
        speed = stats.get("base_speed", 30)
        DirectLabel(
            text=f"Скорость: {speed} фт.",
            text_scale=0.025,
            text_fg=(0.7, 0.7, 0.9, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(panel_x - 0.12, 0, 0.06),
            parent=self.content_frame,
        )

        # Hit Dice
        hit_dice_current = stats.get("hit_dice_current", 1)
        hit_dice_max = stats.get("hit_dice_max", 1)
        hit_die = stats.get("hit_die", "d8")
        DirectLabel(
            text=f"Кости хитов: {hit_dice_current}/{hit_dice_max}{hit_die}",
            text_scale=0.022,
            text_fg=(0.6, 0.6, 0.8, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(panel_x - 0.12, 0, -0.02),
            parent=self.content_frame,
        )

    def _on_equipment_slot_click(self, slot_value: str):
        """Клик по слоту экипировки — снять предмет."""
        self._hide_tooltip()

        if slot_value in self.equipment_slots and self.equipment_slots[slot_value]:
            self.event_manager.post("client_unequip_item", {
                "equipment_slot": slot_value,
            })

    def _on_equipment_hover(self, slot_value: str, event):
        """Наведение на слот экипировки."""
        item = self.equipment_slots.get(slot_value)
        if item:
            self._show_tooltip(item)

    def _on_equipment_right_click(self, slot_value: str, event):
        """ПКМ по слоту экипировки."""
        pass

    # =========================================================================
    # Description Tab
    # =========================================================================

    def _create_description_content(self):
        """Создаёт содержимое вкладки описания."""
        desc = self.character_data.get("description", {})

        # Заголовок
        DirectLabel(
            text="Описание персонажа",
            text_scale=0.04,
            text_fg=(0.9, 0.9, 0.9, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.34),
            parent=self.content_frame,
        )

        DirectLabel(
            text="(Это описание видят другие игроки)",
            text_scale=0.025,
            text_fg=(0.6, 0.6, 0.6, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.28),
            parent=self.content_frame,
        )

        # Метка
        DirectLabel(
            text="Описание:",
            text_scale=0.028,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.7, 0, 0.18),
            parent=self.content_frame,
        )

        # Получаем текст описания - либо из нового поля, либо собираем из старых
        description_text = desc.get("text", "")
        if not description_text:
            # Собираем из старых полей для совместимости
            parts = []
            if desc.get("appearance"):
                parts.append(desc.get("appearance"))
            if desc.get("age"):
                parts.append(f"Возраст: {desc.get('age')}")
            if desc.get("build"):
                parts.append(f"Телосложение: {desc.get('build')}")
            if desc.get("features"):
                parts.append(f"Особые приметы: {desc.get('features')}")
            if desc.get("demeanor"):
                parts.append(f"Манера поведения: {desc.get('demeanor')}")
            description_text = "\n".join(parts)

        # Фрейм для многострочного текста
        from direct.gui.DirectGui import DirectScrolledFrame

        # Скроллящаяся рамка для текстового поля
        scroll_frame = DirectScrolledFrame(
            frameColor=(0.15, 0.15, 0.18, 1),
            frameSize=(-0.72, 0.72, -0.55, 0.1),
            canvasSize=(-0.7, 0.65, -1.5, 0.08),
            scrollBarWidth=0.025,
            pos=(0, 0, 0),
            parent=self.content_frame,
        )

        canvas = scroll_frame.getCanvas()

        # Многострочное поле ввода
        self._description_entry = DirectEntry(
            text=description_text,
            scale=0.03,
            width=45,
            numLines=20,
            pos=(-0.68, 0, 0.05),
            parent=canvas,
            frameColor=(0.12, 0.12, 0.15, 1),
            text_fg=(1, 1, 1, 1),
            focusInCommand=self._on_entry_focus_in,
            focusOutCommand=self._on_description_focus_out,
        )

        # Кнопка сохранения в стиле BG1
        BG1ButtonSmall.create(
            parent=self.content_frame,
            text="Сохранить",
            command=self._save_description,
            pos=(0, 0, -0.62),
        )

    def _on_description_focus_out(self):
        """Выход из поля описания."""
        self._on_entry_focus_out()

    def _save_description(self):
        """Сохраняет описание персонажа."""
        if hasattr(self, '_description_entry') and self._description_entry:
            text = self._description_entry.get()
            self.event_manager.post("client_update_description", {
                "field": "text",
                "value": text,
            })

    def _on_entry_focus_in(self):
        """Вход в поле ввода."""
        self.ignore("i")
        self.ignore("escape")

    def _on_entry_focus_out(self):
        """Выход из поля ввода."""
        self.accept("i", self.toggle_character_sheet)
        self.accept("escape", self.on_escape)

    # =========================================================================
    # Stats Tab
    # =========================================================================

    def _create_stats_content(self):
        """Создаёт содержимое вкладки характеристик."""
        stats = self.character_data.get("stats", {})
        abilities_data = self.character_data.get("abilities", {})
        saving_throws = self.character_data.get("saving_throws", {})

        # Основные характеристики (6 штук в ряд)
        DirectLabel(
            text="Характеристики",
            text_scale=0.035,
            text_fg=(0.9, 0.8, 0.6, 1),
            frameColor=(0, 0, 0, 0),
            pos=(-0.5, 0, 0.34),
            parent=self.content_frame,
        )

        abilities_order = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
        x_start = -0.6
        for i, ability in enumerate(abilities_order):
            data = abilities_data.get(ability, {"value": 10, "modifier": 0})
            value = data.get("value", 10)
            mod = data.get("modifier", 0)
            name = self.ABILITY_NAMES.get(ability, ability[:3].upper())
            x = x_start + i * 0.2
            self._create_ability_display(name, value, mod, x, 0.22)

        # Спасброски
        DirectLabel(
            text="Спасброски",
            text_scale=0.035,
            text_fg=(0.9, 0.8, 0.6, 1),
            frameColor=(0, 0, 0, 0),
            pos=(-0.5, 0, 0.02),
            parent=self.content_frame,
        )

        y = -0.08
        col = 0
        for ability in abilities_order:
            save_data = saving_throws.get(ability, {"modifier": 0, "proficient": False})
            mod = save_data.get("modifier", 0)
            prof = save_data.get("proficient", False)
            name = self.ABILITY_FULL_NAMES.get(ability, ability)

            x = -0.6 + col * 0.45
            self._create_save_display(name, mod, prof, x, y)

            col += 1
            if col >= 3:
                col = 0
                y -= 0.08

        # Производные статы справа
        self._create_derived_stats(stats)

    def _create_ability_display(self, name: str, value: int, mod: int, x: float, y: float):
        """Создаёт отображение характеристики."""
        # Фон
        DirectFrame(
            frameColor=(0.15, 0.15, 0.2, 1),
            frameSize=(-0.08, 0.08, -0.1, 0.06),
            pos=(x, 0, y),
            parent=self.content_frame,
        )

        # Название
        DirectLabel(
            text=name,
            text_scale=0.025,
            text_fg=(0.7, 0.7, 0.7, 1),
            frameColor=(0, 0, 0, 0),
            pos=(x, 0, y + 0.035),
            parent=self.content_frame,
        )

        # Значение
        DirectLabel(
            text=str(value),
            text_scale=0.045,
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            pos=(x, 0, y - 0.015),
            parent=self.content_frame,
        )

        # Модификатор
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        mod_color = (0.5, 0.9, 0.5, 1) if mod >= 0 else (0.9, 0.5, 0.5, 1)
        DirectLabel(
            text=mod_str,
            text_scale=0.028,
            text_fg=mod_color,
            frameColor=(0, 0, 0, 0),
            pos=(x, 0, y - 0.07),
            parent=self.content_frame,
        )

    def _create_save_display(self, name: str, mod: int, proficient: bool, x: float, y: float):
        """Создаёт отображение спасброска."""
        # Кружок владения
        prof_color = (0.3, 0.8, 0.3, 1) if proficient else (0.3, 0.3, 0.35, 1)
        DirectFrame(
            frameColor=prof_color,
            frameSize=(-0.012, 0.012, -0.012, 0.012),
            pos=(x, 0, y),
            parent=self.content_frame,
        )

        # Модификатор
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        DirectLabel(
            text=mod_str,
            text_scale=0.025,
            text_fg=(0.9, 0.9, 0.9, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(x + 0.03, 0, y - 0.008),
            parent=self.content_frame,
        )

        # Название
        DirectLabel(
            text=name,
            text_scale=0.022,
            text_fg=(0.7, 0.7, 0.7, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(x + 0.08, 0, y - 0.008),
            parent=self.content_frame,
        )

    def _create_derived_stats(self, stats: dict):
        """Создаёт панель производных статов под спасбросками."""
        # Заголовок под спасбросками
        DirectLabel(
            text="Производные характеристики",
            text_scale=0.03,
            text_fg=(0.9, 0.8, 0.6, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.6, 0, -0.28),
            parent=self.content_frame,
        )

        prof_bonus = stats.get("proficiency_bonus", 2)
        hp = stats.get("current_hp", 10)
        max_hp = stats.get("max_hp", 10)
        temp_hp = stats.get("temp_hp", 0)
        speed = stats.get("base_speed", 30)
        ac = stats.get("armor_class", 10)
        initiative = stats.get("initiative", 0)
        passive_perception = stats.get("passive_perception", 10)

        # Левая колонка
        left_col = [
            ("Бонус мастерства", f"+{prof_bonus}"),
            ("Класс доспеха", str(ac)),
            ("Инициатива", f"+{initiative}" if initiative >= 0 else str(initiative)),
        ]

        # Правая колонка
        right_col = [
            ("Здоровье", f"{hp}/{max_hp}" + (f" (+{temp_hp})" if temp_hp > 0 else "")),
            ("Скорость", f"{speed} фт."),
            ("Пассивное восприятие", str(passive_perception)),
        ]

        y = -0.36
        for label, value in left_col:
            DirectLabel(
                text=f"{label}: {value}",
                text_scale=0.024,
                text_fg=(0.8, 0.8, 0.8, 1),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                pos=(-0.6, 0, y),
                parent=self.content_frame,
            )
            y -= 0.055

        y = -0.36
        for label, value in right_col:
            DirectLabel(
                text=f"{label}: {value}",
                text_scale=0.024,
                text_fg=(0.8, 0.8, 0.8, 1),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                pos=(0.1, 0, y),
                parent=self.content_frame,
            )
            y -= 0.055

    # =========================================================================
    # Skills Tab
    # =========================================================================

    def _create_skills_content(self):
        """Создаёт содержимое вкладки навыков."""
        skills_data = self.character_data.get("skills", {})

        DirectLabel(
            text="Навыки",
            text_scale=0.04,
            text_fg=(0.9, 0.8, 0.6, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.34),
            parent=self.content_frame,
        )

        # Навыки по колонкам (2 колонки по 9 навыков)
        skills_list = list(self.SKILL_NAMES.keys())
        y_start = 0.22
        row_height = 0.065

        for i, skill_en in enumerate(skills_list):
            skill_ru = self.SKILL_NAMES[skill_en]
            skill_data = skills_data.get(skill_en, {"modifier": 0, "proficient": False})
            mod = skill_data.get("modifier", 0)
            prof = skill_data.get("proficient", False)
            ability = skill_data.get("ability", "")

            col = i // 9
            row = i % 9
            x = -0.55 + col * 0.75
            y = y_start - row * row_height

            self._create_skill_display(skill_ru, ability, mod, prof, x, y)

    def _create_skill_display(self, name: str, ability: str, mod: int, proficient: bool, x: float, y: float):
        """Создаёт отображение навыка."""
        # Кружок владения
        prof_color = (0.3, 0.8, 0.3, 1) if proficient else (0.3, 0.3, 0.35, 1)
        DirectFrame(
            frameColor=prof_color,
            frameSize=(-0.012, 0.012, -0.012, 0.012),
            pos=(x, 0, y),
            parent=self.content_frame,
        )

        # Модификатор
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        DirectLabel(
            text=mod_str,
            text_scale=0.028,
            text_fg=(0.9, 0.9, 0.9, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(x + 0.03, 0, y - 0.008),
            parent=self.content_frame,
        )

        # Название навыка
        DirectLabel(
            text=name,
            text_scale=0.024,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(x + 0.09, 0, y - 0.008),
            parent=self.content_frame,
        )

        # Связанная характеристика (маленьким шрифтом)
        if ability:
            ability_short = self.ABILITY_NAMES.get(ability, ability[:3].upper())
            DirectLabel(
                text=f"({ability_short})",
                text_scale=0.018,
                text_fg=(0.5, 0.5, 0.5, 1),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                pos=(x + 0.35, 0, y - 0.008),
                parent=self.content_frame,
            )

    # =========================================================================
    # Abilities Tab (Features)
    # =========================================================================

    def _create_abilities_content(self):
        """Создаёт содержимое вкладки способностей."""
        features = self.character_data.get("features", {})

        # Handle case where features is a list instead of dict
        if isinstance(features, list):
            # Convert list to dict format
            racial = []
            class_features = features  # Assume list contains class features
            background = []
        else:
            racial = features.get("racial", [])
            class_features = features.get("class", [])
            background = features.get("background", [])

        # Скроллящийся фрейм
        scroll_frame = DirectScrolledFrame(
            frameColor=(0.1, 0.1, 0.14, 0),
            frameSize=(-0.75, 0.75, -0.65, 0.35),
            canvasSize=(-0.7, 0.7, -2.0, 0.3),
            scrollBarWidth=0.03,
            verticalScroll_frameColor=(0.3, 0.3, 0.35, 1),
            verticalScroll_thumb_frameColor=(0.5, 0.5, 0.55, 1),
            pos=(0, 0, 0),
            parent=self.content_frame,
        )

        canvas = scroll_frame.getCanvas()
        y = 0.25

        # Расовые способности
        if racial:
            y = self._create_feature_section(canvas, "Расовые особенности", racial, y)

        # Классовые способности
        if class_features:
            y = self._create_feature_section(canvas, "Классовые способности", class_features, y)

        # Способности предыстории
        if background:
            y = self._create_feature_section(canvas, "Предыстория", background, y)

        # Владения
        proficiencies = self.character_data.get("proficiencies", {})
        if proficiencies:
            y = self._create_proficiencies_section(canvas, proficiencies, y)

        # Обновляем размер canvas
        scroll_frame["canvasSize"] = (-0.7, 0.7, y - 0.1, 0.3)

    def _create_feature_section(self, parent, title: str, features: list, y: float) -> float:
        """Создаёт секцию способностей."""
        # Заголовок секции
        DirectLabel(
            text=title,
            text_scale=0.035,
            text_fg=(0.9, 0.8, 0.6, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.65, 0, y),
            parent=parent,
        )
        y -= 0.06

        for feature in features:
            name = feature.get("name", "Неизвестно")
            description = feature.get("description", "")

            # Название способности
            DirectLabel(
                text=f"• {name}",
                text_scale=0.028,
                text_fg=(0.8, 0.9, 0.8, 1),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                pos=(-0.6, 0, y),
                parent=parent,
            )
            y -= 0.04

            # Описание
            if description:
                DirectLabel(
                    text=description,
                    text_scale=0.022,
                    text_fg=(0.6, 0.6, 0.6, 1),
                    text_align=TextNode.ALeft,
                    text_wordwrap=50,
                    frameColor=(0, 0, 0, 0),
                    pos=(-0.55, 0, y),
                    parent=parent,
                )
                # Приблизительная высота текста
                lines = len(description) // 50 + 1
                y -= 0.03 * lines + 0.02

        y -= 0.04
        return y

    def _create_proficiencies_section(self, parent, proficiencies: dict, y: float) -> float:
        """Создаёт секцию владений."""
        DirectLabel(
            text="Владения",
            text_scale=0.035,
            text_fg=(0.9, 0.8, 0.6, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.65, 0, y),
            parent=parent,
        )
        y -= 0.06

        categories = [
            ("armor", "Доспехи"),
            ("weapons", "Оружие"),
            ("tools", "Инструменты"),
            ("languages", "Языки"),
        ]

        for key, label in categories:
            items = proficiencies.get(key, [])
            if items:
                items_text = ", ".join(items)
                DirectLabel(
                    text=f"{label}: {items_text}",
                    text_scale=0.022,
                    text_fg=(0.7, 0.7, 0.7, 1),
                    text_align=TextNode.ALeft,
                    text_wordwrap=55,
                    frameColor=(0, 0, 0, 0),
                    pos=(-0.6, 0, y),
                    parent=parent,
                )
                lines = len(items_text) // 55 + 1
                y -= 0.03 * lines + 0.02

        return y

    # =========================================================================
    # Quests Tab
    # =========================================================================

    def _create_quests_content(self):
        """Создаёт содержимое вкладки квестов."""
        DirectLabel(
            text="Журнал квестов",
            text_scale=0.04,
            text_fg=(0.9, 0.8, 0.6, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.34),
            parent=self.content_frame,
        )

        # Фильтр по статусам
        filter_y = 0.26
        filters = [
            ("active", "В процессе"),
            ("completed", "Готов к сдаче"),
            ("available", "Доступен"),
        ]

        # Скроллящийся список квестов
        scroll_frame = DirectScrolledFrame(
            frameColor=(0.12, 0.12, 0.15, 1),
            frameSize=(-0.75, 0.75, -0.65, 0.2),
            canvasSize=(-0.7, 0.7, -2.0, 0.15),
            scrollBarWidth=0.03,
            verticalScroll_frameColor=(0.3, 0.3, 0.35, 1),
            verticalScroll_thumb_frameColor=(0.5, 0.5, 0.55, 1),
            pos=(0, 0, 0),
            parent=self.content_frame,
        )

        canvas = scroll_frame.getCanvas()
        y = 0.1

        if not self.quests_data:
            DirectLabel(
                text="У вас нет квестов",
                text_scale=0.03,
                text_fg=(0.5, 0.5, 0.5, 1),
                frameColor=(0, 0, 0, 0),
                pos=(0, 0, -0.3),
                parent=canvas,
            )
        else:
            # Группируем квесты по статусу
            active_quests = [q for q in self.quests_data if q.get("status") == "active"]
            completed_quests = [q for q in self.quests_data if q.get("status") == "completed"]
            available_quests = [q for q in self.quests_data if q.get("status") == "available"]

            # Активные квесты
            if active_quests:
                DirectLabel(
                    text="В процессе",
                    text_scale=0.032,
                    text_fg=(0.8, 0.9, 0.8, 1),
                    text_align=TextNode.ALeft,
                    frameColor=(0, 0, 0, 0),
                    pos=(-0.65, 0, y),
                    parent=canvas,
                )
                y -= 0.05

                for quest in active_quests:
                    y = self._create_quest_entry(canvas, quest, y)
                y -= 0.05

            # Готов к сдаче
            if completed_quests:
                DirectLabel(
                    text="Готов к сдаче",
                    text_scale=0.032,
                    text_fg=(0.9, 0.9, 0.6, 1),
                    text_align=TextNode.ALeft,
                    frameColor=(0, 0, 0, 0),
                    pos=(-0.65, 0, y),
                    parent=canvas,
                )
                y -= 0.05

                for quest in completed_quests:
                    y = self._create_quest_entry(canvas, quest, y)
                y -= 0.05

            # Доступные квесты
            if available_quests:
                DirectLabel(
                    text="Доступен",
                    text_scale=0.032,
                    text_fg=(0.7, 0.7, 0.9, 1),
                    text_align=TextNode.ALeft,
                    frameColor=(0, 0, 0, 0),
                    pos=(-0.65, 0, y),
                    parent=canvas,
                )
                y -= 0.05

                for quest in available_quests:
                    y = self._create_quest_entry(canvas, quest, y)
                y -= 0.05

        scroll_frame["canvasSize"] = (-0.7, 0.7, y - 0.1, 0.15)

    def _create_quest_entry(self, parent, quest: dict, y: float) -> float:
        """Создаёт запись квеста."""
        quest_name = quest.get("name", "Неизвестный квест")
        quest_desc = quest.get("description", "")
        objectives = quest.get("objectives", [])

        # Название квеста
        DirectLabel(
            text=f"• {quest_name}",
            text_scale=0.028,
            text_fg=(0.9, 0.9, 0.9, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.6, 0, y),
            parent=parent,
        )
        y -= 0.04

        # Описание
        if quest_desc:
            DirectLabel(
                text=quest_desc,
                text_scale=0.02,
                text_fg=(0.6, 0.6, 0.6, 1),
                text_align=TextNode.ALeft,
                text_wordwrap=55,
                frameColor=(0, 0, 0, 0),
                pos=(-0.55, 0, y),
                parent=parent,
            )
            lines = len(quest_desc) // 55 + 1
            y -= 0.025 * lines + 0.01

        # Цели
        if objectives:
            for obj in objectives:
                obj_desc = obj.get("description", "")
                current = obj.get("current", 0)
                target = obj.get("target", 1)
                completed = obj.get("completed", False)

                status_color = (0.5, 0.9, 0.5, 1) if completed else (0.7, 0.7, 0.7, 1)
                status_mark = "✓" if completed else "○"

                DirectLabel(
                    text=f"  {status_mark} {obj_desc} ({current}/{target})",
                    text_scale=0.022,
                    text_fg=status_color,
                    text_align=TextNode.ALeft,
                    frameColor=(0, 0, 0, 0),
                    pos=(-0.52, 0, y),
                    parent=parent,
                )
                y -= 0.035

        y -= 0.02
        return y

    # =========================================================================
    # Spells Tab
    # =========================================================================

    def _create_spells_content(self):
        """Создаёт содержимое вкладки заклинаний."""
        spellcasting = self.character_data.get("spellcasting")

        # Проверяем наличие spellcasting данных
        # Сервер присылает None для не-заклинателей или объект с данными
        if not spellcasting:
            DirectLabel(
                text="Нет способности к магии",
                text_scale=0.04,
                text_fg=(0.5, 0.5, 0.5, 1),
                frameColor=(0, 0, 0, 0),
                pos=(0, 0, 0.1),
                parent=self.content_frame,
            )
            DirectLabel(
                text="Этот персонаж не умеет творить заклинания.",
                text_scale=0.025,
                text_fg=(0.4, 0.4, 0.4, 1),
                frameColor=(0, 0, 0, 0),
                pos=(0, 0, 0.0),
                parent=self.content_frame,
            )
            return

        # Базовая магическая характеристика
        ability = spellcasting.get("ability", spellcasting.get("spellcasting_ability", ""))
        ability_name = self.ABILITY_FULL_NAMES.get(ability, ability)
        spell_save_dc = spellcasting.get("spell_save_dc", 10)
        spell_attack = spellcasting.get("spell_attack", spellcasting.get("spell_attack_bonus", 0))

        DirectLabel(
            text="Заклинания",
            text_scale=0.04,
            text_fg=(0.9, 0.8, 0.6, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.34),
            parent=self.content_frame,
        )

        # Магические статы
        DirectLabel(
            text=f"Базовая характеристика: {ability_name}",
            text_scale=0.025,
            text_fg=(0.7, 0.7, 0.7, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.7, 0, 0.26),
            parent=self.content_frame,
        )

        DirectLabel(
            text=f"Сложность спасброска: {spell_save_dc}",
            text_scale=0.025,
            text_fg=(0.7, 0.7, 0.7, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.7, 0, 0.20),
            parent=self.content_frame,
        )

        atk_str = f"+{spell_attack}" if spell_attack >= 0 else str(spell_attack)
        DirectLabel(
            text=f"Бонус атаки заклинанием: {atk_str}",
            text_scale=0.025,
            text_fg=(0.7, 0.7, 0.7, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.7, 0, 0.14),
            parent=self.content_frame,
        )

        # Ячейки заклинаний
        slots_current = spellcasting.get("spell_slots_current", spellcasting.get("slots_current", {}))
        slots_max = spellcasting.get("spell_slots_max", spellcasting.get("slots_max", {}))

        if slots_max:
            DirectLabel(
                text="Ячейки заклинаний",
                text_scale=0.03,
                text_fg=(0.8, 0.8, 0.8, 1),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                pos=(-0.7, 0, 0.04),
                parent=self.content_frame,
            )

            x = -0.65
            for level in range(1, 10):
                level_str = str(level)
                max_slots = slots_max.get(level_str, 0)
                if max_slots > 0:
                    current = slots_current.get(level_str, 0)
                    self._create_spell_slot_display(level, current, max_slots, x, -0.06)
                    x += 0.15

        # Известные/подготовленные заклинания
        spells_known = spellcasting.get("spells_known", [])
        spells_prepared = spellcasting.get("spells_prepared", [])

        # Скроллящийся список заклинаний
        scroll_frame = DirectScrolledFrame(
            frameColor=(0.12, 0.12, 0.15, 1),
            frameSize=(-0.75, 0.75, -0.65, -0.18),
            canvasSize=(-0.7, 0.7, -1.5, 0),
            scrollBarWidth=0.03,
            verticalScroll_frameColor=(0.3, 0.3, 0.35, 1),
            verticalScroll_thumb_frameColor=(0.5, 0.5, 0.55, 1),
            pos=(0, 0, 0),
            parent=self.content_frame,
        )

        canvas = scroll_frame.getCanvas()
        y = -0.05

        if spells_prepared:
            DirectLabel(
                text="Подготовленные заклинания",
                text_scale=0.028,
                text_fg=(0.8, 0.9, 0.8, 1),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                pos=(-0.65, 0, y),
                parent=canvas,
            )
            y -= 0.05

            for spell in spells_prepared:
                spell_name = spell if isinstance(spell, str) else spell.get("name", "???")
                DirectLabel(
                    text=f"• {spell_name}",
                    text_scale=0.024,
                    text_fg=(0.7, 0.9, 0.7, 1),
                    text_align=TextNode.ALeft,
                    frameColor=(0, 0, 0, 0),
                    pos=(-0.6, 0, y),
                    parent=canvas,
                )
                y -= 0.04

            y -= 0.03

        if spells_known:
            DirectLabel(
                text="Известные заклинания",
                text_scale=0.028,
                text_fg=(0.8, 0.8, 0.9, 1),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                pos=(-0.65, 0, y),
                parent=canvas,
            )
            y -= 0.05

            for spell in spells_known:
                spell_name = spell if isinstance(spell, str) else spell.get("name", "???")
                DirectLabel(
                    text=f"• {spell_name}",
                    text_scale=0.024,
                    text_fg=(0.7, 0.7, 0.9, 1),
                    text_align=TextNode.ALeft,
                    frameColor=(0, 0, 0, 0),
                    pos=(-0.6, 0, y),
                    parent=canvas,
                )
                y -= 0.04

        scroll_frame["canvasSize"] = (-0.7, 0.7, y - 0.1, 0)

    def _create_spell_slot_display(self, level: int, current: int, max_slots: int, x: float, y: float):
        """Создаёт отображение ячеек заклинаний."""
        # Уровень
        DirectLabel(
            text=str(level),
            text_scale=0.025,
            text_fg=(0.7, 0.7, 0.7, 1),
            frameColor=(0, 0, 0, 0),
            pos=(x + 0.03, 0, y + 0.03),
            parent=self.content_frame,
        )

        # Индикаторы ячеек
        for i in range(max_slots):
            filled = i < current
            color = (0.4, 0.7, 0.9, 1) if filled else (0.2, 0.2, 0.25, 1)
            DirectFrame(
                frameColor=color,
                frameSize=(-0.012, 0.012, -0.012, 0.012),
                pos=(x + i * 0.025, 0, y),
                parent=self.content_frame,
            )

    # =========================================================================
    # Tooltip
    # =========================================================================

    def _show_tooltip(self, item: dict):
        """Показывает tooltip для предмета."""
        self._hide_tooltip()

        # Получаем данные
        name = item.get("name", "???")
        tooltip_text = item.get("tooltip", "")
        rarity = item.get("rarity", "common")

        name_color = self.RARITY_COLORS.get(rarity, (1, 1, 1, 1))

        # Позиция около мыши
        if hasattr(self.app, 'mouseWatcherNode'):
            if self.app.mouseWatcherNode.hasMouse():
                mx = self.app.mouseWatcherNode.getMouseX()
                my = self.app.mouseWatcherNode.getMouseY()
            else:
                mx, my = 0.3, 0.1
        else:
            mx, my = 0.3, 0.1

        # Размер tooltip
        lines = tooltip_text.split("\n") if tooltip_text else [name]
        height = 0.04 + len(lines) * 0.03

        self.tooltip_frame = DirectFrame(
            frameColor=(0.05, 0.05, 0.08, 0.95),
            frameSize=(-0.18, 0.18, -height, 0.04),
            pos=(mx + 0.2, 0, my),
            parent=self.app.aspect2d,
            sortOrder=1000,
        )

        # Название
        DirectLabel(
            text=name,
            text_scale=0.03,
            text_fg=name_color,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.16, 0, 0.01),
            parent=self.tooltip_frame,
        )

        # Текст tooltip
        if tooltip_text:
            DirectLabel(
                text=tooltip_text,
                text_scale=0.022,
                text_fg=(0.8, 0.8, 0.8, 1),
                text_align=TextNode.ALeft,
                text_wordwrap=14,
                frameColor=(0, 0, 0, 0),
                pos=(-0.16, 0, -0.04),
                parent=self.tooltip_frame,
            )

    def _hide_tooltip(self):
        """Скрывает tooltip."""
        if self.tooltip_frame:
            self.tooltip_frame.destroy()
            self.tooltip_frame = None

    def _on_slot_unhover(self, event=None):
        """Убрали курсор со слота."""
        self._hide_tooltip()

    def _on_mouse_click(self):
        """Клик мышью."""
        self._hide_tooltip()

    # =========================================================================
    # Cleanup
    # =========================================================================

    def _destroy_ui(self):
        """Уничтожает UI."""
        self._hide_tooltip()
        self.ignore("mouse1")

        if self.drag_frame:
            self.drag_frame.destroy()
            self.drag_frame = None

        if self.main_frame:
            self.main_frame.destroy()
            self.main_frame = None

        self.tab_buttons = {}
        self.content_frame = None
