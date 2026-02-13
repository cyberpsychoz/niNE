"""
WebView API - Python API для вызовов из JavaScript.

JavaScript вызывает методы через:
    await pywebview.api.exit_game()
    await pywebview.api.attempt_login(ip, name, password)
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class WebViewAPI:
    """Python API exposed to JavaScript via pywebview."""

    def __init__(self, webview_manager, callbacks: Dict[str, Any]):
        """
        Initialize WebView API.

        Args:
            webview_manager: WebViewUIManager instance
            callbacks: Dictionary of callback functions from client
        """
        self.manager = webview_manager
        self.callbacks = callbacks
        self.app = webview_manager.app

        # Store login credentials for get_login_credentials() to retrieve
        self._login_credentials = {}

        # Подписываемся на события для отправки в JS
        self._subscribe_to_events()

        logger.info("WebViewAPI initialized")

    def _subscribe_to_events(self):
        """Subscribe to game events and forward to JavaScript."""
        event_manager = self.app.event_manager

        # Chat events
        event_manager.subscribe("chat_broadcast", self._on_chat_message)

        # Combat events
        event_manager.subscribe("combat_started", self._on_combat_started)
        event_manager.subscribe("combat_ended", self._on_combat_ended)
        event_manager.subscribe("combat_turn_start", self._on_combat_turn_start)
        event_manager.subscribe("combat_action_result", self._on_combat_action_result)
        event_manager.subscribe("combat_round_start", self._on_combat_round_start)

        # Character/inventory events
        event_manager.subscribe("character_sheet", self._on_character_sheet)
        event_manager.subscribe("inventory_update", self._on_inventory_update)
        event_manager.subscribe("equipment_update", self._on_equipment_update)

        # Conditions
        event_manager.subscribe("conditions_update", self._on_conditions_update)

        # Game state
        event_manager.subscribe("game_state_changed", self._on_game_state_changed)

        # World state
        event_manager.subscribe("world_state_received", self._on_world_state)

        # Spellcasting events
        event_manager.subscribe("spellcasting_update", self._on_spellcasting_update)
        event_manager.subscribe("spell_cast_result", self._on_spell_cast_result)

        # Quest events
        event_manager.subscribe("quest_list", self._on_quest_list)
        event_manager.subscribe("quest_accepted", self._on_quest_accepted)
        event_manager.subscribe("quest_completed", self._on_quest_completed)
        event_manager.subscribe("quest_objective_progress", self._on_quest_objective_progress)
        event_manager.subscribe("quest_ready_to_turn_in", self._on_quest_ready_to_turn_in)

        # Rest events
        event_manager.subscribe("show_rest_dialog", self._on_show_rest_dialog)
        event_manager.subscribe("rest_result", self._on_rest_result)
        event_manager.subscribe("hit_die_result", self._on_hit_die_result)

        # Character sheet tab navigation
        event_manager.subscribe("open_character_sheet_tab", self._on_open_character_sheet_tab)

        # Context menu events
        event_manager.subscribe("show_context_menu", self._on_show_context_menu)
        event_manager.subscribe("hide_context_menu", self._on_hide_context_menu)

        logger.info("Subscribed to game events")

    # ============================================================
    # JavaScript -> Python calls
    # ============================================================

    def exit_game(self):
        """Exit the game (called from main thread via _dispatch_js_call)."""
        logger.info("Exit game called from JavaScript")
        if "exit" in self.callbacks:
            self.callbacks["exit"]()
        else:
            logger.warning("No exit callback registered")

    def open_login_menu(self):
        """Open login menu (called from JavaScript)."""
        logger.info("Open login menu called from JavaScript")
        if "connect" in self.callbacks:
            self.callbacks["connect"]()
        else:
            logger.warning("No connect callback registered")

    def attempt_login(self, ip: str, nickname: str, password: str):
        """
        Attempt login to server (called from JavaScript).

        Args:
            ip: Server IP address
            nickname: Player nickname
            password: Server password
        """
        logger.info(f"Attempt login: {nickname} -> {ip}")

        # Store credentials for get_login_credentials() to retrieve
        # The client.attempt_login() will call ui.get_login_credentials()
        self._login_credentials = {
            "ip": ip,
            "name": nickname,
            "password": password
        }

        if "attempt_login" in self.callbacks:
            # client.attempt_login() takes no arguments - it reads from get_login_credentials()
            self.callbacks["attempt_login"]()
        else:
            logger.warning("No attempt_login callback registered")

    def get_login_credentials(self) -> Dict[str, Any]:
        """
        Return stored login credentials.

        Called by client.attempt_login() to get the credentials
        that were passed from JavaScript.
        """
        return self._login_credentials

    def close_login_menu(self):
        """Close login menu (called from JavaScript)."""
        logger.info("Close login menu called from JavaScript")
        if "close_login_menu" in self.callbacks:
            self.callbacks["close_login_menu"]()
        else:
            logger.warning("No close_login_menu callback registered")

    def open_settings(self):
        """Open settings menu (called from JavaScript)."""
        logger.info("Open settings called from JavaScript")
        if "settings" in self.callbacks:
            self.callbacks["settings"]()
        else:
            logger.warning("No settings callback registered")

    def save_settings(self, settings: Dict[str, Any]):
        """
        Save settings (called from main thread via _dispatch_js_call).

        Args:
            settings: Dictionary of settings to save
        """
        logger.info(f"Saving settings from JavaScript: {settings}")

        # Thread-safe update of user_config
        lock = getattr(self.manager, '_config_lock', None)
        if lock:
            lock.acquire()
        try:
            self.app.user_config.update(settings)

            # Save to config.json
            try:
                import json
                with open("config.json", "w") as f:
                    json.dump(self.app.user_config, f, indent=4)
                logger.info("Settings saved successfully")
            except Exception as e:
                logger.error(f"Failed to save settings: {e}")
        finally:
            if lock:
                lock.release()

        # Apply some settings immediately (main thread, no lock needed)
        if "camera_sensitivity" in settings:
            self.app.camera_sensitivity = settings["camera_sensitivity"]
        if "invert_mouse_x" in settings:
            self.app.invert_mouse_x = settings["invert_mouse_x"]
        if "invert_mouse_y" in settings:
            self.app.invert_mouse_y = settings["invert_mouse_y"]
        if "fov" in settings:
            self.app.fov = settings["fov"]

        # Resolution
        if "resolution" in settings:
            try:
                w, h = map(int, settings["resolution"].split("x"))
                from panda3d.core import WindowProperties
                props = WindowProperties()
                props.setSize(w, h)
                self.app.win.requestProperties(props)
            except Exception:
                pass

        # Camera controller
        cc = getattr(self.app, 'camera_controller', None)
        if cc:
            if "fov" in settings:
                cc.set_fov(settings["fov"])
            if "third_person_camera" in settings:
                cc.set_third_person(settings["third_person_camera"])
                if hasattr(self.app, 'update_player_model_visibility'):
                    self.app.update_player_model_visibility()
            if "camera_sensitivity" in settings:
                cc.sensitivity = settings["camera_sensitivity"] * 30.0
            if "invert_mouse_x" in settings:
                cc.invert_x = settings["invert_mouse_x"]
            if "invert_mouse_y" in settings:
                cc.invert_y = settings["invert_mouse_y"]

        # Audio volumes — Panda3D side
        am = getattr(self.app, 'audio_manager', None)
        if am:
            from nine.core.audio_manager import AudioChannel
            if "audio_master_volume" in settings:
                am.set_master_volume(settings["audio_master_volume"] / 100.0)
            if "audio_bgm_volume" in settings:
                am.set_channel_volume(AudioChannel.BGM, settings["audio_bgm_volume"] / 100.0)
            if "audio_sfx_volume" in settings:
                am.set_channel_volume(AudioChannel.SFX, settings["audio_sfx_volume"] / 100.0)
            if "audio_ambient_volume" in settings:
                am.set_channel_volume(AudioChannel.BGS, settings["audio_ambient_volume"] / 100.0)

        # Audio volumes — JS SoundManager side (menu BGM, UI sounds)
        self.manager.send_to_js("audio_volume_changed", {
            "master_volume": settings.get("audio_master_volume", 65) / 100.0,
            "bgm_volume": settings.get("audio_bgm_volume", 69) / 100.0,
            "ui_volume": settings.get("audio_ui_volume", 70) / 100.0,
        })

    def send_chat_message(self, message: str):
        """
        Send chat message (called from JavaScript).

        Args:
            message: Chat message text
        """
        logger.info(f"Chat message from JavaScript: {message}")
        # Post as plain string (same format as chat plugin cl_ui.py)
        self.app.event_manager.post("client_send_chat_message", message)

    def set_chat_active(self, active: bool):
        """Set chat active state (called from JavaScript when chat opens/closes)."""
        self.app._web_chat_active = bool(active)
        # Reset movement keys to prevent stuck walking when chat opens
        if active and hasattr(self.app, 'keyMap'):
            for key in self.app.keyMap:
                self.app.keyMap[key] = False
        logger.debug(f"Chat active: {active}")

    def select_character(self, character_uuid: str):
        """Select a character to play (called from JavaScript)."""
        logger.info(f"Select character: {character_uuid}")
        if "select_character" in self.callbacks:
            self.callbacks["select_character"](character_uuid)
        else:
            logger.warning("No select_character callback registered")

    def disconnect(self):
        """Disconnect from server (called from JavaScript)."""
        logger.info("Disconnect called from JavaScript")
        if hasattr(self.app, 'disconnect_from_server'):
            self.app.disconnect_from_server()
        else:
            logger.warning("No disconnect_from_server method found")

    def get_settings(self):
        """Return current settings (called from JavaScript)."""
        logger.info("get_settings called from JavaScript")
        lock = getattr(self.manager, '_config_lock', None)
        if lock:
            with lock:
                return dict(self.app.user_config)
        return dict(self.app.user_config)

    def hide_in_game_menu(self):
        """Hide in-game menu and resume game (called from JavaScript)."""
        logger.info("Hide in-game menu called from JavaScript")
        # Navigate back to game (no UI overlay)
        self.manager.send_to_js("navigate", {"screen": "hidden"})

        # Re-enable game input
        if hasattr(self.app, 'enable_game_input'):
            self.app.enable_game_input()
        if hasattr(self.app, 'in_game_menu_active'):
            self.app.in_game_menu_active = False

    # ============================================================
    # WebViewer API
    # ============================================================

    def open_web_page(self, url: str, title: str = "Document"):
        """
        Open a web page in the in-game WebViewer.

        Args:
            url: URL to open (e.g., "https://www.dndbeyond.com/spells")
            title: Window title

        Usage:
            - DM command: /dm openweb https://www.dndbeyond.com/spells
            - Python: ui_manager.api.open_web_page("https://...", "Spells")
        """
        logger.info(f"Opening web page: {url}")
        self.manager.send_to_js("open_webview", {"url": url, "title": title})

    def close_web_page(self):
        """Close the WebViewer."""
        logger.info("Closing web page")
        self.manager.send_to_js("close_webview", {})

    def on_webviewer_opened(self, data: Dict[str, Any]):
        """Callback when WebViewer is opened (from JavaScript)."""
        url = data.get("url", "")
        title = data.get("title", "")
        logger.info(f"WebViewer opened: {title} - {url}")

    def on_webviewer_closed(self, data: Dict[str, Any]):
        """Callback when WebViewer is closed (from JavaScript)."""
        logger.info("WebViewer closed")

    # ============================================================
    # Python -> JavaScript events
    # ============================================================

    def _on_chat_message(self, data: Dict[str, Any]):
        """Forward chat message to JavaScript."""
        self.manager.send_to_js("chat_message", data)

    def _on_combat_started(self, data: Dict[str, Any]):
        """Forward combat started event to JavaScript."""
        self.manager.send_to_js("combat_started", data)

    def _on_combat_ended(self, data: Dict[str, Any]):
        """Forward combat ended event to JavaScript."""
        self.manager.send_to_js("combat_ended", data)

    def _on_world_state(self, data: Dict[str, Any]):
        """Forward world state to JavaScript."""
        self.manager.send_to_js("world_state", data)

    def _on_combat_turn_start(self, data: Dict[str, Any]):
        """Forward combat turn start to JavaScript."""
        self.manager.send_to_js("combat_turn_start", data)

    def _on_combat_action_result(self, data: Dict[str, Any]):
        """Forward combat action result to JavaScript."""
        self.manager.send_to_js("combat_action_result", data)

    def _on_combat_round_start(self, data: Dict[str, Any]):
        """Forward combat round start to JavaScript."""
        self.manager.send_to_js("combat_round_start", data)

    def _on_character_sheet(self, data: Dict[str, Any]):
        """Forward character sheet data to JavaScript."""
        self.manager.send_to_js("character_sheet", data)

    def _on_inventory_update(self, data: Dict[str, Any]):
        """Forward inventory update to JavaScript."""
        self.manager.send_to_js("inventory_update", data)

    def _on_equipment_update(self, data: Dict[str, Any]):
        """Forward equipment update to JavaScript."""
        self.manager.send_to_js("equipment_update", data)

    def _on_conditions_update(self, data: Dict[str, Any]):
        """Forward conditions update to JavaScript."""
        self.manager.send_to_js("conditions_update", data)

    def _on_game_state_changed(self, data: Dict[str, Any]):
        """Forward game state change to JavaScript."""
        from enum import Enum
        # Convert enum values to strings for JSON serialization
        safe_data = {}
        for k, v in data.items():
            safe_data[k] = v.name if isinstance(v, Enum) else v
        self.manager.send_to_js("game_state_changed", safe_data)

    def _on_spellcasting_update(self, data: Dict[str, Any]):
        """Forward spellcasting update to JavaScript."""
        self.manager.send_to_js("spellcasting_update", data)

    def _on_spell_cast_result(self, data: Dict[str, Any]):
        """Forward spell cast result to JavaScript."""
        self.manager.send_to_js("spell_cast_result", data)

    def _on_quest_list(self, data: Dict[str, Any]):
        """Forward quest list to JavaScript."""
        self.manager.send_to_js("quest_list", data)

    def _on_quest_accepted(self, data: Dict[str, Any]):
        """Forward quest accepted to JavaScript."""
        self.manager.send_to_js("quest_accepted", data)

    def _on_quest_completed(self, data: Dict[str, Any]):
        """Forward quest completed to JavaScript."""
        self.manager.send_to_js("quest_completed", data)

    def _on_quest_objective_progress(self, data: Dict[str, Any]):
        """Forward quest objective progress to JavaScript."""
        self.manager.send_to_js("quest_objective_progress", data)

    def _on_quest_ready_to_turn_in(self, data: Dict[str, Any]):
        """Forward quest ready to turn in to JavaScript."""
        self.manager.send_to_js("quest_ready_to_turn_in", data)

    def _on_show_rest_dialog(self, data: Dict[str, Any]):
        """Forward show rest dialog to JavaScript."""
        self.manager.send_to_js("show_rest_dialog", data)

    def _on_rest_result(self, data: Dict[str, Any]):
        """Forward rest result to JavaScript."""
        self.manager.send_to_js("rest_result", data)

    def _on_hit_die_result(self, data: Dict[str, Any]):
        """Forward hit die result to JavaScript."""
        self.manager.send_to_js("hit_die_result", data)

    def _on_open_character_sheet_tab(self, data: Dict[str, Any]):
        """Forward open character sheet tab to JavaScript."""
        self.manager.send_to_js("open_character_sheet_tab", data)

    # ============================================================
    # New JS -> Python methods
    # ============================================================

    def create_character(self, data: dict):
        """Create a character (called from JavaScript)."""
        logger.info(f"Create character from JavaScript: {data}")
        if "create_character" in self.callbacks:
            self.callbacks["create_character"](data)
        else:
            logger.warning("No create_character callback registered")

    def request_character_list(self):
        """Request character list from server (called from JavaScript)."""
        logger.info("Request character list from JavaScript")
        if hasattr(self.app, 'send_message'):
            self.app.send_message({"type": "character_list_request"})

    def combat_action(self, action: str, target: str = ""):
        """Execute combat action (called from JavaScript)."""
        logger.info(f"Combat action from JavaScript: {action} target={target}")
        self.app.event_manager.post("combat_player_action", {
            "action": action,
            "target": target,
        })

    def equip_item(self, data: dict):
        """Equip an item from inventory (called from JavaScript)."""
        slot = data.get("inventory_slot", 0) if isinstance(data, dict) else data
        logger.info(f"Equip item slot {slot} from JavaScript")
        self.app.event_manager.post("client_equip_item", {"inventory_slot": slot})

    def unequip_item(self, data: dict):
        """Unequip an item from equipment slot (called from JavaScript)."""
        slot = data.get("equipment_slot", "") if isinstance(data, dict) else data
        logger.info(f"Unequip item slot {slot} from JavaScript")
        self.app.event_manager.post("client_unequip_item", {"equipment_slot": slot})

    def cast_spell(self, data: dict):
        """Cast a spell (called from JavaScript)."""
        spell_id = data.get("spell_id", "")
        slot_level = data.get("slot_level", 0)
        logger.info(f"Cast spell {spell_id} at level {slot_level} from JavaScript")
        self.app.event_manager.post("cast_spell_request", {
            "spell_id": spell_id,
            "slot_level": slot_level,
        })

    def prepare_spell(self, data: dict):
        """Prepare a spell (called from JavaScript)."""
        spell_id = data.get("spell_id", "")
        logger.info(f"Prepare spell {spell_id} from JavaScript")
        self.app.event_manager.post("prepare_spell_request", {"spell_id": spell_id})

    def unprepare_spell(self, data: dict):
        """Unprepare a spell (called from JavaScript)."""
        spell_id = data.get("spell_id", "")
        logger.info(f"Unprepare spell {spell_id} from JavaScript")
        self.app.event_manager.post("unprepare_spell_request", {"spell_id": spell_id})

    def quest_list_request(self, data: dict):
        """Request quest list from server (called from JavaScript)."""
        filter_type = data.get("filter", "all") if isinstance(data, dict) else "all"
        logger.info(f"Quest list request: {filter_type} from JavaScript")
        self.app.event_manager.post("quest_list_request", {"filter": filter_type})

    def quest_abandon(self, data: dict):
        """Abandon a quest (called from JavaScript)."""
        quest_id = data.get("quest_id", "")
        logger.info(f"Quest abandon {quest_id} from JavaScript")
        self.app.event_manager.post("quest_abandon", {"quest_id": quest_id})

    def spend_hit_die(self, data: dict = None):
        """Spend a hit die during rest (called from JavaScript)."""
        count = data.get("count", 1) if isinstance(data, dict) else 1
        logger.info(f"Spend hit die (count={count}) from JavaScript")
        self.app.event_manager.post("spend_hit_die", {"count": count})

    def finish_rest(self, data: dict):
        """Finish a rest (called from JavaScript)."""
        rest_type = data.get("rest_type", "short") if isinstance(data, dict) else "short"
        logger.info(f"Finish rest ({rest_type}) from JavaScript")
        self.app.event_manager.post("rest_request", {"rest_type": rest_type})

    def update_description(self, data: dict):
        """Update character description field (called from JavaScript)."""
        field = data.get("field", "")
        value = data.get("value", "")
        logger.info(f"Update description field={field} from JavaScript")
        self.app.event_manager.post("client_update_description", {
            "field": field,
            "value": value,
        })

    def item_use(self, data: dict):
        """Use an inventory item (called from JavaScript)."""
        slot = data.get("slot", 0) if isinstance(data, dict) else data
        logger.info(f"Item use slot {slot} from JavaScript")
        if hasattr(self.app, 'send_item_use_packet'):
            self.app.send_item_use_packet({"slot": slot})

    def item_drop(self, data: dict):
        """Drop an inventory item (called from JavaScript)."""
        slot = data.get("slot", 0) if isinstance(data, dict) else data
        count = data.get("count", 1) if isinstance(data, dict) else 1
        logger.info(f"Item drop slot {slot} (count={count}) from JavaScript")
        if hasattr(self.app, 'send_message'):
            self.app.send_message({
                "type": "item_drop",
                "slot": slot,
                "count": count,
            })

    def interact_with(self, data: dict):
        """Execute an interaction from context menu click (called from JavaScript)."""
        entity_id = data.get("entity_id", "")
        action = data.get("action", "")
        logger.info(f"Interact with {entity_id[:8]} action={action} from JavaScript")
        self.app.event_manager.post("interact_request", {
            "entity_id": entity_id,
            "action": action,
        })

    # ============================================================
    # Context menu events (Python -> JavaScript)
    # ============================================================

    def _on_show_context_menu(self, data: Dict[str, Any]):
        """Forward show_context_menu event to JavaScript."""
        self.manager.send_to_js("show_context_menu", data)

    def _on_hide_context_menu(self, data: Dict[str, Any]):
        """Forward hide_context_menu event to JavaScript."""
        self.manager.send_to_js("hide_context_menu", data)
