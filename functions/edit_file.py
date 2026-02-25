import os
import difflib


def find_fuzzy_match(file_lines, search_lines, threshold=0.6):
    """Slides a window over file_lines to find the best fuzzy match for search_lines."""
    best_ratio = 0
    best_start = -1
    search_len = len(search_lines)

    for i in range(len(file_lines) - search_len + 1):
        chunk = file_lines[i : i + search_len]
        ratio = difflib.SequenceMatcher(None, chunk, search_lines).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_start = i

    if best_ratio >= threshold:
        return best_start, search_len, best_ratio
    return None


def edit_file(working_directory: str, file_path: str, search: str, replace: str):
    abs_working_directory = os.path.abspath(working_directory)
    abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))

    if not abs_file_path.startswith(abs_working_directory):
        return f'Error: "{file_path}" is not in the working directory.' 

    if not os.path.isfile(abs_file_path):
        return f"Error: '{file_path}' does not exist. Use `write_file` to create a new file."

    try:
        with open(abs_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Attempt 1: Exact match
        if search in content:
            count = content.count(search)
            if count > 1:
                return (
                    f"Error: The search string occurs {count} times in the file. "
                    f"Please provide a more specific search string that uniquely identifies the block to replace."
                )
            new_content = content.replace(search, replace)
            with open(abs_file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f'Successfully edited "{file_path}" (exact match). Replaced a {len(search)} char block with a {len(replace)} char block.'

        # Attempt 2: Fuzzy match using difflib
        file_lines = content.splitlines(keepends=True)
        search_lines = search.splitlines(keepends=True)

        # Ensure search_lines has proper line endings for comparison
        if search_lines and not search_lines[-1].endswith("\n"):
            search_lines[-1] += "\n"

        match = find_fuzzy_match(file_lines, search_lines)

        if match is None:
            return (
                f"Error: Could not find a match (exact or fuzzy) in '{file_path}'. "
                f"Please use `get_file_content` to re-read the file and provide an accurate search string."
            )

        start, length, ratio = match

        original_chunk = "".join(file_lines[start : start + length])

        # Replace the matched region
        replace_with_newline = replace if replace.endswith("\n") else replace + "\n"
        new_lines = file_lines[:start] + [replace_with_newline] + file_lines[start + length :]
        new_content = "".join(new_lines)

        with open(abs_file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return (
            f'Successfully edited "{file_path}" (fuzzy match, {ratio:.0%} similarity). '
            f'Replaced {length} lines starting at line {start + 1}.'
        )

    except Exception as e:
        return f"Failed to edit file: {file_path}, {e}"
