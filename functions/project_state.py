import os
import json

def get_project_state(working_directory: str):
    """Reads the current project state, or returns a prompt to create it."""
    # Define the hardcoded location for the project tracking file
    state_path = os.path.join(working_directory, "project_state.json")
    
    # Let the agent know it needs to initialize the state if it hasn't yet
    if not os.path.exists(state_path):
        return "No project_state.json exists yet. You should use the `update_project_state` tool to initialize your project tracking."
    
    try:
        # Read the raw JSON string back into the prompt
        with open(state_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading project state: {e}"

def update_project_state(working_directory: str, state_data: dict):
    """Writes the updated state dictionary to the JSON file."""
    # Always save straight to the root of the workspace
    state_path = os.path.join(working_directory, "project_state.json")
    try:
        # Format with indent=4 so it's readable if a human opens the file
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=4)
        return "✅ Successfully saved project_state.json."
    except Exception as e:
        return f"❌ Failed to save project state: {e}"