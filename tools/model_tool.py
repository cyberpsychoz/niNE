#!/usr/bin/env python3
"""
niNE Model Tool - Mixamo Workflow Edition

Optimized for:
1. Opening FBX/GLB files directly (auto-convert to temp)
2. Testing base.bam animations on new models
3. Quick export to game folder
4. Adding Mixamo animations to existing models

Run: python tools/model_tool.py
"""

import sys
import os
import subprocess
import shutil
import platform
import tempfile
from pathlib import Path

# Project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)
sys.path.insert(0, project_root)

# Game assets path
GAME_MODELS_PATH = Path(project_root) / "nine" / "assets" / "models"
PLAYER_MODEL_PATH = GAME_MODELS_PATH / "base.bam"

# Steam Blender paths (for FBX conversion)
STEAM_BLENDER_PATHS = [
    Path.home() / ".steam/debian-installation/steamapps/common/Blender/blender",
    Path.home() / ".steam/steam/steamapps/common/Blender/blender",
    Path.home() / ".local/share/Steam/steamapps/common/Blender/blender",
]

# Blender script for FBX -> GLB conversion
FBX_TO_GLB_SCRIPT = '''
import bpy
import sys
import os
argv = sys.argv
argv = argv[argv.index("--") + 1:]
input_fbx, output_glb = argv[0], argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)

# Import FBX with automatic image search
bpy.ops.import_scene.fbx(
    filepath=input_fbx,
    use_image_search=True,  # Search for textures in subfolders
)

# Try to pack all external images into the blend file
try:
    bpy.ops.file.pack_all()
except:
    pass

# Export GLB with textures embedded
bpy.ops.export_scene.gltf(
    filepath=output_glb,
    export_format='GLB',
    export_image_format='AUTO',
    export_materials='EXPORT',
    export_colors=True,
    export_texcoords=True,
    export_normals=True,
    export_animations=True,
    export_skins=True,
)
'''

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QSlider, QFileDialog, QMessageBox,
    QTextEdit, QGroupBox, QProgressBar, QLineEdit,
    QToolBar, QAction, QStatusBar, QSizePolicy, QComboBox,
    QCheckBox, QInputDialog
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor

# Panda3D imports
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from panda3d.core import (
    loadPrcFileData, getModelPath, Filename,
    WindowProperties, AmbientLight, DirectionalLight
)

# Configure Panda3D before ShowBase init
loadPrcFileData('', 'window-type none')
loadPrcFileData('', 'audio-library-name null')
getModelPath().appendDirectory(Filename.fromOsSpecific(project_root))


# ==================== CONVERSION TOOLS ====================

class ConversionTools:
    """Detect and run conversion utilities."""

    def __init__(self):
        self.system = platform.system()
        self.tools = {}
        self.blender_path = None
        self.temp_dir = Path(tempfile.gettempdir()) / "nine_model_tool"
        self.temp_dir.mkdir(exist_ok=True)
        self._detect_tools()

    def _detect_tools(self):
        self.tools['gltf2bam'] = shutil.which('gltf2bam') is not None
        self.tools['egg2bam'] = shutil.which('egg2bam') is not None
        self.tools['bam2egg'] = shutil.which('bam2egg') is not None

        # Find Blender for FBX conversion
        blender_exe = shutil.which('blender')
        if blender_exe:
            self.blender_path = Path(blender_exe)
            self.tools['blender'] = True
        else:
            # Check Steam paths
            for steam_path in STEAM_BLENDER_PATHS:
                if steam_path.exists():
                    self.blender_path = steam_path
                    self.tools['blender'] = True
                    break
            else:
                self.tools['blender'] = False

    def get_status(self):
        return self.tools.copy()

    def can_convert(self, suffix):
        """Check if we can convert this file type."""
        suffix = suffix.lower()
        if suffix in ('.bam', '.egg'):
            return True
        if suffix in ('.gltf', '.glb'):
            return self.tools.get('gltf2bam', False)
        if suffix == '.fbx':
            # FBX needs Blender + gltf2bam
            return self.tools.get('blender', False) and self.tools.get('gltf2bam', False)
        return False

    def can_convert_fbx(self):
        """Check if FBX conversion is available."""
        return self.tools.get('blender', False) and self.tools.get('gltf2bam', False)

    def convert_to_bam(self, input_path, output_path=None, callback=None):
        """Convert file to BAM format. Returns (success, output_path, message)."""
        input_path = Path(input_path)
        suffix = input_path.suffix.lower()

        if output_path is None:
            output_path = self.temp_dir / (input_path.stem + '.bam')
        else:
            output_path = Path(output_path)

        if suffix == '.bam':
            return True, input_path, "File is already BAM format"

        if suffix == '.egg':
            if not self.tools.get('egg2bam'):
                return False, None, "egg2bam not found"
            try:
                result = subprocess.run(
                    ['egg2bam', '-o', str(output_path), str(input_path)],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    return True, output_path, f"Converted: {output_path.name}"
                return False, None, f"Error: {result.stderr}"
            except Exception as e:
                return False, None, str(e)

        if suffix in ('.gltf', '.glb'):
            if not self.tools.get('gltf2bam'):
                return False, None, "gltf2bam not found. Install: pip install panda3d-gltf"
            try:
                result = subprocess.run(
                    ['gltf2bam', str(input_path), str(output_path)],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    return True, output_path, f"Converted: {output_path.name}"
                return False, None, f"Error: {result.stderr or result.stdout}"
            except subprocess.TimeoutExpired:
                return False, None, "Conversion timeout (>120s)"
            except Exception as e:
                return False, None, str(e)

        if suffix == '.fbx':
            if not self.tools.get('blender'):
                return False, None, "Blender not found (needed for FBX conversion)"
            if not self.tools.get('gltf2bam'):
                return False, None, "gltf2bam not found. Install: pip install panda3d-gltf"

            try:
                # Step 1: FBX -> GLB via Blender
                glb_path = self.temp_dir / (input_path.stem + '.glb')
                script_path = self.temp_dir / 'fbx_to_glb.py'
                script_path.write_text(FBX_TO_GLB_SCRIPT)

                result = subprocess.run(
                    [str(self.blender_path), '--background', '--python', str(script_path),
                     '--', str(input_path), str(glb_path)],
                    capture_output=True, text=True, timeout=120
                )
                if not glb_path.exists():
                    return False, None, f"FBX->GLB error: {result.stderr or result.stdout}"

                # Step 2: GLB -> BAM
                result = subprocess.run(
                    ['gltf2bam', str(glb_path), str(output_path)],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    return True, output_path, f"Converted: {output_path.name}"
                return False, None, f"GLB->BAM error: {result.stderr or result.stdout}"

            except subprocess.TimeoutExpired:
                return False, None, "Conversion timeout (>120s)"
            except Exception as e:
                return False, None, str(e)

        return False, None, f"Unsupported format: {suffix}"

    def cleanup_temp(self):
        """Clean up temporary files."""
        try:
            for ext in ('*.bam', '*.glb', '*.gltf', '*.py'):
                for f in self.temp_dir.glob(ext):
                    f.unlink()
        except Exception:
            pass


# ==================== PANDA3D VIEWER ====================

class Panda3DWidget(QWidget):
    """Widget that hosts Panda3D viewport."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.base = None
        self.actor = None
        self.anims = []
        self.current_anim_idx = 0
        self.play_rate = 1.0
        self.current_file = None

        # Reference model for animations
        self.ref_actor = None
        self.ref_anims = []

        # Camera
        self.cam_distance = 5
        self.cam_heading = 180
        self.cam_pitch = 15
        self.look_at_z = 1.0

        # Mouse tracking
        self.last_mouse_pos = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def init_panda3d(self):
        """Initialize Panda3D after widget is shown."""
        if self.base is not None:
            return

        self.base = ShowBase()

        wp = WindowProperties()
        wp.setParentWindow(int(self.winId()))
        wp.setOrigin(0, 0)
        wp.setSize(self.width(), self.height())

        self.base.openDefaultWindow(props=wp)
        self.base.setBackgroundColor(0.15, 0.15, 0.18)
        self.base.disableMouse()

        # Try to enable PBR rendering
        try:
            import simplepbr
            simplepbr.init()
            self._has_pbr = True
        except ImportError:
            self._has_pbr = False
            # Fallback: basic lighting
            ambient = AmbientLight("ambient")
            ambient.setColor((0.4, 0.4, 0.4, 1))
            self.base.render.setLight(self.base.render.attachNewNode(ambient))

            directional = DirectionalLight("directional")
            directional.setColor((0.8, 0.8, 0.8, 1))
            dir_np = self.base.render.attachNewNode(directional)
            dir_np.setHpr(45, -45, 0)
            self.base.render.setLight(dir_np)

        # Floor grid
        self._create_floor_grid()

        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._panda_step)
        self.update_timer.start(16)

        self._update_camera()

    def _create_floor_grid(self):
        """Create a simple floor grid."""
        from panda3d.core import LineSegs, NodePath
        lines = LineSegs()
        lines.setColor(0.3, 0.3, 0.35, 1)
        lines.setThickness(1)

        size = 5
        step = 0.5
        for i in range(int(-size / step), int(size / step) + 1):
            pos = i * step
            lines.moveTo(pos, -size, 0)
            lines.drawTo(pos, size, 0)
            lines.moveTo(-size, pos, 0)
            lines.drawTo(size, pos, 0)

        grid = self.base.render.attachNewNode(lines.create())
        grid.setPos(0, 0, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.base and self.base.win:
            wp = WindowProperties()
            wp.setSize(self.width(), self.height())
            self.base.win.requestProperties(wp)

    def _panda_step(self):
        """Run one Panda3D frame."""
        if self.base:
            self.base.taskMgr.step()

    def load_model(self, path):
        """Load a model file."""
        if self.actor:
            self.actor.cleanup()
            self.actor.removeNode()
            self.actor = None

        self.anims = []
        self.current_file = path

        try:
            self.actor = Actor(str(path))
            self.actor.reparentTo(self.base.render)

            # Get animations
            self.anims = list(self.actor.getAnimNames())

            # Compute bounds for camera
            bounds = self.actor.getTightBounds()
            if bounds:
                min_pt, max_pt = bounds
                height = max_pt.z - min_pt.z
                self.look_at_z = (max_pt.z + min_pt.z) / 2
                self.cam_distance = max(height * 2.5, 3)

            self._update_camera()

            # Play first animation
            if self.anims:
                self.play_anim(0)

            return True, self.anims

        except Exception as e:
            return False, str(e)

    def load_reference_model(self, path):
        """Load reference model for animation testing."""
        if self.ref_actor:
            self.ref_actor.cleanup()
            self.ref_actor.removeNode()

        try:
            self.ref_actor = Actor(str(path))
            # Don't add to render - just for animation extraction
            self.ref_anims = list(self.ref_actor.getAnimNames())
            return True, self.ref_anims
        except Exception as e:
            return False, str(e)

    def apply_reference_anims(self):
        """Apply animations from reference model to current model."""
        if not self.actor or not self.ref_actor:
            return False, "No model or reference loaded"

        if not self.ref_anims:
            return False, "Reference has no animations"

        try:
            # Get joint compatibility info
            model_joints = set(j.getName() for j in self.actor.getJoints())
            ref_joints = set(j.getName() for j in self.ref_actor.getJoints())
            common = model_joints & ref_joints

            # Load anims from reference file
            ref_path = self.ref_actor.getCurrentAnim()  # This won't work, need to track path
            # We need to store the reference path
            if hasattr(self, '_ref_path'):
                anims_dict = {name: str(self._ref_path) for name in self.ref_anims}
                self.actor.loadAnims(anims_dict)
                self.anims = list(self.actor.getAnimNames())

            compat = len(common) / len(ref_joints) * 100 if ref_joints else 0

            if self.anims:
                self.play_anim(0)

            return True, {
                'model_bones': len(model_joints),
                'ref_bones': len(ref_joints),
                'common': len(common),
                'compatibility': compat,
                'anims_loaded': len(self.ref_anims)
            }

        except Exception as e:
            return False, str(e)

    def load_reference_model_with_path(self, path):
        """Load reference model and store path."""
        self._ref_path = path
        return self.load_reference_model(path)

    def apply_anims_from_file(self, anim_source_path):
        """Apply animations from a file to current model."""
        if not self.actor:
            return False, "No model loaded", {}

        try:
            # Load temp actor to get anim names
            temp = Actor(str(anim_source_path))
            anim_names = list(temp.getAnimNames())

            if not anim_names:
                temp.cleanup()
                return False, "No animations in source", {}

            # Check joint compatibility
            model_joints = set(j.getName() for j in self.actor.getJoints())
            source_joints = set(j.getName() for j in temp.getJoints())
            common = model_joints & source_joints

            compat = len(common) / len(source_joints) * 100 if source_joints else 0

            # Load anims
            anims_dict = {name: str(anim_source_path) for name in anim_names}
            self.actor.loadAnims(anims_dict)
            self.anims = list(self.actor.getAnimNames())

            temp.cleanup()

            if self.anims:
                self.play_anim(0)

            return True, f"Loaded {len(anim_names)} animations", {
                'model_bones': len(model_joints),
                'source_bones': len(source_joints),
                'common': len(common),
                'compatibility': compat
            }

        except Exception as e:
            return False, str(e), {}

    def get_model_info(self):
        """Get info about loaded model."""
        if not self.actor:
            return None
        joints = self.actor.getJoints()
        return {
            'bones': len(joints),
            'anims': len(self.anims),
            'bone_names': [j.getName() for j in joints[:30]],
            'all_bones': [j.getName() for j in joints]
        }

    def play_anim(self, idx):
        if not self.actor or idx >= len(self.anims):
            return
        self.current_anim_idx = idx
        name = self.anims[idx]
        self.actor.stop()
        self.actor.loop(name)
        self.actor.setPlayRate(self.play_rate, name)

    def stop_anim(self):
        if self.actor:
            self.actor.stop()

    def set_play_rate(self, rate):
        self.play_rate = rate
        if self.actor and self.current_anim_idx < len(self.anims):
            self.actor.setPlayRate(rate, self.anims[self.current_anim_idx])

    def rotate_model(self, angle=45):
        if self.actor:
            self.actor.setH(self.actor.getH() + angle)

    def _update_camera(self):
        if not self.base:
            return
        from math import sin, cos, radians
        h = radians(self.cam_heading)
        p = radians(self.cam_pitch)

        x = self.cam_distance * cos(p) * sin(h)
        y = self.cam_distance * cos(p) * cos(h)
        z = self.cam_distance * sin(p) + self.look_at_z

        self.base.camera.setPos(x, y, z)
        self.base.camera.lookAt(0, 0, self.look_at_z)

    def mousePressEvent(self, event):
        self.last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.last_mouse_pos and event.buttons() & Qt.MiddleButton:
            dx = event.x() - self.last_mouse_pos.x()
            dy = event.y() - self.last_mouse_pos.y()
            self.cam_heading += dx * 0.5
            self.cam_pitch = max(-89, min(89, self.cam_pitch + dy * 0.5))
            self._update_camera()
        self.last_mouse_pos = event.pos()

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120
        self.cam_distance = max(1, min(30, self.cam_distance - delta * 0.5))
        self._update_camera()

    def get_current_anim_info(self):
        """Get info about current animation."""
        if not self.actor:
            return None
        anim = self.actor.getCurrentAnim()
        if not anim:
            return {'name': 'Stopped', 'frame': 0, 'total': 0}
        ctrl = self.actor.getAnimControl(anim)
        return {
            'name': anim,
            'frame': int(self.actor.getCurrentFrame(anim) or 0),
            'total': ctrl.getNumFrames() if ctrl else 0
        }


# ==================== CONVERTER THREAD ====================

class ConvertThread(QThread):
    finished = pyqtSignal(bool, object, str)  # success, output_path, message

    def __init__(self, tools, input_path, output_path=None):
        super().__init__()
        self.tools = tools
        self.input_path = input_path
        self.output_path = output_path

    def run(self):
        success, output_path, msg = self.tools.convert_to_bam(self.input_path, self.output_path)
        self.finished.emit(success, output_path, msg)


# ==================== MAIN WINDOW ====================

class ModelToolWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("niNE Model Tool - Mixamo Workflow")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        self.conv_tools = ConversionTools()
        self.current_file = None
        self.current_source_file = None  # Original FBX/GLB before conversion

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._apply_dark_theme()

        # Init Panda3D after window is shown
        QTimer.singleShot(100, self.viewport.init_panda3d)

        # Update timer for animation info
        self.info_timer = QTimer(self)
        self.info_timer.timeout.connect(self._update_anim_info)
        self.info_timer.start(100)

        self._log("niNE Model Tool - Mixamo Workflow Edition")
        self._log_tools_status()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # === LEFT PANEL ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Model info
        info_group = QGroupBox("Model Info")
        info_layout = QVBoxLayout(info_group)
        self.model_info_label = QLabel("No model loaded")
        self.model_info_label.setWordWrap(True)
        info_layout.addWidget(self.model_info_label)

        # Bones list
        self.bones_list = QListWidget()
        self.bones_list.setMaximumHeight(120)
        info_layout.addWidget(QLabel("Bones:"))
        info_layout.addWidget(self.bones_list)

        left_layout.addWidget(info_group)

        # === MIXAMO WORKFLOW ===
        workflow_group = QGroupBox("Mixamo Workflow")
        workflow_layout = QVBoxLayout(workflow_group)

        # Step 1: Open model
        workflow_layout.addWidget(QLabel("1. Open Mixamo model:"))
        open_model_btn = QPushButton("Open Model (FBX/GLB/BAM)")
        open_model_btn.clicked.connect(self._open_model)
        open_model_btn.setStyleSheet("background-color: #2a82da;")
        workflow_layout.addWidget(open_model_btn)

        # Step 2: Test animations
        workflow_layout.addWidget(QLabel("2. Test with base.bam anims:"))
        self.test_anims_btn = QPushButton("Apply base.bam Animations")
        self.test_anims_btn.clicked.connect(self._apply_player_anims)
        workflow_layout.addWidget(self.test_anims_btn)

        # Or load custom animation source
        load_custom_anims_btn = QPushButton("Load Custom Animation Source...")
        load_custom_anims_btn.clicked.connect(self._load_custom_anims)
        workflow_layout.addWidget(load_custom_anims_btn)

        # Compatibility result
        self.compat_label = QLabel("")
        self.compat_label.setWordWrap(True)
        workflow_layout.addWidget(self.compat_label)

        # Step 3: Export
        workflow_layout.addWidget(QLabel("3. Export to game:"))

        export_layout = QHBoxLayout()
        self.export_name = QLineEdit("player")
        self.export_name.setPlaceholderText("Model name (without .bam)")
        export_layout.addWidget(self.export_name)
        workflow_layout.addLayout(export_layout)

        self.export_btn = QPushButton("Export to Game Folder")
        self.export_btn.clicked.connect(self._export_to_game)
        self.export_btn.setStyleSheet("background-color: #28a745;")
        workflow_layout.addWidget(self.export_btn)

        self.export_path_label = QLabel(f"Target: {GAME_MODELS_PATH}")
        self.export_path_label.setWordWrap(True)
        self.export_path_label.setStyleSheet("color: #888; font-size: 10px;")
        workflow_layout.addWidget(self.export_path_label)

        left_layout.addWidget(workflow_group)

        # === ANIMATION IMPORT ===
        anim_import_group = QGroupBox("Add Animations")
        anim_import_layout = QVBoxLayout(anim_import_group)

        anim_import_layout.addWidget(QLabel("Add Mixamo animations to model:"))

        self.import_anim_btn = QPushButton("Import Animation (FBX/GLB)...")
        self.import_anim_btn.clicked.connect(self._import_animation)
        anim_import_layout.addWidget(self.import_anim_btn)

        self.anim_import_status = QLabel("")
        self.anim_import_status.setWordWrap(True)
        anim_import_layout.addWidget(self.anim_import_status)

        left_layout.addWidget(anim_import_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        # Tools status
        status_group = QGroupBox("Tools")
        status_layout = QVBoxLayout(status_group)
        self.tools_status = QLabel()
        self.tools_status.setStyleSheet("font-size: 10px;")
        status_layout.addWidget(self.tools_status)
        left_layout.addWidget(status_group)

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # === CENTER: VIEWPORT ===
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(4)

        self.viewport = Panda3DWidget()
        center_layout.addWidget(self.viewport, stretch=1)

        # Console
        console_group = QGroupBox("Console")
        console_layout = QVBoxLayout(console_group)
        console_layout.setContentsMargins(4, 4, 4, 4)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(100)
        self.console.setFont(QFont("Monospace", 9))
        console_layout.addWidget(self.console)
        center_layout.addWidget(console_group)

        splitter.addWidget(center_widget)

        # === RIGHT PANEL: ANIMATIONS ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        anim_group = QGroupBox("Animations")
        anim_layout = QVBoxLayout(anim_group)

        self.anim_list = QListWidget()
        self.anim_list.itemDoubleClicked.connect(self._on_anim_double_click)
        anim_layout.addWidget(self.anim_list)

        # Current anim info
        self.anim_info_label = QLabel("No animation")
        anim_layout.addWidget(self.anim_info_label)

        # Controls
        ctrl_layout = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self._play_selected)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.viewport.stop_anim)
        ctrl_layout.addWidget(self.play_btn)
        ctrl_layout.addWidget(self.stop_btn)
        anim_layout.addLayout(ctrl_layout)

        # Speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(10, 300)
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self._on_speed_change)
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("1.00x")
        speed_layout.addWidget(self.speed_label)
        anim_layout.addLayout(speed_layout)

        right_layout.addWidget(anim_group)

        # View controls
        view_group = QGroupBox("View")
        view_layout = QVBoxLayout(view_group)

        rotate_layout = QHBoxLayout()
        rotate_left = QPushButton("<< 45")
        rotate_left.clicked.connect(lambda: self.viewport.rotate_model(-45))
        rotate_right = QPushButton("45 >>")
        rotate_right.clicked.connect(lambda: self.viewport.rotate_model(45))
        rotate_layout.addWidget(rotate_left)
        rotate_layout.addWidget(rotate_right)
        view_layout.addLayout(rotate_layout)

        reset_cam = QPushButton("Reset Camera")
        reset_cam.clicked.connect(self._reset_camera)
        view_layout.addWidget(reset_cam)

        right_layout.addWidget(view_group)

        right_layout.addStretch()
        splitter.addWidget(right_panel)

        # Splitter proportions
        splitter.setSizes([280, 650, 250])

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Open FBX/GLB model to start")

    def _setup_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open Model...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_model)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        export_action = QAction("Export to Game...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_to_game)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("View")

        reset_cam = QAction("Reset Camera", self)
        reset_cam.triggered.connect(self._reset_camera)
        view_menu.addAction(reset_cam)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        open_btn = QPushButton("Open Model")
        open_btn.clicked.connect(self._open_model)
        toolbar.addWidget(open_btn)

        toolbar.addSeparator()

        test_btn = QPushButton("Test base.bam Anims")
        test_btn.clicked.connect(self._apply_player_anims)
        toolbar.addWidget(test_btn)

        toolbar.addSeparator()

        export_btn = QPushButton("Export to Game")
        export_btn.clicked.connect(self._export_to_game)
        export_btn.setStyleSheet("background-color: #28a745;")
        toolbar.addWidget(export_btn)

    def _apply_dark_theme(self):
        """Apply dark theme."""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(45, 45, 48))
        palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
        palette.setColor(QPalette.Base, QColor(30, 30, 32))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 48))
        palette.setColor(QPalette.ToolTipBase, QColor(220, 220, 220))
        palette.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
        palette.setColor(QPalette.Text, QColor(220, 220, 220))
        palette.setColor(QPalette.Button, QColor(45, 45, 48))
        palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))
        palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        self.setPalette(palette)

        self.setStyleSheet("""
            QMainWindow { background-color: #2d2d30; }
            QGroupBox {
                border: 1px solid #3e3e42;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            QPushButton {
                background-color: #3e3e42;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 60px;
            }
            QPushButton:hover { background-color: #505054; }
            QPushButton:pressed { background-color: #2a82da; }
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #3e3e42;
                border-radius: 4px;
            }
            QListWidget::item:selected { background-color: #2a82da; }
            QListWidget::item:hover { background-color: #3e3e42; }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3e3e42;
                border-radius: 4px;
            }
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 4px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #3e3e42;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #2a82da;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QProgressBar {
                border: 1px solid #3e3e42;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk { background-color: #2a82da; }
            QMenuBar { background-color: #2d2d30; }
            QMenuBar::item:selected { background-color: #3e3e42; }
            QMenu { background-color: #2d2d30; border: 1px solid #3e3e42; }
            QMenu::item:selected { background-color: #2a82da; }
            QToolBar { background-color: #2d2d30; border: none; spacing: 4px; }
            QStatusBar { background-color: #007acc; color: white; }
        """)

    def _log(self, message):
        """Add message to console."""
        self.console.append(message)
        print(message)

    def _log_tools_status(self):
        """Log tools status."""
        status = self.conv_tools.get_status()
        lines = []
        for tool, available in status.items():
            icon = "+" if available else "-"
            lines.append(f"{icon} {tool}")

        self.tools_status.setText('\n'.join(lines))

        if not status.get('gltf2bam'):
            self._log("WARNING: gltf2bam not found!")
            self._log("Install: pip install panda3d-gltf")
        elif status.get('blender'):
            self._log("Ready! FBX and GLB supported")
            if self.conv_tools.blender_path:
                self._log(f"Blender: {self.conv_tools.blender_path.parent.name}")
        else:
            self._log("GLB supported. FBX needs Blender installed.")

    def _open_model(self):
        """Open model file - supports FBX/GLB/GLTF/BAM."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Model",
            str(Path(project_root)),
            "3D Models (*.fbx *.glb *.gltf *.bam *.egg);;All Files (*)"
        )

        if path:
            self._load_model_file(path)

    def _load_model_file(self, path):
        """Load model, converting if necessary."""
        path = Path(path)
        suffix = path.suffix.lower()

        self._log(f"Opening: {path.name}")
        self.status_bar.showMessage(f"Loading {path.name}...")
        self.current_source_file = path

        # Auto-set export name from filename
        self.export_name.setText(path.stem)

        # Check if conversion needed
        if suffix in ('.bam', '.egg'):
            # Direct load
            self._load_model_into_viewport(str(path))
        elif self.conv_tools.can_convert(suffix):
            # Need to convert
            if suffix == '.fbx':
                self._log(f"Converting FBX -> GLB -> BAM...")
            else:
                self._log(f"Converting {suffix} to BAM...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)

            self.conv_thread = ConvertThread(self.conv_tools, str(path))
            self.conv_thread.finished.connect(self._on_convert_for_view_finished)
            self.conv_thread.start()
        else:
            if suffix == '.fbx' and not self.conv_tools.can_convert_fbx():
                QMessageBox.warning(self, "Error",
                    "FBX conversion not available.\n\n"
                    "Blender is required for FBX conversion.")
            else:
                QMessageBox.warning(self, "Error", f"Cannot open {suffix} files.\nSupported: FBX, GLB, GLTF, BAM, EGG")

    def _on_convert_for_view_finished(self, success, output_path, message):
        """Handle conversion finished for viewing."""
        self.progress_bar.setVisible(False)

        if success and output_path:
            self._log(f"Conversion OK: {message}")
            self._load_model_into_viewport(str(output_path))
        else:
            self._log(f"Conversion FAILED: {message}")
            self.status_bar.showMessage("Conversion failed")
            QMessageBox.warning(self, "Conversion Failed", message)

    def _load_model_into_viewport(self, path):
        """Load model into viewport."""
        success, result = self.viewport.load_model(path)

        if success:
            self.current_file = path
            anims = result

            # Update animation list
            self.anim_list.clear()
            for i, anim in enumerate(anims):
                item = QListWidgetItem(f"{i+1}. {anim}")
                self.anim_list.addItem(item)

            # Update model info
            info = self.viewport.get_model_info()
            if info:
                source_name = self.current_source_file.name if self.current_source_file else Path(path).name
                self.model_info_label.setText(
                    f"File: {source_name}\n"
                    f"Bones: {info['bones']}\n"
                    f"Animations: {info['anims']}"
                )

                self.bones_list.clear()
                for bone in info['bone_names']:
                    self.bones_list.addItem(bone)
                if info['bones'] > 30:
                    self.bones_list.addItem(f"... +{info['bones'] - 30} more")

            self._log(f"Loaded: {Path(path).name} ({info['bones']} bones, {info['anims']} anims)")
            self.status_bar.showMessage(f"Loaded: {Path(path).name}")

        else:
            self._log(f"Error: {result}")
            self.status_bar.showMessage("Load failed")
            QMessageBox.warning(self, "Error", f"Failed to load model:\n{result}")

    def _apply_player_anims(self):
        """Apply animations from base.bam to current model."""
        if not self.viewport.actor:
            QMessageBox.warning(self, "Error", "Load a model first!")
            return

        if not PLAYER_MODEL_PATH.exists():
            QMessageBox.warning(self, "Error", f"base.bam not found at:\n{PLAYER_MODEL_PATH}")
            return

        self._log(f"Loading animations from base.bam...")
        self._apply_anims_from_path(PLAYER_MODEL_PATH)

    def _load_custom_anims(self):
        """Load animations from custom file."""
        if not self.viewport.actor:
            QMessageBox.warning(self, "Error", "Load a model first!")
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Animation Source",
            str(GAME_MODELS_PATH),
            "3D Models (*.fbx *.glb *.gltf *.bam *.egg);;All Files (*)"
        )

        if path:
            path = Path(path)
            suffix = path.suffix.lower()

            if self.conv_tools.can_convert(suffix) and suffix not in ('.bam', '.egg'):
                # Need to convert first
                self._log(f"Converting {path.name} for animations...")
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)

                self._pending_anim_source = True
                self.conv_thread = ConvertThread(self.conv_tools, str(path))
                self.conv_thread.finished.connect(self._on_anim_source_converted)
                self.conv_thread.start()
            elif suffix in ('.bam', '.egg'):
                self._apply_anims_from_path(path)
            else:
                QMessageBox.warning(self, "Error", f"Cannot convert {suffix} files")

    def _on_anim_source_converted(self, success, output_path, message):
        """Handle animation source conversion."""
        self.progress_bar.setVisible(False)
        self._pending_anim_source = False

        if success and output_path:
            self._apply_anims_from_path(output_path)
        else:
            self._log(f"Conversion failed: {message}")
            QMessageBox.warning(self, "Error", f"Failed to convert animation source:\n{message}")

    def _apply_anims_from_path(self, path):
        """Apply animations from path to current model."""
        success, msg, info = self.viewport.apply_anims_from_file(path)

        if success:
            # Update anim list
            self.anim_list.clear()
            for i, anim in enumerate(self.viewport.anims):
                self.anim_list.addItem(f"{i+1}. {anim}")

            # Show compatibility
            compat = info.get('compatibility', 0)
            compat_text = (
                f"Bones: {info['model_bones']} model / {info['source_bones']} source\n"
                f"Common: {info['common']}\n"
                f"Compatibility: {compat:.0f}%"
            )

            if compat >= 90:
                compat_text += "\n\nEXCELLENT - Rigs match!"
                self.compat_label.setStyleSheet("color: #28a745;")
            elif compat >= 70:
                compat_text += "\n\nGOOD - Most bones match"
                self.compat_label.setStyleSheet("color: #ffc107;")
            else:
                compat_text += "\n\nPOOR - Rigs differ"
                self.compat_label.setStyleSheet("color: #dc3545;")

            self.compat_label.setText(compat_text)
            self._log(f"Applied animations. Compatibility: {compat:.0f}%")
        else:
            self.compat_label.setText(f"Error: {msg}")
            self.compat_label.setStyleSheet("color: #dc3545;")
            self._log(f"Error: {msg}")

    def _export_to_game(self):
        """Export current model to game folder."""
        if not self.current_file and not self.current_source_file:
            QMessageBox.warning(self, "Error", "No model loaded!")
            return

        export_name = self.export_name.text().strip()
        if not export_name:
            QMessageBox.warning(self, "Error", "Enter export name!")
            return

        # Ensure .bam extension
        if not export_name.endswith('.bam'):
            export_name += '.bam'

        target_path = GAME_MODELS_PATH / export_name

        # Check if file exists
        if target_path.exists():
            reply = QMessageBox.question(
                self, "Overwrite?",
                f"{export_name} already exists.\nOverwrite?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Get source file (converted BAM)
        source_path = self.current_file
        if not source_path or not Path(source_path).exists():
            QMessageBox.warning(self, "Error", "Converted model not found!")
            return

        try:
            # Create target directory if needed
            GAME_MODELS_PATH.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source_path, target_path)

            self._log(f"Exported: {target_path}")
            self.status_bar.showMessage(f"Exported to {export_name}")
            QMessageBox.information(self, "Success", f"Model exported to:\n{target_path}")

        except Exception as e:
            self._log(f"Export failed: {e}")
            QMessageBox.warning(self, "Error", f"Export failed:\n{e}")

    def _import_animation(self):
        """Import animation from Mixamo FBX/GLB into current model."""
        if not self.viewport.actor:
            QMessageBox.warning(self, "Error", "Load a model first!")
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Mixamo Animation",
            str(Path.home() / "Downloads"),
            "3D Files (*.fbx *.glb *.gltf);;BAM Files (*.bam);;All Files (*)"
        )

        if not path:
            return

        path = Path(path)
        suffix = path.suffix.lower()

        self._log(f"Importing animation: {path.name}")

        if self.conv_tools.can_convert(suffix) and suffix not in ('.bam', '.egg'):
            # Convert first
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)

            self._pending_anim_import = path.stem
            self.conv_thread = ConvertThread(self.conv_tools, str(path))
            self.conv_thread.finished.connect(self._on_anim_import_converted)
            self.conv_thread.start()
        elif suffix in ('.bam', '.egg'):
            self._do_anim_import(path, path.stem)
        else:
            QMessageBox.warning(self, "Error", f"Cannot convert {suffix} files")

    def _on_anim_import_converted(self, success, output_path, message):
        """Handle animation import conversion."""
        self.progress_bar.setVisible(False)

        if success and output_path:
            anim_name = getattr(self, '_pending_anim_import', 'imported')
            self._do_anim_import(output_path, anim_name)
        else:
            self._log(f"Conversion failed: {message}")
            self.anim_import_status.setText(f"Failed: {message}")
            self.anim_import_status.setStyleSheet("color: #dc3545;")

    def _do_anim_import(self, path, anim_name):
        """Actually import the animation."""
        try:
            # Load the source to get animation
            temp = Actor(str(path))
            source_anims = list(temp.getAnimNames())

            if not source_anims:
                temp.cleanup()
                self.anim_import_status.setText("No animations found in file")
                self.anim_import_status.setStyleSheet("color: #dc3545;")
                return

            # Use original name or first anim name
            if source_anims[0] and source_anims[0] != 'pose':
                anim_name = source_anims[0]

            # Load animation into current model
            self.viewport.actor.loadAnims({anim_name: str(path)})
            self.viewport.anims = list(self.viewport.actor.getAnimNames())

            # Update list
            self.anim_list.clear()
            for i, anim in enumerate(self.viewport.anims):
                self.anim_list.addItem(f"{i+1}. {anim}")

            temp.cleanup()

            self.anim_import_status.setText(f"Imported: {anim_name}")
            self.anim_import_status.setStyleSheet("color: #28a745;")
            self._log(f"Animation imported: {anim_name}")

            # Play the new animation
            idx = self.viewport.anims.index(anim_name) if anim_name in self.viewport.anims else -1
            if idx >= 0:
                self.viewport.play_anim(idx)

        except Exception as e:
            self.anim_import_status.setText(f"Error: {e}")
            self.anim_import_status.setStyleSheet("color: #dc3545;")
            self._log(f"Import error: {e}")

    def _on_anim_double_click(self, item):
        """Play animation on double click."""
        idx = self.anim_list.row(item)
        self.viewport.play_anim(idx)

    def _play_selected(self):
        """Play selected animation."""
        item = self.anim_list.currentItem()
        if item:
            idx = self.anim_list.row(item)
            self.viewport.play_anim(idx)

    def _on_speed_change(self, value):
        """Handle speed slider change."""
        rate = value / 100.0
        self.viewport.set_play_rate(rate)
        self.speed_label.setText(f"{rate:.2f}x")

    def _update_anim_info(self):
        """Update animation info label."""
        info = self.viewport.get_current_anim_info()
        if info:
            self.anim_info_label.setText(
                f"{info['name']} - Frame {info['frame']}/{info['total']}"
            )

    def _reset_camera(self):
        """Reset camera to default."""
        self.viewport.cam_distance = 5
        self.viewport.cam_heading = 180
        self.viewport.cam_pitch = 15
        self.viewport._update_camera()

    def _show_about(self):
        QMessageBox.about(
            self,
            "About niNE Model Tool",
            "niNE Model Tool - Mixamo Workflow Edition\n\n"
            "Workflow:\n"
            "1. Download model from Mixamo (FBX or GLB)\n"
            "2. Open here - auto converts to BAM\n"
            "3. Test base.bam animations\n"
            "4. Export to game folder\n\n"
            "Supported: FBX, GLB, GLTF, BAM, EGG\n"
            "Conversion: FBX -> GLB -> BAM\n\n"
            "Controls:\n"
            "- Middle mouse drag - Rotate camera\n"
            "- Mouse wheel - Zoom\n"
            "- Double-click animation - Play"
        )

    def closeEvent(self, event):
        """Clean up on close."""
        if hasattr(self, 'viewport') and self.viewport.base:
            self.viewport.update_timer.stop()
        # Clean temp files
        self.conv_tools.cleanup_temp()
        event.accept()


# ==================== MAIN ====================

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("niNE Model Tool")

    window = ModelToolWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
