import json
from rich.live import Live
from rich.markdown import Markdown

# Import all custom functions
from functions.get_files_info import get_file_info
from functions.get_file_content import get_file_content
from functions.write_file import write_file
from functions.create_directory import create_directory
from functions.run_python_file import run_python_file
from functions.web_search import web_search
from functions.install_package import install_package
from functions.run_linter import run_linter
import asyncio

# ==========================================
# THE WORKER AGENT (The Developer)
# ==========================================
async def run_worker_agent(client, model, console, task_description, working_dir, auto_mode=False):
    """This function contains the original ReAct loop you built!"""
    # The Worker Agent operates inside this function, responding directly to the Tech Lead's task_description
    console.print("\n[bold magenta] Worker Agent has received the task and is executing...[/bold magenta]")

    # The tools the worker can use
    tools = [

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
                "description": "Creates a new file or OVERWRITES an existing file. You MUST provide the ENTIRE, complete file content from top to bottom. Never output partial code, snippets, or placeholders.",
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

    messages = [
    {
        "role": "system",
        "content": (
            "You are an expert autonomous developer working inside a project directory. "
            "You will be assigned tasks by your Tech Lead. Complete them fully and correctly using your tools.\n\n"

            f"CURRENT PROJECT STATE:\n[Dynamically injected below]\n\n"

            "AVAILABLE TOOLS & WHEN TO USE THEM:\n"
            "- `get_files_info`: Use to map out the directory structure and discover files. Skip hidden/env folders.\n"
            "- `get_file_content`: Use once BEFORE modifying a file to gather its exact contents.\n"
            "- `write_file`: Use to create or overwrite a file. CRITICAL: You MUST provide the ENTIRE, complete file content. NEVER use placeholders or partial code.\n"
            "- `create_directory`: Use to create nested folders BEFORE explicitly writing files into them.\n"
            "- `run_linter`: Use on `.py` files strictly to check for syntax and import errors. ALWAYS do this BEFORE running new code.\n"
            "- `run_python_file`: Executes a script for STDOUT/STDERR. NEVER execute GUI apps or blocking servers.\n"
            "- `web_search`: Look up documentation, APIs, or tutorials.\n"
            "- `install_package`: Install PyPI dependencies when hitting ModuleNotFoundError.\n"
            "- `consult_user`: Stop loop and ask the user for help if you are repeatedly failing (e.g., Auth 401s, mysterious bugs).\n"
            "- `finish_task`: End your turn. Provide a clear summary of modifications/results.\n\n"

            "OPERATIONAL RULES:\n"
            "1. NO BLIND OVERWRITES: If a file exists, `get_file_content` it first. Then `write_file` it wholly.\n"
            "2. RELATIVE PATHS: All paths are relative. Do not invent absolute paths.\n"
            "3. EXTREME CONCISENESS: Output ONE single sentence stating your immediate next action before calling a tool. No paragraphs.\n"
            "4. SELF-CORRECTION: If `run_linter` or `run_python_file` yields errors, FIX them repeatedly before `finish_task`.\n"
        )
    },
    {"role": "user", "content": task_description}
]


    # Save the base system prompt locally so we can rebuild it dynamically
    # This ensures the core rules remain untouched while allowing us to inject changing variables (like files) into the bottom.
    WORKER_BASE_SYSTEM_PROMPT = messages[0]["content"]

    # Infinite ReAct (Reason + Act) loop for the worker.
    while True:
        # FETCH THE LATEST REALITY ON EVERY LOOP
        # We constantly rescan the disk so the AI knows EXACTLY what files exist at all times.
        current_project_state = get_file_info(working_dir, ".")
        
        # Dynamically update the System Prompt (Index 0) to know about new files!
        messages[0]["content"] = (
            f"{WORKER_BASE_SYSTEM_PROMPT}\n\n"
            f"📂 CURRENT PROJECT FILES:\n{current_project_state}\n\n"
        )

        # --- Character-Based Context Sliding Window ---
        MAX_CHARS = 120000  # Roughly 6,000 tokens (Leaves plenty of room for Mistral's 32k window)
        
        # Helper to safely get the string length of a message
        def get_msg_length(msg):
            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
            # Also account for tool calls taking up space
            tool_calls = msg.get("tool_calls", []) if isinstance(msg, dict) else getattr(msg, "tool_calls", [])
            return len(str(content)) + len(str(tool_calls))

        total_length = sum(get_msg_length(m) for m in messages)

        if total_length > MAX_CHARS:
            console.print(f"\n[dim yellow]🧹 Worker memory reached {total_length} chars. Truncating older steps to protect context window...[/dim yellow]")
            
            # Always keep System Prompt [0] and Manager's Task [1]
            core_messages = messages[:2]
            core_length = sum(get_msg_length(m) for m in core_messages)
            
            tail = []
            tail_length = 0
            
            # Walk backwards through the rest of the messages
            for i in range(len(messages) - 1, 1, -1):
                msg = messages[i]
                msg_len = get_msg_length(msg)
                
                # If adding this message exceeds our budget (leaving a 2000 char safety buffer)
                if core_length + tail_length + msg_len > (MAX_CHARS - 2000):
                    break
                    
                tail.insert(0, msg) # Prepend to keep chronological order
                tail_length += msg_len
                
            # Bulletproof Boundary: Clean up orphaned 'tool' messages at the start of the tail
            while len(tail) > 0:
                first_msg = tail[0]
                role = first_msg.get("role") if isinstance(first_msg, dict) else getattr(first_msg, "role", "")
                
                if role == "tool":
                    tail.pop(0) # Drop the orphan
                else:
                    break # We found a safe Assistant or User message
                    
            messages = core_messages + tail
            console.print(f"[dim yellow]✅ Memory optimized. Resuming with {sum(get_msg_length(m) for m in messages)} chars.[/dim yellow]")

        # --- NEW STREAMING API CALL ---
        # Strings to hold the final output since the LLM gives it to us in tiny fragments
        full_content = ""
        stitched_tools = {}

        console.print("\n[dim cyan]⚙️ Worker is thinking...[/dim cyan]")
        
        # Start a rich live block to visually smoothly append tokens to the console as they come from the API
        with Live(Markdown(""), console=console, refresh_per_second=15) as live:
            response = await client.chat.stream_async(
                model=model,
                messages=messages,
                tools=tools
            )
            
            async for chunk in response:
                delta = chunk.data.choices[0].delta
                
                # 1. Stream Text
                if delta.content:
                    full_content += delta.content
                    live.update(Markdown(full_content))
                    
                # 2. Stitch Tool Calls in the Background
                if delta.tool_calls:
                    for tool_chunk in delta.tool_calls:
                        idx = tool_chunk.index
                        if idx not in stitched_tools:
                            stitched_tools[idx] = {
                                "id": tool_chunk.id,
                                "name": tool_chunk.function.name if tool_chunk.function.name else "",
                                "arguments": tool_chunk.function.arguments if tool_chunk.function.arguments else ""
                            }
                        else:
                            if tool_chunk.function.name:
                                stitched_tools[idx]["name"] += tool_chunk.function.name
                            if tool_chunk.function.arguments:
                                stitched_tools[idx]["arguments"] += tool_chunk.function.arguments

        # --- RECONSTRUCT WORKER MESSAGE FOR MEMORY ---
        assistant_msg = {
            "role": "assistant",
            "content": full_content
        }
        
        parsed_tool_calls = []
        
        if stitched_tools:
            tool_calls_list = []
            for idx, tc in stitched_tools.items():
                parsed_tool_calls.append(tc)
                
                tool_calls_list.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"]
                    }
                })
            assistant_msg["tool_calls"] = tool_calls_list
            
        messages.append(assistant_msg)
        # --- END STREAMING BLOCK ---
        
        # Did the Worker decide to use a tool?
        if parsed_tool_calls:
            for tc in parsed_tool_calls:
                function_name = tc["name"]
                args_string = tc["arguments"]
                tool_call_id = tc["id"]
                
                try:
                    args = json.loads(args_string)
                except json.JSONDecodeError:
                    args = {}

                if function_name == "finish_task":
                    summary = args.get("summary", "Task completed without summary.")
                    console.print(f"\n[bold green]✅ Worker task complete![/bold green]")
                    return summary
                
                function_result = ""

                # --- NEW: Fast, Silent Tool Execution for Data Retrieval ---
                if function_name in ["get_files_info", "get_file_content", "create_directory", "web_search", "run_linter"]:
                    with console.status(f"[bold cyan]Worker executing {function_name}...[/bold cyan]", spinner="dots"):
                        if function_name == "get_files_info":
                            function_result = await asyncio.to_thread(get_file_info, working_dir, args.get("directory", "."))
                            console.print(f"[bold green]✓[/bold green] [dim]Checked directory tree[/dim]")
                            
                        elif function_name == "get_file_content":
                            function_result = await asyncio.to_thread(get_file_content, working_dir, args.get("file_path"))
                            console.print(f"[bold green]✓[/bold green] [dim]Read file: {args.get('file_path')}[/dim]")
                            
                        elif function_name == "create_directory":
                            function_result = await asyncio.to_thread(create_directory, working_dir, args.get("directory_path"))
                            console.print(f"[bold green]✓[/bold green] [dim]Created directory: {args.get('directory_path')}[/dim]")
                            
                        elif function_name == "web_search":
                            function_result = await asyncio.to_thread(web_search, args.get("query"))
                            console.print(f"[bold green]✓[/bold green] [dim]Searched web for: {args.get('query')}[/dim]")
                            
                        elif function_name == "run_linter":
                            function_result = await asyncio.to_thread(run_linter, working_dir, args.get("file_path"))
                            console.print(f"[bold green]✓[/bold green] [dim]Linted file: {args.get('file_path')}[/dim]")

                # --- NEW: Auto-Bypass Logic for Destructive/Execution Tools ---
                elif function_name == "write_file":
                    file_path = args.get("file_path")
                    content = args.get("content")
                    
                    approval = 'y' if auto_mode else ''
                    if auto_mode:
                        console.print(f"[dim yellow]⚡ Auto-approving write to '{file_path}'[/dim yellow]")
                    else:
                        console.print(f"\n[bold red] WARNING: Worker wants to WRITE/OVERWRITE '{file_path}'.[/bold red]")
                        while approval.strip().lower() not in ['y', 'yes', 'n', 'no']:
                            approval = await asyncio.to_thread(console.input, "[bold red]Approve full file write? (y/n) > [/bold red]")
                    
                    with console.status(f"[bold cyan]Writing {file_path}...[/bold cyan]", spinner="dots"):
                        if approval.strip().lower() in ['y', 'yes']:
                            function_result = await asyncio.to_thread(write_file, working_dir, file_path, content)
                            console.print(f"[bold green]✓[/bold green] [dim]Wrote file: {file_path}[/dim]")
                        else:
                            function_result = "SYSTEM ERROR: User denied permission to write file." 

                elif function_name == "run_python_file":
                    file_path = args.get("file_path")
                    script_args = args.get("args", [])
                    
                    approval = 'y' if auto_mode else ''
                    if auto_mode:
                        console.print(f"[dim yellow]⚡ Auto-approving execution of '{file_path}'[/dim yellow]")
                    else:
                        console.print(f"\n[bold red] WARNING: Worker wants to EXECUTE '{file_path}'.[/bold red]")
                        while approval.strip().lower() not in ['y', 'yes', 'n', 'no']:
                            approval = await asyncio.to_thread(console.input, "[bold red]Approve execution? (y/n) > [/bold red]")
                            
                    with console.status(f"[bold cyan]Executing {file_path}...[/bold cyan]", spinner="dots"):
                        if approval.strip().lower() in ['y', 'yes']:
                            function_result = await asyncio.to_thread(run_python_file, working_dir, file_path, script_args)
                            console.print(f"[bold green]✓[/bold green] [dim]Executed: {file_path}[/dim]")
                        else:
                            function_result = f"SYSTEM ERROR: User denied permission."
                
                elif function_name == "install_package":
                    package_name = args.get("package_name")
                    
                    approval = 'y' if auto_mode else ''
                    if auto_mode:
                        console.print(f"[dim yellow]⚡ Auto-approving install of '{package_name}'[/dim yellow]")
                    else:
                        console.print(f"\n[bold red] WARNING: Worker wants to INSTALL PACKAGE: '{package_name}'.[/bold red]")
                        while approval.strip().lower() not in ['y', 'yes', 'n', 'no']:
                            approval = await asyncio.to_thread(console.input, "[bold red]Approve installation? (y/n) > [/bold red]")
                    
                    with console.status(f"[bold cyan]Installing {package_name}...[/bold cyan]", spinner="dots"):
                        if approval.strip().lower() in ['y', 'yes']:
                            function_result = await asyncio.to_thread(install_package, working_dir, package_name)
                            console.print(f"[bold green]✓[/bold green] [dim]Installed: {package_name}[/dim]")
                        else:
                            function_result = f"SYSTEM ERROR: User denied permission."

                elif function_name == "consult_user":
                    question = args.get("question_and_options", "")
                    console.print("\n[bold red] WORKER IS STUCK & NEEDS YOUR INPUT:[/bold red]")
                    console.print(Markdown(question))
                    user_feedback = await asyncio.to_thread(console.input, "\n[bold blue]Your response (or type 'exit' to stop) > [/bold blue]")
                    if user_feedback.lower() in ['exit', 'quit']:
                        return "Task aborted by user during consultation."
                    function_result = f"USER INSTRUCTION: {user_feedback}"

                # Append result back to memory
                messages.append({
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_result),
                    "tool_call_id": tool_call_id 
                })
            continue 
        else:
            # --- THE GUARDRAIL ---
            # If the worker just talks without using a tool, nudge it back!
            nudge = "SYSTEM: You output text but did not call a tool. If you are trying to write code, you MUST use the `write_file` tool. If the task is completely finished, you MUST call the `finish_task` tool to exit."
            messages.append({"role": "user", "content": nudge})
            continue
