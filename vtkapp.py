import vtk
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QSlider, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, 
    QFileDialog, QVBoxLayout, QSlider, QPushButton, QLabel, QWidget, QMenuBar, QAction, QToolBar, QDockWidget, QListWidget, QHBoxLayout, QPushButton, QCheckBox, QLineEdit
)
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QLabel, QListWidgetItem, QColorDialog
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QIcon

from logger import logger

def to_vtk_color(c):
    return [c[0]/255, c[1]/255, c[2]/255]

def from_vtk_color(c):
    return [int(c[0]*255), int(c[1]*255), int(c[2]*255)]


class PaintBrush:
    def __init__(self, radius_in_pixel=(20,20), pixel_spacing=(1.0, 1.0), color= (0,255,0), line_thickness= 1):
        self.radius_in_pixel = radius_in_pixel
        self.pixel_spacing = pixel_spacing

        # Paintbrush setup
        self.enabled = False

        # Brush actor for visualization
        self.brush_actor = vtk.vtkActor()
        self.brush_actor.SetVisibility(False)  # Initially hidden

        # Create a green brush representation
        # Create a 2D circle for brush visualization
        self.brush_source = vtk.vtkPolyData()
        self.circle_points = vtk.vtkPoints()
        self.circle_lines = vtk.vtkCellArray()


        self.brush_source.SetPoints(self.circle_points)
        self.brush_source.SetLines(self.circle_lines)
        self.brush_mapper = vtk.vtkPolyDataMapper()
        self.brush_mapper.SetInputData(self.brush_source)
        self.brush_actor.SetMapper(self.brush_mapper)
        self.brush_actor.GetProperty().SetColor(color[0], color[1], color[2])  

        self.set_radius_in_pixel(radius_in_pixel, pixel_spacing=(1.0, 1.0))
    def get_actor(self):
        return self.brush_actor
    
    def set_color(self, color_vtk):
        if hasattr(self, 'brush_actor') and self.brush_actor is not None:
            self.brush_actor.GetProperty().SetColor(color_vtk[0], color_vtk[1], color_vtk[2]) 

    def set_radius_in_pixel(self, radius_in_pixel, pixel_spacing):
        
        self.radius_in_pixel = radius_in_pixel
        self.pixel_spacing = pixel_spacing

        radius_in_real = (radius_in_pixel[0] * pixel_spacing[0], radius_in_pixel[1] * pixel_spacing[1])

        self.update_circle_geometry(radius_in_real)

    def update_circle_geometry(self, radius_in_real):
        """Update the circle geometry to reflect the current radius."""
        self.circle_points.Reset()
        self.circle_lines.Reset()

        num_segments = 50  # Number of segments for the circle
        for i in range(num_segments):
            angle = 2.0 * math.pi * i / num_segments
            x = radius_in_real[0] * math.cos(angle)
            y = radius_in_real[1] * math.sin(angle)
            self.circle_points.InsertNextPoint(x, y, 0)

            # Connect the points to form a circle
            if i > 0:
                line = vtk.vtkLine()
                line.GetPointIds().SetId(0, i - 1)
                line.GetPointIds().SetId(1, i)
                self.circle_lines.InsertNextCell(line)

        # Close the circle
        line = vtk.vtkLine()
        line.GetPointIds().SetId(0, num_segments - 1)
        line.GetPointIds().SetId(1, 0)
        self.circle_lines.InsertNextCell(line)

        # Notify VTK that the geometry has been updated
        self.circle_points.Modified()
        self.circle_lines.Modified()
        self.brush_source.Modified()


    def paint(self, segmentation, x, y, value=1):
        """Draw a circle on the segmentation at (x, y) with the given radius."""
        dims = segmentation.GetDimensions()
        scalars = segmentation.GetPointData().GetScalars()
        extent = segmentation.GetExtent()

        # radius in pixel space
        radius_in_pixelx = self.radius_in_pixel[0]
        radius_in_pixely = self.radius_in_pixel[1]

        for i in range(-radius_in_pixelx, radius_in_pixelx + 1):
            for j in range(-radius_in_pixely, radius_in_pixely + 1):
                
                # Check if the pixel is within the circle
                if ((i/radius_in_pixelx)**2 + (j/radius_in_pixely)**2) <= 1.0:
                    xi = x + i
                    yj = y + j
                    if extent[0] <= xi <= extent[1] and extent[2] <= yj <= extent[3]:
                        idx = (yj - extent[2]) * dims[0] + (xi - extent[0])
                        scalars.SetTuple1(idx, value)

import math


class Panning:
    def __init__(self, viewer=None):
        self.viewer = viewer
        self.interactor = viewer.interactor
        self.left_button_is_pressed = False
        self.last_mouse_position = None
        self.enabled = False

    def enable(self, enabled=True):
        self.enabled = enabled

        if enabled:
            self.left_button_press_observer = self.interactor.AddObserver("LeftButtonPressEvent", self.on_left_button_press)
            self.mouse_move_observer = self.interactor.AddObserver("MouseMoveEvent", self.on_mouse_move)
            self.left_button_release_observer = self.interactor.AddObserver("LeftButtonReleaseEvent", self.on_left_button_release)
        else:    
            self.interactor.RemoveObserver(self.left_button_press_observer)
            self.interactor.RemoveObserver(self.mouse_move_observer)
            self.interactor.RemoveObserver(self.left_button_release_observer)   
            self.last_mouse_position = None

        if enabled:
            self.viewer.setCursor(Qt.OpenHandCursor)  # Change cursor for panning mode
        else:
            self.viewer.setCursor(Qt.ArrowCursor)  # Reset cursor
        
        print(f"Panning mode: {'enabled' if enabled else 'disabled'}")
    
    def on_left_button_press(self, obj, event):
        if not self.enabled:
            return
        
        self.left_button_is_pressed = True
        self.last_mouse_position = self.interactor.GetEventPosition()

    def on_mouse_move(self, obj, event):
        if not self.enabled:
            return

        if self.left_button_is_pressed:
            self.perform_panning()

        self.viewer.render_window.Render()

    def on_left_button_release(self, obj, event):
        if not self.enabled:
            return
        
        self.left_button_is_pressed = False
        self.last_mouse_position = None

    def perform_panning(self):
        """Perform panning based on mouse movement, keeping the pointer fixed on the same point in the image."""
        current_mouse_position = self.interactor.GetEventPosition()

        if self.last_mouse_position:
            
            renderer = self.viewer.get_renderer()
            
            # Get the camera and renderer
            camera = renderer.GetActiveCamera()

            # Convert mouse positions to world coordinates
            picker = vtk.vtkWorldPointPicker()

            # Pick world coordinates for the last mouse position
            picker.Pick(self.last_mouse_position[0], self.last_mouse_position[1], 0, renderer)
            last_world_position = picker.GetPickPosition()

            # Pick world coordinates for the current mouse position
            picker.Pick(current_mouse_position[0], current_mouse_position[1], 0, renderer)
            current_world_position = picker.GetPickPosition()

            # Compute the delta in world coordinates
            delta_world = [
                last_world_position[0] - current_world_position[0],
                last_world_position[1] - current_world_position[1],
                last_world_position[2] - current_world_position[2],
            ]

            # Update the camera position and focal point
            camera.SetFocalPoint(
                camera.GetFocalPoint()[0] + delta_world[0],
                camera.GetFocalPoint()[1] + delta_world[1],
                camera.GetFocalPoint()[2] + delta_world[2],
            )
            camera.SetPosition(
                camera.GetPosition()[0] + delta_world[0],
                camera.GetPosition()[1] + delta_world[1],
                camera.GetPosition()[2] + delta_world[2],
            )

            # Render the updated scene
            self.viewer.render_window.Render()

        # Update the last mouse position
        self.last_mouse_position = current_mouse_position
        

class Zooming:
    def __init__(self, viewer=None):
        self.viewer = viewer
        self.interactor = viewer.interactor
        self.enabled = False
        self.zoom_in_factor = 1.2
        self.zoom_out_factor = 0.8

    def enable(self, enabled=True):
        self.enabled = enabled

        if enabled:
            self.mouse_wheel_forward_observer = self.interactor.AddObserver("MouseWheelForwardEvent", self.on_mouse_wheel_forward)
            self.on_mouse_wheel_backward_observer = self.interactor.AddObserver("MouseWheelBackwardEvent", self.on_mouse_wheel_backward)
        else:    
            self.interactor.RemoveObserver(self.mouse_wheel_forward_observer)
            self.interactor.RemoveObserver(self.on_mouse_wheel_backward_observer)   

        print(f"Zooming mode: {'enabled' if enabled else 'disabled'}")
    
    def on_mouse_wheel_forward(self, obj, event):
        if not self.enabled:
            return

        self.zoom_in()        

        self.viewer.render_window.Render()

    def on_mouse_wheel_backward(self, obj, event):
        if not self.enabled:
            return

        self.zoom_out()

        self.viewer.render_window.Render()

    def zoom_in(self):
        """Zoom in the camera."""
        camera = self.viewer.get_renderer().GetActiveCamera()
        camera.Zoom(self.zoom_in_factor)  
        
        self.viewer.get_render_window().Render()

    def zoom_out(self):
        """Zoom out the camera."""
        camera = self.viewer.get_renderer().GetActiveCamera()
        camera.Zoom(self.zoom_out_factor)  
        
        self.viewer.get_render_window().Render()

    def zoom_reset(self):
        # Get the active camera
        camera = self.viewer.get_renderer().GetActiveCamera()

        if camera.GetParallelProjection():
            # Reset parallel projection scale
            self.viewer.get_renderer().ResetCamera()
        else:
            # Reset perspective projection parameters
            camera.SetPosition(0.0, 0.0, 1000.0)
            camera.SetFocalPoint(0.0, 0.0, 0.0)
            camera.SetViewUp(0.0, 1.0, 0.0)
            self.viewer.get_renderer().ResetCameraClippingRange()

        # Render the updated scene
        self.viewer.get_render_window().Render()

class LineWidget:
    def __init__(self, vtk_image, pt1_w, pt2_w, line_color_vtk=[1,0,0], line_width=2, renderer=None):
        # Create a ruler using vtkLineWidget2
        widget = vtk.vtkLineWidget2()
        representation = vtk.vtkLineRepresentation()
        widget.SetRepresentation(representation)

        # Set initial position of the ruler
        representation.SetPoint1WorldPosition(pt1_w)
        representation.SetPoint2WorldPosition(pt2_w)
        representation.GetLineProperty().SetColor(line_color_vtk[0],line_color_vtk[1],line_color_vtk[2])  
        representation.GetLineProperty().SetLineWidth(line_width)
        representation.SetVisibility(True)

        representation.text_actor = vtk.vtkTextActor()
        representation.text_actor.GetTextProperty().SetFontSize(12)
        representation.text_actor.GetTextProperty().SetColor(1, 1, 1)  # White color
        
        renderer.AddActor2D(representation.text_actor)

        interactor = renderer.GetRenderWindow().GetInteractor()

        # Set interactor and enable interaction
        if interactor:
            widget.SetInteractor(interactor)

        self.widget = widget
        self.representation = representation
        self.interactor = interactor
        self.renderer = renderer
        self.color_vtk = line_color_vtk
        self.line_width = line_width
        self.vtk_image = vtk_image

        # Attach a callback to update distance when the ruler is moved
        widget.AddObserver("InteractionEvent", lambda obj, event: self.update_ruler_distance())

        # Attach the camera observer
        self.renderer.GetActiveCamera().AddObserver("ModifiedEvent", lambda obj, event: self.update_ruler_distance())

        # Attach the window resize observer
        self.renderer.GetRenderWindow().AddObserver("WindowResizeEvent", lambda obj, event: self.update_ruler_distance())

        self.update_ruler_distance()
    
    def world_to_display(self, renderer, world_coordinates):
        """Convert world coordinates to display coordinates."""
        display_coordinates = [0.0, 0.0, 0.0]
        renderer.SetWorldPoint(*world_coordinates, 1.0)
        renderer.WorldToDisplay()
        display_coordinates = renderer.GetDisplayPoint()
        return display_coordinates

    def update_ruler_distance(self):

        representation = self.representation

        # Calculate the distance
        point1 = representation.GetPoint1WorldPosition()
        point2 = representation.GetPoint2WorldPosition()
        distance = ((point2[0] - point1[0]) ** 2 +
                    (point2[1] - point1[1]) ** 2 +
                    (point2[2] - point1[2]) ** 2) ** 0.5

        print(f"Ruler Distance: {distance:.2f} mm")

        # Update the text actor position 
        midpoint_w = [(point1[i] + point2[i]) / 2 for i in range(3)]
        midpoint_screen = self.world_to_display(self.renderer, midpoint_w)
        representation.text_actor.SetInput(f"{distance:.2f} mm")
        representation.text_actor.SetPosition(midpoint_screen[0], midpoint_screen[1])       





import vtk
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QLabel, QLineEdit, QListWidgetItem, QColorDialog
)
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QColor

class LineItem:
    def __init__(self, point1_w, point2_w, color=[255, 0, 0], width=1.0, visible=True, renderer=None, interactor=None):
        self.point1_w = point1_w
        self.point2_w = point2_w
        self.color = color
        self.visible = visible
        self.modified = False
        self.width = width

        # Create a line representation
        self.representation = vtk.vtkLineRepresentation()
        self.representation.SetPoint1WorldPosition(self.point1_w)
        self.representation.SetPoint2WorldPosition(self.point2_w)
        self.representation.GetLineProperty().SetColor(color[0] / 255, color[1] / 255, color[2] / 255)
        self.representation.GetLineProperty().SetLineWidth(self.width)

        # Create a line widget
        self.widget = vtk.vtkLineWidget2()
        self.widget.SetRepresentation(self.representation)

        # Add observer for interaction
        self.widget.AddObserver("InteractionEvent", self.on_interaction)

        # Add the widget to the interactor
        if interactor:
            self.widget.SetInteractor(interactor)
            self.widget.On()

    def set_highlight(self, highlighted):
        """Highlight or unhighlight the line."""
        representation = self.widget.GetRepresentation()
        if highlighted:
            representation.GetLineProperty().SetLineWidth(self.width * 2.0)  # Increase width for highlighting
        else:
            representation.GetLineProperty().SetLineWidth(self.width)
            

    def set_visibility(self, visible):
        self.visible = visible
        self.widget.EnabledOn() if visible else self.widget.EnabledOff()

    def set_color(self, color):
        self.color = color
        self.modified = True
        self.representation.GetLineProperty().SetColor(color[0] / 255, color[1] / 255, color[2] / 255)

    def on_interaction(self, obj, event):
        self.point1_w = self.representation.GetPoint1WorldPosition()
        self.point2_w = self.representation.GetPoint2WorldPosition()
        self.modified = True


class LineListItemWidget(QWidget):
    def __init__(self, name, line, manager):
        super().__init__()
        self.manager = manager
        self.line = line
        self.name = name

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Checkbox for visibility
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.line.visible)
        self.checkbox.stateChanged.connect(self.toggle_visibility)
        self.layout.addWidget(self.checkbox)

        # Color patch for the line
        self.color_patch = QLabel()
        self.color_patch.setFixedSize(16, 16)  # Small square
        self.color_patch.setStyleSheet(f"background-color: {self.get_color_hex_string()}; border: 1px solid black;")
        self.color_patch.setCursor(Qt.PointingHandCursor)
        self.color_patch.mousePressEvent = self.change_color_clicked
        self.layout.addWidget(self.color_patch)

        # Label for the line name
        self.label = QLabel(name)
        self.label.setCursor(Qt.PointingHandCursor)
        self.label.mouseDoubleClickEvent = self.activate_name_editor
        self.layout.addWidget(self.label)

        # Editable name field
        self.edit_name = QLineEdit(name)
        self.edit_name.setToolTip("Edit the line name (must be unique and file-system compatible).")
        self.edit_name.hide()  # Initially hidden
        self.edit_name.returnPressed.connect(self.deactivate_name_editor)
        self.edit_name.editingFinished.connect(self.deactivate_name_editor)
        self.edit_name.textChanged.connect(self.validate_name)
        self.layout.addWidget(self.edit_name)

        # Remove button (with 'x')
        self.remove_button = QPushButton("X")
        self.remove_button.setMinimumSize(25, 25)  # Adjust size for better appearance
        self.remove_button.setToolTip("Remove this line")
        self.remove_button.clicked.connect(self.remove_line_clicked)
        self.layout.addWidget(self.remove_button, alignment=Qt.AlignCenter)

        self.setLayout(self.layout)

    def toggle_visibility(self, state):
        self.line.set_visibility(state == Qt.Checked)
        self.manager.on_line_changed(self.name)

    def get_color_hex_string(self):
        color = self.line.color
        return f"rgb({color[0]}, {color[1]}, {color[2]})"

    def change_color_clicked(self, event):
        current_color = QColor(self.line.color[0], self.line.color[1], self.line.color[2])
        color = QColorDialog.getColor(current_color, self, "Select Line Color")

        if color.isValid():
            c = [color.red(), color.green(), color.blue()]
            self.line.set_color(c)
            self.color_patch.setStyleSheet(f"background-color: {self.get_color_hex_string()}; border: 1px solid black;")
            self.manager.on_line_changed(self.name)

    def activate_name_editor(self, event):
        self.label.hide()
        self.edit_name.setText(self.label.text())
        self.edit_name.show()
        self.edit_name.setFocus()
        self.edit_name.selectAll()

    def deactivate_name_editor(self):
        new_name = self.edit_name.text()
        self.validate_name()

        if self.edit_name.toolTip() == "":
            self.label.setText(new_name)
            self.name = new_name

        self.label.show()
        self.edit_name.hide()

    def validate_name(self):
        new_name = self.edit_name.text()
        invalid_chars = r'<>:"/\\|?*'
        if any(char in new_name for char in invalid_chars) or new_name.strip() == "":
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")
            self.edit_name.setToolTip("Line name contains invalid characters or is empty.")
            return

        existing_names = [name for name in self.manager.lines.keys() if name != self.name]
        if new_name in existing_names:
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")
            self.edit_name.setToolTip("Line name must be unique.")
            return

        self.edit_name.setStyleSheet("")
        self.edit_name.setToolTip("")
        self.manager.update_line_name(self.name, new_name)

    def remove_line_clicked(self):
        self.manager.remove_line_by_name(self.name)


class LineListManager(QObject):
    log_message = pyqtSignal(str, str)  # For emitting log messages

    def __init__(self, vtk_viewer):
        super().__init__()
        self.vtk_viewer = vtk_viewer
        self.vtk_renderer = vtk_viewer.get_renderer()
        self.lines = {}  # Dictionary of LineItem objects
        self.active_line_name = None

        self.color_rotator = ColorRotator()

    def clear(self):
        """Clear all lines and their widgets."""
        for name, line in list(self.lines.items()):  # Use list to avoid mutation during iteration
            self.remove_line_by_name(name)  # Properly remove each line

        self.lines.clear()  # Clear the dictionary
        self.list_widget.clear()  # Clear the list widget
        self._modified = False  # Reset the modified flag
        self.vtk_renderer.GetRenderWindow().Render()  # Refresh the renderer

        self.log_message.emit("INFO", "All lines cleared.")

    def setup_ui(self):
        """Set up the UI with a dockable widget."""
        dock = QDockWidget("Lines")
        widget = QWidget()
        layout = QVBoxLayout()

        # List widget for lines
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.on_current_item_changed)
        layout.addWidget(self.list_widget)

        # Buttons to manage lines
        button_layout = QHBoxLayout()

        add_line_button = QPushButton("Add Line")
        add_line_button.clicked.connect(self.add_line_clicked)
        button_layout.addWidget(add_line_button)

        layout.addLayout(button_layout)
        widget.setLayout(layout)
        dock.setWidget(widget)

        return None, dock

    def get_exclusive_actions(self):
        """Return an empty list of exclusive actions."""
        return []

    def on_current_item_changed(self, current, previous):
        """Handle line selection in the list widget."""
        if current:
            # Retrieve the custom widget associated with the current QListWidgetItem
            item_widget = self.list_widget.itemWidget(current)
            
            if item_widget and isinstance(item_widget, LineListItemWidget):
                # Get the line and name from the widget
                line = item_widget.line
                name = item_widget.name

                # Deselect previous line, if any
                if previous:
                    previous_widget = self.list_widget.itemWidget(previous)
                    if previous_widget and isinstance(previous_widget, LineListItemWidget):
                        previous_line = previous_widget.line
#                        previous_line.widget.Off()  # Disable interaction for the previous line
                        previous_line.set_highlight(False)

                # Highlight and enable the selected line
                line.widget.On()  # Enable interaction for the selected line
                line.set_highlight(True)

                # Update the active line name
                self.active_line_name = name
                print(f"Line {name} selected")

                # Render the updated scene
                self.vtk_viewer.get_render_window().Render()
                
    def generate_unique_name(self, base_name="Line"):
        index = 1
        while f"{base_name} {index}" in self.lines:
            index += 1
        return f"{base_name} {index}"

    def add_line_clicked(self):
        """Handle the 'Add Line' button click."""
        # Determine the center of the current view
        renderer = self.vtk_viewer.get_renderer()
        camera = renderer.GetActiveCamera()
        focal_point = camera.GetFocalPoint()
        view_extent = camera.GetParallelScale()  # Approximate size of the visible area

        # Calculate start and end points for the new line
        point1_w = [
            focal_point[0] - view_extent / 6,
            focal_point[1],
            focal_point[2] + 1.0,  # Slightly above the focal plane
        ]
        point2_w = [
            focal_point[0] + view_extent / 6,
            focal_point[1],
            focal_point[2] + 1.0,  # Slightly above the focal plane
        ]

        # Generate a unique name for the new line
        line_name = self.generate_unique_name()

        # Add the new line
        self.add_line(
            point1_w=point1_w,
            point2_w=point2_w,
            color=self.color_rotator.next(),  # Generate a new color
            name=line_name,
        )

        # Log the addition
        self.log_message.emit("INFO", f"Added line {line_name}")
        
    def add_line(self, point1_w, point2_w, color=[255, 0, 0], visible=True, width=1.0, name=None):
        line = LineItem(point1_w=point1_w, point2_w=point2_w, color=color, width=width, visible=visible, renderer=self.vtk_renderer, interactor=self.vtk_viewer.interactor)
        if name is None:
            name = self.generate_unique_name()

        self.lines[name] = line

        item_widget = LineListItemWidget(name, line, self)
        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, item_widget)
        self.list_widget.setCurrentItem(item)
        
        self._modified = True

        self.log_message.emit("INFO", f"Added line: pt1={point1_w}, pt2={point2_w}")

    def find_list_widget_item_by_text(self, text):
        """
        Find a QListWidgetItem in the list widget based on its text.

        :param list_widget: The QListWidget instance.
        :param text: The text of the item to find.
        :return: The matching QListWidgetItem or None if not found.
        """
        list_widget = self.list_widget

        for index in range(list_widget.count()):
            item = list_widget.item(index)
            item_widget = list_widget.itemWidget(item)

            if item_widget.name == text:
                return item, item_widget
        return None

    def remove_line_by_name(self, name):
        
        if name in self.lines:
            
            item, item_widget = self.find_list_widget_item_by_text(name)

            if item is not None:
                line = item_widget.line

                # Disable the line widget and remove it
                from vtk_tools import remove_widget
                remove_widget(line.widget, self.vtk_renderer)

                # Remove from the data list
                del self.lines[name]

                # Remove from the list widget
                self.list_widget.takeItem(self.list_widget.row(item))

                # Select the last item in the list widget (to activate it)
                if name == self.active_line_name and self.list_widget.count() > 0:
                    self.list_widget.setCurrentRow(self.list_widget.count() - 1)
            
                self._modified = True
            else:
                logger.error(f'List item of name {name} not found!')
        else:
            logger.error(f'Remove line failed. the line with name {name} in the line list')
    

    def on_line_changed(self, name):
        self.vtk_renderer.GetRenderWindow().Render()

    def update_line_name(self, old_name, new_name):
        if old_name in self.lines:
            self.lines[new_name] = self.lines.pop(old_name)

    def save_state(self, data_dict, data_dir):
        """Save the state of all lines to the workspace."""
        lines_data = []
        for name, line in self.lines.items():
            lines_data.append({
                "name": name,
                "point1_w": list(line.representation.GetPoint1WorldPosition()),
                "point2_w": list(line.representation.GetPoint2WorldPosition()),
                "color": line.color,
                "width": line.width,
                "visible": line.visible,
            })
        data_dict["lines"] = lines_data
        self.reset_modified()  # Reset modified state after saving
        self.log_message.emit("INFO", "Lines state saved successfully.")

    def load_state(self, data_dict, data_dir, aux_data):
        """Load the state of all lines from the workspace."""
        self.clear()  # Clear existing lines before loading new ones

        if "lines" not in data_dict:
            self.log_message.emit("WARNING", "No lines found in workspace to load.")
            return

        for line_data in data_dict["lines"]:
            try:
                name = line_data["name"]
                point1_w = line_data["point1_w"]
                point2_w = line_data["point2_w"]
                color = line_data["color"]
                width = line_data["width"]
                visible = line_data["visible"]

                # Add the line to the manager
                self.add_line(point1_w=point1_w, point2_w=point2_w, color=color, width=width, visible=True, name=name)

            except Exception as e:
                self.log_message.emit("ERROR", f"Failed to load line {line_data.get('name', 'Unnamed')}: {str(e)}")

        self._modified = False  # Reset modified state after loading
        self.log_message.emit("INFO", "Lines state loaded successfully.")

    def reset_modified(self):
        self._modified = False
        for _, data in self.lines.items():
            data.modified = False

    def modified(self):
        if self._modified:
            return True

        for name, line in self.lines.items():
            if line.modified:
                return True
            
        return False
    
class VTKViewer(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
    
        if main_window is not None:
            self.main_window = main_window

        background_color = (0.5, 0.5, 0.5)

        # Create a VTK Renderer
        self.base_renderer = vtk.vtkRenderer()
        self.base_renderer.SetLayer(0)
        self.base_renderer.SetBackground(*background_color)  # Set background to gray
        self.base_renderer.GetActiveCamera().SetParallelProjection(True)
        self.base_renderer.SetInteractive(True)

        # Create a VTK Renderer for the brush actor
        #self.brush_renderer = vtk.vtkRenderer()
        #self.brush_renderer.SetLayer(1)  # Higher layer index
        #self.brush_renderer.SetBackground(*background_color)  # Transparent background

        # Create a QVTKRenderWindowInteractor
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        self.render_window = self.vtk_widget.GetRenderWindow()  # Retrieve the render window
        #self.render_window.SetNumberOfLayers(2)
        self.render_window.AddRenderer(self.base_renderer)
        #self.render_window.AddRenderer(self.brush_renderer)

        # Set up interactor style
        self.interactor = self.render_window.GetInteractor()
        self.interactor_style = vtk.vtkInteractorStyleUser()
        self.interactor.SetInteractorStyle(self.interactor_style)

        # Layout for embedding the VTK widget
        layout = QVBoxLayout()
        layout.addWidget(self.vtk_widget)
        self.setLayout(layout)

        # Connect mouse events
        self.interactor.AddObserver("LeftButtonPressEvent", self.on_left_button_press)
        self.interactor.AddObserver("LeftButtonReleaseEvent", self.on_left_button_release)
        self.interactor.AddObserver("MouseMoveEvent", self.on_mouse_move)

        self.rulers = []
        self.zooming = Zooming(viewer=self)
        self.panning = Panning(viewer=self)  

    def clear(self):
        # Remove the previous image actor if it exists
        if hasattr(self, 'image_actor') and self.image_actor is not None:
            self.get_renderer().RemoveActor(self.image_actor)
            self.image_actor = None

        self.vtk_image = None

    def print_status(self, msg):
        if self.main_window is not None:
            self.main_window.print_status(msg)

    def set_vtk_image(self, vtk_image, window, level):

        # reset first
        self.clear()

        self.vtk_image = vtk_image
                
        # Connect reader to window/level filter
        self.window_level_filter = vtk.vtkImageMapToWindowLevelColors()
        #self.window_level_filter.SetOutputFormatToRGB()
        self.window_level_filter.SetInputData(vtk_image)
        self.window_level_filter.SetWindow(window)
        self.window_level_filter.SetLevel(level)
        self.window_level_filter.Update()

        self.image_actor = vtk.vtkImageActor()
        self.image_actor.GetMapper().SetInputConnection(self.window_level_filter.GetOutputPort())

        self.get_renderer().AddActor(self.image_actor)
        
        self.get_renderer().ResetCamera()

        self.get_render_window().Render()

    def get_renderer(self):
        return self.base_renderer
    
    def get_render_window(self):
        return self.render_window
    
    def get_camera_info(self):
        """Retrieve the camera's position and direction in the world coordinate system."""
        camera = self.base_renderer.GetActiveCamera()

        # Get the camera origin (position in world coordinates)
        camera_position = camera.GetPosition()

        # Get the focal point (the point the camera is looking at in world coordinates)
        focal_point = camera.GetFocalPoint()

        # Compute the view direction (vector from camera position to focal point)
        view_direction = [
            focal_point[0] - camera_position[0],
            focal_point[1] - camera_position[1],
            focal_point[2] - camera_position[2],
        ]

        # Normalize the view direction
        magnitude = (view_direction[0] ** 2 + view_direction[1] ** 2 + view_direction[2] ** 2) ** 0.5
        view_direction = [component / magnitude for component in view_direction]

        print(f"Camera Position (Origin): {camera_position}")
        print(f"Focal Point: {focal_point}")
        print(f"View Direction: {view_direction}")

        return camera_position, focal_point, view_direction


    def print_camera_viewport_info(self):
        """Print the viewport and camera information."""
        # Get the renderer and camera
        renderer = self.base_renderer
        camera = renderer.GetActiveCamera()

        # Viewport settings
        viewport = renderer.GetViewport()
        print(f"Viewport: {viewport}")  # Returns (xmin, ymin, xmax, ymax)

        # Camera position and orientation
        position = camera.GetPosition()
        focal_point = camera.GetFocalPoint()
        view_up = camera.GetViewUp()

        print(f"Camera Position: {position}")
        print(f"Focal Point: {focal_point}")
        print(f"View Up Vector: {view_up}")

        # Parallel scale (if in parallel projection mode)
        if camera.GetParallelProjection():
            parallel_scale = camera.GetParallelScale()
            print(f"Parallel Scale: {parallel_scale}")

        # Clipping range (near and far clipping planes)
        clipping_range = camera.GetClippingRange()
        print(f"Clipping Range: {clipping_range}")

    def add_ruler(self):
        """Add a ruler to the center of the current view and enable interaction."""
        camera = self.get_renderer().GetActiveCamera()
        focal_point = camera.GetFocalPoint()
        view_extent = camera.GetParallelScale()  # Approximate size of the visible area

        # Calculate ruler start and end points
        start_point = [focal_point[0] - view_extent / 6, focal_point[1], focal_point[2]+0.1]
        end_point = [focal_point[0] + view_extent / 6, focal_point[1], focal_point[2]+0.1]

        # Create a ruler using vtkLineWidget2
        line_widget = LineWidget(
            vtk_image=self.vtk_image,
            pt1_w=start_point, 
            pt2_w=end_point, 
            line_color_vtk=[1,0,0], 
            line_width=2, 
            renderer=self.get_renderer())
        
        line_widget.widget.On()

        # Add the ruler to the list for management
        self.rulers.append(line_widget)

        self.get_render_window().Render()

    def on_left_button_press(self, obj, event):
        self.left_button_is_pressed = True

    def on_mouse_move(self, obj, event):
        self.print_mouse_coordiantes()
        self.render_window.Render()

    def print_mouse_coordiantes(self):
        """Update brush position and print mouse position details when inside the image."""
        mouse_pos = self.interactor.GetEventPosition()

        # Use a picker to get world coordinates
        picker = vtk.vtkWorldPointPicker()
        picker.Pick(mouse_pos[0], mouse_pos[1], 0, self.get_renderer())

        # Get world position
        world_pos = picker.GetPickPosition()

        # Check if the world position is valid
        if not picker.GetPickPosition():
            print("Mouse is outside the render area.")
            return

        # Get the image data
        vtk_image = self.vtk_image
        if not vtk_image:
            print("No image loaded.")
            return

        # Get image properties
        dims = vtk_image.GetDimensions()
        spacing = vtk_image.GetSpacing()
        origin = vtk_image.GetOrigin()

        # Convert world coordinates to image index
        image_index = [
            int((world_pos[0] - origin[0]) / spacing[0] + 0.5),
            int((world_pos[1] - origin[1]) / spacing[1] + 0.5),
            int((world_pos[2] - origin[2]) / spacing[2] + 0.5)
        ]

        # Check if the index is within bounds
        if not (0 <= image_index[0] < dims[0] and 0 <= image_index[1] < dims[1] and 0 <= image_index[2] < dims[2]):
            # Print details
            self.print_status(f"Point - World: ({world_pos[0]:.2f}, {world_pos[1]:.2f}))")
            return

        # Get the pixel value
        scalars = vtk_image.GetPointData().GetScalars()
        flat_index = image_index[2] * dims[0] * dims[1] + image_index[1] * dims[0] + image_index[0]
        pixel_value = scalars.GetTuple1(flat_index)

        # Print details
        self.print_status(f"Point - World: ({world_pos[0]:.2f}, {world_pos[1]:.2f}) Index: ({image_index[0]}, {image_index[1]}), Value: {pixel_value} )")
        
        

    def on_left_button_release(self, obj, event):
        self.left_button_is_pressed = False

    def center_image(self):
        
        dims = self.vtk_image.GetDimensions()
        spacing = self.vtk_image.GetSpacing()
        original_origin = self.vtk_image.GetOrigin()

        # Calculate the center of the image in world coordinates
        center = [
            original_origin[0] + (dims[0] * spacing[0]) / 2.0,
            original_origin[1] + (dims[1] * spacing[1]) / 2.0,
            original_origin[2] + (dims[2] * spacing[2]) / 2.0,
        ]

        # Shift the origin to center the image in the world coordinate system
        new_origin = [
            original_origin[0] - center[0],
            original_origin[1] - center[1],
            0.0,
        ]
        self.vtk_image.SetOrigin(new_origin)
        
        print('new_origin: ', new_origin)

        self.image_original_origin = original_origin


    def print_properties(self):
        """Print the properties of the camera, image, and line widgets."""
        # Camera properties
        camera = self.base_renderer.GetActiveCamera()
        print("Camera Properties:")
        print(f"  Position: {camera.GetPosition()}")
        print(f"  Focal Point: {camera.GetFocalPoint()}")
        print(f"  View Up: {camera.GetViewUp()}")
        print(f"  Clipping Range: {camera.GetClippingRange()}")
        print(f"  Parallel Scale: {camera.GetParallelScale()}")
        print()

        # Image properties
        if self.vtk_image:
            dims = self.vtk_image.GetDimensions()
            spacing = self.vtk_image.GetSpacing()
            origin = self.vtk_image.GetOrigin()
            print("Image Properties:")
            print(f"  Dimensions: {dims}")
            print(f"  Spacing: {spacing}")
            print(f"  Origin: {origin}")
            print()

        # Line widget properties
        if self.rulers:
            print("Line Widget Properties:")
            for idx, line_widget in enumerate(self.rulers, start=1):
                representation = line_widget.GetRepresentation()
                point1 = representation.GetPoint1WorldPosition()
                point2 = representation.GetPoint2WorldPosition()
                print(f"  Line Widget {idx}:")
                print(f"    Point 1: {point1}")
                print(f"    Point 2: {point2}")
                print()
        else:
            print("No Line Widgets Present.")

    def reset_camera_parameters(self):
        """Align the camera viewport center to the center of the loaded image."""
        if self.vtk_image is None:
            print("No image data loaded.")
            return

        # Get the image center
        dims = self.vtk_image.GetDimensions()
        spacing = self.vtk_image.GetSpacing()
        origin = self.vtk_image.GetOrigin()

        # Calculate the center of the image in world coordinates
        image_center = [
            origin[0] + (dims[0] * spacing[0]) / 2.0,
            origin[1] + (dims[1] * spacing[1]) / 2.0,
            origin[2] + (dims[2] * spacing[2]) / 2.0,
        ]

        # Set the camera parameters
        camera = self.base_renderer.GetActiveCamera()

        # Position the camera at the center of the image, slightly offset in Z
        camera.SetPosition(image_center[0], image_center[1], image_center[2] + 100)  # Adjust Z for visibility

        # Set the focal point to the center of the image
        camera.SetFocalPoint(image_center)

        # Set the view-up vector
        camera.SetViewUp(0.0, -1.0, 0.0)  # Y-axis up in world coordinates

        # Adjust the parallel scale to fit the image height
        camera.SetParallelScale((dims[1] * spacing[1]) / 2.0)

        # Reset the clipping range for visibility
        camera.SetClippingRange(1, 1000)

        print(f"Camera aligned to image center: {image_center}")
        print(f"Camera Position: {camera.GetPosition()}")
        print(f"Camera Focal Point: {camera.GetFocalPoint()}")
        print(f"Camera View Up: {camera.GetViewUp()}")

        # Render the changes
        self.render_window.Render()
            
    def toggle_base_image(self, visible):
        """Toggle the visibility of the base image."""
        self.base_image_visible = visible
        self.image_actor.SetVisibility(self.base_image_visible)
        self.render_window.Render()

    def toggle_panning_mode(self, checked):
        """Enable or disable panning mode."""
        self.panning.enable(checked)

    def toggle_zooming_mode(self, checked):
        """Enable or disable panning mode."""
        self.zooming.enable(checked)
  
    def toggle_paintbrush(self, enabled):
        """Enable or disable the paintbrush tool."""
        self.painting_enabled = enabled
        self.brush_actor.SetVisibility(enabled)  # Show brush if enabled
        self.render_window.Render()


from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QToolButton, QHBoxLayout
import os

# Construct paths to the icons
current_dir = os.path.dirname(__file__)
brush_icon_path = os.path.join(current_dir, "icons", "brush.png")
eraser_icon_path = os.path.join(current_dir, "icons", "eraser.png")
reset_zoom_icon_path = os.path.join(current_dir, "icons", "reset_zoom.png")

import numpy as np

class SegmentationItem:
    def __init__(self, segmentation, visible=True, color=np.array([255, 255, 128]), alpha=0.5, actor=None) -> None:
        self.segmentation = segmentation
        self.visible = visible
        self.color = color
        self.alpha = alpha
        self.actor = actor
        self.modified = False

from line_edit2 import LineEdit2

class SegmentationListItemWidget(QWidget):
    
    def get_viewer(self):
        return self.manager
    
    def __init__(self, layer_name, layer_data, manager):
        super().__init__()
        self.manager = manager
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
        self.color_patch.mousePressEvent = self.change_color_clicked  # Assign event for color change
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

        # Remove button (with 'x')
        self.remove_button = QPushButton("X")
        self.remove_button.setMinimumSize(25, 25)  # Adjust size for better appearance
        self.remove_button.setToolTip("Remove this layer")
        self.remove_button.clicked.connect(self.remove_layer_clicked)
        self.layout.addWidget(self.remove_button, alignment=Qt.AlignCenter)

        self.setLayout(self.layout)

    def remove_layer_clicked(self):
        """Remove the layer when the 'x' button is clicked."""
        self.manager.remove_segmentation_by_name(self.layer_name)

    def visible_checkbox_clicked(self, state):
        visibility = state == Qt.Checked
        self.layer_data.visible = visibility
        self.layer_data.actor.SetVisibility(visibility)
        self.manager.on_layer_changed(self.layer_name)

    def get_layer_color_hex(self):
        """Convert the layer's color (numpy array) to a hex color string."""
        color = self.layer_data.color
        return f"rgb({color[0]}, {color[1]}, {color[2]})"

    def change_color_clicked(self, event):
        
        """Open a color chooser dialog and update the layer's color."""
        # Get the current color in QColor format
        current_color = QColor(
            self.layer_data.color[0], 
            self.layer_data.color[1], 
            self.layer_data.color[2]
        )
        color = QColorDialog.getColor(current_color, self, "Select Layer Color")

        if color.isValid():
            
            c = [color.red(), color.green(), color.blue()]
            # Update layer color
            self.layer_data.color = c
            # Update color patch
            self.color_patch.setStyleSheet(f"background-color: {self.get_layer_color_hex()}; border: 1px solid black;")
            # Notify the viewer to update rendering
            #self.parent_viewer.on_layer_chagned(self.layer_name)
            
            # lookup table of the image actor
            # Create a lookup table for coloring the segmentation
            lookup_table = vtk.vtkLookupTable()
            lookup_table.SetNumberOfTableValues(2)  # For 0 (background) and 1 (segmentation)
            lookup_table.SetTableRange(0, 1)       # Scalar range
            lookup_table.SetTableValue(0, 0, 0, 0, 0)  # Background: Transparent
            lookup_table.SetTableValue(1, c[0]/255, c[1]/255, c[2]/255, self.layer_data.alpha)  # Segmentation: Red with 50% opacity
            lookup_table.Build()
            
            mapper = vtk.vtkImageMapToColors()
            mapper.SetInputData(self.layer_data.segmentation)
            mapper.SetLookupTable(lookup_table)
            mapper.Update()

            actor = self.layer_data.actor
            actor.GetMapper().SetInputConnection(mapper.GetOutputPort())

            self.manager.on_layer_changed(self.layer_name)

            self.manager.print_status(f"Color changed to ({c[0]}, {c[1]}, {c[2]})")



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
        existing_names = [name for name in self.manager.segmentation_layers.keys() if name != self.layer_name]
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
            
            self.manager.segmentation_layers[new_name] = self.manager.segmentation_layers.pop(self.layer_name)
            
            # if the current layer is the active layer, update the active layer name as well
            if self.manager.active_layer_name == self.layer_name:
                self.manager.active_layer_name = new_name
            
            self.layer_name = new_name

            self.manager.on_layer_changed(new_name)

from PyQt5.QtCore import pyqtSignal, QObject

from color_rotator import ColorRotator

class SegmentationListManager(QObject):
    # Signal to emit log messages
    log_message = pyqtSignal(str, str)  # Format: log_message(type, message)

    def __init__(self, vtk_viewer):
        super().__init__()  # Initialize QObject

        self.vtk_viewer = vtk_viewer
        self.vtk_renderer = vtk_viewer.get_renderer()
        self.active_layer_name = None

        # segmentation data
        self.segmentation_layers = {}
        self.active_layer_name = None

        self.paint_active = False
        self.paint_brush_color = [0,1,0]

        self.erase_active = False
        self.erase_brush_color = [0, 0.5, 1.0]

        self.paintbrush = None

        self.color_rotator = ColorRotator()

        self._modified = False

        logger.info("SegmentationListManager initialized")

    def reset_modified(self):
        self._modified = False
        for _, data in self.segmentation_layers.items():
            data.modified = False

    def modified(self):
        if self._modified:
            return True
        
        for _, data in self.segmentation_layers.items():
            if data.modified:
                return True
        
        return False


    def setup_ui(self):   
        toolbar = self.create_toolbar()
        dock = self.create_dock_widget()
        return None, dock

    def create_toolbar(self):
        
        from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QIcon
        from labeled_slider import LabeledSlider

        # Create a toolbar
        toolbar = QToolBar("PaintBrush Toolbar")
     

        # Add Paint Tool button
        self.paint_action, self.paint_button = self.create_checkable_button("Paint", self.paint_active, toolbar, self.toggle_paint_tool)
        self.erase_action, self.erase_button = self.create_checkable_button("Erase", self.erase_active, toolbar, self.toggle_erase_tool)

        # paintbrush size slider
        self.brush_size_slider = LabeledSlider("Brush Size:", initial_value=20)
        self.brush_size_slider.slider.setMinimum(3)
        self.brush_size_slider.slider.setMaximum(100)
        self.brush_size_slider.slider.valueChanged.connect(self.update_brush_size)
        toolbar.addWidget(self.brush_size_slider)

        return toolbar
    
    def create_dock_widget(self):
        
        # Create a dockable widget
        dock = QDockWidget("Segmentations")

        # Layer manager layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        # Layer list
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.list_widget_on_current_item_changed)
       
        # Enable Reordering
        self.list_widget.setDragEnabled(True)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDropIndicatorShown(True)
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
       
        main_layout.addWidget(self.list_widget)

        # Buttons to manage layers
        button_layout = QHBoxLayout()

        add_layer_button = QPushButton("Add Layer")
        add_layer_button.clicked.connect(self.add_layer_clicked)
        button_layout.addWidget(add_layer_button)
        
        # Add Paint Tool button
        self.paint_action, self.paint_button = self.create_checkable_button("Paint", self.paint_active, None, self.toggle_paint_tool)
        button_layout.addWidget(self.paint_button)

        self.erase_action, self.erase_button = self.create_checkable_button("Erase", self.erase_active, None, self.toggle_erase_tool)
        button_layout.addWidget(self.erase_button)

        # Add the button layout 
        main_layout.addLayout(button_layout)
        
        from labeled_slider import LabeledSlider
        brush_size_slider = LabeledSlider("Brush Size:", initial_value=20)
        brush_size_slider.slider.setMinimum(3)
        brush_size_slider.slider.setMaximum(100)
        brush_size_slider.slider.valueChanged.connect(self.update_brush_size)
        main_layout.addWidget(brush_size_slider)
        
        # Set layout for the layer manager
        main_widget.setLayout(main_layout)
        
        dock.setWidget(main_widget)

        return dock

    def get_exclusive_actions(self):
        return [self.paint_action, self.erase_action]
    
    def clear(self):
        
        # remove actors
        for layer_name, layer_data in self.segmentation_layers.items():
            print(f"removing actor of layer {layer_name}")
            actor = layer_data.actor
            self.vtk_renderer.RemoveActor(actor)    
        
        self.vtk_image = None
        self._modified = False
        self.segmentation_layers.clear()
        self.list_widget.clear()


    def save_segmentation_layer(self, segmentation, file_path):
        from itkvtk import save_vtk_image_using_sitk
        save_vtk_image_using_sitk(segmentation, file_path)

    def save_state(self,data_dict, data_dir):
        # Save segmentation layers as '.mha'
        data_dict["segmentations"] = {}

        for layer_name, layer_data in self.segmentation_layers.items():
            segmentation_file = f"{layer_name}.mhd"
            segmentation_path = os.path.join(data_dir, segmentation_file )
            self.save_segmentation_layer(layer_data.segmentation, segmentation_path)

            # Add layer metadata to the workspace data
            data_dict["segmentations"][layer_name] = {
                "file": segmentation_file,
                "color": list(layer_data.color),
                "alpha": layer_data.alpha,
            }

    def load_state(self, data_dict, data_dir, aux_data):
        import os

        self.clear()

        self.vtk_image = aux_data['base_image']

        # Load segmentation layers
        from itkvtk import load_vtk_image_using_sitk
        for layer_name, layer_metadata in data_dict.get("segmentations", {}).items():
            seg_path = os.path.join(data_dir, layer_metadata["file"])
            if os.path.exists(seg_path):
                try:
                    vtk_seg = load_vtk_image_using_sitk(seg_path)

                    self.add_layer(
                        segmentation=vtk_seg,
                        layer_name=layer_name,
                        color_vtk=to_vtk_color(layer_metadata["color"]),
                        alpha=layer_metadata["alpha"]
                    )
                    
                except Exception as e:
                    self.print_status(f"Failed to load segmentation layer {layer_name}: {e}")
            else:
                self.print_status(f"Segmentation file for layer {layer_name} not found.")

    def render(self):
        self.vtk_renderer.GetRenderWindow().Render()

    def on_layer_changed(self, layer_name):
        self._modified = True
        self.render()

    def get_active_layer(self):
        return self.segmentation_layers.get(self.active_layer_name, None)

    def enable_paintbrush(self, enabled=True):
        
        if self.paintbrush is None:
            self.paintbrush = PaintBrush()
            self.paintbrush.set_radius_in_pixel(radius_in_pixel=(20, 20), pixel_spacing=self.vtk_viewer.vtk_image.GetSpacing())
            self.vtk_viewer.get_renderer().AddActor(self.paintbrush.get_actor())

        self.paintbrush.enabled = enabled

        interactor = self.vtk_viewer.interactor 
        if enabled:
            self.left_button_press_observer = interactor.AddObserver("LeftButtonPressEvent", self.on_left_button_press)
            self.mouse_move_observer = interactor.AddObserver("MouseMoveEvent", self.on_mouse_move)
            self.left_button_release_observer = interactor.AddObserver("LeftButtonReleaseEvent", self.on_left_button_release)
        else:    
            interactor.RemoveObserver(self.left_button_press_observer)
            interactor.RemoveObserver(self.mouse_move_observer)
            interactor.RemoveObserver(self.left_button_release_observer)   
        
        self.left_button_is_pressed = False
        self.last_mouse_position = None
        
        print(f"Painbrush mode: {'enabled' if enabled else 'disabled'}")


    def paint_at_mouse_position(self):
        
        vtk_viewer = self.vtk_viewer
        vtk_image = vtk_viewer.vtk_image
        
        mouse_pos = vtk_viewer.interactor.GetEventPosition()
        picker = vtk.vtkWorldPointPicker()
        picker.Pick(mouse_pos[0], mouse_pos[1], 0, vtk_viewer.get_renderer())
        world_pos = picker.GetPickPosition()

        print(f"World position: ({world_pos[0]:.2f}, {world_pos[1]:.2f}, {world_pos[2]:.2f})"
              f"Mouse position: ({mouse_pos[0]:.2f}, {mouse_pos[1]:.2f})")
        
        dims = vtk_image.GetDimensions()
        spacing = vtk_image.GetSpacing()
        origin = vtk_image.GetOrigin()

        print(f"Image dimensions: {dims}")
        print(f"Image spacing: {spacing}")
        print(f"Image origin: {origin}")

        x = int((world_pos[0] - origin[0]) / spacing[0] + 0.49999999)
        y = int((world_pos[1] - origin[1]) / spacing[1] + 0.49999999)


        if not (0 <= x < dims[0] and 0 <= y < dims[1]):
            print(f"Point ({x}, {y}) is outside the image bounds.")
            return

        layer = self.get_active_layer()
        if layer is None:
            print("No active layer selected.")
            return

        segmentation = layer.segmentation
        
        # paint or erase
        if self.paint_active:
            value = 1
        else:
            value = 0

        self.paintbrush.paint(segmentation, x, y, value)
        
        segmentation.Modified() # flag vtkImageData as Modified to update the pipeline.
        
        self._modified = True
        self.render()

    def on_left_button_press(self, obj, event):
        if not self.paintbrush.enabled:
            return
        
        self.left_button_is_pressed = True
        self.last_mouse_position = self.vtk_viewer.interactor.GetEventPosition()
        
        if self.left_button_is_pressed and self.paintbrush.enabled and self.active_layer_name is not None:
            print('paint...')
            self.paint_at_mouse_position()
       
    def on_mouse_move(self, obj, event):
        if not self.paintbrush.enabled:
            return

        if self.paintbrush.enabled:
            mouse_pos = self.vtk_viewer.interactor.GetEventPosition()
            picker = vtk.vtkWorldPointPicker()
            picker.Pick(mouse_pos[0], mouse_pos[1], 0, self.vtk_viewer.get_renderer())

            # Get world position
            world_pos = picker.GetPickPosition()

            # Update the brush position (ensure Z remains on the image plane + 0.1 to show on top of the image)
            self.paintbrush.get_actor().SetPosition(world_pos[0], world_pos[1], world_pos[2] + 0.1)
            self.paintbrush.get_actor().SetVisibility(True)  # Make the brush visible

            if self.paint_active:
                self.paintbrush.set_color(self.paint_brush_color)
            else:
                self.paintbrush.set_color(self.erase_brush_color)

            # Paint 
            if self.left_button_is_pressed and self.paintbrush.enabled and self.active_layer_name is not None:
                print('paint...')
                self.paint_at_mouse_position()
        else:
            self.paintbrush.get_actor().SetVisibility(False)  # Hide the brush when not painting
       
    def on_left_button_release(self, obj, event):
        if not self.paintbrush.enabled:
            return
        
        self.left_button_is_pressed = False
        self.last_mouse_position = None

    def create_checkable_button(self, label, checked, toolbar, on_toggled_fn):
        action = QAction(label)
        action.setCheckable(True)  # Make it togglable
        action.setChecked(checked)  # Sync with initial state
        #action.triggered.connect(on_click_fn)
        action.toggled.connect(on_toggled_fn)

        # Create a QToolButton for the action
        button = QToolButton(toolbar)
        button.setCheckable(True)
        button.setChecked(checked)
        button.setDefaultAction(action)

        # add to the toolbar
        if toolbar is not None:
            toolbar.addWidget(button)

        return action, button
 
    def update_button_style(self, button, checked):
        """Update the button's style to dim or brighten the icon."""
        if checked:
            button.setStyleSheet("QToolButton { opacity: 1.0; }")  # Normal icon
        else:
            button.setStyleSheet("QToolButton { opacity: 0.5; }")  # Dimmed icon

    def update_brush_size(self, value):
        self.paintbrush.set_radius_in_pixel(
            radius_in_pixel=(value, value), 
            pixel_spacing=self.get_base_image().GetSpacing())


    def list_widget_on_current_item_changed(self, current, previous):
        if current:
            # Retrieve the custom widget associated with the current QListWidgetItem
            item_widget = self.list_widget.itemWidget(current)
            
            if item_widget and isinstance(item_widget, SegmentationListItemWidget):
                # Access the layer_name from the custom widget
                layer_name = item_widget.layer_name
                if self.active_layer_name != layer_name:
                    self.active_layer_name = layer_name
                    self.print_status(f"Layer {layer_name} selected")
                    

    def toggle_paint_tool(self, checked):
        
        # no change, just return
        if self.paint_active == checked:
            return 
        
        # turn off both
        self.erase_action.setChecked(False)
        self.paint_action.setChecked(False)

        self.paint_active = checked
        self.paint_action.setChecked(checked)
        
        if self.paint_active:
            self.print_status("Paint tool activated")
        else:
            self.print_status("Paint tool deactivated")

        self.enable_paintbrush(self.paint_active or self.erase_active)

    def toggle_erase_tool(self, checked):
        
        # no change, just return
        if self.erase_active == checked:
            return 

        # turn off both
        self.erase_action.setChecked(False)
        self.paint_action.setChecked(False)

        self.erase_active = checked
        self.erase_action.setChecked(checked)

        if self.erase_active:
            self.print_status("Erase tool activated")
        else:
            self.print_status("Erase tool deactivated")    

        self.enable_paintbrush(self.paint_active or self.erase_active)

    def get_status_bar(self):
        return self._mainwindow.status_bar
    
    def print_status(self, msg):
        #if self.get_status_bar() is not None:
        #    self.get_status_bar().showMessage(msg)
    
        """
        Emit a log message with the specified type.
        log_type can be INFO, WARNING, ERROR, etc.
        """
        log_type = "INFO"
        self.log_message.emit(log_type, msg)

    def add_layer_widget_item(self, layer_name, layer_data):

        # Create a custom widget for the layer
        layer_item_widget = SegmentationListItemWidget(layer_name, layer_data, self)
        layer_item = QListWidgetItem(self.list_widget)
        layer_item.setSizeHint(layer_item_widget.sizeHint())
        self.list_widget.addItem(layer_item)
        self.list_widget.setItemWidget(layer_item, layer_item_widget) # This replaces the default text-based display with the custom widget that includes the checkbox and label.

        # set the added as active (do I need to indicate this in the list widget?)
        self.active_layer_name = layer_name
    
    def generate_unique_layer_name(self, base_name="Layer"):
        index = 1
        while f"{base_name} {index}" in self.segmentation_layers:
            index += 1
        return f"{base_name} {index}"
    
    def add_layer(self, segmentation, layer_name, color_vtk, alpha):
        actor = self.create_segmentation_actor(segmentation, color=color_vtk, alpha=alpha)
        layer_data = SegmentationItem(segmentation=segmentation, color=from_vtk_color(color_vtk), alpha=alpha, actor=actor)
        self.segmentation_layers[layer_name] = layer_data
        self.vtk_renderer.AddActor(actor)
        self.vtk_renderer.GetRenderWindow().Render()

        self.add_layer_widget_item(layer_name, layer_data)

        # Select the last item in the list widget (to activate it)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)

        self._modified = True

    def add_layer_clicked(self):

        # Generate a random bright color for the new layer
        layer_color = self.color_rotator.next()

        # add layer data        
        layer_name = self.generate_unique_layer_name()
        
        # empty segmentation
        segmentation = self.create_empty_segmentation()

        self.add_layer(
            segmentation=segmentation, 
            layer_name=layer_name, 
            color_vtk=[layer_color[0]/255, layer_color[1]/255, layer_color[2]/255],
            alpha=0.8)
        
        self.print_status(f'A layer added: {layer_name}, and active layer is now {self.active_layer_name}')
        

    def remove_segmentation_by_name(self, layer_name):
        
        if layer_name in self.segmentation_layers:
            # remove actor
            actor = self.segmentation_layers[layer_name].actor
            self.vtk_renderer.RemoveActor(actor)

            # Remove from the data list
            del self.segmentation_layers[layer_name]

            # Remove from the list widget
            item, _ = self.find_list_widget_item_by_text(layer_name)
            if item is not None:
                self.list_widget.takeItem(self.list_widget.row(item))
            else:
                logger.error(f'Internal error! List item of {layer_name} is not found!')

            # Select the last item in the list widget (to activate it)
            if layer_name == self.active_layer_name and self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(self.list_widget.count() - 1)

            self._modified = True        
        else:
            logger.error(f'Remove layer failed. the name {layer_name} given is not in the segmentation layer list')
    
    def find_list_widget_item_by_text(self, text):
        """
        Find a QListWidgetItem in the list widget based on its text.

        :param list_widget: The QListWidget instance.
        :param text: The text of the item to find.
        :return: The matching QListWidgetItem or None if not found.
        """
        list_widget = self.list_widget

        for index in range(list_widget.count()):
            item = list_widget.item(index)
            item_widget = list_widget.itemWidget(item)

            if item_widget.layer_name == text:
                return item, item_widget
        return None

    def remove_layer_clicked(self):
        #if len(self.list_widget) == 1:
        #        self.print_status("At least 1 layer is required.")
        #        return 

        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            widget = self.list_widget.itemWidget(item)
            layer_name = widget.layer_name
            self.remove_layer(layer_name)

        # render
        self.vtk_renderer.GetRenderWindow().Render()    

        self._modified = True

        self.print_status(f"Selected layers removed successfully. The acive layer is now {self.active_layer_name}")


    def toggle_visibility(self):
        """Toggle the visibility of the selected layer."""
        current_item = self.list_widget.currentItem()
        if current_item:
            layer_name = current_item.text()
            actor = self.segments[layer_name]['actor']
            visibility = actor.GetVisibility()
            actor.SetVisibility(not visibility)
            print(f"Toggled visibility for layer: {layer_name} (Visible: {not visibility})")

    def get_base_image(self):
        return self.vtk_viewer.vtk_image
    
    def create_empty_segmentation(self):
        """Create an empty segmentation as vtkImageData with the same geometry as the base image."""
        
        image_data = self.get_base_image() 
        
        if image_data is None:
            raise ValueError("Base image data is not loaded. Cannot create segmentation.")

        # Get properties from the base image
        dims = image_data.GetDimensions()
        spacing = image_data.GetSpacing()
        origin = image_data.GetOrigin()
        direction_matrix = image_data.GetDirectionMatrix()

        # Create a new vtkImageData object for the segmentation
        segmentation = vtk.vtkImageData()
        segmentation.SetDimensions(dims)
        segmentation.SetSpacing(spacing)
        segmentation.SetOrigin(origin)
        segmentation.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)  # Single component for segmentation
        segmentation.GetPointData().GetScalars().Fill(0)  # Initialize with zeros

        # Set the direction matrix if supported
        if hasattr(segmentation, 'SetDirectionMatrix') and direction_matrix is not None:
            segmentation.SetDirectionMatrix(direction_matrix)

        return segmentation

    def create_segmentation_actor(self, segmentation, color=(1, 0, 0), alpha=0.8):
        """Create a VTK actor for a segmentation layer."""
        # Create a lookup table for coloring the segmentation
        lookup_table = vtk.vtkLookupTable()
        lookup_table.SetNumberOfTableValues(2)  # For 0 (background) and 1 (segmentation)
        lookup_table.SetTableRange(0, 1)       # Scalar range
        lookup_table.SetTableValue(0, 0, 0, 0, 0)  # Background: Transparent
        lookup_table.SetTableValue(1, color[0], color[1], color[2], alpha)  # Segmentation: Red with 50% opacity
        lookup_table.Build()
        
        mapper = vtk.vtkImageMapToColors()
        mapper.SetInputData(segmentation)
        mapper.SetLookupTable(lookup_table)
        mapper.Update()

        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputConnection(mapper.GetOutputPort())
              
        return actor


import vtk
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QDockWidget, QColorDialog, QLabel, QLineEdit, QCheckBox, QListWidgetItem
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QColor

class PointItem:
    def __init__(self, coordinates, color=[255, 0, 0], visible=True, renderer=None, interactor=None):
        self.coordinates = coordinates
        self.color = color
        self.visible = visible
        self.modified = False

        # Create a handle representation
        self.representation = vtk.vtkPointHandleRepresentation3D()
        self.representation.SetWorldPosition(self.coordinates)
        self.representation.SetHandleSize(20.0)
        self.representation.GetProperty().SetLineWidth(3.0)
        self.representation.GetProperty().SetColor(color[0] / 255, color[1] / 255, color[2] / 255)

        # Create a handle widget
        self.widget = vtk.vtkHandleWidget()
        self.widget.SetRepresentation(self.representation)

        # Add observer for position change
        self.widget.AddObserver("InteractionEvent", self.on_position_changed)

        # Add the widget to the interactor
        if interactor:
            self.widget.SetInteractor(interactor)
            self.widget.EnabledOn()

    def set_highlight(self, highlighted):
        if highlighted:
            #self.representation.SetHandleSize(20.0)
            self.representation.GetProperty().SetLineWidth(6.0)
        else: 
            #self.representation.SetHandleSize(10.0)
            self.representation.GetProperty().SetLineWidth(3.0)

    def set_visibility(self, visible):
        self.widget.EnabledOn() if visible else self.widget.EnabledOff()

    def on_position_changed(self, obj, event):
        self.coordinates = list(self.representation.GetWorldPosition())
        self.modified = True
        print(f"Point moved to: {self.coordinates}")


class PointListItemWidget(QWidget):
    def __init__(self, name, point, manager):
        super().__init__()
        self.manager = manager
        self.point = point
        self.name = name

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Checkbox for visibility
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.point.visible)
        self.checkbox.stateChanged.connect(self.toggle_visibility)
        self.layout.addWidget(self.checkbox)

        # Color patch for the point
        self.color_patch = QLabel()
        self.color_patch.setFixedSize(16, 16)  # Small square
        self.color_patch.setStyleSheet(f"background-color: {self.get_color_hex_string()}; border: 1px solid black;")
        self.color_patch.setCursor(Qt.PointingHandCursor)
        self.color_patch.mousePressEvent = self.change_color_clicked
        self.layout.addWidget(self.color_patch)

        # Label for the point name
        self.label = QLabel(name)
        self.label.setCursor(Qt.PointingHandCursor)
        self.label.mouseDoubleClickEvent = self.activate_name_editor
        self.layout.addWidget(self.label)

        # Editable name field
        self.edit_name = QLineEdit(name)
        self.edit_name.setToolTip("Edit the point name (must be unique and file-system compatible).")
        self.edit_name.hide()  # Initially hidden
        self.edit_name.returnPressed.connect(self.deactivate_name_editor)
        self.edit_name.editingFinished.connect(self.deactivate_name_editor)
        self.edit_name.textChanged.connect(self.validate_name)
        self.layout.addWidget(self.edit_name)

        # Remove button (with 'x')
        self.remove_button = QPushButton("X")
        self.remove_button.setMinimumSize(25, 25)  # Adjust size for better appearance
        self.remove_button.setToolTip("Remove this point")
        self.remove_button.clicked.connect(self.remove_point_clicked)
        self.layout.addWidget(self.remove_button, alignment=Qt.AlignCenter)

        self.setLayout(self.layout)

    def remove_point_clicked(self):
        """Remove the layer when the 'x' button is clicked."""
        self.manager.remove_point_by_name(self.name)

    def toggle_visibility(self, state):
        self.point.visible = state == Qt.Checked
        self.point.set_visibility(self.point.visible)
        self.manager.on_point_changed(self.name)

    def get_color_hex_string(self):
        color = self.point.color
        return f"rgb({color[0]}, {color[1]}, {color[2]})"

    def change_color_clicked(self, event):
        current_color = QColor(self.point.color[0], self.point.color[1], self.point.color[2])
        color = QColorDialog.getColor(current_color, self, "Select Point Color")

        if color.isValid():
            c = [color.red(), color.green(), color.blue()]
            self.point.color = c
            self.color_patch.setStyleSheet(f"background-color: {self.get_color_hex_string()}; border: 1px solid black;")
            self.point.representation.GetProperty().SetColor(c[0] / 255, c[1] / 255, c[2] / 255)
            self.manager.on_point_changed(self.name)

    def activate_name_editor(self, event):
        self.label.hide()
        self.edit_name.setText(self.label.text())
        self.edit_name.show()
        self.edit_name.setFocus()
        self.edit_name.selectAll()

    def deactivate_name_editor(self):
        new_name = self.edit_name.text()
        self.validate_name()

        if self.edit_name.toolTip() == "":
            self.label.setText(new_name)
            self.name = new_name

        self.label.show()
        self.edit_name.hide()

    def validate_name(self):
        print('==== validate_name() ====')
        new_name = self.edit_name.text()

        print(f'new_name={new_name}')
        invalid_chars = r'<>:"/\\|?*'
        if any(char in new_name for char in invalid_chars) or new_name.strip() == "":
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")
            self.edit_name.setToolTip("Point name contains invalid characters or is empty.")
            print("Point name contains invalid characters or is empty.")
            return

        existing_names = [name for name in self.manager.points.keys() if name != self.name]
        print(f'existing_names={existing_names}')
        if new_name in existing_names:
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")
            self.edit_name.setToolTip("Point name must be unique.")
            return

        self.edit_name.setStyleSheet("")
        self.edit_name.setToolTip("")

        self.update_point_name(new_name)
        self.name = new_name
        self.label.setText(new_name)
    
    def update_point_name(self, new_name):
        """Update the layer name in the viewer."""
        if new_name != self.name:
            
            self.manager.points[new_name] = self.manager.points.pop(self.name)
            
            # if the current layer is the active layer, update the active layer name as well
            if self.manager.active_point_name == self.name:
                self.manager.active_point_name = new_name
            
            self.name = new_name

            self.manager.on_point_changed(new_name)


class PointListManager(QObject):
    log_message = pyqtSignal(str, str)  # For emitting log messages

    def __init__(self, vtk_viewer):
        super().__init__()
        self.vtk_viewer = vtk_viewer
        self.vtk_renderer = vtk_viewer.get_renderer()
        self.points = {}  # List of Point objects
        self.active_point_name = None

        self._modified = False

        self.color_rotator = ColorRotator()

    def reset_modified(self):
        self._modified = False
        for _, data in self.points.items():
            data.modified = False


    def modified(self):
        if self._modified:
            return True

        for name, point in self.points.items():
            if point.modified:
                return True
            
        return False

    def setup_ui(self):
        """Set up the UI with a dockable widget."""
        dock = QDockWidget("Points")
        widget = QWidget()
        layout = QVBoxLayout()

        # List widget for points
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.on_current_item_changed)
        layout.addWidget(self.list_widget)

        # Buttons to manage points
        button_layout = QHBoxLayout()
        add_point_button = QPushButton("Add Point")
        add_point_button.clicked.connect(self.add_point_clicked)
        button_layout.addWidget(add_point_button)

        edit_point_button = QPushButton("Edit Points")
        edit_point_button.clicked.connect(self.edit_points_clicked)
        button_layout.addWidget(edit_point_button)

        layout.addLayout(button_layout)
        widget.setLayout(layout)
        dock.setWidget(widget)

        # no toolbar
        toolbar = None

        return toolbar, dock

    def get_exclusive_actions(self):
        return []

    def generate_unique_name(self, base_name="Point"):
        index = 1
        while f"{base_name} {index}" in self.points:
            index += 1
        return f"{base_name} {index}"
    
    def add_point(self, coordinates, color=[255, 0, 0], visible=True, name=None):
        """Add a new editable point."""
        editable_point = PointItem(
            coordinates=coordinates,
            color=color,
            visible=visible,
            renderer=self.vtk_renderer,
            interactor=self.vtk_viewer.interactor
        )

        if name is None:
            name = self.generate_unique_name()

        self.points[name]= editable_point

        item_widget = PointListItemWidget(name, editable_point, self)
        item = QListWidgetItem()
        item.data = editable_point
        item.setSizeHint(item_widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, item_widget)
        self.list_widget.setCurrentItem(item)
        
        self._modified = True

        self.log_message.emit("INFO", f"Added point at {coordinates}")

    def edit_points_clicked(self):
        """Toggle editing mode for points."""
        self.editing_points_enabled = not self.editing_points_enabled
        for point in self.points:
            point.set_visibility(self.editing_points_enabled)
        self.log_message.emit("INFO", f"Point editing {'enabled' if self.editing_points_enabled else 'disabled'}.")

    def on_point_changed(self, name):
        self._modified = True
        self.vtk_renderer.GetRenderWindow().Render()

    def edit_point(self, index, new_coordinates=None, new_color=None, new_visibility=None):
        """Edit a point's properties."""
        if index is not None and 0 <= index < len(self.points):
            point = self.points[index]

            if new_coordinates:
                point.coordinates = new_coordinates
                point.actor.SetPosition(*new_coordinates)

            if new_color:
                point.color = new_color
                point.actor.GetProperty().SetColor(new_color[0] / 255, new_color[1] / 255, new_color[2] / 255)

            if new_visibility is not None:
                point.visible = new_visibility
                point.actor.SetVisibility(new_visibility)

            point.modified = True
            self._modified = True
            self.vtk_viewer.get_render_window().Render()
            self.log_message.emit("INFO", f"Edited point {index}")


    def on_current_item_changed(self, current, previous):
        """Handle point selection in the list widget."""
        if current:
            # Retrieve the custom widget associated with the current QListWidgetItem
            item_widget = self.list_widget.itemWidget(current)
            
            if item_widget and isinstance(item_widget, PointListItemWidget):

                point = item_widget.point
                name = item_widget.name

                # turn off all others    
                for key in self.points:
                    p = self.points[key]
                    if p is not point:
                        p.set_highlight(False)
                    
                # turn on the selected point
                point.set_highlight(True)

                if self.active_point_name != name:
                    self.active_point_name = name
                    print(f"Point {name} selected")

                self.vtk_renderer.GetRenderWindow().Render()

    def add_point_clicked(self):
        """Handle the 'Add Point' button click."""
        # Add a point at the center of the current view
        camera = self.vtk_renderer.GetActiveCamera()
        focal_point = camera.GetFocalPoint()
        
        # move closer to camera, so that it's visible.
        focal_point = [focal_point[0], focal_point[1], focal_point[2]+1.0]
        
        name = self.generate_unique_name()

        self.add_point(coordinates=focal_point, color=self.color_rotator.next(), visible=True, name=name)

        self._modified = True

    

    def remove_point_by_name(self, name):
        
        if name in self.points:
            
            item, item_widget = self.find_list_widget_item_by_text(name)

            if item is not None:
                point = item_widget.point

                # Disable the point's widget and remove it
                from vtk_tools import remove_widget
                remove_widget(point.widget, self.vtk_renderer)
                #point.widget.EnabledOff()

                # Remove from the data list
                del self.points[name]

                # Remove from the list widget
                self.list_widget.takeItem(self.list_widget.row(item))

                # Select the last item in the list widget (to activate it)
                if name == self.active_point_name and self.list_widget.count() > 0:
                    self.list_widget.setCurrentRow(self.list_widget.count() - 1)
            
                self._modified = True
            else:
                logger.error(f'List item of name {name} not found!')
        else:
            logger.error(f'Remove point failed. the point with name {name} in the point list')
    
    def find_list_widget_item_by_text(self, text):
        """
        Find a QListWidgetItem in the list widget based on its text.

        :param list_widget: The QListWidget instance.
        :param text: The text of the item to find.
        :return: The matching QListWidgetItem or None if not found.
        """
        list_widget = self.list_widget

        for index in range(list_widget.count()):
            item = list_widget.item(index)
            item_widget = list_widget.itemWidget(item)

            if item_widget.name == text:
                return item, item_widget
        return None

    def save_state(self, data_dict, data_dir):
        """Save points to the state dictionary."""
        points_data = []
        for name in self.points:
            point = self.points[name]
            points_data.append({
                "name": name,
                "coordinates": point.coordinates,
                "color": point.color,
            })
        data_dict["points"] = points_data

    def load_state(self, data_dict, data_dir, aux_data):
        """Load points from the state dictionary."""
        self.clear()
        for point_data in data_dict.get("points", []):
            self.add_point(
                coordinates=point_data["coordinates"],
                color=point_data["color"],
                visible= True,
                name=point_data["name"]
            )
        
    def clear(self):
        """Clear all points."""
        for name in self.points:
            point = self.points[name]
            # Disable the point's widget and remove it
            point.widget.EnabledOff()

        self.points = {}
        self._modified = False
        self.list_widget.clear()
        self.vtk_viewer.get_render_window().Render()


def is_dicom(file_path):
    import pydicom 

    """Check if the file is a valid DICOM file using pydicom."""
    try:
        # Attempt to read the file as a DICOM
        ds = pydicom.dcmread(file_path, stop_before_pixels=True)
        # If no exception occurs, it's a valid DICOM
        return True
    except pydicom.errors.InvalidDicomError:
        return False
    except Exception as e:
        print(f"Error reading file: {e}")
        return False

from PyQt5.QtWidgets import QMessageBox

from PyQt5.QtCore import QSettings
settings = QSettings("_settings.conf", QSettings.IniFormat)
     
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # exclusive QActions
        self.exclusive_actions = []
        self.managers = []
        self.vtk_image = None

        ### init ui ###    
        self.setup_ui()

        ##########################
        # Segmentation List Manager
        self.segmentation_list_manager = SegmentationListManager(self.vtk_viewer)
        toolbar, dock = self.segmentation_list_manager.setup_ui()
        if toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, toolbar)
        if dock is not None:
            self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.add_exclusive_actions(self.segmentation_list_manager.get_exclusive_actions()) 
        self.segmentation_list_manager.log_message.connect(self.handle_log_message) # Connect log messages to a handler
        self.managers.append(self.segmentation_list_manager)
        self.segmentation_list_dock_widget = dock

        ##########################
        # Point List Manager
        self.point_list_manager = PointListManager(self.vtk_viewer)
        toolbar, dock = self.point_list_manager.setup_ui()
        if toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, toolbar)
        if dock is not None:
            self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.add_exclusive_actions(self.point_list_manager.get_exclusive_actions())
        self.point_list_manager.log_message.connect(self.handle_log_message) # Connect log messages to a handler
        self.managers.append(self.point_list_manager)
        self.point_list_dock_widget = dock

        self.tabifyDockWidget(self.segmentation_list_dock_widget, self.point_list_dock_widget)

        ##########################
        # Line List Manager
        self.line_list_manager = LineListManager(self.vtk_viewer)
        toolbar, dock = self.line_list_manager.setup_ui()
        if toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, toolbar)
        if dock is not None:
            self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.add_exclusive_actions(self.line_list_manager.get_exclusive_actions())
        self.line_list_manager.log_message.connect(self.handle_log_message) # Connect log messages to a handler
        self.managers.append(self.line_list_manager)
        self.line_list_dock_widget = dock

        self.tabifyDockWidget(self.segmentation_list_dock_widget, self.line_list_dock_widget)

        # Load a sample DICOM file
        #dicom_file = "./data/jaw_cal.dcm"
        #self.load_dicom(dicom_file)

        logger.info("MainWindow initialized")

    def closeEvent(self, event):
        """
        Override the closeEvent to log application or window close.
        """
        logger.info("MainWindow is closing.")

        

        super().closeEvent(event)  # Call the base class method to ensure proper behavior


    def setup_ui(self):
        self.setWindowTitle("Image Labeler 2D")
        self.setGeometry(100, 100, 1024, 786)

        self.main_widget = QWidget()
        self.layout = QVBoxLayout()

        # VTK Viewer
        self.vtk_viewer = VTKViewer(parent = self, main_window = self)
        self.layout.addWidget(self.vtk_viewer)

        self.main_widget.setLayout(self.layout)
        self.setCentralWidget(self.main_widget)

        # Add the File menu
        self.create_menu()
        self.create_file_toolbar()
        self.create_view_toolbar()

        # Add status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")  # Initial message

    def handle_log_message(self, log_type, message):
        """
        Handle log messages emitted by SegmentationListManager.
        """
        if log_type == "INFO":
            self.status_bar.showMessage(message)
            logger.info(message)  # Log the message
        elif log_type == "WARNING":
            self.status_bar.showMessage(f"WARNING: {message}")
            logger.warning(message)  # Log the warning
            self.show_popup("Warning", message, QMessageBox.Warning)
        elif log_type == "ERROR":
            self.status_bar.showMessage(f"ERROR: {message}")
            logger.error(message)  # Log the error
            self.show_popup("Error", message, QMessageBox.Critical)
        else:
            logger.debug(f"{log_type}: {message}")
            self.status_bar.showMessage(f"{log_type}: {message}")

    def show_popup(self, title, message, icon=None):
        """
        Display a QMessageBox with the specified title, message, and icon.
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)

        if icon is None:
            icon = QMessageBox.Information
            
        msg_box.setIcon(icon)
        
        msg_box.exec_()

    def on_exclusiave_action_clicked(self):
        
        sender = self.sender()

        # Check if the sender is a QAction and retrieve its text
        if isinstance(sender, QAction):
            print(f"Exclusive action clicked: {sender.text()}")
        else:
            print("The sender is not a QAction.")

        # Get the QAction that triggered this signal
        sender = self.sender()

        # uncheck all other actions
        for action in self.exclusive_actions:
            if action is not sender:
                action.setChecked(False)

    def add_exclusive_actions(self, actions):
        for action in actions:
            self.exclusive_actions.append(action)
            action.triggered.connect(self.on_exclusiave_action_clicked)

    def print_status(self, msg):
        self.status_bar.showMessage(msg)

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
        
        from PyQt5.QtWidgets import QAction
        
        # Add Open Image action
        open_image_action = QAction("Import Image", self)
        open_image_action.triggered.connect(self.import_image_clicked)
        file_menu.addAction(open_image_action)

        # Add Save Workspace action
        open_workspace_action = QAction("Open Workspace", self)
        open_workspace_action.triggered.connect(self.open_workspace)
        file_menu.addAction(open_workspace_action)

        # Add Save Workspace action
        save_workspace_action = QAction("Save Workspace", self)
        save_workspace_action.triggered.connect(self.save_workspace)
        file_menu.addAction(save_workspace_action)

        # Add Open Image action
        close_image_action = QAction("Close Workspace", self)
        close_image_action.triggered.connect(self.close_workspace)
        file_menu.addAction(close_image_action)

        # Print Object Properties Button
        print_objects_action = QAction("Print Object Properties", self)
        print_objects_action.triggered.connect(self.vtk_viewer.print_properties)
        file_menu.addAction(print_objects_action)
        
    def create_view_menu(self, view_menu):
        
        # Zoom In
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.vtk_viewer.zooming.zoom_in)
        view_menu.addAction(zoom_in_action)

        # Zoom Out
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.vtk_viewer.zooming.zoom_out)
        view_menu.addAction(zoom_out_action)

        # Zoom Reset
        zoom_reset_action = QAction("Zoom Reset", self)
        zoom_reset_action.triggered.connect(self.vtk_viewer.zooming.zoom_reset)
        view_menu.addAction(zoom_reset_action)
        
        # Add Toggle Button
        toggle_image_button = QAction("Toggle Base Image", self)
        toggle_image_button.setCheckable(True)
        toggle_image_button.setChecked(True)
        toggle_image_button.triggered.connect(self.vtk_viewer.toggle_base_image)
        view_menu.addAction(toggle_image_button)


    def create_file_toolbar(self):
        # Create a toolbar
        toolbar = QToolBar("File Toolbar", self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Add actions to the toolbar
        # Add Open DICOM action
        open_image_action = QAction("Import Image", self)
        open_image_action.triggered.connect(self.import_image_clicked)
        toolbar.addAction(open_image_action)

        # Add Save Workspace action
        open_workspace_action = QAction("Open Workspace", self)
        open_workspace_action.triggered.connect(self.open_workspace)
        toolbar.addAction(open_workspace_action)

        save_workspace_action = QAction("Save Workspace", self)
        save_workspace_action.triggered.connect(self.save_workspace)
        toolbar.addAction(save_workspace_action)

        close_image_action = QAction("Close Workspace", self)
        close_image_action.triggered.connect(self.close_workspace)
        toolbar.addAction(close_image_action)

    def create_view_toolbar(self):
        from labeled_slider import LabeledSlider
        from rangeslider import RangeSlider

        # Create a toolbar
        toolbar = QToolBar("View Toolbar", self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Add a label for context
        toolbar.addWidget(QLabel("Window/Level:", self))

        # Replace two QSliders with a RangeSlider for window and level
        self.range_slider = RangeSlider(self)
        self.range_slider.setFixedWidth(200)  # Adjust size for the toolbar
        self.range_slider.rangeChanged.connect(self.update_window_level)
        toolbar.addWidget(self.range_slider)
        
        # zoom in action
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.vtk_viewer.zooming.zoom_in)
        toolbar.addAction(zoom_in_action)    
        
         # zoom out action
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.vtk_viewer.zooming.zoom_out)
        toolbar.addAction(zoom_out_action)    

        # zoom reset button
        zoom_reset_action = QAction("Zoom Reset", self)
        zoom_reset_action.triggered.connect(self.vtk_viewer.zooming.zoom_reset)
        toolbar.addAction(zoom_reset_action)        

        # zoom toggle button
        zoom_action = QAction("Zoom", self)
        zoom_action.setCheckable(True)
        zoom_action.toggled.connect(self.vtk_viewer.toggle_zooming_mode)
        toolbar.addAction(zoom_action)        

        # pan toggle button
        pan_action = QAction("Pan", self)
        pan_action.setCheckable(True)
        pan_action.toggled.connect(self.vtk_viewer.toggle_panning_mode)
        toolbar.addAction(pan_action)        

        # pad is an exclusive
        self.add_exclusive_actions([pan_action])
        
        # Add ruler toggle action
        add_ruler_action = QAction("Add Ruler", self)
        add_ruler_action.triggered.connect(self.vtk_viewer.add_ruler)
        toolbar.addAction(add_ruler_action)

    def update_window_level(self):
        if self.vtk_image is not None:
            # Update the window and level using the RangeSlider values
            window = self.range_slider.get_width()
            level = self.range_slider.get_center()

            self.vtk_viewer.window_level_filter.SetWindow(window)
            self.vtk_viewer.window_level_filter.SetLevel(level)
            self.vtk_viewer.get_render_window().Render()

            self.print_status(f"Window: {window}, Level: {level}")

    def get_list_dir(self):
        if settings.contains('last_directory'):
            return settings.value('last_directory')
        else:
            return '.'

    def import_image_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open DICOM File", self.get_list_dir(), "Medical Image Files (*.dcm *.mhd *.mha);;DICOM Files (*.dcm);;MetaImage Files (*.mhd *.mha);;All Files (*)")
        
        if file_path == '':
            return 
        
        # save to last_directory
        settings.setValue("last_directory", os.path.dirname(file_path))

        try:
            logger.info(f"Loading image from {file_path}")
            self.image_path = file_path 

            _,file_extension = os.path.splitext(file_path)
            file_extension = file_extension.lower()

            print(f"File extension: {file_extension}")  # Output: .mha      

            image_type = ""
            if file_extension == ".dcm" or is_dicom(file_path):
                # NOTE: this did not work for RTImage reading. So, using sitk to read images.
                #reader = vtk.vtkDICOMImageReader()
                from itkvtk import load_vtk_image_using_sitk
                self.vtk_image = load_vtk_image_using_sitk(file_path)
                image_type = "dicom"
            elif file_extension == ".mhd" or file_extension == ".mha":
                self.vtk_image = load_vtk_image_using_sitk(file_path)
                image_type = "meta"
            else:
                raise Exception("Only dicom or meta image formats are supported at the moment.")

            # Extract correct spacing for RTImage using pydicom
            if image_type == "dicom":
                
                import pydicom
                dicom_dataset = pydicom.dcmread(file_path)
                if hasattr(dicom_dataset, "Modality") and dicom_dataset.Modality == "RTIMAGE":

                    # Extract necessary tags
                    if hasattr(dicom_dataset, "ImagePlanePixelSpacing"):
                        pixel_spacing = dicom_dataset.ImagePlanePixelSpacing  # [row spacing, column spacing]
                    else:
                        raise ValueError("RTImage is missing ImagePlanePixelSpacing")

                    if hasattr(dicom_dataset, "RadiationMachineSAD"):
                        SAD = float(dicom_dataset.RadiationMachineSAD)
                    else:
                        raise ValueError("RTImage is missing RadiationMachineSAD")

                    if hasattr(dicom_dataset, "RTImageSID"):
                        SID = float(dicom_dataset.RTImageSID)
                    else:
                        raise ValueError("RTImage is missing RTImageSID")

                    # Scale pixel spacing to SAD scale
                    scaling_factor = SAD / SID
                    scaled_spacing = [spacing * scaling_factor for spacing in pixel_spacing]

                    # Update spacing in vtkImageData
                    self.vtk_image.SetSpacing(scaled_spacing[1], scaled_spacing[0], 1.0)  # Column, Row, Depth

                    # Print the updated spacing
                    print(f"Updated Spacing: {self.vtk_image.GetSpacing()}")
            
            self.image_type = image_type

            # align the center of the image to the center of the world coordiante system
            # Get image properties
            dims = self.vtk_image.GetDimensions()
            spacing = self.vtk_image.GetSpacing()
            original_origin = self.vtk_image.GetOrigin()

            print('dims: ', dims)
            print('spacing: ', spacing)
            print('original_origin: ', original_origin)

            # Get the scalar range (pixel intensity range)
            scalar_range = self.vtk_image.GetScalarRange()

            self.range_slider.range_min = scalar_range[0]
            self.range_slider.range_max = scalar_range[1]
            self.range_slider.low_value = scalar_range[0]
            self.range_slider.high_value = scalar_range[1]
            self.range_slider.update()  
            
            self.vtk_viewer.set_vtk_image(self.vtk_image, self.range_slider.get_width()/4, self.range_slider.get_center())
            logger.info("Image loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load image:{e}") 
            self.show_popup("Load Image", f"Error: Load Image Failed, {str(e)}", QMessageBox.Critical)


    def modified(self):
        for manager in self.managers:
            if manager.modified():
                return True
        return False
    
    def show_yes_no_question_dialog(self, title, msg):
        # Create a message box
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)  # Set the icon to a question mark
        msg_box.setWindowTitle(title)  # Set the title of the dialog
        msg_box.setText(msg)  # Set the main message
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)  # Add Yes and No buttons
        
        # Set the default button to Yes
        msg_box.setDefaultButton(QMessageBox.Yes)
        
        # Show the dialog and get the user's response
        response = msg_box.exec_()
        
        if response == QMessageBox.Yes:
            return True
        elif response == QMessageBox.No:
            return False
            
    def close_workspace(self):

        if self.vtk_image is None:
            self.show_popup("Close Image", "No image has been loaded.")
            return 

        if self.modified():
            yes = self.show_yes_no_question_dialog("Save Workspace", "There are modified objects. Do you want to save the workspace?")

            if yes:
                self.save_workspace()
        
        for manager in self.managers:
            manager.clear()

        self.vtk_viewer.clear()

        self.image_path = None
        self.vtk_image = None
        self.image_type = None



    def save_workspace(self):
        import json
        import os
        from PyQt5.QtWidgets import QFileDialog

        """Save the current workspace to a folder."""
        if self.vtk_image is None:
            self.print_status("No image loaded. Cannot save workspace.")
            return

        # workspace json file
        workspace_json_path, _ = QFileDialog.getSaveFileName(self, "Save Workspace", "", "Json (*.json)")
        if not workspace_json_path:
            logger.info("Save workspace operation canceled by user.")
            return 
        
        # save to last_directory
        settings.setValue("last_directory", os.path.dirname(workspace_json_path))

        try:
            # data folder for the workspace
            data_dir = workspace_json_path+".data"
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                logger.debug(f"Created data directory: {data_dir}")

            # Create a metadata dictionary
            workspace_data = {
                "window_settings": {
                    "level": self.range_slider.get_center(),
                    "width": self.range_slider.get_width(),
                    "range_min" : self.range_slider.range_min,
                    "range_max" : self.range_slider.range_max
                }
            }

            # Save input image as '.mha'
            from itkvtk import save_vtk_image_using_sitk
            input_image_path = os.path.join(data_dir, "input_image.mhd")
            save_vtk_image_using_sitk(self.vtk_image, input_image_path)
            logger.info(f"Saved input image to {input_image_path}")
            
            logger.info('Saving manager states')
            for manager in self.managers:
                logger.info(f'{manager} - Saving state')
                manager.save_state(workspace_data, data_dir)

            # Save metadata as 'workspace.json'
            with open(workspace_json_path, "w") as f:
                json.dump(workspace_data, f, indent=4)
            
            # clear the modifed flags of managers
            for manager in self.managers:
                manager.reset_modified()
            
            logger.info(f"Workspace metadata saved to {workspace_json_path}.")
            self.print_status(f"Workspace saved to {workspace_json_path}.")
            self.show_popup("Save Workspace", "Workspace saved successfully.", QMessageBox.Information)
        except Exception as e:
            logger.error(f"Failed to save workspace: {e}", exc_info=True)
            self.print_status("Failed to save workspace. Check logs for details.")
            self.show_popup("Save Workspace", f"Error saving workspace: {str(e)}", QMessageBox.Critical)      

    def open_workspace(self):
        import json
        import os

        """Load a workspace from a folder."""
        workspace_json_path, _ = QFileDialog.getOpenFileName(self, "Select Workspace File", self.get_list_dir(), "JSON Files (*.json)")
        if not workspace_json_path:
           logger.info("Load workspace operation canceled by user.")
           return

        # save to last dir
        settings.setValue('last_directory', os.path.dirname(workspace_json_path))

        data_path = workspace_json_path+".data"
        if not os.path.exists(data_path):
            msg = "Workspace data folder not found."
            logger.error(msg)
            self.print_status(msg)
            return

        try:
            with open(workspace_json_path, "r") as f:
                workspace_data = json.load(f)

            logger.info(f"Loaded workspace metadata from {workspace_json_path}.")

            # Clear existing workspace
            self.vtk_image = None
            #self.point_list_manager.points.clear()

            from itkvtk import load_vtk_image_using_sitk

            # Load input image
            input_image_path = os.path.join(data_path, "input_image.mhd")
            if os.path.exists(input_image_path):
                self.vtk_image = load_vtk_image_using_sitk(input_image_path)
                logger.info(f"Loaded input image from {input_image_path}.")
            else:
                raise FileNotFoundError(f"Input image file not found at {input_image_path}")

            # Restore window settings
            window_settings = workspace_data.get("window_settings", {})
            window = window_settings.get("width", 1)
            level = window_settings.get("level", 0)

            # Get the scalar range (pixel intensity range)
            scalar_range = self.vtk_image.GetScalarRange()

            self.range_slider.range_min = scalar_range[0]
            self.range_slider.range_max = scalar_range[1]
            self.range_slider.low_value = level-window/2
            self.range_slider.high_value = level+window/2
            self.range_slider.update()  

            self.vtk_viewer.set_vtk_image(self.vtk_image, window, level)

            logger.info('loading manager states')
            for manager in self.managers:
                logger.info(f'{manager} - Loading state')
                manager.load_state(workspace_data, data_path, {'base_image': self.vtk_image})

            # clear the modifed flags of managers
            for manager in self.managers:
                manager.reset_modified()

            self.print_status(f"Workspace loaded from {data_path}.")
            logger.info("Loaded workspace successfully.")

        except Exception as e:
            logger.error(f"Failed to load workspace: {e}", exc_info=True)
            self.print_status("Failed to load workspace. Check logs for details.")



if __name__ == "__main__":
    import sys
    
    logger.info("Application started")

    app = QApplication(sys.argv)
    
    app.setWindowIcon(QIcon(brush_icon_path))  # Set application icon

    app.aboutToQuit.connect(lambda: logger.info("Application is quitting."))

    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
