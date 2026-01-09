# nine/plugins/admin_manager/sv_admin.py
import sqlite3
from nine.core.plugins import PluginModule

class AdminManager(PluginModule):
    def __init__(self, context):
        super().__init__(context)
        self.conn = sqlite3.connect('admin.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS admins (player_id INTEGER PRIMARY KEY, admin_level INTEGER)''')
        self.conn.commit()

    def on_load(self):
        self.event_manager.subscribe("add_admin", self.add_admin)
        self.event_manager.subscribe("remove_admin", self.remove_admin)

    def add_admin(self, player_id, admin_level=1):
        self.cursor.execute("INSERT INTO admins (player_id, admin_level) VALUES (?, ?)", (player_id, admin_level))
        self.conn.commit()
        self.event_manager.post("admin_list_updated")

    def remove_admin(self, player_id):
        self.cursor.execute("DELETE FROM admins WHERE player_id = ?", (player_id,))
        self.conn.commit()
        self.event_manager.post("admin_list_updated")

    def is_admin(self, player_id):
        self.cursor.execute("SELECT * FROM admins WHERE player_id = ?", (player_id,))
        return self.cursor.fetchone() is not None

    def get_admin_list(self):
        self.cursor.execute("SELECT * FROM admins")
        return [{"player_id": row[0], "admin_level": row[1]} for row in self.cursor.fetchall()]
