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

'''
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
'''
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
            self.interactor.AddObserver("LeftButtonPressEvent", self.on_left_button_press)
            self.interactor.AddObserver("MouseMoveEvent", self.on_mouse_move)
            self.interactor.AddObserver("LeftButtonReleaseEvent", self.on_left_button_release)
        else:    
            self.interactor.RemoveObserver("LeftButtonPressEvent", self.on_left_button_press)
            self.interactor.RemoveObserver("MouseMoveEvent", self.on_mouse_move)
            self.interactor.RemoveObserver("LeftButtonReleaseEvent", self.on_left_button_release)    
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
        
        
class VTKViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
    
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

        self.rulers = []
        self.panning = Panning(viewer=self)  # State to track panning mode

    def get_renderer(self):
        return self.base_renderer
    
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
        camera = self.base_renderer.GetActiveCamera()
        focal_point = camera.GetFocalPoint()
        view_extent = camera.GetParallelScale()  # Approximate size of the visible area

        # Calculate ruler start and end points
        start_point = [focal_point[0] - view_extent / 6, focal_point[1], focal_point[2]]
        end_point = [focal_point[0] + view_extent / 6, focal_point[1], focal_point[2]]

        print('start_point: ', start_point)
        print('end_point: ', end_point)

        # Create a ruler using vtkLineWidget2
        line_widget = vtk.vtkLineWidget2()
        line_representation = vtk.vtkLineRepresentation()
        line_widget.SetRepresentation(line_representation)

        # Set initial position of the ruler
        line_representation.SetPoint1WorldPosition(start_point)
        line_representation.SetPoint2WorldPosition(end_point)
        line_representation.GetLineProperty().SetColor(1, 0, 0)  # Red color
        line_representation.GetLineProperty().SetLineWidth(2)
        line_representation.SetVisibility(True)

        # Set interactor and enable interaction
        line_widget.SetInteractor(self.render_window.GetInteractor())
        line_widget.On()

        # Add the ruler to the list for management
        self.rulers.append(line_widget)

        # Calculate and display the initial distance
        self.update_ruler_distance(line_representation)

        # Attach a callback to update distance when the ruler is moved
        line_widget.AddObserver("InteractionEvent", lambda obj, event: self.update_ruler_distance(line_representation))

    def update_ruler_distance(self, line_representation):
        """Update and display the distance of the ruler."""
        # Check if the line representation already has a text actor
        if not hasattr(line_representation, "text_actor"):
            # Create a text actor if it doesn't exist
            line_representation.text_actor = vtk.vtkTextActor()
            self.base_renderer.AddActor2D(line_representation.text_actor)

        # Calculate the distance
        point1 = line_representation.GetPoint1WorldPosition()
        point2 = line_representation.GetPoint2WorldPosition()
        distance = ((point2[0] - point1[0]) ** 2 +
                    (point2[1] - point1[1]) ** 2 +
                    (point2[2] - point1[2]) ** 2) ** 0.5
        spacing = self.image_data.GetSpacing()
        physical_distance = distance * spacing[0]  # Assuming uniform spacing

        print(f"Ruler Distance: {physical_distance:.2f} mm")

        # Update the text actor with the new distance
        midpoint = [(point1[i] + point2[i]) / 2 for i in range(3)]
        line_representation.text_actor.SetInput(f"{physical_distance:.2f} mm")
        line_representation.text_actor.GetTextProperty().SetFontSize(14)
        line_representation.text_actor.GetTextProperty().SetColor(1, 1, 1)  # White color
        line_representation.text_actor.SetPosition(midpoint[0], midpoint[1])

        # Render the updates
        self.render_window.Render()
        
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

        #self.panning.on_mouse_move(obj, event)

        self.render_window.Render()

    def on_left_button_press(self, obj, event):
        self.left_button_is_pressed = True
        if self.painting_enabled and self.active_segmentation:
            self.paint_at_mouse_position()

        # for panning
        #self.planning.on_left_button_press(obj, event)

    def on_left_button_release(self, obj, event):
        self.left_button_is_pressed = False
        
        #self.panning.on_left_button_release(obj, event)
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


    def center_image(self):
        
        dims = self.image_data.GetDimensions()
        spacing = self.image_data.GetSpacing()
        original_origin = self.image_data.GetOrigin()

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
        self.image_data.SetOrigin(new_origin)
        
        print('new_origin: ', new_origin)

        self.image_original_origin = original_origin


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

        # Extract correct spacing for RTImage using pydicom
        import pydicom
        dicom_dataset = pydicom.dcmread(dicom_path)
        if dicom_dataset.Modality == "RTIMAGE":
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
            self.image_data.SetSpacing(scaled_spacing[1], scaled_spacing[0], 1.0)  # Column, Row, Depth
            
            # Print the updated spacing
            print(f"Updated Spacing: {self.image_data.GetSpacing()}")

        # align the center of the image to the center of the world coordiante system
        # Get image properties
        dims = self.image_data.GetDimensions()
        spacing = self.image_data.GetSpacing()
        original_origin = self.image_data.GetOrigin()

        print('dims: ', dims)
        print('spacing: ', spacing)
        print('original_origin: ', original_origin)

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

        #self.reset_camera_parameters()
        self.get_camera_info()
        self.print_camera_viewport_info()


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
        if self.image_data:
            dims = self.image_data.GetDimensions()
            spacing = self.image_data.GetSpacing()
            origin = self.image_data.GetOrigin()
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
        if self.image_data is None:
            print("No image data loaded.")
            return

        # Get the image center
        dims = self.image_data.GetDimensions()
        spacing = self.image_data.GetSpacing()
        origin = self.image_data.GetOrigin()

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

    def toggle_panning_mode(self, enabled):
        """Enable or disable panning mode."""
        self.panning.enable(enabled)

        
    
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


import pyvista as pv
import numpy as np

class PyVistaWindow:
    def __init__(self, vtk_viewer):
        self.vtk_viewer = vtk_viewer
        self.plotter = pv.Plotter(title="PyVista Visualization", window_size=(800, 600))
    
    def extract_camera_parameters(self):
        """Extract camera parameters from the VTK viewer."""
        camera = self.vtk_viewer.base_renderer.GetActiveCamera()
        position = np.array(camera.GetPosition())
        focal_point = np.array(camera.GetFocalPoint())
        view_up = np.array(camera.GetViewUp())
        clipping_range = camera.GetClippingRange()
        parallel_scale = camera.GetParallelScale()
        aspect_ratio = self.plotter.window_size[0] / self.plotter.window_size[1]
        return position, focal_point, view_up, clipping_range, parallel_scale, aspect_ratio

    def create_camera_frustum(self, position, focal_point, view_up, clipping_range, parallel_scale, aspect_ratio):
        """Create a PyVista representation of the camera frustum."""
        direction = focal_point - position
        direction = direction / np.linalg.norm(direction)  # Normalize the direction vector

        # Calculate frustum corners at near and far clipping planes
        near_plane = position + direction * clipping_range[0]
        far_plane = position + direction * clipping_range[1]

        # Frustum dimensions
        near_height = parallel_scale
        near_width = near_height * aspect_ratio
        far_height = near_height * (clipping_range[1] / clipping_range[0])
        far_width = far_height * aspect_ratio

        # Calculate the corners
        def calculate_corners(center, width, height, view_up):
            right = np.cross(direction, view_up)
            right = right / np.linalg.norm(right)
            up = view_up / np.linalg.norm(view_up)
            return [
                center - right * width - up * height,  # Bottom-left
                center + right * width - up * height,  # Bottom-right
                center + right * width + up * height,  # Top-right
                center - right * width + up * height,  # Top-left
            ]

        near_corners = calculate_corners(near_plane, near_width, near_height, view_up)
        far_corners = calculate_corners(far_plane, far_width, far_height, view_up)

        # Create a PolyData representation
        points = near_corners + far_corners
        lines = [
            [2, 0, 1], [2, 1, 2], [2, 2, 3], [2, 3, 0],  # Near plane
            [2, 4, 5], [2, 5, 6], [2, 6, 7], [2, 7, 4],  # Far plane
            [2, 0, 4], [2, 1, 5], [2, 2, 6], [2, 3, 7],  # Connecting edges
        ]
        return pv.PolyData(points, lines)

    def extract_image_plane(self):
        """Create a PyVista representation of the image plane."""
        image_data = self.vtk_viewer.image_data
        dims = image_data.GetDimensions()
        spacing = image_data.GetSpacing()
        origin = image_data.GetOrigin()

        # Create an image plane using the bounds
        x_range = origin[0] + np.array([0, dims[0]]) * spacing[0]
        y_range = origin[1] + np.array([0, dims[1]]) * spacing[1]
        z = origin[2]

        # Create PyVista surface (rectangle) for the image plane
        points = [
            [x_range[0], y_range[0], z],
            [x_range[1], y_range[0], z],
            [x_range[1], y_range[1], z],
            [x_range[0], y_range[1], z],
        ]
        faces = [4, 0, 1, 2, 3]  # One face connecting all points
        plane = pv.PolyData(points, faces)
        return plane

    def setup_scene(self):
        """Setup the PyVista scene with the camera, image plane, and line widget."""
        # Extract camera parameters
        position, focal_point, view_up, clipping_range, parallel_scale, aspect_ratio = self.extract_camera_parameters()

        # Add camera frustum
        camera_frustum = self.create_camera_frustum(position, focal_point, view_up, clipping_range, parallel_scale, aspect_ratio)
        self.plotter.add_mesh(camera_frustum, color="green", opacity=0.5, label="Camera Frustum")

        # Add image plane
        image_plane = self.extract_image_plane()
        self.plotter.add_mesh(image_plane, color="lightgray", opacity=0.5, label="Image Plane")

        # Add a legend and axes
        self.plotter.add_legend()
        self.plotter.add_axes()

    def show(self):
        """Render the PyVista visualization."""
        self.setup_scene()
        self.plotter.show()


# Function to open the PyVista visualization
def open_pyvista_window(vtk_viewer):
    pv_window = PyVistaWindow(vtk_viewer)
    pv_window.show()



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



        # Zoom Buttons
        zoom_layout = QVBoxLayout()
        zoom_in_button = QPushButton("Zoom In")
        zoom_in_button.clicked.connect(self.zoom_in)
        zoom_layout.addWidget(zoom_in_button)

        zoom_out_button = QPushButton("Zoom Out")
        zoom_out_button.clicked.connect(self.zoom_out)
        zoom_layout.addWidget(zoom_out_button)

        # Add Panning Button
        panning_button = QPushButton("Activate Panning")
        panning_button.setCheckable(True)
        panning_button.toggled.connect(self.vtk_viewer.toggle_panning_mode)
        zoom_layout.addWidget(panning_button)

        layout.addLayout(zoom_layout)



        # Tools Layout
        tools_layout = QVBoxLayout()

        # Add Ruler Button
        add_ruler_button = QPushButton("Add Ruler")
        add_ruler_button.clicked.connect(self.vtk_viewer.add_ruler)
        tools_layout.addWidget(add_ruler_button)


        # Add Toggle Button
        toggle_image_button = QPushButton("Toggle Base Image")
        toggle_image_button.setCheckable(True)
        toggle_image_button.setChecked(True)
        toggle_image_button.toggled.connect(self.vtk_viewer.toggle_base_image)
        tools_layout.addWidget(toggle_image_button)


        # Add PyVista Window Button
        pyvista_button = QPushButton("Open PyVista Window")
        pyvista_button.clicked.connect(self.open_pyvista_window)
        tools_layout.addWidget(pyvista_button)


        # Print Object Properties Button
        print_properties_button = QPushButton("Print Object Properties")
        print_properties_button.clicked.connect(self.vtk_viewer.print_properties)
        tools_layout.addWidget(print_properties_button)

        layout.addLayout(tools_layout)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)


        # Load a sample DICOM file
        dicom_file = "W:/RadOnc/Planning/Physics QA/2024/1.Monthly QA/TrueBeamSH/2024_11/imaging/jaw_cal.dcm"
        self.vtk_viewer.load_dicom(dicom_file)
    
    def open_pyvista_window(self):
        open_pyvista_window(self.vtk_viewer)

    def zoom_in(self):
        """Zoom in the camera."""
        camera = self.vtk_viewer.base_renderer.GetActiveCamera()
        camera.Zoom(1.2)  # Zoom in by 20%
        self.vtk_viewer.render_window.Render()

        self.vtk_viewer.get_camera_info()
        self.vtk_viewer.print_camera_viewport_info()
        

    def zoom_out(self):
        """Zoom out the camera."""
        camera = self.vtk_viewer.base_renderer.GetActiveCamera()
        camera.Zoom(0.8)  # Zoom out by 20%
        self.vtk_viewer.render_window.Render()

        self.vtk_viewer.get_camera_info()
        self.vtk_viewer.print_camera_viewport_info()
        

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
