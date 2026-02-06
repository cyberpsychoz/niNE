"""
Playwright UI Manager - Modern Chromium integration with Panda3D.

Uses Playwright for headless browser rendering to texture.
Works with any Python version (3.7+).
"""

import logging
import threading
import time
import http.server
import socketserver
from pathlib import Path
from typing import Any, Dict, Optional
from queue import Queue
from io import BytesIO

import numpy as np
from PIL import Image

from panda3d.core import (
    Texture, CardMaker, TransparencyAttrib, PNMImage, PTAUchar
)
from direct.task.Task import Task

# Use root logger to ensure logs go to client.log
logger = logging.getLogger("nine.ui.playwright")

# HTTP server port for serving web files
HTTP_PORT = 18599

# Playwright imports (lazy loaded)
playwright_module = None
Browser = None
Page = None


def _init_playwright():
    """Lazy init playwright to avoid import errors."""
    global playwright_module
    if playwright_module is None:
        try:
            from playwright.sync_api import sync_playwright
            playwright_module = sync_playwright
            logger.info("Playwright loaded successfully")
            return True
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return False
    return True


class PlaywrightUIManager:
    """Manages Playwright browser overlay for HTML/CSS/JS UI."""

    def __init__(self, app, callbacks: Dict[str, Any]):
        """
        Initialize Playwright UI Manager.

        Args:
            app: GameClient instance (has ShowBase)
            callbacks: Dictionary of callback functions from client
        """
        self.app = app
        self.callbacks = callbacks

        # Browser state
        self.playwright = None
        self.browser = None
        self.page = None
        self.browser_thread = None
        self.running = False

        # Texture
        self.texture = None
        self.card = None
        self.width = 1920
        self.height = 1080

        # Communication queues
        self.to_browser_queue = Queue()  # Commands to browser
        self.frame_buffer = None  # Latest frame bytes
        self.frame_lock = threading.Lock()

        # HTTP server for web files
        self.http_server = None
        self.http_thread = None

        # API для вызовов из JavaScript
        from nine.ui.webview_api import WebViewAPI
        self.api = WebViewAPI(self, callbacks)

        # Путь к web ресурсам
        self.web_dir = Path(__file__).parent / "web"

        # Compatibility with DirectGUI plugins
        self.base = app
        self.font = self._load_font()

        # Game state for plugin compatibility
        from nine.ui.manager import GameState
        self.game_state = GameState.MENU

        logger.info("PlaywrightUIManager initialized")

    def _load_font(self):
        """Load font for DirectGUI compatibility."""
        try:
            from nine.ui.theme import NineTheme
            font = self.app.loader.loadFont(NineTheme.FONT_PATH)
            if font:
                font.setPixelsPerUnit(NineTheme.FONT_PIXELS_PER_UNIT)
                return font
        except Exception as e:
            logger.warning(f"Could not load font: {e}")
        return None

    def _start_http_server(self):
        """Start local HTTP server for web files."""
        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(self.web_dir), **kwargs)

            def log_message(self, format, *args):
                pass  # Suppress logging

        # Create handler with correct directory
        web_dir = self.web_dir

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(web_dir), **kwargs)

            def log_message(self, format, *args):
                pass

        try:
            # Allow port reuse to avoid "Address already in use" errors
            socketserver.TCPServer.allow_reuse_address = True
            self.http_server = socketserver.TCPServer(("127.0.0.1", HTTP_PORT), Handler)
            self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
            self.http_thread.start()
            logger.info(f"HTTP server started on port {HTTP_PORT}")
            return True
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            return False

    def create_overlay(self):
        """Create browser overlay."""
        if not _init_playwright():
            logger.error("Cannot create overlay: Playwright not available")
            return

        # Get window size
        props = self.app.win.getProperties()
        self.width = props.getXSize()
        self.height = props.getYSize()

        # Start HTTP server for web files
        if not self._start_http_server():
            logger.error("Cannot create overlay: HTTP server failed")
            return

        # Create texture
        self._create_texture_card()

        # Start browser in background thread
        self.running = True
        self.browser_thread = threading.Thread(target=self._browser_loop, daemon=True)
        self.browser_thread.start()

        # Add update task
        self.app.taskMgr.add(self._update_texture, "playwright-update")

        # Add mouse polling task (backup for click detection)
        self._last_mouse_state = False
        self.app.taskMgr.add(self._poll_mouse, "playwright-mouse-poll")

        # Setup input
        self._setup_input()

        logger.info("Playwright overlay created")

    def _create_texture_card(self):
        """Create Panda3D texture and card."""
        self.texture = Texture("playwright_texture")
        self.texture.setup2dTexture(
            self.width, self.height,
            Texture.T_unsigned_byte, Texture.F_rgba
        )

        cm = CardMaker("playwright_card")
        cm.setFrame(-1, 1, -1, 1)

        self.card = self.app.render2d.attachNewNode(cm.generate())
        self.card.setTexture(self.texture)
        self.card.setTransparency(TransparencyAttrib.MAlpha)

        logger.info("Texture card created")

    def _browser_loop(self):
        """Background thread: run Playwright browser."""
        logger.info("Browser thread started")
        try:
            with playwright_module() as pw:
                self.playwright = pw
                logger.info("Launching Chromium...")
                self.browser = pw.chromium.launch(headless=True)
                logger.info("Creating page...")
                self.page = self.browser.new_page(viewport={'width': self.width, 'height': self.height})

                # Capture browser console logs
                self.page.on("console", lambda msg: logger.info(f"[Browser] {msg.text}"))

                # Expose Python API BEFORE loading page
                self.page.expose_function("pyCall", self._handle_js_call)
                logger.info("pyCall function exposed")

                # Inject pyapi bridge BEFORE page loads using add_init_script
                self.page.add_init_script("""
                    window.pyapi = {
                        exit_game: () => { console.log('[pyapi] exit_game'); return pyCall('exit_game', {}); },
                        open_login_menu: () => { console.log('[pyapi] open_login_menu'); return pyCall('open_login_menu', {}); },
                        attempt_login: (ip, name, pw) => { console.log('[pyapi] attempt_login'); return pyCall('attempt_login', {ip, name, password: pw}); },
                        close_login_menu: () => { console.log('[pyapi] close_login_menu'); return pyCall('close_login_menu', {}); },
                        open_settings: () => { console.log('[pyapi] open_settings'); return pyCall('open_settings', {}); },
                        save_settings: (s) => { console.log('[pyapi] save_settings'); return pyCall('save_settings', s); },
                        send_chat_message: (m) => { console.log('[pyapi] send_chat_message'); return pyCall('send_chat_message', {message: m}); },
                        disconnect: () => { console.log('[pyapi] disconnect'); return pyCall('disconnect', {}); },
                        hide_in_game_menu: () => { console.log('[pyapi] hide_in_game_menu'); return pyCall('hide_in_game_menu', {}); },
                    };
                    console.log('[Playwright] Python API bridge ready');
                """)
                logger.info("pyapi bridge script added")

                # Load HTML via HTTP (fetch API requires http://)
                url = f"http://127.0.0.1:{HTTP_PORT}/index.html"
                logger.info(f"Loading HTML: {url}")
                self.page.goto(url)
                self.page.wait_for_load_state('networkidle')
                logger.info("HTML loaded")

                logger.info("Browser started, entering render loop")

                # Render loop
                last_frame_time = 0
                target_fps = 30  # 30 FPS is enough for UI
                frame_interval = 1.0 / target_fps
                frame_count = 0

                while self.running:
                    current_time = time.time()

                    # Process commands from main thread
                    while not self.to_browser_queue.empty():
                        try:
                            cmd = self.to_browser_queue.get_nowait()
                            self._process_command(cmd)
                        except:
                            pass

                    # Capture frame at target FPS
                    if current_time - last_frame_time >= frame_interval:
                        try:
                            # omitBackground=True for transparent overlay
                            screenshot = self.page.screenshot(type='png', omit_background=True)
                            with self.frame_lock:
                                self.frame_buffer = screenshot
                            last_frame_time = current_time
                            frame_count += 1
                            if frame_count == 1:
                                logger.info(f"First screenshot captured ({len(screenshot)} bytes)")
                        except Exception as e:
                            logger.error(f"Screenshot error: {e}")

                    # Small sleep to prevent CPU spin
                    time.sleep(0.001)

        except Exception as e:
            logger.error(f"Browser loop error: {e}")
        finally:
            if self.browser:
                self.browser.close()
            logger.info("Browser loop ended")

    def _handle_js_call(self, method: str, args: dict):
        """Handle JavaScript -> Python calls."""
        logger.info(f"JS call received: {method}({args})")

        if method == 'exit_game':
            self.api.exit_game()
        elif method == 'open_login_menu':
            self.api.open_login_menu()
        elif method == 'attempt_login':
            self.api.attempt_login(args.get('ip', ''), args.get('name', ''), args.get('password', ''))
        elif method == 'close_login_menu':
            self.api.close_login_menu()
        elif method == 'open_settings':
            self.api.open_settings()
        elif method == 'save_settings':
            self.api.save_settings(args)
        elif method == 'send_chat_message':
            self.api.send_chat_message(args.get('message', ''))
        elif method == 'disconnect':
            self.api.disconnect()
        elif method == 'hide_in_game_menu':
            self.api.hide_in_game_menu()

    def _process_command(self, cmd: dict):
        """Process command in browser thread."""
        cmd_type = cmd.get('type')

        if cmd_type == 'evaluate':
            js_code = cmd.get('code', '')
            try:
                self.page.evaluate(js_code)
            except Exception as e:
                logger.error(f"JS evaluate error: {e}")

        elif cmd_type == 'click':
            x, y = cmd.get('x', 0), cmd.get('y', 0)
            try:
                logger.info(f"Processing browser click at ({x}, {y})")
                self.page.mouse.click(x, y)
                logger.info(f"Click sent to browser")
            except Exception as e:
                logger.error(f"Click error: {e}")

        elif cmd_type == 'type':
            text = cmd.get('text', '')
            try:
                self.page.keyboard.type(text)
            except Exception as e:
                logger.error(f"Type error: {e}")

        elif cmd_type == 'key':
            key = cmd.get('key', '')
            try:
                self.page.keyboard.press(key)
            except Exception as e:
                logger.error(f"Key error: {e}")

        elif cmd_type == 'shortcut':
            modifier = cmd.get('modifier', '')
            key = cmd.get('key', '')
            try:
                # Press modifier+key combination
                self.page.keyboard.press(f"{modifier}+{key}")
            except Exception as e:
                logger.error(f"Shortcut error: {e}")

    def _update_texture(self, task):
        """Update texture from frame buffer (main thread)."""
        with self.frame_lock:
            if self.frame_buffer is not None:
                try:
                    # Decode PNG with PIL (fast)
                    img = Image.open(BytesIO(self.frame_buffer))
                    img = img.convert('RGBA')

                    # Flip vertically for Panda3D
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)

                    # Get as numpy array
                    arr = np.array(img, dtype=np.uint8)
                    arr = np.ascontiguousarray(arr)

                    # Update texture
                    self.texture.setRamImage(arr.tobytes())

                    if not hasattr(self, '_logged_first_frame'):
                        logger.info("First frame rendered successfully")
                        self._logged_first_frame = True

                except Exception as e:
                    logger.error(f"Texture update error: {e}")

                self.frame_buffer = None

        return Task.cont

    def _setup_input(self):
        """Setup input forwarding to browser."""
        logger.info("Setting up Playwright input handlers...")

        # Mouse click - use direct method binding
        self.app.accept("mouse1", self._on_click)
        self.app.accept("mouse1-up", self._on_click_up)
        logger.info("Mouse handlers registered: mouse1, mouse1-up")

        # Mouse move tracking for debugging
        self.app.accept("mouse3", self._on_right_click)

        # Keyboard
        self.app.buttonThrowers[0].node().setKeystrokeEvent('playwright-keystroke')
        self.app.accept('playwright-keystroke', self._on_keystroke)

        # Special keys
        for key in ['enter', 'backspace', 'tab', 'escape', 'delete', 'home', 'end',
                    'arrow_up', 'arrow_down', 'arrow_left', 'arrow_right']:
            self.app.accept(key, self._on_special_key, [key])

        # Ctrl+key combinations for copy/paste
        for key in ['a', 'c', 'v', 'x', 'z']:
            self.app.accept(f'control-{key}', self._on_ctrl_key, [key])

        # Shift+arrow for text selection
        for key in ['arrow_up', 'arrow_down', 'arrow_left', 'arrow_right', 'home', 'end']:
            self.app.accept(f'shift-{key}', self._on_shift_key, [key])

        # Ctrl+Shift combinations
        for key in ['arrow_left', 'arrow_right', 'home', 'end']:
            self.app.accept(f'control-shift-{key}', self._on_ctrl_shift_key, [key])

        logger.info("All Playwright input handlers registered")

    def _get_mouse_pos(self):
        """Get mouse position in browser coordinates."""
        mwn = self.app.mouseWatcherNode
        if mwn.hasMouse():
            mx, my = mwn.getMouseX(), mwn.getMouseY()
            x = int((mx + 1.0) * 0.5 * self.width)
            y = int((1.0 - my) * 0.5 * self.height)
            return x, y
        return 0, 0

    def _on_click(self):
        """Handle mouse click."""
        x, y = self._get_mouse_pos()
        logger.info(f"Mouse click at screen pos ({x}, {y})")
        self.to_browser_queue.put({'type': 'click', 'x': x, 'y': y})

    def _on_click_up(self):
        """Handle mouse release."""
        pass  # Playwright click includes release

    def _on_right_click(self):
        """Debug: Handle right click to verify input is working."""
        x, y = self._get_mouse_pos()
        logger.info(f"RIGHT CLICK detected at ({x}, {y}) - input system working")

    def _poll_mouse(self, task):
        """Poll mouse state directly as backup click detection."""
        from direct.task.Task import Task

        # Check if mouse button is pressed via mouseWatcherNode
        mwn = self.app.mouseWatcherNode
        if mwn.isButtonDown('mouse1'):
            if not self._last_mouse_state:
                # Mouse just pressed
                self._last_mouse_state = True
                x, y = self._get_mouse_pos()
                logger.info(f"POLL: Mouse1 pressed at ({x}, {y})")
                self.to_browser_queue.put({'type': 'click', 'x': x, 'y': y})
        else:
            self._last_mouse_state = False

        return Task.cont

    def _on_keystroke(self, keycode):
        """Handle text input."""
        if len(keycode) == 1:
            self.to_browser_queue.put({'type': 'type', 'text': keycode})

    def _on_special_key(self, key):
        """Handle special keys."""
        key_map = {
            'enter': 'Enter',
            'backspace': 'Backspace',
            'tab': 'Tab',
            'escape': 'Escape',
            'delete': 'Delete',
            'home': 'Home',
            'end': 'End',
            'arrow_up': 'ArrowUp',
            'arrow_down': 'ArrowDown',
            'arrow_left': 'ArrowLeft',
            'arrow_right': 'ArrowRight',
        }
        pw_key = key_map.get(key, key)
        self.to_browser_queue.put({'type': 'key', 'key': pw_key})

    def _on_ctrl_key(self, key):
        """Handle Ctrl+key combinations (copy/paste/etc)."""
        # Send as keyboard shortcut
        self.to_browser_queue.put({'type': 'shortcut', 'modifier': 'Control', 'key': key})

    def _on_shift_key(self, key):
        """Handle Shift+key combinations (text selection)."""
        key_map = {
            'arrow_up': 'ArrowUp',
            'arrow_down': 'ArrowDown',
            'arrow_left': 'ArrowLeft',
            'arrow_right': 'ArrowRight',
            'home': 'Home',
            'end': 'End',
        }
        pw_key = key_map.get(key, key)
        self.to_browser_queue.put({'type': 'shortcut', 'modifier': 'Shift', 'key': pw_key})

    def _on_ctrl_shift_key(self, key):
        """Handle Ctrl+Shift+key combinations (word selection)."""
        key_map = {
            'arrow_left': 'ArrowLeft',
            'arrow_right': 'ArrowRight',
            'home': 'Home',
            'end': 'End',
        }
        pw_key = key_map.get(key, key)
        self.to_browser_queue.put({'type': 'shortcut', 'modifier': 'Control+Shift', 'key': pw_key})

    def send_to_js(self, event_type: str, data: Any = None):
        """Send message to JavaScript."""
        import json
        msg = {"type": event_type, "data": data}
        json_msg = json.dumps(msg)
        js_code = f"window.receiveFromPython({json_msg})"
        self.to_browser_queue.put({'type': 'evaluate', 'code': js_code})

    # UI methods
    def show_main_menu(self):
        self.send_to_js("navigate", {"screen": "main-menu"})
        logger.info("Showing main menu")

    def show_login_menu(self, default_ip: str = "127.0.0.1", default_name: str = None):
        """Show login menu with optional default values."""
        name = default_name or self.app.user_config.get("nickname", "Player")
        self.send_to_js("navigate", {
            "screen": "login-menu",
            "params": {
                "ip": default_ip,
                "name": name
            }
        })
        logger.info("Showing login menu")

    def close_login_menu(self):
        self.send_to_js("navigate", {"screen": "main-menu"})

    def hide_login_menu(self):
        """Hide login menu and navigate back to main menu."""
        self.send_to_js("navigate", {"screen": "main-menu"})
        logger.info("Hiding login menu")

    def get_login_credentials(self) -> dict:
        """
        Return login credentials stored by the API.

        Called by client.attempt_login() to get credentials
        that were passed from JavaScript.
        """
        return self.api.get_login_credentials()

    def show_settings_menu(self, client=None):
        """Show settings menu. client argument for DirectGUI compatibility."""
        self.send_to_js("navigate", {
            "screen": "settings-menu",
            "params": {"settings": self.app.user_config}
        })

    def show_loading_screen(self, text: str = "Loading..."):
        self.send_to_js("navigate", {"screen": "loading-screen"})
        self.send_to_js("loading_text", {"text": text})

    def update_loading_progress(self, progress: float, text: str = None):
        data = {"progress": progress}
        if text:
            data["text"] = text
        self.send_to_js("loading_progress", data)

    def hide_loading_screen(self):
        self.send_to_js("navigate", {"screen": "main-menu"})

    def show_in_game_menu(self):
        self.send_to_js("navigate", {"screen": "in-game-menu"})

    def hide_in_game_menu(self):
        self.send_to_js("navigate", {"screen": "hidden"})

    def destroy(self):
        """Clean up resources."""
        self.running = False

        if self.browser_thread:
            self.browser_thread.join(timeout=2.0)

        if self.http_server:
            self.http_server.shutdown()

        if self.card:
            self.card.removeNode()

        # Remove input handlers
        self.app.ignore("mouse1")
        self.app.ignore("mouse1-up")
        self.app.ignore("mouse3")
        self.app.ignore("playwright-keystroke")

        # Remove special key handlers
        for key in ['enter', 'backspace', 'tab', 'escape', 'delete', 'home', 'end',
                    'arrow_up', 'arrow_down', 'arrow_left', 'arrow_right']:
            self.app.ignore(key)

        # Remove Ctrl+key handlers
        for key in ['a', 'c', 'v', 'x', 'z']:
            self.app.ignore(f'control-{key}')

        # Remove Shift+key handlers
        for key in ['arrow_up', 'arrow_down', 'arrow_left', 'arrow_right', 'home', 'end']:
            self.app.ignore(f'shift-{key}')

        # Remove Ctrl+Shift handlers
        for key in ['arrow_left', 'arrow_right', 'home', 'end']:
            self.app.ignore(f'control-shift-{key}')

        logger.info("PlaywrightUIManager destroyed")
