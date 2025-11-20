from direct.gui.DirectGui import DirectFrame, DirectButton, DGG
from panda3d.core import LVector4, NodePath, LColor

from nine.ui.base_component import BaseUIComponent


class InGameMenu(BaseUIComponent):
    """
    In-game menu component accessible during gameplay.
    Allows continuing the game or disconnecting from the server.
    """

    def __init__(self, ui_manager, client):
        super().__init__(ui_manager)
        self.client = client  # Reference to the GameClient for disconnect functionality

        # Consistent button styling
        self.button_color = (LColor(0.1, 0.1, 0.1, 0.8), LColor(0.2, 0.2, 0.2, 0.8), LColor(0.3, 0.3, 0.3, 0.8), LColor(0.1, 0.1, 0.1, 0.5))

        self._setup()

    def _setup(self):
        # Background frame - similar to LoginMenu's root frame
        self._add_element(
            'root',
            DirectFrame(
                frameSize=(-0.7, 0.7, -0.5, 0.5), # Adjusted size for central appearance
                frameColor=(0, 0, 0, 0.7),      # Dark transparent background
                parent=self.base.aspect2d,      # Parent to aspect2d for central positioning
                sortOrder=10  # Ensure it's on top
            )
        )

        # Buttons anchor - for central vertical stacking
        buttons_anchor = self._add_element('buttons_anchor', NodePath("in-game-menu-buttons-anchor"))
        buttons_anchor.reparentTo(self._elements['root'])
        # The anchor is already centered within its parent (the root frame)

        # Continue Button
        self._add_element(
            'continue_button',
            DirectButton(
                text="Continue Game",
                scale=0.07,  # Consistent scale
                command=self._on_continue_click,
                frameColor=self.button_color, # Consistent color
                text_fg=(1,1,1,1), # White text
                pressEffect=True, # Consistent effect
                relief=DGG.FLAT, # Consistent relief
                pos=(0, 0, 0.1), # Adjusted position within the frame
                parent=buttons_anchor # Parent to the anchor
            )
        )

        # Disconnect Button
        self._add_element(
            'disconnect_button',
            DirectButton(
                text="Disconnect",
                scale=0.07, # Consistent scale
                command=self._on_disconnect_click,
                frameColor=self.button_color, # Consistent color
                text_fg=(1,1,1,1), # White text
                pressEffect=True, # Consistent effect
                relief=DGG.FLAT, # Consistent relief
                pos=(0, 0, -0.1), # Adjusted position within the frame
                parent=buttons_anchor # Parent to the anchor
            )
        )

        self.hide() # Initially hidden

    def _on_continue_click(self):
        """Hides the menu and resumes gameplay."""
        print("Continue button clicked!")
        self.ui_manager.hide_in_game_menu()

    def _on_disconnect_click(self):
        """Initiates disconnection from the server."""
        print("Disconnect button clicked!")
        self.client.disconnect_from_server()