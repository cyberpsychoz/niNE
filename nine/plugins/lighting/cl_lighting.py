"""
Клиентский модуль освещения.
Применяет настройки освещения, полученные от сервера.
"""

from panda3d.core import AmbientLight, DirectionalLight, Fog, Vec4
from nine.core.plugins import PluginModule


class LightingClientModule(PluginModule):

    def on_load(self):
        self.light_nodes = []
        self.fog_applied = False

        # Подписка на конфигурацию мира
        self.event_manager.subscribe("world_config", self.on_world_config)

        self.logger.info("Клиентский модуль освещения загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("world_config", self.on_world_config)
        self._clear_lights()
        self._clear_fog()
        self.logger.info("Клиентский модуль освещения выгружен")

    def on_world_config(self, data: dict):
        """Обрабатывает конфигурацию мира от сервера."""
        lighting_config = data.get("lighting", {})
        fog_config = data.get("fog", {})

        if lighting_config:
            self._apply_lighting(lighting_config)

        self._apply_fog(fog_config)

    def _clear_lights(self):
        """Удаляет все созданные источники света."""
        for node in self.light_nodes:
            self.app.render.clearLight(node)
            node.removeNode()
        self.light_nodes.clear()

    def _clear_fog(self):
        """Удаляет туман."""
        if self.fog_applied:
            self.app.render.clearFog()
            self.fog_applied = False

    def _apply_lighting(self, config: dict):
        """Применяет конфигурацию освещения."""
        self._clear_lights()

        # Ambient light
        ambient_cfg = config.get("ambient", {})
        if ambient_cfg.get("enabled", True):
            ambient = AmbientLight("ambient")
            color = ambient_cfg.get("color", [0.2, 0.2, 0.2, 1.0])
            ambient.setColor(Vec4(*color))
            ambient_np = self.app.render.attachNewNode(ambient)
            self.app.render.setLight(ambient_np)
            self.light_nodes.append(ambient_np)

        # Directional lights (sun, fill, rim)
        for light_name in ["sun", "fill", "rim"]:
            light_cfg = config.get(light_name)
            if light_cfg and light_cfg.get("enabled", True):
                light = DirectionalLight(light_name)
                color = light_cfg.get("color", [1.0, 1.0, 1.0, 1.0])
                light.setColor(Vec4(*color))
                light_np = self.app.render.attachNewNode(light)
                direction = light_cfg.get("direction", [0, -45, 0])
                light_np.setHpr(*direction)
                self.app.render.setLight(light_np)
                self.light_nodes.append(light_np)

        self.logger.info("Освещение применено")

    def _apply_fog(self, config: dict):
        """Применяет конфигурацию тумана."""
        self._clear_fog()

        if not config.get("enabled", False):
            return

        fog = Fog("world_fog")
        color = config.get("color", [0.5, 0.5, 0.5])
        fog.setColor(*color)

        linear_range = config.get("linear_range", [100, 500])
        fog.setLinearRange(linear_range[0], linear_range[1])

        self.app.render.setFog(fog)
        self.fog_applied = True

        self.logger.info("Туман применён")
