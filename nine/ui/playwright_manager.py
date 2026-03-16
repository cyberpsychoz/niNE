"""
Playwright UI Manager - Modern Chromium integration with Panda3D.

Uses Playwright for headless browser rendering to texture.
Works with any Python version (3.7+).
"""

import json
import logging
import subprocess
import threading
import time
import http.server
import socketserver
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional
from queue import Queue, Empty
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
        self.frame_lock = threading.Lock()
        # Pre-decoded raw RGBA bytes (decoded in browser thread, not main thread)
        self._raw_frame = None  # bytes
        self._raw_frame_w = 0
        self._raw_frame_h = 0

        # Dirty flag: only screenshot when something changed
        self._dirty = True
        self._last_activity_time = 0.0
        # Keep capturing for a short time after last activity
        _ACTIVITY_WINDOW = 2.0

        # HTTP server for web files
        self.http_server = None
        self.http_thread = None

        # Thread-safe settings lock
        self._config_lock = threading.Lock()

        # API for JavaScript calls
        from nine.ui.webview_api import WebViewAPI
        self.api = WebViewAPI(self, callbacks)

        # Path to web resources
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
        """Start local HTTP server for web files and game assets."""
        web_dir = self.web_dir
        # Assets root: nine/ directory (parent of ui/)
        assets_root = Path(__file__).parent.parent

        class DualHandler(http.server.SimpleHTTPRequestHandler):
            """Serves /assets/* from nine/assets/, everything else from nine/ui/web/."""

            def translate_path(self, path):
                parsed = urllib.parse.urlparse(path)
                clean_path = urllib.parse.unquote(parsed.path)

                if clean_path.startswith('/assets/'):
                    rel = clean_path[len('/assets/'):]
                    return str(assets_root / "assets" / rel)
                else:
                    rel = clean_path.lstrip('/')
                    return str(web_dir / rel)

            def log_message(self, format, *args):
                pass

        try:
            socketserver.TCPServer.allow_reuse_address = True
            self.http_server = socketserver.TCPServer(("127.0.0.1", HTTP_PORT), DualHandler)
            self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
            self.http_thread.start()
            logger.info(f"HTTP server started on port {HTTP_PORT} (web + assets)")
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

        # Add update task (only copies pre-decoded bytes to texture)
        self.app.taskMgr.add(self._update_texture, "playwright-update")

        # Setup input (event-based only, NO polling)
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
                        get_settings: () => { console.log('[pyapi] get_settings'); return pyCall('get_settings', {}); },
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

                # Render loop - decoupled command processing and screenshots
                last_frame_time = 0
                target_fps = 30
                frame_interval = 1.0 / target_fps
                frame_count = 0
                # Activity window: keep screenshotting for N seconds after last command
                activity_window = 2.0

                while self.running:
                    current_time = time.time()
                    had_commands = False

                    # Process ALL pending commands first (fast, non-blocking)
                    while True:
                        try:
                            cmd = self.to_browser_queue.get_nowait()
                            self._process_command(cmd)
                            had_commands = True
                        except Empty:
                            break

                    if had_commands:
                        self._dirty = True
                        self._last_activity_time = current_time

                    # Capture frame only when needed:
                    # - dirty flag set (recent commands)
                    # - within activity window after last command
                    # - at least once per second when idle (for animations/transitions)
                    should_capture = (
                        current_time - last_frame_time >= frame_interval
                        and (
                            self._dirty
                            or current_time - self._last_activity_time < activity_window
                            or current_time - last_frame_time >= 1.0
                        )
                    )

                    if should_capture:
                        try:
                            screenshot = self.page.screenshot(type='png', omit_background=True)

                            # Decode PNG in browser thread (NOT main thread)
                            img = Image.open(BytesIO(screenshot))
                            img = img.convert('RGBA')
                            img = img.transpose(Image.FLIP_TOP_BOTTOM)
                            raw_bytes = np.ascontiguousarray(
                                np.array(img, dtype=np.uint8)
                            ).tobytes()

                            with self.frame_lock:
                                self._raw_frame = raw_bytes

                            last_frame_time = current_time
                            self._dirty = False
                            frame_count += 1
                            if frame_count == 1:
                                logger.info(f"First screenshot captured ({len(screenshot)} bytes)")
                        except Exception as e:
                            logger.error(f"Screenshot error: {e}")

                    # Sleep less when active, more when idle
                    if current_time - self._last_activity_time < activity_window:
                        time.sleep(0.002)
                    else:
                        time.sleep(0.016)  # ~60hz poll when idle

        except Exception as e:
            logger.error(f"Browser loop error: {e}")
        finally:
            if self.browser:
                self.browser.close()
            logger.info("Browser loop ended")

    def _handle_js_call(self, method: str, args: dict):
        """Handle JavaScript -> Python calls (runs in browser thread).

        All callbacks that touch main-thread state are deferred to the
        main thread via taskMgr.doMethodLater to avoid race conditions.
        """
        logger.info(f"JS call received: {method}({args})")

        # get_settings is read-only and must return a value synchronously
        if method == 'get_settings':
            with self._config_lock:
                return dict(self.app.user_config)

        # All other methods are deferred to the main thread
        def _defer(task):
            self._dispatch_js_call(method, args)
            return task.done

        self.app.taskMgr.doMethodLater(0, _defer, f"js-call-{method}")

    def _dispatch_js_call(self, method: str, args: dict):
        """Dispatch JS call on the main thread (thread-safe)."""
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
        elif method == 'set_chat_active':
            self.api.set_chat_active(args.get('active', False))

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
                self.page.mouse.click(x, y)
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

        elif cmd_type == 'clipboard_paste':
            text = cmd.get('text', '')
            try:
                self.page.evaluate("""(text) => {
                    const el = document.activeElement;
                    if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
                        const start = el.selectionStart;
                        const end = el.selectionEnd;
                        const before = el.value.substring(0, start);
                        const after = el.value.substring(end);
                        el.value = before + text + after;
                        el.selectionStart = el.selectionEnd = start + text.length;
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                    } else if (el && el.isContentEditable) {
                        document.execCommand('insertText', false, text);
                    }
                }""", text)
            except Exception as e:
                logger.error(f"Clipboard paste error: {e}")

        elif cmd_type == 'clipboard_copy':
            try:
                selected = self.page.evaluate("""() => {
                    const el = document.activeElement;
                    if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
                        return el.value.substring(el.selectionStart, el.selectionEnd);
                    }
                    const sel = window.getSelection();
                    return sel ? sel.toString() : '';
                }""")
                if selected:
                    self._write_system_clipboard(selected)
            except Exception as e:
                logger.error(f"Clipboard copy error: {e}")

        elif cmd_type == 'clipboard_cut':
            try:
                selected = self.page.evaluate("""() => {
                    const el = document.activeElement;
                    if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
                        const text = el.value.substring(el.selectionStart, el.selectionEnd);
                        const start = el.selectionStart;
                        el.value = el.value.substring(0, start) + el.value.substring(el.selectionEnd);
                        el.selectionStart = el.selectionEnd = start;
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        return text;
                    }
                    const sel = window.getSelection();
                    const text = sel ? sel.toString() : '';
                    document.execCommand('delete');
                    return text;
                }""")
                if selected:
                    self._write_system_clipboard(selected)
            except Exception as e:
                logger.error(f"Clipboard cut error: {e}")

        elif cmd_type == 'select_all':
            try:
                self.page.evaluate("""() => {
                    const el = document.activeElement;
                    if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
                        el.select();
                    } else {
                        document.execCommand('selectAll');
                    }
                }""")
            except Exception as e:
                logger.error(f"Select all error: {e}")

        elif cmd_type == 'undo':
            try:
                self.page.evaluate("() => { document.execCommand('undo'); }")
            except Exception as e:
                logger.error(f"Undo error: {e}")

        elif cmd_type == 'shortcut':
            modifier = cmd.get('modifier', '')
            key = cmd.get('key', '')
            try:
                self.page.keyboard.press(f"{modifier}+{key}")
            except Exception as e:
                logger.error(f"Shortcut error: {e}")

    def _update_texture(self, task):
        """Update texture from pre-decoded frame buffer (main thread).

        Only copies raw bytes to the GPU texture - all decoding
        happens in the browser thread.
        """
        with self.frame_lock:
            raw = self._raw_frame
            if raw is not None:
                self._raw_frame = None

        if raw is not None:
            try:
                self.texture.setRamImage(raw)

                if not hasattr(self, '_logged_first_frame'):
                    logger.info("First frame rendered successfully")
                    self._logged_first_frame = True
            except Exception as e:
                logger.error(f"Texture update error: {e}")

        return Task.cont

    def _setup_input(self):
        """Setup input forwarding to browser (event-based only)."""
        logger.info("Setting up Playwright input handlers...")

        # Mouse click - event-based only (NO polling to avoid double clicks)
        self.app.accept("mouse1", self._on_click)
        self.app.accept("mouse1-up", self._on_click_up)

        # Mouse move tracking for debugging
        self.app.accept("mouse3", self._on_right_click)

        # Keyboard - text input
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
        self.to_browser_queue.put({'type': 'click', 'x': x, 'y': y})

    def _on_click_up(self):
        """Handle mouse release."""
        pass  # Playwright click includes release

    def _on_right_click(self):
        """Debug: Handle right click to verify input is working."""
        x, y = self._get_mouse_pos()
        logger.info(f"RIGHT CLICK detected at ({x}, {y}) - input system working")

    def _on_keystroke(self, keycode):
        """Handle text input. Filter control characters to avoid duplication
        with _on_special_key and _on_ctrl_key handlers."""
        if len(keycode) == 1 and ord(keycode) >= 32:
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

    def _read_system_clipboard(self):
        """Read text from system clipboard via xclip."""
        try:
            result = subprocess.run(
                ['xclip', '-selection', 'clipboard', '-o'],
                capture_output=True, text=True, timeout=1
            )
            if result.returncode == 0:
                return result.stdout
        except FileNotFoundError:
            try:
                result = subprocess.run(
                    ['xsel', '--clipboard', '--output'],
                    capture_output=True, text=True, timeout=1
                )
                if result.returncode == 0:
                    return result.stdout
            except FileNotFoundError:
                logger.warning("Neither xclip nor xsel found for clipboard access")
        except Exception as e:
            logger.error(f"Clipboard read error: {e}")
        return ''

    def _write_system_clipboard(self, text):
        """Write text to system clipboard via xclip."""
        try:
            proc = subprocess.Popen(
                ['xclip', '-selection', 'clipboard'],
                stdin=subprocess.PIPE
            )
            proc.communicate(input=text.encode('utf-8'), timeout=1)
        except FileNotFoundError:
            try:
                proc = subprocess.Popen(
                    ['xsel', '--clipboard', '--input'],
                    stdin=subprocess.PIPE
                )
                proc.communicate(input=text.encode('utf-8'), timeout=1)
            except FileNotFoundError:
                logger.warning("Neither xclip nor xsel found for clipboard access")
        except Exception as e:
            logger.error(f"Clipboard write error: {e}")

    def _on_ctrl_key(self, key):
        """Handle Ctrl+key combinations via DOM manipulation for clipboard."""
        if key == 'v':
            text = self._read_system_clipboard()
            if text:
                self.to_browser_queue.put({'type': 'clipboard_paste', 'text': text})
        elif key == 'c':
            self.to_browser_queue.put({'type': 'clipboard_copy'})
        elif key == 'x':
            self.to_browser_queue.put({'type': 'clipboard_cut'})
        elif key == 'a':
            self.to_browser_queue.put({'type': 'select_all'})
        elif key == 'z':
            self.to_browser_queue.put({'type': 'undo'})
        else:
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
        msg = {"type": event_type, "data": data}
        json_msg = json.dumps(msg)
        js_code = f"window.receiveFromPython({json_msg})"
        self.to_browser_queue.put({'type': 'evaluate', 'code': js_code})

    # UI methods
    def show_main_menu(self):
        # Scan for background images
        bg_dir = Path(__file__).parent.parent / "assets" / "materials" / "textures" / "backgrounds"
        backgrounds = []
        if bg_dir.exists():
            backgrounds = [
                f"/assets/materials/textures/backgrounds/{f.name}"
                for f in bg_dir.iterdir()
                if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')
            ]
        self.send_to_js("navigate", {
            "screen": "main-menu",
            "params": {"backgrounds": backgrounds}
        })
        logger.info(f"Showing main menu (backgrounds: {len(backgrounds)})")

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
        self.show_main_menu()

    def hide_login_menu(self):
        """Hide login menu and navigate back to main menu."""
        self.show_main_menu()
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
        with self._config_lock:
            settings = dict(self.app.user_config)
        self.send_to_js("navigate", {
            "screen": "settings-menu",
            "params": {"settings": settings}
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
        self.show_main_menu()

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
