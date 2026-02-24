import json
from rich.live import Live
from rich.markdown import Markdown

# Import all custom functions
from functions.get_files_info import get_file_info
from ai_utils import safe_mistral_complete

# Import worker refactored tools and helpers
from worker_tools import WORKER_TOOLS
from worker_helpers import trim_memory, execute_tool

# ==========================================
# THE WORKER AGENT (The Developer)
# ==========================================
def run_worker_agent(client, model, console, task_description, working_dir, auto_mode=False):
    """This function contains the ReAct loop for the Worker"""
    # The Worker Agent operates inside this function, responding directly to the Tech Lead's task_description

    # The tools the worker can use
    tools = WORKER_TOOLS

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
            "- `write_file`: Use to create a NEW file or modify an EXISTING file. CRITICAL: You MUST provide the ENTIRE, complete file content.\n"
            "- `delete_file`: Use to explicitly delete an existing file.\n"
            "- `create_directory`: Use to create nested folders BEFORE explicitly writing files into them.\n"
            "- `run_compiler`: Use on `.py` files strictly to check for syntax errors. ALWAYS do this BEFORE running new code, and use this as your primary way to test GUI applications.\n"
            "- `run_python_file`: Executes a script for STDOUT/STDERR. NEVER execute GUI apps or blocking servers under any circumstances! If the code contains a GUI, test it ONLY by compiling.\n"
            "- `web_search`: Look up documentation, APIs, or tutorials.\n"
            "- `install_package`: Install PyPI dependencies when hitting ModuleNotFoundError.\n"
            "- `consult_user`: Stop loop and ask the user for help if you are repeatedly failing (e.g., Auth 401s, mysterious bugs).\n"
            "- `finish_task`: End your turn. Provide a clear summary of modifications/results.\n\n"

            "OPERATIONAL RULES:\n"
            "1. NO BLIND OVERWRITES: If a file exists, `get_file_content` it first. Then use `write_file` to rewrite it completely.\n"
            "2. RELATIVE PATHS: All paths are relative. Do not invent absolute paths.\n"
            "3. EXTREME CONCISENESS: Output ONE single sentence stating your immediate next action before calling a tool. No paragraphs.\n"
            "4. SELF-CORRECTION: If `run_compiler` or `run_python_file` yields errors, FIX them repeatedly before `finish_task`.\n"
            "5. NO VISUAL GUIs: You are a text-only terminal bot. NEVER open, execute, or interact with GUI files, images, or windows.\n"
        )
    },
    {"role": "user", "content": task_description}
]


    # Save the base system prompt locally so we can rebuild it dynamically
    # This ensures the core rules remain untouched while allowing us to inject changing variables (like files) into the bottom.
    WORKER_BASE_SYSTEM_PROMPT = messages[0]["content"]

    # Track consecutive edits to the same file to nudge the worker
    last_edited_file = None
    consecutive_edit_count = 0

    # Infinite ReAct (Reason + Act) loop for the worker.
    while True:
        # FETCH THE LATEST REALITY ON EVERY LOOP
        # We constantly rescan the disk so the AI knows EXACTLY what files exist at all times.
        current_project_state = get_file_info(working_dir, ".")
        
        # Dynamically update the System Prompt (Index 0) to know about new files!
        messages[0]["content"] = (
            f"{WORKER_BASE_SYSTEM_PROMPT}\n\n"
            f" CURRENT PROJECT FILES:\n{current_project_state}\n\n"
        )

        # --- Character-Based Context Sliding Window ---
        MAX_CHARS = 120000  # Roughly 6,000 tokens
        
        messages = trim_memory(messages, MAX_CHARS, console)

        # --- SYNCHRONOUS API CALL ---
        with console.status("[bold cyan]Coding Assistant is thinking...[/bold cyan]", spinner="dots"):
            response = safe_mistral_complete(
                client=client,
                model=model,
                messages=messages,
                tools=tools
            )
            
            # Since this is a completion call, we get the full message at once
            assistant_message = response.choices[0].message
            full_content = assistant_message.content if assistant_message.content else ""
            
            # Extract tool calls if any
            stitched_tools = {}
            if assistant_message.tool_calls:
                for idx, tool_call in enumerate(assistant_message.tool_calls):
                    # For Mistral, tool_call includes id, function with name and arguments
                    stitched_tools[idx] = {
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }

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
                    return summary
                
                # Execute the tool using our refactored helper
                function_result = execute_tool(function_name, args, working_dir, auto_mode, console)
                
                # --- Consecutive Edit Tracking ---
                # If they edit the same file more than once consecutively without reading it, nudge them.
                if function_name == "edit_file":
                    file_path = args.get("file_path")
                    if file_path == last_edited_file:
                        consecutive_edit_count += 1
                        if consecutive_edit_count >= 2:
                            function_result += "\n\nSYSTEM NUDGE: You have edited this file multiple times in a row. Consider using `get_file_content` to read the file first to ensure you have the correct context and line numbers before editing again!"
                    else:
                        last_edited_file = file_path
                        consecutive_edit_count = 1
                else:
                    # Reset if they use a different tool (like reading the file)
                    if function_name != "finish_task":
                        last_edited_file = None
                        consecutive_edit_count = 0
                # ---------------------------------

                # Append result back to memory
                messages.append({
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_result),
                    "tool_call_id": tool_call_id 
                })
            continue 
        else:
            # If the worker just talks without using a tool, nudge it back!
            nudge = "SYSTEM: You output text but did not call a tool. If you are trying to write code, you MUST use the `write_file` tool. If the task is completely finished, you MUST call the `finish_task` tool to exit."
            messages.append({"role": "user", "content": nudge})
            continue

