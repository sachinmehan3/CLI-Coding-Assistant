import json
from rich.markdown import Markdown
from rich.panel import Panel

from functions.project_state import get_project_state, update_project_state
from functions.get_file_content import get_file_content
from memory import summarize_planner_history
from worker import run_worker_agent

def display_project_tracker(working_dir, console):
    """Displays the current project tracker state as a formatted Rich Panel."""
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
    Prevents context overflow by summarizing the middle of the conversation.
    Keeps system prompt [0] and the last 8 messages intact, compresses
    everything in between via a secondary LLM call.
    """
    def get_msg_length(msg):
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        tool_calls = msg.get("tool_calls", []) if isinstance(msg, dict) else getattr(msg, "tool_calls", [])
        return len(str(content)) + len(str(tool_calls))

    total_planner_length = sum(get_msg_length(m) for m in messages)

    if total_planner_length > max_chars:
        console.print(f"\n[dim yellow] Memory reached {total_planner_length} chars. Summarizing older tasks...[/dim yellow]")
        
        system_prompt = messages[0]
        tail = messages[-8:]
        
        # Drop orphaned 'tool' messages at the start of the tail so we
        # don't break the assistant→tool pairing Mistral expects
        while len(tail) > 0:
            first_msg = tail[0]
            role = first_msg.get("role") if isinstance(first_msg, dict) else getattr(first_msg, "role", "")
            if role == "tool":
                tail.pop(0)
            else:
                break
                
        middle_messages = messages[1 : len(messages) - len(tail)]
        summary_text = summarize_planner_history(client, model, middle_messages)
        
        summary_message = {
            "role": "system", 
            "content": f"PREVIOUS TASKS SUMMARY:\n{summary_text}"
        }
        
        messages = [system_prompt, summary_message] + tail
    
    return messages

def execute_planner_tool(tc_name, tc_args_string, tc_id, working_dir, console, client, model, auto_mode):
    """Routes Planner tool calls to their implementations and returns formatted tool response dicts."""
    try:
        args = json.loads(tc_args_string)
    except json.JSONDecodeError:
        return {
            "role": "tool",
            "name": tc_name,
            "content": f"SYSTEM ERROR: Failed to parse tool arguments as JSON: {tc_args_string}",
            "tool_call_id": tc_id 
        }
    
    if tc_name == "update_project_plan":
        try:
            current_state = json.loads(get_project_state(working_dir))
        except Exception:
            current_state = {
                "status": "in_progress",
                "completed_tasks": [],
                "current_task": None
            }
        
        current_state["project_goal"] = args.get("project_goal", current_state.get("project_goal"))
        current_state["pending_tasks"] = args.get("milestones", [])
        if "status" not in current_state:
            current_state["status"] = "in_progress"
        if "completed_tasks" not in current_state:
            current_state["completed_tasks"] = []
        
        console.print("\n[dim cyan] Updating the project plan...[/dim cyan]")
        update_project_state(working_dir, current_state)
        display_project_tracker(working_dir, console)

        return {
            "role": "tool",
            "name": tc_name,
            "content": "Plan successfully updated. You may now proceed.",
            "tool_call_id": tc_id 
        }

    elif tc_name == "delegate_to_worker":
        target_task = args.get("target_milestone", "unknown_task")
        task = args.get("task_description", "")
        
        try:
            current_state = json.loads(get_project_state(working_dir))
        except (json.JSONDecodeError, ValueError):
            current_state = {"status": "in_progress", "completed_tasks": [], "pending_tasks": []}
        current_state["current_task"] = target_task
        update_project_state(working_dir, current_state)

        # Blocking call — Planner sleeps until Worker finishes its entire sub-agent loop
        worker_report = run_worker_agent(client, model, console, task, working_dir, auto_mode)

        # Worker may have deleted project_state.json, so we fall back gracefully
        try:
            current_state = json.loads(get_project_state(working_dir))
        except (json.JSONDecodeError, ValueError):
            current_state = {"status": "in_progress", "completed_tasks": [], "pending_tasks": []}
        
        if "pending_tasks" not in current_state:
            current_state["pending_tasks"] = []
        if "completed_tasks" not in current_state:
            current_state["completed_tasks"] = []

        # Monolithic architecture: worker handles all features at once, so move all pending → completed
        for task_name in current_state["pending_tasks"]:
            if task_name not in current_state["completed_tasks"]:
                current_state["completed_tasks"].append(task_name)
                
        current_state["pending_tasks"] = []
        
        if target_task not in current_state["completed_tasks"]:
            current_state["completed_tasks"].append(target_task)
            
        current_state["current_task"] = None
        update_project_state(working_dir, current_state)
        display_project_tracker(working_dir, console)

        return {
            "role": "tool",
            "name": "delegate_to_worker",
            "content": f"WORKER REPORT:\n{worker_report}\n\nSYSTEM: Task '{target_task}' is complete. The project specification has been completed. Inform the user.",
            "tool_call_id": tc_id 
        }

    elif tc_name == "get_file_content":
        file_path = args.get("file_path")

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
        "content": f"SYSTEM ERROR: Unknown tool {tc_name} called by Planner.",
        "tool_call_id": tc_id
    }
