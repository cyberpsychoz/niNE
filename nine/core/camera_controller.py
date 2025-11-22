from panda3d.core import NodePath, WindowProperties, LVector3, Vec3
from direct.task import Task
from direct.showbase.ShowBaseGlobal import globalClock


class CameraController:
    def __init__(self, base, camera: NodePath, win, target: NodePath, sensitivity: float = 1.0):
        self.base = base
        self.camera = camera
        self.win = win
        self.target = target

        self.camera_pivot = self.base.render.attachNewNode("camera_pivot")
        self.camera.reparentTo(self.camera_pivot)
        self.camera.setPos(0, -8, 3)
        self.camera.lookAt(self.camera_pivot)

        self.sensitivity_multiplier = sensitivity
        self.min_pitch = -60
        self.max_pitch = 30
        
        self.last_x = None
        self.last_y = None
        
        self._task = None

    def start(self):
        self.stop()
        self._task = taskMgr.add(self._update, "camera-controller-update")
        props = WindowProperties()
        props.setCursorHidden(True)
        # We request relative mode, but the _update logic will handle fallback
        props.setMouseMode(WindowProperties.M_relative)
        self.win.requestProperties(props)
        
        # Initialize mouse position for delta calculation
        if self.base.mouseWatcherNode.hasMouse():
            self.last_x = self.base.mouseWatcherNode.getMouseX()
            self.last_y = self.base.mouseWatcherNode.getMouseY()

    def stop(self):
        if self._task:
            taskMgr.remove(self._task)
            self._task = None
        props = WindowProperties()
        props.setCursorHidden(False)
        props.setMouseMode(WindowProperties.M_absolute)
        self.win.requestProperties(props)
        
        self.last_x = None
        self.last_y = None

    def _update(self, task):
        if not self.target or self.target.isEmpty():
            return Task.cont

        # Follow the target
        self.camera_pivot.setPos(self.target.getPos() + Vec3(0, 0, 1))

        if not self.base.mouseWatcherNode.hasMouse():
            return Task.cont
        
        # Get current mouse data
        x = self.base.mouseWatcherNode.getMouseX()
        y = self.base.mouseWatcherNode.getMouseY()
        
        dx = 0
        dy = 0

        # Calculate delta based on mouse mode
        if self.win.getProperties().getMouseMode() == WindowProperties.M_relative:
            # In relative mode, the values are already the deltas
            dx = x
            dy = y
        elif self.last_x is not None:
            # In absolute mode, calculate the delta from the last position
            dx = x - self.last_x
            dy = y - self.last_y
        
        # Apply rotation if there was movement
        if dx != 0 or dy != 0:
            # Base sensitivity is scaled by the multiplier from config
            sensitivity = 50.0 * self.sensitivity_multiplier

            # Horizontal rotation (yaw)
            self.camera_pivot.setH(self.camera_pivot.getH() - dx * sensitivity)
            
            # Vertical rotation (pitch)
            new_pitch = self.camera_pivot.getP() - dy * sensitivity
            self.camera_pivot.setP(max(self.min_pitch, min(self.max_pitch, new_pitch)))

        # In absolute mode, re-center the pointer to allow continuous movement
        if self.win.getProperties().getMouseMode() == WindowProperties.M_absolute:
            self.win.movePointer(0, self.win.getXSize() // 2, self.win.getYSize() // 2)
            # After re-centering, the new "last" position becomes the center of the screen,
            # which corresponds to (0,0) in the -1 to 1 coordinate space.
            self.last_x = 0
            self.last_y = 0
        
        return Task.cont

    def get_camera_pivot(self):
        return self.camera_pivot

    def destroy(self):
        self.stop()
        if self.camera_pivot:
            self.camera_pivot.removeNode()
            self.camera_pivot = None
        self.camera.reparentTo(self.base.render)
