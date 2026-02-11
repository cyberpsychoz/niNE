"""
CEF UI Manager - Chromium Embedded Framework integration with Panda3D.

Uses cef-capi-py for direct CEF C API access. Provides raw BGRA pixel
rendering via OnPaint (no PNG encode/decode), native input handling,
and native clipboard support.

Requires: pip install cef-capi-py (Python 3.11+)
"""

import ctypes
import json
import logging
import threading
import http.server
import socketserver
import urllib.parse
from pathlib import Path
from typing import Any, Dict

import numpy as np

from panda3d.core import Texture, CardMaker, TransparencyAttrib
from direct.task.Task import Task
from direct.showbase.DirectObject import DirectObject

logger = logging.getLogger("nine.ui.cef")

HTTP_PORT = 18599

# JS→Python bridge: injected via execute_java_script after page load.
# Uses console.log with __PYCALL__ prefix intercepted by display_handler.
# For get_settings (needs return value), Python responds via execute_java_script.
PYAPI_INJECT_JS = """
(function() {
    if (window.__pyapi_ready) return;
    window.__pyapi_ready = true;

    function pyCall(method, args) {
        console.log('__PYCALL__:' + method + ':' + JSON.stringify(args || {}));
    }

    window.pyapi = {
        exit_game: function() { pyCall('exit_game', {}); },
        open_login_menu: function() { pyCall('open_login_menu', {}); },
        attempt_login: function(ip, name, pw) {
            pyCall('attempt_login', {ip: ip, name: name, password: pw});
        },
        close_login_menu: function() { pyCall('close_login_menu', {}); },
        open_settings: function() { pyCall('open_settings', {}); },
        save_settings: function(s) { pyCall('save_settings', s); },
        send_chat_message: function(m) { pyCall('send_chat_message', {message: m}); },
        set_chat_active: function(data) { pyCall('set_chat_active', data); },
        select_character: function(uuid) { pyCall('select_character', {character_uuid: uuid}); },
        disconnect: function() { pyCall('disconnect', {}); },
        hide_in_game_menu: function() { pyCall('hide_in_game_menu', {}); },
        create_character: function(data) { pyCall('create_character', data); },
        request_character_list: function() { pyCall('request_character_list', {}); },
        combat_action: function(action, target) { pyCall('combat_action', {action: action, target: target || ''}); },
        get_settings: function() {
            pyCall('get_settings', {});
            return window.__pyapi_settings || {};
        },
    };
    console.log('[CEF] pyapi bridge injected');
})();
"""


class CEFUIManager:
    """Manages CEF browser overlay for HTML/CSS/JS UI via cef-capi-py."""

    def __init__(self, app, callbacks: Dict[str, Any]):
        self.app = app
        self.callbacks = callbacks
        self.base = app  # DirectGUI compatibility

        self.width = 1920
        self.height = 1080

        # CEF objects
        self._cef_app = None
        self._client = None
        self._browser = None       # cef_browser_t instance
        self._browser_host = None  # POINTER(cef_browser_host_t)

        # Texture
        self.texture = None
        self.card = None

        # Frame buffer (raw BGRA pixels from OnPaint)
        self._frame_buffer = None
        self._frame_lock = threading.Lock()
        self._config_lock = threading.Lock()

        # HTTP server
        self.http_server = None
        self.http_thread = None

        # Input handler (separate DirectObject to avoid conflicts with game)
        self._input = DirectObject()
        self._input_paused = False

        # Page loaded flag
        self._page_loaded = False
        self._js_queue = []  # JS calls queued before page loads

        # API for JavaScript calls
        from nine.ui.webview_api import WebViewAPI
        self.api = WebViewAPI(self, callbacks)

        # Path to web resources
        self.web_dir = Path(__file__).parent / "web"

        # Font for DirectGUI compatibility
        self.font = self._load_font()

        # Game state
        from nine.core.game_state import GameState
        self.game_state = GameState.MENU

        logger.info("CEFUIManager initialized")

    def _load_font(self):
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
        web_dir = self.web_dir
        assets_root = Path(__file__).parent.parent

        class DualHandler(http.server.SimpleHTTPRequestHandler):
            def translate_path(self, path):
                parsed = urllib.parse.urlparse(path)
                clean_path = urllib.parse.unquote(parsed.path)
                if clean_path.startswith('/assets/'):
                    rel = clean_path[len('/assets/'):]
                    return str(assets_root / "assets" / rel)
                else:
                    rel = clean_path.lstrip('/')
                    return str(web_dir / rel)

            def end_headers(self):
                # Disable caching so JS/CSS changes take effect immediately
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                super().end_headers()

            def log_message(self, format, *args):
                pass

        try:
            socketserver.TCPServer.allow_reuse_address = True
            self.http_server = socketserver.TCPServer(
                ("127.0.0.1", HTTP_PORT), DualHandler
            )
            self.http_thread = threading.Thread(
                target=self.http_server.serve_forever, daemon=True
            )
            self.http_thread.start()
            logger.info(f"HTTP server started on port {HTTP_PORT}")
            return True
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            return False

    def create_overlay(self):
        """Create CEF browser overlay."""
        try:
            from cef_capi import (
                base_ctor, size_ctor, handler, cef_string_ctor,
                decode_cef_string, struct, header
            )
            from cef_capi.app_client import settings_main_args_ctor, app_ctor
        except ImportError:
            logger.error(
                "cef-capi-py not installed. Run: pip install cef-capi-py"
            )
            return

        # Store imports for use in other methods
        self._cef = {
            'base_ctor': base_ctor,
            'size_ctor': size_ctor,
            'handler': handler,
            'cef_string_ctor': cef_string_ctor,
            'decode_cef_string': decode_cef_string,
            'struct': struct,
            'header': header,
        }

        # Get window size
        props = self.app.win.getProperties()
        self.width = props.getXSize()
        self.height = props.getYSize()

        # Start HTTP server
        if not self._start_http_server():
            logger.error("Cannot create overlay: HTTP server failed")
            return

        # Create Panda3D texture and card
        self._create_texture_card()

        # Initialize CEF
        self._init_cef(settings_main_args_ctor, app_ctor)

        logger.info("CEF overlay created")

    def _create_texture_card(self):
        self.texture = Texture("cef_texture")
        self.texture.setup2dTexture(
            self.width, self.height,
            Texture.T_unsigned_byte, Texture.F_rgba
        )

        cm = CardMaker("cef_card")
        cm.setFrame(-1, 1, -1, 1)

        self.card = self.app.render2d.attachNewNode(cm.generate())
        self.card.setTexture(self.texture)
        self.card.setTransparency(TransparencyAttrib.MAlpha)

        logger.info("Texture card created")

    def _init_cef(self, settings_main_args_ctor, app_ctor):
        base_ctor = self._cef['base_ctor']
        size_ctor = self._cef['size_ctor']
        handler_deco = self._cef['handler']
        cef_string_ctor = self._cef['cef_string_ctor']
        decode_cef_string = self._cef['decode_cef_string']
        struct = self._cef['struct']
        header = self._cef['header']

        # No single_process — it crashes with real HTTP pages.
        # JS→Python bridge uses console.log interception instead of V8 extensions.
        self._cef_app = app_ctor(disable_gpu=True, single_process=False)

        # Create settings
        settings, main_args = settings_main_args_ctor()
        settings.windowless_rendering_enabled = 1
        settings.no_sandbox = 1
        settings.log_severity = struct.LOGSEVERITY_WARNING

        # Initialize CEF
        result = header.cef_initialize(main_args, settings, self._cef_app, None)
        if not result:
            logger.error("cef_initialize failed")
            return
        logger.info("CEF initialized")

        # Create client with handlers
        self._client = base_ctor(struct.cef_client_t)
        cef_mgr = self  # closure reference

        # --- Render Handler ---
        @handler_deco(self._client)
        def get_render_handler(*_):
            rh = base_ctor(struct.cef_render_handler_t)

            @handler_deco(rh)
            def get_view_rect(browser, rect):
                rect.x = 0
                rect.y = 0
                rect.width = cef_mgr.width
                rect.height = cef_mgr.height
                return 1

            @handler_deco(rh)
            def on_paint(browser, element_type, dirty_rects_count,
                         dirty_rects, buffer, width, height):
                if element_type == header.PET_VIEW:
                    try:
                        size = width * height * 4
                        raw = ctypes.string_at(buffer, size)
                        # BGRA -> RGBA: swap B and R channels
                        arr = np.frombuffer(raw, dtype=np.uint8).copy()
                        arr = arr.reshape(-1, 4)
                        arr[:, [0, 2]] = arr[:, [2, 0]]
                        # Flip vertically for Panda3D (bottom-up)
                        arr = arr.reshape(height, width, 4)
                        arr = arr[::-1]
                        with cef_mgr._frame_lock:
                            cef_mgr._frame_buffer = arr.tobytes()
                    except Exception as e:
                        logger.error(f"OnPaint error: {e}")

            return rh

        # --- Display Handler (JS→Python via console.log interception) ---
        @handler_deco(self._client)
        def get_display_handler(*_):
            dh = base_ctor(struct.cef_display_handler_t)

            @handler_deco(dh)
            def on_console_message(browser, level, message, source, line):
                try:
                    msg = decode_cef_string(message)
                    if msg.startswith('__PYCALL__:'):
                        # Format: __PYCALL__:method:json_args
                        parts = msg.split(':', 2)
                        if len(parts) >= 3:
                            method = parts[1]
                            try:
                                args = json.loads(parts[2])
                            except json.JSONDecodeError:
                                args = {}
                            cef_mgr._handle_js_call(method, args)
                        return 1  # suppress from console
                    else:
                        # Forward JS console output to Python logger
                        logger.info(f"[JS] {msg}")
                except Exception as e:
                    logger.error(f"Console handler error: {e}")
                return 0  # pass through to console

            return dh

        # --- Load Handler ---
        @handler_deco(self._client)
        def get_load_handler(*_):
            lh = base_ctor(struct.cef_load_handler_t)

            @handler_deco(lh)
            def on_loading_state_change(browser, is_loading,
                                        can_go_back, can_go_forward):
                if not is_loading:
                    logger.info("Page loaded")
                    first_load = not cef_mgr._page_loaded
                    cef_mgr._page_loaded = True
                    # Inject pyapi bridge (always, in case of navigation)
                    cef_mgr._inject_pyapi()
                    # Force repaint
                    if cef_mgr._browser_host:
                        cef_mgr._browser_host.contents.was_resized(
                            cef_mgr._browser_host
                        )

            return lh

        # --- Life Span Handler ---
        @handler_deco(self._client)
        def get_life_span_handler(*_):
            lsh = base_ctor(struct.cef_life_span_handler_t)

            @handler_deco(lsh)
            def on_after_created(browser):
                logger.info("Browser created")
                cef_mgr._browser = browser
                browser_host_ptr = browser.get_host(
                    ctypes.pointer(browser)
                )
                if browser_host_ptr:
                    cef_mgr._browser_host = ctypes.cast(
                        browser_host_ptr,
                        ctypes.POINTER(struct.cef_browser_host_t)
                    )
                    # Focus the browser
                    cef_mgr._browser_host.contents.set_focus(
                        cef_mgr._browser_host, 1
                    )
                    logger.info("Browser host acquired")

            @handler_deco(lsh)
            def on_before_close(browser):
                logger.info("Browser closing")

            return lsh

        # Create offscreen browser
        window_info = struct.cef_window_info_t()
        window_info.windowless_rendering_enabled = 1

        browser_settings = size_ctor(struct.cef_browser_settings_t)

        url = f"http://127.0.0.1:{HTTP_PORT}/index.html"

        header.cef_browser_host_create_browser(
            window_info,
            self._client,
            cef_string_ctor(url),
            browser_settings,
            None,
            None
        )
        logger.info(f"Browser creation requested: {url}")

        # Register Panda3D tasks
        self.app.taskMgr.add(self._cef_loop, "cef-loop", sort=-100)
        self.app.taskMgr.add(self._update_texture, "cef-texture")
        self.app.taskMgr.add(self._mouse_move, "cef-mouse-move")

        # Setup input handlers
        self._setup_input()

    def _inject_pyapi(self):
        """Inject pyapi JS bridge after page loads, then replay queued calls."""
        self._exec_js(PYAPI_INJECT_JS, allow_queue=False)
        # Push current settings so get_settings works immediately
        with self._config_lock:
            settings = dict(self.app.user_config)
        self._exec_js(
            f"window.__pyapi_settings = {json.dumps(settings)};",
            allow_queue=False
        )
        # Replay any JS calls that were queued before page loaded
        if self._js_queue:
            logger.info(f"Replaying {len(self._js_queue)} queued JS calls")
            for js_code in self._js_queue:
                self._exec_js(js_code, allow_queue=False)
            self._js_queue.clear()

    def _exec_js(self, js_code, allow_queue=True):
        """Execute JavaScript in the browser. Queues if page not loaded yet."""
        if self._browser is None:
            if allow_queue and not self._page_loaded:
                self._js_queue.append(js_code)
            return

        struct = self._cef['struct']
        cef_string_ctor = self._cef['cef_string_ctor']

        try:
            browser_ptr = ctypes.pointer(self._browser)
            frame_ptr = self._browser.get_main_frame(browser_ptr)
            if not frame_ptr:
                if allow_queue and not self._page_loaded:
                    self._js_queue.append(js_code)
                return

            frame = ctypes.cast(
                frame_ptr, ctypes.POINTER(struct.cef_frame_t)
            )
            frame.contents.execute_java_script(
                frame,
                cef_string_ctor(js_code),
                cef_string_ctor(""),
                0
            )
        except Exception as e:
            logger.error(f"_exec_js error: {e}")

    def _handle_js_call(self, method: str, args: dict):
        """Handle JavaScript -> Python calls (from console.log interception)."""
        logger.info(f"JS call: {method}({args})")

        # get_settings: push settings back to JS
        if method == 'get_settings':
            with self._config_lock:
                settings = dict(self.app.user_config)
            self._exec_js(
                f"window.__pyapi_settings = {json.dumps(settings)};"
            )
            return

        # All other methods deferred to main thread
        def _defer(task):
            self._dispatch_js_call(method, args)
            return task.done

        self.app.taskMgr.doMethodLater(0, _defer, f"js-call-{method}")

    def _dispatch_js_call(self, method: str, args: dict):
        if method == 'exit_game':
            self.api.exit_game()
        elif method == 'open_login_menu':
            self.api.open_login_menu()
        elif method == 'attempt_login':
            self.api.attempt_login(
                args.get('ip', ''),
                args.get('name', ''),
                args.get('password', '')
            )
        elif method == 'close_login_menu':
            self.api.close_login_menu()
        elif method == 'open_settings':
            self.api.open_settings()
        elif method == 'save_settings':
            self.api.save_settings(args)
        elif method == 'send_chat_message':
            self.api.send_chat_message(args.get('message', ''))
        elif method == 'select_character':
            self.api.select_character(args.get('character_uuid', ''))
        elif method == 'disconnect':
            self.api.disconnect()
        elif method == 'hide_in_game_menu':
            self.api.hide_in_game_menu()
        elif method == 'create_character':
            self.api.create_character(args)
        elif method == 'request_character_list':
            self.api.request_character_list()
        elif method == 'combat_action':
            self.api.combat_action(args.get('action', ''), args.get('target', ''))
        elif method == 'set_chat_active':
            self.api.set_chat_active(args.get('active', False))

    # ================================================================
    # Tasks
    # ================================================================

    def _cef_loop(self, task):
        """Pump CEF message loop each frame."""
        self._cef['header'].cef_do_message_loop_work()
        return Task.cont

    def _update_texture(self, task):
        """Copy raw frame buffer to GPU texture."""
        with self._frame_lock:
            buf = self._frame_buffer
            self._frame_buffer = None

        if buf is not None:
            try:
                self.texture.setRamImage(buf)
                if not hasattr(self, '_logged_first_frame'):
                    logger.info("First frame rendered")
                    self._logged_first_frame = True
            except Exception as e:
                logger.error(f"Texture update error: {e}")

        return Task.cont

    # ================================================================
    # Input
    # ================================================================

    def _setup_input(self):
        logger.info("Setting up CEF input handlers...")

        self._input.accept("mouse1", self._on_click)
        self._input.accept("mouse1-up", self._on_click_up)
        self._input.accept("mouse3", self._on_right_click)
        self._input.accept("wheel_up", self._on_wheel_up)
        self._input.accept("wheel_down", self._on_wheel_down)

        self.app.buttonThrowers[0].node().setKeystrokeEvent('cef-keystroke')
        self._input.accept('cef-keystroke', self._on_keystroke)

        for key in ['enter', 'backspace', 'tab', 'escape', 'delete',
                     'home', 'end', 'arrow_up', 'arrow_down',
                     'arrow_left', 'arrow_right']:
            self._input.accept(key, self._on_special_key, [key])

        for key in ['a', 'c', 'v', 'x', 'z']:
            self._input.accept(f'control-{key}', self._on_ctrl_key, [key])

        for key in ['arrow_up', 'arrow_down', 'arrow_left', 'arrow_right',
                     'home', 'end']:
            self._input.accept(f'shift-{key}', self._on_shift_key, [key])

        for key in ['arrow_left', 'arrow_right', 'home', 'end']:
            self._input.accept(f'control-shift-{key}', self._on_ctrl_shift_key, [key])

        logger.info("CEF input handlers registered")

    def _get_mouse_pos(self):
        mwn = self.app.mouseWatcherNode
        if mwn.hasMouse():
            mx, my = mwn.getMouseX(), mwn.getMouseY()
            x = int((mx + 1.0) * 0.5 * self.width)
            y = int((1.0 - my) * 0.5 * self.height)
            return x, y
        return 0, 0

    def _make_mouse_event(self, modifiers=0):
        struct = self._cef['struct']
        x, y = self._get_mouse_pos()
        me = struct.cef_mouse_event_t()
        me.x = x
        me.y = y
        me.modifiers = modifiers
        return me

    def _on_click(self):
        if self._browser_host is None or self._input_paused:
            return
        me = self._make_mouse_event()
        self._browser_host.contents.send_mouse_click_event(
            self._browser_host, ctypes.byref(me),
            self._cef['header'].MBT_LEFT, 0, 1
        )

    def _on_click_up(self):
        if self._browser_host is None or self._input_paused:
            return
        me = self._make_mouse_event()
        self._browser_host.contents.send_mouse_click_event(
            self._browser_host, ctypes.byref(me),
            self._cef['header'].MBT_LEFT, 1, 1
        )

    def _on_right_click(self):
        x, y = self._get_mouse_pos()
        logger.info(f"RIGHT CLICK at ({x}, {y})")

    def _on_wheel_up(self):
        if self._browser_host is None or self._input_paused:
            return
        me = self._make_mouse_event()
        self._browser_host.contents.send_mouse_wheel_event(
            self._browser_host, ctypes.byref(me), 0, 120
        )

    def _on_wheel_down(self):
        if self._browser_host is None or self._input_paused:
            return
        me = self._make_mouse_event()
        self._browser_host.contents.send_mouse_wheel_event(
            self._browser_host, ctypes.byref(me), 0, -120
        )

    def _mouse_move(self, task):
        if self._browser_host is None or self._input_paused:
            return Task.cont
        me = self._make_mouse_event()
        self._browser_host.contents.send_mouse_move_event(
            self._browser_host, ctypes.byref(me), 0
        )
        return Task.cont

    def _send_key(self, vk, char=0, modifiers=0, send_char=False):
        """Send a key event to CEF."""
        if self._browser_host is None or self._input_paused:
            return
        struct = self._cef['struct']
        header = self._cef['header']

        ke = struct.cef_key_event_t()
        ke.windows_key_code = vk
        ke.native_key_code = 0
        ke.is_system_key = 0
        ke.character = char
        ke.unmodified_character = char
        ke.modifiers = modifiers
        ke.focus_on_editable_field = 1

        events = [header.KEYEVENT_RAWKEYDOWN]
        if send_char:
            events.append(header.KEYEVENT_CHAR)
        events.append(header.KEYEVENT_KEYUP)

        for event_type in events:
            ke.type = event_type
            self._browser_host.contents.send_key_event(
                self._browser_host, ctypes.byref(ke)
            )

    def _on_keystroke(self, keycode):
        if self._input_paused:
            return
        if len(keycode) != 1 or ord(keycode) < 32:
            return
        char = ord(keycode)
        # Windows VK codes for letters are uppercase ASCII (VK_A=0x41 .. VK_Z=0x5A)
        vk = ord(keycode.upper()) if keycode.isalpha() else char
        self._send_key(vk, char, 0, send_char=True)

    _VK_MAP = {
        'enter': 0x0D, 'backspace': 0x08, 'tab': 0x09,
        'escape': 0x1B, 'delete': 0x2E, 'home': 0x24, 'end': 0x23,
        'arrow_up': 0x26, 'arrow_down': 0x28,
        'arrow_left': 0x25, 'arrow_right': 0x27,
    }

    def _on_special_key(self, key):
        vk = self._VK_MAP.get(key)
        if vk is not None:
            self._send_key(vk)

    def _on_ctrl_key(self, key):
        self._send_key(
            ord(key.upper()), ord(key),
            self._cef['header'].EVENTFLAG_CONTROL_DOWN
        )

    def _on_shift_key(self, key):
        vk = self._VK_MAP.get(key)
        if vk is not None:
            self._send_key(vk, 0, self._cef['header'].EVENTFLAG_SHIFT_DOWN)

    def _on_ctrl_shift_key(self, key):
        vk = self._VK_MAP.get(key)
        if vk is not None:
            header = self._cef['header']
            self._send_key(
                vk, 0,
                header.EVENTFLAG_CONTROL_DOWN | header.EVENTFLAG_SHIFT_DOWN
            )

    # ================================================================
    # Input Pause/Resume
    # ================================================================

    def pause_input(self):
        """Pause CEF input (let DirectGUI handle input)."""
        self._input_paused = True

    def resume_input(self):
        """Resume CEF input."""
        self._input_paused = False

    # ================================================================
    # Python -> JavaScript
    # ================================================================

    def send_to_js(self, event_type: str, data=None):
        """Send message to JavaScript via execute_java_script."""
        msg = json.dumps({"type": event_type, "data": data})
        js = f"if(window.receiveFromPython){{window.receiveFromPython({msg})}}"
        self._exec_js(js)

    # ================================================================
    # UI Methods (identical interface to PlaywrightUIManager)
    # ================================================================

    def show_main_menu(self):
        bg_dir = (Path(__file__).parent.parent
                  / "assets" / "materials" / "textures" / "backgrounds")
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
        from nine.core.game_state import GameState
        self.set_game_state(GameState.MENU)
        logger.info(f"Showing main menu (backgrounds: {len(backgrounds)})")

    def show_login_menu(self, default_ip="127.0.0.1", default_name=None):
        name = default_name or self.app.user_config.get("nickname", "Player")
        self.send_to_js("navigate", {
            "screen": "login-menu",
            "params": {"ip": default_ip, "name": name}
        })
        logger.info("Showing login menu")

    def close_login_menu(self):
        self.show_main_menu()

    def hide_login_menu(self):
        # Don't navigate — caller (attempt_login) will show loading screen next
        logger.info("Hiding login menu")

    def get_login_credentials(self):
        return self.api.get_login_credentials()

    def show_settings_menu(self, client=None):
        with self._config_lock:
            settings = dict(self.app.user_config)
        self.send_to_js("navigate", {
            "screen": "settings-menu",
            "params": {"settings": settings}
        })

    def show_loading_screen(self, text="Loading..."):
        self.send_to_js("navigate", {"screen": "loading-screen"})
        self.send_to_js("loading_text", {"text": text})

    def update_loading_progress(self, progress, text=None):
        data = {"progress": progress}
        if text:
            data["text"] = text
        self.send_to_js("loading_progress", data)

    def hide_loading_screen(self):
        self.send_to_js("navigate", {"screen": "hidden"})

    def show_in_game_menu(self, client=None):
        self.send_to_js("navigate", {"screen": "in-game-menu"})

    def hide_in_game_menu(self):
        self.send_to_js("navigate", {"screen": "hidden"})

    def show_character_select(self, characters_data, max_characters=2, client=None):
        logger.info(f"show_character_select: {len(characters_data)} chars, max={max_characters}")
        for i, c in enumerate(characters_data):
            logger.info(f"  char[{i}]: uuid={c.get('uuid','?')}, name={c.get('character_name','?')}")
        self.send_to_js("navigate", {
            "screen": "character-select",
            "params": {
                "characters": characters_data,
                "max_characters": max_characters,
            }
        })
        from nine.core.game_state import GameState
        self.set_game_state(GameState.CHARACTER_SELECT)

    def hide_character_create(self):
        self.send_to_js("navigate", {"screen": "character-select"})

    def set_game_state(self, state):
        """Set game state and notify plugins (mirrors UIManager.set_game_state)."""
        from nine.core.game_state import GameState
        if self.game_state == state:
            return
        old_state = self.game_state
        self.game_state = state
        # Post actual enum values (plugins compare with GameState.MENU etc.)
        self.app.event_manager.post("game_state_changed", {
            "old_state": old_state,
            "new_state": state,
        })

    def enter_game(self, character_data=None):
        from nine.core.game_state import GameState
        self.set_game_state(GameState.IN_GAME)
        self.send_to_js("navigate", {"screen": "hidden"})
        logger.info("Entered game state")

    def destroy_all(self):
        self.send_to_js("navigate", {"screen": "hidden"})

    # ================================================================
    # Shutdown
    # ================================================================

    def destroy(self):
        """Clean up CEF resources."""
        header = self._cef.get('header') if hasattr(self, '_cef') else None

        if self._browser_host:
            try:
                self._browser_host.contents.close_browser(
                    self._browser_host, 1
                )
            except Exception as e:
                logger.error(f"close_browser error: {e}")

        self.app.taskMgr.remove("cef-loop")
        self.app.taskMgr.remove("cef-texture")
        self.app.taskMgr.remove("cef-mouse-move")

        if self.http_server:
            self.http_server.shutdown()

        if self.card:
            self.card.removeNode()

        # Remove all input handlers
        self._input.ignoreAll()

        if header:
            try:
                header.cef_shutdown()
            except Exception as e:
                logger.error(f"cef_shutdown error: {e}")

        self._browser = None
        self._browser_host = None
        self._client = None
        self._cef_app = None

        logger.info("CEFUIManager destroyed")
