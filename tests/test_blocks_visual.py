"""Visual test script for Block layout system."""

from direct.showbase.ShowBase import ShowBase
from panda3d.core import loadPrcFileData, TransparencyAttrib
from direct.gui.DirectGui import DirectFrame

# Window config
loadPrcFileData('', 'window-title Block Layout Test')
loadPrcFileData('', 'win-size 1280 720')

class TestApp(ShowBase):
    def __init__(self):
        super().__init__()

        from nine.ui.blocks import Block
        from nine.ui.ui_config import ui

        # Dark background
        bg = DirectFrame(
            parent=self.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=(0.1, 0.08, 0.06, 1.0),
        )

        # Test Block 1: Simple rows with labels and sliders
        block1 = Block(
            parent=self.aspect2d,
            width=1.4,
            padding=0.05,
            bg_color=ui.colors.bg_medium,
            pos=(-0.5, 0, 0.3)
        )

        block1.label("AUDIO SETTINGS", style="title", align="center")
        block1.spacer(0.04)

        r1 = block1.row(justify="space-between")
        r1.label("Master Volume:")
        r1.slider(name="master", min_val=0, max_val=100, initial=80, value_format="{:.0f}%")

        block1.spacer(0.03)

        r2 = block1.row(justify="space-between")
        r2.label("Music:")
        r2.slider(name="music", min_val=0, max_val=100, initial=70, value_format="{:.0f}%")

        block1.spacer(0.03)

        r3 = block1.row(justify="space-between")
        r3.label("Sound Effects:")
        r3.slider(name="sfx", min_val=0, max_val=100, initial=90, value_format="{:.0f}%")

        frame1 = block1.build()
        print(f"Block 1 content height: {block1.get_content_height()}")

        # Test Block 2: Buttons and checkboxes
        block2 = Block(
            parent=self.aspect2d,
            width=1.0,
            padding=0.05,
            bg_color=ui.colors.bg_medium,
            pos=(0.5, 0, 0.3)
        )

        block2.label("OPTIONS", style="title", align="center")
        block2.spacer(0.04)

        r4 = block2.row(justify="space-between")
        r4.label("Invert Y:")
        r4.checkbox(name="invert_y", initial=False)

        block2.spacer(0.03)

        r5 = block2.row(justify="space-between")
        r5.label("Third Person:")
        r5.checkbox(name="third_person", initial=True)

        block2.spacer(0.04)

        r6 = block2.row(justify="center", gap=0.1)
        r6.button("Save", command=lambda: print("Save clicked"), small=True)
        r6.button("Cancel", command=lambda: print("Cancel clicked"), small=True)

        frame2 = block2.build()
        print(f"Block 2 content height: {block2.get_content_height()}")

        # Test Block 3: Entry fields
        block3 = Block(
            parent=self.aspect2d,
            width=1.2,
            padding=0.05,
            bg_color=ui.colors.bg_medium,
            pos=(0, 0, -0.4)
        )

        block3.label("LOGIN", style="title", align="center")
        block3.spacer(0.04)

        r7 = block3.row(justify="space-between")
        r7.label("Nickname:")
        r7.entry(name="nickname", initial="Player", width=14)

        block3.spacer(0.03)

        r8 = block3.row(justify="space-between")
        r8.label("Resolution:")
        r8.dropdown(name="resolution", items=["1280x720", "1920x1080", "2560x1440"], initial="1280x720")

        block3.spacer(0.04)

        r9 = block3.row(justify="center")
        r9.button("Connect", command=lambda: print(f"Connecting as {block3.get('nickname')}"), small=True)

        frame3 = block3.build()
        print(f"Block 3 content height: {block3.get_content_height()}")

        # Print values on key press
        def print_values():
            print("---")
            print(f"Master: {block1.get('master')}")
            print(f"Music: {block1.get('music')}")
            print(f"SFX: {block1.get('sfx')}")
            print(f"Invert Y: {block2.get('invert_y')}")
            print(f"Third Person: {block2.get('third_person')}")
            print(f"Nickname: {block3.get('nickname')}")
            print(f"Resolution: {block3.get('resolution')}")

        self.accept('space', print_values)
        self.accept('escape', self.userExit)

        print("\n=== Block Layout Visual Test ===")
        print("Press SPACE to print current values")
        print("Press ESC to exit")


if __name__ == '__main__':
    app = TestApp()
    app.run()
