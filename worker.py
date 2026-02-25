import json
from rich.live import Live
from rich.markdown import Markdown

from functions.get_files_info import get_file_info
from ai_utils import safe_mistral_complete

from worker_tools import WORKER_TOOLS
from worker_helpers import trim_memory, execute_tool

def run_worker_agent(client, model, console, task_description, working_dir, auto_mode=False):
    """This function contains the ReAct loop for the Worker"""

    tools = WORKER_TOOLS

    messages = [
    {
        "role": "system",
        "content": (
            "You are an expert autonomous Worker working inside a project directory. "
            "You will be assigned tasks by your Planner. Complete them fully and correctly using your tools.\n\n"

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
            "- `consult_user`: Stop loop and ask the user for help if you are repeatedly failing (e.g., Auth 401s, mysterious bugs), OR if the task is ambiguous and you need clarification on requirements or design decisions.\n"
            "- `finish_task`: End your turn. Provide a clear summary of modifications/results.\n\n"

            "OPERATIONAL RULES:\n"
            "1. NO BLIND OVERWRITES: If a file exists, `get_file_content` it first. Then use `write_file` to rewrite it completely.\n"
            "2. RELATIVE PATHS: All paths are relative. Do not invent absolute paths.\n"
            "3. BREVITY: Be brief. State your next action in 1-2 sentences before calling a tool. Do not write paragraphs of explanation.\n"
            "4. ONE TOOL AT A TIME: For file-modifying operations (`write_file`, `delete_file`, `create_directory`), call only one tool per response to avoid conflicts. Read-only tools can be batched.\n"
            "5. SELF-CORRECTION: If `run_compiler` or `run_python_file` yields errors, FIX them repeatedly before `finish_task`.\n"
            "6. NO VISUAL GUIs: You are a text-only terminal bot. NEVER open, execute, or interact with GUI files, images, or windows.\n"
        )

    },
    {"role": "user", "content": task_description}
]

    # Cached so we can rebuild the system prompt with dynamic state without losing the base rules
    WORKER_BASE_SYSTEM_PROMPT = messages[0]["content"]

    last_edited_file = None
    consecutive_edit_count = 0

    while True:
        # Inject live file tree into system prompt before every LLM call
        current_project_state = get_file_info(working_dir, ".")
        messages[0]["content"] = (
            f"{WORKER_BASE_SYSTEM_PROMPT}\n\n"
            f" CURRENT PROJECT FILES:\n{current_project_state}\n\n"
        )

        MAX_CHARS = 120000
        messages = trim_memory(messages, MAX_CHARS, console)

        with console.status("[bold cyan]Thinking...[/bold cyan]", spinner="dots"):
            response = safe_mistral_complete(
                client=client,
                model=model,
                messages=messages,
                tools=tools
            )
            
            assistant_message = response.choices[0].message
            full_content = assistant_message.content if assistant_message.content else ""
            
            stitched_tools = {}
            if assistant_message.tool_calls:
                for idx, tool_call in enumerate(assistant_message.tool_calls):
                    stitched_tools[idx] = {
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }

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
                
                function_result = execute_tool(function_name, args, working_dir, auto_mode, console)
                
                # Nudge the worker if it writes the same file repeatedly without reading it first
                if function_name == "write_file":
                    file_path = args.get("file_path")
                    if file_path == last_edited_file:
                        consecutive_edit_count += 1
                        if consecutive_edit_count >= 2:
                            function_result += "\n\nSYSTEM NUDGE: You have written to this file multiple times in a row. Consider using `get_file_content` to read the file first to ensure you have the correct context before writing again!"
                    else:
                        last_edited_file = file_path
                        consecutive_edit_count = 1
                else:
                    if function_name != "finish_task":
                        last_edited_file = None
                        consecutive_edit_count = 0

                messages.append({
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_result),
                    "tool_call_id": tool_call_id 
                })
            continue 
        else:
            nudge = "SYSTEM: You output text but did not call a tool. If you are trying to write code, you MUST use the `write_file` tool. If the task is completely finished, you MUST call the `finish_task` tool to exit."
            messages.append({"role": "user", "content": nudge})
            continue

