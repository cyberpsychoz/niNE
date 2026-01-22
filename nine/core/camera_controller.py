"""
Camera controller with first-person and third-person modes.

Third-person: Camera orbits around the player target with collision detection.
First-person: Camera at player eye level, looking where player faces.

Mouse moves the camera in both modes. Player rotation is handled based on movement direction.

Collision detection prevents camera from going through walls using raycasting.
"""

from math import sin, cos, radians, pi

from panda3d.core import (
    NodePath, WindowProperties, Vec3, Point3, BitMask32,
    CollisionTraverser, CollisionNode, CollisionRay, CollisionSegment,
    CollisionHandlerQueue, CollisionSphere
)
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
        self._paused = False  # True = cursor visible, no mouse rotation, but camera still follows player

        # Collision detection for third-person mode
        self._collision_enabled = True
        self._collision_offset = 0.3  # How far to keep camera from walls
        self._actual_distance = self.distance  # Current distance after collision
        self._setup_collision()

    def _setup_collision(self):
        """Setup collision detection for camera."""
        # Create collision traverser
        self._coll_traverser = CollisionTraverser("camera_coll_traverser")
        self._coll_handler = CollisionHandlerQueue()

        # Create collision ray from target to camera
        self._coll_ray = CollisionSegment()
        coll_node = CollisionNode("camera_ray")
        coll_node.addSolid(self._coll_ray)

        # Set collision masks - camera ray checks against geometry
        # FROM_MASK = what this ray can collide with
        # INTO_MASK = what can collide with this (not used for rays)
        coll_node.setFromCollideMask(BitMask32.bit(0))  # Collide with default geometry
        coll_node.setIntoCollideMask(BitMask32.allOff())  # Nothing collides with the ray

        # Attach to render (not to target, as we set points manually)
        self._coll_np = self.base.render.attachNewNode(coll_node)
        self._coll_traverser.addCollider(self._coll_np, self._coll_handler)

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
        self._paused = False

    def pause(self):
        """Pause mouse input but keep camera following player.

        Use this when opening UI (chat, menus) - camera stays attached
        but user can move mouse freely.
        """
        if self._paused:
            return

        self._paused = True
        props = WindowProperties()
        props.setCursorHidden(False)
        props.setMouseMode(WindowProperties.M_absolute)
        self.win.requestProperties(props)

    def resume(self):
        """Resume mouse input after pause.

        Call this when closing UI to re-capture mouse.
        """
        if not self._paused:
            return

        self._paused = False
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_relative)
        self.win.requestProperties(props)

    @property
    def is_paused(self) -> bool:
        """Check if camera input is paused."""
        return self._paused

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
        # Don't process mouse when paused (UI open)
        if self._paused:
            return

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
        """Position camera in orbit around target (third-person mode) with collision."""
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

        # Desired camera position
        desired_pos = Vec3(look_at.x + cam_x, look_at.y + cam_y, look_at.z + cam_z)

        # Check collision between target and desired camera position
        actual_distance = self.distance
        if self._collision_enabled:
            actual_distance = self._check_camera_collision(look_at, desired_pos)

        # Recalculate position with actual distance (after collision)
        if actual_distance < self.distance:
            cam_x = actual_distance * cos_pitch * sin(yaw_rad)
            cam_y = -actual_distance * cos_pitch * cos(yaw_rad)
            cam_z = actual_distance * sin_pitch
            actual_pos = Vec3(look_at.x + cam_x, look_at.y + cam_y, look_at.z + cam_z)
        else:
            actual_pos = desired_pos

        self._actual_distance = actual_distance

        # Set camera position
        self.camera.setPos(actual_pos)
        self.camera.lookAt(look_at)

    def _check_camera_collision(self, start: Vec3, end: Vec3) -> float:
        """
        Check for collision between start and end points.

        Args:
            start: Look-at point (near target)
            end: Desired camera position

        Returns:
            Safe distance from start (may be less than desired distance)
        """
        # Calculate direction and distance
        direction = end - start
        desired_distance = direction.length()

        if desired_distance < 0.1:
            return desired_distance

        # Set collision segment from target to desired camera position
        self._coll_ray.setPointA(Point3(start))
        self._coll_ray.setPointB(Point3(end))

        # Traverse collision
        self._coll_traverser.traverse(self.base.render)

        # Check for collisions
        if self._coll_handler.getNumEntries() > 0:
            # Sort by distance (closest first)
            self._coll_handler.sortEntries()

            # Get closest collision point
            entry = self._coll_handler.getEntry(0)
            hit_point = entry.getSurfacePoint(self.base.render)

            # Calculate distance to hit
            hit_distance = (hit_point - start).length()

            # Apply offset to keep camera away from wall
            safe_distance = max(self.min_distance * 0.5, hit_distance - self._collision_offset)

            return min(safe_distance, desired_distance)

        return desired_distance

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

    def set_collision_enabled(self, enabled: bool):
        """Enable or disable camera collision detection."""
        self._collision_enabled = enabled

    def get_actual_distance(self) -> float:
        """Get current camera distance (may be less than target due to collision)."""
        return self._actual_distance

    def destroy(self):
        """Clean up."""
        self.stop()
        if hasattr(self, '_coll_np') and self._coll_np:
            self._coll_np.removeNode()
