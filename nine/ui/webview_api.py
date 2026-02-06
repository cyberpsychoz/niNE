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

        # Character events
        event_manager.subscribe("world_state_received", self._on_world_state)

        logger.info("Subscribed to game events")

    # ============================================================
    # JavaScript -> Python calls
    # ============================================================

    def exit_game(self):
        """Exit the game (called from JavaScript)."""
        logger.info("Exit game called from JavaScript")
        if "exit" in self.callbacks:
            # Schedule exit in main thread to avoid threading issues with Playwright
            def do_exit(task):
                self.callbacks["exit"]()
                return task.done
            self.app.taskMgr.doMethodLater(0.1, do_exit, "exit-game")
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
        Save settings (called from JavaScript).

        Args:
            settings: Dictionary of settings to save
        """
        logger.info(f"Saving settings from JavaScript: {settings}")

        # Update user_config
        self.app.user_config.update(settings)

        # Save to config.json
        try:
            import json
            with open("config.json", "w") as f:
                json.dump(self.app.user_config, f, indent=4)
            logger.info("Settings saved successfully")

            # Apply some settings immediately
            if "camera_sensitivity" in settings:
                self.app.camera_sensitivity = settings["camera_sensitivity"]
            if "invert_mouse_x" in settings:
                self.app.invert_mouse_x = settings["invert_mouse_x"]
            if "invert_mouse_y" in settings:
                self.app.invert_mouse_y = settings["invert_mouse_y"]
            if "fov" in settings:
                self.app.fov = settings["fov"]

        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def send_chat_message(self, message: str):
        """
        Send chat message (called from JavaScript).

        Args:
            message: Chat message text
        """
        logger.info(f"Chat message from JavaScript: {message}")
        # Отправляем событие для отправки на сервер
        self.app.event_manager.post("client_send_chat_message", {"message": message})

    def disconnect(self):
        """Disconnect from server (called from JavaScript)."""
        logger.info("Disconnect called from JavaScript")
        if hasattr(self.app, 'disconnect_from_server'):
            self.app.disconnect_from_server()
        else:
            logger.warning("No disconnect_from_server method found")

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
