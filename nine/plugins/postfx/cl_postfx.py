"""
Client-side PS1 pixelation post-processing effect.
Renders scene at low resolution and scales up with nearest-neighbor filtering.
"""

from panda3d.core import (
    Texture, GraphicsOutput, FrameBufferProperties,
    WindowProperties, SamplerState, CardMaker,
    NodePath, Camera, OrthographicLens
)
from nine.core.plugins import PluginModule
from nine.core.config import config


# Resolution presets (width, height)
PS1_RESOLUTIONS = {
    0: (320, 240),   # Low - Classic PS1
    1: (640, 480),   # Medium - PS1 high-res
    2: (800, 600),   # High - Retro PC
}


class PostFXModule(PluginModule):
    """PS1-style pixelation effect module."""

    def on_load(self):
        self._buffer = None
        self._texture = None
        self._quad = None
        self._camera = None
        self._enabled = False
        self._resolution_level = config.get("ps1_effect_resolution", 1)

        # Subscribe to settings changes
        self.event_manager.subscribe("ps1_effect_toggle", self._on_toggle)
        self.event_manager.subscribe("ps1_effect_resolution", self._on_resolution_change)

        # Apply saved setting on load
        if config.get("ps1_effect_enabled", False):
            # Defer setup to allow window to initialize
            self.app.taskMgr.doMethodLater(0.5, self._deferred_enable, "ps1_deferred_enable")

        self.logger.info("PostFX module loaded")

    def on_unload(self):
        self.event_manager.unsubscribe("ps1_effect_toggle", self._on_toggle)
        self.event_manager.unsubscribe("ps1_effect_resolution", self._on_resolution_change)
        self._teardown_pixelation()
        self.logger.info("PostFX module unloaded")

    def _deferred_enable(self, task):
        """Enable effect after window is ready."""
        self.toggle(True)
        return task.done

    def _on_toggle(self, data: dict):
        """Handle toggle event from settings."""
        enabled = data.get("enabled", False)
        self.toggle(enabled)

    def _on_resolution_change(self, data: dict):
        """Handle resolution change event from settings."""
        level = data.get("level", 1)
        self.set_resolution(level)

    def toggle(self, enabled: bool):
        """Enable or disable pixelation effect."""
        if enabled and not self._enabled:
            self._setup_pixelation()
        elif not enabled and self._enabled:
            self._teardown_pixelation()

    def set_resolution(self, level: int):
        """Set pixelation resolution level (0=Low, 1=Medium, 2=High)."""
        level = max(0, min(2, level))
        if level != self._resolution_level:
            self._resolution_level = level
            if self._enabled:
                # Rebuild with new resolution
                self._teardown_pixelation()
                self._setup_pixelation()

    def _setup_pixelation(self):
        """Create low-resolution render buffer and display quad."""
        if self._enabled:
            return

        res = PS1_RESOLUTIONS.get(self._resolution_level, (640, 480))
        width, height = res

        try:
            # Create texture for render target
            self._texture = Texture("ps1_buffer")
            self._texture.setMinfilter(SamplerState.FT_nearest)
            self._texture.setMagfilter(SamplerState.FT_nearest)
            self._texture.setWrapU(SamplerState.WM_clamp)
            self._texture.setWrapV(SamplerState.WM_clamp)

            # Create offscreen buffer
            fbprops = FrameBufferProperties()
            fbprops.setRgbColor(True)
            fbprops.setDepthBits(24)

            winprops = WindowProperties()
            winprops.setSize(width, height)

            flags = GraphicsOutput.BF_refuse_window | GraphicsOutput.BF_resizeable

            self._buffer = self.app.graphicsEngine.makeOutput(
                self.app.pipe,
                "ps1_buffer",
                -100,  # Sort order (render before main window)
                fbprops,
                winprops,
                flags,
                self.app.win.getGsg(),
                self.app.win
            )

            if not self._buffer:
                self.logger.error("Failed to create offscreen buffer")
                return

            # Setup render texture
            self._buffer.addRenderTexture(
                self._texture,
                GraphicsOutput.RTM_copy_ram,
                GraphicsOutput.RTP_color
            )

            # Create camera for the buffer
            self._buffer.setClearColor(self.app.win.getClearColor())
            self._buffer.setSort(-100)

            # Use main camera for buffer rendering
            dr = self._buffer.makeDisplayRegion()
            dr.setCamera(self.app.cam)

            # Hide main window's 3D rendering
            self.app.win.getDisplayRegion(0).setActive(False)

            # Create fullscreen quad to display the texture
            cm = CardMaker("ps1_quad")
            cm.setFrameFullscreenQuad()
            cm.setUvRange(self._texture)

            self._quad = NodePath(cm.generate())
            self._quad.setTexture(self._texture)
            self._quad.reparentTo(self.app.render2d)

            # Ensure quad is behind UI
            self._quad.setBin("background", 0)

            self._enabled = True
            self.logger.info(f"PS1 effect enabled at {width}x{height}")

        except Exception as e:
            self.logger.error(f"Failed to setup pixelation: {e}")
            self._teardown_pixelation()

    def _teardown_pixelation(self):
        """Remove pixelation effect and restore normal rendering."""
        if not self._enabled and self._buffer is None and self._quad is None:
            return

        try:
            # Remove quad
            if self._quad:
                self._quad.removeNode()
                self._quad = None

            # Restore main window rendering
            if self.app.win and self.app.win.getNumDisplayRegions() > 0:
                self.app.win.getDisplayRegion(0).setActive(True)

            # Remove buffer
            if self._buffer:
                self.app.graphicsEngine.removeWindow(self._buffer)
                self._buffer = None

            self._texture = None
            self._enabled = False
            self.logger.info("PS1 effect disabled")

        except Exception as e:
            self.logger.error(f"Error during teardown: {e}")
            self._enabled = False
            self._buffer = None
            self._quad = None
            self._texture = None

    @property
    def enabled(self) -> bool:
        """Check if effect is enabled."""
        return self._enabled

    @property
    def resolution_level(self) -> int:
        """Get current resolution level."""
        return self._resolution_level
