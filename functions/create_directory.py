import os

def create_directory(working_directory, directory_path):
    abs_working_directory = os.path.abspath(working_directory)
    abs_directory_path = os.path.abspath(os.path.join(working_directory, directory_path))

    # Security check: Ensure we aren't creating a folder outside the project workspace
    if not abs_directory_path.startswith(abs_working_directory):
        return f'Error: "{directory_path}" is not in the working directory.'

    # Return a note if it already exists so the agent doesn't panic
    if os.path.exists(abs_directory_path):
        return f'Note: "{directory_path}" already exists.'

    try:
        # exist_ok=True handles race conditions, though makedirs is robust
        # This will create all intermediate folders if they don't exist
        os.makedirs(abs_directory_path, exist_ok=True)
        return f'Successfully created directory structure: "{directory_path}"'
    except Exception as e:
        return f"Failed to create directory: {directory_path}, {e}"