"""
ImGui Manager V2 - Improved with proper sizing and all components.
"""

import logging
from typing import Any, Dict

try:
    import imgui
    from imgui.integrations.opengl import FixedPipelineRenderer
    IMGUI_AVAILABLE = True
except ImportError:
    IMGUI_AVAILABLE = False
    logging.warning("imgui not installed")

from direct.task.Task import Task
from nine.ui.imgui_helpers import (
    UIHelpers, WINDOW_FLAGS_MENU, SIZE_BUTTON_LARGE, SIZE_BUTTON_MEDIUM,
    SPACING_SECTION, SPACING_ELEMENT
)

logger = logging.getLogger(__name__)


class ImGuiManager:
    """Manages ImGui overlay for Panda3D with proper sizing."""

    def __init__(self, app, callbacks: Dict[str, Any]):
        if not IMGUI_AVAILABLE:
            raise RuntimeError("imgui not installed")

        self.app = app
        self.callbacks = callbacks
        self.ui = UIHelpers()

        # ImGui context
        self.imgui_context = None
        self.imgui_renderer = None

        # Screen management
        self.current_screen = "main_menu"  # main_menu, login, settings, char_select, char_create, in_game

        # Login state
        self.login_ip = "127.0.0.1"
        self.login_name = app.user_config.get("nickname", "Player")
        self.login_password = ""

        # Settings state
        self.settings = app.user_config.copy()
        self.settings_tab = 0

        # Chat state
        self.show_chat = False
        self.chat_messages = []
        self.chat_input = ""

        # Character state
        self.characters = []  # Will be populated from server
        self.selected_character = -1

        # Character creation
        self.char_name = ""
        self.char_race = "human"
        self.char_class = "fighter"
        self.char_background = ""

        # Compatibility
        self.base = app
        self.font = None

        logger.info("ImGuiManager V2 initialized")

    def create_overlay(self):
        if not IMGUI_AVAILABLE:
            return

        self.imgui_context = imgui.create_context()
        self.imgui_renderer = FixedPipelineRenderer()
        self._setup_style()
        self.app.taskMgr.add(self._update_imgui, "imgui-update", sort=1000)
        self._setup_input()
        logger.info("ImGui overlay created")

    def _setup_style(self):
        """Setup BG1-inspired dark fantasy theme."""
        style = imgui.get_style()

        # Colors
        style.colors[imgui.COLOR_TEXT] = (0.94, 0.90, 0.82, 1.00)
        style.colors[imgui.COLOR_WINDOW_BACKGROUND] = (0.08, 0.06, 0.04, 0.94)
        style.colors[imgui.COLOR_FRAME_BACKGROUND] = (0.16, 0.14, 0.10, 0.85)
        style.colors[imgui.COLOR_FRAME_BACKGROUND_HOVERED] = (0.20, 0.17, 0.12, 0.90)
        style.colors[imgui.COLOR_FRAME_BACKGROUND_ACTIVE] = (0.24, 0.20, 0.14, 0.95)
        style.colors[imgui.COLOR_BUTTON] = (0.28, 0.22, 0.14, 0.90)
        style.colors[imgui.COLOR_BUTTON_HOVERED] = (0.35, 0.27, 0.18, 0.95)
        style.colors[imgui.COLOR_BUTTON_ACTIVE] = (0.42, 0.32, 0.21, 1.00)
        style.colors[imgui.COLOR_TITLE_BACKGROUND] = (0.20, 0.15, 0.10, 0.90)
        style.colors[imgui.COLOR_TITLE_BACKGROUND_ACTIVE] = (0.83, 0.69, 0.22, 0.90)
        style.colors[imgui.COLOR_TITLE_BACKGROUND_COLLAPSED] = (0.16, 0.12, 0.08, 0.80)
        style.colors[imgui.COLOR_TAB] = (0.24, 0.18, 0.12, 0.90)
        style.colors[imgui.COLOR_TAB_HOVERED] = (0.35, 0.27, 0.18, 0.95)
        style.colors[imgui.COLOR_TAB_ACTIVE] = (0.42, 0.32, 0.21, 1.00)

        # Sizing
        style.window_padding = (12, 12)
        style.frame_padding = (8, 4)
        style.item_spacing = (8, 6)
        style.item_inner_spacing = (6, 4)

        # Rounding
        style.window_rounding = 6.0
        style.frame_rounding = 3.0
        style.scrollbar_rounding = 3.0
        style.grab_rounding = 3.0
        style.tab_rounding = 3.0

        # Borders
        style.window_border_size = 1.5
        style.frame_border_size = 1.0

    def _setup_input(self):
        self.app.accept("mouse1", self._on_mouse_down, [0])
        self.app.accept("mouse1-up", self._on_mouse_up, [0])
        self.app.accept("mouse3", self._on_mouse_down, [1])
        self.app.accept("mouse3-up", self._on_mouse_up, [1])
        self.app.accept("t", self._toggle_chat)

    def _on_mouse_down(self, button):
        io = imgui.get_io()
        io.mouse_down[button] = True

    def _on_mouse_up(self, button):
        io = imgui.get_io()
        io.mouse_down[button] = False

    def _toggle_chat(self):
        self.show_chat = not self.show_chat

    def _update_imgui(self, task):
        # Update display size
        props = self.app.win.getProperties()
        io = imgui.get_io()
        io.display_size = (props.getXSize(), props.getYSize())

        imgui.new_frame()

        # Update mouse
        if self.app.mouseWatcherNode.hasMouse():
            mouse_x = self.app.mouseWatcherNode.getMouseX()
            mouse_y = self.app.mouseWatcherNode.getMouseY()
            props = self.app.win.getProperties()
            screen_x = (mouse_x + 1.0) * 0.5 * props.getXSize()
            screen_y = (1.0 - mouse_y) * 0.5 * props.getYSize()
            io = imgui.get_io()
            io.mouse_pos = (screen_x, screen_y)

        # Render current screen
        if self.current_screen == "main_menu":
            self._render_main_menu()
        elif self.current_screen == "login":
            self._render_login()
        elif self.current_screen == "settings":
            self._render_settings()
        elif self.current_screen == "char_select":
            self._render_character_select()
        elif self.current_screen == "char_create":
            self._render_character_create()
        elif self.current_screen == "in_game":
            # No menu shown in-game
            pass

        # Chat is overlay (always available)
        if self.show_chat:
            self._render_chat()

        imgui.render()
        self.imgui_renderer.render(imgui.get_draw_data())
        return Task.cont

    def _render_main_menu(self):
        """Main menu with proper sizing."""
        if self.ui.centered_window("DUNGEONS & DRAGONS", 0.35, 0.45, WINDOW_FLAGS_MENU):
            self.ui.center_text("niNE Engine - D&D 5e Mode")
            self.ui.separator()

            # Play button
            if self.ui.centered_button("PLAY", 0.85, SIZE_BUTTON_LARGE):
                self.current_screen = "login"

            self.ui.spacing(SPACING_ELEMENT)

            # Settings button
            if self.ui.centered_button("SETTINGS", 0.85, SIZE_BUTTON_LARGE):
                self.current_screen = "settings"

            self.ui.spacing(SPACING_ELEMENT)

            # Exit button
            if self.ui.centered_button("EXIT", 0.85, SIZE_BUTTON_LARGE):
                if self.callbacks.get("exit"):
                    self.callbacks["exit"]()

            imgui.end()

    def _render_login(self):
        """Login menu with auto-sizing inputs."""
        if self.ui.centered_window("CONNECTION", 0.4, 0.5, WINDOW_FLAGS_MENU):
            self.ui.spacing(SPACING_SECTION)

            # Server IP
            _, self.login_ip = self.ui.labeled_input(
                "Server IP:", self.login_ip, 256, 0.95
            )

            self.ui.spacing(SPACING_SECTION)

            # Character Name
            _, self.login_name = self.ui.labeled_input(
                "Character Name:", self.login_name, 256, 0.95
            )

            self.ui.spacing(SPACING_SECTION)

            # Password
            _, self.login_password = self.ui.labeled_input_password(
                "Password (optional):", self.login_password, 256, 0.95
            )

            self.ui.separator()

            # Buttons side by side
            available_width = imgui.get_content_region_available_width()
            button_width = (available_width - 10) / 2

            if imgui.button("CONNECT", button_width, SIZE_BUTTON_MEDIUM):
                if self.callbacks.get("attempt_login"):
                    self.callbacks["attempt_login"](
                        self.login_ip,
                        self.login_name,
                        self.login_password
                    )
                    self.current_screen = "char_select"

            imgui.same_line()

            if imgui.button("BACK", button_width, SIZE_BUTTON_MEDIUM):
                self.current_screen = "main_menu"

            imgui.end()

    def _render_settings(self):
        """Settings menu with tabs."""
        if self.ui.centered_window("SETTINGS", 0.5, 0.6, WINDOW_FLAGS_MENU):

            if imgui.begin_tab_bar("SettingsTabs"):
                # General tab
                if imgui.begin_tab_item("General")[0]:
                    self.ui.spacing(SPACING_SECTION)

                    _, self.settings["nickname"] = self.ui.labeled_input(
                        "Nickname:", self.settings.get("nickname", "Player"), 256, 0.7
                    )

                    self.ui.spacing(SPACING_ELEMENT)

                    # Resolution dropdown
                    imgui.text("Resolution:")
                    resolutions = ["800x600", "1024x768", "1280x720", "1920x1080"]
                    current_res = self.settings.get("resolution", "1920x1080")
                    current_idx = resolutions.index(current_res) if current_res in resolutions else 3

                    imgui.push_item_width(imgui.get_content_region_available_width() * 0.7)
                    changed, new_idx = imgui.combo("##resolution", current_idx, resolutions)
                    imgui.pop_item_width()

                    if changed:
                        self.settings["resolution"] = resolutions[new_idx]

                    imgui.end_tab_item()

                # Graphics tab
                if imgui.begin_tab_item("Graphics")[0]:
                    self.ui.spacing(SPACING_SECTION)

                    _, self.settings["fov"] = self.ui.labeled_slider_int(
                        "Field of View:", self.settings.get("fov", 70), 60, 110, 0.8
                    )

                    self.ui.spacing(SPACING_ELEMENT)

                    _, self.settings["ps1_effect_enabled"] = self.ui.labeled_checkbox(
                        "PS1 Retro Effect", self.settings.get("ps1_effect_enabled", False)
                    )

                    if self.settings["ps1_effect_enabled"]:
                        _, self.settings["ps1_effect_resolution"] = self.ui.labeled_slider_int(
                            "PS1 Resolution:", self.settings.get("ps1_effect_resolution", 2), 1, 4, 0.8
                        )

                    imgui.end_tab_item()

                # Audio tab
                if imgui.begin_tab_item("Audio")[0]:
                    self.ui.spacing(SPACING_SECTION)

                    _, self.settings["audio_master_volume"] = self.ui.labeled_slider_int(
                        "Master Volume:", self.settings.get("audio_master_volume", 100), 0, 100, 0.8
                    )

                    self.ui.spacing(SPACING_ELEMENT)

                    _, self.settings["audio_bgm_volume"] = self.ui.labeled_slider_int(
                        "Music Volume:", self.settings.get("audio_bgm_volume", 100), 0, 100, 0.8
                    )

                    self.ui.spacing(SPACING_ELEMENT)

                    _, self.settings["audio_sfx_volume"] = self.ui.labeled_slider_int(
                        "SFX Volume:", self.settings.get("audio_sfx_volume", 100), 0, 100, 0.8
                    )

                    imgui.end_tab_item()

                # Controls tab
                if imgui.begin_tab_item("Controls")[0]:
                    self.ui.spacing(SPACING_SECTION)

                    _, self.settings["camera_sensitivity"] = imgui.slider_float(
                        "Camera Sensitivity",
                        self.settings.get("camera_sensitivity", 1.0),
                        0.1, 2.0
                    )

                    self.ui.spacing(SPACING_ELEMENT)

                    _, self.settings["invert_mouse_x"] = self.ui.labeled_checkbox(
                        "Invert Mouse X", self.settings.get("invert_mouse_x", False)
                    )

                    _, self.settings["invert_mouse_y"] = self.ui.labeled_checkbox(
                        "Invert Mouse Y", self.settings.get("invert_mouse_y", False)
                    )

                    imgui.end_tab_item()

                imgui.end_tab_bar()

            # Bottom buttons
            self.ui.separator()

            available_width = imgui.get_content_region_available_width()
            button_width = (available_width - 10) / 2

            if imgui.button("SAVE", button_width, SIZE_BUTTON_MEDIUM):
                self._save_settings()
                self.current_screen = "main_menu"

            imgui.same_line()

            if imgui.button("BACK", button_width, SIZE_BUTTON_MEDIUM):
                self.current_screen = "main_menu"

            imgui.end()

    def _render_character_select(self):
        """Character selection screen."""
        if self.ui.centered_window("SELECT CHARACTER", 0.5, 0.6, WINDOW_FLAGS_MENU):
            self.ui.center_text("Choose your adventurer")
            self.ui.separator()

            # Character list
            imgui.begin_child("CharList", 0, -80, border=True)

            if not self.characters:
                imgui.text("No characters found.")
                imgui.text("Create your first character!")
            else:
                for idx, char in enumerate(self.characters):
                    is_selected = (idx == self.selected_character)

                    if imgui.selectable(
                        f"{char['name']} - {char['race']} {char['class_name']} (Lvl {char.get('level', 1)})",
                        is_selected
                    )[0]:
                        self.selected_character = idx

            imgui.end_child()

            # Bottom buttons
            available_width = imgui.get_content_region_available_width()
            button_width = (available_width - 20) / 3

            if imgui.button("SELECT", button_width, SIZE_BUTTON_MEDIUM):
                if self.selected_character >= 0:
                    # TODO: Actually select character
                    self.current_screen = "in_game"

            imgui.same_line()

            if imgui.button("CREATE NEW", button_width, SIZE_BUTTON_MEDIUM):
                self.current_screen = "char_create"

            imgui.same_line()

            if imgui.button("DISCONNECT", button_width, SIZE_BUTTON_MEDIUM):
                if self.callbacks.get("close_login_menu"):
                    self.callbacks["close_login_menu"]()
                self.current_screen = "main_menu"

            imgui.end()

    def _render_character_create(self):
        """Character creation screen."""
        if self.ui.centered_window("CREATE CHARACTER", 0.5, 0.7, WINDOW_FLAGS_MENU):
            self.ui.center_text("D&D 5e Character Creation")
            self.ui.separator()

            # Name
            _, self.char_name = self.ui.labeled_input(
                "Character Name:", self.char_name, 50, 0.7
            )

            self.ui.spacing(SPACING_SECTION)

            # Race dropdown
            imgui.text("Race:")
            races = ["Human", "Elf", "Dwarf", "Halfling", "Dragonborn",
                    "Gnome", "Half-Elf", "Half-Orc", "Tiefling"]
            imgui.push_item_width(imgui.get_content_region_available_width() * 0.7)
            _, self.char_race = imgui.combo("##race", races.index(self.char_race.capitalize()), races)
            self.char_race = races[self.char_race].lower()
            imgui.pop_item_width()

            self.ui.spacing(SPACING_ELEMENT)

            # Class dropdown
            imgui.text("Class:")
            classes = ["Fighter", "Wizard", "Rogue", "Cleric", "Ranger",
                      "Paladin", "Barbarian", "Bard", "Druid", "Monk",
                      "Sorcerer", "Warlock"]
            imgui.push_item_width(imgui.get_content_region_available_width() * 0.7)
            _, self.char_class = imgui.combo("##class", classes.index(self.char_class.capitalize()), classes)
            self.char_class = classes[self.char_class].lower()
            imgui.pop_item_width()

            self.ui.spacing(SPACING_ELEMENT)

            # Background (optional)
            _, self.char_background = self.ui.labeled_input(
                "Background (optional):", self.char_background, 100, 0.7
            )

            self.ui.separator()

            # Bottom buttons
            available_width = imgui.get_content_region_available_width()
            button_width = (available_width - 10) / 2

            if imgui.button("CREATE", button_width, SIZE_BUTTON_MEDIUM):
                if self.char_name.strip():
                    # TODO: Send to server
                    logger.info(f"Creating character: {self.char_name}")
                    self.current_screen = "char_select"

            imgui.same_line()

            if imgui.button("CANCEL", button_width, SIZE_BUTTON_MEDIUM):
                self.current_screen = "char_select"

            imgui.end()

    def _render_chat(self):
        """Chat window overlay."""
        imgui.set_next_window_position(20, 400, imgui.ONCE)
        imgui.set_next_window_size(600, 350, imgui.ONCE)

        imgui.begin("CHAT (Press T)", True)

        # Messages area
        imgui.begin_child("ChatMessages", 0, -35, border=True)
        for msg in self.chat_messages[-100:]:
            imgui.text(msg)
        imgui.end_child()

        # Input area
        imgui.separator()

        imgui.push_item_width(-80)
        _, self.chat_input = imgui.input_text("##chatinput", self.chat_input, 512)
        imgui.pop_item_width()

        imgui.same_line()

        if imgui.button("Send", 70, 0) or imgui.is_key_pressed(imgui.KEY_ENTER):
            if self.chat_input.strip():
                self.add_chat_message(f"You: {self.chat_input}")
                self.chat_input = ""

        imgui.end()

    def _save_settings(self):
        """Save settings to config.json."""
        import json
        self.app.user_config.update(self.settings)
        with open("config.json", "w") as f:
            json.dump(self.app.user_config, f, indent=4)
        logger.info("Settings saved")

    # Public API methods
    def add_chat_message(self, message: str):
        self.chat_messages.append(message)

    def send_to_js(self, event_type: str, data: Any = None):
        pass

    def show_main_menu(self):
        self.current_screen = "main_menu"

    def show_login_menu(self):
        self.current_screen = "login"

    def close_login_menu(self):
        self.current_screen = "main_menu"

    def show_settings_menu(self):
        self.current_screen = "settings"

    def show_loading_screen(self, text: str = "Loading..."):
        logger.info(f"Loading: {text}")

    def update_loading_progress(self, progress: float, text: str = None):
        pass

    def hide_loading_screen(self):
        pass

    def show_in_game_menu(self):
        pass

    def hide_in_game_menu(self):
        pass

    def destroy(self):
        if self.imgui_renderer:
            self.imgui_renderer.shutdown()
        if self.imgui_context:
            imgui.destroy_context(self.imgui_context)
        logger.info("ImGuiManager destroyed")
