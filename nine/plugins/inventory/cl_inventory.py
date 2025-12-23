"""
Клиентский модуль системы инвентаря.
Отображает UI инвентаря и прицел.
"""

from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectLabel, OnscreenText
)
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode, TransparencyAttrib

from nine.core.plugins import PluginModule


class InventoryClientModule(PluginModule, DirectObject):
    """Клиентский модуль управления UI инвентаря."""

    def on_load(self):
        # Данные инвентаря
        self.inventory_items = []
        self.max_slots = 20
        self.is_open = False

        # UI элементы
        self.inventory_frame = None
        self.slots = []
        self.tooltip = None
        self.crosshair = None

        # Подписки на события
        self.event_manager.subscribe("inventory_update", self.on_inventory_update)

        # Обработка клавиш
        self.accept("i", self.toggle_inventory)
        self.accept("escape", self.on_escape)

        # Создаём прицел
        self._create_crosshair()

        self.logger.info("Клиентский модуль инвентаря загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("inventory_update", self.on_inventory_update)
        self.ignoreAll()
        self._destroy_ui()
        if self.crosshair:
            self.crosshair.destroy()
        self.logger.info("Клиентский модуль инвентаря выгружен")

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
        if self.is_open:
            self.close_inventory()
        else:
            self.open_inventory()

    def open_inventory(self):
        """Открывает UI инвентаря."""
        if self.is_open:
            return

        self.is_open = True
        self._create_ui()

        # Показываем курсор мыши
        props = self.app.win.getProperties()
        props.setCursorHidden(False)
        self.app.win.requestProperties(props)

        self.logger.debug("Инвентарь открыт")

    def close_inventory(self):
        """Закрывает UI инвентаря."""
        if not self.is_open:
            return

        self.is_open = False
        self._destroy_ui()

        # Скрываем курсор мыши если камера активна
        if hasattr(self.app, 'camera_controller') and self.app.camera_controller:
            props = self.app.win.getProperties()
            props.setCursorHidden(True)
            self.app.win.requestProperties(props)

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

        # Tooltip для отображения названия
        self.tooltip = OnscreenText(
            text="",
            pos=(0, -0.52),
            scale=0.04,
            fg=(1, 1, 0.8, 1),
            shadow=(0, 0, 0, 0.8),
            parent=self.inventory_frame,
            align=TextNode.ACenter,
        )

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
        slot_btn.bind("enter", self._on_slot_hover, [index])
        slot_btn.bind("exit", self._on_slot_unhover)

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
        """Клик по слоту - использовать предмет."""
        if index < len(self.inventory_items):
            item = self.inventory_items[index]
            self.logger.debug(f"Использование предмета: {item.get('name')} (слот {index})")

            # Отправляем событие использования на сервер
            # Используем player_id как uuid
            if hasattr(self.app, 'player_id') and self.app.player_id >= 0:
                self.event_manager.post("client_item_use", {
                    "slot": index,
                })

    def _on_slot_hover(self, index: int, event):
        """Наведение на слот - показать tooltip."""
        if index < len(self.inventory_items):
            item = self.inventory_items[index]
            name = item.get("name", item.get("class_id", "???"))
            desc = item.get("description", "")

            tooltip_text = name
            if desc:
                tooltip_text += f"\n{desc}"

            if self.tooltip:
                self.tooltip.setText(tooltip_text)

    def _on_slot_unhover(self, event):
        """Убрали курсор со слота."""
        if self.tooltip:
            self.tooltip.setText("")

    def _destroy_ui(self):
        """Уничтожает UI инвентаря."""
        if self.inventory_frame:
            self.inventory_frame.destroy()
            self.inventory_frame = None
        self.slots = []
        self.tooltip = None
