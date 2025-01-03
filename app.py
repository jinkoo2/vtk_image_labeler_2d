import sys
import numpy as np
import SimpleITK as sitk
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QFileDialog, QVBoxLayout, QSlider, QPushButton, QLabel, QWidget, QMenuBar, QAction, QToolBar, QDockWidget, QListWidget, QHBoxLayout, QPushButton, QCheckBox, QLineEdit
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QIcon
import cv2

import os

from segmentation_list_manager import SegmentationListManager
from point_list_manager import PointListManager
### helper functions
import numpy as np

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QLabel, QListWidgetItem, QColorDialog
from labeled_slider import LabeledSlider


class ImageWindowLevelRenderer:
    def __init__(self) -> None:
        pass

    def apply_window_level(self, image_array, level, width):
        """
        Adjust the DICOM image brightness and contrast using window level and width.
        :param image: NumPy array of the image.
        :param level: Window level (center).
        :param width: Window width.
        :return: Window-leveled image as NumPy array.
        """
        min_intensity = level - (width / 2)
        max_intensity = level + (width / 2)

        # Clamp pixel values
        adjusted = np.clip(image_array, min_intensity, max_intensity)

        # Normalize to 0-255 for display
        adjusted = ((adjusted - min_intensity) / (max_intensity - min_intensity) * 255).astype(np.uint8)
        
        return adjusted
    
    def render(self, image_array, level, width):
        adjusted_image = self.apply_window_level(image_array, level, width)
        return adjusted_image
    
class GraphicsView2D(QGraphicsView):
    def __init__(self, parent_viewer, parent=None):
        super().__init__(parent)
        
        self.parent_viewer = parent_viewer  # Reference to the DicomViewer instance

        self.setMouseTracking(True)  # Enable mouse tracking
        self.setInteractive(True) # Enable mouse interaction drgging
        
        self.zoom_factor = 1.0  # Initial zoom level
        self.zoom_step = 0.1  # Amount of zoom per scroll
        self.min_zoom = 0.5  # Minimum zoom factor
        self.max_zoom = 5.0  # Maximum zoom factor

        # point data
        self.points = []  # List of Point objects
        self.active_point_index = None  # Index of the active point
        self.dragging_point = False  # State for dragging

        # renderers
        self.image_window_level_renderer = ImageWindowLevelRenderer()

    def get_managers(self):
        return self.parent_viewer.managers

    def get_renderers(self):
        return [manager.renderer for manager in self.get_managers()]

    def get_image_array(self):
        return self.parent_viewer.image_array

    def point_in_image_boundary(self, x, y):
        
        if self.get_image_array() is None:
            return False

        if 0 <= x < self.get_image_array().shape[1] and 0 <= y < self.get_image_array().shape[0]:
            return True
        else:
            return False

    def wheelEvent(self, event):
        # Check if the Left Control key is pressed
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            # Determine the scroll direction
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()

    def print_status(self, msg):
        self.parent_viewer.print_status(msg)

    def zoom_in(self):
        """Zoom in the view."""
        if self.zoom_factor < self.max_zoom:
            self.zoom_factor += self.zoom_step
            self.scale(1 + self.zoom_step, 1 + self.zoom_step)
            self.print_status(f"Zoom: {self.zoom_factor:.2f}x")

    def zoom_out(self):
        """Zoom out the view."""
        if self.zoom_factor > self.min_zoom:
            self.zoom_factor -= self.zoom_step
            self.scale(1 - self.zoom_step, 1 - self.zoom_step)
            self.print_status(f"Zoom: {self.zoom_factor:.2f}x")

    def zoom_reset(self):
        """Reset zoom to the default level."""
        self.resetTransform()
        self.zoom_factor = 1.0
        self.print_status(f"Zoom: {self.zoom_factor:.2f}x")


    def render_layers(self, brush_x=None, brush_y=None):
        """Render the image and layers, including a brush indicator if provided."""
        if self.get_image_array() is None:
            return

        # Apply window-level adjustments to the base image
        level = self.parent_viewer.window_level_slider.value()
        width = self.parent_viewer.window_width_slider.value()
        image_uchar = self.image_window_level_renderer.render(self.get_image_array(), level, width)

        # conver to rgb image
        overlay_rgb = cv2.cvtColor(image_uchar, cv2.COLOR_GRAY2RGB)
    
        # Render Segmentation Layers
        for renderer in self.get_renderers():
            renderer.render_rgb(overlay_rgb, brush_x, brush_y)
        
        # Convert the final overlay image to QImage and display it
        height, width, channel = overlay_rgb.shape
        qimage = QImage(overlay_rgb.data, width, height, 3 * width, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        self.scene().clear()
        self.scene().addPixmap(pixmap)

    def update(self):
        self.render_layers()
    
    def mousePressEvent(self, event):
        if self.get_image_array() is None:
            return 

        for renderer in self.get_renderers():
            renderer.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        image_array = self.get_image_array()

        if image_array is None:
            return

        # Map mouse position to the scene
        scene_pos = self.mapToScene(event.pos())
        image_x = int(scene_pos.x())
        image_y = int(scene_pos.y())

        # Ensure coordinates are within the image bounds
        if self.point_in_image_boundary(image_x,image_y):

            # Render layers with the brush indicator
            self.render_layers(image_x, image_y)

            # Update the status bar with the current mouse position and pixel value
            pixel_value = image_array[image_y, image_x]
            self.parent_viewer.status_bar.showMessage(f"Mouse: ({image_x}, {image_y}) | Pixel Value: {pixel_value}")

        for renderer in self.get_renderers():
            renderer.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.get_image_array() is None:
            return 
        
        for renderer in self.get_renderers():
            renderer.mouseReleaseEvent(event)
    
    
    def add_ruler(self):
        from PyQt5.QtCore import QPointF
        from ruler_widget import RulerWidget
        
        """Add a ruler widget at the center of the scene."""
        if self.scene():
            scene_center = self.sceneRect().center()
            start = QPointF(scene_center.x() - 50, scene_center.y())
            end = QPointF(scene_center.x() + 50, scene_center.y())
            self.ruler_widget = RulerWidget(start, end, self.scene())
            self.scene().addItem(self.ruler_widget)

    def toggle_ruler(self):
        """Toggle ruler visibility."""
        if hasattr(self, "ruler_widget"):
            self.ruler_widget.setVisible(not self.ruler_widget.isVisible())
            self.ruler_widget.start_handle.setVisible(self.ruler_widget.isVisible())
            self.ruler_widget.end_handle.setVisible(self.ruler_widget.isVisible())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.image_array = None

        self.init_ui()

        self.managers = []

        # segmenation list manager
        self.segmentation_list_manager = SegmentationListManager(self)
        self.segmentation_list_manager.init_ui()
        self.managers.append(self.segmentation_list_manager)

        # point list manager
        self.point_list_manager = PointListManager(self)
        self.point_list_manager.init_ui()
        self.managers.append(self.point_list_manager)
            
    def init_ui(self):
        self.setWindowTitle("Image Labeler 2D")
        self.setGeometry(100, 100, 1024, 786)

        self.main_widget = QWidget()
        self.layout = QVBoxLayout()

        # Graphics View
        self.graphics_view = GraphicsView2D(self, self)
        self.graphics_scene = QGraphicsScene(self)
        self.graphics_view.setScene(self.graphics_scene)
        self.layout.addWidget(self.graphics_view)

        # Set the layout
        self.main_widget.setLayout(self.layout)
        self.setCentralWidget(self.main_widget)

        # Add the File menu
        self.create_menu()
        self.create_file_toolbar()
        self.create_view_toolbar()

        # Add status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")  # Initial message

        self.sitk_image = None

    def create_menu(self):
        # Create a menu bar
        menubar = self.menuBar()

        # Add the File menu
        file_menu = menubar.addMenu("File")
        self.create_file_menu(file_menu)

        # Add View menu
        view_menu = menubar.addMenu("View")
        self.create_view_menu(view_menu)


    def create_file_menu(self, file_menu):
        
        # Add Open DICOM action
        open_image_action = QAction("Open Image", self)
        open_image_action.triggered.connect(self.open_dicom)
        file_menu.addAction(open_image_action)

        # Add Save Workspace action
        open_workspace_action = QAction("Open Workspace", self)
        open_workspace_action.triggered.connect(self.load_workspace)
        file_menu.addAction(open_workspace_action)

        # Add Save Workspace action
        save_workspace_action = QAction("Save Workspace", self)
        save_workspace_action.triggered.connect(self.save_workspace)
        file_menu.addAction(save_workspace_action)

    def create_view_menu(self, view_menu):
        
        # Zoom In
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.zoom_in_clicked)
        view_menu.addAction(zoom_in_action)

        # Zoom Out
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoom_out_clicked)
        view_menu.addAction(zoom_out_action)

        # Zoom Reset
        zoom_reset_action = QAction("Zoom Reset", self)
        zoom_reset_action.triggered.connect(self.zoom_reset_clicked)
        view_menu.addAction(zoom_reset_action)
        
    def create_file_toolbar(self):
        # Create a toolbar
        toolbar = QToolBar("File Toolbar", self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Add actions to the toolbar
        # Add Open DICOM action
        open_action = QAction("Open Image", self)
        open_action.triggered.connect(self.open_dicom)
        toolbar.addAction(open_action)

        # Add Save Workspace action
        open_workspace_action = QAction("Open Workspace", self)
        open_workspace_action.triggered.connect(self.load_workspace)
        toolbar.addAction(open_workspace_action)

        save_workspace_action = QAction("Save Workspace", self)
        save_workspace_action.triggered.connect(self.save_workspace)
        toolbar.addAction(save_workspace_action)


    def create_view_toolbar(self):
        # Create a toolbar
        toolbar = QToolBar("View Toolbar", self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # window_level_slider - level slider
        self.window_level_slider = LabeledSlider("Window Level:")
        self.window_level_slider.slider.valueChanged.connect(self.update_window_level)
        toolbar.addWidget(self.window_level_slider)

        # window_level_slider - width slider
        self.window_width_slider = LabeledSlider("Window Width:")
        self.window_width_slider.slider.valueChanged.connect(self.update_window_level)
        toolbar.addWidget(self.window_width_slider)
        
        # zoom in action
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.zoom_in_clicked)
        toolbar.addAction(zoom_in_action)    
        
         # zoom in action
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoom_out_clicked)
        toolbar.addAction(zoom_out_action)    

        # zoom reset button
        zoom_reset_action = QAction("Zoom Reset", self)
        zoom_reset_action.triggered.connect(self.zoom_reset_clicked)
        toolbar.addAction(zoom_reset_action)        

        # Add ruler toggle action
        toggle_ruler_action = QAction("Toggle Ruler", self)
        toggle_ruler_action.triggered.connect(self.graphics_view.toggle_ruler)
        toolbar.addAction(toggle_ruler_action)

    def zoom_in_clicked(self):
        if self.image_array is not None:
            self.graphics_view.zoom_in()
    
    def zoom_out_clicked(self):
        if self.image_array is not None:
            self.graphics_view.zoom_out()

    def zoom_reset_clicked(self):
        if self.image_array is not None:
            self.graphics_view.zoom_reset()

    def update_window_level(self):
        
        if self.image_array is not None:
            self.graphics_view.render_layers()

    def open_dicom(self):
        init_folder = "W:/RadOnc/Planning/Physics QA/2024/1.Monthly QA/TrueBeamSH/2024_11/imaging"
        file_path, _ = QFileDialog.getOpenFileName(self, "Open DICOM File", init_folder, "DICOM Files (*.dcm)")
        if file_path:
            # Load DICOM using SimpleITK
            self.sitk_image = sitk.ReadImage(file_path)
            image_array = sitk.GetArrayFromImage(self.sitk_image)[0]

            self.set_default_window_level(image_array)

            self.image_array = image_array
           
            self.update_window_level()

            self.graphics_view.render_layers()

            # notify other managers
            self.segmentation_list_manager.on_image_loaded(self.sitk_image)
            self.point_list_manager.on_image_loaded(self.sitk_image)

   
    def save_data(self):
        print('save data if dirty')

    def print_status(self, msg):
        self.status_bar.showMessage(msg)

    def save_workspace(self):
        import json
        import os

        """Save the current workspace to a folder."""
        if self.image_array is None:
            self.print_status("No image loaded. Cannot save workspace.")
            return

        # workspace json file
        workspace_json_path, _ = QFileDialog.getSaveFileName(self, "Save Workspace", "", "Json (*.json)")
        if not workspace_json_path:
            return 
        
        # data folder for the workspace
        data_dir = workspace_json_path+".data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # Create a metadata dictionary
        workspace_data = {
            "window_settings": {
                "level": self.window_level_slider.get_value(),
                "width": self.window_width_slider.get_value(),
            }
        }

        # Save input image as '.mha'
        input_image_path = os.path.join(data_dir, "input_image.mha")
        sitk.WriteImage(self.sitk_image, input_image_path, useCompression=True)

        #save segmentation layers
        self.segmentation_list_manager.save_state(workspace_data, data_dir)

        # Save points metadata
        self.point_list_manager.save_state(workspace_data, data_dir)

        # Save metadata as 'workspace.json'
        with open(workspace_json_path, "w") as f:
            json.dump(workspace_data, f, indent=4)

        self.print_status(f"Workspace saved to {workspace_json_path}.")

    def set_default_window_level(self, image_array):
        # Set default window-level values
        min = np.min(image_array)
        max = np.max(image_array)

        default_level = int((max + min) / 2)
        default_width = int(max - min)

        self.window_level_slider.setMinimum(min)
        self.window_level_slider.setMaximum(max)
        self.window_level_slider.setTickInterval(int(default_width/200))
        self.window_level_slider.setValue(default_level)
            
        self.window_width_slider.setMinimum(1)
        self.window_width_slider.setMaximum(default_width)
        self.window_width_slider.setTickInterval(int(default_width/200))
        self.window_width_slider.setValue(default_width)

    def load_workspace(self):
        import json
        import os

        """Load a workspace from a folder."""
        init_dir = "W:/RadOnc/Planning/Physics QA/2024/1.Monthly QA/TrueBeamSH/2024_11/imaging"
        workspace_json_path, _ = QFileDialog.getOpenFileName(self, "Select Workspace File", init_dir, "JSON Files (*.json)")
        if not workspace_json_path:
           return

        # Load metadata from 'workspace.json'
        if not os.path.exists(workspace_json_path):
            self.print_status("Workspace JSON file not found.")
            return

        data_path = workspace_json_path+".data"
        if not os.path.exists(data_path):
            self.print_status("Workspace data folder not found.")
            return

        try:
            with open(workspace_json_path, "r") as f:
                workspace_data = json.load(f)
        except json.JSONDecodeError as e:
            self.print_status(f"Failed to parse workspace.json: {e}")
            return

        # Clear existing workspace
        self.image_array = None
        self.sitk_image = None
        self.point_list_manager.points.clear()

        # Load input image
        input_image_path = os.path.join(data_path, "input_image.mha")
        if os.path.exists(input_image_path):
            try:
                self.sitk_image = sitk.ReadImage(input_image_path)
                self.image_array = sitk.GetArrayFromImage(self.sitk_image)[0]
                self.set_default_window_level(self.image_array)  # Call set_default_window_level
            except Exception as e:
                self.print_status(f"Failed to load input image: {e}")
                return

        self.segmentation_list_manager.load_state(workspace_data, data_path, {'base_image': self.sitk_image})
        self.point_list_manager.load_state(workspace_data, data_path, {'base_image': self.sitk_image})

        # Restore window settings
        window_settings = workspace_data.get("window_settings", {})
        self.window_level_slider.set_value(window_settings.get("level", 0))
        self.window_width_slider.set_value(window_settings.get("width", 1))

        # Render the workspace
        if self.image_array is not None:
            self.graphics_view.render_layers()

        self.print_status(f"Workspace loaded from {data_path}.")


class MyApplication(QApplication):
    def notify(self, receiver, event):
        
        #if event.type() == QEvent.FocusOut:
        #    print(f"Focus out: {receiver}")
        
        return super().notify(receiver, event)
    

if __name__ == "__main__":
    app = MyApplication(sys.argv)
    viewer = MainWindow()
    viewer.show()
    sys.exit(app.exec_())
