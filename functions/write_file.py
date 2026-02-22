import os

def write_file(working_directory: str, file_path: str, content: str):
    abs_working_directory = os.path.abspath(working_directory)
    abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))

    # Guardrail: Path validation
    if not abs_file_path.startswith(abs_working_directory):
        return f'Error: "{file_path}" is not in the working directory.' 

    # Find out which folder this file is attempting to be placed inside
    parent_dir = os.path.dirname(abs_file_path)

    # Fail explicitly if the directory isn't ready. 
    # This prevents the AI from silently failing and reinforces using create_directory.
    if not os.path.isdir(parent_dir):
        return f"Error: Parent directory '{os.path.relpath(parent_dir, working_directory)}' does not exist. Create it first using `create_directory`."

    try:
        # Write mode will completely overwrite the previous file
        with open(abs_file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f'Successfully wrote entire file to "{file_path}" ({len(content)} characters).'
    
    except Exception as e:
        return f"Failed to write to file: {file_path}, {e}"