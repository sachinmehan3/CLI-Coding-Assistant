import os

def delete_file(working_directory: str, file_path: str):
    abs_working_directory = os.path.abspath(working_directory)
    abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))

    # Guardrail: Path validation against escaping the working directory
    if not abs_file_path.startswith(abs_working_directory):
        return f'Error: "{file_path}" is not in the working directory.' 

    if not os.path.exists(abs_file_path):
        return f'Error: File "{file_path}" does not exist.'
        
    if not os.path.isfile(abs_file_path):
        return f'Error: "{file_path}" is a directory, not a file.'

    try:
        os.remove(abs_file_path)
        return f'Successfully deleted "{file_path}".'
    except Exception as e:
        return f"Failed to delete file: {file_path}, {e}"
