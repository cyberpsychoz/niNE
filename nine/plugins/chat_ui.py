from direct.showbase.DirectObject import DirectObject
from nine.core.plugins import BasePlugin
from nine.ui.chat_window import ChatWindow

class ChatUIPlugin(BasePlugin, DirectObject):
    name = "Chat UI"
    plugin_type = "client"

    def on_load(self):
        self.app.logger.info(f"Плагин '{self.name}' загружен.")
        
        # app.ui is an instance of UIManager, which is needed by ChatWindow's parent class
        self.ui_window = ChatWindow(self.app.ui)
        
        # --- Callbacks & Events ---
        self.ui_window.on_send_callback = self.send_chat_message
        self.event_manager.subscribe("chat_broadcast", self.add_incoming_message)
        
        # --- Keybindings ---
        self.accept('t', self.ui_window.toggle_input)

        # Monkey-patch the app instance
        self.app.is_chat_active = self.is_active

    def on_unload(self):
        self.ignoreAll()
        if self.event_manager:
            self.event_manager.unsubscribe("chat_broadcast", self.add_incoming_message)
        if self.ui_window:
            self.ui_window.destroy()
        
        # Clean up the monkey-patch
        if hasattr(self.app, 'is_chat_active'):
            del self.app.is_chat_active

        self.app.logger.info(f"Плагин '{self.name}' выгружен.")

    def send_chat_message(self, message: str):
        """Called by the UI. Posts an event for the client to handle."""
        self.event_manager.post("client_send_chat_message", message)
        # Hide input after sending
        self.ui_window.toggle_input() 

    def add_incoming_message(self, data: dict):
        """Called by the EventManager when a network message arrives."""
        self.ui_window.add_message(data['from_name'], data['message'])
    
    def is_active(self) -> bool:
        """Is the chat input currently active?"""
        if not self.ui_window:
            return False
        return self.ui_window.is_visible()

