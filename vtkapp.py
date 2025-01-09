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

class PaintBrush:
    def __init__(self, radius_in_pixel=(20,20), pixel_spacing=(1.0, 1.0), color= (0,255,0), line_thickness= 1):
        self.radius_in_pixel = radius_in_pixel
        self.pixel_spacing = pixel_spacing

        # Paintbrush setup
        self.active_segmentation = None  # Reference to the active segmentation
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
        self.setLayout(layout)

        # Connect mouse events
        self.interactor.AddObserver("LeftButtonPressEvent", self.on_left_button_press)
        self.interactor.AddObserver("LeftButtonReleaseEvent", self.on_left_button_release)
        self.interactor.AddObserver("MouseMoveEvent", self.on_mouse_move)

        self.rulers = []
        self.zooming = Zooming(viewer=self)
        self.panning = Panning(viewer=self)  

    def set_vtk_image(self, vtk_image, window, level):

        self.vtk_image = vtk_image
                
        # Connect reader to window/level filter
        self.window_level_filter = vtk.vtkImageMapToWindowLevelColors()
        self.window_level_filter.SetOutputFormatToRGB()
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

    def world_to_display(self, renderer, world_coordinates):
        """Convert world coordinates to display coordinates."""
        display_coordinates = [0.0, 0.0, 0.0]
        renderer.SetWorldPoint(*world_coordinates, 1.0)
        renderer.WorldToDisplay()
        display_coordinates = renderer.GetDisplayPoint()
        return display_coordinates

    def update_ruler_distance(self, line_representation):
        """Update and display the distance of the ruler."""
        # Check if the line representation already has a text actor
        if not hasattr(line_representation, "text_actor"):
            # Create a text actor if it doesn't exist
            line_representation.text_actor = vtk.vtkTextActor()
            self.get_renderer().AddActor2D(line_representation.text_actor)

        # Calculate the distance
        point1 = line_representation.GetPoint1WorldPosition()
        point2 = line_representation.GetPoint2WorldPosition()
        distance = ((point2[0] - point1[0]) ** 2 +
                    (point2[1] - point1[1]) ** 2 +
                    (point2[2] - point1[2]) ** 2) ** 0.5
        spacing = self.vtk_image.GetSpacing()
        physical_distance = distance * spacing[0]  # Assuming uniform spacing

        print(f"Ruler Distance: {physical_distance:.2f} mm")

        # Update the text actor with the new distance
        midpoint_w = [(point1[i] + point2[i]) / 2 for i in range(3)]
        midpoint_screen = self.world_to_display(self.get_renderer(), midpoint_w)
        
        line_representation.text_actor.SetInput(f"{physical_distance:.2f} mm")
        line_representation.text_actor.GetTextProperty().SetFontSize(14)
        line_representation.text_actor.GetTextProperty().SetColor(1, 1, 1)  # White color
        line_representation.text_actor.SetPosition(midpoint_screen[0], midpoint_screen[1])

        # Render the updates
        self.render_window.Render()
        
    

        

        self.render_window.Render()

    def on_left_button_press(self, obj, event):
        self.left_button_is_pressed = True

       

    def on_mouse_move(self, obj, event):
        """Update brush position and optionally paint."""
        

        

        self.render_window.Render()


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

    def set_active_segmentation(self, segmentation):
        """Set the currently active segmentation layer."""
        self.active_segmentation = segmentation

    def toggle_panning_mode(self):
        """Enable or disable panning mode."""
        self.panning.enable(not self.panning.enabled)

    def toggle_zooming_mode(self):
        """Enable or disable panning mode."""
        self.zooming.enable(not self.zooming.enabled)
        
    

    def toggle_paintbrush(self, enabled):
        """Enable or disable the paintbrush tool."""
        self.painting_enabled = enabled
        self.brush_actor.SetVisibility(enabled)  # Show brush if enabled
        self.render_window.Render()


from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout
import os

# Construct paths to the icons
current_dir = os.path.dirname(__file__)
brush_icon_path = os.path.join(current_dir, "icons", "brush.png")
eraser_icon_path = os.path.join(current_dir, "icons", "eraser.png")
reset_zoom_icon_path = os.path.join(current_dir, "icons", "reset_zoom.png")

from color_rotator import ColorRotator

color_rotator = ColorRotator()

import numpy as np

class SegmentationLayer:
    def __init__(self, segmentation, visible=True, color=np.array([255, 255, 128]), alpha=0.5, actor=None) -> None:
        self.segmentation = segmentation
        self.visible = visible
        self.color = color
        self.alpha = alpha
        self.actor = actor
        self.modified = False

from line_edit2 import LineEdit2

class LayerItemWidget(QWidget):
    
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

        self.setLayout(self.layout)

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


class SegmentationListManager():
    def __init__(self, vtk_viewer, mainwindow=None):
        
        self.vtk_viewer = vtk_viewer
        self.vtk_renderer = vtk_viewer.get_renderer()
        self.active_layer_name = None

        # mainwindow
        self._mainwindow = mainwindow

        # segmentation data
        self.segmentation_layers = {}
        self.active_layer_name = None

        self.brush_active = False
        self.erase_active = False

        self.paintbrush = None

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

    def render(self):
        self.vtk_renderer.GetRenderWindow().Render()

    def on_layer_changed(self, layer_name):
        self.render()

    def get_active_layer(self):
        return self.segmentation_layers.get(self.active_layer_name, None)

    def get_mainwindow(self):
        return self._mainwindow   

    def init_ui(self):   
        self.create_paintbrush_toolbar()
        self.create_layer_manager()


    def enable_paintbrush(self, enabled=True):
        
        if self.paintbrush is None:
            self.paintbrush = PaintBrush()
            self.paintbrush.set_radius_in_pixel(radius_in_pixel=(20, 20), pixel_spacing=self.vtk_viewer.vtk_image.GetSpacing())
            self.get_mainwindow().vtk_viewer.get_renderer().AddActor(self.paintbrush.get_actor())

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

        self.active_segmentation = layer.segmentation
        self.paintbrush.paint(self.active_segmentation, x, y)
        self.active_segmentation.Modified()
        self.vtk_viewer.get_render_window().Render()

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


    def get_mainwindow(self):
        return self._mainwindow
    def create_paintbrush_toolbar(self):
        
        from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QIcon
        from labeled_slider import LabeledSlider

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
        self.brush_size_slider = LabeledSlider("Brush Size:", initial_value=20)
        self.brush_size_slider.slider.setMinimum(3)
        self.brush_size_slider.slider.setMaximum(100)
        self.brush_size_slider.slider.valueChanged.connect(self.update_brush_size)
        toolbar.addWidget(self.brush_size_slider)

    def update_brush_size(self, value):
        self.paintbrush.set_radius_in_pixel(
            radius_in_pixel=(value, value), 
            pixel_spacing=self.vtk_viewer.get_pixel_spacing())

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
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.list_widget_on_current_item_changed)
        layer_layout.addWidget(self.list_widget)

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

    def list_widget_on_current_item_changed(self, current, previous):
        if current:
            # Retrieve the custom widget associated with the current QListWidgetItem
            item_widget = self.list_widget.itemWidget(current)
            
            if item_widget and isinstance(item_widget, LayerItemWidget):
                # Access the layer_name from the custom widget
                layer_name = item_widget.layer_name
                if self.active_layer_name != layer_name:
                    self.active_layer_name = layer_name
                    self.print_status(f"Layer {layer_name} selected")
                    

    def toggle_brush_tool(self):
        
        self.brush_active = not self.brush_active

        self.erase_active = False  # Disable erase tool when brush is active
        self.erase_action.setChecked(False)  # Uncheck the erase button

        self.brush_action.setChecked(self.brush_active)
        if self.brush_active:
            self.brush_action.setText("Brush Tool (Active)")
            self.print_status("Brush tool activated")
        else:
            self.brush_action.setText("Brush Tool (Inactive)")
            self.print_status("Brush tool deactivated")

        self.enable_paintbrush(self.brush_active)

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
          

    def get_status_bar(self):
        return self._mainwindow.status_bar
    
    def print_status(self, msg):
        if self.get_status_bar() is not None:
            self.get_status_bar().showMessage(msg)
    
    def add_layer_widget_item(self, layer_name, layer_data):

        # Create a custom widget for the layer
        layer_item_widget = LayerItemWidget(layer_name, layer_data, self)
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
    
    def add_layer_clicked(self):

        # Generate a random bright color for the new layer
        layer_color = color_rotator.next()

        # add layer data        
        layer_name = self.generate_unique_layer_name()
        
        segmentation = self.create_empty_segmentation()
        
        actor = self.create_segmentation_actor(segmentation, color=(layer_color[0]/255.0, layer_color[1]/255.0, layer_color[2]/255.0), alpha=0.8)
        layer_data = SegmentationLayer(segmentation=segmentation, color=layer_color, alpha=0.8, actor=actor)
        self.segmentation_layers[layer_name] = layer_data
        self.vtk_renderer.AddActor(actor)
        self.vtk_renderer.GetRenderWindow().Render()

        self.add_layer_widget_item(layer_name, layer_data)

        # Select the last item in the list widget (to activate it)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)

        self.print_status(f'A layer added: {layer_name}, and active layer is now {self.active_layer_name}')



    def remove_layer_clicked(self):
        if len(self.list_widget) == 1:
                self.print_status("At least 1 layer is required.")
                return 

        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            widget = self.list_widget.itemWidget(item)
            layer_name = widget.layer_name

            # remove actor
            actor = self.segmentation_layers[layer_name].actor
            self.vtk_renderer.RemoveActor(actor)

            # Remove from the data list
            del self.segmentation_layers[layer_name]

            # Remove from the list widget
            self.list_widget.takeItem(self.list_widget.row(item))

        # Select the last item in the list widget (to activate it)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)

        # render
        self.vtk_renderer.GetRenderWindow().Render()    

        self.print_status(f"Selected layers removed successfully. The acive layer is now {self.active_layer_name}")


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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        ### init ui ###    
        self.init_ui()

        # Segmentation Manager
        self.segmentation_manager = SegmentationListManager(self.vtk_viewer, self)
        
        self.segmentation_manager.init_ui()
        

        self.vitk_image = None

        # Load a sample DICOM file
        dicom_file = "./data/jaw_cal.dcm"
        self.load_dicom(dicom_file)

    def init_ui(self):
        self.setWindowTitle("Image Labeler 2D")
        self.setGeometry(100, 100, 1024, 786)

        self.main_widget = QWidget()
        self.layout = QVBoxLayout()

        # VTK Viewer
        self.vtk_viewer = VTKViewer(self)
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

    def load_dicom(self, dicom_path):

        # Use VTK DICOM Reader
        reader = vtk.vtkDICOMImageReader()
        reader.SetFileName(dicom_path)
        reader.Update()

        # Check if the output is valid
        if not reader.GetOutput():
            print("Error: Could not read DICOM file.")
            return

        self.vtk_image = reader.GetOutput()
        self.vtk_viewer.vtk_image = self.vtk_image

        # Extract correct spacing for RTImage using pydicom
        import pydicom
        dicom_dataset = pydicom.dcmread(dicom_path)
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
        
        # test
        #self.vtk_image.SetOrigin(50.0, 50.0, 0.0)
        #self.vtk_image.SetSpacing(0.5, 0.5, 1.0)  # Column, Row, Depth (0.8, 0.8, 1.0)

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
        
        self.vtk_viewer.set_vtk_image(self.vtk_image, self.range_slider.get_width(), self.range_slider.get_center())

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
        zoom_action.triggered.connect(self.vtk_viewer.toggle_zooming_mode)
        toolbar.addAction(zoom_action)        


        # pan toggle button
        plan_action = QAction("Pan", self)
        plan_action.setCheckable(True)
        plan_action.triggered.connect(self.vtk_viewer.toggle_panning_mode)
        toolbar.addAction(plan_action)        
        
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

    def set_default_window_level(self, image_array):
        import numpy as np

        # Set default window-level values
        min = np.min(image_array)
        max = np.max(image_array)


    def open_dicom(self):
        import SimpleITK as sitk

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

    def save_workspace(self):
        import json
        import os
        from PyQt5.QtWidgets import QFileDialog

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
                "level": self.range_slider.get_center(),
                "width": self.range_slider.get_width(),
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
                #self.set_default_window_level(self.image_array)  # Call set_default_window_level
            except Exception as e:
                self.print_status(f"Failed to load input image: {e}")
                return

        self.segmentation_list_manager.load_state(workspace_data, data_path, {'base_image': self.sitk_image})
        self.point_list_manager.load_state(workspace_data, data_path, {'base_image': self.sitk_image})

        # Restore window settings
        window_settings = workspace_data.get("window_settings", {})
        window = window_settings.get("width", 1)
        level = window_settings.get("level", 0)

        self.range_slider.low_value = level - window / 2
        self.range_slider.high_value = level + window / 2

        # Render the workspace
        if self.image_array is not None:
            self.graphics_view.render_layers()

        self.print_status(f"Workspace loaded from {data_path}.")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
