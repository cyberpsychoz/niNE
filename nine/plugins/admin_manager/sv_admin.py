from nine.core.plugins import PluginModule
import sqlite3

class AdminServerModule(PluginModule):
    def on_load(self):
        self.admin_db_path = self.plugin_path / "admin.db"
        self.conn = sqlite3.connect(str(self.admin_db_path))
        self.cursor = self.conn.cursor()

        # Create table for admins if it doesn't exist
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                player_id TEXT PRIMARY KEY,
                admin_level INTEGER
            )
        """)
        self.conn.commit()

    def on_unload(self):
        self.conn.close()

    def add_admin(self, player_id, admin_level=1):
        try:
            self.cursor.execute("INSERT INTO admins (player_id, admin_level) VALUES (?, ?)", (player_id, admin_level))
            self.conn.commit()
            self.logger.info(f"Added {player_id} as an admin with level {admin_level}")
        except sqlite3.IntegrityError:
            self.logger.warning(f"{player_id} is already an admin.")

    def remove_admin(self, player_id):
        try:
            self.cursor.execute("DELETE FROM admins WHERE player_id = ?", (player_id,))
            self.conn.commit()
            self.logger.info(f"Removed {player_id} from admins.")
        except sqlite3.Error as e:
            self.logger.error(f"Error removing admin: {e}")

    def is_admin(self, player_id):
        self.cursor.execute("SELECT * FROM admins WHERE player_id = ?", (player_id,))
        return self.cursor.fetchone() is not None