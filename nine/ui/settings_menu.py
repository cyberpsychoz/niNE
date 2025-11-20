# nine/ui/settings_menu.py
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectEntry, DirectLabel, DirectOptionMenu, DGG
from panda3d.core import LColor, TextNode, WindowProperties

from nine.ui.base_component import BaseUIComponent
from nine.core.config import config # Import the global config instance


class SettingsMenu(BaseUIComponent):
    """
    Settings menu component to adjust game settings like nickname and resolution.
    """
    def __init__(self, ui_manager, client):
        super().__init__(ui_manager)
        self.client = client
        self.button_color = (LColor(0.1, 0.1, 0.1, 0.8), LColor(0.2, 0.2, 0.2, 0.8), LColor(0.3, 0.3, 0.3, 0.8), LColor(0.1, 0.1, 0.1, 0.5))
        self._setup()

    def _setup(self):
        # Main Frame
        frame = self._add_element('root', DirectFrame(
            parent=self.base.aspect2d, 
            frameColor=(0, 0, 0, 0.7), 
            frameSize=(-0.8, 0.8, -0.6, 0.6),
            sortOrder=10
        ))

        # Title
        self._add_element('title', DirectLabel(
            parent=frame,
            text="Settings",
            scale=0.1,
            pos=(0, 0, 0.45),
            text_fg=(1,1,1,1),
            relief=None
        ))

        # Nickname Label and Entry
        self._add_element('nickname_label', DirectLabel(
            parent=frame,
            text="Nickname:",
            scale=0.06,
            pos=(-0.4, 0, 0.2),
            text_align=TextNode.ALeft,
            text_fg=(1,1,1,1),
            relief=None
        ))
        self._add_element('nickname_entry', DirectEntry(
            parent=frame,
            scale=0.06,
            pos=(0.1, 0, 0.2),
            initialText=config.get("nickname"),
            numLines=1,
            width=10,
            text_align=TextNode.ALeft,
            frameColor=self.button_color[0], # Using normal button color
            text_fg=(1,1,1,1)
        ))

        # Resolution Label and Option Menu
        self._add_element('resolution_label', DirectLabel(
            parent=frame,
            text="Resolution:",
            scale=0.06,
            pos=(-0.4, 0, 0.0),
            text_align=TextNode.ALeft,
            text_fg=(1,1,1,1),
            relief=None
        ))
        available_resolutions = config.get("available_resolutions")
        current_resolution = config.get("resolution")
        self._add_element('resolution_option_menu', DirectOptionMenu(
            parent=frame,
            text=current_resolution,
            scale=0.06,
            pos=(0.1, 0, 0.0),
            items=available_resolutions,
            initialitem=available_resolutions.index(current_resolution) if current_resolution in available_resolutions else 0,
            highlightColor=(0.2, 0.6, 0.2, 1), # Highlight color for selected item
            frameColor=self.button_color[0],
            text_fg=(1,1,1,1),
            sortOrder=11, # Ensure dropdown is on top
            command=self._on_resolution_selected
        ))

        # Save Button
        self._add_element('save_button', DirectButton(
            parent=frame,
            text="Save",
            scale=0.07,
            pos=(0, 0, -0.3),
            command=self._on_save_click,
            frameColor=self.button_color,
            text_fg=(1,1,1,1),
            pressEffect=True,
            relief=DGG.FLAT
        ))

        # Back Button
        self._add_element('back_button', DirectButton(
            parent=frame,
            text="Back",
            scale=0.07,
            pos=(0, 0, -0.45),
            command=self._on_back_click,
            frameColor=self.button_color,
            text_fg=(1,1,1,1),
            pressEffect=True,
            relief=DGG.FLAT
        ))
        
        self.hide()

    def _on_resolution_selected(self, selection):
        """Callback for when a resolution is selected from the dropdown."""
        print(f"Resolution selected: {selection}")

    def _on_save_click(self):
        """Saves the settings and applies changes."""
        new_nickname = self._elements['nickname_entry'].get()
        selected_resolution = self._elements['resolution_option_menu'].get()

        # Update config
        config.set("nickname", new_nickname)
        config.set("resolution", selected_resolution)

        # Apply nickname change to client
        self.client.character_name = new_nickname

        # Apply resolution change
        width, height = map(int, selected_resolution.split('x'))
        
        # Correct way to change window size in Panda3D
        props = WindowProperties()
        props.setSize(width, height)
        self.client.win.requestProperties(props)
        
        print(f"Settings saved: Nickname={new_nickname}, Resolution={selected_resolution}")
        
        self.ui_manager.hide_settings_menu()
        self.ui_manager.show_main_menu() # Go back to main menu

    def _on_back_click(self):
        """Goes back to the main menu without saving changes."""
        print("Settings not saved, returning to main menu.")
        self.ui_manager.hide_settings_menu()
        self.ui_manager.show_main_menu() # Go back to main menu
