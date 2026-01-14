"""
Camera controller with first-person and third-person modes.

Third-person: Camera orbits around the player target.
First-person: Camera at player eye level, looking where player faces.

Mouse moves the camera in both modes. Player rotation is handled based on movement direction.
"""

from math import sin, cos, radians, pi

from panda3d.core import NodePath, WindowProperties, Vec3
from direct.task import Task


class CameraController:
    def __init__(self, base, camera: NodePath, win, target: NodePath,
                 sensitivity: float = 1.0, third_person: bool = True,
                 invert_x: bool = False, invert_y: bool = False, fov: float = 70.0):
        self.base = base
        self.camera = camera
        self.win = win
        self.target = target

        # Camera mode
        self.third_person = third_person

        # Mouse inversion
        self.invert_x = invert_x
        self.invert_y = invert_y

        # Field of view (for first-person)
        self.fov = fov
        self._apply_fov()

        # Third-person orbit parameters
        self.distance = 2.0  # Distance from player
        self.tp_height_offset = 0.5  # Height above player to look at (third-person)
        self.min_distance = 2.0
        self.max_distance = 15.0

        # First-person parameters
        self.fp_eye_height = 0.5  # Eye height above player origin

        # Camera angles (degrees)
        self.yaw = 0.0      # Horizontal angle (0 = looking at +Y)
        self.pitch = 20.0 if third_person else 0.0  # Vertical angle
        self.min_pitch = -89.0 if not third_person else -20.0  # First-person can look almost straight up/down
        self.max_pitch = 89.0 if not third_person else 70.0

        # Sensitivity (adjust for comfortable feel)
        self.sensitivity = sensitivity * 30.0

        # Smoothing
        self.smoothing = 0.15  # Lower = smoother but more lag
        self.target_yaw = self.yaw
        self.target_pitch = self.pitch

        # State
        self._task = None

    def _apply_fov(self):
        """Apply field of view to the camera lens."""
        if self.base.camLens:
            self.base.camLens.setFov(self.fov)

    def set_fov(self, fov: float):
        """Set new field of view."""
        self.fov = fov
        self._apply_fov()

    def start(self):
        """Start camera updates and capture mouse."""
        self.stop()
        self._task = self.base.taskMgr.add(self._update, "camera-update")

        # Hide cursor and capture mouse
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_relative)
        self.win.requestProperties(props)

    def stop(self):
        """Stop camera updates and release mouse."""
        if self._task:
            self.base.taskMgr.remove(self._task)
            self._task = None

        props = WindowProperties()
        props.setCursorHidden(False)
        props.setMouseMode(WindowProperties.M_absolute)
        self.win.requestProperties(props)

    def _update(self, task):
        if not self.target or self.target.isEmpty():
            return Task.cont

        # Process mouse movement
        self._handle_mouse()

        # Update camera position
        self._position_camera()

        return Task.cont

    def _handle_mouse(self):
        """Handle mouse input for camera rotation with smoothing."""
        if not self.base.mouseWatcherNode.hasMouse():
            return

        # Get mouse position (-1 to 1 range, or deltas in relative mode)
        mx = self.base.mouseWatcherNode.getMouseX()
        my = self.base.mouseWatcherNode.getMouseY()

        is_relative = self.win.getProperties().getMouseMode() == WindowProperties.M_relative

        if is_relative:
            dx = mx
            dy = my
        else:
            # Fallback: recenter mouse
            dx = mx
            dy = my
            self.win.movePointer(0, self.win.getXSize() // 2, self.win.getYSize() // 2)

        # Применяем инверсию мыши
        if self.invert_x:
            dx = -dx
        if self.invert_y:
            dy = -dy

        # Update target angles (raw input)
        # В first-person режиме инвертируем направление yaw для правильного управления
        if self.third_person:
            self.target_yaw += dx * self.sensitivity
        else:
            self.target_yaw -= dx * self.sensitivity  # Инверсия для FP
        self.target_pitch -= dy * self.sensitivity

        # Clamp target pitch
        self.target_pitch = max(self.min_pitch, min(self.max_pitch, self.target_pitch))

        # Smooth interpolation towards target (using angle-aware lerp for yaw)
        # This prevents camera jumping when crossing 0/360 boundary
        yaw_diff = (self.target_yaw - self.yaw + 180) % 360 - 180
        self.yaw += yaw_diff * self.smoothing
        self.pitch += (self.target_pitch - self.pitch) * self.smoothing

    def _position_camera(self):
        """Position camera based on current mode."""
        if self.third_person:
            self._position_camera_third_person()
        else:
            self._position_camera_first_person()

    def _position_camera_third_person(self):
        """Position camera in orbit around target (third-person mode)."""
        # Get target position
        target_pos = self.target.getPos()
        look_at = Vec3(target_pos.x, target_pos.y, target_pos.z + self.tp_height_offset)

        # Convert spherical coordinates to cartesian
        # yaw=0 means camera is behind target (negative Y relative to target)
        # yaw increases clockwise when viewed from above
        yaw_rad = radians(self.yaw)
        pitch_rad = radians(self.pitch)

        # Calculate camera offset from target
        cos_pitch = cos(pitch_rad)
        sin_pitch = sin(pitch_rad)

        # Camera position relative to look_at point
        # At yaw=0: camera at (0, -distance, height) looking at target
        cam_x = self.distance * cos_pitch * sin(yaw_rad)
        cam_y = -self.distance * cos_pitch * cos(yaw_rad)
        cam_z = self.distance * sin_pitch

        # Set camera position
        self.camera.setPos(look_at.x + cam_x, look_at.y + cam_y, look_at.z + cam_z)
        self.camera.lookAt(look_at)

    def _position_camera_first_person(self):
        """Position camera at player eye level (first-person mode)."""
        # Get target position
        target_pos = self.target.getPos()

        # Camera at eye level
        eye_pos = Vec3(target_pos.x, target_pos.y, target_pos.z + self.fp_eye_height)
        self.camera.setPos(eye_pos)

        # Set camera rotation directly from yaw and pitch
        # In Panda3D: H (heading) = yaw, P (pitch) = tilt (positive = look down)
        # yaw используется напрямую для направления взгляда
        # pitch: положительный = смотрим вниз
        self.camera.setHpr(self.yaw, self.pitch, 0)

    def get_forward_vector(self):
        """
        Get forward direction based on camera yaw.
        This is where the player will move when pressing W.

        Camera position formula: (dist*sin(yaw), -dist*cos(yaw), height)
        Forward = direction from camera to player = -camera_offset
        So forward = (-sin(yaw), cos(yaw), 0)
        """
        yaw_rad = radians(self.yaw)
        return Vec3(-sin(yaw_rad), cos(yaw_rad), 0)

    def get_right_vector(self):
        """
        Get right direction based on camera yaw.
        This is the direction player moves when pressing D.
        Right = 90° clockwise from forward (when viewed from above)
        """
        yaw_rad = radians(self.yaw)
        return Vec3(cos(yaw_rad), sin(yaw_rad), 0)

    def get_movement_vector(self, input_x, input_y):
        """
        Convert WASD input to world movement direction.

        Args:
            input_x: -1 (A), 0, or 1 (D)
            input_y: -1 (S), 0, or 1 (W)

        Returns:
            Normalized Vec3 movement direction in world space
        """
        if input_x == 0 and input_y == 0:
            return Vec3(0, 0, 0)

        forward = self.get_forward_vector()
        right = self.get_right_vector()

        move_dir = forward * input_y + right * input_x
        move_dir.normalize()
        return move_dir

    def zoom(self, delta):
        """Adjust camera distance."""
        self.distance = max(self.min_distance, min(self.max_distance, self.distance + delta))

    def set_third_person(self, third_person: bool):
        """Switch between first-person and third-person modes."""
        if self.third_person == third_person:
            return

        self.third_person = third_person

        # Update pitch limits for new mode
        if third_person:
            self.min_pitch = -20.0
            self.max_pitch = 70.0
            # Reset pitch to reasonable third-person value
            self.pitch = max(self.min_pitch, min(self.max_pitch, 20.0))
            self.target_pitch = self.pitch
        else:
            self.min_pitch = -89.0
            self.max_pitch = 89.0
            # Reset pitch to level for first-person
            self.pitch = 0.0
            self.target_pitch = self.pitch

    def destroy(self):
        """Clean up."""
        self.stop()
