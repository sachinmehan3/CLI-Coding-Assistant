import os

def edit_file(working_directory: str, file_path: str, search: str, replace: str):
    abs_working_directory = os.path.abspath(working_directory)
    abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))

    # Guardrail 1: Path validation
    if not abs_file_path.startswith(abs_working_directory):
        return f'Error: "{file_path}" is not in the working directory.' 

    # Guardrail 2: Check if file exists
    if not os.path.isfile(abs_file_path):
        return f"Error: '{file_path}' does not exist. Use `write_file` to create a new file."

    try:
        with open(abs_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if search not in content:
            return f"Error: The exact search string was not found in '{file_path}'. Please assure your 'search' string perfectly matches the file text including spaces and indentation."

        count = content.count(search)
        if count > 1:
            return f"Error: The search string occurs {count} times in the file. Please provide a more specific search string that uniquely identifies the block to replace."

        new_content = content.replace(search, replace)

        with open(abs_file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        return f'Successfully edited "{file_path}". Replaced a {len(search)} char block with a {len(replace)} char block.'
    
    except Exception as e:
        return f"Failed to edit file: {file_path}, {e}"
