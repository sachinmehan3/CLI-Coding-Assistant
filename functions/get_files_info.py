import os

def get_file_info(working_directory: str, directory="."):
    abs_working_directory = os.path.abspath(working_directory)
    abs_directory = os.path.abspath(os.path.join(working_directory, directory))

    # Guardrail 1: Prevent escaping the working directory
    if not abs_directory.startswith(abs_working_directory):
        return f'Error: "{directory}" is not in the working directory.'   
    
    # Guardrail 2: Check if the path actually exists
    if not os.path.exists(abs_directory):
        return f"Error: The directory '{directory}' does not exist."

    if not os.path.isdir(abs_directory):
        return f"Error: '{directory}' is a file, not a directory."

    # CRITICAL: Ignore these folders so they don't blow up the context window!
    IGNORE_DIRS = {'.venv', 'venv', 'env', '__pycache__', '.git', 'node_modules', '.idea', '.vscode'}

    final_response = f"📂 Project Structure (Relative to Workspace Root):\n\n"
    
    is_empty = True

    # os.walk recursively goes through all subdirectories
    for root, dirs, files in os.walk(abs_directory):
        # Modify the 'dirs' list in-place to skip ignored directories entirely
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            is_empty = False
            file_path = os.path.join(root, file)
            
            # Get the path RELATIVE TO THE WORKING DIRECTORY.
            # This is crucial so the LLM knows the exact string to use in other tools!
            rel_path = os.path.relpath(file_path, abs_working_directory)
            size = os.path.getsize(file_path)

            # Append to our final response string
            final_response += f"- {rel_path} (Size: {size} bytes)\n"
            
    # Provide a clear message if no files were found
    if is_empty:
        return f"The directory '{directory}' is completely empty."

    return final_response