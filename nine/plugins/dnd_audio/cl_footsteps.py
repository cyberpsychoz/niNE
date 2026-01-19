"""
Footstep System - система звуков шагов персонажа.

Воспроизводит звуки шагов синхронно с анимацией движения.
Поддерживает разные поверхности и типы брони.
"""

import time
from nine.core.plugins import PluginModule


class FootstepSystem(PluginModule):
    """
    Система звуков шагов.
    Воспроизводит шаги в зависимости от:
    - Скорости движения (ходьба/бег)
    - Типа поверхности
    - Наличия тяжёлой брони
    """

    # Интервалы между шагами (в секундах)
    WALK_INTERVAL = 0.5      # Интервал при ходьбе
    RUN_INTERVAL = 0.3       # Интервал при беге

    # Громкость шагов (0.0 - 1.0)
    FOOTSTEP_VOLUME = 0.25   # Базовая громкость шагов
    JUMP_VOLUME = 0.3        # Громкость прыжка
    LAND_VOLUME = 0.35       # Громкость приземления

    def on_load(self):
        self.logger.info("Footstep System loaded")

        # Состояние
        self.last_step_time = 0.0
        self.is_moving = False
        self.is_running = False
        self.current_surface = "dirt"
        self.has_chain_armor = False

        # Audio manager
        self.audio = None

        # Состояние прыжка
        self.was_on_ground = True

        # Запускаем задачу обновления
        self.app.taskMgr.add(self._update_task, "footstep-update")

    def on_unload(self):
        self.app.taskMgr.remove("footstep-update")
        self.logger.info("Footstep System unloaded")

    def _get_audio(self):
        """Получает audio manager (ленивая инициализация)."""
        if self.audio:
            return self.audio

        if hasattr(self.app, 'audio_manager'):
            self.audio = self.app.audio_manager
            return self.audio

        return None

    def _update_task(self, task):
        """Задача обновления звуков шагов."""
        audio = self._get_audio()
        if not audio:
            return task.cont

        # Получаем состояние игрока
        player_state = self._get_player_state()
        if not player_state:
            return task.cont

        is_moving = player_state.get("is_moving", False)
        is_running = player_state.get("is_running", False)
        is_on_ground = player_state.get("is_on_ground", True)

        # Обновляем состояние
        self.is_moving = is_moving
        self.is_running = is_running

        # Прыжок/приземление
        if not is_on_ground and self.was_on_ground:
            # Начали прыжок
            audio.play_jump(self.current_surface, self.has_chain_armor, volume=self.JUMP_VOLUME)
        elif is_on_ground and not self.was_on_ground:
            # Приземлились
            audio.play_land(self.current_surface, self.has_chain_armor, volume=self.LAND_VOLUME)

        self.was_on_ground = is_on_ground

        # Шаги только на земле и при движении
        if not is_on_ground or not is_moving:
            return task.cont

        # Проверяем интервал
        current_time = time.time()
        interval = self.RUN_INTERVAL if is_running else self.WALK_INTERVAL

        if current_time - self.last_step_time >= interval:
            # Воспроизводим шаг с правильной громкостью
            volume = self.FOOTSTEP_VOLUME * (1.2 if is_running else 1.0)
            audio.play_footstep(
                surface=self.current_surface,
                is_running=is_running,
                has_chain_armor=self.has_chain_armor,
                volume=volume
            )
            self.last_step_time = current_time

        return task.cont

    def _get_player_state(self) -> dict:
        """Получает состояние игрока."""
        # Пытаемся получить из dev_state (если клиент в dev mode)
        if hasattr(self.app, '_dev_state'):
            state = self.app._dev_state
            return {
                "is_moving": state.get("is_moving", False),
                "is_running": state.get("is_running", False),
                "is_on_ground": state.get("is_on_ground", True),
            }

        # Проверяем keyMap для определения движения
        if hasattr(self.app, 'keyMap'):
            km = self.app.keyMap
            is_moving = km.get("w") or km.get("a") or km.get("s") or km.get("d")
            is_running = km.get("shift", False) and is_moving

            return {
                "is_moving": is_moving,
                "is_running": is_running,
                "is_on_ground": True,  # На клиенте мы не всегда знаем
            }

        return None

    # =========================================================================
    # Публичные методы
    # =========================================================================

    def set_surface(self, surface: str):
        """
        Устанавливает тип поверхности.

        Args:
            surface: dirt, stone, water, wood
        """
        valid_surfaces = ["dirt", "stone", "water", "wood"]
        if surface.lower() in valid_surfaces:
            self.current_surface = surface.lower()
            self.logger.debug(f"Surface changed to: {self.current_surface}")

    def set_armor_type(self, has_chain: bool):
        """
        Устанавливает тип брони (влияет на звук шагов).

        Args:
            has_chain: True если персонаж в кольчуге/латах
        """
        self.has_chain_armor = has_chain

    def detect_surface_at_position(self, x: float, y: float, z: float) -> str:
        """
        Определяет тип поверхности в позиции (через raycast).

        TODO: Реализовать через материалы коллизий.
        """
        # По умолчанию - земля
        return "dirt"


class FootstepSurfaceDetector:
    """
    Определитель типа поверхности через raycast.

    Использует текстуры или теги узлов для определения материала.
    """

    # Маппинг названий узлов/материалов на типы поверхностей
    SURFACE_MAPPING = {
        # По имени узла
        "floor_stone": "stone",
        "floor_wood": "wood",
        "water": "water",
        "grass": "dirt",
        "dirt": "dirt",

        # По материалу/текстуре
        "stone_floor": "stone",
        "wooden_floor": "wood",
        "cobblestone": "stone",
        "planks": "wood",
    }

    @staticmethod
    def detect_from_node_name(node_name: str) -> str:
        """Определяет поверхность по имени узла."""
        name_lower = node_name.lower()

        for pattern, surface in FootstepSurfaceDetector.SURFACE_MAPPING.items():
            if pattern in name_lower:
                return surface

        # По умолчанию
        return "dirt"
