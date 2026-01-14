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
from panda3d.core import TextPropertiesManager, TextProperties

from .base_component import BaseUIComponent

logger = logging.getLogger(__name__)


# =============================================================================
# Работа с буфером обмена
# =============================================================================

def _get_clipboard_text() -> str:
    """Получает текст из буфера обмена."""
    # Пробуем pyperclip
    try:
        import pyperclip
        return pyperclip.paste()
    except ImportError:
        pass
    except Exception:
        # pyperclip установлен, но не работает (нет xclip/xsel)
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
    # Пробуем pyperclip
    try:
        import pyperclip
        pyperclip.copy(text)
        return
    except ImportError:
        pass
    except Exception:
        # pyperclip установлен, но не работает (нет xclip/xsel)
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

    # RP Chat colors
    COLOR_EMOTE = (1.0, 0.85, 0.4, 1.0)      # /me действие (жёлто-оранжевый)
    COLOR_IT = (1.0, 0.85, 0.4, 1.0)         # /it безличное (тот же цвет)
    COLOR_LOOC_TAG = (0.9, 0.2, 0.2, 1.0)    # [LOOC] тег - красный
    COLOR_LOOC_TEXT = (0.7, 0.7, 0.7, 1.0)   # LOOC текст - серый
    COLOR_OOC_TAG = (0.9, 0.2, 0.2, 1.0)     # [OOC] тег - красный
    COLOR_OOC_TEXT = (0.7, 0.7, 0.7, 1.0)    # OOC текст - серый

    # Command suggestions
    COLOR_SUGGESTIONS_BG = (0.1, 0.08, 0.05, 0.95)
    COLOR_SUGGESTIONS_TEXT = (0.9, 0.85, 0.7, 1.0)
    COLOR_SUGGESTIONS_HIGHLIGHT = (1.0, 0.9, 0.5, 1.0)


# Команды чата (для автокомплита на клиенте)
CHAT_COMMANDS_CLIENT = {
    # RP команды (доступны всем)
    "me": "/me <действие> — действие от первого лица",
    "it": "/it <текст> — безличное действие",
    "looc": "/looc <текст> — локальный OOC чат",
    "ooc": "/ooc <текст> — глобальный OOC чат",
    "help": "/help — показать список команд",
    # Предметы
    "give": "/give <id> [кол-во] — выдать предмет",
    "spawn": "/spawn <id> [кол-во] — заспавнить предмет",
    "items": "/items — список предметов",
}


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
    chat_type: str = "ic"  # ic, emote, it, looc, ooc
    formatted_message: Optional[str] = None  # Pre-formatted message (e.g., for /me, /it)


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

        # RP Chat colors
        self.color_emote = LColor(*getattr(cfg, 'COLOR_EMOTE', (1.0, 0.85, 0.4, 1.0)))
        self.color_it = LColor(*getattr(cfg, 'COLOR_IT', (1.0, 0.85, 0.4, 1.0)))
        self.color_looc_tag = getattr(cfg, 'COLOR_LOOC_TAG', (0.9, 0.2, 0.2, 1.0))
        self.color_looc_text = LColor(*getattr(cfg, 'COLOR_LOOC_TEXT', (0.7, 0.7, 0.7, 1.0)))
        self.color_ooc_tag = getattr(cfg, 'COLOR_OOC_TAG', (0.9, 0.2, 0.2, 1.0))
        self.color_ooc_text = LColor(*getattr(cfg, 'COLOR_OOC_TEXT', (0.7, 0.7, 0.7, 1.0)))

        # Command suggestions colors
        self.color_suggestions_bg = getattr(cfg, 'COLOR_SUGGESTIONS_BG', (0.1, 0.08, 0.05, 0.95))
        self.color_suggestions_text = LColor(*getattr(cfg, 'COLOR_SUGGESTIONS_TEXT', (0.9, 0.85, 0.7, 1.0)))
        self.color_suggestions_highlight = LColor(*getattr(cfg, 'COLOR_SUGGESTIONS_HIGHLIGHT', (1.0, 0.9, 0.5, 1.0)))

        # Настраиваем TextProperties для цветных тегов
        self._setup_text_properties()

        # --- Состояние ---
        self.message_history: List[ChatMessageData] = []
        self.visible_messages: List[VisibleMessage] = []
        self._is_open = False
        self.on_send_callback: Callable[[str], None] = None

        # История отправленных сообщений (для стрелок вверх/вниз)
        self.input_history: List[str] = []
        self.input_history_index: int = -1  # -1 = текущий ввод
        self.input_history_max: int = 50
        self.current_input_backup: str = ""  # Сохраняем текущий ввод при навигации

        # Выделение текста (логическое, без визуального отображения)
        self.selection_start: int = -1  # -1 = нет выделения
        self.selection_end: int = -1

        # Состояние подсказок команд
        self._last_input_text: str = ""
        self._suggestions_visible: bool = False
        self._input_monitor_task = None
        self._current_suggestions: List[tuple] = []  # Список (cmd_name, cmd_desc)
        self._selected_suggestion: int = -1  # Индекс выбранной подсказки (-1 = нет)

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

        # Фрейм подсказок команд (над полем ввода)
        self.suggestions_frame = self._add_element('suggestions_frame', DirectFrame(
            parent=self.root,
            pos=(0, 0, 0.065),  # Над полем ввода
            frameSize=(0, self.chat_width, 0, 0.25),
            frameColor=self.color_suggestions_bg,
            borderWidth=(0.005, 0.005),
        ))
        self.suggestions_frame.hide()

        # Контейнер для текста подсказок
        self.suggestions_container = self._add_element(
            'suggestions_container',
            self.suggestions_frame.attach_new_node("suggestions_text")
        )

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

    def _setup_text_properties(self):
        """Настраивает TextProperties для цветных тегов в тексте."""
        tp_mgr = TextPropertiesManager.getGlobalPtr()

        # Свойства для красного тега LOOC
        tp_looc = TextProperties()
        tp_looc.setTextColor(*self.color_looc_tag)
        tp_mgr.setProperties("looc_tag", tp_looc)

        # Свойства для красного тега OOC
        tp_ooc = TextProperties()
        tp_ooc.setTextColor(*self.color_ooc_tag)
        tp_mgr.setProperties("ooc_tag", tp_ooc)

    def _setup_keybindings(self):
        """Устанавливает keybindings для чата."""
        self.accept('control-v', self._on_paste)
        self.accept('control-c', self._on_copy)
        self.accept('control-a', self._on_select_all)
        self.accept('control-x', self._on_cut)
        self.accept('arrow_up', self._on_history_up)
        self.accept('arrow_down', self._on_history_down)
        # Выделение текста
        self.accept('shift-arrow_left', self._on_select_left)
        self.accept('shift-arrow_right', self._on_select_right)
        self.accept('shift-home', self._on_select_home)
        self.accept('shift-end', self._on_select_end)
        # Сброс выделения при обычном движении
        self.accept('arrow_left', self._on_cursor_move)
        self.accept('arrow_right', self._on_cursor_move)
        self.accept('home', self._on_cursor_move)
        self.accept('end', self._on_cursor_move)
        # Tab для навигации по подсказкам команд
        self.accept('tab', self._on_tab_key)
        self.accept('shift-tab', self._on_shift_tab_key)

    def _remove_keybindings(self):
        """Убирает keybindings."""
        self.ignore('control-v')
        self.ignore('control-c')
        self.ignore('control-a')
        self.ignore('control-x')
        self.ignore('arrow_up')
        self.ignore('arrow_down')
        self.ignore('shift-arrow_left')
        self.ignore('shift-arrow_right')
        self.ignore('shift-home')
        self.ignore('shift-end')
        self.ignore('arrow_left')
        self.ignore('arrow_right')
        self.ignore('home')
        self.ignore('end')
        self.ignore('tab')
        self.ignore('shift-tab')

    def _on_paste(self):
        """Вставка из буфера обмена."""
        if not self._is_open:
            return

        clipboard_text = _get_clipboard_text()
        if clipboard_text:
            # Убираем переносы строк
            clipboard_text = clipboard_text.replace('\n', ' ').replace('\r', '')

            current_text = self.input.get()

            # Если есть выделение - заменяем выделенный текст
            if self.selection_start != -1 and self.selection_end != -1:
                start = min(self.selection_start, self.selection_end)
                end = max(self.selection_start, self.selection_end)
                new_text = current_text[:start] + clipboard_text + current_text[end:]
                cursor_pos = start
            else:
                cursor_pos = self.input.guiItem.getCursorPosition()
                new_text = current_text[:cursor_pos] + clipboard_text + current_text[cursor_pos:]

            # Ограничиваем длину
            if len(new_text) > self.max_input_chars:
                new_text = new_text[:self.max_input_chars]

            self.input.enterText(new_text)
            # Перемещаем курсор после вставленного текста
            new_cursor_pos = min(cursor_pos + len(clipboard_text), len(new_text))
            self.input.guiItem.setCursorPosition(new_cursor_pos)
            self._clear_selection()

    def _on_copy(self):
        """Копирование выделенного текста."""
        if not self._is_open:
            return

        text = self._get_selected_text()
        if text:
            _set_clipboard_text(text)

    def _on_cut(self):
        """Вырезание выделенного текста."""
        if not self._is_open:
            return

        full_text = self.input.get()

        if self.selection_start != -1 and self.selection_end != -1:
            # Вырезаем выделенный текст
            start = min(self.selection_start, self.selection_end)
            end = max(self.selection_start, self.selection_end)
            selected = full_text[start:end]
            if selected:
                _set_clipboard_text(selected)
                # Удаляем выделенную часть
                new_text = full_text[:start] + full_text[end:]
                self.input.enterText(new_text)
                self.input.guiItem.setCursorPosition(start)
                self._clear_selection()
        elif full_text:
            # Нет выделения - вырезаем всё
            _set_clipboard_text(full_text)
            self.input.enterText('')
            self._clear_selection()

    def _on_select_all(self):
        """Выделение всего текста."""
        if not self._is_open:
            return
        text = self.input.get()
        self.selection_start = 0
        self.selection_end = len(text)
        self.input.guiItem.setCursorPosition(len(text))

    def _on_cursor_move(self):
        """Сброс выделения при обычном движении курсора."""
        self._clear_selection()

    def _on_select_left(self):
        """Расширение выделения влево."""
        if not self._is_open:
            return
        cursor_pos = self.input.guiItem.getCursorPosition()

        # Начинаем выделение если его нет
        if self.selection_start == -1:
            self.selection_start = cursor_pos
            self.selection_end = cursor_pos

        # Расширяем влево
        if cursor_pos > 0:
            new_pos = cursor_pos - 1
            self.input.guiItem.setCursorPosition(new_pos)
            # Обновляем границы выделения
            if new_pos < self.selection_start:
                self.selection_start = new_pos
            else:
                self.selection_end = new_pos

    def _on_select_right(self):
        """Расширение выделения вправо."""
        if not self._is_open:
            return
        text = self.input.get()
        cursor_pos = self.input.guiItem.getCursorPosition()

        # Начинаем выделение если его нет
        if self.selection_start == -1:
            self.selection_start = cursor_pos
            self.selection_end = cursor_pos

        # Расширяем вправо
        if cursor_pos < len(text):
            new_pos = cursor_pos + 1
            self.input.guiItem.setCursorPosition(new_pos)
            # Обновляем границы выделения
            if new_pos > self.selection_end:
                self.selection_end = new_pos
            else:
                self.selection_start = new_pos

    def _on_select_home(self):
        """Выделение до начала строки."""
        if not self._is_open:
            return
        cursor_pos = self.input.guiItem.getCursorPosition()

        if self.selection_start == -1:
            self.selection_end = cursor_pos

        self.selection_start = 0
        self.input.guiItem.setCursorPosition(0)

    def _on_select_end(self):
        """Выделение до конца строки."""
        if not self._is_open:
            return
        text = self.input.get()
        cursor_pos = self.input.guiItem.getCursorPosition()

        if self.selection_start == -1:
            self.selection_start = cursor_pos

        self.selection_end = len(text)
        self.input.guiItem.setCursorPosition(len(text))

    def _clear_selection(self):
        """Сбрасывает выделение."""
        self.selection_start = -1
        self.selection_end = -1

    def _get_selected_text(self) -> str:
        """Возвращает выделенный текст или весь текст если выделения нет."""
        text = self.input.get()
        if self.selection_start != -1 and self.selection_end != -1:
            start = min(self.selection_start, self.selection_end)
            end = max(self.selection_start, self.selection_end)
            return text[start:end]
        return text

    def _on_history_up(self):
        """Навигация вверх по истории отправленных сообщений."""
        if not self._is_open or not self.input_history:
            return

        # Сохраняем текущий ввод если это первое нажатие
        if self.input_history_index == -1:
            self.current_input_backup = self.input.get()

        # Переходим к предыдущему сообщению
        if self.input_history_index < len(self.input_history) - 1:
            self.input_history_index += 1
            # История хранится от нового к старому (индекс 0 = последнее)
            history_text = self.input_history[self.input_history_index]
            self.input.enterText(history_text)
            self.input.guiItem.setCursorPosition(len(history_text))

    def _on_history_down(self):
        """Навигация вниз по истории отправленных сообщений."""
        if not self._is_open:
            return

        if self.input_history_index > 0:
            # Переходим к более новому сообщению
            self.input_history_index -= 1
            history_text = self.input_history[self.input_history_index]
            self.input.enterText(history_text)
            self.input.guiItem.setCursorPosition(len(history_text))
        elif self.input_history_index == 0:
            # Возвращаемся к текущему вводу
            self.input_history_index = -1
            self.input.enterText(self.current_input_backup)
            self.input.guiItem.setCursorPosition(len(self.current_input_backup))

    # =========================================================================
    # Подсказки команд
    # =========================================================================

    def _start_input_monitor(self):
        """Запускает задачу мониторинга ввода для подсказок."""
        if self._input_monitor_task:
            return

        def monitor_input(task):
            if not self._is_open:
                return task.done

            current_text = self.input.get()

            # Проверяем изменился ли текст
            if current_text != self._last_input_text:
                self._last_input_text = current_text
                self._update_suggestions(current_text)

            return task.cont

        self._input_monitor_task = self.base.taskMgr.add(
            monitor_input,
            "chat_input_monitor"
        )

    def _stop_input_monitor(self):
        """Останавливает задачу мониторинга ввода."""
        if self._input_monitor_task:
            self.base.taskMgr.remove(self._input_monitor_task)
            self._input_monitor_task = None

    def _update_suggestions(self, text: str):
        """Обновляет подсказки на основе текста ввода."""
        # Очищаем старые подсказки
        for child in self.suggestions_container.get_children():
            child.removeNode()

        # Показываем подсказки только если текст начинается с /
        if not text.startswith("/"):
            self._hide_suggestions()
            return

        # Извлекаем частичную команду (без /)
        partial_cmd = text[1:].split()[0] if len(text) > 1 else ""

        # Фильтруем команды
        matching_commands = []
        for cmd_name, cmd_desc in CHAT_COMMANDS_CLIENT.items():
            if not partial_cmd or cmd_name.startswith(partial_cmd.lower()):
                matching_commands.append((cmd_name, cmd_desc))

        if not matching_commands:
            self._hide_suggestions()
            return

        # Сохраняем текущие подсказки и сбрасываем выбор
        self._current_suggestions = matching_commands[:6]
        self._selected_suggestion = -1

        # Показываем подсказки
        self._show_suggestions(self._current_suggestions)

    def _show_suggestions(self, commands: list):
        """Показывает список подсказок команд."""
        # Очищаем старые
        for child in self.suggestions_container.get_children():
            child.removeNode()

        y_pos = 0.22
        line_height = 0.035

        for i, (cmd_name, cmd_desc) in enumerate(commands):
            tn = TextNode(f'suggestion_{cmd_name}')
            tn.set_font(self.ui_manager.font)

            # Подсветка выбранной подсказки
            if i == self._selected_suggestion:
                tn.set_text_color(self.color_suggestions_highlight)
            else:
                tn.set_text_color(self.color_suggestions_text)

            tn.setText(cmd_desc)
            tn.set_align(TextNode.ALeft)
            tn.set_shadow(0.02, 0.02)
            tn.set_shadow_color(LColor(0, 0, 0, 0.7))

            node = self.suggestions_container.attach_new_node(tn)
            node.set_scale(0.032)
            node.set_pos(0.015, 0, y_pos)
            y_pos -= line_height

        # Подстраиваем размер фрейма под количество команд
        frame_height = len(commands) * line_height + 0.02
        self.suggestions_frame['frameSize'] = (0, self.chat_width, 0, frame_height)

        self.suggestions_frame.show()
        self._suggestions_visible = True

    def _hide_suggestions(self):
        """Скрывает подсказки."""
        if self._suggestions_visible:
            self.suggestions_frame.hide()
            self._suggestions_visible = False
            self._current_suggestions = []
            self._selected_suggestion = -1

            # Очищаем текст
            for child in self.suggestions_container.get_children():
                child.removeNode()

    def _on_tab_key(self):
        """Обработка Tab - переход к следующей подсказке или вставка выбранной."""
        if not self._is_open:
            return

        if not self._suggestions_visible or not self._current_suggestions:
            return

        if self._selected_suggestion == -1:
            # Начинаем выбор с первой подсказки
            self._selected_suggestion = 0
        else:
            # Переходим к следующей или вставляем если уже выбрана
            next_idx = self._selected_suggestion + 1
            if next_idx >= len(self._current_suggestions):
                # Вставляем выбранную команду
                self._insert_selected_suggestion()
                return
            self._selected_suggestion = next_idx

        # Перерисовываем подсказки с новым выбором
        self._show_suggestions(self._current_suggestions)

    def _on_shift_tab_key(self):
        """Обработка Shift+Tab - переход к предыдущей подсказке."""
        if not self._is_open:
            return

        if not self._suggestions_visible or not self._current_suggestions:
            return

        if self._selected_suggestion <= 0:
            self._selected_suggestion = len(self._current_suggestions) - 1
        else:
            self._selected_suggestion -= 1

        # Перерисовываем подсказки
        self._show_suggestions(self._current_suggestions)

    def _insert_selected_suggestion(self):
        """Вставляет выбранную команду в поле ввода."""
        if self._selected_suggestion < 0 or self._selected_suggestion >= len(self._current_suggestions):
            return

        cmd_name, _ = self._current_suggestions[self._selected_suggestion]
        # Вставляем команду с / и пробелом
        new_text = f"/{cmd_name} "
        self.input.enterText(new_text)
        self.input.guiItem.setCursorPosition(len(new_text))

        # Скрываем подсказки
        self._hide_suggestions()

    def _on_send_message(self, text: str):
        """Обработка отправки сообщения."""
        text = text.strip()

        # Ограничиваем длину
        if len(text) > self.max_input_chars:
            text = text[:self.max_input_chars]

        self.input.enterText('')

        if text:
            # Сохраняем в историю (в начало списка = самое новое)
            if not self.input_history or self.input_history[0] != text:
                self.input_history.insert(0, text)
                if len(self.input_history) > self.input_history_max:
                    self.input_history.pop()

            if self.on_send_callback:
                self.on_send_callback(text)

        # Сбрасываем индекс истории
        self.input_history_index = -1
        self.current_input_backup = ""

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

    def add_rp_message(
        self,
        sender: str,
        message: str,
        chat_type: str = "ic",
        formatted_message: Optional[str] = None,
        is_system: bool = False
    ):
        """
        Добавляет RP сообщение в чат с поддержкой разных типов.

        Args:
            sender: Имя отправителя
            message: Текст сообщения
            chat_type: Тип сообщения (ic, emote, it, looc, ooc)
            formatted_message: Предварительно отформатированное сообщение
            is_system: Системное ли сообщение
        """
        if not message.strip() and not formatted_message:
            return

        msg_data = ChatMessageData(
            sender=sender,
            text=message.strip(),
            timestamp=time.time(),
            is_system=is_system,
            chat_type=chat_type,
            formatted_message=formatted_message,
        )

        self.message_history.append(msg_data)

        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

        if self._is_open:
            self._rebuild_history_view()
        else:
            self._show_visible_message(msg_data)

    def _show_visible_message(self, msg_data: ChatMessageData):
        """Показывает сообщение в закрытом режиме."""
        while len(self.visible_messages) >= self.max_visible:
            old_msg = self.visible_messages.pop(0)
            old_msg.destroy()

        # Определяем текст и цвет в зависимости от типа сообщения
        text, color = self._format_message_for_display(msg_data)

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

    def _format_message_for_display(self, msg_data: ChatMessageData) -> tuple:
        """
        Форматирует сообщение для отображения.
        Возвращает (текст, цвет).
        """
        chat_type = msg_data.chat_type

        if msg_data.is_system:
            return f"* {msg_data.text}", self.color_system_msg

        if chat_type == "emote":
            # /me - "**Имя игрока действие"
            if msg_data.formatted_message:
                return msg_data.formatted_message, self.color_emote
            return f"**{msg_data.sender} {msg_data.text}", self.color_emote

        elif chat_type == "it":
            # /it - "**текст"
            if msg_data.formatted_message:
                return msg_data.formatted_message, self.color_it
            return f"**{msg_data.text}", self.color_it

        elif chat_type == "looc":
            # LOOC - "[LOOC]" красный, остальное серое
            # Используем TextProperties: \1property_name\1text\2
            tag = "\1looc_tag\1[LOOC]\2"
            return f"{tag} {msg_data.sender}: {msg_data.text}", self.color_looc_text

        elif chat_type == "ooc":
            # OOC - "[OOC]" красный, остальное серое
            tag = "\1ooc_tag\1[OOC]\2"
            return f"{tag} {msg_data.sender}: {msg_data.text}", self.color_ooc_text

        else:
            # IC - обычный чат "Имя: сообщение"
            return f"{msg_data.sender}: {msg_data.text}", self.color_player_msg

    def _redraw_visible_messages(self):
        """
        Перерисовывает позиции видимых сообщений.
        Сообщения растут вверх от нижней границы чата.
        Новые сообщения внизу, старые вверху.
        """
        # Сначала вычисляем высоту каждого сообщения
        heights = []
        for visible_msg in self.visible_messages:
            if not visible_msg.node_path:
                heights.append(0)
                continue
            min_b, max_b = visible_msg.node_path.get_tight_bounds()
            height = max_b.z - min_b.z
            heights.append(height)

        # Позиционируем снизу вверх
        # Последнее сообщение (самое новое) внизу, первое (самое старое) вверху
        y_pos = 0
        for i in range(len(self.visible_messages) - 1, -1, -1):
            visible_msg = self.visible_messages[i]
            if not visible_msg.node_path:
                continue

            height = heights[i]
            # Сдвигаем текст вверх на его высоту, чтобы он рос вверх, а не вниз
            visible_msg.node_path.set_pos(0, 0, y_pos + height)
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
            # Используем общий метод форматирования
            text, color = self._format_message_for_display(msg_data)

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

        # Сбрасываем состояние клавиш движения
        if hasattr(self.base, 'keyMap'):
            for key in self.base.keyMap:
                self.base.keyMap[key] = False

        self._enable_mouse_cursor()
        self._setup_keybindings()

        self.visible_container.hide()
        self.hint_text.hide()

        self.history_frame.show()
        self.input_frame.show()
        self._rebuild_history_view()

        self.input['focus'] = 1

        # Запускаем мониторинг ввода для подсказок команд
        self._last_input_text = ""
        self._start_input_monitor()

        logger.debug("Чат открыт")

    def close(self):
        """Закрывает чат."""
        if not self._is_open:
            return

        self._is_open = False

        self._remove_keybindings()

        # Останавливаем мониторинг и скрываем подсказки
        self._stop_input_monitor()
        self._hide_suggestions()

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
        self._stop_input_monitor()
        self.ignoreAll()

        for visible_msg in self.visible_messages:
            visible_msg.destroy()
        self.visible_messages.clear()

        self.message_history.clear()

        BaseUIComponent.destroy(self)
        logger.info("ChatWindow уничтожен.")
