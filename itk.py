import SimpleITK as sitk
import numpy as np

def rot90(sitk_image, plus: bool):

    image = sitk_image

    # Convert to NumPy array while preserving data type
    pixel_type = image.GetPixelID()  # Get original pixel type
    image_array = sitk.GetArrayFromImage(image)
    origin = image.GetOrigin()
    spacing = image.GetSpacing()
    direction = image.GetDirection()

    # Rotate 90 degrees clockwise
    if plus: # x axis to y
        rotated_array = np.rot90(image_array, k=-1, axes=(1, 2))
    else: # y axis to x
        rotated_array = np.rot90(image_array, k=1, axes=(1, 2))

    # Convert back to SimpleITK image with the same pixel type
    rotated_image = sitk.GetImageFromArray(rotated_array)
    rotated_image = sitk.Cast(rotated_image, pixel_type)  # Ensure same pixel type

    # Keep metadata unchanged
    rotated_image.SetOrigin(origin)
    rotated_image.SetDirection(direction)
    rotated_image.SetSpacing([spacing[1], spacing[0], spacing[2]])
    
    return rotated_image

def flip_x(sitk_image):
    return flip(sitk_image, axis=2)

def flip_y(sitk_image):
    return flip(sitk_image, axis=1)


def flip(sitk_image, axis):
    """
    Flip a SimpleITK image along the x-axis.
    """
    # Convert to NumPy array
    pixel_type = sitk_image.GetPixelID()
    image_array = sitk.GetArrayFromImage(sitk_image)
    
    # Flip along the x-axis (axis=1)
    flipped_array = np.flip(image_array, axis)

    # Convert back to SimpleITK image
    flipped_image = sitk.GetImageFromArray(flipped_array)
    flipped_image = sitk.Cast(flipped_image, pixel_type)  # Preserve pixel type

    # Preserve metadata (origin, spacing, direction)
    origin = sitk_image.GetOrigin()
    spacing = sitk_image.GetSpacing()
    direction = sitk_image.GetDirection()

    # Update metadata
    flipped_image.SetOrigin(origin)
    flipped_image.SetSpacing(spacing)
    flipped_image.SetDirection(direction)  # Direction remains the same

    return flipped_image


if __name__ == '__main__':
    import numpy as np

    # Define a 2x8 array with values from 0 to 7
    array = np.array([[[0, 1, 2, 3],
                    [4, 5, 6, 7]]])

    print("Original Array:")
    print(array)

    # Rotate 90 degrees clockwise (k=-1 for clockwise rotation)
    #transformed_array = np.rot90(array, k=-1, axes=(1, 2))
    #transformed_array = np.flip(array, axis=1)
    transformed_array = np.flip(array, axis=2)


    print("\nTraisnformed Array (90° Clockwise):")
    print(transformed_array)

