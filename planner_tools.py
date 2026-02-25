PLANNER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "delegate_to_worker",
            "description": "Delegates the entire project to the Worker agent in one huge prompt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_milestone": {
                        "type": "string",
                        "description": "A short name for the overall feature/project."
                    },
                    "task_description": {
                        "type": "string",
                        "description": "A massive, highly detailed prompt containing ALL specifications, architectures, features, directory structures to create, and files to write."
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
            "description": "Use this during the Planning Stage to save the agreed features to the project tracker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_goal": {"type": "string", "description": "The overall goal."},
                    "milestones": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of the high-level features/specifications required for the project."
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
            "description": "Reads and returns the text content of a specified file. Use this to understand existing code architecture before delegating a task to the Worker.",
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
