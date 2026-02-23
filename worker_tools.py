WORKER_TOOLS = [
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
            "description": "Creates a NEW file. Do not use this for modifying existing files. You MUST provide the ENTIRE, complete file content from top to bottom.",
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
            "description": "Edits an existing file by replacing a specific search string with a new replace string. Use this to modify files without rewriting them completely.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The EXACT path to the file to edit."},
                    "search": {"type": "string", "description": "The exact string to search for and replace. Must match the file contents PERFECTLY, including whitespace and indentation."},
                    "replace": {"type": "string", "description": "The new string that will replace the search string."}
                },
                "required": ["file_path", "search", "replace"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_linter",
            "description": "Runs a linter on a Python file to check for syntax errors, undefined variables, and bad imports WITHOUT executing the code. Always use this to check your work before using run_python_file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The exact relative path to the Python file to lint."
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
            "description": "Executes a Python script and returns the console output (STDOUT and STDERR).",
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
            "name": "finish_task",
            "description": "Call this tool ONLY when you have fully completed the assigned task. This tells the Tech Lead you are done.",
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
    },
    {
        "type": "function",
        "function": {
            "name": "consult_user",
            "description": "Use this immediately if you encounter repeated errors (like API 403 Forbidden or 401 Unauthorized), get stuck in a loop, or need the user to make a decision (e.g., 'Should I try a different API?').",
            "parameters": {
                "type": "object",
                "properties": {
                    "question_and_options": {
                        "type": "string",
                        "description": "A summary of the error you are getting and the options you are giving the user to proceed."
                    }
                },
                "required": ["question_and_options"]
            }
        }
    }
]
