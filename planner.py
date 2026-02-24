# planner.py
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

# Import the planner's dependencies
from functions.get_files_info import get_file_info
from functions.project_state import get_project_state
from ai_utils import safe_mistral_complete

# Import planner refactored tools and helpers
from planner_tools import PLANNER_TOOLS
from planner_helpers import display_project_tracker, trim_planner_memory, execute_planner_tool

# ==========================================
# THE PLANNER AGENT
# ==========================================

PLANNER_BASE_PROMPT = (
    "You are an expert, highly autonomous Planner overseeing a developer agent. "

    "YOUR ROLE:\n"
    "You translate user requests into actionable tasks for your developer and manage their execution until the initial request is completely resolved.\n"
    "You do not write code yourself — you delegate everything through the `delegate_to_worker` tool.\n\n"

    "UNDERSTAND YOUR TEAM:\n"
    "- The 'Worker' (your developer) is a headless AI script. It CAN read/write files, create directories, run code, search the web, etc. It CANNOT interact with visual GUIs.\n"
    "- The 'User' is a human.\n\n"

    "AVAILABLE TOOLS & WHEN TO USE THEM:\n"
    "- `get_file_content`: Use to read existing files to understand the current architecture before making a plan or delegating.\n"
    "- `update_project_plan`: Use to set or update the list of features/specifications needed to fulfill the user's request. Call this during the Planning Stage after agreeing on features with the user.\n"
    "- `delegate_to_worker`: Use to assign the ENTIRE project specification to the Worker in one massive prompt.\n\n"

    "OPERATIONAL RULES:\n"
    "1. TWO-STAGE PROCESS: You operate in two distinct stages.\n"
    "   - STAGE 1 (Planning): Discuss the user's request, outline all features, architectures, and fixes. Do NOT delegate yet. Once the user agrees, use `update_project_plan` to lock in the agreed features.\n"
    "   - STAGE 2 (Delegation): Give a SINGLE, highly detailed prompt to the Worker mapping out ALL specifications at once using `delegate_to_worker`. The prompt MUST include the desired directory structure, what directories to create, and what files to create.\n"
    "2. FULL AUTONOMY FOR THE WORKER: Push the worker to complete the entire app in its own loop based on your massive prompt. Do not break it down step-by-step for the worker.\n"
    "3. NO HAND-HOLDING: Do not stop to explain every step to the user mid-execution. Your job is to get it done completely and only return control to the user when the entire project plan is 100% finished.\n"
    "4. REVIEW & FIX: If the monolithic task fails based on the worker's report, fix the prompt and re-delegate immediately.\n"
)

def get_initial_planner_messages():
    """Returns the freshly initialized memory block for a brand new Planner agent."""
    return [
        {
            "role": "system",
            "content": PLANNER_BASE_PROMPT
        }
    ]

def run_planner_step(client, model, console, working_dir, user_input, planner_messages, auto_mode):
    # These are the JSON-schema definitions for tools the Planner AI is permitted to use.
    planner_tools = PLANNER_TOOLS

    # Append the newest user input to the planner's memory
    planner_messages.append({"role": "user", "content": user_input})

    # --- PLANNER THINKING LOOP (Allows chaining tasks) ---
    # This loop is crucial for the Planner's autonomy. It allows the planner to repeatedly
    # process the project state, call tools (like delegating to the worker or updating the plan), 
    # and receive the results of those tool calls without needing to ask the human user for 
    # further input. The loop only breaks when the Planner outputs a regular message (no tool calls),
    # which usually means it's returning control or asking a question to the user.
    while True:
        try:
            # --- Character-Based Planner Memory ---
            # To prevent the context window from growing indefinitely and causing API limits or 
            # high costs, we enforce a strict character limit on the Planner's message history.
            MAX_PLANNER_CHARS = 40000  # roughly 10,000 tokens
            
            # trim_planner_memory will summarize old messages if the limit is exceeded, 
            # keeping the system prompt and recent history intact but compressing the middle.
            planner_messages = trim_planner_memory(planner_messages, MAX_PLANNER_CHARS, console, client, model)


            # --- FETCH THE LATEST REALITY ---
            # Before every single decision, the Planner needs to see the current state of the world.
            # get_file_info: Returns a map of all files in the directory so the Planner knows what exists.
            # get_project_state: Returns the status of the current plan (tasks, goals, etc.).
            current_project_state = get_file_info(working_dir, ".")
            current_tracker_json = get_project_state(working_dir)
            
            # Dynamically update the System Prompt (Index 0) with both!
            # By constantly updating the system prompt with this data, the Planner is never "blind".
            planner_messages[0]["content"] = (
                f"{PLANNER_BASE_PROMPT}\n\n"
                f" CURRENT PROJECT FILES:\n{current_project_state}\n\n"
                f" CURRENT PROJECT TRACKER:\n{current_tracker_json}"
            )

            # --- API CALL ---
            with console.status("[bold cyan]Thinking...[/bold cyan]", spinner="dots"):

                response = safe_mistral_complete(
                    client=client,
                    model=model,
                    messages=planner_messages,
                    tools=planner_tools
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

            # --- RECONSTRUCT PLANNER MESSAGE FOR MEMORY ---
            # After the stream finishes, we package the total text content generated by the AI
            # into a standard assistant message format to append to the chat history.
            planner_msg = {
                "role": "assistant",
                "content": full_content
            }
            
            # Render the AI's response text to the terminal if it exists
            if full_content.strip():
                console.print(Markdown(full_content))
            
            parsed_tool_calls = []
            
            # If the AI decided to use any tools during its stream, we must reconstruct the 
            # specialized "tool_calls" array exactly how the Mistral API expects to see it 
            # in the conversation history for context on what actions were taken.
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
                planner_msg["tool_calls"] = tool_calls_list
                
            planner_messages.append(planner_msg)
            # --- END STREAMING BLOCK ---

            # --- TOOL EXECUTION PHASE ---
            # Did the Planner decide to delegate or update state?
            if parsed_tool_calls:
                for tool_call in parsed_tool_calls:
                    tc_name = tool_call["name"]
                    tc_args_string = tool_call["arguments"]
                    tc_id = tool_call["id"]
                    
                    # Execute the tool (e.g. update tracker, or spin up the Worker agent)
                    # and get the resulting system confirmation message indicating success/failure.
                    msg_to_append = execute_planner_tool(
                        tc_name, tc_args_string, tc_id, 
                        working_dir, console, client, model, auto_mode
                    )
                    # Append the tool's result to the history so the Planner knows what happened.
                    planner_messages.append(msg_to_append)
                
                # Continue the inner loop to allow chaining tasks! The Planner will see the 
                # tool result and immediately make its next decision.
                continue 

            else:
                # If no tool calls were made, the Planner just output regular conversational text.
                # Break the inner loop to surrender control back to the human user, and return messages 
                # to central router so it remembers state for next turn.
                return planner_messages
                
        except Exception as e:
            import traceback
            console.print(f"[bold red]Error in Planner Loop:[/bold red] {e}")
            console.print(f"[bold red]Traceback:[/bold red]\n{traceback.format_exc()}")
            return planner_messages

