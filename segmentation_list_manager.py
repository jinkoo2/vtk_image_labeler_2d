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

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QLabel, QListWidgetItem, QColorDialog

import os

import numpy as np

from color_rotator import ColorRotator
from labeled_slider import LabeledSlider
from line_edit2 import LineEdit2


# Get the current directory of the script
current_dir = os.path.dirname(__file__)

# Construct paths to the icons
brush_icon_path = os.path.join(current_dir, "icons", "brush.png")
eraser_icon_path = os.path.join(current_dir, "icons", "eraser.png")
reset_zoom_icon_path = os.path.join(current_dir, "icons", "reset_zoom.png")

color_rotator = ColorRotator()

class SegmentationLayer:
    def __init__(self, segmentation, visible=True, color=np.array([255, 255, 128]), alpha=0.5) -> None:
        self.segmentation = segmentation
        self.visible = visible
        self.color = color
        self.alpha = alpha
        self.modified = False

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
        self.edit_name = LineEdit2(layer_name)
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

    def render_rgb(self, overlay_rgb, brush_x, brush_y):
        cv2.circle(overlay_rgb, (brush_x, brush_y), self.paintbrush.radius, self.paintbrush.color, self.paintbrush.line_thickness)
    
class SegmentationLayerRenderer():
    def __init__(self, layers, paintbrush, manager) -> None:
        self.layers = layers
        self.manager = manager
        self.paintbrush = paintbrush
        
        self.left_mouse_pressed = False

        self.paintbrush_renderer = PaintBrushRenderer(self.paintbrush)

    def get_graphics_view(self):
        return self.manager.get_graphics_view()
        
    def render_rgb(self, overlay_rgb, image_x=None, image_y=None):
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
        
        # draw paintbrush if active
        if (self.manager.brush_active or self.manager.erase_active) and image_x is not None and image_y is not None:  
            self.paintbrush_renderer.render_rgb(overlay_rgb, image_x, image_y)
    
    def get_image_array(self):
        return self.manager.image_array
    
    def point_in_image_boundary(self, x, y):
        
        if self.get_image_array() is None:
            return False

        if 0 <= x < self.get_image_array().shape[1] and 0 <= y < self.get_image_array().shape[0]:
            return True
        else:
            return False
        
    def paint_or_erase_on_active_layer(self, event):
        layer_data = self.manager.get_active_layer_data()

        # Ensure we have a valid active layer
        if not layer_data:
            return

        # Get the active segmentation mask
        segmentation = layer_data.segmentation

        # Map the mouse position to the scene
        scene_pos = self.get_graphics_view().mapToScene(event.pos())
        x = int(scene_pos.x())
        y = int(scene_pos.y())

        # Ensure the coordinates are within the image bounds
        if self.point_in_image_boundary(x, y):
            
            #make sure the brush radius is up to date.
            self.paintbrush.radius = self.manager.brush_size_slider.value()

            # paint/erase
            if self.manager.brush_active:
                self.paintbrush_renderer.paint_on_mask(segmentation, x, y)
            elif self.manager.erase_active:
                self.paintbrush_renderer.erase_on_mask(segmentation, x, y)
            
            # flag this layer has been modified
            layer_data.modified = True

            self.manager.get_graphics_view().render_layers()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            
            self.left_mouse_pressed = True

            if self.manager.brush_active or self.manager.erase_active:
                self.paint_or_erase_on_active_layer(event)
            
    
    def mouseMoveEvent(self, event):
        if self.manager.image_array is None:
            return 

        if self.left_mouse_pressed:
            if self.manager.brush_active or self.manager.erase_active:
                self.paint_or_erase_on_active_layer(event)


    def mouseReleaseEvent(self, event):
        if self.manager.image_array is None:
            return 

        self.left_mouse_pressed = False

class SegmentationListManager:
    def __init__(self, mainwindow):

        # mainwindow
        self._mainwindow = mainwindow

        # segmentation data
        self.image_array = None
        self.segmentation_layers = {}
        self.active_layer_name = None

        self.brush_active = False
        self.erase_active = False

        self.paintbrush = CirclePaintBrush(radius=10, color= (0,255,0), line_thickness= 1)

        # renderers
        self.renderer = SegmentationLayerRenderer(self.segmentation_layers, self.paintbrush, self)
        


    def load_from_workspace_file(self, workspace_json_path):
        import json
        import os

        folder_path = workspace_json_path+".data"

        # Load metadata from 'workspace.json'
        if not os.path.exists(workspace_json_path):
            self.print_status("Workspace JSON file not found.")
            return

        try:
            with open(workspace_json_path, "r") as f:
                workspace_data = json.load(f)
        except json.JSONDecodeError as e:
            self.print_status(f"Failed to parse workspace.json: {e}")
            return

        # Clear existing workspace
        self.segmentation_layers.clear()
        self.list_widget_for_segmentation_layers.clear()

        # Load segmentation layers
        for layer_name, layer_metadata in workspace_data.get("segmentation_layers", {}).items():
            segmentation_path = os.path.join(folder_path, layer_metadata["file"])
            if os.path.exists(segmentation_path):
                try:
                    segmentation_image = sitk.ReadImage(segmentation_path)
                    segmentation_array = sitk.GetArrayFromImage(segmentation_image)[0]

                    layer_data = SegmentationLayer(
                        segmentation=segmentation_array,
                        visible=layer_metadata["visible"],
                        color=tuple(layer_metadata["color"]),  # Convert to tuple
                        alpha=layer_metadata["alpha"],
                    )

                    self.segmentation_layers[layer_name] = layer_data

                    self.add_layer_widget_item(layer_name, layer_data)
                    
                except Exception as e:
                    self.print_status(f"Failed to load segmentation layer {layer_name}: {e}")
            else:
                self.print_status(f"Segmentation file for layer {layer_name} not found.")

    def get_mainwindow(self):
        return self._mainwindow

    def get_graphics_view(self):
        
        return self._mainwindow.graphics_view

    def get_status_bar(self):
        return self._mainwindow.status_bar
    
    def print_status(self, msg):
        if self.get_status_bar() is not None:
            self.get_status_bar().showMessage(msg)

    def on_layer_chagned(self,layer_name):
        self.get_graphics_view().update()
        
    def init_ui(self):   
        self.create_paintbrush_toolbar()
        self.create_layer_manager()

    def create_paintbrush_toolbar(self):
        
        mainwindow = self.get_mainwindow()

        # Create a toolbar
        toolbar = QToolBar("PaintBrush Toolbar",  mainwindow)
        mainwindow.addToolBar(Qt.TopToolBarArea, toolbar)

        # Add Brush Tool button
        self.brush_action = QAction("Brush Tool", mainwindow)
        self.brush_action.setCheckable(True)  # Make it togglable
        self.brush_action.setChecked(self.brush_active)  # Sync with initial state
        self.brush_action.triggered.connect(self.toggle_brush_tool)
        self.brush_action.setIcon(QIcon(brush_icon_path))
        toolbar.addAction(self.brush_action)

        # Add Erase Tool button
        self.erase_action = QAction("Erase Tool", mainwindow)
        self.erase_action.setCheckable(True)
        self.erase_action.setChecked(self.erase_active)
        self.erase_action.triggered.connect(self.toggle_erase_tool)
        self.erase_action.setIcon(QIcon(eraser_icon_path))
        toolbar.addAction(self.erase_action)

        # paintbrush size slider
        self.brush_size_slider = LabeledSlider("Brush Size:", initial_value=self.paintbrush.radius)
        self.brush_size_slider.slider.valueChanged.connect(self.update_brush_size)
        toolbar.addWidget(self.brush_size_slider)

    def create_layer_manager(self):
        
        mainwindow = self.get_mainwindow()
        
        # Create a dockable widget
        dock = QDockWidget("Segmentation Layer Manager ", mainwindow)
        dock.setAllowedAreas(Qt.RightDockWidgetArea)
        mainwindow.addDockWidget(Qt.RightDockWidgetArea, dock)

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
            self.get_status_bar().showMessage("Brush tool activated")
        else:
            self.brush_action.setText("Brush Tool (Inactive)")
            self.get_status_bar().showMessage("Brush tool deactivated")

    def toggle_erase_tool(self):
        self.erase_active = not self.erase_active
        self.brush_active = False  # Disable brush tool when erase is active
        self.brush_action.setChecked(False)  # Uncheck the brush button

        self.erase_action.setChecked(self.erase_active)
        if self.erase_active:
            self.erase_action.setText("Erase Tool (Active)")
            self.print_status("Erase tool activated")
        else:
            self.erase_action.setText("Erase Tool (Inactive)")
            self.print_status("Erase tool deactivated")    
          
    def layer_list_widget_on_current_item_changed(self, current, previous):
        if current:
            # Retrieve the custom widget associated with the current QListWidgetItem
            item_widget = self.list_widget_for_segmentation_layers.itemWidget(current)
            
            if item_widget and isinstance(item_widget, LayerItemWidget):
                # Access the layer_name from the custom widget
                layer_name = item_widget.layer_name
                if self.active_layer_name != layer_name:
                    self.active_layer_name = layer_name
                    self.get_graphics_view().render_layers()

    def generate_unique_layer_name(self, base_name="Layer"):
        index = 1
        while f"{base_name} {index}" in self.segmentation_layers:
            index += 1
        return f"{base_name} {index}"
    
    def add_layer_widget_item(self, layer_name, layer_data):

        # Create a custom widget for the layer
        layer_item_widget = LayerItemWidget(layer_name, layer_data, self)
        layer_item = QListWidgetItem(self.list_widget_for_segmentation_layers)
        layer_item.setSizeHint(layer_item_widget.sizeHint())
        self.list_widget_for_segmentation_layers.addItem(layer_item)
        self.list_widget_for_segmentation_layers.setItemWidget(layer_item, layer_item_widget) # This replaces the default text-based display with the custom widget that includes the checkbox and label.

        # set the added as active (do I need to indicate this in the list widget?)
        self.active_layer_name = layer_name
    
    def add_layer_clicked(self):

        # Generate a random bright color for the new layer
        layer_color = color_rotator.next()

        # add layer data        
        layer_name = self.generate_unique_layer_name()
        layer_data = SegmentationLayer(segmentation=np.zeros_like(self.image_array, dtype=np.uint8), color=layer_color)
        self.segmentation_layers[layer_name] = layer_data

        self.add_layer_widget_item(layer_name, layer_data)

        # render
        self.get_graphics_view().render_layers()

    def remove_layer_clicked(self):
        if len(self.list_widget_for_segmentation_layers) == 1:
                self.print_status("At least 1 layer is required.")
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

        # render
        self.get_graphics_view().render_layers()

    def update_brush_size(self, value):

        self.paintbrush.radius = value

        if self.image_array is not None:
            self.get_graphics_view().render_layers()

    def request_view_update(self):
        pass

    def on_image_loaded(self, sitk_image):
        
        self.sitk_image = sitk_image

        image_array = sitk.GetArrayFromImage(sitk_image)[0]

        self.image_array = image_array

        self.add_layer_clicked()
        
        self.request_view_update()

    def get_active_layer_data(self):
        if self.active_layer_name == None:
            return 
        
        layer_data = self.segmentation_layers[self.active_layer_name]

        return layer_data

    def save_segmentation_layer(self, segmentation, file_path):

        # Expand 2D segmentation into 3D (single slice)
        segmentation_3d = np.expand_dims(segmentation, axis=0)
        segmentation_image = sitk.GetImageFromArray(segmentation_3d)

        # Copy spatial metadata from the base
        segmentation_image.CopyInformation(self.sitk_image)

        # Save the segmentation as .mha
        sitk.WriteImage(segmentation_image, file_path,useCompression=True)

    def save_active_segmentation(self):
        
        if self.image_array is None:
            self.print_to_statusbar("No image loaded. Cannot save segmentation.")
            return
    
        active_layer_name = self.segmentation_list_manager.active_layer_name

        if active_layer_name:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Segmentation", "", "MetaImage Files (*.mha *.mhd)")
            if file_path:

                # Get the active layer's segmentation
                segmentation = self.segmentation_list_manager.get_active_layer_data().segmentation 

                self.save_segmentation_layer(segmentation, file_path)

                self.print_status(f"Active layer segmentation saved to {file_path}")
        else:
            self.print_to_statusbar("No active layer to save.")


    def save_state(self,data_dict, data_dir):
        # Save segmentation layers as '.mha'
        data_dict["segmentation_layers"] = {}

        for layer_name, layer_data in self.segmentation_layers.items():
            segmentation_path = os.path.join(data_dir, f"{layer_name}.mha")
            self.save_segmentation_layer(layer_data.segmentation, segmentation_path)

            # Add layer metadata to the workspace data
            data_dict["segmentation_layers"][layer_name] = {
                "file": f"{layer_name}.mha",
                "visible": layer_data.visible,
                "color": list(layer_data.color),
                "alpha": layer_data.alpha,
            }

    def load_state(self, data_dict, data_dir, aux_data):
        import json
        import os

        self.sitk_image = aux_data['base_image']

        # Clear existing workspace
        self.segmentation_layers.clear()
        self.list_widget_for_segmentation_layers.clear()

        # Load segmentation layers
        for layer_name, layer_metadata in data_dict.get("segmentation_layers", {}).items():
            seg_path = os.path.join(data_dir, layer_metadata["file"])
            if os.path.exists(seg_path):
                try:
                    sitk_seg = sitk.ReadImage(seg_path)
                    nparray_seg = sitk.GetArrayFromImage(sitk_seg)[0]

                    layer_data = SegmentationLayer(
                        segmentation=nparray_seg,
                        visible=layer_metadata["visible"],
                        color=tuple(layer_metadata["color"]),  # Convert to tuple
                        alpha=layer_metadata["alpha"],
                    )

                    self.segmentation_layers[layer_name] = layer_data

                    self.add_layer_widget_item(layer_name, layer_data)
                    
                except Exception as e:
                    self.print_status(f"Failed to load segmentation layer {layer_name}: {e}")
            else:
                self.print_status(f"Segmentation file for layer {layer_name} not found.")

