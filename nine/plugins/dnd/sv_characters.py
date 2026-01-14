"""
Серверный модуль D&D персонажей.
Управляет созданием, выбором и удалением персонажей.
"""

import importlib.util
from pathlib import Path
from typing import Dict, Optional
from nine.core.plugins import PluginModule


def _load_constants():
    """Загружает константы из sh_constants.py в той же папке."""
    constants_path = Path(__file__).parent / "sh_constants.py"
    spec = importlib.util.spec_from_file_location("dnd_constants", constants_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_constants = _load_constants()
RACES = _constants.RACES
CLASSES = _constants.CLASSES
BACKGROUNDS = _constants.BACKGROUNDS
MAX_CHARACTERS_PER_ACCOUNT = _constants.MAX_CHARACTERS_PER_ACCOUNT
calculate_modifier = _constants.calculate_modifier
calculate_proficiency_bonus = _constants.calculate_proficiency_bonus
calculate_hp_at_level_1 = _constants.calculate_hp_at_level_1
calculate_base_ac = _constants.calculate_base_ac
get_model_for_race_gender = _constants.get_model_for_race_gender


class CharacterServerModule(PluginModule):
    """
    Серверный модуль управления D&D персонажами.
    Обрабатывает создание, выбор, удаление персонажей.
    """

    def on_load(self):
        # Маппинг client_id -> account_uuid (после авторизации)
        self.authenticated_clients: Dict[int, str] = {}
        # Маппинг client_id -> character_uuid (после выбора персонажа)
        self.active_characters: Dict[int, str] = {}
        # Маппинг character_uuid -> client_id (обратный маппинг)
        self.character_to_client: Dict[str, int] = {}

        # Подписки на события
        self.event_manager.subscribe("dnd_auth_success", self.on_auth_success)
        self.event_manager.subscribe("dnd_character_list_request", self.on_character_list_request)
        self.event_manager.subscribe("dnd_character_select", self.on_character_select)
        self.event_manager.subscribe("dnd_character_create", self.on_character_create)
        self.event_manager.subscribe("dnd_character_delete", self.on_character_delete)
        self.event_manager.subscribe("player_left", self.on_player_left)

        self.logger.info("D&D Character Server Module loaded")

    def on_unload(self):
        self.event_manager.unsubscribe("dnd_auth_success", self.on_auth_success)
        self.event_manager.unsubscribe("dnd_character_list_request", self.on_character_list_request)
        self.event_manager.unsubscribe("dnd_character_select", self.on_character_select)
        self.event_manager.unsubscribe("dnd_character_create", self.on_character_create)
        self.event_manager.unsubscribe("dnd_character_delete", self.on_character_delete)
        self.event_manager.unsubscribe("player_left", self.on_player_left)

        self.logger.info("D&D Character Server Module unloaded")

    def _get_db(self):
        """Получает DatabaseManager из контекста приложения."""
        return getattr(self.context.app, 'db', None)

    def _send_to_client(self, client_id: int, data: dict):
        """Отправляет сообщение клиенту."""
        self.event_manager.post("dnd_send_to_client", {
            "client_id": client_id,
            "data": data
        })

    def on_auth_success(self, data: dict):
        """
        Вызывается после успешной авторизации аккаунта.
        Регистрирует client_id -> account_uuid маппинг.
        """
        client_id = data.get("client_id")
        account_uuid = data.get("account_uuid")

        if client_id is not None and account_uuid:
            self.authenticated_clients[client_id] = account_uuid
            self.logger.info(f"[DND] Client {client_id} authenticated as account {account_uuid}")

    def on_character_list_request(self, data: dict):
        """
        Клиент запросил список своих персонажей.
        """
        client_id = data.get("client_id")
        if client_id is None:
            return

        account_uuid = self.authenticated_clients.get(client_id)
        if not account_uuid:
            self._send_to_client(client_id, {
                "type": "error",
                "message": "Not authenticated"
            })
            return

        db = self._get_db()
        if not db:
            self._send_to_client(client_id, {
                "type": "error",
                "message": "Database unavailable"
            })
            return

        characters = db.get_characters_by_account(account_uuid)

        self._send_to_client(client_id, {
            "type": "character_list",
            "characters": characters,
            "max_characters": MAX_CHARACTERS_PER_ACCOUNT
        })

        self.logger.debug(f"Sent character list to client {client_id}: {len(characters)} characters")

    def on_character_select(self, data: dict):
        """
        Клиент выбрал персонажа для игры.
        """
        client_id = data.get("client_id")
        character_uuid = data.get("character_uuid")
        self.logger.info(f"[DND] on_character_select: client_id={client_id}, character_uuid={character_uuid}")

        if client_id is None or not character_uuid:
            self.logger.warning(f"[DND] on_character_select: missing client_id or character_uuid")
            return

        account_uuid = self.authenticated_clients.get(client_id)
        self.logger.info(f"[DND] on_character_select: account_uuid from cache = {account_uuid}")
        if not account_uuid:
            self.logger.warning(f"[DND] on_character_select: client {client_id} not authenticated")
            self._send_to_client(client_id, {
                "type": "error",
                "message": "Not authenticated"
            })
            return

        db = self._get_db()
        if not db:
            self.logger.error(f"[DND] on_character_select: database unavailable")
            return

        # Получаем данные персонажа
        character = db.get_character(character_uuid)
        self.logger.info(f"[DND] on_character_select: character found = {character is not None}")
        if not character:
            self.logger.warning(f"[DND] on_character_select: character {character_uuid} not found")
            self._send_to_client(client_id, {
                "type": "error",
                "message": "Character not found"
            })
            return

        # Проверяем что персонаж принадлежит этому аккаунту
        char_account = character.get("account_uuid")
        self.logger.info(f"[DND] on_character_select: char_account={char_account}, expected={account_uuid}")
        if char_account != account_uuid:
            self.logger.warning(f"[DND] on_character_select: character belongs to {char_account}, not {account_uuid}")
            self._send_to_client(client_id, {
                "type": "error",
                "message": "Character does not belong to this account"
            })
            return

        # Регистрируем активного персонажа
        self.active_characters[client_id] = character_uuid
        self.character_to_client[character_uuid] = client_id

        # Обновляем last_played
        db.update_character(character_uuid, {})

        # Отправляем событие для создания игрока в мире
        self.logger.info(f"[DND] on_character_select: posting dnd_character_selected event")
        self.event_manager.post("dnd_character_selected", {
            "client_id": client_id,
            "character": character
        })

        self.logger.info(f"[DND] Client {client_id} selected character '{character.get('character_name')}'")

    def on_character_create(self, data: dict):
        """
        Клиент создаёт нового персонажа.
        """
        client_id = data.get("client_id")
        if client_id is None:
            return

        account_uuid = self.authenticated_clients.get(client_id)
        if not account_uuid:
            self._send_to_client(client_id, {
                "type": "character_create_failed",
                "reason": "Not authenticated"
            })
            return

        db = self._get_db()
        if not db:
            self._send_to_client(client_id, {
                "type": "character_create_failed",
                "reason": "Database unavailable"
            })
            return

        # Проверяем лимит персонажей
        char_count = db.get_character_count(account_uuid)
        if char_count >= MAX_CHARACTERS_PER_ACCOUNT:
            self._send_to_client(client_id, {
                "type": "character_create_failed",
                "reason": f"Maximum characters ({MAX_CHARACTERS_PER_ACCOUNT}) reached"
            })
            return

        # Валидация данных
        character_name = data.get("character_name", "").strip()
        if not character_name or len(character_name) < 2:
            self._send_to_client(client_id, {
                "type": "character_create_failed",
                "reason": "Invalid character name"
            })
            return

        race = data.get("race", "human")
        if race not in RACES:
            race = "human"

        gender = data.get("gender", "male")
        if gender not in ["male", "female"]:
            gender = "male"

        char_class = data.get("class", "fighter")
        if char_class not in CLASSES:
            char_class = "fighter"

        background = data.get("background", "")
        if background and background not in BACKGROUNDS:
            background = ""

        # Получаем характеристики
        strength = self._validate_stat(data.get("strength", 10))
        dexterity = self._validate_stat(data.get("dexterity", 10))
        constitution = self._validate_stat(data.get("constitution", 10))
        intelligence = self._validate_stat(data.get("intelligence", 10))
        wisdom = self._validate_stat(data.get("wisdom", 10))
        charisma = self._validate_stat(data.get("charisma", 10))

        # Применяем расовые бонусы
        race_data = RACES.get(race, {})
        ability_bonuses = race_data.get("ability_bonuses", {})
        strength += ability_bonuses.get("strength", 0)
        dexterity += ability_bonuses.get("dexterity", 0)
        constitution += ability_bonuses.get("constitution", 0)
        intelligence += ability_bonuses.get("intelligence", 0)
        wisdom += ability_bonuses.get("wisdom", 0)
        charisma += ability_bonuses.get("charisma", 0)

        # Рассчитываем вторичные характеристики
        con_mod = calculate_modifier(constitution)
        dex_mod = calculate_modifier(dexterity)
        hp_max = calculate_hp_at_level_1(char_class, con_mod)
        ac = calculate_base_ac(dex_mod)
        prof_bonus = calculate_proficiency_bonus(1)

        # Формируем данные персонажа
        character_data = {
            "account_uuid": account_uuid,
            "character_name": character_name,
            "race": race,
            "gender": gender,
            "class": char_class,
            "level": 1,
            "strength": strength,
            "dexterity": dexterity,
            "constitution": constitution,
            "intelligence": intelligence,
            "wisdom": wisdom,
            "charisma": charisma,
            "hp_current": hp_max,
            "hp_max": hp_max,
            "armor_class": ac,
            "proficiency_bonus": prof_bonus,
            "skills": data.get("skills", {}),
            "proficiencies": data.get("proficiencies", {}),
            "class_features": data.get("class_features", []),
            "background": background,
            "personality": data.get("personality", {}),
            "biography": data.get("biography", ""),
            "equipment": data.get("equipment", {}),
            "gold": data.get("gold", 10),
            "pos_x": 8.0,  # Стартовая позиция
            "pos_y": -3.0,
            "pos_z": 1.0,
        }

        # Создаём персонажа в БД
        char_uuid = db.create_character(character_data)
        if not char_uuid:
            self._send_to_client(client_id, {
                "type": "character_create_failed",
                "reason": "Character name already taken or database error"
            })
            return

        # Получаем созданного персонажа
        created_character = db.get_character(char_uuid)

        self._send_to_client(client_id, {
            "type": "character_created",
            "character": created_character
        })

        self.logger.info(f"Character '{character_name}' created for account {account_uuid}")

    def on_character_delete(self, data: dict):
        """
        Клиент удаляет персонажа.
        """
        client_id = data.get("client_id")
        character_uuid = data.get("character_uuid")

        if client_id is None or not character_uuid:
            return

        account_uuid = self.authenticated_clients.get(client_id)
        if not account_uuid:
            self._send_to_client(client_id, {
                "type": "error",
                "message": "Not authenticated"
            })
            return

        db = self._get_db()
        if not db:
            return

        # Удаляем (метод проверяет владельца)
        success = db.delete_character(character_uuid, account_uuid)
        if success:
            self._send_to_client(client_id, {
                "type": "character_deleted",
                "character_uuid": character_uuid
            })
            self.logger.info(f"Character {character_uuid} deleted by account {account_uuid}")
        else:
            self._send_to_client(client_id, {
                "type": "error",
                "message": "Failed to delete character"
            })

    def on_player_left(self, data: dict):
        """
        Игрок отключился - очищаем данные.
        """
        # data может содержать uuid (старый формат) или client_id
        client_id = data.get("client_id") or data.get("uuid")

        if client_id is not None:
            # Сохраняем позицию персонажа
            char_uuid = self.active_characters.get(client_id)
            if char_uuid:
                # TODO: Получить текущую позицию игрока и сохранить
                del self.active_characters[client_id]
                if char_uuid in self.character_to_client:
                    del self.character_to_client[char_uuid]

            if client_id in self.authenticated_clients:
                del self.authenticated_clients[client_id]

    def _validate_stat(self, value) -> int:
        """Валидирует значение характеристики."""
        try:
            value = int(value)
            return max(3, min(18, value))  # D&D диапазон 3-18
        except (TypeError, ValueError):
            return 10

    # =========================================================================
    # Публичные методы для использования другими модулями
    # =========================================================================

    def get_character_by_client(self, client_id: int) -> Optional[str]:
        """Получает UUID персонажа по client_id."""
        return self.active_characters.get(client_id)

    def get_client_by_character(self, character_uuid: str) -> Optional[int]:
        """Получает client_id по UUID персонажа."""
        return self.character_to_client.get(character_uuid)

    def get_account_by_client(self, client_id: int) -> Optional[str]:
        """Получает UUID аккаунта по client_id."""
        return self.authenticated_clients.get(client_id)
