SUBAGENT_TOOL = {
    "type": "function",
    "function": {
        "name": "spawn_subagent",
        "description": "Spawn an isolated sub-agent to handle a complex, self-contained subtask. The sub-agent gets its own context and tools, executes autonomously, and returns a summary. Use this for large refactors, research tasks, or any work you want to delegate without cluttering your main context.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": "A detailed prompt describing what the sub-agent should accomplish. Be specific — include file names, requirements, and expected outcomes."
                }
            },
            "required": ["task_description"]
        }
    }
}

BASE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_files_info",
            "description": "Returns a recursive, complete map of all files and directories in the project. Use this first to understand the layout of the codebase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "The directory to inspect. Defaults to '.' for the whole project."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_content",
            "description": "Reads and returns the text content of a specified file. IMPORTANT: You must provide the EXACT relative path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The EXACT path to the file you want to read. Do not guess this path."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Creates a new directory or a nested directory structure. Use this before creating files in a new folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "The path of the directory to create (e.g., 'scripts', 'tests/unit')."
                    }
                },
                "required": ["directory_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Creates a new file or overwrites an existing file. You MUST provide the ENTIRE, complete file content from top to bottom.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The path and filename to write to."},
                    "content": {"type": "string", "description": "The complete, final code for the file."}
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Edit an existing file by replacing a specific block of text with new text. "
                "PREFERRED over `write_file` for modifying existing files — saves tokens and reduces errors. "
                "First tries exact match, then falls back to fuzzy matching. "
                "IMPORTANT: Copy the search text EXACTLY from the file including all whitespace and indentation. "
                "The search string must uniquely identify the block to replace (include enough surrounding lines if needed)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The exact relative path to the file to edit."},
                    "search": {"type": "string", "description": "The EXACT text block to find in the file. Copy this directly from `get_file_content` output. Include enough lines to uniquely identify the location."},
                    "replace": {"type": "string", "description": "The new text to replace the search block with."}
                },
                "required": ["file_path", "search", "replace"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Deletes a specific existing file. Use this to clean up unnecessary files or when restructuring.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The exact relative path of the file to delete."}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_compiler",
            "description": "Compiles a Python file (using py_compile) to check for syntax errors WITHOUT executing the code. Always use this to check your work before using run_python_file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The exact relative path to the Python file to compile."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python_file",
            "description": "Executes a Python script and returns the console output (STDOUT and STDERR). CAUTION: NEVER execute GUI applications or blocking servers. If the script contains a GUI (e.g. tkinter, PyQt), test it strictly by using the run_compiler tool instead of running it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The exact relative path to the Python file to run."
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional command-line arguments to pass to the script."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Searches the web for up-to-date information, documentation, or tutorials.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "install_package",
            "description": "Installs third-party Python packages using 'uv add'. Use this immediately if you encounter a ModuleNotFoundError when running a test.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "The PyPI package name to install (e.g., 'requests', 'beautifulsoup4', 'fastapi'). You can provide multiple packages separated by spaces."
                    }
                },
                "required": ["package_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": "Stop and ask the user a question. Use this if you need clarification on requirements, design decisions, or if you are repeatedly failing and need human help.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question you want to ask the user, including any options or context they need."
                    }
                },
                "required": ["question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_tracker",
            "description": (
                "Create or update the project progress tracker (PROGRESS.md). "
                "Write the FULL markdown content for the file. Use this at the START of a project "
                "to record the goal and milestones, and after completing work to update the status. "
                "Use markdown checklists: `- [x]` for done, `- [/]` for in-progress, `- [ ]` for pending."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "markdown_content": {
                        "type": "string",
                        "description": (
                            "The COMPLETE markdown content for PROGRESS.md. "
                            "Structure it with a project title, status, and checklist sections. "
                            "Example:\n"
                            "# Project: Build REST API\n"
                            "## Status: In Progress\n"
                            "## Completed\n"
                            "- [x] Set up project structure\n"
                            "## In Progress\n"
                            "- [/] Implementing auth endpoints\n"
                            "## Pending\n"
                            "- [ ] Write unit tests\n"
                        )
                    }
                },
                "required": ["markdown_content"]
            }
        }
    }
]

# Main agent gets all tools + spawn_subagent
AGENT_TOOLS = BASE_TOOLS + [SUBAGENT_TOOL]

# Sub-agent gets base tools + finish_task (no spawn_subagent, no infinite nesting)
SUBAGENT_TOOLS = BASE_TOOLS + [
    {
        "type": "function",
        "function": {
            "name": "finish_task",
            "description": "Call this tool ONLY when you have fully completed the assigned task. This ends your execution and returns your summary to the main agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "A summary of the actions you took, files you modified, and test results."
                    }
                },
                "required": ["summary"]
            }
        }
    }
]
