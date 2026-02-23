MANAGER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "delegate_to_worker",
            "description": "Delegates a coding task to the developer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_milestone": {
                        "type": "string",
                        "description": "The exact name of the milestone from your initialized plan that this task fulfills."
                    },
                    "task_description": {
                        "type": "string",
                        "description": "A detailed, step-by-step explanation..."
                    }
                },
                "required": ["target_milestone", "task_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_project_plan",
            "description": "Use this to update the project plan tracker. Call this whenever you have a new milestone plan approved by the user, or when the worker completes its task and the loop continues, to reflect the updated remaining milestones.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_goal": {"type": "string", "description": "The overall goal."},
                    "milestones": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A chronological list of the remaining or updated major milestones required to finish the project."
                    }
                },
                "required": ["project_goal", "milestones"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_content",
            "description": "Reads and returns the text content of a specified file. Use this to understand existing code architecture before delegating a task to the worker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The EXACT path to the file you want to read (e.g., 'functions/api.py'). Do not guess this path."
                    }
                },
                "required": ["file_path"]
            }
        }
    }
]
