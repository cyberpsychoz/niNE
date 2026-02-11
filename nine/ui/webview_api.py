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
