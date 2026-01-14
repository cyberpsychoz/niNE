"""
Клиентский модуль листа персонажа.

Главный UI с вкладками:
- Инвентарь (с drag & drop)
- Экипировка (слоты на манекене)
- Описание (редактируемое)
- Характеристики (статы D&D)

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

from nine.plugins.inventory.entities.equipment.sh_equipment_slots import EquipmentSlot, SLOT_INFO


class CharacterSheetClientModule(PluginModule, DirectObject):
    """
    Клиентский модуль листа персонажа.

    Объединяет инвентарь, экипировку, описание и статы в одном UI.
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

    def __init__(self, context):
        PluginModule.__init__(self, context)
        DirectObject.__init__(self)

    def on_load(self):
        # Состояние UI
        self.is_open = False
        self.current_tab = "inventory"  # inventory, equipment, description, stats

        # Данные
        self.inventory_items: List[dict] = []
        self.equipment_slots: Dict[str, Optional[dict]] = {}
        self.character_data: dict = {}
        self.max_slots = 20

        # Drag & drop
        self.dragging_item: Optional[dict] = None
        self.dragging_from: Optional[str] = None  # "inventory:0" или "equipment:chest"
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

        # Клавиши
        self.accept("i", self.toggle_character_sheet)
        self.accept("escape", self.on_escape)

        self.logger.info("Клиентский модуль листа персонажа загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("inventory_update", self.on_inventory_update)
        self.event_manager.unsubscribe("equipment_update", self.on_equipment_update)
        self.event_manager.unsubscribe("character_sheet", self.on_character_sheet_update)
        self.event_manager.unsubscribe("game_state_changed", self._on_game_state_changed)
        self.ignoreAll()
        self._destroy_ui()
        self.logger.info("Клиентский модуль листа персонажа выгружен")

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
            if self.current_tab == "description":
                self._refresh_content()
            elif self.current_tab == "stats":
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

    def open_character_sheet(self):
        """Открывает лист персонажа."""
        if self.is_open:
            return

        if hasattr(self.app, 'is_chat_active') and self.app.is_chat_active():
            return

        self.is_open = True

        # Останавливаем камеру
        if hasattr(self.app, 'camera_controller') and self.app.camera_controller:
            self.app.camera_controller.stop()

        self._create_ui()
        self.logger.debug("Лист персонажа открыт")

    def close_character_sheet(self):
        """Закрывает лист персонажа."""
        if not self.is_open:
            return

        self.is_open = False
        self._destroy_ui()

        # Возобновляем камеру
        if hasattr(self.app, 'camera_controller') and self.app.camera_controller:
            self.app.camera_controller.start()

        self.logger.debug("Лист персонажа закрыт")

    def on_escape(self):
        """Escape закрывает UI."""
        if self.is_open:
            self.close_character_sheet()

    # =========================================================================
    # Main UI Creation
    # =========================================================================

    def _create_ui(self):
        """Создаёт основной UI."""
        # Главный фрейм
        self.main_frame = DirectFrame(
            frameColor=(0.08, 0.08, 0.12, 0.98),
            frameSize=(-0.7, 0.7, -0.7, 0.6),
            pos=(0, 0, 0),
            parent=self.app.aspect2d,
        )

        # Заголовок
        name = self.character_data.get("name", "Персонаж")
        DirectLabel(
            text=f"Лист персонажа: {name}",
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.52),
            parent=self.main_frame,
        )

        # Кнопка закрытия
        DirectButton(
            text="X",
            text_scale=0.04,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.6, 0.2, 0.2, 1),
            frameSize=(-0.03, 0.03, -0.025, 0.03),
            pos=(0.64, 0, 0.53),
            parent=self.main_frame,
            command=self.close_character_sheet,
        )

        # Вкладки
        self._create_tabs()

        # Область контента
        self.content_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.14, 1),
            frameSize=(-0.65, 0.65, -0.65, 0.38),
            pos=(0, 0, 0),
            parent=self.main_frame,
        )

        # Загружаем контент текущей вкладки
        self._refresh_content()

        # Клик по фрейму не закрывает UI
        self.accept("mouse1", self._on_mouse_click)

    def _create_tabs(self):
        """Создаёт панель вкладок."""
        tabs = [
            ("inventory", "Инвентарь"),
            ("equipment", "Экипировка"),
            ("description", "Описание"),
            ("stats", "Характеристики"),
        ]

        start_x = -0.5
        for i, (tab_id, tab_name) in enumerate(tabs):
            x = start_x + i * 0.25

            is_active = tab_id == self.current_tab
            color = (0.3, 0.4, 0.5, 1) if is_active else (0.2, 0.2, 0.25, 1)

            btn = DirectButton(
                text=tab_name,
                text_scale=0.035,
                text_fg=(1, 1, 1, 1),
                frameColor=color,
                frameSize=(-0.12, 0.12, -0.025, 0.035),
                pos=(x, 0, 0.43),
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
        start_y = 0.28

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
        # Схема расположения слотов (как манекен)
        #
        #         HEAD
        #   AMULET  CHEST  CLOAK
        #   RING_1  HANDS  RING_2
        #     OFF   BELT   MAIN
        #          LEGS
        #          FEET

        slot_positions = {
            EquipmentSlot.HEAD.value: (0, 0.28),
            EquipmentSlot.CHEST.value: (0, 0.12),
            EquipmentSlot.AMULET.value: (-0.18, 0.12),
            EquipmentSlot.CLOAK.value: (0.18, 0.12),
            EquipmentSlot.HANDS.value: (0, -0.04),
            EquipmentSlot.RING_1.value: (-0.18, -0.04),
            EquipmentSlot.RING_2.value: (0.18, -0.04),
            EquipmentSlot.OFF_HAND.value: (-0.18, -0.20),
            EquipmentSlot.BELT.value: (0, -0.20),
            EquipmentSlot.MAIN_HAND.value: (0.18, -0.20),
            EquipmentSlot.LEGS.value: (0, -0.36),
            EquipmentSlot.FEET.value: (0, -0.52),
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
        panel_x = 0.45

        DirectLabel(
            text="Характеристики",
            text_scale=0.035,
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            pos=(panel_x, 0, 0.28),
            parent=self.content_frame,
        )

        # AC
        ac = 10 + stats.get("dex_mod", 0)  # Базовый расчёт
        DirectLabel(
            text=f"AC: {ac}",
            text_scale=0.03,
            text_fg=(0.7, 0.9, 0.7, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(panel_x - 0.1, 0, 0.18),
            parent=self.content_frame,
        )

        # HP
        hp = stats.get("current_hp", 10)
        max_hp = stats.get("max_hp", 10)
        DirectLabel(
            text=f"HP: {hp}/{max_hp}",
            text_scale=0.03,
            text_fg=(0.9, 0.4, 0.4, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(panel_x - 0.1, 0, 0.10),
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
            pos=(panel_x - 0.1, 0, 0.02),
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
        # TODO: Контекстное меню
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
            pos=(0, 0, 0.3),
            parent=self.content_frame,
        )

        DirectLabel(
            text="(Это описание видят другие игроки)",
            text_scale=0.025,
            text_fg=(0.6, 0.6, 0.6, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.24),
            parent=self.content_frame,
        )

        # Поля описания
        fields = [
            ("appearance", "Внешность", desc.get("appearance", "")),
            ("age", "Возраст", desc.get("age", "")),
            ("build", "Телосложение", desc.get("build", "")),
            ("features", "Особые приметы", desc.get("features", "")),
            ("demeanor", "Манера поведения", desc.get("demeanor", "")),
        ]

        y = 0.15
        for field_id, field_name, field_value in fields:
            self._create_description_field(field_id, field_name, field_value, y)
            y -= 0.18

    def _create_description_field(self, field_id: str, label: str, value: str, y: float):
        """Создаёт поле описания с редактированием."""
        # Метка
        DirectLabel(
            text=f"{label}:",
            text_scale=0.028,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.55, 0, y),
            parent=self.content_frame,
        )

        # Поле ввода
        entry = DirectEntry(
            text=value,
            scale=0.035,
            width=28,
            pos=(-0.55, 0, y - 0.05),
            parent=self.content_frame,
            frameColor=(0.15, 0.15, 0.18, 1),
            text_fg=(1, 1, 1, 1),
            focusInCommand=self._on_entry_focus_in,
            focusOutCommand=self._on_entry_focus_out,
            command=self._on_description_changed,
            extraArgs=[field_id],
        )

        # Сохраняем ссылку для обработки
        entry.setPythonTag("field_id", field_id)

    def _on_entry_focus_in(self):
        """Вход в поле ввода."""
        # Отключаем горячие клавиши
        self.ignore("i")
        self.ignore("escape")

    def _on_entry_focus_out(self):
        """Выход из поля ввода."""
        # Включаем горячие клавиши обратно
        self.accept("i", self.toggle_character_sheet)
        self.accept("escape", self.on_escape)

    def _on_description_changed(self, text: str, field_id: str):
        """Изменение описания."""
        self.event_manager.post("client_update_description", {
            "field": field_id,
            "value": text,
        })

    # =========================================================================
    # Stats Tab
    # =========================================================================

    def _create_stats_content(self):
        """Создаёт содержимое вкладки характеристик."""
        stats = self.character_data.get("stats", {})
        char_class = self.character_data.get("class", "Обыватель")
        race = self.character_data.get("race", "Человек")
        level = stats.get("level", 1)

        # Заголовок
        DirectLabel(
            text=f"{race} {char_class}, {level} уровень",
            text_scale=0.04,
            text_fg=(0.9, 0.9, 0.9, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.3),
            parent=self.content_frame,
        )

        # Основные характеристики
        abilities = [
            ("СИЛ", stats.get("strength", 10), stats.get("str_mod", 0)),
            ("ЛОВ", stats.get("dexterity", 10), stats.get("dex_mod", 0)),
            ("ТЕЛ", stats.get("constitution", 10), stats.get("con_mod", 0)),
            ("ИНТ", stats.get("intelligence", 10), stats.get("int_mod", 0)),
            ("МДР", stats.get("wisdom", 10), stats.get("wis_mod", 0)),
            ("ХАР", stats.get("charisma", 10), stats.get("cha_mod", 0)),
        ]

        x_start = -0.5
        for i, (name, value, mod) in enumerate(abilities):
            x = x_start + i * 0.17
            self._create_ability_display(name, value, mod, x, 0.18)

        # Производные статы
        y = 0.0
        prof_bonus = stats.get("proficiency_bonus", 2)
        hp = stats.get("current_hp", 10)
        max_hp = stats.get("max_hp", 10)
        speed = stats.get("base_speed", 30)

        derived = [
            ("Бонус мастерства", f"+{prof_bonus}"),
            ("Здоровье", f"{hp}/{max_hp}"),
            ("Скорость", f"{speed} фт."),
        ]

        for label, value in derived:
            DirectLabel(
                text=f"{label}: {value}",
                text_scale=0.03,
                text_fg=(0.8, 0.8, 0.8, 1),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                pos=(-0.55, 0, y),
                parent=self.content_frame,
            )
            y -= 0.06

        # Владения
        proficiencies = stats.get("proficiencies", [])
        if proficiencies:
            y -= 0.05
            DirectLabel(
                text="Владения:",
                text_scale=0.028,
                text_fg=(0.7, 0.7, 0.7, 1),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                pos=(-0.55, 0, y),
                parent=self.content_frame,
            )

            y -= 0.04
            prof_text = ", ".join(proficiencies[:5])  # Ограничиваем
            DirectLabel(
                text=prof_text,
                text_scale=0.022,
                text_fg=(0.6, 0.6, 0.6, 1),
                text_align=TextNode.ALeft,
                text_wordwrap=30,
                frameColor=(0, 0, 0, 0),
                pos=(-0.55, 0, y),
                parent=self.content_frame,
            )

    def _create_ability_display(self, name: str, value: int, mod: int, x: float, y: float):
        """Создаёт отображение характеристики."""
        # Фон
        DirectFrame(
            frameColor=(0.15, 0.15, 0.2, 1),
            frameSize=(-0.07, 0.07, -0.08, 0.06),
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
            text_scale=0.04,
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            pos=(x, 0, y - 0.01),
            parent=self.content_frame,
        )

        # Модификатор
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        mod_color = (0.5, 0.9, 0.5, 1) if mod >= 0 else (0.9, 0.5, 0.5, 1)
        DirectLabel(
            text=mod_str,
            text_scale=0.025,
            text_fg=mod_color,
            frameColor=(0, 0, 0, 0),
            pos=(x, 0, y - 0.055),
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
