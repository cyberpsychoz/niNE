"""
Spectator Mode - режим наблюдателя для GM/DM.
Свободный полёт камеры для наблюдения за боем.
"""

from typing import Optional
from panda3d.core import Vec3, WindowProperties
from direct.gui.OnscreenText import OnscreenText

from nine.core.plugins import PluginModule


class SpectatorMode(PluginModule):
    """
    Режим спектатора для GM/DM.
    - Свободный полёт камеры (WASD + Space/Ctrl)
    - Независимость от персонажа
    - Только для ролей dm и admin
    """

    def on_load(self):
        self.logger.info("Spectator Mode loaded")

        # Состояние
        self.is_spectating = False
        self.original_camera_parent = None
        self.original_camera_pos = None
        self.original_camera_hpr = None

        # Параметры камеры
        self.fly_speed = 10.0
        self.fast_speed = 30.0
        self.mouse_sensitivity = 0.2

        # Управление
        self.keys = {
            "forward": False,
            "backward": False,
            "left": False,
            "right": False,
            "up": False,
            "down": False,
            "fast": False,
        }

        # UI
        self.status_text = None

        # Подписки
        self.event_manager.subscribe("dm_spectator_toggle", self._on_toggle_spectator)

        # Привязка клавиш (будет активна только в режиме спектатора)
        # Регистрируем все события, но обрабатываем только когда is_spectating=True

    def on_unload(self):
        self.event_manager.unsubscribe("dm_spectator_toggle", self._on_toggle_spectator)

        if self.is_spectating:
            self._exit_spectator()

        self.logger.info("Spectator Mode unloaded")

    # =========================================================================
    # Переключение режима
    # =========================================================================

    def _on_toggle_spectator(self, data: dict = None):
        """Переключает режим спектатора."""
        # Проверяем права (только dm/admin)
        if not self._check_permissions():
            self._show_message("Недостаточно прав для режима спектатора")
            return

        if self.is_spectating:
            self._exit_spectator()
        else:
            self._enter_spectator()

    def _check_permissions(self) -> bool:
        """Проверяет права на режим спектатора."""
        # TODO: проверить роль игрока (dm/admin)
        # Пока разрешаем всем для тестирования
        return True

    def _enter_spectator(self):
        """Входит в режим спектатора."""
        self.is_spectating = True

        # Сохраняем текущее состояние камеры
        self.original_camera_parent = self.base.camera.getParent()
        self.original_camera_pos = self.base.camera.getPos()
        self.original_camera_hpr = self.base.camera.getHpr()

        # Отсоединяем камеру от персонажа
        self.base.camera.reparentTo(self.base.render)

        # Останавливаем обычный контроллер камеры
        if hasattr(self.base, 'camera_controller') and self.base.camera_controller:
            self.base.camera_controller.stop()

        # Освобождаем курсор для управления мышью
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_relative)
        self.base.win.requestProperties(props)

        # Регистрируем управление
        self._setup_controls()

        # Запускаем задачу обновления
        self.base.taskMgr.add(self._update_task, "spectator-update")

        # Показываем статус
        self._show_status()

        self.logger.info("Entered spectator mode")

    def _exit_spectator(self):
        """Выходит из режима спектатора."""
        self.is_spectating = False

        # Останавливаем задачу
        self.base.taskMgr.remove("spectator-update")

        # Убираем управление
        self._remove_controls()

        # Возвращаем камеру
        if self.original_camera_parent:
            self.base.camera.reparentTo(self.original_camera_parent)
            self.base.camera.setPos(0, 0, 0)  # Сбрасываем позицию относительно родителя
            self.base.camera.setHpr(0, 0, 0)

        # Возобновляем обычный контроллер камеры
        if hasattr(self.base, 'camera_controller') and self.base.camera_controller:
            self.base.camera_controller.start()

        # Скрываем статус
        self._hide_status()

        self.logger.info("Exited spectator mode")

    # =========================================================================
    # Управление
    # =========================================================================

    def _setup_controls(self):
        """Настраивает управление спектатором."""
        # Движение
        self.base.accept("w", self._set_key, ["forward", True])
        self.base.accept("w-up", self._set_key, ["forward", False])
        self.base.accept("s", self._set_key, ["backward", True])
        self.base.accept("s-up", self._set_key, ["backward", False])
        self.base.accept("a", self._set_key, ["left", True])
        self.base.accept("a-up", self._set_key, ["left", False])
        self.base.accept("d", self._set_key, ["right", True])
        self.base.accept("d-up", self._set_key, ["right", False])

        # Вверх/вниз
        self.base.accept("space", self._set_key, ["up", True])
        self.base.accept("space-up", self._set_key, ["up", False])
        self.base.accept("control", self._set_key, ["down", True])
        self.base.accept("control-up", self._set_key, ["down", False])

        # Ускорение
        self.base.accept("shift", self._set_key, ["fast", True])
        self.base.accept("shift-up", self._set_key, ["fast", False])

        # Shift+WASD
        self.base.accept("shift-w", self._set_key, ["forward", True])
        self.base.accept("shift-w-up", self._set_key, ["forward", False])
        self.base.accept("shift-s", self._set_key, ["backward", True])
        self.base.accept("shift-s-up", self._set_key, ["backward", False])
        self.base.accept("shift-a", self._set_key, ["left", True])
        self.base.accept("shift-a-up", self._set_key, ["left", False])
        self.base.accept("shift-d", self._set_key, ["right", True])
        self.base.accept("shift-d-up", self._set_key, ["right", False])

    def _remove_controls(self):
        """Убирает управление спектатором."""
        for key in ["w", "s", "a", "d", "space", "control", "shift"]:
            self.base.ignore(key)
            self.base.ignore(f"{key}-up")
            self.base.ignore(f"shift-{key}")
            self.base.ignore(f"shift-{key}-up")

    def _set_key(self, key: str, value: bool):
        """Устанавливает состояние клавиши."""
        if self.is_spectating:
            self.keys[key] = value

    def _update_task(self, task):
        """Обновляет камеру спектатора."""
        if not self.is_spectating:
            return task.done

        dt = globalClock.getDt()

        # Обработка мыши (поворот камеры)
        self._handle_mouse()

        # Обработка движения
        self._handle_movement(dt)

        return task.cont

    def _handle_mouse(self):
        """Обрабатывает движение мыши для поворота камеры."""
        if not self.base.mouseWatcherNode.hasMouse():
            return

        # В режиме M_relative мышь возвращает смещение
        md = self.base.win.getPointer(0)
        x = md.getX()
        y = md.getY()

        # Центр окна
        center_x = self.base.win.getXSize() // 2
        center_y = self.base.win.getYSize() // 2

        # Вычисляем смещение от центра
        dx = x - center_x
        dy = y - center_y

        # Применяем поворот
        if dx != 0 or dy != 0:
            h = self.base.camera.getH() - dx * self.mouse_sensitivity
            p = self.base.camera.getP() - dy * self.mouse_sensitivity

            # Ограничиваем pitch
            p = max(-89, min(89, p))

            self.base.camera.setHpr(h, p, 0)

            # Возвращаем мышь в центр
            self.base.win.movePointer(0, center_x, center_y)

    def _handle_movement(self, dt: float):
        """Обрабатывает перемещение камеры."""
        speed = self.fast_speed if self.keys["fast"] else self.fly_speed

        # Получаем направления камеры
        forward = self.base.camera.getQuat().getForward()
        right = self.base.camera.getQuat().getRight()
        up = Vec3(0, 0, 1)

        move = Vec3(0, 0, 0)

        if self.keys["forward"]:
            move += forward
        if self.keys["backward"]:
            move -= forward
        if self.keys["right"]:
            move += right
        if self.keys["left"]:
            move -= right
        if self.keys["up"]:
            move += up
        if self.keys["down"]:
            move -= up

        if move.length() > 0:
            move.normalize()
            self.base.camera.setPos(
                self.base.camera.getPos() + move * speed * dt
            )

    # =========================================================================
    # UI
    # =========================================================================

    def _show_status(self):
        """Показывает статус режима спектатора."""
        if not self.status_text:
            self.status_text = OnscreenText(
                text="[СПЕКТАТОР] WASD - движение | Space/Ctrl - вверх/вниз | Shift - ускорение",
                pos=(0, -0.95),
                scale=0.04,
                fg=(0.8, 0.8, 0.3, 0.8),
                shadow=(0, 0, 0, 0.5),
                mayChange=True
            )

    def _hide_status(self):
        """Скрывает статус."""
        if self.status_text:
            self.status_text.destroy()
            self.status_text = None

    def _show_message(self, message: str):
        """Показывает сообщение."""
        msg = OnscreenText(
            text=message,
            pos=(0, 0.5),
            scale=0.05,
            fg=(1, 0.5, 0.5, 1),
            shadow=(0, 0, 0, 0.5)
        )

        def cleanup(task):
            msg.destroy()
            return task.done

        self.base.taskMgr.doMethodLater(2.0, cleanup, f"msg-{id(msg)}")

    # =========================================================================
    # Публичные методы
    # =========================================================================

    def toggle(self):
        """Переключает режим спектатора."""
        self._on_toggle_spectator()

    def is_active(self) -> bool:
        """Возвращает True если режим спектатора активен."""
        return self.is_spectating


# Импорт для globalClock
from direct.showbase.ShowBase import globalClock
