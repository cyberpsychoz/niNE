# nine/ui/chat_window.py
"""
Система чата в стиле Garry's Mod.

Два режима работы:
1. Закрытый чат: сообщения появляются внизу экрана и постепенно исчезают
2. Открытый чат: полная история с прокруткой + поле ввода

История сообщений сохраняется в течение всей сессии.
"""

import time
import logging
from dataclasses import dataclass
from typing import Callable, List, Optional, Any

from direct.gui.DirectGui import DirectScrolledFrame, DirectEntry, DirectFrame
from direct.interval.IntervalGlobal import Sequence, LerpFunc, Func
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode, LColor, NodePath, TransparencyAttrib, WindowProperties

from .base_component import BaseUIComponent

logger = logging.getLogger(__name__)


# =============================================================================
# Работа с буфером обмена
# =============================================================================

def _get_clipboard_text() -> str:
    """Получает текст из буфера обмена."""
    try:
        import pyperclip
        return pyperclip.paste()
    except ImportError:
        pass

    # Fallback на tkinter
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        return text
    except Exception:
        pass

    return ""


def _set_clipboard_text(text: str):
    """Копирует текст в буфер обмена."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return
    except ImportError:
        pass

    # Fallback на tkinter
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
    except Exception:
        pass


# =============================================================================
# Дефолтная конфигурация
# =============================================================================

class DefaultChatConfig:
    """Дефолтная конфигурация чата (используется если не передан конфиг)."""
    MAX_HISTORY = 500
    MAX_VISIBLE_MESSAGES = 10
    MESSAGE_SHOW_TIME = 10.0
    FADE_DURATION = 2.5
    TEXT_SCALE = 0.038
    LINE_HEIGHT = 0.048
    CHAT_WIDTH = 0.95
    CHAT_HEIGHT = 0.55
    CHAT_POSITION = (0.05, 0.18)
    MAX_INPUT_CHARS = 512
    COLOR_PLAYER_MESSAGE = (1.0, 0.95, 0.75, 1.0)
    COLOR_SYSTEM_MESSAGE = (0.9, 0.75, 0.4, 1.0)
    COLOR_INPUT_TEXT = (1.0, 0.95, 0.8, 1.0)
    COLOR_HINT = (0.8, 0.75, 0.55, 0.6)
    COLOR_HISTORY_BG = (0.08, 0.06, 0.04, 0.92)
    COLOR_INPUT_BG = (0.1, 0.08, 0.05, 0.95)
    COLOR_INPUT_FIELD_BG = (0.12, 0.1, 0.07, 0.8)
    COLOR_SCROLLBAR = (0.15, 0.12, 0.08, 0.9)
    COLOR_SCROLLBAR_THUMB = (0.5, 0.4, 0.25, 0.95)
    SHADOW_SIZE_VISIBLE = 0.04
    SHADOW_SIZE_HISTORY = 0.03
    SHADOW_COLOR = (0, 0, 0, 0.9)
    HINT_TEXT = "[ T ] Открыть чат"


# =============================================================================
# Классы данных
# =============================================================================

@dataclass
class ChatMessageData:
    """Данные одного сообщения чата (хранится в истории)."""
    sender: str
    text: str
    timestamp: float
    is_system: bool = False


@dataclass
class VisibleMessage:
    """Видимое сообщение на экране (временное, fade out)."""
    node_path: NodePath
    created_at: float
    fade_interval: Optional[Sequence] = None

    def destroy(self):
        if self.fade_interval:
            self.fade_interval.pause()
            self.fade_interval = None
        if self.node_path:
            self.node_path.removeNode()
            self.node_path = None


# =============================================================================
# ChatWindow
# =============================================================================

class ChatWindow(BaseUIComponent, DirectObject):
    """
    Чат в стиле Garry's Mod.

    Закрытый режим: последние сообщения внизу экрана, fade out
    Открытый режим: полная история + ввод

    Args:
        ui_manager: UIManager
        config: Модуль конфигурации (например, из sh_config.py плагина)
    """

    def __init__(self, ui_manager, config: Any = None):
        BaseUIComponent.__init__(self, ui_manager)
        DirectObject.__init__(self)

        # Используем переданный конфиг или дефолтный
        cfg = config if config else DefaultChatConfig

        # --- Загружаем конфигурацию ---
        self.max_history = getattr(cfg, 'MAX_HISTORY', 500)
        self.max_visible = getattr(cfg, 'MAX_VISIBLE_MESSAGES', 10)
        self.message_show_time = getattr(cfg, 'MESSAGE_SHOW_TIME', 10.0)
        self.fade_duration = getattr(cfg, 'FADE_DURATION', 2.5)
        self.text_scale = getattr(cfg, 'TEXT_SCALE', 0.038)
        self.line_height = getattr(cfg, 'LINE_HEIGHT', 0.048)
        self.chat_width = getattr(cfg, 'CHAT_WIDTH', 0.95)
        self.chat_height = getattr(cfg, 'CHAT_HEIGHT', 0.55)
        self.chat_position = getattr(cfg, 'CHAT_POSITION', (0.05, 0.18))
        self.max_input_chars = getattr(cfg, 'MAX_INPUT_CHARS', 512)

        # Цвета
        self.color_player_msg = LColor(*getattr(cfg, 'COLOR_PLAYER_MESSAGE', (1, 0.95, 0.75, 1)))
        self.color_system_msg = LColor(*getattr(cfg, 'COLOR_SYSTEM_MESSAGE', (0.9, 0.75, 0.4, 1)))
        self.color_input_text = getattr(cfg, 'COLOR_INPUT_TEXT', (1, 0.95, 0.8, 1))
        self.color_hint = getattr(cfg, 'COLOR_HINT', (0.8, 0.75, 0.55, 0.6))
        self.color_history_bg = getattr(cfg, 'COLOR_HISTORY_BG', (0.08, 0.06, 0.04, 0.92))
        self.color_input_bg = getattr(cfg, 'COLOR_INPUT_BG', (0.1, 0.08, 0.05, 0.95))
        self.color_input_field_bg = getattr(cfg, 'COLOR_INPUT_FIELD_BG', (0.12, 0.1, 0.07, 0.8))
        self.color_scrollbar = getattr(cfg, 'COLOR_SCROLLBAR', (0.15, 0.12, 0.08, 0.9))
        self.color_scrollbar_thumb = getattr(cfg, 'COLOR_SCROLLBAR_THUMB', (0.5, 0.4, 0.25, 0.95))

        # Тени
        self.shadow_size_visible = getattr(cfg, 'SHADOW_SIZE_VISIBLE', 0.04)
        self.shadow_size_history = getattr(cfg, 'SHADOW_SIZE_HISTORY', 0.03)
        self.shadow_color = LColor(*getattr(cfg, 'SHADOW_COLOR', (0, 0, 0, 0.9)))

        # Текст подсказки
        self.hint_text_str = getattr(cfg, 'HINT_TEXT', "[ T ] Открыть чат")

        # --- Состояние ---
        self.message_history: List[ChatMessageData] = []
        self.visible_messages: List[VisibleMessage] = []
        self._is_open = False
        self.on_send_callback: Callable[[str], None] = None

        # --- Создание UI ---
        self._create_ui()

        logger.info("ChatWindow инициализирован.")

    def _create_ui(self):
        """Создает все UI элементы."""
        # Корневой узел
        self.root = self._add_element(
            'root',
            self.base.a2dBottomLeft.attach_new_node("chat_root")
        )
        self.root.set_pos(self.chat_position[0], 0, self.chat_position[1])

        # Контейнер для видимых сообщений
        self.visible_container = self._add_element(
            'visible_container',
            self.root.attach_new_node("visible_messages")
        )
        self.visible_container.set_transparency(TransparencyAttrib.M_alpha)

        # Окно истории
        self.history_frame = self._add_element('history', DirectScrolledFrame(
            parent=self.root,
            pos=(0, 0, 0),
            frameSize=(0, self.chat_width, 0, self.chat_height),
            canvasSize=(0, self.chat_width - 0.05, -1, 0),
            frameColor=self.color_history_bg,
            scrollBarWidth=0.02,
            autoHideScrollBars=False,
            manageScrollBars=True,
            horizontalScroll_relief=None,
            verticalScroll_frameColor=self.color_scrollbar,
            verticalScroll_thumb_frameColor=self.color_scrollbar_thumb,
            borderWidth=(0.008, 0.008),
        ))
        self.history_canvas = self.history_frame.getCanvas()
        self.history_frame.hide()

        # Скрываем горизонтальный скроллбар
        if hasattr(self.history_frame, 'horizontalScroll'):
            self.history_frame.horizontalScroll.hide()

        # Поле ввода (фрейм)
        self.input_frame = self._add_element('input_frame', DirectFrame(
            parent=self.root,
            pos=(0, 0, -0.065),
            frameSize=(0, self.chat_width, 0, 0.06),
            frameColor=self.color_input_bg,
            borderWidth=(0.005, 0.005),
        ))
        self.input_frame.hide()

        # Поле ввода
        self.input = self._add_element('input', DirectEntry(
            parent=self.input_frame,
            scale=self.text_scale,
            pos=(0.015, 0, 0.018),
            width=(self.chat_width - 0.03) / self.text_scale,
            numLines=1,
            focus=0,
            command=self._on_send_message,
            frameColor=self.color_input_field_bg,
            text_fg=self.color_input_text,
            suppressKeys=False,  # Разрешаем обработку клавиш
            initialText="",
            cursorKeys=True,
            overflow=True,
        ))

        # Подсказка
        self.hint_text = self._create_hint_text()

    def _create_hint_text(self) -> NodePath:
        """Создает текст-подсказку."""
        tn = TextNode('chat_hint')
        tn.set_font(self.ui_manager.font)
        tn.set_text_color(LColor(*self.color_hint))
        tn.setText(self.hint_text_str)
        tn.set_align(TextNode.ALeft)
        tn.set_shadow(0.04, 0.04)
        tn.set_shadow_color(LColor(0, 0, 0, 0.7))

        node = self.root.attach_new_node(tn)
        node.set_scale(0.028)
        node.set_pos(0, 0, -0.03)
        node.set_transparency(TransparencyAttrib.M_alpha)
        return self._add_element('hint', node)

    def _setup_keybindings(self):
        """Устанавливает keybindings для чата."""
        self.accept('control-v', self._on_paste)
        self.accept('control-c', self._on_copy)
        self.accept('control-a', self._on_select_all)
        self.accept('control-x', self._on_cut)

    def _remove_keybindings(self):
        """Убирает keybindings."""
        self.ignore('control-v')
        self.ignore('control-c')
        self.ignore('control-a')
        self.ignore('control-x')

    def _on_paste(self):
        """Вставка из буфера обмена."""
        if not self._is_open:
            return

        clipboard_text = _get_clipboard_text()
        if clipboard_text:
            # Убираем переносы строк
            clipboard_text = clipboard_text.replace('\n', ' ').replace('\r', '')

            # Получаем текущий текст и позицию курсора
            current_text = self.input.get()
            cursor_pos = self.input.guiItem.getCursorPosition()

            # Вставляем текст
            new_text = current_text[:cursor_pos] + clipboard_text + current_text[cursor_pos:]

            # Ограничиваем длину
            if len(new_text) > self.max_input_chars:
                new_text = new_text[:self.max_input_chars]

            self.input.enterText(new_text)
            # Перемещаем курсор после вставленного текста
            new_cursor_pos = min(cursor_pos + len(clipboard_text), len(new_text))
            self.input.guiItem.setCursorPosition(new_cursor_pos)

    def _on_copy(self):
        """Копирование выделенного текста."""
        if not self._is_open:
            return

        # DirectEntry не поддерживает выделение напрямую,
        # копируем весь текст
        text = self.input.get()
        if text:
            _set_clipboard_text(text)

    def _on_cut(self):
        """Вырезание текста."""
        if not self._is_open:
            return

        text = self.input.get()
        if text:
            _set_clipboard_text(text)
            self.input.enterText('')

    def _on_select_all(self):
        """Выделение всего текста (помечаем для копирования)."""
        if not self._is_open:
            return
        # DirectEntry не поддерживает выделение,
        # но Ctrl+A обычно ожидает выделения всего текста
        # Просто перемещаем курсор в конец
        text = self.input.get()
        self.input.guiItem.setCursorPosition(len(text))

    def _on_send_message(self, text: str):
        """Обработка отправки сообщения."""
        text = text.strip()

        # Ограничиваем длину
        if len(text) > self.max_input_chars:
            text = text[:self.max_input_chars]

        self.input.enterText('')

        if text and self.on_send_callback:
            self.on_send_callback(text)

        self.close()

    def add_message(self, sender: str, message_text: str, is_system: bool = False):
        """Добавляет сообщение в чат."""
        if not message_text.strip():
            return

        msg_data = ChatMessageData(
            sender=sender,
            text=message_text.strip(),
            timestamp=time.time(),
            is_system=is_system,
        )

        self.message_history.append(msg_data)

        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

        if self._is_open:
            self._rebuild_history_view()
        else:
            self._show_visible_message(msg_data)

    def add_system_message(self, message_text: str):
        """Добавляет системное сообщение."""
        self.add_message("", message_text, is_system=True)

    def _show_visible_message(self, msg_data: ChatMessageData):
        """Показывает сообщение в закрытом режиме."""
        while len(self.visible_messages) >= self.max_visible:
            old_msg = self.visible_messages.pop(0)
            old_msg.destroy()

        if msg_data.is_system:
            text = f"* {msg_data.text}"
            color = self.color_system_msg
        else:
            text = f"{msg_data.sender}: {msg_data.text}"
            color = self.color_player_msg

        tn = TextNode('visible_msg')
        tn.set_font(self.ui_manager.font)
        tn.set_text_color(color)
        tn.set_wordwrap(self.chat_width / self.text_scale)
        tn.set_shadow(self.shadow_size_visible, self.shadow_size_visible)
        tn.set_shadow_color(self.shadow_color)
        tn.setText(text)

        node = self.visible_container.attach_new_node(tn)
        node.set_scale(self.text_scale)
        node.set_transparency(TransparencyAttrib.M_alpha)

        visible_msg = VisibleMessage(node_path=node, created_at=time.time())
        self.visible_messages.append(visible_msg)

        self._redraw_visible_messages()
        self._start_fade_out(visible_msg)

    def _redraw_visible_messages(self):
        """Перерисовывает позиции видимых сообщений."""
        y_pos = 0
        for visible_msg in self.visible_messages:
            if not visible_msg.node_path:
                continue
            visible_msg.node_path.set_pos(0, 0, y_pos)

            min_b, max_b = visible_msg.node_path.get_tight_bounds()
            height = max_b.z - min_b.z
            y_pos += height + self.line_height * 0.3

    def _start_fade_out(self, visible_msg: VisibleMessage):
        """Запускает fade out анимацию."""
        def set_alpha(alpha):
            if visible_msg.node_path:
                visible_msg.node_path.set_alpha_scale(alpha)

        def remove_message():
            if visible_msg in self.visible_messages:
                self.visible_messages.remove(visible_msg)
                visible_msg.destroy()
                self._redraw_visible_messages()

        visible_msg.fade_interval = Sequence(
            LerpFunc(lambda t: None, duration=self.message_show_time),
            LerpFunc(set_alpha, duration=self.fade_duration, fromData=1.0, toData=0.0),
            Func(remove_message),
        )
        visible_msg.fade_interval.start()

    def _rebuild_history_view(self):
        """Перестраивает отображение истории."""
        for child in self.history_canvas.get_children():
            child.removeNode()

        y_pos = -self.line_height
        for msg_data in self.message_history:
            if msg_data.is_system:
                text = f"* {msg_data.text}"
                color = self.color_system_msg
            else:
                text = f"{msg_data.sender}: {msg_data.text}"
                color = self.color_player_msg

            tn = TextNode('history_msg')
            tn.set_font(self.ui_manager.font)
            tn.set_text_color(color)
            tn.set_wordwrap((self.chat_width - 0.08) / self.text_scale)
            tn.set_shadow(self.shadow_size_history, self.shadow_size_history)
            tn.set_shadow_color(LColor(0, 0, 0, 0.6))
            tn.setText(text)

            node = self.history_canvas.attach_new_node(tn)
            node.set_scale(self.text_scale)
            node.set_pos(0.015, 0, y_pos)

            min_b, max_b = node.get_tight_bounds()
            height = max_b.z - min_b.z
            y_pos -= height + self.line_height * 0.35

        canvas_height = abs(y_pos) + self.line_height
        self.history_frame['canvasSize'] = (0, self.chat_width - 0.05, -canvas_height, 0)
        self.history_frame.verticalScroll.setValue(1)

    def _enable_mouse_cursor(self):
        """Показывает курсор мыши."""
        if hasattr(self.base, 'camera_controller') and self.base.camera_controller:
            self.base.camera_controller.stop()
        else:
            props = WindowProperties()
            props.setCursorHidden(False)
            props.setMouseMode(WindowProperties.M_absolute)
            self.base.win.requestProperties(props)

    def _disable_mouse_cursor(self):
        """Скрывает курсор."""
        if hasattr(self.base, 'camera_controller') and self.base.camera_controller:
            self.base.camera_controller.start()
        else:
            props = WindowProperties()
            props.setCursorHidden(True)
            props.setMouseMode(WindowProperties.M_relative)
            self.base.win.requestProperties(props)

    def open(self):
        """Открывает чат."""
        if self._is_open:
            return

        self._is_open = True

        self._enable_mouse_cursor()
        self._setup_keybindings()

        self.visible_container.hide()
        self.hint_text.hide()

        self.history_frame.show()
        self.input_frame.show()
        self._rebuild_history_view()

        self.input['focus'] = 1

        logger.debug("Чат открыт")

    def close(self):
        """Закрывает чат."""
        if not self._is_open:
            return

        self._is_open = False

        self._remove_keybindings()

        self.history_frame.hide()
        self.input_frame.hide()
        self.input['focus'] = 0
        self.input.enterText('')

        self.visible_container.show()
        self.hint_text.show()

        self._disable_mouse_cursor()

        logger.debug("Чат закрыт")

    def toggle_input(self):
        """Переключает состояние чата."""
        if self._is_open:
            self.close()
        else:
            self.open()

    def is_visible(self) -> bool:
        """Возвращает True если чат открыт."""
        return self._is_open

    def is_open(self) -> bool:
        """Alias для is_visible()."""
        return self._is_open

    def clear_history(self):
        """Очищает историю сообщений."""
        self.message_history.clear()

        for visible_msg in self.visible_messages:
            visible_msg.destroy()
        self.visible_messages.clear()

        logger.info("История чата очищена")

    def destroy(self):
        """Уничтожает компонент чата."""
        self._remove_keybindings()
        self.ignoreAll()

        for visible_msg in self.visible_messages:
            visible_msg.destroy()
        self.visible_messages.clear()

        self.message_history.clear()

        BaseUIComponent.destroy(self)
        logger.info("ChatWindow уничтожен.")
