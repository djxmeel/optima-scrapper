import os


def rename_files_in_directory(directory_path, naming_func):
    if not os.path.exists(directory_path):
        print(f"The directory '{directory_path}' does not exist.")
        return

    files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]

    for filename in files:
        file_extension = os.path.splitext(filename)[1]
        new_name = naming_func(filename) + file_extension
        os.rename(os.path.join(directory_path, filename), os.path.join(directory_path, new_name))
        print(f"Renamed '{filename}' to '{new_name}'")


def renamer(filename):
    return filename.replace("", "")


# Example usage
directory_paths = [
    "../vtac_italia/PRODUCT_INFO",
    "../vtac_italia/PRODUCT_MEDIA",
    "../vtac_spain/PRODUCT_INFO",
    "../vtac_spain/PRODUCT_MEDIA",
    "../vtac_uk/PRODUCT_INFO",
    "../vtac_uk/PRODUCT_MEDIA"
]


# rename_files_in_directory(directory_path, lambda filename: filename.replace("VTAC_", ""))
for path in directory_paths:
    rename_files_in_directory(path, renamer)
    
