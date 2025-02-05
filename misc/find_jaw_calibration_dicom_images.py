import os



def get_mean_pixel_value(dcm_file):
    import SimpleITK as sitk
    import numpy as np

    # Path to your DICOM file
    dicom_file = dcm_file

    # Read the DICOM file
    image = sitk.ReadImage(dicom_file)

    # Convert the image to a NumPy array
    image_array = sitk.GetArrayFromImage(image)

    # Calculate the mean pixel value
    mean_pixel_value = np.mean(image_array)

    return mean_pixel_value

def find_jaw_cal_kv_dcm_files(root_folder):
    dcm_files = []
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for file in filenames:
            file_path = os.path.join(dirpath, file)
            try:
                if('TrueBeamSH' in dirpath):
                    if file.startswith('RI.') and file.endswith('.dcm'):
                        if os.path.getsize(file_path)/1024 > 1500:
                            if get_mean_pixel_value(file_path) > 50000:
                                dcm_files.append(file_path)
            except:
                print(f'skiping... {file_path}')
    return dcm_files

def find_leeds_kv_dcm_files(root_folder):
    dcm_files = []
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for file in filenames:
            file_path = os.path.join(dirpath, file)
            try:
                if('TrueBeamSH' in dirpath):
                    if file.startswith('RI.') and file.endswith('.dcm'):
                        if os.path.getsize(file_path)/1024 > 1500:
                            if get_mean_pixel_value(file_path) < 50000:
                                dcm_files.append(file_path)
            except:
                print(f'skiping... {file_path}')
    return dcm_files

def filter_by_file_size(dcm_files, file_size):
    out_list = []
    for dcm_file in dcm_files:
        if os.path.getsize(dcm_file) == file_size:
            out_list.append(dcm_file)

    return out_list

def file_count(folder_path):
    # number of existing files
    file_count = sum(1 for item in os.listdir(folder_path)
                 if os.path.isfile(os.path.join(folder_path, item))) 
    return file_count


def find_and_copy_jaw_cal_kv(dir):
    out_dir = './sample_images/jaw_cal_kv'

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # sample dicom
    #sample = 'W:/RadOnc/Planning/Physics QA/2024/1.Monthly QA/TrueBeamSH/2024_11/imaging\jaw_cal.dcm'
    sample = 'W:/RadOnc/Planning/Physics QA/2024/1.Monthly QA/TrueBeamSH/2024_11/imaging\jaw_cal.dcm'
    file_size = os.path.getsize(sample)  # Size in bytes
    print(f'file_size={file_size}')
    print(f'mean_pixel_value={get_mean_pixel_value(sample)}')

    folder_path = dir
    dcm_files = find_jaw_cal_kv_dcm_files(folder_path)
    
    num_existing_files = file_count(out_dir)

    import shutil
    for i, file in enumerate(dcm_files):
        print(f'{file} - {os.path.getsize(file)/1024} - {get_mean_pixel_value(file)}')
        file_dst = os.path.join(out_dir, f'image_{str(i+num_existing_files).zfill(3)}.dcm')
        try:
            shutil.copy2(file, file_dst)
            print("File copied successfully!")
        except FileNotFoundError:
            print("Source file not found.")
        except PermissionError:
            print("Permission denied.")
        except Exception as e:
            print(f"Error: {e}")

def find_and_copy_leeds_kv(dir):
    out_dir = './sample_images/leeds_kv'

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # sample dicom
    #sample = 'W:/RadOnc/Planning/Physics QA/2024/1.Monthly QA/TrueBeamSH/2024_11/imaging\jaw_cal.dcm'
    sample = 'W:/RadOnc/Planning/Physics QA/2024/1.Monthly QA/TrueBeamSH/2024_11/imaging\leeds.dcm'
    file_size = os.path.getsize(sample)  # Size in bytes
    print(f'file_size={file_size}')
    print(f'mean_pixel_value={get_mean_pixel_value(sample)}')

    folder_path = dir
    dcm_files = find_leeds_kv_dcm_files(folder_path)
    
    num_existing_files = file_count(out_dir)

    import shutil
    for i, file in enumerate(dcm_files):
        print(f'{file} - {os.path.getsize(file)/1024} - {get_mean_pixel_value(file)}')
        file_dst = os.path.join(out_dir, f'image_{str(i+num_existing_files).zfill(3)}.dcm')
        try:
            shutil.copy2(file, file_dst)
            print("File copied successfully!")
        except FileNotFoundError:
            print("Source file not found.")
        except PermissionError:
            print("Permission denied.")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":

    find_and_copy_jaw_cal_kv('W:/RadOnc/Planning/Physics QA/2023')
    find_and_copy_jaw_cal_kv('W:/RadOnc/Planning/Physics QA/2024')

    find_and_copy_leeds_kv('W:/RadOnc/Planning/Physics QA/2023')
    find_and_copy_leeds_kv('W:/RadOnc/Planning/Physics QA/2024')



    print('done')