import os

PROGRESS_FILENAME = "PROGRESS.md"


def get_progress(working_directory: str):
    """Reads the current PROGRESS.md content, or returns a prompt to create it."""
    progress_path = os.path.join(working_directory, PROGRESS_FILENAME)

    if not os.path.exists(progress_path):
        return "No PROGRESS.md exists yet. Use the `update_tracker` tool to initialize project tracking."

    try:
        with open(progress_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading PROGRESS.md: {e}"


def write_progress(working_directory: str, markdown_content: str):
    """Writes the full PROGRESS.md content to disk."""
    progress_path = os.path.join(working_directory, PROGRESS_FILENAME)
    try:
        with open(progress_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        return "Successfully saved PROGRESS.md."
    except Exception as e:
        return f"Failed to save PROGRESS.md: {e}"