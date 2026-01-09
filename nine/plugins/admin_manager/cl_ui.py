# nine/plugins/admin_manager/cl_ui.py
from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel, DirectScrolledList
from nine.core.events import EventManager

class AdminUIModule(PluginModule):
    def on_load(self):
        self.admin_frame = None
        self.event_manager.subscribe("game_state_changed", self.on_game_state_changed)
        self.event_manager.subscribe("admin_list_updated", self.update_admin_list)

        # Keyboard shortcut to toggle UI
        self.app.accept("a", self.toggle_ui)

    def create_ui(self):
        if not self.admin_frame:
            self.admin_frame = DirectFrame(
                frameSize=(-0.5, 0.5, -0.5, 0.5),
                frameColor=(0.1, 0.1, 0.1, 0.8)
            )

            self.admin_list_box = DirectScrolledList(
                parent=self.admin_frame,
                pos=(0, 0, 0),
                scale=0.05,
                numItemsVisible=10,
                itemMakeFunction=self.make_admin_item
            )

            self.toggle_button = DirectButton(
                parent=self.admin_frame,
                text="Toggle Admin",
                command=self.toggle_ui
            )

    def make_admin_item(self, admin):
        return DirectLabel(text=admin['name'], relief=None)

    def toggle_ui(self):
        if self.admin_frame:
            if self.admin_frame.isHidden():
                self.admin_frame.show()
                self.update_admin_list()
            else:
                self.admin_frame.hide()

    def update_admin_list(self):
        admin_list = self.get_admin_list()
        self.admin_list_box['items'] = [admin for admin in admin_list]
        self.admin_list_box.refresh()

    def get_admin_list(self):
        # This should be replaced with actual logic to fetch the admin list from the server
        return [{"name": "Player1", "level": 1}, {"name": "Player2", "level": 2}]
