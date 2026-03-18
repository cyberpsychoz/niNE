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
        """Создает таблицы players и game_characters, если они не существуют."""
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
            # Создаем таблицу D&D персонажей
            self.create_characters_table()
            # Создаем таблицу фракций
            self.create_factions_table()
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

                # Миграция: добавление роли пользователя
                if 'role' not in columns:
                    print("Миграция: добавление колонки role в players...")
                    cursor.execute("ALTER TABLE players ADD COLUMN role TEXT DEFAULT 'player'")

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

                # Миграция: добавление фракции в game_characters
                cursor.execute("PRAGMA table_info(game_characters)")
                char_columns = [row['name'] for row in cursor.fetchall()]
                if char_columns and 'faction' not in char_columns:
                    print("Миграция: добавление колонки faction в game_characters...")
                    cursor.execute("ALTER TABLE game_characters ADD COLUMN faction TEXT DEFAULT 'neutral'")

                # Миграция: добавление колонок для системы заклинаний
                if char_columns and 'spells_known' not in char_columns:
                    print("Миграция: добавление колонок для системы заклинаний...")
                    cursor.execute("ALTER TABLE game_characters ADD COLUMN spells_known TEXT DEFAULT '[]'")
                    cursor.execute("ALTER TABLE game_characters ADD COLUMN spells_prepared TEXT DEFAULT '[]'")
                    cursor.execute("ALTER TABLE game_characters ADD COLUMN spell_slots_current TEXT DEFAULT '{}'")
                    cursor.execute("ALTER TABLE game_characters ADD COLUMN spell_slots_max TEXT DEFAULT '{}'")

                # Миграция: добавление колонки inventory для персистентного инвентаря
                if char_columns and 'inventory' not in char_columns:
                    print("Миграция: добавление колонки inventory в game_characters...")
                    cursor.execute("ALTER TABLE game_characters ADD COLUMN inventory TEXT DEFAULT '[]'")

                # Миграция: добавление hit dice для системы отдыха
                if char_columns and 'hit_dice_current' not in char_columns:
                    print("Миграция: добавление колонок hit dice...")
                    cursor.execute("ALTER TABLE game_characters ADD COLUMN hit_dice_current INTEGER DEFAULT 1")
                    cursor.execute("ALTER TABLE game_characters ADD COLUMN hit_dice_max INTEGER DEFAULT 1")

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

    # ==========================================================================
    # D&D CHARACTER SYSTEM - Методы для работы с игровыми персонажами
    # ==========================================================================

    def create_characters_table(self):
        """Создает таблицу game_characters для D&D персонажей."""
        if not self.conn:
            return
        try:
            with self.conn:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_characters (
                        uuid TEXT PRIMARY KEY,
                        account_uuid TEXT NOT NULL,
                        character_name TEXT NOT NULL UNIQUE,

                        -- Базовые характеристики
                        race TEXT NOT NULL DEFAULT 'human',
                        gender TEXT NOT NULL DEFAULT 'male',
                        model TEXT NOT NULL DEFAULT 'human_male',
                        class TEXT NOT NULL DEFAULT 'fighter',
                        level INTEGER DEFAULT 1,
                        experience INTEGER DEFAULT 0,

                        -- D&D атрибуты (6 основных)
                        strength INTEGER DEFAULT 10,
                        dexterity INTEGER DEFAULT 10,
                        constitution INTEGER DEFAULT 10,
                        intelligence INTEGER DEFAULT 10,
                        wisdom INTEGER DEFAULT 10,
                        charisma INTEGER DEFAULT 10,

                        -- Боевые характеристики
                        hp_current INTEGER DEFAULT 10,
                        hp_max INTEGER DEFAULT 10,
                        armor_class INTEGER DEFAULT 10,
                        proficiency_bonus INTEGER DEFAULT 2,

                        -- JSON-поля для комплексных данных
                        skills TEXT DEFAULT '{}',
                        proficiencies TEXT DEFAULT '{}',
                        class_features TEXT DEFAULT '[]',

                        -- Предыстория и RP
                        background TEXT DEFAULT '',
                        personality TEXT DEFAULT '{}',
                        biography TEXT DEFAULT '',

                        -- Инвентарь и экипировка
                        equipment TEXT DEFAULT '{}',
                        gold INTEGER DEFAULT 0,

                        -- Система заклинаний
                        spells_known TEXT DEFAULT '[]',
                        spells_prepared TEXT DEFAULT '[]',
                        spell_slots_current TEXT DEFAULT '{}',
                        spell_slots_max TEXT DEFAULT '{}',

                        -- Система отдыха
                        hit_dice_current INTEGER DEFAULT 1,
                        hit_dice_max INTEGER DEFAULT 1,

                        -- Позиция в мире
                        pos_x REAL DEFAULT 0,
                        pos_y REAL DEFAULT 0,
                        pos_z REAL DEFAULT 0,

                        -- Мета
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                        FOREIGN KEY (account_uuid) REFERENCES players(uuid)
                    )
                """)
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_characters_account ON game_characters(account_uuid)"
                )
                print("Таблица game_characters создана/проверена.")
        except sqlite3.Error as e:
            print(f"Ошибка при создании таблицы game_characters: {e}")

    def get_characters_by_account(self, account_uuid: str) -> List[Dict]:
        """Получает список персонажей аккаунта."""
        if not self.conn:
            return []
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """SELECT uuid, character_name, race, gender, model, class, level,
                          hp_current, hp_max, last_played
                   FROM game_characters
                   WHERE account_uuid = ?
                   ORDER BY last_played DESC""",
                (account_uuid,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            print(f"Ошибка при получении персонажей для аккаунта '{account_uuid}': {e}")
            return []

    def get_character_count(self, account_uuid: str) -> int:
        """Получает количество персонажей аккаунта."""
        if not self.conn:
            return 0
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM game_characters WHERE account_uuid = ?",
                (account_uuid,)
            )
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Ошибка при подсчёте персонажей: {e}")
            return 0

    def get_character(self, char_uuid: str) -> Optional[Dict]:
        """Получает полные данные персонажа по UUID."""
        if not self.conn:
            return None
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM game_characters WHERE uuid = ?", (char_uuid,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # Парсим JSON поля
                for json_field in ['skills', 'proficiencies', 'class_features', 'personality', 'equipment',
                                   'inventory', 'spells_known', 'spells_prepared', 'spell_slots_current', 'spell_slots_max']:
                    if result.get(json_field):
                        try:
                            result[json_field] = json.loads(result[json_field])
                        except (json.JSONDecodeError, TypeError):
                            if json_field in ('class_features', 'spells_known', 'spells_prepared'):
                                result[json_field] = []
                            else:
                                result[json_field] = {}
                # Конвертируем datetime в строки для JSON сериализации
                for date_field in ['created_at', 'last_played']:
                    if result.get(date_field) and hasattr(result[date_field], 'isoformat'):
                        result[date_field] = result[date_field].isoformat()
                return result
            return None
        except sqlite3.Error as e:
            print(f"Ошибка при получении персонажа '{char_uuid}': {e}")
            return None

    def get_character_by_name(self, character_name: str) -> Optional[Dict]:
        """Получает персонажа по имени."""
        if not self.conn:
            return None
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM game_characters WHERE character_name = ?", (character_name,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                for json_field in ['skills', 'proficiencies', 'class_features', 'personality', 'equipment',
                                   'inventory', 'spells_known', 'spells_prepared', 'spell_slots_current', 'spell_slots_max']:
                    if result.get(json_field):
                        try:
                            result[json_field] = json.loads(result[json_field])
                        except (json.JSONDecodeError, TypeError):
                            if json_field in ('class_features', 'spells_known', 'spells_prepared'):
                                result[json_field] = []
                            else:
                                result[json_field] = {}
                return result
            return None
        except sqlite3.Error as e:
            print(f"Ошибка при получении персонажа по имени '{character_name}': {e}")
            return None

    def create_character(self, data: Dict) -> Optional[str]:
        """
        Создает нового персонажа. Возвращает UUID созданного персонажа или None.

        Обязательные поля в data:
        - account_uuid: UUID аккаунта
        - character_name: имя персонажа
        - race, gender, class: базовые параметры
        """
        if not self.conn:
            return None

        import uuid
        char_uuid = str(uuid.uuid4())

        # Формируем модель из расы и пола
        model = f"{data.get('race', 'human')}_{data.get('gender', 'male')}"

        try:
            with self.conn:
                self.conn.execute("""
                    INSERT INTO game_characters (
                        uuid, account_uuid, character_name,
                        race, gender, model, class, level, faction,
                        strength, dexterity, constitution, intelligence, wisdom, charisma,
                        hp_current, hp_max, armor_class, proficiency_bonus,
                        skills, proficiencies, class_features,
                        background, personality, biography,
                        equipment, gold,
                        pos_x, pos_y, pos_z
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    char_uuid,
                    data.get('account_uuid'),
                    data.get('character_name'),
                    data.get('race', 'human'),
                    data.get('gender', 'male'),
                    model,
                    data.get('class', 'fighter'),
                    data.get('level', 1),
                    data.get('faction', 'neutral'),
                    data.get('strength', 10),
                    data.get('dexterity', 10),
                    data.get('constitution', 10),
                    data.get('intelligence', 10),
                    data.get('wisdom', 10),
                    data.get('charisma', 10),
                    data.get('hp_current', 10),
                    data.get('hp_max', 10),
                    data.get('armor_class', 10),
                    data.get('proficiency_bonus', 2),
                    json.dumps(data.get('skills', {})),
                    json.dumps(data.get('proficiencies', {})),
                    json.dumps(data.get('class_features', [])),
                    data.get('background', ''),
                    json.dumps(data.get('personality', {})),
                    data.get('biography', ''),
                    json.dumps(data.get('equipment', {})),
                    data.get('gold', 0),
                    data.get('pos_x', 0),
                    data.get('pos_y', 0),
                    data.get('pos_z', 0),
                ))
            return char_uuid
        except sqlite3.IntegrityError as e:
            print(f"Ошибка: Имя персонажа '{data.get('character_name')}' уже занято.")
            return None
        except sqlite3.Error as e:
            print(f"Ошибка при создании персонажа: {e}")
            return None

    def update_character(self, char_uuid: str, data: Dict) -> bool:
        """Обновляет данные персонажа."""
        if not self.conn or not data:
            return False

        # Поля, которые нельзя обновлять напрямую
        protected_fields = {'uuid', 'account_uuid', 'created_at'}

        # JSON поля требуют сериализации
        json_fields = {'skills', 'proficiencies', 'class_features', 'personality', 'equipment',
                       'inventory', 'spells_known', 'spells_prepared', 'spell_slots_current', 'spell_slots_max'}

        # Формируем SQL запрос
        set_clauses = []
        values = []

        for key, value in data.items():
            if key in protected_fields:
                continue
            if key in json_fields:
                value = json.dumps(value)
            set_clauses.append(f"{key} = ?")
            values.append(value)

        if not set_clauses:
            return False

        # Обновляем last_played
        set_clauses.append("last_played = CURRENT_TIMESTAMP")
        values.append(char_uuid)

        try:
            with self.conn:
                self.conn.execute(
                    f"UPDATE game_characters SET {', '.join(set_clauses)} WHERE uuid = ?",
                    values
                )
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении персонажа '{char_uuid}': {e}")
            return False

    def delete_character(self, char_uuid: str, account_uuid: str) -> bool:
        """
        Удаляет персонажа. Требует account_uuid для проверки владельца.
        """
        if not self.conn:
            return False
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute(
                    "DELETE FROM game_characters WHERE uuid = ? AND account_uuid = ?",
                    (char_uuid, account_uuid)
                )
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Ошибка при удалении персонажа '{char_uuid}': {e}")
            return False

    def update_character_position(self, char_uuid: str, pos_x: float, pos_y: float, pos_z: float) -> bool:
        """Обновляет позицию персонажа в мире."""
        if not self.conn:
            return False
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE game_characters SET pos_x = ?, pos_y = ?, pos_z = ?, last_played = CURRENT_TIMESTAMP WHERE uuid = ?",
                    (pos_x, pos_y, pos_z, char_uuid)
                )
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении позиции персонажа '{char_uuid}': {e}")
            return False

    def update_character_model(self, char_uuid: str, model: str) -> bool:
        """Обновляет модель персонажа (для админ-команды /charsetmodel)."""
        if not self.conn:
            return False
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE game_characters SET model = ? WHERE uuid = ?",
                    (model, char_uuid)
                )
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении модели персонажа '{char_uuid}': {e}")
            return False

    def update_character_faction(self, char_uuid: str, faction: str) -> bool:
        """Обновляет фракцию персонажа (для админ-команды /charsetfaction)."""
        if not self.conn:
            return False
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE game_characters SET faction = ? WHERE uuid = ?",
                    (faction, char_uuid)
                )
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении фракции персонажа '{char_uuid}': {e}")
            return False

    # ==========================================================================
    # FACTIONS SYSTEM - Методы для работы с фракциями
    # ==========================================================================

    def create_factions_table(self):
        """Создает таблицу фракций с начальными данными."""
        if not self.conn:
            return
        try:
            with self.conn:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS factions (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        name_ru TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        spawn_x REAL DEFAULT 8.0,
                        spawn_y REAL DEFAULT -3.0,
                        spawn_z REAL DEFAULT 1.0,
                        color TEXT DEFAULT '#FFFFFF'
                    )
                """)
                # Заполняем начальные данные если таблица пуста
                cursor = self.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM factions")
                if cursor.fetchone()[0] == 0:
                    self.conn.executemany(
                        """INSERT INTO factions (id, name, name_ru, description, spawn_x, spawn_y, spawn_z, color)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        [
                            ('alliance', 'Alliance', 'Альянс',
                             'Союз людей, эльфов и дварфов. Стремятся к порядку и справедливости.',
                             8.0, -3.0, 1.0, '#0066CC'),
                            ('horde', 'Horde', 'Орда',
                             'Объединение орков и других воинственных рас. Ценят силу и честь.',
                             15.0, -3.0, 1.0, '#CC0000'),
                            ('neutral', 'Neutral', 'Нейтралы',
                             'Свободные искатели приключений, не связанные политикой.',
                             0.0, 0.0, 1.0, '#999999'),
                            ('undead', 'Undead', 'Нежить',
                             'Проклятые существа из тёмных земель. Отвергнуты живыми.',
                             -10.0, -3.0, 1.0, '#6600CC'),
                        ]
                    )
                    print("Таблица factions заполнена начальными данными.")
                print("Таблица factions создана/проверена.")
        except sqlite3.Error as e:
            print(f"Ошибка при создании таблицы factions: {e}")

    def get_faction(self, faction_id: str) -> Optional[Dict]:
        """Получает данные фракции по ID."""
        if not self.conn:
            return None
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM factions WHERE id = ?", (faction_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"Ошибка при получении фракции '{faction_id}': {e}")
            return None

    def get_all_factions(self) -> List[Dict]:
        """Получает список всех фракций."""
        if not self.conn:
            return []
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM factions ORDER BY id")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Ошибка при получении списка фракций: {e}")
            return []

    # ==========================================================================
    # ROLES SYSTEM - Методы для работы с ролями пользователей
    # ==========================================================================

    def get_player_role(self, account_uuid: str) -> str:
        """Получает роль игрока (player/dm/admin)."""
        if not self.conn:
            return "player"
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT role FROM players WHERE uuid = ?", (account_uuid,))
            row = cursor.fetchone()
            return row['role'] if row and row['role'] else "player"
        except sqlite3.Error as e:
            print(f"Ошибка при получении роли игрока '{account_uuid}': {e}")
            return "player"

    def set_player_role(self, account_uuid: str, role: str) -> bool:
        """Устанавливает роль игрока."""
        valid_roles = ('player', 'dm', 'admin')
        if role not in valid_roles:
            print(f"Недопустимая роль: {role}. Допустимые: {valid_roles}")
            return False
        if not self.conn:
            return False
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE players SET role = ? WHERE uuid = ?",
                    (role, account_uuid)
                )
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при установке роли для '{account_uuid}': {e}")
            return False
