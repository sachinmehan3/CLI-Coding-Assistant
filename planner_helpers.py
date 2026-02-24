import json
from rich.markdown import Markdown
from rich.panel import Panel

from functions.project_state import get_project_state, update_project_state
from functions.get_file_content import get_file_content
from memory import summarize_manager_history
from worker import run_worker_agent

def display_project_tracker(working_dir, console):
    """
    Displays the current state of the project tracker via a beautifully formatted Rich Panel.
    This UI component reads the JSON state file and visually separates the overarching goal, 
    the active milestone, and the lists of completed vs. pending tasks for easy human readability.
    """
    try:
        state_str = get_project_state(working_dir)
        current_state = json.loads(state_str)
        goal = current_state.get("project_goal", "Not set")
        status = current_state.get("status", "Not started")
        curr = current_state.get("current_task", "None")
        
        status_markdown = f"**Goal:** {goal}\n\n**Status:** {status.upper()} | **Current:** {curr}\n\n**Completed:**\n"
        for m in current_state.get("completed_tasks", []):
            status_markdown += f"- {m}\n"
        if not current_state.get("completed_tasks"):
            status_markdown += "- *None yet*\n"
            
        status_markdown += "\n**Pending:**\n"
        for m in current_state.get("pending_tasks", []):
            status_markdown += f"- {m}\n"
        if not current_state.get("pending_tasks"):
            status_markdown += "- *None*\n"
            
        console.print("\n")
        console.print(Panel(Markdown(status_markdown), title="[bold blue] Project Tracker[/bold blue]", border_style="blue", expand=False))
        console.print("\n")
    except Exception as e:
        console.print(f"[bold red]Could not read project tracker: {e}[/bold red]")

def trim_planner_memory(messages, max_chars, console, client, model):
    """
    Summarizes the middle of the planner's memory if it exceeds max_chars.
    Keeps the system prompt (index 0) and the most recent messages.
    This prevents the AI's context limit from being exceeded while preserving critical details.
    
    The strategy:
    1. Keep the System Prompt (Index 0) untouched.
    2. Keep the most recent 8 messages (the "tail") untouched for immediate context.
    3. Take all messages in between (the "middle"), send them to a secondary LLM call, 
       and ask it to compress them into a dense factual summary.
    4. Replace the middle messages with a single new "System" message containing that summary.
    """
    def get_msg_length(msg):
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        tool_calls = msg.get("tool_calls", []) if isinstance(msg, dict) else getattr(msg, "tool_calls", [])
        return len(str(content)) + len(str(tool_calls))

    total_planner_length = sum(get_msg_length(m) for m in messages)

    if total_planner_length > max_chars:
        console.print(f"\n[dim yellow] Memory reached {total_planner_length} chars. Summarizing older tasks...[/dim yellow]")
        
        system_prompt = messages[0]
        
        # Keep the last 8 messages so the Planner doesn't lose immediate context
        tail = messages[-8:]
        
        # Ensure we don't orphan a 'tool' message from its 'assistant' call
        while len(tail) > 0:
            first_msg = tail[0]
            role = first_msg.get("role") if isinstance(first_msg, dict) else getattr(first_msg, "role", "")
            if role == "tool":
                tail.pop(0)
            else:
                break
                
        # The "middle" is everything between the system prompt and our protected tail
        middle_messages = messages[1 : len(messages) - len(tail)]
        
        # Generate the summary using the secondary Mistral call
        summary_text = summarize_manager_history(client, model, middle_messages)
        
        # Package the summary as a persistent system context block
        summary_message = {
            "role": "system", 
            "content": f"PREVIOUS TASKS SUMMARY:\n{summary_text}"
        }
        
        # Rebuild the Planner's brain!
        messages = [system_prompt, summary_message] + tail
    
    return messages

def execute_planner_tool(tc_name, tc_args_string, tc_id, working_dir, console, client, model, auto_mode):
    """
    Executes a tool called by the Planner and returns a formatted message dict
    to append to the planner's conversation history.
    Central router for executing the Planner Agent's assigned tools.
    Takes the raw parsed tool call data from Mistral, matches it to the correct local Python function,
    executes the logic, and formats the return message exactly how Mistral's API expects tool responses.
    """
    try:
        # Mistral passes tool arguments as a JSON string, so we must parse it first.
        args = json.loads(tc_args_string)
    except json.JSONDecodeError:
        # If the AI hallucinates bad JSON, we return an error message to let it try again.
        return {
            "role": "tool",
            "name": tc_name,
            "content": f"SYSTEM ERROR: Failed to parse tool arguments as JSON: {tc_args_string}",
            "tool_call_id": tc_id 
        }
    
    # --- PLAN UPDATING LOGIC ---
    # Triggered when the Tech Lead wants to establish or modify the milestone roadmap.
    if tc_name == "update_project_plan":
        try:
            current_state = json.loads(get_project_state(working_dir))
        except Exception:
            # First time initialization fallback if the file doesn't exist or is corrupted.
            current_state = {
                "status": "in_progress",
                "completed_tasks": [],
                "current_task": None
            }
        
        # Override the existing goal and pending tasks with the new data from the Tech Lead.
        current_state["project_goal"] = args.get("project_goal", current_state.get("project_goal"))
        current_state["pending_tasks"] = args.get("milestones", [])
        if "status" not in current_state:
            current_state["status"] = "in_progress"
        if "completed_tasks" not in current_state:
            current_state["completed_tasks"] = []
        
        console.print("\n[dim cyan] Updating the project plan...[/dim cyan]")
        update_project_state(working_dir, current_state)
        
        # Automatically display status tracker
        display_project_tracker(working_dir, console)

        return {
            "role": "tool",
            "name": tc_name,
            "content": "Plan successfully updated. You may now proceed.",
            "tool_call_id": tc_id 
        }

    # --- DELEGATION LOGIC ---
    # Triggered when the Tech Lead is ready to assign a specific task to the Worker agent.
    elif tc_name == "delegate_to_worker":
        # Extract the metadata for this specific assignment
        target_task = args.get("target_milestone", "unknown_task")
        task = args.get("task_description", "")
        
        # 1. Update the tracker state so the UI shows this task is currently active.
        current_state = json.loads(get_project_state(working_dir))
        current_state["current_task"] = target_task
        update_project_state(working_dir, current_state)

        # 2. Synchronous/Blocking call to run the Worker. 
        # The Manager goes to "sleep" and waits here until the Worker fully finishes its sub-agent loop.
        worker_report = run_worker_agent(client, model, console, task, working_dir, auto_mode)

        # 3. DETERMINISTIC STATE UPDATE (The Monolithic Worker Finished!)
        # Now that the worker is done, we auto-advance the tracker locally.
        current_state = json.loads(get_project_state(working_dir))
        
        if "pending_tasks" not in current_state:
            current_state["pending_tasks"] = []
        if "completed_tasks" not in current_state:
            current_state["completed_tasks"] = []

        # In our monolithic Two-Stage architecture, the worker completes ALL features at once.
        # Therefore, we move all pending tasks to completed.
        for task_name in current_state["pending_tasks"]:
            if task_name not in current_state["completed_tasks"]:
                current_state["completed_tasks"].append(task_name)
                
        # Clear the pending array now that everything is built
        current_state["pending_tasks"] = []
        
        # Also ensure the overarching monolithic target name is tracked
        if target_task not in current_state["completed_tasks"]:
            current_state["completed_tasks"].append(target_task)
            
        # Clear the active status because the worker has returned.
        current_state["current_task"] = None
        
        # Save the finalized truth to disk.
        update_project_state(working_dir, current_state)

        # Automatically display status tracker now that the worker is completely done.
        display_project_tracker(working_dir, console)

        # Return a summarized report back to the Manager so it knows if the Worker succeeded or failed.

        return {
            "role": "tool",
            "name": "delegate_to_worker",
            "content": f"WORKER REPORT:\n{worker_report}\n\nSYSTEM: Task '{target_task}' is complete. The project specification has been completed. Inform the user.",
            "tool_call_id": tc_id 
        }

    elif tc_name == "get_file_content":
        file_path = args.get("file_path")

        # --- Clean spinner ---
        with console.status(f"[bold cyan]Reading '{file_path}'...[/bold cyan]", spinner="dots"):
            result = get_file_content(working_dir, file_path)
            console.print(f"[dim]Analyzed: {file_path}[/dim]")
        
        return {
            "role": "tool",
            "name": "get_file_content",
            "content": str(result),
            "tool_call_id": tc_id 
        }
    
    return {
        "role": "tool",
        "name": tc_name,
        "content": f"SYSTEM ERROR: Unknown tool {tc_name} called by Tech Lead.",
        "tool_call_id": tc_id
    }
