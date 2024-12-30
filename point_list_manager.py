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

### helper functions
import numpy as np

class Point:
    def __init__(self, x: int, y: int, name:str, color: tuple = (255, 0, 0), visible: bool = True):
        self.x = x
        self.y = y
        self.name = name
        self.color = color
        self.visible = visible

class PointItemWidget(QWidget):
    def __init__(self, point, parent_manager):
        super().__init__()
        self.point = point
        self.parent_manager = parent_manager

        # Layout
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Visibility checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.point.visible)
        self.checkbox.stateChanged.connect(self.toggle_visibility)
        self.layout.addWidget(self.checkbox)

        # Color patch
        self.color_patch = QLabel()
        self.color_patch.setFixedSize(16, 16)
        self.color_patch.setStyleSheet(f"background-color: {self.get_color_hex()}; border: 1px solid black;")
        self.color_patch.setCursor(Qt.PointingHandCursor)
        self.color_patch.mousePressEvent = self.change_color
        self.layout.addWidget(self.color_patch)

        # Editable name
        self.name_label = QLabel(self.point.name)
        self.name_label.setCursor(Qt.PointingHandCursor)
        self.name_label.mouseDoubleClickEvent = self.activate_editor
        self.layout.addWidget(self.name_label)

        self.name_editor = QLineEdit(self.point.name)
        self.name_editor.setVisible(False)
        self.name_editor.returnPressed.connect(self.deactivate_editor)
        self.name_editor.editingFinished.connect(self.deactivate_editor)
        self.layout.addWidget(self.name_editor)

        self.setLayout(self.layout)

    def toggle_visibility(self, state):
        self.point.visible = state == Qt.Checked
        self.parent_manager.update_points()

    def change_color(self, event):
        color = QColorDialog.getColor()
        if color.isValid():
            self.point.color = (color.red(), color.green(), color.blue())
            self.color_patch.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self.parent_manager.update_points()

    def activate_editor(self, event):
        self.name_label.hide()
        self.name_editor.show()
        self.name_editor.setFocus()
        self.name_editor.selectAll()

    def deactivate_editor(self):
        new_name = self.name_editor.text().strip()
        if new_name and self.parent_manager.is_name_unique(new_name):
            self.point.name = new_name
            self.name_label.setText(new_name)
        else:
            self.parent_manager.parent_viewer.print_status("Name must be unique or valid!")
        self.name_label.show()
        self.name_editor.hide()

    def get_color_hex(self):
        r, g, b = self.point.color
        return f"rgb({r}, {g}, {b})"


class PointListRenderer:
    def __init__(self, manager) -> None:
        self.manager = manager
        

    def render_rgb(self, overlay_rgb, image_x=None, image_y=None):
        # Render each layer if it is visible
        for i, point in enumerate(self.manager.points):
            if point.visible:
                color = point.color
                x, y = point.x, point.y
                cv2.circle(overlay_rgb, (x, y), radius=5, color=color, thickness=-1)
                if i == self.active_point_index:
                    # Draw a larger circle around the active point
                    cv2.circle(overlay_rgb, (x, y), radius=8, color=(255, 255, 255), thickness=1)

    def get_image_array(self):
        return self.manager.image_array
    
    def image_loaded(self):
        return self.get_image_array() != None

    def mousePressEvent(self, event):
        if not self.image_loaded():
            return 

        if event.button() == Qt.LeftButton:
            if self.manager.point_edit_active:
                # Handle point editing
                scene_pos = self.mapToScene(event.pos())
                x, y = int(scene_pos.x()), int(scene_pos.y())
                for i, point in enumerate(self.manager.points):
                    if (point.x - x) ** 2 + (point.y - y) ** 2 <= 5 ** 2:  # Check proximity
                        self.manager.active_point_index = i
                        self.manager.dragging_point = True
                        self.manager.update_point_manager()
                        return
    
    def mouseMoveEvent(self, event):
        if not self.image_loaded():
            return 

        if self.manager.point_edit_active and self.manager.dragging_point and self.manager.active_point_index is not None:
            # Move the active point
            scene_pos = self.mapToScene(event.pos())
            x, y = int(scene_pos.x()), int(scene_pos.y())
            self.manager.points[self.manager.active_point_index].x = x
            self.manager.points[self.manager.active_point_index].y = y
            self.manager.update_point_manager()

    def mouseReleaseEvent(self, event):
        if not self.image_loaded():
            return 

        if self.point_edit_active and event.button() == Qt.LeftButton:
            self.dragging_point = False

class PointListWidget(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.layout = QVBoxLayout()

        # List of points
        self.point_list_widget = QListWidget()
        self.point_list_widget.currentItemChanged.connect(self.on_point_selected)
        self.layout.addWidget(self.point_list_widget)

        # Add/Remove buttons
        button_layout = QHBoxLayout()
        add_point_button = QPushButton("Add Point")
        add_point_button.clicked.connect(self.add_point)
        remove_point_button = QPushButton("Remove Point")
        remove_point_button.clicked.connect(self.remove_point)
        button_layout.addWidget(add_point_button)
        button_layout.addWidget(remove_point_button)
        self.layout.addLayout(button_layout)

        self.setLayout(self.layout)

    def get_graphics_view(self):
        self.manager.get_graphics_view()

    def add_point(self):
        """Add a new point with a unique name, placing it at the center of the viewport."""
        name = self.generate_unique_name()
        
        # Get the center of the viewport in scene coordinates
        viewport_center = self.get_graphics_view().mapToScene(
            self.get_graphics_view().viewport().rect().center()
        )
        x, y = int(viewport_center.x()), int(viewport_center.y())

        # Create the new point at the center of the viewport
        new_point = Point(x, y, name)
        self.manager.pointlist_renderer.points.append(new_point)
        self.update_point_list()

        self.get_graphics_view().update()    
    
    def remove_point(self):
        """Remove the selected point."""
        current_row = self.point_list_widget.currentRow()
        if current_row != -1:
            del self.manager.points[current_row]
            self.manager.active_point_index = None
            self.update_point_list()

    def on_point_selected(self, current, previous):
        """Set the selected point as active."""
        if current:
            index = self.point_list_widget.row(current)
            self.manager.active_point_index = index

    def update_point_list(self):
        """Update the point list."""
        self.point_list_widget.clear()
        for point in self.manager.points:
            item = QListWidgetItem(self.point_list_widget)
            item_widget = PointItemWidget(point, self)
            item.setSizeHint(item_widget.sizeHint())
            self.point_list_widget.addItem(item)
            self.point_list_widget.setItemWidget(item, item_widget)

    def generate_unique_name(self, base_name="Point"):
        """Generate a unique name for a new point."""
        index = 1
        while any(p.name == f"{base_name} {index}" for p in self.manager.points):
            index += 1
        return f"{base_name} {index}"

    def is_name_unique(self, name):
        """Check if a name is unique."""
        return not any(p.name == name for p in self.manager.points)

    def update_points(self):
        """Re-render points in the graphics view."""
        self.get_graphics_view().render_layers()

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QLabel, QListWidgetItem, QColorDialog
from color_rotator import ColorRotator

color_rotator = ColorRotator()

class PointListManager:
    
    def __init__(self, mainwindow):

        # mainwindow
        self._mainwindow = mainwindow

        # data
        self.points = []  # List of Point objects
        self.active_point_index = None  # Index of the active point
        self.dragging_point = False  # State for dragging
        self.point_edit_active = False

        self.image_array = None

        self.renderer = PointListRenderer(self)  
      
    def init_ui(self):
        self.create_point_manager()
        self.create_point_edit_toolbar()

    def get_mainwindow(self):
        return self._mainwindow

      

    def create_point_manager(self):
        
        mainwindow = self.get_mainwindow()
        
        # Create a dockable widget
        dock = QDockWidget("Point List Manager", mainwindow)
        dock.setAllowedAreas(Qt.RightDockWidgetArea)
        mainwindow.addDockWidget(Qt.RightDockWidgetArea, dock)

        # Create the PointListManager widget
        self.point_manager = PointListWidget(self)
        dock.setWidget(self.point_manager)

    def create_point_edit_toolbar(self):
        
        mainwindow = self.get_mainwindow()

        # Create a PointEdit toolbar
        toolbar = QToolBar("PointEdit Toolbar", mainwindow)
        mainwindow.addToolBar(Qt.TopToolBarArea, toolbar)

        # Add toggle button for point editing
        self.point_edit_active = False  # Initially inactive
        self.point_edit_action = QAction("Edit Points", mainwindow)
        self.point_edit_action.setCheckable(True)  # Make it toggleable
        self.point_edit_action.setChecked(self.point_edit_active)  # Sync with initial state
        self.point_edit_action.triggered.connect(self.toggle_point_edit)
        toolbar.addAction(self.point_edit_action)
        
    def update_point_manager(self):
        """Update the point manager UI when points change."""
        self.point_manager.update_point_list()
      
    def toggle_point_edit(self):
        self.renderer.point_edit_active = not self.point_edit_active
        self.point_edit_action.setChecked(self.point_edit_active)
        if self.point_edit_active:
            self.print_status("Point editing activated.")
        else:
            self.print_status("Point editing deactivated.")

    def on_image_loaded(self, image_array):
        self.image_array = image_array

   
    def print_status(self, msg):
        self.get_mainwindow().status_bar.showMessage(msg)



