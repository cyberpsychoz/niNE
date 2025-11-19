import sqlite3
import json
import hashlib
import os
from pathlib import Path
from typing import Union, Any, List, Dict, Optional, Tuple

class DatabaseManager:
    """
    Управляет подключением и взаимодействием с базой данных SQLite.
    Использует реляционную схему и безопасное хранение паролей.
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
        """Создает таблицу players, если она не существует."""
        if not self.conn: return
        try:
            cursor = self.conn.cursor()
            # Добавляем колонки для хэша пароля и соли
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    uuid TEXT PRIMARY KEY,
                    name TEXT,
                    password_hash TEXT,
                    salt TEXT,
                    pos_x REAL DEFAULT 0,
                    pos_y REAL DEFAULT 0,
                    pos_z REAL DEFAULT 0,
                    attributes TEXT
                )
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Ошибка при создании таблиц: {e}")

    def _check_and_migrate_schema(self):
        """Проверяет схему и добавляет колонки для пароля, если их нет."""
        if not self.conn: return
        try:
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(players)")
            columns = [row['name'] for row in cursor.fetchall()]

            if 'password_hash' not in columns:
                print("Обнаружена устаревшая схема БД. Добавление колонок для аутентификации...")
                cursor.execute("ALTER TABLE players ADD COLUMN password_hash TEXT")
                cursor.execute("ALTER TABLE players ADD COLUMN salt TEXT")
                self.conn.commit()
                print("Миграция схемы для аутентификации завершена.")
        
        except sqlite3.Error as e:
            if "duplicate column name" not in str(e):
                print(f"Ошибка при миграции схемы: {e}")

    def shutdown(self):
        if self.conn:
            self.conn.close()
            print("Соединение с базой данных SQLite закрыто.")

    # --- Методы для аутентификации ---

    def player_exists(self, player_uuid: str) -> bool:
        """Проверяет, существует ли игрок с таким UUID."""
        if not self.conn: return False
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM players WHERE uuid=?", (player_uuid,))
        return cursor.fetchone() is not None

    def create_player(self, player_uuid: str, name: str, password: str):
        """Создает новую запись игрока с захэшированным паролем."""
        if not self.conn: return
        salt = self._generate_salt()
        password_hash = self._hash_password(password, salt)
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO players (uuid, name, password_hash, salt) VALUES (?, ?, ?, ?)",
                    (player_uuid, name, password_hash, salt)
                )
        except sqlite3.Error as e:
            print(f"Ошибка при создании игрока '{player_uuid}': {e}")
            
    def get_player_auth_data(self, player_uuid: str) -> Optional[Tuple[str, str]]:
        """Возвращает хэш пароля и соль для игрока."""
        if not self.conn: return None
        cursor = self.conn.cursor()
        cursor.execute("SELECT password_hash, salt FROM players WHERE uuid=?", (player_uuid,))
        row = cursor.fetchone()
        if row and row['password_hash'] and row['salt']:
            return row['password_hash'], row['salt']
        return None

    def verify_player_password(self, player_uuid: str, password: str) -> bool:
        """Проверяет, совпадает ли пароль с сохраненным хэшем."""
        auth_data = self.get_player_auth_data(player_uuid)
        if not auth_data:
            return False
        
        stored_hash, salt = auth_data
        new_hash = self._hash_password(password, salt)
        return new_hash == stored_hash

    # --- Методы для работы с атрибутами ---

    def get_player_all_attributes(self, player_uuid: str) -> dict:
        """Получает все атрибуты игрока, собирая их из разных колонок."""
        if not self.conn: return {}
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM players WHERE uuid = ?", (player_uuid,))
            row = cursor.fetchone()
            if row:
                result = {
                    "name": row["name"],
                    "pos": [row["pos_x"], row["pos_y"], row["pos_z"]]
                }
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
        """Устанавливает значение атрибута для игрока в соответствующую колонку."""
        if not self.conn: return
        
        core_attributes_map = { "name": "name", "pos": ("pos_x", "pos_y", "pos_z") }
        # Запрещаем изменение пароля через этот метод
        if attribute in ['password_hash', 'salt']: return

        try:
            with self.conn:
                if attribute in core_attributes_map:
                    if attribute == "pos":
                        if isinstance(value, list) and len(value) == 3:
                            self.conn.execute("""
                                UPDATE players SET pos_x=?, pos_y=?, pos_z=? WHERE uuid=?
                            """, (value[0], value[1], value[2], player_uuid))
                    else: # name
                        self.conn.execute("UPDATE players SET name=? WHERE uuid=?", (value, player_uuid))
                else: # Кастомный атрибут в JSON
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT attributes FROM players WHERE uuid = ?", (player_uuid,))
                    row = cursor.fetchone()
                    custom_attrs = json.loads(row['attributes']) if row and row['attributes'] else {}
                    custom_attrs[attribute] = value
                    self.conn.execute("UPDATE players SET attributes=? WHERE uuid=?", (json.dumps(custom_attrs), player_uuid))
        except sqlite3.Error as e:
            print(f"Ошибка при установке атрибута '{attribute}' для '{player_uuid}': {e}")

    def get_player_attribute(self, player_uuid: str, attribute: str) -> Union[Any, None]:
        # ... (реализация остается прежней, но для краткости убрана)
        pass

    def save_player_inventory(self, player_uuid: str, inventory: list):
        self.set_player_attribute(player_uuid, "inventory", inventory)

    def get_player_inventory(self, player_uuid: str) -> Union[List, None]:
        return self.get_player_attribute(player_uuid, "inventory")