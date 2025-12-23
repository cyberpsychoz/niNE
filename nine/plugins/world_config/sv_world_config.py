"""
Серверный модуль конфигурации мира.
Загружает конфиг из server_config.json и отправляет клиентам при подключении.
"""

import json
from nine.core.plugins import PluginModule


class WorldConfigServerModule(PluginModule):

    def on_load(self):
        self.world_config = self._load_world_config()

        # Подписка на событие подключения игрока
        self.event_manager.subscribe("player_joined", self.on_player_joined)

        map_model = self.world_config.get("map", {}).get("model", "N/A")
        self.logger.info(f"World config загружен: {map_model}")

    def on_unload(self):
        self.event_manager.unsubscribe("player_joined", self.on_player_joined)

    def _load_world_config(self) -> dict:
        """Загружает конфигурацию мира из server_config.json."""
        try:
            with open("server_config.json") as f:
                config = json.load(f)
            return config.get("world", self._get_default_config())
        except Exception as e:
            self.logger.error(f"Ошибка загрузки world config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        """Возвращает конфигурацию по умолчанию."""
        return {
            "map": {"model": "nine/assets/models/maps/map.bam"},
            "lighting": {
                "ambient": {"color": [0.15, 0.1, 0.2, 1.0], "enabled": True},
                "sun": {"color": [1.2, 0.7, 0.6, 1.0], "direction": [45, -30, 0], "enabled": True},
                "fill": {"color": [0.2, 0.25, 0.4, 1.0], "direction": [150, -30, 0], "enabled": True},
                "rim": {"color": [0.4, 0.2, 0.1, 1.0], "direction": [-120, -10, 0], "enabled": False}
            },
            "skybox": {
                "texture": "nine/assets/materials/textures/sky.png",
                "radius": 1000,
                "segments": 64,
                "rings": 32,
                "uv_scale": {"v_offset": 0.15, "v_scale": 0.9}
            },
            "fog": {"enabled": False}
        }

    def on_player_joined(self, data: dict):
        """Отправляет конфигурацию мира новому игроку."""
        client_id = data.get("uuid")  # player_joined event uses 'uuid' as client_id
        if client_id is None:
            return

        self.event_manager.post("world_config_send_to_client", {
            "client_id": client_id,
            "data": {
                "type": "world_config",
                **self.world_config
            }
        })
        self.logger.debug(f"World config отправлен клиенту {client_id}")
