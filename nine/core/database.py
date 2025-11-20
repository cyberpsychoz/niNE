import sqlite3
import json
import hashlib
import os
from pathlib import Path
from typing import Union, Any, List, Dict, Optional, Tuple

class DatabaseManager:
    """
    Управляет подключением и взаимодействием с базой данных SQLite.
    Использует реляционную схему, уникальные имена и безопасное хранение паролей.
    """
    def __init__(self, db_path: Union[str, Path] = "nine.db"):
        self.db_path = db_path
        self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            print(f"Успешное подключение к базе данных SQLite: {self.db_path}")
            self._create_tables()
            self._check_and_migrate_schema()
        except sqlite3.Error as e:
            print(f"Ошибка при подключении к SQLite: {e}")
            self.conn = None

    # --- Утилиты для паролей ---
    
    def _generate_salt(self) -> str:
        """Генерирует случайную соль."""
        return os.urandom(16).hex()

    def _hash_password(self, password: str, salt: str) -> str:
        """Хэширует пароль с использованием соли."""
        pwd_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        hashed_password = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, 100000)
        return hashed_password.hex()

    # --- Управление схемой ---

    def _create_tables(self):
        """Создает таблицу players, если она не существует, с уникальным полем name."""
        if not self.conn: return
        try:
            with self.conn:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS players (
                        uuid TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        password_hash TEXT,
                        salt TEXT,
                        pos_x REAL DEFAULT 0,
                        pos_y REAL DEFAULT 0,
                        pos_z REAL DEFAULT 0,
                        attributes TEXT
                    )
                """)
        except sqlite3.Error as e:
            print(f"Ошибка при создании таблиц: {e}")

    def _check_and_migrate_schema(self):
        """Проверяет схему, добавляет колонки и создает уникальный индекс для name."""
        if not self.conn: return
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("PRAGMA table_info(players)")
                columns = [row['name'] for row in cursor.fetchall()]

                if 'password_hash' not in columns:
                    print("Миграция: добавление колонок password_hash и salt...")
                    cursor.execute("ALTER TABLE players ADD COLUMN password_hash TEXT")
                    cursor.execute("ALTER TABLE players ADD COLUMN salt TEXT")
                
                # Создаем уникальный индекс для name, если его нет
                cursor.execute("PRAGMA index_list(players)")
                indexes = [row['name'] for row in cursor.fetchall()]
                if 'idx_players_name' not in indexes:
                    print("Миграция: создание уникального индекса для поля name...")
                    # Обработка дубликатов перед созданием индекса
                    cursor.execute("""
                        DELETE FROM players
                        WHERE rowid NOT IN (
                            SELECT MIN(rowid)
                            FROM players
                            GROUP BY name
                        )
                    """)
                    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_players_name ON players(name)")
                
                print("Миграция схемы завершена.")
        
        except sqlite3.Error as e:
            if "duplicate column name" not in str(e):
                print(f"Ошибка при миграции схемы: {e}")

    def shutdown(self):
        if self.conn:
            self.conn.close()
            print("Соединение с базой данных SQLite закрыто.")

    # --- Методы для аутентификации (по имени) ---

    def get_player_by_name(self, name: str) -> Optional[sqlite3.Row]:
        """Получает запись игрока по его имени."""
        if not self.conn: return None
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM players WHERE name=?", (name,))
        return cursor.fetchone()

    def create_player(self, player_uuid: str, name: str, password: str) -> bool:
        """Создает новую запись игрока. Возвращает True в случае успеха."""
        if not self.conn: return False
        salt = self._generate_salt()
        password_hash = self._hash_password(password, salt)
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO players (uuid, name, password_hash, salt) VALUES (?, ?, ?, ?)",
                    (player_uuid, name, password_hash, salt)
                )
            return True
        except sqlite3.IntegrityError:
            # Это ожидаемая ошибка, если имя уже занято
            print(f"Попытка создать игрока с уже существующим именем: {name}")
            return False
        except sqlite3.Error as e:
            print(f"Ошибка при создании игрока '{name}': {e}")
            return False
            
    def verify_player_password_by_name(self, name: str, password: str) -> bool:
        """Проверяет пароль для игрока по его имени."""
        player_data = self.get_player_by_name(name)
        if not (player_data and player_data['password_hash'] and player_data['salt']):
            return False
        
        stored_hash = player_data['password_hash']
        salt = player_data['salt']
        new_hash = self._hash_password(password, salt)
        return new_hash == stored_hash

    def update_player_uuid(self, name: str, new_uuid: str):
        """Обновляет UUID для игрока, найденного по имени.
        Может быть полезно, если пользователь заходит с новой машины.
        """
        if not self.conn: return
        try:
            with self.conn:
                self.conn.execute("UPDATE players SET uuid=? WHERE name=?", (new_uuid, name))
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении UUID для игрока '{name}': {e}")


    # --- Методы для работы с атрибутами ---

    def get_player_all_attributes(self, player_uuid: str) -> dict:
        """Получает все атрибуты игрока по UUID."""
        if not self.conn: return {}
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM players WHERE uuid = ?", (player_uuid,))
            row = cursor.fetchone()
            if row:
                result = { "name": row["name"], "pos": [row["pos_x"], row["pos_y"], row["pos_z"]] }
                if row["attributes"]:
                    try:
                        custom_attrs = json.loads(row["attributes"])
                        result.update(custom_attrs)
                    except (json.JSONDecodeError, TypeError): pass
                return result
            return {}
        except sqlite3.Error as e:
            print(f"Ошибка при загрузке всех атрибутов для '{player_uuid}': {e}")
            return {}

    def set_player_attribute(self, player_uuid: str, attribute: str, value: Any):
        """Устанавливает значение атрибута для игрока по UUID."""
        if not self.conn: return
        if attribute in ['password_hash', 'salt', 'uuid']: return # Запрет опасных изменений

        core_attributes_map = { "name": "name", "pos": ("pos_x", "pos_y", "pos_z") }
        
        try:
            with self.conn:
                if attribute in core_attributes_map:
                    if attribute == "pos":
                        if isinstance(value, list) and len(value) == 3:
                            self.conn.execute("UPDATE players SET pos_x=?, pos_y=?, pos_z=? WHERE uuid=?", (value[0], value[1], value[2], player_uuid))
                    else: # name
                        # Убедимся, что новое имя не занято
                        self.conn.execute("UPDATE players SET name=? WHERE uuid=?", (value, player_uuid))
                else: # Кастомный атрибут в JSON
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT attributes FROM players WHERE uuid = ?", (player_uuid,))
                    row = cursor.fetchone()
                    custom_attrs = json.loads(row['attributes']) if row and row['attributes'] else {}
                    custom_attrs[attribute] = value
                    self.conn.execute("UPDATE players SET attributes=? WHERE uuid=?", (json.dumps(custom_attrs), player_uuid))
        except sqlite3.IntegrityError:
             print(f"Ошибка: Имя '{value}' уже занято.")
        except sqlite3.Error as e:
            print(f"Ошибка при установке атрибута '{attribute}' для '{player_uuid}': {e}")
