import vtk
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QSlider, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor


class CircleBrush:
    def __init__(self, radius=5):
        self.radius = radius

    def paint(self, segmentation, x, y, value=1):
        """Draw a circle on the segmentation at (x, y) with the given radius."""
        dims = segmentation.GetDimensions()
        scalars = segmentation.GetPointData().GetScalars()
        extent = segmentation.GetExtent()

        for i in range(-self.radius, self.radius + 1):
            for j in range(-self.radius, self.radius + 1):
                if i**2 + j**2 <= self.radius**2:  # Circle equation
                    xi = x + i
                    yj = y + j
                    if extent[0] <= xi <= extent[1] and extent[2] <= yj <= extent[3]:
                        idx = (yj - extent[2]) * dims[0] + (xi - extent[0])
                        scalars.SetTuple1(idx, value)

import math


class CustomInteractorStyle(vtk.vtkInteractorStyleImage):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.left_button_is_pressed = False

    def OnMouseMove(self):
        if self.left_button_is_pressed and self.parent:
            self.parent.on_mouse_move(None, "MouseMoveEvent")
        super().OnMouseMove()

    def OnLeftButtonDown(self):
        self.left_button_is_pressed = True
        if self.parent:
            self.parent.on_left_button_press(None, "LeftButtonPressEvent")
        super().OnLeftButtonDown()

    def OnLeftButtonUp(self):
        self.left_button_is_pressed = False
        if self.parent:
            self.parent.on_left_button_release(None, "LeftButtonReleaseEvent")
        super().OnLeftButtonUp()


class VTKViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    

        # Create a VTK Renderer
        self.base_renderer = vtk.vtkRenderer()
        self.base_renderer.SetLayer(0)

        # Create a VTK Renderer for the brush actor
        self.brush_renderer = vtk.vtkRenderer()
        self.brush_renderer.SetLayer(1)  # Higher layer index
        self.brush_renderer.SetBackground(0, 0, 0)  # Transparent background

        # Create a QVTKRenderWindowInteractor
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        self.render_window = self.vtk_widget.GetRenderWindow()  # Retrieve the render window
        self.render_window.SetNumberOfLayers(2)
        self.render_window.AddRenderer(self.base_renderer)
        self.render_window.AddRenderer(self.brush_renderer)

        # Set up interactor style
        self.interactor = self.render_window.GetInteractor()
        self.interactor_style = vtk.vtkInteractorStyleUser()
        self.interactor.SetInteractorStyle(self.interactor_style)

        # Layout for embedding the VTK widget
        layout = QVBoxLayout()
        layout.addWidget(self.vtk_widget)

        # Add sliders for window and level adjustments
        slider_layout = QHBoxLayout()

        self.window_slider = QSlider(Qt.Horizontal)
        self.window_slider.setMinimum(1)
        self.window_slider.setMaximum(2000)
        self.window_slider.setValue(400)
        self.window_slider.setTickInterval(100)
        self.window_slider.valueChanged.connect(self.update_window_level)
        slider_layout.addWidget(QLabel("Window:"))
        slider_layout.addWidget(self.window_slider)

        self.level_slider = QSlider(Qt.Horizontal)
        self.level_slider.setMinimum(-1000)
        self.level_slider.setMaximum(1000)
        self.level_slider.setValue(40)
        self.level_slider.setTickInterval(100)
        self.level_slider.valueChanged.connect(self.update_window_level)
        slider_layout.addWidget(QLabel("Level:"))
        slider_layout.addWidget(self.level_slider)

        layout.addLayout(slider_layout)
        self.setLayout(layout)

        # VTK pipeline for image
        self.image_actor = vtk.vtkImageActor()
        self.window_level_filter = vtk.vtkImageMapToWindowLevelColors()
        self.window_level_filter.SetOutputFormatToRGB()
        self.base_renderer.AddActor(self.image_actor)

        # Paintbrush setup
        self.brush = CircleBrush(radius=20)
        self.active_segmentation = None  # Reference to the active segmentation
        self.painting_enabled = False

        # Brush actor for visualization
        self.brush_actor = vtk.vtkActor()
        self.brush_actor.SetVisibility(False)  # Initially hidden
            
        self.base_renderer.AddActor(self.brush_actor)

        # Create a green brush representation
        # Create a 2D circle for brush visualization
        self.brush_source = vtk.vtkPolyData()
        self.circle_points = vtk.vtkPoints()
        self.circle_lines = vtk.vtkCellArray()

        # Initialize the circle geometry
        self.update_circle_geometry(self.brush.radius)

        self.brush_source.SetPoints(self.circle_points)
        self.brush_source.SetLines(self.circle_lines)

        # Brush mapper and actor
        brush_mapper = vtk.vtkPolyDataMapper()
        brush_mapper.SetInputData(self.brush_source)
        self.brush_actor.SetMapper(brush_mapper)
        self.brush_actor.GetProperty().SetColor(0, 1, 0)  # Green color

        # Connect mouse events
        self.interactor.AddObserver("LeftButtonPressEvent", self.on_left_button_press)
        self.interactor.AddObserver("LeftButtonReleaseEvent", self.on_left_button_release)
        self.interactor.AddObserver("MouseMoveEvent", self.on_mouse_move)


    
    def on_mouse_move(self, obj, event):
        """Update brush position and optionally paint."""
        if self.painting_enabled:
            mouse_pos = self.interactor.GetEventPosition()
            picker = vtk.vtkWorldPointPicker()
            picker.Pick(mouse_pos[0], mouse_pos[1], 0, self.base_renderer)

            # Get world position
            world_pos = picker.GetPickPosition()

            # Update the brush position (ensure Z remains on the image plane + 0.1 to show on top of the image)
            self.brush_actor.SetPosition(world_pos[0], world_pos[1], world_pos[2] + 0.1)
            self.brush_actor.SetVisibility(True)  # Make the brush visible

            # Paint 
            if self.left_button_is_pressed and self.active_segmentation:
                print('paint...')
                self.paint_at_mouse_position()
        else:
            self.brush_actor.SetVisibility(False)  # Hide the brush when not painting

        self.render_window.Render()

    def on_left_button_press(self, obj, event):
        self.left_button_is_pressed = True
        if self.painting_enabled and self.active_segmentation:
            self.paint_at_mouse_position()

    def on_left_button_release(self, obj, event):
        self.left_button_is_pressed = False
        return
    
    def update_circle_geometry(self, radius):
        """Update the circle geometry to reflect the current radius."""
        self.circle_points.Reset()
        self.circle_lines.Reset()

        num_segments = 50  # Number of segments for the circle
        for i in range(num_segments):
            angle = 2.0 * math.pi * i / num_segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
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


    def load_dicom(self, dicom_path):
        # Use VTK DICOM Reader
        reader = vtk.vtkDICOMImageReader()
        reader.SetFileName(dicom_path)
        reader.Update()

        # Check if the output is valid
        if not reader.GetOutput():
            print("Error: Could not read DICOM file.")
            return

        self.image_data = reader.GetOutput()

        # Get the scalar range (pixel intensity range)
        scalar_range = reader.GetOutput().GetScalarRange()
        min_intensity, max_intensity = scalar_range

        # Dynamically adjust sliders based on intensity range
        self.window_slider.setMinimum(1)
        self.window_slider.setMaximum(int(max_intensity - min_intensity))
        self.window_slider.setValue(int((max_intensity - min_intensity) / 2))  # Default to half of the range

        self.level_slider.setMinimum(int(min_intensity))
        self.level_slider.setMaximum(int(max_intensity))
        self.level_slider.setValue(int((max_intensity + min_intensity) / 2))  # Default to the center of the range

        # Connect reader to window/level filter
        self.window_level_filter.SetInputConnection(reader.GetOutputPort())
        self.window_level_filter.SetWindow(self.window_slider.value())
        self.window_level_filter.SetLevel(self.level_slider.value())
        self.window_level_filter.Update()

        # Set the filter output to the actor
        self.image_actor.GetMapper().SetInputConnection(self.window_level_filter.GetOutputPort())
        self.base_renderer.ResetCamera()
        self.render_window.Render()
    

    def update_window_level(self):
        window = self.window_slider.value()
        level = self.level_slider.value()

        self.window_level_filter.SetWindow(window)
        self.window_level_filter.SetLevel(level)
        self.window_level_filter.Update()

        self.render_window.Render()

    def set_active_segmentation(self, segmentation):
        """Set the currently active segmentation layer."""
        self.active_segmentation = segmentation



    def paint_at_mouse_position(self):
        mouse_pos = self.interactor.GetEventPosition()
        picker = vtk.vtkWorldPointPicker()
        picker.Pick(mouse_pos[0], mouse_pos[1], 0, self.base_renderer)
        world_pos = picker.GetPickPosition()

        dims = self.image_data.GetDimensions()
        spacing = self.image_data.GetSpacing()
        origin = self.image_data.GetOrigin()

        x = int((world_pos[0] - origin[0]) / spacing[0])
        y = int((world_pos[1] - origin[1]) / spacing[1])

        self.brush.paint(self.active_segmentation, x, y)
        self.active_segmentation.Modified()
        self.render_window.Render()

    def toggle_paintbrush(self, enabled):
        """Enable or disable the paintbrush tool."""
        self.painting_enabled = enabled
        self.brush_actor.SetVisibility(enabled)  # Show brush if enabled
        self.render_window.Render()


from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout

class SegmentationListManager(QWidget):
    def __init__(self, vtk_viewer                 , parent=None):
        super().__init__(parent)
        self.vtk_viewer = vtk_viewer
        self.vtk_renderer = vtk_viewer.base_renderer  # Reference to the VTK renderer
        self.segments = {}  # Dictionary to store segmentation layers {name: vtkImageData}
        self.active_layer_name = None

        # UI Components
        self.layout = QVBoxLayout()

        # List widget to display layers
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.layout.addWidget(self.list_widget)

        # Buttons for managing layers
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Layer")
        self.add_button.clicked.connect(self.add_layer)
        button_layout.addWidget(self.add_button)

        self.remove_button = QPushButton("Remove Layer")
        self.remove_button.clicked.connect(self.remove_layer)
        button_layout.addWidget(self.remove_button)

        self.toggle_button = QPushButton("Toggle Visibility")
        self.toggle_button.clicked.connect(self.toggle_visibility)
        button_layout.addWidget(self.toggle_button)

        self.layout.addLayout(button_layout)


        # Paintbrush toggle
        self.paintbrush_button = QPushButton("Enable Paintbrush")
        self.paintbrush_button.setCheckable(True)
        self.paintbrush_button.toggled.connect(self.vtk_viewer.toggle_paintbrush)
        self.layout.addWidget(self.paintbrush_button)

        self.setLayout(self.layout)

    def add_layer(self):
        """Add a new segmentation layer."""
        layer_name = f"Segment {len(self.segments) + 1}"
        segmentation = vtk.vtkImageData()
        segmentation.DeepCopy(self.create_empty_segmentation())

        self.segments[layer_name] = segmentation
        self.list_widget.addItem(layer_name)

        # Add the layer actor to the renderer
        actor = self.create_segmentation_actor(segmentation)
        self.segments[layer_name] = {'data': segmentation, 'actor': actor}
        self.vtk_renderer.AddActor(actor)

        self.vtk_renderer.GetRenderWindow().Render()
        
        print(f"Added layer: {layer_name}")

    def remove_layer(self):
        """Remove the selected segmentation layer."""
        current_item = self.list_widget.currentItem()
        if current_item:
            layer_name = current_item.text()
            self.list_widget.takeItem(self.list_widget.row(current_item))

            # Remove the layer from the renderer
            actor = self.segments[layer_name]['actor']
            self.vtk_renderer.RemoveActor(actor)
            del self.segments[layer_name]

            print(f"Removed layer: {layer_name}")

    def toggle_visibility(self):
        """Toggle the visibility of the selected layer."""
        current_item = self.list_widget.currentItem()
        if current_item:
            layer_name = current_item.text()
            actor = self.segments[layer_name]['actor']
            visibility = actor.GetVisibility()
            actor.SetVisibility(not visibility)
            print(f"Toggled visibility for layer: {layer_name} (Visible: {not visibility})")


    def on_selection_changed(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            layer_name = current_item.text()
            self.active_layer_name = layer_name
            segmentation = self.segments[layer_name]['data']
            self.vtk_viewer.set_active_segmentation(segmentation)

    def get_base_image(self):
        return self.vtk_viewer.image_data
    
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


    def create_segmentation_actor(self, segmentation):
        """Create a VTK actor for a segmentation layer."""
        # Create a lookup table for coloring the segmentation
        lookup_table = vtk.vtkLookupTable()
        lookup_table.SetNumberOfTableValues(2)  # For 0 (background) and 1 (segmentation)
        lookup_table.SetTableRange(0, 1)       # Scalar range
        lookup_table.SetTableValue(0, 0, 0, 0, 0)  # Background: Transparent
        lookup_table.SetTableValue(1, 1, 0, 0, 0.8)  # Segmentation: Red with 50% opacity
        lookup_table.Build()
        
        mapper = vtk.vtkImageMapToColors()
        mapper.SetInputData(segmentation)
        mapper.SetLookupTable(lookup_table)
        mapper.Update()

        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputConnection(mapper.GetOutputPort())
        
        # Enable blending
        #actor.SetOpacity(0.5)
        
        return actor


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("VTK Viewer with Paintbrush")

        central_widget = QWidget()
        layout = QHBoxLayout()

        # VTK Viewer
        self.vtk_viewer = VTKViewer(self)
        layout.addWidget(self.vtk_viewer)

        # Segmentation Manager
        self.segmentation_manager = SegmentationListManager(self.vtk_viewer, self)
        layout.addWidget(self.segmentation_manager)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)


        # Load a sample DICOM file
        dicom_file = "W:/RadOnc/Planning/Physics QA/2024/1.Monthly QA/TrueBeamSH/2024_11/imaging/jaw_cal.dcm"
        self.vtk_viewer.load_dicom(dicom_file)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
