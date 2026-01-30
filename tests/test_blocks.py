"""Test script for Block layout system."""

from direct.showbase.ShowBase import ShowBase
from panda3d.core import loadPrcFileData

# Disable window to just test the layout calculations
loadPrcFileData('', 'window-type none')

from nine.ui.blocks import Block, Row, ElementSize
from nine.ui.ui_config import ui

print("=== Testing Block Layout System ===")
print(f"UI_SCALE: {ui.scale}")
print(f"font.label: {ui.font.label}")
print(f"font.entry: {ui.font.entry}")
print(f"button.small_scale: {ui.button.small_scale}")
print()

# Test element sizes
from nine.ui.blocks import LabelElement, EntryElement, SliderElement, CheckboxElement, ButtonElement

label = LabelElement("Test Label:", style="label")
print(f"Label size: {label.get_size()}")

entry = EntryElement(name="test", initial="value", width=12)
print(f"Entry size: {entry.get_size()}")

slider = SliderElement(name="slider", min_val=0, max_val=100, initial=50)
print(f"Slider size: {slider.get_size()}")

checkbox = CheckboxElement(name="check", initial=True)
print(f"Checkbox size: {checkbox.get_size()}")

button = ButtonElement("Button", small=True)
print(f"Button size: {button.get_size()}")

print()

# Test row size calculation
row = Row(justify="space-between")
row.label("Volume:", style="label")
row.slider(name="vol", min_val=0, max_val=100, initial=50)
print(f"Row size: {row.get_size()}")

print()

# Test full block
block = Block(
    parent=None,  # No actual rendering
    width=1.2,
    padding=0.05
)

block.label("TITLE", style="title", align="center")
block.spacer(0.05)

r1 = block.row(justify="space-between")
r1.label("Setting:", style="label")
r1.slider(name="s1", initial=50)

block.spacer(0.03)

r2 = block.row(justify="center", gap=0.1)
r2.button("OK", small=True)
r2.button("Cancel", small=True)

print(f"Block content height: {block.get_content_height()}")
print(f"Block width: {block.width}")
print(f"Expected frame height: {block.get_content_height() + block.padding * 2}")

print()
print("=== Test Complete ===")
