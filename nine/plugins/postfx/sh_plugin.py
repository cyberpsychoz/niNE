"""
Post-processing effects plugin.
Includes PS1-style pixelation effect.
"""

from nine.core.plugins import PluginInfo

PLUGIN_INFO = PluginInfo(
    unique_id="nine.postfx",
    name="Post-Processing Effects",
    description="PS1-style pixelation effect",
    author="niNE Team",
    version="1.0.0",
    dependencies=[],
    load_order=90,
    enabled=True,
)
