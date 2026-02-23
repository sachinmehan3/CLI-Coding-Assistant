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
from functions.project_state import get_project_state
from ai_utils import safe_mistral_stream_async

# Import manager refactored tools and helpers
from manager_tools import MANAGER_TOOLS
from manager_helpers import display_project_tracker, trim_manager_memory, execute_manager_tool

# ==========================================
# THE MANAGER AGENT (The Tech Lead)
# ==========================================
async def run_tech_lead(client, model, console, working_dir):
    # These are the JSON-schema definitions for tools the Manager AI is permitted to use.
    manager_tools = MANAGER_TOOLS

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
            user_input = await asyncio.to_thread(console.input, "\n[bold blue]You > [/bold blue]")
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
                display_project_tracker(working_dir, console)
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
                
                manager_messages = await trim_manager_memory(manager_messages, MAX_MANAGER_CHARS, console, client, model)
                # --- END NEW CONTEXT ENGINEERING ---

                # FETCH THE LATEST REALITY
                current_project_state = get_file_info(working_dir, ".")
                current_tracker_json = get_project_state(working_dir)
                
                # Dynamically update the System Prompt (Index 0) with both!
                manager_messages[0]["content"] = (
                    f"{MANAGER_BASE_PROMPT}\n\n"
                    f" CURRENT PROJECT FILES:\n{current_project_state}\n\n"
                    f" CURRENT PROJECT TRACKER:\n{current_tracker_json}"
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
                        
                        # Execute the tool and get the resulting message dictionary using our helper
                        msg_to_append = await execute_manager_tool(
                            tc_name, tc_args_string, tc_id, 
                            working_dir, console, client, model, auto_mode
                        )
                        manager_messages.append(msg_to_append)
                    
                    # Continue the loop to allow chaining tasks!
                    continue 

                else:
                    # If no tool calls, the Manager just talked to you. Break the inner loop.
                    break
            # --- END OF INNER MANAGER LOOP ---

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            break
