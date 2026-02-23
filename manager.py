# manager.py
import os
import json
import argparse
from dotenv import load_dotenv
from mistralai import Mistral
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
import asyncio

# Import the manager's dependencies
from functions.get_files_info import get_file_info
from functions.get_file_content import get_file_content
from functions.project_state import get_project_state, update_project_state
from memory import summarize_manager_history
from worker import run_worker_agent
from ai_utils import safe_mistral_stream_async

# ==========================================
# THE MANAGER AGENT (The Tech Lead)
# ==========================================
async def run_tech_lead(client, model, console, working_dir):
    # These are the JSON-schema definitions for tools the Manager AI is permitted to use.
    # The language model uses these definitions to determine when and how to call a specific python function.
    manager_tools = [
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

    MANAGER_BASE_PROMPT = (
        "You are an expert, highly autonomous Tech Lead overseeing a developer agent. "

        "YOUR ROLE:\n"
        "You translate user requests into clear, actionable tasks for your developer. "
        "You bias heavily toward ACTION and speed. You do not write code yourself — you delegate everything through the `delegate_to_worker` tool.\n\n"

        "UNDERSTAND YOUR TEAM:\n"
        "- The 'Worker' (your developer) is a headless AI script. It CAN read/write files, create directories, download packages, run code, search the web, and consult the user if stuck. It CANNOT interact with visual GUIs.\n"
        "- The 'User' is a human. Only the human can visually verify UI apps.\n\n"

        "AVAILABLE TOOLS & WHEN TO USE THEM:\n"
        "- `get_file_content`: Use to read existing files BEFORE creating a plan or delegating a task that modifies them. You must understand the current architecture first.\n"
        "- `update_project_plan`: Use to update the project plan tracker. Call this whenever you have a new milestone plan approved by the user, or when the worker completes its task and the loop continues.\n"
        "- `delegate_to_worker`: Use to assign a specific milestone to the Worker. Provide cohesive, complete, step-by-step instructions so the worker can finish it in one attempt.\n\n"

        "OPERATIONAL RULES:\n"
        "1. NO TRIVIAL QUESTIONS: NEVER ask the user for minor design, formatting, or implementation preferences. Assume sensible industry defaults.\n"
        "2. ALWAYS PLAN FIRST: Write out a milestone plan and get user approval. Once approved, `update_project_plan` immediately.\n"
        "3. CONTINUOUS AUTONOMOUS EXECUTION: After updating the plan, execute all milestones autonomously. Automatically `delegate_to_worker` the next milestone as soon as the previous completes. NEVER wait for permission between milestones.\n"
        "4. SCALE MILESTONES (CRITICAL): Do not over-engineer simple tasks. For a basic script (like a calculator or single file app), use exactly 1 milestone. Only create multi-step plans for complex architectures spanning multiple files.\n"
        "5. REVIEW & FIX: Read the worker's completion report. If a task failed, you must formulate a fix and re-delegate.\n"
        "6. BEAUTIFUL FORMATTING: Talk to the User using Markdown (headers, bold text, bullet points)."
    )

    manager_messages = [
        {
            "role": "system",
            "content": MANAGER_BASE_PROMPT
        }
    ]
    console.print("[yellow]Starting the Agency... You are now talking to the Tech Lead![/yellow]")

    auto_mode = False

    # Main infinite loop to keep the console chat session alive
    while True:
        try:
            user_input = await asyncio.to_thread(console.input, "\n[bold blue]You (to Tech Lead) > [/bold blue]")
            if user_input.lower() in ["exit", "quit"]:
                break
            

            # --- Catch slash commands ---
            cmd = user_input.strip().lower()
            if cmd == "/auto":
                auto_mode = not auto_mode
                status_text = "ON (No prompts, high speed)" if auto_mode else "OFF (Safe mode, prompts enabled)"
                console.print(f"\n[bold magenta] Auto Mode is now {status_text}[/bold magenta]")
                continue # Skip sending this to Mistral
                
            elif cmd == "/clear":
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
                
            elif cmd in ["/status", "/plan"]:
                try:
                    state_str = get_project_state(working_dir)
                    current_state = json.loads(state_str)
                    goal = current_state.get("project_goal", "Not set")
                    status = current_state.get("status", "Not started")
                    curr = current_state.get("current_milestone", "None")
                    
                    status_markdown = f"**Goal:** {goal}\n\n**Status:** {status.upper()} | **Current:** {curr}\n\n**Completed:**\n"
                    for m in current_state.get("completed_milestones", []):
                        status_markdown += f"- {m}\n"
                    if not current_state.get("completed_milestones"):
                        status_markdown += "- *None yet*\n"
                        
                    status_markdown += "\n**Pending:**\n"
                    for m in current_state.get("pending_milestones", []):
                        status_markdown += f"- {m}\n"
                    if not current_state.get("pending_milestones"):
                        status_markdown += "- *None*\n"
                        
                    console.print("\n")
                    console.print(Panel(Markdown(status_markdown), title="[bold blue]🚀 Project Tracker[/bold blue]", border_style="blue", expand=False))
                    console.print("\n")
                except Exception as e:
                    console.print(f"[bold red]Could not read project tracker: {e}[/bold red]")
                continue
            # --------------------------------

            manager_messages.append({"role": "user", "content": user_input})

            # --- INNER MANAGER LOOP (Allows chaining tasks) ---
            # This loop allows the Tech Lead to keep taking tool actions automatically 
            # without stopping to ask the user, until a task is completely delegated or finished.
            while True:

                # --- Character-Based Manager Memory ---
                # A hard limit on context window size to stop the AI from reading too much and crashing.
                MAX_MANAGER_CHARS = 40000  # roughly 10,000 tokens
                
                # Simple function to count the size of a message, including any nested JSON tool blocks
                def get_msg_length(msg):
                    content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
                    tool_calls = msg.get("tool_calls", []) if isinstance(msg, dict) else getattr(msg, "tool_calls", [])
                    return len(str(content)) + len(str(tool_calls))

                total_manager_length = sum(get_msg_length(m) for m in manager_messages)

                if total_manager_length > MAX_MANAGER_CHARS:
                    console.print(f"\n[dim yellow] Tech Lead memory reached {total_manager_length} chars. Summarizing older tasks...[/dim yellow]")
                    
                    system_prompt = manager_messages[0]
                    
                    # Keep the last 8 messages so the Manager doesn't lose immediate context
                    tail = manager_messages[-8:]
                    
                    # Ensure we don't orphan a 'tool' message from its 'assistant' call
                    while len(tail) > 0:
                        first_msg = tail[0]
                        role = first_msg.get("role") if isinstance(first_msg, dict) else getattr(first_msg, "role", "")
                        if role == "tool":
                            tail.pop(0)
                        else:
                            break
                            
                    # The "middle" is everything between the system prompt and our protected tail
                    middle_messages = manager_messages[1 : len(manager_messages) - len(tail)]
                    
                    # Generate the summary using the secondary Mistral call
                    summary_text = await summarize_manager_history(client, model, middle_messages)
                    
                    # Package the summary as a persistent system context block
                    summary_message = {
                        "role": "system", 
                        "content": f"PREVIOUS TASKS SUMMARY:\n{summary_text}"
                    }
                    
                    # Rebuild the Manager's brain!
                    manager_messages = [system_prompt, summary_message] + tail
                # --- END NEW CONTEXT ENGINEERING ---

                # FETCH THE LATEST REALITY
                current_project_state = get_file_info(working_dir, ".")
                current_tracker_json = get_project_state(working_dir)
                
                # Dynamically update the System Prompt (Index 0) with both!
                manager_messages[0]["content"] = (
                    f"{MANAGER_BASE_PROMPT}\n\n"
                    f"📂 CURRENT PROJECT FILES:\n{current_project_state}\n\n"
                    f"📋 CURRENT PROJECT TRACKER:\n{current_tracker_json}"
                )
    

                # --- NEW STREAMING API CALL ---
                # We collect all chunks from Mistral into this variable
                full_content = ""
                # Mistral breaks tool calls up into tiny stream chunks too. We accumulate them here to parse later.
                stitched_tools = {}

                console.print("\n[dim cyan] Tech Lead is thinking...[/dim cyan]")
                
                # Open the Live render context
                with Live(Markdown(""), console=console, refresh_per_second=15, vertical_overflow="visible") as live:

                    response = await safe_mistral_stream_async(
                        client=client,
                        model=model,
                        messages=manager_messages,
                        tools=manager_tools
                    )
                    
                    async for chunk in response:
                        delta = chunk.data.choices[0].delta
                        
                        # 1. Stream Text to the Terminal
                        if delta.content:
                            full_content += delta.content
                            live.update(Markdown(full_content))
                            
                        # 2. Stitch Tool Calls in the Background
                        if delta.tool_calls:
                            for tool_chunk in delta.tool_calls:
                                idx = tool_chunk.index
                                
                                # If it's a new tool call, initialize it
                                if idx not in stitched_tools:
                                    stitched_tools[idx] = {
                                        "id": tool_chunk.id,
                                        "name": tool_chunk.function.name if tool_chunk.function.name else "",
                                        "arguments": tool_chunk.function.arguments if tool_chunk.function.arguments else ""
                                    }
                                # If it's an existing tool call, append the chunks
                                else:
                                    if tool_chunk.function.name:
                                        stitched_tools[idx]["name"] += tool_chunk.function.name
                                    if tool_chunk.function.arguments:
                                        stitched_tools[idx]["arguments"] += tool_chunk.function.arguments

                # --- RECONSTRUCT MANAGER MESSAGE FOR MEMORY ---
                manager_msg = {
                    "role": "assistant",
                    "content": full_content
                }
                
                parsed_tool_calls = []
                
                if stitched_tools:
                    tool_calls_list = []
                    for idx, tc in stitched_tools.items():
                        parsed_tool_calls.append(tc) # Save for execution
                        
                        # Format exactly how Mistral's API expects it in history
                        tool_calls_list.append({
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"]
                            }
                        })
                    manager_msg["tool_calls"] = tool_calls_list
                    
                manager_messages.append(manager_msg)
                # --- END STREAMING BLOCK ---

                # Did the Manager decide to delegate or update state?
                if parsed_tool_calls:
                    for tool_call in parsed_tool_calls:
                        tc_name = tool_call["name"]
                        tc_args_string = tool_call["arguments"]
                        tc_id = tool_call["id"]
                        
                        try:
                            args = json.loads(tc_args_string)
                        except json.JSONDecodeError:
                            manager_messages.append({
                                "role": "tool",
                                "name": tc_name,
                                "content": f"SYSTEM ERROR: Failed to parse tool arguments as JSON: {tc_args_string}",
                                "tool_call_id": tc_id 
                            })
                            continue
                        
                        # --- PLAN UPDATING ---
                        if tc_name == "update_project_plan":
                            
                            try:
                                current_state = json.loads(get_project_state(working_dir))
                            except Exception:
                                current_state = {
                                    "status": "in_progress",
                                    "completed_milestones": [],
                                    "current_milestone": None
                                }
                            
                            # Update the goal and pending milestones
                            current_state["project_goal"] = args.get("project_goal", current_state.get("project_goal"))
                            current_state["pending_milestones"] = args.get("milestones", [])
                            if "status" not in current_state:
                                current_state["status"] = "in_progress"
                            if "completed_milestones" not in current_state:
                                current_state["completed_milestones"] = []
                            
                            console.print("\n[dim cyan] Tech Lead is updating the project plan...[/dim cyan]")
                            update_project_state(working_dir, current_state)
                            
                            manager_messages.append({
                                "role": "tool",
                                "name": tc_name,
                                "content": "Plan successfully updated. You may now proceed.",
                                "tool_call_id": tc_id 
                            })
                            
                            # Automatically display status tracker
                            try:
                                status_markdown = f"**Goal:** {current_state.get('project_goal', 'Not set')}\n\n"
                                status_markdown += f"**Status:** {current_state.get('status', 'Not started').upper()} | **Current:** {current_state.get('current_milestone', 'None')}\n\n**Completed:**\n"
                                for m in current_state.get("completed_milestones", []):
                                    status_markdown += f"- {m}\n"
                                if not current_state.get("completed_milestones"):
                                    status_markdown += "- *None yet*\n"
                                    
                                status_markdown += "\n**Pending:**\n"
                                for m in current_state.get("pending_milestones", []):
                                    status_markdown += f"- {m}\n"
                                if not current_state.get("pending_milestones"):
                                    status_markdown += "- *None*\n"
                                    
                                console.print("\n")
                                console.print(Panel(Markdown(status_markdown), title="[bold blue]🚀 Project Tracker[/bold blue]", border_style="blue", expand=False))
                                console.print("\n")
                            except Exception as e:
                                console.print(f"[bold red]Could not display project tracker: {e}[/bold red]")

                        # --- UPDATED DELEGATION LOGIC ---
                        elif tc_name == "delegate_to_worker":
                            target_milestone = args.get("target_milestone")
                            task = args.get("task_description")
                            
                            # 1. Update state to show what is currently happening
                            current_state = json.loads(get_project_state(working_dir))
                            current_state["current_milestone"] = target_milestone
                            update_project_state(working_dir, current_state)

                            # 2. Run the Worker
                            worker_report = await run_worker_agent(client, model, console, task, working_dir, auto_mode)

                            # 3. DETERMINISTIC STATE UPDATE (The Worker Finished!)
                            current_state = json.loads(get_project_state(working_dir))
                            
                            if target_milestone in current_state["pending_milestones"]:
                                current_state["pending_milestones"].remove(target_milestone)
                            
                            if target_milestone not in current_state["completed_milestones"]:
                                current_state["completed_milestones"].append(target_milestone)
                                
                            current_state["current_milestone"] = None
                            
                            # Save the truth to disk
                            update_project_state(working_dir, current_state)

                            # 4. Give the report back to the Manager
                            manager_messages.append({
                                "role": "tool",
                                "name": "delegate_to_worker",
                                "content": f"WORKER REPORT:\n{worker_report}\n\nSYSTEM: Milestone '{target_milestone}' has been automatically marked as complete in the tracker.",
                                "tool_call_id": tc_id 
                            })

                        elif tc_name == "get_file_content":
                            file_path = args.get("file_path")

                            # --- NEW: Clean spinner for Tech Lead ---
                            with console.status(f"[bold cyan]Tech Lead reading '{file_path}'...[/bold cyan]", spinner="dots"):
                                result = get_file_content(working_dir, file_path)
                                console.print(f"[bold green]✓[/bold green] [dim]Tech Lead analyzed: {file_path}[/dim]")
                            
                            # Feed the file content back to the Manager
                            manager_messages.append({
                                "role": "tool",
                                "name": "get_file_content",
                                "content": str(result),
                                "tool_call_id": tc_id 
                            })
                    
                    # CRITICAL FIX: Continue the loop!
                    continue 

                else:
                    # If no tool calls, the Manager just talked to you. Break the inner loop.
                    break
            # --- END OF INNER MANAGER LOOP ---

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            break
