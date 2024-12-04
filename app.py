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

# Get the current directory of the script
current_dir = os.path.dirname(__file__)

# Construct paths to the icons
brush_icon_path = os.path.join(current_dir, "icons", "brush.png")
eraser_icon_path = os.path.join(current_dir, "icons", "eraser.png")
reset_zoom_icon_path = os.path.join(current_dir, "icons", "reset_zoom.png")


### helper functions
import numpy as np


def generate_random_bright_color():
    # Generate a random hue (0-360 degrees)
    hue = np.random.uniform(0, 360)

    # Set high saturation and value (brightness)
    saturation = np.random.uniform(0.8, 1.0)
    value = np.random.uniform(0.8, 1.0)

    # Convert HSV to RGB
    color = hsv_to_rgb(hue, saturation, value)

    # Return as an RGB array
    return np.array(color)

def hsv_to_rgb(h, s, v):
    """
    Convert HSV (Hue, Saturation, Value) to RGB.
    h: Hue (0-360 degrees)
    s: Saturation (0-1)
    v: Value (0-1)
    Returns: (R, G, B) as a tuple of integers (0-255)
    """
    h = float(h)
    s = float(s)
    v = float(v)

    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c

    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    else:  # 300 <= h < 360
        r, g, b = c, 0, x

    r = (r + m) * 255
    g = (g + m) * 255
    b = (b + m) * 255

    return int(r), int(g), int(b)


class ColorRotator:
    def __init__(self):
        # Define a list of 10 preset RGB colors
        self.colors = [
            (255, 0, 0),     # Red
            (0, 255, 0),     # Green
            (0, 0, 255),     # Blue
            (255, 255, 0),   # Yellow
            (0, 255, 255),   # Cyan
            (255, 0, 255),   # Magenta
            (170, 255, 0),   # 
            (255, 165, 0),   # Orange
            (170, 255, 9),   # Indigo
            (0, 128, 0)      # Dark Green
        ]
        self.index = 0  # Track the current position in the rotation

    def next(self):
        """Return the next color in the rotation."""
        color = self.colors[self.index]
        self.index = (self.index + 1) % len(self.colors)  # Move to the next color, wrap around if needed
        return color


class SegmentationLayer:
    def __init__(self, segmentation, visible=True, color=np.array([255, 255, 128]), alpha=0.5) -> None:
        self.segmentation = segmentation
        self.visible = visible
        self.color = color
        self.alpha = alpha


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
    
class SegmentationLayerRenderer:
    def __init__(self, layers) -> None:
        self.layers = layers

    def render(self, overlay_rgb):
        # Render each layer if it is visible
        for layer_name, layer_data in self.layers.items():
            segmentation = layer_data.segmentation
            visibility = layer_data.visible
            color = layer_data.color
            alpha = layer_data.alpha
            if segmentation is not None and visibility:
                mask = segmentation.astype(bool)
                color_array = np.array(color, dtype=np.float32)
                overlay_rgb[mask] = (1 - alpha) * overlay_rgb[mask] + alpha * color_array
        return overlay_rgb

class CirclePaintBrush:
    def __init__(self, radius, color, line_thickness) -> None:
        self.radius = radius
        self.color = color
        self.line_thickness = line_thickness

class PaintBrushRenderer:
    def __init__(self, paintbrush) -> None:
        self.paintbrush = paintbrush

    def paint_on_mask(self, segmentation, x, y):
        color = 1
        cv2.circle(segmentation, (x, y), self.paintbrush.radius, color, -1) # line_thickness of -1 if to fill the mask

    def erase_on_mask(self, segmentation, x, y):
        color = 0
        cv2.circle(segmentation, (x, y), self.paintbrush.radius, color, -1) # line_thickness of -1 if to fill the mask

    def render(self, overlay_rgb, brush_x, brush_y):
        cv2.circle(overlay_rgb, (brush_x, brush_y), self.paintbrush.radius, self.paintbrush.color, self.paintbrush.line_thickness)
    
class GraphicsView2D(QGraphicsView):
    def __init__(self, parent_viewer, parent=None):
        super().__init__(parent)
        
        self.parent_viewer = parent_viewer  # Reference to the DicomViewer instance

        self.setMouseTracking(True)  # Enable mouse tracking
        
        self.paintbrush = CirclePaintBrush(radius=10, color= (0,255,0), line_thickness= 1)
        
        self.zoom_factor = 1.0  # Initial zoom level
        self.zoom_step = 0.1  # Amount of zoom per scroll
        self.min_zoom = 0.5  # Minimum zoom factor
        self.max_zoom = 5.0  # Maximum zoom factor

        # renderers
        self.segmentation_layer_renderer = SegmentationLayerRenderer(parent_viewer.segmentation_layers)
        self.image_window_level_renderer = ImageWindowLevelRenderer()
        self.paintbrush_renderer = PaintBrushRenderer(self.paintbrush)

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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.get_image_array() is not None:
            if self.parent_viewer.brush_active:
                self.paint_on_active_layer(event)

    def mouseMoveEvent(self, event):
        image_array = self.get_image_array()

        if image_array is None:
            return

        # Map mouse position to the scene
        scene_pos = self.mapToScene(event.pos())
        x = int(scene_pos.x())
        y = int(scene_pos.y())

        # Ensure coordinates are within the image bounds
        if self.point_in_image_boundary(x,y):
            # If the left mouse button is pressed, draw on the active layer
            if event.buttons() & Qt.LeftButton and (self.parent_viewer.brush_active or self.parent_viewer.erase_active):
                self.paint_on_active_layer(event)

            # Render layers with the brush indicator
            if self.parent_viewer.brush_active or self.parent_viewer.erase_active:
                self.render_layers(brush_x=x, brush_y=y)
            else:
                self.render_layers(brush_x=None, brush_y=None)

            # Update the status bar with the current mouse position and pixel value
            pixel_value = image_array[y, x]
            self.parent_viewer.status_bar.showMessage(f"Mouse: ({x}, {y}) | Pixel Value: {pixel_value}")


    def paint_on_active_layer(self, event):
        layer_data = self.parent_viewer.get_active_layer_data()

        # Ensure we have a valid active layer
        if not layer_data:
            return

        # Get the active segmentation mask
        segmentation = layer_data.segmentation

        # Map the mouse position to the scene
        scene_pos = self.mapToScene(event.pos())
        x = int(scene_pos.x())
        y = int(scene_pos.y())

        # Ensure the coordinates are within the image bounds
        if self.point_in_image_boundary(x, y):
            
            #make sure the brush radius is up to date.
            self.paintbrush.radius = self.parent_viewer.brush_size_slider.value()

            # paint/erase
            if self.parent_viewer.brush_active:
                self.paintbrush_renderer.paint_on_mask(segmentation, x, y)
            elif self.parent_viewer.erase_active:
                self.paintbrush_renderer.erase_on_mask(segmentation, x, y)
                
            self.render_layers()

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
        self.segmentation_layer_renderer.render(overlay_rgb)

        # Draw the green brush indicator if coordinates are provided
        if brush_x is not None and brush_y is not None:
            self.paintbrush.radius = self.parent_viewer.brush_size_slider.value()
            self.paintbrush_renderer.render(overlay_rgb, brush_x, brush_y)

        # Convert the final overlay image to QImage and display it
        height, width, channel = overlay_rgb.shape
        qimage = QImage(overlay_rgb.data, width, height, 3 * width, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        self.scene().clear()
        self.scene().addPixmap(pixmap)

    def update(self):
        self.render_layers()
        
    def mouseReleaseEvent(self, event):
        pass

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QLabel, QListWidgetItem, QColorDialog


class CustomLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.focus_out_callback = None  # Placeholder for the callback

    def focusOutEvent(self, event):
        if self.focus_out_callback:
            self.focus_out_callback(event)  # Call the assigned function
        super().focusOutEvent(event)  # Ensure default behavior

class LayerItemWidget(QWidget):
    def __init__(self, layer_name, layer_data, parent_viewer):
        super().__init__()
        self.parent_viewer = parent_viewer
        self.layer_name = layer_name
        self.layer_data = layer_data

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Checkbox for visibility
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.stateChanged.connect(self.visible_checkbox_clicked)
        self.layout.addWidget(self.checkbox)

        # Color patch for layer
        self.color_patch = QLabel()
        self.color_patch.setFixedSize(16, 16)  # Small square
        self.color_patch.setStyleSheet(f"background-color: {self.get_layer_color_hex()}; border: 1px solid black;")
        self.color_patch.setCursor(Qt.PointingHandCursor)
        self.color_patch.mousePressEvent = self.open_color_dialog  # Assign event for color change
        self.layout.addWidget(self.color_patch)

        # Label for the layer name
        self.label = QLabel(layer_name)
        self.label.setCursor(Qt.PointingHandCursor)
        self.label.mouseDoubleClickEvent = self.activate_editor  # Assign double-click to activate editor
        self.layout.addWidget(self.label)

        # Editable name field
        self.edit_name = CustomLineEdit(layer_name)
        self.edit_name.focus_out_callback = self.focusOutEvent
        self.edit_name.setToolTip("Edit the layer name (must be unique and file-system compatible).")
        self.edit_name.hide()  # Initially hidden
        self.edit_name.returnPressed.connect(self.deactivate_editor)  # Commit name on Enter
        self.edit_name.editingFinished.connect(self.deactivate_editor)  # Commit name on losing focus
        self.edit_name.textChanged.connect(self.validate_name)
        
        self.layout.addWidget(self.edit_name)

        self.setLayout(self.layout)

    def visible_checkbox_clicked(self, state):
        visibility = state == Qt.Checked
        self.layer_data.visible = visibility
        self.parent_viewer.on_layer_chagned(self.layer_name)

    def get_layer_color_hex(self):
        """Convert the layer's color (numpy array) to a hex color string."""
        color = self.layer_data.color
        return f"rgb({color[0]}, {color[1]}, {color[2]})"

    def open_color_dialog(self, event):
        """Open a color chooser dialog and update the layer's color."""
        current_color = QColor(self.layer_data.color[0], self.layer_data.color[1], self.layer_data.color[2])
        new_color = QColorDialog.getColor(current_color, self, "Select Layer Color")

        if new_color.isValid():
            # Update layer color
            self.layer_data.color = np.array([new_color.red(), new_color.green(), new_color.blue()])
            # Update color patch
            self.color_patch.setStyleSheet(f"background-color: {self.get_layer_color_hex()}; border: 1px solid black;")
            # Notify the viewer to update rendering
            self.parent_viewer.on_layer_chagned(self.layer_name)

    def focusOutEvent(self, event):
        """Deactivate the editor when it loses focus."""
        if self.edit_name.isVisible():
            self.deactivate_editor()
        super().focusOutEvent(event)

    def activate_editor(self, event):
        """Activate the name editor (QLineEdit) and hide the label."""
        self.label.hide()
        self.edit_name.setText(self.label.text())
        self.edit_name.show()
        self.edit_name.setFocus()
        self.edit_name.selectAll()  # Select all text for easy replacement

    def deactivate_editor(self):
        """Deactivate the editor, validate the name, and show the label."""
        new_name = self.edit_name.text()
        self.validate_name()

        # If valid, update the label and layer name
        if self.edit_name.toolTip() == "":
            self.label.setText(new_name)
            self.layer_name = new_name

        # Show the label and hide the editor
        self.label.show()
        self.edit_name.hide()

    def validate_name(self):
        """Validate the layer name for uniqueness and file system compatibility."""
        new_name = self.edit_name.text()

        # Check for invalid file system characters
        invalid_chars = r'<>:"/\|?*'
        if any(char in new_name for char in invalid_chars) or new_name.strip() == "":
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")  # Radish color
            self.edit_name.setToolTip("Layer name contains invalid characters or is empty.")
            return

        # Check for uniqueness
        existing_names = [name for name in self.parent_viewer.segmentation_layers.keys() if name != self.layer_name]
        if new_name in existing_names:
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")  # Radish color
            self.edit_name.setToolTip("Layer name must be unique.")
            return

        # Name is valid
        self.edit_name.setStyleSheet("")  # Reset background
        self.edit_name.setToolTip("")
        self.update_layer_name(new_name)


    def update_layer_name(self, new_name):
        """Update the layer name in the viewer."""
        if new_name != self.layer_name:
            self.parent_viewer.segmentation_layers[new_name] = self.parent_viewer.segmentation_layers.pop(self.layer_name)
            self.layer_name = new_name

class LabeledSlider(QWidget):
    def __init__(self, label_text="Slider", min_value=0, max_value=100, initial_value=50, orientation=Qt.Horizontal):
        super().__init__()

        # Create the components
        self.label = QLabel(label_text)
        self.label.setAlignment(Qt.AlignRight)  # Align label text to the right
        self.slider = QSlider(orientation)
        self.current_value_label = QLabel(str(initial_value))

        # Set slider properties
        self.slider.setMinimum(min_value)
        self.slider.setMaximum(max_value)
        self.slider.setValue(initial_value)

        # Connect the slider value change signal to the update function
        self.slider.valueChanged.connect(self.update_value_label)

        # Layout
        main_layout = QHBoxLayout()  # Horizontal layout for label, slider, and value display

        # Add widgets to layouts with margins
        main_layout.addWidget(self.label)
        main_layout.addWidget(self.slider, stretch=1)  # Let slider expand to fill space
        main_layout.addWidget(self.current_value_label)

        # Set margins for better spacing
        main_layout.setContentsMargins(10, 5, 10, 5)  # Left, top, right, bottom

        self.setLayout(main_layout)

    def update_value_label(self, value):
        """Update the dynamic value display when the slider changes."""
        self.current_value_label.setText(str(value))

    def get_value(self):
        """Get the current slider value."""
        return self.slider.value()

    def set_value(self, value):
        """Set the slider value."""
        self.slider.setValue(value)

    def setMinimum(self, min):
        self.slider.setMinimum(min)
            
    def setMaximum(self, min):
        self.slider.setMaximum(min)

    def setTickInterval(self, min):
        self.slider.setTickInterval(min)

    def setValue(self, min):
        self.slider.setValue(min)
    
    def value(self):
        return self.slider.value()
    
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.image_array = None
        self.segmentation_layers = {}
        self.active_layer_name = None

        self.color_rotator = ColorRotator()

        self.init_ui()

    def on_layer_chagned(self,layer_name):
        self.graphics_view.update()
        
    def init_ui(self):
        self.setWindowTitle("Image Labeler 2D")
        self.setGeometry(100, 100, 800, 600)

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
        self.create_paintbrush_toolbar()
        self.create_view_toolbar()
        self.create_layer_manager()

        # Add status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")  # Initial message

        self.dicom_image = None

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
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_dicom)
        file_menu.addAction(open_action)

        # Add Save Segmentation action
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_segmentation)
        file_menu.addAction(save_action)

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
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_dicom)
        toolbar.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_segmentation)
        toolbar.addAction(save_action)

    def create_paintbrush_toolbar(self):
        # Create a toolbar
        toolbar = QToolBar("PaintBrush Toolbar", self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Add Brush Tool button
        self.brush_active = False  # Initially inactive
        self.brush_action = QAction("Brush Tool", self)
        self.brush_action.setCheckable(True)  # Make it togglable
        self.brush_action.setChecked(self.brush_active)  # Sync with initial state
        self.brush_action.triggered.connect(self.toggle_brush_tool)
        self.brush_action.setIcon(QIcon(brush_icon_path))
        toolbar.addAction(self.brush_action)

        # Add Erase Tool button
        self.erase_active = False  # Initially inactive
        self.erase_action = QAction("Erase Tool", self)
        self.erase_action.setCheckable(True)
        self.erase_action.setChecked(self.erase_active)
        self.erase_action.triggered.connect(self.toggle_erase_tool)
        self.erase_action.setIcon(QIcon(eraser_icon_path))
        toolbar.addAction(self.erase_action)

        # paintbrush size slider
        self.brush_size_slider = LabeledSlider("Brush Size:", initial_value=20)
        self.brush_size_slider.slider.valueChanged.connect(self.update_brush_size)
        toolbar.addWidget(self.brush_size_slider)

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

    def zoom_in_clicked(self):
        if self.image_array is not None:
            self.graphics_view.zoom_in()
    
    def zoom_out_clicked(self):
        if self.image_array is not None:
            self.graphics_view.zoom_out()

    def zoom_reset_clicked(self):
        if self.image_array is not None:
            self.graphics_view.zoom_reset()

    def create_layer_manager(self):
        # Create a dockable widget
        dock = QDockWidget("Layer Manager", self)
        dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        # Layer manager layout
        layer_widget = QWidget()
        layer_layout = QVBoxLayout()

        # Layer list
        self.list_widget_for_segmentation_layers = QListWidget()
        self.list_widget_for_segmentation_layers.currentItemChanged.connect(self.layer_list_widget_on_current_item_changed)
        layer_layout.addWidget(self.list_widget_for_segmentation_layers)

        # Buttons to manage layers
        button_layout = QHBoxLayout()

        add_layer_button = QPushButton("Add Layer")
        add_layer_button.clicked.connect(self.add_layer_clicked)
        button_layout.addWidget(add_layer_button)

        remove_layer_button = QPushButton("Remove Layer")
        remove_layer_button.clicked.connect(self.remove_layer_clicked)
        button_layout.addWidget(remove_layer_button)

        # Add the button layout at the top
        layer_layout.addLayout(button_layout)
        # Set layout for the layer manager
        layer_widget.setLayout(layer_layout)
        dock.setWidget(layer_widget)


    def toggle_brush_tool(self):
        self.brush_active = not self.brush_active
        self.erase_active = False  # Disable erase tool when brush is active
        self.erase_action.setChecked(False)  # Uncheck the erase button

        self.brush_action.setChecked(self.brush_active)
        if self.brush_active:
            self.brush_action.setText("Brush Tool (Active)")
            self.status_bar.showMessage("Brush tool activated")
        else:
            self.brush_action.setText("Brush Tool (Inactive)")
            self.status_bar.showMessage("Brush tool deactivated")

    def toggle_erase_tool(self):
        self.erase_active = not self.erase_active
        self.brush_active = False  # Disable brush tool when erase is active
        self.brush_action.setChecked(False)  # Uncheck the brush button

        self.erase_action.setChecked(self.erase_active)
        if self.erase_active:
            self.erase_action.setText("Erase Tool (Active)")
            self.status_bar.showMessage("Erase tool activated")
        else:
            self.erase_action.setText("Erase Tool (Inactive)")
            self.status_bar.showMessage("Erase tool deactivated")    
                

    def layer_list_widget_on_current_item_changed(self, current, previous):
        if current:
            # Retrieve the custom widget associated with the current QListWidgetItem
            item_widget = self.list_widget_for_segmentation_layers.itemWidget(current)
            
            if item_widget and isinstance(item_widget, LayerItemWidget):
                # Access the layer_name from the custom widget
                layer_name = item_widget.layer_name
                if self.active_layer_name != layer_name:
                    self.active_layer_name = layer_name
                    self.graphics_view.render_layers()

    def generate_unique_layer_name(self, base_name="Layer"):
        index = 1
        while f"{base_name} {index}" in self.segmentation_layers:
            index += 1
        return f"{base_name} {index}"
    
    def add_layer_clicked(self):

        # Generate a random bright color for the new layer
        layer_color = self.color_rotator.next()

        # add layer data        
        layer_name = self.generate_unique_layer_name()
        layer_data = SegmentationLayer(segmentation=np.zeros_like(self.image_array, dtype=np.uint8), color=layer_color)
        self.segmentation_layers[layer_name] = layer_data

        # Create a custom widget for the layer
        layer_item_widget = LayerItemWidget(layer_name, layer_data, self)
        layer_item = QListWidgetItem(self.list_widget_for_segmentation_layers)
        layer_item.setSizeHint(layer_item_widget.sizeHint())
        self.list_widget_for_segmentation_layers.addItem(layer_item)
        self.list_widget_for_segmentation_layers.setItemWidget(layer_item, layer_item_widget) # This replaces the default text-based display with the custom widget that includes the checkbox and label.

        # set the added as active (do I need to indicate this in the list widget?)
        self.active_layer_name = layer_name

        # render
        self.graphics_view.render_layers()

    def remove_layer_clicked(self):
        if len(self.list_widget_for_segmentation_layers) == 1:
                self.print_to_statusbar("At least 1 layer is required.")
                return 

        selected_items = self.list_widget_for_segmentation_layers.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            widget = self.list_widget_for_segmentation_layers.itemWidget(item)
            layer_name = widget.layer_name

            # Remove from the data list
            del self.segmentation_layers[layer_name]

            # Remove from the list widget
            self.list_widget_for_segmentation_layers.takeItem(self.list_widget_for_segmentation_layers.row(item))

        # update
        self.graphics_view.render_layers()

    def update_brush_size(self, value):

        self.graphics_view.paintbrush.radius = value

        if self.image_array is not None:
            self.graphics_view.render_layers()

    
    def update_window_level(self):
        
        if self.image_array is not None:
            self.graphics_view.render_layers()

   

    def open_dicom(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open DICOM File", "", "DICOM Files (*.dcm)")
        if file_path:
            # Load DICOM using SimpleITK
            self.dicom_image = sitk.ReadImage(file_path)
            image_array = sitk.GetArrayFromImage(self.dicom_image)[0]

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

            self.image_array = image_array

            self.add_layer_clicked()
            
            self.update_window_level()

            self.graphics_view.render_layers()

    def get_active_layer_data(self):
        if self.active_layer_name == None:
            return 
        
        layer_data = self.segmentation_layers[self.active_layer_name]

        return layer_data
    
    def save_segmentation(self):
        
        if self.image_array is None:
            self.print_to_statusbar("No image loaded. Cannot save segmentation.")
            return
    
        if self.active_layer_name:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Segmentation", "", "MetaImage Files (*.mha *.mhd)")
            if file_path:
                # Get the active layer's segmentation
                segmentation = self.graphics_view.segmentation_layers[self.active_layer_name].segmentation

                # Expand 2D segmentation into 3D (single slice)
                segmentation_3d = np.expand_dims(segmentation, axis=0)
                segmentation_image = sitk.GetImageFromArray(segmentation_3d)

                # Copy spatial metadata from the original DICOM image
                segmentation_image.CopyInformation(self.dicom_image)

                # Save the segmentation as .mha
                sitk.WriteImage(segmentation_image, file_path)
                self.print_to_statusbar(f"Active layer segmentation saved to {file_path}")
        else:
            self.print_to_statusbar("No active layer to save.")

    def print_status(self, msg):
        self.status_bar.showMessage(msg)


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
