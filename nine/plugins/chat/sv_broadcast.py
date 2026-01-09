# nine/plugins/chat/sv_broadcast.py
from nine.plugins.admin_manager.sv_admin import AdminManager

class ChatBroadcastModule(PluginModule):
    def __init__(self, context):
        super().__init__(context)
        self.admin_manager = AdminManager(context)

    def broadcast_message(self, sender_id, message_text):
        if not self.admin_manager.is_admin(sender_id) and "admin" in message_text:
            return

        # Broadcast the message to all players
        for player in self.get_players_in_radius(sender_pos=[0, 0, 0], radius=100):
            self.event_manager.post("chat_message", {"sender": sender_id, "message": message_text})
