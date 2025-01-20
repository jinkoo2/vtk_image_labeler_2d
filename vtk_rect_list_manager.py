import vtk
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtWidgets import (QListWidgetItem, QVBoxLayout, QPushButton, QLabel, QWidget, QDockWidget, QListWidget, QHBoxLayout, QCheckBox, QLineEdit, QColorDialog)
from PyQt5.QtGui import QColor

from logger import logger
from color_rotator import ColorRotator

class RectItem:
    def __init__(self, corner1, corner2, min_size=[1.0, 1.0], color=[255, 0, 0], visible=True, renderer=None, interactor=None):
        self.corner1 = corner1
        self.corner2 = corner2
        self.min_size = min_size
        self.color = color
        self.visible = visible
        self.modified = False

        # Compute initial rectangle corners
        self.corners = self.calculate_corners(corner1, corner2)

        # Create handles for corners
        self.handles = [self.create_handle(i, corner, color, renderer, interactor) for i, corner in enumerate(self.corners)]

        # Store renderer and interactor for updates
        self.renderer = renderer
        self.interactor = interactor

        # Create rectangle actor
        self.rect_actor = self.create_rectangle_actor()

        self.set_color(self.color)

        renderer.AddActor(self.rect_actor)

    def calculate_corners(self, corner1, corner2):
        """Calculate all four corners of the rectangle given two diagonal corners."""
        x_min, x_max = min(corner1[0], corner2[0]), max(corner1[0], corner2[0])
        y_min, y_max = min(corner1[1], corner2[1]), max(corner1[1], corner2[1])
        z = corner1[2]  # Assuming a 2D rectangle in the same Z-plane

        # Enforce minimum size constraint
        if (x_max - x_min) < self.min_size[0]:
            x_center = (x_min + x_max) / 2.0
            x_min = x_center - self.min_size[0] / 2.0
            x_max = x_center + self.min_size[0] / 2.0

        if (y_max - y_min) < self.min_size[1]:
            y_center = (y_min + y_max) / 2.0
            y_min = y_center - self.min_size[1] / 2.0
            y_max = y_center + self.min_size[1] / 2.0

        return [
            [x_min, y_min, z],  # Bottom-left
            [x_max, y_min, z],  # Bottom-right
            [x_max, y_max, z],  # Top-right
            [x_min, y_max, z],  # Top-left
        ]

    def create_handle(self, index, position, color, renderer, interactor):
        """Create a handle at a given position."""
        handle_rep = vtk.vtkPointHandleRepresentation3D()
        handle_rep.SetWorldPosition(position)
        handle_rep.GetProperty().SetColor(color[0] / 255, color[1] / 255, color[2] / 255)

        handle_widget = vtk.vtkHandleWidget()
        handle_widget.SetRepresentation(handle_rep)
        handle_widget.SetInteractor(interactor)
        handle_widget.On()

        # Attach different interaction event handlers based on corner index
        if index == 0:  # Bottom-left
            handle_widget.AddObserver("InteractionEvent", self.update_bottom_left)
        elif index == 1:  # Bottom-right
            handle_widget.AddObserver("InteractionEvent", self.update_bottom_right)
        elif index == 2:  # Top-right
            handle_widget.AddObserver("InteractionEvent", self.update_top_right)
        elif index == 3:  # Top-left
            handle_widget.AddObserver("InteractionEvent", self.update_top_left)

        return handle_widget

    def create_rectangle_actor(self):
        """Create the rectangle's outline using vtkPolyData."""
        points = vtk.vtkPoints()
        for corner in self.corners:
            points.InsertNextPoint(corner)

        # Create lines to form a rectangle
        lines = vtk.vtkCellArray()
        for i in range(4):
            line = vtk.vtkLine()
            line.GetPointIds().SetId(0, i)
            line.GetPointIds().SetId(1, (i + 1) % 4)  # Wrap around to the first point
            lines.InsertNextCell(line)

        poly_data = vtk.vtkPolyData()
        poly_data.SetPoints(points)
        poly_data.SetLines(lines)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(poly_data)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(self.color[0] / 255, self.color[1] / 255, self.color[2] / 255)
        return actor

    def update_bottom_left(self, obj, event):
        """Update rectangle when bottom-left corner is moved."""
        self.corners[0] = self.handles[0].GetRepresentation().GetWorldPosition()
        self.corners[1][1] = self.corners[0][1]  # Adjust bottom-right Y
        self.corners[3][0] = self.corners[0][0]  # Adjust top-left X
        self.update_rectangle()

    def update_bottom_right(self, obj, event):
        """Update rectangle when bottom-right corner is moved."""
        self.corners[1] = self.handles[1].GetRepresentation().GetWorldPosition()
        self.corners[0][1] = self.corners[1][1]  # Adjust bottom-left Y
        self.corners[2][0] = self.corners[1][0]  # Adjust top-right X
        self.update_rectangle()

    def update_top_right(self, obj, event):
        """Update rectangle when top-right corner is moved."""
        self.corners[2] = self.handles[2].GetRepresentation().GetWorldPosition()
        self.corners[1][0] = self.corners[2][0]  # Adjust bottom-right X
        self.corners[3][1] = self.corners[2][1]  # Adjust top-left Y
        self.update_rectangle()

    def update_top_left(self, obj, event):
        """Update rectangle when top-left corner is moved."""
        self.corners[3] = self.handles[3].GetRepresentation().GetWorldPosition()
        self.corners[0][0] = self.corners[3][0]  # Adjust bottom-left X
        self.corners[2][1] = self.corners[3][1]  # Adjust top-right Y
        self.update_rectangle()

    def update_rectangle(self):
        """Update rectangle shape and reposition handles."""
        # Enforce minimum size constraint and recalculate corners
        bottom_left = self.corners[0]
        top_right = self.corners[2]
        self.corners = self.calculate_corners(bottom_left, top_right)

        # Update handle positions
        for i, handle in enumerate(self.handles):
            handle.GetRepresentation().SetWorldPosition(self.corners[i])

        # Update the rectangle actor
        points = vtk.vtkPoints()
        for corner in self.corners:
            points.InsertNextPoint(corner)

        poly_data = self.rect_actor.GetMapper().GetInput()
        poly_data.SetPoints(points)
        poly_data.Modified()

        self.modified = True

    def set_visibility(self, visible):
        self.visible = visible
        for handle in self.handles:
            handle.EnabledOn() if visible else handle.EnabledOff()
        self.rect_actor.SetVisibility(visible)

    def set_color(self, color):
        self.color = color
        self.rect_actor.GetProperty().SetColor(color[0] / 255, color[1] / 255, color[2] / 255)
        for handle in self.handles:
            handle.GetRepresentation().GetProperty().SetColor(color[0] / 255, color[1] / 255, color[2] / 255)

    def set_highlight(self, highlighted):
        """Highlight or unhighlight the rectangle by changing line width or color."""
        width = 3.0 if highlighted else 1.0  # Thicker lines for highlighting
        #color = [0, 255, 0] if highlighted else self.color  # Green for highlighting
        self.rect_actor.GetProperty().SetLineWidth(width)
        #self.set_color(color)


class RectListItemWidget(QWidget):
    def __init__(self, name, rect, manager):
        super().__init__()
        self.manager = manager
        self.rect = rect
        self.name = name

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Checkbox for visibility
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.rect.visible)
        self.checkbox.stateChanged.connect(self.toggle_visibility)
        self.layout.addWidget(self.checkbox)

        # Color patch for the rectangle
        self.color_patch = QLabel()
        self.color_patch.setFixedSize(16, 16)  # Small square
        self.color_patch.setStyleSheet(f"background-color: {self.get_color_hex_string()}; border: 1px solid black;")
        self.color_patch.setCursor(Qt.PointingHandCursor)
        self.color_patch.mousePressEvent = self.change_color_clicked
        self.layout.addWidget(self.color_patch)

        # Label for the rectangle name
        self.label = QLabel(name)
        self.label.setCursor(Qt.PointingHandCursor)
        self.label.mouseDoubleClickEvent = self.activate_name_editor
        self.layout.addWidget(self.label)

        # Editable name field
        self.edit_name = QLineEdit(name)
        self.edit_name.setToolTip("Edit the rectangle name (must be unique and file-system compatible).")
        self.edit_name.hide()  # Initially hidden
        self.edit_name.returnPressed.connect(self.deactivate_name_editor)
        self.edit_name.editingFinished.connect(self.deactivate_name_editor)
        self.edit_name.textChanged.connect(self.validate_name)
        self.layout.addWidget(self.edit_name)

        # Remove button (with 'x')
        self.remove_button = QPushButton("X")
        self.remove_button.setMinimumSize(25, 25)  # Adjust size for better appearance
        self.remove_button.setToolTip("Remove this rectangle")
        self.remove_button.clicked.connect(self.remove_rect_clicked)
        self.layout.addWidget(self.remove_button, alignment=Qt.AlignCenter)

        self.setLayout(self.layout)

    def toggle_visibility(self, state):
        self.rect.set_visibility(state == Qt.Checked)
        self.manager.on_rect_changed(self.name)

    def get_color_hex_string(self):
        color = self.rect.color
        return f"rgb({color[0]}, {color[1]}, {color[2]})"

    def change_color_clicked(self, event):
        current_color = QColor(self.rect.color[0], self.rect.color[1], self.rect.color[2])
        color = QColorDialog.getColor(current_color, self, "Select Rectangle Color")

        if color.isValid():
            c = [color.red(), color.green(), color.blue()]
            self.rect.set_color(c)
            self.color_patch.setStyleSheet(f"background-color: {self.get_color_hex_string()}; border: 1px solid black;")
            self.manager.on_rect_changed(self.name)

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
            self.edit_name.setToolTip("Rectangle name contains invalid characters or is empty.")
            return

        existing_names = [name for name in self.manager.rects.keys() if name != self.name]
        if new_name in existing_names:
            self.edit_name.setStyleSheet("background-color: rgb(255, 99, 71);")
            self.edit_name.setToolTip("Rectangle name must be unique.")
            return

        self.edit_name.setStyleSheet("")
        self.edit_name.setToolTip("")
        self.manager.update_rect_name(self.name, new_name)

    def remove_rect_clicked(self):
        self.manager.remove_rect_by_name(self.name)


class RectListManager(QObject):
    log_message = pyqtSignal(str, str)  # For emitting log messages

    def __init__(self, vtk_viewer):
        super().__init__()
        self.vtk_viewer = vtk_viewer
        self.vtk_renderer = vtk_viewer.get_renderer()
        self.rects = {}  # Dictionary of RectItem objects
        self.active_rect_name = None

    def clear(self):
        """Clear all rectangles and their widgets."""
        for name, rect in list(self.rects.items()):
            self.remove_rect_by_name(name)

        self.rects.clear()
        self.list_widget.clear()
        self.vtk_renderer.GetRenderWindow().Render()
        self.log_message.emit("INFO", "All rectangles cleared.")

    def setup_ui(self):
        """Set up the UI with a dockable widget."""
        dock = QDockWidget("Rectangles")
        widget = QWidget()
        layout = QVBoxLayout()

        # List widget for rectangles
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.on_current_item_changed)
        layout.addWidget(self.list_widget)

        # Buttons to manage rectangles
        button_layout = QHBoxLayout()

        add_rect_button = QPushButton("Add Rectangle")
        add_rect_button.clicked.connect(self.add_rect_clicked)
        button_layout.addWidget(add_rect_button)

        layout.addLayout(button_layout)
        widget.setLayout(layout)
        dock.setWidget(widget)

        return None, dock

    def on_current_item_changed(self, current, previous):
        if current:
            item_widget = self.list_widget.itemWidget(current)
            if item_widget:
                rect = item_widget.rect
                name = item_widget.name

                if previous:
                    previous_widget = self.list_widget.itemWidget(previous)
                    if previous_widget:
                        previous_rect = previous_widget.rect
                        previous_rect.set_highlight(False)

                rect.set_highlight(True)
                self.active_rect_name = name
                self.vtk_renderer.GetRenderWindow().Render()

    def get_exclusive_actions(self):
        return []

    def generate_unique_name(self, base_name="Rect"):
        index = 1
        while f"{base_name} {index}" in self.rects:
            index += 1
        return f"{base_name} {index}"

    def add_rect_clicked(self):
        renderer = self.vtk_viewer.get_renderer()
        camera = renderer.GetActiveCamera()
        focal_point = camera.GetFocalPoint()
        view_extent = camera.GetParallelScale()

        corner1 = [
            focal_point[0] - view_extent / 4,
            focal_point[1] - view_extent / 4,
            focal_point[2]+0.1,
        ]
        corner2 = [
            focal_point[0] + view_extent / 4,
            focal_point[1] + view_extent / 4,
            focal_point[2]+0.1,
        ]

        rect_name = self.generate_unique_name()

        if not hasattr(self, 'color_rotator'):
            self.color_rotator = ColorRotator()
        
        self.add_rect(corner1=corner1, corner2=corner2, name=rect_name, color=self.color_rotator.next())

    def add_rect(self, corner1, corner2, color=[255, 0, 0], visible=True, name=None):
        rect = RectItem(corner1=corner1, corner2=corner2, color=color, visible=visible, renderer=self.vtk_renderer, interactor=self.vtk_viewer.interactor)
        if name is None:
            name = self.generate_unique_name()

        self.rects[name] = rect

        item_widget = RectListItemWidget(name, rect, self)
        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())

        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, item_widget)
        self.list_widget.setCurrentItem(item)

    def remove_rect_by_name(self, name):
        if name in self.rects:
            item = None
            for i in range(self.list_widget.count()):
                list_item = self.list_widget.item(i)
                item_widget = self.list_widget.itemWidget(list_item)
                if item_widget.name == name:
                    item = list_item
                    break

            if item:
                rect = self.rects[name]
                rect.widget.Off()
                del self.rects[name]
                self.list_widget.takeItem(self.list_widget.row(item))

                if self.list_widget.count() > 0:
                    self.list_widget.setCurrentRow(self.list_widget.count() - 1)

                self.vtk_renderer.GetRenderWindow().Render()

    def on_rect_changed(self, name):
        self.vtk_renderer.GetRenderWindow().Render()
