"""
Клиентский модуль системы инвентаря.
Отображает UI инвентаря и прицел.
"""

from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectLabel, DirectSlider, DGG
)
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode

from nine.core.plugins import PluginModule
from nine.core.game_state import GameState


class InventoryClientModule(PluginModule, DirectObject):
    """Клиентский модуль управления UI инвентаря."""

    def __init__(self, context):
        PluginModule.__init__(self, context)
        DirectObject.__init__(self)

    def on_load(self):
        # Данные инвентаря
        self.inventory_items = []
        self.max_slots = 20
        self.is_open = False

        # UI элементы
        self.inventory_frame = None
        self.slots = []
        self.crosshair = None

        # Tooltip элементы
        self.tooltip_frame = None
        self.tooltip_name = None
        self.tooltip_desc = None
        self.hovered_slot = -1

        # Контекстное меню
        self.context_menu = None
        self.context_slot = -1

        # Диалог выбора количества
        self.drop_dialog = None
        self.drop_slot = -1
        self.drop_count = 1

        # Подписки на события
        self.event_manager.subscribe("inventory_update", self.on_inventory_update)
        self.event_manager.subscribe("game_state_changed", self._on_game_state_changed)

        # Обработка клавиш
        self.accept("i", self.toggle_inventory)
        self.accept("escape", self.on_escape)

        # Создаём прицел (скрытый по умолчанию - мы в меню)
        self._create_crosshair()
        if self.crosshair:
            self.crosshair.hide()

        self.logger.info("Клиентский модуль инвентаря загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("inventory_update", self.on_inventory_update)
        self.event_manager.unsubscribe("game_state_changed", self._on_game_state_changed)
        self.ignoreAll()
        self._destroy_ui()
        if self.crosshair:
            self.crosshair.destroy()
        self.logger.info("Клиентский модуль инвентаря выгружен")

    def _on_game_state_changed(self, data: dict):
        """Показывает/скрывает прицел в зависимости от состояния игры."""
        new_state = data.get("new_state")
        if self.crosshair:
            if new_state == GameState.IN_GAME:
                self.crosshair.show()
            else:
                self.crosshair.hide()

    def _create_crosshair(self):
        """Создаёт прицел в центре экрана."""
        self.crosshair = OnscreenText(
            text="+",
            pos=(0, 0),
            scale=0.05,
            fg=(1, 1, 1, 0.8),
            shadow=(0, 0, 0, 0.5),
            font=self.app.loader.loadFont('cmss12'),
            align=TextNode.ACenter,
        )

    def on_inventory_update(self, data: dict):
        """Обрабатывает обновление инвентаря от сервера."""
        self.inventory_items = data.get("inventory", [])
        self.max_slots = data.get("max_slots", 20)

        # Обновляем UI если открыт
        if self.is_open:
            self._update_slots()

        self.logger.debug(f"Инвентарь обновлён: {len(self.inventory_items)} предметов")

    def toggle_inventory(self):
        """Открывает/закрывает инвентарь."""
        # Не открываем если активен чат
        if not self.is_open:
            if hasattr(self.app, 'is_chat_active') and self.app.is_chat_active():
                return

        if self.is_open:
            self.close_inventory()
        else:
            self.open_inventory()

    def open_inventory(self):
        """Открывает UI инвентаря."""
        if self.is_open:
            return

        # Не открываем если активен чат
        if hasattr(self.app, 'is_chat_active') and self.app.is_chat_active():
            return

        self.is_open = True

        # Останавливаем камеру (отключает захват мыши)
        if hasattr(self.app, 'camera_controller') and self.app.camera_controller:
            self.app.camera_controller.stop()

        self._create_ui()
        self.logger.debug("Инвентарь открыт")

    def close_inventory(self):
        """Закрывает UI инвентаря."""
        if not self.is_open:
            return

        self.is_open = False
        self._destroy_ui()

        # Возобновляем камеру
        if hasattr(self.app, 'camera_controller') and self.app.camera_controller:
            self.app.camera_controller.start()

        self.logger.debug("Инвентарь закрыт")

    def on_escape(self):
        """Обработка Escape - закрыть инвентарь если открыт."""
        if self.is_open:
            self.close_inventory()

    def _create_ui(self):
        """Создаёт UI инвентаря."""
        # Основной фрейм
        self.inventory_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.15, 0.95),
            frameSize=(-0.5, 0.5, -0.6, 0.4),
            pos=(0, 0, 0),
            parent=self.app.aspect2d,
        )

        # Заголовок
        self.title = DirectLabel(
            text="Инвентарь",
            text_scale=0.06,
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.32),
            parent=self.inventory_frame,
        )

        # Кнопка закрытия
        self.close_btn = DirectButton(
            text="X",
            text_scale=0.05,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.6, 0.2, 0.2, 1),
            frameSize=(-0.04, 0.04, -0.03, 0.04),
            pos=(0.44, 0, 0.33),
            parent=self.inventory_frame,
            command=self.close_inventory,
        )

        # Сетка слотов (5 колонок x 4 ряда = 20 слотов)
        self.slots = []
        cols = 5
        rows = 4
        slot_size = 0.15
        start_x = -0.35
        start_y = 0.2

        for row in range(rows):
            for col in range(cols):
                slot_index = row * cols + col
                x = start_x + col * (slot_size + 0.03)
                y = start_y - row * (slot_size + 0.03)

                slot = self._create_slot(slot_index, x, y, slot_size)
                self.slots.append(slot)

        # Клик вне меню закрывает его
        self.accept("mouse1", self._on_click_outside)

        self._update_slots()

    def _create_slot(self, index: int, x: float, y: float, size: float):
        """Создаёт один слот инвентаря."""
        slot_frame = DirectFrame(
            frameColor=(0.2, 0.2, 0.25, 1),
            frameSize=(-size/2, size/2, -size/2, size/2),
            pos=(x, 0, y),
            parent=self.inventory_frame,
        )

        # Кнопка для взаимодействия
        slot_btn = DirectButton(
            frameColor=(0.3, 0.3, 0.35, 0.8),
            frameSize=(-size/2 + 0.01, size/2 - 0.01, -size/2 + 0.01, size/2 - 0.01),
            pos=(0, 0, 0),
            parent=slot_frame,
            command=self._on_slot_click,
            extraArgs=[index],
        )

        # События мыши - используем DGG константы
        slot_btn.bind(DGG.ENTER, self._on_slot_hover, [index])
        slot_btn.bind(DGG.EXIT, self._on_slot_unhover)
        slot_btn.bind(DGG.B3PRESS, self._on_slot_right_click, [index])

        # Название предмета
        item_label = DirectLabel(
            text="",
            text_scale=0.03,
            text_fg=(1, 1, 1, 1),
            text_wordwrap=5,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.01),
            parent=slot_frame,
        )

        # Количество в углу
        count_label = DirectLabel(
            text="",
            text_scale=0.03,
            text_fg=(1, 1, 0.5, 1),
            text_align=TextNode.ARight,
            frameColor=(0, 0, 0, 0),
            pos=(size/2 - 0.02, 0, -size/2 + 0.02),
            parent=slot_frame,
        )

        return {
            "frame": slot_frame,
            "button": slot_btn,
            "label": item_label,
            "count": count_label,
            "index": index,
            "pos_x": x,
            "pos_y": y,
        }

    def _update_slots(self):
        """Обновляет отображение слотов."""
        for i, slot in enumerate(self.slots):
            if i < len(self.inventory_items):
                item = self.inventory_items[i]
                name = item.get("name", item.get("class_id", "???"))
                count = item.get("count", 1)

                # Обрезаем длинные названия
                if len(name) > 10:
                    name = name[:9] + "..."

                slot["label"]["text"] = name
                slot["count"]["text"] = str(count) if count > 1 else ""
                slot["button"]["frameColor"] = (0.3, 0.4, 0.35, 1)
            else:
                slot["label"]["text"] = ""
                slot["count"]["text"] = ""
                slot["button"]["frameColor"] = (0.3, 0.3, 0.35, 0.5)

    def _on_slot_click(self, index: int):
        """Клик по слоту - закрыть контекстное меню."""
        self._hide_context_menu()

    def _on_slot_hover(self, index: int, event):
        """Наведение на слот - показать tooltip."""
        self.hovered_slot = index
        if index < len(self.inventory_items):
            self._show_tooltip(index)

    def _on_slot_unhover(self, event):
        """Убрали курсор со слота."""
        self.hovered_slot = -1
        self._hide_tooltip()

    def _on_slot_right_click(self, index: int, event):
        """Правый клик по слоту - контекстное меню."""
        if index < len(self.inventory_items):
            self._show_context_menu(index)

    def _on_click_outside(self):
        """Клик вне контекстного меню."""
        self._hide_context_menu()

    # -------------------------------------------------------------------------
    # Tooltip
    # -------------------------------------------------------------------------

    def _show_tooltip(self, index: int):
        """Показывает tooltip для предмета."""
        if index >= len(self.inventory_items):
            return

        item = self.inventory_items[index]
        slot = self.slots[index]

        # Получаем данные предмета
        name = item.get("name", item.get("class_id", "???"))
        desc = item.get("description", "")
        category = item.get("category", "misc")
        rarity = item.get("rarity", "common")
        count = item.get("count", 1)

        # Цвет редкости
        rarity_colors = {
            "common": (0.9, 0.9, 0.9, 1),
            "uncommon": (0.3, 0.9, 0.3, 1),
            "rare": (0.3, 0.5, 0.9, 1),
            "epic": (0.7, 0.3, 0.9, 1),
            "legendary": (0.9, 0.7, 0.2, 1),
        }
        name_color = rarity_colors.get(rarity, (1, 1, 1, 1))

        # Удаляем старый tooltip
        self._hide_tooltip()

        # Позиция справа от слота
        tooltip_x = slot["pos_x"] + 0.2
        tooltip_y = slot["pos_y"]

        # Корректируем если выходит за край
        if tooltip_x > 0.3:
            tooltip_x = slot["pos_x"] - 0.2

        # Создаём фрейм tooltip
        self.tooltip_frame = DirectFrame(
            frameColor=(0.08, 0.08, 0.12, 0.95),
            frameSize=(-0.15, 0.15, -0.12, 0.06),
            pos=(tooltip_x, 0, tooltip_y),
            parent=self.inventory_frame,
            sortOrder=100,
        )

        # Название предмета
        self.tooltip_name = DirectLabel(
            text=name,
            text_scale=0.035,
            text_fg=name_color,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.13, 0, 0.02),
            parent=self.tooltip_frame,
        )

        # Описание
        if desc:
            self.tooltip_desc = DirectLabel(
                text=desc,
                text_scale=0.025,
                text_fg=(0.8, 0.8, 0.8, 1),
                text_align=TextNode.ALeft,
                text_wordwrap=10,
                frameColor=(0, 0, 0, 0),
                pos=(-0.13, 0, -0.03),
                parent=self.tooltip_frame,
            )

        # Категория
        category_names = {
            "consumable": "Расходуемое",
            "weapon": "Оружие",
            "armor": "Броня",
            "tool": "Инструмент",
            "currency": "Валюта",
            "misc": "Разное",
        }
        cat_text = category_names.get(category, category)

        DirectLabel(
            text=cat_text,
            text_scale=0.02,
            text_fg=(0.6, 0.6, 0.6, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.13, 0, -0.09),
            parent=self.tooltip_frame,
        )

    def _hide_tooltip(self):
        """Скрывает tooltip."""
        if self.tooltip_frame:
            self.tooltip_frame.destroy()
            self.tooltip_frame = None
        self.tooltip_name = None
        self.tooltip_desc = None

    # -------------------------------------------------------------------------
    # Контекстное меню
    # -------------------------------------------------------------------------

    def _show_context_menu(self, index: int):
        """Показывает контекстное меню для предмета."""
        if index >= len(self.inventory_items):
            return

        item = self.inventory_items[index]
        slot = self.slots[index]

        # Закрываем предыдущее меню
        self._hide_context_menu()
        self.context_slot = index

        # Позиция меню
        menu_x = slot["pos_x"] + 0.1
        menu_y = slot["pos_y"] - 0.05

        # Корректируем если выходит за край
        if menu_x > 0.35:
            menu_x = slot["pos_x"] - 0.1

        # Определяем доступные действия
        category = item.get("category", "misc")
        droppable = item.get("droppable", True)

        # Можно использовать consumable
        can_use = category == "consumable"

        # Создаём меню
        menu_height = 0.08
        if can_use:
            menu_height += 0.05
        if droppable:
            menu_height += 0.05

        self.context_menu = DirectFrame(
            frameColor=(0.15, 0.15, 0.2, 0.98),
            frameSize=(-0.1, 0.1, -menu_height, 0.02),
            pos=(menu_x, 0, menu_y),
            parent=self.inventory_frame,
            sortOrder=200,
        )

        btn_y = -0.02

        # Кнопка "Использовать"
        if can_use:
            DirectButton(
                text="Использовать",
                text_scale=0.03,
                text_fg=(1, 1, 1, 1),
                frameColor=(0.25, 0.4, 0.25, 1),
                frameSize=(-0.09, 0.09, -0.02, 0.025),
                pos=(0, 0, btn_y),
                parent=self.context_menu,
                command=self._use_item,
                extraArgs=[index],
            )
            btn_y -= 0.05

        # Кнопка "Выбросить"
        if droppable:
            DirectButton(
                text="Выбросить",
                text_scale=0.03,
                text_fg=(1, 1, 1, 1),
                frameColor=(0.4, 0.25, 0.25, 1),
                frameSize=(-0.09, 0.09, -0.02, 0.025),
                pos=(0, 0, btn_y),
                parent=self.context_menu,
                command=self._drop_item,
                extraArgs=[index],
            )
            btn_y -= 0.05

        # Кнопка "Отмена"
        DirectButton(
            text="Отмена",
            text_scale=0.03,
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0.3, 0.3, 0.35, 1),
            frameSize=(-0.09, 0.09, -0.02, 0.025),
            pos=(0, 0, btn_y),
            parent=self.context_menu,
            command=self._hide_context_menu,
        )

    def _hide_context_menu(self):
        """Скрывает контекстное меню."""
        if self.context_menu:
            self.context_menu.destroy()
            self.context_menu = None
        self.context_slot = -1

    def _use_item(self, index: int):
        """Использовать предмет из контекстного меню."""
        self._hide_context_menu()

        if index < len(self.inventory_items):
            item = self.inventory_items[index]
            self.logger.debug(f"Использование предмета: {item.get('name')} (слот {index})")

            if hasattr(self.app, 'player_id') and self.app.player_id >= 0:
                self.event_manager.post("client_item_use", {
                    "slot": index,
                })

    def _drop_item(self, index: int):
        """Выбросить предмет - показать диалог выбора количества."""
        self._hide_context_menu()

        if index < len(self.inventory_items):
            item = self.inventory_items[index]
            count = item.get("count", 1)

            if count == 1:
                # Если только 1 предмет, выбрасываем сразу
                self._do_drop(index, 1)
            else:
                # Показываем диалог выбора количества
                self._show_drop_dialog(index, count)

    def _show_drop_dialog(self, index: int, max_count: int):
        """Показывает диалог выбора количества для выбрасывания."""
        self._hide_drop_dialog()

        self.drop_slot = index
        self.drop_count = 1
        item = self.inventory_items[index]
        item_name = item.get("name", item.get("class_id", "???"))

        # Создаём диалог
        self.drop_dialog = DirectFrame(
            frameColor=(0.1, 0.1, 0.15, 0.98),
            frameSize=(-0.25, 0.25, -0.18, 0.12),
            pos=(0, 0, 0),
            parent=self.app.aspect2d,
            sortOrder=300,
        )

        # Заголовок
        DirectLabel(
            text=f"Выбросить: {item_name}",
            text_scale=0.04,
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.07),
            parent=self.drop_dialog,
        )

        # Текст количества
        self.drop_count_label = DirectLabel(
            text=f"Количество: 1 / {max_count}",
            text_scale=0.035,
            text_fg=(1, 1, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.02),
            parent=self.drop_dialog,
        )

        # Слайдер
        self.drop_slider = DirectSlider(
            range=(1, max_count),
            value=1,
            pageSize=1,
            scale=0.4,
            pos=(0, 0, -0.04),
            parent=self.drop_dialog,
            command=self._on_drop_slider_change,
        )

        # Кнопки
        DirectButton(
            text="Выбросить",
            text_scale=0.035,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.4, 0.25, 0.25, 1),
            frameSize=(-0.1, 0.1, -0.025, 0.035),
            pos=(-0.1, 0, -0.12),
            parent=self.drop_dialog,
            command=self._confirm_drop,
        )

        DirectButton(
            text="Отмена",
            text_scale=0.035,
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0.3, 0.3, 0.35, 1),
            frameSize=(-0.08, 0.08, -0.025, 0.035),
            pos=(0.1, 0, -0.12),
            parent=self.drop_dialog,
            command=self._hide_drop_dialog,
        )

    def _on_drop_slider_change(self):
        """Обновляет текст при изменении слайдера."""
        if self.drop_slider and self.drop_count_label:
            value = int(self.drop_slider['value'])
            self.drop_count = value

            if self.drop_slot < len(self.inventory_items):
                max_count = self.inventory_items[self.drop_slot].get("count", 1)
                self.drop_count_label['text'] = f"Количество: {value} / {max_count}"

    def _confirm_drop(self):
        """Подтверждение выбрасывания."""
        slot = self.drop_slot
        count = self.drop_count
        self._hide_drop_dialog()
        self._do_drop(slot, count)

    def _do_drop(self, index: int, count: int):
        """Фактически выбрасывает предмет."""
        if index < len(self.inventory_items):
            item = self.inventory_items[index]
            self.logger.debug(f"Выбрасывание: {count}x {item.get('name')} (слот {index})")

            if hasattr(self.app, 'player_id') and self.app.player_id >= 0:
                self.event_manager.post("client_item_drop", {
                    "slot": index,
                    "count": count,
                })

    def _hide_drop_dialog(self):
        """Скрывает диалог выбора количества."""
        if self.drop_dialog:
            self.drop_dialog.destroy()
            self.drop_dialog = None
        self.drop_slot = -1
        self.drop_count = 1
        self.drop_slider = None
        self.drop_count_label = None

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def _destroy_ui(self):
        """Уничтожает UI инвентаря."""
        self._hide_tooltip()
        self._hide_context_menu()
        self._hide_drop_dialog()
        self.ignore("mouse1")

        if self.inventory_frame:
            self.inventory_frame.destroy()
            self.inventory_frame = None
        self.slots = []
