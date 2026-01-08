from nine.core.plugins import PluginModule
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel

class AdminUIModule(PluginModule):
    def on_load(self):
        self.admin_frame = None
        self.event_manager.subscribe("game_state_changed", self.on_game_state_changed)

        # Keyboard shortcut to toggle UI
        self.app.accept("a", self.toggle_ui)

        self.create_ui()

    def on_unload(self):
        if self.admin_frame:
            self.admin_frame.destroy()
        self.event_manager.unsubscribe("game_state_changed", self.on_game_state_changed)

    def create_ui(self):
        """Create UI for admin commands"""
        self.admin_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.1, 0.9),
            frameSize=(-0.6, 0.6, -0.8, 0.8),
            pos=(0, 0, 0)
        )

        # Title
        DirectLabel(
            text="Admin Commands",
            parent=self.admin_frame,
            scale=0.1,
            pos=(0, 0, 0.7),
            text_fg=(1, 1, 1, 1)
        )

        self.admin_frame.hide()

    def toggle_ui(self):
        """Toggle visibility of the admin UI"""
        if self.admin_frame.isHidden():
            self.admin_frame.show()
        else:
            self.admin_frame.hide()

    def on_game_state_changed(self, data: dict):
        """Hide UI in menu"""
        if data.get("state") != "IN_GAME":
            self.admin_frame.hide()