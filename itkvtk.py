import vtk
import SimpleITK as sitk
from vtk.util.numpy_support import numpy_to_vtk
import numpy as np

def numpy_dtype_to_vtk_type(dtype):
    """Map a NumPy dtype to the corresponding VTK type."""
    vtk_type_map = {
        np.int8: vtk.VTK_CHAR,
        np.uint8: vtk.VTK_UNSIGNED_CHAR,
        np.int16: vtk.VTK_SHORT,
        np.uint16: vtk.VTK_UNSIGNED_SHORT,
        np.int32: vtk.VTK_INT,
        np.uint32: vtk.VTK_UNSIGNED_INT,
        np.int64: vtk.VTK_LONG,  # Note: VTK_LONG may be platform-dependent
        np.uint64: vtk.VTK_UNSIGNED_LONG,
        np.float32: vtk.VTK_FLOAT,
        np.float64: vtk.VTK_DOUBLE,
    }
    
    # Ensure the dtype is a NumPy type
    dtype = np.dtype(dtype)
    
    if dtype.type in vtk_type_map:
        return vtk_type_map[dtype.type]
    else:
        raise ValueError(f"Unsupported dtype: {dtype}")

def sitk_to_vtk(sitk_image):
    """Convert a SimpleITK image to a VTK image."""
    # Get the numpy array from SimpleITK
    np_array = sitk.GetArrayFromImage(sitk_image)
    
    # Get image dimensions and metadata
    spacing = sitk_image.GetSpacing()
    origin = sitk_image.GetOrigin()
    direction = sitk_image.GetDirection()

    # Create a VTK image
    vtk_image = vtk.vtkImageData()
    vtk_image.SetDimensions(np_array.shape[::-1])  # Reverse dimensions to match VTK
    vtk_image.SetSpacing(spacing)
    vtk_image.SetOrigin(origin)

    # Convert numpy array to VTK array
    vtk_type = numpy_dtype_to_vtk_type(np_array.dtype)

    vtk_array = numpy_to_vtk(np_array.ravel(order='F'), deep=True, array_type=vtk_type) 
    vtk_image.GetPointData().SetScalars(vtk_array)

    return vtk_image


def vtk_to_sitk(vtk_image):
    """Convert a VTK image to a SimpleITK image."""
    # Extract dimensions and spacing
    dims = vtk_image.GetDimensions()
    spacing = vtk_image.GetSpacing()
    origin = vtk_image.GetOrigin()

    # Get the VTK scalar data as a numpy array
    scalars = vtk_image.GetPointData().GetScalars()
    np_array = vtk_to_numpy(scalars)
    np_array = np_array.reshape(dims[::-1])  # Reverse dimensions to match SimpleITK

    # Create a SimpleITK image
    sitk_image = sitk.GetImageFromArray(np_array)
    sitk_image.SetSpacing(spacing)
    sitk_image.SetOrigin(origin)

    return sitk_image