# nine/ui/chat_window.py
import time
import logging
from collections import deque
from typing import Callable

from direct.gui.DirectGui import DirectScrolledFrame, DirectEntry
from panda3d.core import TextNode, LColor, NodePath

from .base_component import BaseUIComponent

logger = logging.getLogger(__name__)

class ChatMessage:
    """Обертка для одного сообщения в чате, хранящая NodePath и метаданные."""
    def __init__(self, text_node_path: NodePath, created_at: float):
        self.node_path = text_node_path
        self.created_at = created_at

    def destroy(self):
        self.node_path.removeNode()

class ChatWindow(BaseUIComponent):
    """
    Управляет отображением окна чата, сообщений и поля ввода.
    Использует DirectScrolledFrame для надежной прокрутки.
    """
    def __init__(self, ui_manager):
        super().__init__(ui_manager)

        # --- Конфигурация ---
        self.max_messages = 50
        self.message_lifetime = 15.0  # seconds
        self.fade_duration = 3.0
        self.text_scale = 0.04
        self.line_height = 0.05
        self.chat_width = 0.8
        self.chat_height = 0.4

        # --- Состояние ---
        self.messages: deque[ChatMessage] = deque()
        self._is_input_visible = False
        self.on_send_callback: Callable[[str], None] = None

        # --- UI Элементы ---
        self.root = self._add_element('root', self.base.a2dBottomLeft.attach_new_node("chat_root"))
        self.root.set_pos(0.05, 0, 0.05)

        self.history_frame = self._add_element('history', DirectScrolledFrame(
            parent=self.root,
            pos=(0, 0, self.line_height * 2),
            frameSize=(0, self.chat_width, 0, self.chat_height),
            canvasSize=(0, self.chat_width - 0.05, -1, 0),
            frameColor=(0.05, 0.05, 0.05, 0.5),
            scrollBarWidth=0.03,
            autoHideScrollBars=True,
        ))
        self.canvas = self.history_frame.getCanvas()

        self.input = self._add_element('input', DirectEntry(
            parent=self.root,
            scale=self.text_scale,
            pos=(0, 0, self.line_height),
            width=self.chat_width / self.text_scale,
            numLines=1,
            focus=0,
            command=self._on_send_message,
            frameColor=(0.1, 0.1, 0.1, 0.9),
            text_fg=(1, 1, 1, 1),
            suppressKeys=True,
        ))
        self.input.hide()

        self.base.taskMgr.add(self._update_fade, "chat_fade_task")
        logger.info("Компонент ChatWindow инициализирован.")

    def _on_send_message(self, text: str):
        text = text.strip()
        if not text:
            self.toggle_input()
            return

        if self.on_send_callback:
            self.on_send_callback(text)
        
        self.input.enterText('')

    def add_message(self, sender: str, message_text: str):
        if not message_text.strip(): return

        # Удаляем старые сообщения из истории, если превышен лимит
        if len(self.messages) >= self.max_messages:
            old_chat_message = self.messages.popleft()
            old_chat_message.destroy()

        # Создаем TextNode
        text = f"{sender}: {message_text}"
        tn = TextNode('message')
        tn.set_font(self.ui_manager.font)
        tn.set_text_color(LColor(1, 1, 1, 1))
        tn.set_wordwrap((self.chat_width - 0.05) / self.text_scale)
        tn.setText(text)
        
        text_node_path = self.canvas.attach_new_node(tn)
        text_node_path.set_scale(self.text_scale)
        text_node_path.set_pos(0.02, 0, 0)
        
        new_chat_message = ChatMessage(text_node_path, time.time())
        self.messages.append(new_chat_message)
        
        self._redraw_messages()

    def _redraw_messages(self):
        y_pos = -self.line_height
        for chat_message in self.messages:
            chat_message.node_path.set_z(y_pos)
            min_b, max_b = chat_message.node_path.get_tight_bounds()
            height = max_b.z - min_b.z # already scaled
            y_pos -= height + self.line_height * 0.2
        
        self.history_frame['canvasSize'] = (0, self.chat_width - 0.05, y_pos, 0)
        self.history_frame.verticalScroll.setValue(0)

    def _update_fade(self, task):
        now = time.time()
        # Создаем копию списка, чтобы безопасно изменять его во время итерации
        for chat_message in list(self.messages):
            age = now - chat_message.created_at
            if age > self.message_lifetime:
                fade_progress = (age - self.message_lifetime) / self.fade_duration
                alpha = max(0, 1.0 - fade_progress)
                chat_message.node_path.set_alpha_scale(alpha)
                if alpha == 0: # Полностью исчезнувшее сообщение
                    self.messages.remove(chat_message)
                    chat_message.destroy()
                    self._redraw_messages() # Перерисовать, так как сообщение удалено
            else:
                chat_message.node_path.set_alpha_scale(1) # Убедимся, что новые сообщения непрозрачны
        return task.cont

    def toggle_input(self):
        self._is_input_visible = not self._is_input_visible
        if self._is_input_visible:
            self.input.show()
            self.input['focus'] = 1
            logger.debug("Поле ввода чата показано.")
        else:
            self.input.hide()
            self.input['focus'] = 0
            logger.debug("Поле ввода чата скрыто.")
            
    def is_visible(self) -> bool:
        return self._is_input_visible

    def destroy(self):
        self.base.taskMgr.remove("chat_fade_task")
        while self.messages:
            self.messages.popleft().destroy()
        super().destroy()
        logger.info("Компонент ChatWindow уничтожен.")