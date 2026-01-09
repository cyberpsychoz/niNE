# nine/plugins/inventory/cl_inventory.py
from nine.plugins.admin_manager.cl_ui import AdminUIModule
from direct.showbase.DirectObject import DirectObject
from nine.core.plugins import PluginModule

class InventoryClientModule(PluginModule, DirectObject):
    def __init__(self, context):
        super().__init__(context)
        self.admin_module = AdminUIModule(context)

    def add_item(self, item_id, player_id):
        if not self.admin_module.is_admin(player_id):
            return

        # Add the item to the player's inventory
        self.event_manager.post("add_inventory_item", {"player_id": player_id, "item_id": item_id})
