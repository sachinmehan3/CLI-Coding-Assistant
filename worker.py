import json
import asyncio
from rich.live import Live
from rich.markdown import Markdown

# Import all custom functions
from functions.get_files_info import get_file_info
from ai_utils import safe_mistral_stream_async

# Import worker refactored tools and helpers
from worker_tools import WORKER_TOOLS
from worker_helpers import trim_memory, execute_tool

# ==========================================
# THE WORKER AGENT (The Developer)
# ==========================================
async def run_worker_agent(client, model, console, task_description, working_dir, auto_mode=False):
    """This function contains the ReAct loop for the Worker"""
    # The Worker Agent operates inside this function, responding directly to the Tech Lead's task_description
    console.print("\n[bold magenta] Worker Agent has received the task and is executing...[/bold magenta]")

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
            "- `write_file`: Use to create a NEW file. CRITICAL: You MUST provide the ENTIRE, complete file content.\n"
            "- `edit_file`: Use to modify an EXISTING file. Provide the exact string to search for and the replacement string.\n"
            "- `create_directory`: Use to create nested folders BEFORE explicitly writing files into them.\n"
            "- `run_linter`: Use on `.py` files strictly to check for syntax and import errors. ALWAYS do this BEFORE running new code.\n"
            "- `run_python_file`: Executes a script for STDOUT/STDERR. NEVER execute GUI apps or blocking servers.\n"
            "- `web_search`: Look up documentation, APIs, or tutorials.\n"
            "- `install_package`: Install PyPI dependencies when hitting ModuleNotFoundError.\n"
            "- `consult_user`: Stop loop and ask the user for help if you are repeatedly failing (e.g., Auth 401s, mysterious bugs).\n"
            "- `finish_task`: End your turn. Provide a clear summary of modifications/results.\n\n"

            "OPERATIONAL RULES:\n"
            "1. NO BLIND OVERWRITES: If a file exists, `get_file_content` it first. Then use `edit_file` to modify it.\n"
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
            f" CURRENT PROJECT FILES:\n{current_project_state}\n\n"
        )

        # --- Character-Based Context Sliding Window ---
        MAX_CHARS = 120000  # Roughly 6,000 tokens
        
        messages = trim_memory(messages, MAX_CHARS, console)

        # --- STREAMING API CALL ---
        # Strings to hold the final output since the LLM gives it to us in tiny fragments
        full_content = ""
        stitched_tools = {}

        console.print("\n[dim cyan] Worker is thinking...[/dim cyan]")
        
        # Start a rich live block to visually smoothly append tokens to the console as they come from the API
        with Live(Markdown(""), console=console, refresh_per_second=15, vertical_overflow="visible") as live:
            response = await safe_mistral_stream_async(
                client=client,
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
                    console.print(f"\n[bold green] Worker task complete![/bold green]")
                    return summary
                
                # Execute the tool using our refactored helper
                function_result = await execute_tool(function_name, args, working_dir, auto_mode, console)

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

