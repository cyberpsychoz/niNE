#!/usr/bin/env python3
"""
niNE Model Tool - Professional 3D model viewer and converter.
Built with PyQt5 + Panda3D.

Run: python tools/model_tool.py
"""

import sys
import os
import subprocess
import shutil
import platform
from pathlib import Path

# Project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)
sys.path.insert(0, project_root)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QTreeView, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QSlider, QFileDialog, QMessageBox,
    QTextEdit, QGroupBox, QFormLayout, QLineEdit, QProgressBar,
    QToolBar, QAction, QStatusBar, QFrame, QSizePolicy, QStyle,
    QFileSystemModel, QAbstractItemView
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDir
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon

# Panda3D imports
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from panda3d.core import (
    loadPrcFileData, getModelPath, Filename,
    WindowProperties, AmbientLight, DirectionalLight
)

# Configure Panda3D before ShowBase init
loadPrcFileData('', 'window-type none')  # Start without window
loadPrcFileData('', 'audio-library-name null')
getModelPath().appendDirectory(Filename.fromOsSpecific(project_root))


# ==================== CONVERSION TOOLS ====================

class ConversionTools:
    """Detect and run conversion utilities."""

    def __init__(self):
        self.system = platform.system()
        self.tools = {}
        self._detect_tools()

    def _detect_tools(self):
        self.tools['blend2bam'] = shutil.which('blend2bam') is not None
        self.tools['egg2bam'] = shutil.which('egg2bam') is not None
        self.tools['bam2egg'] = shutil.which('bam2egg') is not None

        blender = 'blender.exe' if self.system == 'Windows' else 'blender'
        self.tools['blender'] = shutil.which(blender) is not None

        try:
            import panda3d_gltf
            self.tools['panda3d_gltf'] = True
        except ImportError:
            self.tools['panda3d_gltf'] = False

    def get_status(self):
        return self.tools.copy()

    def can_convert_fbx(self):
        return self.tools.get('blend2bam', False)

    def convert_to_bam(self, input_path, output_path=None):
        """Convert file to BAM format. Returns (success, message)."""
        input_path = Path(input_path)
        suffix = input_path.suffix.lower()

        if output_path is None:
            output_path = input_path.with_suffix('.bam')
        else:
            output_path = Path(output_path)

        if suffix == '.bam':
            return True, "File is already BAM format"

        if suffix == '.egg':
            if not self.tools.get('egg2bam'):
                return False, "egg2bam not found"
            try:
                result = subprocess.run(
                    ['egg2bam', '-o', str(output_path), str(input_path)],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    return True, f"Converted: {output_path.name}"
                return False, f"Error: {result.stderr}"
            except Exception as e:
                return False, str(e)

        if suffix in ('.fbx', '.blend', '.obj', '.dae', '.gltf', '.glb'):
            if not self.tools.get('blend2bam'):
                return False, "blend2bam not found. Install: pip install panda3d-blend2bam"
            try:
                result = subprocess.run(
                    ['blend2bam', str(input_path), str(output_path)],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    return True, f"Converted: {output_path.name}"
                return False, f"Error: {result.stderr or result.stdout}"
            except subprocess.TimeoutExpired:
                return False, "Conversion timeout (>120s)"
            except Exception as e:
                return False, str(e)

        return False, f"Unsupported format: {suffix}"


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

        # Create ShowBase
        self.base = ShowBase()

        # Get window handle and attach Panda3D to this widget
        wp = WindowProperties()
        wp.setParentWindow(int(self.winId()))
        wp.setOrigin(0, 0)
        wp.setSize(self.width(), self.height())

        self.base.openDefaultWindow(props=wp)
        self.base.setBackgroundColor(0.2, 0.2, 0.25)
        self.base.disableMouse()

        # Setup lighting
        ambient = AmbientLight("ambient")
        ambient.setColor((0.4, 0.4, 0.4, 1))
        self.base.render.setLight(self.base.render.attachNewNode(ambient))

        directional = DirectionalLight("directional")
        directional.setColor((0.8, 0.8, 0.8, 1))
        dir_np = self.base.render.attachNewNode(directional)
        dir_np.setHpr(45, -45, 0)
        self.base.render.setLight(dir_np)

        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._panda_step)
        self.update_timer.start(16)  # ~60 FPS

        self._update_camera()

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

        try:
            self.actor = Actor(str(path))
            self.actor.reparentTo(self.base.render)

            # Get animations
            self.anims = self.actor.getAnimNames()

            # Compute bounds for camera
            bounds = self.actor.getTightBounds()
            if bounds:
                min_pt, max_pt = bounds
                height = max_pt.z - min_pt.z
                self.look_at_z = (max_pt.z + min_pt.z) / 2
                self.cam_distance = max(height * 3, 5)

            self._update_camera()

            # Play first animation
            if self.anims:
                self.play_anim(0)

            return True, self.anims

        except Exception as e:
            return False, str(e)

    def load_external_anims(self, source_path):
        """Load animations from another file."""
        if not self.actor:
            return False, "No model loaded", {}

        try:
            temp = Actor(str(source_path))
            anim_names = temp.getAnimNames()

            if not anim_names:
                temp.cleanup()
                return False, "No animations in source", {}

            # Load anims
            anims_dict = {name: str(source_path) for name in anim_names}
            self.actor.loadAnims(anims_dict)
            self.anims = self.actor.getAnimNames()

            # Check compatibility
            model_joints = set(j.getName() for j in self.actor.getJoints())
            source_joints = set(j.getName() for j in temp.getJoints())
            common = model_joints & source_joints

            compat = len(common) / len(source_joints) * 100 if source_joints else 0

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
            'bone_names': [j.getName() for j in joints[:20]]
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
    finished = pyqtSignal(bool, str)

    def __init__(self, tools, input_path, output_path=None):
        super().__init__()
        self.tools = tools
        self.input_path = input_path
        self.output_path = output_path

    def run(self):
        success, msg = self.tools.convert_to_bam(self.input_path, self.output_path)
        self.finished.emit(success, msg)


# ==================== MAIN WINDOW ====================

class ModelToolWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("niNE Model Tool")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        self.conv_tools = ConversionTools()
        self.current_file = None

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

        self._log("niNE Model Tool started")
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

        # Tabs
        self.tabs = QTabWidget()
        left_layout.addWidget(self.tabs)

        # Tab 1: Model Info
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)

        self.model_info_label = QLabel("No model loaded")
        self.model_info_label.setWordWrap(True)
        info_layout.addWidget(self.model_info_label)

        # Bones list
        bones_group = QGroupBox("Bones")
        bones_layout = QVBoxLayout(bones_group)
        self.bones_list = QListWidget()
        self.bones_list.setMaximumHeight(150)
        bones_layout.addWidget(self.bones_list)
        info_layout.addWidget(bones_group)

        info_layout.addStretch()
        self.tabs.addTab(info_tab, "Model")

        # Tab 2: Converter
        conv_tab = QWidget()
        conv_layout = QVBoxLayout(conv_tab)

        conv_layout.addWidget(QLabel("Convert FBX/GLTF/OBJ to BAM"))

        # Status
        status_group = QGroupBox("Tools Status")
        status_layout = QVBoxLayout(status_group)
        self.tools_status = QLabel()
        status_layout.addWidget(self.tools_status)
        conv_layout.addWidget(status_group)

        # Convert buttons
        self.convert_btn = QPushButton("Select and Convert File...")
        self.convert_btn.clicked.connect(self._convert_file)
        conv_layout.addWidget(self.convert_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        conv_layout.addWidget(self.progress_bar)

        conv_layout.addStretch()
        self.tabs.addTab(conv_tab, "Converter")

        # Tab 3: Rig Check
        rig_tab = QWidget()
        rig_layout = QVBoxLayout(rig_tab)

        rig_layout.addWidget(QLabel("Load animations from another model\nto check rig compatibility:"))

        self.load_anims_btn = QPushButton("Load Animations From...")
        self.load_anims_btn.clicked.connect(self._load_external_anims)
        rig_layout.addWidget(self.load_anims_btn)

        self.rig_result = QLabel("")
        self.rig_result.setWordWrap(True)
        rig_layout.addWidget(self.rig_result)

        rig_layout.addStretch()
        self.tabs.addTab(rig_tab, "Rig Check")

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
        self.console.setMaximumHeight(120)
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

        # Rotate
        rotate_btn = QPushButton("Rotate Model 45°")
        rotate_btn.clicked.connect(lambda: self.viewport.rotate_model(45))
        right_layout.addWidget(rotate_btn)

        right_layout.addStretch()
        splitter.addWidget(right_panel)

        # Splitter proportions
        splitter.setSizes([250, 700, 250])

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _setup_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open Model...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_model)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        convert_action = QAction("Convert File...", self)
        convert_action.triggered.connect(self._convert_file)
        file_menu.addAction(convert_action)

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

        convert_btn = QPushButton("Convert")
        convert_btn.clicked.connect(self._convert_file)
        toolbar.addWidget(convert_btn)

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

        # Stylesheet
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
                min-width: 80px;
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
            QTabWidget::pane { border: 1px solid #3e3e42; }
            QTabBar::tab {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                padding: 6px 12px;
            }
            QTabBar::tab:selected { background-color: #3e3e42; }
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
            icon = "✓" if available else "✗"
            lines.append(f"{icon} {tool}")

        self.tools_status.setText('\n'.join(lines))

        self._log(f"System: {platform.system()}")
        for tool, available in status.items():
            self._log(f"  {tool}: {'OK' if available else 'not found'}")

    def _open_model(self):
        """Open model file dialog."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Model",
            str(Path(project_root) / "nine" / "assets" / "models"),
            "3D Models (*.bam *.egg);;All Files (*)"
        )

        if path:
            self._load_model(path)

    def _load_model(self, path):
        """Load model into viewport."""
        self._log(f"Loading: {path}")
        self.status_bar.showMessage(f"Loading {Path(path).name}...")

        success, result = self.viewport.load_model(path)

        if success:
            self.current_file = path
            anims = result

            # Update animation list
            self.anim_list.clear()
            for i, anim in enumerate(anims):
                item = QListWidgetItem(f"[{i+1}] {anim}")
                self.anim_list.addItem(item)

            # Update model info
            info = self.viewport.get_model_info()
            if info:
                self.model_info_label.setText(
                    f"File: {Path(path).name}\n"
                    f"Bones: {info['bones']}\n"
                    f"Animations: {info['anims']}"
                )

                self.bones_list.clear()
                for bone in info['bone_names']:
                    self.bones_list.addItem(bone)
                if info['bones'] > 20:
                    self.bones_list.addItem(f"... and {info['bones'] - 20} more")

            self._log(f"Loaded: {Path(path).name} ({info['bones']} bones, {info['anims']} anims)")
            self.status_bar.showMessage(f"Loaded: {Path(path).name}")

        else:
            self._log(f"Error: {result}")
            self.status_bar.showMessage("Load failed")
            QMessageBox.warning(self, "Error", f"Failed to load model:\n{result}")

    def _convert_file(self):
        """Open convert file dialog."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Convert",
            str(Path(project_root)),
            "Convertible Files (*.fbx *.blend *.gltf *.glb *.obj *.dae *.egg);;All Files (*)"
        )

        if not path:
            return

        output_path = Path(path).with_suffix('.bam')

        self._log(f"Converting: {path}")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.convert_btn.setEnabled(False)

        self.conv_thread = ConvertThread(self.conv_tools, path, output_path)
        self.conv_thread.finished.connect(self._on_convert_finished)
        self.conv_thread.start()

    def _on_convert_finished(self, success, message):
        """Handle conversion finished."""
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)

        if success:
            self._log(f"Success: {message}")
            self.status_bar.showMessage("Conversion complete")

            reply = QMessageBox.question(
                self, "Conversion Complete",
                f"{message}\n\nLoad converted model?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Extract path from message
                bam_path = Path(project_root) / message.replace("Converted: ", "")
                if bam_path.exists():
                    self._load_model(str(bam_path))
        else:
            self._log(f"Failed: {message}")
            self.status_bar.showMessage("Conversion failed")
            QMessageBox.warning(self, "Conversion Failed", message)

    def _load_external_anims(self):
        """Load animations from external file."""
        if not self.viewport.actor:
            QMessageBox.warning(self, "Error", "Load a model first!")
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Animation Source",
            str(Path(project_root) / "nine" / "assets" / "models"),
            "3D Models (*.bam *.egg);;All Files (*)"
        )

        if not path:
            return

        self._log(f"Loading animations from: {path}")

        success, msg, info = self.viewport.load_external_anims(path)

        if success:
            # Update anim list
            self.anim_list.clear()
            for i, anim in enumerate(self.viewport.anims):
                self.anim_list.addItem(f"[{i+1}] {anim}")

            # Show compatibility
            result_text = (
                f"Loaded {len(self.viewport.anims)} animations\n\n"
                f"Model bones: {info['model_bones']}\n"
                f"Source bones: {info['source_bones']}\n"
                f"Common: {info['common']}\n\n"
                f"Compatibility: {info['compatibility']:.0f}%"
            )

            compat = info['compatibility']
            if compat >= 90:
                result_text += "\n\n✓ EXCELLENT - Rigs match!"
            elif compat >= 70:
                result_text += "\n\n~ GOOD - Most bones match"
            else:
                result_text += "\n\n✗ POOR - Rigs differ significantly"

            self.rig_result.setText(result_text)
            self._log(f"Rig compatibility: {compat:.0f}%")
        else:
            self.rig_result.setText(f"Error: {msg}")
            self._log(f"Error: {msg}")

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
            "niNE Model Tool v1.0\n\n"
            "Professional 3D model viewer and converter.\n"
            "Built with PyQt5 + Panda3D.\n\n"
            "Controls:\n"
            "• Middle mouse drag - Rotate camera\n"
            "• Mouse wheel - Zoom\n"
            "• Double-click animation - Play"
        )

    def closeEvent(self, event):
        """Clean up on close."""
        if hasattr(self, 'viewport') and self.viewport.base:
            self.viewport.update_timer.stop()
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
